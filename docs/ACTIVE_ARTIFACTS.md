# Active Artifacts (Read-Only Inventory, Stage A)

> Read-only classification of root-level files: what's still runnable / load-bearing vs.
> safe-to-tidy-later. No files were moved. "Movable" here means "movable in a future,
> user-confirmed Stage B/C pass" — see `docs/REORGANIZATION_PLAN.md`.

## Core runtime (cannot move without breaking production inference)

| File | Purpose | Movable |
|---|---|---|
| `pipeline.py` | Sole production inference entry point. Hardcodes `BASE = r"C:\My_Project\AIGC"` and loads `shufflenet_v2_layer1_v811d.pth`, `shufflenet_v2_layer2_v811.pth`, `artifact_classifier_v3.pth`, `face_landmarker.task` from that absolute root. | **No** |
| `shufflenet_v2_layer1_v811d.pth` | Production Layer1 weights, loaded by `pipeline.py`. | **No** |
| `shufflenet_v2_layer2_v811.pth` | Production Layer2 weights, loaded by `pipeline.py`. | **No** |
| `artifact_classifier_v3.pth` | Production artifact (filter-subtype) classifier, loaded by `pipeline.py`. | **No** |
| `face_landmarker.task` (if present at root; referenced as `FACE_LANDMARKER_PATH`) | MediaPipe face-presence gate model, loaded by `pipeline.py`. | **No** |

## Active evaluation (currently the reference numbers cited in CLAUDE.md/TODO.md)

| File | Purpose | Movable |
|---|---|---|
| `AIGuard/eval_filter_recall.py` | True Test filter recall by type — cited directly in CLAUDE.md model tables. | No (path referenced by name in docs; moving requires updating all doc cross-references first) |
| `eval_truetest_paired.py`, `AIGuard/eval_truetest.py` | True Test paired balanced-accuracy — current primary Freeze Gate metric. | No, same reason |
| `AIGuard/eval_celeba_real.py`, `AIGuard/eval_stylegan2.py`, `AIGuard/eval_ali_ood_v811.py` | CelebA/StyleGAN2/Alibaba OOD gates. | No, same reason |
| `eval_v811_gates.py` | Full Freeze Gate table driver. | No |
| `AIGuard/stress_test_v811_pipeline.py`, `AIGuard/eval_robustness.py`, `AIGuard/stress_test_layer1.py` | Fake+filter stress test; recently fixed (2026-08-11) to auto-name outputs by loaded weights instead of a fixed filename — moving these now would be safe re: the auto-naming fix but should still wait for Stage C checkpoint review since they take root-relative weight paths as CLI args. | Conditionally — Stage C only |
| `eval_ABCD_cross_combination.py`, `analyze_L1_routing_shift.py` | Layer1×Layer2 diagnostic that isolated the v8.12/v8.13 regression to Layer2 — actively cited reasoning in TODO.md. | Yes, low risk (research script, output already captured in `results/`) |

## Active XAI (Phase 2, ongoing)

| File | Purpose | Movable |
|---|---|---|
| `phase2_p0_v811_filter_gradcam_validation.py` | Authoritative production-checkpoint (v8.11) Grad-CAM++ re-validation; supersedes v8.8-backbone findings. | Yes, low risk once Phase 2 doc cross-refs are checked |
| `phase2_whitening_pointinggame_diagnostic.py` | Root-cause diagnostic for the whitening PointingGame regression found by the above. | Yes |
| `xai_faithfulness_blur_test.py` | Current faithfulness metric (blur-based masking) — supersedes `xai_faithfulness_test.py` (constant-fill masking, superseded 2026-08-13 per TODO.md). | Yes |
| `build_xai_evidence.py`, `build_xai_localization_csv.py`, `build_phase2_evidence_pack.py` | XAI evidence-pack builders referenced by `docs/xai_evidence_schema.md`/`docs/phase2_story.md`. | Yes, low risk |
| `explainability/gradcam.py`, `explainability/explain.py`, `explainability/lrp_baseline.py` | Grad-CAM++ / explanation library, imported by `pipeline.py` (via `GradCAMPlusPlus`, though pipeline.py currently has its own inline copy — verify import graph before moving `explainability/`) | Check first — `pipeline.py` defines its own `GradCAMPlusPlus` class inline rather than importing from `explainability/gradcam.py`; the two may have diverged. Do not assume they're interchangeable. |

## Deployment (Phase 3, mobile)

| File | Purpose | Movable |
|---|---|---|
| `mobile_fft.py` | TFLite-deployable fixed-size-DFT rewrite of the FFT branch — mathematically verified equivalent, referenced in CLAUDE.md as the resolution to the "边缘部署" blocker claim. | No — treat as load-bearing for any future mobile-export rerun even though not imported by `pipeline.py` itself |
| `verify_mobile_fft.py`, `export_mobile_tflite.py`, `benchmark_mobile_artifacts.py` | Mobile export verification/benchmark chain, produces `results/mobile_deployment_benchmark.json` and `results/mobile_export/`. | Yes, as a group (keep together) |
| `diagnose_int8_collapse.py`, `diagnose_int8_collapse2.py` | int8 quantization failure root-cause scripts (superseded-by-later relationship between the two — `2` is the corrected version per CLAUDE.md "第一個假設被自己推翻"). | Yes |
| `measure_mobile_memory.py`, `verify_tflite_fp16.py` | Mobile benchmarking support scripts. | Yes |

## Data manifests / split builders

