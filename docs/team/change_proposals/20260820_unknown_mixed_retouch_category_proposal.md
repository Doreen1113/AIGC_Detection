# Change Proposal: `mixed_retouch` / `app_processed` / `unknown_retouch` output categories for multi-operation retouch input

**Date**: 2026-08-20
**Author**: Member B (Phase 2 / XAI & external validation track)
**Status**: **PROPOSAL — NOT APPROVED, NOT APPLIED.** Nothing in this document has been
implemented. `pipeline.py`, `artifact_classifier_v3.pth`, `ARTIFACT_REGION_MAP`, `TEMPLATES`,
`ARTIFACT_UNKNOWN_THRESHOLD`, and the production JSON schema were read **read-only** to write
it and are all unchanged on disk.
**Scope under `docs/team/PRODUCTION_CHANGE_CONTROL.md`**: `pipeline.py` + explanation
template + production JSON schema. This is squarely inside the change-control list, so this
document is written to that file's mandatory 8-section structure and requires reviewer
approval before any line of it is implemented.
**Assigned backlog item**: `TEAM_WORK_ALLOCATION.md` §D, "`unknown_or_mixed_retouch` 政策提案
（僅設計，非實作）"; `WORKSTREAM_STATUS_BOARD.md` Member B item 4.

---

## 1. Problem statement

Production `pipeline.py` gives a **forced single-label answer** to a question that a large
fraction of real-world retouched input cannot honestly answer. When
`hierarchical_predict()` returns `filter`, `classify_artifact()` runs a closed-set 4-way
softmax over `["eye_enlarging", "face_reshaping", "smoothing", "whitening"]` and emits
exactly one winning type (or `unknown_filter` if top-1 confidence < 0.6), which then keys
`ARTIFACT_REGION_MAP` for a region claim and `TEMPLATES` for a type-specific sentence.

Three findings already on record show this output format is not entitled to what it emits:

**(a) The multi-operation families are a category error, not an accuracy problem.**
`results/phase2/filter_data_xai_provenance_audit_20260814/ARTIFACT_TAXONOMY_ALIGNMENT.md`
established from `FFHQ_four_process/four_process.txt`'s own per-image parameter dicts that
**every** image in families B (`FFHQ_four_process`) and C (`FFHQ_megvii_four_process`) has all
four operations applied simultaneously at independently randomised intensities. Re-verified
directly for this proposal: the file has 10,000 rows, all four keys present on every row, and
**zero** rows contain a zero-intensity operation. For this data "which one type is it?" has no
correct answer — the model cannot be right or wrong, but the *output format* still asserts a
single type. No amount of retraining `artifact_classifier_v3` fixes an output-format problem.

**(b) On the one external family that IS single-operation, the type call is at chance.**
`results/phase2/external_alibaba_artifact_validation_20260814/EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`
scored `artifact_classifier_v3` against family D's (`FFHQ_ali_process`) own folder labels.
Pooled exact-type recall on the two `VERIFIED_SINGLE_TYPE` folders (`Whitening_60`/`_90`) is
**27.5% (95% CI 23.2–31.8%, n=400)** against a 25% four-way chance floor — statistically
indistinguishable from guessing. Every folder landed at `COARSE_RETOUCH_ONLY`; **no folder
reached `EXACT_TYPE_ALLOWED`**. Meanwhile the *coarse* claim on the same data is one of the
best-evidenced numbers the project owns (Alibaba filter OOD recall 98.17%,
`results/releases/v8.11_production_20260813/`). So the system is being conservative in exactly
the wrong place: it withholds nothing at the coarse level where it is strong, and asserts a
type where it is at chance.

**(c) The existing open-set mechanism cannot catch (b), and cannot be tuned to.**
`ARTIFACT_UNKNOWN_THRESHOLD = 0.6` fires on only **2–11%** of Alibaba images
(`external_prediction_distribution.csv`, `frac_pred_unknown_filter`), because per-folder mean
softmax confidence out-of-domain is **0.87–0.96**. The model is *confidently* wrong on
external input, not *uncertainly* wrong. And lowering the threshold cannot separate the two
populations: in-domain A1 held-out confidence has median ≈1.0, so any threshold that starts
rejecting out-of-domain input rejects large amounts of correct in-domain input first. This is
a miscalibration failure, not an under-confidence failure, and **a confidence threshold is
structurally the wrong instrument for it**.

The gap this proposal closes: production has no way to say *"retouched — but I am not entitled
to name which operation"*, and no way to say *"more than one operation, and they are not
separable"*. Today both cases are silently rendered as a confident single type.

## 2. Evidence

| # | Claim | Source (traceable) |
|---|---|---|
| E1 | Families B/C are all-4-operations-per-image by construction; single-type is a category error | `ARTIFACT_TAXONOMY_ALIGNMENT.md`; `FFHQ_four_process/four_process.txt` (10,000 rows, 4/4 keys per row, 0 zero-intensity — re-verified 2026-08-20) |
| E2 | Exact-type accuracy on verified external single-operation data ≈ chance (27.5%, n=400) | `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md` |
| E3 | Coarse "this is retouched" on the same external family is strongly validated (98.17%) | `results/releases/v8.11_production_20260813/alibaba_filter_ood_v811d_layer2v811_20260813.json` |
| E4 | Open-set confidence threshold fires 2–11% OOD; mean OOD confidence 0.87–0.96; in-domain median ≈1.0 | `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md` §"Is `unknown_or_mixed_retouch` worth adding?"; `external_prediction_distribution.csv` |
| E5 | Type accuracy also collapses non-uniformly on fake-base composites (whitening 6%, eye_enlarging 70%, vs smoothing 94% / face_reshaping 92%) — i.e. entitlement varies by *regime*, not just by source | `docs/phase2_story.md` §9 (P2-C2); `results/phase2_composite_filtertype_accuracy_v1_20260813.json` |
| E6 | `COARSE_RETOUCH_ONLY` / `UNKNOWN_OR_MIXED_REQUIRED` labels and their per-folder assignment already exist as a reviewed scheme | `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md` per-folder table |
| E7 | The claim-type × family grid already rates "coarse retouch / app-family label" as ALLOWED / ALLOWED_WITH_CAVEAT for B, C **and** D, while rating "exact artifact_type" NOT_SUPPORTED for all three — an allowed claim with no output class to carry it | `FILTER_XAI_CLAIM_MATRIX.md` summary table |
| E8 | `pipeline.py` already contains a working multi-label detector path (`infer_artifact_type()` appends both `smoothing` and `whitening` when both statistical tests fire) that the `filter` branch currently bypasses | `pipeline.py` lines 386–414 vs 518–523 (read-only) |

