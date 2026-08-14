# Results Provenance (Read-Only Inventory, Stage A)

> Maps important `results/` artifacts and figure-producing scripts to the checkpoint
> version and phase they document. Purpose: prevent exactly the kind of mix-up
> CLAUDE.md/TODO.md already record happening twice ("Layer2c 誤植為 v8.11 最終數字",
> "v8.12 覆蓋 v8.11 baseline") — see the 2026-08-11 fixed-output-filename bug entry.
> Where the checkpoint version cannot be confirmed from repo evidence, it is marked
> `UNVERIFIABLE` rather than guessed.

## v8.8 historical XAI (flat 3-class model, superseded architecture)

| Artifact | Phase | Checkpoint | Source script | Production evidence? | Historical only? | Manifest/hash? |
|---|---|---|---|---|---|---|
| `results/xai_comparison_eye_face_white.json` | Phase 2 | `shufflenet_v2_3class_v88.pth` (explicitly confirmed — `phase2_p0_v811_filter_gradcam_validation.py` line 10: "ran on shufflenet_v2_3class_v88.pth -- a flat 3-class classifier") | Not found as a standalone script in root listing under this exact name — likely produced by an earlier `compare_methods()` routine referenced in comment at `phase2_p0_v811_filter_gradcam_validation.py:9`; exact producing script name UNVERIFIABLE | **No** | **Yes** | No explicit hash/manifest found |
| Grad-CAM++ vs region-head comparison (the "第5節" study cited throughout TODO.md/CLAUDE.md) | Phase 2 | v8.8 | Same as above | No | Yes | No |

## v8.11d + Layer2 v811 production XAI (current production checkpoints)

