#!/usr/bin/env python3
"""
Musical Key Detection with Harmonic Analysis
Detects musical key, converts to Camelot Wheel, and calculates DJ compatibility
Uses librosa with chroma-based key detection and harmonic templates
Optimized for electronic music and DJ use
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# Import librosa for key detection
try:
    import librosa
    import librosa.feature
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False
    print("Error: librosa is required", file=sys.stderr)
    sys.exit(1)


# Camelot Wheel mapping: Standard 12 keys with sharp/flat variants
CAMELOT_WHEEL = {
    # Major keys
    "C Major": "8B",
    "G Major": "9B",
    "D Major": "10B",
    "A Major": "11B",
    "E Major": "12B",
    "B Major": "1B",
    "F# Major": "2B",
    "C# Major": "3B",
    "G# Major": "4B",
    "D# Major": "5B",
    "A# Major": "6B",
    "F Major": "7B",
    
    # Minor keys
    "A Minor": "8A",
    "E Minor": "9A",
    "B Minor": "10A",
    "F# Minor": "11A",
    "C# Minor": "12A",
    "G# Minor": "1A",
    "D# Minor": "2A",
    "A# Minor": "3A",
    "F Minor": "4A",
    "C Minor": "5A",
    "G Minor": "6A",
    "D Minor": "7A",
}

# Harmonic compatibility based on Camelot Wheel
# Adjacent keys are compatible (±1 on the wheel)
HARMONIC_COMPATIBILITY = {
    "1A": ["1B", "2A", "12A"],
    "1B": ["1A", "2B", "12B"],
    "2A": ["2B", "3A", "1A"],
    "2B": ["2A", "3B", "1B"],
    "3A": ["3B", "4A", "2A"],
    "3B": ["3A", "4B", "2B"],
    "4A": ["4B", "5A", "3A"],
    "4B": ["4A", "5B", "3B"],
    "5A": ["5B", "6A", "4A"],
    "5B": ["5A", "6B", "4B"],
    "6A": ["6B", "7A", "5A"],
    "6B": ["6A", "7B", "5B"],
    "7A": ["7B", "8A", "6A"],
    "7B": ["7A", "8B", "6B"],
    "8A": ["8B", "9A", "7A"],
    "8B": ["8A", "9B", "7B"],
    "9A": ["9B", "10A", "8A"],
    "9B": ["9A", "10B", "8B"],
    "10A": ["10B", "11A", "9A"],
    "10B": ["10A", "11B", "9B"],
    "11A": ["11B", "12A", "10A"],
    "11B": ["11A", "12B", "10B"],
    "12A": ["12B", "1A", "11A"],
    "12B": ["12A", "1B", "11B"],
}


class KeyDetector:
    """
    Professional musical key detector with harmonic analysis.
    Detects key, converts to Camelot Wheel, and provides DJ compatibility.
    """
    
    def __init__(self, log_callback=None, sr: int = 22050):
        """
        Initialize key detector.
        
        Args:
            log_callback: Optional callback for logging
            sr: Sample rate (default 22050Hz)
        """
        self.log_callback = log_callback
        self.sr = sr
        self.log("Key Detector initialized")
    
    def log(self, message: str):
        """Log message if callback provided"""
        if self.log_callback:
            self.log_callback(message)
    
    def _validate_audio(self, audio_path: str) -> Tuple[bool, Optional[str]]:
        """Validate audio file exists and is valid format"""
        path = Path(audio_path)
        
        if not path.exists():
            return False, f"File not found: {audio_path}"
        
        if path.suffix.lower() not in ['.mp3', '.wav', '.m4a', '.flac']:
            return False, f"Unsupported format: {path.suffix}"
        
        if path.stat().st_size < 10_000:
            return False, "File is too small to be valid audio"
        
        return True, None
    
    def detect_key_librosa_chroma(self, audio_path: str) -> Dict:
        """
        Detect key using librosa's chroma features.
        Primary method - analyzes harmonic content.
        
        Returns:
            Dictionary with key, scale, confidence, camelot, and compatibility
        """
        try:
            self.log("METHOD: Using librosa Chroma-based Key Detection")
            
            # Load audio - only first 30s for speed
            self.log("LOADING: Loading audio file (first 30s)...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True, duration=30.0)
            duration = librosa.get_duration(y=y, sr=sr)
            self.log(f"LOADED: {duration:.1f}s @ {sr}Hz")
            
            # Compute chroma features
            self.log("ANALYZING: Computing chroma features...")
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            
            # Mean chroma across time
            chroma_mean = np.mean(chroma, axis=1)
            
            # Pitch class names
            notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            note_strengths = {notes[i]: chroma_mean[i] for i in range(12)}
            
            # Detect key using harmonic templates
            key_name, confidence = self._detect_key_from_chroma(chroma_mean)
            
            self.log(f"DETECTED: Key={key_name}, Confidence={confidence:.2%}")
            
            # Get Camelot
            camelot = CAMELOT_WHEEL.get(key_name)
            if not camelot:
                self.log(f"WARNING: Unknown key {key_name}, using closest match")
                camelot = self._find_closest_key(key_name)
            
            # Get harmonic compatibility
            compatible = HARMONIC_COMPATIBILITY.get(camelot, [])
            
            # Convert numpy types to Python native types for JSON serialization
            note_strengths_native = {k: float(v) for k, v in note_strengths.items()}
            
            return {
                "success": True,
                "key": key_name,
                "confidence": float(confidence),
                "camelot": camelot,
                "harmonic_compatible": compatible,
                "method": "librosa_chroma"
            }
        
        except Exception as e:
            self.log(f"ERROR in librosa chroma: {str(e)}")
            return None
    
    def detect_key_librosa(self, audio_path: str) -> Dict:
        """
        Fallback key detection using librosa's onset-based analysis.
        Alternative when chroma features don't work well.
        
        Returns:
            Dictionary with key, scale, confidence, camelot, and compatibility
        """
        try:
            self.log("METHOD: Using librosa Chroma Analysis")
            
            # Load audio - only first 30s for speed
            self.log("LOADING: Loading audio file (first 30s)...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True, duration=30.0)
            duration = librosa.get_duration(y=y, sr=sr)
            self.log(f"LOADED: {duration:.1f}s at {sr}Hz")
            
            # Extract chroma features (pitch class distribution)
            self.log("ANALYZING: Extracting chroma features...")
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            
            # Calculate mean chroma vector
            chroma_mean = np.mean(chroma, axis=1)
            
            # Normalize
            chroma_norm = chroma_mean / (np.sum(np.abs(chroma_mean)) + 1e-10)
            
            # Note names
            note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            
            # Find dominant note (highest chroma energy)
            tonic_idx = np.argmax(chroma_norm)
            tonic = note_names[tonic_idx]
            
            # Simple major/minor detection using harmonic templates
            # This is simplified; real implementation would use more sophisticated methods
            major_confidence, minor_confidence = self._detect_scale_librosa(chroma_norm, tonic_idx)
            
            if major_confidence > minor_confidence:
                scale = "Major"
                confidence = major_confidence
            else:
                scale = "Minor"
                confidence = minor_confidence
            
            key_name = f"{tonic} {scale}"
            self.log(f"DETECTED: Key={key_name}, Confidence={confidence:.2f}")
            
            # Get Camelot
            camelot = CAMELOT_WHEEL.get(key_name)
            if not camelot:
                self.log(f"WARNING: Key {key_name} not in standard wheel, approximating")
                camelot = self._find_closest_key(key_name)
            
            # Get harmonic compatibility
            compatible = HARMONIC_COMPATIBILITY.get(camelot, [])
            
            return {
                "success": True,
                "key": key_name,
                "scale": scale.lower(),
                "confidence": float(confidence),
                "camelot": camelot,
                "harmonic_compatible": compatible,
                "method": "librosa"
            }
        
        except Exception as e:
            self.log(f"ERROR in librosa: {str(e)}")
            return None
    
    def _detect_key_from_chroma(self, chroma_mean: np.ndarray) -> Tuple[str, float]:
        """
        Detect key from chroma vector using harmonic templates.
        
        Args:
            chroma_mean: Mean chroma vector (12 elements)
            
        Returns:
            Tuple of (key_name, confidence)
        """
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        
        # Normalize chroma
        chroma_norm = chroma_mean / (np.sum(np.abs(chroma_mean)) + 1e-10)
        
        best_key = "C Major"
        best_confidence = 0
        
        # Major scale intervals from tonic (in semitones)
        major_intervals = [0, 2, 4, 5, 7, 9, 11]
        # Minor scale intervals from tonic (in semitones)
        minor_intervals = [0, 2, 3, 5, 7, 8, 10]
        
        # Try each possible tonic
        for tonic_idx in range(12):
            tonic = notes[tonic_idx]
            
            # Calculate major confidence
            major_score = sum(chroma_norm[(tonic_idx + i) % 12] for i in major_intervals)
            minor_score = sum(chroma_norm[(tonic_idx + i) % 12] for i in minor_intervals)
            
            # Major key
            total = major_score + minor_score
            if total > 0:
                major_confidence = major_score / total
            else:
                major_confidence = 0.5
            
            if major_confidence > best_confidence:
                best_confidence = major_confidence
                best_key = f"{tonic} Major"
            
            # Minor key
            if total > 0:
                minor_confidence = minor_score / total
            else:
                minor_confidence = 0.5
            
            if minor_confidence > best_confidence:
                best_confidence = minor_confidence
                best_key = f"{tonic} Minor"
        
        return best_key, best_confidence
    
    def _detect_scale_librosa(self, chroma_norm: np.ndarray, tonic_idx: int) -> Tuple[float, float]:
        """
        Simple major/minor detection using harmonic templates.
        """
        # Major scale intervals from tonic (in semitones)
        major_intervals = [0, 2, 4, 5, 7, 9, 11]
        minor_intervals = [0, 2, 3, 5, 7, 8, 10]
        
        major_score = sum(chroma_norm[(tonic_idx + i) % 12] for i in major_intervals)
        minor_score = sum(chroma_norm[(tonic_idx + i) % 12] for i in minor_intervals)
        
        # Normalize to 0-1
        total = major_score + minor_score
        if total > 0:
            major_conf = major_score / total
            minor_conf = minor_score / total
        else:
            major_conf = minor_conf = 0.5
        
        return major_conf, minor_conf
    
    def _find_closest_key(self, key_name: str) -> str:
        """Find closest key in Camelot Wheel"""
        # If key not found, return a default based on first matching pattern
        for camelot_key in CAMELOT_WHEEL.keys():
            if camelot_key.split()[0] == key_name.split()[0]:
                return CAMELOT_WHEEL[camelot_key]
        # Default to 8B (C Major) if nothing matches
        return "8B"
    
    def detect_key(self, audio_path: str) -> Dict:
        """
        Main key detection function.
        Uses librosa chroma analysis with harmonic templates.
        
        Args:
            audio_path: Path to audio file (MP3, WAV, etc.)
            
        Returns:
            Dictionary with key, camelot, confidence, and harmonic compatibility
        """
        self.log("START")
        
        # Validate audio
        is_valid, error_msg = self._validate_audio(audio_path)
        if not is_valid:
            self.log(f"VALIDATION_ERROR: {error_msg}")
            return {
                "success": False,
                "error": error_msg,
                "key": None
            }
        
        self.log(f"VALIDATING: File is valid audio")
        
        # Primary method: chroma-based detection
        result = self.detect_key_librosa_chroma(audio_path)
        
        # Fallback to simpler librosa method if chroma fails
        if result is None or not result.get("success"):
            self.log("FALLBACK: Switching to alternative librosa method")
            result = self.detect_key_librosa(audio_path)
        
        if not result or not result.get("success"):
            self.log("ERROR: All detection methods failed")
            return result or {
                "success": False,
                "error": "All detection methods failed",
                "key": None
            }
        
        self.log("DONE")
        return result


def detect_key(audio_path: str, log_callback=None) -> dict:
    """
    Main entry point function.
    
    Args:
        audio_path: Path to audio file
        log_callback: Optional callback for logging
        
    Returns:
        Dictionary with key detection results
    """
    detector = KeyDetector(log_callback=log_callback)
    return detector.detect_key(audio_path)


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        output = {
            "success": False,
            "error": "Usage: python key_detector.py <audio_file.mp3> [--no-logs]",
            "key": None
        }
        print(json.dumps(output))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    no_logs = "--no-logs" in sys.argv
    
    # Setup logging
    log_dir = None
    log_file = None
    logs = []
    
    def log_callback(msg):
        logs.append(msg)
        # Write to stderr for Electron
        sys.stderr.write(msg + '\n')
        sys.stderr.flush()
        # Also write to log file
        if not no_logs and log_file:
            with open(log_file, 'a') as f:
                f.write(msg + '\n')
                f.flush()
    
    if not no_logs:
        log_dir = Path(__file__).parent.parent / "logs_key"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    # Detect key
    detector = KeyDetector(log_callback=log_callback)
    result = detector.detect_key(audio_file)
    
    # Ensure result is always valid JSON
    if result is None:
        result = {
            "success": False,
            "error": "Detection returned None",
            "key": None
        }
    elif not isinstance(result, dict):
        result = {
            "success": False,
            "error": f"Invalid result type: {type(result)}",
            "key": None
        }
    
    # Ensure required fields exist
    if "success" not in result:
        result["success"] = result.get("key") is not None
    
    if "key" not in result:
        result["key"] = None
    
    if not result.get("success") and "error" not in result:
        result["error"] = "Unknown error - check logs"
    
    # Print ONLY JSON to stdout (logs go to stderr)
    try:
        json_output = json.dumps(result)
        print(json_output, flush=True)
    except Exception as e:
        # If JSON encoding fails, output an error JSON
        print(json.dumps({
            "success": False,
            "error": f"JSON encoding error: {str(e)}",
            "key": None
        }), flush=True)
    
    # Always exit 0 to let Electron handle the success/failure
    sys.exit(0)


if __name__ == "__main__":
    main()
