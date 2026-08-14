# Fake Evidence Resolution-Matched Validation — `tex_local_variance_std` (2026-08-14)

Phase 2F-R1. Direct follow-up to `results/phase2/fake_evidence_discovery_v811d_20260814/`
(`FAKE_EVIDENCE_DISCOVERY_FINDINGS.md` Section 3), which flagged
`tex_local_variance_std` as the only one of 24 hand-computed evidence
features to survive direction-consistency across all 8 fake sources
(AUROC clears 0.60 on 6/8) but carried a non-trivial between-source
resolution correlation (Spearman rho=-0.24) and asked for exactly this
resolution-matched re-validation before being trusted further. This round
is descriptive/statistical only: no model training, no `pipeline.py` or
checkpoint change, no MLLM, no threshold tuning, feature not wired into any
production output.

**Data reuse**: this round did **not** re-extract features. It reuses
`results/phase2/fake_evidence_discovery_v811d_20260814/raw_features.csv`
verbatim (598 rows, same `pl.preprocess_jpeg(q=85)` -> `pl.has_face` ->
224x224-resize pipeline, same `tex_local_variance_std` computation code as
that phase's `scripts/extract_features.py`) — the per-image CSV already
carried `orig_width`, `orig_height`, `orig_resolution`, and MediaPipe
landmark-derived `face_bbox_x0/x1/y0/y1` + `face_size_confound`
(face-bbox-area / 224², used here as `crop_scale`), so no new measurement
code was needed, only new analysis code
(`scripts/resolution_matched_validation.py`). One row (of 598) was dropped
for a missing landmark-derived covariate; final analysis n=597 (real pool
n=209, fake sources n=44-60 each, matching `run_manifest.json`).

## Method summary

- **Matching**: 1:1 optimal assignment (`scipy.optimize.linear_sum_assignment`,
  minimizes total distance) without replacement, real donor pool = **pooled
  real** (celeba_test + lfw + aiguard_unseen_real, n=209) for every fake
  source — each fake source matched independently against the same pool
  using its own covariate values (no cross-source borrowing of fake images,
  no per-source-specific real subsetting). Covariates standardized (z-score)
  jointly per fake-source/condition before distance computation.
- **Three matched conditions** plus the unmatched baseline:
  - `resolution_matched`: covariate = `log(orig_resolution)` only
  - `facesize_matched`: covariates = `log(face_bbox_width)`, `log(face_bbox_height)`, `crop_scale`
  - `joint_matched`: all four covariates together (the strict, primary check)
- **Caliper**: a match is discarded (`MISSING_INSUFFICIENT_MATCH`) if the
  optimal standardized Euclidean distance exceeds `0.20 * sqrt(k)` for `k`
  matching dimensions (equivalent to an average per-dimension tolerance of
  0.20 SD). Documented in `run_manifest.json`.
- **Reliability floor**: on top of the caliper, any matched arm with
  `n < 10` per group is flagged `UNRELIABLE_N<10` and excluded from the
  bar-clearing tally (Cohen's d / AUROC on n<10 is not a trustworthy
  estimate even when a handful of pairs happen to clear the caliper).
- **Metrics per source per condition**: Cohen's d (fake − real, pooled SD),
  AUROC (real=0/fake=1, so ≤0.40 = "clears bar, higher-in-real"; ≥0.60 would
  be "clears bar, higher-in-fake"; 1000-resample seeded bootstrap 95% CI).
- **Regression**: standardized logistic regression `fake ~ tex_local_variance_std
  + log(resolution) + log(face_bbox_width)`, fit two ways: (1) **primary** —
  pooled `joint_matched` set (the strictest design-based control, n=64
  total pairs across all 8 sources after caliper+reliability filtering);
  (2) **secondary/supplementary** — pooled `resolution_matched` set (larger,
  n=554 pairs, single-confound control). Each fit both naive (no source
  term) and with source fixed-effects (dummy variables). A true random-
  intercept `MixedLM` was not used: per-source matched n (5-60, further cut
  by caliper) is too small for a stable variance-component estimate for a
  binary outcome; fixed-effects dummies are the documented substitute.

## Observed (Phase 2F, cited not recomputed)

From `evidence_metrics_sourcewise.csv` (`fake_source`, effect_size=Cohen's d,
auroc = P(fake>real) convention, direction):

| source | n_fake | Cohen's d | AUROC | clears 0.60 bar? |
|---|---|---|---|---|
| aiguard_unseen | 60 | -0.204 | 0.428 | No |
| stylegan2_ood | 60 | -0.526 | 0.370 | Yes |
| df40_dit | 44 | -1.278 | 0.103 | Yes |
| df40_sit | 45 | -1.222 | 0.125 | Yes |
| df40_ddim | 45 | -1.307 | 0.093 | Yes |
| df40_pixart | 45 | -1.389 | 0.076 | Yes |
| df40_sd21 | 44 | -1.249 | 0.125 | Yes |
| midjourney | 45 | -0.090 | 0.514 | No |

6/8 clear; between-source resolution confound Spearman rho=-0.24 (flagged,
sub-threshold). This round's `a_unmatched_recomputed` rows in
`resolution_matched_results.csv` reproduce these numbers closely (tiny
differences from the 1 dropped row and different bootstrap seeds; not a
substantive discrepancy).

## Controlled result (this round)

Full numbers in `resolution_matched_results.csv` (4-way table),
`matching_balance_table.csv` (SMD before/after), `matched_pairs_manifest.csv`
(per-pair audit trail), `regression_sensitivity_results.json/csv`.

### Matching yield (how many fake images per source got a valid match)

| source | n | resolution_matched valid | facesize_matched valid | joint_matched valid |
|---|---|---|---|---|
| aiguard_unseen | 60 | 58 | 21 | 7 |
| stylegan2_ood | 60 | 60 | 8 (unreliable) | 1 (unreliable) |
| df40_dit | 44 | 44 | 3 (unreliable) | 1 (unreliable) |
| df40_sit | 45 | 45 | 2 (unreliable) | 1 (unreliable) |
| df40_ddim | 45 | 45 | 5 (unreliable) | 1 (unreliable) |
| df40_pixart | 45 | 10 (borderline reliable) | 22 | 5 (unreliable) |
| df40_sd21 | 44 | 5 (unreliable) | 36 | 8 (unreliable) |
| midjourney | 45 | 10 (borderline reliable) | 27 | 8 (unreliable) |

The joint (resolution+face-size simultaneously) condition is **data-starved
by design for this sample**: 6/8 fake sources are each captured at a single
fixed native resolution (see Phase 2F's Known Confounds §1), so a 4-D
caliper match against a real pool with continuous resolution/face-size
variance leaves very few real donors close enough on *every* dimension at
once. This is not a bug in the matching code — `matching_balance_table.csv`
confirms the few matches that do survive the joint caliper have much better
balance than the unmatched pool (e.g. df40_pixart resolution SMD 2.09 -> 0.13,
df40_sd21 resolution SMD 0.79 -> -0.57 with only 8 pairs). It means the
*joint* per-source test is underpowered with this sample size, which is
reported honestly below rather than papered over.

### Balance check (matching worked where it had enough donors)

`matching_balance_table.csv` shows the standard "pre vs post SMD" pattern
expected of successful matching: pre-match SMDs of 0.24-2.09 (resolution)
and 0.40-1.23 (face-bbox-height) shrink to <0.15 for every source/condition
where n≥10 valid matches were obtained. `figures/balance_love_plot.png` is
the visual (Love-plot style) version. Where n<10 (e.g. joint_matched for
6/8 sources), balance can look numerically good (small SMD) but the sample
is too small to trust the associated effect-size/AUROC estimate — this is
exactly why the reliability floor exists separately from the caliper.

### Four-way comparison — effect size / AUROC / direction

(`RELIABLE` = n≥10 both arms; unreliable cells shown for transparency but
excluded from the "clears bar" tally.) Full CIs in `resolution_matched_results.csv`.

| source | (a) unmatched d / AUROC | (b) resolution-matched d / AUROC | (c) facesize-matched d / AUROC | (d) joint-matched d / AUROC |
|---|---|---|---|---|
| aiguard_unseen | -0.20 / 0.43 (no) | **-0.66 / 0.30** (yes, n=58) | **-0.65 / 0.32** (yes, n=21) | -0.13 / 0.45 (n=7, unreliable) |
| stylegan2_ood | -0.52 / 0.37 (yes) | **-1.13 / 0.22** (yes, n=60) | -0.54 / 0.38 (n=8, unreliable) | NaN/1.00 (n=1, unreliable) |
| df40_dit | -1.27 / 0.10 (yes) | **-1.93 / 0.06** (yes, n=44) | -1.94 / 0.00 (n=3, unreliable) | NaN/0.00 (n=1, unreliable) |
| df40_sit | -1.22 / 0.13 (yes) | **-1.85 / 0.08** (yes, n=45) | -1.20 / 0.00 (n=2, unreliable) | NaN/0.00 (n=1, unreliable) |
| df40_ddim | -1.30 / 0.09 (yes) | **-2.30 / 0.04** (yes, n=45) | -0.40 / 0.48 (n=5, unreliable) | NaN/0.00 (n=1, unreliable) |
| df40_pixart | -1.38 / 0.08 (yes) | -1.40 / 0.10 (yes, n=10, borderline) | **-1.74 / 0.06** (yes, n=22) | -1.65 / 0.08 (n=5, unreliable) |
| df40_sd21 | -1.25 / 0.13 (yes) | -0.35 / 0.36 (n=5, unreliable) | **-1.04 / 0.16** (yes, n=36) | -1.13 / 0.17 (n=8, unreliable) |
| midjourney | -0.09 / 0.51 (no) | **+0.67 / 0.75 (yes, but FLIPPED direction, n=10, borderline)** | -0.50 / 0.40 (n=27, does not clear) | +0.54 / 0.73 (n=8, unreliable) |

Pooled-across-sources (joint-matched, all 8 sources stacked, n=32
fake/32 real): Cohen's d=-0.336, AUROC=0.368 (95% CI 0.237-0.510, so the
upper bound touches 0.50 — borderline but the point estimate and CI mostly
sit below 0.40), direction=higher-in-real, consistent with the unmatched
pooled direction.

**Key pattern**: for 6 of the 8 sources where a reliable (n≥10) matched
comparison exists, resolution-matching or face-size-matching *did not
shrink* the effect toward null — several got numerically **larger**
(e.g. stylegan2_ood AUROC 0.37 -> 0.22, df40_ddim 0.09 -> 0.04). This argues
against "the raw signal was mostly a resolution artifact" for those
sources. **midjourney is the one clear exception**: it never cleared the
bar unmatched, and under resolution-only matching (n=10, borderline
reliable) it not only fails to clear in the expected direction but flips
sign (AUROC 0.75, higher-in-fake) — the single instance of directional
instability found this round. Its face-size-matched result (n=27, reliable)
reverts to the expected direction but still doesn't clear the bar (AUROC
0.395). midjourney is therefore assessed as **not supporting** the feature,
consistent with (not worse than) its original Phase 2F non-clearing status.

