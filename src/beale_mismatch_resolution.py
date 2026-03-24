"""
Beale Ciphers — Phase 5 Task 1: Exhaustive Mismatch Resolution

Systematically resolve all 22 B2 mismatches via:
  1. NW alignment to catalog exact mismatches
  2. Group classification (95->U, 84->E, 811->Y, 1005->X, orphans)
  3. Digit transposition testing for orphan errors
  4. Single-digit error testing (typographic confusion)
  5. Off-by-n miscounting tests
  6. Corrected accuracy computation

Usage: python beale_mismatch_resolution.py
"""

import re
from collections import Counter, defaultdict
from itertools import permutations

from beale_data import (
    B2_CIPHER, B2_PLAINTEXT, DOI_WORDS, BEALE_DOI_OFFSET, beale_decode
)
from beale_b2_decrypt import _needleman_wunsch
from beale_typography import build_confusion_matrix


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ===========================================================================
# 1. Catalog All Mismatches via NW Alignment
# ===========================================================================

def catalog_all_mismatches():
    """
    Use Needleman-Wunsch alignment to get the exact list of all mismatches
    between the B2 decode (with offsets) and the known plaintext.

    Returns list of mismatch dicts with cipher position, cipher number,
    decoded letter, expected letter, and offset.
    """
    plain_alpha = ''.join(c.upper() for c in B2_PLAINTEXT if c.isalpha())
    decoded_str = beale_decode(B2_CIPHER, DOI_WORDS, use_beale_offset=True)

    aligned_dec, aligned_plain, _ = _needleman_wunsch(
        decoded_str, plain_alpha, match=2, mismatch=-1, gap=-1
    )

    mismatches = []
    matches = 0
    dec_idx = 0  # index into decoded_str (cipher position)

    for k in range(len(aligned_dec)):
        ad = aligned_dec[k]
        ap = aligned_plain[k]

        if ad == '-':
            # Gap in decoded = extra plaintext char (not a mismatch)
            continue
        if ap == '-':
            # Gap in plaintext = extra decoded char
            dec_idx += 1
            continue

        cipher_pos = dec_idx
        cipher_num = B2_CIPHER[cipher_pos] if cipher_pos < len(B2_CIPHER) else -1
        offset = BEALE_DOI_OFFSET.get(cipher_num, 0)
        doi_idx = cipher_num - 1 + offset
        doi_word = DOI_WORDS[doi_idx] if 0 <= doi_idx < len(DOI_WORDS) else '?'

        if ad == ap:
            matches += 1
        else:
            mismatches.append({
                'cipher_pos': cipher_pos,
                'cipher_num': cipher_num,
                'offset': offset,
                'doi_idx': doi_idx,
                'doi_word': doi_word,
                'decoded_letter': ad,
                'expected_letter': ap,
            })
        dec_idx += 1

    total = matches + len(mismatches)
    return {
        'mismatches': mismatches,
        'total_aligned': total,
        'matches': matches,
        'mismatch_count': len(mismatches),
        'accuracy': matches / total if total > 0 else 0.0,
    }


# ===========================================================================
# 2. Classify Mismatch Groups
# ===========================================================================

