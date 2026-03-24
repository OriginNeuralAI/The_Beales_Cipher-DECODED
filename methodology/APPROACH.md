# Methodology: 8-Phase Forensic Analysis

## Overview

The forensic analysis of the three Beale ciphers proceeds in eight phases, each building on results from the preceding phase. The progressive structure is essential: later phases depend on calibrated baselines and resolved ambiguities from earlier work.

**Total scope:** ~16,000 lines of analysis code across 25 Python scripts and 1 Rust validator, producing 35+ statistical diagnostics with bootstrap-validated confidence intervals.

---

## Phase 1: Statistical Fingerprinting

**12 foundational diagnostics** to establish baseline distributional properties:

| Diagnostic | Purpose |
|:-----------|:--------|
| Number distribution | Range, mean, std, distinct ratio |
| Benford's Law | First-digit conformance |
| Last-digit uniformity | Detect fabrication bias |
| Shannon entropy | Information content (bits/char) |
| Number frequency | Zipf's law conformance |
| Bigram analysis | Letter-pair frequencies in decoded text |
| Autocorrelation (50 lags) | Sequential dependency structure |
| Spectral fingerprinting | Transition matrix eigenvalues mod 26 |
| Index of Coincidence | English vs random threshold |
| Gillogly checks | Alphabetical run detection |
| Cross-cipher comparison | B1/B2/B3 distributional overlap |
| Page boundary analysis | Clustering near DoI page breaks |

**Key finding:** B2's near-zero serial correlation (0.044) vs B1's 0.252 and B3's 0.612 — the foundational signal that motivates all subsequent analysis.

---

## Phase 2: Fabrication Scoring

Formalizes Phase 1 anomalies using four Fitzgerald-class metrics (Bayes Factor ~2x10^7):

1. **Serial correlation** — lag-1 autocorrelation of cipher numbers
2. **Distinct ratio** — fraction of unique numbers (genuine: low reuse; fabricated: high reuse)
3. **Fatigue gradient** — increasing serial correlation over time (Q1 to Q4)
4. **Chi-squared selection model** — letter-targeted vs DoI-uniform word selection

Extensions beyond Fitzgerald:
- Changepoint detection revealing fatigue transitions
- Monte Carlo null distributions (N=5,000) for calibration
- Two-phase segmentation (careful Q1 → fatigued remainder)

**Result:** Composite fabrication scores: B2=0.00 [CI: -0.8, 0.8], B1=4.01 [CI: 2.5, 5.5], B3=7.51 [CI: 5.5, 9.5]. Non-overlapping confidence intervals.

---

## Phase 3: Ward Construction Model

8-parameter parametric simulator (WardFabricationModel) reproducing B1/B3 diagnostics:

| Parameter | B3 (fitted) | B1 (fitted) |
|:----------|:------------|:------------|
| Scan direction bias | 0.613 | 0.561 |
| Mean forward step | 37 | 245 |
| Mean backward step | 115 | 310 |
| Fatigue rate | 0.167 | 0.128 |
| Q1 length | 130 | 130 |
| Reset probability | 0.05 | 0.04 |
| Reuse probability | 0.57 | 0.43 |
| Key range | 975 | 2906 |

KS test p-values: B1=0.79, B3=0.65 (both pass).

**Gillogly forensics:** Monotonicity proof — non-monotone cipher numbers (ratio=0.36) producing monotone letters (ratio=1.00) with P < 10^-5.

---

## Phase 4: Cryptanalysis & Edition Identification

- **B2 full decryption** with Needleman-Wunsch alignment resolving 796 vs 763 character discrepancy
- **DoI edition fingerprinting** — 51 non-zero offsets revealing ~13 extra words in Beale's edition
- **B3 Q1 fragment recovery** — rules out genuine content
- **Formal B1/B3 impossibility proofs:**
  - Chi-squared: B1=50.9, B3=57.8 > threshold 44.3
  - IC: both below English threshold 0.050
  - Optimal key bound: even with perfect letter assignment, IC stays below 0.050

---

## Phase 5: Edition Reconstruction & Mismatch Resolution

All 22 true B2 mismatches exhaustively resolved:

