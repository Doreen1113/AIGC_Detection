# Android On-Device Benchmark — Handoff Package

## 狀態：尚未建置、尚未在任何 Android 硬體上執行

本目錄下的所有內容都是在 Windows 上準備的。沒有任何 Android Studio 專案、沒有編譯過
的 APK、沒有在 Emulator 或實體裝置上執行過任何東西。在這裡的任何內容都不能被引用為
Android／實機的效能結果，直到它真的在 Android 硬體上跑過。

> **重要更正（2026-08-14）**：本目錄取代先前基於錯誤裝置平台假設（iOS/iPhone）
> 建立的 `ios_benchmark/`。Member C 實際使用的是 Android 裝置，不是 iPhone。
> `ios_benchmark/` 目錄本身依規則不可刪除，已在其中新增
> `ios_benchmark/DEPRECATED_SEE_ANDROID.md` 說明，僅供歷史留存，不應再被使用。

## Windows 端能做／不能做的事

**能做（本套件已完成）：**
- 讀 `pipeline.py`、`export_mobile_tflite.py`、`benchmark_mobile_artifacts.py`、
  `results/mobile_deployment_benchmark.json`，抽取出精確的前處理／模型／routing
  規格（見 `PRODUCTION_ROUTING_SPEC.md`）。
- 撰寫 benchmark 流程、acceptance gate、manifest 檔案。
- 用 TODO 標記清楚地寫出 Kotlin 檔案骨架（`app_stub/`），標明 LiteRT 整合點。

**不能做（卡在 Windows，需要真實裝置）：**
- 建立／編譯 Android Studio 專案、產生 APK。
- 連結 LiteRT（TensorFlow Lite for Android）並產生可執行的推論程式。
- Provision 裝置、安裝、在實體 Android 裝置上執行任何東西。
- 量測任何真實的 latency、記憶體、熱節流數字——`EXPECTED_OUTPUT_SCHEMA.json` 裡
  每一個數值欄位都只是 schema／佔位，不是量測結果。

## Mac／Windows 之後，在 Android Studio 上要做的步驟

1. **把檔案搬到開發機。**
   - 複製整個 `android_benchmark/` 目錄。
   - 複製兩個已驗證可載入、跟桌機 PyTorch 逐張決策一致的 fp32 TFLite 檔案：
     - `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite`
     - `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite`
   - 依 `TEST_ASSET_MANIFEST.csv` 準備 40 張測試圖片（**不要**把整批資料集塞進
     app，只放這 40 張抽樣圖）。
2. **開啟 Android Studio**，建立新的 Android App 專案（Kotlin，minSdk 依裝置
   實際情況決定），把 `app_stub/` 下的檔案當起點拉進去——這些是骨架，不是可以
   直接執行的程式。
3. **加入 LiteRT**（`org.tensorflow:tensorflow-lite` 透過 Gradle）作為依賴。
   把兩個 `.tflite` 檔案與 40 張測試圖放進 app 的 assets。
4. **把 `// TODO` 區塊補完**——模型載入、tensor I/O、計時邏輯、以及
   `PRODUCTION_ROUTING_SPEC.md` 中定義的 hierarchical routing 邏輯。
5. **Provision**：需要一台已開啟開發者模式／USB 偵錯的實體 Android 裝置，
   透過 USB（或同網段的 wireless debugging）連接。**Emulator 不能給出有效的
   latency 數字**（架構跟真機不同）——只能用來抓 build/crash 問題。
6. **依 `DEVICE_BENCHMARK_PROTOCOL.md` 跑 benchmark**，把結果記錄成
   `EXPECTED_OUTPUT_SCHEMA.json` 的格式。
7. **對照 `DEVICE_BENCHMARK_PROTOCOL.md` 的 Acceptance Gate 檢查結果。**

## 實際要跑這個 benchmark 需要什麼

- 一台裝有 Android Studio 的開發機。
- 一台實體 Android 裝置（實際型號要記錄在 benchmark 輸出的 `device_model` 欄位）。
- USB 連接線（或穩定的 wireless debugging 網路），用於安裝＋log 存取。
- 兩個 fp32 `.tflite` 模型檔案（上面列出）。
- `TEST_ASSET_MANIFEST.csv` 描述的 40 張測試圖片。

## Non-goals（本套件明確不涵蓋的範圍）

- 不做正式產品 UI。`app_stub/` 裡的 Activity/Compose 骨架只需要能觸發三個
  benchmark 動作＋顯示文字結果，沒有其他。
- 不變更 `pipeline.py`、訓練流程、或任何 checkpoint。
- 在真正於 Android 硬體上跑出數字之前，任何地方都不得宣稱「已在 Android 上測試過」。
