

# AIGC Detection Team — 工作分配與協作規範



## A. 專案現況總覽

### 已凍結的 production baseline（撰寫當下已重新核對 `docs/releases/v8.11_production/RELEASE_MANIFEST.json`，非手抄）

- **Release**：`v8.11_production`，`release_status: FROZEN_DESKTOP_VALIDATED`。
- **Layer1**：`shufflenet_v2_layer1_v811d.pth`，SHA256
  `3C61CF6886D2F9D4871B52749A15FD4E1B979D121C664BA85D9B069194C290B7`。
- **Layer2**：`shufflenet_v2_layer2_v811.pth`，SHA256
  `8470AD52DADCDB44A6789067EFBBD7FBC20715CB3F4E3339630191889A55057E`。
- Status 各子欄位（撰寫當下重新讀取）：`checkpoint_provenance_status`、
  `evaluation_integrity_status`、`filter_xai_status`、`desktop_tflite_status` 皆為
  **VERIFIED**；`ios_on_device_status` = **PENDING**（唯一尚未關閉的項目）。
  **平台更正說明（2026-08-14）**：`RELEASE_MANIFEST.json` 這個欄位目前仍沿用
  `ios_on_device_status` 這個既有名稱（本文件未修改該 JSON 檔案），但實際負責
  on-device 實測的 Member C 使用的是 **Android** 裝置，不是 iPhone——見下方
  Deployment 現況與 §E。日後若要正式改欄位名稱，需走
  `PRODUCTION_CHANGE_CONTROL.md`；本文件先在文字說明中做出正確區分。
- `pipeline.py` 是凍結的 production 參考版本，任何成員未經團隊審查不得直接修改。


### Phase 1 已完成事項

- v8.11 hierarchical 架構（Layer1 real-vs-manipulated → Layer2 fake-vs-filter）已凍結，
  全部通過 A 級 Freeze Gate 指標（True Test fake/filter recall、AIGuard-unseen AUROC、
  CelebA/StyleGAN2/Alibaba OOD、fp32 TFLite ≤25MB），見
  `docs/releases/v8.11_production/PHASE1_FREEZE_DECISION.md`。所有頭條數字已在 P0
  Production Evaluation Integrity Repair（`results/releases/v8.11_production_20260813/`）
  中用新鮮、附 hash 的證據重新驗證過。
- Cross-source fake+filter 泛化問題已深入診斷，尚未修復：
  - **P1-R1**（`results/research/p1_r1_cross_source_failure_anatomy_20260814/`）：確認
    DF40-cdf cross-source 失效最可能是與圖片原生解析度相關的 source shortcut（H2 成立），
    Layer1／fake-head 的 routing 不是瓶頸（H5 已排除），且先前的 invariance-loss 嘗試
    （Cell D）收益小、代價大。
  - **P1-R1.5**（`results/research/p1_r1_5_resolution_causal_audit_20260814/`）：跑了
    controlled resolution-resampling audit，發現專案自己的濾鏡生成程式碼使用**固定像素**
    參數（15px bilateral-blur 直徑、60px warp 半徑），不具尺度不變性——直接讀
    `filters/stress_test_filter_functions.py` 確認。把解析度統一到 256px 後，smoothing
    偵測在全部 5 個 DF40-cdf 來源上收斂到 ≥0.97 AUROC（pixart/sd2.1 在原生解析度下原本
    低至 0.51）；face_reshaping 改善幅度較小，且即使解析度校正後仍殘留 generator-identity
    落差。建議下一步：**重新設計濾鏡生成器（讓 kernel／warp 半徑依偵測到的臉部尺寸縮放）**，
    而非 invariance loss，也不是把 resolution-consistency training 當第一步。
- v8.12–v8.16 研究支線（base-diversity、hard-neg mining、dual-head、mixed-lineage）
  完整記錄於 `docs/EXPERIMENT_REGISTRY.md`，皆未晉升 production。

### Phase 2 已完成事項

- XAI evidence-tier 框架（Tier A-D，`docs/phase2_story.md` §8），區分自建 paired-GT 資料
  與外部 RetouchingFFHQ 資料，目前已在指導哪些措辭站得住腳。
