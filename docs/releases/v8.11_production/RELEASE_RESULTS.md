# v8.11 Production Release — Results (Traceable Only)

> **2026-08-13 update**: following the P0 Production Evaluation Integrity Repair
> (`results/releases/v8.11_production_20260813/`), the table below is now the SOLE official
> production score table for this release. It replaces the previous version of this document,
> which excluded three headline metrics (Alibaba OOD, True Test paired balanced accuracy, True
> Test filter-by-type) as UNVERIFIABLE because no archived result file existed for them at the
> time. That gap is now closed: every row below cites a freshly generated, hash-verified result
> file from the P0 repair, produced by an explicitly-invoked (never defaulted) checkpoint pair.
> The checkpoint hash pair is **identical across every row** in this table — same two frozen
> files, confirmed by SHA256, every single time:
>
> - **Layer1 (`shufflenet_v2_layer1_v811d.pth`)**: `3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7`
> - **Layer2 (`shufflenet_v2_layer2_v811.pth`)**: `8470ad52dadcdb44a6789067efbbd7fbc20715cb3f4e3339630191889a55057e`
>
> Older result files quoted in the previous version of this document (`results/eval_v811d_gates.log`,
> `results/stress_test_v811d_pipeline.log`, `results/robustness_eval_v811d.json`,
> `results/eval_v811_layer1d_shadow.log`) were already confirmed to have used this same
> checkpoint pair and are NOT contradicted by the P0 repair — they are superseded as the
> *cited* evidence in favor of the newer, more completely provenanced files, not because they
> were wrong. `results/v811_gates_output.txt` and `results/ali_ood_v811_output.txt` remain
> confirmed **Layer1c** (superseded) and are excluded from this table exactly as before — see
> `ORPHAN_AND_UNVERIFIABLE_REGISTER.md`.

## Official production score table (v8.11d + Layer2 v811, all rows same checkpoint pair)

| Metric | Value | Result JSON | Source script | Layer1d SHA256 | Layer2 v811 SHA256 |
|---|---|---|---|---|---|
| True Test filter recall | 233/249 = **93.6%** (gate ≥92%, pass) | `results/releases/v8.11_production_20260813/core_gates_v811d_layer2v811_20260813.json` | `eval_v811_gates.py --layer1-weights shufflenet_v2_layer1_v811d.pth --layer2-weights shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| AIGuard/unseen fake AUROC | **0.8150**, n=454 (gate ≥0.70, pass) | same file | same command | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| CelebA real recall (n=3000 subsample) | 2992/3000 = **99.7%** (gate ≥95%, pass) | same file | same command | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| StyleGAN2 not-real recall (n=3000 subsample) | 2989/3000 = **99.6%** (gate ≥95%, pass) | same file | same command | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| Alibaba filter OOD overall | 20,743/21,151 = **98.1%** | `results/releases/v8.11_production_20260813/alibaba_filter_ood_v811d_layer2v811_20260813.json` | `AIGuard/eval_ali_ood_v811.py --layer1-weights shufflenet_v2_layer1_v811d.pth --layer2-weights shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| Alibaba filter OOD by type | EyeEnlarging 98.1% / FaceLifting 97.0% / Smoothing 99.9% / Whitening 97.3% | same file | same command | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| True Test paired balanced accuracy | **81.1%** (filter recall 93.6% / real recall 68.7% on the same 249 source photos) | `results/releases/v8.11_production_20260813/truetest_paired_v811d_layer2v811_20260813_provenance.json` (companion metadata) + `truetest_paired_run_console.log` | `eval_truetest_paired.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| True Test filter recall by type | smoothing **100%** / whitening **95.2%** / eye_enlarging **82.3%** / face_reshaping **96.8%** (overall 93.6%) | `results/releases/v8.11_production_20260813/truetest_filter_bytype_v811d_layer2v811_20260813_provenance.json` (companion metadata) + `truetest_bytype_run_console.log` | `eval_truetest_filter_bytype_v811.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| Fake+filter end-to-end misclassification (8 filter-strength conditions × 287 AIGuard/unseen fakes) | 85/2289 = **3.71%** | `results/releases/v8.11_production_20260813/stress_test_v811d_layer2v811_20260813.json` | `AIGuard/stress_test_v811_pipeline.py --layer1-weights shufflenet_v2_layer1_v811d.pth --layer2-weights shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| Robustness baseline (q85, no perturbation) | overall 87.5% / real 68.4% / fake 99.6% / filter 93.6% | `results/releases/v8.11_production_20260813/robustness_eval_v811d_layer2v811_20260813.json` | `AIGuard/eval_robustness.py --layer1-weights shufflenet_v2_layer1_v811d.pth --layer2-weights shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |
| Shadow paired balanced accuracy | **43.5%** (filter recall 10.0% / real recall 77.1%, error direction: missed_filter 69.9% / both_wrong 20.1% / both_ok 7.2% / filter_biased 2.9%) | `results/releases/v8.11_production_20260813/paired_both_domains_truetest_and_shadow_v811d_layer2v811_20260813_provenance.json` (companion metadata) + `paired_both_domains_run_console.log` | `eval_paired_both_domains.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth` | `3c61cf68...94c290b7` | `8470ad52...889a5505` |

