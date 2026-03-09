#!/usr/bin/env python3
"""
Track DNA — Unified audio analysis engine for BLOND
Returns a full musical fingerprint as JSON.

Usage: track_dna <audio_file>
"""

import sys
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np

try:
    import librosa
    import librosa.feature
    import librosa.effects
    import librosa.onset
    import scipy.signal
    import scipy.stats
    import soundfile as sf
except ImportError as e:
    print(json.dumps({"success": False, "error": f"Missing library: {e}"}), flush=True)
    sys.exit(0)

# ─── Constants ────────────────────────────────────────────────────────────────

SR = 22050          # sample rate for analysis
WAVEFORM_POINTS = 300
ENERGY_CURVE_POINTS = 64

CAMELOT_WHEEL = {
    "C Major": "8B",  "G Major": "9B",  "D Major": "10B", "A Major": "11B",
    "E Major": "12B", "B Major": "1B",  "F# Major": "2B", "C# Major": "3B",
    "G# Major": "4B", "D# Major": "5B", "A# Major": "6B", "F Major": "7B",
    "A Minor": "8A",  "E Minor": "9A",  "B Minor": "10A", "F# Minor": "11A",
    "C# Minor": "12A","G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A",
    "F Minor": "4A",  "C Minor": "5A",  "G Minor": "6A",  "D Minor": "7A",
}

SECTION_COLORS = {
    "intro": "#3b82f6",
    "buildup": "#eab308",
    "drop": "#ef4444",
    "breakdown": "#22c55e",
    "outro": "#a855f7",
    "verse": "#06b6d4",
    "chorus": "#f97316",
}

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# ─── Audio loading ─────────────────────────────────────────────────────────────

def load_audio(path: str):
    """Load audio file at analysis sample rate."""
    y, sr = librosa.load(path, sr=SR, mono=True)
    return y, sr


# ─── BPM & Rhythm ─────────────────────────────────────────────────────────────

def analyze_rhythm(y, sr):
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)

    # Primary: tempo from autocorrelation of onset envelope
    tempo_acf = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    tempo_candidates = np.sort(tempo_acf.flatten())[::-1]
    primary_bpm = float(np.median(tempo_candidates[:5])) if len(tempo_candidates) >= 5 else float(tempo_candidates[0])

    # Secondary: beat_track (librosa 0.11: onset_envelope kwarg)
    tempo_bt, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr,
                                               start_bpm=primary_bpm, tightness=100,
                                               trim=False)
    bpm = float(np.atleast_1d(tempo_bt)[0])

    # Correct double/half time
    if bpm > 160 and 80 <= bpm / 2 <= 140:
        bpm = bpm / 2
    elif bpm < 80 and 100 <= bpm * 2 <= 160:
        bpm = bpm * 2

    # Beat grid timestamps
    beat_times = librosa.frames_to_time(beats, sr=sr).tolist()

    # Tempo stability: coefficient of variation of inter-beat intervals
    if len(beat_times) > 2:
        ibis = np.diff(beat_times)
        cv = float(np.std(ibis) / (np.mean(ibis) + 1e-9))
        stability = float(np.clip(1.0 - cv * 5, 0.0, 1.0))
    else:
        stability = 0.5

    return {
        "bpm": round(bpm, 2),
        "beat_grid": [round(t, 3) for t in beat_times[:64]],  # cap at 64 beats
        "tempo_stability": round(stability, 3),
    }


# ─── Key detection ─────────────────────────────────────────────────────────────

def analyze_key(y, sr):
    # Use CQT chroma — more accurate for harmonic analysis
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
    chroma_mean = np.mean(chroma, axis=1)
    chroma_mean = chroma_mean / (np.sum(chroma_mean) + 1e-9)

    # Krumhansl-Schmuckler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
                               2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
                               2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

    major_profile = major_profile / major_profile.sum()
    minor_profile = minor_profile / minor_profile.sum()

    best_key, best_score, best_mode = "C", -1, "major"
    for i in range(12):
        rotated = np.roll(chroma_mean, -i)
        maj_corr = float(np.dot(rotated, major_profile))
        min_corr = float(np.dot(rotated, minor_profile))
        if maj_corr > best_score:
            best_score, best_key, best_mode = maj_corr, NOTES[i], "major"
        if min_corr > best_score:
            best_score, best_key, best_mode = min_corr, NOTES[i], "minor"

    mode_str = "Major" if best_mode == "major" else "Minor"
    key_name = f"{best_key} {mode_str}"
    camelot = CAMELOT_WHEEL.get(key_name, "8B")

    return {
        "key": key_name,
        "camelot": camelot,
        "mode": best_mode,
    }


# ─── Energy & Groove ──────────────────────────────────────────────────────────

