# Filter XAI Claim Matrix — Family × Claim-Type

> Read-only audit. Builds directly on the already-established Tier A-D framework in
> `docs/phase2_story.md` §8-11 (cited, not re-derived) and extends it into a full family ×
> claim-type grid using the family IDs from `FILTER_DATA_PROVENANCE.csv`. Every cell states
> the verdict, the evidence source, the limitation, and one example each of forbidden and
> allowed wording. No template text, `ARTIFACT_REGION_MAP`, or JSON schema was modified to
> produce this document — it is an audit of what the CURRENT deployed system's outputs can be
> honestly defended as, given the data behind them.

## Legend

- **ALLOWED** — the evidence directly supports the claim as currently phrased.
- **ALLOWED_WITH_CAVEAT** — supportable, but only with an explicit qualifier attached (e.g.
  "in offline validation..." or "whole-face, not precise localization").
- **VISUALIZATION_ONLY** — a Grad-CAM++ heatmap may be shown, but it must not be described as
  validated against ground truth.
- **NOT_SUPPORTED** — no evidence exists; producing this claim for this family would be an
  overclaim.
- **UNKNOWN** — evidence gap in this audit itself (not yet checked / not determinable from
  repo contents alone), distinct from NOT_SUPPORTED.

## Claim types (columns)

1. `final_class=filter` (binary/coarse "this is a filtered image")
2. Exact `artifact_type` (one of the 4: smoothing/whitening/eye_enlarging/face_reshaping)
3. Coarse retouch / app-family label (e.g. "processed by a beautification app", no specific type)
4. Eyes region-level text (naming a specific facial region)
5. Whole-face text (non-localized "the face" wording)
6. Grad-CAM visualization only (heatmap shown, no claim about what it proves)
7. Paired-GT-backed localization (heatmap claimed to align with a validated ground truth)
8. Pixel-level / LAB-diff validation (quantitative IoU/PointingGame/delta-E claims)

---

## Family A1/A2/A3 — self-built paired filter pipeline (AIGuard/real, LFW, True-Test)

| Claim type | Verdict | Evidence | Limitation |
|---|---|---|---|
| final_class=filter | **ALLOWED** | `generate_filter_dataset.py` etc., paired by construction; production Layer2 trained+evaluated on this family | None beyond normal model-accuracy caveats |
| exact artifact_type | **ALLOWED** (eye_enlarging, face_reshaping, smoothing) / **ALLOWED_WITH_CAVEAT** (whitening) | Folder label is the exact operation; `artifact_classifier_v3.pth` trained exclusively on this family (A1) | Whitening carries forward risk from the fake+filter composite finding (family F: 6% type accuracy) even though A1/A2/A3 themselves are clean pairs — no clean-pair-specific whitening accuracy audit was located this round beyond the model's own held-out test split in training |
| coarse retouch/app-family label | **ALLOWED** (subsumed by exact type) | Same as above | N/A |
| eyes region-level text | **ALLOWED** (eye_enlarging only) | `docs/phase2_story.md` §7-8: Tier A, region-level GT-backed for eye_enlarging specifically, re-confirmed on production v8.11 (`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`, IoU 0.549, PointingGame 0.864) | Do not extend eyes-region wording to the other 3 types |
| whole-face text | **ALLOWED_WITH_CAVEAT** (whitening, smoothing, face_reshaping) | Same Tier A framework — GT-backed but explicitly whole-face, not precise-region | Must not use heatmap peak location as a precise-position claim for whitening (PointingGame 0.880→0.357 regression on production v8.11, `docs/phase2_story.md` §12) or smoothing (physically whole-face effect, precision is meaningless per §7) |
| Grad-CAM visualization only | **ALLOWED** | Always true as a floor — any family can show a heatmap | Must not imply validation beyond what the tier supports |
| paired-GT-backed localization | **ALLOWED** (eye_enlarging) / **ALLOWED_WITH_CAVEAT** (other 3, whole-face only) | `generate_landmark_gt.py`, landmark displacement + LAB diff, computed per-image | See eyes/whole-face rows above |
| pixel-level/LAB-diff validation | **ALLOWED** | Same GT pipeline; this is the one family where pixel-level GT genuinely exists | Offline-only — see `docs/xai_evidence_schema.md`'s runtime-vs-offline distinction; do not phrase as "the system compared before/after" at inference time |

