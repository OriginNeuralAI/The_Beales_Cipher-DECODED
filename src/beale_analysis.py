"""
Beale Ciphers — Foundational Statistical Fingerprinting

Reproduces known results (Benford's Law, Gillogly sequence, last-digit bias)
and adds spectral/topological diagnostics from the combinatorial optimization stack.

Usage: python beale_analysis.py
"""

import numpy as np
from collections import Counter
import math
import sys

from beale_data import (
    B1_CIPHER, B2_CIPHER, B3_CIPHER, B2_PLAINTEXT,
    DOI_WORDS, ENGLISH_FREQ
)


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ---------------------------------------------------------------------------
# 1. Number Distribution
# ---------------------------------------------------------------------------

def number_distribution(cipher, name="Cipher"):
    """Histogram of cipher values: min, max, mean, median, std, unique count."""
    arr = np.array(cipher)
    stats = {
        'name': name,
        'count': len(arr),
        'min': int(arr.min()),
        'max': int(arr.max()),
        'mean': float(arr.mean()),
        'median': float(np.median(arr)),
        'std': float(arr.std()),
        'unique': len(set(cipher)),
    }
    return stats


def print_distribution(stats):
    p(f"  {stats['name']}: n={stats['count']}, range=[{stats['min']}, {stats['max']}], "
      f"mean={stats['mean']:.1f}, median={stats['median']:.1f}, "
      f"std={stats['std']:.1f}, unique={stats['unique']}")


# ---------------------------------------------------------------------------
# 2. Benford's Law (First-Digit Distribution)
# ---------------------------------------------------------------------------

def first_digit_distribution(cipher, name="Cipher"):
    """
    Benford's Law: P(d) = log10(1 + 1/d) for d=1..9.
    Returns observed vs expected frequencies and chi-squared statistic.
    Wase (2020): B2 follows epsilon-Benford (eps~0.15), B1/B3 deviate.
    """
    first_digits = [int(str(abs(n))[0]) for n in cipher if n > 0]
    n = len(first_digits)
    counts = Counter(first_digits)

    expected_benford = {d: math.log10(1 + 1/d) for d in range(1, 10)}

    chi_sq = 0.0
    results = {}
    for d in range(1, 10):
        observed = counts.get(d, 0) / n
        expected = expected_benford[d]
        chi_sq += n * (observed - expected) ** 2 / expected
        results[d] = {'observed': observed, 'expected': expected}

    # Degrees of freedom = 8 (9 digits - 1)
    # Critical value at p=0.05: 15.51
    return {
        'name': name,
        'chi_squared': chi_sq,
        'df': 8,
        'critical_005': 15.51,
        'follows_benford': chi_sq < 15.51,
        'digits': results,
        'n': n,
    }


def print_benford(result):
    status = "FOLLOWS" if result['follows_benford'] else "DEVIATES"
    p(f"  {result['name']}: chi2={result['chi_squared']:.2f} (critical={result['critical_005']:.2f}) "
      f"-> {status} Benford's Law")
    for d in range(1, 10):
        obs = result['digits'][d]['observed']
        exp = result['digits'][d]['expected']
        bar = '#' * int(obs * 50)
        p(f"    d={d}: obs={obs:.3f} exp={exp:.3f} {bar}")


# ---------------------------------------------------------------------------
# 3. Last-Digit Distribution (Fabrication Detector)
# ---------------------------------------------------------------------------

def last_digit_distribution(cipher, name="Cipher"):
    """
    Last-digit uniformity test.
    Wase (2020): B1/B3 show even-number bias in last digits.
    Genuine random data should have uniform last digits.
    """
    last_digits = [n % 10 for n in cipher]
    n = len(last_digits)
    counts = Counter(last_digits)

    expected = n / 10.0
    chi_sq = sum((counts.get(d, 0) - expected) ** 2 / expected for d in range(10))

    even_count = sum(counts.get(d, 0) for d in [0, 2, 4, 6, 8])
    odd_count = sum(counts.get(d, 0) for d in [1, 3, 5, 7, 9])
    even_ratio = even_count / n

    return {
        'name': name,
        'chi_squared': chi_sq,
        'df': 9,
        'critical_005': 16.92,
        'uniform': chi_sq < 16.92,
        'even_ratio': even_ratio,
        'even_bias': abs(even_ratio - 0.5),
        'counts': dict(counts),
    }