All commands and outputs above were generated 2026-08-13 in a single repair pass, with the two
scripts already defaulting correctly (`eval_truetest_paired.py`, `eval_truetest_filter_bytype_v811.py`,
`eval_paired_both_domains.py`) invoked with explicit args as a matter of discipline, and the
four scripts previously found to silently default to the superseded `shufflenet_v2_layer1_v811c.pth`
(`eval_v811_gates.py`, `AIGuard/stress_test_v811_pipeline.py`, `AIGuard/eval_ali_ood_v811.py`,
`AIGuard/eval_robustness.py`) fixed to be fail-closed and then invoked with explicit args. Full
narrative in `docs/releases/v8.11_production/EVALUATION_INTEGRITY_REPAIR.md`; full machine-readable
manifest (every file's own SHA256, git commit at run time, exact command lines) in
`results/releases/v8.11_production_20260813/RELEASE_EVALUATION_MANIFEST.json`.

## Historical corroboration (not the citation source, kept for cross-reference only)

The following older result files were independently confirmed (in the prior release pass) to
already reflect the same v811d/v811 checkpoint pair, and their numbers match the 2026-08-13
repair run exactly — cited here only as a consistency cross-check, not as the primary source:
`results/eval_v811d_gates.log`, `results/stress_test_v811d_pipeline.log`,
`results/robustness_eval_v811d.json`, `results/eval_v811_layer1d_shadow.log`. None of these
files were modified by the P0 repair or by this closeout pass.

## OOD / cross-source tests

See the official production score table above (Alibaba filter OOD, CelebA real recall,
StyleGAN2 fake recall rows) — no separate table is maintained to avoid duplicate/divergent
citations of the same numbers.

## Robustness

Baseline condition is in the official production score table above. Full per-condition
breakdown (lighting ±30%/±50%, Gaussian blur k3/5/7/9, 2×/4× downscale-upscale, JPEG q50/70/85/95,
multi-stage re-compression, pose-angle buckets) is in
`results/releases/v8.11_production_20260813/robustness_eval_v811d_layer2v811_20260813.json` —
worst observed condition is `downscale_upscale_4x` (overall 69.2%, real recall 16.8%).
Shadow paired evaluation (balanced accuracy, error-direction routing) is in the official table
above, sourced from `eval_paired_both_domains.py`; the isolated Layer1-only Shadow read
(`results/releases/v8.11_production_20260813/shadow_layer1_isolated_v811d_20260813_provenance.json`,
real recall 76.9%, binary AUROC 0.7907) is supplementary evidence for the same finding.

## Filter XAI (production checkpoint, NOT v8.8)

Source: `results/phase2_p0_v811_filter_gradcam_validation_20260813.json`, produced by
`phase2_p0_v811_filter_gradcam_validation.py`, which loads `pl.LAYER1_WEIGHTS_PATH` /
`pl.LAYER2_WEIGHTS_PATH` directly from `pipeline.py` (dynamic import, not a hardcoded path) —
confirmed by the script's own `import pipeline as pl` and the JSON's embedded
`"layer1_checkpoint": "...shufflenet_v2_layer1_v811d.pth"`, `"layer2_checkpoint":
"...shufflenet_v2_layer2_v811.pth"` fields, plus its own `_note` field explicitly stating this
run is "against the ACTUAL production v8.11 hierarchical classifier... not the older v8.8 flat
3-class model." Generated 2026-08-13 09:16:52 +08:00 (file mtime).

| Filter type | n (valid paired GT) | Layer1 routing coverage | Layer2 filter-vs-fake coverage | Final filter accuracy | Grad-CAM++ mean IoU | Grad-CAM++ mean PointingGame |
|---|---:|---:|---:|---:|---:|---:|
| eye_enlarging | 100 | 85.0% | 96.0% | 81.0% | 0.549 | 0.864 |
| face_reshaping | 100 | 96.0% | 97.0% | 94.0% | 0.516 | 0.915 |
| smoothing | 98 | 100.0% | 100.0% | 100.0% | 0.398 | 0.296 |
| whitening | 99 | 86.9% | 98.0% | 84.9% | 0.372 | 0.357 |

Per this JSON's own `v88_vs_v811_delta` comparison block (also file-backed, same JSON), the
v8.11 checkpoint is at parity or improved vs. the v8.8 baseline for eye_enlarging (+0.082 IoU)
and face_reshaping (+0.050 IoU); whitening PointingGame regressed substantially (0.880 → 0.357)
— this is a v8.11-specific finding, root-caused separately (see below), not a v8.8 carryover
issue.

**Whitening PointingGame diagnostic**: `results/phase2_whitening_peak_diagnostic_20260813/summary.json`
+ `contact_sheet.png`, produced by `phase2_whitening_pointinggame_diagnostic.py` (also imports
`pipeline as pl` directly — same dynamic-provenance guarantee as above). Generated 2026-08-13
10:32:04 +08:00. Finding: 17/20 (85%) of PointingGame-failure whitening cases have their
Grad-CAM++ peak landing within 3px of the same absolute pixel coordinate `(80,111)` in the
224×224 normalized frame, regardless of actual face position/size — indicates a near-constant
positional bias in the peak, not a content-driven mislocalization. Root-cause diagnosis only;
no fix applied (out of scope for this diagnostic run).

**Grad-CAM++ faithfulness (blur-based)**: `results/xai_faithfulness_blur_v1_20260813.json`,
produced by `xai_faithfulness_blur_test.py` (also `import pipeline as pl` directly — same
dynamic-provenance guarantee). Generated 2026-08-13 07:52:26 +08:00. Own `_note` field states
this is "on the PRODUCTION v8.11 hierarchical classifier." Result: hot-region drop > cold-region
drop and hot-region drop > matched-random drop at k=5%/10%/20% (margins +0.108/+0.193/+0.300 and
+0.102/+0.059/+0.106 respectively) — supports Grad-CAM++ faithfulness on the production model.

**gt_vs_gradcam figures**: `results/gt_vs_gradcam/gt_vs_gradcam_eye_enlarging.png`,
`gt_vs_gradcam_face_reshaping.png`, produced by `generate_gt_vs_gradcam_figures.py` (also
`import pipeline as pl`, dynamic provenance). File mtime 2026-08-13 11:00 — these are confirmed
Layer1d/Layer2-v811 regenerations; the *original* Layer1c-era versions were overwritten
in-place (git-untracked directory) and are unrecoverable. See
`ORPHAN_AND_UNVERIFIABLE_REGISTER.md` for the full incident record — the current PNGs are valid
production evidence, but no before/after Layer1c comparison is possible anymore.

**`results/v811_confusion_matrix.json` is explicitly EXCLUDED from this release's evidence**:
file mtime is 2026-08-03 08:xx, which **predates the creation of `shufflenet_v2_layer1_v811d.pth`
itself (2026-08-10, per TODO.md)** — this file cannot possibly reflect the current production
Layer1d, despite `generate_v811_confusion_matrix.py` correctly reading `pl.LAYER1_WEIGHTS_PATH`
dynamically (the *script* is fine; the *artifact on disk* is stale). Content cross-check
confirms this: its filter recall (234/249=94.0%) matches the *v811c*-era number seen in
`results/v811_gates_output.txt`, not v811d's 93.6%. **Recommendation: regenerate before citing
in any report; do not use the current file.**

## Deployment artifact

| Item | Value | Source |
|---|---|---|
| TFLite fp32 (Layer1+Layer2 combined) | 20.91 MB, CPU latency 14.4 ms/image (desktop), decision agreement vs. PyTorch = 1.0 (769/769 identical) | `results/mobile_deployment_benchmark.json` |
| TFLite fp16 | **BROKEN** — fails to load (`CONV_2D` prepare error) | same file |
| TFLite dynamic-range/int8 quant | Loads, but **recall collapses to 0%** for filter/fake classes, agreement vs. PyTorch = 0.244 | same file |
| iPhone on-device benchmark | **NOT DONE** — the one remaining open Freeze Gate item per TODO.md | N/A |

`mobile_deployment_benchmark.json` does not itself state which checkpoint produced it, but its
`pytorch_fp32.recall` values (filter 93.57%, real 68.4%, fake 99.63%) match
`results/eval_v811d_gates.log` / `robustness_eval_v811d.json` exactly — cross-confirmed as
v811d/v811, generated 2026-08-11 02:39:38 +08:00 (file mtime).

## Known failures / non-claims

These are known, documented limitations — not silent gaps and not resolved by the P0
evaluation-integrity repair (that repair fixed *evidence provenance*, not the underlying
model behavior these items describe):

- Shadow domain-gap paired balanced accuracy (43.5%, official table above) is well below True
  Test (81.1%) — see `RELEASE_BOUNDARY.md` (same directory) for the ID/OOD/robustness
  classification of each eval and why this does not block the Phase 1 freeze.
- Fake+filter misclassification (3.71%, official table above) exceeds the informal ≤2% stretch
  target.
- FF++ fake recall does not meet the informal ≥70% stretch target (Layer1 video-domain gap).
- Cross-source `has_filter` joint recognition remains far below the informal ≥25% stretch
  target even in the dedicated v8.16 research track — v8.16 is NOT part of this release.
- int8 mobile deployment is blocked by an FFT-branch dynamic-range issue; only fp32 TFLite is
  currently valid.
- iPhone on-device benchmark: not yet performed. See `PHASE1_FREEZE_DECISION.md` for this
  item's status as the next required task.

**Resolved as of the 2026-08-13 P0 repair** (kept here only as a record — these are no longer
open items): True Test paired balanced accuracy and True Test filter-recall-by-type breakdown
now have archived, hash-verified result files (see official table above); Alibaba OOD filter
recall for v8.11d (98.1%) now has an archived, hash-verified result file and is no longer
sourced from narrative text alone.

---

## Related research / not part of release

The following are explicitly OUTSIDE this release's scope (v8.12–v8.16 research track, or
v8.8 historical baseline). They must never appear in the score tables above.

