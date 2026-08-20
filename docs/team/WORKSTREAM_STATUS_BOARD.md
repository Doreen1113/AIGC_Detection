# Workstream Status Board（工作流狀態看板）

> **最後更新：2026-08-20（Member B 全欄位補正）。** 本看板自 2026-08-14 建立後停滯一週，
> 期間 Phase 2 實際進度（Alibaba 外部 benchmark、Phase 2F fake evidence、FF++ Tier D
> Stage 1-5、Status C 核准、v8.17 promotion 後的 Detection Gate 重測）皆未反映。本次已
> 依磁碟上的實際輸出逐項核對後補正 Member B 欄位與 Pending Dependency 的 FF++ 條目；
> Member A／Member C 欄位**未更動**（不代任何成員宣告進度，仍為 8/14 當時狀態）。
>
> 建立於 2026-08-14，2026-08-14 改寫為中文版並納入 Member B 任務範圍修正。看板形式，
> 於每週例會（見 `TEAM_WORK_ALLOCATION.md` §G）開頭更新——本文件由任何成員視狀態變化
> 自行編輯；「Frozen/Completed」欄描述的是本文件建立當下的狀態，之後只能增加內容，
> 不可悄悄改寫既有紀錄。

## Frozen / Completed（已凍結／已完成）

- **v8.11d release** — `docs/releases/v8.11_production/`，`release_status: FROZEN_DESKTOP_VALIDATED`
  （撰寫本文件當下已重新對照 `RELEASE_MANIFEST.json` 確認）。
- **Core / OOD / robustness 評測** — 全部在 P0 Production Evaluation Integrity Repair
  （`results/releases/v8.11_production_20260813/`）中用新鮮、附 hash 的證據重新驗證過。
- **fp32 桌機 TFLite** — 已驗證可載入、與 PyTorch 數值一致（769/769 決策一致），
  合計 20.91 MB（`results/mobile_deployment_benchmark.json`）。fp16 已確認損壞，
  int8 已確認數值不正確——不算「已凍結／完成」，明確標記為不可用。
- **Filter paired-GT XAI** — Tier A 自建框架（`docs/phase2_story.md` §7-8），已在
  production v8.11d checkpoint 上重新驗證過
  （`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`）。
- **Fake 類別（Layer1/fake_head）Grad-CAM++ faithfulness 稽核** — 已確認真實存在且完整，
  透過 `xai_faithfulness_blur_test.py` / `results/xai_faithfulness_blur_v1_20260813.json`：
  在 production v8.11 hierarchical 分類器上，k=5/10/20% 下 hot-region 下降 >
  cold-region 下降 > matched-random 下降。**命名說明**：repo 中找不到任何「Level 1/2」
  這種說法——本項目改用描述性名稱，不套用未經驗證的標籤。搭配的 `filter_head`
  faithfulness test（composite fake+filter 情境）是**另一個、仍未解決**的項目——見
  Known Risks。
- **Release provenance 文件** — `docs/releases/v8.11_production/RELEASE_RESULTS.md`、
  `EVALUATION_INTEGRITY_REPAIR.md`、`PHASE1_FREEZE_DECISION.md`、
  `ORPHAN_AND_UNVERIFIABLE_REGISTER.md`，皆已完成。

## Active — Member A（Phase 1）

- [ ] P1-R3.0 — Scale-normalized 濾鏡生成器校準
- [ ] P1-R3.1 — 小規模 paired cross-resolution 驗證
- [ ] P1-R3.2 — Scale-normalized fake+filter 訓練候選版
- [ ] P1-R3.3 — Held-out DF40-cdf replication 評測
- [ ] Fake+filter cross-source 泛化 — 待 P1-R3.3 結果出爐後重新評估

## Active — Member B（Phase 2）

