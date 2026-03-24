"""
Beale Ciphers — Phase 6 Task 5: Publication Visualizations

10 publication-quality figures (PNG at 300 DPI) saved to figures/.

Usage: python beale_visualize.py
"""

import os
import numpy as np
from collections import Counter

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from beale_data import (
    B1_CIPHER, B2_CIPHER, B3_CIPHER, B2_PLAINTEXT,
    DOI_WORDS, BEALE_DOI_OFFSET, beale_decode, ENGLISH_FREQ
)
from beale_fabrication import (
    serial_correlation, serial_correlation_by_quarter,
    distinct_ratio, fabrication_score, chi_squared_distance,
    decoded_letter_frequencies,
)
from beale_b2_decrypt import _needleman_wunsch, full_decode_comparison


def p(s, end='\n'):
    print(s, end=end, flush=True)


FIGURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figures')

COLORS = {
    'B1': '#d32f2f',   # red (fabricated)
    'B2': '#388e3c',   # green (genuine)
    'B3': '#f57c00',   # orange (fabricated)
    'threshold': '#757575',  # grey
}


def _ensure_dir():
    os.makedirs(FIGURES_DIR, exist_ok=True)


# ===========================================================================
# Figure 1: Fabrication Scores
# ===========================================================================

def fig_fabrication_scores():
    """Horizontal bar: B1/B2/B3 scores, green/red color, threshold lines."""
    _ensure_dir()

    # Get scores and bootstrap CIs
    scores = {}
    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        fs = fabrication_score(cipher)
        scores[name] = fs['composite_score']

    # Bootstrap CIs (quick, 500 iterations)
    rng = np.random.RandomState(42)
    cis = {}
    for cipher, name in [(B1_CIPHER, 'B1'), (B2_CIPHER, 'B2'), (B3_CIPHER, 'B3')]:
        boot = []
        arr = np.array(cipher)
        for _ in range(500):
            idx = rng.randint(0, len(arr), len(arr))
            boot.append(fabrication_score(list(arr[idx]))['composite_score'])
        cis[name] = (np.percentile(boot, 2.5), np.percentile(boot, 97.5))

    fig, ax = plt.subplots(figsize=(8, 3.5))

    names = ['B3 (Names)', 'B1 (Location)', 'B2 (Contents)']
    keys = ['B3', 'B1', 'B2']
    vals = [scores[k] for k in keys]
    colors = [COLORS[k] for k in keys]
    xerr_low = [max(0, vals[i] - cis[keys[i]][0]) for i in range(3)]
    xerr_high = [max(0, cis[keys[i]][1] - vals[i]) for i in range(3)]

    bars = ax.barh(names, vals, color=colors, edgecolor='black', linewidth=0.5, height=0.5)
    ax.errorbar(vals, names, xerr=[xerr_low, xerr_high], fmt='none', ecolor='black',
                capsize=4, linewidth=1.5)

    # Threshold lines
    ax.axvline(x=1.5, color=COLORS['threshold'], linestyle='--', linewidth=1, label='Moderate threshold')
    ax.axvline(x=3.0, color='black', linestyle='--', linewidth=1, label='Strong threshold')

    ax.set_xlabel('Fabrication Score (B2-referenced composite)', fontsize=11)
    ax.set_title('Beale Cipher Fabrication Scores with 95% Bootstrap CIs', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9, loc='lower right')
    ax.set_xlim(-1, 10)

    for i, (v, k) in enumerate(zip(vals, keys)):
        fs = fabrication_score([B1_CIPHER, B2_CIPHER, B3_CIPHER][['B1', 'B2', 'B3'].index(k)])
        ax.text(v + 0.15, i, f'{v:.2f} ({fs["classification"]})', va='center', fontsize=9)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig1_fabrication_scores.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 2: Fatigue Timeline
# ===========================================================================

