#!/bin/bash

# Key Detector Examples

PYTHON_PATH="$(dirname "$0")/python_env/bin/python"

echo "=== Musical Key Detection Examples ==="
echo ""

# Example 1: Basic key detection
echo "Example 1: Detect musical key"
echo "$PYTHON_PATH demucs/key_detector.py /path/to/song.mp3"
echo "Output:"
echo '{'
echo '  "success": true,'
echo '  "key": "F# Minor",'
echo '  "camelot": "11A",'
echo '  "confidence": 0.92,'
echo '  "harmonic_compatible": ["10A", "12A", "11B"]'
echo '}'
echo ""

# Example 2: Without logging
echo "Example 2: Fast detection without logging"
echo "$PYTHON_PATH demucs/key_detector.py /path/to/song.mp3 --no-logs"
echo ""

# Example 3: Batch processing
echo "Example 3: Analyze entire music library"
echo "for f in *.mp3; do"
echo "    python3 demucs/key_detector.py \"\$f\" --no-logs | python3 -m json.tool"
echo "done"
echo ""

echo "=== Features ==="
echo "✓ Essentia (primary) or librosa (fallback) for key detection"
echo "✓ Camelot Wheel compatibility"
echo "✓ Harmonic mixing analysis for DJs"
echo "✓ Confidence scoring"
echo "✓ JSON output for easy parsing"
echo ""