- **v8.8 historical XAI** (`results/xai_comparison_eye_face_white.json`): flat 3-class
  architecture, superseded by the v8.11 hierarchical design. Used only as an explicit
  before/after comparison baseline inside the v8.11 Filter XAI validation JSON's own
  `v88_reference_for_comparison` field — legitimate as a *comparison*, never as a *production*
  number.
- **v8.12/v8.13/v8.14**: base-image-diversity and hard-negative-mining research track.
  `pipeline.py` never routed to any of these; none promoted to production per TODO.md's own
  "暫不將 v8.12 上 production" / "v8.13 不上 production" / "v8.14 保留為研究基準，不替換 v8.11"
  decisions.
- **v8.15 (all cells, including "Cell C")**: dual-head factorized-attribute research pilot +
  ablation grid. `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` ("v8.15-C@0.85")
  is a research checkpoint only; `phase2_composite_explanation.py`'s own output JSON
  self-declares "v8.15-cellC dual-head RESEARCH baseline, not production (pipeline.py still
  v8.11)."
- **v8.16 mixed-lineage** (`shufflenet_v2_layer2_v816_mixedlineage.pth`): source-diverse
  composite training, initialized from v8.15 Cell C per `AIGuard/train_v816.py`'s own console
  output ("Init from cellC checkpoint"). Cross-source generalization improved (2.02%→4.53%)
  but remains far short of the informal target and left several filter types with "完全無殘留
  效果" (zero residual effect) per CLAUDE.md. Research evidence only.