def analyze_energy_groove(y, sr):
    # RMS energy
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    rms_mean = float(np.mean(rms))

    # Energy score 0-100 using perceptual dB mapping
    # Typical music RMS: -30dB (quiet) to -6dB (loud/mastered)
    rms_db = 20 * np.log10(rms_mean + 1e-9)
    # Map [-35, -6] dB → [0, 100]
    energy_score = int(np.clip((rms_db + 35) / 29 * 100, 0, 100))

    # Loudness proxy (approximate LUFS via RMS in dB)
    rms_db_loudness = float(20 * np.log10(np.mean(rms) + 1e-9))

    # Danceability: combine tempo regularity + onset density + bass ratio
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_rate = float(np.mean(onset_env > np.percentile(onset_env, 75)))

    # Bass energy ratio (low freqs 20-250Hz)
    stft = np.abs(librosa.stft(y))
    freqs = librosa.fft_frequencies(sr=sr)
    bass_mask = freqs < 250
    total_energy = np.sum(stft) + 1e-9
    bass_energy = float(np.sum(stft[bass_mask, :]) / total_energy)

    danceability = float(np.clip(onset_rate * 0.4 + bass_energy * 0.4 + 0.2, 0, 1))

    return {
        "energy": energy_score,
        "danceability": round(danceability, 3),
        "loudness_db": round(rms_db_loudness, 1),
        "_rms": rms,
        "_stft": stft,
        "_freqs": freqs,
        "_bass_energy": bass_energy,
    }


# ─── Spectral / Timbre ────────────────────────────────────────────────────────

def analyze_spectral(y, sr, stft, freqs):
    # Spectral centroid — brightness proxy
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
    centroid_mean = float(np.mean(centroid))
    # Normalize: 0 = dark (< 500Hz), 1 = bright (> 8kHz)
    brightness = float(np.clip((centroid_mean - 500) / 7500, 0, 1))

    # Spectral rolloff
    rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, roll_percent=0.85)[0]
    rolloff_mean = float(np.mean(rolloff))

    # Bass strength (energy in 20-250Hz vs total)
    bass_mask = freqs < 250
    bass_strength = float(np.sum(stft[bass_mask, :]) / (np.sum(stft) + 1e-9))
    # Typical range 0.04-0.25 → scale to 0-1 (map [0.04, 0.25] → [0, 1])
    bass_strength = float(np.clip((bass_strength - 0.04) / 0.21, 0, 1))

    # Zero crossing rate (noisiness / transient density)
    zcr = librosa.feature.zero_crossing_rate(y)[0]
    zcr_mean = float(np.mean(zcr))

    return {
        "brightness": round(brightness, 3),
        "spectral_centroid": round(centroid_mean, 1),
        "spectral_rolloff": round(rolloff_mean, 1),
        "bass_strength": round(bass_strength, 3),
        "zcr": round(zcr_mean, 4),
    }


# ─── Dynamics ─────────────────────────────────────────────────────────────────

def analyze_dynamics(y, sr):
    # Dynamic range: difference between loud and quiet segments
    frame_len = 4096
    hop = 1024
    rms = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop)[0]
    rms_db = 20 * np.log10(rms + 1e-9)

    # DR = difference between 95th and 10th percentile in dB
    dynamic_range = float(np.percentile(rms_db, 95) - np.percentile(rms_db, 10))
    dynamic_range = round(float(np.clip(dynamic_range, 0, 40)), 1)

    # Compression estimate: low DR = heavily compressed
    # DR > 20 = uncompressed, DR < 6 = heavily compressed
    compression = float(np.clip(1.0 - (dynamic_range / 20.0), 0, 1))

    return {
        "dynamic_range": dynamic_range,
        "compression": round(compression, 3),
    }


# ─── Energy Curve ─────────────────────────────────────────────────────────────

def compute_energy_curve(y, sr, n_points=ENERGY_CURVE_POINTS):
    chunk_size = len(y) // n_points
    if chunk_size < 1:
        return [0.0] * n_points
    curve = []
    for i in range(n_points):
        start = i * chunk_size
        end = start + chunk_size
        chunk = y[start:end]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        curve.append(rms)
    # Normalize 0-1
    max_val = max(curve) + 1e-9
    curve = [round(v / max_val, 4) for v in curve]
    return curve


# ─── Waveform ─────────────────────────────────────────────────────────────────