**E7 is the load-bearing one**: the claim matrix already says the coarse label is allowed for
every external family; this proposal is not asking to permit a new claim, it is asking to add
the output class that an already-permitted claim has been missing.

## 3. Proposed design

### 3.1 Naming — one of the three categories already exists

The taxonomy-alignment doc proposed `mixed_retouch` / `unknown_retouch` / `app_processed`.
Reading `pipeline.py` for this proposal shows **`unknown_retouch` should not be created**: the
existing `unknown_filter` tag (present in `ARTIFACT_CLASSES`' consumers, `ARTIFACT_REGION_MAP`,
and `TEMPLATES`) already occupies exactly that role. Introducing a second name for the same
concept would be schema churn with no evidentiary gain. **Recommendation: keep the emitted tag
`unknown_filter`, document its role precisely (§3.2 Gate 3), and add only two new tags:
`mixed_retouch` and `app_processed`.** Where this document says "`unknown_retouch`" it refers
to the existing `unknown_filter` tag under its conceptual name.

### 3.2 The decision ladder (replaces the current single softmax call)

Evaluated in order, only when `hierarchical_predict()` has already returned `filter`. Each
gate is defined by *what kind of evidence exists*, so the four outcomes are mutually exclusive
and each is a different epistemic statement — not four flavours of "uncertain".

**Gate 0 — coarse-claim gate.** Is the "this image is retouched" claim itself validated for
this input? Today: **yes, unconditionally** (E3, plus in-domain Layer2 validation). This gate is
a declared no-op placeholder, listed so a future reviewer can see it was considered and why it
is currently always-pass; it is *not* proposed for implementation now.

**Gate 1 — multiplicity evidence → `mixed_retouch`.**
Trigger (positive evidence of ≥2 concurrent operations, **not** an uncertainty signal):
run the existing deterministic statistical detectors from `compute_skin_stats()` —
`texture_var < _SMOOTH_TEXTURE_THR (210)` ⇒ smoothing signal;
`brightness_L > _WHITE_BRIGHT_THR (147)` ⇒ whitening signal — alongside the softmax head, then
fire `mixed_retouch` when **either**:
  - (1a) both statistical detectors fire (already computable today, E8), **or**
  - (1b) a statistical detector fires for an operation the softmax head did *not* select as
    top-1 (i.e. two independent mechanisms name two different operations).
Output: `artifact_types = [<the operations with positive evidence>]` (a genuine multi-element
list, first time the field is used as designed), `suspicious_regions = []`.
Rationale for choosing this trigger: it is the only multiplicity signal in the system that is
**not** derived from the softmax whose calibration E4 shows cannot be trusted, it requires
**no retraining and no new model**, and it reuses code paths already in `pipeline.py`.
Explicitly *rejected* alternative trigger: "top1 − top2 softmax margin below τ". E4 shows the
softmax is confidently wrong OOD, so a margin rule inherits the exact miscalibration this
proposal exists to route around. It may be revisited only if §6's calibration test shows the
margin carries signal the confidence does not.

**Gate 2 — exact-type entitlement → `app_processed`.**
Trigger: the system *could* name a type, but has no measured exact-type accuracy clearing the
**≥0.70 bar already fixed in `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`** for the applicable
evidence regime. Output: `artifact_types = ["app_processed"]`, `suspicious_regions = []`,
coarse wording only.

This gate is where the proposal must be honest about a limitation it does **not** solve:
**`pipeline.py` cannot observe provenance at runtime.** A user-submitted image carries no label
saying "family D" or "self-built A1". So Gate 2 cannot be a per-image source test. Two
implementable forms, with a recommendation:

- **Form A (per-type static entitlement table)** — a new module-level
  `EXACT_TYPE_ENTITLEMENT: dict[str, bool]` whose values are set only by measured evidence.
  Under current evidence this would be a policy decision per type, not an automatic
  consequence of this document, and the honest reading of E2/E5 is that no type currently has
  validated exact-type accuracy *outside* the self-built A-family. **Recommended form**,
  because it is auditable (one table, one evidence citation per row) and degrades safely.
- **Form B (runtime domain/OOD detector)** — would actually condition on the input, but does
  not exist, would need its own training data and its own validation round, and is out of scope
  for a design proposal. **Recorded as the correct long-term answer, explicitly not proposed
  now.**

