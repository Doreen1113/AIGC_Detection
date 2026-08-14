# Android Device Benchmark Protocol

> 建立於 2026-08-14，中文撰寫。取代先前基於錯誤裝置平台假設（iOS/iPhone）建立的
> `ios_benchmark/DEVICE_BENCHMARK_PROTOCOL.md`——Member C 實際使用的是 Android 裝置，
> 見 `ios_benchmark/DEPRECATED_SEE_ANDROID.md`。

## 0. 前置需求

- Android Studio（含 Android SDK／NDK）。
- 一台**實體** Android 裝置，已開啟 USB 偵錯，透過 USB 連接開發機。
- `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite` 與
  `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite` 這兩個檔案
  （**只需要 fp32，fp16/int8 已確認不可用，不得替換**）。
- `TEST_ASSET_MANIFEST.csv` 列出的 40 張測試圖片，以及對應的 golden predictions
  （見 `golden_outputs/README.md`）。
- 執行前：對兩個 `.tflite` 檔案現場重算 SHA256，核對是否與
  `docs/releases/v8.11_production/RELEASE_MANIFEST.json` 記錄的值一致，不一致就
  停下來，不要拿未經確認的模型檔案跑 benchmark。

## 1. 裝置 metadata（每次跑都要記錄）

- 製造商（manufacturer）
- 機型（model）
- SoC（晶片型號）
- Android 版本（`Build.VERSION.RELEASE` / API level）
- 總 RAM
- 開始測試時的電量
- 開始測試時的熱狀態（thermal state，若系統 API 可取得）
- Runtime 版本（LiteRT/TFLite 版本號）
- Thread 數（見下方 benchmark 設定）
- Delegate（CPU／NNAPI／GPU，見下方）

## 2. Benchmark 設定

- **Warmup**：10 次，捨棄計時。
- **正式計時**：100 次。
- **穩定性測試**：500 次連續推論。
- **Thread 設定**：CPU 1 thread（baseline）、CPU 2 threads（對照）；CPU 4
  threads（選配）；NNAPI（選配）；GPU delegate（選配）。**CPU baseline（fp32,
  1 thread 或裝置慣用的預設 thread 數，需明確記錄用的是哪一個）是唯一的正式
  acceptance gate 依據，NNAPI／GPU delegate 的數字只能當對照，不能取代它。**

## 3. 三條路徑（依 `PRODUCTION_ROUTING_SPEC.md`）

- **Real path**：前處理 + Layer1（依 production 規則，Layer2 實際上也會執行，
  但這裡量測的是「最終判定為 real 的圖片」整體耗時，用來跟 manipulated path 對照）。
- **Manipulated path**：前處理 + Layer1 + Layer2（最終判定為 fake 或 filter 的
  圖片）。
- **End-to-end path**：影像解碼 + 前處理 + routing 判斷 + 模型推論，量測使用者
  實際感受到的總延遲，不是只量模型 forward 的時間。

## 4. 必須回報的欄位

- 模型檔案 SHA256（兩個 `.tflite`）
- 測試圖片 SHA256（對照 `TEST_ASSET_MANIFEST.csv`）
- 初始化時間（`init_ms`，載入兩個模型＋配置 interpreter 的一次性成本，跟每張圖的
  推論時間分開量測）
- mean、p50、p95、max（毫秒）
- 峰值 RAM
- 與 golden predictions 的預測一致率（`prediction_consistency`）
- 500-run 穩定性測試的 crash 次數
- 500-run 的前 100 次 vs 後 100 次平均延遲漂移（degradation percent）
- 熱狀態備註（`thermal_notes`，自由文字：是否觀察到降頻、裝置是否發燙等）

## 5. Acceptance Gate

| # | Gate | 門檻 |
|---|---|---:|
| 1 | 模型合計大小 | ≤ 25 MB |
| 2 | Real path 端對端 p50 | ≤ 100 ms |
| 3 | Manipulated path 端對端 p50 | ≤ 150 ms |
| 4 | Manipulated path 端對端 p95 | ≤ 250 ms |
| 5 | 500-run 穩定性：零 crash | 0 crash / 500 runs |
| 6 | 500-run 穩定性：延遲漂移 | 後 100 次平均延遲 ≤ 前 100 次平均延遲 + 30% |
| 7 | Golden prediction 一致率 | 100%（label 層級一致，不要求 bit-exact logits） |

**狀態**：以上七項全部尚未量測——本文件只定義 gate，不能在還沒有真實裝置數字前
自行填入 pass/fail。填表方式比照 `ios_benchmark/BENCHMARK_ACCEPTANCE_GATE.md`
先前的做法：先留空，等真實量測結果出來才填。

## 6. 明確禁止事項

- **Android Emulator 的數字不得當成正式結果**——Emulator 跑在開發機自己的
  CPU 架構上，不是目標裝置，只能用來抓 build/crash 問題。
- **不得**自行替換模型（例如換成 int8／fp16、換 threshold、換 routing 規則）——
  這些都需要走 `PRODUCTION_CHANGE_CONTROL.md`。
- **不得**用 NNAPI 或 GPU delegate 的數字取代 CPU baseline 作為 gate 判定依據。
