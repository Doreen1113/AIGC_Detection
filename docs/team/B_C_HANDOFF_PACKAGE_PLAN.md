# Member B / Member C 最小交接包計畫

> 建立於 2026-08-14，中文撰寫。Member A（使用者本人）持有完整的資料／checkpoint／
> 凍結 release／訓練環境，不需要為自己打包。本文件規劃（不執行）給 Member B 與
> Member C 的最小、可驗證、production-safe 交接包。**本輪未搬移、複製、上傳任何一個
> 既有檔案**——`scripts/build_member_handoff_dry_run.py` 只讀取 manifest、核對現況、
> 計算 hash，從不複製資料。

## Member B 交接包的目的

讓 Member B 能在不取得完整訓練環境的情況下，獨立展開 Phase 2 的工作
（`TEAM_WORK_ALLOCATION.md` §D）：驗證 `artifact_classifier_v3` 對外部
`FFHQ_ali_process` 資料的行為（依 `VERIFIED_SINGLE_TYPE`／`COARSE_OR_MIXED` 範圍
區分）、延續 fake per-image evidence 研究、設計 `unknown_or_mixed_retouch` 政策提案。

### 必要檔案清單

見 `manifests/team_data/B_phase2_xai_handoff_manifest_template.csv`（21 列，真實候選
項目，非佔位文字）。摘要：

- **Production checkpoint（唯讀參考）**：`shufflenet_v2_layer1_v811d.pth`、
  `shufflenet_v2_layer2_v811.pth`、`artifact_classifier_v3.pth`、`face_landmarker.task`
- **Filter paired-GT XAI 樣本**：`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`、
  `results/xai_filter_localization_results_v1_20260812.csv`、
  `results/gt_vs_gradcam/*.png`（4 張）
- **Fake XAI 樣本**：`results/xai_faithfulness_blur_v1_20260813.json`、
  `results/phase2_composite_explanation_v1_20260813.jsonl` 及其 summary、
  `results/phase2_composite_filtertype_accuracy_v1_20260813.json`
- **外部 filter 驗證子集**：`FFHQ_ali_process/Whitening_60/`、`Whitening_90/`
  （`VERIFIED_SINGLE_TYPE`，各約 3,000 張）；其餘資料夾僅需代表性樣本，用於
  `COARSE_OR_MIXED` 的 prediction-distribution 稽核，不需要整批搬過去
- **GT／pair manifest**：本次 provenance audit 的三份核心文件
  （`FILTER_DATA_PROVENANCE.csv`、`FILTER_XAI_CLAIM_MATRIX.md`、
  `ARTIFACT_TAXONOMY_ALIGNMENT.md`）

### 明確排除的檔案

- 完整的 `filter_data/{eye_enlarging,whitening,smoothing,face_reshaping}/` 訓練資料夾
  （Member B 的任務不需要重新訓練，只需要少量已產出的 XAI 樣本／manifest）
- `AIGuard/real/`、`AIGuard/fake/` 等完整原始資料集
- 任何 v8.12–v8.16 研究 checkpoint（跟 Member B 的任務無關，且依
  `TEAM_WORK_ALLOCATION.md` §F 不可被當成 production）
- `splits/v815_replication_set.tsv` 及 `v815_replication_set/`（DF40-cdf replication
  set 屬於 Member A 的 Phase 1 工作範圍，依規則不可用於 Phase 2 的外部驗證）
- `FFHQ_ali_process/` 除 `Whitening_60`/`90` 以外的其餘資料夾**整批**（只給代表性樣本）

## Member C 交接包的目的（**2026-08-14 平台更正：Android，非 iOS**）

> Member C 實際使用的是 **Android** 裝置，不是 iPhone。本節先前以「Mac 上建置
> iOS on-device benchmark」為前提，已確認錯誤並改寫——見
> `ios_benchmark/DEPRECATED_SEE_ANDROID.md`。以下內容為更正後版本。

讓 Member C 能獨立在 Android Studio 上建置並執行 Android on-device benchmark
（`TEAM_WORK_ALLOCATION.md` §E），不需要接觸訓練環境或原始資料集。

### 必要檔案清單

見 `manifests/team_data/C_android_benchmark_handoff_manifest_template.csv`
（新檔案，取代舊的 `C_ios_benchmark_handoff_manifest_template.csv`——舊檔**保留
不動**，僅標記為已被取代，見下方「舊 iOS manifest 的處理方式」）。摘要：

- **fp32 TFLite（僅此，不含 fp16／int8，兩者已確認不可用；int8 根因是 FFT 分支
  activation 動態範圍問題，`CLAUDE.md` 已記錄）**：
  `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite`、
  `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite`
- **40 張 benchmark 圖片**（依 `android_benchmark/TEST_ASSET_MANIFEST.csv` 鎖定的
  清單——與先前 `ios_benchmark/TEST_ASSET_MANIFEST.csv` 完全相同的 40 張圖，只是
  重新對應到 Android 交接套件，不是換一批新圖；本計畫本身不搬移這些圖片）
- **Golden predictions**：**目前不存在**，dry-run report 已明確標記為 MISSING——
  需要先用桌機 fp32 TFLite pipeline 對這 40 張圖跑一次才能產生，這是交接前的
  必要前置步驟，不是交接包本身缺漏
- **Routing spec／protocol／Kotlin app stub**：
  `android_benchmark/PRODUCTION_ROUTING_SPEC.md`、
  `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md`、
  `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json`、
  `android_benchmark/app_stub/*.kt`（5 個檔案）、`android_benchmark/README.md`