- Production checkpoint（v8.11d/v811）的 Grad-CAM++ 重新驗證
  （`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`）——eye_enlarging 與
  face_reshaping 在 production 上持平或優於舊版 v8.8 研究；whitening 的 PointingGame
  定位退步（0.880→0.357），已根因分析為熱圖峰值位置近乎固定的 bug，不是內容驅動的訊號。
- Fake 類別（Layer1/fake_head）Grad-CAM++ **faithfulness** 已用 blur-based masking 驗證
  （`xai_faithfulness_blur_test.py`、`results/xai_faithfulness_blur_v1_20260813.json`）：
  在 k=5/10/20% 下 hot-region 分數下降 > cold-region 下降 > matched-random 下降，
  即熱圖對模型實際依據具備可信度。**命名說明**：本專案用的是四級（A-D）evidence 框架，
  repo 中找不到任何「Level 1/2」這種命名——本節刻意不使用該未經驗證的說法。
- **`filter_head` 自己的 faithfulness test**（在 composite fake+filter 情境下分開測，
  `docs/phase2_story.md` §9）發現對 smoothing 這個濾鏡型別出現**反向／混淆**的結果——
  blur masking 本身就很像一種 smoothing 操作，污染了測試。這是一個尚未解決的方法論缺口，
  不是已通過的檢驗項目。
- **Phase 2 Filter Data & XAI Provenance Audit**
  （`results/phase2/filter_data_xai_provenance_audit_20260814/`）：發現
  `artifact_classifier_v3.pth`（`pipeline.py` 呼叫的 4-way filter-type 分類器）完全只用
  自建資料訓練，從未對任何外部 RetouchingFFHQ 來源自己的 ground-truth type 標籤做過驗證——
  這是一個現行、尚未處理的 overclaim 風險。已找到成本最低的修法：用 `FFHQ_ali_process`
  自己的資料夾名稱標籤來評分（資料已存在，不需新蒐集）——**2026-08-14 已收斂範圍**：
  詳見下方 §D 與驗證說明。
- **⚠️ 2026-08-20 更正（先前敘述已過期，已用完整 `grep -r` 重新查證，先前查證用的
  Grep 工具因遵循 ignore 規則而漏掉 `results/` 底下的內容，導致誤判）**：
  `tex_local_variance_std` **已被明確定義並實作**（`results/phase2/
  fake_evidence_discovery_v811d_20260814/scripts/extract_features.py` L283，
  5x5 local-variance map 跨畫面標準差），是 24 個候選特徵中唯一通過 discovery 輪
  direction-consistency 的一個，並已在 `fake_evidence_resolution_matched_v811d_
  20260814/` 做過解析度混淆因子排除的專屬複測。**有限度可宣稱**：7/8 來源在
  解析度配對後仍保持方向一致；**不可宣稱**：最嚴格的 joint_matched 檢定因樣本
  量不足（6/8 來源 n<10）無法排除混淆因子、midjourney 方向相反、目前是描述性
  統計非已訓練驗證的分類特徵、未接入 `pipeline.py`。完整版見
  `docs/team/WORKSTREAM_STATUS_BOARD.md` 對應條目。

### Deployment 已完成事項

- TFLite 匯出流程已在桌機端完整驗證（僅 fp32；fp16 已確認損壞、int8 已確認數值錯誤——
  見 `results/mobile_deployment_benchmark.json`）。桌機 PyTorch 與 fp32 TFLite 的預測
  一致性已驗證（769/769 決策一致）。
- **平台更正（2026-08-14）**：先前的裝置平台假設是 iOS／iPhone，已確認錯誤——
  Member C 實際使用的是 **Android** 裝置。原本的 `ios_benchmark/` 交接套件
  （TFLite hash 已驗證、routing spec 已抽取、40 張測試圖已鎖定但未裝箱）已被
  `android_benchmark/` 取代，內容對應調整為 Kotlin／Android Studio／LiteRT，
  `ios_benchmark/` 保留作歷史紀錄，新增 `ios_benchmark/DEPRECATED_SEE_ANDROID.md`
  說明，不再用於實際工作。
