# Handoff Package 解壓說明

本文件說明 `handoff_packages/` 下兩個 zip 檔案的內容,以及 Member B、Member C 拿到後應該解壓到自己本機 repo 的哪個位置。這兩個 zip 由 Member A 產生並上傳到 Google Drive,不會進 git。

## Google Drive 分享設定提醒

Google Drive 的連結分享是「知道連結就能看」機制,不是帳號白名單制。如果只想讓 Member B / Member C 兩人看到,請在 Drive 分享設定選「**限定特定人**」並直接輸入他們的 email,而不是用「知道連結的人均可查看」。

---

## Package 1:`AIGC_MemberB_Phase2_XAI_20260815.zip`

**用途**:Member A 授權後產生的完整 Phase 2 XAI / external filter validation handoff package,包含 production checkpoint、自建 paired filter XAI 證據、以及 `FFHQ_ali_process` 的 `Whitening_60` / `Whitening_90` 外部驗證子集。

**內容清單**(對應 `manifests/team_data/B_phase2_xai_handoff_manifest_template.csv`):

| Zip 內路徑 | 說明 |
|---|---|
| `shufflenet_v2_layer1_v811d.pth` | Production Layer1 checkpoint |
| `shufflenet_v2_layer2_v811.pth` | Production Layer2 checkpoint |
| `artifact_classifier_v3.pth` | 4 類 filter artifact 分類器 |
| `face_landmarker.task` | MediaPipe 臉部偵測模型(第三方,僅供內部使用) |
| `results/phase2_p0_v811_filter_gradcam_validation_20260813.json` | Production Filter XAI 驗證結果(IoU/PointingGame) |
| `results/xai_filter_localization_results_v1_20260812.csv` | 逐圖 paired-GT 定位結果 |
| `results/gt_vs_gradcam/*.png` | GT vs. heatmap 對照圖(4 種 filter type) |
| `results/xai_faithfulness_blur_v1_20260813.json` | Fake-class Grad-CAM++ faithfulness 驗證 |
| `results/phase2_composite_explanation_v1_20260813*.{jsonl,json}` | Fake+filter composite explanation 樣本(僅 AIGuard in-domain,不可外推) |
| `results/phase2_composite_filtertype_accuracy_v1_20260813.json` | artifact_classifier_v3 在 composite 上的 type accuracy |
| `results/phase2/filter_data_xai_provenance_audit_20260814/*` | Filter data provenance 稽核三份文件 |
| `filter_data/clean_output/clean_paths.txt` | artifact_classifier_v3 實際訓練資料清單(參考用) |
| `FFHQ_ali_process/Whitening_60/`、`Whitening_90/` | **外部驗證資料(第三方,約 1.8GB)。經 Member A 明確授權後納入,授權審查本身未完成,僅供內部交接使用,不可再對外散布。** |

**解壓位置**:整包解壓到 repo 根目錄,讓路徑直接對齊(例如解壓後 `shufflenet_v2_layer1_v811d.pth` 就落在 repo 根目錄、`results/...` 落在 `results/` 底下)。不需要額外調整路徑,因為 zip 內部結構本身就是相對於 repo 根目錄建的。

**Member B 收到後應該做的驗證**:
1. 核對兩個 production checkpoint 的 SHA256:
   - `shufflenet_v2_layer1_v811d.pth` 應為 `3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7`
   - `shufflenet_v2_layer2_v811.pth` 應為 `8470ad52dadcdb44a6789067efbbd7fbc20715cb3f4e3339630191889a55057e`
2. 先讀 `results/phase2/filter_data_xai_provenance_audit_20260814/FILTER_XAI_CLAIM_MATRIX.md`,確認每個 family 能不能支持哪種 XAI claim,再開始做外部驗證分析。
3. `Whitening_60`/`Whitening_90` 只能作為 `VERIFIED_SINGLE_TYPE` exact-type accuracy 的 benchmark,其餘 `FFHQ_ali_process` 資料夾一律視為 `COARSE_OR_MIXED`,不可混用。

---

## Package 2:`AIGC_MemberC_Android_20260815.zip`