def classify_mismatch_groups(mismatches):
    """
    Group mismatches into known clusters:
      Group A (num=95, 3x): "inalienable" -> "Unalienable" (Dunlap spelling)
      Group B (num=84, 2x): off-by-1 -> "equal" not "created"
      Group C (num=811, 9x): C->Y, edition word difference
      Group D (num=1005, 4x): W->X, no X-words in standard DoI
      Orphans: individual transcription errors
    """
    groups = {
        'A_unalienable': [],   # num=95
        'B_off_by_one': [],    # num=84
        'C_y_word': [],        # num=811
        'D_x_word': [],        # num=1005
        'orphans': [],
    }

    for mm in mismatches:
        num = mm['cipher_num']
        if num == 95:
            groups['A_unalienable'].append(mm)
        elif num == 84:
            groups['B_off_by_one'].append(mm)
        elif num == 811:
            groups['C_y_word'].append(mm)
        elif num == 1005:
            groups['D_x_word'].append(mm)
        else:
            groups['orphans'].append(mm)

    # Analyze each group
    analysis = {}

    # Group A: All 3 uses of 95 want U, standard DoI word 95 = "inalienable" (I)
    # Dunlap broadside uses "unalienable" -> starts with U
    if groups['A_unalienable']:
        expected = [m['expected_letter'] for m in groups['A_unalienable']]
        analysis['A_unalienable'] = {
            'count': len(groups['A_unalienable']),
            'expected_letters': expected,
            'all_want_U': all(e == 'U' for e in expected),
            'explanation': 'Dunlap broadside spelling "unalienable" (U) vs standard "inalienable" (I)',
            'status': 'SOLVED',
        }

    # Group B: num=84, standard word = "created" (C), some uses want E
    # word 85 = "equal" (E) -> off-by-1 counting error
    if groups['B_off_by_one']:
        expected = [m['expected_letter'] for m in groups['B_off_by_one']]
        analysis['B_off_by_one'] = {
            'count': len(groups['B_off_by_one']),
            'expected_letters': expected,
            'standard_word_84': DOI_WORDS[83] if len(DOI_WORDS) > 83 else '?',
            'standard_word_85': DOI_WORDS[84] if len(DOI_WORDS) > 84 else '?',
            'explanation': 'Off-by-1 miscount: word 84="created" (C), word 85="equal" (E)',
            'status': 'SOLVED',
        }

    # Group C: num=811, all but one want Y
    if groups['C_y_word']:
        expected = [m['expected_letter'] for m in groups['C_y_word']]
        analysis['C_y_word'] = {
            'count': len(groups['C_y_word']),
            'expected_letters': expected,
            'want_Y': sum(1 for e in expected if e == 'Y'),
            'want_other': [(m['cipher_pos'], m['expected_letter'])
                          for m in groups['C_y_word'] if m['expected_letter'] != 'Y'],
            'standard_word_811': DOI_WORDS[810] if len(DOI_WORDS) > 810 else '?',
            'explanation': 'Beale\'s edition had a Y-word at position 811 instead of standard word',
            'status': 'EDITION_DIFFERENCE',
        }

    # Group D: num=1005, all want X, NO X-words in standard DoI
    if groups['D_x_word']:
        expected = [m['expected_letter'] for m in groups['D_x_word']]
        analysis['D_x_word'] = {
            'count': len(groups['D_x_word']),
            'expected_letters': expected,
            'all_want_X': all(e == 'X' for e in expected),
            'x_words_in_doi': sum(1 for w in DOI_WORDS if w[0].upper() == 'X'),
            'explanation': 'Beale\'s edition extended beyond standard DoI body with X-word at pos 1005',
            'status': 'EDITION_DIFFERENCE',
        }

    # Orphans
    if groups['orphans']:
        analysis['orphans'] = {
            'count': len(groups['orphans']),
            'details': [{
                'cipher_pos': m['cipher_pos'],
                'cipher_num': m['cipher_num'],
                'decoded': m['decoded_letter'],
                'expected': m['expected_letter'],
                'doi_word': m['doi_word'],
            } for m in groups['orphans']],
            'status': 'UNRESOLVED',
        }

    return {
        'groups': groups,
        'analysis': analysis,
        'systematic_count': sum(len(v) for k, v in groups.items() if k != 'orphans'),
        'orphan_count': len(groups['orphans']),
    }


# ===========================================================================
# 3. Digit Transposition Testing
# ===========================================================================

