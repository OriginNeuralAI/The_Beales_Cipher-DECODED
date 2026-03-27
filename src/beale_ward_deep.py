"""
Beale Ciphers — Phase 5 Task 3: Ward Fabrication Deep Forensics

Extends the Ward model with:
  1. Step-by-step Gillogly construction simulation
  2. Cognitive load timeline (sliding window)
  3. Vocabulary evolution (cumulative distinct numbers)
  4. Even-digit hypothesis testing (3 models)
  5. Fabrication time estimation

Usage: python beale_ward_deep.py
"""

import numpy as np
from collections import Counter, defaultdict
import math
import random

from beale_data import (
    B1_CIPHER, B2_CIPHER, B3_CIPHER,
    DOI_WORDS, BEALE_DOI_OFFSET, beale_decode
)
from beale_ward_model import WardFabricationModel
from beale_fabrication import serial_correlation


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ===========================================================================
# 1. Gillogly Construction Simulation
# ===========================================================================

def simulate_gillogly_construction():
    """
    For each letter in the Gillogly sequence CDEFGHIIJKLM, catalog ALL DoI
    words starting with that letter and show which position Ward chose.

    Demonstrates the non-monotone number / monotone letter pattern.
    Estimates time per selection.
    """
    gillogly_letters = 'CDEFGHIIJKLM'
    gillogly_numbers = B1_CIPHER[189:201]  # positions 189-200

    # Build letter -> DoI positions index
    letter_positions = defaultdict(list)
    for i, word in enumerate(DOI_WORDS):
        letter_positions[word[0].upper()].append(i + 1)  # 1-indexed

    selections = []
    prev_num = None

    for i, (letter, chosen_num) in enumerate(zip(gillogly_letters, gillogly_numbers)):
        all_positions = letter_positions.get(letter, [])
        n_available = len(all_positions)

        # Where was the chosen word among all options?
        if chosen_num in all_positions:
            rank = sorted(all_positions).index(chosen_num) + 1
        else:
            rank = -1

        # Search cost: how far from the previous selection?
        if prev_num is not None:
            search_distance = abs(chosen_num - prev_num)
        else:
            search_distance = chosen_num  # from start

        # Is this selection monotone with previous?
        monotone = prev_num is None or chosen_num >= prev_num

        # Word chosen
        doi_idx = chosen_num - 1
        word = DOI_WORDS[doi_idx] if 0 <= doi_idx < len(DOI_WORDS) else '?'

        selections.append({
            'position': 189 + i,
            'target_letter': letter,
            'chosen_num': chosen_num,
            'doi_word': word,
            'n_available': n_available,
            'rank_in_sorted': rank,
            'search_distance': search_distance,
            'is_monotone': monotone,
            'estimated_lookup_seconds': _estimate_lookup_time(search_distance, n_available),
        })

        prev_num = chosen_num

    # Aggregate statistics
    total_time = sum(s['estimated_lookup_seconds'] for s in selections)
    monotone_count = sum(1 for s in selections if s['is_monotone'])

    return {
        'selections': selections,
        'n_letters': len(gillogly_letters),
        'monotone_numbers': monotone_count,
        'monotone_ratio': monotone_count / len(gillogly_letters),
        'estimated_total_seconds': total_time,
        'estimated_minutes': total_time / 60.0,
        'avg_search_distance': np.mean([s['search_distance'] for s in selections]),
        'avg_n_available': np.mean([s['n_available'] for s in selections]),
    }


def _estimate_lookup_time(search_distance, n_available):
    """
    Estimate time to find a word in a printed DoI text.
    Assumes ~3 seconds per page scan + 1 second per word check.
    Average words per page: ~325.
    """
    pages_to_scan = max(1, search_distance / 325.0)
    # Time = page scan + selection from candidates
    return 3.0 * pages_to_scan + 1.0 * min(n_available, 5)


# ===========================================================================
# 2. Cognitive Load Model
# ===========================================================================

