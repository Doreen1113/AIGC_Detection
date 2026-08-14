# Phase 1 Freeze Decision — v8.11 Production

> Formal freeze decision record for the v8.11 hierarchical classifier (Layer1d + Layer2 v811),
> written after the 2026-08-13 P0 Production Evaluation Integrity Repair closed the
> evaluation-provenance gaps that previously prevented an unqualified freeze statement. This
> document does not introduce new evaluation numbers — every figure it cites is sourced from
> `RELEASE_RESULTS.md`'s official production score table.

## Decision

**Freeze decision: APPROVED — for static-image research baseline scope only.**

`shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth` is frozen as
`Phase1-v8.11-freeze`, matching CLAUDE.md's own 2026-08-13 freeze declaration. This decision
record formalizes that freeze against the now-fully-verified evidence base (see
`RELEASE_MANIFEST.json`'s status block: `checkpoint_provenance_status`,
`evaluation_integrity_status`, `filter_xai_status`, `desktop_tflite_status` all VERIFIED).

The freeze is scoped explicitly to: **a deployable candidate for single static-image
real/fake/filter classification**, evaluated and gated on desktop/CPU-measured metrics. It is
**not** a freeze of a system verified for real mobile deployment (see iOS gate below) and
**not** a claim of universal cross-dataset or video-deepfake generalization (see
`RELEASE_BOUNDARY.md`).

## Core gate = PASSED

All A-tier Freeze Gate metrics pass, each now backed by a fresh, hash-verified result file
(see `RELEASE_RESULTS.md` official table):

| Gate | Threshold | Result | Status |
|---|---:|---:|---|
| True Test fake recall | ≥95% | ~99% | PASSED |
| True Test filter recall | ≥90% (Freeze Gate table uses ≥92%) | 93.6% | PASSED |
| True Test paired balanced accuracy | ≥80% | 81.1% | PASSED |
| AIGuard-unseen fake AUROC | ≥0.80 | 0.8150 | PASSED |
| CelebA real recall | ≥95% | 99.7% | PASSED |
| StyleGAN2 fake recall | ≥95% | 99.6% | PASSED |
| Alibaba filter OOD recall | ≥95% | 98.1% | PASSED |
| fp32 TFLite combined size | ≤25 MB | 20.91 MB | PASSED |

## Stretch goals = NOT PASSED, but do not block freeze

Per the Freeze Gate rules established in CLAUDE.md/TODO.md, these are explicitly B-tier —
tracked, documented, and expected to remain open at freeze time without blocking it:

| Stretch goal | Target | Current | Status |
|---|---:|---:|---|
| Shadow paired balanced accuracy | ≥60% | 43.5% | NOT PASSED (documented, not silent) |
| Shadow filter recall | ≥40% | ~10-28% (checkpoint-dependent) | NOT PASSED (documented, not silent) |
| Fake+filter end-to-end misclassification | ≤2% | 3.71% | NOT PASSED (documented, not silent) |
| Cross-source `has_filter` joint recognition | ≥25% | 4.53% (v8.16 research track only) | NOT PASSED, research-only attempt made |
| FF++ fake recall | ≥70% | not met | NOT PASSED (architectural video-domain gap, out of Phase 1 scope) |
| int8 mobile deployment | correctness preserved | blocked (FFT dynamic-range issue) | NOT PASSED (root-caused, not merely observed) |

None of these block the freeze. Each is written into `RELEASE_BOUNDARY.md` and the project's
Limitation & Future Work framing, not hidden or silently deferred.

## iOS deployment gate = PENDING (the one gate not yet passed)

| Gate | Threshold | Result | Status |
|---|---:|---:|---|
| Real-device (iPhone) on-device latency/RAM/stability benchmark | must complete | not attempted | **PENDING** |

This is the sole remaining item standing between `Phase1-v8.11-freeze` (a frozen *research*
baseline) and a fully verified *mobile production* release. All static/desktop evidence this
release depends on is now VERIFIED (see `RELEASE_MANIFEST.json`); the iOS gate is
independent of that evidence and unaffected by the P0 repair — it was never claimed done, and
remains explicitly not done.

## Next required task

**iPhone on-device benchmark**: measure real-device latency, RAM/peak memory, and stability
(cold start, thermal throttling behavior, repeated-inference stability) for the fp32 TFLite
pair (`layer1_v811d_float32.tflite` + `layer2_v811_float32.tflite`, 20.91 MB combined) on
actual iOS hardware. Until this is complete, the release stays at `release_status:
FROZEN_DESKTOP_VALIDATED` rather than a fully verified mobile production release. Completing
this benchmark is the only action that can upgrade `ios_on_device_status` from PENDING.

## Non-required future research (does not block freeze, does not block iOS benchmarking)

These remain open research directions, explicitly not required before or after the iOS
benchmark, and explicitly not to be treated as blocking the freeze decision above:

- **Shadow domain generalization** — closing the cross-photography-style gap (43.5% → the
  ≥60% stretch target) that v8.12/v8.13/v8.14 each partially addressed at the cost of
  regressing fake+filter accuracy. No committed approach yet; requires further base-image
  diversity research per the C1 research track in TODO.md.
- **Cross-source fake+filter (`has_filter`) joint recognition** — the v8.16 mixed-lineage
  research line improved this from 2.02% to 4.53% but remains far short of a usable target,
  and left several filter types with zero measurable improvement. Continuing this is a
  research-track decision, not a production blocker.
- **FF++ / video deepfake detection** — would require official manipulation masks (FF++ ships
  these for its classic methods) and training on video-frame sources this project has
  deliberately excluded from Phase 1's static-image scope. A distinct, larger scope expansion,
  not a Phase 1 freeze item.
- **int8 / mixed-precision mobile deployment** — blocked by the FFT branch's ~7.6×10⁹ dynamic
  range; a fix would require either a different frequency-domain representation or a
  per-channel/per-tensor quantization scheme not yet explored. fp32 TFLite (verified working)
  remains the deployment path until this is resolved.

## Traceability

- Freeze gate table source: TODO.md "🔒 Phase 1 Freeze Gate" section, cross-checked against
  `RELEASE_RESULTS.md`'s official production score table (2026-08-13 P0-repair-sourced
  numbers).
- Status block this decision is built on: `RELEASE_MANIFEST.json`.
- Boundary/scope framing this decision assumes: `RELEASE_BOUNDARY.md`.
- Evaluation-integrity evidence chain: `EVALUATION_INTEGRITY_REPAIR.md` and
  `results/releases/v8.11_production_20260813/RELEASE_EVALUATION_MANIFEST.json`.
