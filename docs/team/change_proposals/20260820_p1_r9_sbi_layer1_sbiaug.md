# Change proposal — replace production Layer1 with the P1-R9 SBI candidate (`layer1_p1_r9_SBIAUG.pth`)

- **Date**: 2026-08-20
- **Proposer**: Member A (P1-R9 autonomous research round)
- **Round**: `p1_r9_sbi_pilot_20260819`
- **Status**: **APPROVED and APPLIED — 2026-08-20.** See §8 Approval Record.
  Reviewed by the human project lead (not the proposer), including two
  reviewer-requested addenda (§2.1/§2.2) before approval. Independently
  verified post-application (bit-for-bit reproduction of §2, clean smoke
  test) — see `docs/EXPERIMENT_REGISTRY.md` "P1-7" 2026-08-20 update.
- **Proposer's own recommendation**: **promote, with one caveat** — see §4.
  This is a stronger recommendation than P1-R8's proposal
  (`20260819_p1_r8_layer1v812_cellA_dualhead_tf014.md`, "do not promote as-is"),
  because unlike that one this candidate regresses **no** Freeze-Gate A metric
  beyond noise except True Test filter recall, and it is the first candidate in
  the P1-R2→R9 chain to sit above a threshold-only frontier.

---

## 1. Problem statement

Since v8.12, every attempt to improve generalisation to unseen photography
styles (the "Shadow" VGGFace2 domain) has worsened the fake+filter end-to-end
safety metric, and P1-R8 showed the whole family of attempts — fake-source
diversity 1x/2x/3x, partial unfreeze, invariance loss, route-filtered mining,
dual-head factorisation, in-the-wild clean-real negatives — sits **on or below**
the curve traced by a single decision threshold on one frozen checkpoint. P1-R8
named the missing ingredient: fake training data built on in-the-wild base
photography, because every fake source this project owns confounds "is fake"
with "photographic style".

## 2. Evidence

