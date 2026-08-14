# Project Catalog (Read-Only Inventory, Stage A)

> Generated 2026-08-13 as part of a strict read-only cataloging pass. Nothing in the
> repository was moved, renamed, or deleted to produce this document. See
> `docs/REORGANIZATION_PLAN.md` for the (unexecuted) future structure proposal.

## Phase map

| Phase | Definition (per CLAUDE.md / TODO.md) | Status as of 2026-08-13 |
|---|---|---|
| **Phase 1** | Static-image real/fake/filter classifier (v3→v8.16 lineage). Scope: single static face image, real/fake/filter 3-way decision. | **Frozen** as `Phase1-v8.11-freeze` (see TODO.md "🔒 Phase 1 Freeze Gate", 2026-08-13). All A-tier freeze-gate metrics pass except real-device (iPhone) benchmarking, which is still pending — hence "frozen research baseline / pre-deployment production baseline", not yet a fully verified mobile production model. |
| **Phase 2** | Explainability / XAI (Grad-CAM++ validation, region-level localization claims, structured explanation schema v2.1.0). | Active/ongoing. Most recent entries dated 2026-08-13 (Priority 0 Grad-CAM++ re-validation on production v8.11 checkpoints, whitening PointingGame diagnostic, XAI evidence-tier rules locked in `docs/phase2_story.md` §11). |
| **Phase 3** | Robustness / mobile deployment (TFLite export, int8 quantization diagnosis, FF++ zero-shot, Shadow domain-gap research, cross-source composite training v8.12–v8.16). | Research-track, explicitly **not** blocking Phase 1 freeze. Individual stretch goals (Shadow generalization, fake+filter ≤2% misclass, FF++ fake recall ≥70%, int8 deployment) remain open per Freeze Gate section B. |

## Production baseline (what `pipeline.py` actually loads)

Confirmed by reading `pipeline.py` directly (lines 52–53):

```python
LAYER1_WEIGHTS_PATH   = os.path.join(BASE, "shufflenet_v2_layer1_v811d.pth")
LAYER2_WEIGHTS_PATH   = os.path.join(BASE, "shufflenet_v2_layer2_v811.pth")
ARTIFACT_WEIGHTS_PATH = os.path.join(BASE, "artifact_classifier_v3.pth")
```

- **Layer1** (real vs manipulated): `shufflenet_v2_layer1_v811d.pth` — round4 hard-neg fine-tune, 2026-08-10.
- **Layer2** (fake vs filter, only runs if Layer1 says "manipulated"): `shufflenet_v2_layer2_v811.pth`.
- **Artifact classifier** (4-way smoothing/whitening/eye_enlarging/face_reshaping, only runs if final prediction is "filter"): `artifact_classifier_v3.pth`.
- All three files are confirmed present in repo root with matching filenames (verified via `ls`, not guessed).

## Research checkpoints (v8.12 – v8.16): purpose and status

All five are explicitly declared in CLAUDE.md's 2026-08-13 freeze entry as
**"Phase 1 之後的研究支線結果，定位為論文研究章節證據，不進 pipeline、不取代 v8.11"**.