def test_digit_transpositions(cipher_num, expected_letter, doi_words=None):
    """
    For an orphan mismatch, test all digit permutations of the cipher number.
    Check if any transposed number decodes to the expected letter.

    Tests:
      - Digit reversal (29 <-> 92)
      - All permutations of digits (ABC -> ACB, BAC, BCA, CAB, CBA)
    """
    words = doi_words or DOI_WORDS
    digits = list(str(cipher_num))
    results = []

    # Generate all unique permutations
    seen = set()
    for perm in permutations(digits):
        candidate_str = ''.join(perm)
        if candidate_str.startswith('0'):
            continue  # No leading zeros
        candidate = int(candidate_str)
        if candidate == cipher_num or candidate in seen:
            continue
        seen.add(candidate)

        # Check what this number decodes to
        # Try with various offsets
        for off in [0, BEALE_DOI_OFFSET.get(candidate, 0)]:
            idx = candidate - 1 + off
            if 0 <= idx < len(words):
                letter = words[idx][0].upper()
                if letter == expected_letter:
                    results.append({
                        'transposed_num': candidate,
                        'offset_used': off,
                        'doi_word': words[idx],
                        'decoded_letter': letter,
                        'transposition_type': _classify_transposition(cipher_num, candidate),
                    })

    # Also test simple digit reversal explicitly
    reversed_str = ''.join(reversed(digits))
    if not reversed_str.startswith('0'):
        reversed_num = int(reversed_str)
        if reversed_num != cipher_num:
            for off in [0, BEALE_DOI_OFFSET.get(reversed_num, 0)]:
                idx = reversed_num - 1 + off
                if 0 <= idx < len(words):
                    letter = words[idx][0].upper()
                    # Already captured in permutations, just flag it
                    pass

    return {
        'cipher_num': cipher_num,
        'expected_letter': expected_letter,
        'candidates': results,
        'n_candidates': len(results),
        'resolved': len(results) > 0,
    }


def _classify_transposition(original, transposed):
    """Classify the type of digit transposition."""
    orig_s = str(original)
    trans_s = str(transposed)

    if trans_s == orig_s[::-1]:
        return 'full_reversal'

    # Check if it's an adjacent swap
    if len(orig_s) == len(trans_s):
        diffs = [(i, orig_s[i], trans_s[i]) for i in range(len(orig_s))
                 if orig_s[i] != trans_s[i]]
        if len(diffs) == 2:
            i1, i2 = diffs[0][0], diffs[1][0]
            if abs(i1 - i2) == 1:
                return 'adjacent_swap'
            return 'digit_swap'

    return 'permutation'


# ===========================================================================
# 4. Single-Digit Error Testing
# ===========================================================================

def test_single_digit_errors(cipher_num, expected_letter, doi_words=None):
    """
    Replace each digit with 0-9, prioritizing typographic confusion pairs.
    Check if DOI_WORDS[candidate - 1 + offset] starts with expected letter.

    Prioritized confusion pairs from beale_typography:
      1/7, 3/8, 5/6, 0/6, 6/9
    """
    words = doi_words or DOI_WORDS
    digits = list(str(cipher_num))
    results = []

    # Confusion pairs (from beale_typography.build_confusion_matrix)
    confusion_priority = {
        '1': ['7', '4'],
        '7': ['1'],
        '3': ['8'],
        '8': ['3'],
        '5': ['6'],
        '6': ['5', '0', '9'],
        '0': ['6', '9'],
        '9': ['6', '0'],
        '4': ['1'],
        '2': [],
    }

    for pos in range(len(digits)):
        original_digit = digits[pos]

        # Test confusion pairs first, then all others
        test_order = confusion_priority.get(original_digit, []) + \
                     [str(d) for d in range(10) if str(d) not in
                      confusion_priority.get(original_digit, []) and
                      str(d) != original_digit]

        for new_digit in test_order:
            if new_digit == original_digit:
                continue
            new_digits = digits.copy()
            new_digits[pos] = new_digit
            candidate_str = ''.join(new_digits)
            if candidate_str.startswith('0') and len(candidate_str) > 1:
                continue
            candidate = int(candidate_str)

            for off in [0, BEALE_DOI_OFFSET.get(candidate, 0)]:
                idx = candidate - 1 + off
                if 0 <= idx < len(words):
                    letter = words[idx][0].upper()
                    if letter == expected_letter:
                        is_confusion = new_digit in confusion_priority.get(original_digit, [])
                        results.append({
                            'candidate_num': candidate,
                            'digit_position': pos,
                            'original_digit': original_digit,
                            'new_digit': new_digit,
                            'offset_used': off,
                            'doi_word': words[idx],
                            'decoded_letter': letter,
                            'is_confusion_pair': is_confusion,
                            'confusion_type': (f'{original_digit}<->{new_digit} '
                                             f'(typographic confusion)' if is_confusion
                                             else f'{original_digit}->{new_digit}'),
                        })

    return {
        'cipher_num': cipher_num,
        'expected_letter': expected_letter,
        'candidates': results,
        'n_candidates': len(results),
        'confusion_pair_matches': sum(1 for r in results if r['is_confusion_pair']),
        'resolved': len(results) > 0,
        'best_candidate': _pick_best_single_digit(results) if results else None,
    }


