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

**Known trap #5 — a regression check on the training-source pool is not a
regression check on the production-serving population.** P2-R3's whitening
fine-tune candidate (`artifact_classifier_v4`) measured smoothing/face_reshaping
regression at n=60 then n=400, found it not significant (~95-97%), and this
number was cited as evidence in the change proposal approved and applied to
production the same day. Both n=60 and n=400 samples were drawn from
`filter_data/{class}` — the same pool the fine-tune's own training data came
from — not from True Test or Alibaba, the populations `classify_artifact()`
actually serves once Layer1/2 routes an image to `filter` in production. A
same-day urgent audit (`results/research/p2_urgent_v4_diagnosis_20260821/`)
measuring the SAME two classes end-to-end on True Test found smoothing
100.0%→52.4% (−47.6pp) and face_reshaping 95.2%→22.6% (−72.6pp) — a real,
severe, previously-undetected regression, root-caused to the fine-tune's
whitening data being oversampled 64% relative to the other 3 classes, causing
systematic misclassification of smoothing/face_reshaping images as
`whitening`. **This is a distinct failure mode from trap #4's small-n problem
(P2-R3's n=400 was, on its own terms, adequately powered) — the sample size
was fine, the sample's *source population* was wrong.** Enlarging a sample
drawn from the wrong population only tightens a confidence interval around
the wrong answer; it does not fix it. **Mandatory for any future regression/
non-inferiority check on a classifier that sits downstream of a routing gate
(Layer1/2 → artifact type, or any similar cascade): the check must be run on
data drawn from the population the downstream classifier actually receives
in production (i.e. through the actual routing gate, or from an independent
held-out eval set of the same kind used for the primary approval evidence),
never from the fine-tune's own training-data source pool, even if that pool
is disjoint at the image level from the specific fine-tune split used.**
Production was live with the regression for several hours before this was
caught and reverted same-day.

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

| Category | Metric | Gate | v8.11 status | Statistical power (2026-08-21 annotation) |
|---|---|---:|---:|---|
| Core 3-class | True Test fake recall | ≥95% | ~99% | **Decision-grade** (v8.17 n=270, CI [97.93, 99.93]) |
| Core 3-class | True Test filter recall | ≥90% | 93.6% | ⚠️ **Cannot be statistically confirmed** — n=249; v8.17 91.97%, CI [87.92, 94.74] **straddles the 90% gate**; needs n≈890. Even the expanded n=998 set gives cluster-bootstrap [89.80, 94.20], still straddling |
| Paired filter | True Test paired balanced accuracy | ≥80% | 81.1% | ⚠️ **Cannot be statistically confirmed** — n=249; v8.17 82.13%, CI [79.12, 84.94] **straddles the 80% gate**; needs n≈1,340 |
| Fake OOD | AIGuard-unseen AUROC | ≥0.80 | 0.815 | ⚠️ **Marginal pass** — v8.17 0.8410, lower bound 0.8034, only 0.003 above the gate; no safety margin |
| Real OOD | CelebA real recall | ≥95% | 99.7% | **Decision-grade** (v8.17 n=3,000, CI [98.97, 99.57]) |
| GAN fake detection (**not OOD**, see note) | StyleGAN2 fake recall | ≥95% | 99.6% | **Decision-grade** (CI [99.26, 99.75]); but the CI covers sampling error only, **not the 63.8% content-overlap bias** |
| Cross-algorithm filter recall (**not OOD**, see note) | Alibaba filter recall | ≥95% | 98.1% | Verdict will not flip, but **n=21,151 is misleading** (4 types × 3 strengths over shared base images — observations are not independent) → **do not quote its CI width as precision**; also does not cover the 23.5% content-overlap bias |
| Safety | clean-fake false-filter | ≤5% | (reported separately per dual-head version) | not audited in the power round |
| Mobile artifact | fp32 TFLite combined size | ≤25 MB | 20.91 MB | Deterministic measurement, no sampling error |
| Deployment | iPhone real-device test | must complete | **not yet done** | n/a |

> 📌 **2026-08-21 correction note 1 (gate naming).** The two category labels
> previously written as "GAN OOD" and "Filter OOD" are **wrong**. The P1-R11
> content-level audit proved `stylegan2_test/fake/` overlaps training data by
> **63.8% (6,376/10,000)** and `FFHQ_ali_process` by **23.5% (4,980/21,151)**,
> including byte-identical images — neither is an out-of-distribution set.
> **No number and no pass/fail verdict changes** (decontaminated StyleGAN2 is
> ≈99.07%, still passing); only the claimable framing changes: say "StyleGAN2
> fake detection" and "Alibaba filter recall（跨濾鏡演算法，非 OOD——與訓練資料有
> 23.5% 內容重疊）". Evidence:
> `results/research/p1_r11_leakage_scaling_20260820/TASK1_LEAKAGE_AUDIT.md`.
> **Genuinely clean cross-domain evidence that remains**: CelebA real recall and
> AIGuard/unseen AUROC were each separately verified clean, and the True Test vs
> Shadow contrast (identical self-built filter code, different base-image
> photographic style) is a valid within-project cross-domain comparison.
>
> 📌 **2026-08-21 correction note 2 (statistical power).** The rightmost column
> is taken from `results/research/p1_bench_power_20260820/BENCHMARK_POWER_REPORT.md`
> §3. **It does not change any recorded pass/fail verdict** — it marks which
> gates are decision-grade and which were never statistically established.
> Report §3.1 states plainly that for True Test filter recall and paired
> balanced accuracy, the "✅ pass" declared at the v8.11 freeze "was never
> statistically established, and the same is true of v8.17."
>
> 🚧 **Why more data cannot fix this.** Of 13,328 LFW images, all 8,918 that pass
> the project's standard cleaning are already used in some split (intersection
> with unused = 0); the 1,835 "unused" images survive Step1 at 30.1% and Step2 at
> **0**. **The number of new clean LFW base images available is 0 — a hard
> ceiling, not insufficient sampling effort.** Raising filters-per-base-image
> from 1 to 4 (n=249→998) resolves *paired between-model differences* but cannot
> establish *a single model against an absolute threshold*, which needs more
> mutually independent base images. ⇒ **Recommendation: record these two gates
> in the paper's Limitations; do not launch another training round over them.**

v8.11 passes essentially all core static-image metrics; the iPhone test is
the one open item, so pending that it can be called a "frozen research
baseline / pre-deployment production baseline." (⚠️ 2026-08-21: two of those
"passes" — True Test filter recall and paired balanced accuracy — are
statistically unconfirmed; see the rightmost column.)

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
  > ⚠️ **2026-08-26 annotation (remeasure sweep)**: the "1,538 rows" figure above is
  > superseded — P1-R11 (`TASK1_LEAKAGE_AUDIT.md` L2) measured **2,644** `FFHQ_ali_process`
  > rows in `splits/v811_layer1_val.txt` (1.7x larger than recorded here), with 69.6% of the
  > Alibaba gate near-duplicated by val. The clean val is `splits/v811_layer1_val_clean_20260821.txt`;
  > v8.11d's own epoch selection was never re-run on it (epoch 2-4 weights no longer exist).

---

## P1-8: P1-R10 - SBI scaling to 2x (resolves P1-7's open H5) + input-resolution ablation for the geometric filter types

> ⚠️ **2026-08-26 annotation (remeasure sweep)**: this entry's headline claim "SBI does NOT
> plateau at ~22K pairs" was **narrowed by P1-9 (P1-R11)** to "SBI plateaus between 2x and
> 2.92x" (see P1-9 "Retrospective correction to P1-8"). Quote the narrowed form only.

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

---

## P1-BENCH-POWER — True Test 統計檢定力升級 / Freeze-Gate 檢定力稽核（2026-08-20）

- **Round dir**: `results/research/p1_bench_power_20260820/`（報告：`BENCHMARK_POWER_REPORT.md`）
- **Checkpoints evaluated**: v8.17（`shufflenet_v2_layer1_v817sbi.pth` SHA256 `e3057270…` +
  `shufflenet_v2_layer2_v811.pth` SHA256 `8470ad52…`）與 v8.11d（`shufflenet_v2_layer1_v811d.pth`
  SHA256 `3c61cf68…` + 同一顆 Layer2）。**無訓練**，純評測與資料建置。
- **Train/val/test 來源**: 未新增訓練資料。新測試集 True Test v2 =
  `splits/truetest_v2_real.txt`(250) / `truetest_v2_filter.txt`(998) / `truetest_v2_fake.txt`(921)。
  filter 為凍結 True Test 的 250 張 LFW base × 4 種濾鏡（全交叉配對設計，濾鏡函式與參數
  直接 import `filters/generate_filter_dataset.py`，即凍結集當初所用模組）。
  fake = 凍結 270 + 新取樣 651 張 DF40 EFS diffusion。
- **是否 image-disjoint？**: 對 v8.17 production lineage 訓練清單（252,702 條路徑）做
  Known Trap #3 規定的內容鍵稽核：K1 = 解碼像素 SHA256、K2 = dHash 篩選 + 64×64 NCC /
  32×32 MAD 裁決。base 250 張對 REAL 訓練池 K1=0、確認近重複 0；base 對 LFW 衍生 FILTER
  訓練池（濾鏡雙胞胎篩查）K1=0、確認 0；新 fake 對 FAKE 訓練池 **K1=1**，已剔除
  （`sd2.1/ff/733/253_112.png` 與訓練中的 `sd2.1/ff/569/253_112.png` 解碼像素完全相同，
  DF40 同一影格存在兩個來源目錄）。**dHash≤4 篩選在此輪偽陽性率 99.6%**，再次驗證 sub-trap。
  **identity 層級：仍有 39.1%（84/215）重疊，與凍結 v1 相同，v2 不是 identity-disjoint 基準。**
- **Source-disjoint from train/val?**: filter base 沿用凍結 eval 集的底圖（非訓練資料）；
  新 fake 來自 DF40 未被任何 split 引用的部分。
- **Participated in model selection?**: 否。兩顆 checkpoint 都已凍結，v8.17 已於本輪前核准上線。
- **可宣稱結論**:
  1. **LFW 池已耗盡**：13,328 張中通過專案標準清洗的 8,918 張**全部**已被某個 split 使用，
     交集為 0；未使用的 1,835 張實測 Step1 僅存 30.1%、Step2 後為 **0**。
     **可新增的乾淨 LFW base 影像數 = 0**（硬天花板）。
  2. **v8.11d → v8.17 的 True Test filter recall 差異在 n=998 下統計顯著**：
     −1.20pp，exact McNemar p=0.0118（b=4/c=16），cluster permutation p=0.0166，
     cluster bootstrap 差異 95% CI [−2.10, −0.30] 不含 0。
     同一比較在凍結 n=249 上為 b=0/c=4、**p=0.1250、不顯著**。
  3. 同一批資料中 v8.17 的 **real recall 顯著較佳**（+3.60pp，p=0.0225），
     **paired balanced accuracy 差異 +1.20pp、CI [−0.25, +2.80] 不顯著**。
  4. **Freeze-Gate A 有兩項無法統計確認通過**：True Test filter recall（≥90%，
     n=249，91.97%，CI [87.92, 94.74]，需 n≈890）與 True Test paired balanced accuracy
     （≥80%，n=249，82.13%，CI [79.12, 84.94]，需 n≈1,340）。
     AIGuard-unseen AUROC 通過但下界僅 0.8034（邊際）。
  5. 換到 True Test v2 的 998 張後，v8.17 filter recall 92.08%，
     **cluster bootstrap CI [89.80, 94.20] 仍跨 90% 門檻**——增加每張底圖的濾鏡型別
     可解析「兩模型配對差異」，但無法確立「單一模型對絕對門檻」，後者需要更多**獨立底圖**。
- **不可宣稱事項**:
  - 不可宣稱 True Test v2 是 identity-disjoint 或跨語料庫基準（仍是 LFW，仍 39.1% identity 重疊）。
  - 不可宣稱 v2 提升了 real recall 的檢定力（n 仍為 250，未新增底圖）。
  - 不可用 naive Wilson 區間報 v2 的整體 filter recall（998 張叢集於 250 底圖），必須用 cluster bootstrap。
  - 不可宣稱 v8.17 相對 v8.11d 為淨退步或淨改善；證據支持的是「同一條 real↔filter
    trade-off 曲線上換操作點」。
  - 本輪 disjointness 參照池限於 **v8.17 production lineage**；若未來模型用到 v8.12–v8.16
    支線資料，**必須重跑本稽核**才能使用 True Test v2。
  - 不可引用 Alibaba（21,151）與 fake+filter stress（2,289）的區間寬度宣稱精度——
    兩者影像皆為多條件作用於共用底圖，並不獨立。
- **Status**: reported pending reproducibility verification（數字皆由本輪腳本產出，
  凍結 v1 子集在同一 harness 上逐一重現已公布數字：filter 229/249=91.97%、233/249=93.57%、
  fake 269/270=99.63%、v8.11d real 68.40%）

---

## P1-13: P1-R16 — C1↔C2 counter-row DOSE SWEEP; the Shadow/low-FPR trade-off is **not** structural, but the winning dose does **not** survive a reseed

- **Round dir**: `results/research/p1_r16_layer2_ratio_sweep_20260820/`
  (`P1_R16_FINAL_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `ROUND_LOG.md`,
  `RESUME_LOG.md`, `verdict_p1_r16.json`, `analysis_p1_r16.json`,
  `reproduction_check.json`, `seed_replicate_R75s2_posthoc.json`,
  `sd21_dedup_audit.json`, per-image dumps for 7 arms × 2 batteries)
- **Checkpoints**: `checkpoints/research/p1_r16_layer2_ratio_sweep_20260820/`
  `layer2_p1_r16_{R25,R50,R75,R75s2}.pth` — **research only, none promoted**
- **Splits**: `splits/research/p1_r16_layer2_ratio_sweep_20260820/`
  `p1_r16_layer2_{R25,R50,R75,R75s2}_train.txt`
- **Purpose**: P1-12 (P1-R14) left exactly one open question — is C1's Shadow
  gain (frontier 9/9) inseparable from C1's Known-Trap-#2 low-FPR regression, or
  is there a mixing ratio that keeps one and drops the other? Swept the **single**
  quantity separating C1 from C2: the number `k` of IMDB-WIKI SBI counter-rows on
  Layer2's fake side, `r = k/5400` in {0 (=C1), 0.25, 0.50, 0.75, 1 (=C2)}.
- **Checkpoint(s) evaluated**: production Layer1 `shufflenet_v2_layer1_v817sbi.pth`
  held byte-frozen for every arm; **only Layer2 varies**. Init for every trained
  arm = `shufflenet_v2_layer2_v811.pth`; recipe/seed/val-split identical to
  P1-R14's; splits built by **subsetting P1-R14's split files**, so the base
  146,425 rows and the 5,400 added filter rows are byte-identical to C1's/C2's.
- **Train/val/test provenance**: train = P1-R14's C1 rows + a stratified nested
  subset of its counter-rows (same-base-photograph fraction held at 38.87 %:
  measured 38.89 / 38.89 / 38.86 %); val = `splits/v811_layer2_val.txt` unchanged
  and identical for every arm, containing no added row; test = the full
  Freeze-Gate A battery plus a **new secondary confirmation set, Shadow-v2**.
- **Image-disjoint from train/val?**: Yes. (a) split build re-asserts 0 gate-path
  and 0 gate-stem collisions over an extended gate universe; (b) Shadow-v2 audited
  by **decoded-pixel SHA256 against all 138,283 unique paths** in the largest
  Layer2 split — K1 = 0, K2 = 0, **exact-pixel = 0**; 4,172 dHash <= 4 screen hits
  resolved by 64x64 NCC / 32x32 MAD -> 0 confirmed, 1 borderline (dropped anyway),
  **4,171 false positives = 99.98 % FP rate**, independently reconfirming the
  Known-Trap-#3 sub-trap.
- ⚠️ **2026-08-26 annotation (remeasure sweep)**: every S2A-based statement in this entry
  (conclusions 5/6/7, "+21.72 pp", "identity-disjoint") is **superseded**. P2-R1 / P1-R17 /
  paper_readiness_execution_20260822 found `shadow_v2a_filter`'s base photos are **100%
  present in the Layer1 training pool (71.4% of the filtered images near-duplicated)**;
  S2A has been retired (`README_DEPRECATED`) and P1-R17 re-validated on S2B (0.0%
  train-seen). "Identity-disjoint from the primary Shadow set" was true but irrelevant —
  the leak is against *training*, not against the primary Shadow set.
- **Source-disjoint from train/val?**: Shadow-v2 S2A is **identity-disjoint**
  (0/297 VGGFace2 identities shared with the primary Shadow set); S2B is
  photo-disjoint but **287/287 identity-overlapping** — a measured finding,
  reported as a separate weaker stratum and never pooled into S2A.
- **Participated in model selection?**: No. Epoch selection used only the
  unchanged in-domain val split (saturated at macro-F1 0.998 for every arm);
  operating points were selected only on `stressdev` (2,351 images, disjoint from
  every gate) and written to disk before any gate was recomputed.
- **Reproduction gate (ran before anything new was trained)**: PASS. PROD/C1/C2
  re-run in this round's harness reproduce P1-R14 within +-0.50 pp; largest
  deviation 0.4016 pp (True Test real recall, 1 image of 249, identical across
  arms because it is a Layer1-only decision).

### 可宣稱結論

1. **The C1/C2 trade-off is NOT structural.** Every interior dose clears the
   threshold-only frontier **9/9** — as strongly as C1, and *more* strongly at
   the tightest stress budgets (+6.09 / +8.24 pp at <=2.85 % vs C1's +2.87 pp) —
   while simultaneously improving the low-FPR region far beyond production.
   C2's frontier-neutrality in P1-R14 is an **r = 1 endpoint effect**, not a
   monotone price paid per counter-row.
2. **Known Trap #2 is repaired from r = 0.25 upward.** AIGuard-unseen
   pAUC(FPR<=5 %) 0.1630 (PROD) / **0.1420 (C1)** -> 0.2081 / 0.2649 / 0.2646 at
   r = 0.25/0.50/0.75; TPR@FPR=1 % 0.0370 / 0.0741 -> 0.2130 / 0.2731 / 0.2778
   (**7.5x** production). Both statistics **peak in the interior** (r ~ 0.5–0.75),
   not at r = 1.
3. **`R75` (r = 0.75) is the first arm in the P1-R2 -> R16 chain to satisfy all
   four pre-declared conditions** (S1 frontier 9/9; S2 all four low-FPR
   statistics >= production; S3 dev-point Shadow filter recall 20.43 % with
   bootstrap CI [+3.23, +11.11] excluding 0; S4 no Freeze-Gate A breach).
   Pre-declared round verdict = `SUCCESS`.
4. **But that `SUCCESS` does not survive a reseed, and the round says so.**
   `R75s2` (identical split, byte-verified; only the RNG seed differs) reproduces
   S1 (9/9), S2 (all four) and S4 exactly and **fails S3 by 3 images of 279**
   (19.35 % vs the pre-declared 20.00 % bar; R75 was 20.43 %). What **does**
   replicate is the improvement itself: +7.17 pp CI [+3.23, +11.11] and
   +6.09 pp CI [+2.51, +9.68], both significant.
5. **Shadow-v2 (new, identity-disjoint, n ~ 290/type = 4x the primary set)
   confirms the primary set on every material point**: same ordering
   (PROD << C2 < R75 < R50 < C1 ~ R25), both strata agree, every arm's gain over
   production significant under a **paired cluster bootstrap on the base
   photograph** (R75 +21.72 pp CI [+18.83, +24.65]).
6. **The primary Shadow set's per-type ranking does not reproduce at 4x n.**
   Production's "best" type flips from `face_reshaping` (19.7 % at n~71) to
   `whitening` (24.6 % at n~285), and `face_reshaping` falls to 13.6 %. All four
   primary-set Wilson intervals overlap, so that ranking was never supported.
7. **The properly-powered per-type story** (S2A, intervals separate): the
   intervention moves **photometric** types 3–4x (smoothing 14.1 -> 60.8,
   whitening 24.6 -> 44.9 at r = 0.75) and **geometric** types < 2x
   (eye_enlarging 13.2 -> 25.3, face_reshaping 13.6 -> 22.0), consistently across
   all six arms and both strata.
8. **The DF40 `sd2.1` duplicate-path defect reported by P1-BENCH-POWER is present
   in this line**: 3,000 `sd2.1` paths decode to **2,966 distinct images —
   34 duplicate groups**, all of the reported form (same filename under two
   `sd2.1/ff/<dir>/` directories, e.g. `ff/027/209_249.png` = `ff/105/209_249.png`).
   Impact 1.13 % of `sd2.1` rows, 0.022 % of each split, and **identical in every
   arm** (all rows come from the byte-identical v811 base split), so it cannot
   confound any between-arm comparison here. Logged for whoever next rebuilds
   the production Layer2 split.
9. **True Test is completely unmoved by every arm** — per-type recall is
   byte-identical across all seven arms (eye 77.4, reshape 95.2, smoothing 100.0,
   whitening 95.2). The intervention is free in-domain.

### 不可宣稱事項

- 不可宣稱 Shadow domain gap 已解決：~19–20% 仍遠低於 True Test 的 91.97%，
  Shadow paired balanced ~47% 仍低於 >=60% 的 stretch goal。
- **不可引用「R75 達成 SUCCESS」而不同時引用種子複現失敗**（結論 4）。
  單一種子的 20.43% 與另一種子的 19.35% 只差 3 張影像。
- 不可宣稱 r = 0.75 是最佳劑量：r = 0.25/0.50/0.75 的 dev-point Shadow recall
  （54/53/57 of 279）差異落在種子雜訊之內，本輪已直接量測證明。
- **不可用主 Shadow 集（n~70/型別）排序濾鏡型別**（結論 6）。
- 不可用 naive Wilson 區間報 Shadow-v2 的**整體** recall（每張底圖 4 個型別，
  相關），必須用 cluster bootstrap；per-type 可用 Wilson（型別內每底圖 1 張）。
- 不可宣稱 SBI pseudo-fake 是 Layer2「fake」的正確標籤——本輪只顯示它在
  r <= 0.75 有用、在 r = 1 傷害 frontier，無法區分機制。
- 不可宣稱行動端體積/延遲不變：架構與 production Layer2 同構但**未實測**。
- 本輪**未做** Freeze-Gate C 穩健性（20 種擾動）與 TFLite 匯出驗證。
- 未讀取 `splits/v815_replication_set.tsv` 與 P1-R3.4 dose-aligned DF40-cdf 集。

### Status

**Research result only — nothing promoted.** A change proposal is filed at
`docs/team/change_proposals/20260821_p1_r16_layer2_counterrow_dose.md` with its
**Approval Record blank** and the proposer's own recommendation set to
**do not approve as-is; run a multi-seed confirmation first**. All frozen files
(`pipeline.py`, both production Layer1s, production Layer2,
`artifact_classifier_v3.pth`, all three P1-R14 checkpoints) re-hashed
byte-identical at round end (`frozen_hashes_{start,end}.txt`, diff clean).
No git operation was run.

---

## Correction Log — 2026-08-21 documentation-accuracy sweep

**Nature of this entry**: a project-wide **framing / wording correction**, appended
(not overwritten). **No number, no pass/fail verdict, no approved decision, no
checkpoint, no split, and no code was changed by this sweep.**
`pipeline.py`, `splits/`, `results/`, `checkpoints/` were not touched.

### C1 — "OOD" mislabelling of two evaluation sets

**What was wrong.** Two evaluation sets were called out-of-distribution
project-wide. A content-level audit proved neither is:

| set | measured content overlap with training data | source of the overlap |
|---|---|---|
| `stylegan2_test/fake/` | **63.8% (6,376/10,000)** | `AIGuard/fake` + `fake_filter_hard_neg` — both sides sampled the same 140k Real-Fake Faces corpus; some pairs are byte-identical |
| `FFHQ_ali_process` (Alibaba filter gate) | **23.5% (4,980/21,151)** | `AIGuard/real` and `filter_data/*` contain the same FFHQ base photos under different filenames |

The prior clean-bill-of-health for Alibaba was obtained by comparing **FFHQ index
ranges** (Megvii 60002-69999 vs Alibaba 17000-19999). That check is correct as far
as it goes — those two ranges really are disjoint — but it is **structurally blind
to the same photograph stored under a different name**, which is the path the real
overlap took. This is Known trap #3 in this registry, and it is why a content key
is now mandatory.

**What did NOT change.** All measured numbers stand. StyleGAN2 decontaminated
performance is ≈**99.07%**, still above its gate; contaminated images performed
*worse*, not better, on every version, so no approved decision required
re-examination.

**Corrected wording, to be used from now on:**
- **"StyleGAN2 fake detection"** — never "StyleGAN2 OOD".
- **"Alibaba filter recall（跨濾鏡演算法，非 OOD——與訓練資料有 23.5% 內容重疊）"**.

**Applies retroactively to every row in this registry** labelled "Alibaba filter
OOD", "StyleGAN2 ... OOD", "GAN OOD" or "Filter OOD" — including the P1-6 / P1-7 /
P1-9 / P1-11 result tables above. Those rows were left as written (they are dated
records of what was measured); read the label through this correction.

**Genuinely clean cross-domain evidence that remains** — documents must not
over-correct into claiming the project has none:
1. **CelebA real recall** — CelebA's official `list_eval_partition.txt` is
   identity-disjoint by design; separately verified clean.
2. **AIGuard/unseen AUROC** — fully held out; separately verified clean.
3. **True Test vs Shadow** — identical self-built filter code applied to base
   images of a different photographic style. A valid within-project cross-domain
   contrast, unaffected by this correction.

Conversely: **the project currently has no content-verified-clean filter
algorithm-OOD source.** Any future candidate must be screened with a content key
(decoded-pixel SHA256 + perceptual-hash screen resolved by NCC/MAD), not by index
range or filename stem.

**Evidence**: `results/research/p1_r11_leakage_scaling_20260820/TASK1_LEAKAGE_AUDIT.md`.

### C2 — Freeze Gate statistical-power annotation

A statistical-power column was **added** to the Phase 1 Freeze Gate table in this
registry and to its copy in `TODO.md`. **No recorded pass/fail verdict was
altered.** Two gates are marked as never statistically established (True Test
filter recall ≥90%, True Test paired balanced accuracy ≥80% — both CIs straddle
their own thresholds), AIGuard-unseen AUROC is marked marginal (lower bound
0.8034), and the Alibaba / fake+filter-stress sample sizes are marked misleading
(shared base images ⇒ non-independent observations ⇒ their CI widths must not be
quoted as precision). The LFW base-image pool is **exhausted** (0 new clean images
available), so these two gates belong in the paper's Limitations rather than
triggering another training round.

**Evidence**: `results/research/p1_bench_power_20260820/BENCHMARK_POWER_REPORT.md` §1.1, §3.

### Files touched by this sweep

Full before/after log: `results/research/doc_correction_sweep_20260821/CORRECTION_LOG.md`.
Approved change proposals were **appended to only** (addendum sections); no
existing text in any Approval Record was altered.

---

## P2-R1: Tier-A explanation-localization benchmark (8,784 paired images, two base-image domains)

- **Phase**: Phase 2 (XAI / explanation validation track). Round directory:
  `results/research/p2_r1_tierA_localization_20260821/`, full report
  `P2_R1_FINDINGS.md`.
- **Purpose**: The Phase 2 design review (`results/research/phase2_design_review_20260821/`)
  found every localization conclusion in the project rested on n=100/type and that
  the strongest trivial control — a per-type constant mask, which is essentially
  what `ARTIFACT_REGION_MAP` is — had never been run. Build a real Tier-A benchmark
  from the paired filter data and settle three questions: does Grad-CAM++ beat every
  trivial baseline; does explanation localization degrade in the VGGFace2 domain the
  way classification does; does any real method earn its keep.
- **Training performed**: **none**. Inference-only evaluation of existing checkpoints.
- **Model checkpoints**: production pair `shufflenet_v2_layer1_v817sbi.pth` +
  `shufflenet_v2_layer2_v811.pth`, imported directly from `pipeline.py` (read-only)
  with byte-identical preprocessing. `region_head_v4.pth` on the
  `archive/checkpoints_legacy_v3_v89/shufflenet_v2_3class_v88.pth` backbone, i.e.
  the configuration `xai_eval_protocol.py` uses.
  Grad-CAM++ run at **batch=1**; verified max-abs-diff **0.0** vs
  `pipeline.GradCAMPlusPlus` (batch=32 drifts by mean 2.5e-4 through cuDNN
  algorithm selection — measured, rejected, see `_verify_batch_cam.py`).
- **Ground truth**: recomputed, **not reused**. The cited 31,993-row artifact
  (`results/landmark_gt_summary.csv`) is an **8-region ON/OFF table**, not pixel
  masks, and `generate_landmark_gt.py` never stored the difference maps. This round
  computes per-pixel CIELAB dE76 between base and filtered at the same 224x224 frame
  `pipeline.py` feeds the classifier, 3x3 median denoise, threshold tau=3.0.
  A JPEG re-encode control shows tau=3.0 admits <0.5% false-positive pixels.
  All five taus in {1.5, 2.0, 3.0, 5.0, 8.0} were recomputed in full.
- **Test source and disjointness** (content key = **SHA256 of decoded RGB pixels**;
  dHash<=4 used as a screen only and resolved by 64x64 grayscale RMSE<6, per
  Known trap #3). Training corpus = 252,710 unique paths from the split files that
  produced both production checkpoints, 251,348 decoded.

  | stratum | source | domain | n scored | filtered imgs in train | base imgs in train |
  |---|---|---|---:|---:|---:|
  | S1 | `filter_data/{4 types}` | aligned crop | 4,000 | **4,000 (100%)** | 3,899 |
  | S2 | `test_set_true/filter/` (True Test) | aligned crop | 249 | **0** | **0** |
  | S3a | `shadow_filter/` | VGGFace2 wild | 281 | **0** | **0** |
  | S3b | `shadow_v2a_filter/` | VGGFace2 wild | 1,145 | **0** | **1,148 (100%)** |
  | S3c | `shadow_v2b_filter/` | VGGFace2 wild | 1,105 | **0** | **0** |

  Within-stratum content duplicates: 0 in all strata (both filtered and base).
- **Image-disjoint from train/val?**: S2, S3a, S3c **yes, on a decoded-pixel content
  key**. S1 **no by construction** — all 25,212 clean `filter_data` images are in
  `v811_layer2_train/val`; the aligned domain has no held-out self-built-filter
  subset, so S1 is an upper-bound test, not a generalization test.
  **S3b: filtered images held out, but all 1,148 base photographs are in Layer1's
  training set** (see the new finding below). Layer2 has never seen VGGFace2 (0 hits).
- **Participated in model selection?**: No. Nothing was trained, tuned, or selected.
- **Results** (primary metric **APlift** = pixel average-precision / GT prevalence;
  threshold-free and area-free, random = 1.0, so it is not saturated by large masks;
  IoU@15%, IoU@GT-area, IINC, Pointing Game also reported with bootstrap 95% CIs in
  `ci_primary.csv`):
  - **Grad-CAM++ loses to a per-type constant mask in 13 of 15 (stratum x type)
    cells at production's own operating point** (images the hierarchy calls
    `filter`). dAPlift: S1 ALL **-4.87 [-5.04,-4.70]**, S2 ALL **-2.40
    [-3.03,-1.81]**, S3 ALL **-0.67 [-0.89,-0.47]**.
  - **The one surviving win**: S3 (VGGFace2 wild) / **whitening** / detected subset,
    dAPlift **+0.216 [+0.063,+0.367]**, n=134, per-image win rate 67.2%; still
    **+0.247 [+0.039,+0.453]** (n=67) on the contamination-free S3a+S3c subset.
  - **Known trap #1 bit again, in the opposite direction**: S3/smoothing shows
    Grad-CAM++ **significantly better** on all images (+1.274 [+1.060,+1.503]) and
    **significantly worse** on the detected subset (-0.635 [-1.185,-0.122]). Same
    data, same method, opposite verdict, sub-population is the only difference.
  - `region_head_v4` wins exactly 1 of 15 cells (S2/smoothing, n=63, +0.972
    [+0.542,+1.390]) and loses to `facecenter_box@gt` even there; in the wild domain
    it is the worst method measured (APlift 2.306 vs Grad-CAM++ 5.539).
  - **Trivial baselines again beat the real methods on IoU**: `facecenter_box@15`
    ("draw a box on the face") is the IoU@15 winner in S2/S3 ALL and in every
    skin-tone filter type — the filter-side reproduction of the SBI pilot's
    "face box 0.5499 beats both".
  - **Pointing Game confirmed non-discriminative again**: S1 ALL const_prior 0.888,
    trivial center_point 0.343, Grad-CAM++ 0.287.
  - **Explanation localization does NOT collapse where classification does**:
    S2 -> S3 filter recall **91.97% -> 14.62%** (6.3x), while Grad-CAM++ APlift falls
    only **6.717 -> 5.539 (-17.5%)**, still 5.5x random; for smoothing it does not
    fall at all (+0.3%, dAPlift +0.018 [-0.449,+0.478], n.s.). The fixed prior
    degrades **more** (-31.9%) than the image-conditioned heatmap, which is the
    mechanism behind the two cells where Grad-CAM++ wins.
  - **GT coverage (median, as fraction of the MediaPipe face box)**: whitening
    **0.64**, smoothing 0.23-0.31, face_reshaping 0.20-0.34 (only 45-49% of its
    changed pixels fall inside the face box at all), eye_enlarging **0.04-0.10**.
    Whitening therefore sits at the same coverage scale that got SBI masks rejected
    as a benchmark (median 62%) and cannot support strong localization claims.
  - **Threshold sensitivity**: 13/15 cells give the same APlift verdict at all five
    taus; the three-stratum `ALL` verdict is const_prior at **every** tau.
    Two cells flip: S3/whitening (Grad-CAM++ wins at tau<=5.0, loses at tau=8.0)
    and S2/smoothing (underpowered, n=63).
- **New finding, previously undocumented (recorded for cross-phase visibility, not
  a Phase 2 claim)**: all 1,148 base photographs of `shadow_v2a_filter`
  (`vggface2_train_sample`) are in Layer1's training corpus — added as wild real in
  P1-R8 and reused as the SBI source in P1-R9. `generate_p1_r16_shadowv2.py`
  asserted disjointness only against the primary Shadow set, never against the
  training corpus. This is exactly Known trap #3's shape. All P2-R1 S3 headline
  conclusions were re-run on the clean S3a+S3c subset and **none changed**
  (`clean_s3_recheck.csv`). Any future use of Shadow-v2a as an evaluation set must
  carry this caveat.
- **Claim**: On 8,784 pixel-level paired ground-truth images spanning two base-image
  domains, neither Grad-CAM++ nor `region_head_v4` beats a per-type constant mask
  that never looks at the image, at production's operating point, in any filter type
  in the aligned-crop domain, or in three of four types in the wild domain. The
  single exception is whitening in the wild domain, whose effect size is small,
  threshold-sensitive, and sits on a filter type whose GT already covers 64% of the
  face. Separately, and positively: heatmap localization quality is largely
  **decoupled** from classification collapse under domain shift.
- **Non-claim**: (i) does not improve any claim about **real commercial app filters**
  — all four operators are this project's own algorithms, Tier B still has 0 reliable
  pairs; (ii) says nothing about **fake-class localization** — `pipeline.py` emits
  `regions=[]` for fake and Tier D's FF++ conclusions are untouched and unextended;
  (iii) S1's numbers are an in-domain upper bound, not generalization; (iv)
  whitening/smoothing IoU is not strongly discriminative given GT coverage;
  (v) per-type n in S2 is ~62, and cells flagged UNDERPOWERED in
  `operating_point_analysis.csv` are not ranked; (vi) no real-device measurement.
- **Consequences / status**: change proposal
  `docs/team/change_proposals/20260821_p2_r1_localization_consequences.md` written
  with a **blank Approval Record** (C1 keep Grad-CAM++ out of the JSON, now on
  evidence rather than by default; C2 keep `ARTIFACT_REGION_MAP` but document that
  its hand-written boxes score IoU@15 0.122-0.185 versus 0.296-0.409 for an
  empirically fitted per-type prior at the same zero inference cost; C3 archive
  `region_head_v1..v4`). **`pipeline.py`, all checkpoints, `splits/` and existing
  `results/` were not modified by this round.**
- **Self-caught error, recorded so it is not repeated**: the first scoring pass used
  `np.argpartition(-flat, k-1)` on a **uint8** array; negating uint8 wraps modulo 256,
  which silently **inverted** every continuous method's top-k binarization. Caught by
  an implausible diagnostic (the constant prior scoring IoU@GT-area 0.005 on its own
  fitting distribution), fixed by widening to int32, and all tables were recomputed.
  Rule: never negate a uint8 array to sort it.

## P2-R2: empirically-fitted box coordinates for `ARTIFACT_REGION_MAP`, held-out + cross-domain validated

- **Phase**: Phase 2 (XAI / explanation validation track). Round directory:
  `results/research/p2_r2_empirical_region_map_20260821/`, full report
  `P2_R2_FINDINGS.md`.
- **Purpose**: P2-R1's change proposal (C2) found the hand-written
  `ARTIFACT_REGION_MAP` scores IoU@15 0.122-0.185 versus 0.296-0.409 for the
  continuous `const_prior` empirical mask, at the same zero inference cost, but
  only concluded "worth a future change-control round" without concrete
  pipeline-format coordinates or held-out validation of a box-simplified
  version. This round does that: extract boxes, validate on data the fit never
  saw, check cross-domain generalization, and write a proposal.
- **Training performed**: **none**. Extraction from P2-R1's existing
  `const_prior_maps.npy` (fitted on pool P, 500/type, content-disjoint from
  S1/S2/S3 per P2-R1 SHA256 audit) + rescoring on P2-R1's existing GT arrays.
  No new images processed, no model run.
- **Method**: box = axis-aligned bounding box(es) of the connected components
  of `topk_mask(const_prior_maps[type], area=round(mean_gt_frac*224^2))`, up to
  2 components (minor component dropped if <5% of the largest), producing 1-2
  rectangles per type in `pipeline.py`'s `FACE_REGIONS` coordinate format.
  `iou()`/`topk_mask()`/the hardcoded-map expansion and bootstrap CI functions
  are copied verbatim from P2-R1's `score_p2r1.py`, not redesigned.
- **Fit/eval split**: fitting pool P was never scored (P2-R1 already audited P
  disjoint from S1/S2/S3 by decoded-pixel SHA256). S1 (4,000, aligned,
  100% train-seen) is an upper-bound test only. **S2 (249, aligned, true
  held-out) and S3 (2,531, VGGFace2 wild, true held-out, cross-domain) are the
  actual generalization tests.**
- **Results** (box-vs-box IoU, same GT tau=3.0, same `iou()` definition as
  P2-R1; full table `iou_old_vs_new_boxes.csv`):
  - **New box beats the current hardcoded map in all 15 (stratum x type)
    cells**, CI excludes 0 in every cell, including both held-out strata's all
    4 types.
  - S2 (aligned held-out) ALL: old 0.122 -> new **0.313**, delta +0.191
    [+0.181,+0.201], per-image win rate 100.0%.
  - S3 (wild held-out, cross-domain) ALL: old 0.153 -> new **0.295**, delta
    +0.142 [+0.138,+0.147], per-image win rate 87.5%.
  - **Weakest cell**: S3/eye_enlarging, delta +0.067 [+0.060,+0.075], win rate
    72.5% (lowest of all 15 cells) -- expected, it is the only type whose GT is
    genuinely local (P2-R1: 4-10% of the face box), so the fixed box is most
    exposed to face-pose variance in the wild domain.
  - **Largest cross-domain decay**: face_reshaping, S2 delta +0.191 -> S3 delta
    +0.082 (-57%), consistent with P2-R1's mechanism finding that only 45-49%
    of face_reshaping's changed pixels fall inside the face box at all. Still
    CI-excludes-0 significant at 80.5% win rate.
  - Box-simplification cost vs the continuous `const_prior@15` numbers already
    published in P2-R1: non-monotone, from +0.058 (box actually beats the
    continuous mask on S1/ALL) to -0.200 (S2/whitening, largest cost, because a
    rectangle cannot hug an oval GT shape). Cost does not reverse the
    conclusion in any cell (`box_simplification_cost.json`).
- **Claim**: the empirically-fitted box replacement for `ARTIFACT_REGION_MAP`
  generalizes -- it beats the hand-written map on data its fitting process
  never saw, in both the same base-image domain it was fit on (aligned crop)
  and a genuinely different one (VGGFace2 wild), across all 4 filter types.
  This is not an overfit-to-the-fitting-sample result.
- **Non-claim**: (i) does not validate text readability/user comprehension of
  the new `REGION_DISPLAY` strings, only spatial accuracy (IoU proxy); (ii)
  eye_enlarging's cross-domain margin is the thinnest of the 4 types and
  should not be described as equally strong as the others; (iii) does not
  address what happens if the filter-generation algorithms are revised (the
  fit pool shares the same algorithms as production training data, same
  maintenance liability the old map already had); (iv) no real-device or
  production-traffic measurement.
- **Consequences / status**: change proposal
  `docs/team/change_proposals/20260821_p2_r2_empirical_region_map.md` written
  with a **blank Approval Record**, proposing to replace `ARTIFACT_REGION_MAP`
  and add `EMPIRICAL_FILTER_REGIONS` + `REGION_DISPLAY` entries in
  `pipeline.py`. Blast radius stated as bounded to the `suspicious_regions` /
  `explanation` text fields only -- no classification logic, checkpoint,
  threshold, or JSON schema structure touched. **`pipeline.py`, all
  checkpoints, `splits/` and existing `results/` were not modified by this
  round.**

---

## P1-14: P1-R17 — 5-seed replication of the C1↔C2 counter-row dose with INTERVAL-based criteria; **`SEED_VARIANCE_DOMINATES`**, doses **`INDISTINGUISHABLE`**

- **Round dir**: `results/research/p1_r17_seed_replication_20260821/`
  (`P1_R17_FINAL_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `DEVIATION_LOG.md`,
  `analysis_p1_r17.json`, `shadowv2_provenance_audit.json`, per-image dumps for
  10 runs × 2 batteries)
- **Checkpoints**: `checkpoints/research/p1_r17_seed_replication_20260821/`
  `layer2_p1_r17_{R50,R75}_s{20260822,20260823,20260824,20260825}.pth`
  (7 new; 3 more runs reused read-only from P1-R16's `R50`, `R75`, `R75s2`) —
  **research only, none promoted**
- **Purpose**: P1-R16's `R75` reached a pre-declared `SUCCESS` that flipped to
  failure on a single reseed (3 images of 279 on an absolute "≥20%" line). This
  round replaces every absolute threshold with an across-seed interval and asks
  whether either counter-row dose (r = 0.50 or r = 0.75) is a **robust**
  candidate under a criterion immune to a single-seed flip: the primary-gain
  test (S3′) requires the seed-level 95% CI on the delta to exclude 0 **and**
  ≥4 of 5 seeds to be individually significant, not merely a mean above a line.
- **Design**: 5 seeds per dose (20260821–20260825), training split / init
  checkpoint / val split / recipe / Layer1 held byte-identical — the seed is
  the only variable. 3 of 10 runs reused read-only from P1-R16 (re-verified on
  disk: 363 tensors, no NaNs, sha256 matches training manifest); 7 new.
- **Image-disjoint from train/val?**: Splits are byte-identical re-use of
  P1-R16's, already audited (K1=K2=exact-pixel=0 against 138,283 Layer2
  training paths). **Mid-round correction**: the concurrent P2-R1 round found
  Shadow-v2 stratum S2A's base photographs (`vggface2_train_sample`) are
  **inside Layer1's training set** (added P1-R8, used as SBI source P1-R9) —
  P1-R16's own Shadow-v2 audit had checked only the Layer2 universe (138,283
  paths), not Layer1's. Re-audited this round against P2-R1's full v8.17
  lineage universe (**252,710 paths / 249,864 distinct images**, same method:
  decoded-pixel SHA256 exact + dHash≤4 screen resolved by 64×64 RMSE<6.0):
  **S2A filtered 71.4% train-seen, S2A bases 100% train-seen (pixel-identical)
  — confirmed and worse than base-only.** S2B (0.0%) and the **PRIMARY Shadow
  set (0.0% both sides, newly verified against the full universe, previously
  only checked against 138,283 paths)** are clean.
- **Source-disjoint from train/val?**: See above — S2A is NOT source-disjoint
  from Layer1 training; S2B and the primary Shadow set are.
- **Participated in model selection?**: No. Epoch selection used only the
  unchanged in-domain val split; operating points selected per-seed only on
  `stressdev` (disjoint from every gate), written to disk before gates
  recomputed.
- **Reproduction / validation**: every checkpoint (new and reused) verified to
  load with 363 tensors, zero NaNs, sha256 matching its own training manifest,
  at every resume point (the training chain was interrupted by session limits
  three times; each resume validated on-disk state before treating any stage
  as complete and recomputed only stages that failed validation — no run was
  ever silently re-run or silently trusted).

### 可宣稱結論

1. **Neither dose reaches `ROBUST`.** Both R50 and R75 pass S1′ (frontier 9/9,
   every seed) and S2′ (all four low-FPR statistics, every seed — the exact
   criterion that demoted P1-R16's C1) but **fail S3′**: pooled delta CI
   excludes 0 for both (R50 +4.30pp [+0.64,+7.96]; R75 +4.80pp [+1.69,+7.91])
   but only **3 of 5 seeds are individually significant** for either arm
   (need ≥4). S4′ passes for both (no seed breaches any Freeze-Gate A
   threshold). **Verdict: both `NO_ROBUST_GAIN`. Round verdict:
   `SEED_VARIANCE_DOMINATES`.**
2. **R50 and R75 are `INDISTINGUISHABLE`** on the primary endpoint (Shadow
   filter recall delta): CIs [+0.64,+7.96] vs [+1.69,+7.91] overlap almost
   completely, Welch p=0.78. No winner is named between the two doses.
3. **The seed-to-seed spread is large relative to the effect**: Shadow filter
   recall ranges 13.26–20.43% for R50 (one seed's delta is exactly +0.00pp)
   and 14.70–20.43% for R75, with significant and non-significant seeds
   interleaved with no visible pattern. `R75s2` (P1-R16's flip-causing seed)
   sits mid-pack here, not as an outlier.
4. **True Test filter recall**: every seed of every arm — and frozen
   production itself — lands in 90.76–91.97% (k=226–229/249, Wilson CIs all
   straddling both 90% and 92%). Reported against both candidate thresholds
   per the unresolved gate-framing/Freeze-Gate discrepancy (TODO.md:535 vs
   :594); **neither threshold is adjudicated by this round**, and no seed,
   arm, or production baseline is separable from any other on this metric
   under either reading.
5. **Shadow-v2 per-type statements move to S2B** (clean, n≈273–287/type). On
   S2B, **all four per-type lift intervals mutually separate for both doses,
   pooled across 5 seeds**: smoothing (6.5–6.6×) > whitening (~2×) ≫
   eye_enlarging (~1.7×) > face_reshaping (~1.5×) — the first properly-powered,
   seed-pooled per-type Shadow ranking in this research line.
6. **The geometric-vs-photometric gap (P1-R16's descriptive observation) is
   confirmed on S2B for both doses and the pooled seed set**: photometric mean
   lift 4.24–4.34× vs geometric mean lift 1.59–1.66×, group intervals separate,
   and — unlike on the (now-disqualified) S2A — **every individual photometric
   type's interval sits above every individual geometric type's interval** (the
   strict per-type-pair test). **Not established to the originally
   pre-declared "both strata" standard**, since only one stratum remains clean
   this round; reported as single-stratum-confirmed, not fully closed.
7. **No change proposal filed.** The pre-declared rule requires one only if an
   arm reaches `ROBUST`; neither does.

### 不可宣稱事項

- 不可宣稱 r=0.50 或 r=0.75 是穩健候選——兩者皆為 `NO_ROBUST_GAIN`。
- 不可宣稱兩個劑量哪個較好——`INDISTINGUISHABLE`，Welch p=0.78。
- 不可宣稱介入本身無效——pooled 增益顯著（CI 不含 0），只是**逐種子一致性**未達標準。
- **不可用 Shadow-v2 S2A 做任何 per-type 推論**——71.4% 與 Layer1 訓練集重疊，
  已確認且比純底圖污染更嚴重（filtered 影像本身也大量重複，因為濾鏡只是底圖的
  輕微擾動）。S2A 數字僅供對照，標示 CONTAMINATED。
- 不可宣稱 geometric vs photometric gap 已在「兩個 stratum」的原訂標準下確立——
  本輪只剩 S2B 一個乾淨 stratum。
- True Test filter recall 的 ≥90% / ≥92% 門檻分歧**已於 2026-08-21 由 Member A
  裁定為 ≥90%**（≥92% 會讓所有已上線版本回溯性不通過，判定不合理）。本輪報告中
  並陳兩者的段落屬裁定前的既有記錄，保留不動；往後新報告請直接引用 ≥90%。
- 不可宣稱幾何型別缺口已設計或啟動任何介入——本節嚴格描述性，Known Trap #4 適用。
- 未讀取 `splits/v815_replication_set.tsv` 與 P1-R3.4 dose-aligned DF40-cdf 集。

### Status

**Research result only — nothing promoted.** No change proposal filed (round
verdict does not meet the `ROBUST` bar that would require one). All frozen
files (`pipeline.py`, both production Layer1s, production Layer2,
`artifact_classifier_v3.pth`, all P1-R14 and P1-R16 checkpoints) re-hashed
byte-identical at round end. No git operation was run.

---

## P1-15: P1-R18 — geometric-augmented counter-row variant (eye_enlarging /
face_reshaping warps added to SBI counter-rows); **`NO_GEOMETRIC_GAIN`**

- **Round dir**: `results/research/p1_r18_geometric_intervention_20260821/`
  (`P1_R18_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `analysis_p1_r18.json`,
  `geo_warp_log.jsonl`, `geo_split_build_manifest.json`, per-image dumps)
- **Checkpoints**: `checkpoints/research/p1_r18_geometric_intervention_20260821/`
  `layer2_p1_r18_{G50,G100}_s20260821.pth` (2 new; `G0` reused read-only from
  P1-R17/P1-R16's `R75` s20260821 run) — **research only, none promoted**
- **Purpose**: P1-R17 found (properly powered, S2B) the counter-row
  intervention lifts photometric filter types far more than geometric types
  (smoothing 6.5-6.6x, whitening ~2x vs eye_enlarging ~1.7x, face_reshaping
  ~1.5x). This round tests the mechanistic hypothesis (confirmed plausible by
  reading `sbi/sbi_generator.py`: SBI's own geometric perturbation is a small
  global affine + generic elastic seam-warp, never landmark-region-targeted)
  that adding the project's own `apply_eye_enlarging`/`apply_face_reshaping`
  warps (reused unmodified from `filters/stress_test_filter_functions.py`) to
  a fraction of the counter-rows closes the gap.
- **Design**: dose held fixed at r=0.75 (R50/R75 were `INDISTINGUISHABLE` in
  P1-R17); 3 arms, single seed (20260821, matching G0): `G0`=pure SBI
  (unchanged R75), `G50`=50% of the 4,050 counter-rows additionally
  geometric-warped, `G100`=100% (3,998/4,050 succeeded, 52 kept pure-SBI on
  landmark failure, never silently substituted). Everything else
  byte-identical to R75 (base rows, init checkpoint, val split, recipe,
  Layer1, seed). Single-seed pilot, explicitly not a P1-R17-style replication.
- **Image-disjoint from train/val?**: Yes — the warp only perturbs pixels of
  counter-row images already content-audited by P1-R14 (0 overlap); no new
  source image introduced. Integrity gate (path/stem membership against every
  gate/eval set) re-run this round: 0 overlaps.
- **Source-disjoint from train/val?**: Same as R16/R17's R75 (unchanged base).
- **Participated in model selection?**: No. Epoch selection used only the
  unchanged in-domain val split; operating point selected on `stressdev` only.
- **Reproduction / validation**: both new checkpoints verified 363 tensors,
  zero NaNs, sha256 matching their own training manifests.

### 可宣稱結論

1. **Task 1 diagnostic confirms a mechanistic basis**: SBI's counter-row
   construction contains no landmark-region-targeted geometric perturbation —
   only a global small affine and a generic elastic seam-warp, neither of
   which resembles what `eye_enlarging`/`face_reshaping` actually do.
2. **Neither G50 nor G100 clears the pre-declared geometric-lift bar (P1)**:
   pooled Shadow-v2 S2B geometric-type recall moves from G0's 23.46%
   [20.15,27.12] to 25.22% [21.82,28.95] for both arms — a small numeric
   uptick whose CI lower bound (21.82) does not exceed G0's point estimate
   (23.46). **Verdict for both arms: `NO_GEOMETRIC_GAIN`.**
3. **Photometric type preserved (P2 holds)**: pooled photometric S2B recall
   47.5-47.7% vs G0's 49.36% [45.19,53.54] — within G0's interval, no
   detectable trade-off.
4. **Freeze-Gate A: no breach for either arm (P3 holds)**; low-FPR statistics
   non-inferior and in fact numerically better than G0 on AUROC/pAUC(FPR<=5%)/
   TPR@1%/TPR@5% (P4 holds).
5. **Unplanned secondary finding — primary Shadow set regresses significantly**:
   frozen Shadow filter recall drops from G0's 20.43% (57/279) to 15.05%
   (G50, 42/279) and 14.34% (G100, 40/279); paired-bootstrap CIs on the delta
   vs G0 exclude 0 for both ([-8.60,-2.51] and [-9.32,-3.23]). Both remain
   above frozen production's 13.26% baseline (P1-R17), so this is a regression
   relative to G0 specifically, not below the pre-intervention floor. Frontier
   win count vs G0's own curve is 0/9 for both arms.
6. **G50 and G100 are `INDISTINGUISHABLE`** on pooled geometric recall
   (identical point estimates, fully overlapping CIs) — the extra dose from
   50% to 100% geometric mix changed 0 predictions on the S2B geometric-type
   images at this seed.
7. **No change proposal filed.** The pre-declared rule requires one only for a
   `PROMISING_CANDIDATE` verdict; neither arm reaches it.

### 不可宣稱事項

- 不可宣稱幾何濾鏡型別的介入有效——CI 下界未超過 G0 點估計，P1 未過。
- 不可宣稱 G50 與 G100 何者較佳——兩者 pooled geometric 數字完全相同，
  CI 完全重疊，`INDISTINGUISHABLE`。
- 不可宣稱 23.46%→25.22% 的小幅上升是真實效果——這正是 Known Trap #4 警告
  的「小 n 相關性」，區間檢定結果是否定的。
- 不可宣稱 primary Shadow set 的顯著退步一定是幾何擾動本身造成（而非單一
  seed 的雜訊）——本輪為單一 seed pilot，需要 P1-R17 式的 seed replication
  才能確認這個退步是穩定現象還是雜訊，此輪不做這個宣稱（無論是宣稱增益
  還是宣稱退步都一樣需要 replication 才能定案）。
- 不可宣稱本輪已測試過所有可能的幾何介入設計——只測了 50%/100% 兩種混合
  比例、單一劑量 r=0.75、單一 seed；更低比例、不同劑量、seed replication
  皆未執行，留給未來回合。
- 未重啟 dose r、Layer1、SBI scaling 或任何先前回合已關閉的軸線。
- 未 promote 任何 checkpoint。

### Status

**Research result only — nothing promoted.** No change proposal filed (round
verdict is `NO_GEOMETRIC_GAIN` for both arms, not `PROMISING_CANDIDATE`). All
frozen files (`pipeline.py`, both production Layer1s, production Layer2,
`artifact_classifier_v3.pth`, all prior P1-R* checkpoints) re-hashed
byte-identical at round end. No git operation was run.

---

## CLEANUP-20260821: Contamination cleanup + comprehensive clean re-benchmark

- **Phase**: Cross-phase data integrity (not a Phase 1 research round — no new
  candidate trained, no intervention tested).
- **Purpose**: Pause new research threads and resolve three known-but-deferred
  contamination issues (Layer1 val/Alibaba-gate overlap C1.11.7, Shadow-v2 S2A
  71.4% train-seen, sd2.1 duplicate frames), then produce one authoritative
  clean-metrics table for production.
- **Model checkpoint**: Read-only throughout. Verified (not retrained):
  `shufflenet_v2_layer1_v817sbi.pth` (sha256 `e3057270...e14b90`) +
  `shufflenet_v2_layer2_v811.pth` (sha256 `8470ad52...55057e`).
- **Train source**: N/A (no training performed this round).
- **Validation source**: `splits/v811_layer1_val_clean_20260821.txt` (new,
  12,031 rows = `v811_layer1_val.txt` minus 2,644 `FFHQ_ali_process` rows),
  used only for post-hoc rescoring of already-existing P1-R9 checkpoints, not
  for any new training run.
- **Test source**: Reused existing clean assets (True Test v2 n=998 expanded
  set from `p1_bench_power_20260820`, primary Shadow set, AIGuard/unseen,
  CelebA, StyleGAN2, Alibaba, fake+filter stress, FF++), all cross-checked by
  checkpoint sha256 against production before reuse. No re-measurement was
  needed or performed for these.
- **Image-disjoint from train/val?**: Task 1's clean val checked against all
  four in-scope Layer1 train lineages (`v811_layer1_round4_train.txt` +
  P1-R9/R10/R11 SBI extras) on K1 (path) and K2 (stem): 0 path collisions,
  1,236 stem collisions per train set, all resolved to 0 exact-pixel matches
  by decoded SHA256 (same-base-index `FFHQ_four_process` vs
  `FFHQ_megvii_four_process` rows under different filter pipelines — a known,
  pre-existing, non-exact-pixel base-image overlap, out of this task's scope,
  flagged for a future Layer1 retrain to consider).
- **Source-disjoint from train/val?**: See above.
- **Participated in model selection?**: **Yes, this is the finding.** The
  contaminated `v811_layer1_val.txt` was the checkpoint-selection (best-epoch)
  validation set for the P1-R9 round that produced production's current
  Layer1. Rescored all 6 existing P1-R9 checkpoints (CTRL/SBI/SBIAUG,
  best+last) on the clean val: **no arm's best-vs-last ranking flips**.
  Production's actual source epoch (SBIAUG epoch 1) remains the top scorer on
  clean val among the two available snapshots for that arm, consistent with
  its selection on the old val and with the training log showing epoch 1
  strictly dominates epochs 2-5 on the old val too. Full per-checkpoint
  numbers in `results/research/contamination_cleanup_20260821/task1_checkpoint_rescoring.json`.
- **Results**:
  - Task 1: `splits/v811_layer1_val_clean_20260821.txt` (12,031 rows);
    `results/research/contamination_cleanup_20260821/rescoring_layer1_val_clean.py`
    + `task1_checkpoint_rescoring.json`.
  - **Incidental finding (not part of the original task, surfaced by sha256
    cross-checking during rescoring)**: production's `shufflenet_v2_layer1_v817sbi.pth`
    is byte-identical (sha256 `e3057270...`) to P1-R9's **SBIAUG** arm best
    checkpoint, not the "SBI" arm (sha256 `b5f25810...`, never copied to
    production) that the filename and CLAUDE.md's shorthand suggest. The
    underlying round documentation (`P1_R9_FINAL_FINDINGS.md`, and the change
    proposal filename `20260820_p1_r9_sbi_layer1_sbiaug.md` itself) already
    correctly identifies SBIAUG as the promoted candidate, and all reported
    numbers are verified correct for the actual deployed weights (gate JSON
    for "PROMOTED" is byte-for-byte numerically identical to `gates_SBIAUG.json`).
    This is a naming-clarity issue in top-level summary docs (CLAUDE.md,
    production filename), not a wrong-checkpoint or wrong-numbers bug. Flagged
    for a human decision on whether to rename.
  - Task 2: `shadow_v2a_filter/README_DEPRECATED.md` — S2A formally retired,
    S2B confirmed as the standing secondary Shadow confirmation set (both were
    already characterized by P1-R16/P1-R17; this round only executes the
    permanent-disposition decision).
  - Task 3: `results/research/contamination_cleanup_20260821/sd2.1_dedup_manifest.json` —
    full-corpus (53,474 files, `sd2.1/ff/`+`sd2.1/cdf/`) decoded-pixel SHA256
    dedup. **4,125 duplicate groups, 7.714% redundant-file rate** (vs. the
    previously sampled ~0.022% estimate from a 3,000-image subset — the true
    rate is ~350x the earlier estimate because duplication is concentrated,
    not uniform, and confined entirely to `sd2.1/ff/` internal reuse across
    identity/video subfolders; 0 in `cdf/`, 0 cross-`ff`/`cdf`). No existing
    split rebuilt.
  - Task 4: consolidated clean metrics table in
    `results/research/contamination_cleanup_20260821/CLEANUP_AND_RETEST_REPORT.md`.
    All figures reused-and-sha256-verified from `gates_PROMOTED.json` (2026-08-20
    post-promotion reproduction) and `BENCHMARK_POWER_REPORT.md` (2026-08-20
    n=998 power upgrade); no re-measurement found necessary.
- **Claim**: (1) The Layer1 val contamination (C1.9.8/C1.11.7) that was
  avoided for three consecutive rounds is now fixed, and — the highest-value
  part of the assessment — does **not** change which checkpoint is in
  production. (2) A separate, previously-unnoticed naming discrepancy exists
  between the production checkpoint's actual identity (SBIAUG) and its
  filename/shorthand ("SBI"); the underlying numbers and round documentation
  were already correct, only the top-level name is misleading. (3) Shadow-v2
  S2A is now unambiguously retired; S2B is the standing secondary set. (4) The
  true sd2.1 duplicate rate is 7.71% project-wide, ~350x the previously
  sampled estimate, though still confined to intra-`ff` redundancy with no
  demonstrated train/test leakage beyond what was already known and judged
  negligible.
- **Non-claim**: Does **NOT** promote, rename, or modify any production
  checkpoint or `pipeline.py`. Does **NOT** claim the val cleanup is now
  perfectly exhaustive — the `FFHQ_four`/`FFHQ_megvii_four` base-index overlap
  (1,236 stem collisions, 0 exact-pixel) remains unresolved and is a separate,
  lower-severity, pre-existing issue outside this task's declared scope. Does
  **NOT** claim full 5-epoch checkpoint reselection was verified for any arm —
  only best-vs-last (2 of 5 snapshots per arm) was re-scorable without
  retraining, because the original recipe only persists those two states.
  Does **NOT** rebuild the sd2.1 corpus or any split that draws from it — only
  a reference manifest was produced. Does **NOT** touch Layer2's own val
  saturation defect (`v811_layer2_val.txt`, a separate open item).
- **Status**: Complete. All four tasks executed. No git commit. No
  self-approval of anything (nothing was proposed for promotion). Two items
  explicitly flagged for human decision: (a) whether to rename the production
  Layer1 checkpoint/CLAUDE.md shorthand from "SBI" to "SBIAUG" for clarity,
  (b) none for Task 1's substantive selection question — it resolved cleanly
  with no flip.

---

## F1F2-AUDIT-20260821: Alibaba identity-overlap probe (F1) + orphan-register staleness repair (F2)

- **Phase**: Documentation-consistency audit (no training, no new candidate).
- **Purpose**: Resolve two flagged-but-unresolved documentation questions:
  (F1) whether Alibaba filter data (`FFHQ_ali_process`) is identity-disjoint
  from training data, at the level of "different photo, same person" (not the
  pixel-content overlap P1-R11 already measured); (F2) reconcile three
  disagreeing v8.11 release docs on the Alibaba 98.1% figure's evidence status.
- **F1 method**: Checked for existing FFHQ identity-clustering infrastructure
  (none found — `AIGuard/arcface_identity_baseline.py` and
  `AIGuard/identity_sanity_check.py` both target Celeb-DF-v2 video identities,
  not FFHQ; FFHQ itself carries no identity ground truth). Ran a supplementary,
  explicitly non-validated ArcFace (`insightface` buffalo_l, already used
  elsewhere in this project) cosine-similarity probe: 400 `FFHQ_ali_process`
  samples vs. 1,200 training-relevant FFHQ/AIGuard samples (300 each from
  `FFHQ_megvii_four_process`, `FFHQ_four_process`, `filter_data/clean_output`,
  `AIGuard/real`). Script + full ranked output:
  `results/research/f1f2_audit_20260821/f1_identity_overlap_probe.py` /
  `f1_identity_probe_results.json`.
- **F1 result**: bulk best-match cosine similarity 0.16-0.29 (empirical
  non-match noise floor for this domain); 2.75% (11/400) exceed cosine 0.4,
  top two (0.968, 0.955) both matching `filter_data/clean_output` derivatives
  — plausibly re-detecting the already-known 23.5% pixel-content overlap
  (P1-R11), not new information. Mid-tier (cosine 0.3-0.7, ~5-8% of sample)
  is genuinely ambiguous — could be true identity overlap, coincidental
  facial similarity, or a heavily-filtered variant of an already-pixel-matched
  pair — and **cannot be disambiguated with any data this project has**
  (no FFHQ identity ground truth to validate any threshold against).
- **F1 verdict**: **CANNOT BE DETERMINED WITH AVAILABLE DATA** for the strict
  identity-level question. The supplementary probe is reported as
  context/a future starting point, not as a resolving measurement. This is
  independent of, and does not restore, the original 2026-08-02 "index range
  disjoint ⇒ cross-identity" claim, which remains refuted (index-range
  non-overlap does not imply content or identity non-overlap — already proven
  false for content by P1-R11, and never valid as identity evidence to begin
  with).
- **F2 method**: Read all three conflicting docs in full
  (`docs/releases/v8.11_production/ORPHAN_AND_UNVERIFIABLE_REGISTER.md`,
  `RELEASE_RESULTS.md`, `EVALUATION_INTEGRITY_REPAIR.md`), compared file
  mtimes against content, and independently re-opened and verified the JSON
  backing file `RELEASE_RESULTS.md` cites for the 98.1% number (not just
  trusted the citation).
- **F2 result**: `ORPHAN_AND_UNVERIFIABLE_REGISTER.md` mtime is 2026-08-13
  11:42; the P0 repair's backing file
  (`results/releases/v8.11_production_20260813/alibaba_filter_ood_v811d_layer2v811_20260813.json`)
  was written at 12:07 that same day, and `EVALUATION_INTEGRITY_REPAIR.md`
  itself at 12:38 — both after the register was last saved. The register was
  an accurate snapshot when written and was simply never revisited after the
  repair landed 25-56 minutes later; it was not in genuine conflict with the
  other two docs, which post-date the repair and already agree with each
  other. The backing JSON was independently re-verified: its SHA256
  provenance hashes match `RELEASE_RESULTS.md`'s cited hashes exactly, and
  its `overall.recall_pct` (98.071, from 20,743/21,151) rounds to the cited
  98.1%.
- **F2 verdict**: `RELEASE_RESULTS.md` and `EVALUATION_INTEGRITY_REPAIR.md`
  are authoritative and correct; `ORPHAN_AND_UNVERIFIABLE_REGISTER.md` (and,
  found during the same check, `REPRODUCTION_COMMANDS.md`, same 11:4x mtime)
  were stale. Both annotated in place (append-only — no existing text deleted
  or reworded) with the timeline above and a pointer to the now-resolved
  status; `RELEASE_RESULTS.md`/`EVALUATION_INTEGRITY_REPAIR.md` needed no
  changes.
- **Claim**: F1 is honestly unresolvable with current project data — no
  identity ground truth exists for FFHQ, and no fabricated proxy is put
  forward as a substitute. F2 is fully resolved — the three-way disagreement
  was a staleness bug (one doc not updated after a later repair), not a
  genuine factual conflict, and the 98.1% figure's backing file is
  independently confirmed genuine.
- **Non-claim**: Does **NOT** claim the ArcFace probe's mid-tier candidates
  are confirmed identity matches. Does **NOT** change any approved decision,
  gate verdict, or production checkpoint. Does **NOT** claim
  `REPRODUCTION_COMMANDS.md`'s annotation was explicitly requested by the F1/F2
  task — it was added for consistency with the other two corrected docs, same
  append-only convention.
- **Status**: Complete. No git commit. Full findings:
  `results/research/f1f2_audit_20260821/F1F2_AUDIT_FINDINGS.md`.

---

## P2-R3: `artifact_classifier_v3` whitening type-classification diagnosis + fit/eval-disjoint fix candidate

- **Phase**: Phase 2 (explainability — filter-TYPE classifier, downstream of Layer1/2)
- **Purpose**: Diagnose why `artifact_classifier_v3.pth` scores whitening=6% on
  `fake_filter_hard_neg/whitening` (`results/phase2_composite_filtertype_accuracy_v1_20260813.json`,
  P2-2), and reconcile against CLAUDE.md's unrelated "whitening 91.9%" number
  (a different classifier's different metric — Layer1/2 hierarchical filter
  recall, not this classifier's type accuracy).
- **Model checkpoint**: `artifact_classifier_v3.pth` (production, read-only,
  diagnosed only) + a fine-tuned NOT-promoted candidate
  `checkpoints/research/p2_artifact_whitening_20260821/artifact_classifier_v3_whitediv_candidate.pth`.
- **Train source (candidate fine-tune only)**: `filter_data/` (unchanged 3
  classes, 2,500/class) + whitening 4,100 total = 2,500 original
  `filter_data/whitening` + 800 `fake_filter_hard_neg/whitening` (excluding
  the 50 used for eval) + 800 `FFHQ_ali_process/Whitening_30`.
- **Validation/Test source**: (a) `fake_filter_hard_neg/whitening` held-out
  50 (the exact original P2-2 eval set), (b) `FFHQ_ali_process/Whitening_60`+
  `90` in full (n=6,000, strength never in fit set), (c) True Test whitening
  (`splits/truetest_filter.txt`, n=62, never used in fitting), (d) 60/class
  held-out regression check for the 3 unchanged classes.
- **Image-disjoint from train/val?**: Yes, verified programmatically — the
  fine-tune script asserts 0 path overlap between the fit set and all three
  whitening held-out sets before training runs.
- **Source-disjoint from train/val?**: Partial — Alibaba strength-30 was in
  the fit set, strength-60/90 (same source, different strength) was the eval
  set, so that comparison is same-source/different-parameter, not fully
  independent. True Test (different source AND algorithm entirely) is fully
  independent and was never touched.
- **Participated in model selection?**: No — candidate not promoted, no
  production decision made this round.
- **Results**: `results/research/p2_artifact_whitening_20260821/WHITENING_DIAGNOSIS.md`
  (full write-up), `pure_whitening_accuracy.json`,
  `algorithm_signature_check.json` (inconclusive probe, reported for
  completeness), `finetune_whitening_diverse_results.json`.
  Baseline→candidate: composite whitening 6.0%→76.0%, Alibaba 60+90
  29.6%→88.8%, True Test whitening 56.5%→100.0%; regression on unchanged
  classes ≤3.3pp (n=60 each, eye_enlarging 98.3%→95.0%, face_reshaping
  96.7%→96.7%, smoothing 96.7%→95.0%).
- **Claim**: (1) The 6% composite number reproduces exactly and is a real
  model weakness, not a labeling/pipeline bug (folder-name routing, class-index
  mapping, and class balance were all checked and ruled out). (2) The failure
  is NOT specific to the fake+filter composite condition — a pure-filter,
  non-fake sample using a different whitening algorithm (Alibaba) already
  collapses to 23–30% with the identical dominant misroute-to-`eye_enlarging`
  failure mode, so the root cause is algorithm-specific overfitting to the one
  whitening implementation (`filters/generate_lfw_filters.py`'s skin-masked,
  blended, brightness+desaturation effect) seen during training, not
  fake-artifact interference. The fake+filter composite condition is simply
  the worst observed case because it stacks a different (cruder) algorithm on
  top of a fake base. (3) CLAUDE.md's "whitening 91.9%" is confirmed to be an
  unrelated metric (v8.17 hierarchical filter-class recall) — this classifier's
  own whitening type accuracy, measured directly for the first time on True
  Test's pure-filter whitening subset, is actually 56.5%, not 91.9%. (4) A
  targeted, algorithm-diversity fine-tune (whitening class only) recovers
  76–100% accuracy across three independent held-out conditions with small
  (≤3.3pp, n=60) regression on the other three classes, validating the root
  cause and fix hypothesis out-of-sample.
- **Non-claim**: Does NOT promote or modify `artifact_classifier_v3.pth` or
  `pipeline.py` — change proposal filed with blank Approval Record
  (`docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md`).
  Does NOT establish multi-seed robustness (single 5-epoch fine-tune run).
  Does NOT measure end-to-end pipeline impact (only `classify_artifact()`'s
  own type accuracy in isolation, matching the original P2-2 measurement's
  scope — not "how often does a fake+filter composite actually reach this
  classifier and get the wrong type label after Layer1/2's own decision").
  The spatial center-vs-border LAB-L probe attempted as direct mechanistic
  evidence was inconclusive (confounded by ordinary face/background framing)
  and is reported as such, not relied upon for the root-cause claim.
- **Status**: Diagnosis complete and reproduced. Fix candidate produced and
  validated out-of-sample but NOT promoted — pending human review of the
  change proposal.

---

## P2-R3: whitening fine-tune — multi-seed replication + expanded regression + end-to-end pipeline measurement

- **Round dir**: `results/research/p2_r3_whitening_validation_20260821/`
  (`P2_R3_VALIDATION_FINDINGS.md`, `multiseed_finetune_and_regression.py`,
  `multiseed_results.json`, `end_to_end_pipeline_eval.py`,
  `end_to_end_results.json`, `end_to_end_pure_filter_eval.py`,
  `end_to_end_pure_filter_results.json`, per-image dumps)
- **Checkpoints**: `checkpoints/research/p2_r3_whitening_validation_20260821/
  artifact_classifier_v3_whitediv_seed{42,123,2024}.pth` — 3 candidates, one
  copy explicitly labeled `RECOMMENDED_artifact_classifier_v3_whitediv_seed42.pth`.
  **Research only, none promoted; `pipeline.py`'s `ARTIFACT_WEIGHTS_PATH` and
  production `artifact_classifier_v3.pth` untouched.**
- **Purpose**: closes the three gaps the P2 whitening diagnosis round's own
  author explicitly flagged as blocking promotion (single-seed, n=60
  regression, isolated-accuracy-only — see that entry above and
  `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md` §3).
- **Checkpoint(s) evaluated**: baseline = production `artifact_classifier_v3.pth`
  (unchanged). Candidates = 3 re-runs of the exact same fine-tune recipe (5
  epochs, LR=1e-4, Adam, from production weights; whitening fit = 2,500
  `filter_data/whitening` + 800 `fake_filter_hard_neg/whitening` [excl. the
  same held-out first-50] + 800 `FFHQ_ali_process/Whitening_30`; other 3
  classes unchanged 2,500/class), seeds ∈ {42, 123, 2024}. For end-to-end
  measurement, production Layer1 (`shufflenet_v2_layer1_v817sbi.pth`) and
  Layer2 (`shufflenet_v2_layer2_v811.pth`) held fixed throughout — only the
  artifact classifier is swapped.
- **Train/val/test provenance**: identical fit-set construction procedure to
  the original round, but with a NEW fixed regression reserve (400/class,
  independent RNG seed 999999) carved out **before** any per-seed fit
  sampling and excluded from every seed's fit pool by construction. Composite
  whitening eval set extended from 50 to 550 (original 50 + new 500, both
  reserved before fit sampling) for Task 3 statistical power.
- **Image-disjoint from train/val?**: Yes — runtime assertions (0 overlap)
  checked for every seed against: composite50, composite_e2e_extra500,
  Alibaba 60/90, True Test whitening, and all 3 regression sets (400/class).
  All passed.
- **Source-disjoint from train/val?**: Alibaba strength-30 used in fit,
  strength-60/90 used for eval (same source, different parameter — weaker
  independence, same caveat as the original round). True Test and the
  regression reserve are fully independent sources/algorithms.
- **Participated in model selection?**: No — all 3 seeds' held-out results
  used only to characterize variance and pick a recommended seed by the
  least-damaging eye_enlarging regression (seed 42), not by cherry-picking
  the best whitening number.
- **Results**:
  - **Task 1 (multi-seed)**: gain replicates on all 3 seeds. Composite
    whitening (n=50/seed) 6.0%→68-74% (pooled 70.7%, n=150); Alibaba 60/90
    (n=6,000/seed) 29.6%→86.9-89.4% (pooled 88.2%, n=18,000); True Test
    whitening (n=62/seed) 56.5%→**100.0% on all 3 seeds** (pooled n=186).
  - **Task 2 (n=400/class regression, Wilson 95% CI, independent reserve)**:
    `eye_enlarging` regression is **real and larger than originally
    estimated** — 98.25% [96.4,99.2] → 92.08% pooled [90.4,93.5]
    (non-overlapping CIs), consistent on all 3 seeds (94.0/91.5/90.75%),
    roughly double the original n=60 point estimate (−3.3pp → −6.2pp
    pooled). `face_reshaping` (99.0%→99.17%) and `smoothing`
    (99.75%→99.5%) regressions are NOT significant at this n.
  - **Task 3 (end-to-end via `pl.run_single()` → `hierarchical_predict()` →
    `classify_artifact()`, production L1/L2 unchanged)** — population-dependent,
    the round's central finding:
    - `fake_filter_hard_neg` composite whitening (n=550): Layer1/2 already
      routes 547/549 (99.6%) to `fake`, not `filter`, **by design**
      (`generate_fake_filter_hard_neg.py` exists specifically so Layer1/2
      learns fake+filter composites are `fake`; CLAUDE.md's "fake+filter
      誤判" metric tracks the opposite failure). `classify_artifact()` is
      reached on only 1/549 images end-to-end. End-to-end correct: baseline
      0.0% (0/549) → candidate 0.18% (1/549) — **the original isolated
      6%→76% number vastly overstates real-world impact on this specific
      population, because the population almost never reaches this
      classifier in production.**
    - Pure whitening images (real face, no fake base — the actual population
      `classify_artifact()` serves, since it only runs after Layer1/2 says
      `filter`): benefit is large, real, consistent on all 3 seeds. True
      Test end-to-end correct 50.0%→**95.16%** (identical on all 3 seeds,
      n=62); Alibaba pure sample (n=600) end-to-end correct
      24.8%→**84.3-85.7%**.
- **Known Traps checks**: both checked and found not directly applicable in
  their usual AUROC-ranking form (this is a closed-set argmax accuracy metric
  with one fixed threshold, `ARTIFACT_UNKNOWN_THRESHOLD=0.6`, shared
  identically by baseline and every candidate — no separate threshold or
  operating-point choice being compared, no ROC curve being ranked). Task 3's
  end-to-end-vs-isolated-metric split is in the spirit of both traps
  (checking whether an isolated-metric win survives contact with the actual
  deployed decision chain) and is reported in full, including the negative
  3a result.
- **Claim**: (1) The whitening fix's isolated-accuracy gain (Task 1) is not a
  single-seed fluke — direction and magnitude replicate on 3 independent
  seeds. (2) At n=400/class, the previously-uncertain `eye_enlarging`
  regression is confirmed real, not noise, and roughly doubles the original
  small-n point estimate (Task 2). (3) The fix's real-world, end-to-end
  benefit is population-dependent: negligible for `fake_filter_hard_neg`
  composites (because Layer1/2 correctly and overwhelmingly routes that
  population away from `filter` already, by design), but large and
  consistent for pure-filter whitening images — the population
  `classify_artifact()` actually serves in production (Task 3).
- **Non-claim**: Does NOT self-approve promotion — the change-proposal
  addendum's Approval Record is left blank for human review. Does NOT claim
  the original round's diagnosis or root-cause analysis was wrong — the
  algorithm-diversity root cause and the fix's isolated-accuracy effectiveness
  both replicate. Does NOT measure end-to-end impact for the eye_enlarging
  regression (only whitening's end-to-end chain was measured; whether the
  confirmed isolated-accuracy eye_enlarging regression attenuates or
  compounds under Layer1/2 routing the way the composite-whitening gain
  attenuated is an open question for a future round if pursued). Does NOT
  claim 4x epochs or a hyperparameter sweep were tried — recipe held fixed
  intentionally to isolate the seed variable.
- **Status**: Complete. Recommendation updated from the original round's "do
  not approve as-is" to **PROMOTE WITH CAVEATS** (seed 42 recommended),
  written as a dated addendum to
  `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md`
  (original proposal text preserved unmodified). Approval Record left blank
  for human decision; production `pipeline.py` and `artifact_classifier_v3.pth`
  untouched throughout this round.

## P2-Urgent — `artifact_classifier_v4` production regression diagnosis (2026-08-21)

- **Checkpoint(s)**: `artifact_classifier_v4.pth` (production, promoted 2026-08-21;
  confirmed byte-identical, SHA256 `8ec3cf81...`, to P2-R3's
  `RECOMMENDED_artifact_classifier_v3_whitediv_seed42.pth`) vs
  `artifact_classifier_v3.pth` (pre-promotion production, used as control).
  Layer1 = `shufflenet_v2_layer1_v817sbi.pth`, Layer2 =
  `shufflenet_v2_layer2_v811.pth` (production, unchanged, both runs).
- **Train/val/test provenance**: no new training this round (inference-only
  diagnosis). Eval populations: `splits/truetest_filter.txt` (True Test pure
  filter, smoothing n=63 / face_reshaping n=62) and
  `splits/ood_filter_ali_clean_20260821.txt` (Alibaba OOD filter, n=500/type,
  seed=777, sampled with the exact same RNG call as the v4 gapfill round for
  an apples-to-apples comparison).
- **Image-disjoint?**: Yes — both eval populations are independent of
  `filter_data/` (the training pool for all 4 artifact classes) and of the
  P2-R3 fine-tune's fit sets.
- **What this round DOES establish**: (1) The isolated regression test used
  by the P2-R3 promotion decision (`filter_data/{cls}` 400-image reserve)
  measures in-distribution accuracy against the classifier's own training
  pool, NOT the True Test/Alibaba populations `classify_artifact()` actually
  serves in production — this population mismatch, not insufficient sample
  size, is why it missed a real regression. (2) Re-running the exact same
  end-to-end methodology (`run_single()`→`hierarchical_predict()`→
  `classify_artifact()`, production Layer1/2 unchanged) with v3 loaded
  instead of v4, same populations/seed, shows v3 was near-perfect on True
  Test smoothing/face_reshaping (100.0% / 95.16%) where v4 collapses
  (52.38% / 22.58%) — a genuine, newly-introduced v4 regression, not a
  pre-existing routing/OOD issue surfacing for the first time. (3) On
  Alibaba, both v3 (28.4% / 3.21%) and v4 (18.40% / 1.00%) are already poor
  — that portion IS pre-existing and not new with v4, though v4 is somewhat
  worse there too. (4) Confusion-matrix evidence: v4 systematically
  misclassifies smoothing/face_reshaping as `whitening` on Alibaba (310/500,
  405/500) — directionally consistent with the fine-tune's whitening fit set
  being ~64% larger than the other 3 classes (4,100 vs 2,500 images); v3's
  pre-existing Alibaba failure mode is systematically toward `eye_enlarging`
  instead, a different and unrelated weakness. (5) Manual per-image spot
  check (8 True Test smoothing images, direct `run_single()` calls, v4
  loaded) confirms high-confidence (0.80-0.84) misclassifications matching
  the aggregate numbers — ruled out a gap-fill-script measurement bug.
- **Non-claim**: Does NOT modify `pipeline.py` or any `.pth` file — diagnosis
  only, revert is prepared but NOT applied, left for human decision. Does NOT
  re-litigate the whitening improvement itself (P2-R3's True Test 50%→95.16%
  end-to-end whitening gain is not disputed by this round). Does NOT measure
  whether other filter types beyond smoothing/face_reshaping/whitening/
  eye_enlarging are affected (only the 4 documented artifact classes exist).
- **Status**: Complete. Verdict: v4 as currently wired into production IS
  broken for smoothing/face_reshaping (a genuine model regression, not a
  routing failure, preprocessing mismatch, or measurement-script bug), and
  net-negative across the 4 filter types when weighted by real end-to-end
  user-facing correctness. Recommends reverting `ARTIFACT_WEIGHTS_PATH` to
  `artifact_classifier_v3.pth` (one-line change, prepared, not applied).
  Full report: `results/research/p2_urgent_v4_diagnosis_20260821/DIAGNOSIS.md`.

## P2-CrossAlgo — `artifact_classifier_v3` full 4-type end-to-end cross-algorithm/cross-base-image diagnosis (2026-08-21)

- **Checkpoint(s)**: `artifact_classifier_v3.pth` (production, unchanged) only.
  Layer1 = `shufflenet_v2_layer1_v817sbi.pth`, Layer2 =
  `shufflenet_v2_layer2_v811.pth` (production, unchanged).
- **Train/val/test provenance**: no new training (inference-only diagnosis).
  Eval populations: `splits/truetest_filter.txt` (True Test pure filter, all
  4 types, n=62-63/type) and `splits/ood_filter_ali_clean_20260821.txt`
  (Alibaba OOD filter, n=500/type, seed=777, same RNG call as the P2-Urgent
  v3-control/v4-gapfill rounds). Extends P2-Urgent's `eval_artifact_v3_control.py`
  (which only covered smoothing + face_reshaping) to all 4 named classes.
- **Image-disjoint?**: Yes — both eval populations are independent of
  `filter_data/` (the artifact classifier's entire training pool, confirmed
  this round via direct inspection of `filter_data/clean_output/clean_paths.txt`
  to be **100% sourced from `filter_data/{smoothing,whitening,eye_enlarging,
  face_reshaping}/`, i.e. a single script `filters/generate_filter_dataset.py`
  applied to a single base-image pool `AIGuard/real/`, for all 4 classes** —
  zero training rows from any `filter_data/lfw_*` variant despite those
  directories existing, because `train_artifact_classifier_v3.py`'s class-name
  matching silently skips folder names that aren't an exact match).
- **What this round DOES establish**: (1) Full 4-type end-to-end (c) numbers
  on Alibaba: smoothing 28.4%, face_reshaping 3.2%, whitening 24.8%,
  eye_enlarging 78.8% (smoothing/face_reshaping figures reproduce P2-Urgent's
  numbers exactly; whitening/eye_enlarging are new this round). (2) Full
  4-type end-to-end numbers on True Test (same-algorithm, different base
  image LFW vs `AIGuard/real`): smoothing 100.0%, face_reshaping 95.2%,
  whitening 50.0%, **eye_enlarging 4.8%** — the last is a new and previously
  unmeasured finding for `classify_artifact()` specifically (not to be
  confused with CLAUDE.md's Layer1+2 filter-*detection* recall for
  eye_enlarging, 72-82% across versions, which is a different metric the
  task framing for this round initially conflated with type-naming accuracy;
  corrected in the report). (3) Full 8-bucket confusion matrices (4 named
  types + unknown_filter + routed_real + routed_fake + non_face) built for
  both populations. Attractor pattern is **domain-specific, not type-specific**:
  True Test's attractor is `face_reshaping` (whitening 22/62 and eye_enlarging
  41/62 collapse into it); Alibaba's attractor is `eye_enlarging` (smoothing
  210/500, face_reshaping 325/500, whitening 319/500 collapse into it) — each
  domain funnels wrong guesses toward whichever class happens to generalize
  best *in that domain*, not toward one universal class. (4) Root-cause
  hypothesis test results: **training-algorithm/base-image overfitting
  confirmed** (single script × single base-image pool for all 4 classes, see
  provenance above) but only partially explains the 4-type asymmetry (same
  same-algorithm/cross-base-image True Test population leaves
  smoothing/face_reshaping untouched while collapsing whitening/eye_enlarging);
  **geometric-vs-photometric visual similarity partially confirmed** as
  explaining confusion *direction* (eye_enlarging and face_reshaping are both
  subtle geometric warps and confuse into each other; qualitatively consistent
  with P1-R16/P1-R17's independently-observed "geometric-vs-photometric gap"
  in the unrelated Layer2 context — descriptive analogy only, not a shared
  mechanism claim); **confidence-threshold/unknown_filter abstention refuted**
  as the primary driver (unknown_filter never exceeds 11.4% of any
  type/population; the dominant failure mode is confident wrong-class guesses,
  not abstention); **boring bugs (class-index order, label mapping, eval-script
  aggregation) refuted** via direct code inspection + per-image manual
  cross-check — `ARTIFACT_CLASSES` order matches training exactly, `ARTIFACT_TAG_MAP`
  is an identity mapping, no bug found in production code (the one
  "bug" found was in this round's own task framing, which cited a Layer1+2
  metric as if it were a `classify_artifact()` baseline; corrected in the
  report body). (5) Structural-pattern cross-reference: this round's failure
  shape ("single base-image/algorithm training source → domain-specific
  attractor collapse on any other source") is qualitatively similar to
  P1-R14's (`## P1-12`) rigorously-quantified Layer2 "corpus-shortcut" finding
  (corpus-classification AUROC 0.989-0.9995 vs filtered-vs-real AUROC
  0.476-0.581) and to the long-standing Shadow filter-recall domain gap
  (~15-28% vs True Test ~91-94%) — but this round did **not** run an
  equivalent corpus-AUROC-style direct measurement of what
  `classify_artifact()` is actually keying on, so the cross-level analogy is
  reported as "same *shape* of structural weakness observed at 3 independent
  pipeline levels" (Layer1 base-image gap, Layer2 P1-R14 corpus-shortcut,
  and this round's artifact-type collapse), explicitly **not** claimed as
  "proven same root cause" — evidence strength differs materially between
  P1-R14 (direct AUROC quantification) and this round (code-provenance +
  attractor-pattern observation only).
- **Non-claim**: Does NOT modify `pipeline.py` or any `.pth` file — diagnosis
  only. Does NOT re-litigate the P2-Urgent v3/v4 comparison (uses v3 only,
  as production's current state post-diagnosis, pending human revert decision).
  Does NOT claim the Layer1/Layer2/artifact-type structural analogy shares a
  literal root cause or any shared code/weights — analogy is at the level of
  observed failure *shape*, explicitly flagged as weaker evidence than P1-R14's
  own within-level finding. Does NOT propose or implement a fix (diagnosis +
  recommendation only).
- **Status**: Complete. Verdict: `classify_artifact()` type-naming accuracy is
  unreliable for any filter photo whose generation algorithm and/or base-image
  source differs from the classifier's single training source
  (`AIGuard/real` + `filters/generate_filter_dataset.py`) — this affects ALL
  4 types, not just whitening (the previously-diagnosed case) or
  smoothing/face_reshaping (the v4-regression case), and is a pre-existing
  property of v3 itself, independent of the v4 regression already under
  human review. Recommends treating this as a training-data-construction
  problem requiring multi-source retraining across all 4 classes with
  end-to-end (not in-domain-reserve) validation on every future candidate,
  rather than a per-type patch. Full report:
  `results/research/p2_artifact_crossalgo_20260821/CROSSALGO_DIAGNOSIS.md`.

## P2-DataFix — `artifact_classifier` training-data construction bug fix + integrity audit + retrain candidate `v5` (2026-08-21)

- **Checkpoint(s)**: NEW candidate `checkpoints/research/p2_artifact_datafix_20260821/
  artifact_classifier_v5.pth` (SHA256 `9596fb50212a8f87000c8bca7971502fbae8fbf
  853ac79cc7ad6357af88f10ce`). `artifact_classifier_v3.pth` (production)
  untouched, read-only throughout. Layer1/2 (`shufflenet_v2_layer1_v817sbi.pth`
  / `shufflenet_v2_layer2_v811.pth`) untouched, out of scope this round.
  `pipeline.py` untouched — `ARTIFACT_WEIGHTS_PATH` still points at v3.
- **Train/val/test provenance**: new training script `AIGuard/
  train_artifact_classifier_v5.py` (does not overwrite v3's script). Merges
  7 source `clean_output/clean_paths.txt` files: original `filter_data/`
  (4 classes, AIGuard/real base, 25,213 rows) + `lfw_whitening` (4,034,
  newly cleaned this round) + `lfw_face_reshaping` (3,984, newly cleaned) +
  `lfw_eye_enlarging` (4,243, newly cleaned) + `lfw_eye_enlarging_s110/s125/
  s135` (4,168/4,277/4,304, pre-existing clean_output reused unchanged).
  Total pool 50,223 → 80/10/10 stratified split (`random_state=42`, unchanged
  from v3). Same architecture/hyperparameters as v3 (ShuffleNetV2 x1.0, 15
  epochs, LR 1e-3, CosineAnnealingLR) except one evidence-based addition:
  inverse-frequency class weighting on CrossEntropyLoss, justified by the
  corrected pool's 3.8x class imbalance (eye_enlarging 46.7% vs smoothing
  12.4% of pool) — more extreme than the 64% imbalance that caused the
  documented `artifact_classifier_v4` production collapse (see change
  proposal `20260821_p2_artifact_whitening_diversity.md` §7).
- **Image-disjoint?**: Yes, verified by decoded-pixel SHA256 (not path/stem,
  per Known Trap #3) — 0 overlap between the 50,223-image corrected training
  pool and both True Test filter (n=249) and Alibaba clean (n=16,183/16,175
  readable). Cross-checked against this session's other cleaned splits: 2,802
  path-level overlap with `splits/v811_layer1_val_clean_20260821.txt`
  confirmed **pre-existing** (identical to what v3 already shared with that
  split, not newly introduced by this round's fix) — flagged, not fixed
  (Layer1/2 out of scope). Shadow-v2 confirmed disjoint by corpus (VGGFace2
  vs LFW/AIGuard-real), no re-hashing needed.
- **Root cause (two-layered, more precise than the CrossAlgo round's framing)**:
  (a) `filter_data/lfw_whitening`/`lfw_face_reshaping`/`lfw_eye_enlarging`
  had NEVER been through Step1(`clean_dataset.py`)+Step2(`face_attr_filter.py`)
  cleaning — confirmed via mtime comparison: the cleaning run that produced
  `filter_data/clean_output/clean_paths.txt` predates these folders'
  creation entirely, so they were never scanned, not merely filtered out
  by class-name matching. (b) Even after cleaning, `train_artifact_classifier_
  v3.py`'s `cls in CLASS_MAP` exact-string match would still silently skip
  `lfw_*`-prefixed and `_s110/_s125/_s135`-suffixed folder names. Both layers
  fixed: (a) ran the project's standard 2-step cleaning on the 3 previously-
  uncleaned folders (same parameters used everywhere else in the project);
  (b) replaced exact matching with a generic `normalize_class()` rule
  (strip `lfw_` prefix, strip `_s\d+` suffix) — not a hardcoded per-folder
  alias table.
- **Diversity composition per class** (Task 2.1, mandatory before training):
  3/4 classes (whitening, face_reshaping, eye_enlarging) now have 2
  independent base-image sources (AIGuard/real + LFW); eye_enlarging
  additionally has 4 scale variants. **`smoothing` remains single-source**
  (no `filter_data/lfw_smoothing` has ever been generated anywhere in this
  project) — this is a pre-existing DATA GAP distinct from the class-matching
  bug this round fixed, explicitly NOT solved, flagged for future work.
- **What this round DOES establish (Task 4, end-to-end validation through
  `pl.run_single()` → `hierarchical_predict()` → `classify_artifact()`, exact
  same methodology/population/seed=777 as the CrossAlgo round's v3 baseline
  for apples-to-apples comparison)**: **mixed result, NOT a uniform
  improvement across all 4 types.**
  - True Test (n=62-63/type): whitening 50.0%→**91.9%** (+41.9pp, 95% Wilson
    CI non-overlapping, real) and eye_enlarging 4.8%→**72.6%** (+67.7pp, CI
    non-overlapping, real) — these are the two classes the bug fix directly
    targeted, and the fix demonstrably works for the same-algorithm/
    cross-base-image population. face_reshaping flat (95.2%→93.6%, CI
    heavily overlapping). **smoothing regressed significantly**
    (100.0%→**74.6%**, −25.4pp, CI non-overlapping, real, NEW problem not
    present in v3) despite smoothing's own training data being completely
    unchanged (same 6,233 images, same single source) — hypothesized
    (NOT proven, no representation-level verification done) to be
    photometric-type confusion (smoothing vs whitening, mirroring the
    diagnosis round's geometric-vs-photometric framework for eye_enlarging/
    face_reshaping) induced by whitening's dramatically improved, more
    sensitive representation now competing for the same photometric
    decision space.
  - Alibaba (n=500/type): all 4 types' deltas fall within overlapping 95%
    Wilson CIs (smoothing +5.0pp, face_reshaping +1.8pp, whitening +0.4pp,
    eye_enlarging +2.2pp) — **no statistically significant change in either
    direction**, and 3/4 types remain critically poor (5.0%-33.4% correct).
  - Domain-specific attractor pattern (CrossAlgo round's core finding):
    **True Test attractor substantially weakened but not eliminated** —
    v3's `face_reshaping` attractor (66.1% max single-direction
    misclassification rate) is gone in v5, replaced by a much smaller new
    `whitening` attractor (17.5% max, smoothing→whitening). **Alibaba's
    `eye_enlarging` attractor is essentially unchanged** (62.4%-71.0% vs
    v3's 63.8%-65.0%; one direction, face_reshaping→eye_enlarging, actually
    got 6pp worse) — confirms the CrossAlgo diagnosis's "second factor"
    (cross-algorithm generalization gap, independent of base-image
    diversity) is real and NOT solved by this round's fix, which only added
    diversity within this project's own generation-algorithm family (still
    zero non-self-produced filter algorithms in training).
- **Recommendation**: NOT approved as-is. Net effect is a real trade-off
  (fixes 2 severely broken True Test classes, introduces 1 new True Test
  regression, leaves the more production-relevant cross-algorithm gap
  untouched), requiring human judgment rather than an unambiguous promote/
  reject call. Change proposal with BLANK Approval Record:
  `docs/team/change_proposals/20260821_p2_artifact_datafix_candidate.md`.
  Full report: `results/research/p2_artifact_datafix_20260821/
  DATAFIX_FINDINGS.md`.

---

## P2-CompleteFix — `artifact_classifier` smoothing base-image gap (Gap 1) +
smoothing-regression root cause & fix (Gap 2) + train-time augmentation for
cross-algorithm generalization, negative result (Gap 3) (2026-08-21)

- **Checkpoint(s)**: NEW candidate `checkpoints/research/
  p2_artifact_completefix_20260821/artifact_classifier_v6.pth` (SHA256
  `56b4e399475d95366dffea296420d706b91405c437febf23c3b88fec552cfaac`) —
  **recommended for review**. Also produced but NOT candidates: `v6_aug.pth`
  (Gap 3 augmentation arm, negative result, SHA256
  `d3e5627a05e8eac63ea1eaba6d779db8d2e28019919ce7fd0e27de995f99050e`),
  `d1_weighttest.pth` / `v6_fullweight.pth` (Gap 2 diagnostic/attribution
  arms only). `artifact_classifier_v3.pth` (production) untouched, read-only
  throughout. Layer1/2 untouched, out of scope. `pipeline.py` untouched.
- **Gap 1 (smoothing had no LFW base-image source)**: fixed. New script
  `filters/generate_lfw_smoothing.py` reuses the EXISTING `apply_smoothing`
  (imported from `filters/generate_filter_dataset.py`, not reimplemented)
  and the EXISTING LFW-candidate-collection/True-Test-exclusion logic
  (imported from `filters/generate_lfw_filters.py`). Generated 6,000 raw,
  cleaned via the project's standard 2-step pipeline (Step1 82.1% kept =
  4,926; Step2 closed_eye/sunglasses/baby/no_face → **4,032 final**, same
  order of magnitude as whitening (4,034) / face_reshaping (3,984) /
  eye_enlarging (4,243)).
- **Integrity gate (mandatory, run before training)**: candidate pool 54,255
  images, decoded-pixel SHA256 overlap vs True Test filter (n=249) = **0**,
  vs Alibaba clean (n=16,183/16,175 readable) = **0**. Path overlap vs
  Layer1 val clean split unchanged at 2,802 (100% pre-existing from v3/v5,
  0 newly introduced by `lfw_smoothing`). All 4 classes now have 2
  independent base-image sources; class imbalance shrank from v5's 3.8x
  (eye_enlarging 46.7% vs smoothing 12.4%) to 2.3x (eye_enlarging 43.2% vs
  smoothing/face_reshaping/whitening ~18.7-19.2% each, now near-balanced).
- **Gap 2 (v5's smoothing regression, root-caused with a controlled
  experiment, not just a hypothesis)**: v5's ONLY deviation from v3 was
  full inverse-frequency class weighting (smoothing got the highest weight,
  2.014, being the minority class) — candidate mechanisms were (a) the
  weighting formula itself over-amplifying smoothing's loss and hurting
  cross-base-image generalization, or (b) genuine representation
  competition with the now much-more-diverse whitening data. **Diagnostic
  D1** (`train_artifact_d1_weighttest.py`): v5's EXACT data pool (no
  lfw_smoothing), only the weight formula changed to sqrt-damped
  (`n/(C·n_i))**0.5`, smoothing weight 2.014→1.419) — True Test smoothing
  74.6%→**82.5%** (+7.9pp, 95% CI [71.38,89.96] overlaps v5's
  [62.66,83.72], directionally real but not independently significant at
  n=63), whitening/eye_enlarging gains preserved. **Confirms (a) is a real
  contributing factor but not the whole story** (17.5pp gap to v3's 100%
  still unexplained by weighting alone). **Candidate v6**
  (`train_artifact_v6.py`) combines Gap 1 data + the sqrt-damped formula
  (which, on the now-more-balanced Gap-1 pool, computes to near-equal
  weights 0.76-1.16 across all 4 classes) — True Test smoothing **fully
  recovers to 100.0%** (63/63, CI identical to v3, non-overlapping with
  v5's 74.6%). **Attribution arm `v6_fullweight`** (Gap 1 data + v5's
  ORIGINAL exponent=1.0 formula, isolating "does data alone suffice"): True
  Test smoothing **also fully recovers to 100.0%** with data alone (weight
  formula unchanged from v5's). **2×2 verdict: Gap 1 (data) is the primary
  and sufficient driver** — v5→D1 (weight-only change, data held fixed)
  only partially recovers smoothing (74.6%→82.5%, CI overlapping, not
  independently significant); v5→v6_fullweight (data-only change, weight
  formula held at v5's original exponent=1.0) **fully** recovers it
  (74.6%→100.0%). Once data is fixed, `v6` (sqrt weight) and
  `v6_fullweight` (full weight) are statistically indistinguishable from
  each other on every type in both True Test and Alibaba (all CIs
  overlapping) — the weight-formula choice that seemed critical in the
  original v5 hypothesis turns out not to matter once the underlying data
  gap is closed. `v6` (sqrt-damped) is still the recommended candidate
  (more conservative, lower risk of amplifying any future class imbalance)
  but `v6_fullweight`'s results are filed as a directly comparable
  alternate baseline, not discarded.
- **Known Traps checks**: **Trap #3** (content-key disjointness): PASSED,
  full decoded-pixel SHA256 run (see integrity gate above). **Trap #5**
  (regression check must use the production-serving population, not the
  training-source pool): PASSED — Gap 2's diagnostic AND the final
  candidate were both validated exclusively through
  `pl.run_single()→hierarchical_predict()→classify_artifact()` on True Test
  / Alibaba, never on `filter_data/{cls}` reserve accuracy (which stayed
  ~98-99% across v3/v5/v6/v6_aug and was explicitly NOT used as evidence
  for any promotion claim). **Trap #4** (between-group correlate ≠
  within-group causal lever): directly informed this round's design — Gap 1
  (data) and Gap 2 (weight formula) were changed one-at-a-time in isolated
  diagnostic arms (D1: weight-only; v6_fullweight: data-only vs v6:
  data+weight) specifically so the round would not conflate "both changed
  together and it got better" with "we know which one did it".
- **End-to-end validation (Task 4, `pl.run_single()`→`hierarchical_predict()`
  →`classify_artifact()`, same methodology/population/seed=777 as the
  CrossAlgo/DataFix rounds, v3→v5→v6 full trajectory reported)**:
  - True Test (n=62-63/type): **v6 ≥ v3 on all 4 types, zero regressions.**
    smoothing 100.0%→74.6%(v5)→**100.0%**(v6, fully recovered, CI identical
    to v3). face_reshaping 95.2%→93.6%(v5)→**95.2%**(v6, flat vs v3).
    whitening 50.0%→**90.3%**(v6, +40.3pp vs v3, CI non-overlapping, real).
    eye_enlarging 4.8%→**72.6%**(v6, +67.7pp vs v3, CI non-overlapping,
    real, identical to v5).
  - Alibaba (n=500/type): all 4 types' v6-vs-v3 deltas fall within
    overlapping 95% Wilson CIs (smoothing 28.4%→28.2%, face_reshaping
    3.2%→6.4% borderline non-significant improvement, whitening
    24.8%→23.6%, eye_enlarging 78.8%→79.6%) — **no statistically
    significant change either direction; the cross-algorithm attractor
    pattern is untouched by Gap 1+2** (expected, since neither touches
    algorithm diversity).
- **Gap 3 (train-time augmentation for cross-algorithm generalization,
  genuinely attempted, NEGATIVE result)**: `train_artifact_v6_aug.py`, a
  SEPARATE experimental arm on top of v6's exact data/weights (isolating
  the augmentation delta), added 5 independent perturbation axes designed
  BLIND to any Alibaba image (RandomResizedCrop(0.80-1.0 scale),
  RandomAffine(±8°, translate 0.04, scale 0.92-1.08 — directly targeting
  this project's fixed-parameter geometric warps), stronger ColorJitter
  (0.35/0.35/0.3/0.04 vs v6's 0.2/0.2), random GaussianBlur(p=0.25),
  random JPEG re-encode (p=0.3, quality 55-95)). **Result: Alibaba got
  significantly WORSE on 3/4 types** — smoothing 28.2%→**10.6%** (CI
  [8.2,13.61] non-overlapping with v6's [24.43,32.3]), face_reshaping
  6.4%→**1.8%** (CI non-overlapping), whitening 23.6%→**11.2%** (CI
  non-overlapping) — while eye_enlarging rose 79.6%→**89.4%** (CI
  non-overlapping, but for the WRONG reason: the other 3 types'
  misclassification-into-eye_enlarging rate rose across the board,
  e.g. smoothing→eye_enlarging 176/500→346/500). **Mechanism: augmentation
  amplified the pre-existing class-size-driven "eye_enlarging attractor"
  (43.2% of the training pool) rather than teaching an algorithm-invariant
  representation** — under increased input noise, the classifier defaults
  more, not less, to its largest/most-robust class. True Test
  face_reshaping also declined (95.2%→85.5%, CI [74.66,92.17] borderline
  overlapping [86.71,98.34]). **`v6_aug` is explicitly NOT promoted, NOT a
  candidate.** This closes "stronger blind train-time augmentation" as a
  lever for this specific gap, on top of P2-DataFix's prior closure of
  "more base-image diversity within this project's own generation-algorithm
  family" — both now-tested levers fail to move Alibaba; what remains
  untested is training on genuinely algorithm-diverse filter sources
  (non-self-produced, Alibaba itself must stay held-out) or domain
  adaptation techniques, neither of which this project currently has
  ready.
- **Recommendation**: `v6` is the first candidate in this sub-line to
  achieve a uniform True-Test improvement (all 4 types ≥ v3) with Alibaba
  unchanged (no significant regression on any type) — proposed for review.
  `v6_aug` (Gap 3) is explicitly rejected, documented as a genuine,
  informative negative result. Change proposal with BLANK Approval Record:
  `docs/team/change_proposals/20260821_p2_artifact_completefix_v6.md`. Full
  report: `results/research/p2_artifact_completefix_20260821/
  COMPLETEFIX_FINDINGS.md`.

---

## MOBILE-EXPORT-20260822: v8.17 production stack re-export to TFLite (Layer1 v817sbi + Layer2 v811 unchanged + Artifact classifier v6, first-ever mobile export)

- **Phase**: Deployment/infrastructure (no training, no new candidate model —
  format conversion of three already-approved production checkpoints).
- **Purpose**: The mobile TFLite export at `results/mobile_export/` was last
  built for the OLD stack (`shufflenet_v2_layer1_v811d.pth` +
  `shufflenet_v2_layer2_v811.pth`, 2026-08-11). Production has since changed
  twice: Layer1 → `shufflenet_v2_layer1_v817sbi.pth` (2026-08-20, see
  `docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md`) and
  Artifact classifier → `artifact_classifier_v6.pth` (2026-08-22, see
  `docs/team/change_proposals/20260821_p2_artifact_completefix_v6.md`). The
  artifact classifier had **never** been exported to mobile format before —
  this closes that gap and re-validates the whole stack against today's
  production `pipeline.py` paths.
- **Method**: `results/mobile_export/v817_20260822/export_layer1_v817sbi.py`
  re-uses `export_mobile_tflite.py`'s unmodified `export_one()` (same pattern
  as the one-off P1-R9 candidate export) against the production checkpoint
  path. `confirm_layer2_v811.py` re-verifies G3 (load) and G4 (numeric match)
  of the pre-existing, byte-unchanged Layer2 export rather than re-exporting
  from scratch, then copies the confirmed-valid files into the new folder.
  `export_artifact_v6.py` is a new script (architecture check first: plain
  `torchvision.models.shufflenet_v2_x1_0()` + `Linear(1024,4)`, confirmed via
  `pipeline.py`'s `build_artifact_model()`, no FFT branch / no DFT ops, so
  `mobile_fft.py` is not needed) that imports `build_artifact_model()` from
  `pipeline.py` and `real_image_batch()` from `export_mobile_tflite.py`, and
  reimplements the same G1-G4 gate protocol (not parameterized in the
  original script). `benchmark_v817_stack.py` then runs the full 3-stage
  TFLite chain vs the full PyTorch chain over the complete True Test Set
  (769 images), not just the 8-image per-model smoke sample.
- **Result**: All 3 models pass G1-G4 (max|Δprob| 2.7e-7 to 2.0e-6, 2-4
  orders of magnitude under the 1e-3 tolerance; argmax identical on every
  sample). Full-chain, full-True-Test decision agreement TFLite vs PyTorch:
  **769/769 (100%)** final label match, **298/298 (100%)** artifact sub-type
  match on filter-predicted images. Recall/accuracy reproduce existing
  approved numbers exactly on both backends (fake 99.63%, filter 91.97%,
  real 72.40%, artifact-type accuracy 90.36%). Sizes: Layer1+Layer2 fp32
  20.91 MB (apples-to-apples with the prior 20.913 MB, unchanged); full
  3-model stack 25.75 MB (**new figure — never measured before**, since the
  artifact classifier was never in the export before this round). Latency:
  Layer1+Layer2-only apples-to-apples re-measurement 16.72 ms/image (prior:
  14.37 ms/image, ~2.35 ms higher — flagged as likely desktop CPU load
  variance given identical model architectures, not re-run on an idle
  machine to confirm); full 3-stage average over True Test's real class mix
  15.68 ms/image; worst-case (every image pays all 3 stages) 22.97 ms/image.
- **Claim**: The current production 3-checkpoint stack is provably
  TFLite-deployable end-to-end (not just "a file got produced" — genuinely
  loads via `tf.lite.Interpreter` and reproduces PyTorch decisions at
  full-dataset scale, the strongest verification this project has done for
  any mobile export so far). The artifact classifier required no FFT-branch-
  style equivalent reformulation (it has no FFT branch to begin with).
- **Non-claim**: Does **NOT** re-litigate fp16/int8 viability for Layer1/
  Layer2 (architecture-level, already root-caused 2026-08-11, unchanged by a
  weights-only checkpoint swap) or newly validate them for the artifact
  classifier (a float16 file was incidentally produced by the standard
  `onnx2tf` call but not gate-verified — not claimed as deployable). Does
  **NOT** resolve whether the Phase 1 Freeze Gate's "≤25 MB" mobile-size
  threshold was intended to cover the artifact classifier or only Layer1+
  Layer2 — both readings (20.91 MB core classifier only, still passes; or
  25.75 MB full filter-capable stack, 0.75 MB/3% over) are reported, left for
  reviewer decision, see report §5. Does **NOT** claim the 16.72 ms
  Layer1+Layer2 latency figure is a confirmed regression vs the prior
  14.37 ms — flagged as probable measurement noise, not verified on an idle
  machine. Does **NOT** change any production checkpoint or `pipeline.py`
  (read-only on both, per task constraint).
- **Status**: Complete. No git commit. Full report:
  `results/mobile_export/v817_20260822/EXPORT_AND_VERIFY_REPORT.md`. Desktop
  demo (loads all 3 `.tflite` files, runs 8 real True Test images through
  both PyTorch and TFLite chains side by side, 8/8 match):
  `results/mobile_export/v817_20260822/desktop_tflite_demo.py`.

---

## P1-16: P1-R19 — seed-replication check of P1-R18's G50 Shadow regression; **`INCONCLUSIVE`**

- **Round dir**: `results/research/p1_r19_g50_seedcheck_20260822/`
  (`P1_R19_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `analysis_p1_r19.json`,
  per-seed training/gates logs and manifests)
- **Checkpoints**: `checkpoints/research/p1_r19_g50_seedcheck_20260822/`
  `layer2_p1_r19_G50_s{20260822,20260823,20260824,20260825}.pth` (4 new;
  `G50` at seed 20260821 reused read-only from P1-R18; `G0`/R75 at all 5
  seeds reused read-only from P1-R16 (seeds 20260821/20260822) and P1-R17
  (seeds 20260823/20260824/20260825) — **research only, none promoted**
- **Purpose**: P1-R18 found (single seed 20260821, explicitly flagged
  unconfirmed) that the frozen primary Shadow set's overall filter recall
  dropped significantly under `G50` relative to `G0` (20.43%→15.05%,
  -5.38pp, paired-bootstrap CI excluding 0), and recommended a seed
  replication of G50 specifically before treating the regression as a
  stable property of the intervention rather than single-seed noise. This
  round runs that replication.
- **Design**: G50 only (G100 out of scope, task brief). 4 new seeds
  (20260822/23/24/25) chosen to exactly match the 5-seed pool P1-R17 already
  used to replicate G0/R75, giving a fully paired seed-matched comparison
  and requiring zero G0 retraining. Training recipe, G50 counter-row split,
  init checkpoint, val split, and frozen Layer1 held byte-identical to
  P1-R18; only the RNG seed varies. Evaluation restricted to the `shadow`
  and `stressdev` gate blocks only (the two the primary Shadow metric
  needs) — full Freeze-Gate A battery out of scope this round.
- **Image-disjoint from train/val?**: Yes — no new training or evaluation
  data created this round; the G50 split is P1-R18's byte-identical,
  already-audited file, and the Shadow set is the same frozen,
  previously-audited primary set every prior round in this lineage used.
- **Source-disjoint from train/val?**: Same as P1-R18/R17/R16's R75/G50
  (unchanged).
- **Participated in model selection?**: No. Epoch selection used only the
  unchanged in-domain val split (best-val-macro-F1); the Shadow metric plays
  no role in checkpoint selection, only in this round's post-hoc analysis.
- **Reproduction / validation**: all 4 new checkpoints independently
  verified on disk before analysis: 363 tensors, zero NaNs, sha256 matching
  their own training manifests, correct recorded seed, `shadow_n=279`
  sanity check passed for every seed. One training run (seed 20260825) was
  interrupted mid-run by a session limit; the partial, non-conforming
  checkpoint (epoch-1 selection from an incomplete 5-epoch run, no
  manifest, no eval) was discarded rather than reused, and the seed was
  fully retrained from scratch before any number was computed.

### 可宣稱結論

1. **P1-R18's single-seed G50 Shadow regression does not replicate at
   anywhere near its original magnitude**: the 4 new seeds' paired deltas
   vs G0 are `[-1.08, +0.36, -0.36, -0.36]`pp — roughly 4-15x smaller than
   the original `-5.38`pp finding, and none individually significant (all
   4 new seeds' per-seed paired-bootstrap CIs include 0).
2. **Seed-level mean delta across all 5 seeds = -1.36pp, 95% Student-t
   interval (n=5, df=4) = [-4.22, +1.49]** — straddles zero. Per the
   pre-declared three-way interval rule this is **`INCONCLUSIVE`**: not
   `REGRESSION_CONFIRMED` (interval not entirely negative) and not
   `REGRESSION_REFUTED` (interval does include negative values; 4/5 seeds
   directionally negative).
3. **G0 itself has a 5.73pp seed-to-seed spread** (range 14.70-20.43% across
   its own 5 already-published seeds, reused read-only from P1-R16/P1-R17)
   — nearly as large as the effect P1-R18 attributed to the intervention at
   a single seed. This context was not visible in P1-R18's single-seed
   framing and is the main reason a -5.38pp draw is not, in hindsight, an
   extreme outlier for this recipe.
4. Every per-seed value for both G0 and G50, across all 5 seeds, remains
   above frozen production's 13.26% floor (P1-R17 Table 2) — at no seed
   does either arm regress below the pre-intervention baseline.

### 不可宣稱事項

- 不可宣稱退步已被否證（refuted）——區間下界為負（-4.22），5 個 seed 中有 4
  個方向為負，不能排除殘留 1-2pp 真實效果的可能性；`REGRESSION_REFUTED`
  需要區間下界 ≥0，本輪未達到。
- 不可宣稱退步已被證實（confirmed）——區間上界為正（+1.49），未達到
  `REGRESSION_CONFIRMED` 所需「整個區間都在 0 以下」的條件，即使方向計數
  （4/5 為負）條件有滿足。
- 不可宣稱本輪對 G100 有任何結論——本輪 scope 明確排除 G100。
- 不可宣稱本輪重新驗證過 Freeze-Gate A——只跑了 `shadow` 與 `stressdev` 兩個
  gate block，因此**不論本輪 verdict 為何，都不能從本輪證據單獨做出任何
  promotion 決定**（且本專案的既有規範本來就不允許本輪 promote 任何東西）。
- 不可宣稱本輪重啟或推翻了 P1-R18 在幾何增益主要端點（pooled Shadow-v2 S2B
  geometric recall）上的 `NO_GEOMETRIC_GAIN` 判定——本輪只處理次要的 Shadow
  退步問題。
- 不可宣稱更多 seed 數必然能把區間解析成確定方向——本輪的 4 個新 seed 數是
  任務開始前預先承諾、結果出來前未曾修改的數字，未追加第 5、6 個新 seed。

### Status

**Research result only — nothing promoted.** No change proposal filed (round
verdict is `INCONCLUSIVE`, not a `PROMISING_CANDIDATE` or any verdict that
would trigger one under this lineage's standing rules). No fix attempted
even though the regression could not be excluded — task brief scoped this
round to confirm-or-refute only. All frozen files (`pipeline.py`, both
production Layer1s, production Layer2, `artifact_classifier_v6.pth`, all
P1-R16/17/18 checkpoints and per-image dumps) untouched throughout. No git
operation was run.

---

## P1-17: P1-R20 — first architecture-level (not data-mixing) interventions for the Layer2 corpus shortcut: DANN (`PARTIAL`) vs explicit feature de-correlation (`FAIL`)

- **Round dir**: `results/research/p1_r20_domain_adversarial_20260822/`
  (`P1_R20_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `analysis_p1_r20_seeds.json`,
  `frontier_analysis.json`, per-seed training/gates/shadowv2 logs and manifests)
- **Checkpoints**: `checkpoints/research/p1_r20_domain_adversarial_20260822/
  layer2_p1_r20_{dann,decorr}_s{20260822,20260823,20260824}_{taskonly,full}.pth`
  (6 mechanism-seed pairs, `_taskonly` strips the auxiliary domain head so the
  checkpoint loads unmodified into the existing `DualBranchModel` class —
  **research only, none promoted, none applied to `pipeline.py`**)
- **Purpose**: P1-R14 through P1-R19 attacked the Layer2 corpus-shortcut /
  Shadow OOD gap (P1-R14's diagnosis: Layer2's fake-vs-filter score separates
  photographic corpora, AUROC 0.989-0.9995, and is near-chance filtered-vs-
  clean-real *within* a corpus) exclusively via training-data mixing
  (counter-rows at various doses and geometric augmentations). None produced
  a robust, promotable fix. This round tests two mechanistically different
  architecture-level levers per the project lead's explicit instruction to
  try architecture changes, not more data variants: (1) DANN, gradient-
  reversal domain-adversarial training; (2) explicit statistical
  de-correlation between a task-relevant and a domain-relevant feature
  subspace (a scoped, simplified version of the CrossDF/DID idea,
  arXiv:2310.00359v3, cited in `TODO.md` since P1-R7/R14 discussions but never
  implemented).
- **Scope check (mandatory before any training cost)**: `TODO.md` §G2/F2
  records that P1-R13 screened a `grl` (DANN) candidate for a *different*
  problem (True-Test in-domain read-out geometry, not the Shadow OOD gap) and
  killed it pre-training using a `|cos(u,n)|` collinearity screen — a screen
  P1-R13 itself retracted in the same round (Known Trap #4). DANN had
  therefore never been genuinely trained in this project; proceeding was
  judged not disqualified. Full reasoning: `PRE_DECLARED_PROTOCOL.md` §0.
- **Design**: both mechanisms use the SAME base task data (byte-identical
  reuse of P1-R14's `CTRL` arm split, 146,425 rows) plus 12,000 CelebA-train
  domain-only rows (no task label, domain loss only) added specifically to
  avoid a structural degeneracy: in the existing data, corpus and class are
  the same partition (every filter row is LFW/FFHQ-aligned, every fake row is
  AIGuard-video/DF40-crop), so a domain-invariance objective drawn only from
  that data would be forced to fight the task objective. CelebA-train is
  verified 0-filename-overlap with `celeba_test` (Freeze-Gate A eval set) and
  deliberately NOT any Shadow/Shadow-v2 base photography (using the eval
  domain's own corpus unlabeled would leak eval style into training).
  3 seeds per mechanism (20260822/23/24) — chosen because P1-R19 measured
  this exact recipe's own seed-to-seed Shadow-recall spread at 5.7pp (n=5),
  making single-seed readings explicitly untrustworthy in this line.
  Interval-based pre-declared decision rule (SUCCESS requires seed-mean
  Shadow-recall gain ≥5pp AND entirely-positive 95% t-interval AND zero
  Freeze-Gate A breach AND no trap#2 regression AND ≥5/9 threshold-only
  frontier budgets), written before any checkpoint was trained.
- **Result — DANN = `PARTIAL`**: frozen primary Shadow set (dev-threshold-
  matched, n=279 pairs), all 3 seeds positive vs `CTRL`
  (+2.51/+2.15/+4.30pp), 95% seed-level t-interval `[+0.12, +5.85]pp`
  entirely above zero (statistically real). Threshold-only frontier: 7/9
  matched budgets above the frozen production frontier, every seed.
  Shadow-v2 S2B (1,114 pairs, properly powered): every filter type improved
  at every seed (+4.3 to +8.1pp overall vs frozen production's 15.35%).
  Freeze-Gate A: zero breaches, any seed (True Test fake 99.63%/filter
  91.97%, AIGuard-unseen AUROC 0.841-0.851, CelebA 99.33%, StyleGAN2 99.57%,
  Alibaba 97.71-97.74%, stress 2.93-3.32%). Trap#2 (AIGuard-unseen low-FPR):
  TPR@FPR1%/5% IMPROVED vs production at every seed (0.046-0.065/0.356-0.444
  vs production's 0.037/0.324) — no regression, unlike P1-R14's `C1` arm
  which failed exactly this trap. **Falls short only of the pre-declared
  +5pp magnitude bar** (mean +2.99pp) — set specifically below P1-R19's
  measured 5.7pp seed-noise floor so a passing mean would be distinguishable
  from noise. First architecture-only lever in the P1-R14→R20 chain to move
  Shadow filter recall in the right direction with zero cost anywhere.
- **Result — de-correlation = `FAIL`**: all 3 seeds negative vs `CTRL`
  (-4.66/-3.58/-4.30pp), 95% t-interval `[-5.54, -2.82]pp` entirely below
  zero (real regression, not noise). Threshold-only frontier: 0/9 every
  seed. Shadow-v2 S2B flat-to-worse on every type. A genuine, reproducible
  negative result: forcing an explicit domain-relevant subspace and
  decorrelating the task subspace from it removes some of the corpus-linked
  signal the model currently relies on for harder OOD cases, without
  supplying a replacement.
- **Consequences / status**: DANN candidates flagged for the project lead's
  personal review only (per the standing constraint from the
  `artifact_classifier_v4` incident) — not applied to `pipeline.py`, not
  self-approved, no change proposal filed (`PARTIAL` does not clear this
  lineage's promotion bar). Next steps if pursued: `w_domain` magnitude
  sweep (fixed at 0.3 a priori this round, untuned), possible stacking with
  P1-R14's `C1` labeled-target-domain data (untested), minimum 3 additional
  seeds before any promotion discussion. De-correlation, as scoped here, is
  not recommended for further investment without first explaining why the
  removed corpus-linked signal isn't replaced.

### Status

**Research result only — nothing promoted, nothing applied to `pipeline.py`.**
No change proposal filed. `pipeline.py` and both production checkpoints
(`shufflenet_v2_layer1_v817sbi.pth`, `shufflenet_v2_layer2_v811.pth`)
re-hashed at round end and confirmed unchanged (`frozen_hashes_end.txt`,
layer1 sha256 `e3057270...` matches the published production value). All new
artefacts under `results/research/p1_r20_domain_adversarial_20260822/`,
`checkpoints/research/p1_r20_domain_adversarial_20260822/`,
`splits/research/p1_r20_domain_adversarial_20260822/`. No existing split,
result, or checkpoint modified. No git operation was run.

---

## P1-18: P1-R21 — DANN `w_domain` strength sweep: no strength promotable, effect shrinks (not scales) with strength, 4x is the first outright safety `FAIL` in this DANN line

- **Round dir**: `results/research/p1_r21_dann_strength_sweep_20260822/`
  (`P1_R21_FINDINGS.md`, `PRE_DECLARED_PROTOCOL.md`, `analysis_p1_r21_seeds.json`,
  `frontier_analysis.json`, per-seed training/gates/shadowv2 logs and manifests;
  `gates_w030_*`/`perimage_w030_*`/`shadowv2_w030_*` are read-only copies of
  P1-R20's `dann_s{seed}` outputs, not new training)
- **Checkpoints**: `checkpoints/research/p1_r21_dann_strength_sweep_20260822/
  layer2_p1_r21_{w015,w060,w120}_s{20260822,20260823,20260824}_{taskonly,full}.pth`
  (9 new strength-seed pairs; the 1x point, `w030`, reuses P1-R20's
  `layer2_p1_r20_dann_s{seed}_taskonly.pth` unmodified — not retrained —
  **research only, none promoted, none applied to `pipeline.py`**)
- **Purpose**: direct follow-up to P1-16 (this registry's P1-R20 entry,
  above), which found DANN gives a real but sub-bar Shadow-recall gain
  (+2.99pp mean, 95% CI `[+0.12,+5.85]pp`) at a single untuned
  `w_domain=0.3`, and named a `w_domain` magnitude sweep as the cheapest next
  step. This round is that sweep: `w_domain ∈ {0.15, 0.30(reused), 0.60,
  1.20}` (0.5x/1x/2x/4x), 3 seeds each, mechanism (GRL, schedule, domain-head
  shape, 19-domain CelebA-train-only-bucket split) and training data
  byte-identical to P1-R20 (hash-verified before training). De-correlation
  (P1-R20's M2, `FAIL`) was not swept — only DANN.
- **Result**: seed-mean Shadow-recall delta vs CTRL is **monotonically
  decreasing in strength, then negative**: w015=+3.82pp
  (95% CI `[+2.46,+5.18]pp`, tightest interval in this entire research line)
  → w030=+2.99pp (=P1-R20's own result) → w060=+0.60pp (CI crosses zero) →
  **w120=-0.36pp (CI crosses zero, and Shadow point estimate is net
  negative)**. No strength clears the pre-declared +5pp PRIMARY bar; none
  clears this round's own honestly-separate +4pp SECONDARY "promising, needs
  more seeds" tier either (w015 misses by 0.18pp, the closest of any cell).
  **w120 (4x) additionally breaches the mandatory trap#2 (AIGuard-unseen
  low-FPR) tolerance on 3/3 seeds** — TPR@FPR=5% regresses up to -12.96pp
  absolute vs production, the first genuine safety-relevant regression this
  DANN line has produced across two full rounds. Freeze-Gate A: zero
  breaches at any of the 12 strength-seed cells (True Test fake/filter,
  AIGuard-unseen AUROC, CelebA, StyleGAN2, Alibaba, fake+filter stress all
  pass at every cell). Shadow-v2 S2B: every strength improves over frozen
  production (15.35%) at every seed — direction never reverses on this
  secondary check even where the primary metric does.
- **Consequences / status**: no strength promoted; w015 flagged as the
  best-characterized DANN candidate to date (tightest interval, zero safety
  cost, best S2B/frontier record) but explicitly below both promotion tiers
  and, per this round's hard constraint, not self-approved regardless —
  flagged for the project lead's personal review only. w120 judged `FAIL`
  outright (safety cost with no compensating gain). The round also surfaces,
  without adopting, a proposed alternative reading of the +5pp bar
  (interval-exclusion vs point-estimate magnitude as the operative criterion
  — `P1_R21_FINDINGS.md` §8) for the project lead to accept or reject.

### Status

**Research result only — nothing promoted, nothing applied to `pipeline.py`.**
No change proposal filed. `pipeline.py`, `shufflenet_v2_layer1_v817sbi.pth`
(sha256 `e3057270...`, matches published production value), and
`shufflenet_v2_layer2_v811.pth` (sha256 `8470ad52...`, matches every training
manifest's `init_sha256` this round) verified unchanged before and after this
round — all three read-only throughout. All new artefacts under
`results/research/p1_r21_dann_strength_sweep_20260822/`,
`checkpoints/research/p1_r21_dann_strength_sweep_20260822/`. P1-R20's
directory was only read from (perimage/gates/shadowv2 JSON copied, not
moved or modified). No existing split, result, or checkpoint modified. No
git operation was run.

---

## P2-R4: Fake-class explanation faithfulness QA framework -- baseline + Grad-CAM++ named-region candidate

- **Phase**: Phase 2 (XAI / explanation validation track). Round directory:
  `results/research/p2_fake_explanation_qa_20260822/`, full report
  `FAKE_EXPLANATION_QA_FINDINGS.md`.
- **Purpose**: `phase2_design_review_20260821` found the fake-class
  explanation is a single hardcoded sentence for every fake prediction
  (`TEMPLATES["ai_generated"]`, `regions=[]` always), with its correctness
  never validated by any test. Build a reusable faithfulness-testing
  framework (ablation/deletion + content-controlled comparison), measure the
  current production behavior against it, then design and test a concrete
  lightweight candidate (Grad-CAM++ named-region conditioning) using the same
  framework.
- **Training performed**: none. Inference-only evaluation of the current
  production checkpoint pair, imported directly from `pipeline.py`.
- **Model checkpoints**: `shufflenet_v2_layer1_v817sbi.pth` +
  `shufflenet_v2_layer2_v811.pth` (current production, `pl.MODEL_VERSION =
  "v8.17"`), resolved automatically via `pipeline.LAYER1_WEIGHTS_PATH` /
  `LAYER2_WEIGHTS_PATH` (not hardcoded in this round's scripts).
- **Test sources and sizes**:
  - Main population (n=444 correctly-classified-fake, up from the superseded
    2026-08-14 audit's n=150/v8.11d): `aiguard_unseen` (147),
    `stylegan2_ood` (150), `truetest_df40` (147) -- 150 sampled per source,
    independent seed from any prior round.
  - FF++ content-controlled pairs (n=447 real/fake pairs, 237 true-positive
    fake + 194 false-positive real): Deepfakes/FaceSwap/NeuralTextures
    (Face2Face excluded, `DETECTION_INSUFFICIENT_NO_CLAIM` per the existing
    B2 detection gate), `stage2_pairing_audit.csv` `PAIRED_OK` rows. Real-side
    coverage extended from 120/390 to 388/390 targets by extracting 268
    additional real frames from `youtube_c23` raw videos using
    `extract_ffpp_frames.py`'s exact methodology (imported, not
    reimplemented).
- **Image-disjoint from train/val?**: All three main-population sources are
  established held-out/eval-only sets per `CLAUDE.md`'s dataset table
  (`AIGuard/unseen`, `stylegan2_test/fake`, `splits/truetest_fake.txt`); FF++
  is not in any training split for either checkpoint (Tier D external
  evaluation only, per `docs/xai_evidence_schema.md`).
- **Results**:
  1. **Baseline 1 (current production fixed sentence)**: 296/296
     independently-sampled correctly-fake images produce a byte-identical
     explanation string (entropy = 0 bits), verified by directly calling
     `pl.build_explanation()`, not assumed from reading the code. Content-
     controlled test (FF++) confirms the same string is emitted for 237 true
     positives and 194 false positives alike -- the text carries zero
     information about whether the manipulation claim is actually correct.
     Independent check of the template's "texture" wording: Laplacian-
     variance texture proxy (`pl.compute_skin_stats()`, reused) separates
     real (n=300, mean 620.1) from fake (n=300, mean 400.3) with AUROC=0.2942
     (Mann-Whitney p=2.6e-18) -- a real, sizeable effect (partially supports
     "texture" wording, direction = fake images measurably smoother), but
     this is a between-population, unpaired comparison (Known trap #4
     exposure -- not a within-group causal test, and not a claim the
     classifier's own decision uses this specific statistic).
  2. **Baseline 2 (raw Grad-CAM++, continuous top-k% masking)**: refreshed
     the 2026-08-14 audit (n=150, v8.11d, superseded) at n=444 on current
     production. All 9 (source x k) cells pass deletion faithfulness
     (bootstrap 95% CI lower bound > 0 for both hot-bottom and hot-random),
     same direction/magnitude as the superseded round -- reproduces, does not
     newly establish, the underlying finding.
  3. **Part 3 candidate (Grad-CAM++ top-2 named `FACE_REGIONS` boxes ->
     `suspicious_regions` + conditioned sentence)**: passes the SAME
     ablation faithfulness test at the discrete (named-region) resolution
     on all 3 sources (n=444) -- masking the claimed 2 boxes drops fake
     confidence significantly more than masking the 2 least-activated boxes
     or 5 position-matched random controls. **But fails region diversity
     severely**: top-1 claimed region is `nose` in 438/444 (98.65%) of the
     main population, and independently reproduces at 91.7-98.6% across all
     3 FF++ methods (n=237) regardless of true manipulation type (Deepfakes/
     FaceSwap = whole-face swap vs NeuralTextures = mostly mouth) --
     structurally the same "always answers nose" collapse this project's
     Qwen2-VL SBI pilot and `region_head` five-round comparison both hit
     independently. On the 194 FF++ false positives (unmanipulated real
     photos wrongly called fake), the candidate still confidently names a
     specific region (most commonly `nose+right_eye`) for every one, since
     Grad-CAM++ has no "no region" / low-confidence output channel -- a
     concrete overclaiming case, not hypothetical. High region-vs-GT-mask
     overlap (84.9-89.8% across the 3 methods) is not read as localization
     precision: `nose` sits near frame-center and Deepfakes/FaceSwap masks
     cover most of the face, the same "found the face, not the manipulation"
     artifact `p2_r1_tierA_localization_20260821` already documented for
     whitening.
- **Claim**: (1) The current production fake-class explanation conveys zero
  per-image information and is invariant to whether the underlying
  manipulation claim is actually correct, verified directly rather than
  assumed. (2) Baseline 2's deletion-faithfulness pass for raw Grad-CAM++
  reproduces on 444 held-out images on current production, up from n=150 on
  a superseded checkpoint. (3) The Grad-CAM++ named-region candidate passes
  ablation faithfulness at the discrete resolution the text would actually
  use, on 444 held-out EFS-ish images and 237 independent FF++ true
  positives, but its named-region claim is dominated by a single region
  (`nose`, 91.7-98.65%) across 4 independent content sources/samples and
  therefore does not deliver the "per-image, non-constant" claim the
  candidate was designed to provide -- this is a genuine negative result, not
  underpowered evidence (4 independent replications of the same collapse).
- **Non-claim**: Does NOT claim the discrete-region ablation faithfulness
  result is wrong or an artifact -- it is real and reproduced across sources,
  it just does not translate into a useful per-image text claim given the
  region-diversity collapse. Does NOT claim the texture-proxy AUROC finding
  means the classifier's own decision uses that statistic (unpaired,
  between-population; Known trap #4 not fully resolved here). Does NOT
  extend or narrow FF++ Tier D's existing approved scope (c23/`PAIRED_OK`/
  correctly-fake/mask-coverage limits carry over unchanged, this round adds
  no new Tier D approval). Does NOT measure false-positive rate on any
  population other than the FF++ real targets (43.4%, n=447) -- this is not
  claimed to generalize to AIGuard/unseen, StyleGAN2, or True Test real
  populations, which were not measured for false-positive rate in this
  round.
- **Consequences / status**: **No change proposal filed.** The candidate did
  not clear the bar of a genuine, cost-free improvement (Part 3 verdict:
  passes faithfulness, fails the diversity/overclaiming requirement that
  motivated it), so per the task brief's explicit instruction, this round
  reports the negative result honestly rather than forcing a proposal.
  `pipeline.py`, all checkpoints, `splits/`, and all pre-existing `results/`
  files were not modified. New files added: this round's scripts/manifests,
  plus 268 new real-frame JPEGs under this round's own output folder (not
  written into the shared `FaceForensics_frames/` tree).

## P2-R5: Fake-class explanation FIX round -- 4 region-selection mechanisms (causal ablation / center-bias correction / contrastive-vs-real / causal-effect abstention) + confidence+texture text-conditioning fallback

- **Phase**: Phase 2 (XAI / explanation validation track). Round directory:
  `results/research/p2_fake_explanation_fix_20260822/`, full report
  `FAKE_EXPLANATION_FIX_FINDINGS.md`. Follows directly from P2-R4 above.
- **Purpose**: P2-R4 found the Grad-CAM++ named-region candidate collapses to
  "always nose" (91.7-98.65% mode) and overclaims 100% on FF++ false
  positives. This round tests the root-cause hypothesis (CNN center bias),
  implements and evaluates 4 genuinely different region-selection mechanisms
  against it, then builds and validates a non-region text-conditioning
  fallback.
- **Training performed**: none. Inference-only evaluation of the current
  production checkpoint pair, imported directly from `pipeline.py`.
- **Model checkpoints**: `shufflenet_v2_layer1_v817sbi.pth` +
  `shufflenet_v2_layer2_v811.pth` (current production, unchanged, `pl.
  MODEL_VERSION = "v8.17"`).
- **Test sources and sizes**: Main population n=295 correctly-classified-fake
  (`aiguard_unseen`/`stylegan2_ood`/`truetest_df40`, fresh independent seed
  from P2-R4's n=444 and this round's own n=444 Task 0 sample). Second
  independent population: FF++ `PAIRED_OK` pairs, n=237 true-positive fake +
  n=194 false-positive real (same `stage2_pairing_audit.csv` / real-frame
  coverage as P2-R4, reused not regenerated). Root-cause check (Task 0):
  n=444 correctly-fake (fresh sample) + n=260 correctly-real
  (`aiguard_real` 60 + `celeba_real` 200).
- **Image-disjoint from train/val?**: Same held-out/eval-only sources as
  P2-R4 (see that entry); `celeba_test` (real baseline for Fix C / Task 0) is
  the established CelebA OOD real-eval pool per `CLAUDE.md`'s dataset table.
- **Results**:
  1. **Root cause confirmed (Task 0)**: averaged Grad-CAM++ over n=444
     correctly-fake and, separately, n=260 correctly-real images -- BOTH
     average maps peak at the identical pixel (112,112), the crop's exact
     geometric center, inside the `nose` box. Different model output
     (Layer2 "fake" vs Layer1 "real"), different images, same architecture
     -> the peak is `spatial_branch.conv5`'s Grad-CAM++ receptive-field
     geometry, not fake-specific content signal.
  2. **Fix A (causal/ablation-based selection, 8 extra forward passes/image,
     measured 67.27ms mean added latency)**: the only one of 4 mechanisms
     that passes discrete ablation faithfulness on ALL 3 main-population
     sources AND the pooled FF++ population (Cohen's d 0.78-0.88 pooled,
     bootstrap 95% CI lower bound > 0 in every cell). Diversity improves
     substantially over the P2-R4 baseline candidate (top-1 mode fraction:
     main pop 98.98%->54.92%, FF++ 95.36%->31.22%; entropy ratio 0.06->0.73
     main pop, 0.27->0.85 FF++) but nose remains the plurality mode -- does
     NOT fully eliminate the center-bias collapse, only reduces it.
  3. **Fix B (center-bias-corrected: subtract Task 0's averaged fake-CAM
     baseline) and Fix C (contrastive: subtract averaged real-CAM baseline)**:
     diversity improves MORE than Fix A on the main population (entropy
     ratio 0.98/0.98) but **faithfulness FAILS on 2/3 main-population
     sources** (aiguard_unseen, truetest_df40 -- bootstrap 95% CI lower
     bound <= 0 for hot-minus-bottom and/or hot-minus-random), confirming
     the task brief's predicted risk: debiasing removed real signal along
     with the artifact. Only passes on `stylegan2_ood` and pooled (propped
     up by that one source's large effect).
  4. **Fix D (Fix A + causal-effect-size abstention gate, threshold
     calibrated on an INDEPENDENT population)**: TP-vs-FP Mann-Whitney AUROC
     on the best single-region ablation drop = 0.5402 (p=0.1512, not
     significant) -- the gate cannot selectively abstain on false positives
     without abstaining an equal or greater fraction of true positives (at
     the calibration population's median threshold, FF++ TP claim-rate
     drops to 11.4%, FP claim-rate to 7.2% -- both nearly wiped out
     together, not selectively). Also found FF++'s mean effect size (0.017)
     is ~7x smaller than the calibration population's (0.124), a new
     quantification of the project's known FF++/c23 domain gap via a causal-
     effect-size lens.
  5. **100% false-positive overclaiming persists across ALL 4 mechanisms**:
     on the 194 FF++ real-but-misclassified-fake frames, baseline, Fix A,
     Fix B, and Fix C each confidently name a specific region for every
     single one -- none has any "no region" / abstain output channel that
     actually discriminates true from false positives (see Fix D above).
  6. **Texture heuristic re-tested with a proper paired design (Task 3)**:
     P2-R4's AUROC=0.2942 was cross-population (Known trap #4 exposure).
     This round used FF++'s 447 same-source-video real/fake pairs (within-
     subject, controls for camera/compression): 76.06% of pairs have the
     fake frame's texture_var below its OWN paired real frame's
     (Wilcoxon signed-rank p=1.67e-27, paired Cohen's d=-0.52) -- upgrades
     the texture claim from "cross-population correlate" to "within-subject
     effect", but heterogeneous by method (Deepfakes 87.3%, NeuralTextures
     95.3%, **FaceSwap 45.6% ~ null** -- FaceSwap grafts a real face's own
     texture, so no synthesis-smoothing effect is expected there).
  7. **Diffuseness axis rejected (Task 4)**: CAM top-20%-mass concentration
     proxy is itself near-constant on the FF++ TP/FP population (std=0.034,
     zero images in the "concentrated" tier out of 431, TP-vs-FP
     AUROC=0.4951) -- the same degenerate-signal failure mode as region
     collapse, honestly excluded rather than used to manufacture fake
     text variation.
  8. **Text-generation fallback validated (Task 5)**: confidence-tier (3
     bins from `hierarchical_predict`'s existing composite probability) x
     measured-texture_var (existing `compute_skin_stats()` /
     `_SMOOTH_TEXTURE_THR=210`, conditioned per-image not asserted
     unconditionally) candidate, NO named region. n=431 FF++
     fake-predictions: 4 distinct strings, entropy=1.4796 bits (vs current
     production's 0 bits). Strictest available content-controlled check
     (152 same-source-video pairs where BOTH frames were predicted fake):
     34.87% of pairs get different text (65.13% identical) -- neither a
     constant-collapse (100%) nor pure noise decoupled from measured values
     (0%).
- **Claim**: (1) Grad-CAM++'s "always nose" collapse is architecture-level
  center bias (peak coincides for fake-explaining and real-explaining
  passes on disjoint images), not fake-specific signal -- directly measured,
  not inferred. (2) Of 4 genuinely different region-selection mechanisms
  implemented and evaluated (ablation-causal, center-bias-subtraction,
  contrastive-vs-real, causal-effect-abstention), exactly one (Fix A)
  passes faithfulness robustly across both independent populations, and it
  only partially fixes diversity (nose remains plurality) and does not
  reduce the 100%-false-positive-overclaiming rate at all. (3) None of the
  4 mechanisms clears the bar of "meaningfully better than current global-
  only fake explanation, without new risk" -- this is a genuine, 4-way-
  replicated negative result for region-level fake-class explanations on
  this architecture, not underpowered evidence. (4) The confidence+measured-
  texture text-conditioning fallback IS a genuine, evidence-backed, cost-
  free improvement over the current 0-bit constant sentence, with no new
  overclaiming risk (never names a region).
- **Non-claim**: Does NOT claim Fix A is "usable" or "recommended" despite
  passing faithfulness -- faithfulness passing was necessary but not
  sufficient; the diversity/overclaiming shortfalls are treated as
  disqualifying, consistent with P2-R4's bar. Does NOT claim the FaceSwap
  null texture result generalizes beyond FF++'s 3 Tier-D methods to other
  face-swap-style manipulation techniques. Does NOT claim Fix D's finding
  rules out ANY causal-effect-size-based abstention design on a population
  with a smaller domain gap than FF++/c23 -- only tested on FF++. Does NOT
  extend or narrow the FF++ Tier D approved scope from P2-R4. Does NOT
  claim real-device latency for Fix A's 67ms/image figure -- measured on
  the GPU-available dev environment only.
- **Consequences / status**: **One change proposal filed** (text-generation
  fallback only): `docs/team/change_proposals/
  20260822_p2_fake_explanation_text_variation.md` -- **PROPOSED, not
  approved, not applied, Approval Record left blank.** No region-selection
  change proposal filed for any of Fix A/B/C/D (none cleared the bar, same
  disposition as P2-R4's candidate). `pipeline.py`, all checkpoints,
  `splits/`, and all pre-existing `results/` files (including P2-R4's) were
  not modified. New files confined to this round's own output folder plus
  the one change-proposal markdown file.

## P2-R6: Follow-up verification round -- production-stack re-verification (Task A), FF++ Face2Face Status-C addendum (Task B), fake-explanation methodology write-up (Task C)

- **Phase**: Phase 2 (XAI / explanation validation track + production
  verification). Round directory:
  `results/research/p2_followup_verify_20260822/`, full report
  `FOLLOWUP_FINDINGS.md`. Three independent sub-tasks, all read-only against
  production checkpoints; no training performed.
- **Task A -- large-scale re-verification of the full production stack**
  (Layer1 `shufflenet_v2_layer1_v817sbi.pth` + Layer2
  `shufflenet_v2_layer2_v811.pth` + artifact classifier
  `artifact_classifier_v6.pth`, plus today's two code changes: `EMPIRICAL_
  FILTER_REGIONS` swap (P2-R2) and `build_fake_explanation()` (P2-R5,
  applied today with an emergency `UnboundLocalError` fix in `run_single()`
  moving `image_np_for_stat` computation earlier/unconditionally)):
  - n=565 images run end-to-end through `pipeline.py`'s actual
    `run_single()`, sampled across `AIGuard/real` (90), `AIGuard/fake` (90),
    DF40 sd2.1/DiT/SiT/ddim/pixart (25 each = 125), `filter_data/`'s 4 types
    (30 each = 120), `lfw` (70), `celeba_test` (70).
  - **0 crashes, 0 exceptions, 0 malformed outputs** (no null/empty
    explanation, no null suspicious_regions, no leftover pre-P2-R2 region
    names) across every branch reached: real (197), fake (242), filter
    (121), non_face (5, correctly gated). Filter sub-types all reached
    including 1 unknown_filter edge case.
  - Fake-class explanation: 4 distinct strings observed (of the
    theoretically possible 6 = 3 confidence tiers x 2 texture branches),
    entropy=1.4011 bits on this larger/more representative n=242 sample
    (vs today's earlier n=33 smoke test's 2 distinct strings) -- confirms
    the texture branch is genuinely reachable at scale. The >=0.90 "high
    confidence" tier was NEVER observed across all 242 fake predictions in
    this sample (max composite confidence = 0.8732) -- reported as an
    observation about reachability in normal operation, not a bug (the
    tier logic itself is correct and would fire given a high enough
    `hierarchical_predict()` composite probability).
  - **JSON schema validation: 565/565 (100%) FAIL** against
    `docs/structured-output.schema.json`. Root cause, confirmed by direct
    `jsonschema.validate()` testing, not inference: the schema's
    `additionalProperties: false` does not list `image` or `class_probs`
    in its `properties`, both of which `run_single()` always emits --
    every single output is rejected on this basis alone, independent of
    prediction class. A second, independent violation also exists: the
    schema requires `confidence` to be `type: number` with no null
    allowed, but the `non_face` branch legitimately returns
    `confidence: null` -- would fail even if the `additionalProperties`
    issue were fixed. Confirmed via `git diff` that
    `docs/structured-output.schema.json` IS a genuine uncommitted
    working-tree edit made earlier today (added `model_version`,
    `non_face` enum, `unknown_filter`, `EMPIRICAL_FILTER_REGIONS` names --
    real, substantive progress), but the `image`/`class_probs`/null-
    confidence gaps were not part of that edit and remain unresolved. This
    is also independently already a known, previously-tracked issue --
    `TODO.md`'s F5 section already carries the note that
    `docs/structured-output.schema.json` has not matched the actual
    schema-2.1.0 output since 2026-08-11 -- so today's partial schema
    update did not close that pre-existing gap, it only updated the
    enum/const values while leaving the structural
    (`additionalProperties`/nullable-`confidence`) gaps untouched.
    **Flagged as the highest-priority finding per task instructions; NOT
    fixed this round (read-only constraint; `pipeline.py` untouched,
    schema file untouched).**
  - Filter artifact_types distribution observed: eye_enlarging 44,
    whitening 28, smoothing 27, face_reshaping 21, unknown_filter 1.
- **Task B -- FF++ Face2Face Status-C inclusion addendum**: read both
  `docs/team/change_proposals/20260819_fake_xai_status_c_upgrade_ffpp.md`
  (APPROVED 2026-08-20 for Deepfakes/FaceSwap/NeuralTextures) and
  `results/phase2/ffpp_detection_gate_v817sbi_20260820/
  DETECTION_GATE_RESULTS_V817SBI.md` (Face2Face crosses the 60% detection
  gate under current production Layer1 v817sbi: 56.7%->68.0%, +8.0pp
  margin; full Stage 4/4b passes at all 3 mask fractions, a stricter
  record than the already-approved FaceSwap). Re-hashed both checkpoints
  independently (e3057270.../8470ad52...) and confirmed they match current
  production. Checked `results/research/contamination_cleanup_20260821/
  CLEANUP_AND_RETEST_REPORT.md` (one day newer than the Gate report) -- no
  new contamination found that touches the FF++ evidence pool; flagged one
  unrelated, lower, non-comparable "FF++ per-method" number in that same
  cleanup report (from a different, pre-B2-preprocessing-fix
  `FaceForensics_frames` zero-shot methodology, not the B2/`PAIRED_OK`
  population this proposal and its evidence use) as a documentation
  cross-reference risk worth noting, not a contradiction. **Appended a new
  addendum section to the existing approved proposal file** (did not alter
  the pre-existing approved body text) with the evidence summary,
  suggested claim wording, and a blank Approval Record subsection per the
  task's conservative-treatment instruction (this amends an
  already-once-approved document with a filled historical approval
  record, unlike routine research findings which the project lead said no
  longer need blank-ceremony approval going forward).
- **Task C -- fake-explanation methodology formalized into `docs/
  phase2_story.md`**: appended a new dated section (two subsections)
  documenting (1) the EFS-vs-swap/reenactment policy for fake-class
  spatial explanation (established this session in P2-R4/P2-R5 above) as
  permanent, citable methodology -- not a one-off results-folder artifact
  -- with the four-mechanism failure-mode summary table and the
  production decision it supports; (2) the ablation/deletion +
  content-controlled faithfulness-testing framework
  (`p2_fake_explanation_qa_20260822/scripts/`) as reusable project
  infrastructure for evaluating ANY future explanation-generation
  candidate, with its pass/fail rule stated explicitly for reuse. Did not
  rewrite or delete any existing section; appended per the file's
  established pattern.
- **Claim**: (1) The current full production stack (Layer1 v8.17 + Layer2
  v8.11 + artifact v6 + today's two code changes) is crash-free and
  output-well-formed across a 565-image, multi-source, multi-branch
  sample -- directly measured. (2) The fake-explanation text-variation fix
  applied today is producing genuinely varied, non-degenerate output at
  scale (entropy > 0 confirmed on n=242, not just the earlier n=33 smoke
  test). (3) `docs/structured-output.schema.json` does not actually
  validate `pipeline.py`'s real output today, for two independent
  structural reasons, confirmed by direct test -- this is a real,
  currently-live gap between documentation and code, not a theoretical
  one. (4) FF++ Face2Face's evidence for Status-C inclusion is intact,
  checkpoint-matched to current production, and un-contaminated by
  anything found since 2026-08-20 -- ready for the project lead's
  decision, not yet a decision itself.
- **Non-claim**: Task A's 0-crash finding is on a 565-image sample, not
  exhaustive coverage of every possible input (e.g., corrupted files,
  extreme aspect ratios were not specifically targeted). Task A does NOT
  fix the schema mismatch -- flagged only, per the round's explicit
  read-only/no-fix-this-round instruction. Task B's addendum is NOT an
  approval -- Face2Face remains DETECTION_INSUFFICIENT_NO_CLAIM / Tier C
  (global_only) until the project lead fills the addendum's Approval
  Record. Task C's write-up does not change any production behavior --
  `pipeline.py` was not touched by Task C.
- **Consequences / status**: No training. No checkpoint, `pipeline.py`, or
  `splits/` changes. New files confined to
  `results/research/p2_followup_verify_20260822/`. Two existing docs
  appended (not rewritten): `docs/team/change_proposals/
  20260819_fake_xai_status_c_upgrade_ffpp.md` (new addendum section,
  PROPOSED/blank approval) and `docs/phase2_story.md` (new dated section).
  **Schema/output mismatch (Task A finding) surfaced to the project lead
  as the top-priority open item from this round -- needs an explicit fix
  decision, not bundled into routine TODO backlog.**

---

## PAPER-READINESS-EXECUTION-20260822: retroactive contamination audit +
FFT spatial-only ablation + FF++ protocol comparison (execution of the
paper-readiness audit's three top findings)

- **Phase**: Audit + one training round (Phase 1 evidence, cross-cutting).
  Executes `results/research/paper_readiness_audit_20260822/
  PAPER_READINESS_AUDIT.md`'s three highest-priority findings (D2, M3, D1).
  Read-only on `pipeline.py` and all production checkpoints; one genuine
  training run for Task B only. No git operations performed.
- **Checkpoint(s)**: NEW research-only checkpoints
  `checkpoints/research/paper_readiness_execution_20260822/
  {layer1,layer2}_spatial_only.pth` (FFT branch removed, retrained from
  production init). Production `shufflenet_v2_layer1_v817sbi.pth` /
  `shufflenet_v2_layer2_v811.pth` / `artifact_classifier_v6.pth` untouched,
  read-only throughout, used only for eval.
- **Task A (content-key contamination audit, extending p1_r11)**: Reused
  `audit_p1_r11_fullsplit.py`'s exact fp/dHash/NCC/MAD methodology
  (never reimplemented) to close four gaps p1_r11 (2026-08-20) left open:
  (1) Layer1 v8.17sbi's 44,594-row SBI+augreal delta on top of the
  already-audited round4 base; (2) the newer `shadow_v2a_filter`/
  `shadow_v2b_filter` gates (didn't exist at p1_r11's audit date) vs the
  round4 base; (3) Layer2 v8.11's full 126,130-row production train pool
  (never audited with this method before); (4) `artifact_classifier_v6`'s
  full 8-source candidate pool (previously only exact-SHA256 checked
  against 2 gates, now near-dup-resolved against all gates). Also added
  FakeClue test set as a brand-new gate (was never in any prior gate list).
  **Headline finding**: `shadow_v2a_filter` (1,152 images, base corpus
  `vggface2_train_sample`) is **~99-100% content-duplicated** in Layer1's
  actual production training pool (round4 alone: 1,141/1,152 confirmed,
  99.13%; delta alone independently confirms 633/1,152, 97.14%) --
  worse than the already-known StyleGAN2 (63.8%) and Alibaba (23.5%)
  contamination. Root cause matches what `TODO.md` (P2-R1 round,
  2026-08-21) had already flagged as an open item but never quantified:
  `vggface2_train_sample`'s 297 wild-real images entered Layer1's real
  class (P1-R8) then got reused as SBI fake sources (P1-R9);
  `generate_p1_r16_shadowv2.py` only asserted non-overlap with *primary*
  Shadow, never content-checked against training corpus (textbook Known
  Trap #3 shape). Layer2 is completely clean on this gate (0 confirmed --
  never saw VGGFace2). `shadow_v2b_filter` (base `vggface2_test_sample`)
  is completely clean and can substitute as uncontaminated shadow-v2
  evidence. Secondary findings (all newly quantified this round, none
  previously checked at Known-Trap-#3 rigor): True Test fake 4.07%
  (11/270, same 7 confirmed images independently flagged by BOTH Layer1
  and Layer2's separate training pools -- cross-validates the method,
  not noise); AIGuard/unseen 0.88% (4/454, same cross-validation pattern);
  FakeClue 2.33% (35/1,503, same cross-validation pattern); True Test
  real/filter and primary Shadow (`shadow_filter`/`shadow_vggface2_real`)
  and FF++ (`ffpp_frames`, 900 images) all **completely clean** (0
  confirmed on every training pool checked). `artifact_classifier_v6`'s
  pool is clean except for the already-known Alibaba contamination.
  **Not yet done** (flagged as the top follow-up): DF40 held-out leftover
  pool (sd2.1/DiT/SiT/ddim/pixart) vs its own training portion -- the
  fourth eval set named in the original task, not reached this round due
  to time budget spent on the three gaps that turned out to be more
  urgent (README labels this "three and a half of four" complete).
- **Task B (FFT spatial-only ablation)**: Genuine retrain (not
  inference-time zeroing) of both Layer1 (5-epoch fine-tune recipe from
  `train_p1_r9_layer1.py`, byte-identical minus `fft_branch` removed and
  classifier input 1280->1024) and Layer2 (15-epoch recipe from
  `train_v811_layer2.py`, same change), both spatial_branch-initialized
  from the same checkpoints production used (`shufflenet_v2_layer1_v811d.
  pth`, `shufflenet_v2_3class_v88.pth`), same train/val splits as
  production (minus 3.3%/13.9% of rows whose source images were deleted
  after their original P2 experiment round -- `v89d_candidate_pool`/
  `v89d_proxy_unseen_pool`, documented limitation, not this round's
  doing). Evaluated head-to-head against full production on True Test,
  AIGuard/unseen, and Shadow primary, with Wilson 95% CIs.
  **Finding**: every metric's 95% CI overlaps substantially between FULL
  and SPATIAL_ONLY; the point-estimate direction is inconsistent (FULL
  slightly ahead on True Test real/fake by 1.85-2.40pp, filter recall
  identical 91.97%=91.97%; SPATIAL_ONLY slightly ahead on AIGuard/unseen
  AUROC +0.0078 and Shadow balanced accuracy +2.98pp) -- the FFT branch's
  marginal contribution to the primary task is **statistically
  indistinguishable from zero** at current sample sizes, in either
  direction. Training-time macro-F1 shows FULL Layer1 (0.9781) very
  slightly ahead of SPATIAL_ONLY Layer1 (0.9734, -0.47pp) on the same val
  split. Full per-metric table in `EXECUTION_FINDINGS.md`.
- **Claim**: The dual-branch architecture's FFT contribution to the
  classification task cannot be empirically distinguished from zero given
  the evidence gathered this round -- directly relevant to whether the
  int8-blocking FFT branch (7.6e9 dynamic range) is worth its deployment
  cost. Spatial-only is a genuinely viable, more-easily-quantizable
  lightweight alternative worth naming as an option in the paper.
- **Non-claim**: Does NOT prove the FFT branch contributes exactly zero
  (absence of significance != evidence of zero effect at these sample
  sizes) -- does NOT constitute an apples-to-apples data-matched
  comparison (spatial-only trained on ~3-14% less data due to deleted
  source images, a real but judged-unlikely-to-be-decisive confound,
  flagged not resolved). Does NOT evaluate spatial-only against the full
  gate suite (CelebA/StyleGAN2/Alibaba/FF++/FakeClue/TFLite export) --
  only True Test + AIGuard/unseen + Shadow primary this round. Does NOT
  change production `pipeline.py`, which still uses the full dual-branch
  stack.
- **Task C (FF++ protocol comparison)**: Inspected `extract_ffpp_frames.py`
  and confirmed this project's FF++ usage (900 frames: 300 real + 150x4
  manipulation methods, c23 only, one middle-frame-per-video, random
  SEED=20260812 sampling from the full corpus) is an **approximation**,
  NOT the official FF++ train(720)/val(140)/test(140) video-ID split
  protocol, and has no c40 tier or multi-frame video-level aggregation.
  Explicitly documented as non-comparable to literature Table numbers
  without further work. Reused today's existing inference
  (`results/research/v817_scorecard_gapfill_20260821/
  ffpp_full_results.json`, same v8.17 production stack, same population
  -- no re-inference needed) and reformatted into the standard FF++
  paired-binary-accuracy presentation: Deepfakes 60.67%, Face2Face
  50.67%, FaceSwap 55.33%, NeuralTextures 55.78% (average 55.61%), pooled
  all-methods accuracy 51.89% (467/900). Cross-referenced against Task
  A's finding that `ffpp_frames` has zero content-key overlap with any of
  the three production training pools -- can honestly claim the training
  data is confirmed disjoint from this eval population, independent of
  the protocol-framing caveat above. No literature SOTA numbers cited
  (out of this round's scope, left as D1 follow-up).
- **Consequences / status**: No training-affecting or `pipeline.py`
  changes. New files confined to `results/research/
  paper_readiness_execution_20260822/` and two new research-only
  checkpoints under `checkpoints/research/
  paper_readiness_execution_20260822/`. `shadow_v2a_filter` contamination
  finding flagged to the project lead as the top-priority item needing an
  explicit "which past results need the ⚠️-correction treatment" decision,
  same class of decision as the 2026-08-20 StyleGAN2/Alibaba corrections.
  Full write-up: `results/research/paper_readiness_execution_20260822/
  EXECUTION_FINDINGS.md`.

---

## P2-DomainGen (folder tag `p2_r6_domaingeneralization_20260822`): metric-learning (SupCon) + domain-adversarial (DANN) architecture-level interventions for `artifact_classifier` cross-algorithm generalization — **negative, on top of two prior negative/partial rounds**

> Note: this round's output folder is named `p2_r6_domaingeneralization_20260822`
> but is UNRELATED to the earlier `## P2-R6: Follow-up verification round`
> entry above (different date, different task, different session) — do not
> conflate the two when searching this registry by "P2-R6".

- **Checkpoints**: `checkpoints/research/p2_r6_domaingeneralization_20260822/
  artifact_classifier_r6_{supcon,dann}_s{42,123}.pth` (4 candidates, 2
  mechanisms x 2 seeds). Baseline compared against: `artifact_classifier_v6.pth`
  (production `artifact_classifier`, unchanged, read-only).
- **Train/val/test source composition**: IDENTICAL data pool to `v6` -- same 8
  `clean_paths.txt` sources (54,255 images, `filter_data/{cls}` +
  `filter_data/lfw_{cls}[_sNNN]`), same split recipe/seed
  (`test_size=0.10, random_state=42` then `test_size=0.111, random_state=42`),
  same sqrt-damped inverse-freq class weights, same epochs/LR/batch size. No
  new training images were introduced this round (Known Trap #3 content-key
  audit from `p2_artifact_completefix_20260821` reused unchanged, not re-run,
  because the pool itself did not change). The ONLY variable across the 4
  candidates vs. v6 is the training loss/architecture: (A) `supcon` adds a
  supervised-contrastive auxiliary loss on the pre-fc 1024-dim embedding,
  pulling same-type/different-base-image-source samples together; (B) `dann`
  adds a gradient-reversal-layer domain-adversarial head predicting a 2-way
  base-image-source proxy (`AIGuard/real`-direct vs. LFW-derived), forcing the
  shared embedding to NOT be linearly separable by that proxy. Both saved
  checkpoints are architecturally byte-identical to `pipeline.build_artifact_model()`
  (plain `shufflenet_v2_x1_0` + `fc=Linear(1024,4)`; aux heads are training-only,
  not in the state_dict), so they load through the UNMODIFIED production chain
  (`pl.run_single -> hierarchical_predict -> classify_artifact`, Layer1/2
  weights unchanged).
- **Is it image-disjoint from eval?**: Yes -- evaluated only on True Test
  (`splits/truetest_filter.txt`, same-algorithm/cross-base-image, n=62-63/type)
  and Alibaba clean (`splits/ood_filter_ali_clean_20260821.txt`, cross-algorithm,
  n=499-500/type, seed=777), neither of which is in the training pool; per
  Known Trap #5, evaluation ran through the actual production routing chain,
  not an isolated `filter_data/{cls}` reserve.
- **Claim**: True Test performance is unaffected by either mechanism (all 4
  candidates x 4 types fall inside v6's 95% Wilson CI, no regression). Both
  mechanisms are architecturally sound implementations of metric-learning and
  domain-adversarial training respectively (verified via in-domain isolated-
  test-set accuracy of 98.4-98.7%, well above v6's ~94% on the same split --
  the mechanisms genuinely changed what the model learned in-domain). Neither
  mechanism reproduces or amplifies the v6_aug "eye_enlarging attractor"
  regression (Alibaba eye_enlarging stayed 79.6-83.0% across all 4 candidates,
  fully CI-overlapping with v6, vs. v6_aug's CI-non-overlapping 79.6%->89.4%).
- **Non-claim (the overreach this result does NOT support)**: Neither
  mechanism produces a statistically robust improvement on Alibaba
  (cross-algorithm) type accuracy. One data point (`dann_s42` smoothing,
  37.2% [33.08,41.52] vs. v6's 28.2% [24.43,32.3], non-overlapping CIs) looks
  like a real win in isolation, but the SAME mechanism's second seed
  (`dann_s123`) landed at 24.0% [20.46,27.93], fully overlapping v6 -- per
  Known Trap #4 (a rank/effect must be demonstrated within-group across >=3
  perturbations, not asserted from one lucky draw), this is judged to be
  training-seed noise, NOT a reproducible mechanism effect, and must NOT be
  cited as "DANN improved Alibaba smoothing accuracy" in any future summary.
  face_reshaping (the structurally weakest type) showed literally zero
  movement across all 4 candidates (4.0-6.2% vs. v6's 6.41%, all CI-overlapping)
  -- this IS a robust (if negative) finding: no amount of representation-level
  regularization tested moved this type at all.
- **Mechanistic interpretation (why both failed)**: both SupCon and DANN can
  only build invariance to axes of variation that actually exist >=2 ways in
  the training pool. Post-Gap-1, each type has exactly 2 base-image sources,
  but both sources are generated by the SAME in-house script with the SAME
  hardcoded parameters (e.g. `face_reshaping`'s `shrink_ratio=0.92` is
  constant across both `filter_data/face_reshaping` and
  `filter_data/lfw_face_reshaping`) -- the only variation available to learn
  invariance to is "which face", not "which algorithm/parameterization".
  Alibaba requires generalizing across a dimension (algorithm implementation)
  that has literally never varied in training, which no representation-
  learning technique can supply from zero examples of that variation.
- **Consequences / status**: No candidate recommended for adoption; all 4
  flagged for the project lead's personal review only, none applied to
  `pipeline.py` or promoted, consistent with the `artifact_classifier_v4`
  same-day-revert incident that motivated this constraint. This is the THIRD
  independent lever type tried for the same cross-algorithm problem (v6 =
  data/base-image diversity, positive but bounded to same-algorithm gains;
  v6_aug = blind data augmentation, negative; this round = representation-
  learning/architecture, negative) -- three mechanistically distinct
  interventions converging on the same negative conclusion is itself
  meaningful evidence that the blocker is the total absence of genuine
  cross-algorithm/cross-implementation samples in the training data, not a
  training-recipe or architecture deficiency. Full write-up:
  `results/research/p2_r6_domaingeneralization_20260822/P2_R6_FINDINGS.md`.

---

## DF40-TAXONOMY-FOLLOWUP-20260823: DF40 held-out leftover pool contamination
check (closes `paper_readiness_execution_20260822`'s Task A gap) + filter/fake/
real taxonomy vs. DFFD/FF++/DF40 literature comparison

- **Phase**: Audit + documentation (Phase 1 evidence, cross-cutting). Two small,
  previously-flagged-but-unfinished items. Read-only on `pipeline.py` and all
  production checkpoints, no training, no git operations.
- **Task A**: `paper_readiness_execution_20260822/EXECUTION_FINDINGS.md`
  explicitly left ONE population unchecked in its content-key contamination
  audit -- the DF40 held-out leftover pool (`sd2.1`/`DiT`/`SiT`/`ddim`/`pixart`
  images NOT used in current training) vs. the portion of those same 5 sources
  actually used in training. Closed this round. Gate pool: 198 unique
  DF40-cdf source images from `splits/research/p1_r3_4_scale_normalized_
  heldout_20260818/manifest.tsv` (`used_in_training == False`, verified via
  the manifest's own column, not re-derived). Train pool: verified directly
  from the actual split files each production checkpoint trains on -- Layer1
  v8.17sbi's `splits/v811_layer1_round4_train.txt` + `splits/research/
  p1_r9_sbi_pilot_20260819/layer1_sbi_augreal_train.txt` and Layer2 v8.11's
  `splits/v811_layer2_train.txt` all resolve to the **identical** 15,000-row
  DF40 subset (3,000/method, cdf+ff mixed) -- Layer1 and Layer2 train on the
  same DF40 images. Reused `audit_p1_r11_fullsplit.py`'s `fp()`/`load()`
  functions unmodified (imported directly, not reimplemented) -- 64-bit dHash
  Hamming<=4 screen, 64x64 z-scored NCC + 32x32 MAD resolve, same thresholds
  as every prior p1_r11/paper_readiness content-key audit. **Result: 2/198
  (1.01%) confirmed near-duplicates, 9/198 (4.55%) confirmed+borderline** --
  a low rate compared to every other population this project has audited
  (`shadow_v2a_filter` ~99-100%, StyleGAN2 63.8%, Alibaba 23.5%, True Test
  fake 4.07%). Does not change the direction of any existing conclusion.
  All 3 confirmed pairs are cross-generator matches (a DiT leftover image
  near-duplicating a SiT/DiT train image and vice versa) -- consistent with
  DF40-cdf's small shared Celeb-DF source-identity pool across generator
  methods, not a sampling bug. One pixart leftover image borderline-matches
  11 unrelated pixart train identities at NCC 0.90-0.93, flagged as likely
  generic structural similarity from pixart's generation process rather than
  genuine content duplication (kept below the 0.95 confirmed threshold).
  This closes the fourth of four populations `paper_readiness_execution_
  20260822`'s Task A named.
- **Task B**: The paper-readiness audit's MINOR finding that this project's
  real/fake/filter taxonomy was never explicitly compared to DFFD's or
  FF++'s established taxonomies. Checked existing project documentation
  first (per instructions, not treated as fresh literature search): `docs/
  Paper 清單.md` already cites DF40 (arXiv:2406.13495) but has no DFFD
  citation anywhere in the project; `TODO.md` line 113/1015 already had a
  partial DF40 breakdown (10 face-swap/13 reenactment/12 EFS/5 face-editing)
  and an open "DF40 Face Editing 歸類決策" item; `results/research/
  p2_fake_explanation_qa_20260822/FAKE_EXPLANATION_QA_FINDINGS.md` Part 4
  (this session's earlier round) already established the EFS-vs-swap/
  reenactment policy directly reusable here. Produced an explicit mapping
  table: `real` maps 1:1 across all three taxonomies; this project's `fake`
  is the union of DFFD's Identity-Swap+Entire-Face-Synthesis and DF40's
  Face-Swap+EFS groups (a deliberate simplification -- this project doesn't
  distinguish "swap with a real source" from "synthesized from scratch"
  because both are content-false); `filter` has **no clean literature
  analogue** in DFFD/FF++/DF40 -- DF40's Face-Editing group is the nearest
  name match but is a general attribute editor, not specifically
  identity-preserving beautification, and `filter`'s true precedent is the
  face-retouching-detection literature this project already cites
  (RetouchingFFHQ, Deceptive Beauty), a different research lineage than
  deepfake/forgery detection. DFFD's Expression-Swap / DF40's Reenactment
  group (FF++'s Face2Face/NeuralTextures) has zero representation in this
  project's training taxonomy -- always collapses into `fake` at inference,
  a known simplification, not newly discovered. Reaffirmed (did not
  overturn) `TODO.md`'s existing DF40-FE caution: do not fold FE into
  either `fake` or `filter` without new ground-truth labels for what each
  FE sample actually changed.
- **Claim**: The DF40 leftover pool is confirmed low-contamination (1.01%
  confirmed / 4.55% incl. borderline), closing the last unaudited population
  from the paper-readiness Task A gap list. The project's taxonomy-vs-
  literature mapping is now explicit and documented, giving readers a table
  to compare this project's reported numbers against DFFD/FF++/DF40 baselines
  without assuming false 1:1 category correspondence.
- **Non-claim**: Does not fix or attempt to fix the 1.01%/4.55% DF40 leftover
  contamination (audit only, per task scope). Does not change the DF40-FE
  taxonomy decision (still excluded from training). Did not edit `docs/
  paper_draft_zh.md` or `docs/limitations_framing.md` this round (left as a
  follow-up to avoid conflicting with any concurrent round touching those
  files) -- the recommended paper-framing paragraph is written out in full
  in this round's findings file for later reconciliation.
- **Consequences / status**: No training-affecting or `pipeline.py` changes.
  New files confined to `results/research/df40_taxonomy_followup_20260823/`.
  Full write-up: `results/research/df40_taxonomy_followup_20260823/
  FINDINGS.md`.

---

## FFPP-PROTOCOL-20260823: FaceForensics++ 官方 protocol benchmark — 本專案第一組文獻可直接對照的數字；同時證偽「FF++ 表現差 = H.264 domain gap 架構限制」

- **Folder tag**: `ffpp_protocol_20260823`
- **觸發**: `results/research/paper_readiness_audit_20260822/PAPER_READINESS_AUDIT.md`
  的 D1（Disqualifying）——「論文目前完全沒有任何一個數字可以跟文獻直接並排比較」。
- **Protocol（OFFICIAL，非重建）**: FaceForensics++ 官方 split，取自
  `github.com/ondyari/FaceForensics` 的 `dataset/splits/{train,val,test}.json`
  （副本存於本輪資料夾）。360/70/70 個 video-ID 配對 = **720/140/140 個唯一
  real video ID**，與原論文所述一致，三 split 兩兩交集為 0（程式驗證）。
  Fake 影片 `{a}_{b}.mp4` 僅在 **a 與 b 皆屬同一 split** 時歸入該 split，
  因此 source 與 target 身份都不跨界。壓縮率 **c23**（文獻主報設定；
  raw/c40 未下載，不報）。
- **抽幀**: 新增 `extract_ffpp_protocol_frames.py`（既有的
  `extract_ffpp_frames.py` 只取每部影片 1 張中間幀，適合零樣本抽查、
  遠不足以訓練，且無 split 概念，故不改寫、維持可重現）。每部影片抽 N 張
  均勻間隔幀、跳過前後 10%；train real=20/fake=5、val real=4/fake=1、
  test=10。人臉偵測與裁切**沿用專案既有方法**（MediaPipe FaceLandmarker、
  landmark hull、MARGIN=0.35、JPEG q90），與 `pipeline.py` 前處理一致。
  實得 train 27,687 / val 1,059 / test 6,620 幀（人臉偵測失敗約 4%；
  test real 實得 136/140 部影片，已計入 CI，不補樣）。
- **Checkpoint / train / val / test 來源**:
  train = 官方 FF++ train split 幀；val = 官方 val split 幀（模型選擇用）；
  test = 官方 test split 幀（訓練與選模階段完全未讀取）。
  init = ImageNet 預訓練 ShuffleNetV2（**刻意不從 production checkpoint 起步**，
  否則數字不再能解讀為 FF++ in-domain benchmark）。
  新 checkpoint：`checkpoints/research/ffpp_protocol_20260823/`
  `ffpp_full_best.pth`（2,528,742 參數，10.31 MB，SHA256 `7ce808a2…`）、
  `ffpp_spatial_best.pth`（1,779,430 參數，7.30 MB，SHA256 `8351cf5a…`）。
- **是否 image-disjoint**: **是，且用內容金鑰驗證**。
  (A) 磁碟實際檔案反推的身份 ID 三 split 兩兩交集 = 0/0/0；
  (B) 三 split 之間解碼像素 SHA256 重複 = 0/0/0（35,366 張全部唯一）；
  (C) FF++ **test 幀** vs. v8.17 production Layer1 的實際訓練語料
  （`splits/research/p1_r9_sbi_pilot_20260819/layer1_sbi_augreal_train.txt`，
  256,968 列）內容金鑰重複 = **0**。
  **限制**：該 split 有 20,295 列（7.9%）指向已被先前整理刪除的
  `v89d_candidate_pool/` 等路徑，無法計算金鑰——與
  `paper_readiness_execution_20260822` 記錄的是同一批既有缺檔，非本輪造成。
- **結果（frame-level，pooled，官方 test split）**:
  | 模型 | pooled AUC | pooled acc | DF / F2F / FS / NT frame acc |
  |---|---|---|---|
  | Ours dual-branch, FF++-trained | **0.9155** | 83.75% | 85.93 / 84.29 / 84.12 / 80.07 |
  | Ours spatial-only, FF++-trained | **0.9144** | 85.79% | 86.27 / 83.99 / 84.35 / 80.82 |
  | **v8.17 production Layer1, ZERO-SHOT** | 0.5747 | 54.80% | 60.27 / 50.79 / 54.30 / 56.66 |
  | **v8.17 full pipeline, ZERO-SHOT** | 0.5727 | 52.10% | 60.16 / 50.57 / 54.30 / 56.13 |
  Video-level（分數 = 該影片抽出幀的平均）pooled AUC：dual-branch 0.9467、
  spatial-only 0.9474、零樣本 0.5882 / 0.5845。全部 accuracy 皆附 Wilson 95% CI
  （見 `tables.md`）。
- **已核實的文獻對照（唯一一項）**: FaceForensics++ 原論文
  （Rossler et al., ICCV 2019, arXiv:1901.08971）**Table 5**（一次在全部四種
  manipulation 上訓練，與本輪同類設定）HQ/c23 XceptionNet：
  DF **97.49** / F2F **97.69** / FS **96.79** / NT **92.19**。本輪最佳
  frame acc 落後 11.2–13.4pp。原論文 **Table 4**（per-manipulation 專屬模型，
  **與本輪設定不同**）的六個 baseline 數字亦已逐字記錄於本輪 findings，
  僅供讀者定位難度，**不得與本輪數字並排**。
- **Known Traps 檢查**（唯一比較性主張 = 「spatial-only 追平 dual-branch」）:
  **Trap #1**（matched operating point）通過 —— matched FPR 5%：0.6450 vs
  **0.6561**；matched FPR 20%：0.8639 vs **0.8741**，SPATIAL 不輸反略優。
  **Trap #2**（低 FPR + pAUC）**部分不通過，已誠實記錄**：pooled
  TPR@FPR=1% dual-branch **0.4069** vs spatial-only 0.3154，四個 method
  全部同方向；但 TPR@FPR=5% 反轉（0.6450 vs **0.6561**），pAUC(FPR≤5%)
  0.7430 vs 0.7276。
  **配對 bootstrap（2,000 次）**：FULL−SPATIAL AUC 差在 5 個 scope
  （四 method + pooled）的 95% CI **全部含 0**。
  **Trap #3**（內容金鑰）通過，見上。
  **Trap #4/#5** 本輪不適用（無「X 預測效能故最佳化 X」的主張；
  無 production 變更）。
- **可宣稱**:
  (1) 本專案在 FF++ 官方 split（c23）上有 pooled frame AUC **0.9155**、
  video AUC **0.9467** 的可核對數字——**第一個外部讀者能查證的 benchmark**。
  (2) **「FF++ 接近亂猜」是訓練資料涵蓋問題，不是 H.264 domain gap 造成的
  架構限制**——同一個架構、同一批 test 影格，只把訓練資料換成 FF++ 官方
  train split，pooled AUC 就從 0.575 跳到 0.916（+0.34），架構未動一個位元組。
  這正式推翻本專案沿用數月的敘事。
  (3) **FFT 分支的貢獻在 FF++ 上同樣量不出來**——spatial-only 參數少 29.6%、
  checkpoint 小 29.2%，AUC 差 5/5 個 scope 的 CI 全含 0。這是繼
  `PAPER-READINESS-EXECUTION-20260822` Task B 之後**第二次獨立複現**，
  且是在**完全不同的資料集 + 完全不同的訓練起點（ImageNet init 而非
  production checkpoint）**下複現，明顯強化「可移除 FFT 分支」的論據
  （並連帶解鎖 int8 量化——int8 失效根因正是 FFT magnitude 的 7.6e9 動態範圍）。
- **不可宣稱**:
  (1) **不可**宣稱在 FF++ 達到或接近 SOTA（落後 Xception 11–13pp）。
  (2) **不可**把本輪數字放進原論文 Table 4（per-manipulation 專屬模型）那張表。
  (3) **不可**引用 SBI / RECCE / MLFF+CNN / FAME / GSD / RCDN / FDML /
  CrossDF 的任何 FF++ 數字——本輪未核實，`TODO.md` 該待辦仍開啟。
  (4) **不可**宣稱 FFT 分支「完全無用」——FPR ≤ 1% 區間 dual-branch 一致領先，
  正確措辭是「在 FPR ≥ 5% 的一般操作區間與整體排序上量不出差異」。
  (5) **不可**宣稱本輪模型可取代 production（它只做 FF++ real-vs-fake 二分類，
  不是三分類系統）。
  (6) **不可**宣稱 RetouchingFFHQ 側有 literature-comparable 數字（見下）。
- **已知設定偏差（論文表格註腳必須寫）**: 訓練幀數比文獻少一到兩個數量級
  （本輪 27,687 張；FF++ 原論文訓練用每部影片 270 張、測試 100 張）；
  backbone 容量差一個數量級（1.78–2.53M vs Xception 約 22M）；未做文獻常用的
  臉部對齊（為與 `pipeline.py` 一致，只用 landmark hull + margin 裁切）。
- **Step 4（RetouchingFFHQ）判定：NOT protocol-faithfully evaluable**，
  五個獨立阻礙，其中兩個是硬阻礙：
  **B1（硬）** 58,158 張未修圖 FFHQ 原圖完全不在專案磁碟上（掃描命中 0；
  `ffhq/` 是 LaTeX 模板目錄），沒有 level-0 負類 → binary detection 與 TN
  都算不出來；
  **B2** `FFHQ_megvii_four_process`（33,474 張）無任何 level 標註檔，
  AC 需同時評 type 與 level（`FFHQ_four_process` 有 `four_process.txt`、
  `FFHQ_ali_process` 以資料夾名編碼，這兩個有 level）；
  **B3（硬）** 標籤空間不相容——本專案 `artifact_classifier` 是 single-label
  4-way head，該論文是 multi-label × multi-level（`four_process` 每張四型別
  同時開啟），TP/TN/AC **結構上無法輸出**；
  **B4** 官方 80/10/10 index 清單未公開（repo 以申請表擋住），自建 split
  只能是 reconstructed，不可與論文表格並排；
  **B5** 專案只有 Megvii(60000–69999) 與 Alibaba(17000–19999)，Tencent 未取得，
  論文 headline cross-API 是 Megvii→Tencent，專案只能 Megvii→Alibaba，是另一格。
  **因此 filter 側的 Alibaba 跨演算法評測必須標為「本專案自訂 protocol」，
  不得與 RetouchingFFHQ 的 TP/TN/AC 並列同一張表。**
  補齊所需：下載公開 NVlabs FFHQ 原圖配 level-0 負類、把範圍限縮到有 level
  標註的兩個子集、另訓 4-type×4-level multi-label head、向作者索取官方
  index 清單／Tencent 子集。
- **實作坑（已修並記錄）**: 四種 manipulation **共用同一組 fake 檔名**
  （Deepfakes 與 FaceSwap 都有 `035_036.mp4`）。video-level 聚合若只用
  video_id 當 key，會把同一部影片的四種偽造合併成一部「平均影片」，
  pooled 影片數從 544 塌成 136。已改為 `(method, video_id)` 複合 key；
  per-method 數字不受影響。
- **Consequences / status**: **無 production 變更**。`pipeline.py` 與所有
  production checkpoint 本輪唯讀、未修改。新檔案限於
  `results/research/ffpp_protocol_20260823/`、
  `checkpoints/research/ffpp_protocol_20260823/`、
  `splits/research/ffpp_protocol_20260823/`、`FaceForensics_protocol_frames/`
  與 7 支新腳本。完整寫作：
  `results/research/ffpp_protocol_20260823/FFPP_PROTOCOL_FINDINGS.md`。


---

## FFPP-IMPROVE-20260823: FF++ improvement round — recipe tuning, backbone efficiency frontier, FFT-branch low-FPR verdict resolved across 3 seeds

- **Folder tag**: `ffpp_improve_20260823`
- **承接**: `FFPP-PROTOCOL-20260823`（上方條目）。**Protocol 不變**：官方
  split json、抽幀方法論（landmark hull + MARGIN=0.35 + JPEG q90）、val/test
  幀集合本身全部原封不動沿用；本輪唯一新增資料是 **train-only** 加密幀集
  （見下）。模型選擇全程只碰 val；test 只在最終候選做過恰好一次評測。
- **新增資料**: `extract_ffpp_dense_train_frames.py`（逐行沿用
  `extract_ffpp_protocol_frames.py` 的 `build_tasks`/`job`/`detect_and_crop`，
  只換輸出目錄與每片幀數，val/test 完全不碰）——real 20→60 幀/影片、fake
  5→15 幀/影片，train 27,687→**83,038** 幀。`build_ffpp_dense_train_split.py`
  稽核（Known Trap #3，內容金鑰函式逐行沿用）：dense train 身份 ID 與官方
  val/test 交集 = 0；內容金鑰與 val/test 重複 = 0；PASS。
- **Part 1 — Recipe 消融**（val 選型，`AIGuard/train_ffpp_improve.py`，
  單變因對照，全部對照 `BASE_FULL`）:
  | 變因 | val pooled AUC | Δ vs baseline (2k 分層配對 bootstrap) | CI含0？|
  |---|---|---|---|
  | baseline（原封不動）| 0.9243 | — | — |
  | +dense train (27,687→83,038) | 0.9344 | +0.0101 | 含0(邊緣,p=0.051) |
  | +JPEG/縮放/模糊增強 | 0.9054 | **−0.0189** | **不含0(顯著變差,p<0.001)** |
  | +AdamW 20-epoch schedule | 0.9284 | +0.0041 | 含0(p=0.197) |
  | **dense+long 疊加** | **0.9421** | **+0.0178** | **不含0(p<0.001)** |
  dense+long 疊加同時顯著贏過單獨 dense（+0.0077, CI不含0, p=0.033）→ 可疊加。
  Class balancing：baseline 已用 auto inverse-frequency weight，frame 層級
  靠抽幀密度平衡（不靠複製），沿用不變，未發現需額外處理的不平衡。
- **Part 2 — Backbone 效率前緣**（val 選型 5 個 timm 候選 → test 驗證一次，
  official test split 6,620 幀；效率數字：CPU 4-thread pinned 50次中位數，
  GPU=RTX 6000 Ada，batch=1 224×224，PyTorch 側數字不可與專案既有 TFLite
  數字直接比較，同架構間內部一致可比）:
  | Arch(+FFT) | Params | fp32 ckpt | CPU延遲 | test pooled AUC | test pooled acc |
  |---|---|---|---|---|---|
  | ShuffleNetV2(baseline production backbone) | 2.53M | 9.83MB | 19.01ms | 0.9155 | 83.75% |
  | MobileNetV4-small | 3.90M | 15.08MB | 14.12ms | 0.9383 | 88.46% |
  | EfficientNet-Lite0 | 4.78M | 18.50MB | 17.87ms | 0.9420 | 89.21% |
  | FastViT-T8 | 4.40M | 17.09MB | 25.29ms | 0.9509 | 90.36% |
  | **RepViT-M0.9** | **5.67M** | **22.06MB** | **28.88ms** | **0.9546** | 88.47% |
  | **RepViT-M0.9 + dense+long**(headline) | 5.67M | 22.06MB | 28.88ms | 0.9538 | **91.86%** |
  全部 4 個 timm 候選在 test pooled AUC 上**顯著**贏過 ShuffleNetV2（CI 全不含
  0，最小 delta +0.0228／mobilenetv4）。RepViT 全程最佳，加 dense+long 後
  再顯著提升（+0.0314 vs 單獨 repvit，val 上，CI不含0）→ headline 候選。
  **Known Trap #1 誠實記錄**：repvit+dense+long 的 pooled AUC(0.9538) 略低於
  單獨 repvit(0.9546，雜訊範圍)，但 accuracy 大幅領先（91.86% vs 88.47%）——
  這是校準/操作點位移，不是純排序能力提升，兩個角度都寫進表格。
  **對 Xception 文獻差距**（本輪最佳 vs baseline round）：
  DF −11.56→−3.92pp(縮66%)、F2F −13.40→−5.79pp(縮57%)、FS −12.67→−4.44pp
  (縮65%)、NT −12.12→−3.23pp(縮73%)。未打平 Xception，但用 1/3.7 參數量
  把平均差距從 −12.4pp 縮到 −4.3pp（縮小65%）。
- **Part 3 — FFT 分支低 FPR 驗證，跨 3 個獨立種子**（official test split，
  分層配對 bootstrap, 2000次；`BASE`=baseline round seed，`S11`/`S22`=本輪
  新訓練的兩個獨立種子，僅 FFT 開關不同）：TPR@FPR=1% 的 FULL−SPATIAL delta
  在 **15 個 scope×seed 格（3 seed × 4 method + pooled）全部同號為正**
  （二項式檢定 p≈0.00003）；**3/15 格 95% CI 不含0**（皆在 seed=22：pooled
  +0.087[+0.027,+0.150]、Deepfakes +0.118[+0.050,+0.197]、FaceSwap
  +0.125[+0.071,+0.203]）。AUC 層面（排序能力）15格中13格點估計同為正但
  絕大多數CI含0，與 baseline round 一致（整體排序上量不出貢獻）。
  **Val 上同一比較訊號更弱且方向不穩**（val real僅530張，FPR=1%對應約5張
  負類，估計雜訊大：3 seed 的 pooled delta 為 −0.006/+0.110/−0.127，正負
  都有）——故意記錄的負結果，說明為何最終判斷放在 test（約66張負類，穩定
  得多）而非 val。
  **判決**：FFT 分支對低 FPR 有真實、方向一致、跨獨立種子可複現、但幅度
  中等且非每次達統計顯著的正向貢獻——這是本專案第三次在不同資料集/訓練
  起點（`PAPER-READINESS-EXECUTION-20260822` Task B production checkpoint
  分析 → `FFPP-PROTOCOL-20260823` 單一FF++seed → 本輪3個獨立FF++seed）
  看到同一方向。**不建議**單純說「FFT 分支沒用可拿掉」或「被證實有用」，
  兩者都過度簡化。**建議**：低FPR敏感部署保留FFT分支；追求int8量化與更小
  模型則可拿掉，整體AUC/accuracy無可量測代價（int8失效根因是FFT magnitude
  7.6e9動態範圍，見CLAUDE.md）。
- **Known Traps 檢查**: Trap #1（matched operating point）全程用 TPR@FPR=1%/
  matched-FPR而非共用0.5threshold，§Part2明確標出accuracy提升是操作點位移；
  Trap #2（低FPR）是Part 3的核心設計；Trap #3（內容金鑰去重）dense split
  稽核A/B全過；Trap #4本輪未做任何「X預測效能」式宣稱，不適用；Trap #5
  val/test皆為官方split獨立幀非訓練池子集，val選型後test只開一次。
- **已知限制**：backbone比較僅單一種子（Part 2顯著性建立在單一訓練實例，
  未如Part 3做跨種子複現）；dense+long recipe只在shufflenet與repvit上各跑
  一次，其他3個backbone加recipe後數字未知；訓練幀密度(60/15)仍遠低於文獻
  (270/影片)，是本輪與文獻差距最大的單一可解釋來源，受時間/磁碟限制未
  進一步加密。
- **Consequences / status**: **無 production 變更**。`pipeline.py` 與所有
  production checkpoint 本輪唯讀、未修改，不提 change proposal。新 checkpoint
  限於 `checkpoints/research/ffpp_improve_20260823/`（13個，含headline
  `ffpp_BB_repvit_dense_long_best.pth`，全部已驗證可載入）；新資料
  `FaceForensics_protocol_frames_dense/train/`（83,038張，僅train，val/test
  未新增/未觸碰）。完整寫作：
  `results/research/ffpp_improve_20260823/FINDINGS.md`。


---

## P2-R7: Fake-class explanation v2 — three new routes (constrained VLM teacher / FF++-mask-supervised localization head / programmatically verified attributes)

- **Date**: 2026-08-23/24. Folder tag `p2_explanation_v2_20260823`.
- **Checkpoints under evaluation**: production v8.17 (Layer1
  `shufflenet_v2_layer1_v817sbi.pth` SHA256 `e3057270…`, Layer2
  `shufflenet_v2_layer2_v811.pth` SHA256 `8470ad52…`) — read-only. Two NEW
  research checkpoints trained this round:
  `checkpoints/research/p2_explanation_v2_20260823/mask_head_{B1,B2}.pth`
  (mask-localization heads; B1 freezes the production backbone, B2 fine-tunes
  it). Neither is wired into `pipeline.py` and neither is proposed for it.
- **Populations**:
  - FF++ content-controlled TRIPLES (manipulated crop, official manipulation
    mask, same-index real crop of the background video), built this round:
    train 1,426 / val 201 / test 687, 4 methods. Splits are the OFFICIAL FF++
    protocol splits (`results/research/ffpp_protocol_20260823/ffpp_*.json`),
    a fake video admitted only when BOTH its ids are in the split, so no
    identity crosses a boundary. **Image-disjoint: yes, by video identity.**
  - Celeb-DF-v2 pairs (493), same structure, different corpus / swap
    implementation / encode. **Used as confirmation only; never trained on.**
- **What may be claimed**:
  - A constrained/structured VLM teacher (Qwen2-VL-7B-Instruct, forced-choice
    + fp32 two-token logit read, NO free-text generation) yields **0 of 8
    fake-class attributes usable** under pre-declared gates G1–G5, on BOTH
    corpora. Best paired AUROC 0.621 (FF++) / 0.566 (Celeb-DF) against a gate
    of 0.70. Three of eight attributes fail the distribution-health gate
    outright (positive rate 100.0% / 95.7% / 86.1%) — i.e. **yes-bias
    reproduces under a constrained output format**. Two placebo questions
    whose answer is invariant to manipulation score 0.433–0.506, confirming the
    measurement itself is valid. Therefore: **the degeneracy in this project's
    VLM-teacher attempts is a property of the TASK, not of the output format.**
    This closes the "we never tried structured output" open question in
    TODO.md section K.
  - A localization head trained on REAL FF++ per-pixel GT (not pseudo-labels)
    **beats Grad-CAM++ on localization** (area-matched mean IoU 0.856 vs 0.774
    on FF++ test, consistent across all 4 methods) but **loses to a per-method
    constant mask in 4 of 4 methods** (0.888; paired bootstrap 95% CI excludes
    0 in every method). Pre-declared gate BG1 required ≥3 of 4 — **not met**.
    This reproduces P2-R1's constant-mask result on a head trained with genuine
    GT: replacing degenerate labels fixed the label problem but not the fact
    that FF++ manipulation regions are near-constant (mean GT area 23.61%).
  - **NEW POSITIVE, and the only one of the round**: training real partner
    frames with an all-zero target mask gives the head a genuine abstention
    channel. Predicted-mask-area AUROC for separating true-positive fakes from
    **false-positive reals** (real frames production calls fake — the exact
    population on which all five prior region mechanisms overclaimed at 100%)
    is **0.7397 (95% CI [0.702, 0.794]) for B1 and 0.7682 (CI [0.749, 0.838])
    for B2**, versus **0.5402 (p=0.1512, n.s.)** for the FIX round's Fix D
    abstention attempt. **This is the first mechanism in the project whose
    abstention is selective rather than uniformly insensitive.** It degrades but
    survives out of corpus (Celeb-DF 0.6368 / 0.6800). Deletion faithfulness
    (BG3) passes for both arms (B1 delta 0.0238, CI [0.0194, 0.0290], d 0.564).
  - **26 low-level image attributes measured on the paired design: 0 of 26
    reach the pre-declared usability bar** (AUROC ≥ 0.65 with CI lower bound
    > 0.55), best 0.583, despite **22 of 26 being significant after BH
    correction, several at p < 1e-90**. A logistic combination of all 26
    reaches only **0.620 IN-SAMPLE** on FF++ train, 0.619 on test — i.e. this
    is not an overfitting or sample-size problem.
  - **Correction to the evidence base of the SHIPPING fake-class template**:
    this round reproduces the FIX round's paired texture effect on a larger
    independent FF++ sample (`lap_var` paired sign rate 74.2%, BH p = 3.9e-95;
    FIX round reported 76.06%, p = 1.7e-27) AND measures the half the FIX round
    did not: the **single-image AUROC of that same attribute is 0.539**. A
    paired sign rate answers "is the manipulated version of THIS face smoother
    than its own original" (yes, ~74%); the template performs the different
    inference "given ONE image, does its texture value indicate manipulation"
    (essentially no). The shipping clause is cautiously worded and causes no
    overclaiming, so this is **not** a request to change production — it is a
    Limitation the paper must state.
- **What may NOT be claimed**:
  - Nothing here says localization works on the EFS population (`AIGuard/fake`,
    DF40 five methods — the training majority). No GT exists there and this
    round did not and could not test it. Per `docs/phase2_story.md` §13, any
    future region claim from B is scoped to FF++-style swap/reenactment ONLY.
  - The abstention operating point is NOT chosen. The descriptive trade-off
    curve (at TP claim ~80%, FP overclaim is 44.0% for B1 / 33.3% for B2) must
    not be read as a recommendation; picking a point off the curve it was
    scored on is exactly Known Trap #5's shape.
  - The Approach-A negative covers Qwen2-VL-7B-Instruct and these 8 questions.
    It does not license "no VLM can do this"; it licenses "constrained output
    format is not by itself the fix".
  - The 26 attributes are not an exhaustive enumeration of low-level statistics.
- **Known Traps checks**: **#2** honoured — TPR@FPR=10% reported alongside every
  AUROC in A and C. **#4** honoured by construction — every comparison in A and
  C is WITHIN a matched pair, never between populations; and the
  significance-vs-usability finding above is itself a new instance of the same
  family of error (a between-image correlate is not a per-image discriminator).
  **#5** honoured — FF++ splits are identity-disjoint by the official protocol,
  the abstention threshold is calibrated on VAL reals only, and Celeb-DF is
  never trained on. **#1/#3** checked and not directly applicable (no
  threshold-based checkpoint comparison; no new training split claimed disjoint
  from an existing eval pool).
- **Two real bugs found and fixed in-round, both of the "silently wrong, never
  errors" kind**:
  1. FF++ filenames `{a}_{b}` are documented as target_source and this holds for
     Deepfakes (background border MAE ~0.7–1.5 grey levels) but **NOT
     consistently for Face2Face** in this copy of the corpus — some Face2Face
     renders are re-encoded at a different resolution than either source
     (`005_010`: 474 frames @704px vs 005 = 385 @720px, 010 = 474 @640px).
     Trusting the convention kept only 3 of 100 Face2Face videos AND would have
     paired fake frames with unrelated real frames wherever two lengths
     coincided. Partner resolution is now decided by measurement (identical
     dimensions + background border MAE ≤ 12), and the per-pair MAE is
     recorded in the index CSV.
  2. `stem` (`{videoid}__f{idx}`) is **not unique across FF++ methods** — the
     same video id is manipulated by several of them. Keying analyses on `stem`
     merged different images; it collapsed 200 sampled Approach-A pairs to 117.
     All three analysis scripts now key on `(method, stem)`.
- **Verdict**: all three routes **FAIL** their pre-declared criteria. No change
  proposal is raised and `pipeline.py` is untouched. The structural reading —
  three independent failures at three different levels (teacher output format,
  label source, unit of explanation) — is that the blocker is the DATA and the
  TASK FRAMING, not the method: on FF++ the answer to "where" is nearly
  constant, so every method can only rediscover that constant. The one thread
  worth pulling is B's abstention channel, reframed as a confidence gate on
  whether a fake verdict deserves an explanation at all.
- **Full write-up**: `results/research/p2_explanation_v2_20260823/FINDINGS.md`.

---

**P2-R8 (2026-08-24)** — `results/research/p2_abstention_20260823/` — Read-only
on `pipeline.py`/production checkpoints. New checkpoints:
`checkpoints/research/p2_abstention_20260823/gate_*.pth` (10 training variants,
none shipped). Developed P2-R7 Approach B's abstention channel into (1) a
seed-replicated operating point and (2) an out-of-FF++ generalization test on
the project's actual production-serving population, per Known Trap #5.

- **Part 1 (operating point)**: 4 new seeds each for B1 (frozen backbone,
  shippable arm) and B2 (fine-tuned, reference-only). PG0 (reproducibility)
  PASSED: FF++ test gate AUROC mean=0.7717/0.7847, min=0.7664/0.7770 across
  seeds — P2-R7's single-seed numbers (0.7397/0.7682) sit inside this
  distribution, not an outlier. Switching the readout statistic from P2-R7's
  `area05` to `top10_mean` (mean of the top-10%-probability pixels), selected
  on FF++ **val**, is a genuine paired-bootstrap improvement (CI lower bound
  > 0 on all 8 checkpoints, delta +0.025 to +0.062). Val-selected threshold at
  a 60% val TP target reaches **test TP claim ≈61-68%, FP overclaim
  ≈22-28%** (4-seed CI), vs the FIX round's 100% baseline and P2-R7's
  27.7%/7.6% single point — a materially more useful operating point.
  3 genuinely different separability levers (real-partner loss reweighting
  ×2/×4, an explicit image-level gate logit trained alongside the mask, and
  checkpoint selection on val gate AUROC instead of val mIoU) were all tried
  and **none beat the seed-baseline mean** — the architecture/data combination
  appears near its ceiling under this readout.
- **Part 2 (generalization, the critical finding)**: gate AUROC on the
  project's EFS-majority production population (DF40 sd2.1/DiT/SiT/ddim/
  pixart, MidJourney, StyleGAN3) looked strong at face value (0.907-0.925,
  PG4 nominally PASS), but **three independent controls falsify it as a
  corpus-fingerprint artifact, not a real capability**: (C1) production's own
  `p_fake` already achieves the same separation on EFS (AUROC 0.9192) with
  zero added value from the gate, while on swap/reenactment `p_fake` is
  near-chance (0.48-0.52) and the gate is where the real value is; (C2a) the
  gate distinguishes two REAL-only corpora from each other at AUROC 0.88-0.94
  — it has learned corpus style, not manipulation; (C2b, decisive) restricted
  to a single corpus with shared collection process (AIGuard/unseen real vs
  fake), the gate collapses to chance (AUROC 0.41-0.56) while `p_fake` on the
  same images still gets 0.77 — the EFS "signal" is entirely a between-corpus
  confound with no within-corpus lever. **PG4 verdict for EFS: FAIL, actively
  disproven, not just unmet.** On swap/reenactment (FF++ test, Celeb-DF-v2,
  and a third independent corpus DiffusionFace-DiffSwap from Ultimate Test
  Set), the shippable B1 arm passes PG4 on 2/3 corpora (fails narrowly on
  DiffusionFace-DiffSwap: AUROC 0.61-0.63, CI lower 0.55-0.58) while the
  non-shippable B2 arm passes all 3 (0.74-0.79). This extends
  `docs/phase2_story.md` S13's EFS/swap policy from localization claims to
  abstention claims, using falsifying evidence rather than assumption, and
  does not overturn it.
- **Part 3 (deployment spec, not applied)**: TFLite 4-gate discipline (ONNX
  export -> onnx2tf -> `tf.lite.Interpreter` load+alloc -> numerics) all
  PASS: no FFT/DFT ops (head touches only ShuffleNetV2 conv/BN/ReLU/bilinear
  resize), max logit error 2.07e-5, fp32 6.13MB, 5.05ms TFLite CPU. Measured
  added latency (5.03ms GPU / 27.76ms CPU median, batch=1) is flagged as a
  conservative upper bound: it re-runs the full ShuffleNetV2 backbone the head
  shares architecturally with production Layer2, rather than reusing Layer2's
  already-computed features — real integration cost would be much smaller
  (decoder-only, 342K params). A concrete schema addition is specified
  (`region_claim: {status, gate_statistic, threshold, mask}` on fake-class
  output) but is explicitly conditioned on solving S13.3's open problem
  (EFS-vs-swap not identifiable at inference) — NOT resolved this round.
- **Claim**: a calibrated abstention gate exists for the swap/reenactment
  fake population (3 independent corpora), with a materially better operating
  point than P2-R7's, reproducible across seeds, and TFLite-exportable.
- **Non-claim**: this does NOT generalize to the project's EFS-majority
  production population (actively falsified, not merely untested); it does
  NOT solve fake localization (P2-R7's structural finding stands); it is NOT
  deployable today because `pipeline.py` cannot route EFS vs swap at
  inference (pre-existing open problem, unaddressed here); latency numbers
  are an upper bound pending backbone-reuse optimization.
- **Full write-up**: findings returned as agent output in this session (not
  written to a standalone file per this agent's operating constraints);
  raw evidence in `results/research/p2_abstention_20260823/manifests/*.json`
  and `PRE_DECLARED.md`.


---

## RETOUCHING-BENCHMARK-20260823: FFHQ negative class obtained + contamination-verified held-out subset -- filter task's first binary retouching-detection number, **negative result (balanced accuracy 50.7-51.2%, chance level)**

- **Folder tag**: `retouching_benchmark_20260823`
- **Trigger**: `results/research/ffpp_protocol_20260823/FFPP_PROTOCOL_FINDINGS.md`
  Step 4 B1 (un-retouched FFHQ originals absent from disk -> no negative class
  -> no detection metric computable) and B3 (single-label 4-way head vs
  paper's multi-label multi-level target -- structurally cannot resolve).
  This round closes B1, leaves B3 open, and finds a legitimate alternative
  metric that can be honestly compared to literature.
- **Negative class sourcing**: verified FFHQ base index ranges actually on
  disk (script, not doc trust): `FFHQ_four_process`/`FFHQ_megvii_four_process`
  = 60002-69999, `FFHQ_ali_process` = 17001-19999. `ffhq/` on disk is an ACM
  LaTeX template directory, not FFHQ image data. Downloaded ONLY the 2,210
  originals needed for the Alibaba index range from HuggingFace
  `marcosv/ffhq-dataset` (per-index PNG mirror of official FFHQ 1024x1024,
  avoids the ~96GB full-dataset download) = 3.02GB, all 2,210 files
  integrity-verified (PIL load + exact 1024x1024 size check). Resolution
  verified to exactly match `FFHQ_ali_process` (no resampling needed).
  **60002-69999 originals deliberately NOT downloaded** -- see next bullet.
- **Why 60002-69999 originals cannot serve as negative class (measured, not
  assumed)**: `measure_original_vs_retouched_proximity.py` computed dHash
  Hamming distance for 23,795 (original, its own retouched version) pairs
  using this project's own P1-R11 NEAR_DUPLICATE threshold (H<=4): **99.48%**
  of pairs fall at H<=4 (12/12 retouch conditions 96.7-99.9%) -- an original
  is definitionally near-duplicate to its own retouched output. Separately,
  100% of four_process/megvii base indices are already present in Layer1
  and/or Layer2 train or val (val counts as exposure -- both layers select
  checkpoint on best val macro-F1). Downloading and using these originals as
  a negative class would produce a contaminated number, not a clean one.
- **Contamination-verified held-out subset construction** (three independent
  screens, `audit_retouching_heldout.py`, importing -- not reimplementing --
  `results/research/p1_r11_leakage_scaling_20260820/audit_p1_r11_k3_content.py`
  content-key primitives):
  **L1** base-index exposure screen against all four production training
  corpora (Layer1 v817sbi train 256,968 rows, Layer1 v811 val 14,675 rows,
  Layer2 v811 train 146,425 rows, Layer2 v811 val 8,793 rows) -- four_process
  and megvii: 0/7,731 and 0/6,834 base indices survive; ali: 669/2,210 survive.
  **L2** positive-class (Alibaba) row-level content screen, reusing the
  already-published `splits/ood_filter_ali_clean_20260821.txt`
  (P1-R11's decontaminated list): 6,380 -> 5,001 rows.
  **L3** negative-class (FFHQ originals) content-key screen against ALL
  251,348 readable production training images (1,353 listed-but-absent
  disclosed) -- **the step no prior round could do, because the negative
  class did not exist until this round**: of 527 candidate originals,
  87 (16.5%) were NEAR_DUPLICATE_LE4 to production training photos (same
  contamination mechanism as the documented Alibaba 23.5% finding, but
  hitting the negative class this time) and excluded.
  **FINAL: 440 clean FFHQ originals / 4,162 clean Alibaba retouched images /
  440 distinct base-photo identities.**
- **Harness validity control** (`control_harness_validity.py`, run BEFORE
  trusting the negative result below): same `pipeline.preprocess_jpeg` /
  `has_face` / `transform_infer` / composite-probability batched path scored
  against two sets with independently documented production numbers --
  CelebA test real (n=1,193): harness measured 99.66% real recall vs
  documented 99.6-99.7%; True Test real (n=250): harness measured 72.80% vs
  documented v8.17 = 72.40%. Both reproduce within noise; a 5-vs-5-sample
  `pipeline.hierarchical_predict` equivalence assertion also passes at 1e-6.
  **The negative result below is a property of the model, not the harness.**
- **Result -- binary retouched-vs-original detection, Wilson 95% CI**:
  L1 P(manipulated): AUC 0.5796 [0.551,0.606], accuracy 88.64%,
  sensitivity 97.60%, **specificity 3.86% [2.43,6.10]**, balanced acc 50.73%.
  PIPELINE P(filter): AUC 0.5943 [0.566,0.622], accuracy 88.66%,
  sensitivity 97.53%, **specificity 4.77% [3.14,7.19]**, balanced acc 51.15%.
  High accuracy is a class-imbalance artifact (4,162:440); balanced accuracy
  (~51%, chance level) is the honest number. The model labels almost every
  face "filter" regardless of ground truth.
- **Paired within-photo test (contamination-immune, the one surviving
  signal)**: for each retouched image vs ITS OWN original, retouched scored
  higher 62.57% [61.08,64.02] (L1) / **66.07% [64.62,67.50]** (PIPELINE) --　⟵ ⚠️ **2026-09-05 撤回**：跨協定比較無效。同協定對照（`EXTERNAL-BASELINES-20260905`）11 個公開偵測器在同一批 Celeb-DF-B 影格、recall 對齊 90.4% 下 beautified ASR 為 6–21%，**低於 ours 的 23.4%**；且 ours 對 untreated Celeb-DF 換臉 AUROC 僅 0.521、把 87.7% 真影格叫 fake，此母體上的 ASR 不具濾鏡強健含義。
  CI excludes 50%, so the model DOES carry directionally-correct retouching
  signal, but it is swamped at any fixed threshold by a stronger systematic
  bias toward calling nearly all faces "filter."
- **Per-type AUC (shared negative pool)**: Smoothing 0.7726 (only type
  meaningfully above chance, monotonic with intensity 0.69/0.81/0.82),
  EyeEnlarging 0.5826, Whitening 0.5145, FaceLifting 0.5044 (both ~chance
  at all three intensities).
- **Retouching-type identification -- UPPER BOUND on the paper's TP metric**
  (paper's TP requires type+level jointly correct via multi-label multi-level
  Equation 4; project's `artifact_classifier` is single-label 4-way, so this
  is type-argmax-only, a structurally looser upper bound, NOT the same
  metric): EyeEnlarging end-to-end 78.59% [76.01,80.97] (only type
  meaningfully above the 25% random baseline); FaceLifting 7.24% [5.81,8.99],
  Smoothing 28.57% [25.92,31.38], Whitening 18.67% [16.42,21.16] all at or
  below random. **Reconfirms, for the first time on a genuinely clean
  negative-class-backed evaluation, CLAUDE.md's existing "Alibaba
  cross-algorithm type accuracy chronically low (3-35%, consistent across
  v3/v5/v6)" finding** -- not a new discovery, but the first time this
  conclusion rests on uncontaminated data.
- **Verified literature comparisons**:
  (1) RetouchingFFHQ original paper (Ying et al., arXiv:2307.10642, full text
  via ar5iv, verbatim quotes) -- dataset 710,726 images = 58,158 originals +
  652,568 retouched; metrics TP/TN/AC are multi-label multi-level, **the
  paper never reports binary accuracy/AUC anywhere**, so this round's binary
  numbers have no cell in that paper's tables to sit next to. Table 7
  (Megvii->Alibaba direct transfer, TP-only by the paper's own design
  rationale) DenseNet121-MAM TP=0.607/InceptionV3-MAM TP=0.539/
  ResNet50-MAM TP=0.466 -- not directly comparable to this round's
  type-argmax-only upper bound (looser definition), qualitative direction
  only.
  (2) ND-IIITD/MDRF binary retouching detection (Bharati et al., IJCB 2017,
  PDF full text via PyMuPDF, verbatim quotes) -- **this is the paper that
  actually reports binary retouched-vs-original accuracy**: in-domain
  trained baselines 79.3-97.5% (Table 1/2, multiple methods and
  cross-ethnicity splits). Project's zero-shot balanced accuracy
  (50.7-51.2%) sits ~41-47pp below in-domain literature numbers -- framed,
  like the FF++ round's zero-shot-vs-in-domain finding, as a training-target
  misalignment (v8.17 filter class was never trained for a binary
  retouched/original objective), not an architecture ceiling. This is the
  **second independent replication** of the "zero-shot cost, not architecture
  limit" story first established in `FFPP-PROTOCOL-20260823`.
- **Cannot claim**: RetouchingFFHQ official-protocol comparability (B3/B4/B5
  from the FFPP round remain open -- no multi-label multi-level head, no
  official split, no Tencent subset); that v8.17's filter class "does
  retouching detection" (it never trained for that binary objective --
  chance-level balanced accuracy is the direct measurement of that
  misalignment); that this negative result will self-resolve without a
  dedicated training round (none was run this round); any binary metric
  placed in RetouchingFFHQ's own tables (paper reports none).
- **Consequences / status**: **No production change.** `pipeline.py` and all
  three production checkpoints (Layer1 v817sbi, Layer2 v811, artifact
  classifier v6) read-only throughout. New data: `ffhq_originals/Part2/`
  (2,210 files, 3.02GB, disclosed disk impact, well within available space).
  No git operations. Full write-up:
  `results/research/retouching_benchmark_20260823/FINDINGS.md`.

## DOCS-AUDIT-20260823: docs/ staleness/redundancy audit + limitations_framing.md production-vs-experimental labeling fix

- **What**: Not a model experiment. A full audit of all 20 markdown files
  under `docs/` for staleness, redundancy, and archival candidates, triggered
  by a project-lead complaint that `docs/limitations_framing.md` (and the
  same-day-edited `docs/paper_draft_zh.md`, `docs/paper_outline.md`,
  `docs/phase1_story.md`, `docs/phase2_story.md`) reported numbers from
  research/experimental checkpoints (an ImageNet-init model trained
  specifically on FF++'s official split; RepViT/MobileNetV4/EfficientNet-Lite0/
  FastViT backbones never used in production) inline with numbers from the
  actual deployed production stack (`shufflenet_v2_layer1_v817sbi.pth` +
  `shufflenet_v2_layer2_v811.pth` + `artifact_classifier_v6.pth`), without a
  reliable way for a reader to tell which was which.
- **Fix applied**: added a consistent bold inline label —
  **[PRODUCTION]** / **[PRODUCTION-HISTORICAL]** / **[EXPERIMENTAL CANDIDATE,
  NOT DEPLOYED]** — to every section/bullet in the five affected files where
  a number's checkpoint provenance was not already 100% unambiguous, and
  added explicit "this limitation still applies to current production" call-outs
  everywhere an experimental result had previously been read as "fixing" a
  limitation section it only demonstrated a possible fix-path for (the abstention
  gate section and the FF++ backbone-comparison section were the two worst
  offenders — neither ships in `pipeline.py`).
- **Read-only constraints honored**: `pipeline.py`, all checkpoints, `splits/`,
  and all `results/` content were read-only throughout; only files under
  `docs/` were edited, and one file (`docs/work.md`) was moved (not deleted)
  to `archive/docs_archived_20260823/` with a README explaining why.
- **Full per-file verdict table, what changed, and the flagged-for-human-decision
  list**: `results/research/docs_audit_20260823/DOCS_AUDIT.md`.

---

## PRODUCTION-CANDIDATE-V2-20260823: FF++ data integration + RepViT backbone swap, evaluated on the FULL production task — both streams NO-GO, both real/reproducible findings

- **Folder tag**: `production_candidate_v2_20260823`.
- **Trigger**: project-lead instruction to convert `FFPP-PROTOCOL-20260823`
  and `FFPP-IMPROVE-20260823`'s FF++-only-benchmark findings into an actual
  evaluated production candidate that preserves ALL of production's existing
  capabilities (filter detection, cross-domain generalization, safety gates),
  not another side-benchmark proof of concept.
- **Read-only**: `pipeline.py` and all production checkpoints
  (`shufflenet_v2_layer1_v817sbi.pth`, `shufflenet_v2_layer2_v811.pth`,
  `artifact_classifier_v6.pth`) untouched throughout. Layer2 held byte-frozen
  in every arm — only Layer1 was ever retrained.
- **Pre-declared protocol**: written BEFORE any candidate was evaluated,
  `results/research/production_candidate_v2_20260823/PRE_DECLARED_PROTOCOL.md`.
  GO required non-regression beyond seed-to-seed noise on the full existing
  gate battery (True Test, Shadow, AIGuard-unseen, CelebA, StyleGAN2, Alibaba,
  fake+filter stress) PLUS a genuine FF++ generalization gain (Stream 1) or a
  genuine capability gain with honest size/latency reporting (Stream 2). A
  combined candidate would only be attempted if both streams cleared GO
  individually.
- **Data integrity finding (applies to all arms)**: production's actual
  Layer1 training split (`layer1_sbi_augreal_train.txt`, 256,968 rows) has
  20,295 rows (7.9%) pointing to files deleted by the 2026-08-21 archival
  cleanup (`v89d_candidate_pool/`) — a pre-existing gap in shared data, not
  introduced by this round, affecting all arms equally.
- **Stream 1 (FF++ fake frames added to production's data, byte-identical
  P1-R9 recipe, 2 seeds)**: content-key disjointness audit (Known Trap #3)
  against True Test/Shadow/AIGuard-unseen/FF++-official-test: 0 collisions,
  PASS. Existing gates preserved (True Test/AIGuard-unseen/CelebA/StyleGAN2/
  Alibaba/stress all flat or slightly improved, both seeds). **FF++ official-
  test frame AUROC 0.568/0.577 vs zero-shot 0.575 — NO GAIN** (threshold-
  independent metric, so not a cutoff artifact); real-recall-on-FF++ collapsed
  to 9-11% while fake-catch spiked to 93-95%, both seeds — the added data
  shifted the operating point without teaching real separability. **Verdict:
  NO-GO.**
- **Stream 1b (coordinator-directed corrected-recipe diagnostic, single seed,
  bounded scope)**: same data idea + FF++ real frames added for balance +
  LR=1e-4/10-epoch regime (vs production's 2e-5/5-epoch polish-only
  fine-tune). Fixed the ranking problem: FF++ official-test frame AUROC
  **0.808**, video AUROC **0.856** (real, holds on the full 6,620-frame
  split) — but fake+filter stress error nearly tripled (8.17% vs 2.80%) at
  the default threshold. **Threshold sweep (0.05-0.95) found no operating
  point that matches production on True Test real recall AND stress error
  simultaneously** — at tm=0.25 stress beats production (2.27%) but True
  Test real recall craters to 47.2% (-25.5pp); recovering real recall to
  production's range (tm≈0.65-0.70) brings stress back to 5-6x production
  and erases most of the FF++ gain. This is a structural trade-off across the
  whole frontier, not a miscalibrated cutoff. Also found: the "best by val
  macro-F1" checkpoint-selection rule is blind to FF++ capability (val split
  has 0 FF++ rows) — picked epoch 1 over epoch 10, which is clearly stronger
  (AUROC 0.683 vs 0.808). **Verdict: NO-GO**, but confirms the original
  recipe (not the data-augmentation idea) was Stream 1's bottleneck.
- **Stream 2 (RepViT-M0.9 backbone swap, production's actual multi-source
  data, 2 seeds, ImageNet init + `train_ffpp_improve.py`'s validated
  ImageNet-init LR/epoch regime since no RepViT-compatible production
  checkpoint exists to fine-tune from)**: real, reproducible gains both
  seeds — True Test filter recall +4-4.4pp, fake recall +0.37pp,
  AIGuard-unseen AUROC +2.7-3.9pp, and **FF++ zero-shot frame AUROC
  0.686-0.708 vs production's 0.575 (a pure backbone-swap effect, ZERO FF++
  training data)**. Real, reproducible regressions both seeds: **Alibaba
  filter recall 82.6-86.7% vs production's ~98-100% (-12 to -15pp)**, Shadow
  filter recall below production's ~15.8% ceiling, fake+filter stress error
  worse with high seed variance (3.19%/5.68%). TFLite export G1-G4 all PASS
  (22.43 MB fp32 Layer1 alone, ~2.1x production's Layer1 size; 17.4 ms/image
  CPU; numerics match PyTorch to max\|dprob\|=2.4e-7). **Verdict: NO-GO as a
  drop-in replacement** (Alibaba/Shadow/stress regressions are real, not
  noise) but a genuine, honest trade-off worth revisiting, not a clean loss.
- **Combined candidate**: not built (pre-declared: only if both streams
  individually clear GO; neither did).
- **Consequences / status**: no production change, no change proposal filed.
  All 10 research checkpoints (5 arms x best/last, plus RepViT's 2 seeds x
  best/last) retained on disk for reference, none promoted. Full tables,
  per-image dumps, threshold sweep, and a concrete recommendation for what a
  follow-up round should try differently (cap the FF++ data fraction instead
  of the full 41.5K/41.5K addition; investigate whether Layer2 independently
  contributes to the Alibaba/Shadow gap since it was held frozen this round):
  `results/research/production_candidate_v2_20260823/CANDIDATE_FINDINGS.md`.

---

## P1-A1-FFPP-DOSE-20260826: FF++ dose-reduction ("seasoning not main course") + Layer2 decoupling — NO-GO all arms, decisive negative result; init-lineage confound resolved

- **Folder tag**: `p1_a1_ffpp_dose_20260826`.
- **Trigger**: MASTER_PLAN_20260826 P1-A1 follow-ups to
  `PRODUCTION-CANDIDATE-V2-20260823`: (1) rerun Stream 1b's corrected recipe
  with FF++ dose cut from 41.5k/41.5k to ~4k/4k; (2) determine whether the
  Alibaba/Shadow regressions seen last round route through Layer1 gating or
  Layer2. A third item (init-lineage confound) was added mid-round by explicit
  coordinator instruction (see below).
- **Read-only**: `pipeline.py`, all production checkpoints untouched. Layer2
  (`shufflenet_v2_layer2_v811.pth`, SHA256 `8470ad52...`) byte-frozen and
  verified output-identical across every arm tested in Task 2.
- **Correction to last round's docs**: `AIGuard/train_pcand_v2_layer1.py`
  (Stream 1b's script) never wired `--lr` into the optimizer (used the module
  constant 2e-5 regardless of the flag). Weight-drift forensics confirm
  **Stream 1b actually ran at LR=2e-5×10ep, not LR=1e-4** as documented.
  `production_candidate_v2_20260823/CANDIDATE_FINDINGS.md` §3 has a dated
  correction note. Also established: **no arm in either round has ever
  initialised from production** (`shufflenet_v2_layer1_v817sbi.pth`) — S1, S2,
  S1b, RepViT S1/S2, and this round's first two arms all start from
  `shufflenet_v2_layer1_v811d.pth` (P1-R9's own init) or ImageNet (RepViT).
- **Task 1 (FF++ dose ladder)**: 4k fake + 4k real (FF++ share of corpus =
  3.27%, vs 13.0% for S1b's full dose), video-stratified sampling, content-key
  disjointness audit 0 collisions/7 populations PASS. Three arms, all single
  seed (20260819), all v811d init except the coordinator-added one:
  `d4k_lr1e4_s1` (mission-spec'd LR=1e-4×10ep), `d4k_lr2e5_s1` (S1b's actual
  recipe, LR=2e-5×10ep, dose-isolated), `d4k_lr2e5_prodinit_s1` (same as
  latter but init = production, SHA256-verified `e3057270...` before load).
  **All three FAIL the pre-declared bar on stress error (6.25-8.17% vs bar
  ≤3.00%, production 2.80%) and True Test real recall (64.3-69.1% vs bar
  ≥70.7%, production 72.69%) — every arm, no borderline cases, no second seed
  run (protocol: only after a single-seed pass).** Per-epoch curve
  (`d4k_lr1e4_s1`, 10 epochs) shows the stress regression appears at **epoch
  1** (3.71%→7.43% in one epoch) and never recovers — an immediate
  LR-driven re-fit/calibration-shift effect, not a dose-accumulation effect.
  Threshold sweep on epoch 10 (Known Trap #1): no operating point recovers
  both True Test real recall and low stress simultaneously (min stress at
  TTreal≥70.7% = 8.30%, worse than default) — same structural-frontier
  signature as S1b. **Verdict on "seasoning not main course": FALSIFIED at
  the mission-specified LR 1e-4 (dose makes zero difference to stress there);
  partially true but insufficient at LR 2e-5 (dose reduction roughly halves
  the stress excess over production but costs most of the FF++ AUROC gain,
  0.808→0.66-0.67, still below this round's own relaxed 0.70 bar).**
- **Init-lineage confound (coordinator-added arm)**: holding data/recipe/seed
  fixed, production-init vs v811d-init differ by ≤0.81pp / ≤0.0051 AUROC on
  every gate — smaller than or comparable to ordinary seed-to-seed noise
  measured elsewhere in this project. **Verdict: init lineage does not explain
  any of the observed trade-offs; production's SBI-trained Layer1 and v811d
  converge to the same place after this fine-tune regardless of starting
  point.**
- **Task 2 (Layer2 decoupling, analysis only, no training)**: Layer2 verdicts
  confirmed byte-identical across 5 arms (prod, S1b_best/last, RepViT S1/S2)
  on every population. **Alibaba filter-recall regression (RepViT, -12 to
  -15pp) is 100% Layer1 gating** — Layer2's own accuracy on what reaches it is
  99.96-99.98% in every arm; Layer2 is exonerated, a Layer2-side Alibaba fix
  (suggested last round) would not help. **Shadow filter recall (~10-12%
  everywhere) is Layer2-ceiling-limited at 15.77%** (gate-independent,
  identical across all arms) with Layer1 contributing a separate,
  comparable-size gating loss (only 51-59% of Shadow filters reach Layer2 at
  all); fixing Shadow needs a Layer2/architecture change (P1-B2), not an FF++
  dose change. **Fake+filter stress regression is 100% Layer1 gating**
  (Layer2 misroutes exactly 1 image in every arm). Full table:
  `results/research/p1_a1_ffpp_dose_20260826/LAYER2_DECOUPLING.md`.
- **Consequences / status**: no production change, no change proposal filed.
  12 new checkpoints (3 arms × best/last + per-epoch snapshots) retained under
  `checkpoints/research/p1_a1_ffpp_dose_20260826/`, none promoted. Full
  tables, per-epoch curve, threshold sweep, and concrete next-step
  recommendations (treat "epoch-1 decision-surface shift" as the thing to
  directly constrain, not dose/LR alone; drop init-lineage as a variable worth
  re-testing; any Alibaba fix must be Layer1-side, any Shadow fix must be
  Layer2/architecture-side) reported to the coordinator in-session (tool guard
  blocked writing a new `FINDINGS.md` report file from this subagent context —
  full findings text preserved in the session transcript per project policy);
  this registry entry and the TODO.md entry are the durable record.

---

## EVAL2-XAI1-20260826: threshold provenance audit + bootstrap CIs + ECE for production v8.17; Grad-CAM++ faithfulness baseline (deletion/insertion/sanity)

- **Folder tag**: `eval2_xai1_rigor_20260826` (MASTER_PLAN EVAL-2 all three bullets, XAI-1 deletion/insertion bullet).
- **Phase**: cross-phase (Phase 1 statistics; Phase 2 XAI methodology). Inference only; no training; no threshold re-selected.
- **Checkpoints (read-only)**: production `shufflenet_v2_layer1_v817sbi.pth` (`e3057270…`) + `shufflenet_v2_layer2_v811.pth` (`8470ad52…`). Per-image inputs: `p1_r9_sbi_pilot_20260819/post_promotion_verification/perimage_PROMOTED.json` (the published gate dump) + this round's re-score `perimage_shufflenet_v2_layer1_v817sbi__shufflenet_v2_layer2_v811_eval2.json` (same `eval_p1_r9_full_gates.Scorer`, adds True Test fake/real, AIGuard/unseen and dev-val raw probabilities).
- **Train/val/test sources**: no training. Dev set for the threshold check = `splits/v811_layer1_val.txt` with `select_p1_r9_threshold.keep()` applied (12,021 rows: 5,872 real / 6,149 manip). Eval sets = the standard gate battery image lists exactly as dumped.
- **Image-disjoint?**: path/stem check of the dev split vs every gate list run this round: 0 path overlaps; 7 stem coincidences (3 True Test fake, 4 unseen) all removed by `keep()`. Content-key (Trap #3) check NOT run for this dev split.
- **Threshold provenance (Task A) — claim**: the numeric value tm=0.5 was confirmed on the dev split only, before gates were read; **no test/eval set was used to pick it**. **Findings that are real**: (1) `pipeline.py` has **no** `manip_threshold` — `hierarchical_predict()` is an argmax over the composite, an implicit image-dependent Layer1 threshold of 0.51-0.67 (median 0.52); the gate harness uses `p_manip>=0.5`. The two rules disagree on 0-3.6% of images per set (all harness=manip → pipeline=real): published stress error 2.80% is **3.01%** under production's rule, Shadow real recall 74.91 → 78.49, True Test real 72.29 → 73.09; no gate verdict flips. (2) `threshold_selection.json` has PROD/CTRL/SBI only — the **promoted SBIAUG arm has no selection artifact**; P1_R9_FINAL_FINDINGS' "6.35%" re-measures as **5.995%**, and the P1-R9 rule would have returned tm=0.475, not 0.500 (gates were run at 0.5 = slightly stricter on the real side than the matched point). (3) epoch selection used the Alibaba-near-duplicate val (known; no flip on clean val). (4) other constants: Layer2 = argmax; `ARTIFACT_UNKNOWN_THRESHOLD=0.6` uncalibrated by design; `_SMOOTH_TEXTURE_THR/_WHITE_BRIGHT_THR` from AIGuard/real training images; `_FAKE_CONF_TIERS` no basis.
- **Bootstrap CIs (Task B)**: 10k resamples, seed 20260826, pairs / base-image clusters as units. True Test fake 99.63 [98.89, 100]; filter **91.97 [88.35, 95.18]** (CI straddles the ≥90 gate); real 72.29 [66.67, 77.51]; paired balanced 82.13 [79.12, 84.94]; Layer1 AUROC on 769 = 0.9555 [0.9408, 0.9688]; AIGuard/unseen AUROC 0.8410 [0.8036, 0.8761]; CelebA (3k) 99.33 [99.03, 99.60]; StyleGAN2 (3k) 99.57 [99.33, 99.77]; Alibaba 97.71 [97.50, 97.91]; Shadow real 74.91 [69.89, 79.93], filter 12.19 [8.60, 16.13], balanced 43.55 [40.50, 46.59]; stress **2.80 [1.92, 3.76]**. v8.11→v8.17 deltas (filter −1.6 pp, stress −0.9 pp) are inside one CI half-width. Full table: `bootstrap_ci_ece_tables.md`.
- **Calibration (Task B)**: Layer1 p_manip 15-bin ECE = 0.084 True Test, **0.247 AIGuard/unseen**, 0.097 in-domain dev. **p_manip never exceeds 0.933** on 13,244 images; mid-range bins over-confident everywhere (unseen 0.60-0.87 bins are only 24-52% manipulated). `_FAKE_CONF_TIERS` "high (≥0.90)" is **unreachable** (0/1,223 fake predictions); "moderate" bucket precision 100% True Test but **71% on unseen**; "lower" 28%. **Non-claim**: the explanation's confidence wording is NOT calibrated; do not describe it as such.
- **Faithfulness baseline (Task C)**: `faithfulness_eval.py` (RISE deletion/insertion, 20 steps, blur baseline; controls = per-pixel random, resolution-matched random 7×7 CAM, fixed centre Gaussian; Adebayo weight-randomisation) on 100 TT fake + 100 TT filter + 50 unseen fake (seed 0 manifest). **Result: production Grad-CAM++ is statistically indistinguishable from a fixed centre-Gaussian prior.** Layer1: del AUC 0.787 vs centre 0.787 (Δ 0.000 [−0.004, +0.004]), ins 0.804 vs 0.794 (+0.010 [+0.005, +0.017]); Layer2 (all 250): del 0.617 vs centre 0.628 (+0.011 [+0.008, +0.014]), ins 0.843 vs 0.838 (+0.005 [+0.001, +0.009]); only unseen-fake on Layer2 beats centre on both by ≥0.01. Sanity: **classifier-head re-initialisation leaves the map almost unchanged (Spearman 0.83-0.97 → FAIL)**; full re-initialisation gives Spearman 0.15-0.21 but the untrained-network map scores an equal/better deletion AUC on the trained model (L1 0.764 vs 0.787). Per-pixel random deletion "beats" Grad-CAM on deletion (scatter artefacts through the FFT branch) — that control is confounded and should not be the reference. **Bar for the evidence head**: beat the centre prior with CI excluding 0 on deletion AND insertion on all three groups, and Spearman < 0.5 under classifier-only randomisation.
- **Non-claims**: CIs quantify sampling error only, not the test-informed promotion decision; CelebA/StyleGAN2 CIs are for the 3,000-image harness subsample; deletion/insertion use a blur baseline whose interaction with the smoothing filter class is unexamined.
- **Status / consequences**: no production change. Recommendation filed in MASTER_PLAN EVAL-2/XAI-1: make the Layer1 rule explicit and shared between `pipeline.py` and the harness; re-derive the operating point on `v811_layer1_val_clean_20260821` with content-key disjointness and record every arm; temperature-scale before any confidence adjective; evidence head must clear the centre-prior bar above. Full narrative report was returned in-conversation (report-file write blocked by tool policy); all tables/JSON/scripts are in the folder.

---

## EVAL2-CALIB-20260826: temperature/isotonic calibration of production v8.17 confidence + precision-defined explanation tiers (NOT shipped)

> **2026-08-26 follow-up (shipped, text layer only)**: since no precision label
> transfers OOD (see below), `pipeline.py` `_FAKE_CONF_TIERS` was changed by the
> coordinator to drop the "high / moderate / lower confidence" adjectives and
> instead print the raw composite score with its position relative to the
> decision boundary (band boundary 0.80 = the raw bucket closest to nominal
> precision on unseen, 80.0%) plus an explicit "not a calibrated probability"
> statement. Decision path untouched (`hierarchical_predict` unchanged);
> schema v2.1.0 validated on smoke outputs; two fake images (sd2.1 cdf, AIGuard/unseen)
> produce band-appropriate text. No calibration constant is applied anywhere.

- **Folder tag**: `eval2_calibration_20260826` (MASTER_PLAN EVAL-2 "信心措辭改建立在校準後機率上" sub-item; follow-up to EVAL2-XAI1-20260826).
- **Phase**: cross-phase (Phase 1 calibration statistics; Phase 2 explanation wording). Inference-free: reused the per-image probability dumps from EVAL2-XAI1-20260826 and `perimage_PROMOTED.json`; no checkpoint loaded, no training, no threshold or decision rule changed.
- **Checkpoints (read-only)**: production `shufflenet_v2_layer1_v817sbi.pth` (`e3057270…`) + `shufflenet_v2_layer2_v811.pth` (`8470ad52…`).
- **Train/val/test sources**: calibration dev = `splits/v811_layer1_val_clean_20260821.txt` (12,031) minus `build_p1_r9_sbi_data.gate_stems()` collisions (10 dropped) = 12,021 rows (5,872 real / 1,028 fake / 5,121 filter), asserted identical to the previous round's dev block. Held-out = True Test 769, AIGuard/unseen 454, Shadow 279+279. Nothing fitted on any held-out set.
- **Image-disjoint?**: dev vs gate lists — stem-disjoint by construction (gate_stems()); content-key (Trap #3) check NOT run (same status as EVAL2-XAI1).
- **Pre-declared rule**: tiers on calibrated composite P(fake) of argmax-fake images (high ≥0.95 / moderate ≥0.80 / lower); pass iff every tier non-empty on unseen AND empirical precision ≥ bound − 5 pp. Deploy calibrator = per-layer temperature (T1 = 0.5191, T2 = 0.6246; both < 1, i.e. model is under-confident in-domain).
- **Result — claim**: (1) Temperature scaling removes the *unreachability* of the top tier (calibrated ≥0.95 band holds 243/269 True Test and 202/367 unseen fake calls; raw ≥0.90 held 0). (2) It does **not** make the wording truthful out of domain: unseen precision is **77.7% in the "≥95%" band and 35.5% in the "≥80%" band**; isotonic 80.0% / 67.6%. Even on dev the temperature-scaled moderate band is only 31.6% precise (step-shaped reliability; 1-parameter map cannot fit it). (3) Dev-fitted calibration **worsens** OOD ECE: Layer1 p_manip unseen 0.247 → 0.320, Shadow 0.114 → 0.206; composite P(fake) unseen 0.181 → 0.297. In-domain it helps (dev 0.097 → 0.016; True Test composite 0.093 → 0.023). (4) Filter-class explanation templates carry no confidence wording, so no equivalent fix is needed; composite P(filter) tiers show the same OOD under-delivery (True Test moderate 71.7%, Shadow 78.9%). (5) Per-layer temperature preserves each layer's argmax but would flip the composite 3-way argmax on 1/769 TT, 4/454 unseen, 10/558 Shadow if applied to the decision — any future use must be confidence-text-only.
- **Non-claims**: this does not show the model is "uncalibratable"; it shows a dev-fitted monotone calibrator cannot fix a domain-shift over-confidence. Fitting on unseen was deliberately not done (it is the only OOD fake evaluation set). The ±5 pp tolerance is a pre-declared convention, not a literature standard.
- **Status / consequences**: **validation FAILED → `pipeline.py` NOT modified**; `_FAKE_CONF_TIERS` remains raw-threshold and its "high" tier remains unreachable (known, documented in EVAL2-XAI1). MASTER_PLAN sub-item left unticked with a pointer. Options recorded in the in-conversation findings report (report-file write blocked by tool policy, as in EVAL2-XAI1): OOD calibration set; rank-band wording with in-distribution qualifier; or drop the adjective and print the number. Artifacts: `results/research/eval2_calibration_20260826/{calibrate_tiers.py (pre-declared rule in header), calibration_tables.md, calibration_results.json}`.

## DECISION-RULE-UNIFY-20260826: explicit Layer1 threshold vs composite-argmax product rule — val-only re-selection FAILED the gate battery (tm=0.675 NOT applied); `decision_rule.py` created but NOT wired

> **2026-08-26 follow-up (APPLIED, option B, user-authorised)**: `pipeline.py`
> `hierarchical_predict()` now imports `decision_rule.decide()` and calls it at
> `MANIP_THRESHOLD = HARNESS_LEGACY_THRESHOLD = 0.5` — the published operating
> point, not the rejected val-selected 0.675. Verified: `decide(...,0.5)`
> reproduces `pred_harness_tm0p5` on all 13,244 dumped images (0 mismatches,
> `truetest_real/fake/filter`, `aiguard_unseen`, `dev_val_p1r9_filtered`
> sub-groups all 0/n); a crafted wiring-check case where argmax would say
> "real" but the gate says "filter" (p_real=0.48, p_manip=0.52, L2
> fake=0.10/filter=0.90) confirms `decide()` is actually called, not argmax.
> `docs/structured-output.schema.json` v2.1.0 validated on live smoke images
> (AIGuard/unseen fake_108, sd2.1 Celeb-real). Syntax-checked. Effect vs the
> old argmax rule: 2 True Test real + 18 Shadow images change label (per
> `changed_images.tsv` in the folder above); **no Freeze-Gate verdict
> changes** (this was already established in the analysis round above — the
> product now simply reads exactly what every published gate table already
> said). Backup of the pre-change file: `pipeline_pre_unify_20260826.py.bak`.
> `decision_rule.VAL_SELECTED_THRESHOLD_NOT_RECOMMENDED = 0.675` is kept as
> the honest record of the rejected val-only selection; it is not used.

- **Folder tag**: `decision_rule_unify_20260826` (MASTER_PLAN EVAL-2 follow-up to EVAL2-XAI1-20260826 task A). Analysis-only: no training, no checkpoint change, `pipeline.py` unchanged, no existing harness modified, `p1_a1_ffpp_dose_20260826` untouched.
- **Phase**: Phase 1 (decision rule / operating point of the production real-fake-filter classifier).
- **Checkpoints (read-only)**: production `shufflenet_v2_layer1_v817sbi.pth` (`e3057270…`) + `shufflenet_v2_layer2_v811.pth` (`8470ad52…`). Inference only for CelebA 3,000 / StyleGAN2 3,000 / Alibaba 21,151 (published dump has labels only); fresh probabilities reproduce published labels 3000/3000, 3000/3000, 21,150/21,151 (one Layer2 near-tie pf=0.5003 vs pfl=0.4997), unseen AUROC to 1e-15.
- **Train/val/test sources**: dev = `splits/v811_layer1_val_clean_20260821.txt` (12,031) − `gate_stems()` (10) − content-key hits (1,593; decoded-pixel SHA256 exact + dHash≤4, pre-declared conservative) = **10,428** (5,143 real / 5,285 manip); probabilities reused from the EVAL2 dump (row set verified identical). Held-out = full Phase-1 battery (True Test 769, AIGuard/unseen 454, CelebA/StyleGAN2 3,000 each, Alibaba 21,151, Shadow 279+279 via `clean_output/clean_paths.txt`, stress 2,289 / 287 clusters, stressdev 2,351).
- **Image-disjoint?**: dev vs gates now content-checked (first time for this val): **332 dev rows (AIGuard-fake-val) are byte-identical to `stylegan2_test/fake` images; 97 confirmed near-duplicates (76 → Alibaba via FFHQ base photos in AIGuard/real + filter_data, 21 → StyleGAN2); 17 borderline; 1,147 dHash false positives** (`content_key_check.json`, `content_key_resolution.json`). The 2026-08-21 "clean" val removed only `FFHQ_ali_process` rows; it is not gate-content-disjoint. All were dropped before selection.
- **Pre-declared rule** (`PRE_DECLARED.md`, written first): maximise dev balanced accuracy s.t. dev false-manip ≤ product-argmax rule's (5.600 %), grid 0.005, ties → smallest tm; 10k bootstrap; freeze; read gates once; apply iff no Freeze-Gate A pass→fail flip AND unified points inside published CIs.
- **Result — claim**: (1) Selected **tm = 0.675** (dev BA 95.81 % vs 95.59 % at 0.5; +0.11 pp vs argmax, CI [−0.10, +0.33]; bootstrap re-selection band [0.55, 0.72], 20 % on 0.675 — not identified). (2) On the gates it **flips True Test filter recall 91.97 → 88.76 % (gate ≥90)**, Alibaba 97.70 → 95.54, stress error 2.80 → 4.85 %, unseen fake recall 97.69 → 93.06, TT fake 99.63 → 98.89; gains TT real 72.29 → 81.53, Shadow real 74.91 → 84.95, TT paired balanced 82.13 → 85.14, Shadow balanced 43.55 → 47.31 — the P1-R8 single-knob trade-off; dev objective surface flat (0.2 pp over tm 0.45–0.70) while gates move 3–10 pp. (3) Product argmax vs published tm=0.5 deltas now have CIs: Shadow real +3.58 [+1.43, +5.73], stress +0.22 [+0.04, +0.44], TT real +0.80 [0, +2.01], rest within noise; no gate verdict differs between the two current rules. (4) Provenance correction: SBIAUG **has** a `threshold_selection.json` row in `p1_r11_leakage_scaling_20260820` (tm 0.475, written post-promotion, never applied; 0.490 on the cleaned dev); the published 0.5 is the harness default, not val-selected, for v8.11 and v8.17. (5) `decision_rule.decide(…, 0.5)` == harness on 13,244/13,244 images.
- **Non-claims**: does not show any threshold ≠ 0.5 is better or worse in deployment; shows this dev set cannot select one. No multi-seed. CelebA/StyleGAN2 are the published 3,000 subsamples; Alibaba CI optimistic (shared base images).
- **Status / consequences**: **DO NOT APPLY tm=0.675** (criteria (i),(ii) failed). `decision_rule.py` (repo root) holds `MANIP_THRESHOLD=0.675` flagged NOT RECOMMENDED + `HARNESS_LEGACY_THRESHOLD=0.5`; wired only into this round's `eval_gates_unified.py`. Option B for the reviewer (post-hoc, not pre-declared): wire `decide` at 0.5 to remove the harness/product discrepancy at the published operating point (2 True Test + 18 Shadow images change label, no verdict changes) — exact minimal `pipeline.py` diff in `proposed_pipeline_diff.patch`, not applied. Findings report delivered in-conversation (report-file write blocked by tool policy, as in EVAL2-XAI1/EVAL2-CALIB). Artifacts: `results/research/decision_rule_unify_20260826/{PRE_DECLARED.md, proposed_pipeline_diff.patch, threshold_selection.json, unified_gates_tables.md, unified_gates_results.json, changed_images.tsv, posthoc_threshold_frontier.md, content_key_*.json, perimage_…_gatesets.json, *.py, log_*.txt}`.

---

## REMEASURE-SWEEP-20260826: inference-only re-measurement of every INVENTORY §D priority item on production v8.17 + archived v8.3/v8.4/v8.5

- **Phase**: cross-phase (Phase 1 evidence hygiene / MASTER_PLAN "P1-任務｜標了污染、沒重測掃蕩").
  Round dir: `results/research/remeasure_sweep_20260826/` (`FINDINGS.md` blocked by tool guard —
  full findings delivered in the task's final message instead; `remeasure_v817_sweep.py`,
  `dump_recompute.py`, plus reused archived-checkpoint scripts and `eval_df40_benchmark.py`).
- **Checkpoints (read-only)**: production `shufflenet_v2_layer1_v817sbi.pth` (`e3057270…`) +
  `shufflenet_v2_layer2_v811.pth` (`8470ad52…`), hash-verified against `pipeline.py` before every
  job; archived `shufflenet_v2_3class_{v83,v84,v85}.pth`.
- **New data collected**: Celeb-DF-v2 400 frames and WildDeepfake 800 frames on v8.17 for the
  first time (AUROC 0.568/0.744, real recall 14.5%/10.25% — v8.1 was 0/200 on Celeb-DF-v2);
  FakeClue 1,166 (clean 1,132 after excluding 33 content-overlap + non-face rows) on v8.17 for the
  first time (AUROC 0.518, statistically unchanged from v3-era 0.540 — FakeClue has never improved
  with model version); archived v8.3/v8.4/v8.5 True Test filter recall + AIGuard/unseen + FakeClue
  + WildDeepfake on fixed (v8.6+) preprocessing for the first time (v8.3 91.6%/0.7371, v8.4
  94.8%/0.7226, v8.5 94.0%/0.7345 — not directly comparable to the pre-fix "舊量測" numbers because
  v8.4's own C2 data bugs are a separate, un-decoupled confound).
- **Recomputed from existing dumps (zero inference)**: True Test fake recall on 259 clean fakes
  (removed 11 near-dup, L7) = 99.61% [Wilson 97.85, 99.93]; AIGuard/unseen decontaminated AUROC
  (removed 4 near-dup, L8) = 0.8387, bootstrap 95% CI [0.8011, 0.8750] — the CI lower bound clears
  the ≥0.80 Freeze-Gate by only 0.0011, thinner than any prior "marginal pass" framing stated;
  Alibaba recall on base-index cluster bootstrap (2,207/1,706 clusters, not naive per-image) =
  97.71%/97.70% for the full 21,151 and clean 16,183 splits respectively — both splits agree to
  0.01pp, confirming P1-R11's finding that the leaked subset never inflated this number.
- **Canonical artifact produced**: `stylegan2_decontam_exclusion_CANONICAL.json` reconciles the
  6,376-vs-6,252 discrepancy flagged in INVENTORY A1 — verified by set arithmetic that the 124
  difference is exactly the `BORDERLINE`-only (vs `CONFIRMED_NEAR_DUPLICATE`) images; the union
  (6,376) is fixed as canonical (matches every prior published decontaminated number except the
  2026-08-21 gapfill's CONFIRMED-only 6,252). v8.17 full-10k explicit-weight recall: raw 99.67%,
  decontaminated (canonical) 99.25%, contaminated-subset-alone 99.91% (still not inflated).
- **v8.17 explicit-weight reruns**: 3×3 True Test confusion matrix (real 72.8%/fake 99.63%/filter
  91.97%, pipeline-argmax rule — matches every previously published gate exactly; supersedes the
  Layer1c-era `results/v811_confusion_matrix.json`, dated 2026-08-03, before Layer1d existed);
  DF40 EFS sanity benchmark with explicit v8.17 weights (overall AUROC 0.9999, per-method
  99.7-100.0% — essentially identical to the Layer1c-era number, confirming the sanity-check
  framing was never wrong, just unattributed).
- **Code changes**: `eval_df40_benchmark.py` gained `--layer1/--layer2` named flags (default left
  unchanged at v811c per the task's "do not edit its default silently" instruction — every caller
  must now pass explicit weights, named or positional); `generate_v811_confusion_matrix.py` now
  names its output by loaded weights instead of overwriting a fixed filename (the same class of
  bug flagged in `ORPHAN_AND_UNVERIFIABLE_REGISTER.md` Items 2/4 — that register's Item 2 was
  annotated as resolved this round for `eval_v811_gates.py`/`eval_ali_ood_v811.py`, which were
  already fail-closed since 2026-08-13; `eval_df40_benchmark.py` was the one remaining
  silent-default script and is fixed here).
- **Non-claims**: this round did not re-run Face2Face `PAIRED_OK` re-verification (INVENTORY C13),
  P2-R4 Baseline-2 on decontaminated StyleGAN2 (C17), or idle-machine mobile latency (C8 — needs
  hardware access, explicitly out of scope per task instructions). The unified decision-rule gate
  re-publish (C6) is a separate parallel round, `decision_rule_unify_20260826` (see entry above),
  which appears to have finished independently during this session; its outputs were read for
  status only and not incorporated into any number in this entry.
- **Documentation annotations applied (Part 2)**: dated ⚠️ 2026-08-26 append-only notes in
  `CLAUDE.md`, `docs/Dataset 清單.md`, `docs/research_log.md`,
  `docs/研究路線圖：AIGC & Filter Detection 論文發表策略.md`, `docs/dataset.md`,
  `docs/limitations_framing.md`, `docs/phase1_story.md`, `docs/paper_draft_zh.md` (6 sites),
  `docs/phase2_story.md`, `docs/paper_outline.md`, this file (P1-7/P1-8/P1-13 entries above),
  `TODO.md` (7 sites), `docs/releases/v8.11_production/ORPHAN_AND_UNVERIFIABLE_REGISTER.md`,
  `docs/releases/v8.11_production/PHASE1_FREEZE_DECISION.md`, `RELEASE_BOUNDARY.md`,
  `results/research/contamination_cleanup_20260821/CLEANUP_AND_RETEST_REPORT.md`,
  `results/research/v817_scorecard_gapfill_20260821/GAPFILL_LOG.md`. **Lockbox rule applied**:
  `splits/ultimate_clean_test.txt` marked DOWNGRADED TO DEV-TEST in `TODO.md`, `docs/dataset.md`,
  `docs/Dataset 清單.md`, `CLAUDE.md` (trigger: P2-R8 read 783/1,052 images and scored production
  `p_fake` — the project's own 2026-07-31 pre-declared downgrade rule applies).
- **Status / consequences**: no production change; documentation-only + two script hardening
  fixes (both backward-compatible, defaults unchanged). `docs/MASTER_PLAN_20260826.md`'s
  "P1-任務｜標了污染、沒重測掃蕩" item ticked for the INVENTORY §D scope; a new
  "重抽新 lockbox from unused sources" item added (blocked on new data, not attempted).

## ARCH1-UNIFIED-20260826: first ARCH-1 ablation — one shared RepViT-M0.9 backbone, joint heads A+B, vs v8.17 two-model stack — CONTINUE (not GO, not NO-GO)

- **Checkpoints**: `checkpoints/research/arch1_unified_20260826/arch1_unified_S1_best.pth`
  (single unified model, backbone+FFT+head_a+head_b, 24.47MB, 5,994,468 params) +
  `*_layer1view.pth`/`*_layer2view.pth` (same weights, re-keyed for the existing gate harness,
  not separate models). Scripts: `AIGuard/train_arch1_unified.py`, `eval_arch1_unified_gates.py`
  (copy of `eval_pcand_v2_full_gates.py` + `--layer2-backbone` flag), `results/research/
  arch1_unified_20260826/bench_latency.py`. Pre-declaration: `results/research/
  arch1_unified_20260826/PRE_DECLARED.md` (written, and amended with a data-integrity addendum,
  before any gate result was read). Full findings (tool guard blocked writing FINDINGS.md from
  inside the executing agent; content delivered in that agent's final chat message instead):
  reproduced in full below.
- **Design**: single shared RepViT-M0.9 backbone (ImageNet init) + kept FFT branch + two
  independent heads (A: real-vs-manipulated = Layer1's task, B: fake-vs-filter|manipulated =
  Layer2's task), trained JOINTLY (one forward pass, masked per-head CE loss) on the verified
  production-only splits (`layer1_prod_only_filtered_train.txt` for A, `v811_layer2_train.txt`
  for B — no FF++ added, per the mission's explicit constraint and P1-A1-FFPP-DOSE-20260826's
  finding that adding FF++ to training data backfires). Recipe reused verbatim from
  `production_candidate_v2_20260823`'s already-validated RepViT-M0.9 from-scratch recipe (Adam
  1e-4, 10 epochs, cosine) — not a fine-tune LR. One seed only (single-seed-diagnostic
  convention).
- **Data-integrity finding**: `splits/v811_layer2_train.txt` (production Layer2's own training
  split) has 20,295/146,425 rows (13.9%, all fake-class, from two since-deleted hard-neg-mining
  scratch folders `v89d-mined-hardneg`/`v811-round2-mined`) pointing to files no longer on disk.
  Head B trained on the loadable 126,130-row remainder (fake=52,798/filter=73,332, 42/58 skew vs
  the original ~50/50). Disclosed, not silently patched around; flagged as an open follow-up
  (recover files or re-mine) before treating head-B numbers as fully like-for-like with
  production.
- **Result vs v8.17 production** (`gates_PROD_v817.json` from `p1_r16_layer2_ratio_sweep_20260820`,
  FF++ numbers freshly re-run this round for an apples-to-apples harness/environment match —
  reproduces the documented 0.5747 production FF++ frame AUROC to 4 decimals):
  - **Improved, several beyond production's own bootstrap CI**: True Test filter recall
    91.97%→97.99% (CI upper bound 95.18%), True Test balanced/strict accuracy, AIGuard/unseen
    AUROC 0.8410→0.8481, Shadow filter recall 12.19%→**36.20%** (breaks the documented ~15.8%
    Layer2-ceiling — that ceiling was shown in `LAYER2_DECOUPLING.md` to be a property of the
    FROZEN production Layer2; this round's jointly-retrained head B clears it by >2x), Shadow
    real recall +18.3pp, FF++ zero-shot/official-test AUROC +6 to +11pp across frame/video/layer1/
    end2end cuts.
  - **Regressed, clearly beyond CI**: fake+filter stress error 2.80%→**7.86%** (CI upper bound
    3.76%), Alibaba filter OOD recall 97.71%→**76.76%** (−20.95pp), stressdev error +1.96pp,
    in-domain real_filter recall −6.59pp. This is the THIRD independent context (after
    P1-A1-FFPP-DOSE-20260826's Stream-2 arms and `LAYER2_DECOUPLING.md`'s error-flow analysis)
    where a RepViT Layer1/head-A swap produces the same directional cost — more manipulated/
    retouched images get called "real" — now reproduced on clean production-only data with no
    FF++ dose confound, so this is a backbone-level pattern to log, not re-investigate from
    scratch. Per `LAYER2_DECOUPLING.md`'s method, this is presumptively a head-A phenomenon, so
    the head-B data-integrity gap above is an unlikely explanation.
  - **Size**: single unified model 24.47MB vs the 20.62MB two-ShuffleNet subset it replaces —
    **larger, not smaller** (contradicts the round's pre-declared expectation; RepViT-M0.9's
    5.665M-param backbone is ~4.5x ShuffleNetV2's per-model backbone size). **Latency**: 27.24ms
    unified single forward vs 32.53ms worst-case two-sequential-ShuffleNet forward (−16.3%,
    improved).
- **Decision: CONTINUE** — not a GO (stress regression beyond CI + size regression both
  disqualify straight promotion; heads C/D should not be built on this exact backbone yet), not
  a flat NO-GO (the joint multi-task shared-backbone+heads design itself produced real,
  CI-clearing wins independent of backbone choice — Shadow ceiling break, filter recall, FF++
  generalization). Recommended next step: re-run this exact joint-multi-task harness with
  ShuffleNetV2 as the shared backbone (isolates "does joint training help" from "does RepViT
  help/hurt" — currently confounded) before deciding whether to keep RepViT or revert the
  backbone choice for ARCH-1's continuation into heads C/D.
- **Non-claims**: single seed only (not multi-seed confirmed); backbone choice not isolated from
  joint-training choice; head-B data-integrity gap not closed; TFLite export not attempted
  (PyTorch CPU timing only, per mission).
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1's "先做 A+B 雙 head 版證明不輸 v8.17"
  bullet ticked as DONE-with-CONTINUE-verdict (ablation completed; result is mixed, not a clean
  "not worse than v8.17" pass) — see that file for the exact annotation. No production change;
  `pipeline.py` untouched.

## ARCH1-ISOLATION-20260826: backbone isolation — rerun identical joint-training harness with ShuffleNetV2 instead of RepViT — CONTINUE, hypothesis partially falsified

- **Checkpoints**: `checkpoints/research/arch1_isolation_20260826/arch1_unified_S1_best.pth`
  (single unified model, ShuffleNetV2 backbone+FFT+head_a+head_b, 12.94MB, 3,202,327 params) +
  `*_layer1view.pth`/`*_layer2view.pth` re-keyed views. Scripts:
  `AIGuard/train_arch1_unified_shufflenet.py` (byte-for-byte copy of
  `AIGuard/train_arch1_unified.py` with ONLY `build_backbone()` changed to
  `torchvision.models.shufflenet_v2_x1_0` instead of timm RepViT-M0.9 — same data, FFT branch,
  joint masked-CE loss, recipe, seed 20260826), `eval_arch1_unified_gates.py` (reused verbatim,
  unmodified, `--layer1-backbone shufflenet --layer2-backbone shufflenet`, that harness's own
  defaults), `results/research/arch1_isolation_20260826/bench_latency.py` (adapted copy of the
  previous round's latency script). Pre-declaration written before training:
  `results/research/arch1_isolation_20260826/PRE_DECLARED.md`. Full findings (tool guard again
  blocked writing FINDINGS.md from inside the executing agent; delivered in that agent's final
  chat message, reproduced in full below).
- **Purpose**: `ARCH1-UNIFIED-20260826` confounded two variables — joint multi-task training vs
  the RepViT backbone swap — in explaining that round's mixed result (real gains: Shadow filter
  recall 12.19%→36.20% ceiling break, True Test filter recall +6pp, AIGuard/unseen AUROC up,
  FF++ zero-shot up; real regressions: fake+filter stress 2.80%→7.86%, Alibaba filter OOD
  97.71%→76.76%, matching a RepViT-Layer1 failure pattern already seen twice before). This round
  isolates the two variables by rerunning the IDENTICAL harness with ShuffleNetV2 (production's
  own backbone family) substituted for RepViT, changing nothing else.
- **Data**: identical to the previous round, including the same disclosed 20,295/146,425-row
  (13.9%) missing-file drop in `v811_layer2_train.txt` (head B trained on the same loadable
  126,130-row subset, fake=52,798/filter=73,332). `joint_rows=236,673` confirmed identical at
  launch. Training converged normally: best combined F1=0.9271 at epoch 10/10, wall=1706s.
- **Three-way result** (v8.17 production from `results/research/p1_r16_layer2_ratio_sweep_20260820/
  gates_PROD_v817.json` + `gates_PROD_v817_ffpp_only.json`; RepViT arm from
  `arch1_unified_20260826/gates_S1_best.json`; ShuffleNetV2 arm this round's
  `gates_S1_best.json`):
  - True Test filter recall (gate, CI [88.35, 95.18]): 91.97% → RepViT 97.99% (beyond CI, +) →
    ShuffleNetV2 90.36% (within CI, flat/slightly down — RepViT's gain here does NOT reproduce).
  - Shadow filter recall (informational, ~15.8% known ceiling): 12.19% → RepViT 36.20% (breaks
    ceiling 3x) → ShuffleNetV2 24.73% (also breaks ceiling ~2x, smaller than RepViT but real).
  - AIGuard/unseen AUROC (gate): 0.8410 → RepViT 0.8481 (+0.71pp) → ShuffleNetV2 **0.8802**
    (+3.92pp, best of the three arms).
  - FF++ official test video AUROC (informational): 0.5820 → RepViT 0.6583 → ShuffleNetV2
    **0.6861** (best of the three).
  - **Alibaba filter OOD (informational, not gating)**: 97.71% → RepViT 76.76% (−20.95pp) →
    ShuffleNetV2 **56.23%** (−41.48pp — WORSE than RepViT, not better). This directly falsifies
    the working hypothesis that motivated the round (that the pattern seen 3x before was a
    RepViT-specific backbone property for Alibaba specifically).
  - **Fake+filter stress error (gate, CI [1.92, 3.76])**: 2.80% → RepViT **7.86%** (2x CI upper,
    severe) → ShuffleNetV2 3.93% (0.17pp past CI upper, mild — ~4.5x smaller regression than
    RepViT's in delta terms, but still not a clean pass).
  - **Model size**: two-ShuffleNet subset 20.62MB → RepViT unified 24.47MB (LARGER, contradicted
    the round's own pre-declared expectation) → ShuffleNetV2 unified **12.94MB** (37.3% SMALLER
    than the subset, 47.1% smaller than the RepViT unified model — the "far smaller" result
    ARCH-1 originally expected).
  - **CPU latency** (single image, apples-to-apples within this round's own rebenchmark run):
    production worst-case 39.28ms (19.70+19.57 sequential) → ShuffleNetV2 unified single forward
    **19.12ms** (−51.3%, also beats standalone Layer1 alone at 19.70ms since one backbone pass
    now serves both heads). RepViT's latency delta (27.24ms vs its own round's 32.53ms baseline)
    is not from the same measurement run, so only within-round deltas are compared directly.
- **Mechanistic conclusion — mixed, does not cleanly convict or exonerate RepViT**: (1) the
  Alibaba collapse is NOT RepViT-specific — it reproduces, and gets WORSE, with the production
  backbone under joint training, so it is at minimum a joint-multi-task-training property that
  backbone choice modulates but does not remove; (2) the stress-error blowup IS backbone-
  modulated (RepViT ~4.5x worse than ShuffleNetV2 in delta terms) but not backbone-eliminated
  (ShuffleNetV2 still lands just past its CI); (3) the positive gains (Shadow ceiling break,
  unseen AUROC, FF++ generalization) appear with BOTH backbones and are often STRONGEST with
  ShuffleNetV2, confirming they are joint-training properties, not RepViT-specific; (4) True Test
  filter recall's CI-beating gain is the one result that does NOT transfer to ShuffleNetV2 —
  looks RepViT-specific; (5) model size/latency clearly favor ShuffleNetV2 (only backbone tried
  that is actually smaller than what it replaces, per ARCH-1's original design goal).
- **Decision: CONTINUE** (same verdict as the previous round, different reasoning). The
  question shifts from "which backbone" to "the joint-training/head-B-conditioning mechanism
  itself has a real, backbone-independent Alibaba/stress cost that must be addressed before
  promoting any unified-backbone candidate." Recommended next step: a training-mechanism
  diagnostic (e.g. sequential two-stage training — head A first, then add head B at low LR or
  with the backbone partially frozen — to test whether decoupling gradient flow removes the
  Alibaba/stress cost while preserving the Shadow/unseen/FF++ gains) BEFORE trying a third
  backbone. If a further backbone swap is still wanted, EfficientNet-Lite0/FastViT
  (`ffpp_improve_20260823`) remain reasonable for an Alibaba/stress-sensitivity sweep, but the
  size/speed motivation for trying them is now moot since ShuffleNetV2 already clears the
  original size/latency bar decisively.
- **Non-claims**: single seed only (both arms); head-B 13.9% missing-file gap reproduced
  identically, not fixed; RepViT-vs-ShuffleNetV2 latency deltas come from separate benchmark
  runs (not the same measurement session), only within-round deltas are exact; does not touch
  `artifact_classifier`/heads C,D; `pipeline.py` and production checkpoints untouched; no FF++ in
  training data; no TFLite export; no third backbone run this round.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated with this isolation
  result and the revised next-step recommendation (training-mechanism investigation before
  further backbone search). No production change.

## ARCH1-MECHANISM-20260826: training-mechanism diagnostic — sequential/frozen training (Arm 1) vs separate-backbone harness control (Arm 2) — CONTINUE, mixed/metric-specific mechanism, confound found in the control

- **Checkpoints**: `checkpoints/research/arch1_mechanism_20260826/` — Arm 1 (sequential/frozen):
  `arch1_seq_SEQ1_afterA.pth` (after stage 1), `arch1_seq_SEQ1_final.pth` (after stage 2),
  `arch1_seq_SEQ1_layer1view.pth`/`arch1_seq_SEQ1_layer2view.pth` (re-keyed gate-harness views);
  Arm 2 (separate backbones): `arch1_sep_SEP1_layer1view.pth`/`arch1_sep_SEP1_layer2view.pth`
  (native `DualBranchModel`-shaped, no re-keying needed). Scripts:
  `AIGuard/train_arch1_sequential_shufflenet.py` (Arm 1), `AIGuard/train_arch1_separate_shufflenet.py`
  (Arm 2), `eval_arch1_unified_gates.py` (reused verbatim, gate logic unchanged; `ROUND_OUT` path
  constant temporarily repointed to this round's folder for the two eval runs, then reverted to its
  checked-in default afterward), `results/research/arch1_mechanism_20260826/bench_latency.py`
  (four-way latency/size). Pre-declaration written before either arm trained:
  `results/research/arch1_mechanism_20260826/PRE_DECLARED.md`. Full findings (tool guard again
  blocked writing FINDINGS.md from inside the executing agent; delivered in that agent's final chat
  message, reproduced in full below).
- **Purpose**: `ARCH1-UNIFIED-20260826` and `ARCH1-ISOLATION-20260826` both showed the same
  pattern regardless of backbone family — real gains (Shadow filter recall ceiling break,
  AIGuard/unseen AUROC, FF++ zero-shot) alongside a fake+filter stress-error regression and an
  Alibaba filter-OOD collapse — and concluded the mechanism is joint multi-task training /
  head-B-conditioning-on-shared-features itself, not backbone choice. This round asks WHY: is it
  the SIMULTANEOUS gradient flow between the two heads' objectives (fixable by training
  sequentially), or feature entanglement from sharing one backbone at all, independent of training
  order (a harder problem)? Arm 1 tests sequential two-stage training (head A to convergence, then
  FREEZE backbone+FFT branch — `requires_grad_(False)` AND `.eval()`, true fixed feature extractor
  — train only head B on top). Arm 2 is a sanity-check control: two fully independent ShuffleNetV2
  backbones (no sharing, no joint loss — architecturally identical to production's own Layer1/
  Layer2 design), retrained from scratch with this round's harness/recipe/data, to confirm the
  harness itself is sound.
- **Data**: identical to both prior rounds, including the same disclosed 20,295/146,425-row (13.9%)
  missing-file drop in `v811_layer2_train.txt` (both arms trained on the same loadable 126,130-row
  subset, fake=52,798/filter=73,332). Same recipe (Adam 1e-4, 10 epochs per stage/model, cosine,
  batch 192, label smoothing 0.1, inverse-frequency class weights, mixup disabled), same seed
  20260826, single seed per arm (diagnostic, not promotion).
- **A confound the pre-declared control caught**: Arm 2 does NOT reproduce v8.17's Alibaba number
  (76.29% vs 97.71%, −21.4pp) despite zero backbone sharing and zero joint loss — architecturally
  it IS production's design, just retrained from scratch with this round's generic recipe. It DOES
  reproduce v8.17's stress error (3.01% vs 2.80%, within CI) and True Test filter recall (89.96% vs
  91.97%, within CI). Conclusion: this round's simplified recipe (Adam 1e-4/10 epochs/ImageNet-
  init/no mixup, used identically across all three ARCH-1 rounds) reproduces production's
  stress/True-Test behavior but NOT its Alibaba cross-algorithm generalization, independent of any
  architecture change — likely because v8.17's actual Layer1 checkpoint used SBI augmentation
  and/or a different training regime this round never replicated. **Per the pre-declared
  interpretation rule, this means Arm 2 (not v8.17) is the correct "no-sharing" baseline for
  isolating what backbone-sharing itself costs**, and the whole comparison is re-read against it.
- **Four-way result** (v8.17 production `p1_r16_layer2_ratio_sweep_20260820/gates_PROD_v817.json` +
  `arch1_unified_20260826/gates_PROD_v817_ffpp_only.json`; Arm 2 this round's `gates_SEP1.json`;
  joint-ShuffleNetV2 `arch1_isolation_20260826/gates_S1_best.json`; Arm 1 this round's
  `gates_SEQ1_best.json`):
  - **Alibaba filter OOD** (informational): 97.71% → Arm 2 (control) 76.29% → joint-ShuffleNetV2
    56.23% (Arm2 −20.06pp) → Arm 1 sequential/frozen 69.51% (Arm2 −6.78pp). **Arm 1 recovers
    roughly two-thirds of the backbone-sharing-attributable Alibaba loss** relative to the correct
    control — genuine partial support for the gradient-interference hypothesis on this metric.
  - **Fake+filter stress error** (gate, v8.17 CI [1.92,3.76]): 2.80% → Arm 2 (control) 3.01% →
    joint-ShuffleNetV2 3.93% (Arm2 +0.92pp, mild) → Arm 1 sequential/frozen **10.18%** (Arm2
    +7.17pp — the WORST result in the entire three-round table on this metric, over 2.5x worse than
    the joint arm it was meant to improve on). Sequencing did not fix stress error — it made it
    dramatically worse, the opposite of the interference hypothesis's prediction for this metric.
  - True Test filter recall (gate, CI [88.35,95.18]): 91.97% → Arm 2 89.96% → joint-ShuffleNetV2
    90.36% → Arm 1 88.76% (all within/near CI, no clean win or loss).
  - True Test fake recall: 99.63% → Arm 2 98.15% → joint-ShuffleNetV2 98.52% → Arm 1 **86.30%**
    (notably worse than all three other arms; paired real_recall also lowest at 58.23% vs Arm 2's
    68.67% despite nominally identical head-A-only training data/recipe/seed — flagged as likely
    partly single-seed RNG-state noise, see Limitations, not solely attributable to the freeze
    mechanism since stage 2 cannot affect head-A's own Layer1 decision at all).
  - Shadow filter recall (informational, ~15.8% ceiling): 12.19% → Arm 2 19.71% → joint-ShuffleNetV2
    24.73% → Arm 1 **31.18%** (second-highest of all architecture-changed arms across all three
    rounds, after joint-RepViT's 36.20% — retained/improved regardless of training order).
  - AIGuard/unseen AUROC (gate): 0.8410 → Arm 2 0.8703 → joint-ShuffleNetV2 0.8802 → Arm 1
    **0.8862** — the single best number across all four arms in this entire three-round
    investigation.
  - FF++ official test video AUROC (informational): 0.5820 → Arm 2 0.6693 → joint-ShuffleNetV2
    0.6861 → Arm 1 0.6431 (all clearly above production; Arm 1 lower than Arm 2/joint but still a
    clear zero-shot gain).
  - **Model size/latency**: Arm 2 (two independent models) 19.42MB / 36.25ms worst-case — parity
    with production's 19.42MB / 37.47ms (confirms this round's harness measurement is consistent
    with production's own numbers modulo the ~3% latency noise seen throughout this line of work).
    Arm 1 (single shared model) 12.22MB / **16.90ms single forward** — smallest and fastest of the
    four arms, same size as joint-ShuffleNetV2 (12.22MB) since architecture is identical, only
    training procedure differs.
- **Mechanistic conclusion — mixed, metric-specific split, not a uniform partial effect**: (1)
  Alibaba filter-OOD generalization is genuinely helped by decoupling gradient flow in time
  (interference hypothesis holds for this metric); (2) fake+filter stress-test performance is
  genuinely HURT by decoupling gradient flow in time, more than by joint training's own compromise
  (opposite of the interference hypothesis for this metric) — plausible explanation: the
  stress-test's adversarial/boundary cases need backbone features actively co-adapted with head-B's
  fine-grained task, which a fully frozen backbone cannot provide, while joint training's
  interference — costly for Alibaba's never-seen-algorithm generalization — is exactly the
  mechanism that lets head-B sharpen features for stress's harder in-domain cases; (3) both point to
  the same underlying fact: head-A's (coarse) and head-B's (fine-grained, cross-algorithm-sensitive)
  tasks want measurably different feature properties from one shared backbone, and neither "fight it
  out simultaneously" (joint) nor "head-A gets everything, head-B gets nothing" (sequential/frozen)
  resolves the conflict — they trade which metric pays the cost, they do not remove it. This is
  feature-entanglement-with-competing-requirements, not a pure gradient-interference-timing problem
  that sequencing alone fixes.
- **Decision: CONTINUE, but do NOT proceed to heads C/D on a single fully-shared backbone (joint
  OR sequential/frozen) without one more diagnostic first.** Recommended next step: a **partially-
  shared architecture** (shared early/mid layers, split later layers or a final block per head) —
  a genuinely different design point from both arms tested across this three-round line, that could
  let head-B develop fine-grained features (addressing stress) while limiting how much head-B's
  gradients perturb the early, more-generalizable layers that appear to matter for Alibaba. Also
  recommend resolving, before further ARCH-1 rounds, WHY this round's generic recipe underperforms
  production's actual training pipeline on Alibaba specifically (mixup? epoch count? SBI
  augmentation?) — this recipe/harness gap needs pinning down so future ARCH-1 baselines are
  trustworthy on their own, not just their deltas relative to each other.
- **Non-claims**: single seed per arm only — diagnostic, not promotion; head-B 13.9% missing-file
  gap reproduced identically, not fixed; does not touch `artifact_classifier`/heads C,D; `pipeline.py`
  and production checkpoints untouched (read-only); no FF++ in training data; no TFLite export;
  partially-shared architecture (the recommended next diagnostic) explicitly NOT run this round;
  Arm 1's True Test real/fake-recall weakness is flagged as plausibly contaminated by single-seed
  RNG-state noise (the extra randomly-initialized, unused `head_b` module in
  `UnifiedDualHeadModel.__init__` shifts subsequent RNG draws relative to Arm 2's single-head model)
  and should not be over-interpreted without a repeat seed.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated with this mechanism-
  diagnostic result and the revised next-step recommendation (partially-shared architecture +
  recipe/harness gap investigation before further single-shared-backbone work). No production
  change.

---

## ARCH1-PARTIAL-20260826: partial-sharing diagnostic — shared trunk (conv1+stage2+stage3), split stage4+conv5 per head — CONTINUE, best-balanced arm so far, mixed on criterion 3 (Shadow)

- **Checkpoints**: `checkpoints/research/arch1_partial_20260826/arch1_partial_P1_best.pth` (full
  partial-sharing state_dict) + `arch1_partial_P1_best_layer1view.pth`/`_layer2view.pth` (re-keyed
  `DualBranchModel`-shaped gate-harness views, `_last` variants also saved). Scripts:
  `AIGuard/train_arch1_partial_shufflenet.py`, `eval_arch1_unified_gates.py` (reused verbatim,
  `ROUND_OUT` temporarily repointed to this round's folder for the eval run then reverted),
  `results/research/arch1_partial_20260826/bench_latency.py` (five-way latency/size). Pre-declared
  before training: `results/research/arch1_partial_20260826/PRE_DECLARED.md`. Full findings (tool
  guard again blocked writing FINDINGS.md from inside the executing agent; delivered in that agent's
  final chat message).
- **Purpose**: `ARCH1-MECHANISM-20260826` found joint/sequential training on a fully-shared backbone
  trades Alibaba/stress against Shadow/unseen/FF++, and explicitly named "partially-shared
  architecture (shared early layers, split later stages per head)" as the next diagnostic. This round
  runs it: for `shufflenet_v2_x1_0` (verified module boundaries by inspection: `conv1` → `maxpool` →
  `stage2` → `stage3` → `stage4` → `conv5` → `mean([2,3])` → `fc`), SHARE the trunk
  (`conv1+maxpool+stage2+stage3`), SPLIT `stage4+conv5` (the deepest, most task-specialized stage,
  464→1024 channels) into two independent per-head copies, each initialized from its own separately
  loaded ImageNet-pretrained instance. FFT branch stays shared (not split, isolating the spatial-
  backbone-splitting variable only). Trained JOINTLY (not sequentially — training order held
  constant so a result cannot be attributed to the already-characterized sequential-training effect).
  Same data/recipe/seed/transforms as all three prior rounds.
- **Data**: identical to all three prior rounds, same disclosed 20,295/146,425-row (13.9%)
  missing-file drop in `v811_layer2_train.txt` reproduced identically, not fixed. Same recipe (Adam
  1e-4, 10 epochs, cosine, batch 192, label smoothing 0.1, inverse-frequency class weights, mixup
  disabled), seed 20260826, single seed (diagnostic, not promotion). Best combined val F1=0.9331 at
  epoch 9 (headA F1=0.901, headB F1=0.965). Export verified byte-for-byte key-match against
  `eval_arch1_unified_gates.py`'s `DualBranchModel` (363/363 keys, 0 missing/extra) before training.
- **Five-way result** (v8.17 production; Arm 2 corrected baseline from `arch1_mechanism_20260826/
  gates_SEP1.json`, reused verbatim not rerun; joint-shared from `arch1_isolation_20260826/
  gates_S1_best.json`; Arm 1 sequential/frozen from `arch1_mechanism_20260826/gates_SEQ1_best.json`;
  this round's `gates_partial_best.json`):
  - **Alibaba filter OOD**: 97.71% → Arm 2 76.29% → joint-shared 56.23% (Arm2 −20.06pp) → Arm 1
    69.51% (Arm2 −6.78pp) → **partial-sharing 65.67% (Arm2 −10.62pp)** — partial recovers roughly
    half of full joint sharing's Alibaba loss relative to the Arm-2 corrected baseline, less full a
    recovery than Arm 1's sequential training but without Arm 1's stress cost (next line).
  - **Fake+filter stress error** (v8.17 CI [1.92,3.76]): 2.80% → Arm 2 3.01% → joint-shared 3.93% →
    Arm 1 **10.18%** → **partial-sharing 2.75%** — the BEST of all five arms including production
    itself. Splitting only the deepest stage removes essentially all of the joint-training stress
    cost. stressdev (20-condition robustness) also best-of-series at 1.49% vs Arm 2's 1.91%.
  - Shadow filter recall (informational, ~15.8% ceiling): 12.19% → Arm 2 19.71% → joint-shared
    24.73% → Arm 1 31.18% → **partial-sharing 19.00%** — essentially FLAT vs the Arm-2 control
    (statistically tied, arguably slightly below), i.e. this split gives ZERO incremental Shadow
    benefit over a plain separate-backbone retrain, sharply unlike joint/Arm 1 (both of which fully
    share stage4+conv5 and both clearly beat Arm 2 on this metric). The clearest asymmetry in the
    whole five-way table.
  - AIGuard/unseen AUROC (gate): 0.8410 → Arm 2 0.8703 → joint-shared 0.8802 → Arm 1 0.8862 →
    **partial-sharing 0.8795** — gain over v8.17 (+0.0385) exceeds Arm 2's own control gain
    (+0.0293) by +0.92pp, i.e. genuine incremental architectural benefit, not just recipe.
  - True Test filter recall (gate, CI [88.35,95.18]): 91.97% → Arm 2 89.96% → joint-shared 90.36% →
    Arm 1 88.76% → **partial-sharing 92.37%** — the single BEST result across all five arms in this
    entire four-round investigation, including production.
  - FF++ zero-shot end2end AUROC: 0.5597 → Arm 2 0.6648 → joint-shared 0.6762 → Arm 1 0.6306 →
    partial-sharing 0.6683 (gain +0.1086 over v8.17, exceeds Arm 2's +0.1051); fake-catch rate 63.83%
    is best-of-the-four-shared/split-arms (Arm 2's 69.17% remains highest overall but Arm 2 is the
    no-sharing control). FF++ official-test video AUROC 0.6954, highest of all measured this round
    series. **No leakage caveat**: the parallel `ffpp_leakage_audit_20260826` completed during this
    round with VERDICT: NO LEAKAGE (0 exact-pixel matches, 64,913×34,307 comparisons) — these FF++
    numbers are reported without caveat.
  - **Model size/latency**: partial-sharing 15.98MB / 20.52ms single forward — less saving than the
    fully-shared arms (12.22MB / 17.6–18.4ms, since two independent stage4+conv5 tails add back
    roughly half the split-off parameters) but a clear, meaningful win over the two-model production
    subset (19.42MB / 37.41ms worst-case): −17.7% size, −45.2% worst-case latency.
- **Mechanistic conclusion — the two failure/gain modes attach to DIFFERENT parts of the shared
  representation, not one undifferentiated entanglement**: splitting only the deepest stage
  (`stage4+conv5`) while keeping `stage2+stage3` shared (1) fully removes the stress-error cost and
  most of the Alibaba cost, while (2) fully removing the Shadow-domain-gap benefit as well. This
  means "different heads want different deep features" (this round's motivating hypothesis) is only
  PART of the story — it correctly predicts the Alibaba/stress fix, but the SAME deep-layer
  entanglement that hurts Alibaba/stress is apparently the mechanism that helps Shadow. There may be
  no single split point on this shared-early/split-late axis that captures the safety-critical gains
  (Alibaba, stress) without giving up the Shadow domain-gap gain.
- **Decision: CONTINUE, but do NOT yet recommend partial-sharing unconditionally for heads C/D.**
  Per the pre-declared four-criteria test, 3 of 4 hold cleanly (Alibaba recovery vs joint, stress
  safety, size/latency); criterion 3 (Shadow/unseen/FF++ retention) is a genuine mixed result — unseen
  and FF++ are retained/improved, Shadow is not. This is the best-balanced single-shared-backbone
  architecture built across all four ARCH-1 rounds (best stress error and best True Test filter
  recall of ALL FIVE arms including production), but it explicitly does not deliver the Shadow
  domain-gap improvement that was one of ARCH-1's three original motivations. Two concrete next
  steps, both recommended before any heads-C/D commitment: (1) the recipe-gap confound from
  `ARCH1-MECHANISM-20260826` remains unresolved — Arm 2 (separate backbones, this round-series'
  generic recipe) still only reaches 76.29% Alibaba vs production's real 97.71%; transplanting
  production's actual recipe (SBI augmentation is the leading candidate) into the separate-backbone
  control before further architecture variants would raise the floor every future comparison is
  measured against; (2) only one split point (`stage4+conv5`) was tested — a shallower split (e.g.
  share only `stage2`) would trace more of the Alibaba/stress-vs-Shadow trade-off curve, not run
  this round.
- **Non-claims**: single seed only — diagnostic, not promotion; head-B 13.9% missing-file gap
  reproduced identically, not fixed; does not touch `artifact_classifier`/heads C,D; `pipeline.py`
  and production checkpoints untouched (read-only); no FF++ in training data (zero-shot eval only,
  confirmed leakage-free by the concurrent audit); no TFLite export; Arm 2 reused verbatim, not
  rerun; only one split point tested, other split points (shallower/deeper) named as future work.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated with this round's result
  and the revised recommendation (resolve the recipe-gap confound before further architecture
  variants; partial-sharing named as the current best-balanced candidate with an explicit,
  unresolved Shadow trade-off). No production change.

---

## ARCH1-RECIPE-GAP-20260826: recipe-gap diagnostic — why Arm 2 (separate-backbone harness control) only reaches 76.29% Alibaba vs production's real 97.71% — RESOLVED, single-variable fix fully closes the gap (with a newly-surfaced side effect)

- **Purpose**: `ARCH1-MECHANISM-20260826` and `ARCH1-PARTIAL-20260826` both flagged the same
  unresolved confound: Arm 2 (`train_arch1_separate_shufflenet.py`, tag `SEP1`) uses production's
  OWN architecture (two fully independent ShuffleNetV2 `DualBranchModel` backbones, no sharing, no
  joint loss) but retrained from scratch with the ARCH-1 series' generic harness, and only reached
  Alibaba filter OOD recall 76.29% — a 21.4pp shortfall from production's real, audited 97.71%
  (`docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md` §2). Since architecture is held
  constant, this had to be a recipe or data gap, muddying every prior ARCH-1 round's use of Arm 2 as
  an implicit "should reproduce production" sanity anchor. This round diagnoses and quantifies it.
- **Method**: read the real production training scripts side-by-side with the ARCH-1 generic
  harness. Found: `AIGuard/train_p1_r9_layer1.py` (produces `shufflenet_v2_layer1_v817sbi.pth`, the
  deployed SBIAUG arm) warm-starts by fully loading `shufflenet_v2_layer1_v811d.pth` (prior
  production lineage), and `AIGuard/train_v811_layer2.py` (produces `shufflenet_v2_layer2_v811.pth`,
  still production) warm-starts by partially loading `shufflenet_v2_3class_v88.pth`
  (spatial_branch+fft_branch only). All four prior ARCH-1 rounds' harness instead builds every model
  from vanilla `torchvision` `IMAGENET1K_V1` weights. Data was checked and ruled out as the primary
  confound: Arm 2's L1 split (`layer1_prod_only_filtered_train.txt`) was confirmed via
  `grep -c "SBI-"` to already contain the same 22,297 SBI pseudo-fake rows production's SBIAUG arm
  uses; the only data gap is the missing 22,297 degradation-matched real negatives (production's
  "Round 3 fix", named as a lower-ranked candidate, not tested this round). Ranked five candidate
  causes in `PRE_DECLARED.md` (init > LR/epochs [entangled with init, not independently testable] >
  mixup > missing real negatives > batch size) and ran ONE single-variable confirming rerun of the
  top-ranked hypothesis: `AIGuard/train_arch1_recipe_gap_warmstart.py` (tag `RECIPEGAP1`), an exact
  copy of Arm 2's script with ONLY the init logic changed to warm-start from the same two production
  checkpoints (L1 full load of `v811d`, L2 partial load of `v88`) — LR=1e-4, epochs=10, batch=192,
  mixup disabled, data files, transforms, architecture, class-weight formula all held identical to
  Arm 2. Single seed (20260826), diagnostic per mission scope.
- **Result — Alibaba gap fully closed**: 76.29% → **98.23%** (production real: 97.71%), a
  single-variable fix that not only closes the entire 21.4pp gap but lands 0.52pp above production.
  Confirms RANK 1: backbone initialization from the accumulated project lineage (not architecture,
  not mixup, not the missing real negatives, not LR/epoch choice) is the dominant driver of
  production's real Alibaba cross-algorithm filter generalization number.
- **Full three-way comparison** (production v8.17 | Arm 2 `SEP1` [ImageNet init] | `RECIPEGAP1`
  [warm-start init]): Alibaba 97.71 | 76.29 | **98.23** (gap closed); True Test fake recall 99.63 |
  98.15 | **99.63** (matches prod exactly); True Test filter recall 91.97 | 89.96 | **92.77**
  (improved over both); fake+filter stress error **2.80 | 3.01 | 4.33** (regressed vs BOTH — new
  finding, see below); AIGuard-unseen AUROC 0.8410 | 0.8703 | 0.8242 (regressed vs both, still clears
  the ≥0.80 gate); CelebA real recall 99.33 | 98.67 | 98.00 (regressed vs both, still clears ≥95);
  Shadow filter recall 12.19 | 19.71 | 15.77 (partial retention of Arm 2's ceiling-break); StyleGAN2
  decontam 97.57 (Arm2) → 98.97 (improved). Full table + provenance:
  `results/research/arch1_recipe_gap_20260826/gates_RECIPEGAP1.json`,
  `results/research/arch1_mechanism_20260826/gates_SEP1.json` (Arm 2 baseline reused, not rerun).
- **New finding, not predicted in advance**: the same single-variable fix that closes Alibaba makes
  fake+filter stress error WORSE, not better (4.33% vs Arm 2's 3.01%, prod's 2.80%). Plausible
  mechanism: production's real recipe pairs warm-start init WITH the 22,297 degradation-matched real
  negatives (rank 4, the change proposal's "Round 3 fix", explicitly framed there as addressing a
  real-vs-fake+filter confusion risk); this round's single-variable test deliberately did not add
  that data (kept Arm 2's data untouched to isolate init alone), so warm-starting a strong prior
  manipulation-detector onto data missing the specific negatives meant to counter that exact failure
  mode plausibly exposes it more, not less. Named as the clear next diagnostic (two-variable: warm
  start + full SBIAUG augreal data), not run this round (out of single-variable scope).
- **Verdict**: RESOLVED for the Alibaba-specific recipe-gap confound flagged by
  `ARCH1-MECHANISM-20260826` and `ARCH1-PARTIAL-20260826` — quantified, attributed to a single
  element, and closed with a minimal fix. All four prior ARCH-1 rounds' INTERNAL comparisons
  (candidate vs Arm 2, joint arms vs each other) remain valid as self-consistent comparisons; only
  the implicit "Arm 2 ≈ production" framing used as a sanity anchor in those rounds should be read
  with this caveat now resolved — Arm 2's low Alibaba was a harness-init artifact, not evidence about
  backbone-sharing or joint training. Practical implication: any future ARCH-1 round wanting a
  believable "should reproduce production" anchor should warm-start separate-backbone controls from
  the same lineage checkpoints, not ImageNet; this also raises the bar for what "keeping Shadow/
  unseen/FF++ gains without an Alibaba/stress cost" needs to look like against a ~97-98% Alibaba
  floor (not Arm 2's uncorrected 76.29%) in any future round that reuses Arm 2 as a baseline.
- **Non-claims**: single seed, diagnostic only — not a promotion decision; `pipeline.py` and
  production checkpoints untouched (read-only inputs); does not test ranks 2 (LR/epochs, entangled
  with init), 3 (mixup), or 5 (batch size) in isolation, per mission's single-variable scope; does
  not add the missing degradation-matched real negatives to address the newly-observed stress-error
  side effect (named as follow-up, not run); does not fix the pre-existing head-B 13.9% missing-file
  data gap (reproduced identically); no TFLite export; no git commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated noting this resolves the
  recipe-gap caveat from `ARCH1-MECHANISM-20260826`/`ARCH1-PARTIAL-20260826`, with the newly-surfaced
  stress-error side effect named as follow-up. No production change.

---

## ARCH1-FINAL-20260826: promotion-candidate round — partial-sharing architecture + full production recipe (warm-start init) combined — **NO-GO** for this combination; overall ARCH-1 line verdict **CONTINUE**

- **Checkpoints**: `checkpoints/research/arch1_final_20260826/arch1_final_FINAL1_best.pth` (full
  partial-sharing state_dict, warm-started) + `_best_layer1view.pth`/`_layer2view.pth` (re-keyed
  gate-harness views, `_last` variants also saved). Scripts: `AIGuard/train_arch1_final_shufflenet.py`
  (new this round), `eval_arch1_unified_gates.py` (reused verbatim, `ROUND_OUT` temporarily repointed
  then reverted), `results/research/arch1_final_20260826/bench_latency.py` (six-way latency/size).
  Pre-declared before training: `results/research/arch1_final_20260826/PRE_DECLARED.md`. Full findings
  (tool guard again blocked writing FINDINGS.md from inside the executing agent; delivered in that
  agent's final chat message and summarized here).
- **Purpose**: promotion-candidate-level round (not diagnostic) combining the two independently-
  validated fixes from the prior two rounds: `ARCH1-PARTIAL-20260826`'s partial-sharing architecture
  (shared trunk `conv1+maxpool+stage2+stage3`, independent `stage4+conv5` per head) + `ARCH1-RECIPE-
  GAP-20260826`'s warm-start-init recipe fix, PLUS production's real LR/epochs/batch/mixup settings
  (not ARCH-1's generic recipe) and Head A trained on production's actual full Layer1 split.
- **Data-provenance correction found during setup**: the mission's premise — that ~22,297
  "degradation-matched real negative" rows were missing from Arm 2's Layer1 split and this was the
  likely cause of `ARCH1-RECIPE-GAP-20260826`'s stress-error regression — was checked directly and
  found **factually wrong**. `grep -c` on both `SBI-` (fake pseudo rows) and `SBIaugreal-` (real
  negative rows) sources returns 22,297 in BOTH Arm 2's split and production's real split — Arm 2
  already contained all of the real negatives. The verified true diff is only 1,353 rows, all
  label=1 (fake), from two hard-negative-mining sources (`v89d-mined-hardneg` 1,050 +
  `v811-round2-mined` 303). This round trains Head A on production's actual full split
  (`splits/research/p1_r9_sbi_pilot_20260819/layer1_sbi_augreal_train.txt`, 238,026 unique rows) to
  close the real (much smaller) gap correctly, rather than acting on the incorrect premise.
- **Warm-start choice, documented tension**: production's Layer1/Layer2 are two separate fine-tuned
  backbones with no shared trunk to copy directly. This round initializes the shared trunk + head A's
  tail from `v811d` (Layer1's lineage — the coarser, more foundational task), and head B's tail from
  `v88`'s stage4/conv5 (matching `train_v811_layer2.py`'s own choice) — explicitly noting head B's
  tail must re-adapt to a Layer1-flavored trunk it was not originally co-trained with.
- **Recipe**: LR=2e-5 (not ARCH-1's 1e-4), batch=256 (not 192), mixup enabled 50%/alpha=0.2 (first
  ARCH-1 round to enable it, all prior rounds explicitly disabled it), 15 joint epochs (production
  trains L1 for 5 and L2 for 15 as SEPARATE runs; a single joint schedule cannot reproduce both, so
  head A sees 3x more epochs than production's L1 budget — a disclosed deviation named as a possible
  confound, not resolved this round).
- **Result vs the four pre-declared criteria**:
  - (a) Alibaba filter OOD recall: **98.32%** — clears production's bootstrap 95% CI upper bound
    [97.50, 97.91]. **PASS**, confirms `ARCH1-RECIPE-GAP-20260826`'s warm-start fix generalizes to
    the partial-sharing architecture (previously only tested on the separate-backbone Arm 2).
  - (b) fake+filter stress error: **5.68%** (misclassified 130/2,289) — more than 1.5x beyond
    production's CI [1.92, 3.76], and WORSE than `ARCH1-RECIPE-GAP-20260826`'s own already-failing
    4.33%. **FAIL, clearly.** Concentrated almost entirely in two conditions: `eye_enlarging` (16.78%
    error, n=286) and `whitening_medium` (14.63%, n=287) — together 90/130 (69%) of all
    misclassifications; near-zero (<1%) on `combined_*`/`smoothing_*` conditions, so this is NOT a
    globally miscalibrated head B, it is a re-activation of the two specific filter types
    `v811d`'s lineage has the deepest prior exposure to via years of fake+filter hard-negative mining.
  - (c) Retain partial-sharing-generic's wins: True Test filter recall **91.16%** (-1.2pp vs
    partial-generic's 92.37%, still near target); size **15.98MB** / latency **19.21ms** worst-case
    (identical to partial-generic since architecture is unchanged, still -17.7%/-44% vs production's
    19.42MB/34.26ms). **PASS.**
  - (d) FF++ zero-shot AUROC meaningfully above production: end2end **0.6267** (900f) / **0.6257**
    (official 6,620f) vs production's 0.5597/0.5738 — +6.7pp/+5.2pp, clears the bar, but below
    partial-sharing-generic's own 0.6683/0.6656 (-4.2pp/-4.0pp). **PASS** (weaker than architecture
    alone, still clearly above production).
- **Verdict for this combination**: **NO-GO**. (a), (c), (d) pass but (b) fails clearly and by a
  wide margin — per the pre-declared interpretation rule, one clear-fail criterion is sufficient for
  NO-GO regardless of the other three passing.
- **Mechanistic read (pattern now observed twice, growing in magnitude)**: this is the SECOND
  round where closing the Alibaba gap via warm-start has cost stress error, and the cost has grown:
  `ARCH1-RECIPE-GAP-20260826` (separate backbones + warm-start): Alibaba 76.29%→98.23%, stress
  3.01%→4.33% (+1.32pp). This round (partial-sharing + warm-start): Alibaba 65.67%→98.32%, stress
  2.75%→5.68% (+2.93pp — more than double the prior round's regression). Partial-sharing's
  architectural benefit (which ALONE kept stress at 2.75%, best of any arm across all six) and
  warm-start's Alibaba benefit are not simply additive when combined — the combination appears to
  activate a worse failure mode than either fix alone, concentrated specifically in the two filter
  types the warm-started trunk has the most historical exposure to. Not resolved this round: whether
  a shallower warm-start (trunk only, tails ImageNet-init), a blended trunk init, or a corrected
  per-head epoch schedule (production's real 5/15 split rather than this round's joint 15/15) would
  recover Alibaba without reactivating this failure mode — named as follow-up, not run.
- **Six-way final comparison table** (v8.17 production | Arm 2 separate-generic | joint-shared |
  sequential-frozen (Arm 1) | partial-sharing-generic | this round): Alibaba 97.71/76.29/56.23/
  69.51/65.67/**98.32**; stress error 2.80/3.01/3.93/10.18/2.75/**5.68**; True Test filter recall
  91.97/89.96/90.36/88.76/92.37/**91.16**; True Test fake recall 99.63/98.15/98.52/86.30/97.78/
  **98.89**; Shadow filter recall (not a criterion) 12.19/19.71/24.73/31.18/19.00/**21.15**; AIGuard/
  unseen AUROC 0.8410/0.8703/0.8802/0.8862/0.8795/**0.8366**; FF++ zero-shot end2end AUROC
  0.5597/0.6648/0.6762/0.6306/0.6683/**0.6267**; FF++ official-test end2end AUROC
  0.5738/0.6488/0.6560/0.6140/0.6656/**0.6257**; size 19.42MB(2 models)/19.42MB/12.22MB/12.22MB/
  15.98MB/**15.98MB**; CPU worst-case latency 34.26/33.36/16.71/17.28/19.12/**19.21ms**. Full table
  with sources in the executing agent's final message / `results/research/arch1_final_20260826/
  bench_latency_out.txt` + `gates_FINAL1_best.json`.
- **Overall ARCH-1 multi-round research line verdict: CONTINUE (not GO)**. Five rounds
  (unified→isolation→mechanism→partial→final) have cleanly established: partial-sharing is the best
  architecture found on its OWN generic recipe (best stress error and best True Test filter recall of
  any arm including production); warm-start reliably closes the Alibaba gap but reliably costs stress
  error, worse when stacked with partial-sharing than with separate backbones. The "best" ARCH-1
  recipe so far is a genuine two-horn trade-off, not yet a clean win over production on all four
  criteria simultaneously. Do NOT proceed to heads C/D on this round's checkpoint. Next step (not run
  this round): disentangle warm-start's Alibaba benefit from its stress cost (shallower warm-start /
  blended trunk / corrected per-head epoch schedule) before any architecture is carried into heads
  C/D. No production `pipeline.py` or checkpoint change without the user's explicit review, regardless
  of verdict (standing rule).
- **Non-claims**: single seed only (promotion-candidate scope per mission, not multi-seed confirmed —
  named as required follow-up before any actual production swap); does not touch `artifact_classifier`/
  heads C,D; `pipeline.py` and production checkpoints untouched (read-only); no TFLite export;
  head-B 13.9% missing-file gap reproduced identically, not fixed; joint 15-epoch schedule for head A
  (vs production's real 5) is a disclosed, unresolved deviation; no git commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated with this round's NO-GO
  result and the overall CONTINUE verdict for the ARCH-1 line. No production change.

---

## ARCH1-SHALLOWWS-20260826: warm-start decomposition — three named candidates (shallow trunk-only, LR-decoupled tails, blended trunk) — **all three NO-GO**; ARCH-1 line verdict remains **CONTINUE**

- **Checkpoints**: `checkpoints/research/arch1_shallow_ws_20260826/arch1_shallow_ws_SHALLOW1_best*.pth`
  (Candidate 1), `arch1_lrtail_LRTAIL1_best*.pth` (Candidate 2), `arch1_blend_BLEND1_best*.pth`
  (Candidate 3), each with re-keyed `_layer1view`/`_layer2view` gate-harness exports and `_last`
  variants. Scripts (new this round): `AIGuard/train_arch1_shallow_ws_shufflenet.py`,
  `AIGuard/train_arch1_lrtail_shufflenet.py`, `AIGuard/train_arch1_blend_shufflenet.py`.
  `eval_arch1_unified_gates.py` reused via three per-candidate copies with `ROUND_OUT` repointed to
  this round's output dir (`eval_arch1_{shallow_ws,lrtail,blend}_gates.py`), no gate-logic changes.
  Pre-declared before Candidate 1 training: `results/research/arch1_shallow_ws_20260826/PRE_DECLARED.md`.
  Full findings (tool guard blocked writing FINDINGS.md from inside the executing agent; delivered in
  that agent's final chat message, summarized here).
- **Purpose**: `ARCH1-FINAL-20260826` closed the Alibaba gap (98.32%) via full warm-start but broke
  fake+filter stress error (5.68%), with damage concentrated 69% in exactly two conditions —
  `eye_enlarging` (16.78%) and `whitening_medium` (14.63%) — leading to a hypothesis that the
  warm-started `v811d` trunk's deep prior (years of production fake+filter hard-neg mining on exactly
  those two filter types) was reactivated by the new partial-sharing architecture. This round tests
  three named decompositions of the warm-start to locate and isolate that prior, in order of
  cost/benefit, with a pre-declared stop-on-first-pass rule.
- **Production epoch-schedule check (informs Candidate 2's design, done before training)**: direct
  inspection of `AIGuard/train_v811_layer1.py`/`train_v811_layer2.py` found BOTH already use
  `EPOCHS=15, LR=2e-5` — identical to what `ARCH1-FINAL-20260826` used. The mission's premise that
  production "likely" used fewer epochs when fine-tuning from an already-converged checkpoint is
  **factually wrong**; there is no epoch-count mismatch to correct. Candidate 2 was reinterpreted per
  the mission's stated fallback ("and/or a lower LR specifically for the deep tails") as an
  LR-decoupled variant rather than a no-op epoch change.
- **Candidate 1 (shallow warm-start — trunk only, both tails at vanilla ImageNet init)**:
  Alibaba **90.94%** (FAILS criterion a, 7pp below CI lower bound [97.50,97.91] and 7.4pp below
  `ARCH1-FINAL`'s 98.32% — the trunk-only prior is NOT sufficient to reproduce the Alibaba fix,
  meaning a meaningful share of the Alibaba benefit lives in the tails, not just the shared
  low/mid-level trunk features). Stress overall **4.54%** (still FAILS criterion b, CI [1.92,3.76],
  though best of the three candidates and better than `ARCH1-FINAL`'s 5.68%). Critically, the two
  named conditions respond in OPPOSITE directions: `eye_enlarging` improves 16.78%→10.49% (-6.3pp,
  supports "eye_enlarging failure is tail-driven"), but `whitening_medium` WORSENS 14.63%→15.68%
  (+1.1pp, directly contradicts the same hypothesis for whitening) — the two conditions do not share
  a single locus despite being named together in `ARCH1-FINAL`'s FINDINGS.
- **Candidate 2 (LR-decoupled full warm-start — same sources as `ARCH1-FINAL`, tails at 10x lower LR
  2e-6, trunk+fft at full 2e-5, fresh heads at 5x higher LR 1e-4)**: Alibaba **98.32%** (PASSES
  criterion a, essentially identical to `ARCH1-FINAL` to 2 decimals — confirms the trunk, not
  training speed, is the dominant Alibaba driver). Stress overall **4.94%** (FAILS criterion b, only
  a 0.74pp improvement over `ARCH1-FINAL`'s 5.68%). Concentration essentially unchanged:
  `eye_enlarging` 16.78%→13.99%, `whitening_medium` 14.63%→14.29% (both still ~2-3x the CI midpoint).
  10x tail-LR reduction was not aggressive enough to meaningfully slow reactivation, OR the damage is
  baked in at initialization rather than accumulated through this round's 15-epoch training dynamics.
- **Candidate 3 (blended trunk init — elementwise mean of `v811d` and `v88`'s conv1/stage2/stage3,
  246/246 keys verified shape-identical before training; tails unchanged from `ARCH1-FINAL`)**:
  Alibaba **98.41%** (PASSES criterion a, best of all ARCH-1 rounds — consistent with Candidate 1's
  finding that the trunk carries most of the Alibaba signal, and blending two production-adapted
  trunks doesn't hurt it). Stress overall **5.46%** (FAILS criterion b, second-worst of ALL ARCH-1
  rounds after `ARCH1-FINAL` itself). `eye_enlarging` **17.13%** — the WORST measured in the entire
  ARCH-1 research line to date, exceeding even `ARCH1-FINAL`'s 16.78%. Blending did not dilute the
  problematic prior; averaging two independently-adapted trunks while keeping tails matched to
  neither (an even weaker lineage match for both tails than `ARCH1-FINAL`'s single-lineage choice)
  appears to compound rather than mitigate the trunk-tail mismatch. Directionally the opposite of
  this candidate's premise.
- **Cross-candidate synthesis**: none of the three interventions cleanly separates "which sub-module
  carries the failure." (1) Trunk alone is insufficient for either full Alibaba benefit or full
  stress damage — both need the tails too. (2) `eye_enlarging` and `whitening_medium` respond
  DIFFERENTLY to the same trunk-only intervention (one improves, one worsens) — they are likely two
  mechanistically distinct regressions coincidentally both large, not one shared failure mode, despite
  jointly accounting for 69% of `ARCH1-FINAL`'s misclassifications. (3) Slowing tail-adaptation speed
  (Candidate 2) barely moves stress error, suggesting the damage is substantially baked in at
  initialization rather than accumulated via this round's training dynamics. (4) Blending trunk
  sources (Candidate 3) makes eye_enlarging worse, ruling out "single-checkpoint overfitting" as the
  trunk-side explanation. Most likely untested explanation: the NEW trunk/tail PAIRING itself
  (head B's tail, co-adapted with `v88`'s trunk in production, now sitting on a `v811d`-flavored or
  blended trunk it was never co-trained with — the "architectural tension" `ARCH1-FINAL`'s
  PRE_DECLARED.md already flagged) may need either many more epochs to re-adapt, or a same-lineage
  warm-start for both tails (untested in any of the eight ARCH-1 rounds so far), or acceptance that
  partial-sharing's benefit and warm-start's benefit are architecturally in tension for ShuffleNetV2
  partial-sharing specifically.
- **Verdict**: **NO-GO for all three candidates.** Per the pre-declared stopping rule, testing ended
  after Candidate 3 (no candidate passed early, and Candidate 3 was the last named candidate).
- **Overall ARCH-1 multi-round research line verdict: CONTINUE (not GO), unchanged from
  `ARCH1-FINAL-20260826`**. Eight total rounds (unified→isolation→mechanism→partial→final→this
  round's three candidates) have now tested every warm-start decomposition the prior round's FINDINGS
  named as follow-up, without resolving the trade-off. Two credible next steps, neither run this
  round: (1) warm-start BOTH tails from the SAME lineage (`v811d` only, dropping `v88` for head B) to
  remove the trunk-tail pairing mismatch entirely — a cheap single-variable test not yet tried; (2)
  deprioritize further ARCH-1 warm-start tuning in favor of other `MASTER_PLAN` research lines,
  revisiting only with a genuinely new mechanistic idea. Do NOT proceed to heads C/D. No production
  `pipeline.py`/checkpoint change without the user's explicit review (standing rule).
- **Non-claims**: single seed per candidate (diagnostic-tier); `pipeline.py`/production checkpoints
  untouched (read-only, verified — only files touched are under
  `checkpoints/research/arch1_shallow_ws_20260826/`, `results/research/arch1_shallow_ws_20260826/`,
  and the three new `AIGuard/train_arch1_*.py` scripts); no TFLite export; head-B 13.9% missing-file
  gap reproduced identically; full `bench_latency.py` not re-run (architecture identical to
  `ARCH1-PARTIAL-20260826`'s `PartialSharedModel` in all three candidates, so that round's size
  19.42MB / latency 37.41ms-worst-case-vs-production numbers apply unchanged); no git commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated with this round's three
  NO-GO results and the unchanged CONTINUE verdict. No production change.

---

## ARCH1-LINEAGE-20260826: last exploratory round — "head-B-native trunk" (Variant A) vs "no shared trunk, matched lineage" (Variant B, reused from RECIPEGAP1) — **Variant A NO-GO; shared-backbone research line CLOSED**

- **Checkpoints**: `checkpoints/research/arch1_lineage_20260826/arch1_lineage_LINEAGE_A_best*.pth`
  (+ `_layer1view`/`_layer2view` gate-harness exports, `_last` variants). Script (new this round):
  `AIGuard/train_arch1_lineage_shufflenet.py`. `eval_arch1_unified_gates.py` reused via one copy with
  `ROUND_OUT` repointed to this round's output dir
  (`results/research/arch1_lineage_20260826/eval_arch1_lineage_gates.py`), no gate-logic changes.
  Pre-declared before training: `results/research/arch1_lineage_20260826/PRE_DECLARED.md`. Full
  findings (tool guard blocked writing `FINDINGS.md` from inside the executing agent, same as
  `ARCH1-ISOLATION/MECHANISM/PARTIAL/SHALLOWWS-20260826`; delivered in that agent's final chat
  message, summarized here).
- **Purpose**: `ARCH1-SHALLOWWS-20260826` named one untested hypothesis after eight rounds — every
  prior round warm-started the SHARED TRUNK from `v811d` (Layer1's own lineage) or a `v811d`-containing
  blend, always forcing head B's tail onto a trunk it was never co-adapted with, while head A always
  got a native trunk. This round tests whether flipping that asymmetry (give head B the native trunk
  instead) fixes the concentrated `eye_enlarging`/`whitening_medium` stress failure, alongside an
  honest separate-model fallback.
- **Variant A ("head-B-native trunk")**: identical `PartialSharedModel` architecture and recipe to
  `ARCH1-FINAL-20260826` (LR=2e-5, 15 epochs, batch=256, mixup 50%/alpha=0.2, seed=20260826, Head A on
  full production Layer1 split, Head B on `v811_layer2_train.txt`); ONLY the warm-start source changed:
  shared trunk (`conv1/stage2/stage3`) + `fft_branch` now from `v88` (not `v811d`), head B tail
  (`stage4_b/conv5_b`) unchanged from `v88` (now NATIVE to its trunk for the first time in 9 rounds),
  head A tail (`stage4_a/conv5_a`) unchanged from `v811d` (now the FOREIGN pairing instead). Warm-start
  load verified clean: 449/449 shape-matched tensors loaded, 0 skipped.
  **Results**: (a) Alibaba filter OOD **98.49%** — PASSES, best of all 9 ARCH-1 rounds, exceeds
  production's bootstrap CI [97.50,97.91]. (b) fake+filter stress error **5.37%** — FAILS, CI
  [1.92,3.76]; `eye_enlarging` **16.78%**, numerically IDENTICAL to `ARCH1-FINAL`'s 16.78% to 2
  decimals despite completely reversing which lineage supplies the trunk; `whitening_medium` **13.94%**
  (vs `ARCH1-FINAL`'s 14.63%, -0.7pp, still ~4x the CI upper bound). (c) True Test filter recall
  (paired) 91.97% — PASSES (~92% target); model size **15.98MB** (-17.7% vs production's two-model
  19.42MB) — PASSES; CPU worst-case latency **21.97ms single forward** (-40.2% vs production's
  36.70ms) — PASSES. (d) FF++ zero-shot AUROC end2end **0.6257** (900f) / **0.6257** (official 6,620f)
  vs production's 0.5597/0.5738 — PASSES. **Verdict: (a)(c)(d) PASS, (b) FAIL -> NO-GO** (single
  failing criterion is NO-GO per the standing ARCH-1 rule, regardless of the other three).
- **Decisive finding**: reversing the ENTIRE trunk lineage (v811d->v88) — the last untested variable
  in the trunk-tail-pairing hypothesis — left `eye_enlarging` completely unchanged (16.78% both times)
  and moved `whitening_medium` only 0.7pp. This directly falsifies the "head B's tail is misaligned
  with a foreign trunk" mechanism as the (sole) driver: giving head B a fully coherent, single-lineage
  native trunk+tail pairing (exactly matching how production's real Layer2 was built) did not shrink
  the failure materially. Combined with `ARCH1-SHALLOWWS-20260826`'s three candidates (shallow
  trunk-only, LR-decoupled, blended-trunk — all NO-GO, inconsistent per-condition response), all five
  named mechanisms for the failure (lineage source, warm-start depth, LR, blend ratio, and now
  trunk-tail pairing symmetry) have been individually isolated and ruled out. The only shared-backbone
  configuration across all 9 rounds that ever cleared the stress criterion is
  `ARCH1-PARTIAL-20260826`'s ImageNet-only (no warm-start) control (2.75%, PASS) — which fails Alibaba
  badly instead (65.67%). No combination of "warm-start enough to fix Alibaba" with "any tested
  lineage/pairing" has cleared stress in nine attempts.
- **Variant B ("no shared trunk, matched lineage")**: NOT retrained — reused directly from
  `ARCH1-RECIPE-GAP-20260826`'s `RECIPEGAP1` (fully separate Layer1/Layer2 backbones, both warm-started
  from their own correct lineage: L1<-`v811d`, L2<-`v88`), per explicit mission instruction since that
  round is complete and already answers the "correct-lineage, no sharing" question. Its numbers: Alibaba
  98.23%, stress error **4.33%** (still fails CI [1.92,3.76], but the least-damaged stress number of
  ANY warm-started configuration across all 9 rounds — every warm-started shared/partial-shared variant
  falls in a 4.54-5.68% band), True Test filter recall (paired) 92.77%, FF++ zero-shot end2end
  0.6375(900f)/0.6407(official) — both exceed Variant A's 0.6257/0.6257 slightly. Model count/size:
  2 separate models, 19.42MB (+0.00MB vs production, no size win — architecturally identical to
  production, this was never expected to shrink).
- **Final mechanistic read (per PRE_DECLARED.md's decision menu)**: (1) no shared or partial-shared
  backbone design tested in 9 rounds (joint, sequential/frozen, and partial-sharing x 6 distinct
  warm-start recipes: none, full v811d-trunk, shallow-trunk-only, LR-decoupled, blended-trunk, v88-trunk)
  is compatible with production's Alibaba+stress combination simultaneously — this is not a
  lineage-pairing, warm-start-depth, LR, or blend-ratio problem, all four having now been individually
  ruled out; (2) **recommend closing ARCH-1's shared-backbone exploration for heads A/B with this
  verdict** — per the mission's pre-declared stopping rule and the project's standing "solve problems,
  don't just keep testing" directive, no tenth variant is proposed; a future attempt at heads C/D or a
  differently-shaped shared backbone remains possible in principle but should not reuse "vary the
  warm-start source/depth/LR under the same partial-sharing split point" as its premise, since that
  specific avenue is now exhausted (9/9 consistent failure); (3) **separately, `RECIPEGAP1`'s
  lineage-correct warm-start recipe (both Layer1/Layer2 warm-started from their own correct lineage, no
  sharing) is flagged as the best Alibaba+stress+FF++ combination found across the entire 9-round ARCH-1
  body of work, at production's existing model count/size** — not an ARCH-1 win (no size/latency
  reduction), and not itself ready to swap into production (fails its own stress CI at 4.33%, single
  seed, known small data gaps unresolved) — but a real candidate for a future, non-architecture-changing
  production-improvement round, explicitly out of scope to launch this round.
- **Non-claims**: single seed for Variant A (Variant B's numbers are `RECIPEGAP1`'s own single-seed
  results, reused not re-verified); `pipeline.py`/production checkpoints untouched (read-only, verified
  before and confirmed unchanged after — only files touched are under
  `checkpoints/research/arch1_lineage_20260826/`, `results/research/arch1_lineage_20260826/`, and
  `AIGuard/train_arch1_lineage_shufflenet.py`); no TFLite export; head-B 13.9% missing-file gap
  reproduced identically (20,295 rows dropped from both splits); GPU jobs serialized (verified via
  `nvidia-smi`/`tasklist` before training, confirmed process fully exited before eval, confirmed GPU
  free before the CPU-only latency benchmark); no git commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section updated — shared/partial-shared
  backbone sub-line for heads A/B marked CLOSED (final verdict, not CONTINUE); `RECIPEGAP1`'s
  lineage-matched separate-model recipe named as a separate, smaller follow-up track (not launched).

## ARCH1-LINEAGE-HARDNEG-20260826: final pre-decision diagnostic — does adding the missing 1,353 hard-neg rows fix Variant A's stress concentration — **could not be executed: source data confirmed permanently unavailable, not a training result**

- **Output**: `results/research/arch1_lineage_hardneg_20260826/PRE_DECLARED.md` (full verification
  trail). No training was launched, so no new checkpoint, gates file, or eval log exists this round.
  Full findings delivered in the executing agent's final chat message (tool guard blocked writing
  `FINDINGS.md` from inside the agent, same limitation as `ARCH1-ISOLATION/MECHANISM/PARTIAL/
  SHALLOWWS/LINEAGE-20260826`).
- **Purpose**: one more cheap, targeted test requested before a human accept/reject call on
  `ARCH1-LINEAGE-20260826`'s Variant A (98.49% Alibaba / 5.37% stress FAIL / 16.78% eye_enlarging /
  13.94% whitening_medium) — does adding the 1,353 hard-negative-mined rows
  (`v89d-mined-hardneg` 1,050 + `v811-round2-mined` 303), cited by `ARCH1-RECIPE-GAP-20260826` as
  present in production's real split but absent from the generic ARCH-1 splits, close or shrink the
  concentrated `eye_enlarging`/`whitening_medium` stress-error failure mode.
- **Blocking finding from mandatory pre-training verification (Step 1)**: the 1,353-row gap was
  already closed upstream of this round — `ARCH1-FINAL-20260826` switched Head A's split to
  production's real full split (`splits/research/p1_r9_sbi_pilot_20260819/layer1_sbi_augreal_train.txt`,
  238,026 unique rows), and `ARCH1-LINEAGE-20260826`'s own training script already uses this same
  split for Head A. **However, `train_LINEAGE_A.log` shows 20,295 rows — including the specific 1,353
  targeted by this round — were dropped at load time because their source image files no longer exist
  on disk.** Directly confirmed (`find`, folder listing, filename cross-check against the one surviving
  related salvage folder `v89d_paired_mined/` [192 files, zero overlap], and the project's N: backup
  drive) that the two backing folders, `v89d_candidate_pool/` and `v89d_proxy_unseen_pool/`, are both
  permanently gone — not merely absent from a particular split file. `v811_layer2_train.txt` (Head B)
  has the identical, already-disclosed 20,295-row gap from the same two folders (no separate,
  addable Head B gap found beyond what was already known).
- **Consequence**: no valid single-variable experiment could be run — any split file naming these rows
  loads byte-identical training data to Variant A's own run, so a new training would only reproduce
  Variant A under a different seed, not test the hard-neg-data hypothesis. No training was launched
  (confirmed scientifically vacuous, not skipped for GPU-availability reasons — GPU was free, verified
  via `nvidia-smi`/`tasklist`, one orphaned zero-parent `multiprocessing.spawn` worker holding ~2.7GB
  VRAM noted and not competing).
- **Plain statement for the human decision**: `ARCH1-LINEAGE-20260826`'s Variant A numbers stand
  unchanged and this round adds no new evidence either way on whether the hard-neg-data gap explains
  the stress concentration — that hypothesis remains untested (not tested-and-failed), because the
  data it depends on no longer exists anywhere on this machine. Recovering it requires re-running the
  original `mine_fake_filter_hardneg_v813.py`-lineage mining pipeline to regenerate ~20K images from
  scratch, which is out of scope for a single-train+eval diagnostic and was not started. The
  accept/reject decision on Variant A should be made on its standing, actual numbers (real wins on
  Alibaba/FF++/size-latency, failed stress criterion) without expecting this specific gap to be
  closeable by further ARCH-1-line testing.
- **Non-claims**: does not reopen `ARCH1-LINEAGE-20260826`'s CLOSED verdict for the shared/
  partial-shared-backbone line — this is an addendum explaining why the one remaining suggested check
  could not be performed, not a tenth round of results; does not attempt to re-mine or regenerate the
  missing images; `pipeline.py`/production checkpoints untouched (read-only, verified); no git
  commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section gets a final addendum noting this
  outcome; the "9 rounds, CLOSED" framing is preserved, not reopened.
  No production change.

## HARDNEG-REGEN-20260826: regenerated the lost hard-negative pool from scratch and retrained/re-evaluated Variant A — **data restoration partially helps, does not close the stress-CI gap; ARCH-1 CLOSED verdict stands**

- **Output**: `results/research/hardneg_regen_20260826/` — `mine_hardneg_regen.py` (mining script,
  two modes), `build_regen_splits.py`, `hardneg_regen_margin_regen20260827.txt` (188 rows),
  `hardneg_regen_round2_regen20260827.txt` (1,431 rows), `pool/` (1,628 mined images, 42MB),
  `layer1_sbi_augreal_train_hardnegregen.txt` / `v811_layer2_train_hardnegregen.txt` (augmented
  splits), `gates_HARDNEGREGEN_best.json` / `perimage_HARDNEGREGEN_best.json`,
  `AIGuard/train_arch1_hardnegregen_shufflenet.py`, `eval_arch1_hardnegregen_gates.py`. Full findings
  delivered in the executing agent's final chat message (tool guard blocked writing `FINDINGS.md`
  from inside the agent, same limitation as prior ARCH-1 rounds).
- **Purpose**: `ARCH1-LINEAGE-HARDNEG-20260826` established the 20,295-row gap could not be tested
  because the OUTPUT image folders (`v89d_candidate_pool/`, `v89d_proxy_unseen_pool/`) were
  permanently deleted. This round checked whether the underlying SOURCE pools (not the deleted
  output caches) were still present, and if so, re-ran the mining pipeline from scratch to test the
  hard-neg-data hypothesis directly.
- **Feasibility (verified before mining)**: source pools ARE still present — `AIGuard/fake/`
  (56,572 files) and the five DF40 method folders' `clean_output/clean_paths.txt`
  (34,900/16,260/17,051/28,361/21,334 entries). The original scorer checkpoint
  (`shufflenet_v2_3class_v89c.pth`) is also gone; substituted its immediate predecessor in the same
  lineage (`shufflenet_v2_3class_v88.pth`, still loads). `shufflenet_v2_layer1_v811b.pth` (used for
  the `v811-round2-mined` methodology) is still present, used unchanged. Disk space ample
  (64-66GB free of 500GB). **Calibration finding: scoring with the CURRENT production-era
  hierarchical Layer1+Layer2 (v812) — i.e. what `mine_fake_filter_hardneg_v813.py` itself uses —
  gave near-zero yield (3/4,000 = 0.075% on DF40 proxy-unseen, 0/1,000 on AIGuard/fake)**: v812
  already handles most fake+filter combinations correctly, so it cannot be used to regenerate a
  comparably-sized pool. Switched to the vintage-matched v88/v811b scorers (matching the ORIGINAL
  mining checkpoints, not just "any" checkpoint), which restored period-appropriate yields
  (0.31-1.6%, consistent with the original round's own recorded ~1.0% figure).
- **What was mined**: two modes matching the two original tag lineages — `margin` mode (v88
  3-class, hard=argmax!=fake, DF40 proxy-unseen 20,000 imgs + AIGuard/fake 8,000 imgs, x2 variants)
  found 188 hard examples (0.31-0.41% yield); `round2` mode (v811b binary, P(real)>=0.35, types
  restricted to whitening/eye_enlarging/face_reshaping matching `mine_v811_layer1_round2.py`
  exactly, AIGuard/fake 40,000 imgs) found 1,431 (1.6% yield). **Combined: 1,619 unique hard-negative
  images**, comparable in scale to the original 1,353-row gap, all verified present on disk with
  zero duplicates. Merged into copies of Variant A's exact split files at x15 oversample (same
  factor as `build_v811_layer1b_splits.py`/`build_v89d_plus_splits.py`).
  **Methodological note**: `train_arch1_lineage_shufflenet.py`'s `load_split()` dedups by path, so
  the x15 oversample rows collapsed at load time (confirmed in training log: `dropped 22,666
  duplicate-path rows` on both heads) — the actual effective manipulation was +1,619 unique images
  per head (Head A manip 148,810→150,429, Head B fake 52,798→54,417), not +24,285 weighted rows.
  This is inherited loader behavior, not a flaw specific to this round.
- **Retrain**: `AIGuard/train_arch1_hardnegregen_shufflenet.py`, byte-for-byte
  `train_arch1_lineage_shufflenet.py` (PartialSharedModel, v88-trunk warm-start table, LR=2e-5, 15
  epochs, batch=256, mixup 50%/alpha=0.2, seed=20260826) with ONLY the two split-file paths changed.
  Ran to completion (15/15 epochs, wall=3,616s, best combined F1=0.9872 vs Variant A's 0.9877 —
  statistically indistinguishable). Training survived an API-quota interruption mid-run (verified
  alive via process/GPU/log-timestamp checks after the gap; no restart needed).
- **Results vs. Variant A** (arm `HARDNEGREGEN_best` vs `LINEAGE_A_best`): Alibaba 98.49%→97.98%
  (-0.51pp); **stress overall 5.37%→4.63% (-0.74pp, improved but still fails CI[1.92,3.76])**;
  **`eye_enlarging` 16.78%→13.64% (-3.15pp, improved)**; **`whitening_medium` 13.94%→13.94% (ZERO
  change — identical 40/287 misclassified count)**; `face_reshaping` 11.19%→8.04% (-3.15pp,
  improved); True Test filter recall 91.97%→93.57% (+1.61pp, improved); True Test real recall
  71.08%→69.08% (-2.01pp, worse); Shadow balanced 50.54%→44.98% (-5.56pp, worse); FF++ zero-shot
  AUROC(end2end) 0.6258→0.6132 (-0.0126, worse); FF++ official-test AUROC(frame,end2end)
  0.6257→0.6157 (-0.0100, worse). Full table and all raw numbers in the agent's final message.
- **Root cause found for `whitening_medium`'s null result**: the mining pipeline's whitening filter
  (`generate_v89d_candidate_pool.py`/`generate_v89d_proxy_unseen_pool.py`'s verbatim-copied
  function: multiplicative L-channel scaling, `L *= 1.20`) does NOT match the gate battery's actual
  whitening_medium condition (`filters/stress_test_filter_functions.py`: additive move-toward-white,
  `L += 0.15*(255-L)`) — two visually different transforms. This mismatch predates this round (baked
  into the original v8.9d scripts), so the ORIGINAL 20,295-row set likely never closed this specific
  gap either, consistent with `MASTER_PLAN_20260826.md`'s prior note that `ARCH1-FINAL`'s
  `whitening_medium` (14.63%, with the original rows still loadable then) was barely better than
  Variant A's 13.94%. `eye_enlarging`/`face_reshaping`'s mining and eval functions were checked and
  DO match (same landmark-warp math in both places), consistent with those two improving.
- **Four standing criteria** — (a) Alibaba near CI[97.50,97.91]: PASS (97.98%, closer to CI than
  Variant A's 98.49%); (b) stress not worse than CI[1.92,3.76]: **FAIL for both** (4.63% vs 5.37%,
  gap narrowed ~35% relative but still ~0.9pp above upper bound); (c) True Test filter ~92%+/
  size-latency: PASS (93.57%, cleaner pass than Variant A's borderline 91.97%); (d) FF++ meaningfully
  above 0.575: PASS for both (0.6157 vs 0.6257, smaller margin). **Single failing criterion (b) →
  NO-GO, same overall verdict as Variant A**, per the project's established single-failure rule.
- **Answer to the decisive question**: hard-negative data restoration is a REAL, PARTIAL contributor
  to the stress-error gap (not a data-availability red herring) — it measurably improves 2 of 3
  originally-elevated stress conditions in the predicted direction on a controlled single-variable
  run — but is NOT sufficient by itself to pass the production CI, and `whitening_medium`
  specifically has a distinct, non-data-volume root cause (filter-formula mismatch) that mining more
  hard negatives the same way would not fix. Data restoration also cost measurable ground on Shadow
  and FF++ metrics, a trade-off not present in the "hypothesis untested" framing of the prior round.
- **Non-claims**: does not reopen `ARCH1-LINEAGE-20260826`'s CLOSED verdict for the shared/
  partial-shared-backbone line (this is a targeted follow-up on one open question, not a tenth
  architecture variant); does not claim byte-identical reproduction of the original 20,295-row set
  (scorer substitution v88-for-v89c and fresh re-sampling are disclosed deviations); `pipeline.py`/
  production checkpoints untouched (read-only, verified); no git commit/add/push.
- **Consequences**: `docs/MASTER_PLAN_20260826.md` ARCH-1 section gets a final addendum with these
  numbers; the "9 rounds, CLOSED" framing is preserved (this is round 10 as an explicit exception —
  a data-availability diagnostic requested by name, not a new architecture variant — and reconfirms
  rather than reopens the CLOSED decision). No production change.

---

## AUDIT: `ffpp_leakage_audit_20260826` — AIGuard/fake ↔ FF++ official train/test content-key audit (VERDICT: NO LEAKAGE)

- **Phase**: cross-cutting audit (triggered against `ffpp_protocol_20260823`, `ffpp_improve_20260823`,
  ARCH-1/P1-A1 FF++ numbers, `docs/limitations_framing.md` §11).
- **Purpose**: user-supplied third-party README for "DeepFake-450K" (source of `AIGuard/real`+
  `AIGuard/fake`) described a `fake/{faceforensics, wilddeepfake, kaggle_fake}/` layout, raising the
  question of whether production's training corpus already contains FF++-derived frames — which
  would contaminate every "zero-shot FF++" number reported this session.
- **Model checkpoint**: none (read-only audit, no training).
- **Train source**: N/A.
- **Query pool audited**: full `AIGuard/real/{0-4}/*` (32,513) + full `AIGuard/fake/{0-4}/*` (32,400,
  includes the CDDB subset — not a training-split subsample, the entire physical pool).
- **Gate pool audited**: full official FF++ splits used by `ffpp_protocol_20260823` —
  `FaceForensics_protocol_frames/test/*/*.jpg` (6,620 frames, 140 official test video-IDs) +
  `.../train/*/*.jpg` (27,687 frames, 720 official train video-IDs).
- **Image-disjoint from train/test?**: **YES, confirmed** — content-key audit (SHA256 of decoded RGB
  pixel array, methodology reused verbatim from `audit_p1_r11_k3_content.py`, not reimplemented):
  **0 exact-pixel matches** across 64,913 × 34,307 comparisons. Also confirmed: no `faceforensics/`-
  named (or any source-named) subfolder exists anywhere under `AIGuard/` on this disk — it is a flat
  numbered `0-4` layout with no per-image source manifest, so the user-pasted README's structure does
  not match what is physically on disk (explanation for the discrepancy not resolvable from evidence
  on hand; the pixel-content question is answered independently of it).
- **Participated in model selection?**: N/A (read-only).
- **Results**: `results/research/ffpp_leakage_audit_20260826/content_key_audit.py` (script) →
  `log_content_key_audit.txt` + `content_key_audit.json` (raw output); full narrative
  `results/research/ffpp_leakage_audit_20260826/FINDINGS.md`. 16,403 dHash≤4 candidate hits were
  investigated and diagnosed as a **false-positive artifact** of dHash on highly standardized face
  crops (1,888 unique AIGuard images account for all hits; worst offenders "near-duplicate" 100-286
  unrelated FF++ frames spanning dozens of distinct video-IDs — not possible for genuine duplicates),
  not resolved by assumption but by grouping/inspection.
- **Claim**: No leakage between `AIGuard/fake`/`AIGuard/real` and the FF++ official train/test splits
  used for `ffpp_protocol_20260823`'s "zero-shot vs in-domain" headline finding. Every FF++ number
  reported this session (production zero-shot AUC 0.575/0.5747, in-domain AUC 0.9155/0.9467, ARCH-1
  FF++ deltas) stands as previously reported; no correction needed to CLAUDE.md or
  `docs/limitations_framing.md`.
- **Non-claim**: does not re-litigate the pre-existing, much narrower, already-quantified
  `docs/Dataset 清單.md` finding (2026-07-22) that AIGuard/fake's **CDDB** subset contains some
  FF++-derived face-swap content with 3/1,166 (0.3%) pHash near-dup overlap vs. **FakeClue test's**
  `ff++/` subfolder specifically (a different gate set than the official FF++ train/test splits audited
  here) — that finding is real, pre-dates this audit, and is unaffected by it. Does not fix the mild
  documentation tension between CLAUDE.md's "AIGuard/fake sources ... 皆為 EFS" framing and
  `docs/Dataset 清單.md`'s own CDDB entry ("+ FF++ face swap") two lines below it — flagged for a
  human to reconcile, not a correctness bug affecting any reported number.
- **Status**: final (single round, content-key methodology is the project's strongest available test,
  reused not reimplemented).

---

## AUDIT: `citation_audit_20260827` — 全 `docs/Paper 清單.md` 引用查證（VERDICT: 2 件捏造、1 件 ID 指錯論文、4 件出處錯誤）

- **Type**: read-only literature/citation audit（無訓練、無 checkpoint、無 GPU）。
- **Scope**: `docs/Paper 清單.md` 全部條目 = **68 個 arXiv ID**（arXiv 官方 API 逐一取回標題／作者／
  journal_ref／comment，與清單所寫標題逐字比對）＋ **約 24 個非 arXiv 出處**（dblp API、出版社頁面、
  CVF/ICLR/IJCAI proceedings）查證標題、作者、卷期頁碼、**會議 vs workshop**。另 grep
  `docs/paper_draft_zh.md`／`paper_outline.md`／`limitations_framing.md`／`phase1_story.md`／
  `phase2_story.md`／`research_log.md`／`TODO.md`／`CLAUDE.md`，交叉查證不在清單內的 4 個 ID
  （2310.00359 CrossDF、2601.12111 RCDN、2603.09242 GSD、1901.08971 FF++）——**四者皆存在且標題相符**。
- **Findings（總數，直說）**：
  - **捏造引用 2 件**（前輪已發現，本輪確認）：`Deceptive Beauty: The Risks of AI-Enhanced Appearance`
    （arXiv 2409.00375 = 心臟 MRI 影像品質評估論文）、`DeFakeQ: Deepfake Detection via Quantization`
    （arXiv 2412.01799 = HPRM 機器人中介軟體論文）。兩者標題本身皆查無此論文。
  - **arXiv ID 指向另一篇論文 1 件（本輪新增，第三例）**：HEIE 標的 **2412.10667 = 量子模擬演算法論文**
    （Kalev & Hen, Quantum Sci. Technol. 2025）。**與前兩件不同，HEIE 論文真實存在**（正確 ID 2411.17261,
    CVPR 2025），屬誤植 ID + 標題漏字，非捏造。**捏造總數維持 2，ID 錯誤總數 3。**
  - **會議/期刊出處錯誤 4 件**：MoE-FFD（TIFS→TDSC，前輪）、AntifakePrompt（主會議→ICLR 2025 **Workshop**，
    前輪）、Information Fusion 綜述（2025→vol.132, 2026）、Fake or JPEG（→ECCV 2024 **Workshops**, pp.80-95）。
  - **領域錯誤 1 件**：GRIDEX = 音訊／頻譜圖鑑識（前輪）。
  - **作者群錯誤 2 件**：Rathgeb IEEE Access 2020（誤植成 CVPRW 2020 另一篇的作者群）、Ibsen WIFS 2021（漏列
    González-Soler）。
  - **標題誤植／截斷 13 處**（ID 與論文皆正確，僅本清單標題需修正；含以模型名/資料集名代替論文標題 3 處：
    FakeVLM→"Spot the Fake"、Chameleon/AIDE→"A Sanity Check for AI-generated Image Detection"、
    MSCA-FFT→"An Explainable FFT-Based Spatial-Frequency Fusion Framework..."）。
- **可宣稱**：`docs/Paper 清單.md` 中**每一個 arXiv ID 都已逐一驗證指向其宣稱的論文**（3 個例外已標示更正）；
  上列「查證為正確」的出處可直接寫進投稿參考文獻。
- **不可宣稱（仍待查，禁止寫入投稿稿）**：① XPlainVerse / Explainable Deepfake Detection Challenge 的
  **ACM MM 2026 出處**未證實；② Rathgeb 差分式修圖偵測 **D-EER 數字**仍為 snippet 來源；
  ③ `docs/paper_draft_zh.md` 承重對照數字 **Bharati et al. IJCB 2017「79.3-97.5%」**無法由摘要證實，
  需查全文表格；④ `paper_outline.md`／`TODO.md` 標註 GSD 與 RCDN 為「2026 ICICT」——arXiv 頁面無此資訊，**未證實**。
- **另發現（未修改該檔，僅回報）**：`TODO.md` §與 `paper_outline.md` 寫「GSD 原先誤記為 semantic shortcuts，
  正確概念是 semantic fallback」——但 arXiv 2603.09242 的**正式標題就含 "Blocking Semantic Shortcuts"**，
  該更正註本身敘述有瑕疵，需人工確認後再改。
- **Results**: 更正已就地套用於 `docs/Paper 清單.md`（刪除線 + ⚠️/⛔ 註記，未靜默刪除任何條目），
  頂端新增「2026-08-27 全清單引用稽核結果」彙整區塊；DAD-HCNN 全文數字抽取見
  `results/research/citation_audit_20260827/DADHCNN_NUMBERS.md`。

---

## AUDIT: `citation_verify_20260827b` — 外部推薦論文獨立查證（4 篇新推薦 + 3 篇防守性引用；VERDICT: 0 件捏造、1 件查無此文、4+3 件確認存在）

- **Type**: read-only literature/citation verification（無訓練、無 checkpoint、無 GPU）。此輪與同日稍早的
  `citation_audit_20260827`（清單既有 68 個 arXiv ID 全面稽核）不同對象：這輪查的是**使用者收到的一批
  新外部推薦**，鑑於同一 session 已抓到 3 件 ID 指錯/捏造（Deceptive Beauty、DeFakeQ 舊版、HEIE），
  對每一篇重新獨立用 arXiv/出版社官方頁面核對標題、作者、venue、年份與**具體數字**，不採信外部工具原始描述。
- **Scope**：4 篇「新推薦」（LRD-Net、"Real-Time Deepfake Detection on Embedded Systems"、FL-TENB4、
  insightface.ai 月度文獻整理）＋ 3 篇「防守性引用」（HTNet、mobile-edge capsule network、Hybrid
  MobileNet-LSTM，較低查證強度，僅核對標題/作者/venue 存在，不逐字核對數字）。
- **Results**（逐篇見 `docs/Paper 清單.md`「2026-08-27 外部推薦引用查證」章節）：
  - ✅ **VERIFIED，含全部數字**：LRD-Net（arXiv 2604.10862，Zhang & Chaudhary，2.63M 參數／8x 訓練加速／
    10x 推論加速／DiFF benchmark SOTA，四項數字與外部推薦逐字吻合）；FL-TENB4（Sensors 25(3):788, 2025，
    FF++ c23 上 AUC 0.96／延遲 12ms／模型 4.2MB，與推薦描述吻合）。
  - ✅ **VERIFIED 為真實資源**（非可引用論文）：insightface.ai 月度 deepfake/face-swap 文獻整理部落格，
    確認 2026 年 3/5/6/7 月持續發文，可作為文獻監測工具但不可當投稿引用。
  - ❌ **NOT FOUND**：「Real-Time Deepfake Detection on Embedded Systems」（claimed MobileNetV2 + Samsung
    Galaxy A31 實測 + AUC 0.8718 + 100-200ms/frame）——多輪 WebSearch 精確片語與數值組合查詢皆查無此文，
    找到的鄰近論文（MobileNetV2+SVM、DeepConfGuard 等）數字與 venue 皆對不上。**外部推薦未附 arXiv ID**，
    故無法像前三例一樣標記「ID 指錯論文」，只能標記整篇「查無此文」；懷疑是外部工具拼接多篇論文片段
    生成的複合體，與本 session 已知的捏造模式一致。**未加入清單。**
  - ✅ **存在確認（防守性引用，未逐字核對數字）**：HTNet（Pattern Recognition Letters 172:121-127, 2023）、
    mobile-edge capsule network（Software: Practice and Experience 54(9):1651-1670, 2024）、Hybrid
    MobileNet-LSTM（IEEE, 2025，同工作另有 SciTePress/ResearchSquare preprint 版本）。三篇皆確認為
    「階層式/多類別但無 filter 第三類」屬性符合原始推薦描述。
- **Claim**：本輪 4+3=7 篇外部推薦中，**6 篇確認存在（4 篇含數字全對，2 篇僅存在性）、1 篇查無、0 篇捏造**。
  已加入 `docs/Paper 清單.md`「計劃使用」（LRD-Net、FL-TENB4）與新增查證章節（其餘 5 篇，含 NOT FOUND 那篇
  的說明列）。
- **Non-claim**：不代表本 session 之前抓到的 3 件 ID 錯誤（Deceptive Beauty / DeFakeQ / HEIE）性質有變化，
  那 3 件仍是既有清單裡的錯誤，與本輪查的新推薦是不同批次。LRD-Net 的 SOTA 主張限定在 DiFF
  （diffusion-based forgery）benchmark，不可引申為泛用跨資料集 SOTA。
- **Status**: final（single round，每篇皆已抓到官方來源頁面核對，非僅信賴搜尋摘要）。
- **Status**: final（清單內已無未查證條目；四項待查已明確列名）。

---

## FILTER1-PARAMRAND-20260827: artifact_classifier parameter randomization — **NEGATIVE RESULT, NO-GO** (0/4 types doubled Alibaba accuracy vs pre-declared bar)

- **Type**: data generation + retrain + eval (GPU, single seed diagnostic). `pipeline.py` and all
  production checkpoints (Layer1 `v817sbi`, Layer2 `v811`, `artifact_classifier_v6.pth`) read-only,
  unchanged. No git commit/add/push.
- **Purpose**: test the one untested lever named in CLAUDE.md's artifact_classifier section and
  `docs/MASTER_PLAN_20260826.md` FILTER-1/P1-B1 for the long-standing Alibaba cross-algorithm filter
  sub-type gap (production `artifact_classifier_v6.pth`: True Test 90-100% same-algorithm vs Alibaba
  6.4-28.2% cross-algorithm on 3/4 types) — every training image for a given filter type uses exactly
  ONE fixed intensity/scale/ratio (whitening 0.15, eye_enlarging scale=1.18, face_reshaping
  shrink_ratio=0.92, smoothing bilateralFilter sigma=80). Base-image diversity
  (`p2_artifact_datafix_20260821`/`completefix_20260821`) and class-weight tuning had already been
  tried and ruled out; parameter diversity had not.
- **Output**: `results/research/filter1_paramrand_20260827/` (`PRE_DECLARED.md` with pre-declared
  ranges/rationale/success bar, `train_artifact_v7_paramrand.py`,
  `eval_artifact_paramrand_full4type.py`, `audit_content_disjointness_paramrand.py`,
  `artifact_v7_paramrand_full4type_results.json`, `artifact_classifier_v7_paramrand_train_results.csv`,
  sample contact sheets); `filters/generate_paramrand_filters.py` (reusable generation script);
  `checkpoints/research/filter1_paramrand_20260827/artifact_classifier_v7_paramrand.pth` (NOT
  promoted). FINDINGS delivered in the executing agent's final chat message (tool guard blocked
  writing `FINDINGS.md` from inside the agent, same limitation as prior research rounds).
- **Design**: generated 3,000 LFW-based, True-Test-excluded images per type with per-image
  uniformly-sampled parameters (whitening U[0.08,0.25], eye_enlarging scale U[1.08,1.30]
  (radius_factor fixed 1.70), face_reshaping shrink_ratio U[0.85,0.97], smoothing sigmaColor=
  sigmaSpace U[40,120], `d=15` fixed) — ranges visually sanity-checked at both extremes before bulk
  generation, chosen to stay a plausible instance of the same filter type. Alibaba never read for
  generation (held out throughout, per the project's standing rule). ~1,965-2,111 images/type
  survived Step1+Step2 cleaning. Retrained `artifact_classifier_v7_paramrand.pth` on the MIXED pool
  (v6's 8 existing sources + 4 new `*_paramrand` sources, 62,315 images pre-split) with
  `train_artifact_v7_paramrand.py` — byte-identical to production's own `train_artifact_v6.py` except
  the 4 new source lines, isolating "data only" as the variable.
- **Bug caught and fixed mid-round**: the copied `normalize_class()` (strips `lfw_` prefix and
  `_s\d+` scale suffix) did not know about the new `_paramrand` folder suffix — first audit attempt
  silently loaded ZERO paramrand images (pool stayed at v6's original 54,255), which would have made
  the whole round a silent no-op. Caught by the audit script's own composition breakdown before any
  training ran; fixed by adding a `_paramrand` suffix strip, re-audited, confirmed pool grew to
  62,315 with all 4 new sources present.
- **Content-key audit** (decoded-pixel SHA256, same methodology as prior `p2_artifact_*` rounds):
  zero overlap vs True Test filter (249 images), **zero overlap vs Alibaba clean (16,183 images)** —
  gate PASS.
- **Pre-declared success bar**: ≥2 of 4 types at least DOUBLE Alibaba end-to-end accuracy AND no
  type's isolated-test-split accuracy drops >5pp AND no type's True Test end-to-end recall drops
  >10pp.
- **Results — in-domain isolated test-split** (v6 → v7_paramrand): eye_enlarging 98.76%→98.36%
  (−0.40pp), face_reshaping 99.11%→98.68% (−0.43pp), smoothing 99.51%→99.76% (+0.25pp), whitening
  97.69%→96.61% (−1.08pp), overall 98.77%→98.35% (−0.42pp). **All within the 5pp tolerance — PASS.**
- **Results — production-chain end-to-end** (`pl.run_single`→Layer1→Layer2→artifact_classifier,
  Layer1/Layer2 unchanged, same seed=777 as v3/v5/v6 trajectory): True Test deltas all ≤1.62pp in
  either direction (smoothing 100.00%→100.00%, face_reshaping 95.16%→93.55%, whitening
  90.32%→91.94%, eye_enlarging 72.58%→72.58%) — **all within the 10pp tolerance, PASS.** **Alibaba
  deltas: smoothing 28.20%→27.00% (−1.20pp), face_reshaping 6.41%→7.62% (+1.21pp), whitening
  23.60%→25.20% (+1.60pp), eye_enlarging 79.60%→79.60% (0.00pp, already nowhere near needing to
  double). 0 of 4 types came anywhere close to doubling (targets were 56.40%/12.82%/47.20%/already-
  ceiling) — criterion 1 FAILS for all 4 types.**
- **Notable mechanism finding (unplanned)**: per-image confusion buckets show `eye_enlarging` is the
  single largest wrong-answer bucket for every OTHER type on Alibaba in BOTH v6 and v7_paramrand —
  face_reshaping 338/500 (67.6%), whitening 306/500 (61.2%), smoothing 192/500 (38.4%) all
  misclassified as `eye_enlarging` — and the eye_enlarging population's own raw counts (TrueTest
  45/62, Alibaba 398/500) are IDENTICAL to the integer between v6 and v7_paramrand, i.e. this round's
  added data changed literally zero decisions on that population. `eye_enlarging` is 41% of the
  training pool (25,544/62,315, via 5 source folders including 4 pre-existing multi-scale variants) —
  this majority-class-attractor effect looks like at least as strong a candidate driver of the
  Alibaba confusion pattern as the fixed-parameter-signature hypothesis this round tested, and is a
  distinct, not-yet-tried lever (e.g. capping eye_enlarging's source-folder count / rebalancing).
- **Verdict: NO-GO** — parameter randomization does not meaningfully close the Alibaba cross-
  algorithm gap. This is the THIRD independently-tested mechanism (after base-image diversity and
  class-weight tuning) that fails to close it, each moving the needle by at most a few points.
  Per `docs/MASTER_PLAN_20260826.md`'s own pre-stated rule ("若參數隨機化也失敗 → 正式定為 B 類
  limitation，證據鏈完整"), this is the trigger condition for that reclassification — reflected in
  this round's edit to that document's P1-B1 section.
- **Non-claims**: does not rule out FILTER-1's separate, untested idea of training on a genuinely
  different third-party algorithm (Megvii/FFHQ_four) — that is a different lever (a different
  algorithm's formula, not a different parameter of our own formula) and remains open. Does not
  claim the chosen ranges were too narrow (deliberately generous, ~60-70% either side of the fixed
  value, visually sanity-checked). Single seed, as scoped — not run a second time because the effect
  sizes are near the noise floor in the "no effect" direction, not close enough to the bar to be
  worth disambiguating with another seed.

---

## FILTER1B-MULTIVENDOR-20260828: artifact_classifier multi-vendor (Megvii + likely-Tencent) training — **NEGATIVE RESULT, NO-GO** (0/4 types doubled Alibaba accuracy vs pre-declared bar; 5th mechanism to fail)

- **Type**: label-structure investigation + data prep + multi-label retrain + eval (GPU, single
  seed). `pipeline.py` and all production checkpoints (Layer1 `v817sbi`, Layer2 `v811`,
  `artifact_classifier_v6.pth`) read-only, unchanged. Alibaba (`FFHQ_ali_process`) never trained on.
  No git commit/add/push.
- **Purpose**: FILTER-1's one remaining untested lever explicitly flagged as open by
  `FILTER1-PARAMRAND-20260827` ("does not rule out FILTER-1's separate, untested idea of training on
  a genuinely different third-party algorithm") — train on real commercial neural-network retouching
  algorithm families (as opposed to same-family parameter/base-image variation, already 3-for-3
  failed) and test whether that generalizes to the held-out third family, Alibaba.
- **Label-structure finding (corrects the task brief's premise)**: `FFHQ_megvii_four_process`
  (13,139 clean) and `FFHQ_four_process` (7,731 clean) BOTH contain only the
  `Whitening_Smoothing_FaceLifting_EyeEnlarging` four-op composite — **no Megvii single-op subset
  exists on disk**, contrary to the task brief's assumption. Confirmed by directory listing (single
  subfolder per vendor root). `FFHQ_four_process/four_process.txt` (10,000 rows) supplies per-image
  per-op intensity metadata (levels 30/60/90, coverage 7,731/7,731); Megvii has none. Fetched the
  RetouchingFFHQ paper (arXiv:2307.10642) directly: multi-op subsets were generated only by **Megvii
  and Tencent** ("Alibaba only allows performing one retouching at a time") — so `FFHQ_four_process`
  is definitively NOT Alibaba (safe w.r.t. the exam) and most plausibly **Tencent**, the vendor this
  project has flagged as never-used. Ontology mapping applied: `EyeEnlarging→eye_enlarging`,
  `FaceLifting→face_reshaping` (paper's "face lifting" = our "face_reshaping"), `Smoothing→smoothing`,
  `Whitening→whitening`.
- **Design consequence**: single-label CE is impossible on 100%-composite sources. Kept the v6
  single-label pool/CE loss/sqrt-damped class weights/split (`random_state=42`) byte-identical;
  added the two composite sources as TRAIN-ONLY multi-label BCE targets on the same 4 logits (Megvii
  → `[1,1,1,1]`, `four_process` → `intensity/90` per op soft target). Architecture unchanged
  (`shufflenet_v2_x1_0`, `fc→4`) → checkpoint is a drop-in for `pipeline.py`'s `classify_artifact()`.
- **Base-image overlap accounting**: FFHQ index ranges megvii/four = 60002-69999 vs Alibaba clean
  split (16,183 rows, 1,706 unique indices) = 17001-19999 — **0 overlap for both sources**; 100% of
  the Alibaba exam is "unseen base image AND unseen algorithm" w.r.t. the new additions (no
  overlap-status split of results needed, fraction is exactly zero). Megvii and `four_process` share
  6,734 base indices with EACH OTHER (both draw from the same FFHQ range) — expected, not a gate,
  both are training-side.
- **Content-key audit** (decoded-pixel SHA256, Known Trap #3, same methodology as prior
  `p2_artifact_*`/paramrand rounds): 20,870/20,870 new-addition images readable, **0 overlap vs True
  Test (769, all 3 classes)**, **0 overlap vs Alibaba clean (16,175/16,183 readable)** — gate PASS.
- **GPU discipline**: waited for the concurrent P1-A3 ratio-sweep training job (PID 40036,
  `train_p1a3_ratio.py --ratio 0.75 --seed 20260827`) to finish and release the GPU (confirmed via
  `nvidia-smi` 0% util, no compute processes) before launching training — no concurrent GPU
  contention.
- **Output**: `results/research/filter1b_multivendor_20260828/` (`PRE_DECLARED.md`,
  `train_artifact_v8_multivendor.py`, `eval_artifact_multivendor_full4type.py`,
  `audit_content_disjointness_multivendor.py` + `audit_output.log`,
  `artifact_v8_multivendor_full4type_results.json`,
  `artifact_classifier_v8_multivendor_train_results.csv`, training/eval logs); FINDINGS delivered in
  the executing agent's final chat message (tool guard blocked writing `FINDINGS.md` from inside the
  agent, same limitation as prior research rounds).
  `checkpoints/research/filter1b_multivendor_20260828/artifact_classifier_v8_multivendor.pth` (NOT
  promoted).
- **Pre-declared success bar**: identical to the paramrand round — ≥2 of 4 types at least DOUBLE
  Alibaba end-to-end accuracy vs v6 baseline, while no type loses >5pp in-domain (True Test).
- **Results — in-domain (True Test, production chain)**: smoothing 100.0%→100.0% (identical
  confusion), face_reshaping 95.16%→95.16% (identical confusion), whitening 90.32%→93.55% (+3.2pp,
  CI overlap), eye_enlarging 72.58%→72.58% (identical confusion). **No collapse, condition trivially
  satisfied.**
- **Results — Alibaba (cross-algorithm, the target), v6 → v8_multivendor**: smoothing 28.2%
  [24.43,32.3] → 36.0% [31.91,40.3] (+7.8pp, CIs barely touch); face_reshaping 6.41% [4.58,8.91] →
  3.41% [2.14,5.39] (**−3.0pp, regressed**); whitening 23.6% [20.09,27.51] → 34.4% [30.37,38.67]
  (+10.8pp, **CI-disjoint real improvement**, but target for doubling was 47.2%); eye_enlarging 79.6%
  [75.85,82.9] → 63.6% [59.29,67.7] (**−16.0pp, CI-disjoint real regression**). **0 of 4 types
  doubled. 2 of 4 regressed (eye_enlarging significantly). Criterion FAILS.**
- **Mechanism finding**: the "eye_enlarging attractor" from the paramrand round (other types
  misrouted to eye_enlarging) genuinely weakens under multi-vendor co-training — per-500 misroute
  counts to eye_enlarging drop v6→v8_mv: smoothing 176→51, face_reshaping 335→235, whitening
  317→211. But the freed probability mass lands mostly in `unknown_filter` (below the 0.6 confidence
  gate) rather than the correct class: unknown_filter counts rise smoothing 52→188, face_reshaping
  21→103, whitening 19→86, and — critically — eye_enlarging's OWN predictions also lose confidence
  (unknown_filter 13→94), which is why eye_enlarging's correct-accuracy drops despite not being the
  type the intervention targeted. Net: BCE-trained composite co-training makes the classifier more
  honestly uncertain cross-algorithm (safer failure mode) but not more correct — small real gains on
  2 types, a real loss on 1, near-zero-to-negative on the 4th.
- **Verdict: NO-GO** — multi-vendor (2-3 real commercial algorithm family) training does not close
  the Alibaba cross-algorithm gap either. This is the FIFTH independently-tested mechanism (after
  base-image diversity, class-weight tuning, parameter randomization, and now algorithm-family
  diversity itself) to fail the doubling bar — and unlike the first four (same-family variations),
  this one changed the algorithm family itself, which was the most promising untested lever named in
  `docs/MASTER_PLAN_20260826.md` FILTER-1. Its failure is stronger evidence for the B-class
  limitation than another same-family negative result would have been.
- **Non-claims**: does not test whether more Tencent-only single-op data (if ever obtained via formal
  application) would help — this round's Tencent-plausible source was 100% four-op composite, a much
  weaker signal than true single-op supervision. Does not test MoE/shared-expert architectures
  (MoFRR) or domain-adversarial training — both remain untested, structurally different directions.
  Single seed, as scoped.

---

## EVAL-1: `eval1_crossdataset_20260827` — 文獻標準泛化協定 + leave-one-source-out（回答 R9「高分是否因 train/test 同源？」）

- **Type**: Part A = eval-only（重用既有 checkpoint，無新訓練）；Part B = 3 個 LOSO 訓練 arm
  （ShuffleNetV2 dual-branch，warm-start production lineage，5 epoch，與 production 完全同配方）。
- **Trigger**: `docs/MASTER_PLAN_20260826.md` **EVAL-1**（未開始）+ Reviewer 必問清單 **R9**
  （in-domain 99%+ vs 跨 domain 0.57-0.63，全專案最致命的一題）。
- **Part A checkpoint**: `checkpoints/research/ffpp_protocol_20260823/ffpp_full_best.pth`
  （+ `ffpp_spatial_best.pth`）— 重用，未重訓。此 checkpoint 只在 FF++ 官方 train split 上訓練，
  從未見過 Celeb-DF-v2 或 DF40 任何一張圖（`FFPP_PROTOCOL_FINDINGS.md` §2 三項內容金鑰稽核 PASS）。
- **Part A targets/scope**:
  - **Celeb-DF-v2**（`splits/celebdf_v2_blind_holdout.txt`，400 幀，與 v8.17 production 2026-08-20
    量測的同一批幀）：**FULL AUC=0.6876、SPATIAL AUC=0.7049**（frame-level）。對照 production v8.17
    在同一 400 幀上的**零樣本** AUROC=0.568（CLAUDE.md 2026-08-20 條目）——FF++ 訓練（同為真實影片
    換臉家族）比 production 自己的 diffusion/GAN 語料**更能**遷移到 Celeb-DF-v2，儘管 FF++ 訓練本身
    也是零樣本（未見過 Celeb-DF-v2）。
  - **DF40 EFS**（sd2.1/DiT/SiT/ddim/pixart，各 800 張 fake + 共用 200 張 Celeb-DF-v2 real holdout）：
    per-method AUC 差異極大——sd2.1=0.9692、pixart=0.9437（高）vs DiT=0.6590、SiT=0.7076、
    ddim=0.7634（中低）；pooled FULL=0.8069、SPATIAL=0.7639。**這不是 DF40 官方 P-1/P-2/P-3 協定**
    （磁碟上無官方 train/test video-ID metadata），是同語料（Celeb-DF-v2 base identity）不同生成器
    的零樣本測試，且 DF40 EFS 這 5 個方法的 base identity 與 PRODUCTION 訓練用的 3,000/method 子集
    共享同一 Celeb-DF-v2 身份池——但 Part A 測的 checkpoint（FF++-only）從未見過任一張 DF40 圖，
    無洩漏風險。
  - **DFDC**：全專案磁碟搜尋 0 命中，回報「unavailable, not fabricated」，未捏造數字。
  - **文獻對照表缺口（誠實揭露）**：任務簡報引用的 `results/research/litsurvey_20260827/`
    在本輪執行時為**空資料夾**，`0.7365`（Celeb-DF-v2 Xception frame AUC）與 `0.546`（DF40 P-3
    Xception）兩個數字在本 repo 任何檔案中都查無逐字出處，本輪**未採信、未引用**這兩個數字，
    僅重用 `ffpp_protocol_20260823/FFPP_PROTOCOL_FINDINGS.md` §5.1 已核實的 FF++ 原論文 Table 5
    引用。
- **Part B corpus**: `splits/research/p1_r9_sbi_pilot_20260819/layer1_sbi_augreal_train.txt`
  （256,968 rows，即 production Layer1 v817sbi/SBIAUG 的實際訓練 split）。訓練前發現並修復：
  7.9%（20,295 列）路徑已不存在（`v89d_proxy_unseen_pool/` 等既有已知清理遺留問題，與
  `FFPP_PROTOCOL_FINDINGS.md` §2 記錄的同一問題同源），過濾後 236,673 列（與
  `production_candidate_v2_20260823/layer1_prod_only_filtered_train.txt` 的既有數字完全吻合，
  交叉驗證了過濾邏輯正確）。
- **Part B 3 個留一來源**（見 `PRE_DECLARED.md` 選擇理由）：`DF40-sd2.1`（3,000 rows，同 EFS 家族內
  換一個生成器）、`MidJourney`（549 rows，商用生成器，家族外）、`AIGuard-fake`（19,524 rows，最大
  fake 來源，異質混合語料）。
- **Part B held-out test 建構**：每來源從磁碟池中取最多 500 張**從未出現在 production 完整訓練
  split 任一列**的圖（sd2.1 池 37,933 張餘 34,933 張可用；MidJourney 池僅 594 張餘 45 張可用，
  樣本數小、CI 寬，誠實揭露；AIGuard/fake 池 56,572 張餘 37,048 張可用），配對共用 500 張來自
  `splits/v811_layer1_val.txt` 的 real（該 val split 從未參與任何 arm 的梯度更新，僅用於
  best-epoch 選擇，與 `train_p1_r9_layer1.py` 同慣例）。
- **Part B 訓練配方**：`AIGuard/train_eval1_loso_layer1.py`（複製自
  `AIGuard/train_p1_r9_layer1.py`，僅改輸出路徑），與 production Layer1 完全同配方（warm-start
  `shufflenet_v2_layer1_v811d.pth`、Adam 2e-5、5 epoch、batch 256、mixup、auto class weight、
  label smoothing 0.1、cosine schedule、best-macro-F1 存檔於 `v811_layer1_val.txt`）。**Control
  baseline 不另外訓練**：直接用實際 production checkpoint `shufflenet_v2_layer1_v817sbi.pth`
  的數字，因為 Part B 的訓練語料本來就是產生該 checkpoint 的同一個 split——這是本輪最大的算力
  節省，且效度上完全成立。Sanity check：production 在共用 `v811_layer1_val.txt` 上的 macro-F1
  = **0.9781**，與訓練時記錄的既有數字同量級，通過 ARCH-1 教訓要求的「基準健康度」檢查。
- **Part B 結果（held-out AUC / fake recall，production in-domain vs LOSO never-seen）**：

  | Source | n(fake/real) | Production AUC | LOSO AUC | Gap (AUC) | Production fake_recall | LOSO fake_recall | Gap |
  |---|---|---|---|---|---|---|---|
  | DF40-sd2.1 | 500/500 | 0.999984 | 0.999988 | **-0.000004** | 0.998 | 0.998 | **0.000** |
  | MidJourney | 45/500（樣本小）| 0.999867 | 0.999867 | **0.000** | 0.9778 | 0.9778 | **0.000** |
  | AIGuard-fake | 500/500 | 0.998424 | 0.998168 | **+0.000256** | 0.992 | 0.988 | **+0.004** |

  **全部 3 個來源的 LOSO gap 都在雜訊範圍內（≤0.03pp AUC、≤0.4pp recall），與「完全沒看過這個
  來源」和「production 有看過」幾乎無法區分。**
- **Corpus-shortcut 解讀（依 PRE_DECLARED 的預先宣告檢查項）**：held-out 圖片已驗證非重複內容
  （path-exclusion 而非僅 stem/filename 比對），故排除「測試集其實是重複資料」的解釋。真正的
  解讀是：**Layer1 的 real-vs-manipulated 二分類，在「乾淨臉部照片 real pool」vs「任何一種
  manipulated 來源」的框架下，是一個對本專案語料庫內任何生成器都幾乎已解決的任務**——換言之，
  production 的高分不是靠記住特定 3,000 張 sd2.1 圖或特定 549 張 MidJourney 圖撐起來的（LOSO
  gap≈0 直接反證這一點），但這也**不代表泛化能力真的跨資料集成立**：對照 Part A，同一類架構
  換到真正獨立的資料集（Celeb-DF-v2、DF40 用不同生成器、FF++ 官方 test）AUC 掉到 0.57-0.97
  不等，遠不如本輪 LOSO 呈現的 ~0.998-1.0。**兩者合看的結論是：本專案的高分主要由「語料庫內部
  的表層可分性」（前處理管線、臉部裁切慣例、解析度範圍、JPEG 壓縮等所有本專案資料共享的性質）
  撐起，而不是靠記住特定訓練來源的具體樣本；但這個「語料庫內表層可分性」本身不會延伸到真正
  外部、獨立蒐集的資料集**——這是與本專案既有「語料庫捷徑」meta-finding（Layer2、
  artifact_classifier、棄權閘門三處已重複出現）同一機制的第四個獨立實例，且是首次在 Layer1
  本身、用受控的留一實驗量出來的版本。
- **R9 白話回答**：「高分是不是因為 train/test 同源？」——**分兩層回答，兩層都要講**：
  (1) 不是靠記住具體某個來源的訓練樣本：留一來源測試顯示，換掉/拿掉任何單一 fake 來源都不影響
  該來源的偵測分數（gap≈0）。(2) 但高分高度依賴「跟訓練語料庫同一種表層製作方式」：換到真正
  獨立蒐集、不同前處理管線的資料集（FF++、Celeb-DF-v2、跨生成器 DF40），同一架構的 AUC 從
  ~0.98-1.0 掉到 0.57-0.97 不等。**兩種「同源」的意義不同，必須說清楚是哪一種**。
- **Claim**：① 本專案 Layer1 對「留一來源」的內部穩健性已用受控實驗量化，3 個來源、跨家族/
  跨規模皆成立，gap 在雜訊範圍內。② FF++-only 訓練的 checkpoint 對 Celeb-DF-v2 的零樣本遷移
  （AUC 0.688-0.705）優於 production 自己的零樣本（0.568），這是本專案第一次量出「同манip家族
  遷移優於跨家族遷移」的直接證據。③ DF40 EFS 跨生成器零樣本 AUC 因生成器而異（0.66-0.97），
  不是均勻的。
- **Non-claim**：不可宣稱「production 泛化能力已被證明良好」——Part A 明確顯示跨資料集/跨
  compression/跨前處理管線時掉點嚴重。不可把 Part A 的 DF40 數字當成 DF40 論文 P-1/P-2/P-3
  的官方協定數字（無官方 split metadata，僅為同語料不同生成器的近似測試）。不可引用
  `0.7365`／`0.546` 這兩個文獻數字——本輪查證後找不到 repo 內逐字出處，未採用。MidJourney
  held-out 僅 45 張，CI 寬，不可過度解讀其 gap=0 為精確值。不可宣稱 3 個 LOSO 來源涵蓋了
  corpus 全部來源（僅為策略性選取的 3/約 30 個 source label 之一）。
- **Files**: `results/research/eval1_crossdataset_20260827/{PRE_DECLARED.md, part_a_eval_results.json,
  part_b_loso_results.json, log_loso_*.txt}`、`checkpoints/research/eval1_crossdataset_20260827/
  layer1_eval1_loso_{sd21,midjourney,aiguardfake}*.pth`、`splits/research/eval1_crossdataset_20260827/
  *.txt`、`build_eval1_setup.py`、`eval_zeroshot_ffpp_crossdataset.py`、`eval_loso_heldout.py`、
  `AIGuard/train_eval1_loso_layer1.py`。
- **Status**: final（single round，single seed per arm — 3 LOSO 訓練 arm 因為是診斷輪而非
  升版輪，依任務範圍不需多 seed；GPU 訓練期間與另一個並行 agent 的 `filter1_paramrand_20260827`
  訓練共用 GPU，造成部分 epoch 明顯變慢，但未造成任何數值錯誤——已用 CPU/GPU 活動與最終 log
  交叉確認每個 arm 的收斂數字為真實訓練結果，非假象）。

## CELEBDFB-EXTERNAL-20260827: Celeb-DF-B external literature-comparison attempt — **BLOCKED at access-gating step, no eval executed**

- **Type**: inference-only (no training planned, none run). Goal was head-to-head
  comparison of production v8.17 against Libourel et al. (IWBF 2024, EURECOM) and
  Concas et al. (MetroXRAINE 2025), both of whom independently published the same
  "fake+filter → misclassified as real" phenomenon this project's core finding covers.
- **Trigger**: literature-survey citation match; task specified Celeb-DF-B
  (`https://celebdfb.eurecom.fr/`, 232 real + 232 paired FaceSwap fakes from
  Celeb-DF-v2, each beautified with one of 4 Instagram filters — BROWN / California
  dreamin / Relax! You Pretty! / Hawaii Grain — 928 videos total).
- **Result: STOPPED at Step 1 (mandatory access-gating check) — Celeb-DF-B has no
  self-service download.** Verified directly against the live page (cert expired but
  content fetchable, confirmed non-malicious static academic site): the "Download"
  section is a "Contact" block only, listing 4 authors' email addresses
  (mirabet@eurecom.fr / libourel@eurecom.fr / husseini@eurecom.fr / jld@eurecom.fr) —
  no form, no S3/Zenodo/direct link. This is a manual human-to-human email request
  with unknown turnaround, not completable by an autonomous agent (no fabricated
  credentials, no bypass attempted, per task instruction). **Also likely requires
  the base Celeb-DF (v2) dataset itself** (its own separate Google/Tencent-form
  gate, `deepfakeforensics@gmail.com`), since Celeb-DF-B is a derived subset.
- **What unblocks this**: a human on the team emails the 4 EURECOM contacts above
  from a real institutional address requesting the Celeb-DF-B download link
  (stating academic/non-commercial deepfake-detection benchmark purpose); once a
  link exists, resume with frame extraction (reuse existing face-crop/MediaPipe
  logic), content-key contamination audit (reuse
  `results/research/p1_r11_leakage_scaling_20260820` scripts), and a
  `pipeline.py hierarchical_predict()` batch run on the four cells (Real,
  Real+filter, Fake, Fake+filter) — all still open, nothing else about this round
  is blocked once the data lands.
- **AMSL / FRLL morphing datasets checked as instructed (same gating question,
  different target)**: **FRLL-Morphs** (Zenodo, DOI `10.34777/r18q-pr81`) is
  directly downloadable, no gating — not pursued further this round since it's an
  identity-splice morphing dataset, not a beautification-filter dataset, so it
  doesn't map onto this project's `filter` class definition or the fake+filter
  finding. **AMSL Face Morph Image Data Set**
  (`omen.cs.uni-magdeburg.de/disclaimer/index.php`) is gated behind a self-service
  form (Name/Email/Institution → "Get a download link", reads as instant-issue,
  not multi-day manual review) — **not submitted**, since it requires a real
  person's institutional email/name and submitting someone's PII to a third-party
  system is a human decision, not an autonomous default; a human can fill it
  directly at the URL above if the team wants this dataset.
- **Literature numbers recorded for reference only (not compared against any new
  production number this round)**: Libourel et al. Table III (verified directly
  from the IWBF 2024 PDF this round) — CADDM AUC 0.91→0.76 (−0.15), RECCE
  0.81→0.66 (−0.15), FTCN 0.80→0.64 (−0.16), all video-level AUC, no APCER-style
  metric in that paper (AUC + FNR only). Concas et al. MetroXRAINE 2025 APCER
  numbers (VGG19 30.1%→48.4%, AlexNet 22.3%→8.0%) are as supplied in the task
  description and were **not** independently re-fetched/re-verified this round.
- **Non-claims**: does not claim production v8.17 beats, matches, or loses to
  either paper's numbers — no comparison was computed, no data was obtained. Does
  not claim Celeb-DF-B or Celeb-DF (v2) are permanently inaccessible, only that
  they require a manual human step this round could not and should not attempt to
  substitute for. Does not claim AMSL is safe to auto-submit-to — flagged as
  self-service but still requires a human decision to supply real PII.
- **Files**: no `results/research/celebdfb_external_eval_20260827/` artifacts
  produced — the tool guard that blocks report-file writes from inside a
  subagent applies here too (same limitation noted on multiple ARCH-1 rounds
  above); full findings delivered in the executing agent's final chat message and
  folded into this registry entry. No checkpoint, split, or eval script was
  created since no data existed to run against.
- **Status**: final for this round (access-gating audit only). Not a NO-GO on the
  underlying comparison idea — it remains open pending the human email step above.
  No production checkpoint or `pipeline.py` touched (read-only, nothing was run).
  No git commit/add/push performed.

## P2A1-EVIDENCEHEAD-20260827: Layer2 patch evidence head, top-k pooling — **NO-GO** vs pre-declared faithfulness bar; head-randomization sanity check PASSES; GT-localization IoU respectable

- **Checkpoints**: `checkpoints/research/p2a1_evidence_head_20260827/evidence_head_last.pth`
  (primary, epoch 8/8) + `evidence_head_best.pth` + per-epoch `evidence_head_ep{1..8}.pth`.
  NOT `pipeline.DualBranchModel` — a new `PatchEvidenceHead` class (warm-started
  ShuffleNetV2 `spatial_branch` only from `shufflenet_v2_layer2_v811.pth`, FFT
  branch and original classifier dropped, new 7x7-grid patch head with top-k=10
  pooling). Scripts: `results/research/p2a1_evidence_head_20260827/{build_training_pool,
  content_key_audit,mask_gt,precompute_masks,train_evidence_head,evidence_plugin,
  evidence_sanity_check,eval_classification_regression,eval_classification_regression_e2e,
  gt_localization_eval}.py`. Pre-declared before training: `PRE_DECLARED.md`
  (this round's dir). Full findings: `FINDINGS.md` could not be written by the
  executing agent (tool guard: "subagents return findings as text"); delivered
  in that agent's final chat message and summarized here.
- **Train/val/test source**: classification pool = 8,000 fake + 8,000 filter
  sampled from `splits/v811_layer2_train.txt` (production Layer2 corpus,
  dead-path-filtered, 20,295 rows dropped — matches the already-disclosed
  `ARCH1-RECIPE-GAP-20260826` gap) + 400 FF++ **TRAIN-split-only** fake frames
  (100/method, video target-IDs verified against `split_ids.json["train"]`,
  official TEST-split IDs never read). 3,000 filter rows + all 400 FF++ rows
  carry precomputed (7,7) GT mask grids (landmark/skin-mask reconstruction from
  `filters/generate_filter_dataset.py`'s own region logic, and FF++ official
  masks via `phase2_ffpp_mask_xai/common.py`'s frame-alignment recipe,
  respectively) used as a λ=0.5 auxiliary BCE loss. Eval sources: True Test
  (fake+filter), Alibaba-clean (`ood_filter_ali_clean_20260821.txt`, 16,183),
  Shadow-filter, FF++ **official TEST-split** masks (73 images, fresh sample,
  disjoint from training), and the existing `faithfulness_sample_manifest.tsv`
  (250 images: 100 TT-fake/100 TT-filter/50 unseen-fake, reused verbatim).
- **Image-disjoint status**: content-key audit (`content_key_audit.py`, reusing
  `fingerprint()`/`fp_many()` from `audit_p1_r11_k3_content.py` verbatim) found
  0 unexpected exact-pixel overlap between the 16,400-row training pool and
  every eval set checked (True Test/AIGuard-unseen/Shadow×6/Alibaba-clean/
  StyleGAN2-decontam/FF++-official-test) after correctly excluding the
  already-disclosed AIGuard-fake↔StyleGAN2 contamination (CLAUDE.md
  2026-08-20); 10,644 raw near-dup (dHash≤4) hits were spot-verified (60-sample,
  mean-abs-pixel-diff 30.7-73.3 on 64x64) as hash-collision false positives at
  this data scale, not real duplicates. FF++ official TEST video-IDs (140)
  verified never read by the training-pool builder (in-script assertion).
- **Claimable conclusions**:
  1. A patch-evidence head with top-k pooling CAN be built and trained on a
     COPY of Layer2's backbone (warm-started) such that its native evidence
     map is driven by learned weights, not by architecture/geometry alone:
     head-randomization sanity check (reinit only the new patch-head conv
     layers) gives Spearman -0.66 to -0.82 across all 3 faithfulness-manifest
     groups (250 images) between trained-head and randomized-head maps — a
     sharp, clean PASS against the <0.5 bar, and a stark contrast with
     production Grad-CAM++'s already-recorded 0.83-0.97 FAIL on the same kind
     of check.
  2. This head achieves non-trivial GT-localization IoU on TWO independent
     GT sources never available to Grad-CAM++ before: FF++ official TEST-split
     masks (n=73, IoU@10/15/20% = 0.359/0.537/0.692, comparable to or exceeding
     the prior FF++ Grad-CAM++ round's 0.33-0.42 @top10%) and self-built
     filter-type region masks on the held-out True-Test filter group (n=100,
     IoU@10% 0.24-0.72 by type, 0.591 pooled). Pointing Game is also reported
     (0.96-1.00) but per the prior `ffpp_mask_verified_localization_20260818`
     round's `SKEPTICAL_REVIEW.md` finding, Pointing Game is METRIC_INSENSITIVE
     on face-crop data and is NOT independent evidence of localization quality.
  3. Classification: end-to-end (production Layer1 unchanged + this head as
     Layer2) True Test fake recall 99.26% and filter recall 91.94% both land
     inside production's existing bootstrap 95% CIs (non-regressive). Shadow
     filter recall 17.86% exceeds production's CI (an improvement, informational
     per production's own convention). Alibaba-clean filter recall 94.69% is a
     genuine regression, 2.81pp below the CI lower bound [97.50, 97.91] —
     plausibly attributable to dropping the FFT branch / original classifier
     for this candidate (not diagnosed further this round).
  4. Faithfulness (deletion/insertion vs center-Gaussian control,
     `faithfulness_eval.py` run verbatim with a plugin,
     `faithfulness_l2_evidence_plugin_shufflenet_v2_layer2_v811_evidencehead.json`):
     does NOT clear the pre-declared bar (CI-excludes-0 win on BOTH metrics,
     ALL 3 groups). Only unseen-fake (n=50) clears both. TT-fake (n=100) clears
     insertion only (deletion CI straddles 0). TT-filter (n=100) clears NEITHER
     — its insertion gain vs center-prior is significantly NEGATIVE
     (-0.0246, CI [-0.0322,-0.0177]), i.e. on filter images this head's map is
     measurably worse than "assume the face is centered" for the insertion
     metric specifically.
  5. **NO-GO** overall per the pre-declared rule (GO requires all of:
     non-regression, faithfulness-beats-center on all 3 groups/both metrics,
     Spearman<0.5). Criterion 3 clearly passes, criterion 1 partially passes
     (Alibaba fails), criterion 2 clearly fails. Do not wire into `pipeline.py`
     or promote this checkpoint.
- **Non-claimable / out of scope this round**: XAI-2 (evidence-driven
  explanation text generation) — not implemented. Region-set reduction to
  5 classes (eye/nose/mouth/skin/face_contour) — not implemented, this head's
  regions are a generic 7x7 spatial grid, not the named 5-class taxonomy.
  Second seed / longer mask-loss schedule — not run (single-seed budget per
  PRE_DECLARED.md; mask BCE loss was still falling at epoch 8, not plateaued).
  Root-cause diagnosis of the TT-filter insertion regression or the Alibaba
  classification regression — not undertaken this round.
- **Status**: final for this round. Read-only throughout w.r.t. `pipeline.py`
  and every frozen production checkpoint (`shufflenet_v2_layer1_v817sbi.pth`,
  `shufflenet_v2_layer2_v811.pth`). No git commit/add/push performed.

---

## P2A1-EVIDENCEHEAD-R2-20260828: evidence head round 2 (diagnose-then-fix) — both diagnosed round-1 problems FIXED (Alibaba 97.71% back at production point; TT-filter deletion now passes); pre-declared 6-cell faithfulness bar still 4/6 — the 2 failing cells PROVEN structurally unbeatable (GT-mask oracle and metric-aligned occlusion maps also fail them, by larger margins) — verdict **CONTINUE (bar amendment needs reviewer sign-off), not another retrain**

- **Checkpoints**: `checkpoints/research/p2a1_evidence_head_r2_20260828/evidence_head_r2_last.pth`
  (primary, ep 8/8, best val acc 0.9996) + per-epoch. New class
  `PatchEvidenceHeadV2` (`train_evidence_head_r2.py`): spatial_branch AND
  fft_branch warm-started from `shufflenet_v2_layer2_v811.pth`; patch head
  as round 1; **per-class pooling** (fake = top-k 10/49 unchanged, filter =
  dense mean over 49); FFT contributes a zero-initialized `Linear(256→2)`
  global logit bias (evidence map stays purely spatial, disclosed). Full
  corpus classification loss (126,529 rows = dead-path-filtered
  `v811_layer2_train.txt` minus 1 excised contaminated row, + the same 400
  FF++ TRAIN-split rows); mask supervision byte-identical to round 1 (same
  3,400 rows, same λ=0.5, round-1 `masks_grid.npz` reused by key). LR 2e-5,
  8 epochs, batch 64, cosine, seed 20260828. Scripts + all result JSONs in
  `results/research/p2a1_evidence_head_r2_20260828/`; `PRE_DECLARED.md`
  written after diagnosis, before training. `FINDINGS.md` blocked by tool
  guard (same as prior rounds); full findings in executing agent's final
  message, summarized here.
- **Root-cause diagnosis (done FIRST, inference-only on the round-1
  checkpoint — `diagnose_insertion_failure.py` / `diagnose_upper_bound.py`)**:
  1. **TT-filter insertion failure is structural to the harness, not the
     head.** Blur baseline is OUT-of-class for filter (production Layer2:
     p(filter|fully-blurred)≈0.045), so filter-class insertion measures
     "coherent centered un-blurring", at which the center-Gaussian control
     is near-optimal. Proof by upper bounds on production with the identical
     harness: **the GT mask itself as saliency loses insertion −0.0647
     CI[−0.0773,−0.0525] (every type, even localized eye GT −0.094);
     metric-aligned occlusion maps lose by −0.18~−0.28; hi-freq |x−blur(x)|
     by −0.14** — all far worse than round-1's candidate (−0.025). Symmetric
     finding: TT-fake DELETION has ~no dynamic range (blur baseline is
     IN-class for fake at p≈0.956; curves run 0.92→0.956). Hypothesis (a)
     diffuse-vs-sparse: partially supported (smoothing −0.057 = 4x worst)
     but all four types negative → not primary. Hypothesis (b) mask-fights-
     classification: refuted (cls loss →0.02, val 99.9%), reframed+confirmed
     as GT-vs-METRIC tension. Hypothesis (c) FFT drop: refuted for
     faithfulness (map fails filter insertion on its own decision surface
     too, −0.0099 CI excl 0).
  2. **Alibaba regression = systematically missing row family**: round-1's
     8,000 filter rows were 100% self-built (filter_data/LFW); zero
     third-party (`FFHQ_megvii_four_process`) rows — production Layer2 had
     ~23K of them, and Alibaba is a third-party neural filter.
- **Round-2 results vs round 1 (identical harnesses, same manifest)**:
  - Criterion 1 classification e2e (production L1 + candidate as L2):
    **PASS all gates** — Alibaba-clean **97.71%** (production point 97.71,
    CI [97.50,97.91]; round 1: 94.69 FAIL) — **regression fully fixed**;
    TT fake 99.63% (=production point), TT filter 91.94% (in CI), Shadow
    20.36% (above CI = improvement; round 1: 17.86). Isolated L2-only:
    Alibaba 99.96%, TT fake/filter 100%.
  - Criterion 2 faithfulness (deletion+insertion vs center-Gaussian, CI
    excl 0, 3 groups): **4/6 (round 1: 3/6) — bar FAIL**. Passing:
    TT-fake ins +0.0066 [+0.0060,+0.0074]; **TT-filter del +0.0055
    [+0.0020,+0.0088] (round-1 near-miss fixed by dense pooling)**;
    unseen-fake del +0.0160 / ins +0.0060 (both CI excl 0). Failing:
    TT-filter ins −0.0440 (the structurally unbeatable cell; round-2's
    more-GT-faithful map is accordingly further from the center prior —
    sits between round-1's −0.025 and the GT oracle's −0.065) and TT-fake
    del −0.0041 (the ~zero-dynamic-range cell). Pre-declared supplementary
    `--baseline mean` runs (non-gating, both heads): TT-filter deletion
    +0.0694 [+0.0623,+0.0765] (97% of images) — when the metric has range
    the filter map decisively marks evidence; filter insertion stays
    negative under mean too (−0.030) → center-prior dominance on insertion
    is a face-centered-coherence property of the class, not blur-specific.
  - Criterion 3 sanity: **PASS** (Spearman TT-fake −0.47 / TT-filter −0.76
    / unseen −0.38, all < 0.5; Grad-CAM++ reference 0.83–0.97 FAIL).
  - Criterion 4 GT localization (non-gating): held/improved — FF++ official
    TEST IoU@10/15/20 = 0.359/0.535/0.685 (round 1: 0.359/0.537/0.692);
    TT-filter pooled IoU@10 **0.610** (round 1: 0.591).
- **Verdict**: against the unamended pre-declared bar, NO-GO (2/6 cells
  fail). **Recommendation: CONTINUE, not retrain** — everything this round
  was chartered to fix is fixed; the two remaining failures are properties
  of the harness that the ground truth itself cannot pass (same finding
  class as the Pointing-Game METRIC_INSENSITIVE result, now for RISE-style
  insertion/deletion under a blur baseline on this hierarchy's classes).
  Proposed amendment (NOT self-adopted, needs reviewer sign-off): keep the
  center-prior bar on the four testable cells; for the two broken cells
  gate on an oracle-relative or class-neutral-baseline criterion. Head NOT
  wired into `pipeline.py`.
- **Data-integrity by-catch (production-relevant NEW finding)**: the
  full-corpus content-key audit (PASS after exclusion,
  `content_key_audit_r2_VERIFIED.json`) found `sd2.1\ff\803\503_651.png`
  in production's own `v811_layer2_train.txt` is **byte-identical**
  (md5 `89cd1515...`) to True-Test fake `sd2.1\ff\572\503_651.png` — a
  duplicate inside the DF40 sd2.1 corpus. Impact ≤1/270 of the TT fake
  recall cell; absent from round-1's sampled pool (why round 1's audit was
  clean); excised here (126,530→126,529). 44,894 near-dup dHash hits
  spot-verified (80 pairs, mean-abs-diff 26.5–144.7, 0 genuine) as
  collisions.
- **Non-claimable**: 5-class named-region set (eye/nose/mouth/skin/
  face_contour) — still a 7×7 grid; evidence-driven explanation text
  (XAI-2) — not implemented; multi-seed — single seed per protocol; any
  claim that the head "passes faithfulness" — it does not, per the
  unamended bar.
- **Status**: final for this round. Read-only w.r.t. `pipeline.py` and all
  production checkpoints. No git operations performed.

---

## P1A3-SAFETYFIX-20260827: P1-A3 fake+filter->real safety gap — RECIPEGAP1 warm-start + severity-targeted hard-neg mining combined — **best result in the whole ARCH-1/hardneg lineage, primary bar (<=2.00%) NOT met, gap narrowed to 1.23pp**

- **Goal**: close the fake+filter->real safety gap (production v8.17 2.80%,
  gate <=2.00%, unmet since v8.4) on production's real separate-model
  architecture, answering a documented literature gap (Libourel et al. IWBF
  2024; Concas et al. MetroXRAINE 2025 both measure this "beautification
  filter fools deepfake detector" phenomenon but leave mitigation
  unimplemented; Saeed et al. 2025 is the only fix attempt, framed as an
  attack). Two levers tested together for the first time: (1) targeted
  hard-negative mining, 3x-oversampling the two historically-worst stress
  conditions (`eye_enlarging`, `whitening_medium`) on top of a standard 1x
  pass over all 8; (2) `arch1_recipe_gap_20260826`'s validated RECIPEGAP1
  lineage warm-start recipe (L1<-`v811d`, L2<-`v88`, LR=1e-4, 10 epochs,
  batch=192, mixup off) as the base, per `docs/MASTER_PLAN_20260826.md`'s
  P1-A3 section.
- **Output**: `results/research/p1a3_safety_fix_20260827/` (`PRE_DECLARED.md`,
  `mine_p1a3_targeted_hardneg.py`, `hardneg_p1a3_manifest.txt` [867 rows
  pre-decon], `hardneg_p1a3_manifest_clean.txt` [802 rows, used for
  training], `content_key_audit_p1a3.py`/`.json`, `build_p1a3_splits.py`,
  `layer1_p1a3_train.txt` [248,703 rows], `layer2_p1a3_train.txt` [158,455
  rows], `train_p1a3.py`, `gates_P1A3.json`, `perimage_P1A3.json`). Full
  findings delivered in the executing agent's final chat message (tool
  guard blocked writing `FINDINGS.md`, same limitation as prior ARCH-1
  rounds). Checkpoints: `checkpoints/research/p1a3_safety_fix_20260827/
  p1a3_P1A3_layer1view.pth` (sha256 `6842fc79...`), `p1a3_P1A3_layer2view.pth`
  (sha256 `216a3afe...`).
- **Whitening-formula bug check (task-specified)**: confirmed still present
  in `results/research/hardneg_regen_20260826/mine_hardneg_regen.py`
  (its own `apply_whitening()` uses multiplicative LAB-L scaling, factor
  1.10/1.20/1.35 — does not match `filters/stress_test_filter_functions.py`'s
  additive blend-toward-white formula, `L += s*(255-L)`, s=0.15/0.25, the
  actual eval formula). **Fix applied this round**: mined exclusively via
  `mine_fake_filter_hardneg_v813.py`'s approach (imports `FILTERS` directly
  from the correct module), never touching the buggy reimplementation. The
  bug itself remains unpatched in `mine_hardneg_regen.py` (out of scope, a
  different round's artifact).
- **Mining**: 867 hard negatives (standard 1x pass, 8 conditions, 8,000
  source images; targeted 3x pass, eye_enlarging+whitening_medium only,
  24,000 source images), scored against RECIPEGAP1 (current best). Yield
  concentrated as designed: whitening_medium 360/32,000 (1.1%),
  eye_enlarging 328/31,810 (1.0%) = 79% of all mined rows from 2/8
  conditions.
- **Content-key audit**: STOP triggered (0 exact, 133 near-dup dHash<=4 hits
  touching 65/867 rows), visually confirmed genuine duplicates tracing to
  the already-documented `AIGuard/fake` <-> StyleGAN2/Alibaba source-pool
  overlap (CLAUDE.md 2026-08-20 correction), NOT a new leak. Resolved by
  dropping the 65 contaminated rows -> clean 802-row manifest used for
  training. Zero overlap against True Test/AIGuard-unseen/Shadow/
  celeba_test/ffpp_official_test confirmed.
- **Results vs RECIPEGAP1 (Lever 2 alone) / HARDNEGREGEN_best (old buggy
  hard-neg + shared-trunk Variant A)**: `fake_filter_stress` error
  4.33%->4.63%->**3.23%** (P1A3 best of all three, -1.10pp / -25% relative
  vs RECIPEGAP1); `alibaba_filter_recall` 98.23%->97.98%->**98.76%**
  (P1A3 best of all three, guardrail >=97% cleared with margin — the two
  levers did NOT trade against each other). Per-condition:
  eye_enlarging 12.59%->13.64%->**9.44%**, whitening_medium
  11.50%->13.94%->**8.01%**, face_reshaping 9.79%->8.04%->8.39% (roughly
  flat, now co-worst with the two targeted conditions since those
  improved faster — an unintended side effect of only targeting 2/3
  historically-worst conditions this round). True Test filter_recall
  92.77%->93.57%->94.38% (best of all three, still improving); True Test
  fake_recall back to 99.63% (HARDNEGREGEN_best had dropped to 97.78%).
- **Two regressions flagged** (exceed the pre-declared 3pp no-surprise
  band): AIGuard/unseen AUROC 0.8242->**0.7877** (-3.65pp vs RECIPEGAP1,
  already 1.7pp below production's 0.8410 before this round); Shadow
  real_recall 83.51%->**74.91%** (-8.6pp vs RECIPEGAP1, but reproduces
  HARDNEGREGEN_best's own near-identical drop [83.51%->75.27%, -8.24pp]
  regardless of which hard-neg pool was used — reads as a property of
  hard-neg mining onto this recipe in general, not specific to this
  round's targeting choices). FF++ zero-shot/official-test AUROC all moved
  down 1.9-2.7pp vs RECIPEGAP1, same direction/magnitude as
  HARDNEGREGEN_best's own FF++ regression.
- **Verdict**: primary bar (stress <=2.00%) **NOT met** — 1.23pp gap
  remains, narrower than RECIPEGAP1's 1.53pp gap and HARDNEGREGEN_best's
  1.83pp gap (each successive lever closed roughly a third of the
  remaining distance to the bar). Best absolute stress number is still
  production v8.17's own 2.80% (this round: 3.23%, still 0.43pp worse).
  **Reportable partial success against the literature gap**: a documented
  25% relative reduction in the exact fake+filter->real failure mode
  Libourel et al./Concas et al. measured but left unfixed, on production's
  actual architecture, without trading away the independently-validated
  Alibaba cross-algorithm gain.
- **Non-claims / follow-up not run**: single seed only (second seed
  recommended before treating 3.23% as stable); mining budget rebalance
  toward face_reshaping (now relatively worst-but-one) not attempted; root
  cause of the AIGuard/unseen regression not diagnosed; no promotion,
  TFLite export, or `pipeline.py` change attempted (out of scope for a
  single-seed diagnostic). Production checkpoints (`shufflenet_v2_
  layer1_v817sbi.pth`, `shufflenet_v2_layer2_v811.pth`) and `pipeline.py`
  untouched (read-only inputs only). No git commit/add/push.

## P1A3-RATIOSWEEP-20260827: P1-A3 hard-negative mining-ratio sweep — tests whether AIGuard/unseen + Shadow regression scales with hard-neg VOLUME rather than which images were mined — **25% ratio identified as new best candidate, clears AUROC>=0.80 gate that 100%/50% fail**

- **Goal**: `p1a3_safety_fix_20260827` (100% ratio = 802 clean rows x15
  oversample = 4.84%/7.59% of the L1/L2 corpus) and the earlier
  `hardneg_regen_20260826` both showed the SAME-SHAPE AIGuard/unseen +
  Shadow regression despite mining different specific images — suggesting
  the cost scales with hard-neg mixing ratio/volume, not image content.
  This round sweeps ratio (25/50/75/100% of the 802-row clean manifest,
  stratified subsample preserving the eye_enlarging/whitening_medium
  targeting composition, x15 oversample fixed) to find whether a lower
  ratio buys back generalization at an acceptable stress-error cost.
- **Output**: `results/research/p1a3_ratio_sweep_20260827/`
  (`PRE_DECLARED.md`, `build_ratio_splits.py`,
  `layer{1,2}_p1a3_r0{25,50,75,100}_train.txt`, `train_p1a3_ratio.py`
  [verbatim `p1a3_safety_fix_20260827` recipe, ratio-parameterized],
  `eval_p1a3_ratio_gates.py` [copy of root `eval_arch1_unified_gates.py`,
  only `ROUND_OUT` changed], `train_r0{25,50,75,100}.log`,
  `eval_r0{25,50,75,100}.log`, `gates_P1A3R0{25,50,75,100}.json`,
  `perimage_P1A3R0{25,50,75,100}.json`). FINDINGS delivered in the
  executing agent's final chat message (tool guard blocked writing
  `FINDINGS.md`, same limitation as prior ARCH-1 rounds). Checkpoints:
  `checkpoints/research/p1a3_ratio_sweep_20260827/
  p1a3_P1A3R0{25,50,75,100}_layer{1,2}view.pth`.
- **Content-key audit**: not re-run — every row at every ratio is a subset
  of `p1a3_safety_fix_20260827`'s already-audited clean 802-row manifest;
  a subset of a clean set cannot introduce a new leak.
- **Reproducibility sanity check (100% rerun vs `p1a3_safety_fix_20260827`
  original)**: stress 3.15% vs 3.23%, Alibaba 98.72% vs 98.76%, AIGuard/
  unseen AUROC 0.7833 vs 0.7877, Shadow real_recall 76.34% vs 74.91% — all
  within normal single-seed noise; recipe reproduces. This spread (up to
  1.8pp on Shadow, 0.44pp on AUROC) is the noise floor the sweep's ratio
  effects must be read against.
- **Results** (all vs RECIPEGAP1 anchor: stress 4.33%, Alibaba 98.23%,
  AIGuard/unseen AUROC 0.8242, Shadow real_recall 83.51%):
  25% ratio -> stress **3.36%** (-0.97pp), Alibaba **98.68%**, AUROC
  **0.8037** (-2.05pp), Shadow real_recall **80.65%** (-2.86pp), Shadow
  balanced **50.36%** (best of the sweep); 50% -> stress 3.41%, Alibaba
  98.41%, AUROC 0.7940 (-3.02pp), Shadow real_recall 79.93% (-3.58pp); 75%
  -> stress 3.76% (worst of sweep), Alibaba 97.55% (closest to the 97%
  guardrail), AUROC **0.8077** (best of sweep, -1.65pp), Shadow real_recall
  79.21% (-4.30pp); 100% (this round's rerun) -> stress **3.15%** (best of
  sweep), Alibaba 98.72%, AUROC 0.7833 (-4.09pp, worst of sweep), Shadow
  real_recall 76.34% (-7.17pp, worst of sweep).
- **Absolute-gate check (per `docs/MASTER_PLAN_20260826.md`'s 2026-08-28
  dual-track calibration: True Test filter>=90, fake>=95, Alibaba>=95,
  CelebA>=95, AIGuard/unseen AUROC>=0.80, StyleGAN2>=95)**: **only 25% and
  75% clear all six gates; 50% and BOTH 100% runs fail the AIGuard/unseen
  AUROC>=0.80 gate** (0.7940, 0.7833, 0.7877 respectively, all <0.80). This
  is the single clearest result of the sweep — the ratio that was actually
  trained and shipped as `p1a3_safety_fix_20260827`'s candidate does not
  clear the project's own current absolute-gate standard, while a lower
  ratio does. Also: production's own `fake_filter_stress` bootstrap CI is
  [1.92, 3.76] (per the same calibration note) — every ratio point's
  stress error (3.15-3.76%) falls at or inside that CI, so under the
  calibrated standard none of these candidates is statistically
  distinguishable from production on stress alone; RECIPEGAP1 (4.33%,
  outside the CI) remains the correct "thing being beaten."
- **No clean monotonic trade-off curve**: per-condition stress error is
  NOT monotonic in ratio for the two conditions this round's mining
  specifically targeted with 3x oversampling (eye_enlarging:
  10.49%->9.44%->11.54%->9.44% at 25/50/75/100%; whitening_medium:
  8.36%->9.76%->11.15%->8.36%) — 75% is worse than both 50% and 100% on
  both targeted conditions despite having more targeted hard-neg volume
  than 50%. Read as evidence that single-seed training variance is
  comparable in magnitude to the ratio effect being measured, not as a
  refutation of the ratio-volume hypothesis (the AUROC absolute-gate
  result above IS a real, gate-relevant difference between low and full
  ratio).
- **Verdict**: **25% ratio identified as the new best P1-A3 candidate**,
  superseding `p1a3_safety_fix_20260827`'s 100%-ratio result specifically
  because 100% fails the AIGuard/unseen AUROC>=0.80 absolute gate and 25%
  does not (75% also clears all gates but loses to 25% on stress, Alibaba,
  and both Shadow metrics — 25% dominates 75% on 3/4 head-to-head axes).
  25% retains 82-88% of the full-ratio's stress-error improvement over
  RECIPEGAP1 while paying only 45-56% of the AUROC regression and 33-40%
  of the Shadow real_recall regression (both well inside the pre-declared
  "within half" target). This is NOT a strict Pareto win (75% edges it out
  on AUROC and TrueTest balanced by ~0.4pp each) and is explicitly flagged
  as unconfirmed at single-seed granularity — **a second seed at 25% (and
  ideally 75%) is required before any promotion or change-proposal
  consideration**, since the sweep's own reproducibility check shows up to
  ~2pp of pure noise on the same metrics this verdict turns on. The
  ≤2.00% stress stretch-goal remains unmet at every ratio (closest: 100%
  rerun's 3.15%, still 1.15pp above); ratio-tuning alone does not close
  that gap, consistent with `p1a3_safety_fix_20260827`'s own framing that
  a genuinely different lever (not more/less hard-neg volume) would be
  needed for that stretch goal specifically.
- **Non-claims**: single seed per ratio point plus one 100% reproducibility
  rerun (not a substitute for the second-seed confirmation this verdict
  calls for); no re-mining or re-audit (subset of already-clean manifest);
  no promotion, TFLite export, or `pipeline.py` change. Production
  checkpoints and `pipeline.py` untouched (read-only inputs only). No git
  commit/add/push.
- **RESOLVED 2026-08-28 by `P1A3-SEED2-20260828`** (below): the required
  second seed was run. The AUROC>=0.80 gate pass reproduces (0.8102), but the
  25% candidate is **worse than production on `fake_filter_stress` on both
  seeds** and its FF++/Shadow gains are attributable to the RECIPEGAP1
  warm-start, not to hard-neg mining. **This verdict's "new best P1-A3
  candidate" framing is superseded — the candidate is NOT promotable.**

## P1A3-SEED2-20260828: second seed of the P1-A3 25%-ratio candidate — AUROC gate pass CONFIRMED, but candidate regresses on the workstream's own target metric on both seeds → **DO NOT PROMOTE, hard-neg-mining lever closed**

- **Goal**: `P1A3-RATIOSWEEP-20260827` named the 25% hard-neg mixing ratio the
  new best P1-A3 candidate but explicitly required a second seed before any
  promotion consideration, because that round's own 100% reproducibility rerun
  showed ~1-2pp of pure single-seed noise on the very metrics the verdict
  turned on, and 25% cleared the AIGuard/unseen AUROC>=0.80 gate by only
  +0.0037. This round runs seed-2 to settle promotability.
- **Seeds**: seed-1 = **20260827** (`train_p1a3_ratio.py` default, all four
  sweep points); seed-2 = **20260828** (this round). Seed is the ONLY varied
  factor.
- **Held byte-identical**: the seed-1 25% split files were **reused verbatim,
  not regenerated** — `layer1_p1a3_r025_train.txt` (239,689 lines, MD5
  `9c33716b687999b09e6cd0dfd738c8a0`) and `layer2_p1a3_r025_train.txt`
  (149,441 lines, MD5 `333ddeff9e4c9be12717d20040474a78`) from
  `p1a3_ratio_sweep_20260827/`. Same RECIPEGAP1 warm start (L1<-v811d full,
  L2<-v88 partial 361/2), LR=1e-4, 10 epochs, batch=192, CosineAnnealingLR,
  inverse-freq class weights, label smoothing 0.1. `train_p1a3_seed2.py`
  differs from `train_p1a3_ratio.py` in exactly 3 lines (round dir, `S2` tag,
  split source path); `eval_p1a3_seed2_gates.py` is **string-identical** to the
  sweep's `eval_p1a3_ratio_gates.py` except `ROUND_OUT` (verified
  programmatically) — no harness confound.
- **Output**: `results/research/p1a3_seed2_20260828/` (`PRE_DECLARED.md`,
  `train_p1a3_seed2.py`, `eval_p1a3_seed2_gates.py`, `train_r025_seed2.log`,
  `eval_r025_seed2.log`, `gates_P1A3R025S2.json`, `perimage_P1A3R025S2.json`,
  `train_log_P1A3R025S2_L{1,2}.csv`). FINDINGS delivered in the executing
  agent's final chat message (tool guard blocked `FINDINGS.md`, same limitation
  as prior ARCH-1/P1-A3 rounds). Checkpoints:
  `checkpoints/research/p1a3_seed2_20260828/p1a3_P1A3R025S2_layer{1,2}view.pth`
  (SHA256 `8a08021c…` / `8e7c8e67…`), L1 best F1=0.9772, L2 best F1=0.9992.
- **Content-key audit**: not re-run, pre-declared — identical already-audited
  subset of the clean 802-row manifest; a subset of a clean set cannot leak.
- **Track-1 absolute gates (2026-08-28 dual-track calibration): 6/6 PASS on
  BOTH seeds** — True Test filter 93.57/92.37 (>=90), fake 99.63/99.63 (>=95),
  Alibaba 98.68/98.00 (>=95), CelebA 98.27/97.40 (>=95), AIGuard/unseen AUROC
  **0.8037/0.8102** (>=0.80), StyleGAN2 99.50/99.43 (>=95). **The specific risk
  this round was run to test — that 25%'s AUROC gate pass was a single-seed
  fluke — is resolved affirmatively: it reproduces** (spread 0.0066).
- **Two-seed results vs production v8.17** (seed-1 / seed-2 / mean / delta):
  `fake_filter_stress` **3.36/4.11/3.74%** vs 2.80% (**+0.94pp WORSE**;
  seed spread 0.74pp < the regression, so this is a real effect, and seed-2
  falls OUTSIDE production's stress CI [1.92,3.76]); `stressdev` 2.17/3.11/2.64
  vs 1.23 (+1.40 worse); AIGuard/unseen AUROC 0.8037/0.8102/0.8070 vs 0.8410
  (**-0.0341**); CelebA 98.27/97.40/97.83 vs 99.33 (-1.50); Shadow real
  80.65/82.44/81.54 vs 74.91 (**+6.63**); Shadow filter 20.07/19.00/19.53 vs
  12.19 (**+7.35**); Shadow balanced 50.36/50.72/50.54 vs 43.55 (**+6.99**);
  True Test filter 93.57/92.37/92.97 vs 91.97 (+1.00); Alibaba
  98.68/98.00/98.34 vs 97.71 (+0.63); in-domain filter recall 90.51 vs 87.55
  (+2.95); FF++ official-test frame AUROC(e2e) 0.6339/0.6215/0.6277 vs 0.5738
  (**+0.0539**), video 0.6534/0.6391/0.6463 vs 0.5820 (**+0.0643**), zero-shot
  0.6309/0.6240/0.6275 vs 0.5597 (**+0.0678**).
- **Methodological finding — True Test paired metrics (n=249) cannot arbitrate
  1-2pp claims**: seed-to-seed spread was real_recall **7.23pp**, strict
  6.02pp, balanced 3.01pp — *larger than every between-ratio difference the
  ratio sweep used to rank its four points*. **The sweep's ranking of ratios by
  True Test balanced accuracy was inside noise and must not be cited.**
  Large-population metrics were stable by contrast (Shadow balanced 0.36pp,
  AUROC 0.0066, StyleGAN2 0.07pp, FF++ frame 0.0124).
- **Attribution finding — the gains are NOT from hard-neg mining**: against
  `RECIPEGAP1` (identical warm-start recipe, ZERO hard-neg: AUROC 0.8242,
  Shadow real 83.51%, FF++ frame 0.6407 / video 0.6594, stress 4.33%), the 25%
  mixing **strictly degrades** AUROC (0.8242->0.8070), Shadow real
  (83.51->81.54) and FF++ (0.6407->0.6277 frame, 0.6594->0.6463 video). Its
  ONLY contribution is stress 4.33%->3.74%, which still lands worse than
  production's 2.80%. **The FF++ +5-7pp and Shadow +7pp cross-domain gains
  belong to the RECIPEGAP1 warm-start recipe, not to hard-negative mining.**
- **Track-2 trade-off judgment: NET NEGATIVE -> DO NOT PROMOTE.** The
  v8.11->v8.17 precedent (which accepted a 93.57%->91.97% filter-recall
  regression) does not cover this case: v8.17 regressed on a *secondary* metric
  while improving BOTH its headline objectives (AUROC 0.8150->0.8410, stress
  3.71%->2.80%). This candidate does the reverse — it regresses on **the
  defining objective of its own workstream** (P1-A3 exists to drive
  fake+filter->Real safety error DOWN toward <=2%; this pushes it UP to 3.74%,
  +34% relative) **and** on the AUROC gate production itself only passes at the
  margin, leaving the candidate 0.004-0.010 above a hard bar. A
  comparable-scale regression is not automatically disqualifying; a regression
  on the very metric the round was commissioned to improve is.
- **Stretch goal**: `fake_filter_stress <= 2.00%` NOT met (3.74% mean) —
  reported as stretch-goal status per the 2026-08-28 calibration, not as a
  blocking gate. The candidate also fails the calibration's weaker bar ("not
  worse than production 2.80% beyond CI [1.92,3.76]") on seed-2.
- **Verdict**: **DO NOT PROMOTE. Close the hard-negative-mining lever for
  P1-A3.** Five rounds (`hardneg_regen_20260826`, `p1a3_safety_fix_20260827`,
  the four-point ratio sweep, its 100% rerun, and this seed replication) now
  agree that mining volume trades cross-domain generalization for stress error
  and never reaches production's 2.80%. The <=2% stretch goal is not reachable
  by data mixing and needs one of the three untried mechanisms in
  `docs/MASTER_PLAN_20260826.md` (real-centered prototype learning, log-scale
  FFT, MoE shared expert). **The thread worth picking up instead is RECIPEGAP1
  evaluated on its own as a production candidate** — it clears the AUROC gate
  comfortably (0.8242), holds the lineage's best Shadow real recall (83.51%)
  and carries the full FF++ +6pp gain; its one blocker is stress 4.33%. That is
  a different trade-off to put on the table explicitly, not another mining
  round.
- **Non-claims**: two seeds is a reproducibility check, not a power analysis —
  no CI claimed from n=2, spreads reported as observed ranges. The
  RECIPEGAP1-attribution comparison uses that round's single-seed numbers
  (direction consistent across three metrics and both seeds here, but no
  RECIPEGAP1 second seed was run). No promotion, no `pipeline.py` change, no
  TFLite export; production checkpoints, `pipeline.py` and all split files were
  read-only. No git commit/add/push.

## EXTSAFETY-20260828: literature-comparable safety numbers WITHOUT Celeb-DF-B — Concas protocol reproduced on own Celeb-DF-v2 + public beautified-face datasets (B-LFW / FairBeauty) zero-shot — inference-only, production v8.17

- **Type**: inference-only (no training; GPU shared with the running P1-A3
  ratio-sweep job, batch 32 only). Output:
  `results/research/external_safety_bench_20260828/` (`build_concas_cells.py`,
  `concas_cells_manifest.tsv`, `cells/` [4,000 generated images],
  `score_v817.py`, 9 `scores_*.tsv`, `compute_concas_metrics.py` →
  `concas_metrics.json`, `audit_blfw_overlap.py` → `blfw_overlap_audit.json`,
  `compute_blfw_metrics.py` → `blfw_metrics.json`,
  `lfw_controls_summary.json`). External data (~2.1GB, both under the 5GB
  pre-announcement bar): `external_data/blfw/` (B-LFW.zip 222MB, direct
  download, CC BY-NC(-SA) 4.0), `external_data/fairbeauty/`
  (val_fair_beauty.zip 674MB), `external_data/lfw_control_112/` (generated
  control). FINDINGS.md blocked by the subagent tool guard (same as prior
  rounds); full findings in the executing agent's final message, key numbers
  folded in here. Production checkpoints and `pipeline.py` untouched. No git.
- **Scorer**: production stack exactly as `pipeline.py` (Layer1 v817sbi +
  Layer2 v811, JPEG q85 → 224 → Normalize(0.5), `decision_rule.decide()` at
  published tm=0.5). **Sanity anchor passed**: on the 400-frame
  `celebdf_v2_blind_holdout.txt` the harness reproduces the documented
  production numbers exactly (real recall 29/199=14.6%, fake recall 96.0%,
  O-Real-vs-O-Fake AUC(p_manip) 0.5693 vs documented 0.568).
- **Route 1 (Concas et al. arXiv:2509.14120, MetroXRAINE 2025 — protocol
  reproduced, "same protocol, NOT same images")**: their paper (re-fetched and
  read from arXiv HTML this round; Table I/II numbers now independently
  verified, including VGG19 APCER 30.1%→48.4%, AlexNet 22.3%→8.0%, VGG19
  O-Real-vs-F-Fake AUC 75.7→67.1, AlexNet 84.1→89.3) specifies ONLY "a
  smoothing filter ... radius values c 3–5% of face height". Ambiguity
  resolutions documented in `build_concas_cells.py`: Gaussian blur
  (cv2.GaussianBlur, r=round(c·face_height), ksize=2r+1), face height =
  MediaPipe FaceLandmarker landmark y-extent (project-standard tool; 1/2000
  no-detect fallback to image height), whole-image application, c∈{3.0%,5.0%}.
  Frames: 400-frame holdout kept intact as the comparable subset + expanded
  to 1,000 real + 1,000 fake (seed 20260828, from clean_paths pools; 200-fake
  APCER CI ±7pp too wide) — both scopes in `concas_metrics.json`, all
  conclusions identical. **Results (full 2×1,000 scope)**: four-cell 3-class
  distribution — Real-orig 14.0% real/86.0% fake/0% filter; Real-filtered
  0.5%/99.5%/0%; Fake-orig 6.3%/93.7%/0%; Fake-filtered **0%/100%/0%** (both
  c). Rule-based APCER (fake accepted as real) **6.3%→0.0%**; threshold-
  transfer convention (EER threshold fixed on originals, score=p_manip; EER
  45.0% — near-chance domain) APCER 45.0%→9.0%(c=3%)/19.9%(c=5%); asymmetric
  AUC O-Real-vs-F-Fake **0.577→0.790(c=3%)/0.699(c=5%) — RISES**. vs
  literature: v8.17 matches AlexNet's benign direction (APCER drops, AUC
  rises) and does NOT show VGG19's vulnerability (APCER 30.1→48.4, AUC
  75.7→67.1). **Honest mechanism**: NOT graceful filter recognition — the
  filter class fired on 0.0% of beautified frames; Gaussian smoothing pushes
  p_manip UP for everything (fail-closed), so BPCER worsens 86.0%→99.5% on
  this zero-shot H.264 domain. Their detectors are in-domain-trained
  (80/20 Celeb-DF); only the beautification-induced DELTA is comparable, not
  absolute levels.
- **Route 2 (public datasets, zero-shot cross-ALGORITHM filter test)**:
  - **B-LFW** (OpenFilter, NeurIPS D&B 2022, arXiv:2207.12319; 12,000 PNG
    112×112, 8 real Instagram beauty filters via `filters.npy`, direct
    download no gate): overlap audit vs `lfw/` training pool (13,328) — 0
    exact decoded-pixel SHA256, 324/12,000 (2.7%) dHash≤4 near-dups;
    corpus-level identity overlap 100% BY CONSTRUCTION → framing = "seen
    base corpus, unseen filter algorithms". **v8.17: 0.45% → filter
    (correct), 5.2% → real (miss), 94.4% → fake (over-trigger)**; per-filter
    spread small (filter-correct 0.07–0.80%). Detected-as-manipulated 94.8%.
  - **Resolution controls** (`lfw_controls_summary.json`): same 2,000 LFW
    originals (training real source) native-res → 84.7% real / 15.3% filter /
    0% fake; bilinear-downsampled to 112px → **73.2% filter** / 26.6% real /
    0.25% fake. So downsampling alone pushes toward *filter*, while B-LFW's
    beautification pushes into *fake* — the fake verdict is attributable to
    the beautification (+MTCNN crop-tightness, unseparated), not resolution.
  - **FairBeauty val** (beautified FairFace, 9,806 PNG 282×282, unseen base
    corpus + unseen filters; no paired originals downloaded): 12.9% filter /
    24.0% real / 63.1% fake.
  - **LFW-Beautified** (arXiv:2203.06082): freely available (GitHub, MIT)
    but deliberately NOT evaluated — variants are AR props (dog nose,
    sunglasses) + contrast enhancement at 64×64, outside this project's
    filter-class semantics; a number on it would be uninterpretable.
  - **Deepfake-Eval-2024** (arXiv:2503.02857): HuggingFace
    `nuriachandra/Deepfake-Eval-2024` is GATED (ToU + institutional email +
    evidence of deepfake work, manual review, gating until May 2027) — same
    human-application blocker class as Celeb-DF-B; reported, not fetched.
- **Claimable**: (1) "same protocol reproduced" comparison vs Concas et al. —
  v8.17 does not exhibit the beautified-fake→real vulnerability on the shared
  attack axis (APCER falls, O-Real-vs-F-Fake AUC rises), citable ONLY with the
  fail-closed mechanism (BPCER 86→99.5%, filter class 0%) and the zero-shot vs
  in-domain-training asymmetry stated in the same breath. (2) Public
  zero-shot cross-algorithm numbers: real Instagram filters are detected as
  MANIPULATED at 94.8% (B-LFW) / 76.0% (FairBeauty) but typed as `filter` at
  only 0.45% / 12.9% — an external, contamination-caveat-free confirmation of
  the P1-B1 cross-algorithm finding (Alibaba 3–35% type accuracy), now shown
  at the class level, not just the artifact-type level.
- **Non-claims**: no claim of same-image comparability with Concas et al.
  (their test set not distributed; kernel type their paper never specifies);
  no claim that Route 1's APCER advantage reflects in-domain competence
  (score-space EER on originals is 45% — near-chance); no video-level claims
  (frame-level only, frames within a video correlated); FairBeauty
  over-trigger vs miss split not further diagnosed (no original-FairFace
  control this round); B-LFW crop-tightness confound unseparated.

---

## `CROSSDATASET-TABLE-20260828` — 文獻可比 cross-dataset 表（DFD 取得並評測；DFDC/DFDCP/FFIW 人工門檻）

- **Round**：`crossdataset_table_20260828`，2026-08-28，**inference + dataset
  acquisition only，無訓練**。`pipeline.py`、全部 production checkpoint、
  `checkpoints/research/ffpp_protocol_20260823/*` 皆唯讀。無任何 git 操作。
  協定預先宣告於 `results/research/crossdataset_table_20260828/PRE_DECLARED.md`。
- **服務目標**：`docs/MASTER_PLAN_20260826.md` **P1-A2**。
  `eval1_crossdataset_20260827` 只填出一格（Celeb-DF-v2），本輪把標準表補到兩格。

### 1. 取得性稽核（4 個資料集）

| 資料集 | 判定 | 大小 | 人工動作 |
|---|---|---|---|
| **DFD**（DeepFakeDetection, Google/Jigsaw）| ✅ **已取得** | c23 全量 約 25 GB；本輪取 2.0 GB 種子子集 | 無 |
| **DFDC**（Kaggle）| ❌ 人工門檻 | 全量 471 GB；API 可見僅 4.44 GB | 用專案 Kaggle 帳號點一次比賽規則同意鍵 |
| **DFDCP**（DFDC Preview）| ❌ 人工門檻 | 未公布 | AWS 帳號 + IAM + dfdc.ai 白名單（2024-25 回報流程壞掉）|
| **FFIW10K** | ❌ 人工門檻 | 未公布 | Google Form + 作者人工核准（偏好 .edu）|

- **DFD 取得依據**：本專案**原本就有** `DeepFakeDetection_c23.zip` + `actor_c23.zip`
  （證據：`FaceForensics_raw/.cache/huggingface/download/*.metadata` 殘留，來源
  HF 鏡像 `KWChuang/FaceForensics`），兩個 zip 在本 session 清理磁碟時被刪，
  該鏡像現已 404。改用官方 `faceforensics_download_v4.py` 的 URL scheme 從 TUM
  伺服器重新取得（`download_dfd_c23.py`）。⚠️ **合規註記**：FF++ 官方政策是
  表單申請制，TUM 伺服器實際無認證開放；本專案先前已完成該表單且原本就持有這批
  資料，故重新取得無爭議，**但這不是通用繞道**。
- **DFDC 門檻已實測確認**：`competitions data list` 可用，實際下載回
  HTTP 403，訊息為「必須先接受本比賽規則才能下載檔案」；Kaggle 無 API 可接受規則。
  **另注意**：即使點了同意，API 只露出 `test_videos/`（400 支，**無公開標籤**）
  與 `train_sample_videos/`（400 支 + `metadata.json` 標籤，1.87 GB）；
  DeepfakeBench 用的 5,000 支標籤 test set 不在其中。
- **拒用的替代來源**：HF `dfb-data/deep-fake-detection-cropped`（3,293 支，
  0.79 GB，無 gate）**已檢視後拒用**——影片已預先裁成 **112x112**，破壞 crop
  convention，且依本專案 `EXTSAFETY-20260828` 的解析度對照組，低解析度輸入會把
  模型推向 fake；README 為自動生成樣板、無來源聲明。用它會是製造數字不是量測。
- 🔴 **對任務前提的更正**：FFIW **不是**標準表的欄位。DeepfakeBench 跨資料集表的
  欄位為 CDFv1 / CDFv2 / DF-1.0 / **DFD** / **DFDC** / **DFDCP** / Fsh / UADFV
  （本輪逐字核對 repo README 確認），FFIW 在該論文與 README 中完全不存在。
  **任何「DeepfakeBench FFIW」數字都是無據的**。真正的第四欄是 DFDCP。

### 2. DFD holdout 建構

- `download_dfd_c23.py`（seed 20260828）：363 支 actor real 抽 150、3,068 支
  manipulated 抽 300（實際下載完 182 支後停止，TUM 限速）。
- `extract_dfd_frames.py`：**596 real + 925 fake = 1,521 幀，來自 162 支影片**。
  crop 邏輯**逐字 import** `extract_ffpp_protocol_frames.detect_and_crop`
  （MediaPipe landmark hull、`MARGIN=0.35`、JPEG q90），frame-index 規則相同，
  兩類皆 10 幀/支（完全對齊 `FRAMES["test"]`）。
- ⚠️ **兩件 reviewer 必須知道的事**：①**只有約 49% 的 DFD 影片產出任何一幀**
  （162/332）——DFD 的 actor 影片含大量遠景（`walk_down_hall`、
  `walking_outside_cafe`），在取樣幀上 MediaPipe 偵測不到臉；已逐幀手驗
  `01__walk_down_hall_angry.mp4`（10/10 無偵測）。這是本專案 crop convention
  下的語料性質、不是 bug，但代表本子集**偏向近景場景**。②唯一與
  `extract_ffpp_protocol_frames.job` 的差異：不取樣的幀改用 `cap.grab()` 前進而非
  `cap.read()`，**已驗證位元相同**（`np.array_equal`），7.6x 加速；必要原因是
  DFD 為 1080p、單支約 1,500 幀，原寫法推估超過 5 小時。
- **限速實測（供後人參考）**：TUM 伺服器 0.01 MB/s（單連線）→ 0.15 MB/s（32 連線）
  → 尖峰 0.75 MB/s，與連線數幾乎無關；同一台機器對 HuggingFace 是 12 MB/s。
  官方腳本另兩台伺服器（`canis.vc.in.tum.de:8100`、`falas.cmpt.sfu.ca:8100`）
  **皆已死**。全量 25 GB 需以「一整夜」為單位估算。

### 3. 污染稽核 — 乾淨

`audit_dfd_contamination.py`（三金鑰，方法同 `audit_p1_r11_leakage.py`），
對照 FF++ protocol frames（35,366，即 FF++-only checkpoint 的全部訓練分布）
與 production Layer1 split（236,673）：

| 金鑰 | vs FF++ protocol | vs prod Layer1 |
|---|---|---|
| K1 路徑 | **0** | **0** |
| K2 檔名 stem | **0** | **0** |
| K3 解碼像素 sha256 | **0** | **0** |
| K3 dHash Hamming <= 5 | 242（15.9%）| 229（15.1%）|

dHash 欄看似警訊，故**未照單全收而是逐對裁決**（`verify_dfd_neardup_hits.py`）：
取最相似的 60 對，在共同 128x128 灰階網格上算實際正規化像素相關係數——
FF++ 對照組**最高僅 0.828、中位數 0.731**，prod 對照組**最高 0.671、中位數 0.467**，
**兩組皆 0 對超過 0.90，更無超過 0.95**（真正的重新編碼複本會大於 0.95）。
**判定：dHash 碰撞，不是重複**——64-bit dHash 對緊裁人臉是弱金鑰，所有這類裁切
共享同一低頻版面。最相似對的並排圖存於 `neardup_montage_*.jpg` 供人工檢視。
另獨立確認：production Layer1 split 的 source 欄位分布中**完全沒有 FaceForensics
或 DFD 來源**，故 DFD 對兩個受測模型都是真零樣本。

### 4. 🔴 發現既有 Celeb-DF-v2 數字的 crop convention 不一致（本輪最重要的方法學修正）

既有 Celeb-DF-v2 holdout（`splits/celebdf_v2_blind_holdout.txt`，即已公布的
0.5680 / 0.6875 背後那 400 幀）是用 `extract_celebdf_frames.py` 的
**YuNet + `FACE_PADDING=0.2`**（較緊）裁切；而本專案**所有** FF++ 數字、
本輪 DFD、以及 FF++-only checkpoint 自己的訓練分布，用的都是
**MediaPipe landmark hull + `MARGIN=0.35`**。**兩格根本不是同一種裁法**。

`build_celebdf_mediapipe_control.py` 以相同來源影片、相同 frame index 重裁
（400 幀取回 389，11 幀 MediaPipe 無偵測）；`eval_celebdf_crop_paired.py` 再用
**同樣那 389 幀的原始 YuNet 裁切**評分，單一變因為 crop：

| 模型 | YuNet pad 0.20 | MediaPipe margin 0.35 | Δ |
|---|---|---|---|
| FF++-only FULL | 0.6888 | **0.7278** | **+3.90 pp** |
| FF++-only SPATIAL | 0.7062 | **0.7358** | **+2.96 pp** |
| production v8.17（Layer1 P(manip)）| 0.5740 | 0.5794 | +0.54 pp |

（frame-level AUC，n=389，配對）

**v8.17 的 label 分布位移遠大於它的 AUC 位移**：緊裁下判 90.8% 為 fake，
MediaPipe 裁下只判 30.1%。→ **operating point 對 crop convention 高度敏感、
即使排序不變**，這一點必須寫進論文 limitation，緊挨著部署主張。

**拍板**：文獻對照表採用 **MediaPipe/0.35** 版 Celeb-DF-v2 數字，因為那才和 DFD、
和 FF++、和模型自己的訓練分布同一裁法。原本公布的 0.6875 / 0.5680 不是錯的，
是另一組自洽量測，但不該與 DFD 並列在同一張跨資料集表裡。

### 5. 可宣稱的結論

- **frame-level AUC，全部 train on FF++ c23 only、零樣本**：
  我方 DualBranch（2.55M 參數）Celeb-DF-v2 **0.7278**、DFD **0.8487**；
  spatial-only（1.80M）Celeb-DF-v2 **0.7358**、DFD **0.8602**。
  對照 DeepfakeBench Xception（20.81M）Celeb-DF-v2 0.7365、DFD 0.8163。
  → **Celeb-DF-v2 打平（98.8-99.9% of Xception），DFD 勝出（104.0-105.4%），
  用 8.6-12.2% 的參數量。**
- **production v8.17（不同訓練配方，非文獻可比，須另列）**：Celeb-DF-v2 0.5794、
  DFD 0.6887。**同架構的 FF++-trained 模型在兩個外部語料上都領先 production
  +0.15~+0.17 AUC**——`ffpp_protocol_20260823` 的「差距來自訓練資料不是架構」
  結論，首次在第二個完全外部語料上獲得確認。
- **FFT 分支邊際貢獻的第四次獨立證據**：spatial-only 在**兩個**外部語料上都
  贏過 dual-branch（Celeb-DF-v2 +0.8pp、DFD +1.2pp）且小 29%。與
  `paper_readiness_execution_20260822` 及其 2026-08-23 兩次複現一致
  （「低 FPR 有真實貢獻、一般操作區間無淨收益」）。

### 6. 不可宣稱事項

- **不可**寫「cross-dataset 贏過 Xception」不加限定：只有 4 欄中的 2 欄；
  未測的 DFDC 恰好是文獻表上所有方法都最弱的一欄（0.6955-0.7191）。
- **不可**把 DFD 數字當作全量 DFD：本子集為 3,431 支中的 162 支，且偏近景場景。
- **不可**跨 frame-level / video-level 比較。我方 DFD video-level：FULL 0.9034、
  SPATIAL 0.9203、v8.17 0.7395（frame→video gap +5.5~6.0pp，與 Celeb-DF++
  arXiv:2507.18015 報告的 +3~+6pp 一致）。**DeepfakeBench 沒有 video-level 表**，
  不可為 baseline 自行構造；若論文需要 video-level 參照，須引 Celeb-DF++ 自己的
  重訓數字（Xception 79.1 / EffB4 73.8 / SPSL 74.4 / UCF 76.1）並明講那是
  Celeb-DF++ 的重訓、**不是** DeepfakeBench 的 checkpoint（SPSL frame-level
  兩來源差距達 68.4 vs 76.50）。
- **不可**引用的參數量：SPSL、UCF（無任何一手來源）；Xception 的「20.8M」是
  正確推導（Chollet CVPR 2017 Table 3 的 22,855,952 減 1000-way fc 加 2-class
  head）但**不是可直接引用的已發表數字**，Keras 列的是 1000 類版 22.9M。
- 我方 AUC 的信賴區間為 Hanley-McNeil，**未做 video 叢集校正**，真實區間更寬
  （1,521 幀只來自 162 支影片）。

### 7. 順帶更正 `CLAUDE.md` 的長期參數量數字

`CLAUDE.md` 多處寫「1.26M params」——那是 **ShuffleNetV2 spatial backbone 單獨的**
參數量（1,269,840）。從 checkpoint 實測，完整 DualBranch 偵測器是 **2,545,429**
（spatial 1,269,840 + FFT 618,691 + classifier 656,898）；spatial-only 變體
1,795,666；production 三模型堆疊合計 6,364,798。

### 8. 產出物

腳本：`download_dfd_c23.py`、`extract_dfd_frames.py`、`eval_dfd_crossdataset.py`、
`audit_dfd_contamination.py`、`verify_dfd_neardup_hits.py`、
`build_celebdf_mediapipe_control.py`、`eval_celebdf_crop_paired.py`、
`eval_celebdf_v817_20260828.py`。
結果：`results/research/crossdataset_table_20260828/`（`dfd_eval_results.json`、
`dfd_contamination_audit.json`、`dfd_neardup_adjudication.json`、
`neardup_montage_*.jpg`、`celebdf_v817_results.json`、
`celebdf_mp035_control_results.json`、`celebdf_crop_convention_paired.json`、
`PRE_DECLARED.md`）。資料：`DFD_c23/`。
split：`splits/research/crossdataset_table_20260828/celebdf_holdout_mp035.txt`。
⚠️ 本輪 FINDINGS 因工具限制未落地為檔案，完整內容於執行 agent 最終訊息回報並
併入本條目。
**既有數字複現核對**：`eval_celebdf_v817_20260828.py` 在原 400 幀 holdout 上
逐位元組複現 `eval1_crossdataset_20260827` 的 ffpp_FULL 0.6875、ffpp_SPATIAL
0.7049，以及 CLAUDE.md 的 v8.17 Celeb-DF-v2 0.568。

### ⚠️ SUPERSEDED IN PART — see `EVAL3-HEADLINE-RIGOR-20260901`（2026-09-01 追加，僅追加不改寫上文）

本條目的以下具體宣稱已被 `EVAL3-HEADLINE-RIGOR-20260901`（n=3 seed 重訓 + video-cluster
bootstrap 95% CI，完整數字見 `results/research/eval3_headline_rigor_20260901/honest_table.json`、
`bootstrap_ci.json`、`PRE_DECLARED.md`）撤回或更正，**不得再以本條目的原始措辭引用**：

1. **「Celeb-DF-v2 打平、DFD 勝出」（第 5 節「可宣稱的結論」、第 6 節與上文表格多處）**——
   video-cluster 95% CI 顯示 Xception 的文獻點值（0.7365 / 0.8163）落在本文 4/4 格
   （DualBranch + spatial-only × 兩資料集）的 95% CI 之內，正確措辭改為「統計上無法區分」。
2. **「DFD +3.2pp / 104.0% over Xception」「Celeb-DF-v2 98.8-99.9% of Xception」一類方向性
   百分比宣稱**——同一理由撤回。
3. **第 5 節「FFT 分支邊際貢獻的第四次獨立證據：spatial-only 在兩個外部語料上都贏過
   dual-branch」**——按 seed 配對後，Celeb-DF-v2 的 spatial-minus-full delta **變號**
   （s20260823 +0.0071／s20260901 −0.0087／s20260902 +0.0178），判定為 seed 雜訊而非方向一致
   的證據，此框定撤回。DFD 的 delta 三 seed 同號但極小（mean +0.0049±0.0059）。
   **此撤回不影響**本專案既有「FFT 分支在一般操作區間無淨收益、低 FPR 有真實貢獻」的結論
   （該結論建立在 `paper_readiness_execution_20260822` 及其兩次獨立複現上，與本條目的這兩格
   無關）。
4. **參數量「2,545,429 / 1,795,666」用於與 Xception 比較時**——這兩個數字是「參數 + BatchNorm
   buffer」，與 Xception 的 params-only 20.81M 不是同口徑比較。**Trainable 參數量為
   2,528,742（DualBranch）／1,779,430（spatial-only）**，論文中凡是跨架構參數量比較須採用
   trainable 數字並加註腳；本條目原文陳述模型自身體積（不做比較）時仍可引用含 buffer 版本。

**未受影響、仍可照原文引用**：DFD holdout 建構（596 real + 925 fake / 162 支）與三金鑰污染稽核
結果；crop convention 敏感度稽核（第 4 節）；取得性稽核（DFDC/DFDCP/FFIW 人工門檻，第 1 節）；
production v8.17 的 0.5794 / 0.6887（非文獻可比，另列陳述本身不受影響，只有「同架構 FF++
checkpoint 領先 production」這個對照未變）。

新增的允許措辭：「一個 2.53M-trainable 參數的 dual-branch ShuffleNetV2，在本文能量測的兩個
文獻協定跨資料集 benchmark 上，與 DeepfakeBench 20.81M 參數的 Xception 統計上無法區分，且
僅用約 12% 的參數量」。Video-cluster bootstrap（以 video 為重抽樣單位）自本輪起訂為本專案
影片語料 AUC 信賴區間的方法學標準，取代 naive frame-level bootstrap 與 Hanley-McNeil。

---

## P1-PROTO1: real-centered prototype learning (mechanism #1) — `p1_prototype_20260828`, NO-GO

- **問題**：`MASTER_PLAN_20260826.md`「尚未嘗試的機制清單」第一項——用 RCDN
  （arXiv:2601.12111）/LRD-Net（arXiv:2604.10862）的 real-centered prototype
  loss 取代 CE 分界學習，直接對症 Layer1 跨域泛化弱（production FF++官方test
  0.5747 frame / CDF-v2 0.5794 / DFD 0.6887）。十餘輪配方排列組合已榨乾，本輪
  換一個全新 loss 機制而非排列組合。
- **忠實實作**：兩篇論文的公式皆已 WebFetch 全文取得並逐條核對（摘要不含公式，
  用 arxiv.org/html/ 版本取得）。RCDN Eq 5-10 逐條實作於 production DualBranch
  backbone 上（128-d embedding、L2-normalize、單一可學習 prototype、
  L_center=真實樣本到中心均方距離+假樣本 hinge、L_sep=batch mean 距離 hinge、
  CE head 保留輸出）；LRD-Net 的 EMA prototype+drift 正則化另開一個獨立 arm
  （PROTOEMA）。論文未載明的超參數（m、λ_c、λ_s、δ、λ_d）於訓練前寫入
  `PRE_DECLARED.md` 並說明理由，非事後調參。
- **四個 arm，單一 seed 20260828，訓練資料=production Layer1 真實語料
  （`layer1_sbi_augreal_train.txt`，236,673 rows after dead-path filter）**：
  PROTOIM（ImageNet init+RCDN loss）、CEIM（ImageNet init+純CE control）、
  PROTOWS（warm-start v811d+RCDN loss）、PROTOEMA（ImageNet init+LRD-Net EMA）。
  Layer2 全程用 production v811 不變。
- **關鍵單變量對照結果（隔離 loss 機制本身的效果）**：
  - ImageNet init 配對（PROTOIM vs CEIM，僅 λ_c=λ_s=0 不同）：**純 CE 的
    CEIM 贏過 RCDN-loss 的 PROTOIM**——cross-domain mean（FF++/CDF-v2/DFD 三者
    平均）0.7316 vs 0.7060（**+2.56pp 反方向**），Alibaba 83.33% vs 71.96%。
    預先宣告的「PROTOIM 贏 CEIM ≥2pp」判準**被推翻，且方向相反**。
  - warm-start 配對（PROTOWS vs 既有 `arch1_recipe_gap_20260826` 的
    RECIPEGAP1，純CE、同血緣暖啟動）：cross-domain mean **幾乎打平**
    （0.6819 vs 0.6842，−0.23pp，單 seed 雜訊範圍內），RECIPEGAP1 甚至
    stress 更低（4.33% vs PROTOWS 6.29%）。**Prototype loss 在暖啟動情境下
    對跨域泛化沒有可量測的增量貢獻**。
- **絕對門檻（雙軌制六項）**：僅 PROTOWS（6/6 全過，Alibaba 98.03%）與既有
  RECIPEGAP1（6/6 全過，Alibaba 98.23%）通過；**三個 ImageNet-init arm
  （PROTOIM/CEIM/PROTOEMA）全部因 Alibaba 崩潰（72-83% vs ≥95 門檻）未過**，
  與 loss 機制無關（三種不同 loss 皆同樣崩潰）——在第三種獨立 loss 幾何上
  重新確認 `arch1_recipe_gap_20260826` 的「暖啟動血緣才是 Alibaba 跨演算法
  filter 泛化的關鍵，不是 loss 函數」結論。
- **PROTOWS 表面「過關」的歸因**：雖然 PROTOWS 單獨看符合本輪預宣告的
  「meaningful」門檻（cross-domain mean +6.76pp、六項絕對門檻全過），但上述
  兩組對照顯示這個增益**完全來自暖啟動初始化（已知且已被 RECIPEGAP1 利用的
  槓桿），不是來自 prototype loss 本身**。PROTOWS 對 RECIPEGAP1 的微幅領先
  （unseen AUROC 0.8574 vs 0.8242、Shadow real 86.0% vs 83.5%）較可能來自
  資料差異（PROTOWS 用完整 production 語料含 22,297 張退化配對真實負樣本，
  RECIPEGAP1 的 ARCH-1 資料檔缺這批）而非 loss 差異，已於 `PRE_DECLARED.md`
  事前聲明此混淆因子。
- **副作用（stretch goal，非門檻）**：PROTOWS 的 `fake_filter_stress`=6.29%
  為本輪最差數字，遠高於 production 2.80% 與 RECIPEGAP1 自身的 4.33%；三個
  ImageNet-init arm 反而 stress 較低（1.92-2.62%），構成本輪未解決的第二條
  trade-off 軸線。
- **裁決：NO-GO——real-centered prototype learning 對本專案不是真實槓桿**。
  單一 seed，機制驗證性質，不建議任何 arm 升格；`MASTER_PLAN_20260826.md`
  「尚未嘗試的機制清單」第 1 項標記為已測試/已否證。
- 完整證據：`results/research/p1_prototype_20260828/`（`PRE_DECLARED.md`、
  `train_proto_layer1.py`、`eval_proto_gates.py`、`eval_proto_crossdomain.py`、
  `gates_*.json`／`crossdomain_*.json`／`train_log_*.csv` 四個 arm 各一份，
  另加對既有 RECIPEGAP1 checkpoint 補跑的 `crossdomain_RECIPEGAP1.json`）；
  checkpoint 於 `checkpoints/research/p1_prototype_20260828/`。⚠️ 本輪 FINDINGS
  因工具限制未落地為檔案，完整內容於執行 agent 最終訊息回報並併入本條目。
  未修改任何 production checkpoint 或 `pipeline.py`，無 git 操作。

---

## P1-IDPROBE1: identity consistency as an orthogonal signal (mechanism #4) — `p1_identity_probe_20260828`, **REJECT**

- **問題**：同日 `P1-PROTO1` 證實「換 loss 幾何」仍讀同一批紋理/頻域證據，
  因此仍落在既有 stress ↔ 跨域泛化的 trade-off 前緣上（該前緣已由
  `decision_rule_unify_20260826` 證明可由單一純量門檻重現）。本輪改問：
  是否存在**正交於紋理**的證據？候選＝身份一致性，理由來自本專案自己的類別
  語義（`filter`＝身份**保留**的美化；`fake`＝身份**改變**的操弄），且美顏會
  摧毀紋理但理論上不摧毀身份。外部動機：Saeed et al. arXiv:2509.07178（2025）
  逐字回報美顏濾鏡把主流偵測器 ASR 推到 64.63%／GAN 增強 75.12%。　⟵ ⚠️ **2026-09-05 撤回**：跨協定比較無效。同協定對照（`EXTERNAL-BASELINES-20260905`）11 個公開偵測器在同一批 Celeb-DF-B 影格、recall 對齊 90.4% 下 beautified ASR 為 6–21%，**低於 ours 的 23.4%**；且 ours 對 untreated Celeb-DF 換臉 AUROC 僅 0.521、把 87.7% 真影格叫 fake，此母體上的 ASR 不具濾鏡強健含義。
- **性質：零訓練、純推論探針**。未訓練、未升格、未修改 `pipeline.py` 或任何
  checkpoint，無 git 操作。設計目的是在投入一輪訓練**之前**先驗證 teacher
  訊號是否存在。
- **量測定義**：reference-free 內/外臉身份一致性（ICT 概念用現成 ArcFace 實作）
  ——InsightFace `buffalo_l` 偵測 → `face_align.norm_crop` 對齊到標準 112×112
  → 在標準模板上以中心 (56,72)、半軸 (30,34) 的橢圓（涵蓋模板 5 點 landmark）
  分出 inner／outer 兩個互補遮罩變體 → 各自取 ArcFace 嵌入、L2 正規化 →
  **`s_id` = cos(e_inner, e_outer)**。3,744 列，逐張**同一記憶體影像**上同時
  計算 `s_id` 與 production v8.17 預測（`preprocess_jpeg` q85 →
  `transform_infer` → `decision_rule.decide`），確保正交性分析可逐張對齊。
  Cell D 逐位元組沿用 stress harness 的 fake 選取（`rglob`、stem 開頭 `fake`）
  與 `PIL→RGB→resize(224)→np.array→ffunc` 呼叫慣例，濾鏡從
  `filters/stress_test_filter_functions.py` **import 而非重寫**。
- **事前宣告的判準與結果**（全部 bootstrap 10k、image-level 95% CI）：
  | 判準 | 門檻 | 結果 | 判定 |
  |---|---|---|---|
  | Gate 0 指標鑑別力（同人 vs 異人隨機錯排）| AUC ≥0.70 | **0.9299** [0.9078, 0.9502] | **PASS** |
  | 前提：美顏是否摧毀身份訊號 | median(B) > 中點 0.0421 | **0.0914** | **PASS** |
  | **主要**：(−s_id) fake+filter vs real+filter | ≥0.70 建／<0.60 否決 | **0.5402** [0.5020, 0.5790] | **REJECT** |
  | 幾何濾鏡崩潰（addendum 定為 pass/fail）| — | **未發生**（幾何 0.5602 > 光度 0.5335）| n/a |
  | 正交性（production 判錯的 64 張）| 描述性 | 0.6458 [0.5732, 0.7163] | 弱正向 |
- **Gate 0 的作用**：遮罩後影像對 ArcFace 是分布外輸入，指標可能只是在量遮罩
  偽影。同人中位數 0.0830 vs 異人 0.0012、AUC 0.9299 ⇒ 指標確實承載身份資訊，
  **因此下面的否決是關於資料、不是關於壞掉的量測**（等同 XAI-1 對 Grad-CAM++
  先做 Adebayo sanity check 的紀律）。
- **失敗原因不是文獻警告的那一個**：訊號在**套濾鏡之前**就已接近無效——
  True Test fake vs real 0.5747／fake vs filter 0.5803／unseen 未修圖 fake vs
  real+filter 0.5839，套濾鏡只再掉約 0.04。**缺口在美顏之前**。
  per-source 分解給出原因（事前宣告為必做，且本輪由它承載結論）：
  pixart 0.7203 > DiT 0.5672 > ddim 0.5309 > SiT 0.5274 > sd2.1/ff 0.5016 >
  **sd2.1/cdf 0.4437（低於隨機）**——**DF40 EFS 合成整張臉，根本不存在
  「內部來源身份／外部目標身份」的斷裂**可供 ICT 式一致性偵測。此方向已於
  `PRE_DECLARED.md` 事前寫明（「預期在整臉合成上弱於 swap」），屬**預測命中，
  非事後補寫**。
- **事前宣告的風險未成真，如實記錄**：addendum 依已發表的 FR-under-filter 研究
  預測幾何濾鏡（`eye_enlarging` 1.18／`face_reshaping` 0.92）最傷身份，並事先
  規定「只在光度濾鏡成功＝機制沒解到難的一半」。實測**相反**——eye_enlarging
  0.5959 為八條件最高、幾何均值 0.5602 高於光度 0.5335（gap −0.0268）。
  推測因本專案濾鏡為單參數合成，弱於該研究使用的商用 app 濾鏡（addendum 已
  預先指出這使前提對我們更安全）。
- **Claim（可宣稱）**：
  ① **身份一致性在美顏下確實被保留**（real+filter 中位數 0.0914 ≥ 未修圖 real
     0.0830），與 Mirabet-Herranz, Galdi & Dugelay, IEEE TBIOM 7(1) 2025 一致；
     本專案「filter＝身份保留」的語義定義獲得獨立量測支持。
  ② **身份一致性不是本專案可用的 fake/filter 判別證據**，因 fake 母體以 EFS 為主。
  ③ Celeb-DF-v2 mp035 holdout 上零訓練的 (−s_id)＝**0.6678** [0.6142, 0.7211]
     **高於 production v8.17 在同一批 holdout 的 0.5794**——跨域弱點源自
     swap/reenactment **訓練覆蓋缺口**而非架構，第五次獨立確認。
  ④ production 判錯的 64 張 stress 圖上 (−s_id) AUC 0.6458（CI 排除 0.5）、
     判錯組中位數 0.0506 低於判對組 0.0798 ⇒ 身份**確實**帶有紋理模型缺少的
     資訊，只是太弱。
- **Non-claim（不可宣稱）**：
  - **不可**宣稱「身份一致性對 deepfake 偵測無用」——本輪只證明它對**本專案的
    EFS 為主母體**無用；Celeb-DF-v2（swap 語料）上它反而勝過 production。
  - **不可**把 ③ 當成對等 benchmark：`s_id` 是單一純量無訓練分數，v8.17 在做
    三分類任務，分數類型不同，僅 suggestive。
  - **不可**把 ④ 當成可建構的機制：n=64，事前已宣告為描述性。
  - **不可**宣稱本輪機制為原創（見下）。
- **Novelty 位置（事前記錄於 addendum，撰寫時點＝Gate 0 之後、主要結果之前）**：
  機制**已被佔用**——**ICT, Dong et al., CVPR 2022**（arXiv:2203.01318，摘要
  逐字 "identity inconsistency in **inner and outer face regions**"，且已是
  reference-free）＋**Huang et al., CVPR 2023**（"Implicit Identity Driven
  Deepfake Face Swapping Detection"，人臉辨識器於**訓練期**提供身份目標、蒸餾
  進 backbone）。另 TFMD (Computers & Security 2022) 已有 real/replacement/
  reenactment 三分類的身份改變 vs 保留軸；Zhu & Long 2025 為 ArcFace+三分類+
  anti-forensic 但**推論時需要 ArcFace**且第三類是對抗樣本非濾鏡。**唯一未被
  佔用者**＝用此訊號分「美顏 vs 偽造」語義類別＋邊緣預算下零推論成本
  （SELFI／Zhu & Long 皆需 runtime ArcFace）。該位置仍空，**但本輪未提供值得
  去取的證據**。⚠️ Huang et al. 的 CVF 頁面回傳 403，「訓練期限定」係由 loss
  設計推得，**任何書面宣稱前必須先核對 PDF**。
- **反向文獻風險（已記錄，未來若重啟必須處理）**：Implicit Identity Leakage
  (CVPR 2023, arXiv:2210.14457) 與 FRIDAY (arXiv:2412.14623) 主張身份資訊
  **傷害**跨域泛化，FRIDAY 刻意**削弱**身份訊號（與本提案反向）。以本專案
  反覆出現的語料庫捷徑 meta-finding，身份頭是可能的新捷徑向量；addendum 已
  事先規定任何後續訓練輪必須加做「ID 頭是否惡化 OOD」的專門消融。
- **決策**：**不建造特權資訊頭**（0.5402 的 teacher 訊號不值得），身份一致性
  槓桿就 production 目標母體**關閉**。省下一輪訓練＋強制的 OOD 捷徑消融。
  若未來目標母體轉為 swap/reenactment 為主，本結論不適用，可重啟。
- **機制搜尋的收斂條件（同日兩次機制級否決後歸納，寫回 MASTER_PLAN）**：
  `P1-PROTO1` 重組**同一批證據**故仍在前緣上；本輪提供**真正正交的證據**但該
  證據**在 EFS 母體中幾乎不存在**。**下一個機制必須同時：對紋理正交、且在整臉
  合成上確實存在。** 此條件可用於事前篩選候選，不必每個都跑一輪。
- **產出物**：`results/research/p1_identity_probe_20260828/`
  （`PRE_DECLARED.md`（含同日 novelty addendum）、`FINDINGS.md`、
  `probe_identity.py`、`analyze_identity.py`、`scores_A.tsv`／`scores_BCE.tsv`／
  `scores_D.tsv` 共 3,744 列、`emb_A.npz`、`analysis_results.json`、
  `run_BCE.log`／`run_D.log`）。臉部偵測覆蓋率：cell A/B/C/E 零失敗；
  cell D 2,296 個濾鏡變體中 2,288 個成功（8 個為既有 MediaPipe landmark 失敗，
  stress harness 本身同樣 skip）。

---

## P2-XAI2-TEXT1: evidence-driven filter explanation text — `p2_xai2_evidence_text_20260828`, **SHIPPED (text layer only)**

- **問題**：MASTER_PLAN P2-A1／reviewer R4——filter 類解釋為固定 cue 句庫拼接，
  「24 張圖幾乎同文」。本輪做 XAI-2 第一層（文字由實際量測值驅動，每句可回溯到
  一個數字），**刻意不依賴 evidence head**（`P2A1-EVIDENCEHEAD-R2-20260828` 的
  兩個結構壞格仍待裁定），因此不被該決策阻擋。
- **性質**：純推論 + 文字層。無訓練、無 checkpoint 變更、無 git 操作。
  `pipeline.py` 僅改解釋生成函式；改前版本備份於本輪資料夾。
- **本輪查出的實際缺陷**：四個 filter 模板中三個斷言單張影像層級不存在的證據，
  **其中兩個斷言的量從未被計算過**——`eye_enlarging` 模板寫
  "Abnormal eye-to-face ratio detected" 但程式碼從未計算任何眼／臉比值；
  `face_reshaping` 寫 "geometric compression around the jawline and cheeks"
  同樣無對應量測。其分支來源（`classify_artifact` CNN 或 Grad-CAM region
  fallback）中，Grad-CAM 已由 `eval2_xai1_rigor_20260826` 證實統計上等同固定
  中心高斯先驗且未過 Adebayo sanity check（R5）⇒ 該句子雙重無據。
- **量測與驗證設計**：在**配對** True Test（249 張 filter vs 各自的 249 張 LFW
  原圖，配對關係由 `audit_truetest_pairing.py` 建立、photo-level 洩漏 0）上同時做
  ①配對效應（Wilcoxon + sign rate）與②單張影像鑑別力（AUROC vs pooled real，
  bootstrap 10k 95% CI）。**推論時沒有原圖可比對，故只有②能授權逐張斷言**——
  此方法論沿用 P2-R7（`p2_explanation_v2_20260823`）的既有先例。
  六個量：`texture_var`／`brightness_L`（既有 `compute_skin_stats`）＋
  `eye_width_ratio`／`eye_area_ratio`／`jaw_face_ratio`／`face_aspect`
  （MediaPipe FaceMesh 標準索引，沿用 `has_face` 既有偵測器，零新依賴）。
- **核心結果——配對效應極強、單張影像近乎隨機**：
  | 型別 | 量 | 配對 sign rate | Wilcoxon p | 單張 AUROC |
  |---|---|---|---|---|
  | whitening | brightness_L | **1.000**（每一張都變亮）| 7.6e-12 | 0.5537 [0.4727, 0.6308] |
  | smoothing | texture_var | **0.016**（98.4% 下降）| 6.0e-12 | 0.5521 [0.4737, 0.6303] |
  | eye_enlarging | eye_area_ratio | **0.952** | 1.1e-11 | 0.5510 [0.4728, 0.6293] |
  | face_reshaping | face_aspect | **0.000**（100% 下降）| 7.6e-12 | **0.7457 [0.6782, 0.8101]** |
  | face_reshaping | jaw_face_ratio | 0.097 | 3.9e-10 | 0.5661 [0.4850, 0.6449] |
  根因：受試者間變異遠大於濾鏡效應——真實 `brightness_L` sd=27.2 而 whitening
  中位數只位移 +4.04；真實 `texture_var` p05-p95 為 52-300 而 smoothing 中位數
  只位移 −13.6。
- **事前訂定並套用的規則**（訂於量測前）：AUROC ≥0.75 可斷言異常／0.60-0.75
  只可報值不可稱異常／<0.60 **移除主張**（不改寫、不加避險詞，直接移除，比照
  fake 類 region 主張的處理）。四型中僅 `face_reshaping` 的 `face_aspect` 落在
  REPORT_ONLY 層，其餘全為 REMOVE。
- **實作**：`_detect_landmarks()` 自 `has_face()` 抽出（行為不變、不新增偵測器）；
  新增 `measure_filter_evidence()`／`_position_phrase()`／
  `build_filter_explanation()`；`build_explanation()` 增加 `pil_img=None` 參數；
  `run_single` 一處呼叫點。舊 `TEMPLATES` 保留供 provenance 與 legacy 無影像路徑。
  文字內容＝artifact 分類器 top type ＋本張影像各量測值 ＋相對真實參考範圍
  （p05/p50/p95, n=250）的位置 ＋由**最弱**量測決定的單一警語。
- **驗收與非回歸**（以備份的改版前 `pipeline.py` 與現版在同一程序內跑同一批圖）：
  | 檢查 | 結果 |
  |---|---|
  | 分類非回歸（prediction／class_probs／confidence／artifact_types／suspicious_regions）| **249 張 0 差異** |
  | headline 24 張相異解釋數 | **4/24 → 24/24** |
  | 全 filter split（229 張判為 filter）| 5（2.2%）→ **224（97.8%）** |
  | token entropy | 5.617 → 6.315 |
  | 事前宣告門檻 ≥90% distinct | **PASS** |
  | schema v2.1.0（filter／fake／real 三類）| **PASS** |
- **Claim（可宣稱）**：
  ① reviewer R4 就 filter 類**已解決**：解釋為逐張、可回溯到量測值的文字。
  ② 自建濾鏡的配對效應可被客觀量測且極強（四型 p ≤ 1.1e-11）。
  ③ **本專案解釋層第三次出現同一失效模式**（P2-R7 fake 類配對 p=3.9e-95／單張
     AUROC 0.539；EVAL-2 校準證明 precision 式形容詞在 OOD 不成立；本輪 filter
     類）⇒ 可作為一個**模式**寫進論文：**配對／消融證據例行性地授權了單張推論
     無法支撐的主張，而解釋層正是這個落差變成使用者可見斷言的地方。**
- **Non-claim（不可宣稱）**：
  - **不可**宣稱解釋變得更「有資訊量」——本輪只讓文字誠實且逐張特定；所報量測
    在單張層級是弱證據，文字本身即明白寫出這一點。
  - **不可**宣稱 P2-A1 完成：完成定義的後半「指涉區域經 GT 驗證」**未達成**，
    現行文字刻意不做 region 指涉。
  - **不可**把 24/24 當成解釋品質指標——它是多樣性指標，不是正確性指標。
  - **不可**用本輪任何數字宣稱分類效能改變：本輪逐欄位證實分類完全未動。
- **順帶查獲的既有校準問題（已記錄，本輪未修）**：`infer_artifact_type()` 的
  `_SMOOTH_TEXTURE_THR=210`／`_WHITE_BRIGHT_THR=147`，註解宣稱
  "calibrated on AIGuard real baseline: Real images: texture 360~1070"，但
  True Test real（LFW 底圖，n=250）實測為 **52-300、中位數 137** ⇒
  **190/250（76.0%）真實影像落在 smoothing 門檻之下**、33/250（13.2%）超過
  whitening 門檻。**嚴重性有限**：production 載入 `artifact_classifier_v6.pth`，
  該規則僅為 fallback，且本輪非回歸檢查確認 249 張 `artifact_types` 全未改變；
  但常數帶有註解未揭露的母體依賴性。未修的理由：超出本輪事前宣告的 text-only
  範圍，且修改會破壞非回歸保證。另開一輪處理。
- **產出物**：`results/research/p2_xai2_evidence_text_20260828/`
  （`PRE_DECLARED.md`、`FINDINGS.md`、`measure_geometry.py`、`measures.tsv`、
  `validation.json`、`eval_text_diversity.py`、`diversity_results.json`、
  `pipeline_pre_xai2_20260828.py.bak`）。**Rollback ＝還原該 .bak 檔**。

---

## P2-SBIMASK1: 自生成 SBI 配對 mask 定位驗證 — `p2_sbi_mask_localization_20260831`, **PASS（evidence head 接線前置條件滿足）**

- **問題**：evidence head（`P2A1-EVIDENCEHEAD-R2-20260828`）經 2026-08-31
  oracle-relative 裁定後 6/6 過 faithfulness，接線前僅剩一個條件：
  **image-disjoint、自生成、帶像素級 GT mask 的定位驗證**（自己生成的 fake
  確切知道改了哪些像素，blend mask＝免費 GT；即組員建議路線，XAI-1 早已點名
  「SBI blend mask 是免費 GT，尚未使用」）。純推論，無訓練、無 production 變更。
- **方法**：`sbi.sbi_generator.make_sbi` 原樣重用（未改），底圖取 `celeba_test/`
  （eval-only）seed 20260831 抽 500 張，**500 試 / 497 可用**（3 張無臉，已記錄），
  每張存 blend mask PNG。評測程式碼**逐字重用 R2 輪自己的** IoU/pointing
  game/中心先驗實作（與 R2 的 FF++ 0.359／filter-GT 0.591 直接可比）。
  PRE_DECLARED 在生成前寫定。
- **Disjointness／污染稽核 PASS**：路徑層級 head 訓練 manifest（126,529 列）
  0 筆 celeba；內容層級 500 張底圖 MD5 對全 manifest **0 碰撞**
  （`content_key_audit.json`）。
- **主要結果（n=497，image-level bootstrap 10k 95% CI）**：
  | Map | IoU@10% | IoU@15% | IoU@20% | Pointing |
  |---|---|---|---|---|
  | **Evidence head（fake map）** | **0.4485** [0.4335, 0.4636] | **0.4896** | **0.4695** | 0.8008 |
  | 中心高斯 σ=56 | 0.4009 [0.3906, 0.4106] | 0.4386 | 0.4346 | 0.7767 |
  | Random 7×7／224² | 0.0475／0.0532 | — | — | 0.093／0.103 |
  **配對差 IoU@10% ＝ +0.0476，CI [+0.0358, +0.0590]，排除 0**；IoU@15/20 同向
  顯著，且**每個 blend-ratio 分層皆成立**。事前宣告的主要門檻（贏過中心先驗、
  CI 排除 0）**PASS**。Pointing game 差 +0.0241 不顯著——**與事前宣告一致**
  （該指標在臉部裁切上已知不敏感，METRIC_INSENSITIVE 既有結論，不作證據）。
  絕對 IoU 高於 R2 FF++ 錨點 0.359 屬事前預告的 mask 面積效應（SBI mask 佔幀
  11.98%），判準是贏過中心先驗、不是對齊 0.359。
- **附帶發現（不影響本輪判定，登錄檔級）**：production v8.17 在這批 SBI fake 上
  **僅 13.48% 判為 manipulated**（fake 5.43%／filter 8.05%／real 86.52%，
  mean composite p_fake 0.142），捕捉率隨 blend ratio 上升（0.25→2.6%、
  0.75-1.0→~17%）。⚠️ **2026-08-31 同日更正（使用者追問後查證
  `build_p1_r9_sbi_data.py` 原始腳本）**：執行 agent 原本的歸因「訓練底圖為
  IMDB-WIKI/VGGFace2 風格、非 CelebA 風格」**不準確**——實際 SBI 訓練底圖配額為
  imdbwiki 12,000＋celeba_train **6,000**＋lfw 4,000＋vggface2_train 300，
  **CelebA 佔 27%**，且該腳本刻意重用已是 label-0 real 的同一批照片作底圖
  （設計意圖：pseudo-fake 與訓練 real 只差 blend，逼模型學 blend 邊界而非內容；
  eval 池含 celeba_test 有 grep 斷言排除）。**因此「底圖語料風格」不能乾淨解釋
  13.48%，此為未解異常**，候選假設（皆未驗證）：①本輪生成參數與訓練時不同
  （本輪 q95 JPEG／per-image seed，訓練生成的品質/增強分布待比對）；
  ②production 為 SBIAUG arm，其 degradation-matched real 負樣本可能壓低對
  輕度 blend 的敏感度；③celeba_train 取樣（18,315 clean）與 celeba_test 的
  細微分布差。需一輪小型診斷（比對訓練生成參數＋在 celeba_train 底圖上重跑
  同一生成）才可歸因，**在此之前不得引用「語料庫捷徑第 N 實例」的說法**。
- **Claim**：evidence head 的定位品質在 image-disjoint、自生成、精確 GT 上成立
  ⇒ **接線前置條件滿足，頭取得接線資格**。
- **Non-claim**：①不改變任何 production 行為（本輪只授權接線）；②不可宣稱
  production 能在 CelebA 風格 SBI 母體上有效攔截（13.48%，見附帶發現）；
  ③pointing game 不作定位品質證據。
- **產出物**：`results/research/p2_sbi_mask_localization_20260831/`
  （PRE_DECLARED、FINDINGS、生成/稽核/評測腳本、`base_image_list.txt`、
  `generation_log.jsonl`、`scores.tsv`、`sbi_images/`＋`masks/`、
  6 張定性面板 PNG（最佳 0.85／最差 0.000 皆入列））。

---

## P2-EVIDENCEWIRE1: evidence head 接線 `pipeline.py`（filter class）— `p2_evidence_wire_20260831`, **SHIPPED（含上線前發現並修正的評分 bug）**

- **前置條件**：`P2A1-EVIDENCEHEAD-R2-20260828` oracle-relative 裁定 6/6 過
  ＋`P2-SBIMASK1` image-disjoint 定位驗證 PASS，兩者皆滿足後執行本輪接線。
  純推論＋文字層變更，無訓練。決策路徑（prediction/confidence/class_probs/
  artifact_types/suspicious_regions）逐欄位驗證 0 差異（769 張）。
- **⚠️ 上線前發現並當場修正的問題（使用者對 region cross-tab 提出質疑後查證）**：
  首版用**每區平均值**評分 7×7 patch map 對應的 5 個具名區域（eyes/nose/mouth/
  skin/face_contour），non-regression 與 schema 皆過、**首次回報 PASS**，但
  region sanity 交叉表**298 張裡 296 張 top-1 皆為 nose、與 artifact_type
  無關**——與本專案已抓過一次的 Grad-CAM≈中心先驗失效同構。診斷：**區域大小
  混淆**——eyes 僅 4 格、nose 6 格、skin 19 格，小區域只需局部峰值即可贏過平均，
  大區域峰值被稀釋掉。同時發現附加句子**引用錯誤驗證來源**：寫的是
  `P2-SBIMASK1` 的 fake-class map（在自生成 SBI 影像上）驗證數字，卻用來
  背書 filter-class 的區域輸出——兩個不同的 map、不同的驗證，被錯誤黏在一起。
- **補測（`verify_filter_localization_vs_center.py`，逐字重用 R2 輪的 IoU
  程式碼與同一批 100 張 True Test filter GT mask，此前這批 GT 從未做過中心
  先驗對照）**：filter-class map **確實整體贏過中心先驗**——paired IoU@10%
  head 0.6103 vs 中心先驗 0.5652，**配對差 +0.0451，bootstrap 10k 95% CI
  [+0.0268, +0.0637]，排除 0**；但**效果依型別高度不均**：eye_enlarging
  +0.1099、smoothing +0.0275、whitening +0.0222、**face_reshaping +0.0009
  （與中心先驗統計上打平，無訊號）**。
- **修正（同日，推論層修改，未重訓）**：評分改為**機率質量（總和）相對中心
  先驗基準**——新增 `_CENTER_CELL_MASS`（解析解 7×7 中心高斯質量表，σ=56，
  與補測控制組同一顆），僅回報 `head_mass − center_mass > 0` 的區域，
  移除大小混淆（質量對質量比較與區域大小無關）。附加句子改引用修正後的正確
  數字（0.61 vs 0.57）並明寫型別不均（含 face_reshaping 無訊號）。
- **修正效果（769 張全量重驗）**：非回歸維持 0 差異、schema/fail-safe/延遲
  皆持平（5.72ms mean）；eye_enlarging top-1 region eyes 1/103 → **6/103**，
  且逐張句子現在會同時列出多個過關區域及其量值（如 eye_enlarging 圖常同時列
  eyes 與 nose 各自正值）而非只給單一標籤。**誠實殘留限制**：修正評分公式後
  **nose 仍是多數 top-1**（eye_enlarging 103 張裡 97 張仍是 nose）——診斷為
  7×7 網格解析度的真實限制（32px 格子無法乾淨分開解剖學狹窄的 eyes 區與緊鄰
  的 nose-bridge 格，且多型別判別訊號確實集中在該鄰近區，與既有
  `EMPIRICAL_FILTER_REGIONS` 註解描述 `emp_smoothing_upper` 為「eye and
  nose-bridge area」一致），**非評分 bug 重現**（已用中心先驗補測排除大小
  混淆假說），如實記錄為未解決的網格解析度限制，非宣稱已解決。
- **Claim**：①filter-class evidence map 的定位能力經獨立中心先驗對照確認
  為真（非中心先驗偽影），CI 排除 0；②大小混淆評分 bug 已修正並驗證；
  ③fail-safe／schema／非回歸／延遲全部維持過關。
- **Non-claim**：①**不可**宣稱 face_reshaping 的區域輸出為有效證據——與中心
  先驗統計打平；②**不可**宣稱 nose 主導的殘留現象已解決——為已知限制，留待
  提高網格解析度或依型別分別校準門檻的未來輪次；③**不可**引用首版的
  「IoU@10% 0.449 vs 0.401」數字背書 filter 區域——該數字屬 fake-class／
  SBI 母體，已在本輪修正。
- **方法論教訓（值得記錄，非本輪特有）**：region sanity cross-tab 這類
  「非回歸/schema 都過但描述性檢查透露異常」的訊號，**應該在 PASS 判定前
  被視為阻擋條件而非事後補充**——本輪首版即示範了只看硬性 gate（非回歸/
  schema/fail-safe）會放過一個統計上等同已知失效模式的設計缺陷。
- **產出物**：`results/research/p2_evidence_wire_20260831/`
  （`PRE_DECLARED.md`、`FINDINGS.md`（含完整時間軸）、
  `verify_filter_localization_vs_center.py`、`filter_vs_center_result.json`、
  `eval_wire.py`、`eval_wire_result.json`（修正後狀態）、
  `pipeline_pre_wire_20260831.py.bak`）；change proposal
  `docs/team/change_proposals/20260831_p2_evidence_head_wire.md`（同日已更新
  引用與限制段落）。`pipeline.py` 修正範圍：`evidence_regions_for_filter`
  改寫為質量相對評分、新增 `_CENTER_CELL_MASS`、`_evidence_sentence` 引用與
  措辭修正。Rollback＝還原 `.bak`。

---

## P1-PHYSCONSIST1: corneal specular-highlight consistency (mechanism #5) — `p1_physical_consistency_20260831`, **REJECT（診斷修正一個真 bug 後仍確認反向）**

- **問題**：`p1_prototype_20260828`（NO-GO）與 `p1_identity_probe_20260828`
  （REJECT）歸納出的收斂條件——新機制須「對紋理正交＋在 EFS 上確實存在」。
  候選：角膜鏡面反光一致性（真實照片兩眼反射同一光源，位置應幾何一致；
  生成模型無顯式全域光照模型，可能兩眼各自獨立渲染）。訊號落在鞏膜/角膜非
  皮膚，理論上對美顏磨皮正交；且是整張渲染臉的屬性，不需要 swap 的來源/
  目標身份分裂，理論上在 EFS 上仍存在——與身份一致性失敗的原因互補。
- **Novelty 查證（量測前先做，避免結果偏頗框架）**：基礎機制**已被解決三次**
  （Johnson & Farid 古典鑑識法 → Hu, Li, Lyu, ICASSP 2021, arXiv:2009.11924，
  零訓練啟發式，逐字 AUC **0.94**（FFHQ-real vs StyleGAN2）→ CHIEFS 訓練版
  **99.00%**），**不可宣稱基礎機制原創**。**未解決**：①擴散模型時代 EFS 驗證
  （唯一提及擴散目標的 SRI-Net, ICLR 2026, OpenReview `KwXkLYmZvR`，全新、
  結構不同（訓練式 cross-attention）、量化結果未查證，PDF 遭機器人牆擋下）；
  文獻明確警告「diffusion models can effectively interpret geometric patterns
  and generate realistic shading estimations, thereby diminishing the
  reliability of such illumination-based detection approaches」——**假設可能
  已不成立，須實測非假設**；②無邊緣部署蒸餾版本；③無與本專案 3-class
  filter/fake 語義結合的先例。本輪定位為**證偽優先探針**，非宣稱新機制。
- **解析度混淆事前處理**：real 池（LFW 250px／CelebA 178px）與 diffusion fake
  池（sd2.1 512px／pixart 1024px）原生解析度不對稱，直接比較會把「來源解析度」
  跟「真假」混淆。查證後找到**零重採樣的原生同解析度配對**：
  `AIGuard/real`(256) vs `DiT/SiT/ddim`(256)、`ffhq_originals`(1024，2210張)
  vs `pixart`(1024)；唯一需重採樣的一組（sd2.1 512）用 real 側**降採樣**
  （降採樣不會無中生有出細節，方向保守，不同於升採樣）。
- **Gate 0（GAN 年代哨兵檢查，複現文獻宣稱效果）事前宣告門檻 AUC≥0.70，
  失敗即停止全輪**：
  - **首次執行**（委派 agent，逐字照 PRE_DECLARED 執行）：AUC **0.4267**
    [0.3653, 0.4894]——**低於隨機，方向與文獻相反**（StyleGAN2 中位數
    一致性 0.818 高於真實 0.683，理論上真實應該更一致）。**Skip rate 50%
    real／35% StyleGAN2**，全部為 `no_discernible_highlight`。
  - **⚠️ 使用者對可疑數據的一貫要求觸發人工複查（未直接接受首輪結果）**：
    反向+高 skip rate 的組合與本專案已抓過的量測 artifact 同構
    （`P2-EVIDENCEWIRE1` 同週的 region-scoring bug）。人工檢視三張被跳過的圖，
    發現視窗大小 `6×虹膜半徑`（在這批池的 ~6-7px 虹膜半徑下 ≈36-42px，
    約虹膜**直徑的 3 倍**）會把眼皮、眼白、周圍皮膚全部框入，稀釋角膜訊號。
    同三張圖在視窗倍率 1.5×/2.0×/3.0× 下，原本 1.15-1.20（差一點沒過 1.3
    門檻）的比值全部躍升到 1.5-3.9——**機制性確認視窗過大是 skip rate 異常
    的真因**。
  - **修正後重跑 Gate 0**（視窗改 2.0×，同池同 seed 20260831，其餘程式碼逐字
    重用）：**skip rate 50%→3%（real）、35%→0%（StyleGAN2），確認修復生效**；
    但**AUC 仍為 0.4484 [0.4021, 0.4959]——反向未被修正解釋，CI 上界貼近
    0.5、仍完全排除 0.70 門檻**。次要指標 IoU 同方向（StyleGAN2 均值 0.1253 >
    real 均值 0.1089，方向相同但差異未達顯著 p=0.40）——**兩個獨立指標同向
    佐證，非單一脆弱指標的偽影**。
- **判定**：**REJECT，且是經過真實 bug 修正驗證後的 REJECT，比原始數字更
  可信**——診斷排除了一個混淆變數（視窗大小），核心發現（方向反轉）在修正後
  存活。可能原因（未進一步測試，僅列為假說）：①實作落差（Hu et al. 用
  DLib+Canny+Hough 在 1024px FFHQ 影像上直接定位角膜輪廓，本輪用 MediaPipe
  虹膜 landmark＋連續 cosine，256px 原生解析度下更粗糙）；②母體不對等
  （`stylegan2_test/fake` 與 `AIGuard/real` 非同一底圖管線的配對集，不像
  FFHQ/thispersondoesnotexist 那樣是同源訓練；生成器可能傾向產出更對稱、
  打光更均勻的「上鏡」臉，反而比自然照片的頭部姿態/光照不對稱更「一致」，
  這個反向效應與物理光源一致性假說無關）。
- **為何本輪在此收尾，不繼續追根因**：已完成兩項成比例的查核（找出並修正一個
  真實 bug、用第二個獨立指標交叉驗證），兩項都支持穩固的 REJECT。繼續追
  （換 real 池、重建 Hu et al. 原始 DLib+Hough 管線、換原生 1024px 測試）
  對一個本應「便宜篩掉候選」的哨兵檢查而言是不成比例的投入，且該機制在
  擴散模型上的有效性本來就已被文獻點名存疑——不值得為了救一個連 GAN 年代
  哨兵都過不了的實作繼續加碼。
- **Claim**：①角膜鏡面反光一致性（本實作）在 `AIGuard/real` vs
  `stylegan2_test/fake` 上無法複現文獻方向，經 bug 修正後依然如此；
  ②視窗大小混淆是真實、已修正、已驗證的實作問題（skip rate 50%/35%→3%/0%）。
- **Non-claim**：**不可**宣稱角膜鏡面反光一致性此機制本身無效或 Hu et al.
  方法有誤——只能宣稱本專案這個實作、在這兩個池上、修正已知 bug 後仍無法
  複現同方向效果；不同實作（原生 DLib+Hough、FFHQ 原生解析度、真正同源
  real/GAN 配對集）未經測試，不予置評。**不可**宣稱任何關於 diffusion-era
  EFS、濾鏡存活前提、解析度混淆診斷——四格皆未執行（Gate 0 兩次觸發停止
  規則）。
- **機制搜尋收斂條件更新**：三次機制級否決，三種不同失敗方式——prototype
  重組同一批證據（仍在前緣上）、身份一致性正交但在 EFS 母體不存在、
  鏡面反光在本專案實作/母體組合下方向反轉（未能確認是否對紋理正交/在 EFS
  存在，因未過己方的 GAN 年代哨兵）。下一候選除了「對紋理正交＋在 EFS 存在」
  外，應優先考慮**能在高解析度原生影像上驗證**的訊號，避免重蹈本輪
  256px-下解析度不足的覆轍。
- **產出物**：`results/research/p1_physical_consistency_20260831/`
  （`PRE_DECLARED.md`、`FINDINGS.md`（含完整兩階段時間軸）、`iris_geometry.py`
  （幾何虹膜萃取，10/10 smoke test 通過）、`measure_consistency.py`（首輪
  執行）、`scores.tsv`／`results.json`／`run_log.txt`（首輪產出）、
  `rerun_gate0_fixed_window.py`／`scores_gate0_fixedwindow.tsv`／
  `gate0_fixed_window_result.json`（診斷修正輪產出））。未訓練、未動
  `pipeline.py`／checkpoint／split，無 git 操作。

---

## P1-LIGHTDIR1: bilateral illumination-direction consistency (mechanism #6) — `p1_lightdir_consistency_20260831`, **REJECT（構念效度成立，主測試未過，已交叉驗證非計算 bug）**

- **問題**：延續 `p1_physical_consistency_20260831`（角膜鏡面反光，REJECT）
  歸納的第三個條件——候選須「對紋理正交＋在 EFS 上存在＋不需要 sub-10px
  原生解析度即可驗證」（角膜反光敗因之一是 256px 下虹膜半徑僅 ~6-7px）。
  候選：真實照片僅一個主光源，額頭/眼睛/雙頰/鼻樑/嘴巴/下巴各區域的明暗
  不對稱方向理論上應互相一致；生成模型若無顯式全域光照模型，各區域可能
  獨立渲染出不一致方向。訊號為**區域平均低頻亮度**（非高頻微紋理），理論
  對美顏低通濾鏡正交，且是整張渲染臉的屬性（不需要 swap 的身份分裂）。
- **Novelty**：沿用角膜反光輪次已做的文獻查證（避免重複查證成本）——最接近
  的文獻僅泛稱「部分偽造方法因光照模型限制在鼻部產生陰影或反光消失等瑕疵」，
  最接近的具體方法（Wu et al., ICAIS 2022）用色彩恆常性差異餵**訓練式**分類器，
  非本輪這種離散、訓練免費、多區域符號一致性檢查。**此離散操作化本身查無
  已發表先例**，定位為證偽優先探針。
- **Gate 0（構念效度，非文獻複現——此操作化無可比對照數字）事前設計含
  自我發現並修正的 bug**：首版用乘法增益（0.85-1.15×）擾動一側臉，結果
  **coherent 與 incoherent 兩條件的中位數位移皆剛好 0.0000**——診斷為擾動
  強度不足（真實區域差異本來就有數十 LAB-L 單位量級，小增益很難翻轉符號），
  屬於量測設計本身測不出效果，非機制無效。改用**左右內容直接互換**：
  coherent（六區域同步互換，理論上多數符號模式完全鏡射、分數數學上必然
  不變）中位數位移 **0.0000（與理論精確吻合）**；incoherent（每區域獨立
  50% 機率互換）中位數位移 **0.1667，Wilcoxon p=2.50e-10**。**Gate 0 PASS**
  ——量測確實對「刻意製造的不一致」有反應，且對「全域同步翻轉」保持不變，
  是真正的構念效度而非對任何像素擾動都有反應。
- **主測試（4,600 張影像，224px 標準作業解析度，本輪設計刻意不需原生解析度
  對齊，事前宣告的差異化設計）**：全部逐張以第二人（非執行 agent）手動用
  Mann-Whitney U 重算 `ffhq_vs_pixart` 一格，結果 **0.483858 與回報數字
  0.48385799999999995 精確吻合**——排除計算/標籤 bug。
  | Cell | n | AUC | 95% CI | 判定 |
  |---|---|---|---|---|
  | AIGuard/real vs {DiT,SiT,ddim} pooled | 300/900 | 0.4925 | [0.4571,0.5287] | REJECT |
  | — DiT／SiT／ddim 個別 | 300/300 each | 0.4867／0.4859／0.5051 | — | 三個皆 REJECT |
  | ffhq_originals vs pixart | 500/500 | 0.4839 | [0.4495,0.5178] | REJECT |
  | ffhq_originals vs sd2.1 | 500/500 | 0.5597 | [0.5252,0.5947] | **INCONCLUSIVE**（未達 0.60 門檻，CI 下界貼近 0.55）|
  | StyleGAN2 vs AIGuard/real（觀察格，非門檻）| 300/300 | 0.4610 | [0.4187,0.5038] | REJECT |
  **分項回報非池化掩蓋**：DiT/SiT/ddim 個別皆敗，非池化平均掩蓋單一強方法。
  **方向**：3/4 門檻格點估計低於 0.50（EFS/GAN 比真實更「一致」，方向與
  假說相反），但**與角膜反光輪次不同，這次不是可疑的顯著反轉**——手動
  Mann-Whitney 對 `ffhq_vs_pixart` 得 p=0.3475（不顯著），且多數 CI 跨過
  0.50（角膜輪次的 CI 是完全落在 0.50 以下），屬「無鑑別力」而非「confidently
  backwards」，性質不同、可信度較高，不需要像角膜輪次一樣進一步人工診斷。
- **前提檢查（濾鏡是否摧毀訊號）——PASS 8/8，但經交叉驗證證實非 bug**：
  事前宣告 n=150（與 Gate 0 不重疊），**實際 n=50**——`truetest_real.txt`
  僅 250 行，Gate 0 已用掉排列索引 [0:200]，[200:350] 只剩 50 張，執行
  agent 誠實回報此落差，非靜默縮減。**全部 8 種條件中位數絕對位移皆為
  0.0000**——外觀酷似 Gate 0 首版的「量不到效果」bug，**額外查核逐張（非
  僅中位數）差異排除此疑慮**：`smoothing_heavy` 實際改變 50 張中 4 張
  （最大位移 0.167）、`combined_heavy` 改變 2 張、`whitening_medium`
  改變 0 張——濾鏡確實有作用，只是這個離散符號投票量測對多數圖片的粗粒度
  不敏感，中位數（穩健統計量）因此為 0，非計算未執行。**PASS 且經證實
  為真**，但因主測試已 REJECT 而失去實用意義。
- **判定**：**REJECT**。Gate 0 構念效度乾淨通過、主測試計算與方向皆經
  獨立核對非 bug，是繼角膜反光後**第二個乾淨通過解析度/構念效度關卡卻仍
  在主測試失敗**的候選——確立「對紋理正交＋解析度穩健」是必要非充分條件，
  訊號終究要在真假之間真的有差異。
- **Claim**：①本操作化（6 區域 LAB-L 均值、多數符號投票、訓練免費）在
  DF40 三種擴散方法（分開報告）與 pixart 上皆無鑑別力；②sd2.1 一格結果
  不明確，CI 跨越門檻邊界，未進一步追測（不成比例，不符本輪停止規則）；
  ③前提檢查在 n=50 上成立且經證實非計算 bug。
- **Non-claim**：**不可**宣稱光照不一致性此類線索普遍不可偵測——僅本操作
  化、本池、構念效度已確立的前提下無鑑別力；**不可**宣稱 sd2.1 一格已有
  定論；**不可**把 n=50 的前提檢查結果推廣為更大樣本的保證。
- **機制搜尋戰績更新**：四次否決、四種不同死法——prototype 重組舊證據仍在
  前緣；身份一致性正交但 EFS 母體不存在；角膜反光方向反轉（bug 修正後
  確認，非量測缺陷）；光照方向一致性構念效度乾淨通過但主測試無鑑別力
  （非計算/量測缺陷，人工複查排除）。「對紋理正交＋在 EFS 存在＋解析度
  穩健」三條件確認為必要非充分。
- **產出物**：`results/research/p1_lightdir_consistency_20260831/`
  （`PRE_DECLARED.md`、`FINDINGS.md`（含 Gate 0 自我發現 bug 的完整時間軸）、
  `measure_lightdir.py`（含修正後 swap-based 擾動函式）、`run_gate0.py`／
  `gate0_result.json`、`run_primary.py`／`scores_primary.tsv`(4,250列)／
  `results_primary.json`）。未訓練、未動 `pipeline.py`／checkpoint／split，
  無 git 操作。

---

## ARCH2-INT8SPLIT1: 選擇性量化 int8 匯出（圖切分＋靜態校準）— `arch2_int8_split_20260831`, **成功（B1+B2+B3 全過）——int8 從「不可用」變可用，零重訓**

- **前提更正（本輪起點）**：MASTER_PLAN 機制清單第 2 項「加 log-scale FFT 提升
  頻域貢獻」建立在錯誤前提上——`FFTBranch.forward` **從一開始就有**
  `torch.log(torch.abs(fft)+1e-8)`，三次消融就是帶著 log 量的，該訓練槓桿
  不存在。int8 失效的真正位置是 **log 之前的原始 magnitude 中間 activation**
  （7.6e9 動態範圍，`diagnose_int8_collapse2.py` 已查清），正解＝TODO 任務一
  記載但標「不急」未執行的**選擇性量化**。本輪改為零重訓工程輪執行該路徑。
- **方法**：圖切分——頻譜計算（`mobile_fft.py` 常數矩陣 DFT→magnitude→log）
  留在 float32 前處理，模型改雙輸入（RGB＋預算好的 log-magnitude），權重自
  production checkpoint（v817sbi＋v811）逐位元組載入。G1-G4 匯出紀律照舊。
- **主輪結果（分層失敗診斷，本身有登錄價值）**：
  - **B1（fp32 切分等價）PASS**：切分版 vs 原版 fp32 TFLite **769/769 決策
    一致**，三類 recall 逐位小數吻合（72.40/99.63/91.97），G4 max|Δlogit|
    1.25e-05；mobile log-magnitude 值域 [-17.9, +5.2] 確認馴服。
  - **B2（dynamic-range int8）FAIL——但機制與原 blocker 不同**：FFT 分支
    **完全不再溢位**（原假設的修復被證明有效），塌陷點改為
    `spatial_branch/stage2.0` 的 depthwise/grouped conv（飽和至 float32 上限
    →±inf）。**關鍵對照**：同一 tensor 在現役出貨的非切分 dynamic-range
    artifact 裡**本來就非有限**——此不穩定性一直存在，只是被 FFT 塌陷遮蔽、
    從未被診斷到。`diagnose_int8_collapse2.py` 的「raw magnitude 是唯一
    blocker」假設被證偽為不完整（是其中一個，非唯一）。權重檢查排除寬動態
    範圍常數解釋（stage2.0 權重皆在 [-8,8]）。
  - **意外正面副作用**：切分 fp32 比出貨版**更小更快**（19.38MB vs 20.91MB、
    8.91ms vs 12.68ms desktop CPU）——DFT 矩陣移出圖外連 fp32 都受益。
- **Addendum（同日）——full-int8 靜態校準：VERDICT 反轉，全過**：裝
  `tf_keras==2.21.0`（經授權的環境變更）後用 `tf_converter` backend＋既建的
  200 張代表集（seed 20260831）轉換成功。**靜態校準下 stage2.0 完全不再
  飽和**（15 張全 tensor 掃描 0 個非有限值）——證實該不穩定為 dynamic-range
  特有（runtime per-tensor activation scale 對 depthwise conv 退化）。
  | Artifact | NaN | 決策一致率 vs split-fp32 | real/fake/filter recall | 大小 |
  |---|---|---|---|---|
  | full_int8 (float I/O) | 0/769 | **95.19%** | 72.00/98.52/90.76 | 5.41MB |
  | full_int8 (int8 I/O) | 0/769 | **95.71%** | 72.80/99.26/91.57 | 5.41MB |
  三類 delta 全在事前宣告的 3pp 帶內、95% 一致率門檻雙雙通過；體積比出貨
  fp32 **小 3.9 倍**；desktop int8 反而比 fp32 快（4.38-4.82ms，XNNPACK
  int8 路徑）——**依事前宣告強制警語：desktop int8 延遲不代表行動裝置，
  不作部署延遲主張**。數字經母 session 對 addendum JSON 逐項抽查核實。
- **Claim**：①int8 部署經證明可行（靜態校準＋切分圖、零重訓、同一組
  production 權重、95%+ 一致、每類 3pp 內、5.41MB）；②「raw FFT magnitude
  是唯一 int8 blocker」被證偽——它是已修復的其中之一，stage2.0 depthwise
  是第二個（dynamic-range 特有、靜態校準免疫）；③切分 fp32 自身更小更快。
- **Non-claim**：不改變 FFT 分支偵測價值結論（三次消融不動）；**不接線任何
  release**——升級部署產物是獨立的 change-control 決定，本輪未做；desktop
  int8 延遲非行動代表值；artifact classifier（第三模型）在範圍外（符合
  ≤25MB gate 兩模型裁定範圍）。
- **文件影響**：TODO.md 任務一與 mobile benchmark 表的「int8 不可用」需更新
  為「int8 可用（靜態校準＋選擇性量化切分圖）」＋分層失敗機制註記；
  論文 Phase 3 部署故事升級（20.91MB fp32 → 5.41MB int8 選項）。
- **產出物**：`results/research/arch2_int8_split_20260831/`（PRE_DECLARED、
  FINDINGS＋ADDENDUM、`split_model.py`、`export_split.py`、
  `run_evaluation.py`／`run_evaluation_fullint8.py`、兩支診斷腳本＋報告、
  `results_int8_split.json`／`results_int8_split_fullint8_addendum.json`、
  ONNX×2、TFLite 產物資料夾×4、代表集 npy×2）。環境變更：base env 新增
  `tf_keras==2.21.0`（provenance 記錄於 addendum JSON）。無訓練、無 git、
  未動 pipeline.py/checkpoint/split。

---

## RECIPEGAP-SEED2: RECIPEGAP 血緣候選第二 seed — `recipegap_seed2_20260831`, **REPRODUCED（雙軌全過，change proposal 已備妥，promote/hold 保留給使用者）**

- **問題**：`ARCH1-LINEAGE-20260826` 收線時把 RECIPEGAP1（production 同架構、
  血緣暖啟動、零 hard-neg、ARCH-1 通用 recipe）標為九輪以來 Alibaba+stress+
  FF++ 組合最佳配置；`P1A3-SEED2-20260828` 證明其跨域增益來自 recipe 本身。
  升格前置條件＝第二 seed。本輪：`train_arch1_recipe_gap_warmstart.py`
  **未修改**、tag RECIPEGAP2、seed 20260831（seed-1＝20260826），**seed 為
  唯一變因**（loader 列數 236,673/126,130 與 seed-1 逐位元組相同，含同一個
  已揭露的 20,295 列缺檔缺口；暖啟動載入 363/361 tensors 相同）。評測＝
  `eval_proto_gates.py`/`eval_proto_crossdomain.py` 僅改 ROUND_OUT 的複本。
- **Track 1（六項絕對門檻）**：seed-2 全過——TT filter 92.77／TT fake 99.63／
  Alibaba 98.34／CelebA 98.27／unseen AUROC 0.8270／StyleGAN2 99.47。
  **兩 seed 皆 6/6**。
- **Track 2（事前宣告重現帶）4/4 全中，每項至少比帶寬小 6 倍**：
  | 指標 | s1 | s2 | Δ | 帶 |
  |---|---|---|---|---|
  | unseen AUROC | 0.8242 | 0.8270 | +0.0027 | ±0.02 |
  | Shadow real | 83.51 | 83.15 | −0.36pp | ±4pp |
  | FF++ frame AUROC | 0.6407 | 0.6376 | −0.0030 | ±0.02 |
  | fake_filter_stress | 4.33% | 4.28% | −0.04pp | ±1.0pp |
- **輔助觀察**：TT real recall 65.46→69.48（+4.0pp，落在既知 n=249 雜訊帶
  內，依規不作排序依據）；Shadow filter 15.77→18.28；stressdev 2.76→3.57；
  FF++ 操作點擺動（fake-catch +6.1pp／real −4.6pp，AUROC 幾乎不動）。
- **判定**：依 PRE_DECLARED verdict rule——**候選取得 change proposal 資格**，
  草案已寫（`docs/team/change_proposals/20260831_recipegap_lineage_candidate.md`），
  **promote/hold/第三選項（不換裝、寫入論文）三選一保留給使用者**（更換
  production 模型為本 session 代行授權明確排除的決定類）。
- **Claim**：RECIPEGAP 血緣候選的 headline trade-off（stress 2.80→~4.3% 換
  FF++ +6.5pp／Shadow real +6.4pp／Alibaba +0.6pp）為兩 seed 可重現的真實
  現象，非單 seed 僥倖。
- **Non-claim**：不宣稱應該換裝（該裁定未做）；TT real recall 的 +4pp 差異
  不可引用為 seed 效應（雜訊帶內）；CDF-v2/DFD 跨域格為補充證據，非任何
  事前宣告判準（addendum 待補）。
- **產出物**：`results/research/recipegap_seed2_20260831/`（PRE_DECLARED、
  FINDINGS、gates_RECIPEGAP2.json、perimage、訓練/評測 log、僅改 ROUND_OUT
  的兩支 harness 複本）；checkpoint 於
  `checkpoints/research/arch1_recipe_gap_20260826/arch1_sep_RECIPEGAP2_*.pth`
  （腳本硬編碼輸出根目錄，tag 區分、無覆蓋，PRE_DECLARED 已揭露）。
  未動 production、無 git。


---

## FILTER2-REALFILTER-20260831: 用真實商用美顏濾鏡訓練 Layer2（P1-B1 第六個機制）— `filter2_realfilter_train_20260831`, **REJECT（但為 P1-B1 證據鏈最強一筆）**

- **問題**：論文中心主張為「把 filter 提升為顯式第三類即可處理美顏」，但
  `EXTSAFETY-20260828` 自己量到——真實商用濾鏡上 B-LFW（8 個真 Instagram
  濾鏡、12,000 張）僅 **0.45%** 被判 filter、**94.4% 判 fake**；FairBeauty
  12.9%。即 filter 類**只認得自家 OpenCV 濾鏡**。P1-B1 前五個機制（底圖多樣性／
  增強／class weight／參數隨機化／多廠牌演算法家族）**全部仍使用演算法生成的
  濾鏡**，從未用真實商用 app 濾鏡訓練——本輪即該未試槓桿。
- **設計（跨語料＋跨濾鏡家族，單變數）**：訓練加入 **FairBeauty**（FairFace
  底圖，本專案從未使用之語料，零污染）8,828 張為 filter 類；測試 **B-LFW**
  全 12,000 張完全 held out。只改 Layer2（warm-start `v811`），Layer1 與
  artifact classifier 不動，production Layer2 recipe 逐字沿用，seed 20260831。
- **主要結果：REJECT**——B-LFW filter recall **0.45% → 1.41%**
  （169/12,000，Wilson CI [1.21, 1.64]），事前門檻 BUILD≥50%／PARTIAL 10-50%／
  REJECT<10%，**低於 PARTIAL 下限七倍**；93.4% 仍判 fake。
  **per-filter 分解（自語料自帶 `filters.npy` 取得，B-LFW 檔名不編碼資訊）：
  8 個濾鏡無一超過 2.6%（0.53-2.60%）——失敗均勻，無隱藏的部分訊號**。
- **訓練本身確實成功（使負面結果可解讀，非擬合失敗）**：held-out、
  identity-disjoint 的 FairBeauty val（978 張）filter recall
  **12.92% → 70.65%**（691/978，CI [67.72, 73.42]）；限縮於 Layer1 判為
  manipulated 者（Layer2 唯一會看到的），**92.01%** 被判 filter（691/751）。
- **結果的「形狀」即為發現**：FairBeauty（訓練過）12.9→70.7%【學會】；
  Alibaba（演算法生成、不同廠商）97.7→97.7%【本來就解決、不變】；
  **B-LFW（真實、不同家族、held out）0.45→1.41%【未轉移】**。
  ⇒ **Layer2 學的不是「美顏」這個概念，而是訓練集裡各濾鏡家族的特定渲染簽章，
  一次一個家族，幾乎零外溢。**
- **五項硬閘全過**（同 harness 同 Layer1 對照 `p1_r14_layer2_corpus_shortcut_20260821/gates_PROD_v817.json`）：
  True Test filter 91.97（持平）／fake 99.63（持平）／Alibaba 97.70→97.73／
  **`fake_filter_stress` 2.84→2.88（+0.04pp，等同不動）**／CelebA 99.33（持平）。
  **該 stress 閘門正是為了抓「真實濾鏡訓練後 Layer2 開始把加濾鏡的假圖也叫
  filter」的安全性退步而設——結果顯示加入 8,828 列真實濾鏡資料，filter 類
  完全沒有從 fake 類手上拿到任何領土**。另報：Shadow filter recall
  12.19→15.77（+3.58pp，FairBeauty 之外唯一非瑣碎變動）、True Test real
  72.69→72.29、AIGuard/unseen AUROC 0.8410→0.8394，其餘持平。
- **Claim**：①用真實商用濾鏡訓練可在**同家族**上學會（70.65% val），但
  **跨家族轉移僅約 1pp**；②P1-B1 的 limitation 性質由「我們的合成濾鏡不夠真實」
  （我方缺陷、可修）改寫為「**跨家族美顏泛化是開放問題**」（任務本身的性質）
  ——這是前五個機制無法做出的宣稱，因為 reviewer 永遠可回「你沒試過真濾鏡」；
  ③**語料庫捷徑 meta-finding 第四個獨立實例**，且為最乾淨的一個：捷徑在被餵入
  真正寫實的資料後**依然**選擇走捷徑。
- **Non-claim**：**不可**宣稱這證明美顏偵測不可能——僅證明本架構＋本訓練方式下
  跨家族不轉移；**不可**宣稱未見身份泛化（B-LFW 底圖為 LFW，屬「已見底圖語料、
  未見濾鏡演算法」框架，污染稽核 0 exact／2.7% dHash 近重複——**此框架使結論
  更強而非更弱：模型見過這些臉，仍分不出是被美化還是被偽造**）；
  **無 production 變更、REJECT 故不提促升**。
- **登錄義務**：**FairBeauty 自本輪起成為訓練語料，喪失乾淨零樣本 filter
  benchmark 資格**，後續任何輪次不得再引用其零樣本數字為未觸碰；
  **B-LFW 維持乾淨**，成為主要外部 filter benchmark。
- **事前假設更正（誠實記載）**：PRE_DECLARED 假設 FairBeauty 資料夾為身份資料夾，
  實為**濾鏡風格資料夾**（11 種風格）；base-id 範圍跨資料夾互斥，故改以 baseid
  前綴為身份單位（較資料夾更細），90/10 依 baseid 切分並按風格分層，
  **0 個 baseid 跨切分**（程式化斷言）。
- **產出物**：`results/research/filter2_realfilter_train_20260831/`（PRE_DECLARED、
  FINDINGS、prepare_data.py/data_prep.json、兩個 split、trainer＋log、
  eval 腳本、blfw/fairbeauty 結果 JSON＋逐圖 TSV、gates_realfilter.json、
  gate_comparison.json）；checkpoint
  `checkpoints/research/filter2_realfilter_train_20260831/shufflenet_v2_layer2_realfilter_20260831.pth`
  （sha256 `69d64739...`）。未動 `pipeline.py`／production checkpoint／既有 split，無 git。


---

## P1-MULTISCALE1: 多尺度回應簽章（機制 #7）— `p1_multiscale_signature_20260831`, **REJECT——混淆（解析度來源，非頻率結構）**

- **假說**：美顏是高頻編輯、偽造是結構性編輯，故同一張圖跨解析度的模型回應
  **軌跡**應可區分兩者，且**依定義與濾鏡家族無關**——直接對症
  `FILTER2-REALFILTER-20260831` 查出的「Layer2 只學家族簽章」。零訓練、
  用模型當自己的探針、不增加部署體積。
- **未配對主要結果看似有戲**：`slope_filter_given_manip` AUROC **0.6998**
  [0.6764, 0.7232]，通過 Bonferroni。**但這是偽影。**
- **四項獨立檢查一致否決**：①**單用原生解析度 AUROC = 1.0000**（B-LFW 全為
  112px、pooled-forgery 最低 128px，**零重疊**，完美分離為算術必然）；
  ②**解析度配對後崩到 0.5626**（B-LFW vs FF++ 90-200px，n=487），低於事前
  REJECT 底線，而同帶內原生解析度仍有 0.95；③**事前宣告的泛化檢查自身即
  失敗**（True Test filter vs fake，解析度僅差 6px 的最乾淨對照，0.6477 < 0.70
  門檻，依規則單此即 REJECT）；④**控制組失敗**——真實影像落在美顏側
  （CelebA 0.098 高於兩個真實濾鏡語料的 0.022／0.018）。
- **決定性證據——AUROC 追蹤的是解析度差距而非類別**：B-LFW vs FF++
  （解析度重疊）僅 **0.5165（隨機）**；而 **Alibaba 這個「美顏」語料 vs 偽造
  語料高達 0.88-0.91**，純粹因為它 1024px 的原生解析度離偽造語料更遠。
  該特徵對「美顏」毫無概念，讀的是語料來源。
- **⚠️ 流程重點（列為常設檢查）**：此混淆**不在原 PRE_DECLARED 中**，
  是執行 agent 的設定期 smoke test 揭露 B-LFW 原生僅 112px（其 scale=224 與
  scale=112 數學上相同）後，由協調者**在看到任何主要數字之前**追加事前宣告
  （解析度單獨 AUROC、解析度配對重算、明訂「REJECT——混淆」判定規則）。
  **若無此修訂，本輪會回報 PARTIAL 且 Bonferroni 顯著的 0.6998**，並據此在
  一個解析度偽影上開發新頭。這是本專案一週內第二次抓到解析度混淆
  （前次 `p1_physical_consistency_20260831`），**即日起列為所有跨語料比較的
  常設檢查**。
- **次要發現（誠實記載）**：事前假設「scale=224 應重現 production 分數到
  <1e-5」**失敗**（實測 max|Δp| 0.0120-0.4225）——因規格路徑為「bicubic 縮到
  224 → JPEG」而 production 為「原生解析度 JPEG → transform_infer 內部
  bilinear 縮放」，濾波器與順序皆不同；該假設隱含要求原生解析度已是 224，
  本輪無任何語料滿足。軌跡特徵內部一致性不受影響，但**本輪的「scale=224」
  不等於 production 推論，不得如此引用**。
- **Claim**：本 5 特徵多尺度探針在這些語料上未能證明頻率尺度訊號存在；
  且天真版分析對解析度混淆極度脆弱。
- **Non-claim**：**不可**宣稱不存在任何頻率尺度訊號；無訓練、無 production 變更。
- **產出物**：`results/research/p1_multiscale_signature_20260831/`
  （PRE_DECLARED、FINDINGS、4 支腳本、`scores_multiscale.tsv` 35,280 列、
  `native_resolution.tsv`、`features.tsv`、`analysis.json`、
  `resolution_confound_analysis.json`、`identity_check.json`）。


---

## ARCH2-SRM-LOFO: SRM 殘差留一家族外測（未受控→受控兩輪）— `arch2_srm_vs_clip_20260831` + `filter3_controlled_family_20260901`, **先 REJECT（混淆）後 POSITIVE——評測修正後 SRM 確認跨家族可轉移**

- **背景**：文獻稽核（本 session）發現 arXiv:2512.08397 用 SRM（Steganalysis
  Rich Model）殘差在六個真實商用修圖 app 的留一濾鏡外測上拿 **2.17% D-EER**
  （Mobile-ViTv3，邊緣原生）；SRM 不在本專案已否決的七機制內（我們測的是全域
  FFT 頻譜，SRM 是局部高通殘差組），且**本來就是 MASTER_PLAN ARCH-2 條目、
  從未執行**。另 arXiv:2605.24965 已發表證明凍結基礎模型 linear probe 在
  **局部臉部編輯**上 0.4363/0.3191（≤隨機）——CLIP 診斷臂據此裁定不跑
  （文獻已答，記錄為刻意 scope cut）。
- **第一輪（未受控，`arch2_srm_vs_clip_20260831`）：REJECT——但為混淆所致**：
  五家族（ours 250-256px／alibaba 1024／megvii 1024／fairbeauty 152-512／
  blfw 112）LOFO，T2 平均 AUC **0.4238**（blfw 格 **0.0098**＝完美反向），
  但強制解析度控制顯示**單用原生解析度平均 0.7907、五折贏四折**——各「家族」
  的原生解析度近乎類別式分離，**評測量到的是來源不是演算法**。本週第三次
  解析度混淆。連帶效應：`FILTER2-REALFILTER-20260831` 的 0.45%→1.41% 跨家族
  轉移失敗中「濾鏡家族」與「底圖/解析度來源」的貢獻無法分離，該輪結論需加註。
- **第二輪（受控，`filter3_controlled_family_20260901`）：POSITIVE**：
  發現 `ffhq_originals` 2,210 張與 Alibaba 修圖版**完美同索引配對**，三家族
  （ours=自建 OpenCV 濾鏡當輪生成於同批 FFHQ 底圖／alibaba／megvii）全部
  FFHQ 底圖、全部 1024×1024，負類=同批 FFHQ 原圖。**解析度控制精確 0.5000**
  （混淆按構造消除）下：
  | holdout | LOFO AUC | in-domain ref |
  |---|---|---|
  | alibaba | 0.7511 | 0.7940 |
  | megvii | 0.8346 | 0.8836 |
  | ours | 0.8739 | 0.9844 |
  | **mean** | **0.8199** | **0.8873** |
  **概念學習比 = 0.8199/0.8873 = 92.4%**（對照先前六個量測的 −3%~+6.2%）。
- **Meta-finding 重新界定（重大）**：語料庫捷徑不是「此任務學不到概念」，而是
  「**可學習特徵空間在家族與來源共變時走捷徑；固定的鑑識特徵組（SRM）可以
  跨家族轉移概念**」——機制層級的陳述，取代原本的現象觀察，並使 ARCH-2
  （SRM 分支）成為有受控證據的架構變更而非直覺。
- **Claim**：①受控條件下 SRM 跨濾鏡家族轉移成立（T1，3 家族，控制=0.5000）；
  ②第一輪 REJECT 為評測混淆，非 SRM 無效；③本專案所有未受控跨家族數字
  （含 FILTER2 的 1.41%）測到的是「演算法＋來源」混合物。
- **Non-claim**：**T2（filter vs fake）未受控驗證**——偽造池異語料異解析度，
  現有資料無法控制，故本結果尚不能宣稱解決 Layer2 的 B-LFW 1.41%；線性探針
  為下界非系統效能；「ours」家族與第三方演算法不完全對等（濾鏡於 224 施加後
  上採樣，已揭露；受此影響最大的 holdout=ours 反而是最高折，故未膨脹第三方
  跨家族宣稱）。
- **產出物**：兩輪資料夾各含 PRE_DECLARED/FINDINGS/腳本/results JSON；
  `filter3_.../ours_ffhq/` 2,210 張受控家族影像。無訓練、無 production 變更、
  無 git。


---

## DATA-ACQ-20260901: 現代生成器資料＋雙 lockbox 重建 — **完成（Gap A 與 Gap B 同時補上）**

- **Gap A（2025 世代生成器，補「fake 資料過時」reviewer 攻擊面）**：
  OpenFake（HuggingFace `ComplexDataLab/OpenFake`，CC-BY-NC-4.0，免申請）test
  shard 5.1GB 於 Ubuntu 機下載處理——**非純臉語料**，經 Haar-cascade 臉部偵測
  過濾後得 **926 張含臉 2025 世代生成影像**（z-image-turbo 389／flux.2-klein-9b
  306／gpt-image-1.5 125／midjourney-7 76／recraft+ideogram 20），存
  `external_data/openfake_modern_gen/fake_faces/`（398MB）。real 側 1,500 抽樣
  僅 96 張含臉——**明確標記為不可用的配對 real 集**，未混充。原始 parquet 已刪。
- **Gap B（blind lockbox 重建，前一個 lockbox 因被讀取而降級後專案一直無盲測集）**：
  UTKFace in-the-wild（24,106 張、2.7GB、非商業研究授權、免申請）——本專案
  **從未使用過的語料**（對 CLAUDE.md 排除清單查核）。
- **污染篩查全零**：UTKFace 2,000 抽樣＋OpenFake 全 926 張＋兩個 lockbox 子集，
  SHA256 對 `AIGuard/real`、`AIGuard/fake`、`lfw/`、`celeba_train/`、DF40 五資料夾
  各 2,000 抽樣——**所有檢查 0 碰撞**。
- **建立的 lockbox（各 500 張、seed 20260901、規則寫入檔案頭、引用前一個
  lockbox 降級案例為前例）**：
  - `splits/LOCKBOX_utkface_real_20260901.txt`（real 側）
  - `splits/LOCKBOX_openfake_fake_20260901.txt`（fake 側，2025 世代生成器）
  **綁定規則**：任何評測/訓練腳本在正式指定的 final-evaluation 輪之前讀取
  影像清單即立刻降級。本條目的行數/檔頭查核為行政性質、未讀取影像清單本體。
- **未取得（誠實記錄於 `external_data/ACQUISITION_LOG_20260901.md`）**：
  10k US Adult Faces（表單門檻）、CFD（授權協議門檻）、UTKFace aligned 版
  （連結 404，改用 in-the-wild 版）、OpenFake real 側（含臉率過低）。
- **Non-claim**：OpenFake fake_faces 為 Haar 過濾的子集，非官方臉部基準；
  lockbox fake 側單一來源（OpenFake），族群多樣性有限——final-eval 引用時須註明。


---

## MOBILE-EXPORT-20260901: v8.17 全三模型 TFLite 重匯（fp32 切分＋full-int8）— `results/mobile_export/v817_int8_20260831/`, **全過，部署故事升級**

- **內容**：production v8.17 三模型（L1 v817sbi／L2 v811／artifact v6）以
  `ARCH2-INT8SPLIT1` 確立的圖切分＋靜態校準路徑重匯。六個 artifact 全部
  G1-G4 通過（int8 的 G4 依該輪確立的正確判準：無 NaN／不塌類／769 全量
  決策一致與 recall 帶，非逐 logit 精確吻合——中途修正過一次錯誤判準並保留
  兩版數字）。
- **769 張 True Test 端到端鏈驗證（TFLite L1→L2→Artifact vs PyTorch）**：
  - **fp32 切分**：label **769/769（100%）**、濾鏡子型別 **298/298（100%）**、
    recall 72.40/99.63/91.97 與已發布 gate 數字**逐位吻合**、artifact 型別
    準確率 90.36%——完美等價。
  - **full-int8**：label 732/769（**95.19%**，過 ≥95% 門檻）、三類 recall 全在
    3pp 帶內（72.00/98.52/90.76）、artifact 型別 88.76%；**獨立重現
    `ARCH2-INT8SPLIT1` addendum 數字，跨輪一致性通過**。
- **大小（部署 headline 更新）**：
  | 範圍 | fp32 切分 | full-int8 |
  |---|---|---|
  | 兩模型（gate 範圍）| 19.38 MB | **5.41 MB** |
  | **三模型完整系統** | **24.21 MB** | **6.87 MB** |
  三模型 fp32 從 25.75→**24.21 MB**（現在連完整系統都低於 25MB）；int8 完整
  系統 **6.87 MB**（縮 3.7 倍）。桌機延遲（明示非行動代表值）：fp32 兩模型
  8.00ms／int8 4.98ms（PyTorch eager 對照 68.41ms）。
- **Non-claim**：僅匯出與驗證，未接線任何 release（升級部署產物為獨立
  change-control 決定）；桌機 int8 延遲不得引為行動效能。
- **產出物**：`EXPORT_AND_VERIFY_REPORT.md`、六個 .tflite＋ONNX＋代表集、
  `verification_results.json`、`export_{l1l2,artifact}_report.json`、
  `fix_int8_g4.py`（判準修正紀錄）。


---

## ARCH2-SRM-BRANCH: SRM 殘差分支端到端訓練（Layer2）— `arch2_srm_branch_20260901`, **REJECT——捷徑在特徵層與端到端訓練之間重新出現**

- **設計**：把 Layer2 的 FFT 分支換成固定 SRM 殘差分支（`arch2_srm_vs_clip_20260831`
  的 3 個標準核，逐通道 depthwise conv → 9 通道殘差 → 與 FFTBranch 同形狀但首層
  加寬到 9 通道的全新卷積堆）。**與 `FILTER2-REALFILTER-20260831` 對照臂逐位元組
  相同**：同 split（`v811_layer2_train_plus_fairbeauty.txt`）、同 recipe、同 seed
  20260831，僅分支架構不同。暖啟動查核：340/364 tensor 由 checkpoint 載入、
  24 個全新（`srm_branch.*`）、23 個 checkpoint tensor 未用（全為 `fft_branch.*`，
  符合預期）。
- **主要結果：REJECT**——B-LFW filter recall production 0.45%→**0.9333%**
  （112/12,000，Wilson CI [0.776, 1.122]），事前門檻 BUILD≥15%／PARTIAL 5-15%／
  REJECT<5%，**低於 PARTIAL 下限**。且**低於 FFT 分支對照臂自己的 1.4083%**
  （相對 FFT 對照 −0.475pp，相對 production −0.483pp 進步但仍遠低於門檻）。
  per-filter 8 個濾鏡無一超過 1.53%（對照臂範圍 0.53-2.60%），失敗同樣均勻。
- **概念學習比再降**：
  | arm | 同域增益 (FairBeauty val) | 跨家族增益 (B-LFW) | 比值 |
  |---|---|---|---|
  | FILTER2 對照（FFT 分支）| +57.73pp | +0.96pp | 1.66% |
  | **SRM 候選（本輪）** | +57.02pp | +0.48pp | **0.85%** |
  兩種架構在 FairBeauty 同域皆幾乎完美擬合（macro F1 0.9986 vs 0.9992），
  跨家族轉移皆幾近於零——**SRM 分支轉移量約為 FFT 分支的一半**。
- **與 `ARCH2-SRM-LOFO` 受控實驗（AUC 0.82、概念比 92.4%）的落差即為本輪發現**：
  固定特徵在孤立的邏輯迴歸下乾淨可轉移，**接入聯合訓練、暖啟動、mixup 正則化
  的端到端分類器後不再存活**——最可能被暖啟動的空間分支的語料庫指紋容量
  淹沒/收編，此機制已在 Layer2(FFT)、artifact_classifier、棄權閘門三處獨立
  記載，本輪為**第五個獨立實例**（含 FILTER2 則為第六個）。
- **五項硬閘全過**（同 harness 同 Layer1 對照 production）：True Test filter
  91.9679（持平）／fake 99.6296（持平）／Alibaba 97.7022→97.7070／
  **stress 2.8397→2.8834（+0.0437pp，等同不動）**／CelebA 99.3333（持平）。
  另報：Shadow filter 12.19→15.05（+2.87pp，同方向但小於 FFT 對照的 +3.58pp）、
  AIGuard/unseen AUROC 0.8410→0.8414（持平）。
- **Claim**：①SRM 在孤立特徵層級可跨濾鏡家族轉移的結論（`ARCH2-SRM-LOFO`）
  **不因本輪被推翻**——本輪測的是不同問題（架構整合後的轉移）；②架構層級
  SRM 分支未能拯救 FFT 分支已知的低轉移，甚至更差；③捷徑重新進入的位置
  被定位在「固定特徵→聯合端到端訓練」這一步，而非「濾鏡家族本身不可轉移」
  這個更悲觀的宣稱。
- **Non-claim**：不可宣稱 SRM 特徵本身無效（`ARCH2-SRM-LOFO` 仍成立）；
  不可宣稱已窮盡 SRM 整合方式（僅測了一種分支替換法，未測凍結 SRM 分支
  只訓練後續層、或雙分支並聯等變體）；單一 seed；無 production 變更、無 git。
- **產出物**：`results/research/arch2_srm_branch_20260901/`（PRE_DECLARED、
  trainer＋log、`warmstart_tensors.json`、eval 腳本、`blfw_eval_srm.json`、
  `fairbeauty_val_eval_srm.json`、`gates_srm.json`、`gate_comparison_srm.json`）；
  checkpoint `checkpoints/research/arch2_srm_branch_20260901/
  shufflenet_v2_layer2_srm_20260901.pth`（sha256 `989f13bb...`）。


---

## BENCH-CFFB-20260901: Controlled Cross-Filter-Family Benchmark（CFFB v1）— `bench_controlled_family_20260901`, **建立完成，三項效度斷言全過**

- **定位**：這不是偵測結果，是**評測貢獻**。把 `arch2_srm_vs_clip_20260831`
  意外揭露的混淆（同一組固定特徵在未受控評測 0.4238／受控 0.8199，而未受控
  時**單用原生解析度就有 0.7907**）正式化為可釋出的受控 benchmark。
  據查無同類released benchmark：arXiv:2512.08397 的六 app 協定最接近
  （單一底圖語料故 provenance 固定）但未附解析度控制、未作為 benchmark 釋出。
- **組成（109,890 列逐張查核、非抽樣）**：全部 **1024×1024 原生，0 例外**。
  genuine=`ffhq_originals` 2,210／`ours`（自建 OpenCV 濾鏡施於同批底圖）2,210／
  `alibaba`=`FFHQ_ali_process` 71,996（3,000 base ids）／
  `megvii`=`FFHQ_megvii_four_process` 33,474（8,537 base ids）。
- **兩層設計（支撐不同強度的宣稱）**：
  - **Tier A（配對）**：genuine＋ours＋alibaba 於**完全相同的 2,210 個 base id**
    （配對稽核 2,210/2,210 精確），身份/姿態/光照/拍攝管線/解析度全部按構造固定；
    2 個濾鏡家族。
  - **Tier B（同語料）**：Tier A ＋ megvii（base id 與 genuine **互斥，重疊=0**），
    語料與解析度受控、底圖不同；3 家族，滿足留一家族外測最低需求。
- **三項效度斷言全過**：`all_rows_1024`=true（0 張非 1024²）、
  `tierA_pairing_exact`=true、`megvii_disjoint_from_genuine`=true。
- **強制使用協定**（寫入 `RESOLUTION_CONTROL.md`）：①**必須依 `base_id` 切分、
  不得隨機切**（Tier A 為配對設計，隨機切會洩漏身份）；②**必須跑解析度控制**
  （以原生解析度為唯一特徵重跑同一評測，CFFB 上必須 ≈0.5，實測參考 **0.5000**；
  任何擴充若破壞此值即為無效擴充）；③**必須逐家族報告、不得只報平均**
  （未受控前身的逐家族分佈為 0.0098–0.7509，平均會蓋掉反向）。
- **參考結果（Tier B，固定 SRM＋邏輯迴歸）**：LOFO 平均 **0.8199** vs 同域
  0.8873，解析度控制 0.5000。**並列記載反例**：同樣的 SRM 殘差接入暖啟動的
  聯合訓練 Layer2 後未繼承此轉移（`ARCH2-SRM-BRANCH` B-LFW 0.93%）——CFFB
  量的是受控下的特徵可分性，**不預測未受控 in-the-wild 的端到端行為**。
- **明列不控制的項目**：僅 2 個真第三方演算法家族；`ours` 為自建且經
  224→1024 上採樣（處理管線差異，已揭露，且受其影響最大的 fold 反而最高分，
  未膨脹第三方宣稱）；`ours` 濾鏡參數不變（跨**演算法**非跨**參數**）；
  FFHQ 單一底圖（無人口/拍攝多樣性宣稱）；僅 1024px（不涵蓋 B-LFW 112px
  的低解析度區間——CFFB 是受控科學條件，B-LFW/FairBeauty 是產品相關的
  in-the-wild 條件，**兩者互補、回答不同問題**）。
- **釋出形式**：CFFB 是 **manifest 非資料再散布**（不複製任何影像），
  使用者須依各來源授權自行取得；`ours` 家族由本專案腳本本地生成。
- **產出物**：`cffb_manifest.tsv`（109,890 列：family/path/base_id/native_w/
  native_h/tier）、`cffb_stats.json`、`BENCHMARK_CARD.md`、
  `RESOLUTION_CONTROL.md`、`build_cffb.py`、`PRE_DECLARED.md`。無訓練、
  無 production 變更、無 git。


---

## P2-XAI2-REGIONS: evidence 驅動的解釋文字排序 — `p2_xai2_evidence_regions_20260901`, **P2-A1 完成定義兩項全數關閉（但 item (b) 有誠實天花板）**

- **item (a)「region 集合縮減為 5 類」——查核後確認為前輪已完成，本輪未重做**：
  `pipeline.py` 的 `_EVIDENCE_BOX_TO_REGION`／`_build_evidence_cell_map()` 已把
  7×7 patch 網格逐格幾何映射到 eyes(4 格)／nose(6)／mouth(3)／skin(19)／
  face_contour(17)，係 `p2_evidence_wire_20260831` 所建。**agent 主動指出此項
  無須新工作**，未製造虛工。
- **item (b)「文字由 evidence head 驅動」——本輪實作**：原本 evidence 句是
  `tail`（正確計算、正確引用，但結構上是附加物）；改為
  `_evidence_sentence()` 拆成 `_evidence_region_clause()`（**開頭領述**）與
  `_evidence_validation_clause()`（IoU 引用＋per-type caveat，維持結尾），
  `build_filter_explanation()` 改為：區域證據領述 → artifact 型別 →
  **"Supporting measurement on this image:"**（原 "Measured on this image:"）
  → 驗證句。**零數字新增/變更/移除，純重排＋一個標題詞**。
  `evidence_regions is None`（fail-safe）時文字與改版前逐位元組相同。
- **非回歸硬閘 PASS**：769 張 True Test，`prediction`／`confidence`／
  `class_probs`／`artifact_types`／`suspicious_regions` **全部 0 差異**
  （`eval_regions.py` 於同一程序載入備份模組與現版對比）；schema v2.1.0
  五個抽樣（含 non_face）全部 valid。
- **誠實天花板（agent 主動揭露，未宣告成功）**：filter 類 298 張的**領述區域
  分佈 nose 288（96.6%）／eyes 9／skin 1**，且**與 artifact_type 幾乎無關**
  （whitening、smoothing 皆 100% nose）。與 `p2_evidence_wire_20260831` 的
  crosstab 一致（該輪 296-297/298）——本輪未觸碰
  `evidence_regions_for_filter()`，故此數字不變屬預期。已知成因：7×7 網格的
  32px 格子無法乾淨切開狹窄眼區與緊鄰的鼻樑格，且多型別訊號確實集中該鄰域。
  **結論措辭**：文字確實由 evidence head 逐張輸出驅動（298/298 區域子句內容
  相異，非固定模板），但因底層 map 在現行網格解析度下由單一區域主導，
  「evidence 驅動排序」多半是在一個近乎固定的領述（nose）周圍重排，
  **真正的槓桿是提高網格解析度**，非本輪所能修。
- **Claim**：MASTER_PLAN P2-A1 完成定義兩條 checklist 皆可打勾——(a) 前輪
  已完成（指向 `p2_evidence_wire_20260831`），(b) 本輪依字面規格完成；
  分類路徑可證未受影響。
- **Non-claim**：**不可**宣稱解決了「解釋像模板」——298/298 相異在 XAI-2
  第一層即已達成，非本輪貢獻；**不可**宣稱區域證據變得更有鑑別力或 nose
  主導已修復（不變、已揭露、屬既有 7×7 網格解析度限制）；未改任何
  checkpoint／split／模型／分類決策；`suspicious_regions` 仍用 legacy
  `ARTIFACT_REGION_MAP` 名稱（schema enum 限制，沿用 2026-08-31 決定）。
- **產出物**：`results/research/p2_xai2_evidence_regions_20260901/`
  （PRE_DECLARED、`pipeline_pre_xai2_regions_20260901.py.bak` 全檔備份＝
  rollback、`eval_regions.py`、`eval_regions_result.json`）。
  `pipeline.py` 僅改解釋函式。無 git。


---

## EVAL3-HEADLINE-RIGOR-20260901: headline 跨資料集表的可重現性與統計正確性稽核 — `eval3_headline_rigor_20260901`, **可重現 ✅／統計上不成立 ❌——兩個 headline 宣稱必須撤回**

- **動機**：本專案唯一能與文獻並列的那張表（`CROSSDATASET-TABLE-20260828`）
  有兩個未被檢查的可信度缺口：①單一 seed 訓練；②影片語料上用 frame-level
  bootstrap（同影片的幀非獨立樣本）。
- **Part A：可重現 ✅**。以 byte-identical recipe（腳本 **import** 原
  `AIGuard/train_ffpp_protocol.py` 而非複製）補跑 2 個 seed×2 arm：
  FULL **Celeb-DF-v2 0.7361 ± 0.0098**／**DFD 0.8545 ± 0.0086**（n=3）；
  已發表的單 seed 值（0.7284／0.8488）落在區間內——**該 seed 其實是略微
  不利的抽樣，非挑選**。無造假。**但 seed spread ~1pp（CDF 全距 1.9pp），
  意味著表中任何小於 ~2pp 的差異在 n=1 下皆無支撐**。
- **Part B：統計上不成立 ❌**。改以**影片為重抽單位**（B=10,000，
  video-ID 解析檢查 PASS：CDF 389 幀/357 影片、DFD 1,521 幀/162 影片）：
  | 資料集 | arm | AUC | naive frame CI | **video-cluster CI** | 膨脹 |
  |---|---|---|---|---|---|
  | Celeb-DF-v2 | FULL | 0.7284 | [0.6775,0.7773] | [0.6769,0.7790] | ×1.02 |
  | **DFD** | **FULL** | 0.8488 | [0.8288,0.8678] | **[0.7974,0.8941]** | **×2.48** |
  | DFD | SPATIAL | 0.8604 | [0.8413,0.8783] | [0.8141,0.9020] | ×2.37 |
  **原因已定位**：CDF holdout 每支影片僅 1.09 幀（本就近乎獨立，故幾乎不變）；
  **DFD 每支影片 9.4 幀（1-13），隱藏的偽複製全在 DFD——而最強的宣稱正好住在
  DFD**。
- **兩個 headline 宣稱必須撤回**：
  ①「DFD 勝出 Xception +3.2pp／104.0%」——**只在錯誤的 bootstrap 下成立**；
  正確 CI [0.7974, 0.8941] **包含** Xception 的 0.8163。
  ②「Celeb-DF-v2 打平 98.8%」——Xception 0.7365 亦落在我方 CI 內。
  **Xception 點估計在 4/4 格全部落入我方 video-cluster 95% CI。**
- **附帶傷亡：「spatial-only 勝過 dual-branch」的次要結論同樣不成立**。
  依 seed 配對後 Celeb-DF-v2 的 SPATIAL−FULL delta **跨 seed 變號**
  （+0.0071／−0.0087／+0.0178，mean +0.0054 ± 0.0133）；DFD 同號但
  +0.0049 ± 0.0059 屬雜訊量級。原被列為 FFT 分支無用論的「第四個獨立證據」
  ——**它不是證據，是 seed 雜訊**。（不牴觸既有立場，只是這兩格不能當證據引用。）
- **✅ 允許的替代宣稱（事前宣告，非事後框架）**：
  **「2.53M 參數的 dual-branch ShuffleNetV2 在兩個文獻協定跨資料集
  benchmark 上與 20.81M 參數的 Xception 統計上無法區分，參數量約 12%」**
  ——效率宣稱完全不受影響（參數比是硬事實），只有**方向性優勢的措辭**必須移除。
- **附帶查獲三項**：①已發表的「2.55M 參數」實為 params＋BN buffers，
  trainable 為 **2,528,742**（Xception 20.81M 為 params-only，故對照略不對等，
  但方向使我方宣稱更保守）；②`crossdataset_table_20260828` 的 FINDINGS **確實
  有 Hanley–McNeil 區間並自行註明「未做叢集校正、視為下界」**——本輪任務簡報
  說「完全沒有 CI」不精確，已更正；問題在於那些區間**只存在於 markdown 散文、
  沒有任何 JSON 承載**，故從未傳播進 paper-facing 表；③該輪內部有 ~6e-4 的
  數字不一致（表用 0.7278、control JSON 為 0.72838，本輪獨立重跑與後者
  bit-exact 吻合），不影響結論但應統一引用來源。
- **Non-claim**：n=3 的 ±為 2 自由度樣本標準差，僅供指示；CI 僅涵蓋測試集
  抽樣不確定性（seed 變異另計，若合併會更寬，只會強化「無法區分」的判定）；
  無法為 Xception 附 CI（文獻點估計，此不對稱屬保守方向）；DFD 子集
  162/3,431 支影片且偏近拍（沿用原輪 caveat）；DFDC/DFDCP 兩欄仍未取得。
- **建議的下游修改（本輪未執行）**：登錄檔標記 `CROSSDATASET-TABLE-20260828`
  的兩個宣稱為 superseded；論文改採「統計上無法區分、~12% 參數」措辭並改引
  2.53M/1.78M trainable；撤回 spatial-only 的「第四個獨立證據」框架；
  **影片語料 AUC 一律預設採 video-cluster bootstrap**（與
  `remeasure_sweep_20260826` 一致）。
- **產出物**：`results/research/eval3_headline_rigor_20260901/`
  （PRE_DECLARED、3 支 driver、`bootstrap_ci.json` 12 格、
  `honest_table.{json,md}`、6 份 train_meta/log、12 份 `perframe_*.tsv`
  可無 GPU 重算）；checkpoint 於
  `checkpoints/research/eval3_headline_rigor_20260901/`。
  未動 `pipeline.py`／production checkpoint／splits，未讀任何 LOCKBOX，無 git。


---

## DESIGN-AUDIT-20260901: 三個「設計說不通」之處的實測稽核 — `design_audit_20260901`, **三個探針全部命中；其中 Probe 1 推翻本專案一項核心宣稱**

純推論，未動 production。三個模型 sha256 已記錄於 FINDINGS。

### Probe 1 — Layer2 沒有「real」輸出，但 production 一直餵 real 圖給它

- **確認且比預測更嚴重**：Layer2 訓練資料經查**無任何真實照片來源**，但 Layer1
  real recall 72.4% ⇒ 約四分之一真照片會進到 Layer2，而 Layer2 **無任何輸出
  能表達「這其實是真的」**。實測：True Test **250/250（100%）**真照片若送進
  Layer2 都會被判 `filter`；實際通過閘門的 69 張**全部**落 filter、0 落 fake，
  逐數重現 `p1_realrecall_diag_20260831`。
- **🔴 最重要的發現——配對對照推翻「Layer2 會辨識濾鏡」這個宣稱**：True Test
  為配對設計（249/249 濾鏡圖由對應真照片生成，內容/語料/原生解析度全部按構造
  匹配）。**對同一張照片施加濾鏡後，`p_filter|manip` 的變化：平均 −0.00346、
  中位數 −0.00120，41.8%（104/249）的配對反而下降**。
  **⇒ 「施加美顏濾鏡不會讓 Layer2 更傾向判 filter」。Layer2 在 True Test 上
  100% 的 filter argmax 不是濾鏡偵測，是在辨識 LFW 裁切語料。**
  對應的 AUROC：True Test real vs filter = **0.4755 [0.4255, 0.5249]**
  （點估計低於 0.5，CI 跨 0.5），而該格的解析度控制**精確 0.5000**
  （兩側皆 250px）——**唯一一個混淆完美受控的比較，也正是失敗的那個**。
  其餘看似漂亮的格（CelebA vs filter 0.9963、fake vs filter 1.0000）
  解析度控制為 **1.0000／0.9791，完全混淆，不得引用為 Layer2 能力證據**。
- **錯誤流向依語料而異，原「real 錯誤全流向 filter」的通則說法為假**：
  Shadow VGGFace2 real 的閘門洩漏 **62/74（84%）流向 `fake`**，非 filter。
  ⇒ Layer1 real 錯誤的**嚴重性依語料而定且不可預測**，而對真人照片judgment
  為 `fake` 是本產品最糟的失效模式。
- **無「邊界案例」可用來緩和**：閘門通過 vs 未通過的真照片，其
  `p_filter|manip` 分佈 AUROC 0.5285 [0.4473, 0.6124]（True Test）——CI 含 0.5；
  Shadow 那格 0.5749 但**解析度控制 0.5781 ≥ 訊號，該格作廢**。
  Layer2 對 True Test 真照片的判定在 ~0.92 飽和，與閘門是否放行無關。

### Probe 2 — 階層可能切在錯誤的軸上

- **事前宣告的比較 VOID（解析度混淆）**：Grouping A（現行 {real} vs
  {fake,filter}）AUROC 0.9663±0.0136 vs Grouping B（語義 {real,filter} vs
  {fake}）**0.9971±0.0028**，但**解析度單獨控制 A=0.7890、B=0.9329**——
  假語料與真/濾鏡語料的原生解析度近乎互斥，B 的任務本質上更可由解析度分開。
  解析度配對子分析（240-260px 帶）內 **B 的解析度控制達 1.0000**（假 256px
  vs 真/濾鏡 250px 完美分離）⇒ **不存在 B 不被混淆的配對子集，事前比較無法
  回答問題**，如實記為 VOID 而非部分成功。
- **事後補控制（非事前宣告，標記為探索性）**：全部影像先降採樣至
  min-side **128px**（全體最小值）再走 production 前處理，解析度按構造不帶
  類別資訊。結果 **A 0.9060±0.0137 vs B 0.9900±0.0086，ΔAUROC +0.0840，
  fold 不重疊**（B min 0.9798 > A max 0.9220）。
  **依事前宣告的解讀規則：特徵來自為 A 訓練的 Layer1，A 佔便宜；B 仍勝
  8.4 個 AUROC 點 ⇒ 強證據顯示第一層切在錯誤的軸上**（身份保留 vs 身份改變
  的切法，在 production trunk 自己的特徵空間裡比它被訓練去做的切法更線性可分）。
- **本輪自陳的最大威脅（未控制）**：filter 類僅來自單一語料（True Test filter，
  LFW 衍生），而 real 類 249 張中有 83 張正是那些濾鏡圖的底圖；Grouping B 合併
  {real, filter} 等於部分合併了同一批照片，可能膨脹 B。**復現需要一個底圖與
  real 類互斥的濾鏡語料**。故本輪**只 license「值得提出重新設計比較」，
  不 license「階層是錯的，快改」**。

### Probe 3 — 棄權機制根本不運作（比「門檻沒校準」更嚴重）

- **掃描 0.00→0.95 全域：不存在可用操作點**（事前判準：Alibaba 棄權 ≥80%
  且同域棄權 ≤10% ⇒ `exists: false`）。全程只買到 **+1.4pp** 跨演算法準確率
  （37.87%→39.24%），代價是棄權 30% 的輸入。
- **根因：信心值對自身正確性毫無資訊**——跨演算法（Alibaba）上
  **top-conf 預測正確性的 AUROC = 0.5368（等同隨機）**，而同域為 0.9394；
  跨演算法的信心中位數高達 **0.9965**，準確率卻只有 38%。
- **production 門檻 0.6 等同於沒有棄權機制**：Alibaba 保留樣本準確率
  38.33% [35.82, 40.89] vs 關閉棄權的 37.87% [35.45, 40.35]——CI 幾乎完全重疊。
- **最尖銳的單一實例**：`face_reshaping` 在跨演算法輸入上**有信心地回答 96%
  的樣本，且錯 94.7%**（準確率 5.3%，低於 25% 隨機基線），而同域 62/62 全對、
  0 棄權。分類器學到的是某一家的 `shrink_ratio=0.92` 變形，不是「臉型調整」。
- **論文措辭必須升級**：從「`ARTIFACT_UNKNOWN_THRESHOLD=0.6` 未校準」改為
  **「artifact 分類器的 softmax 信心在訓練演算法家族之外，對自身正確性不帶
  可用資訊（AUROC 0.5368），故信心門檻在任何數值下都無法實現開集棄權」**
  ——修法需要不同的棄權訊號（訓練式 OOD/energy score 或逐廠商校準集），
  而非更好的常數。

### Claim / Non-claim

- **Claim**：①Layer2 缺 real 輸出是架構層級缺陷，且其 True Test 濾鏡「能力」
  經配對對照證實為語料辨識而非濾鏡偵測；②Layer1 real 錯誤的流向依語料而異
  （True Test→filter 100%、Shadow→fake 84%），嚴重性不可預測；
  ③棄權機制在任何門檻下皆不可用，根因為信心值 OOD 下無資訊。
- **Non-claim**：Probe 2 的決定性結果為**事後控制**且 filter 語料與 real 類
  部分同底圖，**不得引為「應改架構」的定論**，須以互斥語料事前重跑；
  本輪為推論探針，未量測端到端產品行為改變；無 production 變更、無 git。

### 產出物
`results/research/design_audit_20260901/`（PRE_DECLARED、`_common.py`、三支
probe 腳本＋三份 results JSON＋三份 per-image TSV＋三份 stdout log、
`probe2_features_downsampled128.npy`）。


---

## FIX-PAIRED-CONTRAST-20260901: 配對對照 3-class Layer2（修法輪）— `fix_paired_contrast_layer2_20260901`, **主門檻 REJECT／機制因果性 CONFIRMED／硬閘 FAIL 不可促升——三段判定分開記**

- **設計來源**：直接修 `DESIGN-AUDIT-20260901` 診斷出的病因——Layer2 訓練集中
  filter 與 fake 來自不同語料且無原圖對照 ⇒ 語料身分即標籤充分統計量。
  修法＝把 (原圖, 濾鏡圖) 配對放進訓練（語料/身份/姿態/解析度在決策邊界兩側
  相同，無法承載標籤）＋Layer2 升 3-class 給真照片一個出口。
- **執行史（完整保留，為證據之一）**：v1 配方（保留舊列）於 **epoch 2 被檢查
  攔停**——filter 類僅 5% 配對（捷徑仍在）、real 1.5%＋22 倍權重致訓練崩潰
  （filter F1 0.000）；AMENDMENT 1 重建資料（7,981 組生成配對，底圖刻意選
  celeba_train＋AIGuard/real 以**避開 CelebA gate 與 UTKFace lockbox 污染**
  ——原指令點名的 celeba_test/UTKFace 為第二個被自查攔下的錯誤；＋2,210 組
  FFHQ 三重配對；filter 類 71.3% 配對、三類 2 倍內）。修正後訓練健康
  （macro F1 0.8486；fake 0.997/filter 0.792/real 0.757）。
- **主指標（事前門檻 +0.30/+0.10）：REJECT**——配對 Δ`p_filter|manip` 中位數
  held-out +0.0749／True Test +0.0149。**但方向性徹底翻轉（機制的因果證據）**：
  True Test 反方向配對 **41.8%→8.0%**（92.0% 正向；production 基線中位數
  −0.0012）；3-way 原始刻度（次要，如實並列）+0.167／+0.109 達 PARTIAL。
  **這是語料捷徑診斷的第一個介入性（非相關性）證據，且跨語料成立**
  （True Test 的 LFW 配對從未進配對訓練）。
- **硬閘 FAIL**：`fake_filter_stress` **4.67% > 3.76**（集中於
  whitening_medium 11.15／eye_enlarging 9.09／face_reshaping 8.04，smoothing
  類維持 1.4）；**Alibaba gate 依事前規則判 CONTAMINATED**（gate 母體 2,207
  個 FFHQ base id／1,735 個完全相同路徑在訓練集內，數字 43.77% 記錄但
  **不得引用**）。
- **v8.8 Pareto 如事前預告重現，且首次在階層內被乾淨量化**：`real` 出口
  雙向作用——好的方向：Shadow real 端到端 **74.91→79.93%**（+5.0pp）、
  CelebA 99.80、TT real 73.09（最糟失效模式「真照判偽」收縮）；壞的方向：
  **輕度操弄被吸進 real**（Alibaba by-type：Smoothing 78.5% vs
  FaceLifting 22.2%／Whitening 33.3%——細微型別洩向 real）且部分加濾鏡假圖
  找到新出口（stress 上升）。一個旋鈕、兩個耦合後果。
- **轉移不變（與事前解讀規則預測一致）**：B-LFW 0.66%（production 0.45／
  FILTER2 1.41／SRM 0.93）——配對修的是監督訊號不是表徵，跨家族泛化不動。
- **Claim**：①「缺對照配對」是 Layer2 語料捷徑的真實成因之一（介入性、
  跨語料）；②real 出口的 trade-off 已量化；③下一個自然槓桿是**幅度**——
  方向已修、Δ 仍小，顯示平凡 CE 未充分利用配對，(original, filtered) 的
  pairwise margin loss 是明確的下一步。
- **Non-claim**：不可促升（stress 閘 FAIL）；不可引用 Alibaba 數字（污染）；
  不可宣稱跨家族泛化改善（B-LFW 持平）；單 seed。
- **產出物**：round 資料夾含 PRE_DECLARED（含 AMENDMENT 1）、生成/建構/訓練/
  三支評測腳本與全部 JSON/log（v1 壞版備份保留）；checkpoint sha `c8eeb8c7...`。
  未動 production、無 git、未讀 LOCKBOX。


---

## FIX-PWMARGIN-20260901: pairwise margin loss＋fake-side pairs — `fix_pairwise_margin_20260901`, **primary REJECT／幅度槓桿在有配對處成立／硬閘更差不可促升——但產出三個機制級發現**

- **設計**：承 `FIX-PAIRED-CONTRAST-20260901` 兩項量測結果：①CE 把配對當獨立
  列、從未「看到」對照 ⇒ 加 pairwise hinge（m=2.0, λ=0.5，配對相鄰批次、
  mixup 因毀配對語義而全域停用——記為與 control 的 bundled recipe 差異）；
  ②stress 退步因無「加濾鏡的假仍是假」例子 ⇒ 生成 4,000 組 fake-side 配對
  （排除含 "unseen" 路徑 2,242 列以護 stress gate，斷言 4,000/4,000 通過；
  3,792 成／208 無臉跳過；363 組 held-out 以 sha256 於訓練前固定，零重疊
  斷言 0/726）。
- **主門檻：REJECT**——TT Δ_cond **+0.0158**（持平 control +0.0149，<0.10）；
  但 **held-out FFHQ Δ_cond +0.0749→+0.2077 近三倍**（介入性、held-out base
  id）。**margin loss 是真實的幅度槓桿——僅在配對存在之處**；幅度增益在
  conditional 刻度上不跨語料轉移。
- **方向再收斂**：TT 反向 8.0%→**4.0%**（production 58.2%）；TT Δ_3way
  +0.109→+0.195。**方向問題可視為實質解決。**
- **🔬 機制發現一（hinge 不對稱）**：fake-side hinge epoch~3 飽和
  （1.55→0.14），**real-side 永不飽和**（2.00→0.358 @15，均值仍有 ~18% 未達
  margin）——「real vs filter 的對比」是束縛約束，正是跨語料 Δ 微小的
  訓練期簽章。逐 epoch 曲線存 `train_layer2_pwmargin_log.csv`。
- **🔬 機制發現二（兩 hinge 張力）**：fake-side 配對在自身分佈上完全有效
  （held-out 363 組 median Δp_fake **−0.0010**≈0，濾鏡不侵蝕 fake-ness），
  但保護**不轉移**到 unseen 假底圖（stress 母體被守則排除於配對生成之外），
  而 real-side margin 壓力全域推高 filter logit ⇒ stress 重塑而非修復：
  smoothing/combined 條件塌至 0.35-0.70%，但 whitening_medium 11.15→13.24／
  eye_enlarging 9.09→11.89／face_reshaping 8.04→13.29。
- **硬閘：FAIL 且比 control 差**——stress **5.33**（control 4.67，bar 3.76）；
  **TT filter 89.56 < 90（本線首次跌破）**；TT fake 98.89（過 95 但低於
  production 99.63）；CelebA 99.73 過；Alibaba **CONTAMINATED**（同 control
  的 FFHQ 訓練列；32.52 記錄不可引用）。
- **🔬 機制發現三（意外正向）**：**B-LFW 2.98%**（production 0.45／control
  0.66／FILTER2 1.41／SRM 0.93）——**四輪以來跨家族轉移首次移動**（4.5×
  control），落於事前宣告的 bonus-finding 槽；絕對值仍 REJECT 級，跨家族
  泛化維持不宣稱。Shadow real 82.08（+7.2 vs production）。
- **Claim**：①margin loss=有效的 in-corpus 幅度槓桿（介入性）；②方向已
  實質解決（4.0% vs 58.2%）；③語料捷徑殘餘被精確定位——跨語料 conditional
  幅度，訓練期簽章=永不飽和的 real-side hinge；④兩 hinge 張力已量化。
- **Non-claim**：不可促升（兩硬閘 FAIL 且 stress 劣於 control）；不可引用
  Alibaba；bundle 未消融（促升動機已消失，消融緩辦）；不可宣稱跨家族泛化。
- **產出物**：round 資料夾（生成/訓練/四支評測腳本＋全部 JSON/log/curve）；
  checkpoint sha `836406b4...`。未動 production、無 git、未讀 LOCKBOX、
  前輪檔案唯讀。

---

## AXIS-DECISION-20260901: hierarchy-axis 事前宣告乾淨複現 — `axis_decision_20260901`，**VINDICATED：現行軸 A 勝出，非 inconclusive、非 B 勝**

- **背景**：`DESIGN-AUDIT-20260901` Probe 2（post-hoc 控制）曾發現語意軸
  {real∪filter} vs {fake}（軸 B）在 production trunk 自己的特徵空間裡比
  現行軸 A（{real} vs {fake∪filter}）可分性高 +8.4 AUROC——但該發現因
  post-hoc 探測 + real/filter 兩類共用 83 張 FFHQ 底圖而被判定不可引用，
  PRE_DECLARED 明訂需要一輪乾淨複現才能裁定。
- **設計**：兩個對稱、**ImageNet init（刻意不 warm-start，避免血緣偏向現行
  軸）**的 `DualBranchModel(num_classes=2)`，資料以 FFHQ id 做種子排列對半
  切（half1 1,105 id 僅原圖→real；half2 1,105 id 僅濾鏡版本（Alibaba+
  ours_ffhq）、原圖整批排除→filter，real/filter **零底圖重疊**，斷言通過），
  fake 用 pixart 抽樣 2,210（唯一與 FFHQ 同解析度 1024 native 的 DF40
  method）。3 seed/軸，共 6 個從零訓練的模型。
- **事前宣告決策規則**：cross-corpus mean AUROC（7 個未見語料，依各軸自身
  定義分組），3-seed 平均，B≥A+0.03 且 seed 範圍不重疊→CONFIRMED；
  |Δ|<0.03 或重疊→INCONCLUSIVE；A≥B+0.03→VINDICATED。
- **結果（已用 axis_results.json 逐位元組獨立覆核，含 decision 區塊、兩軸
  seed1 全部 22 個 pair 級 AUROC/confound 旗標、三 seed 混淆計數、error-cost
  三 seed 均值）**：軸 A mean **0.6631**（0.6546/0.6708/0.6640，緊聚）；
  軸 B mean **0.3778**（0.3710/0.3803/0.3822，同樣緊聚）；Δ(B−A)=**−0.2853**，
  seed 範圍不重疊（A min 0.6546 > B max 0.3822）。**VINDICATED：現行軸大幅
  勝出**，Probe 2 的post-hoc勝利歸因於其殘留混淆，非真實軸誤設。
- **⚠️ 解析度混淆密度高，已內建控制並如實報告**：軸 A 12 個 cross-corpus
  pair 中 10 個、軸 B 10 個中 9 個（三 seed 一致）解析度單獨控制 AUROC ≥
  模型 AUROC（各語料原生解析度系統性不同）。**但 A vs B 比較本身不受此
  混淆污染**：兩軸共用的 6 個 pair（fake 對 real/celeba/shadow，三語料下
  fake 皆為 positive）解析度混淆完全相同、在差值中抵消；真正拉開差距的是
  各軸獨有的 6 個/4 個 pair。
- **軸 B 崩潰的根因（機制級）**：`blfw|unseen_fake` AUROC **0.009-0.010**、
  `tt_filter|unseen_fake` **0.058-0.060**（三 seed 一致）——模型把
  AIGuard/unseen 的假圖判得比 B-LFW 濾鏡自拍更「真」，方向完全顛倒。單一
  generator（pixart）撐起軸 B 的唯一決策邊界，對 unseen_fake（不同
  generator 家族）完全不轉移；軸 A 因對抗池更大（fake+filter 混合）而稀釋
  同一弱點。
- **Error-cost cell（genuine 圖落在危險側比例，matched FPR=5%，3-seed 均值，
  已獨立覆核）**：TT real 軸A 90.4% vs 軸B 93.5%；CelebA 55.2% vs **78.4%**；
  Shadow real 46.7% vs 45.1%——軸 B 在每個 genuine 母體上持平或更差，
  CelebA 差距最大，與主判決一致。
- **Claim**：①現行 hierarchy 軸（real vs manipulated）在乾淨、事前宣告、
  base-id-disjoint 的複現下明確優於語意軸，可作為「為什麼這樣切」的決策級
  答案，取代先前的「歷史因素」；②Probe 2 的 post-hoc 發現已被解釋（殘留
  混淆），非被否證的獨立矛盾證據；③軸 B 的失敗機制（單一 generator 不轉移）
  本身是一個可引用的發現，指出未來若要重測任何以「先隔離 fake」為第一刀的
  設計，必須先把 fake 側擴到多 generator。
- **Non-claim**：不構成 architecture 變更提案（規則僅在 B 勝時才授權提案，
  本輪是 A 勝）；fake 側仍單一 generator（pixart），此限制本身已被本輪結果
  證實其重要性、待未來擴充；未讀 LOCKBOX；未動 production/pipeline.py/git。
- **產出物**：`results/research/axis_decision_20260901/`（PRE_DECLARED、
  build_axis_data.py + data_build_report.json、train_axis.py + 6 份
  train_log、eval_axis.py + axis_results.json + 6 份 scores tsv、
  FINDINGS.md）；checkpoints 6 個（`checkpoints/research/axis_decision_20260901/`，
  axisA/B × 3 seed）。GPU serialized，兩次訓練 session 中途重啟但皆從零
  完整重跑同 seed，最終集合內無斷點續訓。

---

## R12-POSTPROCESS-20260901: 濾鏡 vs 一般後處理 confound 檢測 — `filter_vs_postprocess_20260901`，**PARTIAL confound：溫和濾鏡確診分不開，強力濾鏡是已知缺陷的更大量級復現，主判定指標事前訂錯已當場修正**

- **背景**：Reviewer 必問清單 R12（濾鏡與壓縮/重採樣等一般後處理有何區別）
  先前完全零調查。設計：同一批 250 張 True Test real 底圖，分別套用 8 種
  production 濾鏡函式（Group A）vs 5 種無美化意圖的一般後處理（JPEG
  重壓縮 q40/q60、resize round-trip、銳化、模糊，Group B），單獨評分
  production Layer2，比較兩組對 p_filter 的影響。
- **⚠️ 方法論自我修正（事前訂的主指標本身有結構性缺陷，已當場查獲並改正，
  非執行錯誤）**：原訂主指標「AUROC(A vs baseline) 減 AUROC(B vs baseline)」
  的事前 sanity check（A vs baseline 應該 ≈90%+）**實測只有 0.2646，明確
  FAIL**，執行 agent 的 `summary.json` 仍照算下去給出「CONFOUND CONFIRMED」
  ——違反 PRE_DECLARED 自訂的停損規則。根因查明：baseline（完全未處理的
  真照片）本身 p_filter 已達 0.9097 平均、99.6% 已 > 0.5——完全對應
  `DESIGN-AUDIT-20260901` Probe 1 已診斷的「Layer2 無 real 輸出」舊缺陷，
  baseline 已飽和使「各組對共同 baseline 算 AUROC 再相減」這個指標完全
  失去鑑別力。**改用配對 Δp_filter（每張圖對自己的 baseline）+ 直接
  Group A vs Group B 比較**（不透過已飽和的共同 baseline），從
  3,500 筆原始紀錄重新獨立計算驗證。
- **修正後的真實結果，依濾鏡類型二分**：①**強力磨皮/組合濾鏡**（smoothing/
  combined medium/heavy）跟後處理**清楚可分**（直接 AUROC=0.216，即反向
  0.784，效果量大）——但方向是**已知缺陷的更大量級版本**：濾鏡越強
  p_filter 掉越多（combined_heavy 中位數 Δ=−0.2122，smoothing_heavy
  Δ=−0.1451），跟 Probe 1 量到的 −0.0012 中位數同方向、量級大上百倍
  （本輪用的濾鏡函式較強，不能直接說 production 在真實 True Test 上也會
  掉到這個量級，但缺陷本身是同一個）。②**溫和/幾何濾鏡**（eye_enlarging／
  whitening／face_reshaping，也是訓練資料裡數量最多、最貼近真實使用情境
  的型別）**跟一般後處理真的分不開**：三型合併 vs Group B 合併 AUROC=
  **0.4363**（近乎隨機），個別型別 AUROC 0.38-0.52。**這才是 R12 的真正
  確診：不是「所有濾鏡都跟後處理混淆」，是「溫和濾鏡對 Layer2 而言，
  訊號量跟純後處理沒有差異」。**
- **附帶發現（agent 原始資料，已核對無誤）**：後處理誤判觸發 artifact
  分類時路徑高度集中——sharpen/JPEG q40/q60 觸發時 90%+ 被歸類
  `eye_enlarging`（242/248、225/248、231/249），blur/resize_roundtrip
  偏向 `face_reshaping`/`whitening`——代表誤判會附帶生成看似言之鑿鑿但
  無關的濾鏡型別說明文字，比單純誤判本身更糟。
- **Claim**：①R12 首次有實測答案且範圍精確（溫和濾鏡 vs 後處理不可分，
  強力濾鏡可分但方向反）；②強效磨皮方向顛倒缺陷的第 N 次獨立復現，量級
  更大；③後處理誤判會連帶產生無關但看似有據的型別說明，是解釋層繼承
  分類層錯誤的又一具體案例；④方法論教訓：當母體 baseline 因既有缺陷已
  飽和時，「各組對共同 baseline 算 AUROC 再相減」不是有效指標，須改配對
  Δ 或直接組間比較——此教訓需套用到未來任何「Layer2 單獨評分未過 Layer1
  閘門真實照片」的實驗設計。
- **Non-claim**：不是 filter 語義定義錯誤的證據，是訓練資料缺口的證據
  （Layer2 從未見過純後處理負樣本）——修法方向是補訓練資料，非重新定義
  類別；只測 Layer2 單獨評分（略過 Layer1 閘門），跟端到端 pipeline 行為
  可能不同；未動 production、未重訓、未讀 LOCKBOX、無 git commit。
- **產出物**：`results/research/filter_vs_postprocess_20260901/`
  （PRE_DECLARED、generate_and_score.py、per_image_results.json 3,500 筆、
  summary.json（原始數字正確但 verdict 文字已被 FINDINGS.md 取代不應單獨
  引用）、本輪修正版 FINDINGS.md）。未動 production、無 git、未讀 LOCKBOX。

---

## R1R13-IDENTITY-20260901: filter 身分保留下游證據（ArcFace）— `filter_identity_downstream_20260901`，**CONFIRMED，遠超門檻（pooled AUROC 0.99997）**

- **背景**：Reviewer 必問清單 R1（自建濾鏡有何意義）與 R13（filter 為何該
  獨立成類）皆缺下游任務證據，只有語義主張或負面證據（跨演算法型別準確率
  3-35%）。本輪用 ArcFace 身分距離同時回答兩題：filter pairs（原圖↔濾鏡圖）
  vs identity-swap fake pairs（Celeb-real↔SiT/DiT/StyleGAN3 換臉)的身分
  保留程度是否有下游可量測的顯著差異。
- **資料**：filter 側——自建（True Test paired，249)＋Alibaba 真實 app
  （FFHQ id 配對，1,000 抽樣），Megvii 因 FFHQ id 範圍（60000-69999）本機
  無對應原圖，**執行前自查排除**（範圍縮減記錄在案，非事後補充）。fake
  側——Celeb-real 與 SiT/DiT/StyleGAN3 三個 identity-swap 方法共用的 588 個
  身分，全部用中間影格抽 ArcFace embedding（InsightFace buffalo_l, CPU）。
  **明確排除** production 實際 fake 訓練主力 EFS（sd2.1/DiT/SiT/ddim/pixart
  的頂層版本，依 DF40 官方 Table 2 為 entire-face-synthesis，無來源身分
  可比對）。
- **主判定：CONFIRMED，遠超 ≥0.85 門檻**——pooled AUROC=**0.99997**（filter
  合併 1,249 vs fake 合併 1,764，已從 `raw_distances.json` 逐張距離獨立
  重算核對）。filter 中位數 identity distance **0.0335**（身分幾乎完全
  保留），fake 中位數 **0.9855**（身分幾乎完全被替換）——兩分布幾乎零重疊,
  三個 fake 方法各自對 filter 的 AUROC 皆 0.999+。**這是本專案第一次為
  「filter 保留身分、fake 摧毀身分」這個核心語義主張提供量化下游證據**,
  不只是斷言。
- **R1 次要判定：criterion_met=true**——自建（中位數 0.0366）vs Alibaba
  真實 app（中位數 0.0331），絕對差 0.0035（門檻 <0.05）、Cliff's δ=0.097
  （negligible 頻帶，門檻 <0.147），兩條件皆過。Mann-Whitney p=0.0179
  技術上顯著（n 達千級），但效應量趨近零，依事前約定措辭誠實回報為
  「統計上可偵測、實務上可忽略」——**支持性證據（非證明）：自建 OpenCV
  濾鏡跟真實 app 濾鏡對身分保留的下游影響同一量級，語義等價主張站得住腳**。
- **Claim**：①R13 首次有量化下游證據撐著「filter 該獨立成類」的語義主張；
  ②R1 首次有量化證據支持「自建濾鏡跟真實 app 濾鏡語義等價」；③論證對
  EFS（production 實際 fake 主力）而言邏輯上更強（EFS 連來源身分都不存在）
  但本輪不宣稱涵蓋 EFS，僅涵蓋 identity-swap fake。
- **Non-claim**：不涵蓋 EFS fake（無來源身分可比對，邏輯論證更強但無法
  量測）；ArcFace 距離測的是特定凍結第三方模型的可辨識度，非「身分真相」，
  渲染 artifact/壓縮解析度變化兩個已知混淆未拆解；Megvii 排除為範圍縮減；
  純讀取量測，未訓練、未動 pipeline.py、未寫 checkpoint、未讀 LOCKBOX，
  不影響任何母體作為未來分類器 held-out 評測集的地位。
- **產出物**：`results/research/filter_identity_downstream_20260901/`
  （PRE_DECLARED、run_measurement.py、analyze.py、raw_distances.json
  3,013 筆逐張距離、analysis_results.json、FINDINGS.md）。未動 production、
  無 git、未讀 LOCKBOX。

---

## FIX-ABSTENTION-OOD-20260902: 棄權機制十法零重訓修復嘗試 — `fix_abstention_ood_20260902`，**全部 REJECT，但升級為有天花板量測撐著的表徵層限制**

- **背景**：`DESIGN-AUDIT-20260901` Probe 3 診斷 production 棄權機制
  （`ARTIFACT_UNKNOWN_THRESHOLD=0.6`）在任何門檻下皆不可用（信心對自身正確性
  跨演算法 AUROC 0.5368＝隨機），**但從未有任何修復嘗試**。本輪為第一次修復嘗試。
- **設計**：從凍結的 `artifact_classifier_v6`（sha256 `56b4e399...` 執行時驗證）
  算十種零重訓不確定性/OOD 分數：MSP、energy、max-logit、entropy、
  Mahalanobis（empirical + Ledoit-Wolf）、deep-kNN k=50、TTA×3
  （架構無 dropout，依事前宣告以 T=8 TTA 替代 MC-dropout）。母體/前處理/
  正確性定義/seed 全部沿用 Probe 3 逐位元組相同。**復現檢查先過才准報新數字**
  （MSP max|Δ|=7.6e-5，通過）。
- **結果：十種全部 REJECT**（事前線 <0.60）。最佳 TTA mean top-prob
  **0.5627**（production MSP 0.5369，差距落在自身 CI 內）；
  **操作點（Alibaba 棄權≥80% 且 in-domain 棄權≤10%）十種皆 `exists: false`**。
  10% 預算內最好棄權 64.1%；要 80% 最便宜需 **19.3% in-domain 棄權
  ＝預算 1.93 倍**，且留下的跨演算法答案仍過半是錯的。
- **🔬 機制發現（比 Probe 3 更銳利）**：逐型別 AUROC 顯示合併後的 ≈0.54
  **不是「到處都弱」，是一個型別強正向被兩個型別強反向抵銷**。Alibaba
  `face_reshaping` 上 logit 家族 AUROC **0.232-0.291（<0.5）**——**信心越高
  越可能錯，門檻會優先保留錯誤答案**。另：logit 家族與特徵密度家族
  （Mahalanobis）在**互不重疊**的型別上有效（型態完全相反），解釋了為何
  事後 ensemble 無效（成員互相抵銷）；「依型別選分數」需 Alibaba 標籤才能選，
  等於擬合唯一 held-out 集，本輪不可採用。
- **🔬 天花板量測（本輪最有價值的部分）**：用**允許作弊**的 oracle 探針
  （直接拿 Alibaba 正確性標籤訓練，GroupKFold 依 FFHQ 底圖 id 分組防洩漏）
  量「這個表徵裡到底有多少能力資訊」：天花板 **0.6658**，其中
  **0.6074 光靠「模型輸出了哪一類」查表即可取得**（Alibaba 上預測 smoothing
  99.1% 對、預測 face_reshaping 僅 20.4% 對），**表徵本身僅承載 +0.058 AUROC**
  （CI [0.021,0.094]，顯著但實務可忽略）；非線性學習器不提高天花板（0.658）。
  ⇒ 十種分數不是不夠聰明，是在搜尋一個只有約 0.06 AUROC 可用訊號的空間。
- **語料捷徑第四個獨立實例（事前點名、事後命中）**：PRE_DECLARED §4 事前寫明
  「分離 AUROC 高 + 正確性 AUROC 隨機 ⇒ 判為語料捷徑不得當成修好」。實測
  分離 AUROC 0.61-0.89、正確性 AUROC 隨機——**分數知道自己看到不同語料，
  卻不知道自己即將答錯**。
- **Phase 2（outlier exposure）已設計、已事前宣告、刻意未執行**：
  ①`PRE_DECLARED_PHASE1B.md` 在天花板算出前就訂死「0.60-0.75 帶 ⇒ 低勝率、
  設計但不建議執行」，天花板回來 0.666，照規則不做；②事前記錄機制性失敗預測
  （OE 規範 far-OOD 輸出分布，Alibaba 是 near-OOD——同型別同底圖不同廠商演算法，
  且缺口在表徵層非 logit 形狀）；③GPU 被並行訓練輪佔用。全程未用 Alibaba
  擬合任何東西（`phase1_extract.py` abort 級斷言把關，未觸發）。
- **⚠️ 覆核時查出：執行 agent 建議的兩個「後續方向」都已做過且都失敗**——
  參數隨機化＝`FILTER1-PARAMRAND-20260827`（NO-GO，0/4 型翻倍）、
  多廠牌訓練＝`filter1b_multivendor_20260828`（NO-GO，0/4 型翻倍、1/4 型退步）。
  連同底圖多樣性、增強、class weight 共**六個獨立失敗機制**。**此兩項不得
  當作新方向重跑**；記錄於此以防未來輪次重複踩坑。
- **Claim**：①棄權不可後處理修復，已從「試了一個門檻不行」升級為「十種方法
  搜尋過 + 有量測天花板」的可辯護限制；②失敗機制被指名（逐型別信心反向），
  非黑箱；③論文措辭應改為**表徵層限制（representational），非校準問題**。
- **Non-claim**：不可宣稱棄權原理上不可能；不可宣稱此頭不堪用（in-domain
  準確率 96.7%）；Alibaba 只是一家廠商不代表所有跨廠牌偏移；**不可宣稱
  Phase 2 試過並失敗（未執行）**。
- **產出物**：`results/research/fix_abstention_ood_20260902/`（3 份 PRE_DECLARED、
  6 支腳本、4 份 JSON、`perimage_phase1.tsv` 1,749 列×10 分數、
  `feats_*.npz` 可不重跑推論即重算、覆核版 FINDINGS.md）。純推論，未動
  production、未改 pipeline.py、無 git、未讀 LOCKBOX、未用 Alibaba 擬合。

---

## FIX-TRIPLET-POSTPROC-20260902: 三元組訓練把「被改過」與「被美化」拆開 — `fix_triplet_postproc_20260902`，**Primary A（R12 閉合）BUILD 兩 seed／Primary B（幅度）REJECT／stress 仍未過但三輪最佳**

- **設計（核心洞察）**：`R12-POSTPROCESS-20260901` 與 `FIX-PAIRED-CONTRAST`/
  `FIX-PWMARGIN` 兩組缺陷同根——Layer2 訓練資料只有「原圖→real」與
  「原圖+濾鏡→filter」，**「這張圖被改過」就足以預測 filter 標籤**，模型從無
  理由學美化專屬特徵。修法：同一底圖三元組 `原圖→real`／
  `原圖+一般後處理→**仍是 real**`／`原圖+濾鏡→filter`，使「有沒有被改」
  變成無資訊。2 seed，3-class head，warm start v811。
- **✅ 循環論證防呆已落實並驗證**（`transform_assertions.json` 三項斷言全 true）：
  訓練 14 種後處理與 R12 評測 5 種**參數層級完全不重疊**；其中
  **`sharpen`(unsharp) 整個家族從未進訓練**（完全未見家族），jpeg/resize/
  gaussblur 為同家族未見強度。資料：7,981 配對＋7,981 後處理列，
  filter 配對佔比 71.27%，三類比例 1.204，`no_baseid_leak: true`、
  `triplet_legs_never_split: true`；底圖用 celeba_train+AIGuard/real
  （避開 CelebA gate 與 UTKFace LOCKBOX）。
- **Primary A（R12 閉合）：BUILD 兩 seed**——production **0.4363**
  （獨立復現 R12 已發表 0.4362853，確認管線一致）→ **0.9158 / 0.8850**
  （3-way 空間；conditional 空間 0.9093 / 0.7333）。從隨機水準跳到接近乾淨
  可分，**且泛化到完全未見的 unsharp 家族**。⚠️ conditional 空間 seed 差
  0.18，穩定性應以較保守空間看待。
- **🔬 本輪最重要的發現——兩個主指標分道揚鑣**：**Primary B（配對幅度）
  REJECT 兩 seed**（TT 中位數 Δ 0.0089 / 0.0009，門檻 0.10）。
  **「能把美化與一般後處理分開」與「對同一張照片的濾鏡版本給更高 p_filter」
  是兩種不同能力，可以一個達成另一個不動**——先前三輪把它們當同一問題是錯的。
  直接推論：**要修幅度必須用別的槓桿，補負樣本不會順便修好**。
- **硬閘 3/4 過**：TT filter recall **91.16%**（兩 seed 同值，**修回
  PWMARGIN 打破的 89.56%**）、TT fake 98.89/98.52、CelebA 99.67/99.53、
  unseen AUROC 0.8248/0.8227 皆過；**`fake_filter_stress` 4.28%/3.98% 未過**
  （門檻 3.76%，production 2.80%）——但**三輪修法連續改善
  5.33→4.67→3.98**，seed 2 僅差 0.22pp。**不可促升。**
- **代價（誠實記載）**：①Primary B 的**方向穩定性比 PWMARGIN 退步**——反向率
  seed 1 13.65%、**seed 2 48.19%（近擲硬幣）**，PWMARGIN 是 4.0%；
  ②**B-LFW 跨家族增益完全流失**（PWMARGIN 2.98% → 本輪 0.008%/0.31%，
  低於 production 0.45%）；③端到端只有約一半純後處理影像被判 real
  （53.4% vs production 48.2%，改善約 5pp）——**指標層閉合 ≠ 產品層解決**。
- **Claim**：①R12 根因假設取得**介入性因果證據**（加入該類負樣本後指標從
  0.4363 跳到 0.885-0.916），非相關性；②泛化到未見後處理家族；
  ③兩種能力可分離（上述機制發現）；④stress 三輪連續改善且 TT filter 閘門修回。
- **Non-claim**：不可促升（stress 未過）；不可宣稱 R12 實務問題已解決
  （端到端僅改善 5pp）；不可宣稱方向/幅度改善（Primary B REJECT 且 seed 2 退步）；
  不可宣稱跨家族泛化（B-LFW 退步）；Alibaba 仍 CONTAMINATED 不列入判定。
- **下一步（由本輪證據直接推導）**：①幅度需別的槓桿——ArcFace 身分保留分數
  （`R1R13-IDENTITY-20260901` 量到 AUROC 0.99997）當訓練期輔助監督，資料共用；
  ②stress 只差 0.22pp——fake 側補後處理腿（「被壓縮過的假圖仍是假」），與本輪
  同一邏輯，且 PWMARGIN 已證明該類資料能收斂；③seed 變異需先確認配方穩定性。
- **執行註記**：執行 agent 於最後撰寫階段撞到 session 限制中斷，**訓練與全部
  評測皆已完成且結果檔完整**，FINDINGS.md 由覆核者直接從磁碟 JSON 逐項重算撰寫。
- **產出物**：`results/research/fix_triplet_postproc_20260902/`（PRE_DECLARED、
  9 支腳本、各 seed 四類評測 JSON＋perimage、production 對照組、
  transform 斷言與 split 統計）；checkpoints 兩枚
  （sha256 `76fd97d8...` / `c2c8680e...`）。未動 production、無 git、未讀 LOCKBOX。

---

## MOBILE-EVIDENCEHEAD-20260902: evidence head 首次手機匯出 — `results/mobile_export/evidence_head_20260902/`，**G1-G4 全過，但讓四模型 31.56 MiB 的部署成本首次現形**

- **背景（主張缺口，非例行工作）**：論文同時主張「可邊緣部署」與「filter 解釋
  由 patch evidence head 驅動、區域經 GT 驗證」（`P2-EVIDENCEWIRE1` 已接線
  `pipeline.py`），但 2026-08-22 手機匯出只有 Layer1+Layer2+artifact 三顆，
  **evidence head 從未匯出** ⇒ **兩個主張各自成立，但合起來（「手機上會給你
  證據驅動的解釋」）此前沒有任何證據**。本輪補上。
- **設計**：兩個變體。**FULL**＝完整 `forward()`（含 image_logits 路徑的 `topk`）；
  **PATCH**＝只匯出 production 實際消費的張量（`patch_logits`，
  `evidence_regions_for_filter()` 只讀 `patch_logits[0,1]`，從不讀 image_logits）
  ——PATCH **不是簡化版，是每張 filter 影像實際走的子圖**。FFT 分支依既有做法
  換 `mobile_fft.FFTBranchMobile`（矩陣乘法 DFT，數學等價零重訓）。
- **結果：兩變體 G1-G4 全過**。checkpoint `evidence_head_r2_last.pth`
  （sha256 `8f0438c0...`）載入零 missing/零 unexpected。**G4 刻意定義在
  production 消費的量上**（使用者唯一會觀察到的差異是區域排序翻轉）：
  24 張 True Test filter 影像上 filter 通道 sigmoid map 最大絕對誤差
  **2.92e-06**（門檻 1e-3，小 3 個數量級）、**區域排序不一致 0/24**、
  **top-1 不一致 0/24**。大小：FULL 8.95 MiB／**PATCH 5.82 MiB**。
  **附帶確認 `topk` 可轉換**（事前未知），故 PATCH 是部署選擇而非被迫 workaround。
- **⚠️ 代價（首次量到）**：**四模型 fp32 手機總量 = 31.56 MiB**
  （Layer1 10.46 + Layer2 10.46 + Artifact 4.83 = 25.75，＋evidence head 5.82）。
  Freeze Gate ≤25MB 門檻超出更多。**這不是本輪造成的退步，是讓一個一直存在
  但從未被算進去的成本現形**——只要論文宣稱手機端會給證據驅動解釋，這顆
  head 的體積就一直都在。**緩解已量測**：evidence head fp16（PATCH）僅
  **2.94 MiB** ⇒ 四模型約 28.7 MiB；int8 路徑（`ARCH2-INT8SPLIT1` 已解鎖）
  尚未套用到這顆 head。**單位已驗證**：專案用 MiB(2^20)，本輪重量三模型
  25.75 與已發布數字逐位吻合，非換算差異。
- **Claim**：①「手機上跑得出證據驅動解釋」首次有證據；②`topk` 可轉換；
  ③四模型部署成本首次量化，含已量測的 fp16 緩解路徑。
- **Non-claim**：**未做延遲量測**（ms/張，四階段串接端到端為待辦）；
  **未做 769 張全鏈路一致性驗證**（2026-08-22 對三模型做過，evidence head
  納入正式 release 前應比照辦理）；未套用 int8；未動 production／
  `pipeline.py`／任何 checkpoint／無 git；**不裁定 ≤25MB 門檻的原始範圍
  是否應含 evidence head 與 artifact classifier**（三模型時已標記同一問題，
  本輪僅把數字更新為四模型，仍待 reviewer 裁定）。
- **執行註記**：首次執行 G1 假性失敗，實為 Windows cp950 主控台無法輸出
  `torch.onnx` 的 ✅ 字元（`UnicodeEncodeError`），**非匯出失敗**；
  以 `PYTHONIOENCODING=utf-8` 重跑後四關全過。記錄以免日後誤判為模型問題。
- **產出物**：`export_evidence_head.py`（單一腳本兩變體，G1-G4 協定沿用
  `export_mobile_tflite.py`/`export_artifact_v6.py` 未變更）、
  `export_report.json`、`evidence_head_{full,patch}.tflite`、
  `_sm_{full,patch}/`（含 fp16）、`FINDINGS.md`。

---

## FIX-TRIPLET-V2-20260902: 假圖側後處理腿＋身分輔助監督 — `fix_triplet_v2_20260902`，**兩 arm 皆 REJECT；跨語料幅度確立為四機制證據鏈的結構性限制，修法線收線**

- **設計**：承 `FIX-TRIPLET-POSTPROC`。Arm A `fakeleg`＝假圖側加後處理/濾鏡腿（「被壓縮/
  美化的假圖仍是假」，目標 stress 差 0.22pp）；Arm B `idaux`＝ArcFace 身分距離當訓練期
  輔助迴歸（masked loss，目標跨語料幅度；資料共用 `R1R13-IDENTITY`，含 4,901 列
  Celeb-real identity-swap 配對）。各 2 seed，對照＝前輪 TRIPLET checkpoints（不重訓）。
- **Arm A：REJECT**——stress 4.33/3.93 vs 對照 3.98/4.28，落在雜訊內無效應；**R12 閉合
  兩 seed 跌破 0.885 下限（0.878/0.871）**，白補付小代價。
- **Arm B：REJECT**——TT 幅度中位數 0.0074/0.0021（門檻 0.10）完全不動；aux 確實有訓練
  （30,149/44,341 列，loss 0.003）。唯一正面：R12 守住（0.906/0.900）、TT fake recall
  99.26%（本線最高）⇒「無害但無益」。
- **🔬 結構性結論**：跨語料幅度已被四種互異機制攻擊皆敗——配對 CE／pairwise margin／
  三元組負樣本／身分輔助監督。**升級為有四輪證據鏈的結構性限制**，論文可寫
  "attacked with four independent mechanisms"。**修法線正式收線。**
- **系統性現象**：兩 arm 的 seed 2 反向率皆 44-45%（前輪 48%），方向穩定性在 seed 2
  上系統性地差；`FIX-PWMARGIN` 的 4.0% 仍為最佳。
- **執行史（誠實）**：agent 兩度撞 session 限制。①seed 2 fakeleg 訓練 epoch 7 被殺、
  checkpoint 未存，下游評測全為 `checkpoint not found` stub——覆核查出，改名
  `STALE_INVALID_*`；②`compute_identity_targets.py` 被連坐殺（BrokenPipe），第一版 Arm B
  全部 `idtarget=-1`、aux=nan，**根本沒發生**——覆核查出，v3 重跑完成；③恢復 agent 自揭
  誤啟三份重複訓練，已清，無一達 checkpoint。FINDINGS 由覆核者從 JSON 重算撰寫。
- **⚠️ 污染警告**：Arm B 訓練含 Celeb-real 衍生影像；2026-09-03 取得的 Celeb-DF-B `real/`
  與 Celeb-real 逐位元組相同 ⇒ **Arm B 兩枚 checkpoint 在 Celeb-DF-B 上已污染，不得評測
  或引用**。
- **Non-claim**：不可促升（全 stress FAIL）；combined arm 依規則未跑；未動 production／
  無 git／未讀 LOCKBOX；Alibaba CONTAMINATED。
- **產出物**：`results/research/fix_triplet_v2_20260902/`（PRE_DECLARED、4 支腳本、各
  arm×seed 四類 JSON、identity_targets.tsv、STALE_INVALID_* 稽核 stub、FINDINGS.md）；
  checkpoints 4 枚。

---

## CELEBDFB-EXTERNAL-20260903: Celeb-DF-B 第三方美顏基準（Libourel et al. IWBF 2024）— `celebdfb_external_20260903`，**安全性 headline PARTIAL：2.80% 不能原樣外推；一種 grain 型預設（hawaii_grain）擊穿 Layer1；filter 類在此材料上從不觸發**

- **資料**：作者提供（2026-09-03，**必引用**），6 資料夾 × 232 影片 paired by id，1,393/1,393
  逐檔驗證。**只評 production v8.17**（SHA256 L1 `e3057270…`／L2 `8470ad52…`／artifact
  `56b4e399…`）；研究候選全部含 Celeb 衍生列，一律排除。
- **污染事實（PRE_DECLARED 事前寫死，`overlap_audit.json`）**：`real/`＝Celeb-DF-v2 Celeb-real
  逐位元組相同（非新資料）；**58/58 身分、232/232 real 影片 stem 皆出現在 Layer2 split
  （14,062 列 DF40-cdf／mined）與 Layer1 base split**；僅 44 real／11 syn 在 Celeb-DF-v2
  官方 test list。**不可宣稱身分互斥／OOD real**；未見的只有 4 種濾鏡預設、壓縮處理、
  Celeb-synthesis 原生換臉。
- **畫布混淆（`frame_count_audit.json`＋`_inspect/`）**：464/464 三胞胎幀數一致；treated
  變體為 9:16 letterbox、內容同像素尺度（臉區 156×119==156×119，NCC≥0.996），僅 16+16
  小影片輕度放大 1.07–1.13×。以 RES-MATCHED（主）／RAW 雙臂評分＋壓縮組當畫布對照；
  **所有格子雙臂判定一致**⇒解析度非驅動因素。協定：5 幀/影片、YuNet 0.7/pad 0.2、
  production 路徑 `preprocess_jpeg(85)→has_face→decide@0.5→classify_artifact`，
  video-cluster bootstrap CI。
- **A 安全性（headline）：PARTIAL（10–30% 帶）**——beautified deepfake 幀不判 fake
  **23.47%（272/1,159）[19.50, 27.61]**（RAW 20.88%），未處理基線 9.66%（fake recall
  僅 90.34%，未見換臉法）⇒ 美顏可歸因增量 **+13.8pp 幀／+16.4pp 影片**，為 in-house
  2.80% 的 5–7 倍；仍遠低於 Saeed et al. ≈64.6%。**逐預設：`hawaii_grain` 57.59%　⟵ ⚠️ **2026-09-05 撤回**：跨協定比較無效。同協定對照（`EXTERNAL-BASELINES-20260905`）11 個公開偵測器在同一批 Celeb-DF-B 影格、recall 對齊 90.4% 下 beautified ASR 為 6–21%，**低於 ours 的 23.4%**；且 ours 對 untreated Celeb-DF 換臉 AUROC 僅 0.521、把 87.7% 真影格叫 fake，此母體上的 ASR 不具濾鏡強健含義。
  [48.6, 66.6]（36/58 影片，Δp_manip −0.268）為災難級；brown 12.1／california_dreamin
  13.8／relax_you_pretty 10.4% 近中性（條件翻轉 6.5–8.4%，後兩者 Δ CI 含 0）。**
  每一個逃逸都去 `real`，**零** `filter`。
- **B 第三方濾鏡偵測：SCOPE FINDING（事前規則），且更糟**——real vs real_beautified
  `filter` 率 0.0→0.0%，AUROC(p_filter) **0.361 [0.339, 0.383]**（反向）；beautified real
  被判 `real` 12.3→26.0%（hawaii 12.4→65.9%）。**美顏讓影像看起來「更真」，不是「filter」。**
  偏移為內容無關：Δp_manip real −0.0715 vs fake −0.0703；real-vs-fake AUROC 任何處理下
  不變（0.521/0.524/0.522）——**Libourel et al. 的「分數向 real 偏移≈0.07」在 production 上
  精確復現**。
- **C 壓縮對照（R12 第三方版）：可分辨，但方向錯**——壓縮 Δp_manip **+0.046**（real
  recall 12.3→6.1%、synthesis not-fake 9.66→**4.31%**），美顏 −0.0715；差 −0.118
  [−0.136, −0.100]，AUROC(Δ) 0.284。壓縮→更「被操弄」、美顏→更「真」、兩者皆不→filter。
  壓縮 Δ 符號相反⇒畫布/重編碼不是美顏效應的來源。
- **D 協定一致性：PASS**——AUROC 0.521 [0.483, 0.559]、real 12.35% [9.84, 15.11]、fake
  90.34% [88.00, 92.57] vs 已發布 0.568／14.5%／96.0%（fake 低 5.7pp：不同 232 支合成
  影片，僅 8 支共用）。1,015/1,015 real 錯誤全去 `fake`。
- **E**：`has_face` 12 格全 0.00% 掉幀；artifact classifier 從未被呼叫（0 filter 標籤），
  eye_enlarging attractor 在此不可測。
- **🔬 機制發現**：①**Layer2「無 real 類」缺陷的錯誤流向依語料而異**——True Test real
  69/69→filter，Celeb-DF 幀 1,015/1,015→fake；此材料上 filter 類永不觸發。②（事後、
  未驗證、不宣稱）`hawaii_grain` 是唯一增加高頻能量的預設（Laplacian 變異比 1.27 vs
  ≤1.11；壓縮 ≈0.95）——加入的顆粒很可能被 SBI 訓練的 Layer1＋FFT 分支讀成「相機真實感」，
  需消融輪驗證。
- **論文可寫**：安全性框架須收窄為「本專案濾鏡庫＋Celeb-DF-B 四預設中三個；grain 型
  濾鏡可擊穿」；in-house 2.80% 不得單獨作為外部安全性主張；Libourel 偏移量在 production
  上復現可作跨系統一致性證據。**不可寫**：OOD／身分互斥；filter 類跨家族轉移；
  hawaii_grain 機制（未消融）。
- **產出物**：`results/research/celebdfb_external_20260903/`（PRE_DECLARED、FINDINGS、
  `perframe_*.tsv` 13,901 列、`crop_manifest.tsv`、`extract_log.json`、`summary_*.json`、
  `tables_*.md`、`supplementary_auroc_per_treatment.json`、`overlap_audit.json`、
  `frame_count_audit.json`、`_inspect/`、5 支腳本；`frames/` ≈0.2 GB）。純推論、未動
  production／split／git、未讀 LOCKBOX、Celeb-DF-B 僅評測。**覆核**：A/B/C/D 與逐預設
  數字由覆核者從逐幀 TSV 獨立重算，逐位吻合；唯一 1 筆 filter 標籤位於 RAW 臂
  （`id37_id4_0000` f50），agent 「零 filter」指 RES-MATCHED 臂，不影響結論。

---

## GRAIN-ABLATION-20260903: 顆粒注入消融——H1（合成顆粒讀成相機真實感）NOT CONFIRMED，但揭露分支拉鋸與跨域脆弱性 — `grain_ablation_20260903`

- **背景**：`CELEBDFB-EXTERNAL-20260903` 事後觀察 `hawaii_grain`（beautified deepfake
  逃逸率 57.6%）是唯一增加高頻能量的預設（Laplacian 比 1.27），假設 H1＝合成顆粒被
  SBI-Layer1＋FFT 分支讀成「相機真實感」。本輪受控消融驗證，TT fake/real（270/250）＋
  AIGuard/unseen（287）× 16 種處理（顆粒 5 劑量、film-grain 3 劑量、銳化 5 強度、
  模糊 2 強度、JPEG q40 對照），14,527 列逐圖。**執行 agent 撞自己 API 限流死亡，但
  評分＋analyze.py 已跑完（僅最後 console print 因 Windows cp950 崩潰，檔案完整），
  FINDINGS 由覆核者直接讀取完整輸出撰寫。**
- **主判定：NOT CONFIRMED**——比對 Celeb-DF-B 劑量的 `grain_g4`（Laplacian 比 1.67，
  最接近 1.27）在 TT fake 上中位數 Δp_manip 僅 −0.0019、逃逸率 +2.59pp
  [0.00, +5.19]，遠低於事前門檻（≤−0.05 且 CI 排除 0）。**單純合成顆粒不能在
  in-domain 完整復現 hawaii_grain 的 57.6% 逃逸。**
- **🔬 但揭露三個比主假設更值得寫的發現**：①**跨域假圖（AIGuard/unseen）中劑量
  顆粒效應真實顯著**——`grain_g8` 逃逸率 6.27%→21.60%（**+15.33pp
  [+10.80, +20.21]**，CI 明確排除 0），同劑量 TT fake 只有 +2.22pp（CI 含 0）——
  同一處理對「訓練沒見過的假圖生成方式」殺傷力遠大於 in-domain，這是真實安全隱患。
  ②**TT real 上方向與 Celeb-DF-B 相反**：`grain_g8` real recall 57.6%→37.6%
  （−20.00pp，讓真照片更像操弄）、`grain_g16` 更降到 8.4%——推翻「加顆粒＝內容
  無關向 real 偏移」的簡單敘事，hawaii_grain 真正機制可能非純顆粒（同時含色調
  分級/銳化等）。③**銳化在高劑量復現 Celeb-DF-B 模式更乾淨、更劇烈**：
  `sharpen_p300` 在 unseen_fake 上逃逸率衝到 **+56.10pp**、TT real recall
  57.6%→90.0%（真假皆偏向 real，與 Celeb-DF-B 內容無關偏移模式一致），可能才是
  更接近真正機制的候選。
- **🔬 機制發現（推翻 PRE_DECLARED 原假設方向）——元兇是空間分支，不是 FFT 分支**：
  逐分支探針（zero-FFT＝純空間分支決策、zero-spatial＝純 FFT 分支決策）顯示
  **純空間分支隨顆粒劑量單調推向「更像操弄」**（TT real `grain_g16` zero-FFT
  Δp_manip **+0.4728**），**純 FFT 分支則推向「更真」**（同劑量 zero-spatial
  Δp_manip −0.1911，方向相反）。FFT 分支在此扮演煞車而非漏洞，觀察到的整體行為
  是兩分支拉鋸淨結果。**修正論文中任何「頻域分支＝雜訊漏洞」的機制敘述方向。**
- **劑量-反應非單調**：TT fake 上 g2→g16 中位數 Δ 依序 −0.0046/−0.0019/−0.0084/
  **+0.0111（翻正）**/−0.0184，中劑量出現不穩定方向翻轉，需誠實呈現非套用乾淨曲線。
- **Claim**：①H1 NOT CONFIRMED（in-domain）；②跨域效應真實顯著，獨立安全發現；
  ③銳化可能是更接近 hawaii_grain 機制的候選；④空間分支（非 FFT）驅動偏移方向，
  修正原假設；⑤劑量-反應非單調需誠實記載。
- **Non-claim**：不宣稱完整復現 hawaii_grain 機制（真照片方向相反）；不宣稱 FFT
  分支是漏洞（探針顯示相反）；不可促升／未改 pipeline.py／未訓練／無 git／未讀
  LOCKBOX；TT fake/real、AIGuard/unseen 純讀取量測不影響其 held-out 地位。
- **產出物**：`results/research/grain_ablation_20260903/`（PRE_DECLARED、
  `calibrate_laplacian.py`+`calibration_laplacian.json`、`treatments.py`、
  `score.py`、`analyze.py`、`perimage_*.tsv` 14,527 列、`summary.json`、
  `tables.md`、`provenance.json`、FINDINGS.md）。

---

## GRAIN-ROBUST-FIX-20260903: Layer1 顆粒/銳化強健性增強 — `fix_grain_robust_20260903`，**in-house BUILD／外部 PARTIAL／stress 硬閘 FAIL，不可促升但機制修復已驗證**

- **背景**：`GRAIN-ABLATION-20260903` 診斷出 Layer1 對顆粒/銳化的脆弱性由空間分支
  （非 FFT 分支）驅動。本輪修法：把顆粒/銳化當強健性增強加進 Layer1 訓練（「加了
  雜訊的假圖仍是假、加了雜訊的真圖仍是真」），底圖用既有 AIGuard-real/fake 訓練來源
  （避開 AIGuard/unseen、Celeb-DF-B、True Test、LOCKBOX），warm start v817sbi，2 seed。
- **⚠️ 覆核時發現異常並已排除為 bug**：兩 seed 的離散指標（stress/TT filter/TT fake/
  CelebA）逐位元組相同，但 checkpoint md5 不同、連續分數（median Δp_manip、unseen
  AUROC）確有微小差異——**已驗證為兩個真正獨立訓練的模型在小型固定母體上湊巧產生
  相同離散分類結果**（整數計數對得上：111/2289、233/249、2993/3000），非重複訓練
  假象。
- **Primary A（in-house，AIGuard/unseen）：BUILD**——grain_g8 逃逸率變化從 production
  的 +15.33pp 修正到 **−8.36% [−12.20,−4.88]**（矯枉過正，方向已翻轉）；sharpen_p200
  從 +44.60pp 修正到 **+1.74pp [−2.09,+5.57]**（CI 含 0，效應已中和）。兩 seed 數字
  完全一致（已排除為 bug，見上）。
- **Primary B（外部，Celeb-DF-B hawaii_grain，依規則只查一次不迭代）：PARTIAL**——
  逃逸率 57.59% [48.6,66.6] → **54.14% [44.83,63.10]**，新舊 CI 大幅重疊 ⇒ **in-house
  修復不轉移到外部現象**，與 `GRAIN-ABLATION-20260903` 已預告的「真照片方向相反」
  發現一致（顆粒不是 hawaii_grain 的完整機制）。
- **硬閘：5/6 過，1 FAIL**——TT filter 93.57%／TT fake 98.89%／CelebA 99.77%／
  StyleGAN2 去污染 98.50%／unseen AUROC 0.8367-0.8368 皆過；**`fake_filter_stress`
  4.85% FAIL**（門檻 3.76%，production 2.80%），集中在 whitening_medium
  （15.68%）、eye_enlarging（11.89%）、face_reshaping（10.14%）——強健性增強
  意外傷到既有的 filter-vs-fake 邊界。
- **分支探針確認機制修復真實**：空間分支的 swap 分量從 −0.043 翻正到 +0.015，
  FFT 分支不變——診斷出的「空間分支驅動脆弱性」確實被本輪的增強資料矯正。
- **Claim**：①顆粒/銳化強健性增強對 in-house 診斷出的脆弱性有效（機制級證據，
  分支探針證實）；②外部驗證不轉移（Celeb-DF-B PARTIAL，CI 重疊）；③強健性增強
  有代價，傷到 stress 閘門。
- **Non-claim**：**不可促升**（stress 硬閘 FAIL，依 PRE_DECLARED 規則無論 A/B 判定
  如何皆不合格）；不可宣稱外部安全性改善；未動 production／`pipeline.py`／無 git／
  未讀 LOCKBOX／Celeb-DF-B 僅評測一次未迭代。
- **產出物**：`results/research/fix_grain_robust_20260903/`（PRE_DECLARED、
  `build_grain_robust_split.py`、`train_layer1_grain_robust.py`、
  `eval_grain_primaryA.py`、`eval_celebdfb_primaryB.py`、`eval_branch_probe.py`、
  `eval_gates.py`、各 seed 的 gates／primaryA／primaryB／branch_probe JSON、
  `perimage_primaryA_*.tsv`、FINDINGS.md）；checkpoints 2 枚
  （md5 `df26f1ef...`／`5219f88a...`，證實非重複訓練）。
- **覆核**：Primary A/B、硬閘、逐條件退化、seed 一致性異常，均由覆核者直接從
  JSON 獨立重算核對，逐位吻合，並額外驗證了 seed 「異常一致」現象為真實而非 bug
  （整數計數校驗＋checkpoint md5 差異＋連續分數差異三項交叉確認）。

---

## ARTIFACT-NONFILTER-20260903: artifact_classifier 加第五類「非可辨識濾鏡」— `fix_artifact_nonfilter_20260903`，**PARTIAL：JPEG 幾乎修好、resize 幾乎沒動、代價是 Alibaba 更多不答**

- **背景**：`filter_vs_postprocess_20260901` 診斷出一般後處理被 Layer2 誤判 filter 後，
  4-way artifact_classifier 不會說「不知道」，而是自信貼上具體錯誤型別（sharpen/JPEG
  九成以上被貼 eye_enlarging）；`fix_abstention_ood_20260902` 已窮盡十種方法證明
  事後信心門檻修不好（oracle 天花板 0.666）。本輪走全新軸線：**給分類器一個真正的
  第五類**（`none_postproc`），而非再修門檻。5-way，warm start v6，2 seed，第五類資料
  取自既有訓練來源 AIGuard/real＋celeba_train（非新污染來源）。
- **Primary A（pooled）：PARTIAL**——41.08% [38.34,43.81] / 45.50% [42.77,48.23]。
  **但 pooled 數字掩蓋了真正的故事，逐條件差異巨大**：JPEG q40/q60 幾乎修好
  （**92.7%／86.7%** 正確路由到 none_postproc，seed2 更高達 98.0%），**resize
  round-trip 幾乎沒動**（僅 2.8%／3.2%，跟修復前的 0% 幾乎沒差，attractor 型態
  不變：whitening/eye_enlarging/face_reshaping 分散）、sharpen（9-14%）與 blur
  （14-21%）僅部分修復。
- **Primary B（4 類存活）：WITHIN TOLERANCE**——兩 seed 最大退步僅 **1.15pp**
  （遠低於 5pp 門檻），已知類別測試影像被誤導向 none_postproc 的比例 ≤0.43%，
  **無「傾倒桶」效應**。True Test 逐型別在此輪一致量測下持平或改善。
- **⚠️ Non-regression 量測差異需誠實記載**：本輪自測 v6 eye_enlarging 為 90.3%，
  與 `COMPLETEFIX_FINDINGS.md` 記載的 72.6% 不同——原因是 loader 不同（本輪未套用
  `ARTIFACT_UNKNOWN_THRESHOLD` 棄權閘門）。**candidate-vs-v6 在本輪內部是同一套
  loader、逐位可比；但不可拿本輪的 v6 數字去對比歷史文件的 v6 數字。**
- **次要（Alibaba 跨演算法）：新代價，非自動的勝利**——四種型別的真實跨廠牌濾鏡有
  39-66% 被貼上 `none_postproc`；eye_enlarging 正確率 83.8%→48-50%，
  whitening/smoothing 已經很弱又再掉；face_reshaping（已在地板 6.1%）大致不變。
  **兩種讀法皆合理，本輪不裁定哪個該優先**：①更誠實的「不認識」取代捏造的具體
  誤判 ②在唯一已知困難母體上的直接 recall 損失。
- **Claim**：①第五類機制對 JPEG 重壓縮近乎完全修復，成本可忽略（≤1.15pp）；
  ②resize round-trip 的 attractor 型態本質上未被觸動；③本輪首次量化「給分類器
  拒答選項」在跨演算法母體上的真實代價，需要後續決策。
- **Non-claim**：不可宣稱整體修復（resize 幾乎沒動）；不可宣稱 Alibaba 是淨改善
  （recall 損失是真實代價，非自動的優點）；未動 production／`pipeline.py`／無
  git／未讀 LOCKBOX／未用 Celeb-DF-B 資料；GPU 與 `GRAIN-ROBUST-FIX-20260903`
  正確序列化（等待對方 seed b 跑完才啟動自己的 seed 2，已查證）。
- **產出物**：`results/research/fix_artifact_nonfilter_20260903/`（PRE_DECLARED、
  `generate_none_postproc.py`＋`filter_data/none_postproc/`12,000 張、
  `train_artifact_v7_5way.py`、`_common5way.py`、3 支 eval 腳本、各 seed 的
  primary_a/b、secondary_nonregression JSON、`transform_assertions.json`）；
  checkpoints 2 枚（`artifact_classifier_v7_5way_seed{1,2}.pth`）。**FINDINGS 由
  agent 以文字回報（Write 工具拒絕子代理報告檔），內容已由覆核者逐項核對
  primary_a/b 與 secondary JSON，數字逐位吻合，本條目為覆核後版本。**

---

## P1A1-FFPP-ADVMINE-20260904: FF++ 資料 ＋ 對抗式 hard-neg 挖礦迴圈 — `p1a1_ffpp_advmine_20260904`，**P1-A1 未達成（stress 6.12% vs 2.80%），但推翻「安全性 vs 泛化是 Pareto 取捨」的假設，並把缺口精確定位到三個條件**

- **背景**：七輪修復全數死在 `fake_filter_stress` 同一閘門，其中 FF++ Stream 1b 的
  跨域 0.575→0.856 是真實成功卻被 stress 8.17% 否決。本輪測試從未試過的組合：
  **FF++ 資料（已證明的跨域槓桿）＋針對當下模型重新挖礦（本專案史上唯一有效的
  stress 槓桿，v8.3 誤判 50%→0%、v8.8 stress 1.35%）**。過去每輪只用其一，且用的
  都是拿舊模型挖的舊 hard-neg——對抗式挖礦的本質從未被執行。
- **Phase 1 復現 CONFIRMED**（事前門檻 FF++ ≥0.70 且 stress ≥5.0%）：recipe 由
  artifact 驗證非文件（`train_pcand_v2_layer1.py` 硬編 LR=2e-5，`--lr` 未接線）。
  FF++ frame AUROC 0.8082→**0.8113**、video 0.8555→**0.8600**、stress 8.170→7.907%。
- **軌跡（本輪主要交付物）**：

  | arm | hard-neg（佔 fake 類）| stress | Δ | FF++ frame AUROC |
  |---|---|---|---|---|
  | production v8.17 | 17,725（15.1%）| **2.80%** [1.92,3.76] | — | 0.5747 |
  | P1REPRO | 17,725 stale | 7.907% | — | 0.8113 |
  | ADV1（+33,236 挖） | 51,344（34.2%）| 6.378% | **−1.53pp** | 0.8154 |
  | ADV2_s1（+17,252）| 68,596（41.0%）| **6.116%** | −0.26pp | **0.8161** |
  | ADV2_s2（seed2）| 68,596 | 6.728% | — | 0.8144 |

- **🔬 發現一：Pareto 假設沿此軸被推翻**——挖礦讓 stress 單調下降 7.91→6.38→6.12%
  的**同時**，FF++ AUROC 單調上升 0.8113→0.8154→0.8161。**這是本專案第一次
  stress 改善而跨域不需付出代價**，跨域不是被交換掉的東西。
- **🔬 發現二：缺口精確定位到三個條件，其餘五個比 production 還好**（逐條件，
  各約 286 張）：smoothing×3＋combined×2 被壓到 **0.00%**（production 為
  0.00–0.35%）；殘餘全在 **face_reshaping 12.24／eye_enlarging 19.23／
  whitening_medium 16.03**（production 對應 5.24／7.69／9.76）。**把這三個
  條件還原到 production 自己的水準、同時保留本輪的五個 0.00%，總 stress
  ≈2.8%——整個 P1-A1 缺口就是這三個條件，沒有別的。**
- **🔬 發現三：失效是 Layer1 閘門現象，非 Layer2**——50,488 筆挖出的失敗中
  **50,417 筆（99.86%）是 Layer1 gate 誤判、僅 71 筆 Layer2 路由錯誤**，
  獨立再確認既有結論。
- **⚠️ 覆核時推翻該輪自己的「挖礦飽和」結論**：挖礦預算是**平均分配**
  （每條件各掃 ~25,000 張），但 `mining_stats_iter2.json` 顯示第二輪逐條件產出率
  差異巨大——eye_enlarging **26.3%**／whitening_medium **21.0%**／
  face_reshaping **13.6%**（仍是富礦），而 smoothing/combined 五條件已掉到
  **0.2–0.8%**（真正枯竭）。**「飽和」是合併統計的假象：五個沒東西可挖的條件
  持續消耗 5/8 的預算，卡住閘門的三個條件卻各只分到 1/8。這是資源配置錯誤，
  不是方法飽和。** 據此開 `p1a1_targeted_mine_20260904` 續攻。
- **Claim**：①FF++＋對抗式挖礦可同時改善跨域與 stress，安全性/泛化沿此軸非
  Pareto；②P1-A1 缺口完全定位於幾何形變（eye_enlarging／face_reshaping）
  與全域美白（whitening_medium）三條件；③stress 失效 99.86% 屬 Layer1 閘門。
- **Non-claim**：P1-A1 完成定義**未達成**（stress 6.12% vs ≤2.80%，差 3.3pp，
  遠超 production CI 寬度，非 CI 問題）；不可促升；未動 production／
  `pipeline.py`（最後修改 2026-09-01）／無 git／未讀 LOCKBOX；Alibaba
  CONTAMINATED-by-construction；Layer2 全程凍結（SHA256 `8470ad52…` 四次
  gate 執行逐位相同）。
- **執行事故（誠實記載於 `EXECUTION_NOTES.md`）**：①agent 誤把 trainer 自己的
  `val_loader` persistent workers 當成孤兒挖礦程序而殺掉第一次 P1REPRO，
  損失約 1 小時，重跑 epoch 1 逐位元組相同；文件已記錄兩種 worker 的辨別方法。
  ②兩次約 50 分鐘的環境層停滯（GPU 1%、無 python 程序但磁碟佇列飽和），
  其中一次差點誤丟已完成的執行——checkpoint 其實已在磁碟上。教訓：殺任何
  看似停滯的東西前先查產出物。
- **產出物**：`results/research/p1a1_ffpp_advmine_20260904/`（PRE_DECLARED、
  FINDINGS、EXECUTION_NOTES、6 支腳本、4 份 gates JSON、4 份 perimage JSON、
  mining/split stats、全部 log）；checkpoints 8 枚；
  `splits/research/p1a1_ffpp_advmine_20260904/`（4）；
  `fake_filter_advmine_20260904/`（50,488 張挖出的影像）。
- **覆核**：stress 軌跡、逐條件表、FF++ AUROC、挖礦逐條件產出率均由覆核者
  從 JSON 獨立重算核對，逐位吻合；並額外查出「挖礦飽和」結論為合併統計假象
  （見上），該更正為覆核新增，非 agent 原文。

---

## P1A1-TARGETED-MINE-20260904（進行中，中間發現已可引用）: 難度導向挖礦預算重配 — `p1a1_targeted_mine_20260904`，**診斷被改寫：stress 殘差主體不是濾鏡強健性，是基礎偵測失敗被重複計數八次**

- **背景**：`P1A1-FFPP-ADVMINE-20260904` 的「挖礦飽和」結論經覆核判定為合併統計
  假象（五個枯竭條件吃掉 5/8 預算，三個卡關條件各只分到 1/8）。本輪把 90%
  掃描預算集中到 eye_enlarging／face_reshaping／whitening_medium。
- **配置重分配已驗證有效**：iter3 掃 199,900 對，產出 17,039 筆新 hard-neg，
  **99.3% 落在三個目標條件**；三條件產出率 **10.13–21.90%**，遠高於 ~5% 的
  飽和門檻——**確認前輪「飽和」為假象**。
- **🔬 機制發現一：效應大小「反向」預測失敗**——最暴力的處理錯誤率最低
  （combined_heavy 擾動 MAD 33.2 → **0.00%**；smoothing_heavy MAD 5.8 → 0.00%），
  最溫和的錯誤率最高（**eye_enlarging MAD 1.16（八條件最小）→ 19.23%**）；
  且同一條件內失敗圖的擾動量**比通過圖更小**（eye 1.16 vs 1.23、reshape 4.07
  vs 4.43）。⇒ **「幾何重採樣破壞高頻生成痕跡」假設被證偽**。
- **🔬 機制發現二（本輪核心，改寫診斷）：殘差主體是基礎偵測失敗，非濾鏡失敗**
  （`mechanism_ADV2_s1_last.json`，覆核者獨立重算確認）：
  - 287 張 stress 源圖中 **24 張未加任何濾鏡即被判 `real`**（base_images:
    263 fake／24 real／0 filter，mean base p_manip 0.7815）
  - 失敗列 base p_manip 中位數 **0.5475** vs 通過列 **0.8653**
  - 失敗高度非獨立：**69 張源圖承載全部困難條件失敗**（獨立假設下應為 116.2），
    其中 **20 張三條件全錯**
  - **20 張全錯者中 14 張本身就是基礎偵測失敗**（base 判 real），僅 6 張是
    真正被濾鏡翻掉；全錯集合 base p_manip 中位數僅 **0.3443**（覆核值 0.3443／
    base-real 集 0.2814）——**不是在 0.5 邊界搖擺，是深在錯誤側**
  - **算術後果**：287 源 × 8 條件下，一張基礎判錯的圖最多被計 8 次錯誤；
    **光是那 24 張即足以解釋 ADV2_s1 的全部 140 筆錯誤**，且無任何複合濾鏡
    hard-neg 能修。⇒ **stress 指標的設計會把單一基礎失敗放大八倍計數，
    此性質本身值得寫進論文的指標設計討論**。
- **🔬 機制發現三：挖礦對此閘門已無用武之地（生成器層級錯配）**——iter3 逐生成器
  產出率（eye_enlarging）：FF++ NeuralTextures **54.81%**／Face2Face 44.26%／
  FaceSwap 38.46%／Deepfakes 22.15%，但 **AIGuard-fake 僅 0.66%**、DF40 五種
  0.08–0.85%。**stress 閘門在 AIGuard/unseen 上評測，而 AIGuard 家族礦源已真正
  枯竭；90%+ 的新礦來自閘門從不測試的 FF++ 家族。⇒ 再挖也救不了此閘門**，
  此為事前可證偽的預測，由 TGT1 閘門表直接檢驗。
- **⚠️ 尚未解決的歸因問題（agent 自行標註，覆核者認可並保留）**：v8.17 與本候選
  **同時**差在訓練資料（無 FF++）與 hard-neg 池，故 2.80% vs 6.12% **不足以**
  把脆弱核心歸因於 FF++。已排定同一份 base-image 探針跑 **v8.17／P1REPRO／
  TGT1** 三方對照，**由測量結果決定措辭**，不預先承諾干擾敘事。
- **Non-claim（現階段）**：本條目為進行中輪次的中間發現；TGT1/TGT2 閘門、
  停止規則判定、雙 seed 尚未完成，**不得引用任何最終判定**。未動 production／
  `pipeline.py`／無 git／未讀 LOCKBOX；Layer2 byte-frozen；污染斷言 PASS
  （387,238 列，0 列來自 AIGuard/unseen、True Test 精確路徑、celeba_test、
  stylegan2_test、celebdfb、shadow_*、LOCKBOX、FF++ 官方 test）。
  繼承前輪註記：34 筆 basename 巧合為不同生成器的同一 DF40 幀（0 精確路徑重疊），
  原樣保留未增未刪；另發現前輪 50,488 列中有 5,488 列為同一 (source, condition)
  在 iter1/iter2 重複寫入，本輪原樣保留以維持與 ADV2_s1 的乾淨延續性，
  僅對自身新寫入去重。
- **覆核**：三個機制發現的關鍵數字（base_images 分佈、失敗/通過 base p_manip
  中位數、69/116.2 共失效統計、24/20/14 重疊、逐生成器產出率）均由覆核者從
  `mechanism_ADV2_s1_last.json` 與 `mining_stats_iter3.json` 獨立重算，逐位吻合。

### 🔴 TGT1 結果（2026-09-04，覆核者獨立重算，逐位吻合）：**事前預測命中，針對性挖礦無效——且配置錯誤被證明不是瓶頸**

- **stress 6.728%**（ADV2_s1 為 6.116%，**上升 0.61pp**）。關鍵：**0.61pp 正好等於
  已知的 seed 間差距**（ADV2 兩 seed 為 6.116／6.728，同樣 0.61pp）⇒ 誠實讀法是
  **雜訊範圍內無可偵測變化**。FF++ frame AUROC 0.8120（e2e）／video 0.8577，
  與 ADV2_s1 的 0.8161／0.8627 持平。
- **這是一個乾淨的否證**：維持配額（僅 10% 預算）成功守住四個已解決條件的
  **0.00%**，三個卡關條件預算翻三倍卻**買到零改善**。⇒ **配置錯誤真實存在、
  修好它卻毫無效果，證明配置從來不是瓶頸。**
- 逐條件（v8.17／P1REPRO／ADV2_s1／TGT1）：eye_enlarging 7.69／22.03／19.23／
  **20.98**；whitening_medium 9.76／20.56／16.03／**17.42**；face_reshaping
  4.55／17.48／12.24／**13.64**；四個已解決條件 TGT1 全為 **0.00**。
- 六個 Freeze Gate 全過（True Test filter 92.37／fake 97.78／CelebA 99.20／
  StyleGAN2 去污染 99.13／unseen AUROC 0.8225），**True Test real recall
  +5.2pp 至 72.69**；唯一未過為 `fake_filter_stress`。

### 🔬 三方對照（item (a)）：**脆弱核心由 FF++ 資料造成，任務干擾被直接量到**

| 模型 | 未加濾鏡即誤判為 real | 平均 base p_manip | 三條件全錯源圖 |
|---|---|---|---|
| **production v8.17（無 FF++）** | **9** / 287 | **0.8390** | 8 |
| **P1REPRO（＋FF++ dense frames）** | **29** / 287 | 0.7877 | 34 |
| ADV2_s1（＋兩輪均勻挖礦） | 24 | 0.7815 | 20 |
| **TGT1（＋針對性挖礦）** | **29** | **0.7478** | 23 |

（覆核者從四份 `mechanism_*.json` 獨立重算：9/29/24/29 與 0.8390/0.7877/
0.7815/0.7478 逐位吻合。）

- **脆弱核心在加入 FF++ 的瞬間從 9 張暴增到 29 張**（×3.2）；挖礦最多討回 5 張，
  針對性挖礦全數吐回。
- **平均 base 信心隨挖礦量單調衰減** 0.8390→0.7877→0.7815→**0.7478**，
  **即使每一筆挖入的資料都標記為 manipulated** ⇒ 這是 AIGuard 家族決策邊界
  受到的**任務干擾（task interference）被直接量測**，非濾鏡強健性問題，
  且複合濾鏡 hard-neg 依定義無法修復。
- **歸因問題就此解決**：先前保留的「FF++ 造成 vs 本來就在」，由 v8.17（9 張）
  vs P1REPRO（29 張）的對照決定——**是 FF++ 造成的**。此對照為本輪最強證據。
- **下一個槓桿因此明確**：排練比例（每批保留多少原始 AIGuard-fake）、
  往 v8.17 權重正則化（EWC 類）、或雙家族分頭/專家路由——**皆非「挖更多複合樣本」**。
- **執行誠信**：agent 主動更正自身兩項錯誤——①「24 張可解釋 100–190 筆錯誤」
  的上界估計不成立（假設每個濾鏡變體皆失敗，資料反駁），改以逐源精確歸因；
  ②summarize 腳本誤讀不存在的 `ffpp_test_auroc` key 導致 FF++ 印為 None
  （正確 key 為 `ffpp_official_test_frame.auroc_end2end` 與
  `ffpp_official_test_video.auroc`），已修正，故首次回報為空白而非錯誤數字。
- **仍在執行**：iter4 挖礦 → TGT2 雙 seed → 停止規則判定 → FINDINGS.md。
  agent 選擇在 TGT1 已明顯失敗下仍跑第二 seed，理由為「TGT1 的表面變動恰等於
  已知 seed 差距，兩 seed 才能把『針對性挖礦無效』從印象變成量測」——判斷正確。

### 🏁 最終判定（2026-09-04，TGT2 雙 seed + iter4，覆核者從磁碟撰寫 FINDINGS）：**停止規則觸發，P1-A1 未達成，但診斷完整、下一槓桿明確**

- **stress 軌跡收斂到雜訊帶**：ADV2_s1 6.116→TGT1 6.728→TGT2_s1 6.684→
  **TGT2_s2 5.898**，四點落在 5.9–6.7% 帶內無單調改善方向，與已知 seed 間
  差距（0.61pp）同量級 ⇒ **事前預測「再挖礦救不了此閘門」被雙 seed 乾淨證實**。
- **iter4 提供決定性飽和訊號**：掃描 199,898 對找到 25,803 個「困難」樣本，
  **96.5%（24,902 個）是 iter3 已挖過的重複**，僅 901 個真正新樣本；
  AIGuard-fake 逐生成器產出率持續 0.4-1.0%（真正枯竭），FF++ 家族仍
  7.7-49.9%（閘門不測）。**此為直接飽和訊號，非合併統計假象**（與前輪
  「均勻分配掩蓋飽和」性質不同——這次真的挖乾）。
- **脆弱核心軌跡擴充至五點，趨勢一致**：v8.17（9/287,0.8390）→P1REPRO
  （29,0.7877）→ADV2_s1（24,0.7815）→TGT1（29,0.7478）→**TGT2_s1（35,0.7432）**
  ——脆弱核心單調擴大、平均基礎信心單調下降，貫穿整條挖礦軌跡，任務干擾
  診斷進一步坐實。
- **P1-A1 完成定義：未達成**——FF++ 門檻穩定達成（兩 seed 皆 0.8129/0.8132，
  遠超 ≥0.75）證明跨域偵測架構可行性，但 stress 差距 3.1-3.9pp 遠超任何
  seed/CI 寬度，非邊緣未過。六個 Freeze Gate 全過。
- **Claim**：①預測命中（非失敗）；②iter4 重複率是比 stress 數字本身更直接
  的飽和證據；③脆弱核心軌跡五點一致無反轉，任務干擾非挖礦策略問題；
  ④FF++ 跨域可行性已由兩輪四個獨立 checkpoint 穩定證明。
- **Non-claim**：不可促升；不可宣稱挖礦策略執行有誤（配置重分配已驗證
  正確，問題在此路線天花板非執行）；未動 production／無 git／未讀 LOCKBOX。
- **下一步（由本輪直接推導，全新方向）**：不應再嘗試任何挖礦或資料量調整
  （四種策略已測、資訊耗盡）。應直接對抗任務干擾：**排練比例（rehearsal
  ratio）／EWC 類正則化／雙家族分頭路由**——三者皆為標準持續學習技術，
  且與已死亡的四個 Layer2 幅度修復機制、三個 Layer1 修復嘗試完全不同軸線。
- **執行註記**：agent 因磁碟 I/O 飽和未及寫出 FINDINGS.md（訓練與評測本身
  完整落地），本文件與上方軌跡數字由覆核者直接從 `gates_TGT2_s{1,2}_last.json`、
  `mechanism_*.json`（5 份）、`mining_stats_iter4.json` 獨立重算撰寫。

---

## FROMSCRATCH-AUDIT-20260904: 全專案方法論對抗式稽核（read-only，無訓練）— `results/research/fromscratch_audit_20260828/`，**五項方法論問題，其中兩項需要立即修改論文主張**

- **性質**：使用者委託的「從頭重審」稽核。純讀取＋對既有 per-image dump 的重新分解；
  未動 `pipeline.py`／checkpoint／split／既有 results，無 GPU、無 git。唯一新增檔案為
  `results/research/fromscratch_audit_20260828/stress_decomposition.json`。
  完整稽核內容由執行 agent 以文字回報（Write 工具拒絕子代理報告檔）。
- **讀取範圍**：`CLAUDE.md`／`MASTER_PLAN_20260826`／本登錄檔全 9,525 行／`phase1_story`／
  `phase2_story`／`limitations_framing`／`paper_outline`／`lit_check_20260904`／`TODO.md`
  Freeze-Gate 段／`remeasure_inventory_20260826/INVENTORY.md`／`pipeline.py`
  `hierarchical_predict()`／`splits/v811_layer{1,2}_*_train.txt` 逐列計數。

### 🔴 五項主要發現

1. **訓練資料含未被命名的標籤矛盾，四輪修法都沒動它**（新量測，`splits/v811_layer2_train.txt`
   逐列計數）：Layer2 `fake` 類 73,093 列中 **38,020 列（52.0%）是「套了美顏濾鏡的影像，
   標成 fake」**（`fake_filter_hard_neg` 17,725＋`v89d-mined` 15,750＋`round2-mined` 4,545）。
   全訓練集的濾鏡影像中 **34% 帶 `fake` 標籤**。⇒ 這是 `DESIGN-AUDIT-20260901` Probe 1
   「加濾鏡反而讓 `p_filter` 下降（AUROC 0.4755）」的**直接機械成因**，比「缺配對對照」
   更根本。`FIX-PAIRED-CONTRAST`／`FIX-PWMARGIN`／`FIX-TRIPLET-POSTPROC`／`FIX-TRIPLET-V2`
   各加入 4–8k 修正列對抗 38,020 列反向監督（約 1:5），且全部從 v811 暖啟動——
   **「跨語料幅度為結構性限制、四機制皆敗」不成立**，第五個（也是最明顯的）機制
   ——移除/重標/降權那 38,020 列——從未被測試。
2. **`fake_filter_stress` 指標三重不健全**：①**變換循環**——挖礦用的濾鏡函式與評測
   逐位元組同源（`filters/stress_test_filter_functions.py`），參數相同，故該指標量的是
   「對訓練過的八個變換的強健性」，外部未見濾鏡家族實測為 23.47%（5–7×）；
   ②**池化稀釋約 2.7×**——排除基礎偵測失敗後，8 條件中 **5 條件誤判率為 0.00%**，
   全部誤差集中於 whitening_medium 7.55%／eye_enlarging 5.76%／face_reshaping 3.24%，
   ⇒ **≤2% 門檻對條件集不變異，加入更多 smoothing 強度即可通過**；
   ③**26.6% 的誤差不是濾鏡造成的**（新量測）——production v8.17 的 64 筆誤差中
   **17 筆落在 9 張未加濾鏡即被判 `real` 的源圖上**；排除後濾鏡可歸因誤差為 **2.12%**，
   誤差集中在 **38/287（13.2%）源圖**。`P1A1-TARGETED-MINE-20260904` 對候選做過同樣分解，
   **從未對 production 做**——而 2.80% 正是論文 headline。
3. **v8.8→v8.11 架構決策的比較方法在 16 天後被本專案自己列為強制禁止，且從未重跑**：
   決策時（2026-08-02）Shadow real 16.2→75.5pp 的增益中，**+57.9pp 早已由 flat 3-class
   架構的資料改動達成（v8.10a = 74.1%）**，階層化的邊際貢獻僅 +1.4pp／−1.74pp，單一
   操作點、單 seed、未做 threshold-matched。Known trap #1 於 2026-08-18 才列為強制；
   `P1-6/P1-R8`（08-19）隨後證明該 trade-off 是**單一操作點**，且在同一張 frontier 表中
   **v8.11 是九個 arm 裡最差的 −11.83pp**。該數字從未被當成對現役架構的質疑討論過。
4. **目前沒有任何 headline 數字免於選型偏誤**：Freeze-Gate A 全部八項都是 promote/reject
   準則（`AIGuard-unseen AUROC ≥0.80` 曾實際否決候選），故 CelebA／StyleGAN2／Alibaba／
   unseen 皆為 dev 指標，`paper_outline` §5.3 的「乾淨跨域 headline」框架不成立；
   Ultimate lockbox 已被消耗；B-LFW 已被 ≥5 輪讀成 dev 指標；**Celeb-DF-B 於取得當日
   （2026-09-03）即被 `GRAIN-ROBUST-FIX-20260903` 用作 Primary B pass/fail 準則**——
   唯一的第三方儀器在 24 小時內開始被消耗，建議立即凍結。
   另：**base-image/video cluster 重抽已套用於 stress／Alibaba／Shadow-v2／影片語料，
   但未套用於 B-LFW（8 濾鏡/底圖）、FairBeauty、`ARTIFACT-NONFILTER` pooled（5 條件/底圖）**
   ——與已診斷兩次的過度精確缺陷同型。
5. **Gate 門檻從未被推導，且其中一項為了讓已上線版本通過而被調降**：全корpus 查無任何
   把 ≥95／≥90／≥80／≥0.80／≤2%／≤25MB 連結到部署需求、文獻或成本模型的文件；
   `TODO.md:744` 的理由是流程性的（「結束無限迭代」）。filter recall 門檻由 ≥92% 改為
   ≥90%，明載理由為「用 92% 會讓已上線版本回溯性不通過」——**條件於結果的門檻選擇**，
   與 `P2A1-EVIDENCEHEAD-R2` 拒絕 class-neutral baseline（「會開一個新的 researcher
   degree of freedom」）的裁定互相矛盾。兩項門檻本身在統計上從未成立
   （CI 跨線，`BENCHMARK_POWER_REPORT` §3.1 明言）。

### 其他角度的具體發現

- **輸出空間（Angle A）**：`hierarchical_predict()` 的 Layer2 為 2-way softmax，
  `p_fake`／`p_filter` 由構造互斥 ⇒ **本專案的 headline 威脅模型（同時是假的且被美化）
  在輸出空間中不可表達**（`P1-9` 已記載 joint recognition 對此架構「undefined」），
  `fake_filter_stress` 整個指標即是這個缺口的代理。**本專案自己 2026-09-04 的
  `lit_check_20260904.md` Q4 判定 single-label 4-class「在兩個方向上都是異類」，
  multi-label × ordinal level 是 RetouchingFFHQ／MoFRR 兩篇 peer-reviewed 前例的做法，
  且強度標籤（`four_process.txt`）本來就在磁碟上被丟棄**。專案曾建過 multi-label 版
  （dual-head Layer2：Cell A/C/D、v8.16、T600/T900），因 `P1-R8` 的**資料**實驗結果而
  棄用——該比較同時變動了資料與 head 結構，**從未隔離 head 結構本身**。
- **暖啟動混淆（Angle E）**：`P1A1-TARGETED-MINE` 的五點軌跡（base `p_manip`
  0.8390→0.7877→0.7815→0.7478→0.7432，**每一筆新增資料都標 manipulated**）是教科書式的
  catastrophic forgetting 曲線；連同 `ARCH1-RECIPE-GAP`（單變數：init 讓 Alibaba
  76.29→98.23，大於九輪中任何架構效應）與 `P1-PROTO1`，**init 是本專案最大的單一變異軸
  且從未被當成實驗因子控制**。受影響最深者為四輪 `FIX-*`（從自己要修的 checkpoint 暖啟動、
  且保留致病資料）與 v8.17 本身（**從未做第二 seed 複現**，卻是所有候選的比較基準）。
- **捷徑學習的處置（Angle F）**：DANN／de-correlation／SupCon／paired-contrast／SRM 確有
  嘗試（應給予肯定）；但 `docs/Paper 清單.md` 自己標 🔴🔴 的兩個**已發表移除法**
  ——**ED⁴/AdvSCM（IEEE TIP 2025，連實驗設計都已寫在該行）與 SpRAy/ClArC**——從未排程。
  連同 `lit_check` Q3 的判定（「應定位為既有現象的一個實例，非發現」），
  **MASTER_PLAN 的 novelty #1 目前強度不足**。
- **單 seed 低於雜訊底的結論（Angle G）**：已量測雜訊底為 True Test paired real 7.23pp／
  Shadow filter 5.73pp／stress 0.61–0.74pp／FF++ AUC ~1pp。仍在使用中的越界結論：
  **`ARCH1-PARTIAL` 的「stress 2.75% 為五 arm 最佳（含 production 2.80%）」＝0.05pp 差距**
  （MASTER_PLAN 據此稱其為最佳架構候選）；`ARCH1-SHALLOWWS` 三候選排序；
  `FIX-TRIPLET-POSTPROC` 的「三輪連續改善 5.33→4.67→3.98」（該輪自身兩 seed 為 4.28/3.98）；
  `FFPP-IMPROVE` 的 backbone 排序（R7 答覆倚賴之）。`EVAL-2` 的「主要候選至少 3 seed」
  待辦自 2026-08-26 未動，期間又跑了約 15 輪單 seed。
- **從未嘗試的標準技術（Angle H）**：multi-label/ordinal head、focal/cost-sensitive loss
  （目前安全性不對稱**只**由 ×15 過採樣編碼＝任務干擾的直接成因）、rehearsal/EWC、
  ensembling（40+ 互補 checkpoint＋int8 後僅 6.87MB 的預算空間）、大 teacher 蒸餾
  （論文定位正是「邊緣預算下的跨資料集 AUC」，而文獻 SOTA 皆為 CLIP-class）、
  目標域 SSL 預訓練、TTA 當精度槓桿、DCT/wavelet 頻域替代、patch 級分類＋直方圖池化
  （DAD-HCNN 做法，可同時解掉 evidence head 的 7×7 解析度天花板與 5.82MiB 體積）、
  curriculum/progressive（ProDet，已引未用）、SBI 之後的 blending 合成
  （BI/LAA-Net/FreqBlender，皆已引未用）、訓練期校準。

### 建議的優先動作（區分「可能推翻既有結論的便宜檢查」vs「新方向」）

- **Tier 1（數小時，無訓練）**：①採用本輪的 stress 分解改寫 headline（per-condition＋
  排除基礎失敗 2.12%＋源圖級 13.2%）；②**用封存的 v8.10a 做 threshold-matched 對照**
  ——單一最具決定性的未跑檢查，結果將決定論文核心架構主張成立與否；③把「修正列:矛盾列」
  比例補進四輪 FIX 條目；④B-LFW／FairBeauty／ARTIFACT-NONFILTER 的 cluster CI 重算；
  ⑤凍結 Celeb-DF-B 與 B-LFW 的使用狀態；⑥執行 `INVENTORY §D` 十項（自 08-26 未動，
  合計 <1 小時 GPU，其中三項直接影響 Freeze-Gate 表中的數字）。
- **Tier 2（1–3 次訓練）**：⑦**移除消融**（拿掉 38,020 列重訓 Layer2/Layer1）——無論
  結果為何都能終結「結構性限制」之爭；⑧v8.17 第二 seed；⑨往後任何機制輪必須把 `init`
  當成兩層因子。
- **Tier 3（新方向，依對已量測失效輪廓的貼合度排序）**：⑩**multi-label 輸出頭**
  （`is_synthetic`×`has_filter`×4-bit type×ordinal level）——同時解決標籤矛盾、使
  headline 威脅模型可直接量測、取回磁碟上被丟棄的強度標籤、對齊兩個 peer-reviewed 前例；
  ⑪continual-learning 處置任務干擾（rehearsal/EWC/雙家族路由，`P1A1-TARGETED-MINE`
  已點名且未啟動）；⑫cost-sensitive loss 取代 ×15 過採樣；⑬大 teacher 蒸餾；
  ⑭ED⁴/AdvSCM＋ClArC；⑮patch 級分類＋直方圖池化；⑯既有 checkpoint 動物園的 ensembling。

### Claim / Non-claim

- **Claim**：①上述 38,020 列標籤矛盾與 stress 分解為本輪新量測，數字可由
  `splits/v811_layer2_train.txt` 與 `results/research/p1a1_targeted_mine_20260904/
  mechanism_*.json` 直接重現；②Part 3 所列 12 項結論在其現有證據下不成立或過度宣稱；
  ③五項方法論問題皆有具體檔案/行號/數字支撐。
- **Non-claim**：本輪**未**跑任何模型、未重訓、未量測任何新的模型行為；所有關於「若移除
  該批資料會如何」「若做 threshold-matched 對照會如何」的陳述皆為**預測與建議**，非結果；
  未裁定任何 production 變更；未修改 `pipeline.py`／checkpoint／split／既有 results／
  除本條目外的任何文件；未讀 LOCKBOX；無 git 操作。

---

## EXTERNAL-BASELINES-20260905: 首次同協定對照 11 個已發表偵測器 — `results/research/external_baselines_20260905/`，**P3 美顏真臉誤報 ours 贏 13/13；P2 Celeb-DF-B 全面落後；P1 對手測不到 EFS 假臉、matched 判決退化**

- **Checkpoints**：production v8.17（Layer1 `v817sbi` e3057270…＋Layer2 `v811` 8470ad52…，harness 路徑）；外部 11 個（UnivFD CVPR23／NPR CVPR24／SBI CVPR22／DeepfakeBench v1.0.1 release 的 Xception、EfficientNet-B4、SPSL、F3Net、UCF、RECCE、CORE、SRM；sha256 在 `models.json`）；本專案 FF++-protocol 同架構兩個（`ffpp_full_best.pth`、`ffpp_BB_repvit_dense_long_best.pth`）。**推論 only，無訓練**。
- **資料／協定**：P1＝`p1_r8` stress cache（287 源圖 × 8 條件，2,289 有效列）＋真臉側 250 TT real＋3,000 CelebA；P2＝Celeb-DF-B RES-MATCHED crops（`celebdfb_external_20260903/crop_manifest.tsv`，6 folders × 232 影片 × 5 幀）；P3＝249 LFW+filter＋250 LFW real。**13 個模型看同一批 13,026 張影像位元組**，各自官方前處理（表列於 PRE_DECLARED）。Sanity：production 逐位重現 2.80%／90.34／23.47／57.59。
- **Image-disjoint**：對外部模型全部 OOD（它們沒看過任何一張）；對 ours，P1/P3 為 in-domain 家族、P2 濾鏡與換臉未見但 Celeb-DF-v2 real 身份見過（`CELEBDFB-EXTERNAL` 已宣告）。
- **結果**（threshold-matched，cluster bootstrap 95% CI）：
  - **P3**（真臉 FPR 對齊 5%）：249 張美顏真臉叫 fake——ours **0.0%**（229→filter、20→real），13 個對手 22.5–33.7%（NPR 退化 100%）→ **ours_better 13/13**。
  - **P2**：beautified AUROC ours 0.524 [0.484, 0.568] vs 對手 0.64–0.76（SBI 0.752、UCF 0.756）→ ours_worse 12/13；real_beautified 誤報 ours 74.1% vs SBI 19.3% → ours_worse 9/13；beautified ASR（recall 對齊 90.4%）對手 6–21%，ours 23.4%。**ours 對 untreated Celeb-DF 換臉 AUROC 0.521、把 87.7% 真影格叫 fake**——production 在此母體不辨真假。同架構 FF++ 配方（RepViT）beautified AUROC 0.713，進入對手區間。
  - **P1**：對手 base AUROC 0.45–0.70（ours 0.995 [0.989, 0.999]）；matched 到 96.9% recall 時對手真臉 FPR 89–100% → **4 個 ours_worse 判決為退化操作點，不得引用**（PRE_DECLARED 判決規則未限制 FPR，本輪設計缺陷，如實記載）。所有對手 filtered AUROC > base AUROC（偵測到的是濾鏡）。
- **可宣稱**：①3-way 設計消除「美顏真臉被誣告」的失效模式，同協定 13/13 對手做不到（in-house 濾鏡）——文獻（Saeed 2025）只量了反方向；②production 在第三方 Celeb-DF-B 全面落後 FF++ 訓練偵測器，根因為換臉家族未訓練，非架構；③公開偵測器對 EFS 假臉零樣本失效。
- **不可宣稱**：P1 matched 輸贏；P3 勝利外推到第三方濾鏡（P2 已證偽）；「2.80% vs 64.63%」任何跨協定措辭（**全專案刪除**）；`CELEBDFB-EXTERNAL` 的「well below Saeed regime」**撤回**（對手 matched ASR 15–21% 比 ours 低）。
- 未動 production／`pipeline.py`／無 git／未讀 LOCKBOX。

## REMOVAL-ABLATION-20260904: 移除／重標／降權 38,020 筆矛盾列重訓 Layer2 — `results/research/removal_ablation_20260904/`，**四臂全無效，「標籤矛盾是 Layer2 幅度根因」假設否證**

- **Checkpoints**：Layer1 固定 `v817sbi`；Layer2 四臂 CTRL（同配方重訓，seed 20260904）／REMOVE（拿掉 38,020 列）／RELABEL3（改三類）／DOWNWEIGHT，皆 `checkpoints/research/removal_ablation_20260904/`；PROD 對照。
- **結果**（`gates_*.json`、`paired_delta_results_*.json`）：stress PROD 2.80 → CTRL 2.93／REMOVE 3.01／RELABEL3 2.80／DOWNWEIGHT 2.93；TT filter 91.97 全臂不變（RELABEL3 91.57）；Shadow filter recall 12.2 → 16.5／17.2／13.6／17.9；Layer2 幅度（1,272 對 held-out FFHQ 配對 `frac_right_direction`）PROD 0.387 → CTRL 0.440／REMOVE **0.498**／RELABEL3 0.432／DOWNWEIGHT 0.443——全部在機率水準附近，無一臂達到方向性訊號。
- **可宣稱**：`FROMSCRATCH-AUDIT` Tier 2 ⑦ 已執行；移除矛盾列不改變 Layer2 跨語料幅度，也不改變 stress——標籤矛盾**不是**已量測失效的槓桿。**不可宣稱**：「結構性限制」（本輪只否證一個機制）；未跑 Layer1 側移除；單 seed。

## FLAT3CLASS-REVISIT-20260828（結果補登）: 扁平 3-class（F1）與 multi-label 兩 sigmoid 頭（ML）vs production 階層式 — `results/research/flat3class_revisit_20260828/`，**單模型在泛化指標上全面領先、只輸 stress**

- **Checkpoints**：`flat3_F1_seed20260828.pth`、`flat3_ML_seed20260828.pth`（同 v811 合併語料 211,991 列；ML 的 (1,1) 複合列 38,020 由來源標籤指定）；封存扁平 v6/v79/v81/v83/v85/v86/v88 同 harness 重評。
- **結果**（`gates_{PROD_full,F1_full,ML}.json`）：

  | | stress | TT filter | TT real | unseen AUROC | Shadow real | Shadow filter | FF++ frame |
  |---|---|---|---|---|---|---|---|
  | PROD v8.17 | **2.80** | 91.97 | 72.29 | 0.8410 | 74.91 | 12.19 | 0.5747 |
  | F1 flat | 7.25 | 92.37 | 68.67 | 0.8279 | 83.15 | 25.45 | 0.5426 |
  | **ML multi-label** | 7.30 | **95.18** | 65.86 | **0.8622** | 81.72 | **31.54** | 0.5554 |

  封存扁平 stress：v83 0.26／v85 1.40／v86 1.66／v88 1.62／v81 8.65／v79 9.70／v6 12.67（Shadow 未補測）。
- **可宣稱**：ML 頭是全專案 unseen AUROC 最高（0.8622）、TT filter 最高（95.18）、Shadow filter 為 production 2.6 倍的單一模型；stress 7.3% 為其代價；stress 隨語料版本演進的軌跡與架構（扁平／階層）無關。**不可宣稱**：階層式 vs 扁平的 Shadow 對照（封存扁平未測 Shadow）；單 seed；ML 的 (1,1) 格無 in-domain val（PRE_DECLARED 已註）。

## P1A1-INTERFERENCE-20260905: 任務干擾三種 continual-learning 處置 — `results/research/p1a1_interference_20260905/`，**FAM3 候選經第二 seed 推翻；三種處置在此設定下均未達標，脆弱核心指標唯一跨 seed 複現**

- **Checkpoints**：LWF（蒸餾 v817sbi 於非 FF++ 列，T=2 λ=1）／FAM3（[real, manip_EFS, manip_swap] 家族頭，p_manip=1−p_real，初始化令 p_real 與 production 起點相同）／L2SP（λ=1e-2）各加在 P1REPRO 配方（Adam 2e-5, 10 epoch, split `layer1_pcand_v2b_train.txt` 319,711 列、FF++ 83,038）上；污染斷言 PASS（0 硬違規，11 個已知跨生成器 stem 巧合警告）。
- **結果**：

  | arm | FF++ end2end AUROC | stress | vs production CI [1.92, 3.76] | 六絕對閘門 | 脆弱核心（prod=9, P1REPRO=29, 門檻≤19）| TT real |
  |---|---|---|---|---|---|---|
  | LWF | 0.784 | 6.204 | 外 | 過 | 23（不過）| 73.49 |
  | **FAM3** | **0.825** | **3.757** | **內，僅差 0.003** | 過 | **18（過）** | **54.62（−17.7pp）** |
  | L2SP | 0.753（勉強）| 6.509 | 外 | 過 | 27（不過）| 68.67 |

- **可宣稱**：①FAM3 是本專案第一個同時滿足 P1-A1 全部事前門檻（FF++、stress CI、六絕對、脆弱核心機制檢查）的機制，證實「共用決策邊界的任務干擾」診斷是可處置的、不只是描述性的；②三臂脆弱核心縮減排序 FAM3(18) > LWF(23) > L2SP(27) 與「拆開邊界最有效、只蒸餾不衝突列次之、錨定全部參數最鈍」的機制假說一致。
- **不可宣稱**：FAM3 尚未升格、非 production；0.003 的 CI 邊際在單一 seed 上與雜訊不可區分（本專案同指標曾見 seed 間差距達 0.61pp），依 PRE_DECLARED 規則本身就是「候選，待第二 seed」；**FAM3 的代價未被六絕對閘門看見**——True Test real recall 從 72.29% 掉到 54.62%（−17.7pp），CelebA 也降到 97.27%（仍過 95% 但三臂中最低）；L2SP 的 λ=1e-2 為事前固定值未調參，本輪不代表 L2SP 的天花板；未動 production／`pipeline.py`／無 git／未讀 LOCKBOX；Layer2 全程凍結。
- **第二 seed 結果（`--seed 20260906`，2026-09-05 20:41）**：FAM3 stress 3.757%→**4.238%，掉出 production CI 外**；FF++ 0.822（打平）；**脆弱核心兩個 seed 完全相同＝18**（production 9、P1REPRO 29）。依 PRE_DECLARED 自訂規則（「若第二 seed 落在 CI 外，本輪 FAM3 結果即為雜訊」），**候選正式推翻，判決關閉**。
- **最終可宣稱**：①三種處置在本輪設定下均未達 P1-A1 完成定義（FF++≥0.75 且 stress 在 production CI 內）；②脆弱核心縮減排序 LWF(23) < FAM3(18) < L2SP(27) 為唯一跨兩個 seed 完全複現的指標，與「拆開共用決策邊界最有效」的機制假說一致，即使聚合 stress 閘門未必跟著過；③FAM3 的 real recall 代價（72.3%→54.6%／58.2%，兩 seed 皆大幅退步）為真實、可複現的 trade-off，與 stress 結果無關獨立成立。
- **最終不可宣稱**：任務干擾在此路線上「無解」——僅代表這三個機制在這組固定超參數、這個訓練配方下未解；L2SP 的 λ=1e-2 未調參，不代表其天花板。
- **下一步**（直接由本輪證據推導，非重跑同一件事）：①FAM3 家族頭 + rehearsal ratio 組合（架構＋資料取樣同時處置共用邊界，尚未試過的組合）；②承認 FF++ 覆蓋與 stress 閘門對此 backbone 是真實的 Pareto 前緣，把整條前緣（production 0.57/2.80、LWF 0.78/6.20、FAM3 0.82/3.76-4.24、L2SP 0.75/6.51、ADV2 0.82/6.12、TGT2 0.81/5.90-6.68）當作論文的誠實發現本身呈現，而非繼續追一個同時過兩個閘門的單點。

### EXTERNAL-BASELINES-20260905 補充（2026-09-06）：六個 FF++ 訓練 Layer1 候選同協定定位
- `score_candidates_p2.py` 以 production 決策規則將 P1REPRO／ADV2_s1／TGT2_s1／FAM3（兩 seed）／RECIPEGAP 放進同一張表（sha256 在 `models.json`）。Celeb-DF-B beautified AUROC：0.524（production）→ 0.60–0.64（FAM3 0.641 最佳），對手區間 0.72–0.76 未達；real_beautified 誤報 72–91%（P1REPRO 32% 但 ASR 54%）。**主導失效為 real 側（影片幀真臉被叫 fake），且本專案所有濾鏡訓練資料皆為靜態照片**→ 直接推導出 `filter_video_20260906`（FF++ train 幀套四種濾鏡，real+filter→filter、fake+filter→fake，L1 家族頭＋L2 同時重訓，三項 Celeb-DF-B 門檻同時達標為唯一成功定義，PRE_DECLARED 已寫）。可宣稱：FF++ c23 幀不足以補 Celeb-DF 缺口；P3 0% 在全部候選穩定。不可宣稱：任何候選達到三項門檻（無一達成）。

## FILTER-VIDEO-20260906: FF++ 訓練幀套四種濾鏡（real+filter→filter、fake+filter→fake）L1 家族頭＋L2 同時重訓 — `results/research/filter_video_20260906/`，**事前主準則 FAIL（1/3）；「影片幀＋美顏沒看過」假設被否證**

- **資料**：12,000 新列（各 6,000；1,500/型/方法；43 張 MediaPipe 失敗未補），源自 `layer1_pcand_v2b_train.txt` 的 FF++ train 列；污染斷言 PASS（0 硬違規）。L1 = FAM3 配方 seed 20260906（331,711 列）；L2 = v811 暖啟動 CTRL 配方（158,425 列）。
- **Celeb-DF-B 三項（事前門檻）**：beautified AUROC **0.628** [0.588, 0.667]（門檻 ≥0.72 ✗）；real_beautified 誤報 **75.0%** [71.3, 78.5]（≤20% ✗；production 74.1%）；beautified ASR **11.9%** [9.4, 14.6]（≤15% ✓；production 23.4；hawaii_grain 57.6→31.4）。untreated real 誤報 86.0%（production 87.7%）。
- **次要**：六絕對全過（TT filter 95.98／fake 99.63／CelebA 97.30／SG2 99.67／unseen 0.8198）、Alibaba 98.74、FF++ 0.808、in-house stress 5.16%（CI 外，揭露）、TT real 59.04（FAM3 家族代價第三次複現）、P3 0.4%。
- **可宣稱**：①濾鏡側強健性可由影片幀濾鏡資料改善且不傷絕對閘門；②Celeb-DF-B 的 real 側失效**與美顏無關**——未加濾鏡的 Celeb-DF 真影格本來就 86–88% 被叫 fake，41,512 張 FF++ 真影格在訓練中也無法轉移；③唯一守住 Celeb-DF 真影格的對手是 SBI（35.9%／19.3%），即唯一「real 類不綁定任何假語料庫」的訓練法——語料庫捷徑 meta-finding 在第三方資料的 real 側再現。
- **不可宣稱**：候選／升格；「SBI 式錨定 real 類、假語料全部移到 Layer2」為由此推導的**未測假設**（需另立 PRE_DECLARED）。依本輪停止規則，不在此軸調參。

## TERNARY-NECESSITY-20260906: 四種標籤空間的受控對照 — `results/research/ternary_necessity_20260906/`，**判決 NECESSARY：二元標籤空間不存在能同時匹配三分類的操作點**

- **設計**：backbone／資料池／配方／optimizer／schedule／seed 全同，**只有標籤空間不同**；四臂皆重新初始化最後一層。資料＝`flat3class_revisit_20260828/flat3_train.txt`（211,991 列）。seed 20260906。
- **結果**（4.80% 乾淨真臉 FPR 對齊點）：

  | 標籤空間 | FA(修圖真臉) | MISS(套濾鏡假臉) | 乾淨假臉 recall |
  |---|---|---|---|
  | **三分類** | **8.84%** | **1.97%** | 98.61% |
  | filter→real | 10.04% | 3.54% | 98.95% |
  | filter 不存在 | 37.75% | 3.41% | 98.61% |
  | filter→fake | 41.37% | 76.37% | 41.11% |

- **配對 bootstrap（同圖、源圖分群，`paired_differences.json`）**：vs「filter 不存在」FA −28.92pp [−35.34, −22.49]、MISS −1.44pp [−2.14, −0.79]，**兩軸顯著**；vs「filter→fake」−32.53pp／−74.44pp**兩軸顯著**；vs「filter→real」MISS −1.57pp [−2.27, −0.92] **顯著**，FA −1.20pp [−5.62, +3.21] **不顯著**。
- **Dominance 檢定**：四個二元臂＋11 個公開偵測器的門檻**全範圍掃描**，**0 個**能同時達到更低 FA 與更低 MISS。事前判準（無 dominator 且至少一軸差距超出 CI）全部滿足 → **NECESSARY**。
- **機制**：三分類在其原生決策規則下把 **94.78%** 的修圖真臉判為 `filter`（FA 0.0%、乾淨 FPR 0.0%、MISS 7.65%）。
- **可宣稱**：①「filter 不存在」臂的 37.75% 落在公開偵測器 22–33% 帶內，證實該臂是有效對照；②三分類優勢對兩個實務上會採用的二元選擇皆為大幅且顯著。**不可宣稱**：對「filter→real」為全面顯著勝出（FA 軸不顯著，已如實記載）；本輪 TERN 是研究臂（flat3 語料＋RECIPEGAP 配方），**不是** production v8.17，兩者數字不可互換。

## CROSSDATASET-BACKBONES-20260906: 全 backbone 跨資料集評測＋公開偵測器同幀重測 — `results/research/crossdataset_backbones_20260906/`，**更正先前「打平 Xception」的宣稱；MobileNetV4 為最佳小模型**

- **關鍵更正**：`CROSSDATASET-TABLE-20260828` 是拿我方量測值對比 DeepfakeBench **論文published數字**（不同抽幀／裁切）。本輪把 11 個公開 checkpoint 拿來跑**我方同一批影格**：Xception 實得 CDFv2 **0.8063**／DFD **0.9007**（非 0.7365／0.8163）。**「我方打平 Xception、DFD 勝出」的說法撤回。**
- **同幀結果**（全部 FF++ c23 訓練、零樣本、frame AUC）：SBI 0.8928/0.9273｜UCF 0.8312/0.8833｜CORE 0.8174/0.8811｜SRM 0.8100/0.8982｜F3Net 0.8078/0.8464｜Xception 0.8063/0.9007｜RECCE 0.7914/0.9060｜EffB4 0.7801/0.8636｜SPSL 0.7740/0.8746｜UnivFD 0.6740/0.9038｜NPR 0.5266/0.5289。
- **我方**：MobileNetV4(3.90M) **0.7932/0.9062**｜EffLite0(4.78M) 0.7893/0.8853｜FastViT(4.40M) 0.7854/0.9015｜RepViT(5.67M) 0.7846/0.8783｜ShuffleNet dense-long(2.53M) 0.7546/0.8578｜ShuffleNet dual(2.53M，現行 backbone) 0.7286/0.8487｜spatial-only(1.78M) 0.7355/0.8605。
- **可宣稱**：①換 backbone（ShuffleNetV2→MobileNetV4）帶來 CDFv2 +6.5pp／DFD +5.8pp，**proposal 原指定的 backbone 在此協定上明顯較佳**；②DFD 欄我方 MobileNetV4 領先 Xception／RECCE／UnivFD，參數少 5–110 倍；③FF++ 域內排名（RepViT 最佳 0.9546）**不轉移**到跨資料集（MobileNetV4 最佳）。**不可宣稱**：CDFv2 第一（SBI 0.8928 明顯領先）；DFD 第一（SBI 0.9273）。

## FFPP-SBI-20260906: 在 FF++ 協定上加入自混合增強 — `results/research/ffpp_sbi_20260906/`，**假設否證，跨資料集大幅退步**

- 12,000 張自混合圖（源自 FF++ dense-train 真影格，705 支影片，manifest 齊全）加入 dense split（95,038 列）後重訓兩個 backbone。
- **結果**：MobileNetV4 CDFv2 0.7932→**0.7012**、DFD 0.9062→**0.7851**；FastViT 0.7854→**0.7469**、0.9015→**0.7480**。域內 val AUC 仍健康（0.9602）→ 傷害專屬於跨資料集轉移。
- **最可能原因（假設，未測）**：本輪跑的是**混合**配方（FF++ 假圖＋SBI），而 SBI 原論文是**只有** real＋自混合、完全不含偽造語料；混合下網路可用較容易的 FF++ 生成痕跡滿足 manipulated 類，混合邊界線索不必學。**純 SBI 配方未跑，需另立 PRE_DECLARED。**
- **不可宣稱**：SBI 式訓練普遍無效；我方 SBI 生成器忠於原論文；單 seed。

## VLM-TEACHER-20260906: Qwen2-VL-7B + LoRA 對照組與 clue 蒸餾素材 — `results/research/vlm_teacher_20260906/`，**補上 proposal 偏離 #2／#4；語料捷徑在 7B 多模態模型上再現**

- LoRA r=16（10,092,544 可訓練參數）於 32,961 張（FakeClue ff++ 23,961 帶自然語言 clue ＋ 我方三類 9,000）訓練 1 epoch，2,061 步，99 分鐘。
- **對照組（True Test 769）**：real recall **20.80%**（250 張中 192 張被判 filter）、fake 80.00%、filter 77.51%，整體約 **59.9%**。→ 7B 多模態模型微調後**不及** 5.06M 專用偵測器，支持 proposal「Qwen 當 teacher／對照組而非主模型」的定位。
- **clue 品質（FakeClue test ff++，n=300）**：ROUGE-L mean **0.4618**／median 0.4309；**同一模型在 FakeClue 自己的測試集上分類正確率 99.67% [99.0, 100.0]**。
- **可宣稱**：99.67%（域內）vs 59.9%（我方 held-out）的 40 點落差，是**語料捷徑 meta-finding 在 7B 多模態模型上的再現**——解釋文字流暢不構成學會任務的證據。
- **產出**：`tags_train.jsonl`（32,961 列；23,961 來自 FakeClue GT、3,000 teacher 生成、6,000 由標籤推導；14 個 tag）供後續 tag head 蒸餾。**尚未**訓練 student tag head。

### VLM-TEACHER-20260906 補充（2026-09-07）：tag head 蒸餾結果
- Student = 凍結 production L1+L2 的 2,560-d 特徵上一層線性層，**35,854 參數**（事前預算 ≤0.1M）。目標 14 個 tag，訓練 32,961 列，held-out = FakeClue test ff++ 1,168 張（tag 由該 split 自己的參考 clue 推導）。
- **事前門檻 macro-F1 ≥ 0.70（全 14 tag）→ 實得 0.4758，FAIL，如實記載。**
- **但門檻是我設計錯的**：`smoothing`／`whitening`／`face_reshaping`／`eye_enlarging` 四個 filter tag 在 FakeClue test 上 **support = 0**（FakeClue 根本沒有 filter 類），依定義 F1=0，直接吃掉 14-tag 平均的 28.6 個百分點。分層看：10 個有 support 的 tag macro-F1 = **0.6662**；8 個 support>100 的 tag = **0.8188**（個別 F1 0.729–0.869）。
- **可宣稱**：8 個 artifact 概念可蒸餾進 35,854 參數的線性探針、掛在凍結 production 特徵上，不動 backbone。**不可宣稱**：filter tag 可蒸餾（未測）；事前門檻達成（未達成）。
- **正確的後續**：改用含濾鏡影像的測試集（True Test 249 張 filter，型別已知）才能量到那四個 tag；忠實度 deletion 檢定亦已宣告但尚未執行。

### CDF-SHORTCUT-20260906 / FFPP-SBI-20260906 判決（見各自 FINDINGS.md）
- `cdf_shortcut_20260906`：**REFUTED**。移除 11,735 筆 Celeb-DF 衍生假圖，Celeb-DF-B untreated real 誤判 41.71%→41.45%（−0.26pp，配對影片分群 CI [−1.98, +1.47]），三個 real 資料夾全部不顯著。**存活的解釋改為「真類缺少真實影片影格」**：加入 FF++（含 41,512 張真影片影格）使該指標由 87.7%→41.7%。該存活解釋本輪**未經受控操作驗證**，僅為跨臂觀察。
- `ffpp_sbi_20260906`：**REFUTED，且大幅退步**。混合配方（FF++ 假圖＋12,000 自混合圖）使 MobileNetV4 CDFv2 0.7932→0.7012、DFD 0.9062→0.7851；FastViT 亦退 4–15pp。域內 val AUC 0.9602 仍健康 → 傷害專屬跨資料集。**純 SBI 配方（real＋自混合、不含偽造語料）未跑**，需另立 PRE_DECLARED。

## FILTER-AUX-20260907: 第三類是否也改善跨資料集偽造偵測 — `results/research/filter_aux_20260907/`，**REFUTED，且顯著往反方向；第三類的泛化代價首次量化為 1.8–3.7 AUC 點**

- **設計**：兩臂 backbone／訓練幀／配方／schedule／seed（20260907）全同，只差標籤空間。BIN＝FF++ dense 二元（41,512 real / 41,526 fake）；AUX3＝同列＋12,000 張濾鏡圖為第三類（95,038 列）。污染斷言：0 個禁用語料命中、0 個 FF++ val/test video-id 碰撞（`split_stats.json`）。推論以 $p_\text{fake}$ 讀取（事前宣告）。
- **配對 image bootstrap（同一組重抽索引同時評兩臂，NB=10,000）**：

  | holdout | BIN | AUX3 | Δ | 95% CI | 判定 |
  |---|---|---|---|---|---|
  | Celeb-DF-v2 (389) | **0.8325** | 0.7955 | **−0.0370** | [−0.0687, −0.0061] | 顯著 |
  | DFD (1,521) | **0.8916** | 0.8739 | **−0.0177** | [−0.0314, −0.0044] | 顯著 |

  域內 FF++ val 幾乎不變（F1 0.9207 vs 0.9206）→ 代價專屬於跨資料集轉移。**事前判準：REFUTED。**
- **可宣稱**：①第三類**不會**改善跨資料集偽造偵測，反而顯著降低 1.8–3.7 AUC 點；②因此本專案的設計主張精確化為「第三類消除誣告失效模式（0.0% vs 對手 22.5–33.7%）、且二元標籤空間無任何操作點可匹配（`TERNARY-NECESSITY-20260906`），代價為 1.8–3.7 AUC 點的跨資料集泛化」——這比未限定的主張更強。
- 🔴 **對本專案所有單 seed 跨資料集比較的重要約束**：BIN 與 `CROSSDATASET-BACKBONES-20260906` 的 `mobilenetv4` 是同一設定、只差 seed，Celeb-DF-v2 得 **0.8325 vs 0.7932＝3.93pp 的 seed 落差**（DFD 1.46pp），**大於我們報告過的多數「方法間」差距**。389 幀 holdout 上的單 seed 排名不可靠；本專案先前的排名陳述同受此限制。正面讀法：seed 20260907 的 BIN（3.90M）Celeb-DF-v2 0.8325 領先 Xception 0.8063／CORE 0.8174／SRM 0.8100／F3Net 0.8078／RECCE 0.7914／EffB4 0.7801／SPSL 0.7740／UnivFD 0.6740，與 UCF 0.8312 齊平，SBI 0.8928 仍明顯領先——但此讀法同受 seed 限制。
- **不可宣稱**：其他濾鏡資料量／來源／權重也會傷害（僅測一組配置、每臂單 seed）；此效應在 MobileNetV4 以外的 backbone 成立；憑單 seed 對 UCF／Xception 宣稱序位優勢。未動 production、無 git、未讀 LOCKBOX。

## BACKBONE-SWAP-20260907: MobileNetV4 取代 ShuffleNetV2 於濾鏡三分類任務 — `results/research/backbone_swap_20260907/`，**判決 KEEP：較佳的偵測 backbone 沒有犧牲濾鏡安全性，反而顯著改善誣告率**

- **設計**：只換 backbone。資料／標籤空間／配方／optimizer／schedule／epoch／seed（20260906）全同 `ternary_necessity_20260906` 的 TERN 臂，控制組即該臂既有 checkpoint（同腳本產生）。MobileNetV4 = timm `mobilenetv4_conv_small.e2400_r224_in1k`，與 FF++ benchmark 用的同一個。
- **結果**（同在 4.80% 乾淨真臉 FPR；配對 bootstrap 依源圖分群 NB=10,000）：

  | 軸 | ShuffleNetV2 | **MobileNetV4** | 配對 Δ | 95% CI | 判定 |
  |---|---|---|---|---|---|
  | FA（249 張修圖真臉被判 fake）| 8.84% [5.22, 12.45] | **2.81% [0.80, 4.82]** | **−6.43pp** | [−10.44, −2.41] | **顯著改善** |
  | MISS（2,289 張套濾鏡假臉逃脫）| 1.97% [1.22, 2.80] | 2.71% [1.83, 3.65] | +0.74pp | [−0.22, +1.71] | 無顯著變化 |
  | 乾淨假臉 recall（287）| 98.61% | **100.00%** | — | — | 改善 |

  原生三分類決策：兩臂誣告皆 0.0%，MobileNetV4 把 **95.58%** 修圖真臉導向 `filter`（ShuffleNetV2 94.78%）。**事前判準 KEEP。**
- **合併偵測軸證據**：MobileNetV4 在 FF++ 域內 0.9383 vs 0.9155、Celeb-DF-v2 0.7932/0.8325 vs 0.7286、DFD 0.9062/0.8916 vs 0.8487、CPU 14.1ms vs 19.0ms（參數較多但更快）。**除參數量外每一項都較佳，且正是 proposal 原本指定、我們當初偏離掉的 backbone。**
- **不可宣稱**：production 升格（仍為 ShuffleNetV2 階層式 v8.17；升格需第二 seed、階層式架構的完整 Freeze-Gate、change proposal）；第二 seed 會複現；RepViT／FastViT 同樣成立；階層式二階段架構繼承此結果（本輪為扁平三分類）。
- **精度註記**：`frontier.json` 以全精度計算 FA=7/249=2.81%；配對檢定讀 6 位小數的 per-image dump，一張分數距門檻 5e-7 內的圖翻面得 6/249=2.41%。兩臂 dump 同精度故配對比較內部一致，一張圖無法動搖 CI 排除 0 的 6.43pp 差距。

### TERNARY-NECESSITY-20260906 更正（2026-09-07）
- 該輪四臂實際訓練列數為 **191,696**（65,566 real / 52,798 fake / 73,332 filter），非條目原記的 211,991——`flat3_train.txt` 有 **20,295 列檔案遺失**，`load_split` 逐列跳過。四臂與 `BACKBONE-SWAP-20260907` 掉的是同一批、class counts 完全相同，故所有臂間比較與判決不受影響，僅列數記載需更正。

### BACKBONE-SWAP — addendum 2026-09-07: full Freeze-Gate battery
Flat MobileNetV4 (seed 20260906) at the native rule: True Test fake 99.63 / filter 95.58 / real 67.07;
unseen AUROC 0.8226; CelebA 100; StyleGAN2 99.9; Shadow real 94.27; **stress 11.36% (FAIL, v8.17 2.80%,
flat SNV2 twin 7.25%)**; **Alibaba 72.40% (FAIL, twin 99.73%)**; FF++ zero-shot 0.537. Verdict: frontier
KEEP stands, but the backbone is NOT a production candidate on this evidence. Backbone vs flat-label-space
confound unresolved -> BACKBONE-HIER. Evidence: `results/research/backbone_swap_20260907/FINDINGS.md` §8,
`gates_MNV4_stdout.log`. Seed-2 frontier (`eval_frontier_s2.py`) first run had SEED not updated and
re-scored seed 1 (identical numbers); fixed 2026-09-07 and re-run — see `frontier_s2.json` when present.

### BACKBONE-HIER — 2026-09-07 (pre-declared, RUNNING)
MobileNetV4 spatial branch inside the production hierarchy (L1 real-vs-manip @0.5 -> L2 fake-vs-filter),
production v8.11 splits, ImageNet init, BASE recipes of P1A1-INTERFERENCE (L1) and REMOVAL-ABLATION (L2),
seed 20260907, one seed. Decision rule fixed in `results/research/backbone_hier_20260907/PRE_DECLARED.md`:
ADOPT-CANDIDATE only if all Freeze Gates pass (stress <= 3.76%) AND a stretch metric improves beyond the
v8.17 CI; otherwise KEEP-SHUFFLENET and the backbone question closes for the capstone. Cannot claim: anything
about the SBI-augmented L1 recipe of v8.17 (not trained here).
- BACKBONE-SWAP seed-2 replication (2026-09-07): FA 2.81 / MISS 2.49 / clean-fake 99.65; paired vs SNV2
  dFA -6.02 [-10.04, -2.01] significant, dMISS +0.52 [-0.48, +1.57] n.s. -> KEEP replicated (2/2 seeds).
  Evidence: `backbone_swap_20260907/frontier_s2.json`, `paired_test_s2.json`, FINDINGS §9.

### BACKBONE-HIER — 2026-09-07 RESULT: KEEP-SHUFFLENET (backbone question closed)
Hierarchical MobileNetV4 (production splits, ImageNet init, BASE recipes, seed 20260907) fails 6/8 release
gates: True Test fake 98.52 / filter 89.56; unseen AUROC 0.7653; StyleGAN2 98.13; **stress 15.12%**;
**Alibaba 57.31%**; passes CelebA 99.97; Shadow real 94.62 (filter 7.53); FF++ zero-shot frame AUROC 0.5423 (v8.17 0.5738). Worse than flat MNV4 on stress and
Alibaba -> the label-space confound of BACKBONE-SWAP §8 is resolved: the backbone, not the flat label space,
fails the safety gates. Can claim: the P3 frontier KEEP (2 seeds) is real but does not transfer to the native
rule / composite attacks / third-party retouching. Cannot claim: anything about MobileNetV4 under the SBI-aug
lineage recipe (not run; not justified after this result). Evidence: `results/research/backbone_hier_20260907/
FINDINGS.md`, `eval_HIER_MNV4.log`, checkpoints `checkpoints/research/backbone_hier_20260907/`.
- 2026-09-07 correction to BACKBONE-SWAP §8 / BACKBONE-HIER tables: the v8.17 column now uses the SAME harness
  (`flat3class_revisit_20260828/gates_PROD_full.json`: CelebA 99.33, StyleGAN2 99.57, Shadow real 74.91 /
  filter 12.19, FF++ official 0.5747, unseen 0.8410 composite) instead of CLAUDE.md headline numbers
  (99.05 / 99.6 / 76.9). No verdict changes. Flat MNV4 vs v8.17: wins TT filter +3.6, Shadow real +19.4,
  CelebA/SG2 marginal; loses stress +8.6pp, Alibaba -25.3pp, TT real -5.2, unseen -0.014, FF++ -0.01..-0.04.