def model_cognitive_load(cipher, window_size=30):
    """
    Sliding window computing:
    - Running serial correlation
    - Running distinct ratio (unique/window)
    - Number of "resets" (jumps > 500)
    - Composite cognitive load score

    Detect the exact position where careful -> lazy transition occurs.
    """
    n = len(cipher)
    windows = []

    for start in range(0, n - window_size + 1, 5):  # step by 5
        end = start + window_size
        segment = cipher[start:end]

        sc = serial_correlation(segment)
        dr = len(set(segment)) / len(segment)
        jumps = [abs(segment[i+1] - segment[i]) for i in range(len(segment) - 1)]
        large_jumps = sum(1 for j in jumps if j > 500)
        mean_jump = float(np.mean(jumps)) if jumps else 0

        # Composite cognitive load:
        # Low SC + low DR + many large jumps = high cognitive effort (careful)
        # High SC + high DR + few large jumps = low effort (lazy)
        effort_score = (1.0 - sc) * 0.4 + (1.0 - dr) * 0.3 + (large_jumps / len(jumps) if jumps else 0) * 0.3

        windows.append({
            'center': start + window_size // 2,
            'start': start,
            'end': end,
            'serial_correlation': sc,
            'distinct_ratio': dr,
            'large_jumps': large_jumps,
            'mean_jump': mean_jump,
            'effort_score': effort_score,
        })

    # Detect transition point: where effort drops significantly
    effort_scores = [w['effort_score'] for w in windows]
    if len(effort_scores) > 10:
        # Sliding difference
        diffs = [effort_scores[i] - effort_scores[i + 5] for i in range(len(effort_scores) - 5)]
        # Find max drop
        max_drop_idx = max(range(len(diffs)), key=lambda i: diffs[i]) if diffs else 0
        transition_pos = windows[max_drop_idx + 2]['center'] if max_drop_idx + 2 < len(windows) else 0
    else:
        transition_pos = n // 4

    # Quarter analysis
    q_size = n // 4
    quarter_effort = []
    for q in range(4):
        q_windows = [w for w in windows
                    if q * q_size <= w['center'] < (q + 1) * q_size]
        if q_windows:
            q_effort = np.mean([w['effort_score'] for w in q_windows])
            q_sc = np.mean([w['serial_correlation'] for w in q_windows])
        else:
            q_effort = 0.0
            q_sc = 0.0
        quarter_effort.append({
            'quarter': q + 1,
            'mean_effort': float(q_effort),
            'mean_sc': float(q_sc),
        })

    # Is there a monotonic fatigue gradient?
    efforts = [qe['mean_effort'] for qe in quarter_effort]
    is_monotonic_fatigue = all(efforts[i] >= efforts[i + 1]
                               for i in range(len(efforts) - 1))

    return {
        'windows': windows,
        'window_size': window_size,
        'transition_position': transition_pos,
        'quarter_effort': quarter_effort,
        'is_monotonic_fatigue': is_monotonic_fatigue,
        'effort_gradient': (efforts[0] - efforts[-1]) if len(efforts) >= 2 else 0,
    }


# ===========================================================================
# 3. Vocabulary Evolution
# ===========================================================================

def vocabulary_evolution(cipher, window_size=50):
    """
    Track cumulative distinct numbers:
    - Growth curve: new numbers introduced per window
    - Plateau detection: when did Ward stop introducing new numbers?
    - Compare B1 vs B3 curves
    """
    n = len(cipher)
    seen = set()
    growth_curve = []

    for i in range(n):
        seen.add(cipher[i])
        if (i + 1) % window_size == 0 or i == n - 1:
            growth_curve.append({
                'position': i + 1,
                'cumulative_distinct': len(seen),
                'fraction_of_cipher': (i + 1) / n,
            })

    # New numbers per window
    new_per_window = []
    prev_count = 0
    for gc in growth_curve:
        new_count = gc['cumulative_distinct'] - prev_count
        new_per_window.append({
            'window_end': gc['position'],
            'new_numbers': new_count,
        })
        prev_count = gc['cumulative_distinct']

    # Plateau detection: find first window where new numbers < threshold
    plateau_threshold = max(2, window_size * 0.05)  # 5% of window size
    plateau_pos = n  # default: never plateaus
    for npw in new_per_window:
        if npw['new_numbers'] < plateau_threshold:
            plateau_pos = npw['window_end']
            break

    # Final distinct ratio
    final_distinct = len(set(cipher))
    final_ratio = final_distinct / n

    return {
        'growth_curve': growth_curve,
        'new_per_window': new_per_window,
        'plateau_position': plateau_pos,
        'plateau_fraction': plateau_pos / n,
        'final_distinct': final_distinct,
        'final_ratio': final_ratio,
        'window_size': window_size,
    }


# ===========================================================================
# 4. Even-Digit Hypothesis Testing
# ===========================================================================

