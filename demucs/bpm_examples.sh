#!/bin/bash
# BPM Detection Usage Examples for BLOND

# Example 1: Direct Python script usage
echo "=== Example 1: Direct BPM Detection ==="
python3 /Users/menro/Documents/BLOND/demucs/bpm_detector.py "/path/to/song.mp3"

# Output example:
# {"success": true, "bpm": 120, "confidence": 85, "duration": 245.5, "sample_rate": 22050}

# Example 2: From within Node.js/Electron (automatic via preload bridge)
# const result = await window.api.detectBPM("/path/to/song.mp3")
# console.log(`BPM: ${result.bpm}`)

# Example 3: Testing with multiple files
echo "=== Example 3: Batch BPM Detection ==="
for file in ~/Music/*.mp3; do
    echo "Testing: $file"
    python3 /Users/menro/Documents/BLOND/demucs/bpm_detector.py "$file"
done
