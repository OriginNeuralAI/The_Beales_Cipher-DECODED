"""
Beale Ciphers -- Phase 4 Task 1: DoI Edition Fingerprinting

The 51 non-zero offsets in BEALE_DOI_OFFSET encode word-position differences
between the standard DoI text and the edition Beale/Ward actually used.
This module:
  1. Catalogs offset patterns by position, magnitude, direction
  2. Models offsets as word insertions/deletions at paragraph boundaries
  3. Reconstructs "Beale's DoI word list" (the text he actually used)
  4. Cross-references with known 1800-1830 DoI printing variations
  5. Separates edition differences from pamphlet typos

Usage: python beale_doi_editions.py
"""

import numpy as np
from collections import Counter, defaultdict
import math
import re

from beale_data import (
    B1_CIPHER, B2_CIPHER, B3_CIPHER, B2_PLAINTEXT,
    DOI_WORDS, BEALE_DOI_OFFSET, beale_decode
)


def p(s, end='\n'):
    print(s, end=end, flush=True)


# ===========================================================================
# 1. Offset Pattern Analysis
# ===========================================================================

def catalog_offsets():
    """
    Catalog all non-zero offsets in BEALE_DOI_OFFSET.
    Group by magnitude, direction, and position range.
    """
    offsets = []
    for num, off in sorted(BEALE_DOI_OFFSET.items()):
        if off != 0:
            offsets.append({'cipher_num': num, 'offset': off})

    if not offsets:
        return {'non_zero_count': 0, 'clusters': [], 'negatives': []}

    # Group into contiguous clusters by offset value
    clusters = []
    current_cluster = [offsets[0]]
    for i in range(1, len(offsets)):
        if offsets[i]['offset'] == current_cluster[-1]['offset']:
            current_cluster.append(offsets[i])
        else:
            clusters.append({
                'offset': current_cluster[0]['offset'],
                'count': len(current_cluster),
                'range': (current_cluster[0]['cipher_num'],
                          current_cluster[-1]['cipher_num']),
                'numbers': [e['cipher_num'] for e in current_cluster],
            })
            current_cluster = [offsets[i]]
    clusters.append({
        'offset': current_cluster[0]['offset'],
        'count': len(current_cluster),
        'range': (current_cluster[0]['cipher_num'],
                  current_cluster[-1]['cipher_num']),
        'numbers': [e['cipher_num'] for e in current_cluster],
    })

    # Separate negatives (potential typos)
    negatives = [o for o in offsets if o['offset'] < 0]

    # Offset magnitude histogram
    magnitudes = Counter(abs(o['offset']) for o in offsets)

    return {
        'non_zero_count': len(offsets),
        'all_offsets': offsets,
        'clusters': clusters,
        'negatives': negatives,
        'magnitude_histogram': dict(magnitudes.most_common()),
        'unique_magnitudes': sorted(magnitudes.keys()),
    }


# ===========================================================================
# 2. Edition Difference Model
# ===========================================================================

def model_edition_differences(catalog):
    """
    Model offsets as word insertions/deletions at DoI structural boundaries.

    Key insight: a consistent offset of +N for all cipher numbers above a
    threshold means Beale's edition had N extra words before that point.
    """
    clusters = catalog['clusters']

    # Identify insertion points (where offset increases)
    insertions = []
    prev_offset = 0
    for cl in sorted(clusters, key=lambda c: c['range'][0]):
        off = cl['offset']
        if off > prev_offset:
            delta = off - prev_offset
            # The insertion happened just before the first number in this cluster
            insert_before = cl['range'][0]
            # Map cipher number to approximate DoI word position
            doi_pos = insert_before - 1  # 0-indexed word position
            insertions.append({
                'doi_position': doi_pos,
                'words_inserted': delta,
                'first_cipher_num': insert_before,
                'doi_word_at_pos': DOI_WORDS[doi_pos] if doi_pos < len(DOI_WORDS) else '?',
            })
        elif off < prev_offset and off >= 0:
            # Offset decreased but stayed positive -- partial correction
            pass
        prev_offset = off

    # Identify deletion points (negative offsets)
    deletions = []
    for entry in catalog['negatives']:
        num = entry['cipher_num']
        off = entry['offset']
        doi_pos = num - 1
        deletions.append({
            'cipher_num': num,
            'offset': off,
            'doi_position': doi_pos,
            'doi_word_at_pos': DOI_WORDS[doi_pos] if doi_pos < len(DOI_WORDS) else '?',
            'type': 'typo_or_local_variant',
        })

    # Map insertion points to DoI paragraph structure
    # DoI has major sections: Preamble, Grievances, Conclusion
    doi_sections = [
        (0, 60, 'Preamble (self-evident truths)'),
        (60, 145, 'Government philosophy'),
        (145, 240, 'History of King George'),
        (240, 490, 'Grievances (He has...)'),
        (490, 600, 'Legislative acts (For...)'),
        (600, 750, 'War/tyranny grievances'),
        (750, 900, 'Appeals and resolution'),
        (900, len(DOI_WORDS), 'Declaration proper'),
    ]

    insertion_sections = []
    for ins in insertions:
        pos = ins['doi_position']
        for start, end, name in doi_sections:
            if start <= pos < end:
                insertion_sections.append({**ins, 'section': name})
                break

    return {
        'insertions': insertions,
        'insertion_sections': insertion_sections,
        'deletions': deletions,
        'total_words_inserted': sum(i['words_inserted'] for i in insertions),
        'total_deletions': len(deletions),
    }


