# BLOND Stem Splitter

🎵 Separate vocals and instrumentals from your music using AI

## Features

- 🎬 Easy-to-use interface built with Vue 3 and Tailwind CSS
- 🤖 AI-powered audio separation using Demucs
- 🎵 High-precision BPM detection (madmom + librosa)
- 💾 High-quality MP3 output (128 kbps)
- ⚡ Fast processing with lightweight models
- 📊 Real-time progress tracking
- 📱 Cross-platform (Windows & macOS)

## For Users

### Quick Start

1. **Download** the latest release:
   - **Windows**: `BLOND-Stem-Splitter-1.0.0.exe`
   - **macOS**: `BLOND-Stem-Splitter-1.0.0.dmg` or `.zip`

2. **Install & Run**:
   - **Windows**: Download `.exe`, double-click to install or run portable version
   - **macOS**: Download `.dmg`, drag to Applications, or unzip and run `.app`

3. **Use**:
   - Click "Choose Audio File" to select your song (MP3 or WAV)
   - Click "Choose Output Folder" to select where to save results
   - **(Optional)** Click "Detect BPM" to analyze the song's tempo (shows confidence %)
   - Click "Split Audio" and wait for processing
   - Find your separated tracks in the output folder:
     - `song_name/vocals.mp3` - The vocal track
     - `song_name/instrumental.mp3` - The instrumental track

**Note**: No Python, Node.js, or terminal knowledge required! Everything is included in the executable.

---

## For Developers

### Prerequisites

- Node.js 14+ and npm
- macOS (for building macOS app) or Windows (for building Windows exe)
- Python 3.9+ with venv
- PyInstaller (`pip install pyinstaller`)

### Development Setup

```bash
# 1. Clone and setup
cd /Users/menro/Documents/BLOND

# 2. Install npm dependencies
npm install

# 3. (Optional) Install BPM detection dependencies
pip install -r requirements_bpm.txt

# 4. Start development server
npm start
```

### Building Distributions

#### Build Everything (Automated)

```bash
# For macOS
npm run build
```

This automatically:
1. Installs npm dependencies
2. Bundles Python venv with Electron
3. Creates `.dmg` (installer) and `.zip` (portable) for macOS

#### Build Components Separately

```bash
# Build only for macOS
npm run build:mac
```

#### Output Files

Distribution files are saved in `dist/`:

- **macOS**: 
  - `BLOND Stem Splitter-1.0.0.dmg` - Installer (double-click to install)
  - `BLOND Stem Splitter-1.0.0.zip` - Portable version (unzip and run)

### Project Structure

```
BLOND/
├── main.js                 # Electron main process
├── preload.js              # IPC bridge
├── index.html              # HTML entry
├── renderer/
│   ├── app.js             # Vue 3 root component
│   └── App.js             # Main component with Tailwind
├── demucs/
│   ├── demucs_runner.py   # Python audio processor
│   ├── bpm_detector.py    # BPM detection script
│   ├── build_exe.sh       # PyInstaller script
│   └── dist/              # Compiled Python executable
├── python_env/            # Virtual environment
├── assets/                # Icons and resources
└── package.json           # Node configuration
```

### How It Works

1. **Frontend**: Vue 3 + Tailwind CSS (responsive UI)
2. **IPC**: Electron preload bridge communicates between Electron and Python
3. **Audio Processing**: Python venv bundled directly with app
4. **Demucs**: AI model for audio separation (in venv)
5. **BPM Detection**: Professional-grade beat tracking with madmom + librosa
6. **Distribution**: Electron-builder packages everything into standalone `.dmg` and `.zip`

**Key Advantage**: No PyInstaller needed - just bundles the venv directly, which is simpler and faster!

#### BPM Detection Algorithm

**Method Selection (Automatic):**
1. **Primary**: Madmom RNN-based beat tracking (professional DJ software accuracy)
2. **Fallback**: Librosa tempogram (if madmom unavailable)

**Features:**
- ✓ High precision for electronic music (House, Techno, Hip-Hop)
- ✓ Comparable to Rekordbox, Serato, and Traktor
- ✓ Automatic double-time/half-time error correction
- ✓ Confidence scoring (0-100%)
- ✓ MP3 validation
- ✓ Optimized for long audio files (fast processing)
- ✓ Inter-beat interval analysis for stability

