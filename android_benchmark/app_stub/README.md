# Android App Stub

> 這裡的 Kotlin 檔案是骨架（skeleton），**不是**可以直接編譯執行的完整 app——每個檔案
> 都用 `// TODO` 標出還沒實作、需要在 Android Studio 中補完的地方。刻意保持精簡，
> 只服務 benchmark 這一個目的，不是正式產品 UI。

## 檔案清單

- `MainActivity.kt` — 最小的 Activity 骨架，觸發 benchmark 流程、顯示文字結果。
  沒有任何正式產品 UI 元素。
- `ModelRunner.kt` — LiteRT interpreter 載入與推論骨架，對應
  `PRODUCTION_ROUTING_SPEC.md` 的 Layer1→Layer2 hierarchical routing 邏輯。
- `ImagePreprocessor.kt` — 對應 `PRODUCTION_ROUTING_SPEC.md` §2 的前處理骨架
  （JPEG 標準化、resize、正規化、NHWC 轉換）。
- `BenchmarkRunner.kt` — warmup／timed-run／stability-run 的控制流程骨架，對應
  `DEVICE_BENCHMARK_PROTOCOL.md`。
- `BenchmarkStats.kt` — p50/p95/max/degradation 計算骨架。

## 使用方式

把這些檔案拉進一個新的 Android Studio 專案（Kotlin，建議用 Jetpack Compose 或
最簡單的 View-based Activity 皆可），加上 LiteRT 依賴，依每個檔案的 `// TODO`
補完實作。