def print_last_digit(result):
    status = "UNIFORM" if result['uniform'] else "NON-UNIFORM"
    p(f"  {result['name']}: chi2={result['chi_squared']:.2f} -> {status}, "
      f"even_ratio={result['even_ratio']:.3f} (bias={result['even_bias']:.3f})")


# ---------------------------------------------------------------------------
# 4. Index of Coincidence
# ---------------------------------------------------------------------------

def index_of_coincidence(text):
    """
    IC of a text string. English ~ 0.065, random ~ 0.038.
    Used on decoded text to assess quality.
    """
    text = text.upper()
    text = ''.join(c for c in text if c.isalpha())
    n = len(text)
    if n < 2:
        return 0.0
    counts = Counter(text)
    ic = sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))
    return ic


# ---------------------------------------------------------------------------
# 5. Bigram Analysis (Number Pairs)
# ---------------------------------------------------------------------------

def bigram_analysis(cipher, name="Cipher"):
    """
    Consecutive number pair patterns.
    Detects repeated bigrams that might indicate structure.
    """
    bigrams = [(cipher[i], cipher[i+1]) for i in range(len(cipher) - 1)]
    counts = Counter(bigrams)
    total = len(bigrams)
    unique = len(counts)

    # Most common bigrams
    top_10 = counts.most_common(10)

    # Expected unique bigrams if random (approximation)
    vocab = len(set(cipher))
    expected_unique = min(total, vocab * vocab)

    return {
        'name': name,
        'total_bigrams': total,
        'unique_bigrams': unique,
        'vocab_size': vocab,
        'top_10': top_10,
        'repetition_rate': 1.0 - (unique / total) if total > 0 else 0,
    }


def print_bigrams(result):
    p(f"  {result['name']}: {result['unique_bigrams']} unique bigrams from "
      f"{result['total_bigrams']} total (vocab={result['vocab_size']}, "
      f"rep_rate={result['repetition_rate']:.3f})")
    p(f"    Top 5: {result['top_10'][:5]}")


# ---------------------------------------------------------------------------
# 6. Autocorrelation (Periodicity Detection)
# ---------------------------------------------------------------------------

def autocorrelation(cipher, max_lag=50, name="Cipher"):
    """
    Autocorrelation of the number sequence.
    Peaks indicate periodic structure (e.g., page boundaries, key length).
    """
    arr = np.array(cipher, dtype=float)
    arr = arr - arr.mean()
    n = len(arr)
    var = np.sum(arr ** 2)

    if var == 0:
        return {'name': name, 'lags': [], 'values': []}

    correlations = []
    for lag in range(1, min(max_lag + 1, n)):
        corr = np.sum(arr[:n-lag] * arr[lag:]) / var
        correlations.append((lag, float(corr)))

    # Sort by absolute correlation
    correlations.sort(key=lambda x: abs(x[1]), reverse=True)

    return {
        'name': name,
        'top_lags': correlations[:10],
        'all_correlations': correlations,
    }


def print_autocorrelation(result):
    p(f"  {result['name']} — Top autocorrelation lags:")
    for lag, corr in result['top_lags'][:5]:
        bar = '+' * int(abs(corr) * 40) if corr > 0 else '-' * int(abs(corr) * 40)
        p(f"    Lag {lag:3d}: {corr:+.4f} {bar}")


# ---------------------------------------------------------------------------
# 7. Spectral Fingerprint (Transition Matrix Eigenvalues)
# ---------------------------------------------------------------------------

