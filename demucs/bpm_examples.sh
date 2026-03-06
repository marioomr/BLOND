#!/bin/bash

# BPM Detector Examples - High-precision beat tracking for electronic music

# Get Python from venv
PYTHON_PATH="$(dirname "$0")/../python_env/bin/python"

echo "=== BLOND BPM Detector - High Precision Examples ==="
echo ""

# Example 1: Basic BPM detection
echo "Example 1: Basic BPM Detection from single MP3"
echo "$PYTHON_PATH bpm_detector.py /path/to/song.mp3"
echo "Output: {\"success\": true, \"bpm\": 128, \"confidence\": 92, ...}"
echo ""

# Example 2: Without logging (faster)
echo "Example 2: Detection without logging"
echo "$PYTHON_PATH bpm_detector.py /path/to/song.mp3 --no-logs"
echo ""

# Example 3: Batch processing
echo "Example 3: Batch process all MP3 files in folder"
echo "for file in /path/to/songs/*.mp3; do"
echo "    \$PYTHON_PATH bpm_detector.py \"\$file\""
echo "done"
echo ""

# Example 4: Python integration
echo "Example 4: Using in Python code"
echo "from bpm_detector import BPMDetector"
echo ""
echo "detector = BPMDetector()"
echo "result = detector.detect_bpm('song.mp3')"
echo "print(f\"BPM: {result['bpm']}, Confidence: {result['confidence']}%\")"
echo ""

echo "=== Features ==="
echo "✓ Primary: madmom RNN (most accurate for electronic music)"
echo "✓ Fallback: librosa tempogram"
echo "✓ Auto-correct double-time/half-time errors"
echo "✓ Confidence scoring (0-100%)"
echo "✓ Support: House, Techno, Hip-Hop, Electronic"
echo "✓ Quality: Comparable to Rekordbox/Serato/Traktor"
echo ""
