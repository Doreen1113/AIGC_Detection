# Workstream Status Board（工作流狀態看板）

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

- [ ] Phase 2F — fake per-image evidence 候選特徵驗證（包括先明確定義、再驗證任何類似
      `tex_local_variance_std` 這種名稱的特徵——**撰寫本看板當下 repo 中找不到**，
      必須從零開始定義）
- [ ] RetouchingFFHQ single-operation（Alibaba）外部 artifact-type benchmark ——
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
- [ ] 外部 artifact-classifier type 泛化完整拆解
- [ ] `unknown_or_mixed_retouch` 輸出類別提案（僅設計，非實作）

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
- **FF++ masks／可信的 fake manipulation mask** — 卡住任何未來的 fake-class
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