- All `build_v*_splits.py`, `build_v81*.py` … `build_v816*.py` files at root are **generators**, not the splits themselves — the actual training splits live in `splits/*.txt`/`.tsv` (106 files). The splits directory is the artifact that matters for reproducibility; the builder scripts are re-runnable but not guaranteed idempotent against current disk state without care (some depend on intermediate mined pools). See `docs/DEPRECATED_OR_HISTORICAL.md` for which builders are superseded.
- `sync_splits.py`, `rebuild_splits_from_clean.py`, `check_split_structure.py` — split-integrity tooling, still generically useful, low risk to move.

## Documentation

- `README.md`, `CLAUDE.md`, `TODO.md` — root-level project docs. `CLAUDE.md` explicitly instructs updates happen in place; **do not move**.
- `docs/*.md`, `docs/*.json`, `docs/*.txt` — all pre-existing, untouched by this task except the 7 new files this task adds.

## Explicit "cannot move" list with reasons

1. **`pipeline.py`** — task instructions forbid modifying it; it also hardcodes an absolute `BASE` path and bare filenames for all three production checkpoints, so any relocation of those checkpoints breaks it silently (no error until `torch.load` fails).
2. **`shufflenet_v2_layer1_v811d.pth`** — loaded by hardcoded relative-to-BASE path in `pipeline.py`.
3. **`shufflenet_v2_layer2_v811.pth`** — same.
4. **`artifact_classifier_v3.pth`** — same.
5. **`face_landmarker.task`** — same (face-presence gate, added 2026-08-11).
6. **`CLAUDE.md`** — is the project's single source of instruction truth per its own header; user/process explicitly maintains it in place.
7. **`TODO.md`** — declared single source of truth for TODOs since 2026-07-31 per CLAUDE.md.
8. **`splits/*.txt` referenced by name in CLAUDE.md's version tables** (e.g. `v85_train_real_fake.txt`, `truetest_*.txt`) — CLAUDE.md quotes exact filenames/paths in its results tables; moving breaks traceability between a documented result and its data source.
9. **`docs/Dataset 清單.md`, `docs/research_log.md`, `docs/EXPERIMENT_REGISTRY.md`** — actively cross-referenced by CLAUDE.md and by each other; moving requires updating those cross-references first.
10. **`AIGuard/eval_filter_recall.py`, `eval_truetest_paired.py`** — the exact scripts whose output numbers are quoted verbatim in CLAUDE.md's model comparison tables; relocating without updating those mentions breaks traceability even though the script itself would still run.
11. **`mobile_fft.py`** — the substance of the "edge deployment now provable" claim in CLAUDE.md's top banner; treat as a frozen research artifact, not a general utility script.
12. **Every dataset directory listed under "Status: ✅"** in CLAUDE.md's dataset table (`AIGuard/real/`, `AIGuard/fake/`, `AIGuard/unseen/`, `FFHQ_*_process/`, `filter_data/`, `lfw/`, `sd2.1/`/`DiT/`/`SiT/`/`ddim/`/`pixart/`, `FakeClue/`, `WildDeepfake_subset/`, `stylegan2_test/`) — these are the datasets whose exact paths are hardcoded into dozens of build/train/eval scripts (see `docs/CHECKPOINT_REFERENCE_MAP.csv` and grep results); moving any of them requires a full reference sweep first, explicitly deferred to Stage C.
13. **All `.pth` files in root** — every one is a potential `torch.load(...)` target somewhere in the 149 root scripts or `AIGuard/*.py`; see `docs/CHECKPOINT_REFERENCE_MAP.csv` for the confirmed reference list. Treat the whole set as high move-risk until Stage C's full reference check is done.
14. **`archive/`** — already the destination of a prior (out-of-band, already-committed-looking) legacy-file move per `archive/MOVE_LOG.txt` ("Root checkpoints: moved 42, missing 0; Root scripts: moved 37, missing 0; AIGuard scripts: moved 43, missing 0"). Do not move its contents again or treat it as untouched legacy — it is itself the record of a completed move.

## Safe low-risk tidy-up candidates (grouped, no move performed)

- **Superseded flat 3-class train scripts** (already relocated to `archive/scripts_legacy_v3_v89/` per MOVE_LOG — verified, not re-flagged here).
- **One-off diagnostic/audit scripts with results already captured in `results/*.json`**: `audit_base_image_geometry.py`, `audit_shadow_filter_strength.py`, `audit_truetest_pairing.py`, `audit_identity_leakage.py`, `audit_identity_disjoint_recall.py`, `audit_full_leakage_composition.py`, `audit_retouchingffhq_full_pairing.py`, `audit_cellC_checkpoint_ancestry.py`, `diagnose_*.py` (fft branch, face crop, filter carryover, cascade subset, int8 collapse ×2, eye enlarging, midjourney).
- **One-off chart/figure generators**: `generate_fake_filter_misclass_chart.py`, `generate_phase2_v1_v4_chart.py`, `generate_phase3_outcomes_chart.py`, `generate_tradeoff_chart.py`, `generate_system_overview_png.py`, `generate_v811_confusion_matrix.py`, `generate_v815b_paired_consistency.py`, `generate_demo_composites.py`, `generate_gt_vs_gradcam_figures.py`.
- **Download/extraction one-shot scripts** (already run, data present on disk): `download_celeba_test.py`, `download_celeba_train.py`, `download_diffusionface_diffswap.py`, `download_imdbwiki.py`, `download_vggface2_test.py`, `download_vggface2_topup.py`, `download_vggface2_train_sample.py`, `extract_celebdf_frames.py`, `extract_ffpp_frames.py`, `extract_imdbwiki_*.py`, `sample_stylegan3.py`.