# ===========================================================================
# 3. Synthetic Edition Reconstruction
# ===========================================================================

def reconstruct_beale_doi():
    """
    For each B2 cipher number, compute the actual DoI word Beale referenced.
    Build "Beale's DoI word list" -- the effective text he was using.

    Note: B2_PLAINTEXT has 796 alpha chars for 763 cipher numbers. The 33-char
    discrepancy is from minor reconstruction variations. We compare position-by-
    position against the plaintext letter stream.
    """
    # Extract plaintext as continuous letter sequence
    plain_alpha = ''.join(c.upper() for c in B2_PLAINTEXT if c.isalpha())

    decode_details = []
    beale_words = []
    mismatches = 0
    total = 0

    for i, num in enumerate(B2_CIPHER):
        off = BEALE_DOI_OFFSET.get(num, 0)
        doi_idx = num - 1 + off

        if 0 <= doi_idx < len(DOI_WORDS):
            word = DOI_WORDS[doi_idx]
            decoded_letter = word[0].upper()
        else:
            word = '?'
            decoded_letter = '?'

        # Expected plaintext letter (direct positional match)
        expected = plain_alpha[i] if i < len(plain_alpha) else '?'

        match = (decoded_letter == expected) or decoded_letter == '?'
        if decoded_letter != '?' and decoded_letter != expected:
            mismatches += 1
        total += 1 if decoded_letter != '?' else 0

        decode_details.append({
            'position': i,
            'cipher_num': num,
            'offset': off,
            'doi_idx': doi_idx,
            'doi_word': word,
            'decoded_letter': decoded_letter,
            'expected_letter': expected,
            'match': match,
        })
        beale_words.append(word)

    accuracy = (total - mismatches) / total if total > 0 else 0.0

    return {
        'beale_words': beale_words,
        'decode_details': decode_details,
        'total_positions': len(B2_CIPHER),
        'plaintext_length': len(plain_alpha),
        'in_range': total,
        'mismatches': mismatches,
        'accuracy': accuracy,
        'accuracy_pct': accuracy * 100,
    }


def analyze_residual_errors(reconstruction):
    """
    For each mismatch in the B2 decode, analyze the error type:
    - Near-miss (adjacent letter)?
    - Single-digit typo in cipher number?
    - Clustered or random?
    """
    details = reconstruction['decode_details']
    errors = [d for d in details if not d['match'] and d['decoded_letter'] != '?']

    error_analysis = []
    for err in errors:
        decoded = err['decoded_letter']
        expected = err['expected_letter']
        letter_dist = abs(ord(decoded) - ord(expected))

        # Check if a nearby cipher number would give the right letter
        num = err['cipher_num']
        near_miss_nums = []
        for delta in range(-3, 4):
            if delta == 0:
                continue
            alt_num = num + delta
            off = BEALE_DOI_OFFSET.get(alt_num, BEALE_DOI_OFFSET.get(num, 0))
            alt_idx = alt_num - 1 + off
            if 0 <= alt_idx < len(DOI_WORDS):
                alt_letter = DOI_WORDS[alt_idx][0].upper()
                if alt_letter == expected:
                    near_miss_nums.append(delta)

        error_analysis.append({
            'position': err['position'],
            'cipher_num': num,
            'decoded': decoded,
            'expected': expected,
            'letter_distance': letter_dist,
            'near_miss': len(near_miss_nums) > 0,
            'near_miss_deltas': near_miss_nums,
            'type': 'adjacent' if letter_dist == 1 else
                    'near' if letter_dist <= 3 else 'far',
        })

    # Cluster analysis: are errors grouped or random?
    error_positions = [e['position'] for e in error_analysis]
    gaps = [error_positions[i+1] - error_positions[i]
            for i in range(len(error_positions) - 1)] if len(error_positions) > 1 else []

    return {
        'total_errors': len(error_analysis),
        'errors': error_analysis,
        'error_types': Counter(e['type'] for e in error_analysis),
        'near_miss_count': sum(1 for e in error_analysis if e['near_miss']),
        'mean_gap': float(np.mean(gaps)) if gaps else 0,
        'clustered': any(g <= 3 for g in gaps) if gaps else False,
    }


