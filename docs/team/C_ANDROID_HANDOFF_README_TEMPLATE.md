# Member C Android 交接包 README 範本

> 隨 Member C 的 Android 交接包一起提供的 README 範本。實際打包時複製本文件、填入
> 當次的日期與實際內容，放進交接包根目錄。**取代先前基於錯誤裝置平台假設（iOS）
> 建立的版本**——Member C 使用的是 Android 裝置。

## Member C 不需要完整資料集

Member C **只需要**：

- `layer1_v811d_float32.tflite`、`layer2_v811_float32.tflite`（僅 fp32，
  不含 fp16／int8——兩者皆已確認不可用）
- `TEST_ASSET_MANIFEST.csv` 中鎖定的 40 張固定 benchmark 圖片
- 這 40 張圖片對應的 golden predictions（見 `golden_outputs/README.md`；
  截至目前尚未生成，需先補上）
- `PRODUCTION_ROUTING_SPEC.md`（routing 規格）
- `DEVICE_BENCHMARK_PROTOCOL.md`（Android benchmark 流程）
- `app_stub/`（Kotlin 骨架）

**不需要**任何原始訓練資料集、任何 PyTorch checkpoint、任何 split 檔案。

## Baseline checkpoint 身分

- **Layer1**：`shufflenet_v2_layer1_v811d.pth`
  SHA256：`3C61CF6886D2F9D4871B52749A15FD4E1B979D121C664BA85D9B069194C290B7`
- **Layer2**：`shufflenet_v2_layer2_v811.pth`
  SHA256：`8470AD52DADCDB44A6789067EFBBD7FBC20715CB3F4E3339630191889A55057E`
- **對應的 fp32 TFLite**：
  - `layer1_v811d_float32.tflite`，SHA256
    `c16cf71f250bea1cc83fe171dc7120edbd2335c06eef3f20998e20d2f4194389`
  - `layer2_v811_float32.tflite`，SHA256
    `3deed69d6ca4ebb9f7597391ce04390c49758e283a59bbbc988f615dd14eb0cd`
- 來源：`docs/releases/v8.11_production/RELEASE_MANIFEST.json`

## 允許的使用方式

- 在 Android Studio 中建置 benchmark app，載入上述兩個 fp32 TFLite 模型跑推論。
- 依 `PRODUCTION_ROUTING_SPEC.md` 實作 hierarchical routing 邏輯。
- 依 `DEVICE_BENCHMARK_PROTOCOL.md` 在實體裝置上跑 latency／RAM／穩定性測試。
- 額外測 NNAPI／GPU delegate 作為**清楚標示的對照組**。

## 禁止的使用方式

- **不得**使用 Android Emulator 的數字作為正式結果——只能用來抓 build/crash 問題。
- **不得**自行替換模型（int8／fp16）、threshold、或 routing 規則——這些都不是
  Member C 的職責範圍，任何懷疑都要回報，不要自行決定換掉。
- **不得**把 NNAPI／GPU delegate 的數字取代 CPU fp32 baseline 作為 acceptance gate
  判定依據。
- **不得**把本套件內容宣告為新的 production 版本——所有 production 變更都要走
  `PRODUCTION_CHANGE_CONTROL.md`。

## 收到後應執行的驗證指令

對兩個 `.tflite` 檔案，在開發機與（若可行）裝置端各自核對 SHA256：

```powershell
Get-FileHash -Path "layer1_v811d_float32.tflite" -Algorithm SHA256
Get-FileHash -Path "layer2_v811_float32.tflite" -Algorithm SHA256
```

或在 Android 端（例如透過一個除錯用的 Activity 或 adb shell）確認 bundle 進 app
的模型檔案雜湊值跟上方記錄的一致。任何不一致都要停下來回報，不要假設「應該沒差」。

## 輸出路徑規則

所有 benchmark 結果一律輸出到 **`android_benchmark/results/<device_model>_<date>/`**，
使用 `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` 定義的格式，**絕對不要覆寫**
任何既有結果——每次跑（不同裝置或不同日期）都是新的資料夾。

## 升級／交還給 Member A 的規則

- 任何觸及 `PRODUCTION_CHANGE_CONTROL.md` 涵蓋清單的發現或提案，一律先走該流程的
  提案格式，不要直接動手改。
- 若發現 golden predictions 缺失、checkpoint SHA256 不符、或任何本 README「禁止
  使用」清單中的情況，立即回報。

## 回報結果時要用的格式

每次裝置實測都要包含：完整的裝置 metadata（廠牌、機型、SoC、Android 版本、RAM、
電量、熱狀態、runtime 版本、thread 數、delegate）＋模型／圖片 SHA256＋
`android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` 定義的完整指標集。並依
`EXPERIMENT_HANDOFF_TEMPLATE.md` 格式附上 claim／non-claim／limitations。
