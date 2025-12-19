#!/usr/bin/env python3
"""
Audio Analyzer for Tux Tunes
Detects song boundaries using multiple techniques:
1. Silence detection (gaps between songs)
2. Spectral analysis (frequency pattern changes)
3. Energy envelope changes

This module is used to find the actual boundary between songs
in the pre-buffer, allowing us to trim recordings accurately.
"""

import os
import tempfile
from typing import Optional, Tuple, List
from dataclasses import dataclass

# We'll try to import audio analysis libraries
# and gracefully degrade if not available
LIBROSA_AVAILABLE = False
PYDUB_AVAILABLE = False
NUMPY_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    pass

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    pass

try:
    from pydub import AudioSegment
    from pydub.silence import detect_silence
    PYDUB_AVAILABLE = True
except ImportError:
    pass


@dataclass
class BoundaryResult:
    """Result of song boundary detection."""
    found: bool
    position_seconds: float  # Position of boundary in the audio
    confidence: float  # 0.0 to 1.0
    method: str  # Which detection method found it
    details: str  # Human-readable explanation


class AudioAnalyzer:
    """
    Analyzes audio to find song boundaries.
    
    Uses a hybrid approach:
    1. First try silence detection (fastest, works for non-crossfaded songs)
    2. If no silence found, use spectral analysis (works for crossfaded songs)
    3. Combine multiple signals for higher confidence
    """
    
    # Minimum requirements
    MIN_SILENCE_DURATION_MS = 200  # At least 200ms of silence
    SILENCE_THRESHOLD_DB = -40  # Anything below -40dB is silence
    
    # Spectral analysis settings
    HOP_LENGTH = 512
    FRAME_LENGTH = 2048
    
    def __init__(self):
        """Initialize the analyzer and check available features."""
        self.features_available = {
            'numpy': NUMPY_AVAILABLE,
            'librosa': LIBROSA_AVAILABLE,
            'pydub': PYDUB_AVAILABLE,
        }
        
        # Determine what analysis we can do
        self.can_analyze = NUMPY_AVAILABLE and (LIBROSA_AVAILABLE or PYDUB_AVAILABLE)
        
        if not self.can_analyze:
            print("Warning: Audio analysis requires numpy and either librosa or pydub")
            print(f"  numpy: {NUMPY_AVAILABLE}")
            print(f"  librosa: {LIBROSA_AVAILABLE}")
            print(f"  pydub: {PYDUB_AVAILABLE}")
    
    def get_missing_dependencies(self) -> List[str]:
        """Return list of missing dependencies needed for full functionality."""
        missing = []
        if not NUMPY_AVAILABLE:
            missing.append("numpy")
        if not LIBROSA_AVAILABLE:
            missing.append("librosa")
        if not PYDUB_AVAILABLE:
            missing.append("pydub")
        return missing
    
    def get_install_command(self) -> str:
        """Return pip install command for missing dependencies."""
        missing = self.get_missing_dependencies()
        if not missing:
            return ""
        return f"pip install {' '.join(missing)}"
    
    def find_song_boundary(
        self,
        audio_path: str,
        search_start_seconds: float = 0,
        search_end_seconds: Optional[float] = None,
    ) -> BoundaryResult:
        """
        Find a song boundary in the audio file.
        
        Args:
            audio_path: Path to the audio file (OGG, MP3, WAV, etc.)
            search_start_seconds: Start searching from this position
            search_end_seconds: Stop searching at this position (None = end of file)
        
        Returns:
            BoundaryResult with the detected boundary position and confidence
        """
        if not self.can_analyze:
            return BoundaryResult(
                found=False,
                position_seconds=0,
                confidence=0,
                method="none",
                details="Audio analysis libraries not available"
            )
        
        if not os.path.exists(audio_path):
            return BoundaryResult(
                found=False,
                position_seconds=0,
                confidence=0,
                method="none",
                details=f"File not found: {audio_path}"
            )
        
        # Try silence detection first (fastest)
        silence_result = self._detect_silence_boundary(
            audio_path, search_start_seconds, search_end_seconds
        )
        
        if silence_result.found and silence_result.confidence > 0.7:
            return silence_result
        
        # Try spectral analysis (more accurate for crossfades)
        if LIBROSA_AVAILABLE:
            spectral_result = self._detect_spectral_boundary(
                audio_path, search_start_seconds, search_end_seconds
            )
            
            # If spectral found something with good confidence, use it
            if spectral_result.found and spectral_result.confidence > 0.6:
                return spectral_result
            
            # If both found something, combine them
            if silence_result.found and spectral_result.found:
                # Average the positions, boost confidence if they agree
                pos_diff = abs(silence_result.position_seconds - spectral_result.position_seconds)
                if pos_diff < 1.0:  # Within 1 second of each other
                    return BoundaryResult(
                        found=True,
                        position_seconds=(silence_result.position_seconds + spectral_result.position_seconds) / 2,
                        confidence=min(1.0, (silence_result.confidence + spectral_result.confidence) / 2 + 0.2),
                        method="combined",
                        details=f"Silence and spectral analysis agree (diff: {pos_diff:.2f}s)"
                    )
        
        # Return best result we have
        if silence_result.found:
            return silence_result
        
        if LIBROSA_AVAILABLE and spectral_result.found:
            return spectral_result
        
        return BoundaryResult(
            found=False,
            position_seconds=0,
            confidence=0,
            method="none",
            details="No song boundary detected"
        )
    
    def _detect_silence_boundary(
        self,
        audio_path: str,
        search_start: float,
        search_end: Optional[float],
    ) -> BoundaryResult:
        """Detect song boundary using silence detection."""
        
        if not PYDUB_AVAILABLE:
            return BoundaryResult(
                found=False, position_seconds=0, confidence=0,
                method="silence", details="pydub not available"
            )
        
        try:
            # Load audio
            audio = AudioSegment.from_file(audio_path)
            
            # Convert search range to milliseconds
            start_ms = int(search_start * 1000)
            end_ms = int(search_end * 1000) if search_end else len(audio)
            
            # Extract the search region
            search_region = audio[start_ms:end_ms]
            
            # Detect silence periods
            silences = detect_silence(
                search_region,
                min_silence_len=self.MIN_SILENCE_DURATION_MS,
                silence_thresh=self.SILENCE_THRESHOLD_DB,
            )
            
            if not silences:
                return BoundaryResult(
                    found=False, position_seconds=0, confidence=0,
                    method="silence", details="No silence detected"
                )
            
            # Find the most significant silence (longest one)
            best_silence = max(silences, key=lambda s: s[1] - s[0])
            silence_start_ms, silence_end_ms = best_silence
            silence_duration = silence_end_ms - silence_start_ms
            
            # The boundary is in the middle of the silence
            boundary_ms = (silence_start_ms + silence_end_ms) / 2
            boundary_seconds = search_start + (boundary_ms / 1000)
            
            # Calculate confidence based on silence duration
            # 200ms = 0.5 confidence, 500ms+ = 0.9 confidence
            confidence = min(0.9, 0.5 + (silence_duration / 1000) * 0.8)
            
            return BoundaryResult(
                found=True,
                position_seconds=boundary_seconds,
                confidence=confidence,
                method="silence",
                details=f"Found {silence_duration}ms silence at {boundary_seconds:.2f}s"
            )
            
        except Exception as e:
            return BoundaryResult(
                found=False, position_seconds=0, confidence=0,
                method="silence", details=f"Error: {e}"
            )
    
    def _detect_spectral_boundary(
        self,
        audio_path: str,
        search_start: float,
        search_end: Optional[float],
    ) -> BoundaryResult:
        """Detect song boundary using spectral analysis (onset detection)."""
        
        if not LIBROSA_AVAILABLE:
            return BoundaryResult(
                found=False, position_seconds=0, confidence=0,
                method="spectral", details="librosa not available"
            )
        
        try:
            # Load audio
            y, sr = librosa.load(audio_path, sr=22050)
            
            # Convert search range to samples
            start_sample = int(search_start * sr)
            end_sample = int(search_end * sr) if search_end else len(y)
            
            # Extract search region
            y_region = y[start_sample:end_sample]
            
            if len(y_region) < sr:  # Less than 1 second
                return BoundaryResult(
                    found=False, position_seconds=0, confidence=0,
                    method="spectral", details="Audio region too short"
                )
            
            # Compute onset strength envelope
            onset_env = librosa.onset.onset_strength(
                y=y_region,
                sr=sr,
                hop_length=self.HOP_LENGTH,
            )
            
            # Detect onsets with backtracking for better segmentation
            onset_frames = librosa.onset.onset_detect(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=self.HOP_LENGTH,
                backtrack=True,
                units='frames'
            )
            
            if len(onset_frames) == 0:
                return BoundaryResult(
                    found=False, position_seconds=0, confidence=0,
                    method="spectral", details="No onsets detected"
                )
            
            # Convert frames to time
            onset_times = librosa.frames_to_time(
                onset_frames,
                sr=sr,
                hop_length=self.HOP_LENGTH
            )
            
            # Look for the strongest onset (likely song boundary)
            # We want the onset with the biggest change in spectral content
            
            # Compute spectral flux (measure of spectral change)
            S = np.abs(librosa.stft(y_region, hop_length=self.HOP_LENGTH))
            spectral_flux = np.sqrt(np.sum(np.diff(S, axis=1)**2, axis=0))
            
            # Find onset with highest spectral flux
            best_onset_idx = 0
            best_flux = 0
            
            for i, frame in enumerate(onset_frames):
                if frame < len(spectral_flux):
                    # Look at flux around this onset
                    start = max(0, frame - 5)
                    end = min(len(spectral_flux), frame + 5)
                    local_flux = np.max(spectral_flux[start:end])
                    
                    if local_flux > best_flux:
                        best_flux = local_flux
                        best_onset_idx = i
            
            boundary_seconds = search_start + onset_times[best_onset_idx]
            
            # Calculate confidence based on flux strength
            avg_flux = np.mean(spectral_flux)
            if avg_flux > 0:
                confidence = min(0.9, 0.4 + (best_flux / avg_flux) * 0.1)
            else:
                confidence = 0.5
            
            return BoundaryResult(
                found=True,
                position_seconds=boundary_seconds,
                confidence=confidence,
                method="spectral",
                details=f"Spectral change detected at {boundary_seconds:.2f}s (flux: {best_flux:.2f})"
            )
            
        except Exception as e:
            return BoundaryResult(
                found=False, position_seconds=0, confidence=0,
                method="spectral", details=f"Error: {e}"
            )
    
    def split_at_boundary(
        self,
        audio_path: str,
        boundary_seconds: float,
        output_before: Optional[str] = None,
        output_after: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Split an audio file at the detected boundary.
        
        Args:
            audio_path: Input audio file
            boundary_seconds: Position to split at
            output_before: Output path for audio before boundary (None = temp file)
            output_after: Output path for audio after boundary (None = temp file)
        
        Returns:
            Tuple of (path_before, path_after) - paths to the split files
        """
        if not PYDUB_AVAILABLE:
            return (None, None)
        
        try:
            audio = AudioSegment.from_file(audio_path)
            boundary_ms = int(boundary_seconds * 1000)
            
            before = audio[:boundary_ms]
            after = audio[boundary_ms:]
            
            # Generate output paths if not provided
            if output_before is None:
                output_before = tempfile.mktemp(suffix='.ogg')
            if output_after is None:
                output_after = tempfile.mktemp(suffix='.ogg')
            
            # Export
            before.export(output_before, format='ogg')
            after.export(output_after, format='ogg')
            
            return (output_before, output_after)
            
        except Exception as e:
            print(f"Split error: {e}")
            return (None, None)


def check_requirements() -> dict:
    """Check if audio analysis requirements are met."""
    return {
        'numpy': NUMPY_AVAILABLE,
        'librosa': LIBROSA_AVAILABLE,
        'pydub': PYDUB_AVAILABLE,
        'can_analyze': NUMPY_AVAILABLE and (LIBROSA_AVAILABLE or PYDUB_AVAILABLE),
        'full_features': NUMPY_AVAILABLE and LIBROSA_AVAILABLE and PYDUB_AVAILABLE,
    }


def get_install_instructions() -> str:
    """Get installation instructions for missing dependencies."""
    reqs = check_requirements()
    
    if reqs['full_features']:
        return "All audio analysis dependencies are installed!"
    
    missing = []
    if not reqs['numpy']:
        missing.append('numpy')
    if not reqs['librosa']:
        missing.append('librosa')
    if not reqs['pydub']:
        missing.append('pydub')
    
    # Distribution-specific instructions
    instructions = []
    instructions.append("To enable audio analysis features, install:")
    instructions.append("")
    
    # pip
    instructions.append("Using pip:")
    instructions.append(f"  pip install {' '.join(missing)}")
    instructions.append("")
    
    # Arch
    instructions.append("On Arch Linux:")
    arch_pkgs = []
    if 'numpy' in missing:
        arch_pkgs.append('python-numpy')
    if 'librosa' in missing:
        arch_pkgs.append('python-librosa')  # AUR
    if 'pydub' in missing:
        arch_pkgs.append('python-pydub')  # AUR
    instructions.append(f"  pacman -S {' '.join([p for p in arch_pkgs if not 'AUR' in p])}")
    if any('librosa' in p or 'pydub' in p for p in arch_pkgs):
        instructions.append(f"  yay -S {' '.join([p for p in arch_pkgs if 'librosa' in p or 'pydub' in p])}")
    instructions.append("")
    
    # Debian/Ubuntu
    instructions.append("On Debian/Ubuntu:")
    deb_pkgs = []
    if 'numpy' in missing:
        deb_pkgs.append('python3-numpy')
    instructions.append(f"  apt install {' '.join(deb_pkgs)}")
    instructions.append(f"  pip install {' '.join([p for p in missing if p not in ['numpy']])}")
    
    return '\n'.join(instructions)


# Test function
if __name__ == '__main__':
    print("Audio Analyzer Module")
    print("=" * 40)
    
    reqs = check_requirements()
    print(f"NumPy:   {'✓' if reqs['numpy'] else '✗'}")
    print(f"Librosa: {'✓' if reqs['librosa'] else '✗'}")
    print(f"PyDub:   {'✓' if reqs['pydub'] else '✗'}")
    print()
    
    if not reqs['full_features']:
        print(get_install_instructions())
    else:
        print("All features available!")
        print()
        
        # Test with a file if provided
        import sys
        if len(sys.argv) > 1:
            test_file = sys.argv[1]
            print(f"Analyzing: {test_file}")
            
            analyzer = AudioAnalyzer()
            result = analyzer.find_song_boundary(test_file)
            
            print(f"Found: {result.found}")
            print(f"Position: {result.position_seconds:.2f}s")
            print(f"Confidence: {result.confidence:.2f}")
            print(f"Method: {result.method}")
            print(f"Details: {result.details}")