**Algorithm Details:**
- **Madmom**: Uses pre-trained RNN to detect beat activations, then applies beat tracking for stability
- **Librosa**: Analyzes onset strength and tempogram for tempo estimation
- **Correction**: Automatically detects and corrects common octave errors (double-time/half-time)
- **Confidence**: Based on beat stability (standard deviation of inter-beat intervals)

**Typical Detection Time:** 1-2 seconds per song (even for 10+ minute tracks)

### Sharing the App

#### Option 1: Direct Executable (Fastest)
```bash
# After building, upload from dist/ folder:
# - Windows: BLOND-Stem-Splitter-1.0.0.exe
# - macOS: BLOND-Stem-Splitter-1.0.0.zip
```

#### Option 2: Installer (Recommended)
```bash
# macOS DMG installer (included in dist/)
# Users can drag-and-drop to Applications
```

#### Option 3: GitHub Releases
1. Create release on GitHub
2. Upload `.exe` and `.dmg`/`.zip` from `dist/`
3. Share release link

#### Option 4: Cloud Storage
1. Upload from `dist/` to:
   - Google Drive
   - Dropbox
   - OneDrive
2. Share link with users

---

## BPM Detection Setup (For Developers)

### Installation

The BPM detector requires additional Python dependencies. These are automatically installed in the bundled venv for distribution builds, but for development:

```bash
# Install high-precision BPM detection dependencies
pip install -r requirements_bpm.txt

# This installs:
# - madmom (primary: RNN-based beat tracking)
# - librosa (fallback: tempogram-based)
# - numpy, scipy (required for signal processing)
```

### Usage

```bash
# Command line usage
python demucs/bpm_detector.py /path/to/song.mp3

# Output:
# {
#   "success": true,
#   "bpm": 128,
#   "confidence": 92,
#   "method": "madmom_rnn",
#   "beats_detected": 512
# }
```

### Python Integration

```python
from demucs.bpm_detector import BPMDetector

detector = BPMDetector()
result = detector.detect_bpm('song.mp3')
print(f"BPM: {result['bpm']}, Confidence: {result['confidence']}%")
```

### Advanced Examples

See `demucs/bpm_advanced_examples.py` for:
- Batch processing
- Performance testing
- Genre-specific detection
- Error handling
- Custom logging

---

## Troubleshooting

### "App won't open on macOS"
- Right-click app → "Open" (security check)
- Or allow in System Preferences → Security

### "No output files created"
- Check that output folder has write permissions
- Ensure input file is valid MP3/WAV
- Check `output/demucs_log_*.txt` for errors

### "Process timed out"
- Very long songs may take longer
- Check available disk space
- Increase timeout in `demucs/demucs_runner.py` if needed

### "BPM detection fails"
- Ensure the file is a valid MP3
- Check that the file is at least 10KB
- Very noisy or low-quality audio may fail
- Check console output for detailed error messages
- Verify madmom/librosa are installed: `pip list | grep -E "madmom|librosa"`

### "BPM detection is slow"
- First detection loads RNN model (1-2 seconds on first run)
- Subsequent detections reuse the model (faster)
- Very long songs (>20 min) take slightly longer
- Try `--no-logs` flag to skip logging overhead

### "BPM detection accuracy"
- Madmom is optimized for electronic music (House, Techno, Hip-Hop)
- Low-quality MP3s or heavily compressed audio may reduce accuracy
- Confidence score indicates how stable the detected BPM is
- If confidence is low (<60%), the result may be less reliable

---

## Development Notes

- **Python version**: 3.9 (required for compatibility)
- **Demucs model**: `htdemucs` (fast, good quality)
- **Output bitrate**: 128 kbps (adjust in `demucs_runner.py` if needed)
- **Timeout**: 180 seconds (3 minutes) max processing time
- **BPM Detection**: Uses Librosa's beat tracking algorithm
- **Librosa version**: Latest (handles MP3 with audioread backend)

## License

MIT

## Credits

- [Demucs](https://github.com/facebookresearch/demucs) - Audio separation AI
- [Electron](https://www.electronjs.org/) - Cross-platform desktop app
- [Vue 3](https://vuejs.org/) - UI framework
- [Tailwind CSS](https://tailwindcss.com/) - Styling