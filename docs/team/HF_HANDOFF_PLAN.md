# Hugging Face Handoff Plan（規劃文件，尚未執行任何上傳）

> 建立於 2026-08-14，中文撰寫。本文件規劃（**不執行**）兩個 Hugging Face private
> Dataset repo，作為 Member B、Member C 實際的跨團隊資料交付管道——理由見
> `DATA_SHARING_STRATEGY.md` 的修正說明：N-drive 是 Member A 個人磁碟，B/C 完全
> 無法存取，HF private repo 是這份清單裡唯一 B/C 真正搆得到的層級。
>
> **本次協作環境中沒有 Hugging Face token，本文件與對應的
> `scripts/build_hf_handoff_package.py` 都只執行過 dry-run（唯讀，不連網、不需要
> token），沒有建立任何實際的 HF repo，也沒有上傳任何檔案。** 下方所有數字都是
> `scripts/build_hf_handoff_package.py --member B --member C` 實際執行後的真實結果
> （見 `results/team/hf_handoff_dry_run_20260815/hf_handoff_plan_B.json` 與
> `hf_handoff_plan_C.json`），不是估計值。

## Repo 1 — Member B（Phase 2 XAI handoff）

- **提議的 repo 名稱**：`aigc-team/phase2-xai-handoff-b`（**提議中，尚未建立**）
- **Visibility**：**private**（必要條件，非選配——即使全部內容都通過授權審查，
  也維持 private，只邀請團隊成員）
- **資料來源**：`manifests/team_data/B_phase2_xai_handoff_manifest_template.csv`
  （21 列）＋其 dry-run 結果

### 資料夾結構（提議）

```
aigc-team/phase2-xai-handoff-b/
├── checkpoints/
│   ├── shufflenet_v2_layer1_v811d.pth
│   ├── shufflenet_v2_layer2_v811.pth
│   └── artifact_classifier_v3.pth
├── xai_evidence/
│   ├── phase2_p0_v811_filter_gradcam_validation_20260813.json
│   ├── xai_filter_localization_results_v1_20260812.csv
│   ├── xai_faithfulness_blur_v1_20260813.json
│   ├── phase2_composite_explanation_v1_20260813.jsonl
│   ├── phase2_composite_explanation_v1_20260813_summary.json
│   └── phase2_composite_filtertype_accuracy_v1_20260813.json
├── figures/
│   ├── gt_vs_gradcam_eye_enlarging.png
│   ├── gt_vs_gradcam_face_reshaping.png
│   ├── gt_vs_gradcam_smoothing.png
│   └── gt_vs_gradcam_whitening.png
├── provenance_manifests/
│   ├── FILTER_DATA_PROVENANCE.csv
│   ├── FILTER_XAI_CLAIM_MATRIX.md
│   ├── ARTIFACT_TAXONOMY_ALIGNMENT.md
│   └── clean_paths.txt
└── README.md（放置本次 dry-run 摘要＋每個檔案的來源／SHA256 對照表）
```

### 現在就可以上傳的項目（17 項，共 32.08 MB，已通過授權判定）

判定依據：`license_status` 欄位以 `internal (project-owned)` 或
`internal (project-generated` 開頭——即本專案自己擁有或自己生成的內容，不涉及
第三方轉散布問題。