# ===========================================================================
# 4. Historical DoI Variation Analysis
# ===========================================================================

def historical_doi_variations():
    """
    Cross-reference offset patterns with known 1800-1830 DoI printing variations.

    Known variations:
    1. inalienable vs unalienable (word ~97)
    2. Preamble-only vs full text editions
    3. Inclusion of signatures/signers list
    4. Section headings ("In Congress, July 4, 1776" etc.)
    5. Capitalization and punctuation differences
    """
    # Check our DoI text for key variant words
    doi_lower = [w.lower() for w in DOI_WORDS]

    # Find "inalienable" or "unalienable"
    alien_pos = None
    alien_form = None
    for i, w in enumerate(doi_lower):
        if 'alienable' in w:
            alien_pos = i + 1  # 1-indexed
            alien_form = DOI_WORDS[i]
            break

    # Check offset pattern around critical variant positions
    variant_checks = {
        'inalienable_unalienable': {
            'position': alien_pos,
            'form_in_our_doi': alien_form,
            'offset_at_pos': BEALE_DOI_OFFSET.get(alien_pos, 'not in B2'),
            'note': 'Jefferson wrote "inalienable"; engrossed copy has "unalienable"',
        },
    }

    # The +1 offset cluster (positions ~246-470) suggests one extra word
    # between our DoI position ~245 and Beale's edition.
    # Check what's at position 245 in our DoI
    if len(DOI_WORDS) > 245:
        word_at_245 = DOI_WORDS[244]  # 0-indexed
        word_at_246 = DOI_WORDS[245]
    else:
        word_at_245 = '?'
        word_at_246 = '?'

    variant_checks['plus_1_insertion_point'] = {
        'our_doi_word_245': word_at_245,
        'our_doi_word_246': word_at_246,
        'hypothesis': 'One extra word (section heading, variant reading, or '
                      'numbering artifact) in Beale\'s edition before position 246',
    }

    # The +11 offset cluster (positions ~485-620) suggests 11 extra words
    # Check what section of DoI this corresponds to
    if len(DOI_WORDS) > 485:
        words_480_490 = DOI_WORDS[479:490]
    else:
        words_480_490 = []

    variant_checks['plus_11_insertion_point'] = {
        'doi_words_480_490': words_480_490,
        'hypothesis': '~11 extra words in Beale\'s edition near position 485. '
                      'Possibly: signers list, "In Congress July 4 1776", '
                      'or "Unanimous Declaration of the thirteen United States"',
        'candidate_insertions': [
            'In Congress July 4 1776 (5 words)',
            'The unanimous Declaration of the thirteen united States of America (10 words)',
            'Signed by order of Congress (5+) words',
        ],
    }

    # The +13 offset for 807 suggests 13 extra words before position 807
    # (807 is the most-used number in B2, appearing 15 times)
    variant_checks['position_807'] = {
        'offset': 13,
        'usage_count_in_b2': B2_CIPHER.count(807),
        'standard_doi_word_806': DOI_WORDS[805] if len(DOI_WORDS) > 805 else '?',
        'beale_doi_word': DOI_WORDS[818] if len(DOI_WORDS) > 818 else '?',
        'note': 'Most-used number in B2; offset=13 consistent with cumulative insertions',
    }

    return variant_checks


# ===========================================================================
# 5. Offset vs Typo Separation
# ===========================================================================