def spectral_fingerprint(cipher, n_bins=26, name="Cipher"):
    """
    Build transition matrix from cipher number sequence (modulo n_bins),
    compute eigenvalues. Core spectral diagnostic.
    """
    # Map cipher numbers to bins
    binned = [n % n_bins for n in cipher]

    # Build transition matrix
    T = np.zeros((n_bins, n_bins))
    for i in range(len(binned) - 1):
        T[binned[i]][binned[i+1]] += 1

    # Normalize rows
    row_sums = T.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    T = T / row_sums

    # Eigenvalues
    eigenvalues = np.linalg.eigvals(T)
    eigenvalues = np.sort(np.abs(eigenvalues))[::-1]

    # Spectral gap (difference between largest and second-largest)
    spectral_gap = float(eigenvalues[0] - eigenvalues[1]) if len(eigenvalues) > 1 else 0.0

    return {
        'name': name,
        'top_eigenvalues': eigenvalues[:6].tolist(),
        'spectral_gap': spectral_gap,
        'n_bins': n_bins,
    }


def print_spectral(result):
    p(f"  {result['name']} (mod {result['n_bins']}):")
    p(f"    Spectral gap: {result['spectral_gap']:.4f}")
    eigs = ', '.join(f'{e:.4f}' for e in result['top_eigenvalues'])
    p(f"    Top eigenvalues: [{eigs}]")


# ---------------------------------------------------------------------------
# 8. Shannon Entropy
# ---------------------------------------------------------------------------

def shannon_entropy(cipher, name="Cipher"):
    """
    Shannon entropy H = -sum(p * log2(p)) of the number sequence.
    Higher entropy = more random. English text ~ 4.0-4.5 bits/char.
    """
    n = len(cipher)
    counts = Counter(cipher)
    entropy = -sum((c / n) * math.log2(c / n) for c in counts.values() if c > 0)

    # Maximum possible entropy
    max_entropy = math.log2(n)
    normalized = entropy / max_entropy if max_entropy > 0 else 0

    return {
        'name': name,
        'entropy': entropy,
        'max_entropy': max_entropy,
        'normalized': normalized,
        'unique_symbols': len(counts),
    }


def print_entropy(result):
    p(f"  {result['name']}: H={result['entropy']:.3f} bits "
      f"(max={result['max_entropy']:.3f}, normalized={result['normalized']:.3f}, "
      f"symbols={result['unique_symbols']})")


# ---------------------------------------------------------------------------
# 9. Gillogly Check (DoI Key Applied to B1/B3)
# ---------------------------------------------------------------------------

def gillogly_check(cipher, doi_words, name="Cipher", use_beale_offset=True):
    """
    Apply DoI key to cipher (book cipher decode), then find alphabetical runs.
    Gillogly (1980): B1 positions 190-203 give DEFGHIIJKLMMNO.

    Phase 2 fixes:
    - Uses Beale offset correction when available
    - Skips '?' characters when evaluating runs (treats as wildcards)
    - Proper p-value: exact probability for 26-letter alphabet with Bonferroni
    - Reports both 'non-decreasing' and 'strictly sequential' modes
    """
    # Import Beale offset if available
    try:
        from beale_data import BEALE_DOI_OFFSET, beale_decode
        if use_beale_offset:
            decoded_str = beale_decode(cipher, doi_words, use_beale_offset=True)
        else:
            decoded_str = beale_decode(cipher, doi_words, use_beale_offset=False)
    except ImportError:
        decoded = []
        for num in cipher:
            idx = num - 1
            if 0 <= idx < len(doi_words):
                decoded.append(doi_words[idx][0].upper())
            else:
                decoded.append('?')
        decoded_str = ''.join(decoded)

    decoded = list(decoded_str)

    # --- Non-decreasing mode: each letter >= previous (skipping '?') ---
    nd_runs = _find_runs(decoded, mode='non_decreasing')

    # --- Strictly sequential mode: each letter exactly +1 or same ---
    seq_runs = _find_runs(decoded, mode='sequential')

    # Combine and sort
    all_runs = nd_runs + seq_runs
    all_runs.sort(key=lambda x: x[1], reverse=True)

    # Proper p-value computation
    longest_nd = max((r[1] for r in nd_runs), default=0)
    longest_seq = max((r[1] for r in seq_runs), default=0)
    n = len([c for c in decoded if c != '?'])  # effective length

    p_nd = _run_pvalue(longest_nd, n, mode='non_decreasing')
    p_seq = _run_pvalue(longest_seq, n, mode='sequential')

    return {
        'name': name,
        'decoded_sample': decoded_str[:50] + '...',
        'decoded_full': decoded_str,
        'total_decoded': len(decoded_str),
        'out_of_range': decoded_str.count('?'),
        'non_decreasing_runs': sorted(nd_runs, key=lambda x: -x[1])[:5],
        'sequential_runs': sorted(seq_runs, key=lambda x: -x[1])[:5],
        'top_runs': sorted(nd_runs, key=lambda x: -x[1])[:5],
        'longest_nd': longest_nd,
        'longest_seq': longest_seq,
        'longest_run': longest_nd,
        'p_non_decreasing': p_nd,
        'p_sequential': p_seq,
        'p_longest': p_nd,
    }