### Regression sensitivity

**Primary (joint-matched, n=64 pooled)** — direction-consistent with the
matching result but **not statistically significant** at this small n:
- naive (no source term): coef=-0.438, SE=0.295, p=0.138, 95% CI [-1.02, 0.14]
- source fixed-effects: coef=-0.536, SE=0.335, p=0.110, 95% CI [-1.19, 0.12]

**Secondary (resolution-matched, n=554 pooled, well-powered)** — highly
significant, and the coefficient is essentially unchanged by adding source
fixed effects (the sign of "does source-level baseline absorb the effect"
test):
- naive: coef=-0.684, SE=0.153, **p=7.6e-6**, 95% CI [-0.98, -0.38]
- source fixed-effects: coef=-0.686, SE=0.179, **p=1.3e-4**, 95% CI [-1.04, -0.33]

Per-source individual logistic fits mostly hit perfect/quasi-separation
(statsmodels `PerfectSeparationWarning`, MLE non-convergent, `fit_regularized`
fallback used) for the 5 DF40 sources under `resolution_matched` — this is
itself informative: separation happens when a feature very cleanly predicts
the binary outcome within that subgroup, i.e. it is a *symptom of a strong
effect*, not evidence against one, but it means those per-source
coefficients/CIs are not individually trustworthy and only the pooled
fixed-effects model should be read for those sources. df40_pixart (n=20,
converged) and midjourney (n=20, converged) are the two per-source fits
that did converge under `resolution_matched`: df40_pixart coef=-9.18
(p=0.075, large because 20 points is small and separation is near-total),
midjourney coef=+1.03 (p=0.326, consistent with its matching-based
direction instability above).