- **目前仍未在任何硬體上跑過任何東西**——不論是先前規劃的 iOS 路徑、還是現在的
  Android 路徑，`android_on_device`／`ios_on_device` 狀態都是 **PENDING**，這點沒有
  因為平台更正而改變。

---

## B. 三人分工表

| | **Member A — Phase 1** | **Member B — Phase 2** | **Member C — Deployment** |
|---|---|---|---|
| **研究問題** | fake+filter cross-source 泛化為什麼失效？scale-normalized 濾鏡生成器能否解決？ | 依資料來源，哪些 filter/XAI 主張站得住腳？如何補上外部 type 驗證缺口？ | 凍結版 v8.11d release 能否達到真實 **Android** 裝置的 latency/RAM/stability 目標？ |
| **目前起點** | P1-R1.5 的發現：固定像素濾鏡參數不具尺度不變性；解析度統一化能解掉大部分 smoothing 缺口，但補不齊 face_reshaping | Phase 2 provenance audit 的發現：`artifact_classifier_v3` 未對任何外部來源測過；`unknown_retouch`/`mixed_retouch` 已提案但未建置 | `android_benchmark/` handoff package（取代先前錯誤平台假設下的 `ios_benchmark/`，見 `ios_benchmark/DEPRECATED_SEE_ANDROID.md`）：TFLite hash 已驗證、routing spec 已抽取、測試圖已鎖定但未裝箱、尚未在硬體上跑過 |
| **範圍內任務** | Scale-normalized 濾鏡生成器設計＋校準；小規模 paired cross-resolution 驗證；scale-normalized 訓練候選版；DF40-cdf held-out 重新評測；**僅在**經 scale-normalization 後仍殘留落差時才考慮 source disentanglement | Phase 2F fake per-image evidence 研究；RetouchingFFHQ single-operation（Alibaba）外部 type-accuracy benchmark（**已收斂範圍**：只有 `Whitening_60`/`Whitening_90` 這個 `VERIFIED_SINGLE_TYPE` 子集可以算進 exact-type accuracy；其餘 `FFHQ_ali_process` 資料夾（`EyeEnlarging_*`、`FaceLifting_*`、`Smoothing_*`、`Whitening_30`）一律列為 `COARSE_OR_MIXED`/`UNVERIFIABLE`，只能用於 prediction-distribution／overclaim 稽核，不得算進 accuracy 指標）；`unknown_or_mixed_retouch` 政策設計；fake evidence 特徵驗證（例如尚未定案的 `tex_local_variance_std` 這類候選特徵，需先明確定義再驗證） | 把 40 張測試圖＋TFLite 檔案裝箱搬到 Android Studio 開發機；實作 Android Studio／Kotlin／LiteRT harness；跑實機 benchmark 流程；跟桌機做 golden-output parity test |
| **範圍外任務** | Production XAI 措辭、外部 type 樣板、Android app、Android latency | 凍結版 Phase 1 checkpoint、訓練 splits、production routing、Android benchmark | 分類器、threshold、routing 公式、checkpoint、任何把 Android Emulator 數字當成實機 latency 的作法 |
| **輸入素材** | `filters/stress_test_filter_functions.py`（唯讀參考）、`splits/v815_replication_set.tsv`、`shufflenet_v2_layer1_v812.pth` + Cell C/v816 checkpoint（研究專用，非 production） | `results/phase2/filter_data_xai_provenance_audit_20260814/*`、`FFHQ_ali_process/`、`artifact_classifier_v3.pth`（唯讀參考，了解 baseline 行為用） | `android_benchmark/*`、`results/mobile_export/layer{1,2}_*_tf/*.tflite`、`results/releases/v8.11_production_20260813/*` |
| **預期產出** | 新的 scale-normalized 濾鏡生成器程式碼（新檔案，不改既有濾鏡函式）＋校準報告＋新 checkpoint（研究層級）＋新評測結果，全部放在新的、有日期的 results 資料夾 | 新的外部 benchmark 結果、新的政策提案文件、任何新的 evidence-feature 驗證報告，全部放在新的、有日期的 results 資料夾 | 完成的 Android Studio 專案＋符合 `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` 格式的真實 benchmark 輸出，放在 `android_benchmark/results/<device_model>_<date>/` |
| **成功標準** | DF40-cdf joint recognition 有改善，且不讓 True Test/Shadow/fake+filter-misclass 各項 gate 退步；殘留落差問題（單純解析度 vs. generator-identity）要有證據回答，不能用猜的 | `Whitening_60`/`Whitening_90` 這個 `VERIFIED_SINGLE_TYPE` 子集要有 exact-type accuracy 數字；其餘 `COARSE_OR_MIXED`/`UNVERIFIABLE` 資料夾要有獨立的 prediction-distribution／overclaim 稽核（不是 accuracy 數字）；針對 B/C（mixed-operation）來源要有經過審查的處理提案 | `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` 全部 acceptance gate 項目都要在真機上量測到（不要求全部 pass） |
| **需要文件** | 新的 `P1-R3.x` findings 文件，每份都要有 claim/non-claim | 新的 Phase 2 findings 文件，格式比照 `EXTERNAL_FILTER_XAI_RISK_REGISTER.md`，每份都要有 claim/non-claim | 填好的 `android_benchmark/EXPECTED_OUTPUT_SCHEMA.json` 格式結果＋填好的 `DEVICE_BENCHMARK_PROTOCOL.md` gate 表 |
| **對其他成員的依賴** | 起步不需要；若日後有 production candidate 提案，需要 B 確認 XAI 主張仍成立、C 確認不會讓部署體積／延遲退步 | 起步不需要 | 需要 A/B 在 benchmark 進行期間不要中途更換 checkpoint（只是排程協調，非主動阻擋） |
| **交接條件** | Production candidate 提案唯有通過 `PRODUCTION_CHANGE_CONTROL.md` 流程、並取得 B、C 簽核才能往下走 | 任何新輸出類別（`unknown_retouch` 等）要成為 production candidate，一樣要走同一套變更管制流程，並由 A 確認不會跟 Phase 1 語意衝突 | 完成的裝置實測結果直接餵進 `docs/releases/v8.11_production/PHASE1_FREEZE_DECISION.md` 的裝置實測狀態升級流程（目前欄位仍名為 `ios_on_device_status`，見 §A 平台更正說明），經變更管制提案 |

