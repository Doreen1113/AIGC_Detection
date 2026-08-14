# v8.11 Production — 能力邊界說明 (Release Boundary)

> 本文件回答：v8.11 能宣稱做什麼、不能宣稱做什麼、每項測試屬於哪一種評測性質、以及
> 為什麼 v8.12-v8.16 不能取代 v8.11 成為 production。純文字說明，不含任何本文件自行
> 計算的新數字——所有數字皆引用自 `RELEASE_RESULTS.md`（已逐項核實 provenance，
> 2026-08-13 P0 repair 後為單一官方數字來源）。

## 一句話定位

**v8.11d（Layer1d + Layer2 v811）是一個已凍結（frozen）的靜態單張人臉圖片研究基準
（static-image research baseline），不是通用、跨資料集、或影片 deepfake 的偵測系統。**
它的能力邊界必須逐項對照下方表格閱讀，不可從「production」這個字面推論出「什麼情境都
可靠」。Shadow 43.5%、fake+filter 3.71% 這兩項是**已知、已記錄在案的限制**，不是本輪
評測誠信修復（P0 repair）之後才發現、也沒有被隱藏——它們在 CLAUDE.md／TODO.md 的
Freeze Gate 與 stretch goal 表格中，從 v8.11 一開始被標記至今就是「未達標但不阻擋凍結」
的已知項目。

## v8.11 可以做什麼

- 對**單張靜態人臉圖片**做三分類：real（未修改真實臉孔）／fake（身份替換或合成）／
  filter（身份保留的美化濾鏡：smoothing／whitening／eye_enlarging／face_reshaping）。
- 在 filter 類別下，進一步判斷是哪一種濾鏡子類型（4 選 1 + `unknown_filter` 開集拒判）。
- 對 filter 類別中的 eye_enlarging 提供**區域級**（region-level）Grad-CAM++ 定位解釋，
  對 smoothing／whitening／face_reshaping 提供**全臉級**（whole-face）解釋（非精確定位
  主張——這是刻意的設計決策，見 `pipeline.py` 的 `ARTIFACT_REGION_MAP` 註解）。
- 在**與訓練資料同分布的靜態人臉圖片**上（True Test、CelebA、StyleGAN2 這類 in-distribution
  held-out 或演算法-OOD 測試），達到 Freeze Gate 定義的核心指標門檻（見下方 ID 測試段落）。
- 匯出為 fp32 TFLite（Layer1+Layer2 合計 20.91MB），在桌機 CPU 上決策與 PyTorch 版本
  100% 一致（769/769）。

## v8.11 不可以宣稱做什麼

- **不可宣稱**能可靠泛化到**跨底圖攝影風格**的 filter 偵測（Shadow domain gap 尚未解決，
  paired balanced accuracy 遠低於 True Test，且低於或接近 50% 隨機基線，視 checkpoint
  而定）。
- **不可宣稱** fake+filter 混合情境下的最終誤判率已達安全目標（3.71% 高於原訂 ≤2% 的
  stretch goal，是已知未解決的差距，非隱藏的問題）。
- **不可宣稱**對 FaceForensics++（FF++）或其他影片 deepfake 有可靠偵測能力——Layer1
  有已知的 video/H.264 domain gap，FF++ fake recall 未達到非正式的 ≥70% 參考目標。
- **不可宣稱**跨來源（cross-source）的 `has_filter` 聯合辨識能力——即使是專門為此設計的
  v8.16 research track，也只從 2.02% 改善到 4.53%，遠低於 ≥25% 的參考目標，且部分濾鏡
  類型（whitening／幾何類濾鏡／pixart／sd2.1）「完全無殘留效果」。
- **不可宣稱**支援 int8 量化部署——FFT branch 的動態範圍問題（~7.6×10⁹）已根因分析確認
  會導致 98% 頻譜 bin 崩為零、輸出 NaN，此路徑目前被阻擋。
- **不可宣稱**已完成真實裝置（iPhone）效能驗證——這是 Freeze Gate 中唯一尚未通過的項目，
  目前只有桌機 CPU 的測量數字。
- **不可宣稱** fake 類別有區域級（region-level）定位解釋——目前的 fake 訓練來源
  （AIGuard、DF40 diffusion/EFS）皆為整臉合成、無官方 manipulation mask，fake 的解釋
  維持整體層級（global-level），不做逐區域主張。

