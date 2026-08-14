# External Alibaba Filter Claim Recommendation

Analysis-only, 2026-08-14. Read-only against `pipeline.py`; nothing here is implemented — every recommendation below is a proposal for a future change, not a change made.

## Bar definition (applied uniformly)

`EXACT_TYPE_ALLOWED` requires **both**:
1. Task 1 label provenance verdict = `VERIFIED_SINGLE_TYPE`, **and**
2. Task 2 measured external performance on that folder: macro-relevant recall/F1 for the presumed class ≥ 0.70 (chosen as a round, clearly-above-chance bar for a 4-way closed-set classifier — chance is 0.25 — and roughly in line with the ≥0.70 informal bar this project has used elsewhere for "usable" recall, e.g. filter-recall gates in `TODO.md`).

Any folder failing either condition does not qualify for `EXACT_TYPE_ALLOWED`, regardless of how confident the classifier's raw softmax looks (confidence is not accuracy — see Task 2 calibration finding below).

## Per-folder recommendation

| Folder | Task1 verdict | Task2 result | Label | 
|---|---|---|---|
| EyeEnlarging_30/60/90 | UNVERIFIABLE | descriptive only (72-81% predicted eye_enlarging, but no verified ground truth to score against) | `COARSE_RETOUCH_ONLY` |
| FaceLifting_30/60/90 | UNVERIFIABLE | descriptive only (65-69% predicted eye_enlarging, 20-25% whitening, only 3-8% predicted face_reshaping) | `COARSE_RETOUCH_ONLY` |
| Smoothing_30/60 | COARSE_OR_MIXED | descriptive only (43-56% predicted eye_enlarging, 26-14% whitening, only 5.5-27.5% predicted smoothing) | `COARSE_RETOUCH_ONLY` |
| Smoothing_90 | COARSE_OR_MIXED | descriptive only (50% predicted smoothing — highest name-match rate of any coarse folder, but label provenance is not reliable enough to score this as "correct") | `UNKNOWN_OR_MIXED_REQUIRED` (see note) |
| Whitening_30 | UNVERIFIABLE | descriptive only (67% predicted eye_enlarging, 23% whitening) | `COARSE_RETOUCH_ONLY` |
| **Whitening_60** | **VERIFIED_SINGLE_TYPE** | **recall(whitening)=25.0%, n=200** (below 0.70 bar) | `COARSE_RETOUCH_ONLY` |
| **Whitening_90** | **VERIFIED_SINGLE_TYPE** | **recall(whitening)=30.0%, n=200** (below 0.70 bar) | `COARSE_RETOUCH_ONLY` |

**No folder reaches `EXACT_TYPE_ALLOWED`.** Even the two folders with real, name-consistent provenance evidence (Whitening_60/90) fail the accuracy bar by a wide margin: pooled recall/accuracy = **27.5% (95% CI 23.2-31.8%, n=400, bootstrap n=2000, seed=42)** against a 25% random-chance floor for a 4-way classifier — i.e. the model's performance on verified external whitening images is statistically indistinguishable from guessing.

**Smoothing_90 special case**: it is the one coarse/unverifiable folder where the model's raw predicted-type distribution most resembles the folder's name (50% "smoothing" — its single most-predicted class, versus every other folder where "eye_enlarging" dominates regardless of true operation). This is interesting descriptively but the task's own rule (Task 2) forbids treating folder-name as ground truth here since Task 1 verdicted it `COARSE_OR_MIXED` — so this is flagged as the best available future candidate for a possible `unknown_or_mixed_retouch` bucket rather than scored as correct.

## Why `COARSE_RETOUCH_ONLY` and not worse (`VISUALIZATION_ONLY`)

The Layer1/Layer2 hierarchical classifier's own filter-vs-not decision is a separate model from `artifact_classifier_v3` and is not what this validation tested (see `AIGuard/eval_ali_ood_v811.py`'s existing "Alibaba OOD filter recall = 98.1%" number, from `TODO.md` / CLAUDE.md — that is filter-vs-real/fake performance, a different, well-supported claim). This validation only concerns the **downstream 4-way type classifier**. Because coarse-level "this image has been retouched" is a *different, already-validated* claim (98.1% Alibaba filter recall) from "this image was specifically whitened/smoothed/etc." (27.5% recall on the one verified subset, and no reliable ground truth at all for the rest), `COARSE_RETOUCH_ONLY` is the correct, defensible ceiling for every Alibaba-derived filter image today — not `VISUALIZATION_ONLY`, since the coarse retouch claim itself is well-supported by existing evidence, just not the type claim.

## Example wording

