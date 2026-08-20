# Change Proposal — Layer1 v812 + Cell-A dual-head Layer2 @ (fake_thr 0.14, filter_thr 0.50)

- **Proposer**: Member A (P1-R8 autonomous research round, 2026-08-19)
- **Status**: **PENDING HUMAN REVIEW — NOT APPROVED, NOT APPLIED.** No production
  file was modified. `pipeline.py`, `shufflenet_v2_layer1_v811d.pth` and
  `shufflenet_v2_layer2_v811.pth` are byte-unchanged (hashes re-verified below).
- **Proposer's own recommendation**: **do NOT promote as-is.** This candidate is
  the first ever to beat production on *both* contested axes simultaneously, but
  it fails the noise tolerance this round pre-declared for the Freeze-Gate
  metrics. It is submitted as a decision-ready package, not as a request to ship.

## 1. Problem statement

Phase 1's two open stretch goals pull against each other. Every intervention
since v8.12 that improved Shadow (VGGFace2-style photography) paired balanced
accuracy pushed the fake+filter end-to-end stress error **up** from production's
3.71% (v8.12 5.29%, v8.13 5.72%, v8.14 4.33%, v8.16 5.11%, P1-R7 T900 5.94%).
Production v8.11 sits at Shadow balanced **43.55% — below the 50% degenerate
baseline**, i.e. its manipulated/real decision on that photography domain is
anti-informative, while its stress error is 3.71% (stretch goal ≤2%).

## 2. Evidence

All numbers produced by one harness, `eval_p1_r8_full_gates.py`, with explicit
checkpoint paths and SHA-256 recorded per run (no default fallback). The harness
was validated *before* any new number was read: it reproduces every published
v8.11 gate exactly (True Test filter 93.57%, paired balanced 81.12%, Shadow
balanced 43.55%, AUROC 0.8150, CelebA 99.73%, StyleGAN2 99.60%, Alibaba 98.17%,
stress 3.7134%) and independently reproduces Cell C's published numbers.

**Candidate**: `shufflenet_v2_layer1_v812.pth` (Layer1, unchanged, already on
disk) + `shufflenet_v2_layer2_v815ablation_cellA_unfreeze0_inv0.pth` (Layer2
dual-head, unchanged, already on disk), `fake_threshold = 0.14`,
`filter_threshold = 0.50`. **No retraining is involved and no new checkpoint is
introduced** — this is a routing/threshold change over two checkpoints that
already exist.

| Freeze-Gate A metric | gate | v8.11 (prod) | **candidate** | Δ |
|---|---:|---:|---:|---:|
| True Test fake recall | ≥95% | 99.63% | 99.63% | 0.00 |
| True Test filter recall | ≥90% | 93.57% | 93.98% | +0.40 |
| True Test paired balanced | ≥80% | 81.12% | 80.32% | **−0.80** |
| AIGuard-unseen AUROC | ≥0.80 | 0.8150 | 0.8014 | **−0.0136** |
| CelebA real recall | ≥95% | 99.73% | 99.53% | −0.20 |
| StyleGAN2 not-real recall | ≥95% | 99.60% | 99.53% | −0.07 |
| Alibaba filter recall | ≥95% | 98.17% | 96.61% | **−1.56** |
| fp32 TFLite combined size | ≤25 MB | 20.91 MB | ~20.6 MB (same 2 nets) | ≈0 |

| Stretch goal | target | v8.11 | **candidate** | Δ (paired bootstrap, 10k) |
|---|---:|---:|---:|---|
| fake+filter stress error | ≤2% | 3.71% | **2.97%** | **−0.74pp, 95% CI [−1.27, −0.26]** |
| Shadow paired balanced | ≥60% | 43.55% | **52.69%** | **+9.13pp, 95% CI [+6.27, +12.01]** |
| Shadow filter recall | ≥40% | 10.04% | 32.26% | +22.24pp [+17.20, +27.24] |
| Shadow real recall | ≥80% | 77.06% | 73.12% | **−3.95pp [−7.17, −0.72]** |

