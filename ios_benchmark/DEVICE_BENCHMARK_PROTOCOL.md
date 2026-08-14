# Device Benchmark Protocol — v8.11 Production, iOS On-Device

> The exact procedure to run once a Mac + Xcode + a physical iPhone are available. This
> document formalizes and is consistent with the protocol already sketched in `README.md` and
> the gate thresholds already defined in `BENCHMARK_ACCEPTANCE_GATE.md` (both pre-existing in
> this directory) — it does not introduce different numbers, it is the single canonical
> procedure document those two should be read alongside.

## 0. Prerequisites (see `HANDOFF_AUDIT.md` for what's confirmed ready vs still needed)

- Mac with Xcode (iOS 16+ SDK).
- Physical iPhone, Developer Mode enabled, connected via USB or wireless debugging.
- Apple ID for code signing (free personal-team signing is sufficient).
- The two fp32 TFLite files, copied from this repo (paths and SHA256 to verify against, see
  `TEST_ASSET_MANIFEST.csv`'s header note and `HANDOFF_AUDIT.md` §1):
  - `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite`
  - `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite`
- The 40 test images listed in `TEST_ASSET_MANIFEST.csv` (20 real, 10 fake, 10 filter), copied
  from their source paths into the Xcode app bundle. **Verify each file's SHA256 against
  `TEST_ASSET_MANIFEST.csv` after copying**, before trusting the bundle — a corrupted or
  substituted copy would silently invalidate the whole benchmark.
- Before running: recompute the SHA256 of both `.tflite` files **on the Mac, after copying**
  (`shasum -a 256 <file>`) and confirm they still match the values in `HANDOFF_AUDIT.md` §1 /
  `docs/releases/v8.11_production/RELEASE_MANIFEST.json`. If they don't match, **stop and
  re-copy** — do not proceed with a benchmark run against an unverified model file.

## 1. Routing rule decision (must be made before writing any timing code)

Per `IOS_BENCHMARK_SPEC.md` §4 and `HANDOFF_AUDIT.md` §2, `pipeline.py`'s actual shipped
production behavior runs Layer2 **unconditionally on every image** (composite-probability
argmax over `[p_real, p_fake, p_filter]`), not the cheaper "skip Layer2 for confident-real"
strict-gate rule used only in the desktop benchmark script. **Decide and record which rule
the iOS harness implements before running the protocol below** — this changes what "real
path" latency means:

- **If implementing the exact production rule** (recommended, for a faithful benchmark of
  what's actually deployed): every image pays the Layer1+Layer2 cost. There is no cheaper
  "real path" — report a single latency profile and treat gates 2/3 in
  `BENCHMARK_ACCEPTANCE_GATE.md` as needing re-derivation (flag this back rather than
  silently reinterpreting the existing 80ms/150ms thresholds, per that document's own
  instruction).
- **If implementing the strict-gate approximation** (matches the existing gate thresholds
  as written): Layer2 is skipped when Layer1's argmax is "real". Report real-path and
  manipulated-path latency separately, matching `BENCHMARK_ACCEPTANCE_GATE.md`'s gates 2-4
  as currently defined.

Record the choice made in the `routing_rule_implemented` field of the benchmark output (see
`EXPECTED_OUTPUT_SCHEMA.json`).

## 2. Warmup phase

- Run **10 warmup inferences** per path (real path and manipulated path, or the single path
  if the production rule is implemented) before any timing starts.
- Use a real test image for warmup (not a synthetic/blank tensor) so LiteRT delegate
  initialization, memory allocation, and any lazy caches are in their steady state.
- **Discard all warmup timings** — they are not part of any reported metric.

## 3. Timed runs (100 per path)

- Run **100 timed inferences** per path, cycling through the path's test images (20 real
  images for the real path; 20 manipulated images — 10 fake + 10 filter — for the manipulated
  path) so no single image dominates the sample.
- For each run, record: per-image `layer1_ms`, `layer2_ms` (manipulated path only, `null`/
  absent for real-path-only runs under the strict-gate rule), `end_to_end_ms` (preprocessing +
  layer1 + [layer2] + routing decision), and the resulting `predicted_class`.
- From the 100 `end_to_end_ms` values per path, compute: **mean, p50 (median), p95, max**.
- Measure **initialization time** (`init_ms`) **once**, separately from the 100 timed runs —
  this is the one-time cost of loading both `.tflite` models and allocating interpreter
  tensors, not amortized into per-image latency.
- Measure **peak RAM** (`peak_memory_mb`) during the timed-run phase using a real on-device
  measurement API (e.g. `os_proc_available_memory()`, or Instruments' Allocations/Memory
  instrument) — not an estimate or a desktop-measured proxy.

## 4. Prediction consistency check

- For each of the 40 test images, compare the iPhone's final predicted class
  (`real`/`fake`/`filter`) against the desktop fp32 TFLite reference prediction for the same
  image. The desktop reference source is `results/mobile_deployment_benchmark.json`'s
  `tflite_float32` block (this project's own desktop CPU TFLite run, already confirmed 100%
  decision-agreement with the PyTorch reference on the full 769-image True Test set) — for
  images inside `TEST_ASSET_MANIFEST.csv`'s selection, re-derive or trust that existing
  desktop agreement figure per `BENCHMARK_ACCEPTANCE_GATE.md`'s "How to evaluate" section
  (label-level match, not bit-exact logit match — cross-platform floating point is not
  expected to be bit-identical, matching the same bar the ONNX→TFLite conversion itself was
  held to).
- Report `prediction_consistency` as the fraction of the 40 test images (or however many were
  actually used) where iPhone label == desktop label.

## 5. Stability run (500 runs)

- Run **500 consecutive inferences** on the **manipulated path** (exercises both models,
  the stricter test per `README.md`'s own reasoning — Layer2 always runs, so this is the
  heavier and more failure-prone path).
- Requirements:
  - **Zero crashes** across all 500 runs.
  - Compute mean latency of the **first 100 runs** and the **last 100 runs**; the last-100
    mean must not exceed the first-100 mean by more than **30%** (this is the
    `degradationPercent` field already stubbed in `swift_stub/BenchmarkStats.swift`).
- Record any thermal-throttling observations in free text (`thermal_notes`) — device
  temperature state (if observable via API or manual note), any visible slowdown pattern,
  whether the device felt warm/hot to the touch. There is no separate thermal gate; sustained
  throttling shows up as a gate-6 (latency drift) failure on its own.

## 6. Compute and record device metadata

- `device_model` (e.g. `iPhone15,3` — from `UIDevice` / `sysctlbyname("hw.machine", ...)`, not
  the marketing name).
- `ios_version` (from `UIDevice.current.systemVersion`).
- `runtime` and its exact version (e.g. `TensorFlowLiteSwift 2.x.y` — record whatever LiteRT
  distribution/version is actually linked; CoreML was never verified in this project, see
  `IOS_BENCHMARK_SPEC.md` §6 TODO — do not silently substitute CoreML numbers for LiteRT ones
  or vice versa without re-verifying export/conversion correctness first).
- `threads` — the number of threads the LiteRT interpreter was configured with (`Interpreter.Options.threadCount`
  or equivalent). Record whatever value is actually used; this project has no prior on-device
  measurement to derive a "correct" thread count from.

## 7. Evaluate against the acceptance gate

Compare the completed run's numbers against `BENCHMARK_ACCEPTANCE_GATE.md`'s 7-row gate table
(combined size ≤25MB, real p50 ≤80ms, manipulated p50 ≤150ms, manipulated p95 ≤250ms, 0 crashes
in 500 runs, ≤30% last-vs-first-100 latency drift, prediction consistency == desktop labels).
Fill in that document's "Measured value" / "Pass/Fail" columns **only** once real numbers
exist — per that document's own instruction, do not fill in pass/fail without an actual result
to point to. If the routing-rule decision in step 1 was the production composite rule rather
than the strict-gate rule, flag that gates 2-3's thresholds need re-derivation rather than
silently marking them pass/fail against thresholds that assumed the other rule.

## 8. Record results

Save the completed run's numbers in the shape defined by `EXPECTED_OUTPUT_SCHEMA.json`,
including full checkpoint/TFLite provenance (paths + SHA256, re-verified on-device per step 0)
so the result is traceable back to this exact frozen v8.11d + Layer2 v811 release. Do not
overwrite `benchmark_manifest.json` (the pre-existing placeholder/schema file in this
directory) — write the actual completed result to a new, dated file
(e.g. `benchmark_result_<device_model>_<YYYYMMDD>.json`) so the placeholder template and the
real result are never confused with each other.