def fig_fatigue_timeline():
    """Line plot: 4 quarters x 3 ciphers. B2 flat, B1 gradual, B3 steep."""
    _ensure_dir()

    fig, ax = plt.subplots(figsize=(7, 4.5))

    for cipher, name, key in [(B1_CIPHER, 'B1 (Location)', 'B1'),
                               (B2_CIPHER, 'B2 (Contents)', 'B2'),
                               (B3_CIPHER, 'B3 (Names)', 'B3')]:
        scq = serial_correlation_by_quarter(cipher)
        quarters = scq['quarter_correlations']
        ax.plot([1, 2, 3, 4], quarters, 'o-', color=COLORS[key], label=name,
                linewidth=2, markersize=8)

    ax.axhline(y=0.05, color=COLORS['threshold'], linestyle=':', linewidth=1,
               label='Genuine baseline (~0.05)')
    ax.set_xlabel('Quarter', fontsize=11)
    ax.set_ylabel('Serial Correlation', fontsize=11)
    ax.set_title('Fabrication Fatigue: Serial Correlation by Quarter', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)
    ax.set_xticks([1, 2, 3, 4])
    ax.set_xticklabels(['Q1', 'Q2', 'Q3', 'Q4'])
    ax.set_ylim(-0.1, 0.8)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig2_fatigue_timeline.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 3: Chi-Squared Impossibility
# ===========================================================================

def fig_chi_squared_impossibility():
    """Grouped bar: chi-sq vs English, critical threshold at 44.3."""
    _ensure_dir()

    fig, ax = plt.subplots(figsize=(7, 4.5))

    ciphers = [('B1', B1_CIPHER), ('B2', B2_CIPHER), ('B3', B3_CIPHER)]
    chi_eng = []
    chi_doi = []

    for name, cipher in ciphers:
        decoded_dist, _ = decoded_letter_frequencies(cipher)
        ce = chi_squared_distance(decoded_dist, dict(ENGLISH_FREQ))
        chi_eng.append(ce)
        # DoI first-letter distribution
        doi_counts = Counter(w[0].upper() for w in DOI_WORDS)
        doi_total = sum(doi_counts.values())
        doi_dist = {chr(c): (doi_counts.get(chr(c), 0) / doi_total * 100.0) for c in range(65, 91)}
        cd = chi_squared_distance(decoded_dist, doi_dist)
        chi_doi.append(cd)

    x = np.arange(3)
    width = 0.3
    bars1 = ax.bar(x - width/2, chi_eng, width, label='vs English', color=['#ef5350', '#66bb6a', '#ffa726'])
    bars2 = ax.bar(x + width/2, chi_doi, width, label='vs DoI first-letter', color=['#ef9a9a', '#a5d6a7', '#ffe0b2'])

    ax.axhline(y=44.3, color='black', linestyle='--', linewidth=1.5, label='Critical threshold (p=0.01)')

    ax.set_xlabel('Cipher', fontsize=11)
    ax.set_ylabel('Chi-squared Distance', fontsize=11)
    ax.set_title('Letter Frequency: Chi-Squared Impossibility Proof', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(['B1 (Location)', 'B2 (Contents)', 'B3 (Names)'])
    ax.legend(fontsize=9)

    # Annotate values
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1, f'{h:.1f}', ha='center', va='bottom', fontsize=8)
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 1, f'{h:.1f}', ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig3_chi_squared_impossibility.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 4: NW Alignment Strip
# ===========================================================================

def fig_nw_alignment_strip():
    """Strip heatmap: 763 positions green/red, annotated mismatch clusters."""
    _ensure_dir()

    comp = full_decode_comparison()
    ad = comp['aligned_decoded']
    ap = comp['aligned_plain']

    # Build match array for cipher positions only
    match_arr = []
    for k in range(len(ad)):
        if ad[k] == '-':
            continue  # gap in decoded = extra plaintext char
        if ap[k] == '-':
            match_arr.append(0.5)  # gap in plain
        elif ad[k] == ap[k]:
            match_arr.append(1.0)  # match
        else:
            match_arr.append(0.0)  # mismatch

    n = len(match_arr)
    arr = np.array(match_arr).reshape(1, -1)

    fig, ax = plt.subplots(figsize=(14, 1.8))

    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(['#d32f2f', '#ffeb3b', '#388e3c'])
    ax.imshow(arr, aspect='auto', cmap=cmap, vmin=0, vmax=1, interpolation='nearest')

    ax.set_xlabel('Cipher Position', fontsize=10)
    ax.set_yticks([])
    ax.set_title(f'B2 NW Alignment: {sum(1 for m in match_arr if m == 1.0)}/{n} matches (green=match, red=mismatch)',
                 fontsize=11, fontweight='bold')

    # Annotate mismatch clusters
    mismatch_positions = [i for i, m in enumerate(match_arr) if m == 0.0]
    if mismatch_positions:
        for pos in mismatch_positions[:5]:  # label first 5
            ax.annotate('', xy=(pos, 0.6), xytext=(pos, 1.2),
                        arrowprops=dict(arrowstyle='->', color='black', lw=0.8))

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig4_nw_alignment_strip.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 5: Vocabulary Growth
# ===========================================================================

