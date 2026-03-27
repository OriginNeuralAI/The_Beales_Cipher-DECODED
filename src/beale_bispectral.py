"""
Beale Ciphers — Phase 6 Task 2: Bispectral & Higher-Order Spectral Analysis

Existing spectral analysis captures only pairwise (2nd-order) correlations.
Bispectral analysis reveals 3rd-order non-linear correlations — patterns
invisible in the power spectrum that distinguish fabricated from genuine
sequences.

Key prediction: B2 has higher spectral entropy, more uniform phases, and lower
bicoherence than B1/B3.

Implements:
1. power_spectrum() — FFT-based power spectral density
2. bispectrum() — B(f1, f2) = X(f1) * X(f2) * conj(X(f1+f2))
3. bicoherence() — Normalized bispectrum, detects phase coupling
4. trispectrum_slice() — 4th-order spectral slice
5. spectral_entropy() — Shannon entropy of PSD
6. phase_randomness_test() — Rayleigh test for phase uniformity
7. cepstral_analysis() — Inverse FFT of log PSD (periodicity detection)
8. multitaper_spectrum() — Slepian taper-based PSD (reduced variance)
9. spectral_forensic_battery() — Full diagnostic suite
10. compare_all_ciphers() — Side-by-side comparison

Usage: python beale_bispectral.py
"""

import numpy as np
from typing import Dict, Tuple, Any, List
import json

from beale_data import B1_CIPHER, B2_CIPHER, B3_CIPHER


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ===========================================================================
# 1. Power Spectrum
# ===========================================================================

def power_spectrum(cipher: List[int], normalize: bool = True) -> np.ndarray:
    """
    FFT of centered cipher sequence, return PSD array.
    
    Args:
        cipher: List of cipher numbers
        normalize: If True, normalize to sum to 1
    
    Returns:
        PSD array (one-sided spectrum)
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()  # Center the signal
    
    n = len(arr)
    fft_result = np.fft.fft(arr)
    psd = np.abs(fft_result) ** 2
    
    # One-sided spectrum (positive frequencies only)
    n_freq = n // 2 + 1
    psd_onesided = psd[:n_freq]
    psd_onesided[1:-1] *= 2  # Double non-DC/Nyquist bins
    
    if normalize:
        total = psd_onesided.sum()
        if total > 0:
            psd_onesided = psd_onesided / total
    
    return psd_onesided


# ===========================================================================
# 2. Bispectrum
# ===========================================================================

def bispectrum(cipher: List[int], n_freq: int = 64) -> np.ndarray:
    """
    B(f1, f2) = X(f1) * X(f2) * conj(X(f1+f2)).
    Returns 2D complex bispectrum matrix.
    
    Detects phase coupling between frequency components.
    Non-zero bispectrum indicates quadratic phase coupling.
    
    Args:
        cipher: List of cipher numbers
        n_freq: Number of frequency bins to analyze
    
    Returns:
        Complex bispectrum matrix of shape (n_freq, n_freq)
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    
    n = len(arr)
    X = np.fft.fft(arr, n=n*2)[:n]  # Zero-padded FFT
    
    # Build bispectrum for frequency pairs (f1, f2)
    B = np.zeros((n_freq, n_freq), dtype=complex)
    
    for f1 in range(n_freq):
        for f2 in range(n_freq):
            f3 = f1 + f2
            if f3 < n:
                B[f1, f2] = X[f1] * X[f2] * np.conj(X[f3])
    
    return B


def bispectrum_magnitude(cipher: List[int], n_freq: int = 64) -> np.ndarray:
    """Return magnitude of bispectrum."""
    return np.abs(bispectrum(cipher, n_freq))


# ===========================================================================
# 3. Bicoherence
# ===========================================================================

