# FINDINGS — MobileNetV4 in place of ShuffleNetV2 on the filter-aware task (`backbone_swap_20260907`) — **KEEP**

Pre-registered question (`PRE_DECLARED.md`): every backbone comparison in this project says
ShuffleNetV2 is the weakest candidate, but all of that evidence is on the *forgery-detection*
axis. The entire safety case rests on ShuffleNetV2 and the substitution had never been tested.

## 0. Verdict: KEEP

One arm trained; the control (`ternary_necessity_20260906` TERN) already existed from the same
script, data, recipe and seed, so the comparison isolates the backbone. Both read at the same
matched operating point (4.80 % FPR on 250 clean real faces). Paired bootstrap clustered by
source image, $N_B = 10{,}000$.

| axis | ShuffleNetV2 (control) | **MobileNetV4** | paired $\Delta$ | 95 % CI | |
|---|---|---|---|---|---|
| FA — 249 filtered genuine faces called `fake` | 8.84 % [5.22, 12.45] | **2.81 % [0.80, 4.82]** | **−6.43 pp** | [−10.44, −2.41] | **improves, significant** |
| MISS — 2,289 filtered fakes not called `fake` | 1.97 % [1.22, 2.80] | 2.71 % [1.83, 3.65] | +0.74 pp | [−0.22, +1.71] | no significant change |
| clean fake recall (287) | 98.61 % [97.21, 99.65] | **100.00 %** | — | — | improves |

Per the pre-declared rule (KEEP = neither safety axis degrades outside its paired CI):
**KEEP**. One safety axis improves significantly, the other does not significantly degrade,
and clean fake recall is perfect.

At the native three-way decision rule both arms accuse zero filtered genuine faces, and
MobileNetV4 routes **95.58 %** of them to the `filter` class (ShuffleNetV2 94.78 %).

## 1. Combined with the forgery-axis evidence, the case for switching is now complete

| | ShuffleNetV2 (current production) | MobileNetV4 |
|---|---|---|
| filter-aware FA / MISS (this round) | 8.84 % / 1.97 % | **2.81 %** / 2.71 % |
| FF++ in-domain AUC | 0.9155 | **0.9383** |
| Celeb-DF-v2 zero-shot | 0.7286 | **0.7932 / 0.8325** (two seeds) |
| DFD zero-shot | 0.8487 | **0.9062 / 0.8916** (two seeds) |
| CPU latency (batch 1, 4 threads) | 19.0 ms | **14.1 ms** |
| parameters (3-way, with FFT branch) | 2.53 M | 3.90 M |

MobileNetV4 is better on every measured axis except parameter count, and it is *faster*
despite being larger. It is also the backbone the project's own proposal specified before we
deviated to ShuffleNetV2 — that deviation is now measured, and it cost us.

## 2. Caveats, stated rather than buried

* **Single seed per arm.** The pre-declaration already said a positive result is a candidate
  requiring a second seed, not a promotion. On the cross-dataset side we measured a 3.93-point
  seed spread (`FILTER-AUX-20260907`); the in-house paired sets here are better conditioned
  (249 images, and 2,289 images over 287 source clusters) but the caveat stands.
* **One-image precision artifact.** `frontier.json` computes at full precision (FA = 7/249 =
  2.81 %); the paired test reads the per-image dumps, which are written to six decimals, and
  one image whose score sits within 5e-7 of the threshold flips, giving 6/249 = 2.41 % on that
  side. Both arms' dumps use the same precision so the paired comparison is internally
  consistent, and a one-image shift cannot move a 6.43-point gap whose CI excludes zero. The
  authoritative point estimate is 2.81 %.
* **Not a production change.** Production remains the ShuffleNetV2 hierarchical v8.17 stack.
  This round licenses the switch on evidence; promoting it requires a second seed, the full
  Freeze-Gate battery on the hierarchical (not flat) architecture, and a change proposal.
* **Correction carried from the control round.** `flat3_train.txt` references 20,295 rows whose
  files are missing, so both arms trained on **191,696** rows (65,566 real / 52,798 fake /
  73,332 filter), not the 211,991 recorded in `TERNARY-NECESSITY-20260906`. Both arms dropped
  the identical rows with identical class counts, so that round's conclusions are unaffected,
  but its row count is wrong and is corrected in the registry.

## 3. Claim / Non-claim

**Claim**: replacing ShuffleNetV2 with MobileNetV4 under an otherwise identical three-way
recipe significantly reduces false accusation of beautified genuine faces (−6.43 pp, CI
excluding zero), does not significantly change the filtered-fake miss rate, and raises clean
fake recall to 100 % — so the better forgery backbone does not trade away the safety
properties.

**Non-claim**: that this is a production promotion; that a second seed will replicate; that
RepViT or FastViT behave the same; that the hierarchical two-stage architecture inherits the
result (this round is the flat three-way variant). No production change, no git, LOCKBOX
never read.

