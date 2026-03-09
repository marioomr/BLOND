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
    "bridge": "#06b6d4",
    "verse": "#f97316",
}

NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


# ─── Logging helpers ──────────────────────────────────────────────────────────

def log(msg: str):
    """Write a timestamped log line to stderr (never to stdout)."""
    print(f"[track_dna] {msg}", file=sys.stderr, flush=True)

def progress(pct: int, step: str = ""):
    """Emit a machine-readable progress line to stderr."""
    line = f"PROGRESS:{pct}"
    if step:
        line += f" {step}"
    print(line, file=sys.stderr, flush=True)


# ─── Audio loading ─────────────────────────────────────────────────────────────

def load_audio(path: str):
    """Load audio file at analysis sample rate."""
    log(f"Loading audio: {path}")
    y, sr = librosa.load(path, sr=SR, mono=True)
    dur = len(y) / sr
    log(f"Loaded {dur:.1f}s at {sr}Hz")
    return y, sr


# ─── BPM & Rhythm ─────────────────────────────────────────────────────────────

# Musical tempo ranges: most EDM sits 60–200 BPM.
# When an estimator returns half/double time we snap to the most common range.
_TARGET_RANGE = (80, 175)  # preferred BPM window for EDM / pop

def _snap_to_musical_tempo(bpm: float, candidates: list = None) -> float:
    """
    Given a raw BPM estimate (may be half or double), return the musically
    correct value by:
    1. Preferring the value (or its ×2 / ÷2) that falls inside _TARGET_RANGE.
    2. If candidates are provided, picking the candidate closest to the winner.
    3. Always returning the value closest to the median of all candidates if
       they agree within ±5 BPM, otherwise falling back to the corrected value.
    """
    lo, hi = _TARGET_RANGE

    def in_range(v):
        return lo <= v <= hi

    # Build a list of octave candidates for this estimate
    octaves = [bpm * 0.5, bpm, bpm * 2.0]
    # Also include ×0.75 and ×1.5 for swing/half-step corrections
    octaves += [bpm * 0.75, bpm * 1.5]

    # Prefer candidates inside target range
    valid = [v for v in octaves if in_range(v)]
    if valid:
        # Pick the one closest to 120 BPM (musical centre of gravity)
        best = min(valid, key=lambda v: abs(v - 120))
    else:
        # Outside range entirely — pick closest octave to 120
        best = min(octaves, key=lambda v: abs(v - 120))

    return best


def _weighted_median(values, weights):
    """Compute a weighted median from a list of (value, weight) pairs."""
    pairs = sorted(zip(values, weights), key=lambda x: x[0])
    total = sum(w for _, w in pairs)
    cumsum = 0.0
    for v, w in pairs:
        cumsum += w
        if cumsum >= total / 2:
            return v
    return pairs[-1][0]