## 各項測試的 ID / OOD / Robustness 分類

| 測試 | 分類 | 說明 |
|---|---|---|
| True Test filter recall / AUROC / baseline confusion（`results/eval_v811d_gates.log`、`robustness_eval_v811d.json`） | **ID held-out**（同分布held-out，配對設計） | 影像來源與訓練分布相同（LFW real、DF40 diffusion fake、自建 filter pipeline），但是獨立held-out set，非訓練集切分洩漏 |
| CelebA real recall | **Real OOD** | CelebA 未參與 filter/fake 訓練來源，作為「這是不是真的能辨識任意真人網路照片」的獨立驗證 |
| StyleGAN2 fake recall | **Fake OOD（GAN）** | 與訓練用 DF40 diffusion/EFS 方法完全不同的 GAN 架構，驗證跨演算法 fake 泛化 |
| Alibaba filter OOD | **Filter OOD（跨濾鏡演算法）** | 與訓練用 self-built/Megvii filter pipeline 完全不同公司的濾鏡演算法；v8.11d 的 98.1% 數字已於 2026-08-13 P0 repair 補上存檔結果檔（`results/releases/v8.11_production_20260813/alibaba_filter_ood_v811d_layer2v811_20260813.json`），見 `RELEASE_RESULTS.md` 官方表格 |
| AIGuard/unseen fake AUROC | **Fake OOD（held-out 來源）** | 獨立於訓練集的 fake 來源子集 |
| Shadow domain-gap paired eval（real/filter/fake_gan/fake_diffusion，`eval_v811_layer1d_shadow.log`） | **Robustness stress test（跨底圖攝影風格）** | 刻意設計來測試「同一濾鏡演算法、不同底圖攝影風格」下是否仍成立；這是本專案已知最弱的一環，不是 ID/OOD 意義下的常規測試 |
| Fake+filter 8 種濾鏡強度組合 stress test（`stress_test_v811d_pipeline.log`） | **Robustness stress test（對抗性組合）** | 刻意疊加 fake 圖像與濾鏡效果，測試分類器是否會被濾鏡效果「洗白」成 filter 判定，非常規分布測試 |
| Grad-CAM++ faithfulness（blur-based，`xai_faithfulness_blur_v1_20260813.json`） | **XAI 忠實度測試（非分類準確度測試）** | 測的是熱區是否真的對應模型決策依據，不是分類正確率 |
| FF++ zero-shot（`ffpp_zeroshot_*.tsv`） | **Robustness / 域外壓力測試** | 影片幀來源，H.264 壓縮，已知 domain gap，非 Phase 1 主要宣稱範圍 |

## 為什麼 v8.12–v8.16 不能取代 v8.11（呼應 CLAUDE.md Phase 1 凍結理由）

CLAUDE.md 於 2026-08-13 明確將 Phase 1 凍結為 `Phase1-v8.11-freeze`，理由整理如下：

1. **v8.11 已通過全部 A 類 Freeze Gate 指標**（True Test fake/filter recall、AIGuard-unseen
   AUROC、CelebA/StyleGAN2/Alibaba OOD、fp32 TFLite ≤25MB），唯獨真實裝置實測尚未完成。
2. **v8.12–v8.16 每一版都是為了解決 B 類 stretch goal（不阻擋凍結的目標）而做的研究性
   實驗**，而非修復 A 類 gate 的缺陷：
   - v8.12／v8.13：嘗試改善 Shadow domain gap，但都**讓 fake+filter 誤判率退步**
     （3.71%→5.29%→5.72%），這是安全性相關指標，退步方向錯誤，故不採用。
   - v8.14：route-filtered mining，是「淨正向但不足以晉升」的部分成功——改善了部分
     stress test 條件，但 Shadow real recall 沒有回升，whitening_medium 甚至惡化。
   - v8.15：dual-head 分解式架構 pilot，判定為「誠實負面結果，frozen-backbone 拆 head
     不足」。
   - v8.16：mixed-lineage 跨來源訓練，cross-source joint recognition 有改善但仍遠低於
     目標，且部分濾鏡類型完全無效。