Because Form A cannot distinguish in-domain from out-of-domain input, adopting it at its
evidence-honest setting would suppress exact-type output *globally*, including for in-domain
images where §12/`FILTER_XAI_CLAIM_MATRIX.md` rate the type claim ALLOWED. **That trade-off is
the central decision this proposal hands to the reviewer, and this document does not
pre-empt it.** It is stated rather than hidden because the alternative — keeping today's
behaviour — means asserting a chance-level type on unknown-provenance input, which is the
overclaim `EXTERNAL_FILTER_XAI_RISK_REGISTER.md` already rates HIGH severity.

**Gate 3 — confidence → `unknown_filter` (unchanged).**
`ARTIFACT_UNKNOWN_THRESHOLD = 0.6`, current behaviour, **value not changed**. Its role is now
documented precisely: it is a *within-distribution* abstention mechanism. E4 is the evidence
that it must not be repurposed as the mixed/external mechanism, and the constant should carry
a comment saying so, so a future maintainer does not "fix" external overclaiming by lowering
it (which E4 shows would cost in-domain recall without buying OOD rejection).

**Gate 4 — otherwise**: current behaviour, single named type, unchanged.

### 3.3 Interaction summary with the existing open-set mechanism

| | current `unknown_filter` | proposed `mixed_retouch` | proposed `app_processed` |
|---|---|---|---|
| Triggered by | top-1 softmax < 0.6 | ≥2 independent positive operation signals | entitlement table says this regime has no validated exact-type accuracy |
| Signal source | the softmax whose OOD calibration is known bad (E4) | deterministic image statistics, softmax-independent | static policy table, input-independent |
| Statement made | "the type head declined to answer" | "more than one operation is present and they are not separable" | "retouched; type deliberately not asserted" |
| Fires OOD today | 2–11% (E4) — near-inert | n/a (new) | n/a (new) |
| Threshold change proposed | **none** | n/a | n/a |

The three are **additive and non-overlapping**; none replaces the others, and the existing
threshold is untouched.

### 3.4 Region and evidence-tier policy (consistent with `docs/xai_evidence_schema.md`)

For all three categories: `suspicious_regions = []`, whole-image framing only. This follows
`EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md` §"Region policy" verbatim — `ARTIFACT_REGION_MAP` is
keyed to a *type* prediction, so attaching any region (including the whole-face `"face"`
marker) to a category that exists *because the type is not assertable* would present the
region as more certain than the type it depends on.

Schema fields (`docs/xai_evidence_schema.md`) for records in these categories:
- `region_claim_source = "unavailable"` (no region claim is made)
- `gt_source = "none"` (no pairing exists for any RetouchingFFHQ family — 0 reliable pairs,
  `results/retouchingffhq_pair_audit_20260812.json`)
- `text_evidence_level = "global_only"`. Deliberately **not** `attention_faithfulness`, even
  though a Grad-CAM++ heatmap may still be *shown*: `docs/phase2_story.md` §9 records that the
  `filter_head` faithfulness test is an **unresolved methodological gap** (blur masking is
  itself a smoothing operation and contaminates the test), so the faithfulness tier is not
  currently earned for filter-target explanations. Heatmaps remain `VISUALIZATION_ONLY` per
  `FILTER_XAI_CLAIM_MATRIX.md`.
- `limitations` gains one of: `"multi-operation input; individual operations not separated"` /
  `"exact filter type not asserted: no validated exact-type accuracy for this evidence regime"`.

### 3.5 Proposed template wording (drafts, for review — not installed)

Lifted from wording already rated allowed in `FILTER_XAI_CLAIM_MATRIX.md` /
`EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`, and checked against
`docs/phase2_story.md` §10's runtime-vs-offline boundary (no phrasing implies a before/after
comparison at inference time):

- `mixed_retouch`: *"Multiple beautification effects were detected in this image. The
  individual editing operations could not be separated, so no single filter type is reported."*
- `app_processed`: *"This image shows signs of beauty-filter / retouching processing. The
  specific type of edit could not be reliably determined for this image."* (verbatim from the
  Alibaba doc's Allowed wording)
- `unknown_filter`: current template retained.

Banned alongside these categories (restating the Alibaba doc's ban so it travels with the
categories): any specific-type sentence, any region name, and any presentation of raw softmax
confidence as a reliability number (E2 shows 0.87–0.96 confidence coexisting with 27.5%
correctness).

### 3.6 What this proposal deliberately does not propose

No MLLM/VLM. The explanation path stays evidence-backed template/rule output. Substituting
free-generated text here is rejected project-wide (`CLAUDE.md`; `docs/phase2_story.md`;
`TEAM_WORK_ALLOCATION.md` §D "明講的防呆規則") and would in any case not supply the missing
*evidence* — it would only make the same unentitled type claim in fluent prose.

## 4. Expected benefit

- The already-permitted coarse claim (E7) finally has an output class to carry it, on the
  families where it is the *only* permitted claim (B, C, D — the majority of external
  retouch data this project holds).
- Removes the HIGH-severity risk-register item "confident but wrong external type prediction
  reaches a user-visible template sentence unflagged"
  (`EXTERNAL_FILTER_XAI_RISK_REGISTER.md`) for the routed cases.
- `mixed_retouch` is the first output that is *more informative* than today's, not just more
  cautious: "multiple effects, not separable" says strictly more than a coin-flip single type.
- Zero retraining, zero checkpoint change, zero threshold change; reuses existing code paths.

## 5. Risk / regression

