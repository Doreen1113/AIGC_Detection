// BenchmarkRunner.swift
//
// STATUS: skeleton only, prepared on Windows -- never compiled, never run,
// never linked against LiteRT. Every TODO below is a real gap, not a
// formality -- this file does not run inference yet.
//
// Implements the protocol from ../README.md:
//   - warmup = 10, timed runs = 100, per path (real / manipulated)
//   - report mean/p50/p95/max, init time, peak RAM
//   - separate 500-run stability test
// Acceptance thresholds live in ../BENCHMARK_ACCEPTANCE_GATE.md, this file
// only measures, it does not judge pass/fail.

import Foundation
import UIKit
// TODO: import TensorFlowLite (SPM package "TensorFlowLiteSwift") once
// added to the Xcode project. See IOS_BENCHMARK_SPEC.md for the open
// CoreML-vs-LiteRT question -- this stub assumes LiteRT since that's the
// format already exported (.tflite) and verified on desktop.

final class BenchmarkRunner {

    // TODO: replace with real TFLite Interpreter instances once
    // TensorFlowLiteSwift is linked. Interpreter(modelPath:) throws, and
    // allocateTensors() must be called before first inference -- both
    // should be timed as part of `initMs` below.
    private var layer1Interpreter: Any? // TODO: TFLTensorFlowLite.Interpreter
    private var layer2Interpreter: Any? // TODO: TFLTensorFlowLite.Interpreter

    private(set) var initMs: Double = 0

    /// Loads both .tflite models and allocates tensors. Must be called once
    /// before any benchmark run. Times its own execution into `initMs`.
    func initializeModels(layer1Path: URL, layer2Path: URL) throws {
        let start = CFAbsoluteTimeGetCurrent()

        // TODO:
        // layer1Interpreter = try Interpreter(modelPath: layer1Path.path)
        // try layer1Interpreter.allocateTensors()
        // layer2Interpreter = try Interpreter(modelPath: layer2Path.path)
        // try layer2Interpreter.allocateTensors()
        fatalError("TODO: implement model loading on the Mac once TensorFlowLiteSwift is linked")

        // initMs = (CFAbsoluteTimeGetCurrent() - start) * 1000
    }

    /// Runs Layer1 (and Layer2 for manipulated-path images, per the routing
    /// rule chosen in HierarchicalRouter) once on a preprocessed tensor.
    /// Returns per-layer and end-to-end latency in ms, plus the routing
    /// result. Does NOT include preprocessing time -- caller decides
    /// whether "end_to_end_ms" in the output schema includes preprocessing;
    /// TODO: confirm against benchmark_manifest.json's expected_output_schema
    /// intent before finalizing (currently ambiguous -- resolve on Mac).
    func runOnce(inputTensorNHWC: [Float]) throws -> (routing: RoutingResult, layer1Ms: Double, layer2Ms: Double, endToEndMs: Double) {
        // TODO:
        // let t0 = CFAbsoluteTimeGetCurrent()
        // try layer1Interpreter.copy(Data(...), toInputAt: 0)
        // try layer1Interpreter.invoke()
        // let l1Logits = try layer1Interpreter.output(at: 0) ...
        // let l1Ms = (CFAbsoluteTimeGetCurrent() - t0) * 1000
        //
        // then route per HierarchicalRouter, invoking layer2Interpreter only
        // if the chosen rule requires it, and time that separately.
        fatalError("TODO: implement inference on the Mac once TensorFlowLiteSwift is linked")
    }

    /// Full protocol for one path (real or manipulated): warmup=10 (discarded),
    /// then 100 timed runs, returning BenchmarkStats. `images` should already
    /// be preprocessed tensors for the relevant test_assets_manifest.csv
    /// subset (real images for the real path, fake+filter for the
    /// manipulated path).
    func runBenchmarkPath(images: [[Float]], warmupCount: Int = 10, timedCount: Int = 100) throws -> BenchmarkStats {
        precondition(!images.isEmpty, "runBenchmarkPath requires at least one preprocessed image")

        for i in 0..<warmupCount {
            _ = try runOnce(inputTensorNHWC: images[i % images.count])
        }

        var samples: [Double] = []
        samples.reserveCapacity(timedCount)
        for i in 0..<timedCount {
            let result = try runOnce(inputTensorNHWC: images[i % images.count])
            samples.append(result.endToEndMs)
        }
        return BenchmarkStats(samplesMs: samples)
    }

    /// 500-run stability test. Per README.md, does not crash across all 500
    /// runs is itself part of the pass criteria (BENCHMARK_ACCEPTANCE_GATE.md)
    /// -- this function should be run with the app's normal crash reporting/
    /// exception handling in place, not wrapped in a try/catch that would
    /// mask a crash as a graceful failure.
    func runStabilityTest(images: [[Float]], totalRuns: Int = 500) throws -> StabilityResult {
        precondition(totalRuns >= 200, "need at least 200 runs to split into first/last 100")
        var samples: [Double] = []
        samples.reserveCapacity(totalRuns)
        for i in 0..<totalRuns {
            let result = try runOnce(inputTensorNHWC: images[i % images.count])
            samples.append(result.endToEndMs)
        }
        let first100 = BenchmarkStats(samplesMs: Array(samples.prefix(100)))
        let last100 = BenchmarkStats(samplesMs: Array(samples.suffix(100)))
        return StabilityResult(totalRuns: totalRuns, crashed: false, firstHundred: first100, lastHundred: last100)
    }

    // TODO: peak memory measurement -- e.g. via os_proc_available_memory()
    // sampled on a timer during runBenchmarkPath / runStabilityTest, or
    // Instruments Allocations for a one-off manual measurement. Not
    // implemented in this stub.
    func peakMemoryMb() -> Double {
        fatalError("TODO: implement peak memory measurement on the Mac (os_proc_available_memory or Instruments)")
    }
}