def _find_runs(decoded, mode='non_decreasing'):
    """
    Find alphabetical runs, skipping '?' characters.

    mode='non_decreasing': each letter ord >= previous
    mode='sequential': each letter ord == previous or previous+1
    """
    runs = []
    # Build list of (position, letter) excluding '?'
    valid = [(i, c) for i, c in enumerate(decoded) if c != '?']

    if len(valid) < 2:
        return runs

    start_idx = 0
    for k in range(1, len(valid)):
        pos_prev, char_prev = valid[k - 1]
        pos_curr, char_curr = valid[k]

        is_continuation = False
        if mode == 'non_decreasing':
            is_continuation = ord(char_curr) >= ord(char_prev)
        elif mode == 'sequential':
            diff = ord(char_curr) - ord(char_prev)
            is_continuation = diff in (0, 1)

        if not is_continuation:
            run_len = k - start_idx
            if run_len >= 4:
                run_chars = ''.join(c for _, c in valid[start_idx:k])
                run_start_pos = valid[start_idx][0]
                runs.append((run_start_pos, run_len, run_chars))
            start_idx = k

    # Final run
    run_len = len(valid) - start_idx
    if run_len >= 4:
        run_chars = ''.join(c for _, c in valid[start_idx:])
        run_start_pos = valid[start_idx][0]
        runs.append((run_start_pos, run_len, run_chars))

    return runs


def _run_pvalue(k, n, mode='non_decreasing'):
    """
    Compute p-value for an alphabetical run of length k in n letters.

    For non-decreasing: P(next >= current) over uniform 26-letter alphabet
    = sum_{a=0}^{25} (26-a)/26 / 26 = 351/676 ≈ 0.519

    For sequential: P(next == current or current+1) = 2/26 ≈ 0.077

    With Bonferroni correction for n starting positions.
    """
    if k < 2:
        return 1.0

    if mode == 'non_decreasing':
        # P(pair is non-decreasing) ≈ 0.519
        p_pair = 351.0 / 676.0
    elif mode == 'sequential':
        # P(pair is same or +1) = 2/26 for most letters, 1/26 for Z
        p_pair = (25 * 2 + 1) / (26 * 26)  # = 51/676 ≈ 0.0754
    else:
        p_pair = 0.5

    # P(run of length k) = p_pair^(k-1)
    p_single = p_pair ** (k - 1)

    # Bonferroni correction: multiply by number of starting positions
    p_bonferroni = min(1.0, p_single * n)

    return p_bonferroni


def print_gillogly(result):
    p(f"  {result['name']}: decoded {result['total_decoded']} chars "
      f"({result['out_of_range']} out-of-range)")
    p(f"    Sample: {result['decoded_sample']}")
    if result.get('non_decreasing_runs'):
        p(f"    Non-decreasing runs (longest={result['longest_nd']}, "
          f"p={result['p_non_decreasing']:.2e}):")
        for start, length, run in result['non_decreasing_runs'][:3]:
            p(f"      pos {start}: {run} (len={length})")
    if result.get('sequential_runs'):
        p(f"    Sequential runs (longest={result['longest_seq']}, "
          f"p={result['p_sequential']:.2e}):")
        for start, length, run in result['sequential_runs'][:3]:
            p(f"      pos {start}: {run} (len={length})")
    if not result.get('non_decreasing_runs') and not result.get('sequential_runs'):
        p(f"    No significant alphabetical runs found")