| Risk | Mitigation |
|---|---|
| **Gate 2 in Form A suppresses in-domain exact-type output too** (§3.2) — a real capability regression on A-family input where the type claim is ALLOWED | Surfaced explicitly as the reviewer's decision, not decided here. If the reviewer prefers to preserve in-domain output, the honest interim is to keep exact type *and* attach the "not validated for this source" qualifier already drafted in the Alibaba doc's allowed wording — weaker than suppression, still an improvement over silent assertion |
| `mixed_retouch` false-fires on single-operation input (a heavily-smoothed-only image can also read bright) | Measurable today with zero new data — see §6. If precision on A-family single-op negatives is poor, Gate 1 falls back to condition (1a) only, or the proposal is withdrawn |
| Thresholds 210 / 147 in `compute_skin_stats` were calibrated on the AIGuard real baseline and have never been validated on external sources | Stated as a known limitation; §6 measures it. These constants are **not** proposed for change in this round |
| Users read `app_processed` as a detection failure rather than a deliberate scope limit | Wording drafted (§3.5) to state the limit affirmatively; final wording is part of the review |
| Schema consumers break on a multi-element `artifact_types` | `artifact_types` is already declared a list in schema 2.1.0; this is the first *use* of >1 element, not a type change. Still requires an explicit schema-version decision by the reviewer |

## 6. Test plan (all runnable on data already on disk — no new collection)

1. **`mixed_retouch` recall (should-fire cases)** — families B/C are all-4-operations by
   construction (E1), so every one of the 10,000 `FFHQ_four_process` rows (plus
   `FFHQ_megvii_four_process`) is a positive. Measure the Gate-1 trigger's fire rate.
   Caveat to state up front: this set contains **only** positives, so it measures recall, not
   precision.
2. **`mixed_retouch` precision (should-not-fire cases)** — family A1/A2/A3 self-built
   single-operation images and family D's Alibaba single-operation folders supply the
   negatives. A trigger that also fires on most single-operation input is useless; propose a
   pre-declared bar (e.g. false-fire rate ≤20% on A-family single-op) fixed *before* the
   measurement, per `docs/EXPERIMENT_REGISTRY.md`'s Known-Traps discipline.
3. **No in-domain regression** — re-run the existing per-type filter validation
   (`phase2_p0_v811_filter_gradcam_validation.py`-style) and confirm A-family images that
   previously received a correct exact type are not newly routed to `mixed_retouch`.
4. **Template conformance** — sample outputs across all four ladder outcomes, confirm no
   banned phrasing (specific type under `app_processed`, any region name, raw softmax
   presented as reliability, any before/after comparison wording).
5. **Threshold non-regression** — confirm `ARTIFACT_UNKNOWN_THRESHOLD` behaviour is
   bit-identical to today for in-domain input (it must not be touched by this change).

## 7. Rollback plan

All proposed changes are additive and confined to `pipeline.py`'s post-`filter` branch plus
`TEMPLATES` / schema documentation. Rollback = remove the two new tags, delete the ladder,
restore the direct `classify_artifact()` call. No checkpoint, no threshold value, no training
data, and no routing logic (`hierarchical_predict()`) is touched, so rollback cannot affect
real/fake/filter classification at all. Rollback cost is a single revert of one function.

## 8. Approval record

| Field | Content |
|---|---|
| Reviewer | 人類專案負責人 |
| Review date | 2026-08-20 |
| Verdict | **PARTIAL APPROVAL — §6 measurement plan only (Gate 1 recall/precision, no new data collection, no `pipeline.py`/schema change). Gate 2's `EXACT_TYPE_ENTITLEMENT` table (§3.2 Form A) is explicitly NOT approved and remains PENDING — its correct setting depends on a product-scope question only the reviewer can answer ("real deployment users more closely resemble the self-built in-domain A-family, or the external app-processed B/C/D-style multi-operation input?"), not on evidence this document or further research can supply alone.** No implementation of any gate is authorized by this record; §6 measurement results feed back into a future decision on Gate 2, not an automatic go-ahead to wire Gates 1/2/3/4 into production. |
| Notes | Author is not authorised to approve or apply this proposal — this record documents a human decision, not a self-approval. Gate 1's trigger mechanism (statistical-detector multiplicity) is measurement-safe and independent of the Gate 2 product question, which is why it can proceed while Gate 2 waits. |

---

## Claim / non-claim

**This document claims:**
- Families B/C are multi-operation by construction, re-verified against
  `four_process.txt` (10,000 rows, all four keys present, zero zero-intensity entries).
- `artifact_classifier_v3`'s exact-type output on the one verified external single-operation
  subset is statistically indistinguishable from chance (27.5%, 95% CI 23.2–31.8%, n=400) —
  quoted from `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`, not re-measured here.
- `ARTIFACT_UNKNOWN_THRESHOLD = 0.6` is a within-distribution abstention mechanism that is
  near-inert on the external data measured (2–11% fire rate at 0.87–0.96 mean confidence), and
  therefore structurally cannot implement the proposed categories.
- `pipeline.py` already contains an unused multi-label detection path (`infer_artifact_type`)
  that the `filter` branch bypasses, so a multiplicity trigger needs no new model.
- One of the three originally-proposed category names (`unknown_retouch`) is already
  implemented as `unknown_filter` and should be documented rather than duplicated.

**This document does NOT claim:**
- That the proposed `mixed_retouch` trigger works. Its recall and precision are **unmeasured**;
  §6 is the plan to measure them, not results. No number in this document describes the
  proposed mechanism's performance.
- That this fixes `artifact_classifier_v3`'s miscalibration. It routes around it. The
  classifier remains confidently wrong out-of-domain; nothing here retrains or recalibrates it.
- That `pipeline.py` can detect input provenance or out-of-distribution input. It cannot, and
  Gate 2 Form A is explicitly a static policy table rather than a runtime test because of it
  (§3.2). Any reading of this proposal as "the pipeline will know when it's looking at external
  data" is wrong.