---

## C. Member A 詳細工作包 — Phase 1（fake+filter cross-source 泛化）

直接延續 P1-R1／P1-R1.5。任務編號沿用既有的 `P1-Rn` 命名慣例。

- **P1-R3.0 — Scale-Normalized Filter Generator Calibration**：設計新的濾鏡生成模組
  （新檔案——不要手動修改 `filters/stress_test_filter_functions.py`，該檔已明確標示為
  逐位元組抽取、不可手改；若上游 `AIGuard/stress_test_v811_pipeline.py` 有變動才需要
  重新產生，見該檔自己的檔頭說明），讓 `apply_smoothing` 的 bilateral-filter 直徑與
  `apply_face_reshaping` 的 warp 半徑依偵測到的臉部尺寸縮放（沿用 `apply_eye_enlarging`
  已經在用的 self-scaling 模式），取代目前固定的 15px/60px 常數。校準時要對照既有自建
  訓練分佈，確保同分布內的濾鏡強度不會被悄悄改變。
- **P1-R3.1 — 小規模 paired cross-resolution 驗證**：在正式訓練前，先確認新生成器在
  不同解析度下產出的相對濾鏡強度視覺上／統計上一致（重用 P1-R1.5 的
  resolution-controlled harness 設計模式——新腳本、新輸出資料夾，不要覆寫
  `results/research/p1_r1_5_resolution_causal_audit_20260814/`）。
- **P1-R3.2 — Scale-normalized fake+filter 訓練候選版**：用新生成器的輸出訓練一個新的
  研究用 checkpoint（絕對不是凍結的 v8.11d/v811 那組），遵循本專案既有的
  checkpoint-promotion 紀律（完整 SHA256＋訓練 manifest＋split manifest，即使停留在
  研究層級也要做到，見 `PRODUCTION_CHANGE_CONTROL.md` §checkpoint 規則）。