def bicoherence(cipher: List[int], n_freq: int = 64) -> np.ndarray:
    """
    Normalized bispectrum b²(f1,f2) = |B(f1,f2)|² / (P(f1)*P(f2)*P(f1+f2)).
    
    Near 1 = strong non-linear coupling (fabrication signal)
    Near 0 = independent phases (genuine/random)
    
    Returns:
        Bicoherence matrix of shape (n_freq, n_freq), values in [0, 1]
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    
    n = len(arr)
    X = np.fft.fft(arr, n=n*2)[:n]
    P = np.abs(X) ** 2  # Power at each frequency
    
    # Bispectrum
    B = bispectrum(cipher, n_freq)
    
    # Bicoherence normalization
    bc = np.zeros((n_freq, n_freq))
    
    for f1 in range(n_freq):
        for f2 in range(n_freq):
            f3 = f1 + f2
            if f3 < n:
                denom = P[f1] * P[f2] * P[f3]
                if denom > 0:
                    bc[f1, f2] = np.abs(B[f1, f2]) ** 2 / denom
    
    return bc


def mean_bicoherence(cipher: List[int], n_freq: int = 64) -> float:
    """Average bicoherence value (scalar summary). DEPRECATED: single-realization, saturates to ~1."""
    bc = bicoherence(cipher, n_freq)
    # Only count valid region (f1 + f2 < n_freq)
    valid = np.triu(bc)
    return float(np.mean(valid[valid > 0])) if np.any(valid > 0) else 0.0


def max_bicoherence(cipher: List[int], n_freq: int = 64) -> float:
    """Maximum bicoherence value. DEPRECATED: single-realization, saturates to ~1."""
    bc = bicoherence(cipher, n_freq)
    return float(np.max(bc))


# ===========================================================================
# 3b. Welch-Style Bicoherence (Phase 7 Fix)
# ===========================================================================

def bicoherence_welch(cipher: List[int], seg_len: int = 128,
                      overlap: float = 0.5, n_freq: int = 32) -> np.ndarray:
    """
    Segment-averaged bicoherence (Welch-style).

    Single-realization bicoherence always saturates to ~1.0 because the
    bispectrum phase is deterministic for a single FFT. Meaningful bicoherence
    requires averaging over multiple segments, analogous to Welch PSD.

    b²(f1,f2) = |<B(f1,f2)>|² / (<|X(f1)*X(f2)|²> * <|X(f1+f2)|²>)

    Args:
        cipher: List of cipher numbers
        seg_len: Segment length (shorter = more segments but coarser freq resolution)
        overlap: Fractional overlap between segments (0.0 to 0.75)
        n_freq: Number of frequency bins in output

    Returns:
        Bicoherence matrix of shape (n_freq, n_freq), values in [0, 1]
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    n = len(arr)

    # Compute segment start positions
    step = max(1, int(seg_len * (1 - overlap)))
    starts = list(range(0, n - seg_len + 1, step))
    n_segs = len(starts)

    if n_segs < 2:
        # Not enough data for segment averaging; fall back to single-realization
        # but clip to avoid saturation
        bc = bicoherence(cipher, n_freq)
        return np.clip(bc, 0, 1)

    # Accumulators
    bispectrum_sum = np.zeros((n_freq, n_freq), dtype=complex)  # <B(f1,f2)>
    denom_a_sum = np.zeros((n_freq, n_freq))  # <|X(f1)*X(f2)|²>
    denom_b_sum = np.zeros((n_freq, n_freq))  # <|X(f1+f2)|²>

    for start in starts:
        seg = arr[start:start + seg_len]
        seg = seg - seg.mean()  # Re-center each segment

        # FFT of segment
        X = np.fft.fft(seg)

        # Build segment bispectrum and denominator terms
        for f1 in range(n_freq):
            for f2 in range(n_freq):
                f3 = f1 + f2
                if f3 < seg_len:
                    B_val = X[f1] * X[f2] * np.conj(X[f3])
                    bispectrum_sum[f1, f2] += B_val
                    denom_a_sum[f1, f2] += (np.abs(X[f1]) * np.abs(X[f2])) ** 2
                    denom_b_sum[f1, f2] += np.abs(X[f3]) ** 2

    # Normalize: b²(f1,f2) = |<B>|² / (<|X1*X2|²> * <|X3|²>)
    bc = np.zeros((n_freq, n_freq))
    for f1 in range(n_freq):
        for f2 in range(n_freq):
            num = np.abs(bispectrum_sum[f1, f2]) ** 2
            denom = denom_a_sum[f1, f2] * denom_b_sum[f1, f2]
            if denom > 0:
                bc[f1, f2] = num / denom

    return np.clip(bc, 0, 1)