| Artifact | Phase | Checkpoint | Source script | Production evidence? | Historical only? | Manifest/hash? |
|---|---|---|---|---|---|---|
| `results/phase2_p0_v811_filter_gradcam_validation_20260813.json` | Phase 2 | `shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth` (confirmed by filename and by script docstring, which explicitly re-runs the v8.8 study's paired-GT methodology "against the production checkpoint") | `phase2_p0_v811_filter_gradcam_validation.py` | **Yes** | No | Filename includes date (`20260813`); no separate hash file found |
| `results/phase2_whitening_peak_diagnostic_20260813/` (incl. `contact_sheet.png`) | Phase 2 | v8.11d/v811 (follow-up diagnostic on the whitening PointingGame regression found above) | `phase2_whitening_pointinggame_diagnostic.py` | Yes | No | No |
| `results/xai_faithfulness_blur_v1_20260813.{json,csv}` | Phase 2 | UNVERIFIABLE from filename alone — not explicitly re-confirmed which checkpoint's Grad-CAM++ was tested; given it's dated the same day as the v8.11d re-validation and described in CLAUDE.md/TODO.md as fixing a masking-methodology bug in the *general* faithfulness protocol (not tied to one checkpoint by name), treat as **UNVERIFIABLE** pending a script read to confirm the model-loading line | `xai_faithfulness_blur_test.py` | Likely yes, but flagged UNVERIFIABLE | No | No |
| `results/xai_evidence_v1_20260812.jsonl`, `results/xai_evidence_heatmaps_20260812/` | Phase 2 | UNVERIFIABLE from filename; likely production given the 20260812 date is after the v8.11 freeze work began, but not confirmed by a grep of the producing script's model path | `build_xai_evidence.py` | UNVERIFIABLE | UNVERIFIABLE | No |
| `results/gt_vs_gradcam/gt_vs_gradcam_eye_enlarging.png`, `gt_vs_gradcam_face_reshaping.png` | Phase 2 | UNVERIFIABLE — filenames don't encode a checkpoint version; file mtime (Aug 13 11:00) matches the v8.11d re-validation work but this is circumstantial, not confirmed | `generate_gt_vs_gradcam_figures.py` | UNVERIFIABLE | UNVERIFIABLE | No |
| `results/v811_confusion_matrix.json` | Phase 1 | `shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth` (filename convention matches production naming used elsewhere, e.g. `stress_test_v811d_pipeline.log`) | `generate_v811_confusion_matrix.py` | Yes | No | No |
| `results/v811_gates_output.txt`, `results/eval_v811d_gates.log` | Phase 1 | v8.11d/v811 | `eval_v811_gates.py` | Yes | No | No |
| `results/robustness_eval_v811d.json` | Phase 1/3 | v8.11d (explicit in filename) | `AIGuard/eval_robustness.py` | Yes | No | No |
| `results/stress_test_v811_pipeline.json`, `results/stress_test_v811d_pipeline.log` | Phase 1 | v8.11d/v811 — **note**: TODO.md documents this exact file was previously overwritten by a v8.12 run due to a fixed-filename bug, then "已重跑還原（3.71%，與文件數字完全吻合）" (re-run and restored). Current file content should be v8.11 baseline but there is no in-file checksum to independently verify against the historical bug. | `AIGuard/stress_test_v811_pipeline.py` | Yes (per TODO.md's own restoration claim) | No | No — this is exactly the kind of artifact that would benefit from a hash/manifest per the script's own documented history of being clobbered |

## v8.15 Cell C research composite (`unfreeze1_inv0` ablation cell)

| Artifact | Phase | Checkpoint | Source script | Production evidence? | Historical only? | Manifest/hash? |
|---|---|---|---|---|---|---|
| `results/eval_v815_ablation_full.{json,log}` | Phase 3 (research) | All 4 ablation cells (`shufflenet_v2_layer2_v815ablation_cell{A,B,C,D}_*.pth`), Cell C = `unfreeze1_inv0` | `eval_v815_ablation_full.py` via `AIGuard/train_v815_ablation.py` | **No** — explicitly a research ablation grid | Yes (research-track) | No |
| `results/train_v815ablation_cellC_unfreeze1_inv0_log.csv` | Phase 3 | `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` | `AIGuard/train_v815_ablation.py` | No | Yes | No |
| `results/eval_v815a_dualhead.{json,log}` | Phase 3 | v8.15a dual-head pilot (not Cell C specifically — this is the earlier dual-head pilot, judged "誠實負面結果") | `eval_v815a_dualhead.py` | No | Yes | No |
| `phase2_composite_explanation.py` output (no dated results file located; script explicitly self-documents) | Phase 2 (research) | v8.15-cellC — confirmed in-script: `"_note": "P2-1 composite explanation protocol run summary, v8.15-cellC dual-head research baseline."` and `"Uses the v8.15-cellC dual-head RESEARCH baseline, not production (pipeline.py still v8.11)."` | `phase2_composite_explanation.py` | **Explicitly No** (script self-declares this) | Yes | No |
| `results/build_v815_replication_set.log`, `splits/v815_replication_set.tsv` | Phase 3 | v8.15 family (replication-set construction, not tied to one specific cell) | `build_v815_replication_set.py` | No | Yes | Has a `.tsv` manifest (`v815_replication_set.tsv`) — this one **does** have a manifest |

## v8.16 mixed-lineage research composite

| Artifact | Phase | Checkpoint | Source script | Production evidence? | Historical only? | Manifest/hash? |
|---|---|---|---|---|---|---|
| `results/train_v816_mixedlineage.log`, `results/train_v816_log.csv` | Phase 3 | `shufflenet_v2_layer2_v816_mixedlineage.pth` — confirmed initialized "from cellC checkpoint" per `AIGuard/train_v816.py` line 160 (`print(f"Init from cellC checkpoint..."`) and the file's own top comment: `NAMED "mixed-lineage" per audit_cellC_checkpoint_ancestry.py: Cell C's own ...` | `AIGuard/train_v816.py` | No | Yes | No |
| `results/eval_v816_indomain_and_joint.log` | Phase 3 | v8.16 mixed-lineage | Producing script name not directly confirmed by grep in this pass — likely `eval_replication_set_v816.py` or `threshold_sweep_v816.py`, UNVERIFIABLE which exact script wrote this specific log without opening both | UNVERIFIABLE (script) but checkpoint is No | Yes | No |
| `results/eval_replication_auroc_v816.log`, `splits/v816_manifest.tsv` | Phase 3 | v8.16 | `eval_replication_auroc_v816.py`, `build_v816_manifest.py` | No | Yes | `v816_manifest.tsv` **is** a manifest |
| `results/threshold_sweep_v816.log` | Phase 3 | v8.16 | `threshold_sweep_v816.py` | No | Yes | No |
| `audit_cellC_checkpoint_ancestry.py` output (printed to console per script; no dated results file located in this pass) | Phase 3 (provenance audit) | Traces v8.16 ← Cell C ← (v814/v812 lineage) | `audit_cellC_checkpoint_ancestry.py` | N/A (audit tool, not a results artifact) | N/A | N/A |

## General observations

- **Clean separation exists between v8.8 and v8.11 XAI claims** — `phase2_p0_v811_filter_gradcam_validation.py` explicitly re-runs the v8.8-era Grad-CAM++-vs-region-head study against production checkpoints specifically *because* the original study used the now-superseded v8.8 model, and the script's own output JSON carries both the v8.8 reference numbers and the v8.11 numbers side by side with a `delta_IoU`/`delta_PointingGame` comparison. This is a good provenance pattern; no evidence found of the two being conflated in current docs.
- **v8.15/v8.16 research artifacts self-declare their non-production status** in at least two places (`phase2_composite_explanation.py`'s own JSON output, and CLAUDE.md's freeze entry) — no evidence found of these being cited as production numbers anywhere in the docs scanned.
- **The one confirmed historical clobbering incident** (`results/stress_test_v811_pipeline.json` overwritten by a v8.12 run, later restored) has no independent hash/manifest to verify the restoration was byte-exact vs. merely "re-ran and got the same number." This is the single highest-value candidate for adding a manifest/hash in a future pass — flagged here, not acted on.
- Several dated-but-not-checkpoint-tagged filenames (`xai_faithfulness_blur_v1_20260813.*`, `xai_evidence_v1_20260812.jsonl`, `gt_vs_gradcam_*.png`) could not be conclusively tied to a checkpoint version from filename + directory-listing evidence alone within this read-only pass's budget; marked `UNVERIFIABLE` rather than assumed production. A follow-up pass that opens each producing script's model-loading lines would resolve these.