- That the `compute_skin_stats` thresholds (210 / 147) are valid outside the AIGuard real
  baseline they were calibrated on. They are reused as-is and their external validity is
  untested.
- That any evidence tier changes. These categories are `global_only` / `gt_source = none` /
  `region_claim_source = unavailable`; no new localization or faithfulness claim is created,
  and the unresolved `filter_head` faithfulness gap (`docs/phase2_story.md` §9) is unaffected.
- That any of this is approved or in effect. **PROPOSAL ONLY** — implementing it requires
  reviewer approval per `docs/team/PRODUCTION_CHANGE_CONTROL.md`, plus Member A's
  Phase-1-semantics sign-off per `TEAM_WORK_ALLOCATION.md` §D.

---

## §9 Measurement Results（2026-08-20）— Gate 1 recall / precision，§6 items 1-3

> **這是核准後追加的量測證據，不是對提案內文或 §8 Approval Record 的改寫。** 上方 §1-§8
> 與 Claim/non-claim 段全部維持原樣。撰寫者：Member B。
> **本輪只做量測，沒有實作任何 gate。** 依 §8 PARTIAL APPROVAL：「§6 measurement plan only」，
> Gate 2 明確未核准。`pipeline.py`、schema、任何 checkpoint、任何 threshold **皆未改動**。
> §6 items 4-5（template conformance、threshold non-regression）**刻意未執行**，因為它們
> 預設了實作，不在核准範圍內。
> 事前門檻寫死於 `results/phase2/mixed_retouch_gate1_measurement_20260820/PRE_DECLARED_BARS.md`
> （在讀到任何數字之前）；完整結果見同資料夾 `GATE1_MEASUREMENT_FINDINGS.md`。

### 9.1 方法與母體

`compute_skin_stats`、`preprocess_jpeg`、`transform_artifact`、`hierarchical_predict`、
`_SMOOTH_TEXTURE_THR(210)`、`_WHITE_BRIGHT_THR(147)`、`ARTIFACT_UNKNOWN_THRESHOLD(0.6)`
全部由 `pipeline.py` **唯讀 import 直接使用**（非重寫複製），故量測行為與 production 無漂移。
前處理採 `run_single()` 的正式順序。checkpoint 為現行 production
（Layer1 `v817sbi` `e3057270…` + Layer2 `v811` + `artifact_classifier_v3`），SHA256 記於 manifest。
母體一律取各資料集的 `clean_output/clean_paths.txt`（依 2026-08-11 規則，不直接 glob 原始資料夾）。
**共 50,010 張，0 張讀取失敗。**

| 角色 | 群組 | n |
|---|---|---:|
| 正例（E1：全 4 種操作）| B `FFHQ_four_process` | 7,731 |
| 正例 | C `FFHQ_megvii_four_process` | 13,139 |
| **正例合計** | | **20,870** |
| 負例（自建單一操作）| A `filter_data`（4 型別，含 `lfw_*` 與 multi-scale）| 25,213 |
| 負例（外部 `VERIFIED_SINGLE_TYPE`）| D `ali Whitening_60` + `Whitening_90` | 3,927 |

其餘 10 個 ali 資料夾**未納入負例**——`EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md` 判其為
`COARSE_OR_MIXED`/`UNVERIFIABLE`，納入等於把未驗證標籤放進 precision 分母。

### 9.2 結構性發現：(1a) 是 (1b) 的真子集，OR 完全冗餘

**代數上**：(1a) 要求兩個統計偵測器都觸發；`top1` 只有一個類別，不可能同時等於
`smoothing` 和 `whitening`，因此必有一個觸發的偵測器指向 `top1` 沒選的操作——那正是 (1b)。
故 **(1a) ⇒ (1b) 恆成立**。
**實測上**：`cond_1a=1 且 cond_1b=0` 的影像 = **0 / 50,010**；全部 50,010 列 `fire == cond_1b`。

**這對提案的設計論證有直接影響**：§3.2 主張 Gate 1 的價值在於「這是系統裡唯一**不**衍生自
softmax 的多重性訊號」。(1a) 確實與 softmax 無關，**但 (1a) 從來不是實際生效的條件**。
因此 **trigger 實際上 100% 依賴 softmax**，正好繼承了 E4 所證明、本提案原本要繞開的
miscalibration。此點在量測之前不可見。

### 9.3 §6 item 1 — Recall（should-fire，100% 正例，fire rate = recall）

| 母體 | n | **fire（=recall）** | 僅 (1a) | routed to `filter` | 條件於 routed-filter 的 recall |
|---|---:|---:|---:|---:|---:|
| B `FFHQ_four_process` | 7,731 | **47.77%** [46.66, 48.89] | 7.08% | 7,168 | 48.19% |
| C `FFHQ_megvii_four_process` | 13,139 | **22.09%** [21.39, 22.81] | 1.58% | 13,100 | 22.11% |
| **B + C 合計** | **20,870** | **31.60%** [30.97, 32.23] | **3.62%** | 20,268 | **31.33%** |

（Wilson 95% CI。此資料 97.1% 都被 routing 判為 `filter`，故條件與非條件版本幾乎相同。）

**在每一張都套了全部四種操作的資料上，trigger 只在不到三分之一觸發。** 且 B 與 C 差距
**25.7pp**——兩者是同一批 FFHQ 底圖、相同的「全四種操作」內容，只是不同 app，
說明 trigger 追蹤的是各 app 的亮度呈現，不是操作多重性。
依事前宣告，recall **無門檻**（always-fire 也能拿 100%），必須與 9.4 併讀。

### 9.4 §6 item 2 — Precision（false-fire）對照事前門檻 ≤20%