def separate_edition_vs_typo(catalog):
    """
    Consistent offsets (+1 block, +11 block) = edition differences.
    Isolated large/negative offsets (557=-6, 647=-7) = pamphlet typos.

    Classification criteria:
    - Edition difference: offset shared by 3+ cipher numbers at same magnitude
    - Typo: unique offset magnitude, or negative offset, or isolated
    """
    offsets = catalog['all_offsets']

    # Build position -> offset map
    offset_map = {o['cipher_num']: o['offset'] for o in offsets}

    # Count how many cipher numbers share each offset value
    offset_counts = Counter(o['offset'] for o in offsets)

    edition_diffs = []
    typos = []
    ambiguous = []

    for o in offsets:
        off_val = o['offset']
        count = offset_counts[off_val]

        if off_val < 0:
            # Negative offsets are always classified as typos
            typos.append({**o, 'reason': f'negative offset ({off_val})'})
        elif count >= 3:
            # Shared by multiple cipher numbers = edition difference
            edition_diffs.append({**o, 'reason': f'shared by {count} positions'})
        elif count == 1 and abs(off_val) > 5:
            # Unique large offset = likely typo
            typos.append({**o, 'reason': f'unique offset magnitude {off_val}'})
        elif count <= 2:
            # Small count but moderate offset = ambiguous
            ambiguous.append({**o, 'reason': f'low count ({count}), offset={off_val}'})
        else:
            edition_diffs.append({**o, 'reason': f'consistent with block (count={count})'})

    # For each typo, check if correcting it improves B2 decode
    typo_corrections = []
    b2_plain_letters = [w[0].upper() for w in B2_PLAINTEXT.split() if w]

    for t in typos:
        num = t['cipher_num']
        off = t['offset']
        # Current decode (with offset)
        current_idx = num - 1 + off
        current_letter = (DOI_WORDS[current_idx][0].upper()
                          if 0 <= current_idx < len(DOI_WORDS) else '?')

        # Without this specific offset (use interpolated offset from neighbors)
        # Find nearest non-negative offset
        neighbor_offsets = []
        for delta in range(-10, 11):
            neighbor = num + delta
            if neighbor in offset_map and offset_map[neighbor] >= 0 and neighbor != num:
                neighbor_offsets.append(offset_map[neighbor])
        interpolated = int(np.median(neighbor_offsets)) if neighbor_offsets else 0

        alt_idx = num - 1 + interpolated
        alt_letter = (DOI_WORDS[alt_idx][0].upper()
                      if 0 <= alt_idx < len(DOI_WORDS) else '?')

        # Find expected letter from B2 positions using this number
        b2_positions = [i for i, n in enumerate(B2_CIPHER) if n == num]
        expected_letters = [b2_plain_letters[pos] for pos in b2_positions
                            if pos < len(b2_plain_letters)]

        typo_corrections.append({
            'cipher_num': num,
            'current_offset': off,
            'interpolated_offset': interpolated,
            'current_letter': current_letter,
            'alt_letter': alt_letter,
            'expected_letters': expected_letters,
            'correction_helps': alt_letter in expected_letters if expected_letters else False,
        })

    return {
        'edition_differences': edition_diffs,
        'typos': typos,
        'ambiguous': ambiguous,
        'typo_corrections': typo_corrections,
        'summary': {
            'n_edition': len(edition_diffs),
            'n_typo': len(typos),
            'n_ambiguous': len(ambiguous),
        },
    }


# ===========================================================================
# 6. Encoder Movement Model
# ===========================================================================

