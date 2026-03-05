#!/usr/bin/env python3
"""
Quick test script to debug demucs
"""
import subprocess
import sys
from pathlib import Path

python_env_path = Path(__file__).parent / "python_env" / "bin" / "demucs"
print(f"Demucs path: {python_env_path}")
print(f"Demucs exists: {python_env_path.exists()}")

# Try to get demucs version
print("\n=== Testing demucs command ===")
try:
    result = subprocess.run(
        [str(python_env_path), "--help"],
        capture_output=True,
        text=True,
        timeout=30
    )
    print(f"Exit code: {result.returncode}")
    print(f"Output length: {len(result.stdout)}")
    if result.stderr:
        print(f"STDERR: {result.stderr[:500]}")
except subprocess.TimeoutExpired:
    print("TIMEOUT: demucs --help timed out")
except Exception as e:
    print(f"ERROR: {e}")

# Try to import demucs module directly
print("\n=== Testing demucs import ===")
try:
    sys.path.insert(0, str(Path(__file__).parent / "python_env" / "lib" / "python3.9" / "site-packages"))
    import demucs
    print(f"Demucs imported successfully")
    print(f"Demucs version: {demucs.__version__ if hasattr(demucs, '__version__') else 'unknown'}")
except Exception as e:
    print(f"ERROR importing demucs: {e}")