## 4. Outputs

`PRE_DECLARED.md`, `make_scripts.py`, `train_arm.py`, `eval_frontier.py`, `paired_test.py`,
`frontier.json`, `paired_test.json`, `perimage_TERN_MNV4.tsv`, `train_TERN_mnv4_stdout.log`;
checkpoint `tern_TERN_mobilenetv4_seed20260906.pth` (3,899,747 parameters, best macro-F1
0.9479, 1,315 s).

## 8. Full Freeze-Gate battery at the native three-way rule (added 2026-09-07)

`eval_gates_flat3.py --arch mobilenetv4` (`gates_MNV4_stdout.log`), flat MobileNetV4 seed 20260906,
compared with the flat ShuffleNetV2 twin (`flat3class_revisit_20260828/gates_F1_full.json`) and production v8.17 read by the SAME harness (`flat3class_revisit_20260828/gates_PROD_full.json`; corrected 2026-09-07 from CLAUDE.md headline numbers to same-harness numbers).

| Gate | flat MNV4 | flat SNV2 twin | production v8.17 | gate |
|---|---|---|---|---|
| True Test fake recall | 99.63 | 99.63 | 99.63 | >= 99 PASS |
| True Test filter recall | 95.58 | -- | 91.97 | >= 90 PASS |
| True Test real recall | 67.07 | -- | 72.29 | (stretch, -5.2pp) |
| AIGuard/unseen AUROC | 0.8226 (p_fake) / 0.8272 (composite) | 0.8279 | 0.8410 (composite) / 0.7724 (p_fake) | >= 0.80 PASS (-0.014 on composite) |
| CelebA real recall (3,000) | 100.0 | -- | 99.33 | >= 99 PASS (+0.67) |
| StyleGAN2 fake recall (3,000 / decontam) | 99.9 / 99.8 | -- | 99.57 / 99.2 | >= 99 PASS (+0.3 / +0.6) |
| Shadow real recall | 94.27 | -- | 74.91 | (stretch, +19.4pp) |
| Shadow filter recall | 16.13 | -- | 12.19 | (+3.9pp) |
| **fake+filter stress (P1)** | **11.36** | 7.25 | 2.80 [1.92, 3.76] | <= 3.76 **FAIL** |
| **Alibaba filter recall** | **72.40** | 99.73 | 97.71 | >= 95 **FAIL** |
| FF++ 900-frame zero-shot AUROC (end-to-end, same harness) | 0.5502 | -- | 0.5597 | (stretch, -0.010) |
| FF++ official test frame AUROC | 0.5372 | -- | 0.5747 | (stretch, -0.037) |

**Verdict: NOT a clean win.** Two release gates fail (stress 11.36%, Alibaba 72.4%). The frontier KEEP
(Section 5) and these failures are not contradictory: the frontier is read at a matched operating point on
True-Test-style filters, whereas stress/Alibaba probe composite attacks and a third-party retouching
algorithm at the native rule. Confound: the flat label space alone raises stress from 2.80 to 7.25% (SNV2
twin), so the backbone's own contribution to the 11.36% cannot be isolated here. Follow-up:
`backbone_hier_20260907` (MobileNetV4 inside the production hierarchy, production splits, pre-declared).

## 9. Seed-2 replication of the frontier (2026-09-07)

First seed-2 run was invalid: `eval_frontier_s2.py` still had `SEED = 20260906` in the tuple
assignment, so it re-scored the seed-1 checkpoint (numbers identical to seed 1). Fixed, re-run on CPU
against `tern_TERN_mobilenetv4_seed20260907.pth` -> `frontier_s2.json`, `perimage_TERN_MNV4_s2.tsv`,
`paired_test_s2.py` -> `paired_test_s2.json`.

| seed | FA filt-real | MISS filt-fake | clean fake recall | paired vs SNV2: dFA | dMISS | verdict |
|---|---|---|---|---|---|---|
| 20260906 | 2.81 | 2.71 | 100.00 | -6.43 [-10.44, -2.41] | +0.74 [-0.22, +1.71] | KEEP |
| 20260907 | 2.81 | 2.49 | 99.65 | -6.02 [-10.04, -2.01] | +0.52 [-0.48, +1.57] | KEEP |

Frontier KEEP replicates across seeds. This does not change Section 8: the full-gate failures (stress,
Alibaba) are at the native rule and are what block production.

**Win/lose summary vs v8.17 (same harness):** wins — True Test filter +3.6pp, CelebA +0.7, StyleGAN2 +0.3,
Shadow real +19.4pp, Shadow filter +3.9pp, TT fake tie. Losses — **stress +8.6pp (FAIL)**, **Alibaba -25.3pp (FAIL)**,
True Test real -5.2pp, unseen AUROC -0.014, FF++ -0.01 to -0.04. Not "全面優於": it wins the in-house filter/real
gates and loses both external/safety gates that define the paper.