def _pick_best_single_digit(candidates):
    """Pick the most likely correction: prefer confusion pairs, then smallest change."""
    confusion = [c for c in candidates if c['is_confusion_pair']]
    if confusion:
        return confusion[0]
    return candidates[0] if candidates else None


# ===========================================================================
# 5. Off-by-N Testing
# ===========================================================================

def test_off_by_n(cipher_num, expected_letter, max_n=20, doi_words=None):
    """
    Test if cipher_num ± 1..max_n gives the expected letter.
    This models Beale miscounting when looking up a DoI word.
    """
    words = doi_words or DOI_WORDS
    results = []

    for n in range(1, max_n + 1):
        for sign in [+1, -1]:
            candidate = cipher_num + sign * n
            if candidate < 1:
                continue

            for off in [0, BEALE_DOI_OFFSET.get(candidate, 0)]:
                idx = candidate - 1 + off
                if 0 <= idx < len(words):
                    letter = words[idx][0].upper()
                    if letter == expected_letter:
                        results.append({
                            'candidate_num': candidate,
                            'offset_n': sign * n,
                            'offset_used': off,
                            'doi_word': words[idx],
                            'decoded_letter': letter,
                            'miscount_type': f'{"over" if sign > 0 else "under"}count by {n}',
                        })

    return {
        'cipher_num': cipher_num,
        'expected_letter': expected_letter,
        'candidates': results,
        'n_candidates': len(results),
        'resolved': len(results) > 0,
        'best_candidate': results[0] if results else None,  # smallest offset first
    }


# ===========================================================================
# 6. Comprehensive Orphan Resolution
# ===========================================================================

def resolve_orphans(orphan_mismatches):
    """
    Apply all three correction methods to each orphan mismatch.
    Rank candidates by plausibility:
      1. Typographic confusion pair (single digit)
      2. Off-by-1 miscount
      3. Adjacent digit swap
      4. Off-by-2..5
      5. Other single-digit change
      6. Digit permutation
    """
    resolutions = []

    for mm in orphan_mismatches:
        cipher_num = mm['cipher_num']
        expected = mm['expected_letter']

        trans = test_digit_transpositions(cipher_num, expected)
        single = test_single_digit_errors(cipher_num, expected)
        off_n = test_off_by_n(cipher_num, expected)

        # Collect all candidates with source tags
        all_candidates = []

        for c in trans['candidates']:
            all_candidates.append({
                **c, 'method': 'transposition',
                'plausibility': 3 if c['transposition_type'] == 'adjacent_swap' else 5,
            })

        for c in single['candidates']:
            plaus = 1 if c['is_confusion_pair'] else 4
            all_candidates.append({
                **c, 'method': 'single_digit',
                'plausibility': plaus,
            })

        for c in off_n['candidates']:
            n = abs(c['offset_n'])
            plaus = 2 if n == 1 else (3 if n <= 5 else 6)
            all_candidates.append({
                **c, 'method': f'off_by_{n}',
                'plausibility': plaus,
            })

        # Sort by plausibility (lower = more likely)
        all_candidates.sort(key=lambda x: x['plausibility'])

        best = all_candidates[0] if all_candidates else None

        resolutions.append({
            'cipher_pos': mm['cipher_pos'],
            'cipher_num': cipher_num,
            'decoded_letter': mm['decoded_letter'],
            'expected_letter': expected,
            'doi_word': mm['doi_word'],
            'n_candidates': len(all_candidates),
            'best_correction': best,
            'all_candidates': all_candidates[:5],  # top 5
            'resolved': best is not None,
        })

    return resolutions


# ===========================================================================
# 7. Compute Corrected Accuracy
# ===========================================================================