| 檔案 | 大小 |
|---|---:|
| `shufflenet_v2_layer1_v811d.pth` | 9.84 MB |
| `shufflenet_v2_layer2_v811.pth` | 9.84 MB |
| `artifact_classifier_v3.pth` | 4.97 MB |
| `results/phase2_p0_v811_filter_gradcam_validation_20260813.json` | 0.12 MB |
| `results/xai_filter_localization_results_v1_20260812.csv` | 0.01 MB |
| `results/gt_vs_gradcam/gt_vs_gradcam_eye_enlarging.png` | 1.33 MB |
| `results/gt_vs_gradcam/gt_vs_gradcam_face_reshaping.png` | 1.40 MB |
| `results/gt_vs_gradcam/gt_vs_gradcam_smoothing.png` | 1.37 MB |
| `results/gt_vs_gradcam/gt_vs_gradcam_whitening.png` | 1.31 MB |
| `results/xai_faithfulness_blur_v1_20260813.json` | 0.03 MB |
| `results/phase2_composite_explanation_v1_20260813.jsonl` | 0.04 MB |
| `results/phase2_composite_explanation_v1_20260813_summary.json` | 0.00 MB |
| `results/phase2_composite_filtertype_accuracy_v1_20260813.json` | 0.05 MB |
| `results/phase2/filter_data_xai_provenance_audit_20260814/FILTER_DATA_PROVENANCE.csv` | 0.01 MB |
| `.../FILTER_XAI_CLAIM_MATRIX.md` | 0.01 MB |
| `.../ARTIFACT_TAXONOMY_ALIGNMENT.md` | 0.01 MB |
| `filter_data/clean_output/clean_paths.txt` | 1.75 MB |

### 卡在授權審查、不可上傳的項目（3 項，共約 1,792 MB）

| 檔案 | 大小 | 卡住原因 |
|---|---:|---|
| `face_landmarker.task` | 3.58 MB | 第三方（MediaPipe/Google）預訓練模型，本輪未做轉散布條款確認 |
| `FFHQ_ali_process/Whitening_60/` | **887.52 MB** | 第三方（RetouchingFFHQ／Alibaba）資料，未做授權審查 |
| `FFHQ_ali_process/Whitening_90/` | **901.14 MB** | 第三方（RetouchingFFHQ／Alibaba）資料，未做授權審查 |

**這兩個 900MB 級目錄正是體積安全檢查要攔下來的典型案例**——即使它們理論上是
Member B 任務需要的資料（`VERIFIED_SINGLE_TYPE` 子集，見
`TEAM_WORK_ALLOCATION.md` §D），在完成 RetouchingFFHQ 授權審查之前依然不可上傳，
不論是 HF 還是任何其他管道。

### 尚未存在、無法判定的項目（1 項）

- `FFHQ_ali_process/EyeEnlarging_30/`（代表性 `COARSE_OR_MIXED` 樣本）——manifest
  裡描述的是「代表性子集」而非單一路徑，需要 Member B 實際決定要抽哪 200 張後
  才能具體化成可檢查的資產。

## Repo 2 — Member C（Android benchmark handoff）

- **提議的 repo 名稱**：`aigc-team/android-benchmark-handoff-c`（**提議中，尚未建立**）
- **Visibility**：**private**
- **資料來源**：`manifests/team_data/C_android_benchmark_handoff_manifest_template.csv`
  （16 列）＋其 dry-run 結果

### 資料夾結構（提議）

```
aigc-team/android-benchmark-handoff-c/
├── tflite/
│   ├── layer1_v811d_float32.tflite
│   └── layer2_v811_float32.tflite
├── spec/
│   ├── PRODUCTION_ROUTING_SPEC.md
│   ├── DEVICE_BENCHMARK_PROTOCOL.md
│   └── EXPECTED_OUTPUT_SCHEMA.json
├── app_stub/
│   ├── MainActivity.kt
│   ├── ModelRunner.kt
│   ├── ImagePreprocessor.kt
│   ├── BenchmarkRunner.kt
│   └── BenchmarkStats.kt
├── test_assets/
│   ├── TEST_ASSET_MANIFEST.csv
│   └── （40 張圖片本身——待授權審查後才可放入，見下）
├── golden_outputs/
│   └── （待生成，見下）
├── reference/
│   └── mobile_deployment_benchmark.json
└── README.md
```

### 現在就可以上傳的項目（14 項，共 20.95 MB，已通過授權判定）

