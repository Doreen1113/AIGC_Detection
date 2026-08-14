# P1-R1.5: Resolution Causal Audit — Findings

> Follow-on to P1-R1 (`results/research/p1_r1_cross_source_failure_anatomy_20260814/`).
> Diagnostic-only, controlled-resampling round. No checkpoint trained/modified, `pipeline.py`
> and the frozen v8.11 production release untouched, no existing result/split file
> (including yesterday's P1-R1 outputs) overwritten. All findings below are tagged
> **OBSERVED** (a measured fact), **CAUSAL_SUPPORT** (the controlled design permits a causal
> reading), or **UNRESOLVED** (evidence insufficient or the control itself doesn't hold),
> per the task's explicit request — these tags are not used interchangeably.

## 0. Was the resolution control actually valid?

**Mixed — valid for 2 of 4 filter types, confounded for the other 2. This is the single most
important caveat governing how to read everything below.**

Read directly from `filters/stress_test_filter_functions.py` (unmodified, only read) and
confirmed in `control_validation.csv` (800 rows, one per base_id × filter_type):

| Filter type | Validity | Why (code-level fact) |
|---|---|---|
| `whitening_medium` | **VALID** (198/200 groups complete) | `apply_whitening` is a pure per-pixel LAB tone shift (`L += 0.15*(255-L)`) — no spatial kernel, no pixel-count parameter anywhere. Resolution-invariant by construction. |
| `eye_enlarging` | **VALID_WITH_CAVEAT** (198/200) | Warp radius = `eye_width_px_at_current_resolution × 1.70`, re-measured fresh at each resolution from freshly-detected landmarks — self-scaling by design, so relative filter strength is approximately constant across resolution. Caveat: landmark-detection precision and `cv2.remap`/`INTER_CUBIC` interpolation quality are not separately controlled for. |
| `smoothing_medium` | **INVALID** (198/200 groups, but flagged invalid regardless) | `cv2.bilateralFilter(bgr, d=15, ...)` uses a **fixed 15-pixel diameter** regardless of image resolution. A 15px kernel is a dramatically different *relative* blur strength on a 256×256 image than on a 1024×1024 image of the same face. The underlying filter *operation* is not held constant across resolution — confirmed by reading the code, not assumed. |
| `face_reshaping` | **INVALID** (198/200) | Warp radius is **fixed at 60.0 pixels**, same issue as smoothing — and this exact confound was already independently flagged in `pipeline.py`'s own code comments ("face_reshaping's fixed 60px warp radius saturates most regions at dataset scale"), now confirmed to also break the resolution-audit's independent-variable assumption. |

2/200 base images are `MISSING` for every filter type (landmark detection failed at one or
more canonical resolutions for those 2 specific bases — excluded, not guessed, per the task's
instruction).

**Practical consequence**: findings for `whitening_medium`/`eye_enlarging` below are
genuinely causal (resolution was the only thing that varied). Findings for
`smoothing_medium`/`face_reshaping` are reported as **OBSERVED** data (real measurements, real
numbers) but explicitly **cannot** support a **CAUSAL_SUPPORT** verdict about "resolution"
specifically — a change in score for these two types could be caused by resolution's effect
on the *model*, or by resolution's effect on the *physical strength of the filter itself*, and
this design cannot separate the two. Both readings are given below where relevant.

## 1-2. Manifests and control validation

`resolution_manifest.csv` (3,970 rows: native + canonical_256/512/1024, clean + 4 filter
types, per base image) and `control_validation.csv` (800 rows) — see Section 0 for the
headline result. Every row traces a source image SHA256, base/resized resolution, face bbox
(where applicable), filter parameters, and output SHA256, per the task's traceability
requirement. 2,376 new composite/clean images were generated (canonical_256/512/1024
conditions); the `native` condition reuses the 994 existing `v815_replication_set/` files
completely unmodified (0 new files for that leg).

## 3. Inference results

`source_by_filter_by_resolution_metrics.csv` (240 rows: 3 model variants × 5 sources × 4
filter types × 4 resolutions). Sanity-consistent with P1-R1: at `native` resolution, this
round's freshly-recomputed AUROC values match P1-R1's `source_by_filter_metrics.csv` values
for the same (model, source, filter_type) cells (e.g. v816@0.95, DiT, smoothing_medium: 1.000
in both rounds).

---

## Explicit answers

### Does canonicalizing to 256 improve pixart/sd2.1?

**whitening_medium (VALID control): OBSERVED, essentially no — CAUSAL_SUPPORT: no meaningful
resolution effect found.** pixart AUROC native→canonical_256: 0.538→0.655; sd2.1:
0.499→0.567. Both remain well within chance-level territory (95% CIs in
`source_by_filter_by_resolution_metrics.csv` include 0.5 at every resolution for both
sources). There is a small upward wobble at 256 for *every* source (including DiT/SiT/ddim,
which also don't need rescuing) — consistent with generic resize/interpolation noise, not a
targeted resolution-fixes-the-gap effect.

**eye_enlarging (VALID_WITH_CAVEAT control): OBSERVED, no. CAUSAL_SUPPORT: no meaningful
resolution effect found.** pixart: 0.564→0.568; sd2.1: 0.511→0.531. Flat within noise.

**smoothing_medium (INVALID/confounded — reported as OBSERVED only, no causal claim):**
dramatically yes, but this cannot be attributed to resolution alone. pixart AUROC jumps
0.512→0.968 and sd2.1 jumps 0.652→0.972 when canonicalized to 256px — nearly matching
DiT/SiT/ddim's already-high canonical_256 AUROC (0.997–1.000). Joint recognition follows the
same pattern (pixart 0.0%→20.9%, sd2.1 0.0%→10.8%, `source_by_filter_by_resolution_metrics.csv`).
See Figure 1 and Figure 2. **This is the single largest effect found in this entire round**,
but per Section 0, a 15px bilateral-filter kernel is physically a much stronger relative blur
at 256px than at pixart's native 1024px — so this observation is equally (arguably more)
consistent with "the filter was barely applying any real blur at native pixart/sd2.1
resolution in the first place" as with "the model specifically fails to recognize smoothing
on higher-resolution sources." Both readings point toward the same practical fix (see
Recommended Next Step).

**face_reshaping (INVALID/confounded): OBSERVED, partially yes, but a residual gap remains.**
pixart: 0.500→0.548; sd2.1: 0.490→0.543 — a small rise, but nowhere near DiT/SiT/ddim's
canonical_256 AUROC (0.733–0.798). Even setting aside the confound, resolution-matching alone
does not close this gap for face_reshaping.

### Does canonicalizing to 512/1024 degrade the 256px-native sources (DiT/SiT/ddim)?

**whitening_medium / eye_enlarging (VALID controls): OBSERVED, no meaningful degradation —
CAUSAL_SUPPORT: no resolution effect in either direction**, because there was no signal to
degrade in the first place (AUROC already near chance at native 256px for both types, stays
near chance at 512/1024 too — see Figure 3, top-left/top-right-equivalent panels).

**smoothing_medium (INVALID/confounded, OBSERVED only): yes, severely, and this is the
cleanest large effect in the round.** DiT AUROC collapses from 1.000 (native/256) to 0.745
(512) to **0.333 (1024, below chance — an inverted signal)**; SiT: 1.000→0.668→0.278; ddim:
1.000→0.732→0.241. Joint recognition follows the same collapse (e.g. ddim 60-70%→2.5%→0.0%).
See Figure 3 and Figure 5 (with 95% CI — the collapse is far outside CI overlap, a real
effect, not noise). Under the fixed-15px-kernel reading, this is exactly what's expected:
at 1024px a 15px-diameter blur is nearly imperceptible relative to face size, so there is
almost no physical smoothing effect left for the model to detect — this is best read as **the
filter itself losing potency at high resolution**, not the model "forgetting" how to detect
smoothing.

**face_reshaping (INVALID/confounded, OBSERVED only): yes, same direction, smaller magnitude.**
DiT: 0.748(256)→0.568(512)→0.515(1024); similar for SiT, ddim. Consistent with the same
fixed-pixel-radius mechanism, proportionally smaller because face_reshaping's 60px radius is
larger relative to a typical face crop than smoothing's 15px kernel.

### Is resolution sufficient to explain the source-level failure, or does a generator-specific residual gap remain after resolution-matching?

**UNRESOLVED for whitening_medium/eye_enlarging** — cannot answer either way, because there
is no detectable signal for ANY source at ANY resolution for these two (clean, valid-control)
filter types. The resolution hypothesis is not falsified here, but it is **untestable with
this filter-type pair** since there's no baseline effect to explain in the first place (a
floor effect, not evidence of "resolution doesn't matter").

**For smoothing_medium (OBSERVED, not CAUSAL_SUPPORT due to confound): resolution alone looks
sufficient to explain nearly all of the observed source-level gap.** At canonical_256, all
five sources — including the two that fail badly at native resolution — converge to a tight,
uniformly high AUROC band (0.968–1.000). If a generator-specific residual gap existed
independent of resolution, we would expect pixart/sd2.1 to still lag DiT/SiT/ddim even after
matching resolution; they do not (0.968/0.972 vs 0.997–1.000, a gap of ≤0.03 AUROC, well
within the natural spread already seen among DiT/SiT/ddim themselves at native resolution).
**Caveat, restated**: because the filter operation itself is not resolution-invariant for
this type, "resolution alone is sufficient" and "the filter's real physical strength is what
varies, and it happens to correlate with resolution" are observationally indistinguishable
in this design.

**For face_reshaping (OBSERVED): a residual gap remains even after resolution-matching.**
Canonical_256 AUROC for pixart (0.548) and sd2.1 (0.543) remains clearly below DiT/SiT/ddim's
canonical_256 AUROC (0.733–0.798) — resolution-matching narrows but does not close the gap for
this filter type, suggesting *something else* (generator fingerprint, or a different
resolution-dependent aspect of the geometric warp not captured by simple canonicalization)
contributes here beyond what a single global resize can fix.

---

## Recommended next step

**Filter-generator redesign (scale-adaptive kernel/radius parameters), not resolution-
consistency training and not source disentanglement, is the best-evidenced next step for
`smoothing_medium` and `face_reshaping` specifically — and the two clean-control filter types
(`whitening_medium`, `eye_enlarging`) give no evidence to justify any intervention at all
right now, because there's no signal present to fix.**

Reasoning, not hedged: the single largest, cleanest, most dramatic effect in this entire round
— smoothing's near-perfect AUROC convergence at 256px and near-total collapse at 1024px,
symmetric in both directions, for every source tested — is fully consistent with a simple,
already-known, already-documented mechanism: this project's own filter-generation code uses
fixed-pixel spatial parameters (15px blur kernel, 60px warp radius) that were tuned/calibrated
implicitly against the AIGuard/fake-dominant, historically lower-and-more-uniform-resolution
training distribution, and simply do not scale to DF40-cdf's native 512–1024px sources. This
is a **data-generation** problem with a direct, testable fix — make `apply_smoothing`'s kernel
diameter and `apply_face_reshaping`'s warp radius scale with detected face size (the same
self-scaling pattern `apply_eye_enlarging` *already* uses successfully, per this round's own
code reading) — **not** a model-architecture or model-training problem. Resolution-consistency
*training* (resizing training data to match test-time resolution distributions) would likely
help as a band-aid but does not address the root cause the way fixing the filter generator
does, and source disentanglement / representation-invariance training is actively **not
supported** by this round's evidence: the residual gap that remains after resolution-matching
(face_reshaping) is small relative to the huge confounded effect that resolution/filter-scale
alone appears to explain (smoothing), so there currently isn't enough evidence of a genuine
*representation*-level entanglement problem to justify designing an invariance mechanism
around it — consistent with P1-R1's own finding that Cell D (an invariance-loss variant
already tried) produced small gains at high cost.

This is a next-**testable-method-choice** pick, not an implementation — no loss function or
architecture change is proposed here, per this round's scope.

## Non-claims

This round does not claim the resolution/filter-scale mechanism is the *only* thing going on
(face_reshaping's residual gap after resolution-matching says otherwise), does not claim
whitening_medium or eye_enlarging are resolution-insensitive (only that no evidence either way
exists because there's no baseline signal), and does not recommend a specific implementation
of a scale-adaptive filter parameter — only that redesigning the filter generator's spatial
parameters is the best-evidenced category of next step among the options considered.