def compute_waveform(y, n_points=WAVEFORM_POINTS):
    chunk_size = max(1, len(y) // n_points)
    waveform = []
    for i in range(n_points):
        start = i * chunk_size
        end = min(start + chunk_size, len(y))
        chunk = y[start:end]
        if len(chunk) == 0:
            waveform.append(0.0)
        else:
            waveform.append(float(np.sqrt(np.mean(chunk ** 2))))
    max_val = max(waveform) + 1e-9
    waveform = [round(v / max_val, 4) for v in waveform]
    return waveform


# ─── Structure Detection ──────────────────────────────────────────────────────

def detect_sections(y, sr, energy_curve, bpm):
    """
    Detect musical sections using energy + spectral flux + novelty curve.
    Returns list of {type, start, end, color}.
    """
    duration = librosa.get_duration(y=y, sr=sr)

    # Novelty / structural segmentation via recurrence matrix
    hop_length = 512
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13, hop_length=hop_length)
    feature_stack = np.vstack([chroma, mfcc])

    # Recurrence matrix → Laplacian segmentation
    R = librosa.segment.recurrence_matrix(feature_stack, mode='affinity',
                                           metric='cosine', k=5, sym=True)
    df = librosa.segment.timelag_filter(scipy.ndimage.median_filter)(R, size=(1, 7))
    Rf = librosa.segment.path_enhance(df, n=15)

    # Novelty curve from Laplacian
    novelty = librosa.segment.recurrence_to_lag(Rf, pad=False)
    novelty_1d = np.mean(novelty, axis=0)
    # Smooth
    novelty_smooth = scipy.ndimage.uniform_filter1d(novelty_1d, size=16)

    # Find peaks (structural boundaries)
    from scipy.signal import find_peaks
    times = librosa.frames_to_time(np.arange(len(novelty_smooth)), sr=sr,
                                    hop_length=hop_length)

    # Adaptive peak detection
    min_dist = max(1, int(SR / hop_length * 8))  # min 8 seconds between boundaries
    peaks, _ = find_peaks(novelty_smooth, distance=min_dist,
                           prominence=np.std(novelty_smooth) * 0.5)

    boundaries = [0.0] + sorted([float(times[p]) for p in peaks if p < len(times)]) + [duration]
    # Remove duplicates and boundaries too close together
    filtered = [boundaries[0]]
    for b in boundaries[1:]:
        if b - filtered[-1] >= 6.0:
            filtered.append(b)
    if filtered[-1] < duration - 2:
        filtered.append(duration)
    boundaries = filtered

    # Classify each segment
    sections = []
    n_segs = len(boundaries) - 1
    energy_curve_arr = np.array(energy_curve)

    for i in range(n_segs):
        seg_start = boundaries[i]
        seg_end = boundaries[i + 1]

        # Map to energy curve
        ec_start = int(seg_start / duration * len(energy_curve_arr))
        ec_end = int(seg_end / duration * len(energy_curve_arr))
        ec_start = min(ec_start, len(energy_curve_arr) - 1)
        ec_end = min(ec_end, len(energy_curve_arr))
        if ec_end <= ec_start:
            ec_end = ec_start + 1

        seg_energy = float(np.mean(energy_curve_arr[ec_start:ec_end]))
        seg_energy_max = float(np.max(energy_curve_arr[ec_start:ec_end]))
        global_energy_mean = float(np.mean(energy_curve_arr))
        global_energy_max = float(np.max(energy_curve_arr))

        # Energy ramp direction
        if ec_end > ec_start + 1:
            trend = float(np.polyfit(np.arange(ec_end - ec_start),
                                     energy_curve_arr[ec_start:ec_end], 1)[0])
        else:
            trend = 0.0

        # Classify based on position + energy + trend
        pos = seg_start / duration

        if i == 0 and seg_energy < global_energy_mean * 0.8:
            label = "intro"
        elif i == n_segs - 1 and seg_energy < global_energy_mean * 0.85:
            label = "outro"
        elif seg_energy_max >= global_energy_max * 0.85:
            label = "drop"
        elif trend > 0.004 and seg_energy < global_energy_mean:
            label = "buildup"
        elif seg_energy < global_energy_mean * 0.75 and i > 0:
            label = "breakdown"
        else:
            label = "drop" if seg_energy >= global_energy_mean else "breakdown"

        sections.append({
            "type": label,
            "start": round(seg_start, 1),
            "end": round(seg_end, 1),
            "color": SECTION_COLORS.get(label, "#6b7280"),
        })

    return sections


# ─── Drop & Breakdown detection ───────────────────────────────────────────────

def detect_drops_breakdowns(sections):
    drops = [s["start"] for s in sections if s["type"] == "drop"]
    breakdowns = [s["start"] for s in sections if s["type"] == "breakdown"]
    return drops, breakdowns


# ─── Mood estimation ──────────────────────────────────────────────────────────