def fig_vocabulary_growth():
    """Cumulative distinct numbers vs position."""
    _ensure_dir()

    fig, ax = plt.subplots(figsize=(7, 4.5))

    for cipher, name, key in [(B1_CIPHER, 'B1 (Location)', 'B1'),
                               (B2_CIPHER, 'B2 (Contents)', 'B2'),
                               (B3_CIPHER, 'B3 (Names)', 'B3')]:
        seen = set()
        cumulative = []
        for num in cipher:
            seen.add(num)
            cumulative.append(len(seen))
        positions = np.arange(1, len(cipher) + 1)
        ax.plot(positions, cumulative, color=COLORS[key], label=name, linewidth=1.5)

    ax.set_xlabel('Cipher Position', fontsize=11)
    ax.set_ylabel('Cumulative Distinct Numbers', fontsize=11)
    ax.set_title('Vocabulary Growth: Distinct Numbers vs Position', fontsize=12, fontweight='bold')
    ax.legend(fontsize=9)

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig5_vocabulary_growth.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 6: Gillogly Smoking Gun
# ===========================================================================

def fig_gillogly_smoking_gun():
    """Dual panel: scattered numbers → monotone letters."""
    _ensure_dir()

    # Gillogly positions in B1 (189-200, 0-indexed)
    gillogly_start = 189
    gillogly_end = 201
    gillogly_nums = B1_CIPHER[gillogly_start:gillogly_end]
    gillogly_decoded = beale_decode(B1_CIPHER, DOI_WORDS, use_beale_offset=True)
    gillogly_letters = gillogly_decoded[gillogly_start:gillogly_end]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))

    positions = range(gillogly_start, gillogly_end)

    # Panel 1: Cipher numbers (non-monotone)
    ax1.plot(list(positions), gillogly_nums, 'o-', color=COLORS['B1'], linewidth=2, markersize=8)
    ax1.set_xlabel('B1 Position', fontsize=10)
    ax1.set_ylabel('Cipher Number', fontsize=10)
    ax1.set_title('Cipher Numbers (Non-Monotone)', fontsize=11, fontweight='bold')
    for i, (pos, num) in enumerate(zip(positions, gillogly_nums)):
        ax1.annotate(str(num), (pos, num), textcoords="offset points",
                     xytext=(0, 8), ha='center', fontsize=7)

    # Panel 2: Decoded letters (monotone alphabetical)
    letter_ords = [ord(c) for c in gillogly_letters]
    ax2.plot(list(positions), letter_ords, 's-', color='#1565c0', linewidth=2, markersize=8)
    ax2.set_xlabel('B1 Position', fontsize=10)
    ax2.set_ylabel('Letter (ordinal)', fontsize=10)
    ax2.set_title('Decoded Letters (Monotone: CDEFGHIIJKLM)', fontsize=11, fontweight='bold')
    ax2.set_yticks(letter_ords)
    ax2.set_yticklabels(list(gillogly_letters))

    plt.suptitle('Gillogly Smoking Gun: Deliberate Letter-Targeted Insertion',
                 fontsize=12, fontweight='bold', y=1.02)
    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig6_gillogly_smoking_gun.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 7: Offset Clusters
# ===========================================================================

