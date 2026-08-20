# Experiment Registry

> Single cross-phase index of experiments involving checkpoints, train/val/test
> source composition, and what can/cannot be claimed from each result. Created
> 2026-08-13 after a cross-phase misattribution: a Phase 1 finding (dual-head
> filter attribute failing to generalize to DF40-cdf) got mis-stated in a
> Phase 2 conversation as if it were a Phase 2 XAI-track result, and almost
> got written into `docs/phase2_story.md` as a Phase 2 finding before being
> caught. **Read this file before citing any cross-source/cross-checkpoint
> claim in either `docs/phase1_story.md` or `docs/phase2_story.md`.**
>
> Each entry is a single experiment. Fields are mandatory; leave `(unknown)`
> rather than omitting a field. `Claim` = what this result supports.
> `Non-claim` = the specific overreach this result does NOT support (always
> fill this in — it's usually where misattribution happens).

---

## Known Traps (apply to all future experiments — check both before any "beats X" claim)

> These are not entry-specific footnotes. Any new experiment in this registry
> that compares a candidate against a reference checkpoint must run BOTH checks
> below before accepting an improvement claim. Both were discovered the hard way
> in the P1-3/P1-4 chain, each after the naive comparison looked like a win.

**Known trap #1 — Threshold-vs-operating-point mismatch.** A shared/default
threshold is not a shared operating point when two checkpoints have different
global score scales (e.g. one loss adds a fixed margin, shifting every logit
up). A candidate can sweep 100% of matched-threshold comparisons purely by
trading false positives for recall, while being significantly *worse* at every
matched false-filter-rate budget. **Mandatory check: re-run any threshold-based
comparison at matched operating points (e.g. matched false-filter rate), not
matched thresholds.** Caught 4 times in this project: v8.16-uncalibrated's
11.21% (P1-2), C1/C2/C3 in P1-R3.4, K1_pairmargin in P1-R5, and — differently
— M2_refhead in P1-R6 (see trap #2, which is NOT the same failure mode).

**Known trap #2 — Operating-point mismatch inside a scale-invariant metric
(AUROC).** Even after trap #1 is checked, a candidate can have the *highest*
AUROC of all candidates — a real, scale-invariant ranking improvement, not a
rescaling artifact — while being the *worst* candidate at the low-FPR operating
region any real deployment would actually use. AUROC averages performance
across the entire ROC curve; a model can gain rank purely in a high-FPR region
(e.g. FPR ≥ 20%) that no production system operates in, while losing ground at
FPR ≤ 1-5%. This is the textbook motivation for **partial AUC (pAUC)** in any
application where false-positive cost bounds the usable FPR range (established
practice in diagnostic testing and fraud detection; see
en.wikipedia.org/wiki/Partial_Area_Under_the_ROC_Curve and the general result
that "if the application is constrained to some FPR, the only meaningful
statistic is TPR at that FPR" regardless of overall AUC). **Mandatory check:
report low-FPR TPR (or partial AUC restricted to FPR ≤ 1-5%) alongside overall
AUROC for every candidate comparison, not overall AUROC alone.** First caught in
P1-R6: `M2_refhead` posted the best in-scope AUROC (0.6211, highest of 3
candidates) but the *worst* TPR@FPR=1% (0.0084 vs the control's 0.0421) — it
only leads at FPR ≥ 20%. This is a distinct failure mode from trap #1: trap #1
is a score-scale artifact (the ranking itself is fake), trap #2 is a real
ranking change concentrated in an operationally irrelevant region (the ranking
is real but useless). Both must be checked; passing one does not imply passing
the other.

**Known trap #3 — path/stem disjointness is not content disjointness.** Every
integrity gate this project has ever written — P1-2's v8.16 build, P1-R7's G7,
P1-R9/R10's `gate_stems()` — matches on absolute file path or filename stem.
Both are structurally blind to *the same photograph stored under a different
name*, which is how **63.8% of the StyleGAN2 "OOD" gate, 23.5% of the Alibaba
gate, and a byte-identical CelebA train/test pair** all passed every prior
check undetected (found in P1-9/P1-R11, which was the first round to run a
content key at all). **Mandatory for any future split build or disjointness
claim: a content key — SHA256 of *decoded pixels* for exact matches (catches
re-encodes and renames), plus a perceptual hash used as a screen and then
resolved with a stronger similarity measure for near-duplicates.** Note the
sub-trap discovered in the same round: a 64-bit dHash at Hamming ≤ 4 is **far
too permissive on aligned face crops** — 83% of its hits were false positives,
and one photo matched a StyleGAN2 fake, a CelebA photo and an FFHQ photo
simultaneously, which cannot all be true. **Use dHash as a screen only, never
as the verdict.** This trap differs from #1 and #2 in kind: those are about
*comparing* two models fairly, this one is about whether the evaluation set
was ever independent in the first place.


**Known trap #4 — a between-group correlate is not a within-group causal
lever.** P1-R12 measured `|cos(u, n)|` across the four filter types, found it
rank-ordered per-type AUROC *perfectly* (ρ = −1.0), and handed the next round a
falsifiable screen: reduce `|cos|` and AUROC should follow. P1-R13 tested it and
it is **false**. Two independent refutations: (a) driving `|cos|` from ~0.9 to
~0.05 in closed form, by projecting out nuisance principal components, buys
≤ +0.02 AUROC with inconsistent sign; (b) ordinary continued training with **no
intervention at all** cut `|cos|` 10× on smoothing and 4.4× on face_reshaping
and made **both worse**, while *raising* whitening's `|cos|` and making whitening
*better* — the screen was correct on **1 of 4** types, and within-type
Spearman(`|cos|`, AUROC) across four checkpoints came out **+0.40 / +0.32 /
0.00 / +1.00**, i.e. the *opposite* sign to the prediction. Two compounding
errors made the original look convincing: a perfect rank correlation at **n = 4**
has two-sided p ≈ 0.083 and is not significant, and a quantity that separates
*groups* (here, filter types, which differ in many ways at once) carries no
implication that *moving* it within a group moves the outcome. **Mandatory for
any future "quantity X predicts performance, so optimize X" claim: (i) report the
sample size and significance of the correlation, never a bare ρ from a handful of
groups; (ii) demonstrate the relationship *within* a group by actually perturbing
X across ≥3 checkpoints or ≥3 closed-form settings, before spending a training
run on it.** The screen that survived this test in the same round, and that is
recommended in its place, is **out-of-sample Fisher/LDA AUROC on frozen features
versus the model's achieved AUROC**: it costs one embedding pass, it is a direct
measurement of headroom rather than a proxy for it, and it correctly redirected
P1-R13 in ~20 minutes.

---

## Cross-Phase Decision: Phase 1 Freeze Gate (2026-08-13)

> Recorded here for cross-phase visibility because this registry is the
> shared index — **ownership and execution of this gate belongs to Phase 1**,
> not Phase 2. Phase 2 (this session) is recording it, not enforcing it.

Rationale: every new OOD failure found (Shadow domain gap, DF40-cdf
cross-source failure, etc.) could otherwise justify an unbounded next
training round. Splitting requirements into a release gate (must all pass to
freeze a baseline) and stretch goals (tracked as limitations/future work,
non-blocking) gives Phase 1 a defined stopping point.

**A. Freeze gate (all must pass to call a version a frozen static-image baseline)**

| Category | Metric | Gate | v8.11 status |
|---|---|---:|---:|
| Core 3-class | True Test fake recall | ≥95% | ~99% |
| Core 3-class | True Test filter recall | ≥90% | 93.6% |
| Paired filter | True Test paired balanced accuracy | ≥80% | 81.1% |
| Fake OOD | AIGuard-unseen AUROC | ≥0.80 | 0.815 |
| Real OOD | CelebA real recall | ≥95% | 99.7% |
| GAN OOD | StyleGAN2 fake recall | ≥95% | 99.6% |
| Filter OOD | Alibaba filter recall | ≥95% | 98.1% |
| Safety | clean-fake false-filter | ≤5% | (reported separately per dual-head version) |
| Mobile artifact | fp32 TFLite combined size | ≤25 MB | 20.91 MB |
| Deployment | iPhone real-device test | must complete | **not yet done** |

v8.11 passes essentially all core static-image metrics; the iPhone test is
the one open item, so pending that it can be called a "frozen research
baseline / pre-deployment production baseline."

**B. Stretch goals (tracked, do NOT block freezing A)**

| Stretch goal | Target | Current |
|---|---:|---|
| Shadow paired balanced accuracy | ≥60% | 43.5% |
| Shadow filter recall | ≥40% | low (see Shadow section, TODO.md) |
| Fake+filter end-to-end misclassification | ≤2% | 3.71% |
| Cross-source `has_filter` joint recognition | ≥25% | 4.53% (v8.16, see P1-2) |
| FF++ fake recall | ≥70% | not currently met |
| int8 deployment | no correctness regression | blocked (FFT branch, see mobile deployment entries) |

**C. Robustness gate (kept separate from classification gates, per-class recall required, not just overall accuracy)**

| Perturbation | Minimum gate | Note |
|---|---:|---|
| JPEG q70 | must not collapse; report full per-class recall | never just overall accuracy |
| JPEG q50 | stress test only, no pass requirement | extreme compression |
| Downscale 4x | real/filter recall must not swing severely one-sided | esp. watch real→filter |
| Blur k5 | stress test only | filter texture cues naturally affected |
| Blur k9 | failure characterization only | not a formal pass gate |
| Lighting | report per-class recall + error direction | esp. whether Layer1 routes real→manipulated |

This reflects an existing finding (`docs/paper_outline.md` section 4.4):
overall accuracy stays 70-89% under perturbation while real/filter recall
swing in opposite directions by up to 88pp — aggregate accuracy hides this,
so gates must be per-class.

---

## P2-P0: production v8.11 filter Grad-CAM++ vs. paired GT (re-validation)

- **Phase**: Phase 2 (XAI / explanation validation track)
- **Purpose**: The Grad-CAM++-vs-region-head study (section 5 of
  `docs/phase2_story.md`, `results/xai_comparison_eye_face_white.json`) ran
  on `shufflenet_v2_3class_v88.pth` — a flat 3-class model, NOT the
  hierarchical architecture actually in production. Check whether "Grad-CAM++
  localizes filter effects well" still holds on the real deployed model.
- **Model checkpoint**: `shufflenet_v2_layer1_v811d.pth` +
  `shufflenet_v2_layer2_v811.pth` — same as `pipeline.py`'s
  `LAYER1_WEIGHTS_PATH`/`LAYER2_WEIGHTS_PATH`, i.e. actual production.
- **Test source**: `filter_data/{type}/` — same self-built paired real+filter
  data the v8.8 study used (eye_enlarging/face_reshaping/whitening/smoothing,
  100 each). GT method: `generate_landmark_gt.py`, unchanged.
- **Results**: `results/phase2_p0_v811_filter_gradcam_validation_20260813.json`.
  Script: `phase2_p0_v811_filter_gradcam_validation.py`.
  - eye_enlarging IoU 0.467→**0.549** (+0.082), face_reshaping IoU
    0.466→**0.516** (+0.050) — holds up or improves on v8.11.
  - whitening IoU 0.448→0.372 (−0.076, modest), but PointingGame
    **0.880→0.357 (−0.523)** — heatmap shape still roughly covers GT, but the
    single peak-activation pixel frequently falls outside it. v8.11-specific
    problem, not present in the v8.8 study.
  - Coverage breakdown (Layer1 routing / Layer2 favor-filter / final filter
    accuracy) reported separately per type so "never reached filter" isn't
    conflated with "reached filter but heatmap wrong" — whitening has the
    lowest Layer1 routing coverage (86.9%), consistent with v8.11's known
    real-recall weakness.
- **Claim**: Production v8.11's filter Grad-CAM++ localization is as good or
  better than v8.8's for eye_enlarging/face_reshaping. Whitening has a new,
  specific peak-instability problem (PointingGame collapse) not present in
  the v8.8 architecture — must be reported separately, not folded into a
  blanket "Grad-CAM++ still works on v8.11" statement.
- **Non-claim**: Does not re-validate region_head_v4 or LRP-approx on v8.11
  (both trained/calibrated on v8.8 features specifically; not re-run here).
  Does not diagnose WHY whitening's peak moved — only confirms the
  phenomenon exists. n=100/type, same scale as the original v8.8 study, not
  a bigger sample.
- **Status**: Complete for its stated scope; whitening peak-instability root
  cause is an open follow-up (low priority, not blocking).

  **Follow-up (2026-08-13, optional diagnostic, now done): root cause found
  — position-invariant peak, not a preprocessing bug.**
  `phase2_whitening_pointinggame_diagnostic.py` reran the 20 whitening
  images with `gradcam_PointingGame==0` from the run above, classified where
  the Grad-CAM++ peak lands relative to the detected face bbox and the 8
  named region boxes. **85% of failure cases (17/20) have their peak within
  3px of the SAME absolute pixel, (80,111) in the standardized 224x224
  frame** — regardless of where the face actually sits in the crop, its
  scale, hair, glasses, or background (visually confirmed in
  `results/phase2_whitening_peak_diagnostic_20260813/contact_sheet.png`: the
  peak marker sits in nearly the same on-screen spot across faces of very
  different sizes/positions). This rules out both hypothesized outcomes it
  was designed to distinguish between (a fixable GT-alignment/preprocessing
  bug, or peaks simply landing somewhere reasonable-but-imprecise inside the
  face) — instead it's a third finding: **for these failure cases,
  Grad-CAM++'s peak for the filter_head's whitening decision is dominated by
  a near-constant positional bias, not image-specific content.** A truly
  image-driven attention mechanism would track the face's actual position;
  this doesn't.
  - **Claim**: The whitening PointingGame collapse (P2-P0 above) is at least
    partly explained by a specific, position-invariant peak artifact, not
    random noise or a GT/preprocessing bug.
  - **Non-claim**: Does not explain WHY the peak is position-invariant (e.g.
    whether it's an FFT-branch effect, a training-data artifact, or
    something else) — that would need further architecture-level
    investigation, not attempted here. n=20, all drawn from the same
    failure-case pool as P2-P0, not an independent sample.
  - **Decision**: No fix attempted (per the task brief, this is a diagnostic
    stop, not a fix task). **Strengthens, does not weaken, the existing
    whole-face / no-precise-claim policy for whitening** (see
    `docs/phase2_story.md` §11) — a heatmap this position-invariant should
    not be read as pointing at anything in particular, which is exactly what
    the current policy already assumes.
  - Output: `results/phase2_whitening_peak_diagnostic_20260813/` (contact
    sheet, per-case CSV, summary.json).

---

## P1-1: v815-Cell-C DF40-cdf replication (filter-head cross-source generalization)

- **Phase**: Phase 1 (classifier / dual-head architecture track)
- **Purpose**: Test whether v8.15-Cell-C's filter_head generalizes beyond the
  AIGuard/fake photographic style it was trained/threshold-selected on.
- **Model checkpoint**: `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth`
  (Layer1 frozen at `shufflenet_v2_layer1_v812.pth`), threshold=0.85
- **Train source**: `v815_clean_train.txt` (AIGuard/fake-dominant; ⚠️ P1-0
  finding: still mixed-domain, contains 11,254 DF40-cdf rows — see TODO.md,
  not a clean ff/cdf Protocol-2 split)
- **Validation source (threshold selection)**: `v815_clean_val.txt` (canonical,
  same mixed-domain composition as train)
- **Test source**: `splits/v815_replication_set.tsv` (995 rows incl. header) /
  `v815_replication_set/` (994 images) — 200 base images from **DF40-cdf**
  (multiple sub-methods, e.g. `DF40-cdf-DiT`), each paired clean + up to 4
  filter conditions. Built by `build_v815_replication_set.py`.
- **Image-disjoint from train/val?**: Yes — `used_in_v815_training` column in
  the manifest tsv is `False` for all 994 rows (explicitly tracked, not
  assumed).
- **Source-disjoint from train/val?**: Partially — DF40-cdf as a *dataset* was
  not deliberately excluded from `v815_clean_train.txt` (see P1-0 caveat
  above), but these specific 200 base images were never seen.
- **Participated in model selection (threshold=0.85, checkpoint choice)?**: No
  — confirmed by construction (200 images sampled specifically to have never
  touched training/threshold-selection/any prior eval).
- **Results**: `eval_replication_set.py` / `eval_replication_auroc.py`.
  Numbers recorded in `TODO.md` (search "Joint recognition... 2.02%"), not
  archived as a separate `results/*.json` — script + input manifest are
  reproducible, but the exact run's raw log was not saved separately.
  - Joint recognition (fake AND filter both correct): canonical val 56.99% →
    replication set (DF40-cdf) **2.02%**
  - Fake-head recall: ~99% (canonical) vs 100% (replication) — fake detection
    itself generalizes fine
  - Clean-fake false-filter rate: 4.59% (canonical) vs 0.00% (replication) —
    over-conservative on the new domain, not over-triggering
  - filter_head AUROC (not just threshold-clipped accuracy, to rule out "just
    a calibration problem"): **0.5304 overall** (chance level), whitening_medium
    0.4620 (worse than chance); clean_fake vs fake+filter p_filter score
    distributions almost completely overlap (mean 0.0695 vs 0.1148)
  - Per-type collapse: eye_enlarging 0.0%, face_reshaping 0.0%,
    whitening_medium 0.0%, smoothing_medium 8.1%
- **Claim**: v8.15-Cell-C's filter_head learned "AIGuard/fake photographic
  style × self-built filter pipeline" combined artifacts, not a filter
  attribute that transfers across fake-generation sources. This is a genuine
  representational failure (AUROC at chance), not a threshold/calibration
  issue. Echoes the previously-established Shadow-vs-True-Test finding
  (filter detection fails across different REAL-photo base styles) — this is
  the analogous failure across different FAKE-generation sources.
- **Non-claim**: This does NOT say anything about Grad-CAM++ localization
  quality, IoU/PointingGame against paired GT, or the artifact classifier's
  per-type accuracy on AIGuard-sourced composites — those are separate
  questions answered by P2-C1/P2-C2 below, on different (AIGuard-only) data,
  and remain valid as in-domain results regardless of this finding.
- **Status**: Reported with full provenance in TODO.md (2026-08-13 entry,
  "重大修正：C@0.85 的 joint recognition 完全不能跨 fake 來源泛化"); script
  and input manifest exist and are re-runnable; treated as established,
  triggered the v8.16 decision below.
- **Downstream decision**: v8.16 (Source-Diverse Composite Training) launched
  in response — manifest builder `build_v816_manifest.py` exists (adds
  DF40-ff sources: sd2.1/DiT/SiT/ddim/pixart, all 8 filter conditions, paired
  clean/filtered supervision, DF40-cdf entirely excluded and reserved as the
  frozen external replication test). Manifest `splits/v816_manifest.tsv`
  (16,145 rows, each with `base_fake_path`/`filtered_fake_path`/
  `source_dataset`/`domain` — same shape as P1-1's manifest, ready for a
  stratified eval to key off) has been generated.

  **UPDATE (2026-08-13, later same day): resolved.** `shufflenet_v2_layer2_
  v816_mixedlineage.pth` — first observed as an unvalidated file — now has
  full gate numbers recorded in `TODO.md`. See **P1-2** below for the
  outcome: negative but informative, not promoted to production. The
  reasoning that follows was correct procedure at the time (a file existing
  is not validation) and is kept for reference on how this project handles
  in-flight artifacts, but is superseded by P1-2's actual result.

  <details><summary>Original caution note (2026-08-13, earlier same day, superseded)</summary>

  A checkpoint file (`shufflenet_v2_layer2_v816_mixedlineage.pth`) now
  exists on disk (first observed 2026-08-13, timestamp minutes before this
  registry entry was written) — presumably from a concurrent Phase 1 session.
  This is NOT the same thing as "v8.16 is ready to build on." No `TODO.md`
  entry, canonical-val gate numbers, or DF40-cdf frozen-replication numbers
  exist for it yet. Per this project's own checkpoint-promotion discipline
  (v8.11 required 7 gates before replacing v8.8; v8.15-Cell-C itself was only
  called a "research baseline" after passing its own val-set checks), a file
  appearing on disk is not validation.

  </details>

---

## P1-2: v8.16-mixed-lineage (Source-Diverse Composite Training) — outcome

- **Phase**: Phase 1 (classifier / dual-head architecture track)
- **Purpose**: Test whether adding fake-source diversity to filter_head's
  training data (P1-1 showed it fails to generalize past AIGuard/fake) fixes
  the DF40-cdf generalization failure.
- **Model checkpoint**: `shufflenet_v2_layer2_v816_mixedlineage.pth`, init
  from Cell C, same architecture (unfreeze conv5 + FFT last layer, no
  invariance loss) — only the training DATA changed, not the architecture.
- **Train source**: Cell C init (⚠️ ancestry audit `audit_cellC_checkpoint_
  ancestry.py` found Cell C's own lineage already carries ~11,000-11,700
  DF40-cdf rows going back to v812 — v8.16 is NOT a clean ff/cdf Protocol-2
  split, labeled `v816-mixed-lineage` precisely because of this) + new
  `build_v816_manifest.py` composite pairs: AIGuard/fake + DF40-ff (sd2.1/
  DiT/SiT/ddim/pixart, 5 methods), ~300 base images/source, all 8 filter
  conditions, paired clean/filtered supervision (16,144 new pairs).
- **Validation source (threshold selection)**: `v816_val.txt`, **in-domain
  only** — DF40-cdf never participates in threshold selection, by design.
- **Test source**: same frozen `v815_replication_set` (DF40-cdf) P1-1 used —
  untouched by v8.16 training, genuinely held out.
- **Image/source-disjoint from train?**: DF40-cdf entirely excluded from
  v8.16's own new training data by construction; a filename-collision bug
  (different DF40 generators sharing FF++ frame numbers, e.g. sd2.1 and ddim
  both having `766_360.png`) was caught and fixed before final assert checks
  passed (global stem-based split assignment instead of per-source).
- **Results**: recorded in `TODO.md` (2026-08-13, "v8.16-mixed-lineage...完整驗證"),
  not yet copied into a separate `results/*.json`.

  | Metric | Cell C@0.85 | v8.16@0.85 (uncalibrated) | **v8.16@0.95 (calibrated)** |
  |---|---:|---:|---:|
  | DF40-cdf filter-head AUROC | 0.5304 | 0.6182 | (same, threshold-invariant) |
  | DF40-cdf joint recognition | 2.02% | 11.21% (inflated) | **4.53%** |
  | In-domain clean-fake false-filter | 4.59% | 10.04% | **2.97%** |
  | In-domain joint recognition | 56.99% | 61.40% (inflated) | **42.33%** |

  **The uncalibrated 11.21% was a false positive**: threshold=0.85 made
  filter_head over-trigger (in-domain false-filter rate roughly doubled),
  which mechanically inflates joint recognition without the model actually
  discriminating better. Re-threshold-swept on `v816_val.txt` (in-domain
  only) to 0.95 before drawing any conclusion — the calibrated 4.53% is the
  real number.
  - Per-type breakdown (calibrated): residual improvement concentrated in
    smoothing_medium (18.2%), ddim (15.0%), SiT (4.2%), DiT (3.5%);
    **whitening_medium, eye_enlarging, face_reshaping, pixart, sd2.1 are all
    0.0% — zero residual transfer for these.**
- **Claim**: Adding ONE additional fake source (DF40-ff, 5 methods, ~300
  base images/source) to filter_head training does produce a real,
  measurable (if small) cross-source signal — DF40-cdf joint recognition
  moved from 2.02% (P1-1) to 4.53%, more than double, and this survives
  proper in-domain-only threshold calibration. This rules out "cross-source
  filter attribution is fundamentally unlearnable" — some of it transfers.
- **Non-claim**: 4.53% is nowhere near a usable joint recognition rate. This
  does NOT claim v8.16 solves or meaningfully mitigates cross-source
  generalization — it demonstrates the mechanism partially works while
  showing the current scale/method (one extra source, ~300 images/source) is
  insufficient. Does NOT claim uniform improvement — 5 of 9 tested
  type/method combinations show literally zero residual transfer.
- **Status**: Complete. **Decision: v8.16-mixed-lineage is a research
  candidate — not promoted to pipeline.py, does not replace v8.11, does not
  claim cross-source generalization is solved. No further data/threshold
  iteration or a v8.17 attempt is planned off the back of this result** — it
  is treated as a settled negative-but-informative finding (adding one
  source isn't enough; that's different from "adding sources doesn't work
  at all," which remains an open question for a differently-scaled future
  attempt, not an active workstream right now).

---

## P2-C1: Composite Explanation Protocol (fake+filter, AIGuard-only)

- **Phase**: Phase 2 (XAI / explanation validation track)
- **Purpose**: Given a fake+filter composite image, can the filter component's
  Grad-CAM++ heatmap be validated against paired ground truth, and is the
  attention faithful?
- **Model checkpoint**: same as P1-1 (`shufflenet_v2_layer2_v815ablation_
  cellC_unfreeze1_inv0.pth` + `shufflenet_v2_layer1_v812.pth`, threshold=0.85)
  — reused as-is, no retraining in this experiment.
- **Train/val source**: n/a (no training performed; this experiment only runs
  inference + post-hoc explanation on an existing checkpoint)
- **Test source**: `fake_filter_hard_neg/{type}/` — **AIGuard/fake ONLY**
  (built by `generate_fake_filter_hard_neg.py`, which samples exclusively
  from `AIGuard/fake`). 40 images (10/type × 4 types) for this run.
- **Image-disjoint from P1-1's replication set?**: Yes, disjoint by
  construction (different source directories: AIGuard/fake vs DF40-cdf).
- **Source-disjoint from P1-1's replication set?**: Yes — this experiment
  never touches DF40 in any form.
- **Results**: `results/phase2_composite_explanation_v1_20260813.jsonl` +
  `_summary.json`. Script: `phase2_composite_explanation.py`.
  - filter_status=='detected' coverage: 31/40 (77.5%)
  - Conditional on detection: mean IoU=0.398, mean PointingGame=0.774 against
    paired landmark/LAB-diff GT (base image = the known AIGuard/fake source,
    same method as `generate_landmark_gt.py` uses for real+filter pairs)
  - Blur-based faithfulness (k=20%) on filter_head score: mean_hot_drop
    near-zero/negative (-0.0396) — anomalous, see script's `key_finding` for
    the "blur masking may itself inject a smoothing-like signal" hypothesis
- **Claim**: On AIGuard/fake-sourced composites specifically, the filter
  component of a fake+filter explanation can use the SAME Tier A (paired-GT)
  evidence standard as clean real+filter pairs — localization quality
  (IoU/PointingGame) is comparable to the established filter_data/ study.
- **Non-claim**: Does NOT claim this coverage/localization quality holds for
  any other fake source (DF40 or otherwise) — see P1-1 above, which shows the
  filter_head's underlying signal does NOT transfer to DF40-cdf. Does NOT
  claim blur-based faithfulness is a valid method for filter_head (see
  key_finding). Small n=40, diagnostic scale, not a publication-scale study.
- **Status**: Complete for its stated (AIGuard-only) scope. Not run against
  any other fake source — this is a scope boundary, not a pending task,
  unless/until a cross-source composite GT set is built (does not currently
  exist for the paired-GT method specifically, distinct from P1-1's
  replication set which has no paired GT, only class labels).

---

## P2-C2: Filter-type accuracy on fake+filter composites (AIGuard-only)

- **Phase**: Phase 2 (XAI / explanation validation track)
- **Purpose**: Does the artifact (filter-type) classifier, validated on clean
  real+filter pairs, stay accurate when the base image is fake instead of real?
- **Model checkpoint**: `artifact_classifier_v3.pth` (production, same as
  `pipeline.py` uses) — NOT the same checkpoint as P1-1/P2-C1 (that's the
  dual-head Layer2; this is the separate 4-way filter-type classifier).
- **Test source**: `fake_filter_hard_neg/{type}/` — **AIGuard/fake ONLY**,
  same source restriction as P2-C1. 200 images (50/type × 4 types).
- **Ground truth**: folder label (exact, by construction — no separate GT
  pipeline needed, unlike P2-C1's pixel-level GT).
- **Results**: `results/phase2_composite_filtertype_accuracy_v1_20260813.json`.
  Script: `phase2_composite_filtertype_accuracy.py`.
  - face_reshaping 92%, smoothing 94% — reliable
  - eye_enlarging 70%, **whitening 6%** — unreliable, whitening systematically
    misclassified as eye_enlarging/face_reshaping
- **Claim**: On AIGuard/fake-sourced composites, filter-type accuracy is
  usably high for 2/4 types (face_reshaping, smoothing) and unreliable for
  2/4 (eye_enlarging, whitening).
- **Non-claim**: This is an **in-domain (AIGuard/fake) number only**. Does NOT
  claim general "fake+filter type recognition" accuracy — no cross-fake-source
  test of the artifact classifier exists yet (would need a DF40-based
  composite set analogous to P1-1's, but for the 4-way type classifier, which
  P1-1 did not test — P1-1 tested the dual-head filter_head's binary
  detection, not the separate artifact_classifier_v3's type prediction).
- **Status**: Complete for its stated (AIGuard-only) scope. Cross-source type
  accuracy is an open question, not yet measured by any experiment in this
  registry.

---

## P1-3: P1-R3→R5 chain — scale-normalized filter generator, cross-source retraining, and filter-type failure anatomy

- **Phase**: Phase 1 (fake+filter cross-source generalization track, continues P1-1/P1-2)
- **Purpose**: P1-1/P1-2 left an open question — does the fake+filter cross-source
  failure trace to the v1 filter generator's fixed-pixel parameters (15px
  smoothing kernel, 60px face_reshaping warp radius) making the same class label
  mean different actual filter strength at different resolutions/face sizes? This
  chain (P1-R3.0 → R3.0b → R3 autonomous → R3.4 → R5) answers it end to end:
  build a scale-stable generator, retrain on it, test fairly, then diagnose what's
  left.
- **Model checkpoints**:
  - Generator-only (no detector training): `filters_v2/scale_normalized_filters.py`
    (face_reshaping_v2, eye_enlarging reference), `filters_v2/revisions/r3_0b/
    candidates.py` (smoothing_S2), `filters_v2/revisions/p1_r3_autonomous_20260818/
    whitening_candidates.py` (whitening_W5).
  - Trained research candidates: `C1_sn_swap`, `C2_sn_multilabel`, `C3_sn_multiscale`
    (`checkpoints/research/p1_r3_autonomous_20260818/`) and `K0_calib`/`K1_pairmargin`/
    `K2_nuisancevar`/`K3_dosereg` (`checkpoints/research/p1_r5_filter_type_
    anatomy_20260818/`), all research-tier, none promoted.
  - Reference checkpoints used for comparison, unmodified: `shufflenet_v2_
    layer2_v815ablation_cellC_unfreeze1_inv0.pth` (Cell C) and `shufflenet_v2_
    layer2_v816_mixedlineage.pth` (v8.16, see P1-2 above).
- **Train source**: scale-normalized composite pairs built from non-cdf sources
  only (AIGuard/fake + DF40-**ff** domain, 5 methods) — `splits/research/
  p1_r3_autonomous_20260818/`. C1/C2/C3 differ only in data/label recipe; K0-K3
  are loss-side-only variants on **byte-identical** data/splits/init/seed/schedule
  as C1 (K0 does no retraining at all — temperature-scaling only).
- **Validation source**: in-domain held-out split of the same R3.1 data, never
  DF40-cdf.
- **Test source (final, one-shot only)**: two disjoint DF40-cdf sets — (1)
  `splits/v815_replication_set.tsv`, the original P1-1/P1-2 replication set,
  built with the **v1 fixed-pixel generator** (legacy dose); (2) a second,
  newly-built dose-aligned set from `splits/research/
  p1_r3_4_scale_normalized_heldout_20260818/`, built with the **scale-normalized
  v2 generator** on cdf sources proven disjoint from set (1) (0 overlap on
  source_stem/path/`already_used_stems()`). Set (2) exists specifically because
  testing scale-normalized-trained candidates against a v1-generator eval set is
  itself a confound — see Known Trap below.
- **Image-disjoint from train/val?**: Yes, both held-out sets proven disjoint
  from all R3.1/R3.2/R5 training and validation data on multiple independent
  keys (absolute path, source stem, row stem); logged per-round.
- **Source-disjoint from train/val?**: Yes — DF40-cdf is entirely excluded from
  all training data in this chain by construction (training only ever used
  ff-domain + AIGuard/fake).
- **Participated in model selection?**: No. Both DF40-cdf sets were opened
  exactly once each, after all candidate selection and threshold freezing was
  already complete (frozen via in-domain-only rules, logged in
  `heldout_frozen_thresholds.json` before any held-out file was read).

### Results by round

1. **P1-R3.0 / P1-R3.0b** (`results/research/p1_r3_0_scale_normalized_generator_
   calibration_20260817/`, `..._p1_r3_0b_selective_generator_revision_20260817/`)
   — generator scale-stability only, no detector involved. Final state:
   face_reshaping_v2 CV 0.041 (v1 0.547, PASS), smoothing_S2 CV 0.045 (v1 0.068,
   PASS), whitening_W5 CV 0.00072 (v1 0.051, PASS), eye_enlarging CV 0.269
   (unchanged from v1, does **not** meet the scale-stability gate — carried
   forward as REFERENCE_UNCHANGED, not fixed, not blocking).
2. **P1-R3 autonomous / P1-R3.4** (`results/research/p1_r3_autonomous_20260818/`,
   `..._p1_r3_4_scale_normalized_heldout_20260818/`) — trained C1/C2/C3 on
   scale-normalized data. On the v1-generator eval set (1), candidates looked
   competitive with v8.16 (joint recognition 14.6-15.1% vs v8.16's 4.53%) but a
   threshold-matched re-analysis showed the gain was a pure operating-point
   artifact (v8.16 wins 7/7 at matched thresholds). On the dose-aligned eval set
   (2), all three ΔAUROC vs v8.16 are non-significant and slightly negative;
   verdict `NEGATIVE_CONFIRMED`. Incidental finding: under dose-aligned testing,
   v8.16's own source-wise AUROC std shrank 0.088→0.025 (pixart 0.528→0.687,
   sd2.1 0.537→0.636) — most of the evidence base for a "source shortcut"
   requiring source-invariance machinery (DID/GRL) turned out to be a generator
   dose-mismatch artifact, not a real source-identity signal. **DID/GRL/generic
   source-invariance work is therefore explicitly deferred**, not because it was
   tried and failed, but because the evidence that motivated it weakened
   substantially — do not re-open without new evidence.
3. **P1-R5** (`results/research/p1_r5_filter_type_anatomy_20260818/`) — with the
   dose confound closed, the residual failure axis is filter **type**, not
   source: dose-aligned in-domain AUROC smoothing=0.905 vs whitening=0.586 /
   eye_enlarging=0.603 / face_reshaping=0.594. Root cause and 4 candidates below.

### P1-R5 root cause — OBSERVED/SUPPORTED, quantified

Smoothing is more recognizable **not because its physical effect is larger**
(paired LAB ΔE: whitening 4.48 vs smoothing 4.78, within 7%) but because the
effect is larger **relative to the natural between-image variance of the score
it perturbs**: signal/nuisance ratio (|mean Δlogit| ÷ SD(clean-fake logit)) is
1.182 for smoothing vs 0.242 (whitening) / 0.330 (eye) / 0.405 (reshaping). The
model is *not blind* to the weak types — paired win rate (does the filtered
image score higher than its own clean partner?) is 78-84% for all three — it
fails at the population/single-image level because that per-pair signal drowns
in cross-image variance when there's no reference to compare against. This is a
**signal-to-nuisance-variance problem intrinsic to reference-free single-image
inference**, confirmed at both the raw-pixel-statistic and model-representation
levels (full tables/figures: `results/research/
p1_r5_filter_type_anatomy_20260818/DIAGNOSIS_CONCLUSIONS.md`,
`diagnosis_summary.csv`, `phase_a_hypothesis_verdicts.json`).

**Hypotheses tested and rejected (do not re-test without new evidence):**

| hypothesis | verdict | how it was killed |
|---|---|---|
| H-DOSE (weak types just have weaker physical effects) | REJECTED | whitening dose within 7% of smoothing's, 0.25 lower AUROC anyway |
| H-AUG (ColorJitter teaches invariance to whitening specifically) | REJECTED | a luminance push calibrated to whitening's own ΔL reproduces only 12-17% of whitening's logit response — model reads masked facial structure, not raw luminance |
| H-DATA (per-type training sample imbalance) | REJECTED | exactly 764 composite rows/type by construction; background-sample counts are *anti*-correlated with performance |
| H-CAL (a decision-layer/threshold artifact) | REJECTED, demonstrated not asserted | K0_calib control: in-domain temperature fit returns T=1.00 everywhere; temperature scaling is monotone, provably cannot change AUROC |
| H-GEOM (geometric displacement is sub-pixel at 224px input) | SUPPORTED (eye_enlarging), PARTIAL (face_reshaping) | mean landmark displacement 0.24px (eye) / 0.92px (reshaping); eye's native displacement (0.55px) is barely above the ~0.45px landmark-detector noise floor **measured on this project's own clean, controlled composite images** — do **not** generalize this ceiling to in-the-wild/user-uploaded photos, where landmark detector error is typically far higher (double-digit px on unconstrained benchmarks) and the "near the noise floor" conclusion would not hold |

**Four candidates tried, held-out (dose-aligned set), all fail:**

| candidate | mechanism | held-out ΔAUROC vs v8.16 (primary set) | verdict |
|---|---|---:|---|
| K0_calib | per-type temperature scaling only, no retrain | n/a (provably can't change AUROC) | closes "just recalibrate" as a fix |
| K1_pairmargin | margin loss raising filtered-vs-clean-partner logit gap | −0.0008 (ns overall); per-type positive but ns (whitening +0.014, eye +0.005, reshaping +0.019); smoothing **significantly regresses** (−0.041) | **false win, see Known Trap below** |
| K2_nuisancevar | penalize clean-fake logit variance directly | not applicable (failed pre-declared in-domain smoothing guard, −0.0394 significant, never reached held-out) | mechanically worked (variance 1.46→0.18) but destroys signal along with noise |
| K3_dosereg | auxiliary head regressing measured physical dose (LAB ΔE etc.) | −0.0087 (ns); tracks the λ=0 control (C1) within noise on every weak type | no effect attributable to the added supervision |

### ⚠️ Known trap: threshold-matched comparison is a MANDATORY check, not optional

This is the **third time** in this research chain (P1-R3 autonomous → P1-R3.4 →
P1-R5) that a candidate showed an apparent win at a shared/default threshold
that reversed or vanished once operating points were matched instead of
thresholds. In P1-R5 specifically: K1_pairmargin swept **7/7** matched
thresholds on both held-out sets — the first candidate in this whole chain to
ever do that — which reads exactly like a breakthrough. Re-run at matched
**false-filter budgets** (operating points invariant to monotone rescaling), K1
is significantly better at **0/6** budgets and significantly worse at 4-5/6,
because the margin loss inflates joint recognition purely by shifting global
score scale (2-5x the false-filter rate at the same nominal threshold). **Any
future candidate comparison in this project must include a matched-operating-
point (not matched-threshold) re-analysis before a "beats v8.16" claim is
accepted** — a shared threshold is not a shared operating point when score
scales differ, and this project has now been fooled by exactly this three times
(v8.16-uncalibrated-11.21% in P1-2, C1/C2/C3 in P1-R3.4, K1 here).

- **Claim**: (1) The v1 fixed-pixel filter generator's dose-inconsistency was a
  real, fixable confound — the scale-normalized v2 generator (3 of 4 filters
  passing a quantitative CV gate) closes it, proven by a before/after dose audit
  and by whitening's AUROC rising from at-or-below-chance to above-chance once
  aligned. (2) With that confound removed, the residual cross-source weakness in
  whitening/eye_enlarging/face_reshaping is a signal-to-nuisance-variance
  problem of reference-free single-image inference, not a dose, augmentation,
  data-imbalance, or calibration problem — each independently rejected by direct
  measurement. (3) Four targeted loss-side interventions (calibration, margin,
  variance penalty, auxiliary dose regression) all fail to fix it on held-out
  DF40-cdf once operating points are matched fairly.
- **Non-claim**: Does NOT claim scale-normalization was pointless — it fixed a
  real, measured confound and is a precondition for P1-R5's diagnosis being
  trustworthy at all. Does NOT claim the SNR ceiling is irreducible in general —
  only that it is not reducible by the four loss-side methods tested; a
  reference-region/self-referential normalization approach (comparing the face
  region against the same image's untouched background/hair/neck) is untested
  and is the recommended next round (see TODO.md P1-R6 candidate). Does NOT
  re-open or re-argue source-disentanglement/DID/GRL — the evidence that
  motivated it weakened in P1-R3.4, and no new evidence for it was produced
  here. Does NOT propose any of C1-C3/K0-K3 for promotion; none touches or
  affects production v8.11 (both frozen checkpoints re-hashed unchanged at the
  end of every round in this chain).
- **Status**: Complete. **NEGATIVE_BUT_INFORMATIVE at every stage from P1-R3.4
  onward** — not "failed" (the diagnosis is a solid, quantified, mechanistic
  finding with real value) and not "succeeded" (no tested intervention improves
  held-out per-type discrimination). The value of this round is the causal
  diagnosis plus catching the third instance of the threshold-vs-operating-point
  trap, not a shipped fix.

---

## P1-4: P1-R6 — reference-region noise correction (whitening/eye_enlarging/face_reshaping only)

> **Bottom line up front: the reference-region direction is now exhausted,
> alongside loss-side engineering (P1-3/P1-R5). Both directions this project has
> tried for the whitening/eye_enlarging/face_reshaping weak-type gap are closed.
> The next round needs a genuinely different lever, not another variant of
> either.**

- **Phase**: Phase 1 (fake+filter cross-source generalization track, continues
  P1-3/P1-R5)
- **Purpose**: P1-R5 found the weak-type gap is a signal-to-nuisance-variance
  problem intrinsic to reference-free single-image inference. This round tests
  the direct fix implied by that diagnosis: use the same image's own untouched
  background/hair/neck region as a per-image noise baseline, so the filter head
  scores relative to that baseline instead of an absolute score.
- **Model checkpoints**: `M0_control` (= `C1_sn_swap` reused unmodified, λ=0
  reference), `M1_bgz` (post-hoc, 1-parameter background z-score correction,
  no retraining), `M1b_bgstat` (post-hoc, 6-coefficient OLS on physical
  background statistics, no retraining), `M2_refhead` (retrained, shared trunk
  over image + reference region, auxiliary delta head init from the same Cell-C
  checkpoint C1/K1-K3 used — NOT from trained C1, a protocol correction made and
  disclosed before execution to avoid confounding). All under
  `checkpoints/research/p1_r6_reference_region_20260818/`, none promoted.
- **Train source**: same scale-normalized R3.1 composite data as P1-3/P1-R5,
  restricted at scoring time to the 3 in-scope filter types (2,292 pairs used
  for M2's margin term; 764 smoothing pairs explicitly excluded, see Stage 0
  below).
- **Validation source**: in-domain held-out split of the same data, never
  DF40-cdf.
- **Test source (final, one-shot)**: same two disjoint DF40-cdf sets as P1-3 —
  primary = P1-R3.4's dose-aligned set, secondary = `splits/v815_replication_
  set.tsv` (legacy v1-generator dose).
- **Image/source-disjoint from train/val?**: Yes, same proof pattern as P1-3.
- **Participated in model selection?**: No — thresholds frozen to disk
  (`stage2_heldout_frozen_thresholds.json`) before any held-out file was read.

### Stage 0 — mandatory human checkpoint (scope narrowing, not a silent decision)

Before any model work, Stage 0 measured whether background/hair/neck pixels
actually stay invariant under each **final v2 filter** (100+ clean/filtered
pairs per type, pre-declared A/B/C thresholds in `PRE_DECLARED_THRESHOLDS.md`):

| filter | background/face effect ratio (R_max) | verdict |
|---|---:|---|
| `whitening_W5` | 0.000 (bit-exact on 117/118 pairs) | A — BACKGROUND_STABLE |
| `eye_enlarging_v2` | 0.000 (bit-exact on 117/118 pairs) | A — BACKGROUND_STABLE |
| `face_reshaping_v2` | 0.192 (exactly 0.000 beyond d ≥ 0.50·face-width) | B — PARTIAL_BLEED, excludable |
| `smoothing_S2` | **1.020** | **C — INVARIANCE_VIOLATED** |

`smoothing_S2` applies an **unmasked, whole-frame** bilateral filter (the face
mask is only used to pick σ, not to restrict where the blur applies) — there is
no untouched reference region left in the frame for it. The project lead was
given this result and made an explicit decision (this is the mandatory
checkpoint, not an agent judgment call): **restrict Stages 1-2 to {whitening,
eye_enlarging, face_reshaping}; carry smoothing forward as a held-fixed,
monitored control arm; do not attempt to fix `smoothing_S2`'s missing mask in
this round** (flagged as a separate, out-of-scope generator-fidelity question
for a possible future round).

### Core mechanistic finding — this is the round's real result

Fitted on **train clean-fake rows only**, before any held-out set was opened:
`corr(z_full, z_bg) = -0.0127`; the post-hoc background z-score correction
(`M1_bgz`) removes **0.0%** of clean-fake logit variance; the 6-channel physical
background-statistic regression (`M1b_bgstat`) explains **R² = 0.0085** of it.

**The background region is geometrically untouched (Stage 0 proved this) but
statistically empty with respect to the filter_head's nuisance variance.**
P1-R5's "signal drowned in between-image noise" finding is therefore refined,
not merely unfixed: the nuisance is **face-region-specific**, not a global
per-image property (exposure, white balance, general image noise) that a
same-image scene reference can proxy. This is a **negative result about the
mechanism**, not just about these three specific implementations — closes the
entire "use this image's own background as a reference" family, not only the
tested variants.

`M2_refhead` (the only retrained arm) did learn to use the reference signal
(‖W_delta‖ grew 0 → 0.0818) and posted the best in-domain in-scope AUROC
(0.6295 vs `M0`'s 0.5900), but:

1. **It breached the pre-declared smoothing guard** (ΔAUROC −0.0743 vs the
   allowed −0.02) — smoothing is the held-fixed control arm and is not supposed
   to move. Carried to held-out anyway as an explicitly disclosed rule
   exception (written to disk before any held-out manifest was read), same
   discipline as K1_pairmargin in P1-R5.
2. **Known trap #1, 4th occurrence**: at its own frozen threshold, M2 shows
   joint recognition 23.48% vs v8.16's 0.38% (a 60x apparent win) — pure
   operating-point artifact (false-filter 10.61% vs 0.00%, logit SD 2.545 vs
   1.126). At matched false-filter budgets, M2 is significantly **worse at
   12/12** and better at **0/12**.
3. **Known trap #2, 1st occurrence — a new failure mode, not a repeat of
   trap #1**: M2 has the *highest* in-scope AUROC of all 3 candidates (0.6211)
   — a real, scale-invariant ranking gain, unlike trap #1's rescaling artifact —
   but the *lowest* TPR@FPR=1% (0.0084 vs `M0`'s 0.0421, v8.16's 0.0168),
   leading only at FPR ≥ 20%. See the global "Known Traps" section above.

On both held-out sets, ΔAUROC vs v8.16 for the 3 in-scope types is **not
significant** for any candidate (`M1_bgz`: essentially zero movement, ±0.004;
`M2_refhead`: positive point estimates on 5/6 type×set cells, e.g. face_reshaping
+0.0371 primary / +0.0353 secondary, but none significant).

- **Claim**: (1) Stage 0's scope narrowing was correct and is now doubly
  confirmed — the reference-region premise holds cleanly for whitening/
  eye_enlarging (bit-exact stable) and boundedly for face_reshaping, and
  correctly does not apply to smoothing. (2) The core reference-region
  *mechanism* fails for a measured, specific reason (background statistically
  uninformative about the face-region nuisance, R²≈0.01), not merely "the
  models tried didn't work" — this is a mechanistic negative result that closes
  the family of approaches, not just 3 implementations. (3) `M2_refhead`'s
  apparent AUROC gain is real (not trap #1) but concentrated entirely in a
  deployment-irrelevant FPR region (trap #2) and comes at the cost of breaching
  the smoothing control guard — not promotable under either reading.
- **Non-claim**: Does NOT claim reference-region ideas are wrong in principle
  for other tasks — only that a same-image background/hair/neck proxy carries
  no measurable information about this specific filter_head's per-image
  nuisance variance. Does NOT claim smoothing_S2's missing face mask is fixed
  or should be ignored — flagged as an open generator-fidelity question, out of
  scope here. Does NOT propose any of M0-M2 for promotion; production v8.11
  unaffected (both frozen checkpoints re-hashed unchanged at round end,
  matching P1-3/P1-R5 records). Does NOT claim the loss-side (P1-R5) and
  reference-region (P1-R6) directions were the only possible levers — only that
  both are now closed by direct evidence; other levers (input resolution,
  larger-scale fake-source diversity, a redefined acceptance scope) remain
  untested by this registry.
- **Status**: Complete. **NEGATIVE_BUT_INFORMATIVE.** Reference-region
  normalization is closed as a direction (not just this round's 3 variants),
  alongside loss-side engineering (P1-3/P1-R5) for the same weak-type gap. See
  `TODO.md` for the open "next lever" decision this leaves outstanding.

---

## P1-5: P1-R7 — fake-source diversity SCALING (300 → 600 → 900 base images/source)

> **Bottom line up front: the first candidate in this chain to pass known trap #2
> outright, and the first to beat v8.16 significantly on a held-out set — but the
> win is small at honest operating points, confined to smoothing (+ some
> whitening), and does not cleanly pass trap #1. `PARTIAL_SUCCESS`. A 10x round is
> explicitly NOT recommended.**

- **Phase**: Phase 1 (fake+filter cross-source generalization track, continues
  P1-1/P1-2/P1-3/P1-4)
- **Purpose**: P1-2 showed adding ONE fake-source family at ~300 base images/source
  produced this project's only significant held-out cross-source gain, but that
  scale was never varied. P1-R6 closed the reference-region direction and P1-R5
  closed the loss-side direction, leaving diversity scale as the one lever with a
  proven, trap-free, significant effect. This round scales it 2x and 3x — an
  exploratory 3-point marginal-trend measurement, **lever chosen by the human
  project lead, not agent-selected** (TODO.md C1.5 "下一輪 milestone" option ②).
- **Model checkpoints**: `T600_2x`, `T900_3x` (`checkpoints/research/
  p1_r7_diversity_scaling_20260818/`), research-tier, neither promoted. Reference
  arms reused unmodified: `shufflenet_v2_layer2_v816_mixedlineage.pth` (P1-2) and
  `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` (Cell C, also the
  init of every arm).
- **Train source**: `splits/research/p1_r7_diversity_scaling_20260818/
  {T600_2x,T900_3x}_train.txt` — `v815_clean_ffonly_train.txt` base + composite
  pairs over AIGuard/fake + DF40-**ff** (sd2.1/DiT/SiT/ddim/pixart), **v1** filter
  generator, all 8 conditions. Tiers are **nested** (v8.16's exact 300/source ⊂
  T600 ⊂ T900) and v8.16's original composites are reused byte-identically.
  Everything except data volume is byte-identical to `AIGuard/train_v816.py`:
  architecture, loss, `pos_weight` rule, init, optimizer, LR, cosine schedule,
  6 epochs, batch 192, seed 20260812, augmentation, source families, Layer1.
- **Validation source (threshold selection)**: `splits/v816_val.txt` — a **single
  common in-domain set no arm trained on**; the tiers inherit v8.16's exact val
  base-image assignment and every added base image went to train only (asserted in
  `build_p1_r7_splits.py`). v8.16 kept its published threshold 0.95; the same rule
  independently re-derived 0.95 for it, so the reference is not disadvantaged.
- **Test source (one shot each)**: the same two disjoint DF40-cdf sets as P1-3/P1-4
  — primary `splits/research/p1_r3_4_scale_normalized_heldout_20260818/manifest.tsv`
  (dose-aligned v2 generator, 990 rows), secondary `splits/v815_replication_set.tsv`
  (legacy v1 generator, 994 rows). Disclosed asymmetry: all four arms are
  v1-generator-trained, so the primary set is generator-mismatched for all of them
  **equally** — between-arm comparison is fair on both sets, absolute primary-set
  numbers are not comparable to the v2-trained candidates of P1-3/P1-4.
- **Image-disjoint from train/val?**: Yes — 7 gates, all pass
  (`stage1_integrity_report.json`): 0 DF40-cdf rows; 0 overlap with either held-out
  set on stem or path; 0 overlap with True Test / Shadow / AIGuard-unseen /
  Ultimate / cascade stems; 0 missing files; exact per-tier per-source counts;
  0 train/val stem overlap per tier.
- **Source-disjoint from train/val?**: Yes — DF40-cdf entirely excluded by
  construction, ff-only, same discipline as v8.16.
- **Participated in model selection?**: No — thresholds written to
  `heldout_frozen_thresholds.json` before any held-out manifest was read; the
  script asserts the ordering.

### Pipeline validation before any new number was read

Both reference arms reproduce their published registry numbers **exactly** on the
secondary set: Cell C AUROC **0.5304** / joint **2.02%** (P1-1) and v8.16 AUROC
**0.6182** / joint **4.53%** (P1-2). The scoring path is therefore independently
verified against two prior results.

### Integrity defect caught and rejected, not patched over

A first pass matched added images against v8.16's originals on **path only** and
admitted **266 stem collisions** — different DF40 generators re-render the *same*
underlying FF++ frame under the *same* stem (`pixart/ff/970/100_340.png` vs
`ddim/ff/970/100_340.png`). **38 collided with v8.16 VAL images**, which would have
put the same source frame in the tiers' training data *and* in the common in-domain
threshold-selection set. v8.16's own manifest holds 0 train/val stem overlap
(verified), so this would have regressed against the project's own standard.
Selection was made stem-strict, 281 picks replaced, and a new gate **G7 (no
train/val stem overlap per tier)** added — passes at 0 for all tiers. **This is the
same class of bug v8.16's own build caught and fixed; it recurs whenever DF40
methods are mixed, so any future DF40 multi-method build must match on stem, never
path.**

### Results

| metric | Cell C (0) | v8.16 (300) | T600 (600) | T900 (900) |
|---|---:|---:|---:|---:|
| in-domain filter AUROC | 0.8899 | 0.9190 | 0.9264 | **0.9299** |
| primary held-out AUROC | 0.5830 | 0.6720 | 0.6826 | **0.6868** |
| secondary held-out AUROC | 0.5304 | 0.6182 | **0.6404\*** | **0.6547\*** |
| joint @ matched 5% false-filter (primary) | 9.72% | 21.84% | 23.36% | **23.99%** |
| TPR@FPR1% (secondary) | 0.0504 | 0.1574 | 0.1713 | **0.1927** |
| fake-head recall (primary/secondary) | 99.9/100.0 | 99.9/100.0 | 99.9/100.0 | 99.9/100.0 |
| clean-fake logit SD (secondary) | 1.555 | 0.827 | 0.754 | **0.730** |

`*` significant paired-bootstrap ΔAUROC vs v8.16 (T600 +0.0222, T900 +0.0365).
On the primary set ΔAUROC is positive but not significant (+0.0106 / +0.0147).

- **Trap #1 (matched false-filter budgets, MANDATORY)**: **MIXED** for both tiers —
  T600 significantly better at 9/12, worse at 2/12; T900 better at 10/12, worse at
  2/12. The 2 "worse" points are the 0.5% and 1.0% budgets on the primary set,
  which at n=198 clean rows resolve to the same 0-1-image operating point. Real
  result nonetheless: at an extremely tight false-filter budget on the dose-aligned
  set, **v8.16 is still the better model**. Trap #1 also cut the headline ~5x:
  frozen-threshold joint recognition reads 0.38% → 4.92% → 10.61%, but at a matched
  5% budget the same arms read 21.8% → 23.4% → 24.0%. **Never quote the
  frozen-threshold trend.** (5th occurrence of this trap in the chain.)
- **Trap #2 (low-FPR / pAUC, MANDATORY)**: **BOTH TIERS PASS** — significantly
  better at 3/20 low-FPR points, significantly worse at **0/20**; AUROC, TPR@FPR1%,
  TPR@FPR5% and pAUC all monotone in scale on both sets. **First candidate in the
  P1-R2→R7 chain to hold its advantage in the deployment-relevant region**, the
  opposite of P1-R6's `M2_refhead`.
- **Marginal trend (3 points)**: primary AUROC +0.0106 then +0.0041; primary
  matched-5% joint +1.52pp then +0.63pp — decaying. Secondary AUROC +0.0222 then
  +0.0143; secondary matched-5% joint −0.13pp then +1.64pp — noisy. Three points
  cannot separate saturating from log-linear; what is supported is that the
  per-doubling gain is **small (~1pp matched joint, 0.005-0.015 AUROC) and not
  growing**.
- **Per type**: the whole gain is **smoothing** (primary 0.9054 → 0.9208; secondary
  0.8031 → 0.8774) plus some **whitening** (secondary 0.5119 → 0.5628).
  **eye_enlarging and face_reshaping do not move at any scale** (secondary eye
  0.5811 → 0.5827; primary eye 0.6026 → 0.6025). `pixart`/`sd2.1` remain near
  chance on the secondary set even at T900 (0.5548 / 0.5754).
- **Results dir**: `results/research/p1_r7_diversity_scaling_20260818/` —
  `P1_R7_FINAL_FINDINGS.md`, `README.md`, `MASTER_RUN_MANIFEST.json`,
  `PRE_DECLARED_PROTOCOL.md`, `final_heldout_evaluation.csv/json`,
  `matched_operating_point_analysis.csv/json`, `low_fpr_tpr_analysis.csv/json`,
  `candidate_method_comparison.csv`, `scaled_dataset_manifest.csv`,
  `checkpoints_index.csv`, `figures/`.

- **Claim**: (1) Fake-source diversity scaling beyond 300/source **continues to
  help**, monotonically across 300/600/900, on two disjoint held-out DF40-cdf sets,
  with zero fake-recall or false-filter regression, significant on the secondary
  set, and — uniquely in this chain — retained at FPR ≤ 1-5%. (2) The gain is
  **type-restricted**: smoothing and (weakly) whitening only. (3) More source
  diversity **monotonically reduces the clean-fake logit SD**, the exact
  nuisance-variance quantity P1-R5 identified as the root cause — a mechanistic
  link between this lever and that diagnosis. (4) The per-doubling marginal return
  is small and, on the dose-aligned set, decaying.
- **Non-claim**: Does NOT claim a "beats v8.16" result in this project's strict
  sense — trap #1 is MIXED, not clean, and the pre-declared STRONG_SUCCESS gate
  fails. Does NOT support the frozen-threshold 0.38→10.61% trend as a real 28x
  improvement (~5/6 of it is operating point). Does NOT establish the trend's
  functional form — 3 points, `INCONCLUSIVE` between saturating and log-linear.
  Does NOT claim the weak-type gap (eye_enlarging / face_reshaping) is affected at
  all — it is unmoved at every scale, consistent with P1-R5's diagnosis and P1-R6's
  negative result. Does NOT re-open DID/GRL, reference-region, or loss-side
  directions. Neither tier is proposed for promotion; production v8.11 unaffected
  (both frozen checkpoints re-hashed **byte-identical to P1-R6's record**).
- **Status**: Complete. **PARTIAL_SUCCESS.** **Recommendation on record: do NOT run
  a 10x round.** Reasons: the marginal gain per doubling is ~1pp matched joint
  recognition and decaying on the primary set; the gain is confined to the one
  filter type that already worked and does not touch the diagnosed blocker; and
  after exclusions the DF40-ff pools hold only 3,288 (DiT/SiT) / 3,705
  (ddim/pixart) usable images per source, so 3,000/source sits **at the pool
  ceiling for 4 of 6 sources** — a larger round would require new source families,
  which is a *composition* question, not a *scale* one. If the weak-type gap stays
  on the agenda, the live variables are diversity **composition** (new families) or
  a genuinely different lever (e.g. input resolution, priced against the
  20.91MB/14.4ms mobile budget), not more volume of the same data.

---

## P1-6: P1-R8 — Shadow vs fake+filter tradeoff; full-gate audit of the Cell-C/diversity lineage

> **Bottom line up front: the tradeoff is not a training problem. A single
> fake-head threshold swept on ONE frozen checkpoint traces a curve that every
> independently trained arm in the v8.12→P1-R7 chain sits ON or BELOW — none
> above it. `NEGATIVE_BUT_INFORMATIVE`, plus one decision-ready (NOT
> recommended-for-promotion) operating-point proposal.**

- **Phase**: Phase 1 (classifier track; audits the P1-2 and P1-5 candidates on
  gates they were never measured on)
- **Purpose**: (1) run T900_3x / v8.16 / Cell C through the COMPLETE original
  gate suite — P1-R7 only measured DF40-cdf cross-source metrics; (2) determine
  whether the Shadow-vs-fake+filter tradeoff is structural.
- **Model checkpoints**: reference arms reused unmodified —
  `shufflenet_v2_layer2_v811.pth` + `shufflenet_v2_layer1_v811d.pth`
  (production), `..._v815ablation_cell{A,C,D}_*.pth`, `..._v816_mixedlineage.pth`,
  P1-R7 `T600_2x` / `T900_3x`, Layer1 `shufflenet_v2_layer1_v812.pth`. Trained
  this round (research tier, neither promoted):
  `checkpoints/research/p1_r8_shadow_composite_tradeoff_20260819/layer2_p1_r8_{ctrl,wild}.pth`.
- **Train source** (Round 4 only): `v815_clean_train.txt` + 12,000 in-the-wild
  CLEAN REAL photos (IMDB-WIKI + `celeba_train`) carried with dual-head target
  **(0,0)** — a label combination with zero prior training support
  (`splits/research/p1_r8_.../wildreal_{train,val}.txt`). VGGFace2 never used.
- **Validation source (threshold selection)**: `splits/v815_clean_val.txt`
  (in-domain) for filter thresholds; a purpose-built disjoint `stressdev` set
  (300 AIGuard/**fake** sources × 8 stress conditions, 2,351 images) for the fake
  threshold and the Round-3 arbitration τ. **No gate set participated in any
  selection.**
- **Test source**: the full Freeze-Gate suite — True Test (paired), Shadow
  (paired, via `clean_output/clean_paths.txt`), AIGuard-unseen, CelebA,
  StyleGAN2, Alibaba OOD, and the AIGuard/unseen × 8-condition fake+filter stress
  test (pre-generated once, identical pixels for every arm).
- **Image-disjoint from train/val?**: Yes — `build_p1_r8_stressdev.py` and
  `build_p1_r8_wildreal_splits.py` assert zero stem collisions against 25,874
  gate stems and 208,196 train/val-seen stems before writing.
- **Source-disjoint from train/val?**: mining pool `AIGuard/fake` vs gate
  `AIGuard/unseen` asserted mutually exclusive. DF40-cdf not used at all.
- **Participated in model selection?**: No. Every threshold was written to disk
  before the corresponding gates were read; each round's hypothesis is recorded
  in `ROUND_LOG.md` ahead of that round's results.

### Pipeline validation before any new number was read

The single harness reproduces **every** published v8.11 gate exactly (True Test
filter 93.57%, paired balanced 81.12%, Shadow balanced 43.55%, AUROC 0.8150,
CelebA 99.73%, StyleGAN2 99.60%, Alibaba 98.17%, stress 3.7134%) and Cell C's
published numbers independently. Round 4's control retrain came out
**bit-identical** to the original Cell A checkpoint (max weight diff 0.0 over 365
tensors), isolating the single data variable.

### Results

| metric | v8.11 | Cell C | v8.16 | T600 | T900 |
|---|---:|---:|---:|---:|---:|
| True Test paired balanced | **81.12** | 80.32 | 80.32 | 80.32 | 80.32 |
| AIGuard-unseen AUROC | **0.8150** | 0.8062 | 0.8090 | 0.8089 | 0.8089 |
| Alibaba filter OOD | **98.17** | 96.04 | 95.35 | 95.97 | 96.34 |
| Shadow paired balanced | 43.55 | 55.73 | 54.84 | **56.09** | 55.91 |
| fake+filter stress err | **3.71** | 5.50 | 5.11 | 5.85 | **5.94** |

Error decomposition (Layer1 gating miss / Layer2 fake-head miss): production
84/1, Cell A 48/64, v8.16 48/69, Cell C 48/78, T600 48/86, T900 48/88,
Cell D 48/109 — Layer2 fake-head misses rise monotonically with how hard the
shared trunk is pushed toward representing filters.

Frontier test (one frozen model, fake-threshold sweep only; each arm compared to
the curve at its own stress error): Cell A **+0.00pp**, Cell D −0.36, T600 −1.08,
Cell C −1.25, T900 −1.25, v8.16 −2.15, witness-veto −2.33, R4 wild-real −5.56,
v8.11 −11.83. **No arm above the curve.**

Domain measurement explaining it — median `p_fake` on Layer1-passed images:
True Test filter 0.079 / True Test clean real 0.078 / Shadow filter 0.892 /
Shadow clean real 0.906 / genuine fake+filter composites 0.917.

Dev-selected operating point (`t_f*` = 0.14 on `stressdev`, matched to
production's dev safety), gates read once: stress **3.71 → 2.97%** (paired
bootstrap −0.74pp, 95% CI [−1.27, −0.26]) and Shadow balanced **43.55 → 52.69%**
(+9.13pp [+6.27, +12.01]), all Freeze-Gate A metrics still passing.

- **Known trap #1 (matched operating point)**: satisfied by construction — the
  fake threshold was chosen so dev-set stress error matches production's on the
  same disjoint set, then gates read once. The Round-3 arbitration sweep is
  reported at every τ and the rule-selected τ (0.95) is honoured even though it
  is a no-op; the favourable τ=0.85 point is labelled a sensitivity run and
  explicitly **not** claimed as a candidate.
- **Known trap #2 (low-FPR region)**: the frontier analysis is an
  operating-point analysis end to end — every arm is compared at matched stress
  error rather than at a shared threshold.
- **Claim**: (1) P1-R7's T900_3x and P1-2's v8.16 are **not** net-positive on the
  full gate suite — T900 is the worst arm measured on the fake+filter safety
  metric and gains no Shadow accuracy over Cell C. (2) The Shadow-vs-fake+filter
  tradeoff is a **single operating point on the fake channel**, not a
  representation-capacity or data problem: six independent training interventions
  land on or below the curve traced by one threshold on one frozen checkpoint.
  (3) The mechanism is measured: on VGGFace2-style photography the fake channel
  scores real photos, filtered real photos and true fake+filter composites almost
  identically, so it carries no usable signal there. (4) Choosing the operating
  point on disjoint dev data beats production on both contested axes
  simultaneously — the first configuration in this project's history to do so.
- **Non-claim**: Does NOT claim the Shadow domain gap is solved (52.69% is still
  far from the ≥60% stretch goal, and Shadow real recall *drops* 3.95pp). Does
  NOT claim the Round-5 configuration should ship — three Freeze-Gate A metrics
  regress beyond the round's pre-declared noise tolerance (True Test paired
  balanced −0.80pp, AUROC −0.0136, Alibaba −1.56pp) though all still pass their
  absolute gates, and the mobile ≤25 MB / latency figures were never re-measured
  for a dual-head Layer2. Does NOT claim the Round-4 wild-real intervention is
  useless — it produced this project's first ≥80% Shadow real recall (81.36%) —
  only that it cannot be had together with the stress metric. Does NOT re-open
  diversity scaling, invariance loss, reference-region or mining directions: all
  four are now shown to be moves along the same curve. Does NOT claim anything
  about cross-source filter attribution (untouched this round).
- **Status**: Complete. `NEGATIVE_BUT_INFORMATIVE` on the training axis.
  Production v8.11 unaffected; both frozen checkpoints re-hashed byte-identical
  to the P1-R6/P1-R7 record. Change proposal
  `docs/team/change_proposals/20260819_p1_r8_layer1v812_cellA_dualhead_tf014.md`
  is **pending human review, Approval Record deliberately blank** (an agent must
  not self-approve); the proposer's own recommendation is **do not promote
  as-is**. Results dir:
  `results/research/p1_r8_shadow_composite_tradeoff_20260819/`.

---

## P1-7: P1-R9 - Self-Blended Images (SBI) pilot; first arm above a threshold-only frontier

> **Bottom line up front: SBI is the first lever in the P1-R2->R9 chain to place a
> trained arm ABOVE the curve traced by a single threshold on one frozen
> checkpoint - 9/9 matched budgets, on both a Layer1-level and an end-to-end
> view, with a matched-recipe control arm sitting ON the curve exactly as all six
> P1-R8 interventions did. `SUCCESS`, with a decision-ready change proposal.**
>
> **🚀 2026-08-20 UPDATE - PROMOTED TO PRODUCTION as v8.17.** Human project lead
> (designated reviewer) reviewed §2's evidence, requested two addenda
> (Freeze-Gate C robustness + mobile TFLite re-export, both reviewer-requested
> re-runs of existing scripts, not new research design), reviewed those too, then
> approved via direct instruction. `pipeline.py`'s `LAYER1_WEIGHTS_PATH` now
> points to `shufflenet_v2_layer1_v817sbi.pth` (copy of `layer1_p1_r9_SBIAUG.pth`,
> SHA256 verified identical before and after copy: `e3057270...`). Independent
> post-promotion verification re-ran test plan §6 items 1-3 against the
> now-live `pipeline.py`: **all numbers reproduce §2 bit-for-bit** (per-image
> dumps byte-identical to the original round's dumps). Smoke test (single +
> batch) passes, schema structurally unchanged. Old `shufflenet_v2_layer1_v811d.pth`
> retained unmodified on disk for rollback. Full record:
> `docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md` §8 (Approval
> Record), `TODO.md` "C1.9". This is the first production change approved
> since v8.11's 2026-08-13 freeze.

- **Phase**: Phase 1 (classifier track; direct follow-up to P1-6/P1-R8 section 6)
- **Purpose**: P1-R8 concluded the Shadow-vs-fake+filter tradeoff is one
  operating point, not a training problem, and named the one untested remedy:
  fake training data built on in-the-wild base photography, since every fake
  source this project owns confounds "is fake" with "photographic style". SBI
  (Shiohara & Yamasaki, CVPR 2022) needs no external generator - pseudo-fakes
  come from real photos only - so it supplies exactly that.
- **Model checkpoints**: trained this round, research tier at the time of
  writing, **`layer1_p1_r9_SBIAUG.pth` promoted 2026-08-20** as
  `shufflenet_v2_layer1_v817sbi.pth` (production, see update above) -
  `CTRL`/`SBI` variants and the `_last` checkpoints remain research-only -
  `checkpoints/research/p1_r9_sbi_pilot_20260819/layer1_p1_r9_{CTRL,SBI,SBIAUG}.pth`
  (+ `_last` variants). Reference arm reused unmodified: production
  `shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth`.
  **Layer2 is byte-frozen at production for every arm**; only Layer1 is trained.
  Candidate = `layer1_p1_r9_SBIAUG.pth`
  (sha256 `e3057270481074169dc3776ab94a8bfcd0372eb0db53eda9d2a6e71966e14b90`).
- **Train source**: `splits/v811_layer1_round4_train.txt` (212,374 rows,
  unchanged) + 22,297 SBI pseudo-fakes (label 1) built from
  `imdbwiki_v810_expanded` 12,000 / `celeba_train` 6,000 / `lfw` 4,000 /
  `vggface2_train_sample` 297, + (Round 3) 22,297 degradation-matched real rows
  (label 0): the same base photo, same RNG stream, same global degradations, no
  blend. **22,160 of 22,297 (99.4%) SBI base photos are already in the base split
  as label-0 REAL rows** - the same photograph appears under both labels, which
  is the de-confounding mechanism being tested.
- **Validation source (checkpoint selection)**: `splits/v811_layer1_val.txt`,
  identical for every arm and containing no SBI rows, so the selection rule
  (best macro-F1) cannot favour the candidate.
- **Test source**: the full Freeze-Gate suite via `eval_p1_r9_full_gates.py`
  (a byte-derived copy of P1-R8's harness writing to a new round dir, reading
  P1-R8's stress cache read-only, plus a `--manip-threshold` flag) - True Test
  paired + fake, Shadow paired, AIGuard-unseen, CelebA, StyleGAN2, Alibaba OOD,
  fake+filter stress - **plus FF++ zero-shot** (900 frames,
  `eval_p1_r9_ffpp.py`, checkpoint-explicit and output-named from the loaded
  weights).
- **Image-disjoint from train/val?**: Yes. 34,815 gate stems (True Test
  real/filter/fake, Shadow real/filter, AIGuard-unseen, celeba_test, StyleGAN2,
  Alibaba, FF++) excluded from the SBI base pools before generation and
  re-asserted at split time (all integrity gates 0); 208 LFW photos were blocked
  because they are True Test stems.
- **Source-disjoint from train/val?**: `vggface2_train_sample` is
  identity-disjoint from `shadow_vggface2_real` by VGGFace2's official
  train/test identity split - verified this round, 0 of 480 train identities
  among the 500 Shadow identities. DF40-cdf and
  `splits/v815_replication_set.tsv` were **not read at all** in this round.
- **Participated in model selection?**: No. The operating point was chosen on
  dev data only (`select_p1_r9_threshold.py`, in-domain val, Alibaba-linked rows
  removed) and written to disk before any gate was re-read; the dev rule returned
  tm~0.5 for every arm, i.e. the arms were already calibration-matched.
- **Results**: `results/research/p1_r9_sbi_pilot_20260819/` -
  `P1_R9_FINAL_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `ROUND_LOG.md`,
  `round1_sanity/`, `gates_*.json`, `perimage_*.json`, `frontier_analysis.json`,
  `trap_analysis.json`, `threshold_selection.json`, `ffpp_*.json`,
  `sbi_generation_*.json(l)`, `train_log_*.csv`.

  Harness reproduces every published v8.11 gate exactly before any candidate
  number was read (True Test filter 93.574 / paired balanced 81.124 / Shadow
  balanced 43.548 / AUROC 0.81499 / CelebA 99.733 / StyleGAN2 99.600 /
  Alibaba 98.170 / stress 3.7134).

  | gate | PROD v8.11 | CTRL | SBI (R2) | **SBIAUG (R3)** |
  |---|---:|---:|---:|---:|
  | True Test fake / filter recall | 99.63 / 93.57 | 99.63 / 92.77 | 99.63 / 95.18 | 99.63 / **91.97** |
  | True Test paired balanced | 81.12 | 82.73 | 80.12 | **82.13** |
  | AIGuard-unseen AUROC | 0.8150 | 0.8195 | 0.8332 | **0.8410** |
  | CelebA / StyleGAN2 | 99.73 / 99.60 | 99.83 / 99.63 | 98.30 / 99.50 | **99.33 / 99.57** |
  | Alibaba filter OOD | 98.17 | 97.90 | 97.63 | **97.71** |
  | Shadow real / filter recall | 77.06 / 10.04 | 81.72 / 8.96 | 67.03 / 11.83 | **74.91 / 12.19** |
  | fake+filter stress err | 3.71 | 3.98 | 2.62 | **2.80** |
  | FF++ Layer1 AUROC | 0.5275 | 0.5272 | 0.5785 | **0.5611** |

  **Threshold-only frontier** (P1-R8 Round-5 methodology applied to Layer1's
  `p_manip`, since production's stress error is 98.8% a Layer1 gating failure).
  Arm minus frontier, in pp, at 9 matched budgets:

  | view | CTRL | SBI | **SBIAUG** |
  |---|---|---|---|
  | Layer1-level (matched L1 gating-miss) | -0.36 ... +0.90 | +1.43 ... +3.41 | **+3.05 ... +4.48 (9/9)** |
  | end-to-end (matched stress error) | 0.00 ... +1.43 | -0.90 ... +3.05 | **+0.18 ... +5.56 (9/9)** |

  A decomposition measured before any candidate existed: sweeping production's
  Layer1 threshold over its whole range, **end-to-end Shadow filter recall never
  exceeds 15.77%** even at tm->0 - production's 10.04% is **Layer2-bound**, so
  end-to-end Shadow paired balanced is hard-capped at ~57.9% for any Layer1.
  Production's Layer1-level Shadow baseline is 63.98% with a threshold-only
  maximum of 64.34% (0.36pp of free headroom).
- **Known trap #1 (matched operating point, MANDATORY)**: **PASSES.** The arms
  are calibration-matched in-domain (dev false-manipulated 6.369% vs 6.35%), so
  the headline table is already at a matched operating point. At matched Shadow
  real recall SBIAUG is better at **6/6** on Shadow Layer1 routing (+5.37 to
  +7.53pp), **6/6** on Shadow filter recall (+1.07 to +3.58pp) and **5/6** on
  stress error (the one loss is +0.05pp). At matched True Test real recall it is
  worse at 4/6 on True Test filter recall (-0.40 to -0.81pp) - the one
  consistent regression, honestly reported.
- **Known trap #2 (low-FPR / pAUC, MANDATORY)**: **PASSES OUTRIGHT.**
  AIGuard-unseen pAUC(FPR<=5%) 0.0852->**0.1630**, TPR@FPR1% 0.0093->**0.0370**,
  TPR@FPR5% 0.2778->**0.3241**, TPR@FPR10% 0.4630->**0.4815** - all four improve,
  dAUROC +0.0261 with a 10k paired-bootstrap CI excluding 0. The opposite of
  P1-R6's `M2_refhead` (best AUROC, worst TPR@1%).
- **Claim**: (1) SBI is the first lever in this chain to beat a threshold-only
  frontier, at every matched budget on two independent views, with a
  matched-recipe control arm on the curve - which falsifies, **for this one
  lever**, P1-R8's generalisation that every training intervention is a move
  along the same curve. (2) The mechanism is the one P1-R8 named: pseudo-fakes
  with no fixed photographic style, 99.4% of them built on photographs the model
  simultaneously sees labelled real. (3) Naive SBI has a specific, measurable
  artefact - if the whole-image degradations appear only on the pseudo-fake
  branch, the model learns "degraded => manipulated" and clean OOD real recall
  falls (CelebA -1.43pp, Shadow real -10.03pp in Round 2); adding
  degradation-matched real negatives removes it and *improves* nearly every
  manipulation-side metric at the same time. (4) FF++ zero-shot moves off chance
  (0.5275 -> 0.5611 AUROC; +2.5 to +5.7pp catch at 7/8 matched-real-recall
  points), consistent with SBI's paper claim about blending/reenactment families.
- **Non-claim**: Does NOT claim the Shadow domain gap is solved - end-to-end
  Shadow paired balanced is 43.55%, identical to production, because the frozen
  2-class Layer2 caps it; the gain appears as +2.15pp Shadow filter recall and
  +5.4-7.5pp Layer1 routing. Does NOT claim FF++ is fixed (0.5611, far below the
  >=70% stretch goal). Does NOT claim SBI helps True Test - True Test filter
  recall is the one consistent regression. Does NOT claim anything about
  **scaling**: a pre-declared 2x round (H5) was launched and abandoned after
  generator throughput collapsed ~50x for machine-level I/O reasons, so no
  scaling evidence exists in either direction - this is explicitly NOT a
  "scale plateau" finding of the P1-5/P1-R7 kind. Does NOT touch Layer2,
  cross-source filter attribution, DF40-cdf, or the dual-head lineage. Does NOT
  re-measure the mobile 20.91 MB / 14.4 ms budget (Layer1's architecture is
  byte-identical to production's, so it should carry over, but it was not
  verified). Does NOT propose self-approval.
- **Status**: Complete. **SUCCESS.** Production v8.11 unaffected; both frozen
  checkpoints re-hashed byte-identical to the P1-R6/R7/R8 record
  (`3c61cf68...`, `8470ad52...`). No git commit. Change proposal
  `docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md` is **pending
  human review, Approval Record deliberately blank**; the proposer's
  recommendation is **promote, with the True-Test-filter-recall caveat** - a
  stronger recommendation than P1-R8's, which was "do not promote as-is".
- **Incidental integrity finding (pre-existing, reported not fixed)**:
  `splits/v811_layer1_val.txt` - the val split production's own Layer1 was
  epoch-selected on - contains **1,538 `FFHQ_ali_process` rows**, and
  `FFHQ_ali_process` **is** the Alibaba filter OOD gate. Same base FFHQ
  photographs under different filter types/strengths, so the Alibaba gate is not
  fully independent of production Layer1's checkpoint selection. P1-R9 removed
  those rows from its own threshold-selection set. **Recommend rebuilding the
  Layer1 val split without FFHQ_ali before the next Layer1 training round.**

---

## P1-8: P1-R10 - SBI scaling to 2x (resolves P1-7's open H5) + input-resolution ablation for the geometric filter types

- **Phase**: Phase 1. Two independent tasks in one round: (a) Layer1 SBI data
  scaling, continuing P1-7; (b) input resolution for the dual-head Layer2
  filter path, closing the last lever P1-3/P1-R5 left open.
- **Purpose**:
  (a) P1-7 recorded "whether SBI scales past ~22K pairs is the single most
  valuable open follow-up" and could not test it - its Round 4 generator
  collapsed from ~1,150 to ~22 img/min and was abandoned as "infrastructure,
  not evidence". P1-R10 first DIAGNOSED that collapse, then engineered around
  it, then answered the science question.
  (b) P1-R5 (registry P1-3) closed loss-side engineering and P1-R6 closed
  reference-region normalisation for the weak filter types, and explicitly
  named **input resolution** as the one untested lever with headroom, "at a
  real cost to the 20.91 MB / 14.4 ms mobile budget, which must be weighed
  explicitly rather than assumed acceptable".
- **Model checkpoint**:
  (a) `checkpoints/research/p1_r10_sbi_scale_20260820/layer1_p1_r10_SBIR10.pth`
  (sha256 `0279412f24e8a3bfae73a0c6da72bdb57dae0bd591ea6604cd7005506c9fb30c`),
  init from the frozen `shufflenet_v2_layer1_v811d.pth`, recipe byte-identical
  to `AIGuard/train_p1_r9_layer1.py`; Layer2 held byte-frozen at
  `shufflenet_v2_layer2_v811.pth` for every arm.
  (b) `checkpoints/research/p1_r10_resolution_20260820/layer2_p1_r10_R{224,320,448}{,c}.pth`
  - the exact `C1_sn_swap` lambda=0 control recipe with ONLY the input Resize
  changed; identical parameter count in all arms (both pools are adaptive), so
  no arm has a capacity advantage.
- **Train source**:
  (a) `splits/research/p1_r10_sbi_scale_20260820/layer1_sbi_r10_train.txt` =
  unchanged `splits/v811_layer1_round4_train.txt` (212,374 rows) + 44,297 SBI
  pseudo-fakes (imdbwiki 12,000 / celeba_train 12,000 / lfw 8,000 /
  vggface2_train 297 / **aiguard_real 12,000, a NEW family**) + 44,297
  degradation-matched real negatives = 300,968 rows. All 8 integrity gates 0.
  **98.3%** of SBI base photos are also present as label-0 real rows.
  (b) `splits/research/p1_r3_autonomous_20260818/C1_sn_swap_{train,val}.txt`,
  unchanged and unmodified (23,820 / 3,675 rows).
- **Validation source**: (a) `splits/v811_layer1_val.txt`, with the 1,538
  `FFHQ_ali_process` rows and 13 gate-stem collisions removed for threshold
  selection (the same removal P1-7 applied; the underlying integrity defect is
  **still unfixed** and is re-flagged here). (b) `C1_sn_swap_val.txt`,
  in-domain only; used for epoch selection and for freezing each arm's
  operating threshold **before** any held-out manifest was opened.
- **Test source**: (a) the full Freeze-Gate A suite + FF++ zero-shot +
  fake+filter stress + Shadow, via `eval_p1_r10_full_gates.py` /
  `eval_p1_r10_ffpp.py`. (b) TWO one-shot DF40-cdf held-out sets:
  PRIMARY `splits/research/p1_r3_4_scale_normalized_heldout_20260818/manifest.tsv`
  (990 rows, generator-matched) and SECONDARY `splits/v815_replication_set.tsv`
  (994 rows, legacy generator). Both **eval-only, opened once**; the
  `used_in_training == False` invariant is asserted in code per row.
- **Image-disjoint from train/val?**: (a) Yes - every gate stem (True Test,
  Shadow, AIGuard-unseen, CelebA-test, StyleGAN2, Alibaba, FF++) is excluded
  from SBI base photos before generation and re-asserted after
  (`gate_stem_in_sbi_source = 0`, `gate_stem_in_augreal_source = 0`).
  (b) Yes, by construction - the DF40-cdf held-out sets were never in
  `C1_sn_swap_train.txt`.
- **Source-disjoint from train/val?**: (a) No, and deliberately not - the whole
  point of SBI is that the pseudo-fake inherits the base pool's photography, so
  base photos are intentionally shared with the real class. (b) Partially - the
  arms train on DF40-**ff** composites and are tested on DF40-**cdf**; the
  inherited `v816-mixed-lineage` ancestry caveat from registry P1-2 still
  applies to the shared init checkpoint and is unchanged by this round.
- **Participated in model selection?**: **No.** (a) The operating point was
  chosen by `select_p1_r10_threshold.py` on the Alibaba-free dev split before
  any gate was re-read. (b) `res_frozen_thresholds.json` is written before the
  first held-out row is loaded, and the script enforces that order.
- **Results**:
  `results/research/p1_r10_sbi_scale_and_resolution_20260820/P1_R10_FINAL_FINDINGS.md`
  (+ `PRE_DECLARED_PROTOCOL.md`, `ROUND_LOG.md`, `frontier_analysis.json`,
  `trap_analysis.json`, `ffpp_matched_comparison.json`,
  `res_heldout_evaluation.json`, `resolution_mobile_cost.json`,
  `bit_identity_gate.json`, `worker_scaling_bench.json`).

  **(0) The infrastructure blocker was a diagnosable fact, not an excuse.**
  Root cause = external machine-level I/O contention on this shared host,
  established by four decisive tests: flat RSS (436 -> 451 MB over 300 items);
  the same pool and code running at 1,592 img/min today vs 1,090-1,460 in the
  aborted run; **identical source-megapixel distributions in the fast (0.123),
  collapsed (0.132) and burst (0.131) regions**, reconstructed by mapping the
  aborted run's output mtimes back to their sources; and a full-speed
  1,050 img/min recovery burst mid-run that no monotonic in-process cause can
  produce. Four workarounds (process pool; single-read/single-encode I/O;
  chunked fsync checkpoint + resume; throughput watchdog with back-off) took
  the job from a projected **33 h to 219 s**, and a **bit-identity gate**
  (jpg bytes, mask bytes, both sha256 fields, index alignment; PASS on 2 pools,
  0 mismatches) proves the scaled data is byte-identical to what the serial
  generator would have produced.

  **(a) SBI scaling, all arms at their own dev-matched operating point**
  (the candidate is NOT calibration-matched at 0.5 - dev false-manipulated
  2.895% vs production's 6.369% - so tm = 0.500 / 0.475 / **0.355**):

  | gate | Gate A | PROD v8.11 | v8.17 SBIAUG (current prod) | **SBIR10 (2x)** |
  |---|---|---:|---:|---:|
  | True Test fake recall | >=95 | 99.63 | 99.63 | 99.63 |
  | True Test filter recall | >=90 | 93.57 | 91.97 | **93.98** |
  | True Test paired balanced | >=80 | 81.12 | 82.13 | 81.73 |
  | AIGuard-unseen AUROC | >=0.80 | 0.8150 | **0.8411** | 0.8031 |
  | CelebA real recall | >=95 | 99.73 | 99.20 | 96.23 |
  | StyleGAN2 fake recall | >=95 | 99.60 | 99.63 | 99.27 |
  | Alibaba filter recall | >=95 | 98.17 | 97.91 | **99.13** |
  | Shadow real / filter recall | - | 77.06 / 10.04 | 73.48 / 12.54 | 64.52 / **13.26** |
  | **fake+filter stress error** | <=5 (stretch <=2) | 3.71 | 2.36 | **0.79** |
  | FF++ Layer1 AUROC | - | 0.5275 | 0.5611 | **0.5812** |

  All Freeze-Gate A gates pass. Threshold-only frontier (Layer1 primary
  endpoint), arm - frontier in pp over 9 matched budgets: SBIAUG
  +3.05..+4.48, **SBIR10 +3.94..+8.24** - above the frontier at 9/9 and above
  the current production at 9/9. FF++ fake catch at 8 matched real-recall
  points: SBIR10 beats SBIAUG at **8/8** and PROD at **8/8** (+4.3..+10.7pp).

  **(b) Input resolution.** In-domain val mean-F1 at a matched 30-epoch budget
  falls monotonically: 224 **0.9465** / 320 0.8957 / 448 0.8466. Held-out
  per-type filter AUROC (PRIMARY / SECONDARY), paired-bootstrap dAUROC vs the
  R224 control, 10,000 resamples, `*` = 95% CI excludes 0:
  R448c smoothing **-0.236\***/+0.026, whitening **-0.092\***/-0.015,
  eye_enlarging **-0.099\***/**-0.087\***, face_reshaping
  **-0.110\***/**-0.099\***. **No type improves significantly on either set at
  either resolution.** The decisive stratified control (by the source's NATIVE
  resolution - DiT/SiT/ddim 256 px, sd2.1 512 px, pixart 1024 px): **every
  significant cell is negative and every one is on 256-native sources**, where a
  >224 input is pure interpolation; on the 512/1024-native sources, where real
  extra pixels exist, **not one geometric cell is significant in either
  direction on either set**.

  **Measured mobile cost (G1-G4 all PASS, 9/9 artifacts, no DFT op in any ONNX
  graph, max |dlogit| <= 1.7e-5)** - re-measured on the same code path that
  produced the published figure, not extrapolated:

  | input | two-stage fp32 TFLite | worst-case CPU latency | FFT constant matrices |
  |---|---:|---:|---:|
  | **224** | **20.91 MB** (reproduces the published figure exactly) | **15.7 ms/img** | 0.80 MB |
  | 320 | 22.51 MB (+7.7%) | 36.9 ms/img (2.35x) | 1.64 MB |
  | 448 | 25.51 MB (+22.0%) | **84.3 ms/img (5.37x)** | 3.21 MB |

- **Known Traps checks** (both mandatory, both run):
  - **Trap #1 (matched operating points)**: PASSED and decisive in both tasks.
    (a) The candidate's dev calibration differs from production's, so tm=0.5 is
    NOT a shared operating point; every table is at dev-matched points. At
    matched Shadow real recall, SBIR10 beats production **6/6** on Shadow
    Layer1 routing, **6/6** on Shadow end-to-end filter recall and **6/6** on
    fake+filter stress error simultaneously - the strongest trap-#1 result in
    the P1-R2->R10 chain. (b) Matched false-filter budgets (6 budgets x 2 sets)
    rescue no resolution arm.
  - **Trap #2 (low-FPR region)**: **CAUGHT A REAL REGRESSION, and it is the
    reason the promotion recommendation is negative.** SBIR10's AIGuard-unseen
    AUROC is 0.8027 (dAUROC vs v8.11 -0.0122, **not significant**) and it is
    worse than the checkpoint currently in production on **all four** low-FPR
    statistics: pAUC<=5% 0.1630 -> 0.0696, TPR@1% 0.0370 -> 0.0139,
    TPR@5% 0.3241 -> 0.2083, TPR@10% 0.4815 -> 0.4028. Overall-AUROC-only
    reporting would have shown "0.8027, still above the >=0.80 gate" and hidden
    this entirely.
- **Claim**: (1) The P1-7 Round-4 blocker was an identifiable external-contention
  fact, and a parallel/I/O-lean/checkpointed/watchdogged generator that is
  **byte-identical** to the original removes it (33 h -> 219 s). (2) **SBI does
  NOT plateau at ~22K pairs** - at 2x it is further above the threshold-only
  frontier at 9/9 budgets, better at 8/8 FF++ matched points, and it meets the
  <=2% fake+filter stretch goal (**0.79%**) for the first time in the project's
  history. This distinguishes SBI from fake-source diversity, which P1-5/P1-R7
  found plateaus. (3) The gain is **not free and the trade is monotone in
  scale**: every manipulation-side metric improves and every clean-OOD-real-side
  metric degrades as SBI volume rises (CelebA 99.73 -> 99.20 -> 96.23; Shadow
  real 77.06 -> 73.48 -> 64.52; unseen pAUC<=5% 0.0852 -> 0.1630 -> 0.0696).
  P1-7's degradation-matched real negatives mitigate this at 1x but not at 2x
  with an in-domain base family added. (4) **Input resolution is closed as a
  lever for the geometric filter types** for this architecture and transfer
  protocol - no significant improvement anywhere, significant *degradation*
  exactly where the extra pixels are interpolated, and a **measured** 5.37x
  latency cost at 448 for zero discrimination gain.
- **Non-claim**: Does **NOT** recommend promoting SBIR10 - the change proposal
  (`docs/team/change_proposals/20260820_p1_r10_sbi_scale_layer1_sbir10.md`)
  explicitly says do not promote by default, and its Approval Record is blank.
  Does **NOT** claim the Shadow domain gap is solved - end-to-end Shadow paired
  balanced is *worse* (43.01 -> 38.89), still capped ~57.9% by the frozen 2-class
  Layer2. Does **NOT** claim FF++ is fixed (0.5812, far below the >=70% stretch
  goal). Does **NOT** claim 4x scaling was tested - it was not; the observed
  direction predicts the trade would steepen. Does **NOT** claim resolution is
  closed for a model pretrained and trained natively at high resolution - the
  arms here inherit 224-trained weights under a mostly-frozen backbone and never
  reach the 224 arm's in-domain performance even at a matched 30-epoch budget;
  that confound is disclosed in `ROUND_LOG.md` as a pre-declared amendment, not
  discovered afterwards. Does **NOT** touch Layer2 training, DF40-cdf training,
  the dual-head lineage, `pipeline.py`, any existing split, or anything in
  Phase 2's territory (external artifact-type accuracy, attribution stability).
  Does **NOT** fix the `splits/v811_layer1_val.txt` / `FFHQ_ali_process`
  integrity defect first reported in P1-7 - it is re-flagged here, still open.
- **Verdict-rule honesty note**: the pre-declared rule set for task (a) was
  `SCALE_HELPS` / `SCALE_PLATEAUS` / `SCALE_HURTS`. The observed outcome fits
  **none** of them (margin clearly beats the 1x arm, no gate breached, but
  trap #2 regresses vs the 1x arm, which `SCALE_HELPS` forbade). The rule set is
  recorded as **incomplete** and the outcome reported under an explicit fourth
  label rather than bending a rule to fit.
- **Status**: Complete. **(a) SUCCESS with a measured Pareto cost** - candidate
  proposed, not promoted, production untouched. **(b) NEGATIVE_BUT_INFORMATIVE
  - RESOLUTION_CLOSED**, with the measured price tag P1-3/P1-R5 asked for.
  `pipeline.py` and all three frozen checkpoints re-hashed **byte-identical** at
  round end (`frozen_hashes_{start,end}.txt`, diff clean). No git commit.

---

## P1-9: P1-R11 - adversarial leakage audit; v8.17 on DF40-cdf; SBI scaling to 2.92x (ceiling found)

> **Bottom line up front: (1) an independent content-hash audit found SIX genuine
> leaks that every prior round's path/stem checks were structurally blind to -
> including 63.8% of the StyleGAN2 "OOD" gate and 23.5% of the Alibaba gate -
> but decontaminated recomputation shows none of them inflates any number v8.17's
> promotion relied on; (2) v8.17 on DF40-cdf is a pre-declared null for a
> structural reason; (3) SBI's ceiling is between 2x and 2.92x, and 2.92x is also
> the structural maximum this lever can ever reach.**

- **Phase**: Phase 1. Three independent tasks in one round.
- **Purpose**: (1) re-verify, adversarially rather than confirmatorily, that
  v8.17's and SBIR10's training data are disjoint from every evaluation set;
  (2) run v8.17 on the DF40-cdf axis it had never been tested on; (3) resolve
  whether P1-8's "SBI does not plateau" claim survives a third scale point.
- **Model checkpoint**: (3) `checkpoints/research/p1_r11_sbi_scale4x_20260820/layer1_p1_r11_SBIR11.pth`
  (sha256 `a0a7a1d0e850ebb240ca4d9ab17d844211fc99fddd5c133f76ab8a151bbfad82`),
  init from frozen `shufflenet_v2_layer1_v811d.pth`, recipe byte-identical to
  `AIGuard/train_p1_r9_layer1.py`. Layer2 byte-frozen at
  `shufflenet_v2_layer2_v811.pth` for every arm. Research tier, **not promoted**.
- **Train source**: (3) `splits/research/p1_r11_sbi_scale4x_20260820/layer1_sbi_r11_train.txt`
  = unchanged `splits/v811_layer1_round4_train.txt` (212,374) + 65,099 SBI
  pseudo-fakes + 65,099 degradation-matched reals = 342,572 rows.
  **65,099 = 2.919x** v8.17's 22,297; this is the pool ceiling (see below).
  All 8 integrity gates 0; bit-identity gate PASS on 2 pools.
- **Validation source**: `splits/v811_layer1_val.txt` for epoch selection; the
  Alibaba-free / gate-stem-free subset for threshold selection (`tm = 0.380`,
  written to disk before any gate was read).
- **Test source**: (1) every eval set the project owns, on 3 keys.
  (2) BOTH DF40-cdf held-out sets, **one shot**, `used_in_training == False`
  asserted per row. (3) full Freeze-Gate A suite + FF++ zero-shot + fake+filter
  stress + Shadow, via `eval_p1_r11_full_gates.py` / `eval_p1_r11_ffpp.py`
  (checkpoint-explicit, output named from the loaded weights).
- **Image-disjoint from train/val?**: **See task 1 - this is the finding.**
  Stem/path-disjoint: yes, as prior rounds asserted. **Content-disjoint: NO.**
- **Participated in model selection?**: No for all three tasks; every threshold
  written to disk before the corresponding held-out/gate file was read.
- **Results**: `results/research/p1_r11_leakage_scaling_20260820/` -
  `P1_R11_FINAL_FINDINGS.md`, `TASK1_LEAKAGE_AUDIT.md`, `TASK2_V817_DF40CDF.md`,
  `PRE_DECLARED_PROTOCOL.md` (+ AMENDMENT 1), `audit_*.json`,
  `task2_df40cdf_results.json`, `scaling_four_point_table.json`,
  `scaling_trend_analysis.json`, `frontier_analysis.json`, `trap_analysis.json`,
  `decontaminated_gate_numbers.json`, `frozen_hashes_{start,end}.txt`.

### (1) Leakage audit - `CLEAN WITH CAVEATS`, not a stop-trigger

Three keys: absolute path, filename stem (the key every prior round used), and
**content** (SHA256 of decoded pixels + dHash screen resolved by 64x64 NCC /
32x32 MAD). The content key had never been run in this project.

| leak | scale | affects |
|---|---|---|
| `AIGuard/fake` + `fake_filter_hard_neg` share the 140k-Real-and-Fake-Faces StyleGAN2 corpus with the StyleGAN2 gate | **6,376/10,000 (63.8%)**, many pixel-identical | base split -> v8.11d, v8.17, SBIR10 |
| `AIGuard/real` + `filter_data/*` contain the FFHQ base photos of the Alibaba gate | **4,980/21,151 (23.5%)** | base split + SBIR10's `aiguard_real` SBI family |
| `splits/v811_layer1_val.txt` holds **2,644** `FFHQ_ali` rows (P1-7 recorded 1,538 - **1.7x larger**); 69.6% of the Alibaba gate near-duplicated, 8 pixel-identical | epoch selection for all three Layer1s |
| `sd2.1/ff/803/503_651.png` (train) pixel-identical to `sd2.1/ff/572/503_651.png` (True Test fake), + cross-DF40-method frame reuse | 11/270 (4.1%) | base split |
| CelebA train/test partition overlap (`celeba_train/154561.jpg` = `celeba_test/195917.jpg`, byte-identical) | 41/19,962 (0.21%) | base split + SBI base pool, both arms |
| `AIGuard/fake` near-duplicates of `AIGuard/unseen` | 4/454 (0.88%) | base split |

Candidate accounting: 104,963 K1 path collisions (all resolved as
dual-head-lineage self-overlap or the documented v8.5-era `FFHQ_ali` training
use, 0 new), 122,475 K2 stem candidates, and 153,595 content-screen pairs of
which **127,167 resolved as dHash false positives** and 23,530 confirmed +
2,898 borderline. Hypothesis A1 (the 212,374-row base split was never
gate-audited, because `gate_stems()` is applied only to SBI base photos) is
**CONFIRMED and is the source of the two largest leaks**. A2 (a train-side
`FFHQ_ali` counterpart) is **REJECTED** - 0 such rows in the Layer1 train split.

**The decisive test** - every affected gate recomputed with contaminated images
removed, from the archived per-image dumps:

| gate | v8.17 reported | v8.17 decontaminated |
|---|---:|---:|
| StyleGAN2 (63.8% removed) | 99.50 | 99.07 |
| Alibaba (23.5% removed) | 97.71 | 97.73 |
| CelebA (0.2% removed) | 99.33 | 99.33 |
| **AIGuard-unseen AUROC** (0.9% removed) | **0.8410** | **0.8387** |

**The v8.17-minus-production AUROC gain is +0.0260 reported and +0.0263
decontaminated.** Every Freeze-Gate A threshold still passes; every between-arm
ranking is unchanged; on the leaked Alibaba subset every arm scores *worse* than
on the clean subset (-0.24 to -0.73pp), i.e. contamination was mildly adverse,
never advantageous.

### (2) v8.17 on DF40-cdf - `SAME_CURVE` (pre-declared)

dAUROC v8.17 - PROD: **-0.0034 CI [-0.0083,+0.0014]** (primary, dose-aligned)
and **-0.0024 CI [-0.0069,+0.0021]** (secondary). Trap #1 (6 budgets x 2 sets):
better 1/12, worse 4/12, all |delta| <= 0.63pp. Trap #2: mixed and tiny.

Two structural findings worth more than the numbers:
- `filter_auroc_layer2only` is **0.4972 / 0.4715 for BOTH arms to 4 dp** - Layer2
  is frozen, so v8.17's filter score is byte-identical to production's. The only
  channel SBI could act through is Layer1 routing, which is already 99.5-100% on
  these all-fake sets. **No headroom exists for SBI on this axis.**
- **`joint recognition` is undefined for the production architecture**: it reads
  0.00% for both arms because the hierarchical classifier's argmax can emit
  "fake" or "filter", never both. Every prior DF40-cdf joint-recognition number
  (Cell C 2.02%, v8.16 4.53%, T600/T900 ~24%) comes from a **dual-head** Layer2.
  **The two families must not be quoted as one series.**

### (3) SBI scaling to 2.92x - `CEILING_REACHED` + `DIVERGING` + `DIVERSITY_LEVER_EXHAUSTED`

The pre-declared 4x point is **unreachable**: the entire gate-excluded photo
inventory is 65,145 images and the generator samples without replacement, so
**2.92x is the structural maximum of this lever**.

All arms at their own dev-matched operating point (0.500/0.475/0.355/**0.380**):

| gate | Gate A | PROD 0x | v8.17 1x | SBIR10 2x | **SBIR11 2.92x** |
|---|---|---:|---:|---:|---:|
| True Test filter recall | >=90 | 93.57 | 91.97 | 93.98 | **95.18** |
| True Test paired balanced | >=80 | 81.12 | 82.13 | 81.73 | **78.51 FAIL** |
| AIGuard-unseen AUROC | >=0.80 | 0.8150 | **0.8411** | 0.8031 | **0.7828 FAIL** |
| CelebA real recall | >=95 | 99.73 | 99.20 | 96.23 | 95.23 |
| Alibaba filter recall | >=95 | 98.17 | 97.92 | 99.13 | **99.28** |
| fake+filter stress err | <=5 | 3.71 | 2.36 | **0.79** | 1.14 |
| FF++ Layer1 AUROC | - | 0.5275 | 0.5611 | 0.5812 | **0.5890** |
| Shadow real / filter | - | 77.06/10.04 | 73.48/12.54 | 64.52/13.26 | 62.01/**13.98** |

**SBIR11 is the first arm in the P1-R2->R11 chain to breach a Freeze-Gate A
threshold - two of them.**

- **Trap #1**: at matched Shadow real recall, SBIR11's stress error is **worse
  than SBIR10 at 6/6 budgets**, worse than v8.17 at 5/6, worse than production
  at 2/6. The safety metric has reversed, not merely flattened.
- **Trap #2**: AIGuard-unseen dAUROC vs production **-0.0321, SIGNIFICANT** (at
  2x it was -0.0118, n.s.). pAUC5 0.0852 -> 0.1630 -> 0.0696 -> 0.0607.
- **Frontier**: SBIR11 is still above the threshold-only frontier at 9/9
  Layer1-level budgets (+4.12..+4.84), but below SBIR10's margin at the tight
  budgets (0.5%: 4.84 vs 8.24) and below it end-to-end at 9/9.
- **Trend** (sign-corrected, + = better; last step normalized to 0.545 doublings):
  stress error +1.573 -> **-0.641/doubling** (sign flip), FF++ pAUC5 +0.0078 ->
  **-0.0041** (sign flip), FF++ AUROC +0.0201 -> +0.0143 (29% decay); meanwhile
  unseen AUROC degrades at a **constant** rate (ratio 0.98) and True Test paired
  balanced degrades **14.7x faster** per doubling. Cost-per-unit-gain ratios go
  **negative** on every stress-error pairing.

- **Claim**: (1) This project's disjointness guarantees were path- and
  stem-based and therefore structurally blind to renamed/re-encoded duplicates;
  a content key finds six real leaks, two of them large. **The StyleGAN2 gate
  (63.8% contaminated) and, more weakly, the Alibaba gate (23.5%) must stop
  being described as OOD/out-of-distribution results** - a documentation claim
  in `CLAUDE.md` and the Freeze-Gate A table since v8.3. (2) No leak inflates
  any promotion-relevant number: all gates pass decontaminated and the headline
  v8.17 gain is marginally *larger* after decontamination. (3) v8.17 is a null
  on DF40-cdf for a structural reason (frozen filter head, no Layer1 headroom),
  and DF40-cdf joint recognition is architecturally undefined for the production
  hierarchy. (4) **SBI's ceiling lies between 2x and 2.92x**, reached
  simultaneously from three directions - metric (manipulation side saturates and
  the safety metric reverses), feasibility (two Gate A breaches), and structural
  (2.92x exhausts the entire photo inventory).
- **Non-claim**: Does **NOT** recommend promoting SBIR11 - it fails two Gate A
  thresholds and is worse than SBIR10 at 6/6 matched safety budgets. Does
  **NOT** claim v8.17's promotion should be revisited - the audit's own
  decontaminated recomputation is the evidence against that. Does **NOT** claim
  the audit is exhaustive: dHash+NCC is a strong near-duplicate key but not a
  proof of disjointness, augreal was sampled at 30,000/66,594, and the DF40-cdf
  sets were checked on metadata only to preserve the one-shot rule. Does
  **NOT** fix any of the six leaks or the `v811_layer1_val.txt` defect - no
  existing split was modified. Does **NOT** claim SBI cannot help cross-source
  filter attribution, only that the v8.17 configuration cannot, because the
  relevant head is frozen. Does **NOT** touch Layer2 training, `pipeline.py`, or
  Phase 2 territory.
- **Retrospective correction to P1-8**: P1-8 claimed "SBI does NOT plateau at
  ~22K pairs", distinguishing it from fake-source diversity which P1-5/P1-R7
  found plateaus. With a third point that claim must be narrowed: **SBI does
  plateau, between 2x and 2.92x** - it simply had more runway than diversity
  scaling. The qualitative distinction P1-8 drew is weaker than stated.
- **Status**: Complete. **(1) `CLEAN WITH CAVEATS` - not a stop-trigger, with a
  documentation correction required. (2) `SAME_CURVE`, pre-declared null.
  (3) `CEILING_REACHED` - no further SBI scaling round is recommended, and
  unlike P1-8's open question this one is closed in both directions.**
  `pipeline.py` and all three frozen checkpoints re-hashed **byte-identical** at
  round end. No git commit.

---

## P1-10: P1-R12 — Self-Calibration Probe (architecture-level pilot); the weak-type gap is a REPRESENTATION-GEOMETRY problem, not an architecture problem

> **Bottom line up front: the standing "no architecture redesign" constraint was
> lifted for the whitening/eye_enlarging/face_reshaping gap and a genuine
> architecture-level candidate was piloted. Every intermediate step succeeded —
> the reference is valid, carries 65.9 % of the nuisance variance (vs P1-R6's
> 0.0 %), and the head learned to use it — and the discrimination payoff was ~0.
> The round's deliverable is the measured reason: the filter-effect direction and
> the between-photo nuisance direction are nearly the same axis, and the degree
> of collinearity rank-orders the per-type gap exactly.
> `NEGATIVE_BUT_INFORMATIVE`.**

- **Phase**: Phase 1 (weak-filter-type track; continues P1-4 / P1-6 / P1-5 / P1-8)
- **Purpose**: after loss-side (P1-R5), background-reference (P1-R6), fake-source
  diversity (P1-R7) and input resolution (P1-R10) all failed, pilot an
  architecture-level intervention that supplies the missing per-image reference:
  score the same photograph twice — raw, and after a KNOWN fixed-dose
  re-manipulation `T_k` — with the same trunk, and let a learned head see
  `[h(x) ; h(x) − h(T_k(x))]`. Literature-grounded in steganalysis
  **calibration** (Kodovský & Fridrich, *Calibration Revisited*, ACM MM&Sec 2009)
  and forensic **near-idempotence**; Cartesian calibration is why both views are
  kept rather than the difference alone. Design doc written before any
  implementation:
  `results/research/p1_r12_selfcal_probe_20260820/PHASE1_DESIGN_DOC.md`
  (candidate B = RECCE-style reconstruction residual documented as runner-up;
  candidate C = PatchCore-style memory bank rejected on mechanism first, because
  its reference is a different person and therefore cannot cancel the per-photo
  nuisance at all).
- **Model checkpoints**: `A0_ctrl_T_white` (the exact λ=0 control — identical
  code path, data, splits, init, seed, schedule, with the delta half held at zero
  and its gradient masked), `A2_scp_head_T_white`, `A2_scp_head_T_smooth`, all
  under `checkpoints/research/p1_r12_selfcal_probe_20260820/`. Research-tier,
  none promoted. Init `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth`
  — the same init C1/K1–K3/M2 used.
- **Train source**: `splits/research/p1_r3_autonomous_20260818/C1_sn_swap_train.txt`,
  **unmodified** (23,820 rows), plus probe views materialised from those exact
  rows (`selfcal/build_probe_views.py`; 27,495 sources, 17 landmark failures
  recorded MISSING, never silently substituted).
- **Validation source**: `C1_sn_swap_val.txt`, unmodified (540 composite pairs,
  664 clean-fake, 2,336 real+filter).
- **Test source**: **none — the one-shot DF40-cdf held-out sets were deliberately
  NOT opened.** The pre-declared rule required passing the selection rule AND
  both Known Traps in-domain; trap #2 failed and no in-scope AUROC delta was
  significant, so the eval-only-forever resource was preserved for a round that
  has a signal. No script in this round reads `splits/v815_replication_set.tsv`
  or the P1-R3.4 dose-aligned manifest.
- **Image-disjoint from train/val?**: n/a (no test set opened). Probe views are
  derived from train/val rows by construction and are used only as a second view
  of the same row, never as extra training rows.
- **Source-disjoint from train/val?**: n/a.
- **Participated in model selection?**: Stage 0 and Stage 1 selection used
  in-domain val only, under rules pre-declared in `PHASE1_DESIGN_DOC.md` §5 and
  `PRE_DECLARED_STAGE1.md` (the latter written after Stage 0 but before any
  Stage 1 number existed).
- **Results** (`results/research/p1_r12_selfcal_probe_20260820/`, full write-up in
  `P1_R12_FINAL_FINDINGS.md`):
  - **Stage 0 — post-hoc, no retraining** (`stage0_verdict.json`, `stage0_fit.json`):
    all three pre-declared gates PASS. Best probe `T_white`:
    corr(z₀, z_probe) = **+0.795** (gate 0.40) and **65.9 %** of clean-fake logit
    variance removed (gate 15 %) — against P1-R6's background reference at
    **−0.0127 / 0.0 %**. Near-idempotence significant for eye_enlarging (+0.198)
    and face_reshaping (+0.205) under `T_smooth`; matched probes are
    *super-additive* (`T_white` on whitening −0.350), not saturating.
  - **Stage 0 also killed the naive linear form**: every post-hoc calibrated arm is
    WORSE than raw (in-scope 0.5903 → 0.5298; smoothing control 0.8045 → 0.6591),
    and difference-only arms sit at chance (0.466–0.512).
  - **Stage 1 — learned two-view head vs the exact λ=0 control**
    (`stage1_indomain_comparison.csv`, `stage1_delta_vs_control.csv`): mean
    in-scope AUROC 0.5898 (ctrl) → 0.5924 (`T_white`) / 0.5938 (`T_smooth`).
    **No in-scope delta is significant on either arm.** `T_smooth` significantly
    damages the smoothing control arm (−0.0154). `‖W_delta‖/‖W_img‖` reached only
    2.3 % / 6.9 % — P1-R6's M2 reached 8.0 % on a reference carrying no
    information at all.
  - **KNOWN TRAP #1 (matched false-filter budgets, which is simultaneously the
    threshold-only frontier check)** (`stage1_matched_ff_significance.csv`,
    `stage1_frontier_verdict.json`): the false-filter@0.5 drop 11.75 % → 6.33 %
    at unchanged SD(z) is a mean shift and is **not** credited. At matched
    budgets `A2_scp_T_white` is **0/15 significantly worse** and 1/15
    significantly better (eye_enlarging @5 %, +4.44 pp) — the best
    matched-operating-point behaviour of any candidate in this chain (K1 was
    significantly worse at 9/12, M2 at 12/12) — but not a discrimination win.
  - **KNOWN TRAP #2 (low-FPR region)** (`stage1_lowfpr_trap2.csv`): TPR@FPR = 1 %
    **worse on 3 of 4 types** (whitening 0.0370 → 0.0222, eye 0.0741 → 0.0444,
    smoothing 0.1333 → 0.1259). **Trap #2 not passed** — the reason held-out was
    not opened.
  - **THE DECISIVE MEASUREMENT** (`selfcal/stage2_why.py`, `stage2_why.json`), in
    the 512-d trunk feature space, with u = filter-effect direction,
    v = probe-effect direction, n = PC1 of clean-fake features (nuisance direction):

    | type | cos(u, n) | best cos(v, u) | in-domain AUROC |
    |---|---:|---:|---:|
    | smoothing | **−0.475** | +0.998 | **0.804** |
    | face_reshaping | −0.611 | +0.999 | 0.594 |
    | eye_enlarging | −0.806 | +0.999 | 0.587 |
    | whitening | **−0.979** | +0.937 | **0.580** |

    |cos(u, n)| **rank-orders the per-type performance exactly**, and every probe
    direction is near-parallel to every filter direction (+0.65 to +0.999) —
    including the landmark-free crop/resize/JPEG probe against whitening (+0.891).
  - **Measured mobile cost** (`mobile_cost.json`): +512 params = **+2.0 KB**
    (the trunk is shared), **2.0×** Layer2 latency (14.97 → 29.94 ms desktop CPU,
    against resolution's 5.37× in P1-8), probe operator `T_white` +13.7 ms,
    `T_smooth` +615 ms (whole-frame bilateral — not deployable), `T_neutral`
    +0.6 ms and landmark-free but Stage 0's weakest probe. **Export-compatible,
    no new op types.** The cheapest architecture intervention this project has
    costed; it simply buys nothing.
- **Claim**: (1) The reference-region premise is **correct** once the reference is
  face-region-derived — a re-manipulated copy of the same photograph carries
  65.9 % of the nuisance variance versus the background's 0.0 %, vindicating
  P1-R6 §4's redirection as a premise. (2) Supplying that reference to a learned
  head still yields no significant per-type gain; it passes trap #1 and fails
  trap #2. (3) The measured reason is **representational collinearity**: the
  filter effect, the probe effect and the between-photo nuisance all lie along
  nearly the same axis, so subtracting the nuisance necessarily subtracts the
  signal in near-equal proportion. This single geometry retrodicts P1-R5's K2
  (a variance penalty shrank clean-logit variance 1.46 → 0.18 and made
  discrimination worse), P1-R5's 78–84 % paired win rate against a low population
  AUROC (a pair holds the photograph fixed, which is the only construction that
  removes the nuisance without removing signal — and it is unavailable at
  inference by definition), Stage 0's calibration collapse, and the head's
  refusal to lean on the delta. (4) Therefore the missing lever is
  **representation geometry, not architecture**.
- **Non-claim**: Does **not** claim reference-based architectures are useless in
  general — only that in this representation they cannot pay off, for a measured
  reason. Does **not** claim candidate B (RECCE-style reconstruction residual)
  was tested — it was not; the collinearity argument predicts the same failure,
  but that is a prediction, not a result. Does **not** claim anything about
  held-out DF40-cdf, True Test, Shadow, AIGuard-unseen, CelebA, StyleGAN2,
  Alibaba, FF++ or any end-to-end / deployment gate — none were run. Does **not**
  propose any checkpoint for promotion. Does **not** close
  *representation-learning* interventions (base-photo/identity treated as an
  explicit nuisance factor; the disentanglement/GRL family P1-R3.4 deferred) —
  those are a different lever and are the direction this round's evidence points at.
- **Status**: Complete. **NEGATIVE_BUT_INFORMATIVE.** Adds a fifth closed family
  (reference-by-re-manipulation) and, unlike the previous four, supplies the
  common reason all five failed. **Falsifiable handoff for the next round: any
  candidate that reduces |cos(u, n)| should improve per-type AUROC, and the
  improvement should track the reduction. `selfcal/stage2_why.py` computes this
  in minutes on a single checkpoint, so it is usable as a PRE-TRAINING SCREEN
  rather than a post-hoc autopsy.** `pipeline.py` and all frozen checkpoints
  re-hashed **byte-identical** at round end (`frozen_hashes_start.txt` ==
  `frozen_hashes_end.txt`, verified IDENTICAL). No git commit.

---

## P1-11: P1-R13 — representation-learning interventions; the weak-type gap is a READ-OUT problem, and P1-R12's predictive screen is FALSIFIED

> **Bottom line up front: representation learning is a sixth closed family, but
> for a reason nobody expected — the trunk already encodes the weak filter types
> far better than the deployed head reads out (out-of-sample Fisher direction
> beats the model's own logit by +0.10 to +0.21 AUROC on every type). P1-R12's
> falsifiable handoff ("reduce |cos(u,n)| ⇒ improve per-type AUROC") is
> falsified twice independently and must not be used again in that form. A
> read-out replacement discovered by the screen produced this chain's first
> 20/20 matched-operating-point result. `NEGATIVE_BUT_INFORMATIVE` for the
> mandate; `PARTIAL` for the new lever it opened.**

- **Phase**: Phase 1 (weak-filter-type track; continues P1-4 / P1-5 / P1-6 / P1-8 / P1-10)
- **Purpose**: execute P1-R12's explicit handoff — pilot representation-learning
  interventions (the one lever untested by the five closed families) and use
  P1-R12's own cosine-collinearity measurement as a **pre-training screen**,
  validating the screen itself as a deliverable. Design doc written before any
  implementation: `results/research/p1_r13_repgeom_20260820/PHASE1_DESIGN_DOC.md`;
  Stage B gates and the held-out policy pre-declared in `PRE_DECLARED_STAGE_B.md`
  (§1-4 before any Stage B number; B1b/B1c addendum written after B1 and before
  either ran, and labelled post-hoc-motivated everywhere it appears).
- **Model checkpoints**: `B2_ctrl` (exact λ=0 control), `B2_fisher_lam0.3`,
  `B2_fisher_lam1.0`, under `checkpoints/research/p1_r13_repgeom_20260820/`.
  Research-tier, **none promoted**. Init
  `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` — the same init
  C1/K1–K3/M2/A0–A2 used. Frozen reference for all Stage A/B1 work:
  `layer2_p1_r3_autonomous_20260818_C1_sn_swap.pth`.
- **Train source**: `splits/research/p1_r3_autonomous_20260818/C1_sn_swap_train.txt`,
  **unmodified** (23,820 rows) + the native-scale R3.1 composite pairs from
  `r3_1_dataset_manifest.csv` (764 pairs/type). All Fisher directions, covariances
  and standardizations fitted on **train rows only**.
- **Validation source**: `C1_sn_swap_val.txt`, unmodified (135 composite
  pairs/type, 664 clean-fake, 2,336 real+filter).
- **Test source**: **none — the one-shot DF40-cdf held-out sets were deliberately
  NOT opened**, and the policy was pre-declared as *binding regardless of
  outcome* (`PRE_DECLARED_STAGE_B.md` §4), because the read-out direction is
  fitted on in-domain composite statistics and a cross-source number would
  pre-confound "the lever is real" with "this fitted direction transfers".
  No script in this round reads `splits/v815_replication_set.tsv` or the
  P1-R3.4 dose-aligned manifest.
- **Image-disjoint from train/val?**: verified before Stage B — train vs val
  overlap is **0** on base photo (764 vs 135), **0** on `pair_id`, **0** on
  output `sha256`.
- **Source-disjoint from train/val?**: n/a (no test set opened).
- **Participated in model selection?**: in-domain val only, under rules
  pre-declared in `PHASE1_DESIGN_DOC.md` §3/§6 and `PRE_DECLARED_STAGE_B.md`.
- **Results** (`results/research/p1_r13_repgeom_20260820/`, full write-up in
  `P1_R13_FINAL_FINDINGS.md`):
  - **Stage A, A1 — reproduction** (`repgeom/stage_a_geometry_ceiling.py`):
    `cos(u, n)` on val = −0.475 / −0.979 / −0.806 / −0.611 (smoothing /
    whitening / eye / reshaping), identical to P1-R12's `stage2_why.json` from an
    independently written script.
  - **Stage A, A2 — THE DECISIVE MEASUREMENT** (`stage_a_a12_fisher_ceiling.csv`).
    Fisher direction `w* = (Σ+εI)⁻¹u` fitted on **train**, evaluated
    **out-of-sample on val**, versus the model's own filter logit:

    | type | model logit | Fisher `w*` (OOS) | headroom | `d′` | `cos_Σ(w_head, w*)` |
    |---|---:|---:|---:|---:|---:|
    | smoothing | 0.8045 | **0.9496** | +0.1451 | 7.36 | 0.180 |
    | whitening | 0.5714 | **0.7820** | **+0.2106** | 1.72 | 0.157 |
    | eye_enlarging | 0.5970 | **0.6975** | +0.1005 | 1.29 | 0.288 |
    | face_reshaping | 0.6024 | **0.7052** | +0.1028 | 3.01 | 0.175 |

    The pre-declared decisive fork (≥ +0.05 on ≥2 weak types ⇒ read-out problem)
    is met on all three. **The trunk already encodes the signal; the deployed head
    reads along a nearly-wrong axis.**
  - **Stage A, A3 — first falsification of P1-R12's screen**
    (`stage_a_a3_projection_sweep.csv`): removing the top-k nuisance PCs drives
    |cos| from ~0.9 to ~0.05 and buys **≤ +0.02** AUROC, with inconsistent sign
    (within-type Spearman −0.14 / −0.33 / −0.03 / +0.33).
  - **Stage A, A4** (`stage_a_a4_screen_validation.json`): |cos| rank-orders the
    4 types perfectly (ρ = −1.0) but **n = 4, two-sided p ≈ 0.083, not
    significant**; `d′` gives ρ = +0.8 while over-predicting achieved AUROC by
    **0.279** — exactly the read-out gap A2 measured.
  - **Pre-training screen outcome — all three representation-learning candidates
    screened OUT before any training**: R1 `ortho` (DSN-style subspace
    orthogonality, Bousmalis et al. NeurIPS 2016) killed by A3, since exact
    projection is its closed-form limit; R2 `supcon` (SupCon / Fisher-ratio
    maximization) killed by A2, since `d′` is already 2-7× what the head
    realises; R3 `grl` (DANN) killed by both. R4 (RECCE residual) rejected on
    mechanism before screening. **Cost: ~20 min of GPU instead of three
    training runs.**
  - **Stage B1/B1b — read-out replacement on the FROZEN trunk, zero training**
    (`stage_b1_arm_table.csv`, `stage_b1b_arm_table.csv`). The control is the
    same model's own logit on the same trunk and images — an exact λ=0 control
    differing only in the read-out direction.
    - The deployed head is **statistically indistinguishable from the unwhitened
      mean-difference direction** (Δ = +0.0025 / +0.0022 / +0.0015 / −0.0002) and
      is **at or barely above a random projection** of its own trunk on the weak
      types (whitening 0.5714 vs random-median 0.5675 over 200 draws). Σ⁻¹
      whitening is the entire lever.
    - **No single linear direction can serve smoothing and the weak types.**
      Pooled-4 Fisher is dominated by smoothing (‖u‖ 2.00 vs 0.58-0.71);
      pooled-3-weak wins whitening (+0.129 sig) and reshaping (+0.084 sig) but
      **collapses smoothing** (−0.160 sig). `stage_b1c_mahalanobis_cosine_matrix.csv`
      gives the reason: the four types' Fisher directions are
      near-mutually-orthogonal (smoothing·whitening = **0.024**,
      whitening·reshaping = 0.044). **This retrodicts the recurring
      smoothing-damage pattern in P1-R5 (K1, −0.041), P1-R6 (M2, −0.074) and
      P1-R12 (T_smooth, −0.015): they are nearly orthogonal problems forced
      through one scalar.**
    - `B1b_multidir_max4` (type-agnostic blind max over 4 standardized Fisher
      directions; +1,536 params ≈ +6 KB, no new op types): AUROC 0.8633 /
      0.7262 / 0.6288 / 0.6203 — smoothing +0.0588 (sig) and whitening +0.1548
      (sig); eye +0.0318 and reshaping +0.0179 not significant.
    - **KNOWN TRAP #1, simultaneously the threshold-only frontier check
      (`stage_b1b_matched_budgets_trap1.csv`): PASSED 20/20 cells better, 0
      worse** — whitening detection 14.07 % → 48.89 % at a 5 % false-filter
      budget, 19.26 % → 62.22 % at 10 %; smoothing 44.4 % → 71.9 % at 5 %. Because
      the control is the same model's logit, a free threshold sweep on it cannot
      change these numbers, so this table *is* the frontier check. **Compare K1
      (0/6) and M2 (0/12) — this is the first genuine matched-operating-point win
      in the chain.** Real+filter guard also improved (97.90 % vs 97.47 % @0.5 %).
    - **KNOWN TRAP #2 — MIXED, not passed** (`stage_b1b_lowfpr_trap2.csv`):
      normalized pAUC(FPR ≤ 20 %) improves on all 4 types (whitening 0.122 →
      0.241) and TPR@FPR=5 % on 3 of 4, but **TPR@FPR=1 % on whitening goes
      0.0370 → 0.0000** (5/135 → 0/135) and eye 0.0741 → 0.0370. Pre-declared
      resolution caveat: at 135 negatives the FPR=1 % threshold is set by a single
      image; a 5→0 change is at the edge of resolvable and is reported as a
      failure, not waved away. **Verdict `B1b_PARTIAL`** (rule required ≥2 of 3
      *weak* types significant; only whitening clears).
  - **Stage B2 — the one training pilot** (`repgeom/stage_b2_train_fisher.py`):
    scale-invariant Fisher-ratio auxiliary loss
    `L = −mean_pairs(z_filt − z_clean)/sqrt(var_cleanfake(z)+ε)`, deliberately
    distinct from P1-R5's K2 (which minimized the denominator alone and collapsed
    the scalar 1.46 → 0.18; a ratio cannot be gamed by rescaling). Three arms,
    byte-identical data/order/seed/schedule.
    **The loss optimized its own objective 33× (batch d′ 0.33 → 11.15) and bought
    nothing**: vs the λ=0 control, whitening −0.028 (ns), eye −0.032 (ns),
    reshaping +0.001 (ns); population d′ moved only 13-18 %. **Trap #1: worse at
    17/20 matched budgets, better at 2. Trap #2: worse pAUC on 3 of 4 types.**
    `B2` = `NEGATIVE`.
  - **The read-out gain replicates on every trunk** independently of training arm
    (`multidir_max4` vs that arm's own logit, whitening): +0.155 (M0), +0.128
    (`B2_ctrl`), +0.101 (λ=0.3), +0.103 (λ=1.0), all significant. The lever is
    the read-out, not the objective.
  - **Guard failure that blocks promotion, and its diagnosed fix**: on the
    *retrained* `B2_ctrl` trunk, `multidir_max4` still wins 20/20 matched budgets
    but **real+filter recall collapses to 3.25 %** at the 0.5 % budget (vs 99.3 %
    for the logit). The Fisher directions are fitted on composite pairs and
    clean-fake only; the `real_filter` population (15,533 train rows, **5.08×**
    the composite rows) is nowhere in the fit, so nothing constrains where it
    lands. It landed safely on the frozen trunk by accident. **The property is
    incidental, not structural.** Fix is specified: include `real_filter` in the
    positive class of the fit, or add a fifth direction, then re-run the guard.
  - **SCREEN VALIDATION — the round's most transferable result**
    (`screen_validation_final.json`). Second, independent falsification: ordinary
    continued training with **no intervention at all** (M0 → `B2_ctrl`) cut
    |cos(u,n)| 10× on smoothing (0.697 → 0.069) and 4.4× on reshaping (0.760 →
    0.172) and made **both worse** (0.8045 → 0.7449; 0.6024 → 0.5856), while
    *raising* whitening's |cos| (0.889 → 0.986) and making whitening **better**
    (0.5714 → 0.5997). **The screen was correct on 1 of 4 types.** Within-type
    across 4 checkpoints, Spearman(|cos|, AUROC) = **+0.40 / +0.32 / 0.00 /
    +1.00** — sign *opposite* to the screen's claim.
- **Claim**: (1) The weak whitening/eye_enlarging/face_reshaping gap is a
  **read-out-geometry** problem, not a representation-capacity problem: the
  frozen trunk supports +0.10 to +0.21 more AUROC per type than the deployed head
  extracts, measured out-of-sample on disjoint photos. (2) A linear head trained
  by BCE converged to the **unwhitened mean-difference (naive-Bayes) direction**,
  statistically indistinguishable from it and barely above a random projection on
  the weak types; the Σ⁻¹ whitening is the whole lever. (3) The four filter types
  have **near-mutually-orthogonal Fisher directions**, which is the geometric
  reason every prior weak-type intervention damaged smoothing, and it implies
  the fix is *more read-out directions*, not a better single one.
  (4) **P1-R12's `|cos(u,n)|` screen is falsified** — a between-type correlate
  (ρ = −1.0 at n = 4, ns) with no within-type causal purchase, refuted in closed
  form and again by an un-intervened training run. (5) The screen that *does*
  work, and that this round validates, is **out-of-sample Fisher/LDA AUROC on
  frozen features versus achieved AUROC**: one embedding pass, and it correctly
  redirected the round in ~20 minutes. (6) Representation-shaping objectives are
  a **sixth closed family**.
- **Non-claim**: Does **not** claim `B1b_multidir_max4` is promotable — it is
  `PARTIAL`, fails trap #2 on whitening at FPR=1 %, and its real+filter guard is
  incidental rather than structural (it collapses on a retrained trunk). Does
  **not** claim anything cross-source: **no held-out set was opened**, and every
  number is in-domain R3.1 composites, train-fitted / val-evaluated; whether the
  fitted directions transfer to DF40-cdf is **untested and explicitly reserved**
  for the next round's one-shot. Does **not** claim the classifier-side search
  space is closed — this round *opened* the read-out-geometry family, which is
  not closed and has the chain's first 20/20 matched-operating-point result.
  Does **not** claim R1/R2/R3 were *trained* and failed — they were screened out
  before training, on measured grounds, and that distinction matters. Does
  **not** claim anything about True Test, Shadow, AIGuard-unseen, CelebA,
  StyleGAN2, Alibaba, FF++ or any end-to-end / deployment gate — none were run.
  Does **not** propose any checkpoint for promotion.
- **Status**: Complete. **NEGATIVE_BUT_INFORMATIVE** for the representation-
  learning mandate; **PARTIAL** for the read-out lever it uncovered; **SCREEN
  FALSIFIED**. Adds a sixth closed family and opens a seventh, untested one.
  **Handoff, falsifiable: fit the multi-direction read-out with `real_filter` in
  the positive class (or as a fifth direction), re-run the real+filter guard on a
  retrained trunk, and only then spend the one-shot DF40-cdf held-out on it.**
  `pipeline.py` and all three frozen production checkpoints re-hashed
  **byte-identical** at round end (`frozen_hashes_start.txt` ==
  `frozen_hashes_end.txt`, verified IDENTICAL). No git commit.

---

## P1-12: P1-R14 — Shadow filter recall is a **Layer2 corpus-shortcut** problem; first Layer2 arm above a threshold-only frontier

> **Bottom line up front: the production 2-class Layer2 does not detect filters
> at all — it detects which photographic corpus an image came from (corpus AUROC
> 0.989–0.9995; filtered-vs-clean-real AUROC 0.476/0.550/0.581, i.e. chance).
> On VGGFace2 photography its read-out is worse than chance (0.380) on frozen
> features that support an out-of-sample linear separation of 0.994. Breaking
> the corpus↔class correlation with in-the-wild filtered photos beats a
> threshold-only frontier at 9/9 matched budgets — the first Layer2 arm ever to
> do so — and lifts Shadow filter recall +10.04 pp at production-matched dev
> safety. `PARTIAL`: one pre-declared condition (trap #2) fails, promotion not
> recommended, axis OPEN.**

- **Phase**: Phase 1 (classifier track). First round in the P1-R2→R14 chain to
  train the **production 2-class Layer2**; every prior Shadow-axis round trained
  Layer1 or an unpromoted dual-head Layer2.
- **Purpose**: P1-7 recorded in passing that end-to-end Shadow filter recall is
  capped at 15.77% by Layer2 for *any* Layer1 threshold. No round acted on it.
  This round asks whether that cap is a Layer2 training-data problem.
- **Model checkpoints**: trained this round, research tier, **none promoted** —
  `checkpoints/research/p1_r14_layer2_corpus_shortcut_20260821/layer2_p1_r14_{CTRL,C1,C2}.pth`
  (C1 sha256 `642bbbf2…`, C2 `16dcd69e…`). Reference arms reused unmodified:
  production `shufflenet_v2_layer1_v817sbi.pth` + `shufflenet_v2_layer2_v811.pth`.
  **Layer1 is byte-frozen at production for every arm; only Layer2 is trained.**
- **Train source**: `splits/research/p1_r14_.../layer2_p1_r14_{CTRL,C1,C2}_train.txt`.
  CTRL = `splits/v811_layer2_train.txt` unchanged (146,425). C1 = +5,400
  IMDB-WIKI **filtered** photos as filter class. C2 = C1's rows byte-identical
  +5,400 IMDB-WIKI **SBI pseudo-fakes** as fake class, of which 38.9% are the
  *same photograph* as a filter row (2,062 purpose-generated by
  `generate_p1_r14_paired_sbi.py`, reusing `sbi/sbi_fast.py` unmodified).
- **Validation source**: `splits/v811_layer2_val.txt`, unchanged and identical
  for all three arms, containing none of the added rows. **Note: it is
  saturated** — every arm hits macro-F1 0.998 at epoch 1 and epoch 1 is
  therefore selected for all three, which is itself evidence of the shortcut and
  also means the val split cannot select anything.
- **Test source**: full Freeze-Gate A suite via `eval_p1_r14_full_gates.py`
  (byte-derived from `eval_p1_r11_full_gates.py`, new output dir), plus two
  gates **new in this round**: `shadow_diffswap_fake` (291) and
  `shadow_stylegan3_fake` (102) — VGGFace2-corpus fakes, added because a
  filter-side intervention could plausibly break them and nothing else measured
  it.
- **Image-disjoint from train/val?**: Yes, and verified on a **content key**
  (Known trap #3): `audit_p1_r14_disjointness.py`, both pools × 9 eval sets,
  K1 = 0, K2 = 0, decoded-pixel SHA256 matches = 0, and **3,462 dHash≤4 screen
  hits all resolved as false positives** by 64×64 NCC / 32×32 MAD. This was not
  ceremonial: IMDB-WIKI and VGGFace2 are both scraped celebrity corpora.
- **Source-disjoint from train/val?**: The added corpus (IMDB-WIKI) is disjoint
  from the eval corpus (VGGFace2) at source level — the round deliberately does
  **not** train on the eval set's own photo family.
- **Participated in model selection?**: No. The frontier bar was computed from
  P1-R10/R11 archived dumps before any arm existed; the dev operating point was
  chosen on P1-R8's disjoint `stressdev` and written to
  `threshold_selection.json` before any gate was recomputed.
- **Results**: `results/research/p1_r14_layer2_corpus_shortcut_20260821/` —
  `P1_R14_FINAL_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `ROUND_LOG.md`,
  `diagnosis_layer2_corpus.json`, `headroom_probe_withincorpus.json`,
  `audit_disjointness.json`, `gates_{PROD_v817,CTRL,C1,C2}.json`,
  `perimage_*.json`, `frontier_analysis.json`, `threshold_selection.json`,
  `dev_selected_operating_point.json`, `devpoint_bootstrap.json`,
  `alibaba_threshold_*.json`, `frozen_hashes_{start,end}.txt`.

  Diagnosis (frozen production Layer2): untouched LFW photos get p_filter ≈0.921
  and are called "filter" **100%** of the time; untouched VGGFace2 photos get
  ≈0.089. Filtered-vs-clean-real AUROC **0.476** (True Test) / 0.550 (Shadow) /
  0.581 (IMDB-WIKI). LFW-clean-real vs VGGFace2-clean-real AUROC **0.989**;
  train-filter vs train-fake corpus **0.9995**. Within-corpus headroom probe
  (Shadow filtered vs `shadow_diffswap_fake`): deployed head **0.380**,
  out-of-sample LDA on the same frozen 512-d features **0.994**, in-domain
  direction transferred **0.285**.

  Gate table at the shared default (Layer1 = v8.17):

  | gate | Gate A | PROD | CTRL | C1 | C2 |
  |---|---|---:|---:|---:|---:|
  | True Test filter recall | ≥90 | 91.97 | 91.57 | 91.97 | 91.97 |
  | True Test paired balanced | ≥80 | 82.33 | 82.13 | 82.33 | 82.33 |
  | AIGuard-unseen AUROC | ≥0.80 | 0.8410 | 0.8480 | 0.8201 | **0.8494** |
  | Alibaba filter recall | ≥95 | 97.70 | 97.71 | 97.70 | 97.72 |
  | fake+filter stress err | ≤5 | 2.84 | 2.80 | **7.16 FAIL** | 3.84 |
  | **Shadow filter recall** | — | 12.19 | 11.11 | **40.86** | 22.58 |
  | DiffSwap (VGGFace2) fake recall | — | 56.01 | 55.67 | 54.64 | 56.36 |

  Threshold-only frontier (one frozen pair, Layer2 threshold swept; 2.796%
  stress-error floor imposed by Layer1 excluded), arm − frontier over 9 reachable
  budgets: **C1 +2.51…+11.11 (9/9 above)**, C2 −2.51…+2.15 (4/9), CTRL
  −2.15…+0.72 (1/9), PROD 0.00 by construction. Inverse view: to reach 40%
  Shadow filter recall C1 needs 6.42% stress error vs the frontier's 36.09%.

  Dev-selected operating point (`stressdev`-matched to production's 1.2335%):
  C1 @ t*=0.8765 — Shadow filter **13.26 → 23.30** (+10.04 pp, 10k paired
  bootstrap CI [+6.09, +14.34]), DiffSwap fake recall **55.67 → 62.54**
  (+6.87 pp, CI [+4.12, +9.97]), True Test filter recall unchanged, stress
  2.84 → 3.41 (−0.57 pp, CI [−0.92, −0.26]), Alibaba 97.72 → 95.71 (gate still
  passes), **all Freeze-Gate A thresholds pass**. CTRL at its own dev point is an
  exact null on all four bootstrapped metrics (0.00 pp, CI [0, 0]).
- **Known trap #1 (matched operating point)**: **PASSES.** Nothing is claimed at
  a shared threshold — the frontier is matched on stress error (and inversely on
  Shadow recall), and the operating point is matched on disjoint dev-set safety
  before gates are re-read.
- **Known trap #2 (low-FPR / pAUC)**: **CAUGHT A REGRESSION, and it is the
  reason the recommendation is negative.** AIGuard-unseen pAUC(≤5%)
  0.1626 → **0.1420** for C1, TPR@5% 0.3241 → 0.2685, TPR@10% 0.4815 → 0.4028
  (only TPR@1% improves, 0.0370 → 0.0741). C2 improves **all four**
  (pAUC 0.2074, TPR@1% 0.1157, @5% 0.4583, @10% 0.5787) and posts the best AUROC
  of any arm.
- **Known trap #3 (content key)**: **PASSES**, run in full (see above).
- **Known trap #4 (between-group correlate)**: **not applicable by
  construction** — no claim rests on a correlation across a few groups; the
  driver is a direct head-vs-features measurement and the verdict rests on a
  three-checkpoint perturbation with an exact-null control.
- **Claim**: (1) The production Layer2's fake-vs-filter score is a
  **photographic-corpus classifier**, not a filter detector — it is at chance on
  filtered-vs-clean-real within every corpus tested and near-perfect between
  corpora, and it calls 100% of *unfiltered* LFW photographs "filter". (2)
  Shadow filter recall is therefore **Layer2-bound and Layer2-fixable**: the
  frozen features support 0.994 out-of-sample linear separation of the exact
  within-corpus decision on which the deployed head scores 0.380. (3) Adding
  in-the-wild filtered photography to Layer2's filter class beats a
  threshold-only frontier at **9/9** matched budgets — the first Layer2
  intervention in this project to clear such a frontier, with a matched-recipe
  control **on** the curve — and at production-matched dev safety improves
  Shadow filter recall and VGGFace2-corpus fake recall **simultaneously** with
  True Test filter recall unchanged. (4) The pre-declared prediction that a
  **two-sided** de-confounder would dominate the one-sided one is **refuted in
  direction**: C2 is frontier-neutral but is the *safe* arm (best AUROC, best
  low-FPR profile, zero stress cost); C1 is the strong arm and pays in low-FPR.
- **Non-claim**: Does **NOT** claim the Shadow gap is solved (23.30% vs True
  Test's 91.97%; Shadow paired balanced 49.10%, still below the ≥60% stretch
  goal). Does **NOT** recommend promoting C1 — trap #2 regresses and the
  pre-declared `SUCCESS` rule forbade that; **no change proposal is filed.**
  Does **NOT** claim SBI is a valid Layer2 *fake* label — the round cannot
  separate "C2's counter-rows worked as intended" from "the label was wrong".
  Does **NOT** claim the 0.994 LDA figure is achievable headroom: the two Shadow
  sides differ in processing pipeline (our filter generator vs DiffSwap) even
  with base photography held constant, so it is an upper bound. Does **NOT**
  re-open Layer1, SBI scaling, diversity scaling, invariance loss,
  reference-region or input resolution. Does **NOT** touch DF40-cdf,
  `pipeline.py`, any existing split, or Phase 2 territory. Does **NOT** re-measure
  the mobile budget for these arms.
- **Incidental finding (reported, not fixed)**: `splits/v811_layer2_val.txt` is
  **saturated** — macro-F1 0.998 at epoch 1 for all three arms, so best-epoch
  selection is degenerate and the val split cannot detect a Layer2 intervention
  at all. This is the Layer2 counterpart of the still-open
  `splits/v811_layer1_val.txt` / `FFHQ_ali_process` defect first flagged in P1-7.
  A **corpus-stratified** Layer2 val split is recommended before the next
  Layer2 round.
- **Status**: Complete. **`PARTIAL` — axis OPEN, not closed.** Production
  v8.17/v8.11 unaffected; `pipeline.py` and all three frozen checkpoints
  re-hashed **byte-identical** at round end. No git commit. No self-approval.

---

## Template for new entries

```markdown
## <ID>: <short title>

- **Phase**:
- **Purpose**:
- **Model checkpoint**:
- **Train source**:
- **Validation source**:
- **Test source**:
- **Image-disjoint from train/val?**:
- **Source-disjoint from train/val?**:
- **Participated in model selection?**:
- **Results**: (script + result file paths, numbers)
- **Claim**:
- **Non-claim**:
- **Status**: (reported pending reproducibility verification / reproduced / final)
```
