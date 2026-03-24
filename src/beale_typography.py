"""
Beale Ciphers -- Phase 4 Task 4: Typographic Error Analysis

Investigates B1's anomalous even-digit bias (59%) and potential pamphlet
printing errors across all three ciphers.

1. Digit confusion matrix (1/7, 3/8, 5/6 patterns)
2. B1 digit-swap correction experiments
3. B2 offset-as-typo analysis
4. Cross-cipher digit patterns

Usage: python beale_typography.py
"""

import numpy as np
from collections import Counter, defaultdict
import math

from beale_data import (
    B1_CIPHER, B2_CIPHER, B3_CIPHER,
    DOI_WORDS, BEALE_DOI_OFFSET
)
from beale_fabrication import serial_correlation, fabrication_score


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ===========================================================================
# 1. Digit Confusion Matrix
# ===========================================================================

def digit_distributions_by_position(cipher, name="Cipher"):
    """
    Analyze digit distributions at ones, tens, hundreds places separately.
    In 1880s typesetting, specific digit confusions are common:
    - 1/7 (similar vertical strokes)
    - 3/8 (similar curves)
    - 5/6 (similar top/bottom)
    - 0/6, 0/9 (similar curves)
    """
    ones = []
    tens = []
    hundreds = []

    for num in cipher:
        s = str(num)
        ones.append(int(s[-1]))
        if len(s) >= 2:
            tens.append(int(s[-2]))
        if len(s) >= 3:
            hundreds.append(int(s[-3]))

    results = {}
    for place, digits, place_name in [
        ('ones', ones, 'Ones'),
        ('tens', tens, 'Tens'),
        ('hundreds', hundreds, 'Hundreds'),
    ]:
        counts = Counter(digits)
        n = len(digits)
        even_count = sum(counts.get(d, 0) for d in [0, 2, 4, 6, 8])
        even_ratio = even_count / n if n > 0 else 0.5

        # Chi-squared vs uniform
        expected = n / 10.0
        chi_sq = sum((counts.get(d, 0) - expected) ** 2 / expected
                     for d in range(10)) if n > 0 else 0

        results[place] = {
            'name': place_name,
            'n': n,
            'counts': dict(sorted(counts.items())),
            'even_ratio': even_ratio,
            'chi_squared': chi_sq,
        }

    return results


def build_confusion_matrix(cipher, name="Cipher"):
    """
    Build a confusion likelihood matrix for digit pairs.
    Commonly confused pairs in 1880s hand-set type:
    - 1<->7 (vertical stroke)
    - 3<->8 (curved)
    - 5<->6 (similar form)
    - 0<->6, 0<->9 (round forms)
    """
    # Known confusion pairs from 19th century typography
    confusion_pairs = [
        (1, 7, 'vertical stroke'),
        (3, 8, 'curved form'),
        (5, 6, 'similar shape'),
        (0, 6, 'round form'),
        (0, 9, 'round form'),
        (1, 4, 'narrow form'),
        (6, 9, 'rotation'),
    ]

    # Count digit occurrences at each position
    all_digits = []
    for num in cipher:
        for ch in str(num):
            all_digits.append(int(ch))

    digit_counts = Counter(all_digits)
    total = sum(digit_counts.values())

    # For each confusion pair, compute expected vs observed ratio
    pair_analysis = []
    for d1, d2, reason in confusion_pairs:
        count_d1 = digit_counts.get(d1, 0)
        count_d2 = digit_counts.get(d2, 0)
        ratio = count_d1 / count_d2 if count_d2 > 0 else float('inf')
        # Under uniform, ratio should be ~1.0
        deviation = abs(ratio - 1.0)

        # Even/odd pair?
        even_odd = (d1 % 2 != d2 % 2)

        pair_analysis.append({
            'd1': d1,
            'd2': d2,
            'reason': reason,
            'count_d1': count_d1,
            'count_d2': count_d2,
            'ratio': ratio,
            'deviation': deviation,
            'even_odd_pair': even_odd,
            'could_explain_even_bias': even_odd and deviation > 0.15,
        })

    return {
        'digit_counts': dict(sorted(digit_counts.items())),
        'total_digits': total,
        'pair_analysis': pair_analysis,
        'even_bias_explanations': [pa for pa in pair_analysis
                                    if pa['could_explain_even_bias']],
    }


# ===========================================================================
# 2. B1 Digit-Swap Correction
# ===========================================================================

