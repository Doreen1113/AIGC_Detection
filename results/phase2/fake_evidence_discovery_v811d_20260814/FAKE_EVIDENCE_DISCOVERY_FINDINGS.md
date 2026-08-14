# Fake Evidence Discovery — Findings (2026-08-14)

Companion to `results/phase2/fake_xai_level12_v811d_20260814/` (attention
faithfulness/stability audit). That audit established fake explanations are
currently one fixed template sentence regardless of image, and that
Grad-CAM++ attention is faithfulness-supported (Status B) but not
region/localization-backed (no Status C). This round asked a different
question: are there cheap, hand-computable, per-image signals — independent
of the model — that discriminate real vs fake well enough to eventually
seed a non-templated explanation? Full numbers: `evidence_metrics_sourcewise.csv`
(192 rows: 24 features x 8 fake sources), `evidence_candidate_decision_table.csv`
(24 rows, one per feature), `real_source_breakdown.csv`, `run_manifest.json`,
`figures/`.

**Sample**: 598 images total after the `pl.has_face` gate — real: celeba_test
70, lfw 70, aiguard_unseen_real 70 (pooled n=210); fake: aiguard_unseen 60,
stylegan2_ood 60, df40_dit 44, df40_sit 45, df40_ddim 45, df40_pixart 45,
df40_sd21 44, midjourney 45 (n=388). All requested counts were hit except the
6 DF40/MidJourney sources, capped at their pool size of 45 (44 achieved for
2 of them after the face gate dropped 1 image each). Seed 20260814
throughout; see `run_manifest.json` for exact per-source achieved counts.

## 1. Features showing CONSISTENT discrimination across most/all fake sources

**Exactly one** of 24 hand-computed features cleared the pre-registered bar
(direction-consistent sign of Cohen's d across all 8 sources with usable
data, AUROC ≥0.60 in the majority direction on ≥5/8 sources, no strong
resolution/face-size confound): **`tex_local_variance_std`** (std of a 5x5
sliding-window local-variance map — spatial *uniformity* of local texture
roughness), family=texture, decision=**ACCEPT_FOR_NEXT_STAGE**.

- Direction: higher-in-real on all 8 sources (real faces have MORE
  spatially-variable local texture than every fake source sampled).
- AUROC (real=0/fake=1, so lower=stronger-in-this-direction): aiguard_unseen
  0.43 (CI 0.35–0.51, does NOT clear bar), stylegan2_ood 0.37 (0.30–0.44,
  clears), df40_dit 0.10 (0.05–0.18, clears), df40_sit 0.12 (0.06–0.20,
  clears), df40_ddim 0.09 (0.06–0.14, clears), df40_pixart 0.08 (0.04–0.12,
  clears), df40_sd21 0.12 (0.07–0.19, clears), midjourney 0.51 (0.44–0.59,
  does NOT clear). 6/8 clear.
- Between-source resolution confound rho = −0.24 (below this round's 0.5
  flag threshold, but not zero — this is a real caveat, not a clean bill of
  health; see Section 3).
- This is the ONLY family-2 (texture) feature that survived; all 8 others
  in that family, and all 8 frequency-family features, and all 4
  landmark-geometry features, and all 3 boundary features, flipped sign
  across sources and were REJECTed.

No feature reached ACCEPT with zero caveats. `tex_local_variance_std` is
the single positive result this round, and it is a modest one (misses the
bar on 2/8 sources, has a non-trivial though sub-threshold resolution
correlation).

## 2. Features that only discriminate specific sources (generator fingerprints, not general fake signal)

Every one of the 8 frequency-family features and 7 of the 9 texture-family
features shows the SAME pattern: strong, often large-effect discrimination
that works in OPPOSITE directions for two source clusters —
**{aiguard_unseen, stylegan2_ood, midjourney}** vs **{df40_dit, df40_sit,
df40_ddim, df40_pixart, df40_sd21}** (see `figures/heatmap_auroc.png` — the
column-blocking pattern is visible by eye). Concretely: `freq_logmag_mean`
AUROC is 0.72–0.82 (higher-in-fake) for the first cluster but 0.00–0.44
(higher-in-real) for the DF40 cluster; `tex_lbp_uniformity` is 0.22–0.26 for
the first cluster but 0.55–0.99 for the DF40 cluster. This is the taxonomy
document's Family 1/2 "AIGuard/StyleGAN2/MidJourney vs DF40" split, and it
lines up with `between_source_resolution_confound_spearman` values ≥0.4 for
several of these same features — the most parsimonious read is that this is
a **rendering-pipeline/resolution fingerprint of the DF40 release process**
(all 5 DF40 methods here share native resolution 256–512px2 pre-224-resize,
vs AIGuard/StyleGAN2/MidJourney's different native sizes and JPEG/PNG
provenance), not a "fake-in-general" signal. `tex_autocorr_peak_sharpness`
(CONDITIONAL, clears the bar on 4/8: aiguard_unseen, stylegan2_ood,
df40_ddim, midjourney) is a partial version of the same story — and it has
this round's single strongest between-source resolution confound (rho=0.63),
so even its 4-source hits should be treated as more likely resolution than
fakeness until that confound is controlled.

## 3. Features safe to consider for a future per-image structured output field

