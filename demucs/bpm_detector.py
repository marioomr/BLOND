#!/usr/bin/env python3
"""
High-Precision BPM Detection for BLOND Stem Splitter
Supports MP3 files with professional-grade accuracy
Uses madmom for onset-based and RNN-based beat tracking
Comparable to Rekordbox, Serato, and Traktor
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
import numpy as np

# Try importing madmom with fallback to librosa
try:
    import madmom
    HAS_MADMOM = True
except ImportError:
    HAS_MADMOM = False

# Always have librosa as backup
try:
    import librosa
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


class BPMDetector:
    """
    High-precision BPM detector for MP3 files.
    Primary method: madmom (RNNBeatProcessor + BeatTrackingProcessor)
    Fallback: librosa with tempogram
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
        self.log("BPM Detector initialized")
        
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
    
    def detect_bpm_madmom(self, audio_path: str) -> Dict:
        """
        Detect BPM using madmom's RNN-based beat tracking.
        Most accurate method for electronic music (house, techno, hip-hop).
        
        Args:
            audio_path: Path to MP3 file
            
        Returns:
            Dictionary with BPM, confidence, and metadata
        """
        try:
            self.log("METHOD: Using madmom RNN Beat Tracking")
            
            # Load audio with madmom
            # This preprocesses the audio for the RNN
            from madmom.audio.chroma import CLPExtractor
            from madmom.features.beats import RNNBeatProcessor, BeatTrackingProcessor
            
            self.log("LOADING: Processing audio for RNN...")
            
            # RNNBeatProcessor finds beat activations
            processor = RNNBeatProcessor()
            activations = processor(audio_path)
            
            self.log("PROCESSING: Running beat tracking...")
            
            # BeatTrackingProcessor converts activations to stable beats
            beat_processor = BeatTrackingProcessor(fps=100)
            beats = beat_processor(activations)
            
            if len(beats) < 4:
                return {
                    "success": False,
                    "error": "Not enough beats detected",
                    "bpm": None
                }
            
            # Calculate BPM from inter-beat intervals
            inter_beat_intervals = np.diff(beats)
            
            # Filter out unrealistic intervals (< 0.3s or > 3s)
            valid_intervals = inter_beat_intervals[
                (inter_beat_intervals > 0.3) & (inter_beat_intervals < 3.0)
            ]
            
            if len(valid_intervals) < 3:
                return {
                    "success": False,
                    "error": "Unable to calculate stable BPM",
                    "bpm": None
                }
            
            # Calculate BPM from median interval
            median_interval = np.median(valid_intervals)
            bpm = 60.0 / median_interval
            bpm = round(bpm)
            
            # Validate BPM range (realistic for most music: 60-180 BPM)
            if bpm < 60 or bpm > 180:
                self.log(f"WARNING: Detected BPM {bpm} is outside typical range")
            
            # Calculate confidence from beat stability
            # Lower standard deviation = higher confidence
            std_dev = np.std(valid_intervals)
            mean_interval = np.mean(valid_intervals)
            
            # Confidence metric (0-100)
            # Perfect regularity = 100%, very variable = low confidence
            variation_coeff = (std_dev / mean_interval) if mean_interval > 0 else 1.0
            confidence = max(0, min(100, int(100 * (1.0 - min(variation_coeff, 1.0)))))
            confidence = max(70, confidence)  # Minimum 70% for madmom
            
            self.log(f"DETECTED: {bpm} BPM with confidence {confidence}%")
            
            return {
                "success": True,
                "bpm": bpm,
                "confidence": confidence,
                "method": "madmom_rnn",
                "beats_detected": len(beats),
                "intervals_analyzed": len(valid_intervals)
            }
            
        except Exception as e:
            self.log(f"ERROR in madmom: {str(e)}")
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
            
            # Load audio
            self.log("LOADING: Loading audio file...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
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
        Automatically selects best available method and applies double-time/half-time correction.
        
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
        
        # Try madmom first (most accurate)
        result = None
        if HAS_MADMOM:
            result = self.detect_bpm_madmom(audio_path)
        
        # Fallback to librosa if madmom failed or unavailable
        if result is None or not result.get("success"):
            if HAS_LIBROSA:
                self.log("FALLBACK: Switching to librosa")
                result = self.detect_bpm_librosa(audio_path)
            else:
                return {
                    "success": False,
                    "error": "Neither madmom nor librosa available",
                    "bpm": None
                }
        
        if not result or not result.get("success"):
            self.log("ERROR: All detection methods failed")
            return result or {
                "success": False,
                "error": "All detection methods failed",
                "bpm": None
            }
        
        # Apply double-time/half-time correction if BPM seems unrealistic
        result = self._correct_bpm_errors(result)
        
        self.log("DONE")
        return result
    
    def _correct_bpm_errors(self, result: Dict) -> Dict:
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
    
    # Exit with success code only if detection succeeded
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
