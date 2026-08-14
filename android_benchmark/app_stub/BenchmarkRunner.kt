package com.aigc.benchmark

/**
 * Top-level benchmark control flow: warmup(10) -> timed runs(100, per path) ->
 * stability run(500). See DEVICE_BENCHMARK_PROTOCOL.md for full spec.
 * Skeleton only -- not functional code.
 */
class BenchmarkRunner(private val modelRunner: ModelRunner) {

    /** TODO: run 10 warmup inferences per path on a real test image, discard timings. */
    fun warmup(realPathInputs: List<java.nio.ByteBuffer>, manipulatedPathInputs: List<java.nio.ByteBuffer>) {
        TODO("10x modelRunner.runProductionRouting() per path, ignore results/timings")
    }

    /** TODO: 100 timed runs per path (real, manipulated, end-to-end), record
     * per-run layer1_ms/layer2_ms/end_to_end_ms and predicted class. */
    fun runTimedBenchmark(): Map<String, BenchmarkStats.LatencyStats> {
        TODO(
            "cycle through the 20 real-path images and 20 manipulated-path images " +
            "(10 fake + 10 filter) per TEST_ASSET_MANIFEST.csv, 100 runs each path, " +
            "call BenchmarkStats.computeStats() on the collected latencies"
        )
    }

    /** TODO: compare each of the 40 test images' predicted class against
     * golden_outputs/ (see golden_outputs/README.md), compute consistency_fraction. */
    fun runGoldenParityCheck(): Double {
        TODO("load golden predictions, compare label-for-label against fresh on-device predictions")
    }

    /** TODO: delegate to BenchmarkStats.runStabilityTest(), write results into
     * the EXPECTED_OUTPUT_SCHEMA.json-shaped output. */
    fun runStabilityTest(): BenchmarkStats.StabilityResult {
        TODO("BenchmarkStats.runStabilityTest(modelRunner, manipulatedPathInputs)")
    }
}