- [x] Phase 2F — fake per-image evidence 候選特徵驗證 —— **已完成（2026-08-14）**，見
      `results/phase2/fake_evidence_discovery_v811d_20260814/`（候選特徵分類法、
      per-source 指標、candidate decision table）與
      `results/phase2/fake_evidence_resolution_matched_v811d_20260814/`
      （解析度配對後的重測 + regression sensitivity，排除解析度混淆因子）。
      **⚠️ `tex_local_variance_std` 的狀態已改變，本看板與 `TEAM_WORK_ALLOCATION.md` §D
      的舊敘述（「repo 中完全找不到，應視為外部討論中的未驗證候選名稱」）自 2026-08-14
      起已不再成立**：該特徵已被**明確定義並實作**（`fake_evidence_discovery_.../scripts/
      extract_features.py` L283，定義為 5x5 local-variance map 跨畫面的標準差），
      是 24 個候選特徵中**唯一**通過 discovery 輪 direction-consistency 的一個
      （8 個 fake source 方向一致，6/8 AUROC 清 0.60 門檻），並已針對它做過一輪專屬的
      resolution-matched 驗證（Phase 2F-R1）。
      **可宣稱**：在 resolution-only matching + resolution/face-size 校正、含 source
      fixed-effects 的 logistic regression 下，8 個來源中有 7 個仍維持 higher-in-real
      方向的區辨力——足以反駁「原始訊號主要是解析度混淆」。
      **不可宣稱**：最嚴格的 joint_matched（同時控制解析度與臉部尺寸）8 個來源中有 6 個
      資料量不足（caliper 後 n<10），pooled 層級僅方向一致但不顯著（n=64，p=0.11-0.14），
      **無法宣稱聯合混淆已被排除**；`midjourney` 是明確的反例（配對後方向反轉），
      不得併入 pooled 讀數；全程為 n=44-70/來源的描述統計，**不是**訓練驗證過的分類器特徵，
      也**未**接入 `pipeline.py` 任何輸出。原始 findings 自己對 "ACCEPT" 的定義即為
      「僅通過本輪兩項混淆檢查」，不得被引用成更強的結論。
- [x] RetouchingFFHQ single-operation（Alibaba）外部 artifact-type benchmark ——
      **已完成（2026-08-14）**，見
      `results/phase2/external_alibaba_artifact_validation_20260814/`。關鍵結果：
      `Whitening_60`/`_90`（唯一 `VERIFIED_SINGLE_TYPE` 子集）pooled exact-type
      recall = **27.5%（95% CI 23.2-31.8%，n=400）**，對 4-way 分類器 25% 的隨機
      基準而言**與亂猜無統計差異**；12 個資料夾**無一**達到 `EXACT_TYPE_ALLOWED`，
      全部落在 `COARSE_RETOUCH_ONLY`。以下為原始範圍限定說明，保留不改：
      **已收斂範圍（2026-08-14）**：只有 `Whitening_60`/`Whitening_90` 這個
      `VERIFIED_SINGLE_TYPE` 子集可用於計算 exact-type accuracy；其餘 `FFHQ_ali_process`
      資料夾（`EyeEnlarging_*`、`FaceLifting_*`、`Smoothing_*`、`Whitening_30`）一律列為
      `COARSE_OR_MIXED`/`UNVERIFIABLE`，僅可用於 prediction-distribution／overclaim 稽核，
      不得算入 accuracy 指標。**驗證備註**：本次針對 `FFHQ_ali_process/` 的獨立結構複查
      發現，全部 12 個 type 資料夾格式完全相同（各約 3,000 張，皆為
      `<index_block>/<file>.png` 巢狀結構），且**沒有任何一個資料夾**存在類似
      `FFHQ_four_process/four_process.txt` 那種逐圖操作參數 metadata——換句話說，
      `Whitening_60`/`90` 目前被列為 `VERIFIED_SINGLE_TYPE`是**團隊政策選擇**，不是本次
      複查獨立發現的結構性事實。詳見 `TEAM_WORK_ALLOCATION.md` §A/§D。
- [x] 外部 artifact-classifier type 泛化完整拆解 —— **已完成（2026-08-14）**，見
      `results/phase2/external_alibaba_artifact_validation_20260814/`（per-folder、
      per-intensity prediction-distribution 拆解 + `EXTERNAL_ALIBABA_CLAIM_RECOMMENDATION.md`
      的 `COARSE_OR_MIXED`/`UNVERIFIABLE`/`VERIFIED_SINGLE_TYPE` 分級與 per-folder 措辭政策）。
- [x] `unknown_or_mixed_retouch` 輸出類別提案（僅設計，非實作）—— **本輪完成（2026-08-20）**：
      `docs/team/change_proposals/20260820_unknown_mixed_retouch_category_proposal.md`。
      依 `PRODUCTION_CHANGE_CONTROL.md` 八段格式撰寫，**狀態為 PROPOSAL，尚未核准、
      尚未實作**（`pipeline.py`／`artifact_classifier_v3.pth`／`ARTIFACT_REGION_MAP`／
      `TEMPLATES`／`ARTIFACT_UNKNOWN_THRESHOLD`／JSON schema 全部未變動）。核心設計：
      四階 decision ladder（multiplicity → exact-type entitlement → confidence → single
      type），只新增 `mixed_retouch`／`app_processed` 兩個 tag（第三個構想
      `unknown_retouch` 查證後發現 `pipeline.py` 既有的 `unknown_filter` 已完全對應，
      改為釐清角色而非重複實作）；`ARTIFACT_UNKNOWN_THRESHOLD=0.6` **不變動**，並記錄
      它在 OOD 上僅 2-11% 觸發率（平均信心 0.87-0.96），結構上無法承擔新類別的判定。
      待 reviewer 核准 + Member A 確認無 Phase 1 語意衝突。