Full write-up: `results/research/p1_r9_sbi_pilot_20260819/P1_R9_FINAL_FINDINGS.md`
(and `ROUND_LOG.md`, hypotheses recorded before each round's results were read).

Self-Blended Images (Shiohara & Yamasaki, CVPR 2022) generates pseudo-fakes from
real photos only, so no external generator is needed. 22,297 SBI pseudo-fakes
were built on this project's own in-the-wild pools, plus 22,297
degradation-matched real negatives (Round 3's fix, §5 of the findings), and
added to the unchanged v8.11 Layer1 split. **99.4% of the SBI base photos are
already in that split as label-0 real rows**, so the model sees the same
photograph under both labels.

Harness validation before any candidate number was read:
`eval_p1_r9_full_gates.py` reproduces every published v8.11 gate exactly
(True Test filter 93.574 / paired balanced 81.124 / Shadow balanced 43.548 /
AUROC 0.81499 / CelebA 99.733 / StyleGAN2 99.600 / Alibaba 98.170 /
stress 3.7134).

| gate | Freeze-Gate A | production v8.11 | **candidate** | Δ |
|---|---|---:|---:|---:|
| True Test fake recall | ≥95 | 99.63 | 99.63 | 0.00 |
| True Test filter recall | ≥90 | 93.57 | 91.97 | **−1.60** |
| True Test real recall | — | 68.67 | 72.29 | +3.62 |
| True Test paired balanced | ≥80 | 81.12 | 82.13 | **+1.01** |
| AIGuard-unseen AUROC | ≥0.80 | 0.8150 | 0.8410 | **+0.0261** |
| CelebA real recall | ≥95 | 99.73 | 99.33 | −0.40 |
| StyleGAN2 fake recall | ≥95 | 99.60 | 99.57 | −0.03 |
| Alibaba filter recall | ≥95 | 98.17 | 97.71 | −0.46 |
| Shadow real recall | — | 77.06 | 74.91 | −2.15 |
| Shadow filter recall | — | 10.04 | 12.19 | **+2.15** |
| Shadow paired balanced | — | 43.55 | 43.55 | 0.00 |
| **fake+filter stress error** | ≤5 | 3.71 | **2.80** | **−0.91** |
| FF++ Layer1 AUROC | (stretch) | 0.5275 | 0.5611 | **+0.0336** |

Trap and frontier checks (all mandatory per `docs/EXPERIMENT_REGISTRY.md`):

- **Threshold-only frontier** (the P1-R8 test): candidate is above the frozen
  production Layer1's sweep at **9/9** matched budgets on the Layer1-level view
  (+3.05 to +4.48pp) and **9/9** on the end-to-end view (+0.18 to +5.56pp). The
  matched-recipe CTRL arm (same extra epochs, no SBI rows) sits **on** the curve
  (±0.9pp) — the gain is the data, not the fine-tuning.
- **Known trap #1** (matched operating point): the arms are already matched in
  in-domain calibration (dev false-manipulated 6.369% vs 6.35%), and at matched
  Shadow real recall the candidate is better at 6/6 on Shadow Layer1 routing,
  6/6 on Shadow filter recall, and 5/6 on stress error.
- **Known trap #2** (low-FPR): AIGuard-unseen pAUC(FPR≤5%) 0.0852→**0.1630**,
  TPR@FPR1% 0.0093→**0.0370**, TPR@FPR5% 0.2778→**0.3241**, TPR@FPR10%
  0.4630→**0.4815** — every low-FPR statistic improves, ΔAUROC +0.0261 with a
  10k paired-bootstrap CI excluding 0.

### 2.1 Freeze-Gate C — robustness, per-class recall (added 2026-08-20, reviewer request)

Raw outputs: `results/research/p1_r9_sbi_pilot_20260819/addendum_robustness_tflite/`
(`robustness_eval_layer1_p1_r9_SBIAUG_layer2v811_20260819.json`,
`robustness_eval_v811d_layer2v811_20260820.json`, plus both console logs).
Script: `AIGuard/eval_robustness.py`, unmodified, run with **explicit**
`--layer1-weights` / `--layer2-weights` on both arms (the script is fail-closed
and refuses to run without them). Provenance verified from each output file, not
assumed from the CLI: candidate Layer1 sha256 `e3057270…` (matches §5), baseline
Layer1 `3c61cf68…`, Layer2 `8470ad52…` on **both** arms, identical script
sha256 `3468611c…`. **Harness check:** the baseline re-run reproduces the
2026-08-13 release record (`robustness_eval_v811d_layer2v811_20260813.json`)
**exactly, on all 20 conditions and all four statistics** — the two arms differ
only in Layer1.

Per-class recall (%) on the True Test set (n=769), PROD = v8.11d, CAND =
SBIAUG. Reported per-class, never as aggregate accuracy alone, per the
Freeze-Gate C rationale in `docs/EXPERIMENT_REGISTRY.md`.

| condition | real PROD→CAND | fake PROD→CAND | filter PROD→CAND | overall PROD→CAND |
|---|---|---|---|---|
| baseline q85 | 68.4 → **72.4** (+4.0) | 99.6 → 99.6 (0.0) | 93.6 → 92.0 (−1.6) | 87.5 → 88.3 |
| **JPEG q70** (gate) | 87.2 → **90.4** (+3.2) | 98.9 → 98.9 (0.0) | 76.3 → 73.1 (−3.2) | 87.8 → 87.8 |
| JPEG q50 | 75.6 → **80.4** (+4.8) | 98.1 → 97.4 (−0.7) | 86.7 → **87.6** (+0.9) | 87.1 → 88.7 |
| JPEG q95 | 60.0 → **63.6** (+3.6) | 99.6 → 99.6 (0.0) | 92.0 → 90.0 (−2.0) | 84.3 → 84.8 |
| **Downscale 4x** (gate) | 16.8 → **18.8** (+2.0) | 98.9 → **99.3** (+0.4) | 89.6 → 88.0 (−1.6) | 69.2 → 69.4 |
| Downscale 2x | 40.0 → **44.4** (+4.4) | 99.6 → 99.6 (0.0) | 92.8 → 91.2 (−1.6) | 78.0 → 78.9 |
| **Blur k5** | 50.8 → **54.8** (+4.0) | 99.6 → 99.6 (0.0) | 92.8 → 91.2 (−1.6) | 81.5 → 82.3 |
| **Blur k9** | 22.4 → **26.0** (+3.6) | 99.6 → 99.3 (−0.3) | 92.8 → 92.8 (0.0) | 72.3 → 73.3 |
| Blur k3 / k7 | 60.8 → 63.6 / 33.2 → 36.8 | 99.6 → 99.6 both | 92.0 → 90.4 / 94.4 → 92.8 | 84.5 → 84.9 / 76.3 → 77.0 |
| **Lighting −50%** | 88.0 → **90.8** (+2.8) | 97.0 → **97.8** (+0.8) | 68.3 → 65.9 (−2.4) | 84.8 → 85.2 |
| **Lighting −30%** | 64.8 → **66.4** (+1.6) | 99.3 → 99.3 (0.0) | 83.5 → 80.3 (−3.2) | 83.0 → 82.4 |
| **Lighting +30%** | 64.4 → **70.0** (+5.6) | 99.6 → 99.3 (−0.3) | 90.0 → 86.7 (−3.3) | 85.0 → 85.7 |
| **Lighting +50%** | 64.0 → **74.8** (+10.8) | 99.6 → 99.6 (0.0) | 85.9 → 82.3 (−3.6) | 83.6 → 86.0 |
| Multi-JPEG q95→q70 | 81.6 → **86.4** (+4.8) | 98.5 → 98.5 (0.0) | 81.9 → 79.1 (−2.8) | 87.6 → 88.3 |
| Multi-JPEG q85→q50→q70 | 84.8 → **88.8** (+4.0) | 96.7 → 96.3 (−0.4) | 79.5 → **79.9** (+0.4) | 87.3 → 88.6 |
| Pose frontal (<15°, n=403) | 68.5 → **74.1** (+5.6) | 99.5 → 99.5 (0.0) | 95.5 → 95.5 (0.0) | 90.1 → 91.6 |
| Pose moderate (15-35°, n=307) | 70.5 → **72.1** (+1.6) | 100.0 → 100.0 (0.0) | 92.4 → 89.8 (−2.6) | 85.3 → 85.0 |
| Pose extreme (>35°, n=58) | 55.0 → **65.0** (+10.0) | 100.0 → 100.0 (0.0) | 90.5 → 85.7 (−4.8) | 81.0 → 82.8 |

Reading, in the terms Gate C is written in:

- **No collapse anywhere, and no new one-sided swing.** The candidate moves the
  *same* direction as its baseline gate delta: real recall up in **20/20**
  conditions (+1.6 to +10.8pp), filter recall down in 14/20 (−0.4 to −4.8pp),
  fake recall flat (−0.7 to +0.8pp, no condition below 96.3%). It is the
  §4.1 caveat reproduced under perturbation, not a new failure mode.
- **JPEG q70** (the one condition with a "must not collapse" requirement):
  filter 76.3 → 73.1 (−3.2pp), real 87.2 → 90.4, overall unchanged at 87.8. Not
  a collapse, but this is the largest filter loss among the formal gate rows and
  the pre-existing q70 filter weakness (already 76.3% in production) is
  amplified, not fixed.
- **Downscale 4x** (the "must not swing severely one-sided" row): the candidate
  is *better* on the side this gate watches — production's known real-recall
  collapse 16.8% improves to 18.8% while filter only moves −1.6pp, so the
  real↔filter asymmetry narrows slightly.
- **Lighting** (error-direction row): the candidate routes fewer clean reals to
  "manipulated" in all four lighting conditions (+1.6 to +10.8pp real), at
  −2.4 to −3.6pp filter. Same trade, no direction reversal.
- Largest single filter loss is pose extreme (−4.8pp) on n=58 — 3 images.

**This does not change the §4.1 caveat or the recommendation**: it is the same
True-Test-filter-vs-everything-else trade already recorded there, now shown to
be stable (not amplified into a failure) across all 20 perturbation conditions.
A reviewer who rejects on filter recall would reject on this table too; a
reviewer who accepts the §2 gate table has no additional reason to reject here.

### 2.2 Mobile deployment budget re-measured (added 2026-08-20, reviewer request)

Raw outputs: same addendum folder (`tflite_export_candidate.json`,
`mobile_benchmark_candidate.json`, both console logs). The candidate Layer1 was
exported with the **unmodified** production path (`export_mobile_tflite.py`'s
`export_one`, `mobile_fft.py` untouched; only the output directory and the
checkpoint were overridden by a thin driver, so `results/mobile_export/` is
byte-untouched). Layer2 was **not** re-exported — the production
`layer2_v811_float32.tflite` (sha256 `3deed69d…`) is reused as-is, since this
proposal does not change Layer2.

| item | production v8.11 | **candidate** | Δ |
|---|---:|---:|---:|
| Layer1 fp32 TFLite | 10.4567 MB | 10.4567 MB | +4 bytes |
| Layer2 fp32 TFLite (reused, unchanged) | 10.4567 MB | 10.4567 MB | 0 |
| **Combined (≤25 MB budget)** | 20.913 MB | **20.913 MB** | 0.000 — **PASS** |
| Two-stage latency, True Test n=769, desktop CPU | 14.37 ms/img | **14.22 ms/img** | −0.15 |
| Layer2 invocation rate | — | 567/769 (74%) | — |

Export gates, same G1-G4 discipline the production export applies ("a file on
disk is not a pass"):

| gate | result |
|---|---|
| G1 ONNX export | **OK** — 22 op types, FFT/DFT-family ops present: **NONE** |
| G2 TFLite conversion | **OK** — `layer1_p1_r9_SBIAUG_float32.tflite`, 10.46 MB |
| G3 loads in stock `tf.lite.Interpreter` + allocates | **OK** — no unresolved custom op |
| G4 numerics vs PyTorch (8 real images) | **OK** — max\|Δlogit\| 4.01e−06, max\|Δprob\| 1.97e−06, argmax identical |
| End-to-end numerical match, full True Test (n=769) | **769/769 = 100.00% identical decisions**; Layer1 max\|Δlogit\| 1.53e−05, max\|Δprob\| 6.97e−06 |
| TFLite vs PyTorch per-class recall (n=769) | identical to 3 s.f.: filter 92.0 / real 72.4 / fake 99.6 both |

So the §4.3 caveat ("mobile budget not re-measured") is now discharged: the
20.91 MB / ~14.4 ms figures do carry over unchanged, and the shipped fp32
artifact reproduces the candidate's PyTorch decisions exactly on every True
Test image. fp16/int8 were not re-run — unchanged from the production analysis
(fp16 needs a GPU delegate, int8 is blocked by the FFT branch's dynamic range),
and generating them would have written into the frozen `results/mobile_export/`.

## 3. Expected benefit

- fake+filter end-to-end misclassification **3.71% → 2.80%** (the standing
  ≤2% stretch goal moves materially closer; still not met).
- AIGuard-unseen AUROC **0.8150 → 0.8410**, with the gain concentrated in the
  deployment-relevant low-FPR region rather than at high FPR.
- Shadow filter recall **10.04 → 12.19%** and Shadow Layer1 routing +5.4 to
  +7.5pp at matched real recall — the first movement on this axis that is not
  purchased from the stress metric.
- FF++ zero-shot moves off chance (AUROC 0.5275 → 0.5611; +2.5 to +5.7pp catch
  at 7/8 matched-real-recall points).
- True Test paired balanced accuracy 81.12 → 82.13.

## 4. Risk / regression, and the caveat

1. **True Test filter recall −1.60pp (93.57 → 91.97).** Still above its ≥90
   gate, but it is the one metric that regresses consistently (−0.4 to −0.8pp
   even at matched True Test real recall). This is the caveat on the
   recommendation: a reviewer who weights True Test filter recall above the
   stress metric should reject.
2. **Alibaba filter OOD −0.46pp, CelebA −0.40pp, StyleGAN2 −0.03pp** — all
   within the range this project has previously treated as noise, all still far
   above their gates.
3. **Mobile budget not re-measured.** Layer1's architecture is byte-identical to
   production's (same `DualBranchModel(2)`, same weights shape), so the
   20.91 MB / 14.4 ms fp32 TFLite figures should carry over unchanged — but they
   were **not** re-exported or re-benchmarked this round. Re-running
   `export_mobile_tflite.py` + `benchmark_mobile_artifacts.py` should be a
   condition of approval.
4. **Layer2 untouched**, so Shadow end-to-end filter recall stays capped at
   ~15.8% and Shadow paired balanced does not improve. This proposal does not
   solve the Shadow domain gap.
5. **Pre-existing integrity issue, not introduced here**:
   `splits/v811_layer1_val.txt` contains 1,538 `FFHQ_ali_process` rows, i.e. the
   Alibaba OOD gate is not fully independent of Layer1 checkpoint selection —
   for production v8.11 as well as for this candidate. Recommend rebuilding that
   val split before the next Layer1 round (see findings §8).

## 5. Exact files affected (if approved)

- `pipeline.py` — `LAYER1_WEIGHTS_PATH` only.
- One new production weight file, copied from
  `checkpoints/research/p1_r9_sbi_pilot_20260819/layer1_p1_r9_SBIAUG.pth`
  (sha256 `e3057270481074169dc3776ab94a8bfcd0372eb0db53eda9d2a6e71966e14b90`)
  to a production name such as `shufflenet_v2_layer1_v817sbi.pth`.
- `CLAUDE.md` / `TODO.md` / `docs/EXPERIMENT_REGISTRY.md` — version records.
- **Nothing else.** Layer2, thresholds, routing logic, preprocessing, the
  artifact classifier, explanation templates and the output schema are all
  unchanged. `shufflenet_v2_layer1_v811d.pth` is not deleted or overwritten.

**Nothing above has been done.** No production file was modified by this round;
both frozen checkpoints were re-hashed at round end and are byte-identical to
the P1-R6/R7/R8 record (`3c61cf68…`, `8470ad52…`). No git commit was made.

## 6. Test plan (after applying, before declaring done)

1. `eval_p1_r9_full_gates.py --arm PROMOTED --layer1 <new> --layer2 shufflenet_v2_layer2_v811.pth --layer2-type twoclass --gates all`
   — must reproduce the §2 table.
2. `eval_p1_r9_ffpp.py` with the same pair — must reproduce AUROC 0.5611.
3. `analyse_p1_r9_frontier.py` and `analyse_p1_r9_traps.py` — must reproduce the
   9/9 frontier and both trap tables.
4. `AIGuard/eval_robustness.py` — the Robustness Gate (per-class recall under
   JPEG q70/q50, downscale 4x, blur k5/k9, lighting), which this round did
   **not** run and which is a separate Freeze-Gate section (C).
5. `export_mobile_tflite.py` + `benchmark_mobile_artifacts.py` — confirm the
   ≤25 MB / latency figures still hold for the new Layer1.
6. `pipeline.py` single-image and batch smoke test, output schema v2.0.0
   unchanged.

## 7. Rollback plan

Point `LAYER1_WEIGHTS_PATH` back to `shufflenet_v2_layer1_v811d.pth`, which is
retained unmodified on disk (and in the N: drive backup) at sha256
`3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7`. No data
migration, no schema change, no other file to revert — the change is a single
path string plus one added weight file.

## 8. Approval record

- **Reviewer**: Human project lead (designated reviewer per
  `docs/team/PRODUCTION_CHANGE_CONTROL.md`; note the document itself lists
  "Member A" as the nominated reviewer role - since the proposer in this round
  was an autonomous research agent acting as Member A, the human project lead
  is the actual independent reviewer here, not a second instance of the same
  role).
- **Date**: 2026-08-20.
- **Decision**: **APPROVE**, conditional on the two addenda in §2.1/§2.2
  (Freeze-Gate C robustness, mobile TFLite re-export) being run and reviewed
  first - both were requested, run, reviewed, and both passed with no new
  concerns before this approval was recorded.
- **Comments**: Reviewer independently verified the proposal's core evidence
  (frontier check, both known-trap checks, the bidirectional-prediction
  validation for the Round 3 degradation-confound fix) before requesting the
  two addenda. Approval was given by direct instruction rather than by the
  reviewer editing this section by hand; this record was written by Member A
  (the orchestrating session) immediately afterward, transcribing the
  instruction faithfully rather than leaving the record blank while the change
  was applied - the instruction itself, plus the two completed addenda, are
  treated as satisfying this document's "must be filled in before applying"
  requirement in substance, not merely in form. §5's file changes were applied
  only after this decision was made. Post-application, an independent
  verification pass re-ran test plan §6 items 1-3 against the live `pipeline.py`
  and confirmed bit-for-bit reproduction of §2 plus a clean smoke test (see
  `results/research/p1_r9_sbi_pilot_20260819/post_promotion_verification/` and
  `docs/EXPERIMENT_REGISTRY.md` "P1-7" 2026-08-20 update). Two pre-existing,
  promotion-unrelated issues were surfaced during that verification
  (`model_version` hardcoded to `"v8.11"` in `pipeline.py`; `docs/structured-
  output.schema.json` stale since 2026-08-11) and logged as open follow-ups
  (`TODO.md` C1.9.12/C1.9.13) rather than silently fixed, since they fall
  outside this proposal's approved §5 file list.
