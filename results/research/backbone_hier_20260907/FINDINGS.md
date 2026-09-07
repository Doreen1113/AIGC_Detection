# BACKBONE-HIER — MobileNetV4 inside the production hierarchy: FINDINGS (2026-09-07)

Pre-declared in `PRE_DECLARED.md`. One seed (20260907). Only change vs the production lineage = the spatial
backbone (timm `mobilenetv4_conv_small.e2400_r224_in1k`, ImageNet init; FFT branch + heads fresh).
Data = production v8.11 splits. L1 val macro-F1 0.8656 (10 ep), L2 val macro-F1 0.9798 (best ep 10/15).
v8.17 column = same-harness `flat3class_revisit_20260828/gates_PROD_full.json`. Harness: `eval_gates.py` (derived from p1a1_interference), arm `HIER_MNV4`, log `eval_HIER_MNV4.log`.

| Gate | HIER MNV4 (this round) | production v8.17 | flat MNV4 (backbone_swap §8) | gate | result |
|---|---|---|---|---|---|
| True Test fake recall | 98.52 | 99.63 | 99.63 | >= 99 | **FAIL** |
| True Test filter recall | 89.56 | 91.97 [88.35, 95.18] | 95.58 | >= 90 | **FAIL** |
| True Test real recall | 68.27 | 72.29 | 67.07 | stretch | worse |
| AIGuard/unseen AUROC | 0.7653 | 0.8410 | 0.8226 | >= 0.80 | **FAIL** |
| CelebA real recall (3,000) | 99.97 | 99.33 | 100.0 | >= 99 | pass |
| StyleGAN2 fake recall (3,000 / decontam) | 98.13 / 96.90 | 99.57 / 99.2 | 99.9 / 99.8 | >= 99 | **FAIL** |
| Shadow real / filter recall | 94.62 / 7.53 | 74.91 / 12.19 | 94.27 / 16.13 | stretch | real better, filter worse |
| **fake+filter stress (P1)** | **15.12** | 2.80 [1.92, 3.76] | 11.36 | <= 3.76 | **FAIL** |
| **Alibaba filter recall** | **57.31** | 97.71 | 72.40 | >= 95 | **FAIL** |
| FF++ official test frame AUROC (zero-shot) | 0.5423 (video 0.5485) | 0.5747 | 0.5372 | stretch | worse |

## Verdict: KEEP-SHUFFLENET (pre-declared rule). Backbone question CLOSED for the capstone.
Six of eight release gates fail, including the two that define this paper (stress, Alibaba). The
hierarchy did not rescue the backbone: HIER MNV4 is worse than flat MNV4 on stress (15.1 vs 11.4) and
Alibaba (57.3 vs 72.4), so the flat-label-space confound raised in backbone_swap §8 is resolved — the
backbone itself is what fails the safety gates under our data.

## Honest reading
- The P3 frontier KEEP (backbone_swap, 2/2 seeds) still stands: at a matched operating point on True-Test-style
  filters MobileNetV4 accuses fewer beautified faces. That result is about the *frontier*; the release gates
  are read at the native rule and on composite attacks / a third-party retouching algorithm, where it loses.
- Confound that cannot be removed here: v8.17's ShuffleNetV2 carries a long warm-start lineage (v8.11 -> SBI-aug)
  while MobileNetV4 starts from ImageNet with the plain BASE recipe. A fairer test would need the full SBI-aug
  recipe on MobileNetV4; we did not run it, and given six gate failures we do not consider it justified.
- Paper text: keep the frontier result as the measured case for the substitution, state the full-gate losses,
  and state that the deployed system stays ShuffleNetV2 (the ternary label space, not the backbone, is
  what buys the safety property).
