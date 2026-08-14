# P1-R1: Cross-Source Failure Anatomy — Findings

> Diagnostic-only research round. No checkpoint was trained or modified, `pipeline.py` and
> the frozen v8.11 production release were not touched, no existing result file or split file
> was overwritten. All numbers below are freshly computed in this round from real inference
> over the existing, unmodified `v815_replication_set` (DF40-cdf) using the existing, unmodified
> `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` (Cell C), `shufflenet_v2_layer2_v816_mixedlineage.pth`
> (v8.16), and `shufflenet_v2_layer1_v812.pth` (frozen Layer1) checkpoints. **Sanity check**: this
> round's own pipeline reproduces the exact previously-published headline numbers — overall
> DF40-cdf joint recognition 2.02% (Cell C@0.85), 11.21% (v816@0.85 uncalibrated), 4.53%
> (v816@0.95 calibrated) — see `scoring_console.log`'s "Sanity check" section in
> `p1_r1_compute_metrics.py`'s stdout. This gives high confidence the new, finer-grained
> metrics computed below are measuring the same underlying system correctly.

## What was located on disk (per the task's request to verify, not assume)

| Requested asset | Found? | Path |
|---|---|---|
| v8.15 Cell C checkpoint | Yes | `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` |
| v8.16 mixed-lineage checkpoint | Yes | `shufflenet_v2_layer2_v816_mixedlineage.pth` |
| Layer1 used by both (frozen, shared) | Yes | `shufflenet_v2_layer1_v812.pth` (confirmed via `AIGuard/train_v816.py`'s own docstring: "Layer1: unchanged, stays frozen at v812") |
| "v8.16 validation set" | Yes, but **in-domain only** | `splits/v816_val.txt` (2,411 clean-fake + 3,756 composite rows; used only for threshold calibration per `results/threshold_sweep_v816.log`, never for the cross-source test below) |
| "DF40-cdf replication set" | Yes — **confirmed to be a distinct, purpose-built set, not a repurposed existing split** | `splits/v815_replication_set.tsv` (994 rows / `v815_replication_set/` 994 images), built by `build_v815_replication_set.py`, `used_in_v815_training=False` for all rows |
| Existing source/filter-type manifests | Yes | `v815_replication_set.tsv` itself carries `source_dataset` and `filter_type_label` columns; `splits/v816_manifest.tsv` documents v816's own training composition |
| Existing paired before/after composite images | Yes | Each `replNNNN_clean.jpg` has 1-4 matching `replNNNN_<ftype>.jpg` siblings in `v815_replication_set/`, linked via the tsv's `source_stem` column — 792 of 794 possible pairs successfully matched and processed (2 skipped: no face landmark detected on the clean base) |

No substitutions were made for anything not found — everything requested was located.

## New scripts written this round (read-only w.r.t. existing files, new files only)

`p1_r1_score_replication_set.py` (loads the 3 checkpoints, scores all 994 images, caches
`per_image_scores.csv`), `p1_r1_compute_metrics.py` (→ `source_by_filter_metrics.csv`,
`routing_failure_breakdown.csv`), `p1_r1_paired_effect_stats.py` +
`p1_r1_aggregate_paired_stats.py` (→ `paired_effect_statistics.csv`, uses MediaPipe
FaceLandmarker, same pattern as existing project scripts), `p1_r1_generate_figures.py` (→
`figures/*.png`). None of `eval_replication_set_v816.py`, `eval_replication_auroc_v816.py`,
`threshold_sweep_v815.py`, `threshold_sweep_v816.py`, or `AIGuard/train_v816.py` were modified
— their model-loading pattern and calibration thresholds (Cell C=0.85, v816=0.95) were reused
by reading them, not by editing them.

---

## Hypothesis verdicts

### H1: Data quantity limitation (v816 didn't add *enough* data to generalize)

**Verdict: NOT SUPPORTED as the primary bottleneck.**

- v816 added ~300 base images × 5 DF40-ff sources × 8 filter conditions (16,144 new pairs,
  per `AIGuard/train_v816.py`'s docstring) — a large, non-trivial data addition, not a token one.
- If quantity alone were the limiter, the resulting improvement should be roughly uniform
  across filter types/sources (more data → everything gets a bit better). It is not:
  `source_by_filter_metrics.csv` shows smoothing_medium's AUROC was **already above chance
  under Cell C alone** (0.81–0.91 across DiT/SiT/ddim, 95% CI excluding 0.5), *before* v816's
  extra data existed — while eye_enlarging/face_reshaping/whitening_medium stayed at
  chance-level AUROC (CI includes 0.5) in **both** Cell C and v816, despite v816 training on
  all filter types equally. See Figure 1 and Figure 2 (`fig1_source_x_filtertype_heatmap.png`,
  `fig2_cellc_vs_v816_by_filtertype.png`) — the improvement is concentrated, not distributed.
- pixart and sd2.1 (DF40-*ff*, i.e. the exact same generator families) **were** included in
  v816's training data, yet their DF40-*cdf* (test) AUROC remains at chance for all 4 filter
  types after training (`source_by_filter_metrics.csv`, `v816@0.95_calibrated` rows for
  `DF40-cdf-pixart`/`DF40-cdf-sd2.1`, all AUROC 95% CIs include 0.5). Seeing the generator
  family in training was not sufficient — this argues against "just needs more of the same
  kind of data."
- **What this does NOT rule out**: a *differently scaled or differently composed* data
  intervention (e.g., directly including some cdf-domain images, or resolution-matched
  augmentation) remains untested — see Next Experiments.

### H2: Source shortcut (the model keys off source-level nuisance variables, not the filter attribute)

**Verdict: SUPPORTED — the strongest-evidenced hypothesis in this round.**

Three independent lines of evidence converge on the same 2 sources:

1. **AUROC is flat at chance for pixart and sd2.1 across all 4 filter types**, for both
   checkpoints (`source_by_filter_metrics.csv`: `DF40-cdf-pixart` AUROC range 0.50–0.56,
   `DF40-cdf-sd2.1` AUROC range 0.49–0.65, every single 95% CI includes 0.5) — this is a
   **source**-level effect, not a filter-type effect, since the *same* filter type
   (e.g. smoothing_medium) is well above chance on DiT/SiT/ddim (AUROC 0.99–1.00 under v816)
   but at chance on pixart/sd2.1 (AUROC 0.51/0.65).
2. **Routing-failure composition differs sharply by source, not by filter type alone**:
   pixart and sd2.1 have the *lowest* share of "threshold_calibration_miss" among their
   failures (9.8% and 16.7% respectively, `routing_failure_breakdown.csv`, v816@0.95 rows) —
   meaning their failures are deep misses (raw sigmoid < 0.5), not near-miss borderline cases
   — versus ddim (46.3%), DiT (36.0%), SiT (34.2%). The model isn't "almost" detecting
   pixart/sd2.1 filters; it has essentially no purchase on them at all.
3. **A concrete, measured covariate lines up exactly with the 2 failing sources**:
   `paired_effect_statistics.csv` (grouped by source) shows native image resolution is
   **256×256 for DiT/SiT/ddim, 512×512 for sd2.1, and 1024×1024 for pixart** — a clean 2×/4×
   split that maps exactly onto "transfers somewhat" vs "transfers not at all." This is an
   observed correlation, not yet a proven causal mechanism (see H4).

### H3: Filter-effect mismatch (the same filter looks physically different when applied to different-source images)

**Verdict: NOT SUPPORTED in its literal form; a refined version IS supported.**

- The literal claim — that the *same filter code* produces meaningfully different physical
  effects depending on which fake-generation source it's applied to — is **not** supported:
  `paired_effect_statistics.csv` shows each filter type's LAB delta-E and changed-pixel
  proportion are fairly stable *across sources* (e.g. whitening_medium's mean LAB delta-E
  ranges only 16.4–25.7 across all 5 sources; smoothing_medium's changed-pixel proportion
  ranges 0.095–0.61 driven mostly by pixart being an outlier, not a systematic per-source
  drift). The filter pipeline is applied identically regardless of source, as expected.
- **However, a refined version is well supported**: effect *type* (not magnitude) predicts
  cross-source transfer. Whitening_medium has by far the **largest** physical effect
  (mean LAB delta-E ≈ 22, changed-pixel proportion ≈ 0.98 — i.e., it visibly changes almost
  the entire image) yet has the **worst** cross-source detection (joint recognition ≈ 0% in
  both models, every source). Smoothing_medium has a *moderate* LAB effect (mean ≈ 2.7,
  changed-pixel proportion ≈ 0.39) concentrated in a texture/frequency signature (highest
  mean FFT log-magnitude difference among the 4 types, 0.69 vs 0.35–0.51 for the others,
  `paired_effect_statistics_by_filtertype_rollup.csv`) and is the **only** type with
  meaningfully above-chance cross-source AUROC. See Figure 6
  (`fig6_paired_effect_distributions.png`). **Interpretation**: a large, globally-diffuse
  tone shift (whitening) is easy to confuse with ordinary inter-image brightness variation
  across different fake-generation sources, while a frequency/texture-domain signature
  (smoothing) is comparatively more source-invariant — magnitude of change is not what
  predicts transfer, the *kind* of change is.

### H4: Representation entanglement (trunk features conflate generator identity with filter attribute)

**Verdict: INCONCLUSIVE — genuinely confounded with H2 in this dataset, cannot be separated with the data on hand.**

- Full disentanglement is clearly not achieved: pixart and sd2.1 *were* seen during v816
  training (as DF40-ff variants of the same generator families) and still show zero transfer
  at test (DF40-cdf variants) — consistent with *some* form of entanglement, since seeing the
  generator family was not sufficient.
- But this project's replication set has **exactly one native resolution per generator
  family** (all DF40-cdf-pixart images are 1024px, all DF40-cdf-sd2.1 are 512px, etc.) — so
  generator identity and image resolution are perfectly confounded in the test data available
  here. This analysis cannot distinguish "the model entangled filter detection with generator
  fingerprint" from "the model entangled filter detection with native image resolution /
  downstream resize artifacts" — both predict exactly the pattern observed.
- **This is a real evidence gap, not a forced call**: resolving it requires either (a) the
  DF40-ff (training-side) resolution distribution per generator family — if DF40-ff-pixart/
  sd2.1 were trained at a *different* resolution than DF40-ff-ddim/DiT/SiT, that would support
  the resolution-confound reading directly — or (b) a controlled test with the same generator
  family resampled to multiple resolutions. Neither was available/in-scope to build this
  round (would require new data preparation, arguably beyond "diagnosis only"). See Next
  Experiments.

### H5: Routing failure (Layer1 gates cross-source composites out as "real" before the dual-head model even sees them)

**Verdict: NOT SUPPORTED — cleanly ruled out.**

- `routing_failure_breakdown.csv`, aggregated: **`layer1_real` accounts for only 0.3% of all
  joint-recognition failures**, for both Cell C and v816 (2 or 3 images total out of ~760-780
  failures each). `fake_head_miss` is **exactly 0%** in every model/source/filter-type cell.
  See Figure 5 (`fig5_routing_failure_stacked_bar.png`) — the purple (`layer1_real`) and red
  (`fake_head_miss`) segments are not visible because they round to ~0% of the stacked bar.
- The overwhelming majority of failures (95.2% for Cell C, 72.2–77.6% for v816) is
  `filter_head_miss` — the filter_head's own raw sigmoid output is below 0.5, a genuine
  representational miss, not a routing or fake-detection problem.
- The `threshold_calibration_miss` share (cases where the raw filter score is >0.5 but doesn't
  clear the stricter operating threshold) is secondary but **grew** from 4.5% (Cell C) to
  27.6% (v816 calibrated) — this is itself informative: v816's improvement mechanism was
  "nudge borderline scores up," not "fix deep misses," which is consistent with a still
  fundamentally limited representation rather than evidence that routing/threshold tuning
  alone would close the gap.

---

## Which failure mechanism has the strongest evidence

**H2 (source shortcut)**, specifically correlated with native image resolution, is the most
consistently and multiply evidenced explanation in this round — three independent metrics
(AUROC, calibration-miss composition, and a directly measured resolution covariate) all point
at the same two sources. **H5 (routing failure) is equally cleanly evidenced but as a negative
result** — it rules out Layer1/fake-head as the bottleneck with very tight confidence
(0.3% / 0% shares), which is valuable for narrowing the search but does not itself explain the
failure. **H4 cannot be resolved with this dataset** (confounded with H2) and **H1 and the
literal form of H3 are both weighed against** by the evidence, though a refined,
effect-type-based version of H3 is supported and complements the H2 finding rather than
competing with it (both point toward "the representation the filter_head learned is narrower
and more source/effect-type-specific than a generalizable 'filter attribute' feature").

## Possible next experiments (diagnostic follow-ups, not a design commitment)

These are suggestions for what would resolve the open questions above — none are proposed as
a committed next build:

1. **Resolve the H2/H4 confound**: measure DF40-ff (training-side) native resolution per
   generator family. If pixart-ff/sd2.1-ff were also higher-resolution than ddim-ff/DiT-ff/
   SiT-ff, that's strong evidence the "source shortcut" specifically is a resolution artifact
   (fixable via resolution-matched preprocessing/augmentation, a cheap intervention) rather
   than a deeper generator-fingerprint entanglement (which would need a different fix).
2. **A small, targeted resolution-controlled probe**: downsample a handful of pixart/sd2.1
   replication-set images to 256px and re-score with the existing checkpoints (no retraining)
   — if AUROC jumps toward the DiT/SiT/ddim range purely from resolution matching, that's a
   direct causal test of the resolution-shortcut hypothesis, cheap to run.
3. **Effect-type-stratified data audit**: given H3's refined finding (frequency/texture
   effects transfer better than global tone effects), check whether v816's training data has
   an implicit imbalance in how many "texture-type" vs "tone-type" filter examples it saw
   per source — this round did not check that.

## Non-claims

This round does not claim to have identified a fix, does not claim the resolution correlation
is proven causal (only correlational, from the DF40-cdf test side), and does not recommend a
specific architecture or loss change — those questions are addressed as recommendations in
the final report, separately from these diagnostic verdicts.
