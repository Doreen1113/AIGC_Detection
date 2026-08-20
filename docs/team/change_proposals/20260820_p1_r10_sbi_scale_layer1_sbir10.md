# Change proposal — 2x-scaled SBI Layer1 (`layer1_p1_r10_SBIR10.pth`) as a Pareto ALTERNATIVE to production

- **Date**: 2026-08-20
- **Proposer**: Member A (P1-R10 autonomous research round)
- **Round**: `p1_r10_sbi_scale_and_resolution_20260820`
- **Status**: PROPOSED — Approval Record (§8) deliberately **blank**. An agent
  must not self-approve.
- **Proposer's own recommendation**: **DO NOT promote by default.** This is
  deliberately a weaker recommendation than P1-R9's proposal. The candidate is
  the first arm in the project's history to meet the ≤2% fake+filter stretch
  goal (0.79%) and it beats the current production on every manipulation-side
  axis measured, but it is **clearly worse than current production** on
  AIGuard-unseen ranking quality and on clean out-of-domain real recall. It is
  submitted as a documented Pareto point and as a **conditional** option for a
  deployment whose cost function is dominated by fake+filter safety — not as a
  drop-in upgrade.

---

## 1. Problem statement

P1-R9 promoted `shufflenet_v2_layer1_v817sbi.pth` (SBIAUG) and left one
question explicitly open, calling it "the single most valuable open follow-up":
**does SBI keep helping past ~22K pairs, or does it plateau like fake-source
diversity did (P1-5 / P1-R7)?** P1-R9's own Round 4 could not answer it — its
generator collapsed from ~1,150 to ~22 img/min and the round was abandoned as
"infrastructure, not evidence".

## 2. Evidence

Full write-up: `results/research/p1_r10_sbi_scale_and_resolution_20260820/P1_R10_FINAL_FINDINGS.md`
(+ `PRE_DECLARED_PROTOCOL.md`, `ROUND_LOG.md`; hypotheses and verdict rules
recorded before any result was read).

**The bottleneck was diagnosed, not worked around blindly.** Root cause:
external machine-level I/O contention on this shared host — established by four
decisive tests (flat RSS; the same pool/code running at 1,592 img/min today;
identical source-megapixel distributions in the fast, collapsed and burst
regions of the aborted run; and a full-speed recovery burst mid-run that no
in-process cause can produce). `sbi/sbi_fast.py` then made the pipeline immune
to that class of failure (parallel + redundant-I/O elimination + chunk
checkpoint/resume + throughput watchdog), reducing the job from a projected
**33 hours to 219 seconds**. A **bit-identity gate** (`bit_identity_gate.json`)
proves the parallel driver's outputs are byte-identical to the original serial
generator, so this is a legitimate scaling comparison and not a different
dataset.

**Candidate.** 44,297 SBI pseudo-fakes + 44,297 degradation-matched real
negatives over five base families (adding `AIGuard/real`, 12,000), all 8
integrity gates 0, 98.3% of SBI base photos also present as label-0 real rows.
Split `splits/research/p1_r10_sbi_scale_20260820/layer1_sbi_r10_train.txt`
(300,968 rows). Training recipe byte-identical to P1-R9's, single axis changed.
Layer2 held byte-frozen at `shufflenet_v2_layer2_v811.pth` throughout.

**Operating point.** Unlike P1-R9's arms, the candidate is **not**
calibration-matched at tm=0.5 (dev false-manipulated 2.895% vs production's
6.369%). Known trap #1 applies directly; the dev rule selects **tm = 0.355**,
and every number below is at each arm's own dev-matched point.

