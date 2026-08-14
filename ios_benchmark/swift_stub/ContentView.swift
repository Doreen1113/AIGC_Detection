// ContentView.swift
//
// STATUS: skeleton only, prepared on Windows -- never compiled, never run.
// This is NOT a production UI. Exactly three buttons, per README.md's
// non-goals: no styling beyond what SwiftUI gives for free, no additional
// screens, no settings. Do not add features here without updating
// README.md's "Non-goals" section first.

import SwiftUI

struct ContentView: View {
    @State private var outputText: String = "No benchmark run yet."
    @State private var isRunning: Bool = false

    // TODO: wire up to a real BenchmarkRunner instance once
    // initializeModels() is implemented (see BenchmarkRunner.swift).
    private let runner = BenchmarkRunner()

    var body: some View {
        VStack(spacing: 16) {
            Text("AIGC Detector -- iOS Benchmark Harness")
                .font(.headline)
            Text("Not a production app. Benchmark only.")
                .font(.caption)
                .foregroundColor(.secondary)

            Button("Run real benchmark") {
                runRealBenchmark()
            }
            .disabled(isRunning)

            Button("Run manipulated benchmark") {
                runManipulatedBenchmark()
            }
            .disabled(isRunning)

            Button("Run 500-run stability test") {
                runStabilityTest()
            }
            .disabled(isRunning)

            ScrollView {
                Text(outputText)
                    .font(.system(.body, design: .monospaced))
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
        }
        .padding()
    }

    private func runRealBenchmark() {
        isRunning = true
        outputText = "TODO: not implemented -- BenchmarkRunner.runOnce() is a stub.\n" +
            "Once implemented: load 20 real images from test_assets_manifest.csv, " +
            "preprocess via ImagePreprocessor, call runner.runBenchmarkPath(images:), " +
            "and display stats.summaryText plus init_ms + peak memory here."
        isRunning = false
        // TODO real implementation:
        // Task {
        //     do {
        //         let images = try loadAndPreprocess(pathClass: "real")
        //         let stats = try runner.runBenchmarkPath(images: images)
        //         await MainActor.run {
        //             outputText = "REAL PATH\n" + stats.summaryText +
        //                 "\ninit=\(runner.initMs)ms  peakRAM=\(runner.peakMemoryMb())MB"
        //             isRunning = false
        //         }
        //     } catch {
        //         await MainActor.run {
        //             outputText = "FAILED: \(error)"
        //             isRunning = false
        //         }
        //     }
        // }
    }

    private func runManipulatedBenchmark() {
        isRunning = true
        outputText = "TODO: not implemented -- see runRealBenchmark() for the pattern. " +
            "Manipulated path = 10 fake + 10 filter images from test_assets_manifest.csv, " +
            "exercises both Layer1 AND Layer2 per HierarchicalRouter."
        isRunning = false
    }

    private func runStabilityTest() {
        isRunning = true
        outputText = "TODO: not implemented -- calls runner.runStabilityTest(images:totalRuns:500). " +
            "Must report whether all 500 runs completed without crash, plus " +
            "firstHundred vs lastHundred degradationPercent (see BenchmarkStats.swift), " +
            "checked against BENCHMARK_ACCEPTANCE_GATE.md's 30% threshold."
        isRunning = false
    }
}

#Preview {
    ContentView()
}
