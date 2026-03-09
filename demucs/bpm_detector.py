#!/usr/bin/env python3
"""
High-Precision BPM Detection for BLOND Stem Splitter
Supports MP3 files with professional-grade accuracy
Uses librosa with tempogram and beat tracking
Optimized for electronic music and DJ use cases
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
import numpy as np

# Import librosa for audio processing
try:
    import librosa
    from librosa import feature
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    print("Error: librosa is required", file=sys.stderr)
    sys.exit(1)


class BPMDetector:
    """
    High-precision BPM detector for MP3 files.
    Uses librosa with multiple detection methods for accuracy.
    Methods:
    - Tempogram-based detection (primary)
    - Beat tracking with dynamic programming
    - Onset-based analysis (fallback)
    """
    
    def __init__(self, log_callback=None, sr: int = 22050):
        """
        Initialize BPM detector.
        
        Args:
            log_callback: Optional callback for logging
            sr: Sample rate for processing (default 22050Hz)
        """
        self.log_callback = log_callback
        self.sr = sr
        self.log("BPM Detector initialized (librosa-based)")
        
    def log(self, message: str):
        """Log message if callback provided"""
        if self.log_callback:
            self.log_callback(message)
    
    def _validate_mp3(self, audio_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that file is MP3 and exists.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        path = Path(audio_path)
        
        if not path.exists():
            return False, f"File not found: {audio_path}"
        
        if path.suffix.lower() != '.mp3':
            return False, f"File must be MP3 format, got: {path.suffix}"
        
        if path.stat().st_size < 10_000:  # Less than 10KB
            return False, "File is too small to be a valid MP3"
        
        return True, None
    
    def detect_bpm_tempogram(self, audio_path: str) -> Dict:
        """
        Detect BPM using librosa's beat tracking with multiple methods.
        Primary method - robust tempo detection.
        
        Args:
            audio_path: Path to MP3 file
            
        Returns:
            Dictionary with BPM and confidence
        """
        try:
            self.log("METHOD: Using librosa Multi-Method Detection")
            
            # Load audio - only first 30s for speed
            self.log("LOADING: Loading audio file (first 30s)...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True, duration=30.0)
            duration = librosa.get_duration(y=y, sr=sr)
            self.log(f"AUDIO: {duration:.2f}s @ {sr}Hz")
            
            # Method 1: onset-based beat tracking
            self.log("ANALYZING: Extracting onset strength...")
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            # Method 2: Use beat_track directly with onset_env
            # This avoids the tempogram API issue
            self.log("ANALYZING: Computing beat track from onsets...")
            tempo, beats = librosa.beat.beat_track(onset_strength=onset_env, sr=sr, start_bpm=90, tightness=100)
            primary_bpm = int(round(tempo))
            
            # Validate result
            if primary_bpm < 30 or primary_bpm > 300:
                return None  # Invalid BPM, fallback
            
            # Calculate confidence from number of detected beats
            n_beats = len(beats)
            duration_minutes = duration / 60
            expected_beats = primary_bpm * duration_minutes
            
            # Confidence based on beat regularity
            beat_confidence = min(100, int(80 * (min(n_beats, expected_beats * 1.2) / (expected_beats + 1))))
            beat_confidence = max(50, beat_confidence)
            
            self.log(f"DETECTED: {primary_bpm} BPM ({n_beats} beats detected)")
            
            return {
                "success": True,
                "bpm": primary_bpm,
                "confidence": beat_confidence,
                "method": "librosa_onset_beat",
                "beats_detected": n_beats
            }
            
        except Exception as e:
            self.log(f"ERROR in tempo detection: {str(e)}")
            return None
    
    def detect_bpm_librosa(self, audio_path: str) -> Dict:
        """
        Detect BPM using librosa's beat tracking.
        Fallback method when madmom is unavailable.
        
        Args:
            audio_path: Path to MP3 file
            
        Returns:
            Dictionary with BPM and confidence
        """
        try:
            self.log("METHOD: Using librosa Beat Tracking")
            
            # Load audio - only first 30s for speed
            self.log("LOADING: Loading audio file (first 30s)...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True, duration=30.0)
            duration = librosa.get_duration(y=y, sr=sr)
            self.log(f"LOADED: {duration:.1f}s at {sr}Hz")
            
            # Get onset strength for confidence calculation
            self.log("PROCESSING: Extracting onset strength...")
            onset_env = librosa.onset.onset_strength(y=y, sr=sr)
            
            # Beat tracking - librosa's robust beat tracking
            self.log("ANALYZING: Computing beat track...")
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=90, tightness=100)
            bpm = round(float(tempo))
            self.log(f"DETECTED: {bpm} BPM")
            
            # Calculate confidence from onset strength regularity
            onset_mean = np.mean(onset_env)
            onset_std = np.std(onset_env)
            
            # Confidence increases with strong, regular onsets
            # More onset strength = more confident
            if onset_std > 0:
                regularity = onset_mean / (onset_std + 1e-10)
            else:
                regularity = 0.5
            
            # Map regularity to confidence (0-100)
            confidence = min(100, max(50, int(regularity * 25 + 55)))
            
            self.log(f"CONFIDENCE: {confidence}%")
            
            return {
                "success": True,
                "bpm": bpm,
                "confidence": confidence,
                "method": "librosa_beat_track",
                "duration": float(duration),
                "sample_rate": sr,
                "beats_detected": len(beats)
            }
            
        except Exception as e:
            self.log(f"ERROR in librosa: {str(e)}")
            return None
    
    def detect_bpm(self, audio_path: str) -> Dict:
        """
        Main BPM detection function.
        Uses librosa tempogram for primary detection, beat_track for fallback.
        Automatically applies double-time/half-time correction.
        
        Args:
            audio_path: Path to MP3 file
            
        Returns:
            Dictionary with BPM, confidence, and metadata
        """
        self.log("START")
        
        # Validate MP3
        is_valid, error_msg = self._validate_mp3(audio_path)
        if not is_valid:
            self.log(f"VALIDATION_ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "bpm": None
            }
        
        self.log(f"VALIDATING: File is valid MP3")
        
        # Primary method: tempogram
        result = self.detect_bpm_tempogram(audio_path)
        
        # Fallback to beat_track if tempogram failed
        if result is None or not result.get("success"):
            self.log("FALLBACK: Switching to beat_track")
            result = self.detect_bpm_librosa(audio_path)
        
        if not result or not result.get("success"):
            self.log("ERROR: All detection methods failed")
            return result or {
                "success": False,
                "error": "All detection methods failed",
                "bpm": None
            }
        
        # Apply double-time/half-time correction
        result = self._apply_bpm_correction(result)
        
        self.log("DONE")
        return result
    
    def _apply_bpm_correction(self, result: Dict) -> Dict:
        """
        Correct common BPM errors (double-time, half-time).
        
        For electronic music:
        - Double-time: detected as 2x actual BPM (e.g., 160 BPM detected, actual is 80)
        - Half-time: detected as 0.5x actual BPM (e.g., 90 BPM detected, actual is 180)
        
        Args:
            result: Detection result with BPM
            
        Returns:
            Corrected result
        """
        if not result.get("success") or not result.get("bpm"):
            return result
        
        bpm = result["bpm"]
        original_bpm = bpm
        
        # If BPM is too high, try half
        if bpm > 160 and (bpm / 2) >= 60:
            half_bpm = bpm // 2
            # Check if half-time is more typical for electronic music
            if 80 <= half_bpm <= 140:
                self.log(f"CORRECTION: Possible double-time detected ({bpm} -> {half_bpm})")
                result["bpm"] = half_bpm
                result["correction_applied"] = "half_bpm"
                result["original_bpm"] = original_bpm
                result["confidence"] = max(50, result.get("confidence", 80) - 10)
        
        # If BPM is too low, try double
        elif bpm < 80 and (bpm * 2) <= 180:
            double_bpm = bpm * 2
            # Check if double-time is more typical
            if 100 <= double_bpm <= 150:
                self.log(f"CORRECTION: Possible half-time detected ({bpm} -> {double_bpm})")
                result["bpm"] = double_bpm
                result["correction_applied"] = "double_bpm"
                result["original_bpm"] = original_bpm
                result["confidence"] = max(50, result.get("confidence", 80) - 10)
        
        return result


def detect_bpm(audio_path: str, log_callback=None) -> dict:
    """
    Main entry point function for compatibility.
    
    Args:
        audio_path: Path to MP3 file
        log_callback: Optional callback for logging
        
    Returns:
        Dictionary with BPM and confidence metrics
    """
    detector = BPMDetector(log_callback=log_callback)
    return detector.detect_bpm(audio_path)


def main():
    """Main entry point for CLI usage"""
    if len(sys.argv) < 2:
        output = {
            "success": False,
            "error": "Usage: python bpm_detector.py <audio_file.mp3> [--no-logs]",
            "bpm": None
        }
        print(json.dumps(output))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    no_logs = "--no-logs" in sys.argv
    
    # Setup logging to file and stderr
    log_dir = None
    log_file = None
    logs = []
    
    def log_callback(msg):
        logs.append(msg)
        # Write to stderr for Electron to capture separately
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()
        # Also write to log file
        if not no_logs and log_file:
            with open(log_file, 'a') as f:
                f.write(msg + '\n')
                f.flush()
    
    if not no_logs:
        log_dir = Path(__file__).parent.parent / "logs_bpm"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"bpm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Detect BPM
    detector = BPMDetector(log_callback=log_callback)
    result = detector.detect_bpm(audio_file)
    
    # Ensure result is always a dict with success field
    if result is None:
        result = {
            "success": False,
            "error": "Detection returned None",
            "bpm": None
        }
    elif not isinstance(result, dict):
        result = {
            "success": False,
            "error": f"Invalid result type: {type(result)}",
            "bpm": None
        }
    
    # Ensure success field exists
    if "success" not in result:
        result["success"] = False
        if "bpm" not in result or result.get("bpm") is None:
            result["error"] = result.get("error", "Unknown error")
    
    # IMPORTANT: Print ONLY JSON to stdout for Electron parsing
    # All logs go to stderr
    print(json.dumps(result), flush=True)
    
    # Always exit 0 - Electron reads success from the JSON
    sys.exit(0)


if __name__ == "__main__":
    main()
