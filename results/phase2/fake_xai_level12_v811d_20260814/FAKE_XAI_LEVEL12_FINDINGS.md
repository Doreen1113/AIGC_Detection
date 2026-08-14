# Fake-XAI Level 1/2 Evidence Audit — v8.11d Production Checkpoint (2026-08-14)

**Scope**: read-only audit of the FROZEN production hierarchical classifier
(`shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth`) on
`fake`-labeled images only, from 3 sources (AIGuard unseen fake, StyleGAN2
OOD, True Test DF40 diffusion). No training, no `pipeline.py` edit, no
`splits/` edit, no MLLM/VLM, no pixel-level fake mask produced or claimed.
Full protocol/config: `run_manifest.json` (weight sha256, git commit, seeds).
Scripts: `phase2_fake_xai/task1_global_evidence.py` … `task_figures.py`.

Sample sizes: n=50/source for Task 1–3 (all 150/150 passed the
`pl.has_face` gate, 0 skipped — see `fake_xai_global_metrics.json`'s
`skipped_face_gate`); n=20/source (seeded sub-sample of the correctly-judged-
fake images) for Task 4.

## Task 1 — Global evidence

All 150/150 sampled images were correctly classified `fake`
(`accuracy_correct_fake_rate = 1.0` for all 3 sources — see
`fake_xai_global_metrics.json`'s `aggregate_by_source`), so every image
proceeded to Layer2 as the decisive layer.

Zero-branch ablation proxy (full_prob − freq_only_prob = spatial's marginal
contribution; full_prob − spatial_only_prob = FFT's marginal contribution;
**NOT a gradient/Shapley attribution, only whether the branch as a whole is
causally load-bearing**):

| Source | spatial_branch_contribution_proxy (mean) | fft_branch_contribution_proxy (mean) |
|---|---|---|
| aiguard_unseen | 0.444 | 0.101 |
| stylegan2_ood | 0.468 | 0.088 |
| truetest_df40 | 0.416 | 0.133 |

Both branches are causally load-bearing on every source (both proxies
consistently positive), with the spatial branch contributing roughly
3–5x more than the FFT branch. This is branch-level evidence only — it
says nothing about which pixels or frequency bands matter.

## Task 2 — Deletion faithfulness (blur-based, primary)

**Deletion faithfulness PASSES on all 3 sources at every k (5/10/20%)** —
`hot_drop` bootstrap-CI-significantly exceeds both `bottom_drop` and
`mean_random_drop` (5 random seeds averaged per image/k), sources never
pooled (`fake_xai_deletion_summary.json`):

| Source | k20 hot−bottom Cohen's d | 95% CI | k20 hot−random Cohen's d | 95% CI |
|---|---|---|---|---|
| aiguard_unseen | 1.43 | [0.209, 0.308] | 1.21 | [0.131, 0.204] |
| stylegan2_ood | 2.12 | [0.275, 0.355] | 1.41 | [0.146, 0.216] |
| truetest_df40 | 0.64 | [0.051, 0.120] | 0.54 | [0.034, 0.099] |

All 6 CIs exclude zero. Effect size is largest on stylegan2_ood and
aiguard_unseen, smallest (but still real) on truetest_df40 — the diffusion
source shows a genuinely weaker but still faithful effect, not a failure.
A constant-fill comparison was also run and is stored under
`constant_fill_comparison_CONFOUNDED` in the summary JSON — per
`xai_faithfulness_v1_20260812.json`'s prior finding, this masking method
can inject broadband high-frequency edges the FFTBranch reacts to and
should NOT be read as equally trustworthy as the blur-based numbers above.

## Task 3 — Insertion test

**Insertion test also PASSES on all 3 sources**: hot-first restoration AUC
significantly exceeds bottom-first AUC (bootstrap CI excludes zero) for
every source (`fake_xai_insertion_summary.json`):

| Source | hot-first AUC | bottom-first AUC | diff | Cohen's d | 95% CI |
|---|---|---|---|---|---|
| aiguard_unseen | 0.927 | 0.835 | 0.092 | 1.88 | [0.079, 0.107] |
| stylegan2_ood | 0.932 | 0.831 | 0.102 | 2.15 | [0.090, 0.115] |
| truetest_df40 | 0.938 | 0.908 | 0.030 | 1.13 | [0.024, 0.038] |

Same pattern as deletion: truetest_df40's effect is the smallest of the
three but still clearly significant.

**Conclusion for Tasks 2+3**: all 3 fake sources pass deletion AND
insertion faithfulness — the model's own fake-class decision depends on the
region Grad-CAM++ highlights, consistently across all three fake data
sources. No source disagreement to report here (unlike Task 4).

## Task 4 — Stability / position-bias

**Caveat that applies to every number below**: `pipeline.py`'s `run_single`
has NO face-alignment crop — `Resize((224,224))` is applied directly to
whatever crop/framing the source image already has. A peak that looks
stable across images from the same source may only reflect that source's
consistent framing, not a face-relative invariant the model learned, and
vice versa. Both raw-pixel and face-relative peak movement are reported so
this is not glossed over (`fake_xai_stability_summary.json`).

Per-source, per-perturbation summary (class consistency rate = fraction
that stayed classified `fake`):

| Source | Condition | Class consistency | Mean fake-score delta | Heatmap IoU (top20%) | Mean Spearman ρ |
|---|---|---|---|---|---|
| aiguard_unseen | crop90 | 0.90 | −0.048 | 0.835 | 0.944 |
| aiguard_unseen | jpeg_q70 | 0.95 | −0.026 | 0.927 | 0.987 |
| aiguard_unseen | translate ±8px | 0.68 | −0.254 | 0.735 | 0.907 |
| stylegan2_ood | crop90 | 0.90 | −0.041 | 0.779 | 0.914 |
| stylegan2_ood | jpeg_q70 | 1.00 | −0.001 | 0.903 | 0.973 |
| stylegan2_ood | translate ±8px | **0.42** | **−0.445** | 0.712 | 0.889 |
| truetest_df40 | crop90 | 0.95 | −0.049 | 0.856 | 0.947 |
| truetest_df40 | jpeg_q70 | 0.95 | −0.020 | 0.940 | 0.988 |
| truetest_df40 | translate ±8px | 0.90 | −0.058 | 0.789 | 0.927 |

**Finding — the model shows a fixed-position sensitivity, not stability,
under small translation, and it differs sharply by source**: an 8px
(≈3.6% of 224px) translation, with the CAM shift-corrected before
comparison so this is not a pure geometry artifact, drops class consistency
to 0.68 on aiguard_unseen and to just **0.42 on stylegan2_ood** — under
half of previously-correct predictions flip away from `fake` after a small
shift. truetest_df40 is comparatively robust (0.90 consistency). This is a
genuine per-source disagreement (Task 5 requirement): translation
robustness is NOT uniform across fake sources, and should not be reported
as a single pooled number. JPEG re-encoding at q70 is the most benign
perturbation across all sources (consistency ≥0.95, IoU/ρ highest).
Center-crop 90% is intermediate. Given the no-alignment-crop caveat, the
translation instability is at minimum evidence the decision boundary is
close to some images near a 8px shift, but whether this reflects the model
tracking "fixed input pixels" vs. "face content" cannot be cleanly resolved
by this data alone — face-relative peak movement (0.19–0.27, in bbox-size
units) is smaller than raw-pixel movement in every source, suggesting some
(not complete) face-relative tracking of the CAM peak itself even when the
final classification flips.

## Can the production fake explanation text be upgraded?

Current `pipeline.py` `TEMPLATES["ai_generated"]`:
> "Unnatural global texture and frequency patterns detected across the
> image, consistent with AI-generated (synthetic) facial imagery."

Assessed against what was actually measured:

- **"global"** — supported. `regions = []` for fake in production (no
  region claim made), and Tasks 2/3 show a broad ~20%-of-frame region
  matters (not a single small landmark-sized area), consistent with
  distributed/global evidence.
- **"frequency"** — **partially supported, at branch level only**. Task 1's
  zero-branch-ablation proxy shows the FFT branch is causally load-bearing
  on every source (mean proxy 0.09–0.13, always positive) — so "frequency"
  is not an unsupported claim. But this is a whole-branch causality result,
  not a pixel/frequency-band localization; the wording should not be read
  as implying a specific frequency artifact was pinpointed, since Grad-CAM++
  here only visualizes `spatial_branch.conv5` (spatial-branch activations),
  never the FFT branch's contribution spatially.
- **"texture"** — **not directly supported by anything measured in this
  audit**. No test here measured texture (e.g. local variance, GLCM,
  smoothness) specifically; "texture" is presently an unverified assumption
  about what the spatial branch is picking up, not a tested claim. The
  spatial-branch contribution proxy shows the spatial branch matters (0.42–
  0.47, larger than FFT's), but says nothing about *texture* vs. any other
  spatial cue (shape, color, lighting, compression artifacts, etc.).

**Recommendation (evidence-supported wording only, NOT applied to
`pipeline.py` — human/separate change)**: given Tasks 2+3 pass on all 3
sources, the production text could be defensibly upgraded from
`global_only` to `attention_faithfulness` framing, e.g.:

> "Anomalous patterns detected across the image; the model's attention,
> concentrated broadly rather than in one small region, has been
> faithfulness-tested (deletion/insertion) and measurably contributes to
> this AI-generated classification."

This drops the specific "texture" claim (unsupported) and softens
"frequency" to a branch-level causal statement rather than an implied
localized frequency-artifact finding. It does **not** and must not claim
any region/location — that remains Tier C / `global_only` for the location
axis specifically, pending real fake-class ground truth.

## Explicit non-claims

This audit does **not** and **cannot** support any manipulation-location or
mask claim for the `fake` class. No ground-truth fake manipulation mask
exists for any current training/eval source (AIGuard, DF40 diffusion
methods) — see `docs/xai_evidence_schema.md`'s Tier C. `Tier D`
(`GT_BACKED_LOCALIZATION`, e.g. FF++ official masks) remains pending and is
not addressed by this audit at all.