- **P1-R3.3 — Held-out DF40-cdf replication 評測**：用 P1-R1／P1-R1.5 用過的**同一份、
  未經修改**的 `splits/v815_replication_set.tsv` 評測新 checkpoint——這份資料集**絕對不能**
  用於訓練或 threshold 選擇（見下方 §F 與 `docs/EXPERIMENT_REGISTRY.md` 對這份資料既有的
  provenance 規則）。直接跟 P1-R1.5 的 baseline 數字做對照。
- **Source/filter disentanglement — 有條件，非預設項目**：依 P1-R1.5 自己的發現
  （`P1_R1_5_FINDINGS.md`：face_reshaping 在解析度校正後仍殘留 generator-identity 落差，
  而 smoothing 的落差看起來完全能被解析度混淆因子解釋），只有在 P1-R3.3 顯示解析度
  校正後仍有殘留、且與來源相關的落差時，才考慮 source-disentanglement 或 invariance
  機制。不要預先設計 invariance loss——這正是依循證據的做法，也呼應本專案先前的發現
  （Cell D：收益小、代價大），避免在確認 scale-normalization 沒能解決問題之前就先蓋一個。

**Member A 明確不負責**：production XAI 措辭／樣板（Member B 的）、
`artifact_classifier_v3` 的 type-prediction 驗證（Member B 的）、Android app 或任何
latency/RAM 量測（Member C 的）。

## D. Member B 詳細工作包 — Phase 2（XAI／外部驗證）

- **Phase 2F — fake per-image evidence 研究**：探索 fake-class evidence 的候選量化特徵
  （類比於目前支撐 filter-class Tier A 主張的紋理／頻率統計量）。**⚠️ 2026-08-20
  更正**：`tex_local_variance_std` 已不再是「找不到、未實作」的候選名稱——它已被
  定義、實作、且做過兩輪查證（discovery + resolution-matched 複測），有限度可宣稱
  部分方向一致性，但尚未排除 joint 混淆因子、未接入 pipeline.py。完整、有界限的
  現況見上方§A 更正段落，任何後續使用此特徵的規劃請先讀那段，不要重複本條目
  已過期的「完全找不到」說法。
- **外部 RetouchingFFHQ single-operation benchmark — 已收斂範圍（2026-08-14 修正）**：
  用 `FFHQ_ali_process` 自己的資料夾名稱 ground truth 評分 `artifact_classifier_v3`，
  但**只有 `Whitening_60` 與 `Whitening_90` 可以算進 exact-type accuracy 指標**——這是
  目前唯一歸類為 `VERIFIED_SINGLE_TYPE` 的兩個資料夾。其餘資料夾
  （`EyeEnlarging_{30,60,90}`、`FaceLifting_{30,60,90}`、`Smoothing_{30,60,90}`、
  `Whitening_30`）一律列為 `COARSE_OR_MIXED`/`UNVERIFIABLE`——可以拿去跑分類器並報告成
  **prediction-distribution／overclaim 稽核**（例如「模型在這些資料夾上實際預測出什麼、
  多常預測出跟資料夾名稱不同的型別」），但**不可**併入 exact-type accuracy 數字，
  因為這些資料夾自身的純度從未被驗證過。
  **重要但書，明講不隱瞞**：本輪對 `FFHQ_ali_process/` 做的獨立結構性複查（見 §A）發現，
  repo 中**沒有任何證據**顯示 `Whitening_60`/`90` 真的比其他 10 個資料夾更「已驗證」——
  全部 12 個資料夾格式完全相同、純度 metadata 一律是零。請把 `VERIFIED_SINGLE_TYPE`
  這個標籤理解成**團隊目前的政策選擇**，不是本文件證據自己獨立確立的事實；若 Member B
  的調查發現有理由調整合格資料夾範圍，請同步更新本節與 `WORKSTREAM_STATUS_BOARD.md`，
  並在下次 integration review 上提出。新的評測腳本（不要修改
  `AIGuard/eval_ali_ood_v811.py`），輸出放新的 results 資料夾。