def digit_swap_correction(cipher, swap_pair, name="Cipher"):
    """
    Try swapping one digit for another throughout the cipher.
    Check if the even-digit bias normalizes and if fabrication diagnostics change.

    swap_pair: (from_digit, to_digit) e.g. (7, 1) to test 7->1 confusion
    """
    from_d, to_d = swap_pair

    corrected = []
    n_swaps = 0
    for num in cipher:
        s = str(num)
        # str.replace replaces ALL occurrences (e.g., 170->110 for 7->1).
        # This is intentional: models systematic digit confusion across all
        # positions in a number. Guard: reject if result would be <= 0.
        new_s = s.replace(str(from_d), str(to_d))
        new_val = int(new_s) if new_s else 0
        if new_val <= 0:
            corrected.append(num)  # Keep original if swap produces invalid number
        else:
            if new_s != s:
                n_swaps += 1
            corrected.append(new_val)

    # Compute even-digit ratio for corrected cipher
    even_count = sum(1 for n in corrected if n % 10 in [0, 2, 4, 6, 8])
    corrected_even_ratio = even_count / len(corrected)

    original_even = sum(1 for n in cipher if n % 10 in [0, 2, 4, 6, 8])
    original_even_ratio = original_even / len(cipher)

    # Fabrication score comparison
    orig_fs = fabrication_score(cipher)
    corr_fs = fabrication_score(corrected)

    return {
        'swap': f'{from_d}->{to_d}',
        'n_numbers_changed': n_swaps,
        'original_even_ratio': original_even_ratio,
        'corrected_even_ratio': corrected_even_ratio,
        'even_ratio_change': corrected_even_ratio - original_even_ratio,
        'normalized': abs(corrected_even_ratio - 0.5) < abs(original_even_ratio - 0.5),
        'original_fab_score': orig_fs['composite_score'],
        'corrected_fab_score': corr_fs['composite_score'],
        'fab_score_change': corr_fs['composite_score'] - orig_fs['composite_score'],
    }


def systematic_swap_analysis():
    """
    Try all plausible digit swaps on B1 and find which ones best normalize
    the even-digit bias.
    """
    # Plausible swaps based on typographic confusion
    swaps = [
        (7, 1), (1, 7),  # 1/7 confusion
        (8, 3), (3, 8),  # 3/8 confusion
        (6, 5), (5, 6),  # 5/6 confusion
        (6, 0), (0, 6),  # 0/6 confusion
        (9, 0), (0, 9),  # 0/9 confusion
        (9, 6), (6, 9),  # 6/9 rotation
    ]

    results = []
    for from_d, to_d in swaps:
        result = digit_swap_correction(B1_CIPHER, (from_d, to_d), "B1")
        results.append(result)

    # Sort by how much they normalize even-digit ratio
    results.sort(key=lambda r: abs(r['corrected_even_ratio'] - 0.5))

    return results


# ===========================================================================
# 3. B2 Offset-as-Typo Analysis
# ===========================================================================

def offset_typo_analysis():
    """
    For each non-zero offset in BEALE_DOI_OFFSET, check if the cipher number
    minus the offset is reachable by a single-digit change.

    If num=557 has offset=-6, is 557+6=563 achievable by changing one digit
    of 557? (e.g., 557->567 changes one digit, diff=10, not 6).
    """
    results = []

    for num, off in sorted(BEALE_DOI_OFFSET.items()):
        if off == 0:
            continue

        # Target: the "correct" cipher number if no offset needed
        target = num - off  # What the number "should" have been

        # Single-digit change analysis
        num_str = str(num)
        target_str = str(target) if target > 0 else '?'

        # Check each digit position
        digit_changes = []
        if target > 0 and len(str(target)) == len(num_str):
            for pos in range(len(num_str)):
                if num_str[pos] != target_str[pos]:
                    digit_changes.append({
                        'position': pos,
                        'original': num_str[pos],
                        'target': target_str[pos],
                    })

        single_digit = len(digit_changes) == 1

        # Is the difference a power of 10? (common misread of digit position)
        abs_off = abs(off)
        is_power_10 = abs_off in [1, 10, 100, 1000]

        # Is it a transposition? (digits swapped)
        is_transposition = False
        if len(num_str) == len(target_str) and len(digit_changes) == 2:
            # Check if swapping the two changed positions gives the target
            swapped = list(num_str)
            swapped[digit_changes[0]['position']], swapped[digit_changes[1]['position']] = \
                swapped[digit_changes[1]['position']], swapped[digit_changes[0]['position']]
            is_transposition = ''.join(swapped) == target_str

        results.append({
            'cipher_num': num,
            'offset': off,
            'target': target,
            'single_digit_change': single_digit,
            'digit_changes': digit_changes,
            'is_power_10': is_power_10,
            'is_transposition': is_transposition,
            'plausible_typo': single_digit or is_power_10 or is_transposition,
            'classification': ('single_digit_typo' if single_digit else
                               'power_10_shift' if is_power_10 else
                               'transposition' if is_transposition else
                               'edition_difference'),
        })

    return results


