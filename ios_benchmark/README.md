# iPhone On-Device Benchmark — Handoff Package

## Status: NOT built, NOT run on any Apple hardware

Everything in this directory was prepared **on Windows**. No `.xcodeproj`,
no compiled binary, no Xcode build, and no execution on a simulator or a
physical iPhone has happened. Nothing here should be quoted as an
iOS/on-device result until it has actually been run on Apple hardware.

Windows cannot produce that result — there is no Xcode, no iOS SDK, no
CoreML/LiteRT toolchain, and no way to deploy to an iPhone from this
platform. This package exists so that step is the *only* thing left to do
once a Mac is available.

## What Windows could / could not do here

**Could do (done in this package):**
- Read `pipeline.py`, `export_mobile_tflite.py`, `mobile_fft.py`,
  `benchmark_mobile_artifacts.py`, and `results/mobile_deployment_benchmark.json`
  and extract the exact preprocessing / model / routing spec (see
  `IOS_BENCHMARK_SPEC.md`).
- Write the benchmark protocol, acceptance gates, and manifest files.
- Stub out the Swift file skeletons the Xcode project will need, with the
  LiteRT/CoreML integration points explicitly marked `// TODO`.

**Could NOT do (blocked on Windows, requires the Mac):**
- Open/create an Xcode project or `.xcodeproj`/`.xcworkspace`.
- Compile Swift, link LiteRT (`TensorFlowLiteSwift` / `TensorFlowLiteC`) or
  CoreML, or produce an `.ipa`.
- Provision a device, sign the app, or install/run anything on a physical
  iPhone.
- Measure any real latency, memory, or thermal number. Every numeric field
  in `benchmark_manifest.json` is a placeholder / schema only.

## Steps to run on the Mac (future work)

1. **Get the files onto the Mac.**
   - Copy this whole `ios_benchmark/` directory.
   - Copy the two fp32 TFLite artifacts (already verified to load and match
     PyTorch bit-for-bit on real images, see `IOS_BENCHMARK_SPEC.md` §Model):
     - `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite`
     - `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite`
   - Copy a small test image set (see `test_assets_manifest.csv` — 20 real +
     10 fake + 10 filter faces; **do not** commit large dataset dumps into
     the app bundle, just the sampled 40 images).
2. **Open Xcode**, create a new iOS App project (SwiftUI, iOS 16+
   recommended), and drag in the files from `swift_stub/` as a starting
   point — they are skeletons, not working code.
3. **Add LiteRT** (`TensorFlowLiteSwift` via Swift Package Manager or
   CocoaPods) as a dependency. Add the two `.tflite` files and the 40 test
   images to the app bundle.
4. **Fill in the `// TODO` blocks** in `swift_stub/*.swift` — model loading,
   tensor I/O, timing instrumentation, and the hierarchical routing logic
   (spec in `IOS_BENCHMARK_SPEC.md`).
5. **Provision**: an Apple ID (free personal-team signing is enough for a
   benchmark-only app, no App Store submission needed) and a Developer
   Mode-enabled iPhone connected via USB (or same-network wireless
   debugging) are required to run on-device rather than in the simulator.
   The simulator does **not** give a valid latency number (different CPU
   architecture) — it can only be used to shake out crashes/build errors.
6. **Run the benchmark protocol** (below) on the physical device and record
   results into a copy of `benchmark_manifest.json`'s output schema.
7. **Check results against `BENCHMARK_ACCEPTANCE_GATE.md`.**

## What's needed to actually run this

- A Mac with Xcode installed (version supporting iOS 16+ SDK).
- A physical iPhone (the actual target device model should be recorded in
  the benchmark output — `device_model` field).
- A USB cable (or reliable wireless-debugging network) to connect the
  iPhone to the Mac for install + Console log access.
- An Apple ID signed into Xcode for code signing (free personal-team is
  sufficient).
- The two fp32 `.tflite` model files listed above.
- The 40-image test set described in `test_assets_manifest.csv`.

## Benchmark protocol

Run **real path** (Layer1-only, image predicted `real`) and **manipulated
path** (Layer1 + Layer2, image predicted `fake` or `filter`) as separate,
clearly-labeled benchmark runs — do not average them together, since only
the manipulated path pays the Layer2 cost.

For each path:
- **Warmup runs**: 10, discarded (let CoreML/LiteRT delegate init, caches,
  and thermal state settle before timing).
- **Timed runs**: 100, per path, on-device.
- Report **mean, p50, p95, max** latency (milliseconds) over the 100 timed
  runs, plus:
  - **Initialization time**: one-time cost to load both `.tflite` models
    and allocate tensors, measured separately from per-image inference.
  - **Peak RAM**: peak resident memory during the run (e.g. via
    `os_proc_available_memory` / Instruments Allocations, not a guess).

Additionally run a **500-run stability test** (mixed real + manipulated
images, or manipulated-path-only — decide based on which is the stricter
test; manipulated path exercises both models so prefer that) and confirm:
- No crash across all 500 runs.
- Report whether the last 100 runs show latency drift vs the first 100 (see
  `BENCHMARK_ACCEPTANCE_GATE.md` for the 30% threshold).

## Non-goals (explicitly out of scope for this package)

- No production UI. `ContentView` in `swift_stub/` has exactly three
  buttons and a text output area — nothing else.
- No changes to `pipeline.py`, the training pipeline, or any checkpoint.
- No claim of "tested on iPhone" anywhere until an actual Mac/Xcode run has
  produced numbers.