| gate | Freeze-Gate A | **production v8.17 (SBIAUG)** | **candidate SBIR10** | Δ |
|---|---|---:|---:|---:|
| True Test fake recall | ≥95 | 99.63 | 99.63 | 0.00 |
| True Test filter recall | ≥90 | 91.97 | **93.98** | **+2.01** |
| True Test real recall | — | 72.29 | 69.48 | −2.81 |
| True Test paired balanced | ≥80 | 82.13 | 81.73 | −0.40 |
| AIGuard-unseen AUROC | ≥0.80 | 0.8411 | 0.8031 | **−0.0380** |
| CelebA real recall | ≥95 | 99.20 | 96.23 | **−2.97** |
| StyleGAN2 fake recall | ≥95 | 99.63 | 99.27 | −0.36 |
| Alibaba filter recall | ≥95 | 97.91 | **99.13** | **+1.22** |
| Shadow real recall | — | 73.48 | 64.52 | **−8.96** |
| Shadow filter recall | — | 12.54 | **13.26** | +0.72 |
| Shadow paired balanced | — | 43.01 | 38.89 | −4.12 |
| **fake+filter stress error** | ≤5 (stretch ≤2) | 2.36 | **0.79** | **−1.57**, stretch met |
| FF++ Layer1 AUROC | — | 0.5611 | **0.5812** | +0.0201 |

**All Freeze-Gate A gates pass.** No absolute gate is breached.

### 2.1 Threshold-only frontier (P1-R8 discipline)
Arm − frozen-production threshold-only frontier, Layer1 primary endpoint (pp):

| budget | 0.5 | 1.0 | 2.0 | 3.0 | 3.71 | 5.0 | 7.5 | 10 | 15 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SBIAUG (production) | +4.12 | +3.05 | +4.48 | +3.58 | +3.41 | +3.41 | +3.41 | +3.41 | +3.41 |
| **SBIR10** | **+8.24** | **+5.38** | **+5.20** | **+4.30** | **+3.94** | **+3.94** | **+3.94** | **+3.94** | **+3.94** |

Above the frontier at 9/9 budgets on both the Layer1 and end-to-end views, and
above the current production at 9/9 (Layer1) / 8/9 (end-to-end). **SBI scaling
does not plateau.**

### 2.2 Known trap #1 — matched real-side operating points (vs production v8.11)
Shadow Layer1 manip-routing **6/6 better** (+7.7 to +10.4pp); Shadow end-to-end
filter recall **6/6 better**; fake+filter stress error **6/6 better** (−0.44 to
−2.01pp); True Test filter recall at matched True Test real recall 3 better /
1 equal / 2 worse. Strongest trap-#1 result in the P1-R2→R10 chain.

### 2.3 Known trap #2 — low-FPR region. **This is the reason for the negative recommendation.**

| arm | AUROC | pAUC≤5% | TPR@1% | TPR@5% | TPR@10% |
|---|---:|---:|---:|---:|---:|
| PROD v8.11 | 0.8150 | 0.0852 | 0.0093 | 0.2778 | 0.4630 |
| **production v8.17 (SBIAUG)** | **0.8410** | **0.1630** | **0.0370** | **0.3241** | **0.4815** |
| SBIR10 | 0.8027 | 0.0696 | 0.0139 | 0.2083 | 0.4028 |

SBIR10 beats the older v8.11 on TPR@1% but is **worse than the checkpoint
currently in production on all four low-FPR statistics**, and its ΔAUROC vs
v8.11 (−0.0122) is not significant. Trap #2 is precisely the check that surfaces
this, and it is reported rather than buried.

### 2.4 Mechanism (consistent across every measurement)
SBI scale moves the model **monotonically toward "manipulated"**. Manipulation
side improves with scale (stress 3.71 → 2.36 → 0.79%; FF++ 8/8 matched points;
Shadow filter recall 10.04 → 12.54 → 13.26). Clean-OOD-real side degrades with
scale (CelebA 99.73 → 99.20 → 96.23; Shadow real 77.06 → 73.48 → 64.52;
unseen pAUC≤5% 0.0852 → 0.1630 → 0.0696). P1-R9 Round 3's degradation-matched
real negatives mitigated this at 1x volume; at 2x volume with a new **in-domain**
base family (`AIGuard/real`) the mitigation is no longer sufficient.

