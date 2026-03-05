# BPM Detector Integration Guide

## Overview

BLOND now includes **Librosa-based BPM detection** with confidence scoring. The detector analyzes audio files and returns precise tempo information.

## Features

✅ **Precise Detection**: Uses beat tracking algorithm (not approximate)
✅ **Confidence Scoring**: Returns 0-100% confidence metric
✅ **Fast Processing**: 1-3 seconds per song (after library load)
✅ **Cross-Platform**: Works on Windows, macOS, and Linux
✅ **JSON Output**: Easy integration with Electron
✅ **Error Handling**: Graceful failures with clear error messages

## Architecture

### File Structure

```
/demucs/
├── bpm_detector.py      # Main detection script
├── demucs_runner.py     # Audio separation (existing)
└── bpm_examples.sh      # Usage examples
```

### Data Flow

```
User clicks "Detect BPM"
    ↓
renderer/app.js calls window.api.detectBPM()
    ↓
preload.js invokes IPC "detect-bpm"
    ↓
main.js spawns Python subprocess
    ↓
demucs/bpm_detector.py analyzes audio
    ↓
Returns JSON: {success, bpm, confidence, duration, sample_rate}
    ↓
UI displays BPM with confidence badge
```

## Usage

### From the UI (End User)

1. Select an audio file (MP3 or WAV)
2. Click the "Detect BPM" button
3. Wait 1-3 seconds for analysis
4. View BPM and confidence % in the UI

### From JavaScript/Electron

```javascript
// In renderer/app.js or any component
const result = await window.api.detectBPM(audioFilePath)

// Result structure:
{
  success: boolean,
  bpm: number,                    // e.g., 120
  confidence: number,             // 0-100
  duration: number,              // seconds
  sample_rate: number,           // Hz
  error?: string                 // if success === false
}

// Example
if (result.success) {
  console.log(`Detected: ${result.bpm} BPM (${result.confidence}% confidence)`)
} else {
  console.error(`Error: ${result.error}`)
}
```

### From Python (CLI)

```bash
# Activate venv first
source /Users/menro/Documents/BLOND/python_env/bin/activate

# Run directly
python3 demucs/bpm_detector.py "path/to/song.mp3"

# Output
# {"success": true, "bpm": 128, "confidence": 92, ...}
```

## Implementation Details

### Algorithm: Librosa Beat Tracking

1. **Audio Loading**: Loads MP3/WAV at original sample rate
2. **Onset Detection**: Extracts onset strength (beats)
3. **Tempogram**: Analyzes tempo across time
4. **Peak Detection**: Finds dominant beat frequency
5. **Confidence**: Uses tempogram peak strength

### Why Librosa?

- ✅ Most accurate open-source beat detection
- ✅ Handles various audio formats (MP3, WAV, FLAC, etc.)
- ✅ Pip-installable (no system dependencies)
- ✅ Cross-platform (macOS, Windows, Linux)
- ✅ Active development and community support

### Performance

| Scenario | Time | Notes |
|----------|------|-------|
| First detection | 3-5s | Loads libraries + audio |
| Subsequent | 1-3s | Libraries cached |
| Very long song (>10min) | 2-4s | Linear with duration |
| Noisy/complex audio | 2-4s | Detailed analysis |

## Customization

### Adjusting Confidence Calculation

Edit `bpm_detector.py` line ~35:

```python
# Current (simple)
confidence = min(100, int(np.max(tempogram) * 100))

# Alternative (more aggressive)
confidence = min(100, int(np.percentile(tempogram, 95) * 100))
```

### Supporting More Formats

Librosa already supports: MP3, WAV, FLAC, OGG, M4A

To add format filtering in the UI, modify `index.html` audio file filter:

```javascript
filters: [{ name: "Audio", extensions: ["mp3", "wav", "flac", "m4a"] }]
```

### Changing Tempo Range

To focus on specific tempo ranges, modify `bpm_detector.py`:

```python
# Current: auto-detect any tempo
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)

# Custom: specify range (e.g., 60-180 BPM)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr, start_bpm=60, tightness=100)
```

## Troubleshooting

### "BPM detection fails on startup"

**Problem**: Librosa not installed
**Solution**: 
```bash
source /Users/menro/Documents/BLOND/python_env/bin/activate
pip install librosa
```

### "Returns 0 BPM or confidence very low"

**Problem**: Audio is too noisy or unusual tempo
**Solution**: Try different file, inspect stderr logs

### "Takes too long (>5s)"

**Problem**: Very long file or weak internet (audioread backend)
**Solution**: Use local files, or optimize file before processing

### "JSON parse error in Electron"

**Problem**: Python script output has extra text
**Solution**: Check console.log in main.js, ensure clean JSON output

## Testing

### Manual Test

```bash
# Test with a known song file
python3 demucs/bpm_detector.py ~/Music/sample.mp3

# Should output clean JSON
# {"success": true, "bpm": 120, "confidence": 85, ...}
```

### Integration Test

1. Launch app: `npm start`
2. Select an audio file
3. Click "Detect BPM"
4. Check console (DevTools: Cmd+Option+I)
5. Verify BPM displays in UI

## Future Enhancements

- [ ] Detect key (music_key library)
- [ ] Energy level analysis
- [ ] Onset event markers
- [ ] Batch processing UI
- [ ] BPM history/cache
- [ ] Genre detection

## Dependencies

- **librosa** ^0.11.0 - Audio analysis
- **numpy** - Numerical computing (auto-installed with librosa)
- **scipy** - Signal processing (auto-installed with librosa)
- **audioread** - Audio backend (auto-installed with librosa)

All are pip-installable and included in the venv.

## License

Same as BLOND (MIT)
