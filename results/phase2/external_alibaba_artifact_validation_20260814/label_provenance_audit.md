# Label Provenance Audit — FFHQ_ali_process (Alibaba retouching API)

Analysis-only, 2026-08-14. See `label_provenance_audit.csv` for the full per-folder evidence table (12 rows). This file summarizes method and conclusions.

## Method

1. **Metadata search** (Glob/grep across the whole `FFHQ_ali_process/` tree, not just `clean_output/`): found only `clean_output/clean_paths.txt`, `rejected.csv`, `summary.txt`, and `review_kept/_manifest.json`. All four are **cleaning-pipeline** records (accept/reject decisions, face-count/resolution rejects) — none record what retouching operation was actually applied, what the `_30/_60/_90` suffix parametrizes, or any generation log. **No generation metadata exists anywhere in this tree.**
2. **Base-image availability**: `docs/xai_evidence_schema.md`'s existing RetouchingFFHQ pairing audit (`audit_retouchingffhq_full_pairing.py`) already found 0 reliable before/after pairs across all three RetouchingFFHQ blocks (four/megvii/ali) because **no local copy of the original, pre-retouching FFHQ images exists anywhere in the project**. Verified independently here: the only locally-present folder literally named `ffhq/` is an unrelated LaTeX paper-writing template (`.bst`/`.cls`/`.tex` files), not image data. So no unretouched base image is locatable for any Alibaba-processed image, confirming the schema doc's finding. This means **no pixel-level before/after check is possible for any of the 12 folders** — only (a) statistical checks within the Alibaba pool itself, and (b) single-image visual inspection with no reference.
3. **Within-pool statistical check**: for each folder, sampled up to 200 clean-pool images (seeded, `random_state=42`), ran `pipeline.py`'s own `compute_skin_stats()` (texture_var via Laplacian variance, brightness_L via LAB) on the `preprocess_jpeg(q85)` + `resize(224,224)` image — the same resolution `pipeline.py` itself feeds this function at in production (`pipeline.py:479/513`). Compared **within the Alibaba pool across the 12 folders** (controlled: same FFHQ source images, same preprocessing, only the retouch differs) rather than only against the project's own AIGuard-domain calibration thresholds (`texture<210`→smoothing, `brightness>147`→whitening), since the AIGuard thresholds were calibrated on a different image domain (real photos, not FFHQ/StyleGAN faces) and are cited here only as secondary context.
4. **Visual sampling**: read a handful of full-resolution images per operation (`EyeEnlarging_30/18165.png`, `EyeEnlarging_90/17133.png`, `FaceLifting_90/17655.png`) directly to sanity-check whether the named operation is visually plausible.

## Findings per family

- **Whitening**: real, monotonic, within-pool brightness signal. `brightness_L_224` rises 130.4 (_30) → 135.7 (_60) → 136.5 (_90), consistently ~9-12 points above the other three families' baseline (~123-126) at intensities 60/90. This is the **only family with a positive, name-consistent, intensity-monotonic quantitative signal** found in this audit. `Whitening_30`'s signal (130.4) is too close to baseline noise (other folders' std is ~24-30) to trust, so it is verdicted `UNVERIFIABLE` while `Whitening_60`/`Whitening_90` are verdicted `VERIFIED_SINGLE_TYPE`.
- **Smoothing**: weak, directionally-correct but small signal. `Smoothing_60`/`Smoothing_90` have the joint-lowest `texture_var_224` (490.8) of all 12 folders, consistent with reduced texture from a smoothing operation, but the effect (~10% below the ~545-630 baseline of the other families) is small relative to within-folder noise (std ~250-350) and far short of the project's own "strongly smoothed" calibration (texture<210, a >2x drop). `Smoothing_30` shows no measurable signal above pool noise at all. Cannot distinguish "genuine but mild single smoothing op" from "blended multi-effect beauty preset with partial texture reduction" — verdicted `COARSE_OR_MIXED` for all three intensities.
- **EyeEnlarging**: no diagnostic quantitative evidence available (whole-face texture/brightness stats cannot detect a localized geometric eye warp by construction), and visual inspection of 2 sample images could not confirm eye enlargement without a before/after reference. Verdicted `UNVERIFIABLE` at all three intensities.
- **FaceLifting**: same "no diagnostic whole-face stat" limitation as EyeEnlarging, **plus a specific, still-unresolved naming-mismatch concern**: "FaceLifting" is a common commercial beauty-API preset name that in practice often bundles jaw slimming + cheek contour (sometimes chin/nose) as a single button, which is a coarser semantic unit than this project's own `face_reshaping` label (defined narrowly, per `pipeline.py`'s `ARTIFACT_REGION_MAP` comment, as a fixed ~60px-radius local warp calibrated on the self-built pipeline). One visual sample (`FaceLifting_90/17655.png`) shows a plausible localized jaw/cheek warp artifact near the mouth, weakly consistent with a single reshape op — not strong enough to confirm single-operation status, and not strong enough to positively demonstrate mixing either. Verdicted `UNVERIFIABLE` (not `COARSE_OR_MIXED`, since that would assert mixing evidence this audit does not actually have) at all three intensities, with the naming-mismatch risk flagged explicitly for Task 4.

## Roll-up justification

- `EyeEnlarging_{30,60,90}` → all `UNVERIFIABLE`: no per-intensity evidence differentiates them (whole-face stats are uniformly non-diagnostic regardless of intensity).
- `FaceLifting_{30,60,90}` → all `UNVERIFIABLE`: same reasoning; the one visual sample reviewed was from `_90` (highest intensity, most likely to show a visible effect if any), so lower intensities are, if anything, less verifiable, not more.
- `Smoothing_{30,60,90}` → all `COARSE_OR_MIXED`: `_60`/`_90` show a weak signal, `_30` shows none; none reach a confidence level distinguishable from "coarse/blended", so all three get the same conservative verdict rather than asserting a false intensity boundary.
- `Whitening_{30}` vs `Whitening_{60,90}` → **not** rolled up: this is the one family where intensity materially changes the evidence (30 is noise-level, 60/90 are not), so the per-intensity split is preserved rather than hidden.

## Summary table

| Folder | Verdict |
|---|---|
| EyeEnlarging_30/60/90 | UNVERIFIABLE |
| FaceLifting_30/60/90 | UNVERIFIABLE |
| Smoothing_30/60/90 | COARSE_OR_MIXED |
| Whitening_30 | UNVERIFIABLE |
| Whitening_60 | VERIFIED_SINGLE_TYPE |
| Whitening_90 | VERIFIED_SINGLE_TYPE |

**Only 2 of 12 folders (Whitening_60, Whitening_90) reach `VERIFIED_SINGLE_TYPE`.** This is a narrow evidence base — Task 2's exact-type accuracy/F1/confusion-matrix numbers are computed only on these two folders (n=400); all other folders get descriptive-only prediction-distribution reporting per the task's own rule against computing correctness metrics without reliable ground truth.