def estimate_mood(bpm, energy, brightness, bass_strength, mode, dynamic_range):
    moods = []

    # Energy-based
    if energy > 70:
        moods.append("energetic")
    elif energy < 35:
        moods.append("atmospheric")

    # Mode + brightness
    if mode == "minor" and brightness < 0.4:
        moods.append("dark")
    elif mode == "minor" and brightness >= 0.4:
        moods.append("melancholic")
    elif mode == "major" and brightness > 0.55:
        moods.append("uplifting")

    # Tempo
    if bpm > 140 and energy > 65:
        moods.append("aggressive")
    elif bpm < 100 and energy < 50:
        moods.append("atmospheric")

    # Bass heavy
    if bass_strength > 0.55:
        moods.append("heavy")

    # Deduplicate, limit to 3
    seen = set()
    result = []
    for m in moods:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result[:3] if result else ["atmospheric"]


# ─── Mix compatibility ────────────────────────────────────────────────────────

def mix_compatibility_score(bpm, camelot, energy):
    """
    A simple numeric score 0-100 indicating how 'mixable' this track is.
    Based on: tempo range, camelot key position, energy level.
    """
    bpm_score = 100 if 120 <= bpm <= 135 else \
                80  if 110 <= bpm <= 145 else \
                60  if 95  <= bpm <= 160 else 40

    # Camelot number (1-12): center (5-8) = more mixable
    try:
        camelot_num = int(camelot[:-1])
        key_score = 100 - abs(camelot_num - 6) * 6
    except Exception:
        key_score = 60

    energy_score = 100 if 50 <= energy <= 80 else \
                   70  if 30 <= energy <= 90 else 40

    return int((bpm_score * 0.4 + key_score * 0.3 + energy_score * 0.3))


# ─── Main analysis ─────────────────────────────────────────────────────────────

def analyze(audio_path: str) -> dict:
    y, sr = load_audio(audio_path)
    duration = librosa.get_duration(y=y, sr=sr)

    # All analysis passes
    rhythm = analyze_rhythm(y, sr)
    key_data = analyze_key(y, sr)
    energy_data = analyze_energy_groove(y, sr)

    # Extract internals for reuse
    stft = energy_data.pop("_stft")
    freqs = energy_data.pop("_freqs")
    rms = energy_data.pop("_rms")
    bass_energy = energy_data.pop("_bass_energy")

    spectral = analyze_spectral(y, sr, stft, freqs)
    dynamics = analyze_dynamics(y, sr)
    energy_curve = compute_energy_curve(y, sr)
    waveform = compute_waveform(y)
    sections = detect_sections(y, sr, energy_curve, rhythm["bpm"])
    drops, breakdowns = detect_drops_breakdowns(sections)
    mood = estimate_mood(
        bpm=rhythm["bpm"],
        energy=energy_data["energy"],
        brightness=spectral["brightness"],
        bass_strength=spectral["bass_strength"],
        mode=key_data["mode"],
        dynamic_range=dynamics["dynamic_range"],
    )
    mix_score = mix_compatibility_score(
        bpm=rhythm["bpm"],
        camelot=key_data["camelot"],
        energy=energy_data["energy"],
    )

    return {
        "success": True,
        "duration": round(duration, 2),

        # Rhythm
        "bpm": rhythm["bpm"],
        "beat_grid": rhythm["beat_grid"],
        "tempo_stability": rhythm["tempo_stability"],

        # Tonality
        "key": key_data["key"],
        "camelot": key_data["camelot"],
        "mode": key_data["mode"],

        # Energy & Groove
        "energy": energy_data["energy"],
        "danceability": energy_data["danceability"],
        "loudness_db": energy_data["loudness_db"],

        # Timbre
        "brightness": spectral["brightness"],
        "spectral_centroid": spectral["spectral_centroid"],
        "spectral_rolloff": spectral["spectral_rolloff"],
        "bass_strength": spectral["bass_strength"],

        # Dynamics
        "dynamic_range": dynamics["dynamic_range"],
        "compression": dynamics["compression"],

        # Structure
        "sections": sections,
        "drops": [round(d, 1) for d in drops],
        "breakdowns": [round(b, 1) for b in breakdowns],

        # Visualization
        "waveform": waveform,
        "energy_curve": energy_curve,

        # Mood
        "mood": mood,

        # DJ
        "mix_compatibility": mix_score,
    }


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: track_dna <audio_file>"
        }), flush=True)
        sys.exit(0)

    audio_path = sys.argv[1]

    import os
    if not os.path.exists(audio_path):
        print(json.dumps({
            "success": False,
            "error": f"File not found: {audio_path}"
        }), flush=True)
        sys.exit(0)

    try:
        result = analyze(audio_path)
        print(json.dumps(result, allow_nan=False), flush=True)
    except Exception as e:
        import traceback
        print(json.dumps({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
