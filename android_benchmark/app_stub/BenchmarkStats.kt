package com.aigc.benchmark

/**
 * p50/p95/max/degradation computation skeleton. See DEVICE_BENCHMARK_PROTOCOL.md
 * for what must be computed. Skeleton only -- not functional code.
 */
object BenchmarkStats {

    data class LatencyStats(val mean: Double, val p50: Double, val p95: Double, val max: Double)

    /** TODO: sort, compute mean and percentiles from a list of per-run latencies (ms). */
    fun computeStats(latenciesMs: List<Double>): LatencyStats {
        TODO("sort ascending; mean = avg; p50 = median; p95 = 95th percentile; max = last element")
    }

    data class StabilityResult(
        val crashCount: Int,
        val first100MeanMs: Double,
        val last100MeanMs: Double,
        val degradationPercent: Double  // (last100MeanMs - first100MeanMs) / first100MeanMs * 100
    )

    /** TODO: run 500 inferences on the manipulated path, catch/count crashes,
     * compute first-100 vs last-100 mean latency drift per
     * DEVICE_BENCHMARK_PROTOCOL.md gate 6 (must be <= 30%). */
    fun runStabilityTest(runner: ModelRunner, inputs: List<java.nio.ByteBuffer>): StabilityResult {
        TODO("loop 500x calling runner.runProductionRouting(), catch exceptions, record per-run latency")
    }
}