**Only `tex_local_variance_std`, and only with a caveat, not a clean
green light.** Its between-source resolution confound (rho=−0.24) is below
this round's 0.5 flag bar, so the machine rubric marked it ACCEPT rather
than CONDITIONAL — but −0.24 is a real, non-zero correlation in a dataset
where real sources are systematically lower-resolution than most fake
sources, and this round's within-source confound check is structurally
blind for 6 of 8 fake sources (each is captured at a single fixed native
resolution, so there's no within-source variance to correlate against — see
taxonomy doc). Recommendation: before this feature goes into any structured
output field, re-run this exact measurement on a resolution-matched sample
(e.g. downsample all real/fake sources to a common native resolution before
the pipeline's own 224 resize, or restrict to sources with overlapping
native resolution) to see if the effect survives. It should NOT be shipped
on this round's evidence alone.

No other feature — including `tex_autocorr_peak_sharpness` (CONDITIONAL,
worst confound) — clears even that bar.

## 4. What this round genuinely could not answer

- **Whether the one surviving signal (`tex_local_variance_std`) reflects
  actual generation-process texture statistics or is fully explained by
  resolution** — hand-computed correlation checks can flag "confound
  present, magnitude X" but cannot fully partial it out without a
  resolution-matched or resolution-controlled resample, which this round
  did not build (see Section 3's proposed follow-up — this is a design
  fix, not an MLLM/model need).
- **Whether the AIGuard/StyleGAN2/MidJourney-vs-DF40 split (Section 2) is
  really "rendering pipeline" and not something semantically real about the
  generation method** — hand-computed features can show two clusters
  disagree but cannot explain WHY beyond correlational confound checks; a
  semantic read of what's different between the clusters (was DF40's
  release process itself doing something to the images — a canonicalization
  step, a compression pass — beyond raw pixel resolution?) needs either the
  DF40 paper/release notes (a literature check, not a measurement this
  round performed) or a human/MLLM annotator looking at paired examples and
  describing what they see, which a Cohen's-d table cannot do.
- **Whether ANY of these features localize to a manipulated region** — every
  feature computed this round is a whole-frame scalar; none can support a
  "this part of the face is suspicious" claim, and this round deliberately
  did not attempt one (Family 4's boundary rings are the closest thing to
  region-awareness and they REJECTed outright). Getting there needs either
  ground-truth manipulation masks (no such labels exist in this project per
  `docs/xai_evidence_schema.md` Tier C/D — same gap the prior XAI audit
  flagged) or an MLLM teacher asked to point at (not just describe) a region,
  cross-validated against something (the prior audit's faithfulness tests
  are the closest existing cross-validation tool, but they test attention,
  not a hand-feature).
- **Whether pose/framing (Family 3's confound) is actually masking a real
  geometry-anomaly signal** — this round's `lm_pose_yaw_proxy` diagnostic
  variable shows correlations with the geometry features (see
  `evidence_metrics_sourcewise.csv`'s per-source rows), consistent with pose
  being a real confound, but proving there's "nothing there" after removing
  pose needs either pose-normalized landmarks (a modeling step, e.g. a 3D
  face-pose-normalization model) or a same-pose-matched real/fake sample,
  neither of which exists yet.

## 5. Recommendation

**Do not start a multi-label evidence head or a distillation run yet.**
21 of 24 candidates REJECTed outright (direction-inconsistent — the
single strongest disqualifier in the rubric); 2 more are CONDITIONAL/
source-specific fingerprints, not general fakeness signals; only 1 is a
qualified, caveated ACCEPT. Training a model on this evidence set now would
almost certainly learn the DF40-vs-other-sources rendering/resolution split
identified in Section 2, not fakeness — exactly the kind of shortcut
learning this project's `docs/EXPERIMENT_REGISTRY.md`/Freeze-Gate discipline
exists to catch before it reaches a claim.

The single best next step, grounded in what actually showed up this round,
is **not** MLLM annotation and **not** a new model — it is a **narrow,
cheap re-run of the resolution-confound check that already flagged the
problem**: resolution-match (or resolution-stratify) the real and fake
samples (e.g. downsample every source to the smallest common native
resolution — likely celeba's 178x218 — before any feature computation, or
restrict analysis to sources with genuinely overlapping native resolution
distributions) and re-run this exact pipeline on the same 24 features. That
is a data-design fix, reuses 100% of the code already written
(`scripts/extract_features.py`, `scripts/compute_stats.py`), and directly
answers the one open question blocking `tex_local_variance_std` from a real
ACCEPT (Section 3) — before spending any budget on MLLM annotation,
reconstruction models, or a trained evidence head, none of which would be
trustworthy while this confound is unresolved. If `tex_local_variance_std`
survives resolution-matching, it becomes the first real candidate for a
non-templated per-image evidence field (a single scalar, described in
neutral terms like "texture uniformity score", not "smoothing artifact");
if it does not survive, this whole hand-computed-feature line should be
considered exhausted and the next real investment is either ground-truth
manipulation masks (structural prerequisite for ANY localization claim,
Section 4) or MLLM semantic annotation SPECIFICALLY to explain the DF40-vs-
other-sources cluster split (Section 4's second bullet) — not general
"describe what's fake here" annotation, which would just re-encode the
confound in free text.