| Group | Cipher # | Count | Decoded | Expected | Explanation |
|:------|:---------|:------|:--------|:---------|:------------|
| A | 95 | 3 | I | U | Dunlap "unalienable" spelling |
| B | 84 | 2 | C | E | Off-by-1 miscount |
| C | 811 | 8-9 | C | Y | Y-word edition difference |
| D | 1005 | 4 | W | X | X-word beyond standard DoI |
| -- | various | 4 | -- | -- | Orphan transcription errors |

After group corrections: 755/763 = 99.0% accuracy.

---

## Phase 6: Spectral Forensics & Publication Preparation

- Critical Y/X-word alignment bug fix (8/9 not 2/9 for Y-word)
- **8 bispectral diagnostic tools:** PSD, bispectrum, bicoherence, trispectrum, spectral entropy, phase randomness (Rayleigh), cepstral analysis, multitaper
- **QUBO edition search** with 4-solver Ising ensemble — DoI uniquely correct (>60pp accuracy gap)
- **Bootstrap confidence intervals** (N=2,000) for all key metrics

---

## Phase 7: Validation & Multi-Channel Analysis

- **Welch-averaged bicoherence** corrects single-realization saturation (seg_len=128, 50% overlap)
  - B2: 0.187 (lowest = genuine), B1: 0.293, B3: 0.293
- **Ward cognitive identity profiling** — 12D feature vector with dual-null bootstrap
- **B1 key text impossibility** — 7 candidate texts all produce gibberish (IC 0.039-0.042)
- **Joint offset SA optimization** — 92.2% accuracy blind, 31% offset rediscovery
- **Multi-channel forensic analysis:**
  1. Surface (B2) — intentional book cipher encoding
  2. Edition fingerprint — emergent DoI edition identity
  3. Fabricator signature — emergent cognitive identity
  4. Gillogly sequence — intentional alphabetical embedding

---

## Phase 8: Exhaustive Correctness & Rigor

Deep audit fixing 2 bugs, resolving 4 internal contradictions:

- **Expanded H3 bootstrap:** 12D features, N=10,000, dual-null generation from both models
- **5 open questions closed** (including delta encoding test: no secondary message in B1/B3)
- **Even-digit bias decomposition** by digit position
- **Independent Bayes Factor** via KDE: BF=235.8 (decisive)
- **7 novel data patterns documented:**
  1. B1 block-copy (485-18-436 at positions 37-39 and 84-86)
  2. B1-B2 vocabulary disjointness (216: 8x B1/0x B2; 807: 7x B2/0x B1)
  3. B3 ascending runs (5-6 element forward-scan signatures)
  4. B3 missing digit 5 (single-digit 5 never appears)
  5. Offset 511 anomaly (+3 sandwiched between +11 values)
  6. Negative offset cluster (positions 557-647)
  7. Gillogly flanking gibberish (IAEAEIOG at 180-188, then alphabetical at 189)

---

## Diagnostic Summary

| Diagnostic | B1 | B2 | B3 |
|:-----------|:---|:---|:---|
| **Fabrication score** | 4.01 | **0.00** | 7.51 |
| **Serial correlation** | 0.252 | **0.044** | 0.612 |
| **Distinct ratio** | 0.573 | **0.236** | 0.426 |
| **Chi-sq vs English** | 50.86 | **9.63** | 57.81 |
| **Selection model** | DoI-uniform | **Letter-targeted** | DoI-uniform |
| **Fatigue gradient** | 0.128 | 0.047 | 0.167 |
| **Welch bicoherence** | 0.293 | **0.187** | 0.293 |
| **Spectral entropy** | 0.913 | **0.928** | 0.834 |
| **Classification** | Fabricated | **Genuine** | Fabricated |

---

## References

1. Ward, J.B. (1885). *The Beale Papers*. Lynchburg, VA.
2. Gillogly, J. (1980). "Breaking the Beale Cipher: Part II". *Cryptologia* 4(2):116-119.
3. Fitzgerald, J. (2024). "Quantitative Evidence for Fabrication in the Beale Ciphers". *Cryptologia*.
4. Wase, T. (2020). "Statistical Analysis of the Beale Ciphers". Working paper.
5. Hammer, C. (1968). "Signature in the Beale Cipher". *Cryptologia* preprint.
6. Needleman, S.B. & Wunsch, C.D. (1970). "A general method applicable to the search for similarities in the amino acid sequence of two proteins". *J. Mol. Bio.* 48(3):443-453.
7. Friedman, W.F. (1987). *The Index of Coincidence and its Applications to Cryptanalysis*. Aegean Park Press.