def fig_offset_clusters():
    """Scatter: cipher number vs offset, color-coded clusters."""
    _ensure_dir()

    fig, ax = plt.subplots(figsize=(9, 4.5))

    nums = sorted(BEALE_DOI_OFFSET.keys())
    offsets = [BEALE_DOI_OFFSET[n] for n in nums]

    # Color by offset value
    offset_colors = []
    for off in offsets:
        if off == 0:
            offset_colors.append('#90caf9')  # light blue
        elif off == 1:
            offset_colors.append('#66bb6a')  # green
        elif off == 11:
            offset_colors.append('#ffa726')  # orange
        elif off >= 12:
            offset_colors.append('#ef5350')  # red
        elif off < 0:
            offset_colors.append('#9e9e9e')  # grey (typos)
        else:
            offset_colors.append('#ce93d8')  # purple

    ax.scatter(nums, offsets, c=offset_colors, s=20, edgecolors='black', linewidths=0.3)

    # Annotate clusters
    ax.axhspan(-0.5, 0.5, alpha=0.05, color='blue', label='No offset (0)')
    ax.axhline(y=1, color='green', linestyle=':', alpha=0.5, label='+1 cluster')
    ax.axhline(y=11, color='orange', linestyle=':', alpha=0.5, label='+11 cluster')
    ax.axhline(y=13, color='red', linestyle=':', alpha=0.5, label='+13 cluster')

    ax.set_xlabel('Cipher Number', fontsize=11)
    ax.set_ylabel('Offset from Standard DoI', fontsize=11)
    ax.set_title('B2 Offset Clusters: Evidence for ~13 Extra Words in Beale\'s DoI', fontsize=12, fontweight='bold')
    ax.legend(fontsize=8, loc='upper left')

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig7_offset_clusters.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 8: Bispectrum Comparison
# ===========================================================================

def fig_bispectrum_comparison():
    """3-panel Welch-averaged bicoherence heatmaps (Phase 7 fix)."""
    _ensure_dir()

    from beale_bispectral import bicoherence_welch, mean_bicoherence_welch

    fig, axes = plt.subplots(1, 3, figsize=(14, 4))

    for ax, (cipher, name, key) in zip(axes,
            [(B1_CIPHER, 'B1 (Location)', 'B1'),
             (B2_CIPHER, 'B2 (Contents)', 'B2'),
             (B3_CIPHER, 'B3 (Names)', 'B3')]):
        bic_matrix = bicoherence_welch(cipher, seg_len=128, n_freq=32)
        bic_mean = mean_bicoherence_welch(cipher, seg_len=128, n_freq=32)
        im = ax.imshow(bic_matrix, aspect='auto', cmap='hot', vmin=0, vmax=0.5,
                       origin='lower', interpolation='nearest')
        ax.set_title(f'{name}\nmean={bic_mean:.4f}', fontsize=10, fontweight='bold')
        ax.set_xlabel('f₁', fontsize=9)
        ax.set_ylabel('f₂', fontsize=9)

    plt.colorbar(im, ax=axes, label='Bicoherence (Welch)', shrink=0.8)
    plt.suptitle('Welch-Averaged Bicoherence: Phase Coupling Detection', fontsize=12, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig8_bispectrum_comparison.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 9: ROC Curve
# ===========================================================================

def fig_roc_curve():
    """ROC with AUC from bootstrap analysis."""
    _ensure_dir()

    from beale_bootstrap import roc_curve_data

    p("  Computing ROC curve (N=500 synthetic)...")
    roc = roc_curve_data(n_synthetic=500)

    fig, ax = plt.subplots(figsize=(6, 5.5))

    ax.plot(roc['fprs'], roc['tprs'], 'b-', linewidth=2, label=f'ROC (AUC={roc["auc"]:.3f})')
    ax.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='Random (AUC=0.5)')

    ax.fill_between(roc['fprs'], roc['tprs'], alpha=0.1, color='blue')

    # Mark real ciphers
    b2_score = fabrication_score(B2_CIPHER)['composite_score']
    b1_score = fabrication_score(B1_CIPHER)['composite_score']
    b3_score = fabrication_score(B3_CIPHER)['composite_score']

    ax.set_xlabel('False Positive Rate', fontsize=11)
    ax.set_ylabel('True Positive Rate', fontsize=11)
    ax.set_title('Fabrication Classifier ROC Curve', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10, loc='lower right')
    ax.set_xlim(-0.02, 1.02)
    ax.set_ylim(-0.02, 1.02)
    ax.set_aspect('equal')

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig9_roc_curve.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Figure 10: B2 Key Uniqueness
# ===========================================================================