def mean_bicoherence_welch(cipher: List[int], seg_len: int = 128,
                           overlap: float = 0.5, n_freq: int = 32) -> float:
    """Scalar summary of Welch-averaged bicoherence."""
    bc = bicoherence_welch(cipher, seg_len, overlap, n_freq)
    # Only count valid triangular region (f1 + f2 < n_freq)
    valid_mask = np.zeros_like(bc, dtype=bool)
    for f1 in range(n_freq):
        for f2 in range(n_freq - f1):
            valid_mask[f1, f2] = True
    valid = bc[valid_mask]
    return float(np.mean(valid)) if len(valid) > 0 else 0.0


def max_bicoherence_welch(cipher: List[int], seg_len: int = 128,
                          overlap: float = 0.5, n_freq: int = 32) -> float:
    """Maximum Welch-averaged bicoherence value."""
    bc = bicoherence_welch(cipher, seg_len, overlap, n_freq)
    return float(np.max(bc))


# ===========================================================================
# 4. Trispectrum Slice
# ===========================================================================

def trispectrum_slice(cipher: List[int], f_fixed: int = 1, n_freq: int = 32) -> np.ndarray:
    """
    3rd-order spectral slice T(f1, f2 | f_fixed).
    One order higher than bispectrum.
    
    T(f1, f2, f3) = X(f1) * X(f2) * X(f3) * conj(X(f1+f2+f3))
    
    We fix f3 = f_fixed and compute slice over (f1, f2).
    
    Args:
        cipher: List of cipher numbers
        f_fixed: Fixed frequency for the slice
        n_freq: Number of frequency bins
    
    Returns:
        Complex trispectrum slice of shape (n_freq, n_freq)
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    
    n = len(arr)
    X = np.fft.fft(arr, n=n*2)[:n]
    
    T = np.zeros((n_freq, n_freq), dtype=complex)
    
    for f1 in range(n_freq):
        for f2 in range(n_freq):
            f4 = f1 + f2 + f_fixed
            if f4 < n:
                T[f1, f2] = X[f1] * X[f2] * X[f_fixed] * np.conj(X[f4])
    
    return T


def trispectrum_magnitude(cipher: List[int], f_fixed: int = 1, n_freq: int = 32) -> np.ndarray:
    """Return magnitude of trispectrum slice."""
    return np.abs(trispectrum_slice(cipher, f_fixed, n_freq))


# ===========================================================================
# 5. Spectral Entropy
# ===========================================================================

def spectral_entropy(cipher: List[int]) -> float:
    """
    Shannon entropy of normalized PSD.
    
    Low entropy = concentrated/periodic (fabrication signal)
    High entropy = broadband (genuine/random)
    
    For a length-n sequence, max entropy is log2(n/2).
    """
    psd = power_spectrum(cipher, normalize=True)
    
    # Remove zeros to avoid log(0)
    psd_nonzero = psd[psd > 0]
    
    if len(psd_nonzero) == 0:
        return 0.0
    
    entropy = -np.sum(psd_nonzero * np.log2(psd_nonzero))
    return float(entropy)


def normalized_spectral_entropy(cipher: List[int]) -> float:
    """
    Spectral entropy normalized to [0, 1].
    1 = uniform (white noise), 0 = all power in one bin.
    """
    psd = power_spectrum(cipher, normalize=True)
    n_bins = len(psd)
    
    if n_bins <= 1:
        return 0.0
    
    max_entropy = np.log2(n_bins)
    actual_entropy = spectral_entropy(cipher)
    
    return float(actual_entropy / max_entropy) if max_entropy > 0 else 0.0


# ===========================================================================
# 6. Phase Randomness Test
# ===========================================================================

def phase_randomness_test(cipher: List[int], n_bootstrap: int = 1000) -> Dict[str, Any]:
    """
    Test DFT phase uniformity on [0, 2π] via Rayleigh test.
    
    Genuine = uniform phases
    Fabricated = phase clustering
    
    The Rayleigh test detects non-uniformity in circular data.
    Under null (uniform phases), test statistic Z ~ χ²(2).
    
    Args:
        cipher: List of cipher numbers
        n_bootstrap: Number of bootstrap samples for p-value
    
    Returns:
        Dict with phases, Rayleigh statistic, p-value, uniformity assessment
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    
    X = np.fft.fft(arr)
    phases = np.angle(X)
    
    # Only use positive frequencies (skip DC)
    n = len(phases)
    positive_phases = phases[1:n//2]
    n_phases = len(positive_phases)
    
    # Rayleigh test statistic
    # R² = (Σcos(θ))² + (Σsin(θ))²
    cos_sum = np.sum(np.cos(positive_phases))
    sin_sum = np.sum(np.sin(positive_phases))
    R = np.sqrt(cos_sum**2 + sin_sum**2)
    
    # Normalized: R_bar = R / n
    R_bar = R / n_phases if n_phases > 0 else 0
    
    # Rayleigh Z statistic: Z = n * R_bar²
    Z = n_phases * R_bar**2
    
    # Under null (uniform), 2Z ~ χ²(2)
    # P(Z > z) ≈ exp(-z) for large n
    p_value = np.exp(-Z) if Z < 700 else 0.0  # Avoid overflow
    
    # Bootstrap for more accurate p-value
    bootstrap_z = []
    rng = np.random.default_rng(42)
    for _ in range(n_bootstrap):
        random_phases = rng.uniform(0, 2*np.pi, n_phases)
        cos_b = np.sum(np.cos(random_phases))
        sin_b = np.sum(np.sin(random_phases))
        R_b = np.sqrt(cos_b**2 + sin_b**2) / n_phases
        Z_b = n_phases * R_b**2
        bootstrap_z.append(Z_b)
    
    bootstrap_p = np.mean(np.array(bootstrap_z) >= Z)
    
    # Circular mean and variance
    mean_angle = np.arctan2(sin_sum, cos_sum)
    circular_variance = 1 - R_bar
    
    return {
        'n_phases': n_phases,
        'rayleigh_R': float(R),
        'rayleigh_R_bar': float(R_bar),
        'rayleigh_Z': float(Z),
        'p_value_analytic': float(p_value),
        'p_value_bootstrap': float(bootstrap_p),
        'circular_mean': float(mean_angle),
        'circular_variance': float(circular_variance),
        'uniform': bootstrap_p > 0.05,  # Fail to reject uniformity
        'phase_coupling': bootstrap_p < 0.01,  # Strong evidence of coupling
    }


# ===========================================================================
# 7. Cepstral Analysis
# ===========================================================================

def cepstral_analysis(cipher: List[int]) -> Dict[str, Any]:
    """
    Inverse FFT of log PSD.
    Detects periodicities in the spectral domain.
    
    Page-boundary effects in Ward's scanning would create periodic
    peaks in the cepstrum.
    
    Returns:
        Dict with cepstrum, peak locations, peak magnitudes
    """
    psd = power_spectrum(cipher, normalize=False)
    
    # Log power spectrum (add small epsilon to avoid log(0))
    log_psd = np.log(psd + 1e-10)
    
    # Cepstrum = inverse FFT of log PSD
    cepstrum = np.real(np.fft.ifft(log_psd))
    
    # Find peaks (local maxima after the first few bins)
    n = len(cepstrum)
    half = n // 2
    cepstrum_half = cepstrum[:half]  # Only positive quefrencies
    
    # Find peaks: points higher than neighbors
    peaks = []
    for i in range(2, len(cepstrum_half) - 1):
        if cepstrum_half[i] > cepstrum_half[i-1] and cepstrum_half[i] > cepstrum_half[i+1]:
            if cepstrum_half[i] > np.mean(cepstrum_half) + np.std(cepstrum_half):
                peaks.append((i, float(cepstrum_half[i])))
    
    # Sort by magnitude
    peaks.sort(key=lambda x: x[1], reverse=True)
    
    # Check for page-boundary periodicity (325 words per page)
    # Quefrency = period in original sequence
    page_period = 325
    page_quefrency = page_period
    
    page_signal = 0.0
    if page_quefrency < len(cepstrum_half):
        # Check neighborhood around expected page quefrency
        window = 20
        start = max(0, page_quefrency - window)
        end = min(len(cepstrum_half), page_quefrency + window)
        page_signal = float(np.max(cepstrum_half[start:end]))
    
    return {
        'cepstrum': cepstrum_half.tolist(),
        'peaks': peaks[:10],  # Top 10 peaks
        'n_significant_peaks': len(peaks),
        'page_signal': page_signal,
        'page_periodicity_detected': page_signal > np.mean(cepstrum_half) + 2*np.std(cepstrum_half),
    }


# ===========================================================================
# 8. Multitaper Spectrum
# ===========================================================================

def dpss_tapers(n: int, nw: float, k: int) -> np.ndarray:
    """
    Compute discrete prolate spheroidal sequences (Slepian tapers).
    
    Args:
        n: Length of sequence
        nw: Time-bandwidth product (typically 2-4)
        k: Number of tapers
    
    Returns:
        Array of shape (k, n) containing the tapers
    """
    # Construct the tridiagonal matrix for DPSS
    # This is a simplified implementation; scipy.signal.windows.dpss is better
    # but we're avoiding dependencies
    
    w = nw / n
    i = np.arange(n)
    
    # Diagonal
    d = ((n - 1 - 2*i) / 2) ** 2 * np.cos(2 * np.pi * w)
    
    # Off-diagonal
    e = i[1:] * (n - i[1:]) / 2
    
    # Build tridiagonal matrix
    T = np.diag(d) + np.diag(e, 1) + np.diag(e, -1)
    
    # Eigendecomposition
    eigenvalues, eigenvectors = np.linalg.eigh(T)
    
    # Take top k eigenvectors (highest eigenvalues)
    idx = np.argsort(eigenvalues)[::-1][:k]
    tapers = eigenvectors[:, idx].T
    
    # Normalize
    for i in range(k):
        tapers[i] /= np.linalg.norm(tapers[i])
    
    return tapers


def multitaper_spectrum(cipher: List[int], n_tapers: int = 5, nw: float = 3.0) -> np.ndarray:
    """
    Slepian taper-based PSD for reduced variance.
    More robust than raw FFT for short sequences.
    
    Args:
        cipher: List of cipher numbers
        n_tapers: Number of tapers to use
        nw: Time-bandwidth product
    
    Returns:
        Multitaper PSD estimate
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    n = len(arr)
    
    # Get DPSS tapers
    try:
        tapers = dpss_tapers(n, nw, n_tapers)
    except Exception:
        # Fallback to simple Hann windows if DPSS fails
        tapers = np.zeros((n_tapers, n))
        for i in range(n_tapers):
            # Phase-shifted Hann windows
            tapers[i] = np.hanning(n) * np.cos(2 * np.pi * i * np.arange(n) / n)
            tapers[i] /= np.linalg.norm(tapers[i])
    
    # Compute PSD for each taper and average
    psd_sum = np.zeros(n // 2 + 1)
    
    for taper in tapers:
        tapered = arr * taper
        fft_result = np.fft.fft(tapered)
        psd = np.abs(fft_result[:n//2+1]) ** 2
        psd_sum += psd
    
    psd_avg = psd_sum / n_tapers
    
    # Normalize
    total = psd_avg.sum()
    if total > 0:
        psd_avg /= total
    
    return psd_avg


# ===========================================================================
# 9. Spectral Forensic Battery
# ===========================================================================

def spectral_forensic_battery(cipher: List[int], name: str = "Cipher") -> Dict[str, Any]:
    """
    Run all spectral analyses, return comprehensive results dict.
    """
    results = {
        'name': name,
        'length': len(cipher),
    }
    
    # Power spectrum stats
    psd = power_spectrum(cipher)
    results['psd_max'] = float(np.max(psd))
    results['psd_peak_freq'] = int(np.argmax(psd))
    
    # Spectral entropy
    results['spectral_entropy'] = spectral_entropy(cipher)
    results['normalized_spectral_entropy'] = normalized_spectral_entropy(cipher)
    
    # Bicoherence (Welch-averaged — Phase 7 fix for saturation)
    results['mean_bicoherence'] = mean_bicoherence_welch(cipher)
    results['max_bicoherence'] = max_bicoherence_welch(cipher)
    
    # Phase randomness
    phase_test = phase_randomness_test(cipher)
    results['rayleigh_Z'] = phase_test['rayleigh_Z']
    results['phase_p_value'] = phase_test['p_value_bootstrap']
    results['phase_uniform'] = phase_test['uniform']
    results['circular_variance'] = phase_test['circular_variance']
    
    # Cepstral analysis
    cepstral = cepstral_analysis(cipher)
    results['n_cepstral_peaks'] = cepstral['n_significant_peaks']
    results['page_periodicity'] = cepstral['page_periodicity_detected']
    
    # Multitaper entropy
    mt_psd = multitaper_spectrum(cipher)
    mt_nonzero = mt_psd[mt_psd > 0]
    if len(mt_nonzero) > 0:
        mt_entropy = -np.sum(mt_nonzero * np.log2(mt_nonzero))
    else:
        mt_entropy = 0.0
    results['multitaper_entropy'] = float(mt_entropy)
    
    # Composite fabrication signal from spectral analysis
    # Low entropy + high bicoherence + non-uniform phases = fabrication
    fab_signals = []
    
    # Entropy signal (lower = more fabricated)
    entropy_signal = 1.0 - results['normalized_spectral_entropy']
    fab_signals.append(entropy_signal)
    
    # Bicoherence signal (higher = more fabricated)
    bicoherence_signal = min(1.0, results['mean_bicoherence'] * 10)
    fab_signals.append(bicoherence_signal)
    
    # Phase coupling signal (lower p-value = more fabricated)
    phase_signal = 1.0 - results['phase_p_value']
    fab_signals.append(phase_signal)
    
    results['spectral_fabrication_score'] = float(np.mean(fab_signals))
    
    return results


# ===========================================================================
# 10. Compare All Ciphers
# ===========================================================================

def compare_all_ciphers() -> Dict[str, Dict[str, Any]]:
    """
    Run spectral forensic battery on B1, B2, B3.
    Print comparison table.
    """
    ciphers = {
        'B1': B1_CIPHER,
        'B2': B2_CIPHER,
        'B3': B3_CIPHER,
    }
    
    results = {}
    for name, cipher in ciphers.items():
        results[name] = spectral_forensic_battery(cipher, name)
    
    # Print comparison table
    p("\n" + "="*90)
    p("SPECTRAL FORENSIC COMPARISON: B1 vs B2 vs B3")
    p("="*90)
    
    metrics = [
        ('Spectral Entropy', 'spectral_entropy', '.3f'),
        ('Normalized Entropy', 'normalized_spectral_entropy', '.3f'),
        ('Mean Bicoh (Welch)', 'mean_bicoherence', '.4f'),
        ('Max Bicoh (Welch)', 'max_bicoherence', '.4f'),
        ('Rayleigh Z', 'rayleigh_Z', '.2f'),
        ('Phase P-Value', 'phase_p_value', '.4f'),
        ('Phase Uniform?', 'phase_uniform', ''),
        ('Circular Variance', 'circular_variance', '.3f'),
        ('Cepstral Peaks', 'n_cepstral_peaks', 'd'),
        ('Page Periodicity?', 'page_periodicity', ''),
        ('Multitaper Entropy', 'multitaper_entropy', '.3f'),
        ('SPECTRAL FAB SCORE', 'spectral_fabrication_score', '.3f'),
    ]
    
    p("\n{:<24} {:>12} {:>12} {:>12}".format("Metric", "B1", "B2", "B3"))
    p("-"*60)
    
    for label, key, fmt in metrics:
        vals = []
        for name in ['B1', 'B2', 'B3']:
            v = results[name].get(key, 0)
            if fmt:
                if fmt == 'd':
                    vals.append(f"{int(v):>12}")
                else:
                    vals.append(f"{v:>12{fmt}}")
            else:
                vals.append(f"{str(v):>12}")
        p(f"{label:<24} {vals[0]} {vals[1]} {vals[2]}")
    
    # Interpretation
    p("\n" + "-"*60)
    p("INTERPRETATION:")
    p("-"*60)
    
    # Compare B2 vs B1/B3
    b2_entropy = results['B2']['normalized_spectral_entropy']
    b1_entropy = results['B1']['normalized_spectral_entropy']
    b3_entropy = results['B3']['normalized_spectral_entropy']
    
    p(f"\n  Entropy (higher = more genuine):")
    p(f"    B2: {b2_entropy:.3f} {'<-- HIGHEST' if b2_entropy > max(b1_entropy, b3_entropy) else ''}")
    p(f"    B1: {b1_entropy:.3f}")
    p(f"    B3: {b3_entropy:.3f}")
    
    b2_bc = results['B2']['mean_bicoherence']
    b1_bc = results['B1']['mean_bicoherence']
    b3_bc = results['B3']['mean_bicoherence']
    
    p(f"\n  Bicoherence (lower = more genuine):")
    p(f"    B2: {b2_bc:.4f} {'<-- LOWEST' if b2_bc < min(b1_bc, b3_bc) else ''}")
    p(f"    B1: {b1_bc:.4f}")
    p(f"    B3: {b3_bc:.4f}")
    
    b2_phase = results['B2']['phase_uniform']
    b1_phase = results['B1']['phase_uniform']
    b3_phase = results['B3']['phase_uniform']
    
    p(f"\n  Phase Uniformity (True = more genuine):")
    p(f"    B2: {b2_phase} {'<-- UNIFORM' if b2_phase else ''}")
    p(f"    B1: {b1_phase}")
    p(f"    B3: {b3_phase}")
    
    b2_fab = results['B2']['spectral_fabrication_score']
    b1_fab = results['B1']['spectral_fabrication_score']
    b3_fab = results['B3']['spectral_fabrication_score']
    
    p(f"\n  Composite Spectral Fabrication Score (lower = more genuine):")
    p(f"    B2: {b2_fab:.3f} {'<-- LOWEST' if b2_fab < min(b1_fab, b3_fab) else ''}")
    p(f"    B1: {b1_fab:.3f}")
    p(f"    B3: {b3_fab:.3f}")
    
    return results


def export_spectral_results(output_path: str = 'beale_spectral_results.json'):
    """Export spectral analysis results to JSON."""
    results = compare_all_ciphers()
    
    # Convert numpy types to Python types for JSON
    def convert(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(i) for i in obj]
        else:
            return obj
    
    results = convert(results)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    p(f"\nExported spectral results to: {output_path}")
    return results


# ===========================================================================
# Main
# ===========================================================================

def main():
    p("\n" + "="*80)
    p("BEALE PHASE 6 TASK 2: BISPECTRAL & HIGHER-ORDER SPECTRAL ANALYSIS")
    p("="*80)
    
    p("\nPrediction: B2 (genuine) should have:")
    p("  - Higher spectral entropy (more broadband)")
    p("  - Lower bicoherence (less phase coupling)")
    p("  - More uniform DFT phases")
    p("  - Lower composite spectral fabrication score")
    
    # Run full comparison
    results = compare_all_ciphers()
    
    # Export results
    export_spectral_results()
    
    p("\n" + "="*80)
    p("SPECTRAL ANALYSIS COMPLETE")
    p("="*80)


if __name__ == '__main__':
    main()