| 母體 | n | **false-fire** | 僅 (1a) |
|---|---:|---:|---:|
| **A-family 單一操作全體（門檻適用母體）** | **25,213** | **19.12%** [18.64, 19.61] | **1.14%** |
| — A `whitening` | 6,370 | **3.38%** | 0.86% |
| — A `smoothing` | 6,233 | 22.69% | 1.85% |
| — A `eye_enlarging` | 6,441 | 23.43% | 0.53% |
| — A `face_reshaping` | 6,169 | 27.27% | 1.36% |
| D `ali` 合計（僅供外部效度參考，非門檻）| 3,927 | **25.39%** [24.05, 26.77] | 1.20% |

> **判定：A-family 19.12% ≤ 20%，依事前宣告的規則，trigger 通過了 precision 門檻**（餘裕 0.88pp）。
> 此處**照字面回報，不事後移動門檻**（那正是 Known Traps 紀律要防止的事）。
> 但同一批量測提供了門檻本身抓不到的證據，見 9.5；且外部 D-family 為 25.4%，**高於 20%**
> ——門檻當初只宣告在 A-family，故此為 context 而非 fail，但方向正是本提案要服務的外部輸入。

### 9.5 決定性發現：trigger 量到的是底圖亮度的 base rate，不是多重性

| A-family 真實操作 | `sig_white`(L>147) | `sig_smooth`(var<210) | softmax top-1 | **fire** |
|---|---:|---:|---|---:|
| `whitening` | 30.16% | 2.29% | `whitening` 97.3% | **3.38%** |
| `smoothing` | 22.70% | 7.01% | `smoothing` 99.8% | 22.69% |
| `eye_enlarging` | **22.28%** | 1.75% | `eye_enlarging` 99.3% | 23.43% |
| `face_reshaping` | **23.70%** | 4.94% | `face_reshaping` 99.7% | 27.27% |

`eye_enlarging` 與 `face_reshaping` 是純幾何 warp，**完全不改變膚色亮度**，但
`brightness_L > 147` 在它們身上分別觸發 22.3% / 23.7%。這就是**底圖本身的 base rate**
越過一個在別的母體上校準的門檻——正是本提案 §5 第 3 列自己標註的
「210/147 從未在外部來源驗證」限制。

整個 trigger 的行為由此完全解釋：
- **幾何**單一操作圖：`sig_white` 以 base rate 觸發，而 `top1` 正確地說是
  `eye_enlarging`/`face_reshaping` → 構成「不一致」→ **(1b) 對雜訊觸發**。
- **whitening** 單一操作圖：`sig_white` 觸發率反而最高（30.2%），但 `top1` 正確說是
  `whitening`，沒有不一致 → 全表最低的 **3.38%**。**唯一亮度偵測器真正判對的型別，
  正是 trigger 最安靜的型別。**
- **B/C 多操作**圖：`sig_white` 觸發 32.4%，僅比幾何圖的 22-24% base rate 高約 8-10pp，
  儘管它們 100% 都真的套了 whitening。

即偵測器只在 ~22-24pp 的雜訊地板上加了約 8-10pp 的真實訊號，而 (1b) 把兩者一併轉成 fire。
**正負母體 31.6% vs 19.1%（僅 +12.5pp 區辨力）與「雜訊地板為兩者共有而互相抵銷」一致。**
這是關於「用這兩個門檻建構的 trigger 家族」的機制性結論，不是單一數值的調參抱怨；
它也在不需要新資料的情況下解釋了 9.3 的 B/C 25.7pp 落差。

### 9.6 §6 item 3 — In-domain regression

A-family 中 production **今天就答對**的影像（raw argmax == 真實操作 **且** conf ≥ 0.6，
即 `pipeline.py` 實際會輸出該精確型別）：**24,924 / 25,213 = 98.85%**
（`artifact_classifier_v3` 的 in-domain 精確型別準確率近乎完美，正是 E2 用來對比其
27.5% 外部準確率的背景）。

| 目前答對的子集 | n | 會被新觸發 → 改判 `mixed_retouch` |
|---|---:|---:|
| **全體** | **24,924** | **19.00%**（4,735 張）|
| `whitening` | 6,171 | 2.33% |
| `smoothing` | 6,218 | 22.64% |
| `eye_enlarging` | 6,391 | 23.52% |
| `face_reshaping` | 6,144 | 27.34% |

**Gate 1 依原規格實作，會把 19.0%（4,735/24,924）目前答對的 in-domain 精確型別答案，
換成「多重效果、無法分離」。** 這些是今天輸出正確的圖，因此屬**純粹能力損失、無準確度增益
可抵銷**，且集中在 9.5 顯示亮度偵測器本就不該觸發的兩個幾何型別（23-27%）。
若改用**僅 (1a)**，同一數字為 **1.15%**。

### 9.7 對 §6 item 2 事前宣告後果表的對應，與給 reviewer 的選項

事前宣告的後果表為：combined ≤20% → 「as specified 可用」；>20% 但 (1a) ≤20% → 退回僅 (1a)；
兩者皆 >20% → 撤回/重設計。**實測 combined 19.12% 落在第一格**，故 §5 的 fallback 條款
未被機械式觸發。但 9.2 顯示 (1a) 在 OR 內從不生效，9.5 顯示 (1b) 實際在回應什麼。
中性列出三個選項（**本文件不做決定**）：

- **(i) 依原規格實作**：換得多操作輸入 31.6% recall，代價是 19.0% 正確 in-domain 答案被改判；
  依實測證據，該代價主要由雜訊驅動。
- **(ii) 退回僅 (1a)**：recall 3.62%、false-fire 1.14%、in-domain regression 1.15%。
  安全且如原設計意圖般與 softmax 無關，但觸發率低到幾乎不改變 production 行為。
