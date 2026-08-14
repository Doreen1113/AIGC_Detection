# Benchmark Acceptance Gate — v8.11 iPhone On-Device

Status: **not yet evaluated against any real measurement.** This is the gate
definition only, to be checked once the Mac/Xcode benchmark run in
`README.md`'s protocol has produced numbers in `benchmark_manifest.json`'s
output schema.

| # | Gate | Threshold | Source measured against |
|---|------|-----------|--------------------------|
| 1 | Combined model size | ≤ 25 MB | `layer1_v811d_float32.tflite` + `layer2_v811_float32.tflite` on disk. Desktop reference: 20.91 MB combined (`results/mobile_deployment_benchmark.json`), so this gate should pass by construction unless the iOS bundle format inflates size — confirm actual on-disk size once copied into the app bundle. |
| 2 | Real path end-to-end p50 | ≤ 80 ms | 100 timed runs, real-class images, Layer1-only cost (see `IOS_BENCHMARK_SPEC.md` §4 routing-rule TODO — this threshold assumes the strict-gate rule where Layer2 is skipped for confident-real images; if the production composite-probability rule is used instead, Layer2 always runs and this threshold needs to be re-derived, not assumed to still apply as-is) |
| 3 | Manipulated path end-to-end p50 | ≤ 150 ms | 100 timed runs, fake+filter images, Layer1+Layer2 cost |
| 4 | Manipulated path end-to-end p95 | ≤ 250 ms | same 100 timed runs as gate 3 |
| 5 | 500-run stability: no crash | 0 crashes / 500 runs | `runStabilityTest()` completing all 500 runs |
| 6 | 500-run stability: latency drift | last 100 runs' mean latency ≤ first 100 runs' mean latency **+ 30%** | `StabilityResult.degradationPercent` (`swift_stub/BenchmarkStats.swift`) |
| 7 | Prediction consistency vs desktop | iPhone prediction == desktop fp32 TFLite prediction, on the same test images | Compare per-image `real`/`fake`/`filter` output against the desktop `tflite_float32` predictions (desktop reference agreement vs. PyTorch was 100%, `results/mobile_deployment_benchmark.json`) |

## How to evaluate

For each of the 40 test images in `test_assets_manifest.csv`, run the same
image through the desktop fp32 TFLite pipeline (`benchmark_mobile_artifacts.py`
already does this — its `pred` output per image is the reference) and the
iPhone app, and confirm the final `real`/`fake`/`filter` label matches. This
is a **label-level** consistency check, not a numeric-tolerance check on raw
logits — cross-platform floating-point ops (ARM NEON on iPhone vs. x86 on
the Windows desktop CPU used for `results/mobile_deployment_benchmark.json`)
are not expected to produce bit-identical logits, only bit-identical
**decisions** at this precision, matching the same bar
`export_mobile_tflite.py`'s G4 gate already applies (`max|dprob| < 1e-3`
and `argmax_identical`) for the ONNX→TFLite conversion itself.

## Gate status

All seven rows above are **unevaluated** — every cell in the "measured"
column is empty because no benchmark has run on Apple hardware yet. Do not
fill in pass/fail here without an actual `benchmark_manifest.json`-shaped
result to point to.

| # | Measured value | Pass/Fail |
|---|-----------------|-----------|
| 1 | — | — |
| 2 | — | — |
| 3 | — | — |
| 4 | — | — |
| 5 | — | — |
| 6 | — | — |
| 7 | — | — |

## Notes / open questions for whoever runs this on the Mac

- Gate 2's threshold assumes the strict-gate routing rule (Layer2 skipped
  for real images). If the harness instead implements the exact production
  rule (`HierarchicalRouter.routeProductionRule`, Layer2 always runs), gate
  2 and gate 3 collapse into the same latency profile and this table's
  real/manipulated split stops being meaningful as written — flag this back
  before reporting results, don't silently reinterpret the gate.
- No thermal-throttling gate is defined here beyond the free-text
  `thermal_notes` field in `benchmark_manifest.json` — if the 500-run
  stability test shows throttling-driven slowdown beyond gate 6's 30%, that
  is itself a fail on gate 6, no separate thermal gate is needed.
- These thresholds (80ms / 150ms / 250ms / 30% / 25MB) were not derived from
  any existing iPhone measurement — they don't exist yet in this project.
  Treat them as a first cut; revisit once real hardware numbers are in and
  it's clear whether they're meaningfully tight or loose for the actual
  target device(s).
