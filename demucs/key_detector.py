#!/usr/bin/env python3
"""
Musical Key Detection with Harmonic Analysis
Detects musical key, converts to Camelot Wheel, and calculates DJ compatibility
Uses Essentia for precise key detection (most reliable for professional use)
Fallback to librosa if Essentia unavailable
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import numpy as np

# Try importing Essentia (most accurate)
try:
    import essentia
    import essentia.standard as es
    HAS_ESSENTIA = True
except ImportError:
    HAS_ESSENTIA = False

# Fallback to librosa
try:
    import librosa
    import librosa.feature
    HAS_LIBROSA = True
except ImportError:
    HAS_LIBROSA = False


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
    
    def detect_key_essentia(self, audio_path: str) -> Dict:
        """
        Detect key using Essentia (most accurate, used by Spotify).
        
        Returns:
            Dictionary with key, scale, confidence, camelot, and compatibility
        """
        try:
            self.log("METHOD: Using Essentia Key Detection")
            
            # Load audio
            self.log("LOADING: Loading audio file...")
            loader = es.MonoLoader(filename=audio_path, sampleRate=self.sr)
            audio = loader()
            self.log(f"LOADED: {len(audio) / self.sr:.1f}s")
            
            # Key detection
            self.log("ANALYZING: Detecting musical key...")
            key_detector = es.KeyExtractor()
            key, scale, confidence = key_detector(audio)
            
            # Essentia returns key as string like "C" and scale as "major" or "minor"
            key_name = f"{key} {scale.title()}"
            self.log(f"DETECTED: Key={key_name}, Confidence={confidence:.2f}")
            
            # Get Camelot
            camelot = CAMELOT_WHEEL.get(key_name)
            if not camelot:
                self.log(f"WARNING: Unknown key {key_name}, using closest match")
                camelot = self._find_closest_key(key_name)
            
            # Get harmonic compatibility
            compatible = HARMONIC_COMPATIBILITY.get(camelot, [])
            
            return {
                "success": True,
                "key": key_name,
                "scale": scale,
                "confidence": float(confidence),
                "camelot": camelot,
                "harmonic_compatible": compatible,
                "method": "essentia"
            }
        
        except Exception as e:
            self.log(f"ERROR in Essentia: {str(e)}")
            return None
    
    def detect_key_librosa(self, audio_path: str) -> Dict:
        """
        Detect key using librosa's chroma features.
        Fallback method when Essentia unavailable.
        
        Returns:
            Dictionary with key, scale, confidence, camelot, and compatibility
        """
        try:
            self.log("METHOD: Using librosa Chroma Analysis")
            
            # Load audio
            self.log("LOADING: Loading audio file...")
            y, sr = librosa.load(audio_path, sr=self.sr, mono=True)
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
        Tries Essentia first, falls back to librosa.
        
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
        
        # Try Essentia first (most accurate)
        result = None
        if HAS_ESSENTIA:
            result = self.detect_key_essentia(audio_path)
        
        # Fallback to librosa
        if result is None or not result.get("success"):
            if HAS_LIBROSA:
                self.log("FALLBACK: Switching to librosa")
                result = self.detect_key_librosa(audio_path)
            else:
                return {
                    "success": False,
                    "error": "Neither Essentia nor librosa available",
                    "key": None
                }
        
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
    
    # Ensure result is always valid
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
    
    # Ensure success field exists
    if "success" not in result:
        result["success"] = False
        if "key" not in result or result.get("key") is None:
            result["error"] = result.get("error", "Unknown error")
    
    # Print ONLY JSON to stdout (logs go to stderr)
    print(json.dumps(result), flush=True)
    
    # Exit with appropriate code
    sys.exit(0 if result.get("success", False) else 1)


if __name__ == "__main__":
    main()