- **(iii) 撤回此形式的 trigger**，把本發現本身當成結果：現有兩個膚色統計量所能提供的多重性
  證據太弱，撐不起 Gate 1，因為提案自己已標註的門檻外部效度缺口實際上主導了訊號。
  真正的多重性偵測需要今天並不存在的 per-operation 證據。

### 9.8 本輪的 claim / non-claim

**支持**：(1a)⇒(1b) 恆成立（0/50,010 例外）；combined trigger 通過事前 ≤20% 門檻（19.12%）；
100% 多操作資料上 recall 僅 31.6%；主導因素為底圖亮度 base rate；實作將改判 19.0% 目前正確的
in-domain 答案；僅 (1a) 精確但 recall 3.62%。
**不支持**：對 **Gate 2 沒有任何結論**（不在範圍，維持 PENDING，§8 的產品定位問題完全未觸及）；
非對 210/147 門檻本身的驗證或否證（本輪不得更動它們）；非對真實使用者輸入的 precision；
B/C 觸發率**不是**使用頻率的證據。
**本文件不授權任何實作**——依 §8：「§6 measurement results feed back into a future decision on
Gate 2, not an automatic go-ahead to wire Gates 1/2/3/4 into production.」

### 9.9 本 addendum 動到的檔案

- 新增：`results/phase2/mixed_retouch_gate1_measurement_20260820/`（bars、findings、manifests、log）
- 新增：`phase2_mixed_retouch/measure_gate1_offline.py`、`phase2_mixed_retouch/analyse_gate1.py`
- 本檔案：僅**追加**本 §9，§1-§8 與 Claim/non-claim 段未改動
- **未動**：`pipeline.py`、schema、`TEMPLATES`、`ARTIFACT_UNKNOWN_THRESHOLD`、任何 checkpoint、
  任何既有 `results/` 內容；未實作任何 gate

---

## §10 Gate 1 Trigger **重新設計**量測（2026-08-20，第二輪）

> **這是接續 §9 的第二輪量測附錄，不是對 §1-§9 或 §8 Approval Record 的改寫**；上方內容全部維持原樣。
> 撰寫者：Member B。**本輪一樣只做量測與門檻校準，沒有實作任何 gate、沒有訓練任何模型。**
> `pipeline.py`、schema、`TEMPLATES`、`ARTIFACT_UNKNOWN_THRESHOLD`、210/147、任何 checkpoint 皆未改動。
> Gate 2 維持 PENDING（人類負責人的傾向為 advisory，本輪**不**視為核准）。
> 事前設計與門檻寫死於
> `results/phase2/mixed_retouch_gate1_redesign_20260820/PRE_DECLARED_BARS_REDESIGN.md`（讀到任何數字之前）；
> 完整結果見同資料夾 `GATE1_REDESIGN_FINDINGS.md`。

### 10.1 本輪要修的兩個問題（來自 §9）

**P1**：(1a)⇒(1b) 恆成立（0/50,010），trigger 實際 100% 依賴 softmax，與 §3.2 自己的設計理由矛盾。
**P2**：`brightness_L>147` 在純幾何濾鏡上以 22-24% 的**底圖 base rate** 觸發，量到的不是多重性。

### 10.2 候選設計（事前固定）

| id | 規則 | 想修的問題 |
|---|---|---|
| `C0` | `texture_var_skin < t1` **AND** `L_skin > t2`，t 於 CAL 重新校準 | P1（完全不讀 softmax） |
| `R1` | `d_smooth > t1` **AND** `d_white > t2`，其中 `d_smooth=log((tex_ring+1)/(tex_skin+1))`、`d_white=L_skin−L_ring`（**同一張圖內**的參考環正規化） | P1 + P2 |
| `R2` | `min(z(d_smooth),z(d_white)) > t1` **AND** `softmax p2 > t2` | P1，但改成**連續**讀 softmax（runner-up 質量），並要求獨立統計通道同時成立 |

`filters_v2` 的 LAB diff / landmark displacement **事前排除**：讀 `scale_normalized_filters.py`
可見兩者都是**生成端對 before/after 配對**的量測（`apply_whitening_v2` 保留 `l_before`），
runtime 只有 after 圖，**不可能當推論證據通道**。

母體、清洗規則與 §9 完全相同（50,010 張，0 讀取失敗，checkpoint SHA256 相同）。
新增 `sha256(path)` 決定性 50/50 CAL/TEST 切分（CAL 25,032 / TEST 24,978）；
**所有門檻只在 CAL 擬合，所有數字只報 TEST**，`ORIG` 也重報 TEST 以求可比。

### 10.3 結果（TEST 半，matched operating point，事前門檻 ≤20%）

| trigger | B+C recall (95% CI) | A false-fire | D false-fire（context） | in-domain regression | 判定 |
|---|---|---|---|---|---|
| `ORIG` | **31.49%** [30.61, 32.39] | **19.22%** | 25.10% | **19.08%** | 參考點 |
| `ORIG_1A` | 3.59% | 1.00% | 1.29% | 1.01% | 參考點 |
| `C0` | 31.36% [30.47, 32.25] | 19.95% | 19.03% | 20.03% | **不算改善** |
| `R1` | 18.37% [17.64, 19.13] | 19.83% | 21.50% | 19.80% | **不算改善** |
| `R2` | 77.81% [77.00, 78.60] | 18.67% | **74.23%** | 17.81% | **字面上通過門檻，但被 10.4 的對照否決** |

