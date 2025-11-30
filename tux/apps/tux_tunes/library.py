"""
Tux Tunes - Library Manager

Manages favorite stations and app configuration.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import json
from typing import Optional
from gi.repository import GLib

from .api import Station


class Library:
    """Manages favorite stations and configuration."""
    
    def __init__(self):
        self.config_dir = os.path.join(GLib.get_user_config_dir(), 'tux-tunes')
        self.data_dir = os.path.join(GLib.get_user_data_dir(), 'tux-tunes')
        
        # Get music directory - use XDG or fallback to ~/Music
        music_dir = os.environ.get('XDG_MUSIC_DIR', os.path.expanduser('~/Music'))
        self.recordings_dir = os.path.join(music_dir, 'Tux Tunes')
        
        # Ensure directories exist
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.recordings_dir, exist_ok=True)
        
        self.favorites_file = os.path.join(self.data_dir, 'favorites.json')
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.recents_file = os.path.join(self.data_dir, 'recents.json')
        
        # Load data
        self.favorites: list[Station] = []
        self.recents: list[Station] = []
        self.config: dict = {}
        
        self._load_favorites()
        self._load_recents()
        self._load_config()
    
    def _load_favorites(self):
        """Load favorites from file."""
        try:
            if os.path.exists(self.favorites_file):
                with open(self.favorites_file, 'r') as f:
                    data = json.load(f)
                    self.favorites = [Station.from_dict(s) for s in data]
        except Exception as e:
            print(f"Failed to load favorites: {e}")
            self.favorites = []
    
    def _save_favorites(self):
        """Save favorites to file."""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump([s.to_dict() for s in self.favorites], f, indent=2)
        except Exception as e:
            print(f"Failed to save favorites: {e}")
    
    def _load_recents(self):
        """Load recent stations from file."""
        try:
            if os.path.exists(self.recents_file):
                with open(self.recents_file, 'r') as f:
                    data = json.load(f)
                    self.recents = [Station.from_dict(s) for s in data]
        except Exception as e:
            print(f"Failed to load recents: {e}")
            self.recents = []
    
    def _save_recents(self):
        """Save recents to file."""
        try:
            with open(self.recents_file, 'w') as f:
                json.dump([s.to_dict() for s in self.recents], f, indent=2)
        except Exception as e:
            print(f"Failed to save recents: {e}")
    
    def _load_config(self):
        """Load configuration from file."""
        default_config = {
            'volume': 1.0,
            'recording_mode': 'ask',  # 'auto', 'ask', 'none'
            'auto_save_prompted': False,  # Whether we've asked about auto-save
            'pre_buffer_seconds': 8,
            'post_buffer_seconds': 3,
            'min_recording_seconds': 30,
            'max_recording_seconds': 600,  # 10 minutes
            'recordings_dir': self.recordings_dir,
            'window_width': 900,
            'window_height': 700,
            'window_maximized': False,
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    default_config.update(loaded)
        except Exception as e:
            print(f"Failed to load config: {e}")
        
        self.config = default_config
    
    def save_config(self):
        """Save configuration to file."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Failed to save config: {e}")
    
    def get_config(self, key: str, default=None):
        """Get a config value."""
        return self.config.get(key, default)
    
    def set_config(self, key: str, value):
        """Set a config value and save."""
        self.config[key] = value
        self.save_config()
    
    # Favorites management
    
    def add_favorite(self, station: Station):
        """Add a station to favorites."""
        if not self.is_favorite(station.uuid):
            self.favorites.insert(0, station)
            self._save_favorites()
    
    def remove_favorite(self, station_uuid: str):
        """Remove a station from favorites."""
        self.favorites = [s for s in self.favorites if s.uuid != station_uuid]
        self._save_favorites()
    
    def update_favorite(self, old_uuid: str, updated_station: Station):
        """Update a favorite station (for editing custom stations)."""
        for i, station in enumerate(self.favorites):
            if station.uuid == old_uuid:
                self.favorites[i] = updated_station
                self._save_favorites()
                return
    
    def is_favorite(self, station_uuid: str) -> bool:
        """Check if a station is in favorites."""
        return any(s.uuid == station_uuid for s in self.favorites)
    
    def get_favorites(self) -> list[Station]:
        """Get all favorite stations."""
        return self.favorites.copy()
    
    # Recents management
    
    def add_recent(self, station: Station):
        """Add a station to recents (at the front)."""
        # Remove if already exists
        self.recents = [s for s in self.recents if s.uuid != station.uuid]
        # Add to front
        self.recents.insert(0, station)
        # Keep only last 20
        self.recents = self.recents[:20]
        self._save_recents()
    
    def get_recents(self) -> list[Station]:
        """Get recent stations."""
        return self.recents.copy()
    
    def clear_recents(self):
        """Clear recent stations."""
        self.recents = []
        self._save_recents()
    
    # Recordings management
    
    def get_recordings_dir(self) -> str:
        """Get the recordings directory."""
        path = self.config.get('recordings_dir', self.recordings_dir)
        os.makedirs(path, exist_ok=True)
        return path
    
    def set_recordings_dir(self, path: str):
        """Set the recordings directory."""
        os.makedirs(path, exist_ok=True)
        self.set_config('recordings_dir', path)
    
    def get_recordings(self) -> list[dict]:
        """Get list of recorded files."""
        recordings = []
        rec_dir = self.get_recordings_dir()
        
        try:
            for filename in os.listdir(rec_dir):
                if filename.endswith(('.mp3', '.ogg', '.flac', '.m4a')):
                    filepath = os.path.join(rec_dir, filename)
                    stat = os.stat(filepath)
                    recordings.append({
                        'filename': filename,
                        'filepath': filepath,
                        'size': stat.st_size,
                        'mtime': stat.st_mtime,
                    })
        except Exception as e:
            print(f"Failed to list recordings: {e}")
        
        # Sort by modification time, newest first
        recordings.sort(key=lambda x: x['mtime'], reverse=True)
        return recordings