**用途**:Android on-device benchmark handoff package。**現在已完整**——40 張測試圖與 golden predictions 已補上。

**內容清單**(對應 `manifests/team_data/C_android_benchmark_handoff_manifest_template.csv` 全部 16 項):

| Zip 內路徑 | 說明 |
|---|---|
| `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite` | Layer1 fp32 TFLite |
| `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite` | Layer2 fp32 TFLite |
| `android_benchmark/TEST_ASSET_MANIFEST.csv` | 40 張測試圖清單(含來源路徑與預期 SHA256) |
| `android_benchmark/test_assets/*.jpg\|png`(40 張) | 實際測試圖片,已核對 SHA256 全數與 manifest 相符 |
| `android_benchmark/golden_outputs/golden_predictions_v811d_layer2v811.json` | 桌機 fp32 TFLite 對 40 張圖的逐張參考預測(label + 各層機率 + checkpoint/TFLite SHA256),供 Android 端做 parity 比對 |
| `android_benchmark/PRODUCTION_ROUTING_SPEC.md` | 從 pipeline.py 抽出的路由/前處理規格 |
| `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` | 完整 benchmark 流程與 7 項 acceptance gate |
| `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` | Benchmark 結果輸出格式 |
| `android_benchmark/app_stub/*.kt` | Kotlin 骨架(未實作,需 Member C 補完) |
| `android_benchmark/README.md` | Android Studio 設定步驟 |
| `android_benchmark/golden_outputs/README.md` | Golden output 說明 |
| `results/mobile_deployment_benchmark.json` | 桌機 CPU fp32 TFLite 參考數字,供裝置端結果比對基準 |
| `PACKAGE_COMPLETE_README.md` | **請先讀這份**——說明本次補齊內容,以及一個誠實記錄的發現(見下方) |

**解壓位置**:同樣解壓到 repo 根目錄,`android_benchmark/`、`results/` 會直接對齊到原本的相對路徑。

**Member C 收到後應該做的驗證**:
1. 核對兩個 TFLite 檔案的 SHA256:
   - `layer1_v811d_float32.tflite` 應為 `c16cf71f250bea1cc83fe171dc7120edbd2335c06eef3f20998e20d2f4194389`
   - `layer2_v811_float32.tflite` 應為 `3deed69d6ca4ebb9f7597391ce04390c49758e283a59bbbc988f615dd14eb0cd`
2. 核對 `golden_predictions_v811d_layer2v811.json` 裡每張圖的 `source_sha256` 與 `TEST_ASSET_MANIFEST.csv` 一致。
3. **注意(誠實記錄,非 bug)**:golden predictions 顯示這 20 張 True Test real(LFW)圖片中有 8 張被判為 filter(real recall 60%,僅這 20 張小樣本)。這不是產生腳本的錯誤(SHA256、前處理、checkpoint 都已核對一致),而是**這個指標本來就沒被 production 當作正式 gate 追蹤**(production 用 CelebA real recall 99.7% 把關),詳見 `PACKAGE_COMPLETE_README.md`。Android 端比對 parity 時,golden output 就是這樣的真實模型行為,不要預期 20 張圖都判 real。
4. **不可用 Android Emulator 的延遲數字當正式結果**,只能用實體裝置。
5. **不可自行替換成 int8/fp16 或更改 routing 邏輯**——`PRODUCTION_ROUTING_SPEC.md` 是唯一依據。

---

## 兩個 package 共同的規則(摘自 `docs/team/PRODUCTION_CHANGE_CONTROL.md` 與 `docs/team/TEAM_WORK_ALLOCATION.md`)

- 收到的 checkpoint / TFLite 一律視為唯讀 baseline,不可修改。
- 任何要動到 `pipeline.py`、threshold、routing、checkpoint 的想法,先走 change control 流程,不可直接改。
- B、C 各自產出的新結果,輸出路徑都要帶日期與 task 名稱,不可覆蓋既有檔案(細節見 `docs/team/EXPERIMENT_HANDOFF_TEMPLATE.md`)。
