// BenchmarkStats.swift
//
// STATUS: skeleton only, prepared on Windows -- never compiled, never run.
// Plain latency-array statistics used by BenchmarkRunner. No LiteRT/CoreML
// dependency here, this file should compile as-is once dropped into an
// Xcode project.

import Foundation

struct BenchmarkStats {
    let mean: Double
    let p50: Double
    let p95: Double
    let max: Double
    let sampleCount: Int

    /// `samplesMs` should be the 100 TIMED runs only -- warmup runs must
    /// already be excluded by the caller (see BenchmarkRunner's warmup
    /// count of 10, per README.md's benchmark protocol).
    init(samplesMs: [Double]) {
        precondition(!samplesMs.isEmpty, "BenchmarkStats requires at least one sample")
        let sorted = samplesMs.sorted()
        self.sampleCount = sorted.count
        self.mean = sorted.reduce(0, +) / Double(sorted.count)
        self.p50 = BenchmarkStats.percentile(sorted, 0.50)
        self.p95 = BenchmarkStats.percentile(sorted, 0.95)
        self.max = sorted.last!
    }

    private static func percentile(_ sorted: [Double], _ p: Double) -> Double {
        // TODO: this is a simple nearest-rank percentile. Fine for n=100,
        // revisit if the stability-run analysis (n=500) needs interpolated
        // percentiles instead.
        let idx = Int((Double(sorted.count) * p).rounded(.up)) - 1
        return sorted[max(0, min(idx, sorted.count - 1))]
    }

    var summaryText: String {
        String(
            format: "mean=%.2fms  p50=%.2fms  p95=%.2fms  max=%.2fms  (n=%d)",
            mean, p50, p95, max, sampleCount
        )
    }
}

/// Result of the 500-run stability test: compares the first 100 vs last 100
/// runs to detect latency drift, per BENCHMARK_ACCEPTANCE_GATE.md's "no more
/// than 30% degradation" gate.
struct StabilityResult {
    let totalRuns: Int
    let crashed: Bool
    let firstHundred: BenchmarkStats
    let lastHundred: BenchmarkStats

    /// Percentage change in mean latency, last 100 vs first 100.
    /// Positive = got slower.
    var degradationPercent: Double {
        ((lastHundred.mean - firstHundred.mean) / firstHundred.mean) * 100
    }
}