## Active — Member B（Phase 2，2026-08-20 新增：FF++ Tier D 支線）

> 2026-08-14 建立的上方 Member B 清單一週未更新；以下為 8/14 之後實際發生、
> 但原清單沒有欄位可記錄的工作。

- [x] FF++ 官方 mask 定位驗證 Stage 1-5（Phase2-FFPP）—— 完成，含兩次自我糾錯
      （撤回不具鑑別力的 Pointing Game 證據、修正 Stage 3 前處理不一致後 B2 重跑）。
      見 `results/phase2/ffpp_mask_verified_localization_20260818/`、
      `.../ffpp_mask_verified_localization_B2_20260819/`、
      `.../ffpp_full_set_recall_reconciliation_20260819/`。
- [x] Fake XAI Status C（Tier D）claim policy 升級提案 —— **2026-08-20 核准**，範圍
      3 個 method（Deepfakes 77.3% / FaceSwap 68.0% / NeuralTextures 72.5%），
      Face2Face 因 56.7% < 60% 門檻排除。已套用於 `docs/phase2_story.md` §8；
      `pipeline.py` 未變更。見
      `docs/team/change_proposals/20260819_fake_xai_status_c_upgrade_ffpp.md`。
- [x] **FF++ Detection Gate 在新 production Layer1（v8.17/SBIAUG）下重測** ——
      本輪完成（2026-08-20），**Face2Face 翻盤：56.7% → 68.0%，判定為 ELIGIBLE**；
      四個 method 全數改善 8-11pp，無任何退步。決策規則於讀取結果前已寫入
      `PRE_DECLARED_PROTOCOL.md`；v811d 對照組逐一重現既有 B2 數字（116/85/102/108）。
      依預先聲明的規則觸發 Face2Face 專屬 Stage 4/4b：IoU@10%=0.334（與 3 個已核准
      method 同一區間），faithfulness 3/3 k 全通過（比已核准的 FaceSwap 更嚴格，後者
      k=5% 不顯著）。見 `results/phase2/ffpp_detection_gate_v817sbi_20260820/`。
- [ ] **（待送審，非本輪授權）** 依上一項證據，把 Face2Face 加入 Status C / Tier D
      的 change proposal —— 需另走一輪 change control，Member B 無權自行核准。
- [ ] **（待 reviewer 裁決）** 已核准的 3 個 method 的 Stage 4/4b IoU/faithfulness
      數字是用 **v811d 挑出的子母體**算的，而 v811d 已非上線 checkpoint（各 method
      子母體在 v817sbi 下 +14～+17 支影片）。detection 基礎在 v817sbi 下只更好、
      不會造成 overclaim，故本輪**刻意未重跑**，改為呈報 change control 裁決。

## Active — Member C（Deployment）

> **2026-08-14 平台更正**：Member C 使用的是 **Android** 裝置，不是 iPhone。以下項目
> 已對應調整；原本以 iOS/Xcode/Swift 為前提的內容已被 `android_benchmark/` 取代，
> 見 `ios_benchmark/DEPRECATED_SEE_ANDROID.md`。

- [ ] Android TFLite/LiteRT benchmark harness：從 `android_benchmark/app_stub/` 實作
      Android Studio 專案
- [ ] 實體 Android 裝置 provision（USB 偵錯）與測試素材裝箱
- [ ] Production composite-probability routing 規則實作（非 strict-gate 近似版）作為
      benchmark 主要路徑（見 `android_benchmark/PRODUCTION_ROUTING_SPEC.md`）
- [ ] 完整指標量測：latency（Layer1-only／Layer1+Layer2／端對端）、初始化時間、
      峰值 RAM、500-run 穩定性、golden-output parity、CPU thread 數對照
- [ ] （選配）NNAPI／GPU delegate 對照組——不得取代 CPU fp32 baseline

## Pending Dependency（等待外部依賴）

- **Android Studio + 實體 Android 裝置 + USB 偵錯** — 卡住 Member C 全部進行中項目；
  本專案先前任何工作都無法從 Windows 端滿足這個依賴（`android_benchmark/README.md`
  已詳盡確認）。