# ---------------------------------------------------------------------------
# 10. Cross-Cipher Comparison
# ---------------------------------------------------------------------------

def compare_ciphers(b1, b2, b3):
    """
    Cross-cipher statistical comparison.
    Shared numbers, distribution overlap, correlation.
    """
    s1, s2, s3 = set(b1), set(b2), set(b3)

    # Shared numbers
    shared_12 = s1 & s2
    shared_13 = s1 & s3
    shared_23 = s2 & s3
    shared_all = s1 & s2 & s3

    # Distribution comparison using KS-like metric
    def distribution_distance(a, b):
        """Simple distribution distance (normalized mean difference)."""
        return abs(np.mean(a) - np.mean(b)) / max(np.std(a), np.std(b), 1)

    d12 = distribution_distance(b1, b2)
    d13 = distribution_distance(b1, b3)
    d23 = distribution_distance(b2, b3)

    return {
        'shared_b1_b2': len(shared_12),
        'shared_b1_b3': len(shared_13),
        'shared_b2_b3': len(shared_23),
        'shared_all': len(shared_all),
        'unique_b1': len(s1),
        'unique_b2': len(s2),
        'unique_b3': len(s3),
        'dist_b1_b2': d12,
        'dist_b1_b3': d13,
        'dist_b2_b3': d23,
    }


def print_comparison(result):
    p(f"  Unique values: B1={result['unique_b1']}, B2={result['unique_b2']}, B3={result['unique_b3']}")
    p(f"  Shared: B1&B2={result['shared_b1_b2']}, B1&B3={result['shared_b1_b3']}, "
      f"B2&B3={result['shared_b2_b3']}, All={result['shared_all']}")
    p(f"  Distribution distance: B1-B2={result['dist_b1_b2']:.3f}, "
      f"B1-B3={result['dist_b1_b3']:.3f}, B2-B3={result['dist_b2_b3']:.3f}")


# ---------------------------------------------------------------------------
# 11. Page Boundary Analysis (Fitzgerald 2024)
# ---------------------------------------------------------------------------

def page_boundary_analysis(cipher, words_per_page=325, name="Cipher"):
    """
    Fitzgerald (2024): Max cipher values match page boundaries in 1880s octavo
    (~325 words/page). If max value = N, key text has ceil(N/325) pages.
    """
    arr = np.array(cipher)
    max_val = int(arr.max())
    estimated_pages = math.ceil(max_val / words_per_page)
    estimated_words = estimated_pages * words_per_page

    # Distribution across pages
    page_assignments = [math.ceil(n / words_per_page) for n in cipher]
    page_counts = Counter(page_assignments)

    # Check for uniform page usage
    n_pages_used = len(page_counts)
    most_used = page_counts.most_common(5)

    return {
        'name': name,
        'max_value': max_val,
        'words_per_page': words_per_page,
        'estimated_pages': estimated_pages,
        'estimated_words': estimated_words,
        'pages_used': n_pages_used,
        'most_used_pages': most_used,
    }


def print_page_boundary(result):
    p(f"  {result['name']}: max={result['max_value']}, "
      f"~{result['estimated_pages']} pages @ {result['words_per_page']} words/page "
      f"(~{result['estimated_words']} total words)")
    p(f"    Pages used: {result['pages_used']}")
    top = ', '.join(f'p{pg}={ct}' for pg, ct in result['most_used_pages'][:5])
    p(f"    Most used: {top}")


# ---------------------------------------------------------------------------
# 12. Number Frequency Heatmap
# ---------------------------------------------------------------------------