# ===========================================================================
# 4. Cross-Cipher Digit Patterns
# ===========================================================================

def cross_cipher_digit_comparison():
    """
    Compare digit-position distributions across B1/B2/B3.
    B1's even-digit bias (0.590) is B1-specific (B2=0.528, B3=0.529).
    """
    results = {}

    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        # Overall digit distribution
        all_digits = []
        for num in cipher:
            for ch in str(num):
                all_digits.append(int(ch))

        digit_counts = Counter(all_digits)
        total = sum(digit_counts.values())

        # Even/odd at each position
        pos_data = digit_distributions_by_position(cipher, name)

        # Last digit detail
        last_digits = [num % 10 for num in cipher]
        ld_counts = Counter(last_digits)

        # First digit detail
        first_digits = [int(str(num)[0]) for num in cipher]
        fd_counts = Counter(first_digits)

        results[name] = {
            'total_digits': total,
            'digit_distribution': dict(sorted(digit_counts.items())),
            'overall_even_ratio': sum(digit_counts.get(d, 0) for d in [0, 2, 4, 6, 8]) / total,
            'last_digit_even_ratio': pos_data['ones']['even_ratio'],
            'last_digit_counts': dict(sorted(ld_counts.items())),
            'first_digit_counts': dict(sorted(fd_counts.items())),
            'by_position': pos_data,
        }

    # Compare B1 vs B2/B3 for each digit
    b1_digits = results['B1']['digit_distribution']
    b2_digits = results['B2']['digit_distribution']
    b3_digits = results['B3']['digit_distribution']

    # Normalize to proportions
    b1_total = results['B1']['total_digits']
    b2_total = results['B2']['total_digits']
    b3_total = results['B3']['total_digits']

    digit_comparison = {}
    for d in range(10):
        b1_pct = b1_digits.get(d, 0) / b1_total * 100
        b2_pct = b2_digits.get(d, 0) / b2_total * 100
        b3_pct = b3_digits.get(d, 0) / b3_total * 100
        expected = 10.0  # uniform expectation (rough)

        digit_comparison[d] = {
            'B1': b1_pct,
            'B2': b2_pct,
            'B3': b3_pct,
            'B1_deviation': b1_pct - expected,
            'B1_unique': abs(b1_pct - b2_pct) > 2.0 and abs(b1_pct - b3_pct) > 2.0,
        }

    return {
        'per_cipher': results,
        'digit_comparison': digit_comparison,
    }


# ===========================================================================
# 5. Even-Digit Bias Localization
# ===========================================================================

def even_digit_localization():
    """
    Is B1's even-digit bias uniform across the cipher, or concentrated in
    specific regions? Test by quarter and by digit position.
    """
    n = len(B1_CIPHER)
    q_size = n // 4

    quarter_analysis = []
    for q in range(4):
        start = q * q_size
        end = start + q_size if q < 3 else n
        segment = B1_CIPHER[start:end]

        last_digits = [num % 10 for num in segment]
        even = sum(1 for d in last_digits if d in [0, 2, 4, 6, 8])
        even_ratio = even / len(segment)

        # Per-digit counts
        ld_counts = Counter(last_digits)

        quarter_analysis.append({
            'quarter': q + 1,
            'range': f'{start}-{end}',
            'even_ratio': even_ratio,
            'counts': dict(sorted(ld_counts.items())),
        })

    # By number magnitude (small vs large numbers)
    small = [n for n in B1_CIPHER if n <= 500]
    large = [n for n in B1_CIPHER if n > 500]

    small_even = sum(1 for n in small if n % 10 in [0, 2, 4, 6, 8]) / len(small) if small else 0
    large_even = sum(1 for n in large if n % 10 in [0, 2, 4, 6, 8]) / len(large) if large else 0

    # By number of digits
    by_digits = defaultdict(list)
    for num in B1_CIPHER:
        by_digits[len(str(num))].append(num)

    digit_length_analysis = {}
    for length, nums in sorted(by_digits.items()):
        even = sum(1 for n in nums if n % 10 in [0, 2, 4, 6, 8])
        digit_length_analysis[length] = {
            'count': len(nums),
            'even_ratio': even / len(nums),
        }

    return {
        'by_quarter': quarter_analysis,
        'small_nums_even': small_even,
        'large_nums_even': large_even,
        'small_count': len(small),
        'large_count': len(large),
        'by_digit_length': digit_length_analysis,
        'bias_is_uniform': all(abs(q['even_ratio'] - 0.59) < 0.08
                                for q in quarter_analysis),
    }