| 檔案 | 大小 |
|---|---:|
| `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite` | 10.46 MB |
| `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite` | 10.46 MB |
| `android_benchmark/TEST_ASSET_MANIFEST.csv` | 0.01 MB |
| `android_benchmark/PRODUCTION_ROUTING_SPEC.md` | 0.01 MB |
| `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` | 0.00 MB |
| `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` | 0.00 MB |
| `android_benchmark/app_stub/*.kt`（5 個檔案） | 各 0.00 MB |
| `android_benchmark/README.md` | 0.00 MB |
| `android_benchmark/golden_outputs/README.md` | 0.00 MB |
| `results/mobile_deployment_benchmark.json` | 0.00 MB |

### 卡在授權審查、不可上傳的項目

**本輪判定：0 項被授權規則擋下**——C 套件目前已存在的內容全部是本專案自己
產生的（checkpoint／TFLite／文件／程式碼骨架），沒有第三方資料。

### 尚未存在、無法上傳的項目（2 項）

- **40 張 benchmark 測試圖片**（`android_benchmark/TEST_ASSET_MANIFEST.csv` 所列）——
  manifest 本身可以上傳，但圖片檔案本身：(a) 尚未被裝箱進任何交接位置（本專案
  歷來每一輪都刻意不做這件事），(b) 其中來自 `lfw/`（LFW 條款）與 `sd2.1/`
  （DF40 條款）的圖片需要單獨授權確認，`test_set_true/filter/` 的部分是自建、
  不受此限制。
- **Golden predictions**（例如 `golden_predictions_v811d_layer2v811.json`）——
  截至本輪**仍不存在**，需要先用桌機 fp32 TFLite pipeline 對 40 張圖跑一次才能
  產生，這是本專案本輪多次確認過的既有缺口，不是新發現。

## 使用者自己執行時的實際上傳流程（本次協作環境不會執行，僅記錄指令）

**前提**：需要一個有效的 Hugging Face 帳號、對應的 write-access token，以及
`huggingface_hub` Python 套件。本次協作環境沒有 token，`scripts/build_hf_handoff_package.py`
的 `--upload` 模式在沒有偵測到 `HF_TOKEN`／`HUGGING_FACE_HUB_TOKEN` 環境變數時會
**主動拒絕執行**，不會嘗試連網或要求輸入憑證。

```bash
# 1. 安裝套件（一次性）
pip install huggingface_hub

# 2. 登入（會開瀏覽器或要求貼上 token，互動式）
huggingface-cli login

# 3. 建立兩個 private repo（type=dataset，一次性，之後重複使用同一個 repo）
huggingface-cli repo create phase2-xai-handoff-b --type dataset --private
huggingface-cli repo create android-benchmark-handoff-c --type dataset --private

# 4. 設定 token 環境變數（Windows PowerShell 範例）
$env:HF_TOKEN = "hf_xxxxxxxxxxxxxxxxxxxx"

# 5. 執行本次協作準備好的上傳腳本（--upload 模式；本次協作環境未執行這一步）
python scripts/build_hf_handoff_package.py --member B --upload
python scripts/build_hf_handoff_package.py --member C --upload
```

**目前的實作狀態誠實說明**：`scripts/build_hf_handoff_package.py` 的 `--upload`
模式目前只會檢查 token／套件是否就緒並印出訊息，**尚未實作真正呼叫
`huggingface_hub` 的 `upload_file()`／`create_repo()` 的程式碼**——這是刻意的：
先讓團隊確認本文件規劃的 repo 名稱與資料夾結構沒有問題，再補上真正的上傳呼叫，
避免第一次執行就把還沒定案的結構固化到一個正式 repo 裡。

## 授權審查完成前，兩個 repo 目前建議的初始內容

- **Repo B**：先只放上方「現在就可以上傳」的 17 項（32.08 MB），`FFHQ_ali_process`
  子集待授權審查通過後再補。
- **Repo C**：先只放上方「現在就可以上傳」的 14 項（20.95 MB），40 張測試圖與
  golden predictions 待對應前置步驟完成後再補。

兩者都遠低於任何 HF 免費方案的容量限制，適合作為 repo 建立後的第一批內容。
