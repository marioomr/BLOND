#!/usr/bin/env python3
"""
BPM Detection Script for BLOND Stem Splitter
Uses librosa for accurate tempo detection
"""

import sys
import json
import librosa
import numpy as np
from pathlib import Path
from datetime import datetime

def detect_bpm(audio_path: str, log_callback=None) -> dict:
    """
    Detect BPM from an MP3 file using librosa's beat tracking.
    
    Args:
        audio_path: Path to MP3 file
        log_callback: Optional callback function for logging
        
    Returns:
        Dictionary with BPM and confidence metrics
    """
    try:
        if log_callback:
            log_callback("START")
        
        # Load audio file
        y, sr = librosa.load(audio_path, sr=None)
        if log_callback:
            log_callback(f"LOADING: Loaded audio at {sr}Hz")
        
        # Extract tempo using librosa's built-in beat tracking
        # This uses the tempogram and finds the dominant beat
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        
        # Round to nearest integer for cleaner output
        bpm = round(float(tempo))
        if log_callback:
            log_callback(f"DETECTED: {bpm} BPM")
        
        # Calculate confidence using onset strength
        # More reliable than tempogram which requires specific parameters
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        
        # Confidence is based on how strong the onset strength is
        # Normalize to 0-100 range
        confidence = min(100, int(np.mean(onset_env) * 100 + 20))
        confidence = max(50, confidence)  # Minimum 50% confidence
        
        if log_callback:
            log_callback(f"CONFIDENCE: {confidence}%")
        
        duration = float(librosa.get_duration(y=y, sr=sr))
        
        if log_callback:
            log_callback("DONE")
        
        return {
            "success": True,
            "bpm": bpm,
            "confidence": confidence,
            "duration": float(librosa.get_duration(y=y, sr=sr)),
            "sample_rate": sr
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"File not found: {audio_path}",
            "bpm": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "bpm": None
        }


def main():
    """Main entry point for CLI usage"""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: python bpm_detector.py <audio_file.mp3>",
            "bpm": None
        }))
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    # Setup logging to file
    log_dir = Path(__file__).parent.parent / "bpm_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"bpm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    logs = []
    def log_callback(msg):
        logs.append(msg)
        with open(log_file, 'a') as f:
            f.write(msg + '\n')
            f.flush()
        print(msg, flush=True)
    
    result = detect_bpm(audio_file, log_callback=log_callback)
    
    # Print result as JSON for easy parsing
    print(json.dumps(result))
    
    # Exit with success code only if detection succeeded
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