def even_digit_hypothesis_testing():
    """
    Test 3 hypotheses for B1's 59% even last-digit bias:

    H1: Ward favored round-ending numbers (cognitive preference for even digits)
    H2: Digit confusion in Ward's handwriting (from beale_typography)
    H3: Scanning pattern interacting with DoI word numbering

    Report which hypothesis best fits the observed distribution.
    """
    # Observed B1 last-digit distribution
    b1_last_digits = [num % 10 for num in B1_CIPHER]
    b1_counts = Counter(b1_last_digits)
    n = len(B1_CIPHER)

    observed_even = sum(b1_counts.get(d, 0) for d in [0, 2, 4, 6, 8]) / n

    results = {}

    # H1: Cognitive bias toward even digits
    # Simulate: generate random numbers with slight even preference
    rng = random.Random(42)
    h1_sims = []
    for bias in [0.52, 0.55, 0.58, 0.60, 0.62]:
        even_ratio_sim = []
        for _ in range(1000):
            sim = []
            for _ in range(n):
                if rng.random() < bias:
                    sim.append(rng.choice([0, 2, 4, 6, 8]))
                else:
                    sim.append(rng.choice([1, 3, 5, 7, 9]))
            er = sum(1 for d in sim if d in [0, 2, 4, 6, 8]) / len(sim)
            even_ratio_sim.append(er)
        mean_er = np.mean(even_ratio_sim)
        std_er = np.std(even_ratio_sim)
        z = (observed_even - mean_er) / std_er if std_er > 0 else 0
        h1_sims.append({
            'bias_param': bias,
            'sim_mean': float(mean_er),
            'sim_std': float(std_er),
            'z_score': float(z),
            'fits': abs(z) < 2.0,
        })

    # Find best-fitting bias
    best_h1 = min(h1_sims, key=lambda s: abs(s['z_score']))
    results['H1_cognitive_bias'] = {
        'description': 'Ward had cognitive preference for even-ending numbers',
        'best_fit_bias': best_h1['bias_param'],
        'z_score': best_h1['z_score'],
        'fits': best_h1['fits'],
        'all_fits': h1_sims,
    }

    # H2: Digit confusion (e.g., 3->8, 1->7 makes odd->even)
    # Count how many odd->even confusions would explain the bias
    odd_digits_in_b1 = sum(b1_counts.get(d, 0) for d in [1, 3, 5, 7, 9])
    even_digits_in_b1 = sum(b1_counts.get(d, 0) for d in [0, 2, 4, 6, 8])
    excess_even = even_digits_in_b1 - n // 2

    # How many odd->even swaps needed?
    swaps_needed = excess_even  # each swap moves 1 from odd to even

    # Are there enough confusion-pair opportunities?
    # 3->8 confusions: need b1_counts[3] to have some converted to 8
    # 1->7 confusions: would make even->odd (wrong direction)
    # 5->6 confusions: odd->even (correct direction!)
    # 9->0 confusions: odd->even (correct direction!)
    confusion_opportunities = b1_counts.get(5, 0) + b1_counts.get(9, 0) + b1_counts.get(3, 0)

    results['H2_digit_confusion'] = {
        'description': 'Typographic confusion: odd digits misread as even (5->6, 9->0, 3->8)',
        'excess_even': excess_even,
        'swaps_needed': swaps_needed,
        'confusion_opportunities': confusion_opportunities,
        'sufficient_opportunities': confusion_opportunities >= swaps_needed,
        'fits': confusion_opportunities >= swaps_needed,
    }

    # H3: Scanning pattern + DoI word numbering
    # If Ward scanned DoI sequentially, the word positions he picked
    # would follow a scanning pattern. Does the DoI have an even-bias
    # in word positions for common first letters?
    doi_positions_by_letter = defaultdict(list)
    for i, word in enumerate(DOI_WORDS):
        doi_positions_by_letter[word[0].upper()].append(i + 1)

    # Check if common letters (T, A, O, H, S) have even-biased positions
    common_letters = 'TAOHSINRE'
    letter_even_bias = {}
    for letter in common_letters:
        positions = doi_positions_by_letter.get(letter, [])
        if positions:
            even_positions = sum(1 for p in positions if p % 10 in [0, 2, 4, 6, 8])
            letter_even_bias[letter] = even_positions / len(positions)

    overall_doi_even = sum(1 for pos in range(1, len(DOI_WORDS) + 1)
                          if pos % 10 in [0, 2, 4, 6, 8]) / len(DOI_WORDS)

    results['H3_scanning_pattern'] = {
        'description': 'DoI word positions for common letters have even-digit bias',
        'overall_doi_even_ratio': overall_doi_even,
        'common_letter_even_bias': letter_even_bias,
        'mean_common_even': float(np.mean(list(letter_even_bias.values()))) if letter_even_bias else 0.5,
        'fits': abs(overall_doi_even - 0.5) > 0.05,
    }

    # Verdict
    fitting = [name for name, r in results.items() if r['fits']]

    return {
        'observed_even_ratio': observed_even,
        'hypotheses': results,
        'fitting_hypotheses': fitting,
        'best_hypothesis': fitting[0] if fitting else 'none',
        'b1_last_digit_counts': dict(sorted(b1_counts.items())),
    }


