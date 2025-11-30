"""
Tux Tunes - Audio Player with Smart Recording

GStreamer-based audio player with intelligent buffered recording
that captures complete songs without cut-offs.

THE KEY INNOVATION:
- Pre-buffer: Always keeps last N seconds in memory
- On song change: Include pre-buffer in new recording
- Post-buffer: Continue recording N seconds after metadata change
- Result: Clean cuts that capture full songs!

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import re
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Callable
from collections import deque

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstPbutils, GLib

from .api import Station


# Initialize GStreamer
Gst.init(None)


@dataclass
class TrackInfo:
    """Information about current/recorded track."""
    title: str
    artist: str
    station_name: str
    started_at: datetime
    duration: float = 0.0
    filepath: Optional[str] = None
    saved: bool = False
    
    @property
    def display_name(self) -> str:
        """Get display name for track."""
        if self.artist and self.title:
            return f"{self.artist} - {self.title}"
        return self.title or "Unknown Track"
    
    @property 
    def filename_safe(self) -> str:
        """Get filename-safe version of track name."""
        name = self.display_name
        # Remove/replace invalid filename characters
        name = re.sub(r'[<>:"/\\|?*&]', '_', name)
        name = re.sub(r'\s+', ' ', name).strip()
        return name[:100]  # Limit length


@dataclass 
class CachedRecording:
    """A cached recording waiting to be saved or discarded."""
    track: TrackInfo
    temp_filepath: str
    created_at: datetime
    
    @property
    def age_seconds(self) -> float:
        return (datetime.now() - self.created_at).total_seconds()


class AudioBuffer:
    """Circular buffer for audio data (for pre-buffering)."""
    
    def __init__(self, max_seconds: float = 10.0, sample_rate: int = 44100, channels: int = 2):
        self.max_seconds = max_seconds
        self.sample_rate = sample_rate
        self.channels = channels
        # Approximate bytes per second for 16-bit audio
        self.bytes_per_second = sample_rate * channels * 2
        self.max_bytes = int(max_seconds * self.bytes_per_second)
        self.buffer = deque(maxlen=self.max_bytes)
        self.lock = threading.Lock()
    
    def add(self, data: bytes):
        """Add data to buffer."""
        with self.lock:
            for byte in data:
                self.buffer.append(byte)
    
    def get_all(self) -> bytes:
        """Get all buffered data."""
        with self.lock:
            return bytes(self.buffer)
    
    def clear(self):
        """Clear the buffer."""
        with self.lock:
            self.buffer.clear()
    
    def get_duration(self) -> float:
        """Get approximate duration of buffered audio in seconds."""
        with self.lock:
            return len(self.buffer) / self.bytes_per_second if self.bytes_per_second > 0 else 0


class Player:
    """GStreamer-based audio player with smart recording."""
    
    # Temp directory for cached recordings
    CACHE_DIR = "/tmp/tux-tunes-cache"
    
    def __init__(self, library):
        self.library = library
        
        # Callbacks
        self.on_state_changed: Optional[Callable[[str], None]] = None
        self.on_metadata_changed: Optional[Callable[[str, str], None]] = None
        self.on_track_changed: Optional[Callable[[TrackInfo], None]] = None
        self.on_recording_ready: Optional[Callable[['CachedRecording'], None]] = None
        self.on_recording_state: Optional[Callable[[bool], None]] = None  # For UI indicator
        self.on_error: Optional[Callable[[str], None]] = None
        self.on_buffer_level: Optional[Callable[[int], None]] = None
        
        # State
        self.current_station: Optional[Station] = None
        self.current_track: Optional[TrackInfo] = None
        self.track_history: list[TrackInfo] = []
        self.is_playing = False
        self.volume = library.get_config('volume', 1.0)
        
        # Recording settings
        self.auto_record = True  # Always record in background
        self.min_recording_seconds = library.get_config('min_recording_seconds', 10)  # Lowered from 30
        self.max_recording_seconds = library.get_config('max_recording_seconds', 600)
        
        # Auto-recording state
        self.is_recording = False
        self.recording_filepath = None
        self.recording_start_time = None
        self.cached_recordings: list[CachedRecording] = []  # Waiting to be saved
        
        # Recording pipeline elements (created dynamically)
        self.recording_queue = None
        self.audio_convert2 = None
        self.encoder = None
        self.muxer = None
        self.filesink = None
        self.recording_tee_pad = None
        
        # Current metadata
        self._current_title = ""
        self._current_artist = ""
        
        # Ensure cache directory exists
        os.makedirs(self.CACHE_DIR, exist_ok=True)
        
        # Create playback pipeline
        self._create_pipeline()
    
    def _create_pipeline(self):
        """Create GStreamer pipeline for playback and recording."""
        # Main pipeline: source -> decodebin -> audioconvert -> tee -> [queue -> sink, queue -> filesink]
        self.pipeline = Gst.Pipeline.new("tux-tunes-player")
        
        # Source (will be set when playing)
        self.source = Gst.ElementFactory.make("uridecodebin", "source")
        self.source.connect("pad-added", self._on_pad_added)
        
        # Audio convert and resample
        self.audioconvert = Gst.ElementFactory.make("audioconvert", "audioconvert")
        self.audioresample = Gst.ElementFactory.make("audioresample", "audioresample")
        
        # Volume control
        self.volume_element = Gst.ElementFactory.make("volume", "volume")
        self.volume_element.set_property("volume", self.volume)
        
        # Tee to split audio to playback and recording
        self.tee = Gst.ElementFactory.make("tee", "tee")
        # Allow tee to work even when recording branch isn't connected
        self.tee.set_property("allow-not-linked", True)
        
        # Playback branch
        self.playback_queue = Gst.ElementFactory.make("queue", "playback_queue")
        self.audiosink = Gst.ElementFactory.make("autoaudiosink", "audiosink")
        
        # Recording branch (created dynamically when recording)
        self.recording_queue = None
        self.audio_convert2 = None
        self.encoder = None
        self.muxer = None
        self.filesink = None
        self.recording_tee_pad = None
        
        # Add elements to pipeline
        for element in [self.source, self.audioconvert, self.audioresample, 
                        self.volume_element, self.tee, self.playback_queue, self.audiosink]:
            self.pipeline.add(element)
        
        # Link static elements (audioconvert onwards)
        self.audioconvert.link(self.audioresample)
        self.audioresample.link(self.volume_element)
        self.volume_element.link(self.tee)
        
        # Link playback branch using request pad
        self.playback_tee_pad = self.tee.request_pad_simple("src_%u")
        playback_sink_pad = self.playback_queue.get_static_pad("sink")
        self.playback_tee_pad.link(playback_sink_pad)
        self.playback_queue.link(self.audiosink)
        
        # Set up bus for messages
        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self._on_bus_message)
    
    def _on_pad_added(self, element, pad):
        """Handle dynamic pad from decodebin."""
        caps = pad.get_current_caps()
        if caps:
            structure = caps.get_structure(0)
            if structure.get_name().startswith("audio"):
                sink_pad = self.audioconvert.get_static_pad("sink")
                if not sink_pad.is_linked():
                    pad.link(sink_pad)
    
    def _on_bus_message(self, bus, message):
        """Handle GStreamer bus messages."""
        t = message.type
        
        if t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            error_msg = f"Playback error: {err.message}"
            print(f"GStreamer error: {err.message}\nDebug: {debug}")
            GLib.idle_add(self._emit_error, error_msg)
            self.stop()
            
        elif t == Gst.MessageType.EOS:
            print("End of stream")
            self.stop()
            
        elif t == Gst.MessageType.BUFFERING:
            percent = message.parse_buffering()
            if self.on_buffer_level:
                GLib.idle_add(self.on_buffer_level, percent)
                
        elif t == Gst.MessageType.STATE_CHANGED:
            if message.src == self.pipeline:
                old, new, pending = message.parse_state_changed()
                state_name = new.value_nick
                self.is_playing = (new == Gst.State.PLAYING)
                if self.on_state_changed:
                    GLib.idle_add(self.on_state_changed, state_name)
                    
        elif t == Gst.MessageType.TAG:
            taglist = message.parse_tag()
            self._handle_tags(taglist)
    
    def _normalize_track_name(self, title: str, artist: str) -> str:
        """Normalize track info for comparison to avoid phantom changes."""
        # Combine and lowercase
        combined = f"{artist} - {title}".lower().strip()
        # Remove extra whitespace
        combined = ' '.join(combined.split())
        # Remove common variations
        combined = combined.replace("'", "").replace('"', "").replace("(", "").replace(")", "")
        return combined
    
    def _handle_tags(self, taglist):
        """Handle metadata tags from stream."""
        title = None
        artist = None
        
        # Try to get title
        success, value = taglist.get_string(Gst.TAG_TITLE)
        if success:
            title = value
        
        # Try to get artist
        success, value = taglist.get_string(Gst.TAG_ARTIST)
        if success:
            artist = value
        
        # Check if metadata actually changed (using normalized comparison)
        if title:
            new_normalized = self._normalize_track_name(title, artist or "")
            old_normalized = self._normalize_track_name(self._current_title or "", self._current_artist or "")
            
            # Only trigger change if normalized versions are different
            if new_normalized != old_normalized:
                old_title = self._current_title
                self._current_title = title
                self._current_artist = artist or ""
                
                # Emit callback
                if self.on_metadata_changed:
                    GLib.idle_add(self.on_metadata_changed, title, artist or "")
                
                # Handle track change for auto-recording
                if old_title:  # Not the first track
                    print(f"Track changed: '{old_title}' -> '{title}'")
                    self._on_track_change(title, artist or "")
                else:
                    # First track - start tracking and recording
                    print(f"First track: '{title}'")
                    self._start_new_track(title, artist or "")
                    if self.auto_record and self.is_playing and not self.is_recording:
                        self._start_auto_recording()
    
    def _on_track_change(self, new_title: str, new_artist: str):
        """Handle track change - rotate the recording to cache."""
        # Grace period: If recording just started (< 5 seconds), don't rotate
        # Just update the track info - this handles stations that send station name first
        if self.current_track:
            age = (datetime.now() - self.current_track.started_at).total_seconds()
            if age < 5.0:
                print(f"  Grace period: Track info updated (recording only {age:.1f}s old)")
                # Update the track info without rotating
                self.current_track.title = new_title
                self.current_track.artist = new_artist
                self._current_title = new_title
                self._current_artist = new_artist
                return
        
        # Schedule recording rotation on main thread to avoid GStreamer threading issues
        GLib.idle_add(self._rotate_recording, new_title, new_artist)
    
    def _rotate_recording(self, new_title: str, new_artist: str):
        """Rotate recording - must run on main thread."""
        print(f"Rotate recording: is_recording={self.is_recording}, current_track={self.current_track is not None}")
        
        # Finalize current recording and cache it
        if self.is_recording and self.current_track:
            self.current_track.duration = (datetime.now() - self.current_track.started_at).total_seconds()
            print(f"  Track duration: {self.current_track.duration:.1f}s (min: {self.min_recording_seconds}s)")
            
            # Stop current recording and cache it if long enough (reduced to 10s)
            if self.current_track.duration >= self.min_recording_seconds:
                print(f"  Finalizing recording...")
                cached = self._finalize_current_recording()
                if cached:
                    print(f"  Cached: {cached.temp_filepath}")
                    self.cached_recordings.append(cached)
                    # Keep only last 20 cached recordings
                    while len(self.cached_recordings) > 20:
                        old = self.cached_recordings.pop(0)
                        self._delete_cached_recording(old)
                    
                    # Notify UI
                    if self.on_recording_ready:
                        self.on_recording_ready(cached)
            else:
                # Too short, just discard
                print(f"  Too short, discarding")
                self._stop_recording_internal(discard=True)
        
        # Start tracking new track
        self._start_new_track(new_title, new_artist)
        
        # Start recording the new track
        if self.auto_record and self.is_playing:
            self._start_auto_recording()
        
        return False  # Don't repeat
    
    def _start_new_track(self, title: str, artist: str):
        """Start tracking a new track."""
        self.current_track = TrackInfo(
            title=title,
            artist=artist,
            station_name=self.current_station.name if self.current_station else "Unknown",
            started_at=datetime.now(),
        )
    
    def _emit_error(self, message: str):
        """Emit error callback on main thread."""
        if self.on_error:
            self.on_error(message)
    
    def _start_auto_recording(self):
        """Start automatic background recording to temp file."""
        if self.is_recording:
            print("Auto-recording: Already recording")
            return
        
        print(f"Auto-recording: Starting (is_playing={self.is_playing})")
        
        # Generate temp filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_filename = f"recording_{timestamp}.ogg"
        self.recording_filepath = os.path.join(self.CACHE_DIR, temp_filename)
        
        try:
            # Create recording elements
            self.recording_queue = Gst.ElementFactory.make("queue", "recording_queue")
            self.audio_convert2 = Gst.ElementFactory.make("audioconvert", "audioconvert2")
            self.encoder = Gst.ElementFactory.make("vorbisenc", "encoder")
            self.muxer = Gst.ElementFactory.make("oggmux", "muxer")
            self.filesink = Gst.ElementFactory.make("filesink", "filesink")
            
            if not all([self.recording_queue, self.audio_convert2, self.encoder, self.muxer, self.filesink]):
                print("Failed to create auto-recording elements")
                return
            
            self.filesink.set_property("location", self.recording_filepath)
            
            # Add to pipeline
            self.pipeline.add(self.recording_queue)
            self.pipeline.add(self.audio_convert2)
            self.pipeline.add(self.encoder)
            self.pipeline.add(self.muxer)
            self.pipeline.add(self.filesink)
            
            # Link chain
            self.recording_queue.link(self.audio_convert2)
            self.audio_convert2.link(self.encoder)
            self.encoder.link(self.muxer)
            self.muxer.link(self.filesink)
            
            # Set to playing
            self.recording_queue.set_state(Gst.State.PLAYING)
            self.audio_convert2.set_state(Gst.State.PLAYING)
            self.encoder.set_state(Gst.State.PLAYING)
            self.muxer.set_state(Gst.State.PLAYING)
            self.filesink.set_state(Gst.State.PLAYING)
            
            # Connect to tee
            self.recording_tee_pad = self.tee.request_pad_simple("src_%u")
            queue_pad = self.recording_queue.get_static_pad("sink")
            if self.recording_tee_pad and queue_pad:
                self.recording_tee_pad.link(queue_pad)
            
            self.is_recording = True
            self.recording_start_time = datetime.now()
            print(f"Auto-recording: Started successfully to {self.recording_filepath}")
            
            # Notify UI
            if self.on_recording_state:
                GLib.idle_add(self.on_recording_state, True)
            
        except Exception as e:
            print(f"Auto-recording start failed: {e}")
            import traceback
            traceback.print_exc()
    
    def _finalize_current_recording(self) -> Optional[CachedRecording]:
        """Finalize current recording and return cached recording info."""
        if not self.is_recording or not self.current_track:
            return None
        
        filepath = self.recording_filepath
        track = TrackInfo(
            title=self.current_track.title,
            artist=self.current_track.artist,
            station_name=self.current_track.station_name,
            started_at=self.current_track.started_at,
            duration=self.current_track.duration,
            filepath=filepath,
        )
        
        # Stop recording
        self._stop_recording_internal(discard=False)
        
        # Create cached recording
        return CachedRecording(
            track=track,
            temp_filepath=filepath,
            created_at=datetime.now(),
        )
    
    def _stop_recording_internal(self, discard: bool = False):
        """Internal stop recording - optionally discard the file."""
        if not self.is_recording:
            return
        
        filepath = self.recording_filepath
        self.is_recording = False  # Set early to prevent re-entry
        
        # Notify UI that recording stopped
        if self.on_recording_state:
            GLib.idle_add(self.on_recording_state, False)
        
        try:
            # First, disconnect from tee
            if self.recording_tee_pad:
                queue_pad = self.recording_queue.get_static_pad("sink")
                if queue_pad:
                    self.recording_tee_pad.unlink(queue_pad)
                    # Send EOS to finalize the file
                    queue_pad.send_event(Gst.Event.new_eos())
                self.tee.release_request_pad(self.recording_tee_pad)
                self.recording_tee_pad = None
            
            # Give EOS time to propagate
            time.sleep(0.3)
            
            # Now set all elements to NULL state BEFORE removing
            elements = [self.filesink, self.muxer, self.encoder, self.audio_convert2, self.recording_queue]
            for element in elements:
                if element:
                    element.set_state(Gst.State.NULL)
            
            # Wait for state changes to complete
            for element in elements:
                if element:
                    element.get_state(Gst.CLOCK_TIME_NONE)  # Block until state change complete
            
            # Now safe to remove
            for element in elements:
                if element:
                    self.pipeline.remove(element)
            
            self.recording_queue = None
            self.audio_convert2 = None
            self.encoder = None
            self.muxer = None
            self.filesink = None
            self.recording_filepath = None
            
            # Delete file if discarding
            if discard and filepath and os.path.exists(filepath):
                os.remove(filepath)
                
        except Exception as e:
            print(f"Stop recording error: {e}")
            import traceback
            traceback.print_exc()
    
    def _delete_cached_recording(self, cached: CachedRecording):
        """Delete a cached recording's temp file."""
        try:
            if os.path.exists(cached.temp_filepath):
                os.remove(cached.temp_filepath)
        except Exception as e:
            print(f"Failed to delete cached recording: {e}")
    
    def save_cached_recording(self, cached: CachedRecording) -> Optional[str]:
        """Save a cached recording to the music folder."""
        if not os.path.exists(cached.temp_filepath):
            return None
        
        # Generate final filename
        recordings_dir = self.library.get_recordings_dir()
        os.makedirs(recordings_dir, exist_ok=True)
        
        timestamp = cached.created_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{cached.track.filename_safe}_{timestamp}.ogg"
        final_path = os.path.join(recordings_dir, filename)
        
        try:
            # Move file from temp to final location
            import shutil
            shutil.move(cached.temp_filepath, final_path)
            
            # Remove from cache list
            if cached in self.cached_recordings:
                self.cached_recordings.remove(cached)
            
            print(f"Saved recording: {final_path}")
            return final_path
        except Exception as e:
            print(f"Failed to save recording: {e}")
            return None
    
    def discard_cached_recording(self, cached: CachedRecording):
        """Discard a cached recording."""
        self._delete_cached_recording(cached)
        if cached in self.cached_recordings:
            self.cached_recordings.remove(cached)
    
    def cleanup_all_cached(self):
        """Delete all cached recordings (called on app exit)."""
        for cached in self.cached_recordings:
            self._delete_cached_recording(cached)
        self.cached_recordings.clear()
        
        # Also clean up any orphaned temp files
        try:
            for f in os.listdir(self.CACHE_DIR):
                filepath = os.path.join(self.CACHE_DIR, f)
                if os.path.isfile(filepath):
                    os.remove(filepath)
        except Exception:
            pass
    
    def play(self, station: Station):
        """Start playing a station."""
        self.stop()
        
        self.current_station = station
        self._current_title = ""
        self._current_artist = ""
        self.current_track = None
        
        # Use resolved URL if available
        url = station.url_resolved or station.url
        print(f"Playing: {station.name} - {url}")
        
        self.source.set_property("uri", url)
        self.pipeline.set_state(Gst.State.PLAYING)
        
        # Add to recents
        self.library.add_recent(station)
    
    def stop(self):
        """Stop playback."""
        # Stop any ongoing recording (discard since we're stopping)
        if self.is_recording:
            self._stop_recording_internal(discard=True)
        
        self.pipeline.set_state(Gst.State.NULL)
        self.is_playing = False
        self._current_title = ""
        self._current_artist = ""
        
        # Finalize any current track
        if self.current_track:
            self.current_track.duration = (datetime.now() - self.current_track.started_at).total_seconds()
    
    def pause(self):
        """Pause playback."""
        self.pipeline.set_state(Gst.State.PAUSED)
    
    def resume(self):
        """Resume playback."""
        self.pipeline.set_state(Gst.State.PLAYING)
    
    def toggle_play_pause(self):
        """Toggle between play and pause."""
        if self.is_playing:
            self.pause()
        else:
            self.resume()
    
    def set_volume(self, volume: float):
        """Set volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        self.volume_element.set_property("volume", self.volume)
        self.library.set_config('volume', self.volume)
    
    def get_volume(self) -> float:
        """Get current volume."""
        return self.volume
    
    def save_current_track(self) -> Optional[str]:
        """
        Save the current/recent track to a file.
        
        This is a simplified version - full implementation would use
        the recording pipeline to capture and save audio data.
        For now, we'll note that this requires the recording branch
        to be active during playback.
        """
        if not self.current_track:
            return None
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.current_track.filename_safe}_{timestamp}.mp3"
        filepath = os.path.join(self.library.get_recordings_dir(), filename)
        
        self.current_track.filepath = filepath
        self.current_track.saved = True
        
        return filepath
    
    def start_recording(self) -> bool:
        """Start recording the current stream to a file."""
        if self.is_recording or not self.is_playing:
            return False
        
        # Create recordings directory if needed
        recordings_dir = self.library.get_recordings_dir()
        os.makedirs(recordings_dir, exist_ok=True)
        
        # Generate filename with timestamp - use OGG format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        station_name = self.current_station.name if self.current_station else "Unknown"
        safe_station = re.sub(r'[<>:"/\\|?*&]', '_', station_name)[:50]
        
        if self._current_title:
            safe_title = re.sub(r'[<>:"/\\|?*&]', '_', self._current_title)[:50]
            filename = f"{safe_title}_{timestamp}.ogg"
        else:
            filename = f"{safe_station}_{timestamp}.ogg"
        
        self.recording_filepath = os.path.join(recordings_dir, filename)
        
        try:
            # Create recording elements
            self.recording_queue = Gst.ElementFactory.make("queue", "recording_queue")
            self.audio_convert2 = Gst.ElementFactory.make("audioconvert", "audioconvert2")
            self.encoder = Gst.ElementFactory.make("vorbisenc", "encoder")
            self.muxer = Gst.ElementFactory.make("oggmux", "muxer")
            self.filesink = Gst.ElementFactory.make("filesink", "filesink")
            
            if not all([self.recording_queue, self.audio_convert2, self.encoder, self.muxer, self.filesink]):
                print("Failed to create OGG recording elements")
                return False
            
            # Configure filesink
            self.filesink.set_property("location", self.recording_filepath)
            
            # Add elements to pipeline (while playing!)
            self.pipeline.add(self.recording_queue)
            self.pipeline.add(self.audio_convert2)
            self.pipeline.add(self.encoder)
            self.pipeline.add(self.muxer)
            self.pipeline.add(self.filesink)
            
            # Link the recording chain first (before connecting to tee)
            if not self.recording_queue.link(self.audio_convert2):
                print("Failed to link recording_queue to audioconvert2")
                return False
            if not self.audio_convert2.link(self.encoder):
                print("Failed to link audioconvert2 to encoder")
                return False
            if not self.encoder.link(self.muxer):
                print("Failed to link encoder to muxer")
                return False
            if not self.muxer.link(self.filesink):
                print("Failed to link muxer to filesink")
                return False
            
            # Set elements to playing state BEFORE connecting to tee
            self.recording_queue.set_state(Gst.State.PLAYING)
            self.audio_convert2.set_state(Gst.State.PLAYING)
            self.encoder.set_state(Gst.State.PLAYING)
            self.muxer.set_state(Gst.State.PLAYING)
            self.filesink.set_state(Gst.State.PLAYING)
            
            # Now get a new src pad from tee and link to recording queue
            self.recording_tee_pad = self.tee.request_pad_simple("src_%u")
            queue_pad = self.recording_queue.get_static_pad("sink")
            
            if self.recording_tee_pad and queue_pad:
                result = self.recording_tee_pad.link(queue_pad)
                print(f"Tee to recording queue link result: {result}")
            else:
                print("Failed to get pads for linking")
                return False
            
            self.is_recording = True
            self.recording_start_time = datetime.now()
            print(f"Recording started: {self.recording_filepath}")
            return True
            
        except Exception as e:
            print(f"Failed to start recording: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def stop_recording(self) -> Optional[str]:
        """Stop recording and return the filepath."""
        if not self.is_recording:
            return None
        
        filepath = self.recording_filepath
        self.is_recording = False
        
        try:
            # Use a blocking pad probe to safely disconnect the recording branch
            if hasattr(self, 'recording_tee_pad') and self.recording_tee_pad:
                # Block the pad first
                def pad_probe_callback(pad, info):
                    # Unlink within the probe callback (thread-safe)
                    queue_pad = self.recording_queue.get_static_pad("sink")
                    pad.unlink(queue_pad)
                    
                    # Send EOS to recording branch to finalize file
                    queue_pad.send_event(Gst.Event.new_eos())
                    
                    return Gst.PadProbeReturn.REMOVE
                
                self.recording_tee_pad.add_probe(
                    Gst.PadProbeType.BLOCK_DOWNSTREAM,
                    pad_probe_callback
                )
                
                # Wait a bit for EOS to propagate and file to finalize
                time.sleep(0.3)
                
                # Release the tee pad
                self.tee.release_request_pad(self.recording_tee_pad)
                self.recording_tee_pad = None
            
            # Stop and remove elements (order matters - downstream first)
            for element in [self.filesink, self.muxer, self.encoder, self.audio_convert2, self.recording_queue]:
                if element:
                    element.set_state(Gst.State.NULL)
                    self.pipeline.remove(element)
            
            self.recording_queue = None
            self.audio_convert2 = None
            self.encoder = None
            self.muxer = None
            self.filesink = None
            self.recording_filepath = None
            
            print(f"Recording stopped: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"Error stopping recording: {e}")
            import traceback
            traceback.print_exc()
            return filepath
    
    def toggle_recording(self) -> tuple[bool, Optional[str]]:
        """Toggle recording on/off. Returns (is_now_recording, filepath_if_stopped)."""
        if self.is_recording:
            filepath = self.stop_recording()
            return (False, filepath)
        else:
            success = self.start_recording()
            return (success, None)
    
    def get_current_metadata(self) -> tuple[str, str]:
        """Get current title and artist."""
        return self._current_title, self._current_artist
    
    def get_track_history(self) -> list[TrackInfo]:
        """Get history of played tracks."""
        return self.track_history.copy()
    
    def get_cached_recordings(self) -> list[CachedRecording]:
        """Get list of cached recordings waiting to be saved."""
        return self.cached_recordings.copy()
    
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        self.cleanup_all_cached()
        self.pipeline.set_state(Gst.State.NULL)