- **外部 artifact classifier type 泛化**：等基本數字出來後，把上面的結果擴充成更完整的
  per-type、per-intensity（30/60/90）accuracy 拆解——對 `COARSE_OR_MIXED`/`UNVERIFIABLE`
  資料夾而言，這仍然只是 distribution／overclaim 拆解，不是 accuracy 拆解，依照上面的
  範圍限定。
- **`unknown_or_mixed_retouch` 政策提案**：一份書面設計提案（非實作），說明
  `pipeline.py` 應該如何表示 RetouchingFFHQ 風格的多重操作輸入（provenance audit 中的
  B/C 家族），直接沿用
  `results/phase2/filter_data_xai_provenance_audit_20260814/ARTIFACT_TAXONOMY_ALIGNMENT.md`
  提出的 `mixed_retouch`/`unknown_retouch`/`app_processed` 類別構想。僅止於提案——任何
  實際的 schema／樣板／模型變更都要走 `PRODUCTION_CHANGE_CONTROL.md`。
- **明講的防呆規則**：fake 說明文字必須維持證據支撐的樣板／規則式輸出，**不得**被
  自由生成的 MLLM 文字取代目前的 evidence pipeline——這與本專案既有的立場一致
  （`CLAUDE.md`：FakeVLM 因太重而放棄；`docs/phase2_story.md` 明確限制 VLM 產生的文字
  不可當 ground truth）。

**Member B 明確不能碰**：凍結的 Phase 1 checkpoint
（`shufflenet_v2_layer1_v811d.pth`/`shufflenet_v2_layer2_v811.pth`）、任何訓練 split
檔案、production routing 邏輯（`hierarchical_predict()`）、Android benchmark。

## E. Member C 詳細工作包 — Deployment（**2026-08-14 平台更正：Android，非 iOS**）

> Member C 實際使用的是 **Android** 裝置，不是 iPhone。先前基於 iOS／Xcode／Swift
> 假設建立的內容已被取代，見 `android_benchmark/` 與 `ios_benchmark/DEPRECATED_SEE_ANDROID.md`。

- **Android benchmark handoff package**：已完成（`android_benchmark/`），是本工作包
  的起點，不需要重做。內容包含 `README.md`、`DEVICE_BENCHMARK_PROTOCOL.md`、
  `PRODUCTION_ROUTING_SPEC.md`、`EXPECTED_OUTPUT_SCHEMA.json`、
  `TEST_ASSET_MANIFEST.csv`、`golden_outputs/`、`app_stub/`（Kotlin 骨架）。
- **Android Studio／實體 Android 裝置實作**：從 `android_benchmark/app_stub/*.kt`
  建出真正的 Android Studio 專案，接上 LiteRT（TensorFlow Lite for Android，
  fp32 CPU 為必要 baseline；NNAPI／GPU delegate 僅為選配對照組，見下方）、
  provision 一台實體裝置（**Android Emulator 明確不足以量測 latency**，見
  `android_benchmark/README.md`）。
- **正式 production routing 收尾**：`android_benchmark/PRODUCTION_ROUTING_SPEC.md`
  §4 已定案——把**實際的** production composite-probability 規則
  （`hierarchical_predict()`，Layer2 一律執行）實作成 benchmark 的**主要**路徑，
  因為那才是 `pipeline.py` 真正上線的行為；比較便宜的 strict-gate 近似可以另外
  量測做對照，但要清楚標示那不是 production 規則。
- **Golden output parity test**：對已裝箱的 40 張測試圖，確認 Android 裝置的
  real/fake/filter 預測結果跟桌機 fp32 TFLite 參考值（`results/mobile_deployment_benchmark.json`，
  golden predictions 待生成，見 `android_benchmark/golden_outputs/README.md`）
  逐張標籤一致（不要求 bit-exact logits——見
  `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` gate 7 自己定義的容忍度）。
- **Latency**：Real path（Layer1-only）、Manipulated path（Layer1+Layer2）、
  端對端（影像解碼＋前處理＋routing＋兩層推論）——分開報告，不要混在一起，
  比照 `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` 既有流程。