**Do matching and regression agree?** Direction: yes, at every level
(matching-based and regression-based both put the coefficient/effect in the
higher-in-real direction, except midjourney in both approaches). Statistical
confidence: they disagree on the *strict joint* control (matching finds a
pooled AUROC that clears the bar with a CI brushing 0.50; regression on the
same n=64 pooled joint-matched set is not significant) purely because n=64
is underpowered for a 3-covariate logistic fit — this is a power
disagreement, not a sign disagreement. The *resolution-only* control, which
has 8.6x more pooled n (554 vs 64), agrees with the matching-based per-
source result at high confidence and is stable to adding source fixed
effects (coefficient moves <1%, p stays <1e-3), which is the strongest
piece of evidence this round that the effect is not primarily a resolution
artifact, though it does not rule out a residual joint resolution+face-size
interaction that only the underpowered strict test could detect.

## Claim boundary

**What this round supports**: after (a) resolution-only matching (design-
based) and (b) resolution+face-size-adjusted, source-fixed-effects logistic
regression (analysis-based, well-powered via the larger resolution-matched
pool), `tex_local_variance_std` still discriminates real from fake in the
higher-in-real direction for 7 of 8 fake sources sampled, with the
signal in several sources *strengthening* rather than shrinking under
matching — this is evidence against "the Phase 2F raw signal was mostly a
resolution confound" for those 7 sources.

