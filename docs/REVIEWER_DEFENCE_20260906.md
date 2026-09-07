# Reviewer defence matrix (2026-09-06)

Every question a reviewer of *"Filter-aware lightweight face manipulation detection"* would ask,
the answer we can give **today**, and — where the answer is not yet good enough — the experiment
that is running to fix it. Nothing in the "answer" column is aspirational: each cell cites a file
that can be recomputed.

Legend: 🟢 answerable now · 🟡 running · 🔴 open limitation (must be written as a limitation)

---

## A. The design (why a third class)

| # | Reviewer question | Answer | Evidence |
|---|---|---|---|
| A1 | "Adding a `filter` class is trivial. What is the contribution?" | 🟡 It is not a convenience, it is a **necessity**: a binary detector has one threshold, and beauty filters move filtered-*real* and filtered-*fake* faces the same way along it, so no threshold and no label choice can fix both. Controlled proof: 4 models, identical backbone/data/recipe/seed, **only the label space differs** (filter→real, filter→fake, filter-absent, 3-way). | `ternary_necessity_20260906/` (running) |
| A2 | "Maybe your architecture, not the third class, is doing the work." | 🟢 **Our own architecture trained the literature way scores 23.3 % false accusation — the same as the published detectors — while the 3-way version scores 0 %.** Same backbone, same parameters, same input pipeline. | `external_baselines_20260905/cost_vs_safety.md` rows *Ours* vs *Ours-arch, FF++ recipe* |
| A3 | "Is `filter` even well defined?" | 🟢 Identity-preserving beautification, four named algorithms with published parameters, generated from paired source images; semantic definition (not implementation-based) is fixed in `CLAUDE.md` and predates all experiments. | `CLAUDE.md` class definition; `filters/generate_*.py` |
| A4 | "Why hierarchical rather than flat 3-class?" | 🟢 Both were built and measured under one harness; the trade-off is documented (flat wins Shadow filter recall and unseen AUROC, hierarchical wins the safety metric). | `FLAT3CLASS-REVISIT-20260828` registry entry |

## B. The headline claim (does it beat others)

| # | Question | Answer | Evidence |
|---|---|---|---|
| B1 | "Show me a same-protocol comparison, not literature numbers." | 🟢 13 models, 13,026 identical images, 3 protocols, per-image scores on disk, cluster-bootstrap CIs, threshold-matched. First such benchmark in the filter-aware setting. | `external_baselines_20260905/` |
| B2 | "What do you actually win?" | 🟢 At a matched 5 % FPR on clean real faces, beauty filters push **every** published detector to 22.5–33.7 % false accusation of ordinary beautified faces; ours is **0.0 %** [0.0, 0.0], 13/13. | `analyze.py` P3, `cost_vs_safety.md` |
| B3 | "At what cost?" | 🟢 5.06 M params / 20.6 MB / 43 ms CPU — median 4.3× fewer parameters and 7.1× faster than the published detectors (UnivFD needs 427.6 M). | `cost.json`, `measure_cost.py` |
| B4 | "That is your own filter data. Third-party?" | 🔴 **We lose.** On Celeb-DF-B (Libourel et al., IWBF 2024) ours falsely accuses 74 % of beautified real frames vs SBI's 19 %. Root cause found and being tested, see C2. Reported in the same table, not hidden. | `external_baselines_20260905/FINDINGS.md` §2 |
| B5 | "Are the baselines fairly treated?" | 🟢 Each runs its own official preprocessing and published threshold, plus a threshold-matched operating point; one pre-declared verdict rule was found to be degenerate (matched recall drove baselines to 89–100 % FPR) and is reported as **not citable** rather than used to claim a win. | `FINDINGS.md` §1 |

## C. Generalisation

| # | Question | Answer | Evidence |
|---|---|---|---|
| C1 | "Cross-dataset AUROC 0.57 is poor." | 🟢 Acknowledged and diagnosed, not excused: the **same architecture** trained on FF++'s official split reaches 0.9155, so it is training-data coverage, not architecture. The paper positions itself as filter-aware detection, not cross-domain SOTA. | `ffpp_protocol_20260823` |
| C2 | "Why does your model call third-party real video frames fake?" | 🟡 Specific mechanism found: training contains **11,735 diffusion fakes generated from Celeb-DF real frames and zero Celeb-DF reals** — the model can separate the classes by corpus alone. Ablation running: remove those rows, predict the false-accusation rate drops. | `cdf_shortcut_20260906/` (queued) |
| C3 | "Do you have a leakage problem?" | 🟢 Repeatedly audited and self-reported, including a case where our own published "OOD" claim was retracted (63.8 % content overlap in StyleGAN2). Contamination assertions run per round. | `p1_r11_leakage_scaling_20260820`, per-round `contamination_assertions.json` |
| C4 | "One seed?" | 🟢 Two seeds on every claim that survived; a candidate that passed on seed 1 (FAM3, stress 3.757 vs CI edge 3.760) was **refuted by its own pre-registered seed 2** and withdrawn. | `P1A1-INTERFERENCE-20260905` |

## D. Explainability