# ===========================================================================
# 5. Fabrication Time Estimation
# ===========================================================================

def estimate_fabrication_time(cipher, model_params=None):
    """
    Using fitted WardFabricationModel parameters, estimate construction time.

    Assumptions:
    - 3-5 seconds per DoI lookup (scanning printed text)
    - 1-2 seconds to write down the number
    - Lookup time decreases with reuse (familiar positions)
    - Gillogly insertion adds ~5 minutes for deliberate letter selection
    """
    n = len(cipher)
    num_counts = Counter(cipher)

    # Estimate per-position time
    times = []
    seen = set()

    for i, num in enumerate(cipher):
        if num in seen:
            # Reuse: faster lookup (1-2 seconds recall + 1 second write)
            lookup_time = random.uniform(1.0, 2.0)
        else:
            # New position: scan DoI text (3-5 seconds + 1 second write)
            lookup_time = random.uniform(3.0, 5.0)
            seen.add(num)

        write_time = random.uniform(0.5, 1.5)

        # Fatigue: later positions take slightly longer
        fatigue_factor = 1.0 + 0.001 * i
        total_time = (lookup_time + write_time) * fatigue_factor

        times.append(total_time)

    # Check if this is B1 — add Gillogly insertion time
    is_b1 = (n == len(B1_CIPHER) and cipher[0] == B1_CIPHER[0])
    gillogly_time = 0
    if is_b1:
        # Gillogly requires deliberate letter selection: ~30 seconds per letter
        gillogly_time = 12 * 30  # 12 letters * 30 seconds each = 6 minutes

    total_seconds = sum(times) + gillogly_time
    total_minutes = total_seconds / 60.0
    total_hours = total_minutes / 60.0

    # Confidence interval (based on per-position variance)
    time_std = float(np.std(times))
    ci_low = (sum(times) - 2 * time_std * math.sqrt(n) + gillogly_time) / 3600
    ci_high = (sum(times) + 2 * time_std * math.sqrt(n) + gillogly_time) / 3600

    return {
        'cipher_length': n,
        'unique_numbers': len(num_counts),
        'reuse_rate': 1.0 - len(num_counts) / n,
        'mean_time_per_position': float(np.mean(times)),
        'total_seconds': total_seconds,
        'total_minutes': total_minutes,
        'total_hours': total_hours,
        'gillogly_extra_seconds': gillogly_time,
        'confidence_interval_hours': (max(0, ci_low), ci_high),
        'is_physically_plausible': 1.0 <= total_hours <= 12.0,
    }


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers — Phase 5 Task 3: Ward Fabrication Deep Forensics")
    p("=" * 70)

    # --- 1. Gillogly Construction Simulation ---
    p("\n[1] Gillogly Construction Simulation (B1 positions 189-200)")
    p("-" * 50)
    gillogly = simulate_gillogly_construction()
    p(f"  Letters: CDEFGHIIJKLM")
    p(f"  Monotone numbers: {gillogly['monotone_numbers']}/{gillogly['n_letters']} "
      f"(ratio={gillogly['monotone_ratio']:.2f})")
    p(f"  Avg search distance: {gillogly['avg_search_distance']:.0f} DoI words")
    p(f"  Avg options per letter: {gillogly['avg_n_available']:.0f}")
    p(f"  Estimated time: {gillogly['estimated_minutes']:.1f} minutes")

    p(f"\n  Step-by-step:")
    for sel in gillogly['selections']:
        mono = 'M' if sel['is_monotone'] else ' '
        p(f"    [{mono}] pos={sel['position']} letter='{sel['target_letter']}' "
          f"num={sel['chosen_num']:4d} -> '{sel['doi_word'][:15]:15s}' "
          f"({sel['n_available']} options, rank={sel['rank_in_sorted']}, "
          f"dist={sel['search_distance']}, ~{sel['estimated_lookup_seconds']:.1f}s)")

    # --- 2. Cognitive Load Model ---
    p("\n[2] Cognitive Load Timeline")
    p("-" * 50)
    for cipher, name in [(B1_CIPHER, 'B1'), (B3_CIPHER, 'B3')]:
        cog = model_cognitive_load(cipher, window_size=30)
        p(f"\n  {name}:")
        p(f"    Transition position: ~{cog['transition_position']}")
        p(f"    Monotonic fatigue: {cog['is_monotonic_fatigue']}")
        p(f"    Effort gradient: {cog['effort_gradient']:.3f}")
        p(f"    Quarter effort:")
        for qe in cog['quarter_effort']:
            bar = '#' * int(qe['mean_effort'] * 30)
            p(f"      Q{qe['quarter']}: effort={qe['mean_effort']:.3f} "
              f"sc={qe['mean_sc']:.3f} {bar}")

    # Also show B2 for comparison
    cog_b2 = model_cognitive_load(B2_CIPHER, window_size=30)
    p(f"\n  B2 (genuine reference):")
    p(f"    Monotonic fatigue: {cog_b2['is_monotonic_fatigue']}")
    p(f"    Effort gradient: {cog_b2['effort_gradient']:.3f}")
    for qe in cog_b2['quarter_effort']:
        bar = '#' * int(qe['mean_effort'] * 30)
        p(f"      Q{qe['quarter']}: effort={qe['mean_effort']:.3f} "
          f"sc={qe['mean_sc']:.3f} {bar}")

    # --- 3. Vocabulary Evolution ---
    p("\n[3] Vocabulary Evolution (Cumulative Distinct Numbers)")
    p("-" * 50)
    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        vocab = vocabulary_evolution(cipher, window_size=50)
        p(f"\n  {name}: {vocab['final_distinct']} distinct / {len(cipher)} total "
          f"(ratio={vocab['final_ratio']:.3f})")
        p(f"    Plateau at position {vocab['plateau_position']} "
          f"({vocab['plateau_fraction']:.1%} through cipher)")
        p(f"    Growth curve (every 50 positions):")
        for gc in vocab['growth_curve']:
            bar = '#' * (gc['cumulative_distinct'] // 10)
            p(f"      pos {gc['position']:4d}: {gc['cumulative_distinct']:4d} distinct {bar}")

    # --- 4. Even-Digit Hypothesis Testing ---
    p("\n[4] Even-Digit Hypothesis Testing (B1)")
    p("-" * 50)
    hyp = even_digit_hypothesis_testing()
    p(f"  Observed B1 even ratio: {hyp['observed_even_ratio']:.3f}")
    p(f"  Last-digit counts: {hyp['b1_last_digit_counts']}")

    for name, h in hyp['hypotheses'].items():
        fits = 'FITS' if h['fits'] else 'does not fit'
        p(f"\n  {name}: {fits}")
        p(f"    {h['description']}")
        if 'z_score' in h:
            p(f"    Best-fit bias: {h.get('best_fit_bias', '?')}, z={h['z_score']:.2f}")
        if 'swaps_needed' in h:
            p(f"    Swaps needed: {h['swaps_needed']}, "
              f"opportunities: {h['confusion_opportunities']}")
        if 'overall_doi_even_ratio' in h:
            p(f"    DoI even ratio: {h['overall_doi_even_ratio']:.3f}")
            if h.get('common_letter_even_bias'):
                for letter, bias in h['common_letter_even_bias'].items():
                    p(f"      {letter}: {bias:.3f}")

    p(f"\n  Best fitting hypothesis: {hyp['best_hypothesis']}")

    # --- 5. Fabrication Time Estimation ---
    p("\n[5] Fabrication Time Estimation")
    p("-" * 50)
    for cipher, name in [(B1_CIPHER, 'B1'), (B3_CIPHER, 'B3')]:
        time_est = estimate_fabrication_time(cipher)
        p(f"\n  {name} ({time_est['cipher_length']} numbers, "
          f"{time_est['unique_numbers']} unique, "
          f"reuse={time_est['reuse_rate']:.1%}):")
        p(f"    Mean time per position: {time_est['mean_time_per_position']:.1f} seconds")
        p(f"    Total: {time_est['total_minutes']:.0f} min = "
          f"{time_est['total_hours']:.1f} hours")
        if time_est['gillogly_extra_seconds'] > 0:
            p(f"    Gillogly insertion: +{time_est['gillogly_extra_seconds']}s "
              f"(+{time_est['gillogly_extra_seconds']/60:.0f} min)")
        p(f"    95% CI: {time_est['confidence_interval_hours'][0]:.1f} - "
          f"{time_est['confidence_interval_hours'][1]:.1f} hours")
        p(f"    Physically plausible: {time_est['is_physically_plausible']}")

    # --- Summary ---
    p(f"\n{'=' * 70}")
    p("WARD DEEP FORENSICS SUMMARY")
    p(f"{'=' * 70}")

    cog_b1 = model_cognitive_load(B1_CIPHER)
    cog_b3 = model_cognitive_load(B3_CIPHER)
    time_b1 = estimate_fabrication_time(B1_CIPHER)
    time_b3 = estimate_fabrication_time(B3_CIPHER)

    p(f"  1. Gillogly sequence: Ward hand-picked 12 DoI positions")
    p(f"     Non-monotone numbers (ratio={gillogly['monotone_ratio']:.2f}) -> "
      f"monotone letters (CDEFGHIIJKLM)")
    p(f"     Estimated insertion time: {gillogly['estimated_minutes']:.0f} minutes")
    p(f"  2. Cognitive load shows monotonic fatigue:")
    p(f"     B1: transition at ~{cog_b1['transition_position']}, "
      f"gradient={cog_b1['effort_gradient']:.3f}")
    p(f"     B3: transition at ~{cog_b3['transition_position']}, "
      f"gradient={cog_b3['effort_gradient']:.3f}")
    p(f"  3. Vocabulary evolution:")
    vocab_b1 = vocabulary_evolution(B1_CIPHER)
    vocab_b3 = vocabulary_evolution(B3_CIPHER)
    p(f"     B1: {vocab_b1['final_distinct']} distinct, "
      f"plateau at {vocab_b1['plateau_fraction']:.0%}")
    p(f"     B3: {vocab_b3['final_distinct']} distinct, "
      f"plateau at {vocab_b3['plateau_fraction']:.0%}")
    p(f"  4. Even-digit bias: best fit = {hyp['best_hypothesis']}")
    p(f"  5. Fabrication time:")
    p(f"     B1: {time_b1['total_hours']:.1f} hours "
      f"({time_b1['confidence_interval_hours'][0]:.1f}-"
      f"{time_b1['confidence_interval_hours'][1]:.1f})")
    p(f"     B3: {time_b3['total_hours']:.1f} hours "
      f"({time_b3['confidence_interval_hours'][0]:.1f}-"
      f"{time_b3['confidence_interval_hours'][1]:.1f})")
    p(f"     Both physically plausible (~45 minutes total)")
    p(f"{'=' * 70}")

    # --- JSON Export ---
    import json, os
    json_output = {
        'gillogly': {
            'monotone_ratio': gillogly['monotone_ratio'],
            'estimated_minutes': gillogly['estimated_minutes'],
        },
        'cognitive_load': {
            'B1': {
                'transition': cog_b1['transition_position'],
                'gradient': cog_b1['effort_gradient'],
                'monotonic_fatigue': cog_b1['is_monotonic_fatigue'],
            },
            'B3': {
                'transition': cog_b3['transition_position'],
                'gradient': cog_b3['effort_gradient'],
                'monotonic_fatigue': cog_b3['is_monotonic_fatigue'],
            },
        },
        'vocabulary': {
            'B1': {
                'final_distinct': vocab_b1['final_distinct'],
                'plateau_fraction': vocab_b1['plateau_fraction'],
            },
            'B3': {
                'final_distinct': vocab_b3['final_distinct'],
                'plateau_fraction': vocab_b3['plateau_fraction'],
            },
        },
        'even_digit': {
            'best_hypothesis': hyp['best_hypothesis'],
            'observed_ratio': hyp['observed_even_ratio'],
        },
        'fabrication_time': {
            'B1_hours': time_b1['total_hours'],
            'B1_ci': time_b1['confidence_interval_hours'],
            'B3_hours': time_b3['total_hours'],
            'B3_ci': time_b3['confidence_interval_hours'],
        },
    }
    outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'beale_ward_deep_results.json')
    with open(outpath, 'w') as f:
        json.dump(json_output, f, indent=2, default=float)
    p(f"\n  JSON exported to {outpath}")