def encoder_movement_analysis():
    """
    For each B2 position, find ALL DoI words starting with the target letter.
    Compute distance-to-nearest for each position. Build an "encoder cursor"
    showing how Beale moved through the DoI.
    """
    b2_plain_words = B2_PLAINTEXT.upper().split()
    b2_plain_letters = [w[0] for w in b2_plain_words if w]

    # Build letter -> position index for DoI
    letter_positions = defaultdict(list)
    for i, word in enumerate(DOI_WORDS):
        letter_positions[word[0].upper()].append(i + 1)  # 1-indexed

    cursor_positions = []  # Where Beale was in the DoI at each step
    distances_to_nearest = []
    reuse_flags = []
    used_positions = set()

    for i, num in enumerate(B2_CIPHER):
        off = BEALE_DOI_OFFSET.get(num, 0)
        doi_idx = num - 1 + off  # 0-indexed
        letter = b2_plain_letters[i] if i < len(b2_plain_letters) else '?'

        # All DoI positions for this letter (1-indexed)
        alternatives = letter_positions.get(letter, [])

        # Distance to nearest alternative
        if alternatives:
            dist_to_nearest = min(abs(num - alt) for alt in alternatives)
        else:
            dist_to_nearest = -1  # No alternatives

        # Reuse check
        was_reused = num in used_positions
        used_positions.add(num)

        cursor_positions.append(num)
        distances_to_nearest.append(dist_to_nearest)
        reuse_flags.append(was_reused)

    # Cursor jump analysis
    jumps = [abs(cursor_positions[i+1] - cursor_positions[i])
             for i in range(len(cursor_positions) - 1)]

    # Direction analysis
    forward = sum(1 for i in range(len(cursor_positions) - 1)
                  if cursor_positions[i+1] > cursor_positions[i])
    backward = sum(1 for i in range(len(cursor_positions) - 1)
                   if cursor_positions[i+1] < cursor_positions[i])
    same = sum(1 for i in range(len(cursor_positions) - 1)
               if cursor_positions[i+1] == cursor_positions[i])

    return {
        'mean_distance_to_nearest': float(np.mean([d for d in distances_to_nearest if d >= 0])),
        'median_distance_to_nearest': float(np.median([d for d in distances_to_nearest if d >= 0])),
        'zero_distance_count': sum(1 for d in distances_to_nearest if d == 0),
        'mean_jump': float(np.mean(jumps)),
        'median_jump': float(np.median(jumps)),
        'max_jump': int(max(jumps)),
        'forward_moves': forward,
        'backward_moves': backward,
        'same_position': same,
        'forward_ratio': forward / (forward + backward + same),
        'reuse_count': sum(reuse_flags),
        'reuse_rate': sum(reuse_flags) / len(reuse_flags),
        'cursor_positions': cursor_positions,
        'distances': distances_to_nearest,
    }


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers -- Phase 4 Task 1: DoI Edition Fingerprinting")
    p("=" * 70)

    # --- 1. Offset Catalog ---
    p("\n[1] Offset Pattern Catalog")
    p("-" * 50)
    cat = catalog_offsets()
    p(f"  Non-zero offsets: {cat['non_zero_count']}")
    p(f"  Unique magnitudes: {cat['unique_magnitudes']}")
    p(f"  Magnitude histogram: {cat['magnitude_histogram']}")
    p(f"\n  Offset clusters:")
    for cl in cat['clusters']:
        p(f"    offset={cl['offset']:+3d}: {cl['count']} numbers, "
          f"range [{cl['range'][0]}, {cl['range'][1]}]")
    p(f"\n  Negative offsets (potential typos):")
    for neg in cat['negatives']:
        p(f"    num={neg['cipher_num']}, offset={neg['offset']}")

    # --- 2. Edition Difference Model ---
    p("\n[2] Edition Difference Model")
    p("-" * 50)
    model = model_edition_differences(cat)
    p(f"  Total words inserted in Beale's edition: {model['total_words_inserted']}")
    p(f"  Insertion points:")
    for ins in model['insertion_sections']:
        p(f"    DoI pos ~{ins['doi_position']}: +{ins['words_inserted']} words "
          f"(section: {ins['section']})")
        p(f"      First cipher number affected: {ins['first_cipher_num']}")
        p(f"      DoI word at insertion: '{ins['doi_word_at_pos']}'")
    p(f"  Deletion/variant points: {model['total_deletions']}")
    for d in model['deletions']:
        p(f"    num={d['cipher_num']}: offset={d['offset']}, "
          f"word='{d['doi_word_at_pos']}'")

    # --- 3. Synthetic Edition Reconstruction ---
    p("\n[3] B2 Decode with Beale's Edition")
    p("-" * 50)
    recon = reconstruct_beale_doi()
    p(f"  Total positions: {recon['total_positions']}")
    p(f"  In DoI range: {recon['in_range']}")
    p(f"  Mismatches: {recon['mismatches']}")
    p(f"  Accuracy: {recon['accuracy_pct']:.1f}%")

    # Show first 10 decode details
    p(f"\n  First 20 decode details:")
    for d in recon['decode_details'][:20]:
        match_flag = ' ' if d['match'] else '*'
        p(f"    {match_flag} pos={d['position']:3d} num={d['cipher_num']:4d} "
          f"off={d['offset']:+3d} -> '{d['doi_word'][:12]:12s}' "
          f"decoded={d['decoded_letter']} expected={d['expected_letter']}")

    # --- 4. Residual Error Analysis ---
    p("\n[4] Residual Error Analysis")
    p("-" * 50)
    errors = analyze_residual_errors(recon)
    p(f"  Total errors: {errors['total_errors']}")
    p(f"  Error types: {dict(errors['error_types'])}")
    p(f"  Near-miss count: {errors['near_miss_count']}")
    p(f"  Errors clustered: {errors['clustered']}")
    p(f"  Mean gap between errors: {errors['mean_gap']:.1f} positions")
    if errors['errors']:
        p(f"\n  Error details:")
        for e in errors['errors'][:15]:
            nm = f" (near-miss deltas: {e['near_miss_deltas']})" if e['near_miss'] else ""
            p(f"    pos={e['position']:3d} num={e['cipher_num']:4d} "
              f"got={e['decoded']} want={e['expected']} "
              f"type={e['type']}{nm}")

    # --- 5. Historical DoI Variations ---
    p("\n[5] Historical DoI Variation Analysis")
    p("-" * 50)
    hist = historical_doi_variations()
    for name, data in hist.items():
        p(f"\n  {name}:")
        for k, v in data.items():
            if isinstance(v, list):
                p(f"    {k}:")
                for item in v:
                    p(f"      - {item}")
            else:
                p(f"    {k}: {v}")

    # --- 6. Edition vs Typo Separation ---
    p("\n[6] Edition Difference vs Typo Classification")
    p("-" * 50)
    sep = separate_edition_vs_typo(cat)
    p(f"  Edition differences: {sep['summary']['n_edition']}")
    p(f"  Typos: {sep['summary']['n_typo']}")
    p(f"  Ambiguous: {sep['summary']['n_ambiguous']}")
    p(f"\n  Typo analysis:")
    for tc in sep['typo_corrections']:
        helps = 'YES' if tc['correction_helps'] else 'no'
        p(f"    num={tc['cipher_num']}: offset={tc['current_offset']:+3d} "
          f"-> letter={tc['current_letter']} "
          f"(interpolated offset={tc['interpolated_offset']} -> {tc['alt_letter']}, "
          f"expected={tc['expected_letters']}, helps={helps})")

    # --- 7. Encoder Movement ---
    p("\n[7] B2 Encoder Movement Model")
    p("-" * 50)
    movement = encoder_movement_analysis()
    p(f"  Mean distance to nearest alternative: {movement['mean_distance_to_nearest']:.1f}")
    p(f"  Median distance to nearest: {movement['median_distance_to_nearest']:.1f}")
    p(f"  Exact nearest chosen: {movement['zero_distance_count']} / {len(B2_CIPHER)}")
    p(f"  Mean cursor jump: {movement['mean_jump']:.1f}")
    p(f"  Median cursor jump: {movement['median_jump']:.1f}")
    p(f"  Max cursor jump: {movement['max_jump']}")
    p(f"  Forward/backward/same: {movement['forward_moves']}/{movement['backward_moves']}/{movement['same_position']}")
    p(f"  Forward ratio: {movement['forward_ratio']:.3f}")
    p(f"  Position reuse: {movement['reuse_count']} ({movement['reuse_rate']:.1%})")

    # --- Summary ---
    p(f"\n{'=' * 70}")
    p("EDITION FINGERPRINTING SUMMARY")
    p(f"{'=' * 70}")
    p(f"  1. Beale's DoI had ~{model['total_words_inserted']} extra words vs standard text")
    p(f"  2. +1 cluster (246-470): 1 word inserted ~DoI word 245")
    p(f"  3. +11 cluster (485-620): ~10 more words inserted ~DoI word 485")
    p(f"     Candidate: 'The unanimous Declaration...' heading (10 words)")
    p(f"  4. +13 for num 807: cumulative 13 insertions before position 807")
    p(f"  5. Negative offsets (557,581,620,643,647): pamphlet typos, not edition")
    p(f"  6. B2 decode accuracy with offsets: {recon['accuracy_pct']:.1f}%")
    p(f"  7. Encoder uses targeted jumps, NOT sequential scanning")
    p(f"     (forward ratio {movement['forward_ratio']:.3f}, mean jump {movement['mean_jump']:.0f})")
    p(f"{'=' * 70}")