3. **收斂規則明確**：CLAUDE.md 訂下「只有全部 Freeze Gate 不退步、且至少一個 stretch
   goal 有實質改善，才啟動下一輪訓練」——v8.12–v8.16 沒有一版同時滿足這兩個條件
   （幾乎都是「stretch goal 改善但某個 Freeze Gate 級指標退步」的組合），所以沒有一版
   夠格取代 v8.11。
4. **v8.12–v8.16 的正式定位是「論文研究章節證據」**，用於誠實呈現這些方向「已經試過、
   為什麼沒有成功」，而不是候補 production 版本。

## v8.8 歷史 XAI 表 與 v8.11 production XAI 的使用邊界

- **v8.8 歷史 XAI**（`results/xai_comparison_eye_face_white.json`，Grad-CAM++ vs
  region-head 比較研究）：
  - **可以引用**於：說明「為什麼選擇 Grad-CAM++ 而非 region head」這個架構決策的歷史
    依據；作為 v8.11 重新驗證時的**對照基準**（`v88_reference_for_comparison` 欄位）。
  - **不可引用**於：任何聲稱代表當前 production 模型（v8.11）的 XAI 表現數字——v8.8
    是已被取代的 flat 3-class 架構，兩者的 Grad-CAM++ 目標層與模型輸出空間都不同，
    數字不能互換使用。
- **v8.11 production XAI**（`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`
  及其兩份 follow-up：whitening peak diagnostic、blur-based faithfulness test）：
  - **可以引用**於：任何聲稱代表當前 production 模型能力／限制的正式報告或論文章節。
  - 使用時**必須同時揭露** whitening 的 PointingGame 已知問題（0.880→0.357，v8.11
    specific，非 v8.8 就有的問題）以及其根因（近乎常數的熱圖峰值位置偏誤，位置不隨
    圖片內容變化）。

## 明確澄清（2026-08-13 收版重申，避免被誤讀）

- **v8.11d 是已凍結的靜態圖片研究基準，不是通用或跨資料集偵測系統**：所有 Freeze Gate
  數字都是在特定、有限的測試分布上量測（True Test 配對設計、CelebA/StyleGAN2/Alibaba
  三個特定 OOD 來源），不構成「對任意來源的人臉圖片都同等可靠」的宣稱。
- **v8.11d 不是影片 deepfake 偵測器**：FF++ zero-shot 結果未達標（見上表 Robustness /
  域外壓力測試列），Layer1 對 H.264 影片幀有已知 domain gap，這是架構層級的限制，
  不在本輪 P0 repair 或本次收版的處理範圍內。
- **Shadow 43.5% 與 fake+filter 3.71% 是已知、已記錄的限制，不是本次收版才發現的
  沉默缺口（silent gap）**：兩者皆列在 CLAUDE.md 的模型成績單與 TODO.md 的 stretch
  goal 表格中，且皆有專節根因分析（Shadow：跨底圖攝影風格 domain gap，非濾鏡演算法
  泛化問題；fake+filter：Layer2 對「Layer1 放行難樣本」的誤判傾向，見 TODO.md
  「A/B/C/D checkpoint 交叉組合診斷」）。兩者皆列為 stretch goal，依 Freeze Gate
  規則**不阻擋凍結**，但也**不可被引用為「已解決」**。
- **v8.16 跨來源結果是研究專用，不取代 production**：v8.16 mixed-lineage 的
  cross-source `has_filter` joint recognition 從 2.02% 改善到 4.53%，這是**研究進度
  的證據**，不是可部署的改善——`pipeline.py` 從未指向 v8.16，且 v8.16 在多個濾鏡
  類型（whitening／幾何類濾鏡／pixart／sd2.1）上「完全無殘留效果」，尚未達到可取代
  v8.11 production 的門檻（見上方「為什麼 v8.12–v8.16 不能取代 v8.11」）。
- **iPhone 真實裝置的 latency／RAM／穩定性目前完全未驗證**：目前所有效能數字
  （14.4ms/張、20.91MB）都是**桌機 CPU** 上的測量結果，與行動裝置的實際 CPU/NPU、
  記憶體壓力、熱節流（thermal throttling）、電池消耗等條件皆不相同。在真實 iPhone
  裝置上完成量測之前，不可宣稱「已驗證可在手機部署」，只能宣稱「桌機驗證通過、
  裝置驗證待補」。這是目前唯一未通過的 Freeze Gate 項目，見
  `PHASE1_FREEZE_DECISION.md`。