def fig_b2_key_uniqueness():
    """Bar chart: B2 accuracy with DoI vs alternatives."""
    _ensure_dir()

    from beale_qubo_edition import test_b2_alternative_keys

    p("  Testing B2 against alternative keys...")
    results = test_b2_alternative_keys()

    # Take top 10 results
    top = results[:10]
    names = [r['key_name'][:25] for r in top]
    accuracies = [r['accuracy'] for r in top]
    colors = [COLORS['B2'] if r['key_name'] == 'doi' else '#90a4ae' for r in top]

    fig, ax = plt.subplots(figsize=(10, 5))

    bars = ax.barh(range(len(names)), accuracies, color=colors, edgecolor='black', linewidth=0.5)
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names, fontsize=9)
    ax.invert_yaxis()

    ax.set_xlabel('B2 Decode Accuracy (NW-aligned)', fontsize=11)
    ax.set_title('B2 Key Text Uniqueness: DoI vs All Alternatives', fontsize=12, fontweight='bold')

    # Annotate values
    for bar, acc in zip(bars, accuracies):
        ax.text(bar.get_width() + 0.005, bar.get_y() + bar.get_height()/2,
                f'{acc:.3f}', va='center', fontsize=8)

    # Add gap annotation
    if len(accuracies) >= 2:
        gap = accuracies[0] - accuracies[1]
        ax.annotate(f'Gap: {gap:.3f}\n({gap*100:.1f}pp)',
                    xy=(accuracies[0], 0.5),
                    fontsize=10, fontweight='bold', color='red')

    plt.tight_layout()
    path = os.path.join(FIGURES_DIR, 'fig10_b2_key_uniqueness.png')
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    return path


# ===========================================================================
# Save All Figures
# ===========================================================================

def save_all_figures(output_dir=None):
    """Generate all 10 figures."""
    global FIGURES_DIR
    if output_dir:
        FIGURES_DIR = output_dir
    _ensure_dir()

    paths = []

    p("\n  [1/10] Fabrication scores...")
    paths.append(fig_fabrication_scores())

    p("  [2/10] Fatigue timeline...")
    paths.append(fig_fatigue_timeline())

    p("  [3/10] Chi-squared impossibility...")
    paths.append(fig_chi_squared_impossibility())

    p("  [4/10] NW alignment strip...")
    paths.append(fig_nw_alignment_strip())

    p("  [5/10] Vocabulary growth...")
    paths.append(fig_vocabulary_growth())

    p("  [6/10] Gillogly smoking gun...")
    paths.append(fig_gillogly_smoking_gun())

    p("  [7/10] Offset clusters...")
    paths.append(fig_offset_clusters())

    p("  [8/10] Bispectrum comparison...")
    paths.append(fig_bispectrum_comparison())

    p("  [9/10] ROC curve...")
    paths.append(fig_roc_curve())

    p("  [10/10] B2 key uniqueness...")
    paths.append(fig_b2_key_uniqueness())

    return paths


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    p("=" * 70)
    p("Beale Ciphers — Phase 6 Task 5: Publication Visualizations")
    p("=" * 70)

    p(f"\nOutput directory: {FIGURES_DIR}")
    paths = save_all_figures()

    p(f"\n{'=' * 70}")
    p("VISUALIZATION SUMMARY")
    p(f"{'=' * 70}")
    p(f"  Generated {len(paths)} figures:")
    for path in paths:
        p(f"    {os.path.basename(path)}")
    p(f"  All saved to: {FIGURES_DIR}")
    p(f"{'=' * 70}")