Error-direction check on Shadow clean-real photos (product-relevant, per the
project's per-class rule): false **accusations** (real → "fake") go 53 → 51; the
extra errors land in the softer real → "filter" bucket (11 → 24).

**Operating-point discipline (Known trap #1)**: `fake_threshold = 0.14` was NOT
read off any gate. It was selected on a disjoint dev set by a rule declared in
advance (`results/research/p1_r8_shadow_composite_tradeoff_20260819/ROUND_LOG.md`,
Round 5): the largest threshold whose error on `stressdev` — 300 AIGuard/**fake**
source images × 8 stress conditions, stem-disjoint from AIGuard/unseen, from all
gate sets and from all Layer2 train/val splits — is ≤ production's error on that
same set (1.0208%). The comparison is therefore made at a **matched dev operating
point**, and the gate improvement is a genuine transfer, not a rescaled threshold.

Result files: `results/research/p1_r8_shadow_composite_tradeoff_20260819/`
(`gates_R5_cellA_tf014.json`, `gates_A0_v811_production.json`,
`fake_threshold_selection_r5.json`, `frontier_analysis.json`,
`decomposition.json`, `ROUND_LOG.md`, `P1_R8_FINAL_FINDINGS.md`).

## 3. Expected benefit

- fake+filter stress error 3.71% → **2.97%** (−20% relative), the safety metric
  every version since v8.12 has moved the wrong way.
- Shadow paired balanced 43.55% → **52.69%**: production's decision on that
  photography domain stops being anti-informative (crosses the 50% degenerate
  baseline for the first time in a production-shaped configuration).
- No new checkpoint, no retraining, no change in artifact size or latency
  (same two-network cascade; Layer1 v812 and the Cell-A Layer2 both already
  exist on disk).

## 4. Risk / regression

- **Three Freeze-Gate A metrics regress beyond this round's pre-declared noise
  tolerance** (±0.5pp recall, ±0.005 AUROC): True Test paired balanced −0.80pp,
  AIGuard-unseen AUROC −0.0136, Alibaba filter OOD −1.56pp. All three still pass
  their absolute gates (80.32% ≥ 80%, 0.8014 ≥ 0.80, 96.61% ≥ 95%) but the AUROC
  and paired-balanced margins become thin (0.0014 and 0.32pp respectively).
  **This is the reason the proposer does not recommend promotion.**
- Shadow real recall −3.95pp: fewer genuine VGGFace2-style photos are called
  real. Mitigating evidence: the shift is toward "filter", not "fake".
- Layer1 changes from `v811d` to `v812`, so every published v8.11 Layer1 number
  (Shadow real recall, robustness-gate tables) would need re-measurement, not
  just the Layer2 ones.
- The Layer2 becomes a **dual-head** model whose output contract differs from the
  current 2-class Layer2 (`p_fake`, `p_filter` sigmoids vs a softmax). Any
  downstream consumer of Layer2 probabilities — including the mobile export path
  (`export_mobile_tflite.py`, `mobile_fft.py`) and the Phase 2 explanation
  adapters — must be re-verified; the 20.91 MB / 14.4 ms mobile figures were
  measured on the 2-class Layer2 and would have to be re-measured.
- The dual head's `filter_head` has a documented cross-source failure
  (registry P1-1/P1-2: DF40-cdf joint recognition ≈2-5%), so promoting it must
  not be accompanied by any new cross-source claim.

## 5. Exact files affected (IF approved — none touched today)

- `pipeline.py`: `LAYER1_WEIGHTS_PATH` → `shufflenet_v2_layer1_v812.pth`;
  `LAYER2_WEIGHTS_PATH` → `shufflenet_v2_layer2_v815ablation_cellA_unfreeze0_inv0.pth`;
  `DualBranchModel` Layer2 → `DualHeadModel`; `hierarchical_predict()` decision
  rule → `p_manip<0.5 → real`; `p_fake>0.14 → fake`; `p_filter>0.50 → filter`;
  else `real`.
- `docs/releases/v8.11_production/` — superseded, requires a new release folder.
- `CLAUDE.md`, `TODO.md`, `docs/EXPERIMENT_REGISTRY.md` — current-best pointers.
- No checkpoint file is created, renamed, moved or deleted.

## 6. Test plan (post-change, all with explicit checkpoint paths)

1. `eval_p1_r8_full_gates.py` on the promoted configuration — must reproduce
   `gates_R5_cellA_tf014.json` exactly.
2. `AIGuard/stress_test_v811_pipeline.py` (dual-head variant required) and
   `eval_v811_gates.py` — independent re-measurement through the legacy scripts.
3. `AIGuard/eval_robustness.py` — the full robustness gate re-run, **per-class
   recall reported**, because Layer1 changes.
4. `verify_mobile_fft.py` + `export_mobile_tflite.py` +
   `benchmark_mobile_artifacts.py` — re-verify the ≤25 MB / latency gate against
   the dual-head Layer2 (this is a hard blocker before any deployment claim).
5. `phase2_composite_explanation.py` — confirm the explanation schema still holds.

## 7. Rollback plan

Revert the `pipeline.py` edits (git working tree; the two frozen v8.11
checkpoints are never modified, so rollback is a pointer change only) and
re-run step 1 against `shufflenet_v2_layer1_v811d.pth` +
`shufflenet_v2_layer2_v811.pth`, which must reproduce
`gates_A0_v811_production.json` exactly. Frozen production hashes for
verification (re-hashed 2026-08-19, byte-identical to the P1-R6/P1-R7 record):

- `shufflenet_v2_layer1_v811d.pth` — `3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7`
- `shufflenet_v2_layer2_v811.pth` — `8470ad52dadcdb44a6789067efbbd7fbc20715cb3f4e3339630191889a55057e`

## 8. Approval record

> **PENDING — left deliberately blank for a human reviewer.**
> The proposer (Member A) is nominally the designated reviewer under
> `docs/team/PRODUCTION_CHANGE_CONTROL.md` but **must not self-approve a proposal
> it wrote**. No approval has been given by anyone. Nothing in the "Exact files
> affected" list has been modified.

| Reviewer | Date | Decision (approve / reject / needs work) | Notes |
|---|---|---|---|
| _(pending)_ | | | |