| Version | Checkpoint file(s) found on disk | Purpose | Status |
|---|---|---|---|
| **v8.12** | `shufflenet_v2_layer1_v812.pth`, `shufflenet_v2_layer2_v812.pth` | Base-image diversity experiment for filter training (addresses Shadow domain-gap diagnosis). Confirmed the diagnosis correct but at a cost. | Research candidate / **rejected for production**: Shadow balanced accuracy 43.5%→55.7% (+12.2pp) but fake+filter misclass 3.71%→5.29% (regression). TODO.md: "暫不將 v8.12 上 production，維持 v8.11". |
| **v8.13** | `shufflenet_v2_layer1_v813.pth`, `shufflenet_v2_layer2_v813.pth` | Active hard-negative mining using the v8.12 pipeline against all 8 stress-test filter-strength conditions (previous hard-neg generation only covered 4). | **Rejected** — "誠實的負面結果，不是單純失敗": fake+filter misclass rose further to 5.72% (worse than v8.12). Root cause later diagnosed (mixed L1-miss/L2-miss training signal dilution) and addressed by v8.14. |
| **v8.14** | `shufflenet_v2_layer1_v812.pth` (frozen, reused) + `shufflenet_v2_layer2_v814.pth` | Route-filtered mining: Layer1 frozen at v812, only Layer2 fine-tuned on a mining condition that excludes Layer1-failure samples (fixes v8.13's diagnosed flaw). | **Research baseline, not promoted** — "淨正向、但不晉升 production": improved several stress conditions but Shadow real recall stayed at 73.1% (same as v8.12, i.e., did not recover), and whitening_medium regressed. `pipeline.py` kept pointing at v8.11. |
| **v8.15** | Multiple variants on disk: `shufflenet_v2_layer2_v815a_v812.pth`, `..._v815a_v814.pth`, `..._v815a_v814clean.pth`, `..._v815ablation_cellA_unfreeze0_inv0.pth`, `..._cellB_unfreeze0_inv1.pth`, `..._cellC_unfreeze1_inv0.pth`, `..._cellD_unfreeze1_inv1.pth`, `..._v815b_14.pth` | Dual-head factorized attribute classifier pilot (fake XOR filter → two independent sigmoid heads) plus a 2×2 ablation grid (unfreeze backbone × invert-label) to isolate which factor drives results. "Cell C" = `unfreeze1_inv0` variant, referenced in CLAUDE.md as **"v8.15-C@0.85"**. | Mixed: v8.15a dual-head pilot judged "誠實負面結果，frozen-backbone 拆 head 不足". Cell C ablation cell reported as "in-domain 已校準" (per CLAUDE.md) — a research candidate, **not production**. |
| **v8.16** | `shufflenet_v2_layer2_v816_mixedlineage.pth` | Source-diverse composite training ("mixed-lineage") targeting cross-source `has_filter` joint recognition generalization. | **Rejected as a generalization fix** — CLAUDE.md: "DF40-cdf cross-source joint recognition 2.02%→4.53%但whitening/幾何filter/pixart/sd2.1完全無殘留效果". Stretch-goal table (TODO.md §B) lists this metric still short of the ≥25% target. Retained as research/paper evidence only. |

No `.pth` file for a *plain* "v8.15" (non-suffixed) or any other v8.15/v8.16 naming pattern beyond what's listed above was found in the repo — all filenames above were located by grep, not guessed.

## Major datasets and purpose (from CLAUDE.md dataset table, cross-checked against `ls`)

| Dataset (root dir) | Role |
|---|---|
| `AIGuard/real/`, `AIGuard/fake/` | Primary real/fake training pool (DeepFake-450K derived) |
| `AIGuard/unseen/` | Held-out fake OOD eval (454 images, primary AUROC benchmark) |
| `FFHQ_four_process/`, `FFHQ_megvii_four_process/`, `FFHQ_ali_process/` | RetouchingFFHQ filter-processed training/OOD sources |
| `filter_data/` | Self-built filter dataset (4 types, 25,213 images) |
| `lfw/` | Real-face training source (v5+) |
| `sd2.1/`, `DiT/`, `SiT/`, `ddim/`, `pixart/` | DF40 EFS fake sources (top-level dirs, not under a `DF40/` subdir) |
| `FakeClue/`, `FakeClue_meta/` | Eval + Phase 2 distillation source (not Phase 1 training) |
| `WildDeepfake_subset/` | Deprecated eval source (semantic/video overlap with AIGuard/fake) |
| `stylegan2_test/` | StyleGAN2 static fake OOD eval (10,000 images) |
| `celeba_train/`, `celeba_val/`, `celeba_test/` | CelebA real-face partitions (train/val/OOD test) |
| `MidJourney/` | Fake source, partially used in v8.4/v8.5 splits |
| `Celeb-DF-v2/`, `FaceForensics_frames/`, `FaceForensics_raw/` | Video-frame sources — Phase 3 robustness / FF++ zero-shot only, not Phase 1 primary eval |
| `imdbwiki_raw/`, `imdbwiki_clean_sample/`, `imdbwiki_filter/`, `imdbwiki_v810_disjoint/`, `imdbwiki_v810_expanded/` | C1 base-image-diversity research track (v8.9d/v8.12+) |
| `shadow_vggface2_real/`, `shadow_filter/`, `shadow_diffswap_fake/`, `shadow_stylegan3_fake/` | "Shadow" domain-gap paired eval set (different base-image photography style than True Test) |
| `test_set_true/` | True Held-out Test Set source images (769 total: real/fake/filter, paired design) |
| `vggface2_test_sample/`, `vggface2_train_sample/`, `vggface2_filter_sample/` | Ultimate Test Set construction sources |
| `stargan/`, `StyleGAN3/`, `stylegan3_sample/`, `diffusionface_diffswap_sample/` | GAN/diffusion fake sources for Ultimate Test Set / Shadow set |
| `route_filtered_hardneg_v814/`, `route_filtered_hardneg_v814_df40/`, `fake_filter_hard_neg/`, `fake_filter_hard_neg_v88_backup/`, `fake_filter_hardneg_v813/` | Mined hard-negative pools for successive training rounds |
| `v810b_disjoint_filter_imdbwiki/`, `v810b_filter_imdbwiki_expanded/`, `v815_replication_set/`, `v815b_paired_consistency/`, `v816_composite/`, `v89_filter_imdbwiki/`, `v89_filter_vggface2train/`, `v89d_candidate_pool/`, `v89d_paired_mined/`, `v89d_proxy_unseen_pool/` | Generated/mined intermediate pools for specific version experiments |
| `ffhq/` | Base FFHQ source images |
| `FakeVLM_weights/` | Weights for the (rejected — "太重") FakeVLM teacher model |
| `review_all/`, `review_celebdf/`, `review_celebdf_real/`, `review_lfw_sample/`, `pipeline_test_input/`, `pipeline_test_output/`, `gradcam_output/`, `gradcam_failures/`, `explanation_output/` | Manual review / smoke-test staging outputs |
| `ios_benchmark/` | Mobile deployment benchmark staging (Phase 3) |

## Major `results/` subfolders and purpose

- `results/mobile_export/` — TFLite/ONNX export artifacts, Phase 3.
- `results/gt_vs_gradcam/`, `results/xai_evidence_heatmaps_20260812/`, `results/heatmap_test/`, `results/lab_diff_bleed_viz/`, `results/landmark_gt/` — Phase 2 XAI figure/evidence outputs.
- `results/leakage_analysis/` — data-leakage audit outputs (Phase 1 data integrity work).
- `results/baseline_v2_ckpts/` — early baseline checkpoints (historical, pre-v3).
- `results/abcd_cross_combination/` — the A/B/C/D Layer1×Layer2 cross-combination diagnostic (`eval_ABCD_cross_combination.py`) that isolated the v8.12/v8.13 trade-off to Layer2.
- Root-level files in `results/` are almost entirely per-run `.log`, `.json`, `.csv`, `.tsv` outputs named after the script/version that produced them (e.g. `stress_test_v811_pipeline.json`, `eval_v815_ablation_full.json`, `eval_v816_indomain_and_joint.log`) — see `docs/RESULTS_PROVENANCE.md` for the checkpoint-version mapping of the ones relevant to production vs research claims.

## Current most important entry points

- **`pipeline.py`** — sole production inference entry point (Layer1d + Layer2 v811 hierarchical classifier + artifact classifier + Grad-CAM++ + template explanation, schema v2.1.0). **Not modified by this task.**
- **Main eval scripts**: `AIGuard/eval_filter_recall.py` (True Test filter recall by type), `AIGuard/eval_truetest.py`, `eval_truetest_paired.py` (paired balanced-accuracy metric, the current primary True Test metric), `AIGuard/eval_celeba_real.py`, `AIGuard/eval_stylegan2.py`, `AIGuard/eval_ali_ood_v811.py`, `eval_v811_gates.py` (the full Freeze Gate table driver), `AIGuard/stress_test_v811_pipeline.py` / `AIGuard/eval_robustness.py` / `AIGuard/stress_test_layer1.py` (fake+filter stress test, now auto-named-output per weights loaded).
- **Main XAI scripts**: `phase2_p0_v811_filter_gradcam_validation.py` (production-checkpoint Grad-CAM++ re-validation, the authoritative current XAI evidence), `xai_faithfulness_blur_test.py` (current faithfulness metric, supersedes `xai_faithfulness_test.py`), `phase2_whitening_pointinggame_diagnostic.py`, `build_xai_evidence.py`, `build_phase2_evidence_pack.py`.
- **Mobile export**: `mobile_fft.py` (TFLite-compatible fixed-size DFT rewrite), `verify_mobile_fft.py`, `export_mobile_tflite.py`, `benchmark_mobile_artifacts.py`, `diagnose_int8_collapse.py` / `diagnose_int8_collapse2.py`.
- **Explainability library**: `explainability/gradcam.py`, `explainability/explain.py`, `explainability/lrp_baseline.py`.