**What this round does NOT support**:
- The strictest, single most direct test of "does it survive controlling
  for resolution AND face-size at once" (joint_matched) is **data-starved**
  for 6 of 8 sources individually (n<10 after caliper) and only
  directionally-consistent-but-not-significant at the pooled level (n=64,
  p=0.11-0.14). This round cannot claim the joint confound is *fully* ruled
  out with statistical confidence — only that nothing in the joint-matched
  data contradicts the resolution-only result, and there wasn't enough
  joint-matched data to properly test it. A larger resample (more real
  images per source, wider native-resolution real pool) would be needed to
  power that specific check.
- **midjourney does not support** `tex_local_variance_std` after matching:
  it never cleared the bar unmatched, and its one small-n resolution-matched
  result actively reverses direction. It should be treated as a named
  exception, not averaged into the pooled read.
- This is **descriptive statistics on n=44-70 per source**, not a trained-
  and-validated classifier feature. No claim is made about generalization
  to fake sources never sampled (new generators, new post-processing
  pipelines), about robustness to compression/re-encoding beyond the
  fixed q85 JPEG this pipeline applies, or about behavior once folded into
  a multi-feature model (interactions with the other 23 rejected features
  were not tested).
- "ACCEPT" in the verdict below means **"survives this round's two confound
  checks (matching + regression) on this sample"**, nothing stronger. It is
  not evidence the feature is *causally* about fakeness rather than some
  other correlate of these specific 11 sources' capture/release pipelines
  that resolution-matching and source-FE regression happen not to remove.

## Verdict: **ACCEPT_FOR_STRUCTURED_EVIDENCE** (caveated; named exception: midjourney)

Applying the pre-registered rubric mechanically:
- Direction-consistent higher-in-real on 7/8 sources across the best-
  available reliable matched condition per source (≥5/8 bar cleared: yes,
  7/8).
- Survives resolution-only matching (design-based control) for every
  source with a reliable matched sample, several *strengthening*.
- Survives resolution+face-size-adjusted, source-fixed-effects-adjusted
  logistic regression at high significance (p<1.3e-4) on the well-powered
  resolution-matched pool; the stricter joint-matched regression is
  directionally consistent but underpowered (not a contradiction, a power
  limitation, documented above).
- **midjourney is explicitly excluded from the "supports" tally** — it does
  not clear the bar unmatched or facesize-matched, and destabilizes
  (flips sign) under its one small resolution-matched sample. Per-source
  support is NOT averaged away: 7 sources support (aiguard_unseen,
  stylegan2_ood, df40_dit, df40_sit, df40_ddim, df40_pixart, df40_sd21),
  1 does not (midjourney).

This is a stronger position than Phase 2F's caveated ACCEPT (which had an
unresolved rho=-0.24 confound flag and only 6/8 sources clearing
unmatched) — the resolution confound specifically has now been checked by
two independent methods (matching and regression) and did not explain the
signal away for 7/8 sources. It remains, as stated in the Claim Boundary,
an ACCEPT bounded to "ready for further evidence-head investment", not
"proven" or "production-ready."

## What would still need to happen before this is a structured-output field

1. A resample with a real pool spanning the same native-resolution *range*
   as each fake source (not just overlapping enough for a caliper subset)
   to properly power the joint (resolution+face-size) test that this round
   could only underpower-check.
2. A trained (held-out validated) evidence head using this feature (plus
   possibly the 2 CONDITIONAL features from Phase 2F, source-stratified),
   with its own generalization test on fake sources never seen during
   matching/threshold selection here.
3. An explicit check of whether `tex_local_variance_std` reflects the same
   "lower spatial texture variability" phenomenon in fake sources not yet
   sampled (e.g. any new generator family), since this round (like Phase
   2F) is confined to the 8 sources already in the project's eval pool.

None of this is a blocker for treating the feature as a legitimate research
finding to report in the Phase 2 evidence line; it is a blocker for
treating it as validated enough to ship in any user-facing or model-facing
capacity.