**Wording NOT allowed** (any family, but especially relevant here since it's the strongest
tier): *"The system compared the original and filtered images and confirmed the whitening
effect is centered on the cheeks."* — production inference never has access to an original
image; this misdescribes runtime behavior (see `docs/phase2_story.md` §10).

**Wording that IS allowed**: *"The model's attention is concentrated on the eye region,
consistent with offline paired-ground-truth validation of this filter type."* (eye_enlarging)
/ *"Texture-smoothing artifacts were detected across the face; in offline validation, this
filter type's physical effect spans the whole face rather than a specific region."* (smoothing)

---

## Family F — fake+filter composite (AIGuard/fake base, self-built filter)

| Claim type | Verdict | Evidence | Limitation |
|---|---|---|---|
| final_class=filter (as part of a fake+filter composite) | **ALLOWED_WITH_CAVEAT** | P2-C1 (`docs/EXPERIMENT_REGISTRY.md`): filter_status=detected only 31/40 (77.5%) on the diagnostic subset | Must report coverage alongside any localization number — "among cases where filter was detected," not universally |
| exact artifact_type | **ALLOWED** (face_reshaping, smoothing) / **NOT_SUPPORTED** (whitening) / **ALLOWED_WITH_CAVEAT** (eye_enlarging) | P2-C2 (`results/phase2_composite_filtertype_accuracy_v1_20260813.json`): face_reshaping 92%, smoothing 94%, eye_enlarging 70%, **whitening 6%** | Whitening is **systematically misclassified** as eye_enlarging/face_reshaping on this family — this is not noise, per `docs/phase2_story.md` §9's own characterization ("系統性偏移，不是隨機失準"). Already a locked project decision: whitening/eye_enlarging type is suppressed on fake-base composites, generic "possible post-processing filter" wording used instead. |
| coarse retouch/app-family label | **ALLOWED** | Fallback wording already adopted per §9's decision | None |
| eyes region-level text | **NOT_SUPPORTED** | No region-level GT validation exists for THIS family's eye_enlarging cases specifically (P2-C1's IoU/PointingGame numbers are on the whole 31-image detected subset across types, not decomposed per-type in a way that isolates a validated eye-region claim) | Treat as UNKNOWN-leaning-NOT_SUPPORTED rather than inheriting A1/A3's eye_enlarging ALLOWED verdict — different base-image family, not re-validated |
| whole-face text | **ALLOWED_WITH_CAVEAT** | P2-C1: IoU 0.398, PointingGame 0.774 **only on the 31/40 detected subset** | Must state the 77.5% coverage caveat every time this number is cited (per §9's explicit "報告方式須拆成兩段" instruction) |
| Grad-CAM visualization only | **ALLOWED** | Floor case | — |
| paired-GT-backed localization | **ALLOWED_WITH_CAVEAT** | Same pipeline as A1 (base_dir swapped to AIGuard/fake), confirmed reused unmodified | Coverage caveat above; also cross-fake-source generalization is a SEPARATE, already-answered negative finding (see below) — do not conflate in-domain P2-C1/C2 numbers with cross-source claims |
| pixel-level/LAB-diff validation | **ALLOWED_WITH_CAVEAT** | Same as above | AIGuard/fake only; **NOT_SUPPORTED for any other fake source** (DF40-ff/DF40-cdf) — `docs/EXPERIMENT_REGISTRY.md` P1-1: DF40-cdf joint recognition collapses to 2.02% (v8.15-Cell-C) / 4.53% (v8.16, calibrated), filter_head AUROC 0.53 (chance), confirming this family's paired-GT validation does not transfer across fake-generation sources |

**Wording NOT allowed**: *"The eye-enlarging effect on this fake image was localized with high
precision."* (no per-type region validation exists for eye_enlarging on this family, and this
family's own P2-C2 result shows unreliable type prediction for whitening/eye_enlarging).

**Wording that IS allowed**: *"Among composite images where the model detected a filter
attribute, texture-smoothing (94% type accuracy) and geometric reshaping (92%) predictions
are reliable in offline validation; whitening and eye-enlarging predictions on this fake-image
family are not currently reliable enough to report as a specific type."*

---

## Families B, C — RetouchingFFHQ four_process / megvii_four_process (unbranded + Megvii)

| Claim type | Verdict | Evidence | Limitation |
|---|---|---|---|
| final_class=filter | **ALLOWED** | These families feed production Layer2 training (`splits/v86_train_filter.txt`, confirmed by this round's own grep: 6,872 (B) + 11,679 (C) rows) | Coarse binary signal only |
| exact artifact_type | **NOT_SUPPORTED** | `four_process.txt` (B) confirms EVERY image has all 4 operations applied simultaneously at varying intensity — there is no single "true type" to validate against, by construction, independent of any model limitation | A classifier CANNOT be right or wrong about "the" type here because there isn't one — see `ARTIFACT_TAXONOMY_ALIGNMENT.md` |
| coarse retouch/app-family label | **ALLOWED_WITH_CAVEAT** | Same four_process.txt structure | "Multiple beautification effects" is honest; "an app processed this image" is honest for C (Megvii, confirmed real commercial API per RetouchingFFHQ paper) but UNKNOWN for B (company unbranded in local files) |
| eyes region-level text | **NOT_SUPPORTED** | No pairing (`results/retouchingffhq_pair_audit_20260812.json`, reliable_pair_count=0 for both blocks) and no single operation to attribute a region to | — |
| whole-face text | **NOT_SUPPORTED** (as a GT-backed claim) / **ALLOWED_WITH_CAVEAT** (as unvalidated description) | Same pair audit | May describe "changes across the face" as a generic observation, but cannot claim it is GT-validated |
| Grad-CAM visualization only | **ALLOWED** | Floor case; heatmap can always be shown | Must not be captioned as validated |
| paired-GT-backed localization | **NOT_SUPPORTED** | `results/retouchingffhq_pair_audit_20260812.json` verdict is explicit and exhaustive: 0 local originals found across 5 candidate root directories, 120 indices checked | This is a hard NOT_SUPPORTED, not ALLOWED_WITH_CAVEAT — the audit already concluded pixel-level GT is currently impossible for this family without downloading the full 70K FFHQ dataset, a decision explicitly deferred (§8: "目前不是 blocker") |
| pixel-level/LAB-diff validation | **NOT_SUPPORTED** | Same | Same |

**Wording NOT allowed**: *"This image was identified as having undergone whitening,
localized to the cheek area."* — no basis exists to say WHICH of the 4 simultaneously-applied
operations a heatmap is "explaining," and no pixel GT exists to validate a region claim either
way.

**Wording that IS allowed**: *"This image shows characteristics consistent with digital
beautification processing; the specific technique cannot be determined with confidence from
this system."*

---

## Family D — RetouchingFFHQ Alibaba single-operation blocks

| Claim type | Verdict | Evidence | Limitation |
|---|---|---|---|
| final_class=filter | **ALLOWED** | Held-out OOD eval, 98.1% recall (`results/releases/v8.11_production_20260813/alibaba_filter_ood_v811d_layer2v811_20260813.json`, confirmed matching v8.11d production checkpoint) | Strongest external-source evidence in the whole audit, for THIS claim type only |
| exact artifact_type | **NOT_SUPPORTED** (currently) / **UNKNOWN** (whether it COULD be supported) | Folder names ARE single-operation labels (EyeEnlarging_NN/FaceLifting_NN/Smoothing_NN/Whitening_NN) — unlike B/C, a "true type" genuinely exists here. But `AIGuard/eval_ali_ood_v811.py` (read directly this round) only calls `pl.hierarchical_predict()`, which returns real/fake/filter — it **never invokes `artifact_classifier_v3`** and no per-type accuracy number against this family's own folder labels exists anywhere in this repo | This is a real, currently-open evidence gap, not a proven failure — see `EXTERNAL_FILTER_XAI_RISK_REGISTER.md` and the Findings doc's recommended next step |
| coarse retouch/app-family label | **ALLOWED_WITH_CAVEAT** | Confirmed real Alibaba commercial API output per RetouchingFFHQ paper | — |
| eyes region-level text | **NOT_SUPPORTED** | No pairing (same audit as B/C, 0/23,795 reliable pairs) | — |
| whole-face text | **NOT_SUPPORTED** (GT-backed) / **ALLOWED_WITH_CAVEAT** (unvalidated description) | Same | — |
| Grad-CAM visualization only | **ALLOWED** | Floor case | — |
| paired-GT-backed localization | **NOT_SUPPORTED** | Same pair audit as B/C applies to this family too (23,795 images, reliable_pair_count=0) | — |
| pixel-level/LAB-diff validation | **NOT_SUPPORTED** | Same | — |

**Wording NOT allowed**: *"This image's eye-enlarging filter was detected and matches the
type applied by the source app."* — the exact-type claim on THIS family has never been
tested against its own ground-truth folder labels; only the binary filter/not-filter
decision has been validated here.

**Wording that IS allowed**: *"This image was flagged as containing beautification-filter
characteristics with high confidence (validated on an independent, held-out sample of this
exact processing source); the specific filter type shown is the model's best estimate and has
not been separately validated for this data source."*

---

## Family E — other sources (Tencent etc.)

Not applicable — confirmed absent from local storage (`FILTER_DATA_PROVENANCE.csv`, family E
row). No claims of any kind are possible; this row exists to record the absence, not to rate
claims.

---

## Summary table (one verdict per family × claim-type, collapsed)

| Family | filter (binary) | exact type | coarse label | eyes region | whole-face | viz-only | paired-GT localization | pixel/LAB-diff |
|---|---|---|---|---|---|---|---|---|
| A1/A2/A3 (self-built, real base) | ALLOWED | ALLOWED (3/4 types) | ALLOWED | ALLOWED (eye_enlarging only) | ALLOWED_WITH_CAVEAT | ALLOWED | ALLOWED (eye) / CAVEAT (others) | ALLOWED |
| F (self-built, fake base) | ALLOWED_WITH_CAVEAT | ALLOWED (2/4) / NOT_SUPPORTED (whitening) | ALLOWED | NOT_SUPPORTED | ALLOWED_WITH_CAVEAT | ALLOWED | ALLOWED_WITH_CAVEAT | ALLOWED_WITH_CAVEAT (AIGuard/fake only) |
| B (RetouchingFFHQ unbranded) | ALLOWED | NOT_SUPPORTED | ALLOWED_WITH_CAVEAT | NOT_SUPPORTED | NOT_SUPPORTED | ALLOWED | NOT_SUPPORTED | NOT_SUPPORTED |
| C (RetouchingFFHQ Megvii) | ALLOWED | NOT_SUPPORTED | ALLOWED_WITH_CAVEAT | NOT_SUPPORTED | NOT_SUPPORTED | ALLOWED | NOT_SUPPORTED | NOT_SUPPORTED |
| D (RetouchingFFHQ Alibaba) | ALLOWED | NOT_SUPPORTED (evidence gap) | ALLOWED_WITH_CAVEAT | NOT_SUPPORTED | NOT_SUPPORTED | ALLOWED | NOT_SUPPORTED | NOT_SUPPORTED |
| E (Tencent / other) | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