def number_frequency(cipher, name="Cipher"):
    """Frequency of each number in the cipher. Detects over/under-represented values."""
    counts = Counter(cipher)
    n = len(cipher)

    # Top 20 most frequent
    top_20 = counts.most_common(20)

    # Hapax legomena (appear exactly once)
    hapax = sum(1 for c in counts.values() if c == 1)

    # Numbers appearing 3+ times
    frequent = sum(1 for c in counts.values() if c >= 3)

    return {
        'name': name,
        'top_20': top_20,
        'hapax': hapax,
        'hapax_ratio': hapax / len(counts),
        'frequent_3plus': frequent,
        'total_unique': len(counts),
    }


def print_number_freq(result):
    p(f"  {result['name']}: {result['total_unique']} unique values, "
      f"{result['hapax']} hapax ({result['hapax_ratio']:.1%}), "
      f"{result['frequent_3plus']} appear 3+ times")
    top5 = ', '.join(f'{n}x{c}' for n, c in result['top_20'][:10])
    p(f"    Top 10: {top5}")


# ===========================================================================
# Main: Run All Diagnostics
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers — Statistical Fingerprinting")
    p("Computational Forensic Approach")
    p("=" * 70)

    ciphers = [
        (B1_CIPHER, "B1 (Location)"),
        (B2_CIPHER, "B2 (Contents)"),
        (B3_CIPHER, "B3 (Names)"),
    ]

    # --- 1. Number Distribution ---
    p("\n[1] Number Distribution")
    p("-" * 40)
    for cipher, name in ciphers:
        stats = number_distribution(cipher, name)
        print_distribution(stats)

    # --- 2. Benford's Law ---
    p("\n[2] Benford's Law (First-Digit Distribution)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = first_digit_distribution(cipher, name)
        print_benford(result)

    # --- 3. Last-Digit Bias ---
    p("\n[3] Last-Digit Distribution (Fabrication Test)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = last_digit_distribution(cipher, name)
        print_last_digit(result)

    # --- 4. Shannon Entropy ---
    p("\n[4] Shannon Entropy")
    p("-" * 40)
    for cipher, name in ciphers:
        result = shannon_entropy(cipher, name)
        print_entropy(result)

    # --- 5. Number Frequency ---
    p("\n[5] Number Frequency Analysis")
    p("-" * 40)
    for cipher, name in ciphers:
        result = number_frequency(cipher, name)
        print_number_freq(result)

    # --- 6. Bigram Analysis ---
    p("\n[6] Bigram Analysis (Number Pairs)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = bigram_analysis(cipher, name)
        print_bigrams(result)

    # --- 7. Autocorrelation ---
    p("\n[7] Autocorrelation (Periodicity)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = autocorrelation(cipher, name=name)
        print_autocorrelation(result)

    # --- 8. Spectral Fingerprint ---
    p("\n[8] Spectral Fingerprint (Transition Matrix)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = spectral_fingerprint(cipher, name=name)
        print_spectral(result)

    # --- 9. Index of Coincidence (B2 plaintext) ---
    p("\n[9] Index of Coincidence")
    p("-" * 40)
    ic_b2 = index_of_coincidence(B2_PLAINTEXT)
    p(f"  B2 plaintext IC = {ic_b2:.4f} (English ~ 0.065)")

    # --- 10. Gillogly Check ---
    p("\n[10] Gillogly Check (DoI Key Applied)")
    p("-" * 40)
    for cipher, name in [(B1_CIPHER, "B1"), (B3_CIPHER, "B3")]:
        result = gillogly_check(cipher, DOI_WORDS, name)
        print_gillogly(result)

    # --- 11. Cross-Cipher Comparison ---
    p("\n[11] Cross-Cipher Comparison")
    p("-" * 40)
    result = compare_ciphers(B1_CIPHER, B2_CIPHER, B3_CIPHER)
    print_comparison(result)

    # --- 12. Page Boundary Analysis ---
    p("\n[12] Page Boundary Analysis (Fitzgerald 2024)")
    p("-" * 40)
    for cipher, name in ciphers:
        result = page_boundary_analysis(cipher, name=name)
        print_page_boundary(result)

    p("\n" + "=" * 70)
    p("Analysis complete.")
    p("=" * 70)