def compute_corrected_accuracy(catalog_result, group_result, orphan_resolutions):
    """
    Apply all corrections and compute final accuracy:
      - Group A: 95 -> U (3 fixed)
      - Group B: 84 -> E (2 fixed)
      - Group C: 811 -> Y (8-9 fixed, edition difference)
      - Group D: 1005 -> X (4 fixed, edition difference)
      - Orphans: per individual resolution
    """
    total = catalog_result['total_aligned']
    original_matches = catalog_result['matches']
    original_mismatches = catalog_result['mismatch_count']

    # Group fixes
    group_a_fixed = len(group_result['groups']['A_unalienable'])
    group_b_fixed = len(group_result['groups']['B_off_by_one'])
    group_c_fixed = sum(1 for m in group_result['groups']['C_y_word']
                       if m['expected_letter'] == 'Y')
    group_d_fixed = len(group_result['groups']['D_x_word'])

    # Orphan fixes
    orphan_fixed = sum(1 for r in orphan_resolutions if r['resolved'])
    orphan_total = len(orphan_resolutions)

    systematic_fixed = group_a_fixed + group_b_fixed + group_c_fixed + group_d_fixed
    total_fixed = systematic_fixed + orphan_fixed
    remaining = original_mismatches - total_fixed

    corrected_matches = original_matches + total_fixed
    corrected_accuracy = corrected_matches / total if total > 0 else 0.0

    return {
        'original_accuracy': original_matches / total if total > 0 else 0.0,
        'corrected_accuracy': corrected_accuracy,
        'original_matches': original_matches,
        'corrected_matches': corrected_matches,
        'total': total,
        'original_mismatches': original_mismatches,
        'fixes': {
            'group_A_unalienable': group_a_fixed,
            'group_B_off_by_one': group_b_fixed,
            'group_C_y_word': group_c_fixed,
            'group_D_x_word': group_d_fixed,
            'orphans_resolved': orphan_fixed,
            'orphans_total': orphan_total,
        },
        'total_fixed': total_fixed,
        'remaining_mismatches': remaining,
    }


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers — Phase 5 Task 1: Exhaustive Mismatch Resolution")
    p("=" * 70)

    # --- 1. Catalog all mismatches ---
    p("\n[1] Cataloging All Mismatches (NW Alignment)")
    p("-" * 50)
    catalog = catalog_all_mismatches()
    p(f"  Total aligned positions: {catalog['total_aligned']}")
    p(f"  Matches: {catalog['matches']}")
    p(f"  Mismatches: {catalog['mismatch_count']}")
    p(f"  Accuracy: {catalog['accuracy']:.1%}")

    p(f"\n  All mismatches:")
    for mm in catalog['mismatches']:
        p(f"    pos={mm['cipher_pos']:3d} num={mm['cipher_num']:4d} "
          f"off={mm['offset']:+3d} word='{mm['doi_word'][:15]:15s}' "
          f"got={mm['decoded_letter']} want={mm['expected_letter']}")

    # --- 2. Classify mismatch groups ---
    p("\n[2] Mismatch Group Classification")
    p("-" * 50)
    groups = classify_mismatch_groups(catalog['mismatches'])
    p(f"  Systematic mismatches: {groups['systematic_count']}")
    p(f"  Orphan mismatches: {groups['orphan_count']}")

    for name, analysis in groups['analysis'].items():
        p(f"\n  {name}:")
        for k, v in analysis.items():
            if k == 'details':
                for d in v:
                    p(f"    num={d['cipher_num']:4d} got={d['decoded']} "
                      f"want={d['expected']} word='{d['doi_word'][:15]}'")
            else:
                p(f"    {k}: {v}")

    # --- 3. Resolve orphan mismatches ---
    p("\n[3] Orphan Mismatch Resolution")
    p("-" * 50)
    orphans = groups['groups']['orphans']
    resolutions = resolve_orphans(orphans)

    for res in resolutions:
        status = "RESOLVED" if res['resolved'] else "UNRESOLVED"
        p(f"\n  num={res['cipher_num']:4d} (pos={res['cipher_pos']}) "
          f"got={res['decoded_letter']} want={res['expected_letter']} "
          f"[{status}]")

        if res['best_correction']:
            bc = res['best_correction']
            method = bc.get('method', '?')
            if 'candidate_num' in bc:
                p(f"    Best: {method} -> num={bc['candidate_num']} "
                  f"'{bc.get('doi_word', '?')}' "
                  f"plausibility={bc.get('plausibility', '?')}")
            elif 'transposed_num' in bc:
                p(f"    Best: {method} -> num={bc['transposed_num']} "
                  f"'{bc.get('doi_word', '?')}' ({bc.get('transposition_type', '?')})")

        if res['all_candidates']:
            p(f"    All candidates ({res['n_candidates']} total):")
            for c in res['all_candidates'][:3]:
                num_key = 'candidate_num' if 'candidate_num' in c else 'transposed_num'
                p(f"      {c['method']:20s} num={c.get(num_key, '?'):>5} "
                  f"'{c.get('doi_word', '?')[:12]:12s}' "
                  f"plausibility={c.get('plausibility', '?')}")

    # --- 4. Individual orphan deep-dive ---
    p("\n[4] Orphan Deep-Dive: Transposition, Single-Digit, Off-by-N")
    p("-" * 50)
    for mm in orphans:
        num = mm['cipher_num']
        exp = mm['expected_letter']
        p(f"\n  === num={num} (want '{exp}', have '{mm['decoded_letter']}') ===")

        trans = test_digit_transpositions(num, exp)
        if trans['candidates']:
            p(f"    Transpositions: {trans['n_candidates']} match(es)")
            for c in trans['candidates'][:3]:
                p(f"      {c['transposed_num']} ({c['transposition_type']}) "
                  f"-> '{c['doi_word']}'")
        else:
            p(f"    Transpositions: none")

        single = test_single_digit_errors(num, exp)
        if single['candidates']:
            p(f"    Single-digit errors: {single['n_candidates']} "
              f"({single['confusion_pair_matches']} confusion pairs)")
            for c in single['candidates'][:3]:
                p(f"      {num}->{c['candidate_num']} "
                  f"(digit[{c['digit_position']}]: {c['original_digit']}->{c['new_digit']}) "
                  f"-> '{c['doi_word']}' {'*CONFUSION*' if c['is_confusion_pair'] else ''}")
        else:
            p(f"    Single-digit errors: none")

        off = test_off_by_n(num, exp, max_n=10)
        if off['candidates']:
            p(f"    Off-by-N: {off['n_candidates']} match(es)")
            for c in off['candidates'][:3]:
                p(f"      {num}{c['offset_n']:+d}={c['candidate_num']} "
                  f"-> '{c['doi_word']}' ({c['miscount_type']})")
        else:
            p(f"    Off-by-N (±10): none")

    # --- 5. Corrected accuracy ---
    p("\n[5] Corrected Accuracy")
    p("-" * 50)
    accuracy = compute_corrected_accuracy(catalog, groups, resolutions)

    p(f"  Original accuracy:  {accuracy['original_accuracy']:.1%} "
      f"({accuracy['original_matches']}/{accuracy['total']})")
    p(f"  Fixes applied:")
    for name, count in accuracy['fixes'].items():
        p(f"    {name}: {count}")
    p(f"  Total fixed: {accuracy['total_fixed']}")
    p(f"  Remaining mismatches: {accuracy['remaining_mismatches']}")
    p(f"  Corrected accuracy: {accuracy['corrected_accuracy']:.1%} "
      f"({accuracy['corrected_matches']}/{accuracy['total']})")

    # --- Summary ---
    p(f"\n{'=' * 70}")
    p("MISMATCH RESOLUTION SUMMARY")
    p(f"{'=' * 70}")
    p(f"  Original: {catalog['mismatch_count']} mismatches "
      f"({catalog['accuracy']:.1%} accuracy)")
    p(f"  Group A (95->U, Dunlap spelling): {accuracy['fixes']['group_A_unalienable']} SOLVED")
    p(f"  Group B (84->E, off-by-1): {accuracy['fixes']['group_B_off_by_one']} SOLVED")
    p(f"  Group C (811->Y, Y-word edition): {accuracy['fixes']['group_C_y_word']} EDITION")
    p(f"  Group D (1005->X, X-word edition): {accuracy['fixes']['group_D_x_word']} EDITION")
    p(f"  Orphans resolved: {accuracy['fixes']['orphans_resolved']}/{accuracy['fixes']['orphans_total']}")
    p(f"  Final: {accuracy['remaining_mismatches']} remaining "
      f"({accuracy['corrected_accuracy']:.1%} accuracy)")
    p(f"{'=' * 70}")