def analyze_rhythm(y, sr, audio_path: str = None):
    """
    High-precision BPM estimation using an Essentia multi-method ensemble
    with librosa as fallback.  Returns an integer BPM, beat grid, and
    tempo stability score.

    Strategy
    --------
    1. Essentia RhythmExtractor2013 (multifeature)  — weight 3, confidence-scaled
    2. Essentia RhythmExtractor2013 (degara)        — weight 2
    3. Essentia PercivalBpmEstimator                — weight 2
    4. librosa beat_track (tightness=100)           — weight 1  (always runs)

    All four estimates are snapped to musical tempo range, then combined via
    weighted median.  The result is rounded to the nearest integer.
    """
    bpm_votes  = []   # (bpm_value, weight)
    beat_ticks = []   # best tick array from Essentia for beat_grid

    # ── 1–3. Essentia (44100 Hz required) ──────────────────────────────────
    if audio_path:
        try:
            import essentia
            import essentia.standard as es

            log("Loading 44100Hz audio for Essentia BPM...")
            loader = es.MonoLoader(filename=audio_path, sampleRate=44100)
            audio44 = loader()

            # --- Method 1: RhythmExtractor2013 multifeature (best overall) ---
            try:
                rex_mf = es.RhythmExtractor2013(method="multifeature",
                                                 minTempo=60, maxTempo=200)
                bpm_mf, ticks_mf, conf_mf, ests_mf, _ = rex_mf(audio44)
                bpm_mf_snapped = _snap_to_musical_tempo(float(bpm_mf))
                # Weight boosted by confidence (0–5 typical range → scale to 1–4)
                weight_mf = 2.0 + min(float(conf_mf) / 2.0, 2.0)
                bpm_votes.append((bpm_mf_snapped, weight_mf))
                if len(ticks_mf) > 4:
                    beat_ticks = list(ticks_mf)
                log(f"  Essentia multifeature: {bpm_mf:.2f} → {bpm_mf_snapped:.1f} "
                    f"(conf={conf_mf:.3f}, w={weight_mf:.1f})")
            except Exception as e:
                log(f"  Essentia multifeature failed: {e}")

            # --- Method 2: RhythmExtractor2013 degara ---
            try:
                rex_dg = es.RhythmExtractor2013(method="degara",
                                                 minTempo=60, maxTempo=200)
                bpm_dg, ticks_dg, _, _, _ = rex_dg(audio44)
                bpm_dg_snapped = _snap_to_musical_tempo(float(bpm_dg))
                bpm_votes.append((bpm_dg_snapped, 2.0))
                if not beat_ticks and len(ticks_dg) > 4:
                    beat_ticks = list(ticks_dg)
                log(f"  Essentia degara: {bpm_dg:.2f} → {bpm_dg_snapped:.1f}")
            except Exception as e:
                log(f"  Essentia degara failed: {e}")

            # --- Method 3: PercivalBpmEstimator ---
            try:
                percival = es.PercivalBpmEstimator(sampleRate=44100,
                                                    minBPM=60, maxBPM=200)
                bpm_pc = percival(audio44)
                bpm_pc_snapped = _snap_to_musical_tempo(float(bpm_pc))
                bpm_votes.append((bpm_pc_snapped, 2.0))
                log(f"  Essentia Percival: {bpm_pc:.2f} → {bpm_pc_snapped:.1f}")
            except Exception as e:
                log(f"  Essentia Percival failed: {e}")

        except ImportError:
            log("  Essentia not available, using librosa only")
        except Exception as e:
            log(f"  Essentia load failed: {e}")

    # ── 4. librosa fallback / additional vote ──────────────────────────────
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, aggregate=np.median)

    # Get librosa tempo candidates and pick the strongest
    tempo_acf = librosa.feature.tempo(onset_envelope=onset_env, sr=sr, aggregate=None)
    tempo_candidates = np.sort(tempo_acf.flatten())[::-1]
    bpm_lib_raw = float(np.median(tempo_candidates[:5])) \
                  if len(tempo_candidates) >= 5 else float(tempo_candidates[0])

    # Reinforce with beat_track
    tempo_bt, beats = librosa.beat.beat_track(
        onset_envelope=onset_env, sr=sr,
        start_bpm=bpm_lib_raw, tightness=100, trim=False
    )
    bpm_lib = float(np.atleast_1d(tempo_bt)[0])
    bpm_lib_snapped = _snap_to_musical_tempo(bpm_lib)
    bpm_votes.append((bpm_lib_snapped, 1.0))
    log(f"  librosa: {bpm_lib:.2f} → {bpm_lib_snapped:.1f}")

    # ── Ensemble: weighted median of all votes ─────────────────────────────
    values  = [v for v, _ in bpm_votes]
    weights = [w for _, w in bpm_votes]
    raw_bpm = _weighted_median(values, weights)

    # Final snap: in case weighted median drifted slightly off-range
    raw_bpm = _snap_to_musical_tempo(raw_bpm)

    # Round to nearest integer
    bpm_final = int(round(raw_bpm))
    log(f"  Ensemble result: {raw_bpm:.2f} → {bpm_final} BPM")

    # ── Beat grid ──────────────────────────────────────────────────────────
    if beat_ticks:
        beat_times = [round(float(t), 3) for t in beat_ticks[:64]]
    else:
        beat_times = [round(float(t), 3)
                      for t in librosa.frames_to_time(beats, sr=sr).tolist()[:64]]

    # ── Tempo stability: CoV of inter-beat intervals ───────────────────────
    if len(beat_times) > 2:
        ibis = np.diff(beat_times)
        cv = float(np.std(ibis) / (np.mean(ibis) + 1e-9))
        stability = float(np.clip(1.0 - cv * 5, 0.0, 1.0))
    else:
        stability = 0.5

    return {
        "bpm": bpm_final,
        "beat_grid": beat_times,
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
    Detect musical sections using a multi-feature novelty approach.
    Features: chroma_cqt + mfcc + rms energy. Boundaries via Laplacian
    spectral decomposition. Classification with 6-label system:
    intro / buildup / drop / breakdown / outro / bridge
    """
    from scipy.signal import find_peaks

    duration = librosa.get_duration(y=y, sr=sr)
    hop_length = 512
    n_frames = 1 + len(y) // hop_length

    # ── Feature extraction ──────────────────────────────────────────────
    # Chroma (harmonic content)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length,
                                         bins_per_octave=36)
    # MFCC (timbral texture)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop_length)
    mfcc = librosa.util.normalize(mfcc, axis=1)
    # RMS energy per frame
    rms_frames = librosa.feature.rms(y=y, frame_length=2048,
                                      hop_length=hop_length)[0]
    rms_norm = rms_frames / (np.max(rms_frames) + 1e-9)
    # Spectral contrast (band energy ratios)
    contrast = librosa.feature.spectral_contrast(y=y, sr=sr,
                                                   hop_length=hop_length)
    contrast = librosa.util.normalize(contrast, axis=1)

    # Stack all features, weight chroma higher
    feature_stack = np.vstack([
        chroma * 2.0,
        mfcc,
        contrast,
        rms_norm[np.newaxis, :] * 3.0,
    ])
    # Align frame counts
    min_frames = min(feature_stack.shape[1], len(rms_frames))
    feature_stack = feature_stack[:, :min_frames]

    # ── Novelty curve via recurrence matrix ─────────────────────────────
    R = librosa.segment.recurrence_matrix(
        feature_stack, mode='affinity', metric='cosine', k=7, sym=True
    )
    # Timelag filter + path enhancement
    R_lag = librosa.segment.timelag_filter(scipy.ndimage.median_filter)(
        R, size=(1, 9)
    )
    R_enh = librosa.segment.path_enhance(R_lag, n=15)

    # Lag representation → novelty
    lag = librosa.segment.recurrence_to_lag(R_enh, pad=False)
    novelty_1d = np.mean(lag, axis=0)[:min_frames]

    # Combine with RMS-based novelty (onset of energy changes)
    rms_diff = np.abs(np.diff(rms_frames[:min_frames], prepend=rms_frames[0]))
    rms_novelty = scipy.ndimage.uniform_filter1d(rms_diff, size=32)
    rms_novelty = rms_novelty / (np.max(rms_novelty) + 1e-9)

    # Fused novelty
    novelty_smooth = scipy.ndimage.uniform_filter1d(novelty_1d, size=20)
    novelty_smooth = novelty_smooth / (np.max(novelty_smooth) + 1e-9)
    fused = novelty_smooth * 0.7 + rms_novelty * 0.3
    fused = scipy.ndimage.uniform_filter1d(fused, size=12)

    # Frame times
    frame_times = librosa.frames_to_time(
        np.arange(min_frames), sr=sr, hop_length=hop_length
    )

    # ── Boundary detection ───────────────────────────────────────────────
    # Min distance: ~8 bars at given BPM (at least 8s)
    beats_per_8bars = 32  # 8 bars × 4 beats
    secs_per_8bars = beats_per_8bars / max(bpm, 60) * 60
    min_dist_secs = max(8.0, secs_per_8bars)
    min_dist_frames = max(1, int(min_dist_secs * sr / hop_length))

    peaks, props = find_peaks(
        fused,
        distance=min_dist_frames,
        prominence=np.std(fused) * 0.4,
        height=np.mean(fused) * 0.5,
    )

    raw_boundaries = [float(frame_times[p]) for p in peaks if p < len(frame_times)]

    # Snap boundaries to nearest beat (within ±1 beat)
    beat_period = 60.0 / max(bpm, 60)
    snapped = []
    for b in raw_boundaries:
        # Round to nearest beat_period
        n_beats = round(b / beat_period)
        snapped_b = n_beats * beat_period
        # Clamp to duration
        snapped_b = max(0.0, min(snapped_b, duration - 2.0))
        snapped.append(snapped_b)

    boundaries = [0.0] + sorted(set(round(b, 1) for b in snapped)) + [duration]

    # Merge too-close boundaries
    merged = [boundaries[0]]
    for b in boundaries[1:]:
        if b - merged[-1] >= 6.0:
            merged.append(b)
    if merged[-1] < duration - 2.0:
        merged.append(round(duration, 1))
    boundaries = merged

    log(f"Found {len(boundaries)-1} sections from {len(peaks)} novelty peaks")

    # ── Per-segment feature aggregation ─────────────────────────────────
    # High-res RMS curve (same frames)
    rms_curve = rms_frames[:min_frames]
    global_rms_mean = float(np.mean(rms_curve))
    global_rms_max = float(np.max(rms_curve))
    global_rms_p75 = float(np.percentile(rms_curve, 75))
    global_rms_p25 = float(np.percentile(rms_curve, 25))

    n_segs = len(boundaries) - 1
    seg_features = []
    for i in range(n_segs):
        t0, t1 = boundaries[i], boundaries[i + 1]
        f0 = int(t0 * sr / hop_length)
        f1 = min(int(t1 * sr / hop_length), min_frames)
        if f1 <= f0:
            f1 = f0 + 1

        seg_rms = rms_curve[f0:f1]
        seg_chroma = chroma[:, f0:f1]
        seg_mfcc_data = mfcc[:, f0:f1]

        rms_mean = float(np.mean(seg_rms))
        rms_max = float(np.max(seg_rms))
        rms_std = float(np.std(seg_rms))

        # Trend: positive = energy rising, negative = falling
        if len(seg_rms) > 2:
            xs = np.linspace(0, 1, len(seg_rms))
            trend = float(np.polyfit(xs, seg_rms, 1)[0])
        else:
            trend = 0.0

        # Harmonic stability (chroma entropy — low = stable key = verse/drop)
        chroma_mean = np.mean(seg_chroma, axis=1)
        chroma_mean /= (chroma_mean.sum() + 1e-9)
        chroma_entropy = float(-np.sum(chroma_mean * np.log2(chroma_mean + 1e-9)))

        # Spectral flatness via MFCC variance (high = noisy/percussion)
        mfcc_var = float(np.mean(np.var(seg_mfcc_data, axis=1)))

        seg_features.append({
            "idx": i, "t0": t0, "t1": t1,
            "rms_mean": rms_mean, "rms_max": rms_max, "rms_std": rms_std,
            "trend": trend,
            "chroma_entropy": chroma_entropy,
            "mfcc_var": mfcc_var,
            "dur": t1 - t0,
        })

    # ── Classification ───────────────────────────────────────────────────
    # Thresholds relative to globals
    high_thresh = global_rms_p75
    low_thresh  = global_rms_p25
    mid_thresh  = global_rms_mean

    sections = []
    for sf in seg_features:
        i = sf["idx"]
        t0, t1 = sf["t0"], sf["t1"]
        rm = sf["rms_mean"]
        rx = sf["rms_max"]
        trend = sf["trend"]
        entropy = sf["chroma_entropy"]
        pos = t0 / duration  # 0 = start, 1 = end

        # ── Rule-based classification with priority order ────────────────
        label = None

        # INTRO: first segment(s), energy low/medium, rising or flat
        if i == 0 and rm <= mid_thresh * 1.1:
            label = "intro"

        # OUTRO: last segment, energy declining or low
        elif i == n_segs - 1 and (rm < mid_thresh or trend < -0.002):
            label = "outro"

        # BUILDUP: energy rising strongly, below drop threshold
        elif trend > 0.003 and rm < high_thresh and rm > low_thresh:
            label = "buildup"

        # DROP: energy at/above 75th pct, or is the highest in context
        elif rx >= high_thresh or rm >= global_rms_p75 * 0.9:
            label = "drop"

        # BREAKDOWN: energy clearly low, not at edges
        elif rm <= low_thresh * 1.2 and i > 0 and i < n_segs - 1:
            label = "breakdown"

        # BRIDGE: medium energy, stable harmony (low entropy), not a drop
        elif entropy < 3.0 and low_thresh < rm < high_thresh:
            label = "bridge"

        # Fallback
        else:
            label = "drop" if rm >= mid_thresh else "breakdown"

        sections.append({
            "type": label,
            "start": round(t0, 1),
            "end": round(t1, 1),
            "color": SECTION_COLORS.get(label, "#6b7280"),
        })

    # ── Post-process: merge same-type consecutive short segments ─────────
    merged_sections = []
    for sec in sections:
        if (merged_sections
                and merged_sections[-1]["type"] == sec["type"]
                and sec["start"] - merged_sections[-1]["end"] < 0.5
                and merged_sections[-1]["end"] - merged_sections[-1]["start"] < 24):
            merged_sections[-1]["end"] = sec["end"]
        else:
            merged_sections.append(dict(sec))

    log(f"Sections after merge: {[s['type'] for s in merged_sections]}")
    return merged_sections


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
    progress(5, "Loading audio")
    y, sr = load_audio(audio_path)
    duration = librosa.get_duration(y=y, sr=sr)

    progress(15, "Analyzing rhythm & BPM")
    rhythm = analyze_rhythm(y, sr, audio_path=audio_path)
    log(f"BPM={rhythm['bpm']} stability={rhythm['tempo_stability']}")

    progress(30, "Detecting musical key")
    key_data = analyze_key(y, sr)
    log(f"Key={key_data['key']} camelot={key_data['camelot']}")

    progress(45, "Analyzing energy & groove")
    energy_data = analyze_energy_groove(y, sr)

    # Extract internals for reuse
    stft = energy_data.pop("_stft")
    freqs = energy_data.pop("_freqs")
    rms = energy_data.pop("_rms")
    bass_energy = energy_data.pop("_bass_energy")

    progress(55, "Spectral analysis")
    spectral = analyze_spectral(y, sr, stft, freqs)

    progress(60, "Dynamics analysis")
    dynamics = analyze_dynamics(y, sr)

    progress(65, "Computing waveform")
    energy_curve = compute_energy_curve(y, sr)
    waveform = compute_waveform(y)

    progress(70, "Detecting sections")
    sections = detect_sections(y, sr, energy_curve, rhythm["bpm"])
    drops, breakdowns = detect_drops_breakdowns(sections)

    progress(90, "Estimating mood")
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

    progress(98, "Building result")
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
        progress(100, "Done")
        print(json.dumps(result, allow_nan=False), flush=True)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        log(f"ERROR: {e}\n{tb}")
        print(json.dumps({
            "success": False,
            "error": str(e),
            "traceback": tb
        }), flush=True)

    sys.exit(0)


if __name__ == "__main__":
    main()