- ~~**FF++ masks／可信的 fake manipulation mask**~~ —— **依賴已於 2026-08-18～08-20 解除**
  （原文保留於下方，不改寫既有紀錄）。解除情形：(1) FF++ 官方 mask 已取得並驗證
  非 degenerate（`results/phase2/ffpp_mask_verified_localization_20260818/MASK_INVENTORY.md`，
  4/4 method，frame-mask 配對 PAIRED_OK ≥99.3%）；(2) Layer1 對 FF++ 的 fake recall
  在新 production checkpoint（v8.17/SBIAUG）下為 **68.0-86.0%（4/4 method 全數
  ≥60% detection gate）**，見 `results/phase2/ffpp_detection_gate_v817sbi_20260820/`。
  Tier D 已正式啟用，3 個 method 的 GT-backed localization 措辭已核准
  （`docs/phase2_story.md` §8）；Face2Face 的加入待另一輪 change control。
  **原始條目（2026-08-14 撰寫，已不再成立，保留供對照）**：卡住任何未來的 fake-class
  region-level XAI 工作；依 `docs/phase2_story.md` §11 明確標記為 `pending`
  （非暫停、非放棄），解除條件是 (1) 取得 FF++ masks，(2) Layer1 對 FF++ 來源達到
  fake-recall stretch goal（目前未達）。
- **RetouchingFFHQ single-operation 資料取得** — Alibaba（`FFHQ_ali_process`）已存在
  於本地，**不會**卡住 Member B 上面的 Phase 2 benchmark 項目；這條依賴特指
  Tencent（RetouchingFFHQ 第三家公司），目前仍未取得（申請未核准，見
  `docs/Dataset 清單.md`），卡住的是未來的三家公司對照研究，不是目前的
  Alibaba 單一公司 benchmark。

## Known Risks（已知風險）

- **外部 artifact classifier 自信但錯誤的預測** — `artifact_classifier_v3` 對任何外部
  來源都沒有已驗證的 accuracy；一個「自信但錯誤」的 type 預測目前可能不經標記就直接
  進入使用者可見的樣板句子。HIGH 嚴重度，依
  `results/phase2/filter_data_xai_provenance_audit_20260814/EXTERNAL_FILTER_XAI_RISK_REGISTER.md`。
- **Fake+filter cross-source joint recognition 偏低** — 即使經過 v8.16 介入，
  也只從 2.02%→4.53%；遠低於任何可用門檻。已診斷（P1-R1/P1-R1.5），尚未修復。
- **Shadow domain gap** — 換一種底圖攝影風格（VGGFace2 base 的 Shadow set），
  filter 偵測大幅退步（paired balanced accuracy 43.5% vs. True Test 的 81.1%）；
  已根因為攝影風格 domain gap，不是濾鏡演算法泛化問題，但尚未解決。
- **StyleGAN2 translation instability** — 專案先前紀錄中列為未解決項目；撰寫本文件時
  未獨立重新驗證——沿用既有專案追蹤紀錄，狀態視為 UNVERIFIABLE，待重新確認。
- **int8 FFT collapse** — FFT branch 動態範圍高達約 7.6×10⁹，會讓 per-tensor int8
  量化失效（98% 頻譜 bin 崩為零、輸出 NaN）；已根因分析，目前卡住任何 int8 手機部署路徑。
- **`filter_head` faithfulness test 混淆因子** — blur-based masking 本身很像
  smoothing 操作，導致該濾鏡型別在 composite fake+filter 圖片上的 faithfulness test
  失效（`docs/phase2_story.md` §9）。屬於尚未解決的方法論缺口，不是已測過的
  pass 或 fail。

## Future Research（未來研究方向）

- Fake+filter cross-source 泛化的 source disentanglement／invariance 機制 ——
  **有條件**，僅在 Member A 的 scale-normalization 工作後仍殘留落差時才考慮。
- 以 FF++ 為基礎的 fake region-level XAI — 卡在 masks ＋ Layer1 FF++ recall
  stretch goal。
- NNAPI／GPU delegate 作為 Android 替代 runtime（相對於 CPU fp32 baseline）——
  本專案從未嘗試／驗證過；任何來自它們的數字在被信任前，都需要自己的一輪 G1-G4
  式數值驗證，且只能當對照組，不能取代 CPU baseline。
- 針對 RetouchingFFHQ four_process 風格資料的 multi-label／mixed-retouch 建模 ——
  下游於 Member B 的 `unknown_or_mixed_retouch` 提案，尚未開始。
- Tencent RetouchingFFHQ 取得 — 申請未核准，若取得可解鎖真正的三家公司外部對照研究。
