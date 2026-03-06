#!/bin/bash

# BPM Detection Quick Setup Script
# Installs all required dependencies for high-precision beat tracking

set -e  # Exit on error

echo "╔════════════════════════════════════════════╗"
echo "║ BLOND BPM Detector - Dependency Installer ║"
echo "╚════════════════════════════════════════════╝"
echo ""

# Get the directory this script is in
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

echo "📁 Project directory: $PROJECT_DIR"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1)
echo "   $PYTHON_VERSION"
echo ""

# Check if pip is available
echo "📦 Checking pip..."
if ! command -v pip3 &> /dev/null; then
    echo "   ❌ pip3 not found. Please install Python with pip."
    exit 1
fi
echo "   ✓ pip3 found"
echo ""

# Install requirements
echo "⬇️  Installing BPM detection dependencies..."
echo "   This may take a few minutes..."
echo ""

if [ -f "$PROJECT_DIR/requirements_bpm.txt" ]; then
    pip3 install -r "$PROJECT_DIR/requirements_bpm.txt"
    echo ""
    echo "✓ Dependencies installed successfully!"
else
    echo "❌ requirements_bpm.txt not found"
    exit 1
fi

echo ""
echo "🔍 Verifying installation..."
python3 << 'EOF'
import sys

try:
    import madmom
    print("   ✓ madmom (RNN beat tracking)")
except ImportError:
    print("   ⚠️  madmom not available (optional fallback to librosa)")

try:
    import librosa
    print("   ✓ librosa (tempogram beat tracking)")
except ImportError:
    print("   ❌ librosa not found")
    sys.exit(1)

try:
    import numpy
    print("   ✓ numpy")
except ImportError:
    print("   ❌ numpy not found")
    sys.exit(1)

try:
    import scipy
    print("   ✓ scipy")
except ImportError:
    print("   ❌ scipy not found")
    sys.exit(1)

print("")
print("✓ All required dependencies installed!")
EOF

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║      ✓ Setup Complete!                     ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
    echo "Next steps:"
    echo "1. Test BPM detection:"
    echo "   python3 demucs/bpm_detector.py /path/to/song.mp3"
    echo ""
    echo "2. Read the guide:"
    echo "   cat BPM_DETECTION_GUIDE.md"
    echo ""
    echo "3. Try advanced examples:"
    echo "   python3 demucs/bpm_advanced_examples.py basic"
    echo ""
else
    echo ""
    echo "❌ Installation verification failed"
    exit 1
fi