- **桌機參考數字**：`results/mobile_deployment_benchmark.json`

### 舊 iOS manifest 的處理方式

`manifests/team_data/C_ios_benchmark_handoff_manifest_template.csv` 是在錯誤的
裝置平台假設下建立的，**依規則保留不動、不覆寫、不刪除**。它現在的狀態是
**已被取代（superseded）**，不應再被使用於任何實際交接——請一律改用新的
`C_android_benchmark_handoff_manifest_template.csv`。

### 明確排除的檔案

- 任何 PyTorch checkpoint（`.pth`）——Member C 只需要已匯出的 TFLite，不需要能重新匯出
- fp16／int8 TFLite 變體（已確認損壞／數值錯誤，不該進交接包，避免誤用）
- 除 40 張 benchmark 圖以外的任何資料集
- `splits/`、`AIGuard/`、`FFHQ_*` 等任何訓練資料

## 每個檔案的 source／purpose／SHA256 要求

見兩份 manifest CSV 的 `source`、`purpose`、`sha256` 欄——本計畫階段 `sha256` 欄一律
填 `TBD`，由 `scripts/build_member_handoff_dry_run.py` 在實際打包前現場計算並核對
（已完成一次 dry-run，見下方「Dry-run 結果」）。任何要交接的 checkpoint／TFLite，
其 SHA256 都必須與 `docs/releases/v8.11_production/RELEASE_MANIFEST.json` 記錄的值
完全一致才能出貨；不一致要視為阻斷交接的錯誤，不是警告。

## 需要授權／轉散布確認的項目

依 `DATA_SHARING_STRATEGY.md` 的硬性規則，以下項目在正式交接前需要授權審查：

- **`face_landmarker.task`**（MediaPipe 第三方預訓練模型）——兩份 manifest 都用到，
  尚未做過轉散布條款確認。
- **`FFHQ_ali_process/Whitening_60`、`Whitening_90`**（RetouchingFFHQ／Alibaba
  第三方資料）——Member B 套件中體積最大的部分，也是最需要授權確認的部分。
- **`android_benchmark/TEST_ASSET_MANIFEST.csv` 所引用的 40 張圖片**中，來自 `lfw/`
  （LFW 條款）與 `sd2.1/`（DF40 條款）的圖片——`test_set_true/filter/` 的部分是
  本專案自建，不受此限制。

在完成上述審查前，這些項目在 dry-run report 中一律標記為
`BLOCKED pending license/redistribution audit`，即使檔案已存在、hash 已核對成功，
也不代表可以出貨。

## 建議交付方式

依 `DATA_SHARING_STRATEGY.md` 的五層架構：

- **Manifest／文件（本計畫產出的 CSV／MD）**：走 GitHub（tier 1），本來就該進版控。
- **Member B 的 checkpoint＋XAI 樣本＋部分 FFHQ_ali_process 子集**（約 1.8GB，
  見下方 dry-run 結果）：不適合 GitHub／Git LFS，建議走 **N-drive 或 private Google
  Drive**（tier 4），第三方資料部分待授權審查通過後才可以搬。
- **Member C 的 fp32 TFLite＋40 張圖＋文件**（約 21MB 加上待補的 40 張圖與 golden
  predictions）：體積小，若授權確認完成，這是最適合先試行 **Hugging Face private
  Dataset repo**（tier 3）的候選項目；在授權確認前，一樣走 N-drive／private Drive。

## 收到套件後 B／C 各自要做的驗證步驟

1. 對照 manifest CSV 的 `relative_path` 清單，確認收到的每個檔案都存在。
2. 對每個 `asset_type` 為 checkpoint／tflite_model 的檔案，現場算一次 SHA256，
   核對是否與 manifest（以及 `docs/releases/v8.11_production/RELEASE_MANIFEST.json`）
   記錄的值完全一致——不一致就停下來回報，不要繼續往下用。
3. 確認 `required=yes` 的項目沒有缺漏（可直接重跑
   `scripts/build_member_handoff_dry_run.py` 對照自己收到的路徑）。
4. 確認沒有收到任何本計畫「明確排除」清單中的項目——若發現，回報給 Member A，
   不要自行刪除或使用。
5. 依 `B_HANDOFF_README_TEMPLATE.md` 或 `C_ANDROID_HANDOFF_README_TEMPLATE.md`
   的指示繼續後續工作。

## Dry-run 結果（本輪已實際執行，非估計值）

見下方最終報告與 `manifests/team_data/B_handoff_dry_run_report.json`／
`C_handoff_dry_run_report.json` 兩份實際產出的報告。**本次執行只做了讀取／hash／
統計，沒有複製或搬移任何檔案。**

**平台更正說明**：`C_handoff_dry_run_report.json` 是對照**舊的 iOS manifest**
（`C_ios_benchmark_handoff_manifest_template.csv`）執行的結果，數字本身（TFLite
hash、40 張圖片、golden predictions 缺失等）在 Android 情境下依然成立，因為
底層資產（fp32 TFLite、40 張測試圖）完全相同、只是交接套件重新對應到 Android。
新建立的 `C_android_benchmark_handoff_manifest_template.csv` 本輪**尚未**另外跑過
一次 `scripts/build_member_handoff_dry_run.py`——內容與舊 manifest 的資產清單一致
（只是把 routing spec／protocol／app stub 的路徑換成 `android_benchmark/` 底下的
檔案），需要時可直接對新 manifest 重新執行一次 dry-run 確認。