| # | Question | Answer | Evidence |
|---|---|---|---|
| D1 | "Is your heatmap faithful?" | 🔴 **No, and we say so.** Grad-CAM++ is statistically indistinguishable from a fixed centre-Gaussian prior and fails the Adebayo head-randomisation check. Anything relying on it is presented as a null result. | registry `EVAL-2`, `faithfulness_eval.py` |
| D2 | "Then what is your explanation?" | 🟢 Structured output (class, artifact type, evidence region, raw non-calibrated score, template sentence) with a trained patch evidence head that passes 4/6 pre-declared faithfulness cells; the 2 failing cells were **proven structurally unbeatable** (a GT-mask oracle also fails them). | `P2A1-EVIDENCEHEAD-R2-20260828` |
| D3 | "Confidence values?" | 🟢 Calibration was tested and failed on OOD, so the product prints raw scores explicitly labelled non-calibrated instead of a fake percentage. | `eval2_calibration_20260826` |
| D4 | "Human evaluation?" | 🔴 Not done (out of scope by decision). Stated as a limitation. | — |
| D5 | "Did you use a VLM teacher as your proposal promised?" | 🟡 Qwen2-VL-7B + LoRA training now on FakeClue's 23,961 annotated face clues + 9,000 project images; will serve as the proposal's control group and as a clue-tag teacher distilled into a ≤0.1 M-param head, with a pre-declared fidelity bar (macro-F1 ≥ 0.70) and a deletion-faithfulness bar. | `vlm_teacher_20260906/` (running) |

## E. Deployment

| # | Question | Answer | Evidence |
|---|---|---|---|
| E1 | "Does it actually run on a phone?" | 🟡 fp32 TFLite exported and verified (20.9 MB, 769/769 decisions identical to PyTorch); an Android app mirroring the production decision path is written; **real-device latency not yet measured** — needs a cloud device farm account. | `mobile_export/v817_20260822/`, `android_benchmark_20260905/` |
| E2 | "The FFT branch cannot be deployed." | 🟢 It could not (unresolvable custom op). Rewritten as a fixed-size DFT = constant matrix multiply: mathematically equivalent, zero retraining, existing weights reused, bit-identical decisions. | `mobile_fft.py`, `verify_mobile_fft.py` |
| E3 | "Why not int8?" | 🟢 Root-caused, not hand-waved: FFT magnitude has 7.6 × 10⁹ dynamic range; per-tensor quantisation zeroes 98 % of spectrum bins and outputs NaN. A split int8 path exists for the spatial branch. | `diagnose_int8_collapse*.py`, `arch2_int8_split_20260831` |
| E4 | "Why ShuffleNetV2 and not the MobileNetV4 your proposal named?" | 🟢 Both measured at selection time (0.9987 vs 0.9981 AUROC, ShuffleNet smaller); later FF++ benchmarking found MobileNetV4/RepViT beat it, recorded and **not** hidden — the backbone was not switched on single-seed evidence. | `ffpp_improve_20260823` |

## F. The specific question the supervisor asked ("fake + filter?")

| # | Question | Answer | Evidence |
|---|---|---|---|
| F1 | "A deepfake with a beauty filter on top — what happens, and how much do you solve?" | 🟢 A dedicated protocol exists (287 held-out fakes × 8 filter conditions = 2,289 images). Ours: **2.80 %** escape [1.92, 3.76]. Published detectors cannot even detect these fakes unfiltered (AUROC 0.45–0.70 vs ours 0.995), and for all of them the *filtered* AUROC is **higher** than the unfiltered one — they are detecting the filter, not the fake. | `analyze.py` P1 |
| F2 | "Is 2.80 % honest?" | 🟢 Decomposed by our own audit: 2.11 pp is filter-attributable, the rest is base failure on 26.6 % of source images; and the metric's 8× counting flaw (one failed source counted 8 times) was self-disclosed. | `FROMSCRATCH-AUDIT-20260904`, `tier1_audit_actions_20260904` |
| F3 | "Better than others by how much?" | 🟡 On this protocol the comparison is not citable as a win (see B5). The citable win is B2/B3. | — |

---

## What is still genuinely missing (write these as limitations, do not spin them)

1. Third-party filter generalisation (B4) — losing today; C2 is the live attempt.
2. Real-device latency (E1) — blocked on an account, engineering ready.
3. Heatmap faithfulness (D1) — null result, stays null.
4. Human evaluation of explanations (D4) — not done.
5. Cross-dataset detection SOTA (C1) — out of scope by positioning, with the frontier documented.

## Addendum 2026-09-07 — "Why not a stronger backbone?" (closed)
MobileNetV4 was tested twice: flat three-way (`backbone_swap_20260907`, frontier KEEP on 2 seeds, but stress
11.36% / Alibaba 72.4% at the native rule) and inside the production hierarchy (`backbone_hier_20260907`:
6/8 gates fail, stress 15.12%, Alibaba 57.31%, unseen AUROC 0.765). Answer to a reviewer: the safety property
comes from the ternary label space, not the backbone; a better forgery backbone does not transfer to
composite attacks or third-party retouching under our data. Deployed system stays ShuffleNetV2 (v8.17).
