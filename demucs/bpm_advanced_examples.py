#!/usr/bin/env python3
"""
BPM Detector - Advanced Examples and Testing
Demonstrates high-precision BPM detection for electronic music
"""

import json
import sys
from pathlib import Path
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from bpm_detector import BPMDetector


def example_basic_detection():
    """Basic BPM detection"""
    print("\n=== Example 1: Basic BPM Detection ===")
    
    detector = BPMDetector()
    
    # Test with your own MP3
    test_file = "/path/to/test.mp3"  # Replace with actual path
    
    if Path(test_file).exists():
        result = detector.detect_bpm(test_file)
        print(json.dumps(result, indent=2))
    else:
        print(f"Test file not found: {test_file}")


def example_batch_processing():
    """Process multiple files"""
    print("\n=== Example 2: Batch Processing ===")
    
    detector = BPMDetector()
    
    # Process all MP3 files in a directory
    music_dir = Path("/path/to/music/folder")
    
    if music_dir.exists():
        mp3_files = list(music_dir.glob("*.mp3"))
        print(f"Found {len(mp3_files)} MP3 files")
        
        results = []
        for audio_file in mp3_files[:5]:  # Test first 5
            result = detector.detect_bpm(str(audio_file))
            if result["success"]:
                results.append({
                    "file": audio_file.name,
                    "bpm": result["bpm"],
                    "confidence": result["confidence"],
                    "method": result.get("method", "unknown")
                })
        
        # Display summary
        print(f"\n{'File':<30} {'BPM':>6} {'Confidence':>12} {'Method':<20}")
        print("-" * 68)
        for r in results:
            print(f"{r['file']:<30} {r['bpm']:>6} {r['confidence']:>11}% {r['method']:<20}")
    else:
        print(f"Directory not found: {music_dir}")


def example_performance_testing():
    """Test performance on large files"""
    print("\n=== Example 3: Performance Testing ===")
    
    detector = BPMDetector()
    test_file = "/path/to/long_track.mp3"
    
    if Path(test_file).exists():
        print(f"Testing: {test_file}")
        
        start = time.time()
        result = detector.detect_bpm(test_file)
        elapsed = time.time() - start
        
        if result["success"]:
            print(f"BPM: {result['bpm']}")
            print(f"Confidence: {result['confidence']}%")
            print(f"Method: {result.get('method', 'unknown')}")
            print(f"Processing time: {elapsed:.2f}s")
        else:
            print(f"Error: {result.get('error')}")
    else:
        print(f"Test file not found: {test_file}")


def example_genre_detection():
    """Detect BPM for specific genres"""
    print("\n=== Example 4: Genre-Specific Testing ===")
    
    detector = BPMDetector()
    
    test_files = {
        "house": "/path/to/house_track.mp3",
        "techno": "/path/to/techno_track.mp3",
        "hip_hop": "/path/to/hiphop_track.mp3",
    }
    
    print(f"{'Genre':<15} {'BPM':>6} {'Confidence':>12} {'Expected Range':>20}")
    print("-" * 55)
    
    genre_bpm_ranges = {
        "house": (120, 135),
        "techno": (120, 150),
        "hip_hop": (85, 115),
    }
    
    for genre, filepath in test_files.items():
        if Path(filepath).exists():
            result = detector.detect_bpm(filepath)
            if result["success"]:
                bpm = result["bpm"]
                min_bpm, max_bpm = genre_bpm_ranges[genre]
                in_range = "✓" if min_bpm <= bpm <= max_bpm else "✗"
                print(f"{genre:<15} {bpm:>6} {result['confidence']:>11}% {in_range} ({min_bpm}-{max_bpm})")


def example_error_handling():
    """Demonstrate error handling"""
    print("\n=== Example 5: Error Handling ===")
    
    detector = BPMDetector()
    
    test_cases = [
        ("/path/that/does/not/exist.mp3", "Non-existent file"),
        ("/path/to/document.txt", "Wrong file type"),
    ]
    
    for filepath, description in test_cases:
        print(f"\nTest: {description}")
        print(f"File: {filepath}")
        result = detector.detect_bpm(filepath)
        if not result["success"]:
            print(f"Error: {result.get('error', 'Unknown error')}")
        else:
            print(f"BPM: {result['bpm']}")


def example_double_time_correction():
    """Demonstrate double-time/half-time correction"""
    print("\n=== Example 6: Double-Time/Half-Time Correction ===")
    
    print("""
The detector automatically corrects common BPM errors:

1. Double-Time Detection:
   - When actual BPM is ~90 but detected as ~180
   - Correction: Automatically divides by 2
   - Confidence reduced by 10% to reflect uncertainty

2. Half-Time Detection:
   - When actual BPM is ~160 but detected as ~80
   - Correction: Automatically multiplies by 2
   - Confidence reduced by 10% to reflect uncertainty

Example:
- Input: Techno track, actual BPM: 128
- Detected: 256 (double-time error)
- Corrected: 128
- Confidence: Original - 10%
- Field "correction_applied": "half_bpm"
    """)


def example_with_logging():
    """Demonstrate with logging callback"""
    print("\n=== Example 7: Detection with Logging ===")
    
    logs = []
    
    def log_callback(message):
        logs.append(message)
        print(f"  [LOG] {message}")
    
    detector = BPMDetector(log_callback=log_callback)
    
    test_file = "/path/to/test.mp3"
    if Path(test_file).exists():
        result = detector.detect_bpm(test_file)
        print(f"\nResult: BPM={result['bpm']}, Confidence={result['confidence']}%")
        print(f"Total log messages: {len(logs)}")
    else:
        print(f"Test file not found: {test_file}")


def main():
    """Run all examples"""
    print("=" * 70)
    print("BLOND BPM Detector - Advanced Examples")
    print("High-precision beat tracking for electronic music")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        example_name = sys.argv[1]
        
        examples = {
            "basic": example_basic_detection,
            "batch": example_batch_processing,
            "performance": example_performance_testing,
            "genre": example_genre_detection,
            "errors": example_error_handling,
            "correction": example_double_time_correction,
            "logging": example_with_logging,
        }
        
        if example_name in examples:
            examples[example_name]()
        else:
            print(f"Unknown example: {example_name}")
            print(f"Available: {', '.join(examples.keys())}")
    else:
        print("\nUsage: python bpm_advanced_examples.py <example_name>")
        print("\nAvailable examples:")
        print("  basic        - Basic BPM detection")
        print("  batch        - Process multiple files")
        print("  performance  - Test performance on large files")
        print("  genre        - Test genre-specific detection")
        print("  errors       - Error handling examples")
        print("  correction   - Double-time/half-time correction")
        print("  logging      - Detection with logging")


if __name__ == "__main__":
    main()