### 2.5 Mobile deployment budget
The candidate's architecture is byte-identical to production's Layer1, and the
production two-stage fp32 TFLite pair was **re-measured this round through the
full G1–G4 path**: **20.91 MB / 15.7 ms/img at 224px**, reproducing the
published 20.91 MB exactly. **No size or latency change** from this proposal.

## 3. Expected benefit (if approved)
- fake+filter end-to-end error 2.36% → **0.79%**, meeting the ≤2% stretch goal
  that has been open since v8.4.
- True Test filter recall +2.01pp, Alibaba OOD filter recall +1.22pp.
- FF++ zero-shot fake catch +0.8 to +4.5pp at 8/8 matched real-recall points.
- Shadow Layer1 routing +9pp over the current threshold-only frontier at the
  tightest budgets.

## 4. Risk / regression — why the recommendation is "do not promote by default"
1. **AIGuard-unseen ranking quality regresses materially** (AUROC −0.0380;
   pAUC≤5% halves; TPR@1% 0.0370 → 0.0139). For any deployment operating at a
   low false-positive budget on real user photos, this is the metric that
   matters most and the candidate is worse.
2. **Clean OOD real recall regresses** (CelebA −2.97pp, Shadow real −8.96pp) —
   i.e. more real photographs of unfamiliar photographic style get called
   manipulated. This is a user-facing false-accusation risk.
3. **End-to-end Shadow paired balanced falls** 43.01 → 38.89, because the frozen
   2-class Layer2 still caps it (~57.9%) and the Layer1 gain cannot express
   itself end-to-end.
4. The trade is **monotone in scale**, so "just scale further" is predicted to
   steepen the cost, not resolve it. 4x was not tested.

**Conditional case for approval**: if and only if the deployment's cost function
is dominated by fake+filter composite safety (the ≤2% stretch goal) and can
tolerate ~3pp more false-manipulated on clean OOD real photography, SBIR10 is
the better checkpoint. Otherwise production v8.17 should stay.

## 5. Exact files affected (if approved)
- `pipeline.py`: `LAYER1_WEIGHTS_PATH` → `shufflenet_v2_layer1_sbir10.pth`
  (copy of `checkpoints/research/p1_r10_sbi_scale_20260820/layer1_p1_r10_SBIR10.pth`,
  sha256 `0279412f24e8a3bfae73a0c6da72bdb57dae0bd591ea6604cd7005506c9fb30c`).
- `pipeline.py`: the Layer1 decision threshold must change from 0.5 to
  **0.355** — the candidate is not calibration-matched at 0.5 and promoting it
  without this change would silently move the operating point.
- `LAYER2_WEIGHTS_PATH`: **unchanged** (`shufflenet_v2_layer2_v811.pth`).
- `CLAUDE.md` / `TODO.md` / `docs/EXPERIMENT_REGISTRY.md`: version pointer.
- **Nothing else.** No split, no Layer2, no existing checkpoint is modified.

## 6. Test plan (after applying, before declaring done)
1. Re-run `eval_p1_r10_full_gates.py --manip-threshold 0.355` on the promoted
   file and confirm bit-for-bit reproduction of §2's table.
2. `pipeline.py` smoke test, single-image and batch, schema v2.0.0 unchanged.
3. Re-run `export_p1_r10_resolution_tflite.py --resolutions 224` and confirm
   G1–G4 pass and 20.91 MB total.
4. Confirm `shufflenet_v2_layer2_v811.pth` sha256 still `8470ad52…`.

## 7. Rollback plan
Restore `LAYER1_WEIGHTS_PATH` to `shufflenet_v2_layer1_v817sbi.pth` (sha256
`e3057270…`, unchanged on disk) and the threshold to 0.5. Single-line revert;
no data or checkpoint is destroyed by this proposal.

## 8. Approval record

| field | value |
|---|---|
| Reviewed by | |
| Decision | |
| Date | |
| Notes | |
