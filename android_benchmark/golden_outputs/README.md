# Golden Outputs

> 這個資料夾應該放桌機 fp32 TFLite pipeline 對 `TEST_ASSET_MANIFEST.csv` 那 40 張
> 測試圖片跑出來的參考預測結果，供 Android 端做 golden-output parity 比對用。

## 現況：**尚未生成**

截至本次規劃為止，repo 中找不到任何一份針對這 40 張圖片的 golden-prediction 檔案
（已搜尋過整個 repo，沒有任何 `*golden*` 命名的既有檔案）。這是交接前的必要前置
步驟，不是本次規劃遺漏——見 `manifests/team_data/C_android_benchmark_handoff_manifest_template.csv`
與對應的 dry-run report，該項目已明確標記為 `MISSING`。

## 生成方式（尚未執行，由 Member A 或 Member C 在交接前完成）

對 `TEST_ASSET_MANIFEST.csv` 列出的 40 張圖片，用桌機 fp32 TFLite pipeline
（`benchmark_mobile_artifacts.py` 的邏輯，或直接呼叫 `pipeline.py` 的
`hierarchical_predict()`）逐張跑一次，記錄：

- 圖片路徑／SHA256
- 最終 prediction（real/fake/filter）
- 各層機率（`p_real`／`p_fake`／`p_filter`）
- 使用的 checkpoint SHA256

輸出格式建議跟 `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` 的
`prediction_consistency` 區塊對齊，方便 Android 端直接比對。

## 使用方式

Android benchmark 執行時，每張測試圖片跑完推論後，把最終 prediction 拿來跟這裡的
golden output 比對——比對的是**標籤層級**（real/fake/filter 是否相同），不要求
bit-exact 的機率數值（依 `DEVICE_BENCHMARK_PROTOCOL.md` gate 7 的定義）。