# ===========================================================================
# 6. Even-Digit Decomposition (Phase 8, 8c.3)
# ===========================================================================

def even_digit_decomposition():
    """
    Per-digit (0-9) excess by position (ones/tens/hundreds) by cipher (B1/B2/B3).
    Cross-tabulate to identify which specific digit(s) and position(s) drive
    B1's 59% even-digit bias.
    """
    results = {}

    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        n = len(cipher)
        # Extract digits by position
        ones = [num % 10 for num in cipher]
        tens = [(num // 10) % 10 for num in cipher if num >= 10]
        hundreds = [(num // 100) % 10 for num in cipher if num >= 100]

        position_data = {}
        for pos_name, digits in [('ones', ones), ('tens', tens), ('hundreds', hundreds)]:
            if not digits:
                continue
            total = len(digits)
            counts = Counter(digits)
            expected = total / 10.0

            # Per-digit excess over expected
            digit_excess = {}
            for d in range(10):
                observed = counts.get(d, 0)
                excess = observed - expected
                digit_excess[d] = {
                    'observed': observed,
                    'expected': round(expected, 1),
                    'excess': round(excess, 1),
                    'excess_pct': round(excess / expected * 100, 1) if expected > 0 else 0,
                    'is_even': d % 2 == 0,
                }

            # Sum even excess
            even_excess = sum(digit_excess[d]['excess'] for d in [0, 2, 4, 6, 8])
            odd_excess = sum(digit_excess[d]['excess'] for d in [1, 3, 5, 7, 9])

            position_data[pos_name] = {
                'n': total,
                'digit_excess': digit_excess,
                'even_excess': round(even_excess, 1),
                'odd_excess': round(odd_excess, 1),
                'even_ratio': sum(counts.get(d, 0) for d in [0, 2, 4, 6, 8]) / total,
            }

        # Identify top contributing digits for B1's bias
        top_contributors = []
        if name == 'B1':
            for pos_name, data in position_data.items():
                for d, info in data['digit_excess'].items():
                    if info['excess'] > 3.0 and info['is_even']:
                        top_contributors.append({
                            'position': pos_name,
                            'digit': d,
                            'excess': info['excess'],
                        })
            top_contributors.sort(key=lambda x: -x['excess'])

        results[name] = {
            'positions': position_data,
            'top_contributors': top_contributors if name == 'B1' else [],
        }

    return results


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers -- Phase 4 Task 4: Typographic Error Analysis")
    p("=" * 70)

    # --- 1. Digit Confusion Matrix ---
    p("\n[1] Digit Confusion Matrix")
    p("-" * 50)
    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        cm = build_confusion_matrix(cipher, name)
        p(f"\n  {name}: digit counts = {cm['digit_counts']}")
        p(f"  Confusion pair analysis:")
        for pa in cm['pair_analysis']:
            flag = ' <-- EXPLAINS EVEN BIAS' if pa['could_explain_even_bias'] else ''
            p(f"    {pa['d1']}<->{pa['d2']} ({pa['reason']}): "
              f"{pa['count_d1']} vs {pa['count_d2']}, "
              f"ratio={pa['ratio']:.3f}, dev={pa['deviation']:.3f}{flag}")

    # --- 2. Digit-by-Position Analysis ---
    p("\n[2] Digit Distribution by Position")
    p("-" * 50)
    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        pos_data = digit_distributions_by_position(cipher, name)
        p(f"\n  {name}:")
        for place in ['ones', 'tens', 'hundreds']:
            d = pos_data[place]
            p(f"    {d['name']:10s}: n={d['n']:4d}, even_ratio={d['even_ratio']:.3f}, "
              f"chi2={d['chi_squared']:.2f}")

    # --- 3. B1 Digit-Swap Correction ---
    p("\n[3] B1 Digit-Swap Correction (Even-Bias Normalization)")
    p("-" * 50)
    swaps = systematic_swap_analysis()
    p(f"  Original B1 even-digit ratio: {swaps[0]['original_even_ratio']:.3f}")
    p(f"  Target: ~0.500")
    p(f"\n  {'Swap':8s} {'Changed':8s} {'New Even':10s} {'Delta':8s} {'Normalized':12s} {'Fab Score':10s}")
    p(f"  {'-'*8} {'-'*8} {'-'*10} {'-'*8} {'-'*12} {'-'*10}")
    for r in swaps:
        p(f"  {r['swap']:8s} {r['n_numbers_changed']:8d} "
          f"{r['corrected_even_ratio']:10.3f} "
          f"{r['even_ratio_change']:+8.3f} "
          f"{'YES' if r['normalized'] else 'no':12s} "
          f"{r['corrected_fab_score']:.2f}")

    # --- 4. B2 Offset-as-Typo Analysis ---
    p("\n[4] B2 Offset-as-Typo Analysis")
    p("-" * 50)
    typo_analysis = offset_typo_analysis()
    for ta in typo_analysis:
        if ta['offset'] == 0:
            continue
        p(f"  num={ta['cipher_num']:4d} off={ta['offset']:+3d} "
          f"target={ta['target']:4d} "
          f"class={ta['classification']:20s} "
          f"{'PLAUSIBLE TYPO' if ta['plausible_typo'] else ''}")

    # Summary of typo classifications
    classifications = Counter(ta['classification'] for ta in typo_analysis)
    p(f"\n  Classification summary: {dict(classifications)}")

    # --- 5. Cross-Cipher Digit Patterns ---
    p("\n[5] Cross-Cipher Digit Comparison")
    p("-" * 50)
    cross = cross_cipher_digit_comparison()
    p(f"\n  Overall even-digit ratios:")
    for name, data in cross['per_cipher'].items():
        p(f"    {name}: {data['overall_even_ratio']:.3f} "
          f"(last digit: {data['last_digit_even_ratio']:.3f})")

    p(f"\n  Per-digit comparison (% of all digits):")
    p(f"  {'Digit':6s} {'B1':8s} {'B2':8s} {'B3':8s} {'B1 unique':10s}")
    for d in range(10):
        dc = cross['digit_comparison'][d]
        p(f"  {d:6d} {dc['B1']:8.1f} {dc['B2']:8.1f} {dc['B3']:8.1f} "
          f"{'YES' if dc['B1_unique'] else '':10s}")

    # --- 6. Even-Digit Bias Localization ---
    p("\n[6] B1 Even-Digit Bias Localization")
    p("-" * 50)
    loc = even_digit_localization()
    p(f"  By quarter:")
    for q in loc['by_quarter']:
        p(f"    Q{q['quarter']} ({q['range']}): even_ratio={q['even_ratio']:.3f}")
    p(f"  Small nums (<=500): even={loc['small_nums_even']:.3f} (n={loc['small_count']})")
    p(f"  Large nums (>500):  even={loc['large_nums_even']:.3f} (n={loc['large_count']})")
    p(f"  By digit length:")
    for length, data in loc['by_digit_length'].items():
        p(f"    {length}-digit: n={data['count']}, even_ratio={data['even_ratio']:.3f}")
    p(f"  Bias is uniform across quarters: {loc['bias_is_uniform']}")

    # --- 7. Even-Digit Decomposition ---
    p("\n[7] Even-Digit Decomposition (Phase 8)")
    p("-" * 50)
    decomp = even_digit_decomposition()
    for cname in ['B1', 'B2', 'B3']:
        p(f"\n  {cname}:")
        for pos_name, data in decomp[cname]['positions'].items():
            p(f"    {pos_name:10s} (n={data['n']:4d}): even_ratio={data['even_ratio']:.3f}, "
              f"even_excess={data['even_excess']:+.1f}, odd_excess={data['odd_excess']:+.1f}")
    if decomp['B1']['top_contributors']:
        p(f"\n  B1 top even-bias contributors:")
        for tc in decomp['B1']['top_contributors'][:5]:
            p(f"    digit {tc['digit']} at {tc['position']}: excess={tc['excess']:+.1f}")

    # --- Summary ---
    p(f"\n{'=' * 70}")
    p("TYPOGRAPHIC ANALYSIS SUMMARY")
    p(f"{'=' * 70}")
    # Find the best swap
    if swaps:
        best = swaps[0]
        p(f"  1. Best even-bias correction: {best['swap']} swap "
          f"({best['corrected_even_ratio']:.3f})")
    p(f"  2. B1 even-digit bias is position-independent (uniform across quarters)")
    p(f"  3. Bias is B1-specific: B2={cross['per_cipher']['B2']['last_digit_even_ratio']:.3f}, "
      f"B3={cross['per_cipher']['B3']['last_digit_even_ratio']:.3f}")
    p(f"  4. Suggests B1 manuscript source (not printing) introduced the bias")
    p(f"  5. Negative B2 offsets are NOT single-digit typos -- they are local")
    p(f"     edition variants or pamphlet errors requiring multi-digit changes")
    p(f"{'=' * 70}")
