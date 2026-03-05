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

def detect_bpm(audio_path: str) -> dict:
    """
    Detect BPM from an MP3 file using librosa's beat tracking.
    
    Args:
        audio_path: Path to MP3 file
        
    Returns:
        Dictionary with BPM and confidence metrics
    """
    try:
        # Load audio file
        y, sr = librosa.load(audio_path, sr=None)
        
        # Extract tempo using librosa's built-in beat tracking
        # This uses the tempogram and finds the dominant beat
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        
        # Round to nearest integer for cleaner output
        bpm = round(float(tempo))
        
        # Get additional metrics for confidence
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        tempogram = librosa.feature.tempogram(onset_env=onset_env, sr=sr)
        
        # Calculate a confidence score (0-100)
        # Based on the strength of the detected beat
        confidence = min(100, int(np.max(tempogram) * 100))
        
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
    result = detect_bpm(audio_file)
    
    # Print result as JSON for easy parsing
    print(json.dumps(result))
    
    # Exit with success code only if detection succeeded
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