- **完整指標集**：mean/p50/p95/max、初始化時間、峰值 RAM、CPU thread 數
  （1／2 threads 為必測，4 threads 選配）、裝置 metadata（廠牌、機型、SoC、
  Android 版本、RAM、電量、熱狀態），以及 500-run 穩定性測試（零 crash、
  last-100 vs first-100 latency 漂移 ≤30%，含降頻備註）。
- **NNAPI／GPU delegate（選配對照組）**：只有在被當成**獨立、清楚標示**的對照組
  時才做，**絕對不能取代 CPU fp32 baseline 作為 acceptance gate 判定依據**——
  依 `android_benchmark/DEVICE_BENCHMARK_PROTOCOL.md` §2。
- **不得用 int8 取代 production benchmark**：int8 TFLite 已確認因 FFT 分支的
  activation 動態範圍問題而失效（`CLAUDE.md` 已記錄根因），只能用 fp32。

**Member C 明確不能碰**：分類器、任何 threshold、routing 公式、任何 checkpoint 內容，
以及把 Android Emulator 的輸出當成實體裝置 latency 使用（Emulator 是跑在開發機自己的
CPU 架構上，不是目標裝置——`android_benchmark/README.md` 已明確提醒）。

---

## F. 團隊共同、不可協商的規則

1. **絕不覆寫既有結果。** 每個新實驗都寫進新資料夾。
2. **輸出路徑必須包含日期＋任務編號＋模型版本**（例如
   `results/research/p1_r3_0_scale_normalized_generator_<date>/`），沿用
   `p1_r1_cross_source_failure_anatomy_20260814/`、
   `p1_r1_5_resolution_causal_audit_20260814/`、
   `filter_data_xai_provenance_audit_20260814/` 已建立的慣例。
3. **禁止在沒有明確指定 checkpoint 路徑的情況下跑評測。** 這不是新規則——正是
   P0 Production Evaluation Integrity Repair 的教訓：曾有 4 支腳本靜默地退回到已淘汰的
   checkpoint。任何新的評測腳本都必須把 checkpoint 路徑列為必填參數，未提供就要
   fail closed。
4. **新 checkpoint 必須附 SHA256＋訓練 manifest＋split manifest**，即使停留在研究層級——
   比照 `docs/releases/v8.11_production/` 與本次協作各研究輪次已經在用的標準。
5. **`splits/v815_replication_set.tsv`（DF40-cdf replication set）絕對不能被任何人用於
   訓練或 threshold 選擇**，任何 checkpoint 都一樣——它的價值就在於被真正held-out；這條
   規則其實已隱含存在（manifest 自己的 `used_in_v815_training` 欄位在追蹤這件事），
   這裡重申為團隊硬規則，不是逐次實驗自行決定的事。
6. **Production pipeline 的變更需要團隊審查**——見 `PRODUCTION_CHANGE_CONTROL.md`。
7. **任何外部 filter type／region 主張都需要事先做過外部驗證**——依
   `results/phase2/filter_data_xai_provenance_audit_20260814/FILTER_XAI_CLAIM_MATRIX.md`，
   對 RetouchingFFHQ（或任何其他外部）來源的圖片，未取得該特定來源的驗證 accuracy
   數字前，不得產生 exact-type 或 region-level 主張。
8. **Fake 的 Grad-CAM 絕不能被稱為「manipulation mask」。** 目前的 fake 訓練來源沒有
   任何官方／配對的 ground truth；Grad-CAM++ 熱圖對 fake 而言頂多是 attention
   視覺化——呼應 `docs/phase2_story.md` §8 已定案的 Tier C 政策。
9. **Android latency 只能來自實體裝置。** Emulator 數字可以用來抓 build/crash 問題，
   絕不可回報成 latency/RAM 量測結果。
10. **每個實驗都要寫 claim / non-claim**——沿用 `docs/EXPERIMENT_REGISTRY.md` 與本次
    協作各研究 findings 文件已經在用的格式。
11. **無法確認的產出物要標記 UNVERIFIABLE**，不要悄悄省略或用猜的——比照
    `docs/releases/v8.11_production/ORPHAN_AND_UNVERIFIABLE_REGISTER.md` 已經在用的標準。

