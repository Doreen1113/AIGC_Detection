package com.aigc.benchmark

import android.app.Activity
import android.os.Bundle

/**
 * Minimal benchmark-only Activity skeleton. No production UI -- three buttons
 * (warmup+timed run / stability run / golden parity check) and a text output
 * area is the entire scope, per android_benchmark/README.md's Non-goals section.
 * Skeleton only -- not functional code.
 */
class MainActivity : Activity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // TODO: minimal layout with 3 buttons + a text/log output view.
        // TODO: on button press, instantiate ModelRunner + BenchmarkRunner,
        //   run the corresponding benchmark step, write results to a JSON file
        //   matching EXPECTED_OUTPUT_SCHEMA.json under
        //   android_benchmark/results/<device_model>_<date>/ on the device's
        //   external storage, then surface a summary in the text output view.
        // TODO: record device_metadata (Build.MANUFACTURER, Build.MODEL,
        //   Build.VERSION.RELEASE, ActivityManager.getMemoryInfo(), etc.)
        //   at benchmark start, per DEVICE_BENCHMARK_PROTOCOL.md ss1.
    }
}