低 false-fire 區（Known Trap #2）：`C0` 於 10%/5%/1% 預算下 recall 20.51%/12.29%/3.36%，
`R1` 8.92%/4.94%/1.00%，`R2` 63.31%/46.64%/13.34%。整族落在**同一條曲線**上。

### 10.4 決定性對照：`R2` 量到的是「來源」，不是「多重性」

D family（Alibaba `Whitening_60/_90`）是**外部但已驗證單一操作**。真正的多重性訊號必須在
B/C 觸發、在 D **不**觸發。TEST AUROC：

| 對比 | 測什麼 | `p2` | `entropy` |
|---|---|---|---|
| B/C vs **A** | 混淆（來源⊕多重性⊕訓練集成員） | **0.870** | 0.873 |
| B/C vs **D**（兩者皆外部） | **乾淨的多重性測試** | **0.540** | 0.549 |
| **D vs A**（兩者皆單一操作） | **乾淨的來源測試** | **0.852** | 0.854 |

softmax runner-up 質量分辨**來源** AUROC 0.85，分辨**多操作 vs 單操作只有 0.54＝碰運氣**；
`R2` 在**已驗證單一操作**的外部圖上觸發 **74.23%**，幾乎等於它在真正多操作圖上的 77.81%。
它是個 OOD 偵測器，不是多重性偵測器。另外 `R2` 擬合出的 `t1=−5.63` 被 **100%** 影像通過
（`R1` 的 `t1=−3.22` 亦然），兩者實際都退化成**單一通道**規則。

### 10.5 各候選失敗的機制（不是調參問題）

- **`C0` 免費修好 P1，但一分不賺**：完全不讀 softmax，卻把 `ORIG` 的操作點復現到 recall 差 0.13pp。
  這反過來證明 **P1 診斷出的 softmax 耦合從來不是 trigger 效能的來源**，曲線是被兩個膚色統計量本身的
  弱區辨力決定的。P2 也沒修好：`C0` 在 `face_reshaping` 仍誤觸 26.34%、`eye_enlarging` 12.85%。
- **`R1` 的自我正規化把訊號抵消掉**：正例平均 `d_white`=13.92，反而**低於**單一操作
  `whitening` 的 20.93、與純幾何 `eye_enlarging` 的 13.52 幾乎相同。原因在原始統計量裡看得見：
  B/C 的 app 是**整張圖**提亮（B 的 `L_skin` 均值 145.5 vs A-family 129.4），
  skin−ring 差值恰好把要偵測的效果消掉；而自建 `apply_whitening_v2` 用**臉部 mask**，才留得下來。
  自我正規化對「局部皮膚編輯」是對的工具，對「全域編輯」是錯的，而外部家族正是全域。
- **`R2` 照設計意圖修好了 P1，仍然失敗**，因為唯一有力道的通道是來源偵測器。

### 10.6 反向波及 §9 的量測效度發現

`AIGuard/train_artifact_classifier_v3.py` 以 `filter_data/clean_output/clean_paths.txt`
80/10/10 訓練 `artifact_classifier_v3`——**那份檔案就是 A-family precision 負例母體**。
因此 §9 與本輪用來量 precision 的負例，約 80% 是該 softmax head 的**訓練影像**。
後果：§9 的 19.12% 是**最有利情況**的數字；同一 trigger 在 D family 上是 25.10%（本輪 TEST）／
25.39%（§9 全母體），只要負例不是分類器自己的訓練資料就 +5.9pp。此點**不用來移動任何門檻**，
只如實記錄。

### 10.7 結論（落在事前宣告後果表的第三格）

**沒有任何候選通過 Bar 2。** 依事前宣告如實回報負面結論：`pipeline.py` 現有的兩個膚色統計通道
——不論絕對值、重新校準、或同圖自我正規化——加上對現有 4-way softmax 的**所有**讀法
（top-1 身分、runner-up 質量、entropy、margin），**都不足以支撐 Gate 1**。
整個特徵空間裡最好的乾淨多重性訊號是 `neg texture_var_skin`，B/C-vs-D AUROC 僅 **0.620**。
可用的 Gate 1 需要**今天系統裡不存在的 per-operation 證據**——與 §9 從另一個方向得到的結論一致，
差別在這次是把重新設計**實測掉**，而不是用推論假設掉。
沒有放寬任何門檻、沒有更換負例母體、沒有把 CAL 數字當標題數字、沒有從分母移除幾何型別。

### 10.8 本 addendum 動到的檔案

- 新增：`results/phase2/mixed_retouch_gate1_redesign_20260820/`（事前門檻、findings、manifests、log）
- 新增：`phase2_mixed_retouch/{measure_gate1_redesign.py, analyse_gate1_redesign.py, control_checks_redesign.py}`
- 本檔案：僅**追加**本 §10；§1-§9 與 Claim/non-claim 段未改動
- **未動**：`pipeline.py`、schema、`TEMPLATES`、任何 threshold 常數、任何 checkpoint、
  `results/phase2/mixed_retouch_gate1_measurement_20260820/` 既有內容；未實作任何 gate；未 git commit

---

**Files read (read-only) to produce this document**: `pipeline.py`,
`docs/xai_evidence_schema.md`, `docs/phase2_story.md`, `docs/team/PRODUCTION_CHANGE_CONTROL.md`,
`docs/team/TEAM_WORK_ALLOCATION.md`,
`results/phase2/filter_data_xai_provenance_audit_20260814/{ARTIFACT_TAXONOMY_ALIGNMENT.md,FILTER_XAI_CLAIM_MATRIX.md}`,
`results/phase2/external_alibaba_artifact_validation_20260814/EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`,
`FFHQ_four_process/four_process.txt`.
**Files written**: this file only.