**Allowed** (`COARSE_RETOUCH_ONLY`, all 12 Alibaba-style external folders):
> "This image shows signs of beauty-filter / retouching processing. The specific type of edit could not be reliably determined for this image."

**Explicitly banned** for any of the 12 folders under current evidence:
> ~~"This image was processed with eye enlarging."~~
> ~~"Whitening filter detected with 92% confidence."~~ (92% is the classifier's raw softmax confidence, not measured accuracy — Task 2 showed these can coexist with 27.5% correctness; presenting raw softmax confidence as if it were a reliability number is exactly the overclaim this task exists to catch)
> ~~"The model compared this image to the original and detected a face-lifting edit."~~ (no original/before image exists anywhere for Alibaba data — see Task 1; this phrasing is banned project-wide per `docs/xai_evidence_schema.md`'s runtime-vs-offline-evidence section regardless of source)

## Region policy

All 12 folders: **no region claim** (neither a named sub-region like "eyes"/"jaw" nor even the whole-face `ARTIFACT_REGION_MAP` marker) should accompany a `COARSE_RETOUCH_ONLY` verdict, because the whole-face region markers in `ARTIFACT_REGION_MAP` are keyed to a *type* prediction (`eye_enlarging` → `["left_eye","right_eye"]`, etc.) that this validation shows is not reliable enough to use externally — attaching any region label to an unreliable type would misrepresent the region as more certain than the type it depends on. If `pipeline.py` is ever extended to detect "this looks like external/non-A1-domain filter data" and route accordingly, the safe region policy for that route is: no region, whole-image framing only.

## Grad-CAM defensibility

**Yes, a Grad-CAM++ heatmap remains defensible to show** for Alibaba-sourced filter predictions, but only under the existing `attention_faithfulness` tier semantics from `docs/xai_evidence_schema.md`, i.e. "the model primarily relies on X region for this decision" — never "X region was edited" or "X region matches the [type] operation". This is because faithfulness (does the model's own decision depend on the highlighted pixels) is a property of the classifier's forward pass and its own faithfulness-test validation (`xai_faithfulness_blur_v1_20260813.json`), which is domain-independent of whether the *type* label attached alongside it happens to be correct. The heatmap explains what the *filter-vs-not* decision (98.1%-recall-validated) attended to, not what the *type* decision (27.5%-recall, this validation) attended to — those must not be conflated in the caption.

## GT-backed status

**None of the 12 Alibaba folders can be called `paired_GT_supported`.** Per `docs/xai_evidence_schema.md`'s `gt_source` vocabulary:
- `self_generated_pair` — not applicable (Alibaba data is not `filter_data/`).
- `FFHQ_pair_audited` — explicitly documented in that schema as **never actually emitted**, because `audit_retouchingffhq_full_pairing.py` found 0 reliable pairs across all RetouchingFFHQ blocks (ali included) — this Task 1 audit independently reconfirms that finding (no local base FFHQ images exist at all).
- The correct `gt_source` value for every Alibaba-derived record is **`none`**, and the correct `region_claim_source` is **`unavailable`** (no region claim made) for all 12 folders under `COARSE_RETOUCH_ONLY`.
- A folder name alone (`Whitening_90`) is **not** evidence of paired ground truth — it is, at best, a within-pool statistical signal (this audit's Task 1 finding for Whitening_60/90) or, for the other 10 folders, an unverified label. Conflating "the folder is named X" with "X is GT-backed" is precisely the overclaim this validation was commissioned to catch.

## Is `unknown_or_mixed_retouch` worth adding?

**Recommended as a future category, not implemented here.** Evidence for:
- 2/12 folders (Smoothing folders, `COARSE_OR_MIXED`) have real evidence suggesting a blended/uncertain operation rather than a clean single edit.
- Across all 12 folders, the classifier's own `unknown_filter` open-set reject rate is only 2-11% (see `external_prediction_distribution.csv`, `frac_pred_unknown_filter` column) — i.e. `ARTIFACT_UNKNOWN_THRESHOLD=0.6` almost never fires on this out-of-domain data, because the classifier is confidently (mean confidence 0.87-0.96 per folder) wrong on external images rather than uncertainly wrong. A confidence-threshold-based open-set mechanism cannot catch this failure mode — the model does not "know what it doesn't know" here, it is miscalibrated on out-of-domain input, not merely underconfident. A category triggered by something other than softmax confidence (e.g. an explicit domain/source check, or an ensemble disagreement signal) would be needed to actually catch this in production; simply lowering `ARTIFACT_UNKNOWN_THRESHOLD` would reject far more true-A1-domain images too (the A1 held-out distribution has median confidence ~1.0, so threshold changes have very different effects in-domain vs out-of-domain).
