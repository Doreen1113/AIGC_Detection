# TODO

> 完成立刻打 `[x]`；新 TODO 立刻加入。這份檔案是全專案 TODO 的唯一彙整（整合自舊 TODO 區塊 + 2026-07-31 session 新發現）。

## 📌 全部未解決問題總覽（2026-08-10 盤點，共28項，依主題分類）

> 這是掃描全文件所有未打勾（`[ ]`）項目的索引，每項只列一行摘要+關鍵字，完整說明在文件對應章節（用關鍵字 Ctrl+F 可找到）。組員分工的兩個任務（手機端FFT相容性、Layer 2瓶頸）已在下方獨立成節，此處不重複列出。

**Phase 1 收尾／驗收關卡**
- [ ] DF40官方test split外部benchmark 尚未執行（v8.11候選確定後才做，見「E2｜外部Benchmark」）
- [ ] Ultimate Held-out Test Set 持續暫緩解封，直到v8.11通過完整驗收（含DF40 benchmark）

**論文寫作任務（純寫作，成本低）**
- [ ] True Test contamination bias 需在論文Limitations明確標註（v7+選型曾參考此結果）
- [ ] Alibaba OOD confound排除實驗：找confound-free對照組驗證100%是否為shortcut（需新資料來源，成本較高）
- [ ] StyleGAN3 identity-overlap / VGGFace2-filter algorithm-overlap 雙重限制需在Limitations對稱呈現

**Region Head / FakeVLM 標籤問題**
- [ ] FakeVLM cheek標籤稀疏問題未解決（重新設計prompt，或誠實揭露此限制二選一）
- [ ] region_head_v3.pth 未達部署標準，pipeline.py `REGION_HEAD_PATH` 仍指向v1
- [ ] FakeVLM pseudo-label noise 尚未量化（人工抽樣驗證teacher標籤品質）

**Landmark GT / XAI 相關**（⚠️ 以下兩項內容疑似已被後續完成的工作取代，需確認是否該補打勾）
- [ ] Landmark Displacement GT pipeline 藍圖（條目本身可能已被下方「🧩 Phase 2」章節的完成項取代）
- [ ] 用landmark displacement GT + IINC評估Grad-CAM/region head定位品質（同上，可能已被實際執行的XAI評估取代）
- [ ] XAI論文Discussion段落尚未正式撰寫（數字已齊全，只差寫作）
- [ ] Filter region mapping 需在論文中包裝為「解剖學先驗引導」設計決策
- [ ] XAI評估的協定/函式已就緒，`compare_methods()`是否已對region_head_v4完整跑過需確認（可能已完成，條目未同步打勾）
- [ ] Filter解釋性論文claim改寫：eye_enlarging用region-level，其餘三種改whole-face
- [ ] Fake解釋性論文claim撰寫：global-level explanation文字

**Filter 域泛化研究（C1，Bonus，主線穩定後再開）**
- [ ] Shadow filter domain gap診斷（VGGFace2底圖風格 vs 訓練filter來源的分布差異）
- [ ] 擴充filter訓練來源（RetouchingFFHQ原始資料當主來源，VGGFace2 pipeline降級為補充）
- [ ] 驗證擴充來源後Shadow filter recall能否提升（40-50%目標，否則寫入Limitations）

**Open-set 行為設計（C2，低成本）**
- [ ] `unknown_filter` 類別設計（信心閾值，低於門檻輸出unknown）
- [ ] Unseen filter/fake資料集上的open-set評估（precision/recall/coverage三指標）

**文獻對照實驗（E，成本較高）**
- [ ] 跑FF++ benchmark（與文獻SOTA直接可比較的數字）
- [ ] RetouchingFFHQ MAM頭對頭比較實驗（量化「輕量替代」主張）
- [ ] 查證FF++/SBI/MLFF+CNN/FAME等文獻數字（目前皆未驗證）

**StyleGAN3身份重疊後續（F，低成本可選）**
- [ ] 官方NVIDIA StyleGAN3 pretrained checkpoint + random latent零身份依賴驗證集
- [ ] （大型/獨立專案）Identity-disjoint retrain：DF40全部方法依1,028 identity切分重訓

**外部資源申請（G，使用者行動項）**
- [ ] Tencent RetouchingFFHQ子集申請（[申請表](https://fdmas.github.io/Application_RetouchingFFHQ_new.pdf)）

**其他低優先**
- [ ] 2×2或3×2 ablation matrix（spatial-only vs spatial+FFT × hard_neg強度 × class weight）
- [ ] DF40 Face Editing (FE) 歸類決策（語義偏filter，若加入需重新確認標籤）
- [ ] H.264 domain gap進階：Wavelet Transform取代FFT branch（架構改動大）

---


>  `dev` 分支後，`splits/`、`shufflenet_v2_layer1_v811c.pth`、`shufflenet_v2_layer2_v811.pth` 已一併推送，可直接用來 fine-tune，不用從頭訓練。

### 任務一：手機端 FFT 分支相容性問題（新發現）

- **現況**：模型可以轉出 TFLite 檔案，但**實際載入直接報錯，完全跑不起來**：
  ```
  RuntimeError: Encountered unresolved custom op: ONNX_DFT.
  ```
  根因：`FFTBranch` 用 `torch.fft.fft2`/`fftshift`，轉 ONNX 再轉 TFLite 時被標記成 custom op，標準 TFLite runtime（實際手機App會用的執行環境）不認得這個算子，直接拒絕載入模型。
- **意義**：目前整個 DualBranchModel 架構，不管參數量再怎麼壓縮，理論上都無法真的部署到手機，這是結構性架構問題，不是調參數能解決的。
- **要解決的問題**：FFT 分支要嘛重新設計成 TFLite 原生支援的運算方式，要嘛想辦法讓它在手機上能跑。
- **可能方法方向**（供評估，非唯一解）：
  1. 把 `torch.fft.fft2` 換成矩陣乘法手動實作 DFT（固定尺寸輸入下，DFT可表示成固定矩陣乘法，TFLite原生支援）
  2. 做一個「無FFT分支」的手機專用版本，只用spatial branch，犧牲部分精度換取真能部署，跟桌機版分開維護
  3. 研究TFLite的Select TF ops / Flex delegate機制，把TF版DFT算子塞進手機runtime（風險：App體積變大、部分手機不支援）
- **素材**：
  - `pipeline.py` 的 `FFTBranch` 類別（第93-111行）是要動手的地方
  - `measure_mobile_memory.py`（已包含ONNX匯出+TFLite轉換+載入測試完整流程，可直接當起點）
  - 環境需求：`onnx`、`onnxruntime`、`onnxscript`、`onnx2tf`、`tensorflow`

### 任務二：Layer 2（fake vs filter）辨識瓶頸

- **現況**：Layer 2 的filter recall卡在15.7%-28.1%，多輪嘗試無實質突破：
  | 嘗試 | 結果 |
  |---|---|
  | Layer2b（降oversample+加權） | filter recall 22.4%，但fake_diffusion recall退步9.6pp |
  | Layer2c（更保守加權） | filter recall 21.0%，同樣無淨改善 |
  | 原始Layer2（無手動加權，目前部署版） | filter recall 15.7% |
- **已知根因**：訓練資料裡hard negative（fake+filter邊界樣本）比例拉高，模型會把決策邊界推向「fake」，犧牲對真正filter class的辨識力——純調loss weighting/oversample比例已證實無效。
- **2026-08-10新發現線索**：v8.11壓力測試顯示，fake套濾鏡後的誤判**不是均勻分布在所有濾鏡類型**，而是集中在3種，且誤判方向幾乎都是「誤判成real」：
  | 濾鏡類型 | 誤判率 | 誤判方向 |
  |---|---|---|
  | whitening | 13.2%（最差） | 幾乎全部→real |
  | eye_enlarging | 9.8% | 幾乎全部→real |
  | face_reshaping | 9.1% | →real為主 |
  | smoothing系列 | <1.5%（很穩） | — |
  建議下一輪不要對所有filter類型平均施力，**針對whitening/eye_enlarging/face_reshaping這三種類型加強hard negative挖礦**。
- **要解決的問題**：在不犧牲real recall跟fake_diffusion recall的前提下拉高filter recall，且要能通過完整7項gate評估才能取代目前v8.11。
- **素材**：
  - `results/stress_test_v811_pipeline.json`（原始壓力測試資料）
  - `generate_fake_filter_misclass_chart.py`（分析腳本，可直接跑或改）
  - `AIGuard/train_v811_layer2.py`、`train_v811_layer2b.py`、`train_v811_layer2c.py`（過去三次嘗試，避免重複）
  - `splits/v811_layer2_train.txt` 及變體

---

## 🚨 最高優先（v8.11 Hierarchical Classifier，Ultimate 暫緩解封）

> v8.9（real擴充）/v8.10（real+filter擴充+dose-response）系列已結案：三條獨立路線都證實 real/fake/filter 共用同一softmax空間存在結構性Pareto trade-off，資料層面調整無法同時達標，正式轉向架構改動。完整歷史見下方「已解決」與 `docs/Dataset 清單.md`。

- [x] **v8.11 Layer1（real vs manipulated二分類）3輪迭代**：Layer1（無mining，leak 6.25%/real 77.6%）→Layer1b（+1,050張round1 mined，leak 5.11%/real 77.2%）→Layer1c（+303張round2 mined，leak 3.93%/real 75.5%）。real recall代價可控（僅-2.1pp，遠低於三分類時期10+pp翹翹板），證實hierarchical拆分讓real/manipulated邊界與fake/filter邊界解耦
- [x] **v8.11 Layer2（fake vs filter二分類）第一版**：15x oversample hard core（佔訓練13.9%）導致filter recall崩潰至15.7%、AUROC≈0.5（幾乎隨機）；端到端pipeline（Layer1c+Layer2）fake+filter誤判3.93%，與Layer1c洩漏率完全相同（Layer2對此測試集無淨貢獻）；仍未追平v8.8的1.35%
- [x] **Layer2b calibration 跑完，目標已依實驗結果修正**：oversample 15x→5x + filter class weight×2.5，5 epochs。**修正後的目標描述**：先確認oversample/class weight是否能讓filter recall回到接近v8.8/v8.10a基準（20-30%區間），若仍明顯低於這個區間，判定問題在於domain gap而非sampler——**結果：filter recall僅15.7%→22.4%（仍略低於基準區間下緣），且fake_diffusion recall倒退69.4%→59.8%，判定為domain gap主導，非單純sampler問題**
- [x] **Gate框定調整（2026-08-02拍板）**：Shadow filter recall從「必須過的P0 gate（≥70%）」重新定位為「robustness stress test / OOD benchmark」，不再是部署阻斷條件。原因：v8.8（未受任何v8.11改動汙染的原始3-class模型）shadow filter recall僅26.3%，v8.10a（filter完全未變）也僅28.1%——這個瓶頸從Phase 1一開始就存在，是「VGGFace2+自建filter pipeline」這個特定OOD來源的域泛化難題，不是v8.11架構或Layer2 hard_neg新引入的問題。**後續影響**：Phase 1主gate維持True Test filter recall（≥92%，訓練分布內filter偵測能力）、fake+filter誤判（≤2%）、Shadow real recall、AIGuard/unseen AUROC等；Shadow filter角色改為「專門測試VGGFace2+自建filter pipeline這個OOD domain」，數字（22-28%區間）誠實報告+分析原因，寫入論文Limitations/Future Work（見C1章節），不作為deployment blocker。此定位已同步寫入 `docs/Dataset 清單.md` 對應summary，兩份文件一致
- [x] **Layer2c（溫和校正）跑完，結論：calibration net-negative，鎖定原始Layer2**：oversample 2x + filter weight×1.5，8 epochs。結果shadow filter 21.0%（與Layer2b的22.4%接近，calibration強度不敏感）、fake_diffusion 60.5%（仍比原始Layer2低8.9pp）、**end-to-end fake+filter誤判4.33%，比不加任何手動權重的原始Layer2（3.93%）更差**。**拍板：v8.11 Phase 1候選正式鎖定為Layer1c + 原始Layer2（無手動加權，15x oversample），不再繼續Layer2 calibration**——手動filter class weight對filter recall邊際貢獻小且不敏感倍率，卻穩定犧牲fake_diffusion recall，在最關鍵的end-to-end生產指標上net-negative
- [x] **v8.11完整7項gate評估跑完**（Layer1c + 原始Layer2）：True Test 94.0%✅、AIGuard/unseen AUROC 0.8112✅（全系列最佳等級）、CelebA 99.7%✅、StyleGAN2 99.7%✅——**6項硬性gate中4項過關**（2026-08-02複查修正，原記錄誤寫5項），僅Shadow real（75.5%，差4.5pp）與fake+filter（3.93%，差1.93pp）未達標，但兩者皆遠優於三分類時期任何中間版本。完整對照表見 `docs/Dataset 清單.md`
- [x] **✅ 2026-08-02 拍板：v8.11正式定為Phase 1最終候選，Phase 1收尾，轉入Phase 2**：接受fake+filter 1.35%→3.93%的trade-off，換取real recall 16.2%→75.5%、AIGuard/unseen AUROC 0.7043→0.8112的巨幅進步。定位：v8.11（Layer1c+原始Layer2）用於主要deployment場景；v8.8保留為「高安全性/低誤判優先」場景的reference baseline，論文中誠實呈現兩者trade-off，不繼續在Phase 1砸算力硬壓fake+filter至≤2%（過去v8.9/v8.10/v8.11三條路線的邊際效益已證實遞減）
- [x] **Phase 1 論文骨架草稿完成**：`docs/phase1_story.md`——完整敘事結構（問題陳述→假設與方法→結果→誠實揭露Layer2殘留的資料比例效應→trade-off陳述），含可直接用於論文Discussion的英文段落草稿，整理v8.8→v8.9d→v8.10a→v8.11演進表格與折線圖對應說明
- [x] **Phase 2 論文骨架草稿完成**：`docs/phase2_story.md`——對應Phase 1骨架的Phase 2版本，完整敘事結構（問題陳述→v1-v3 label degeneracy診斷→Landmark GT建構與校準→region_head_v4 trivial baseline驗證→四方法系統性對照核心發現→Discussion定位），含可直接用於論文的英文Discussion段落，定位為「建立誠實XAI評估方法論、得出反直覺但站得住腳結論」的研究貢獻
- [x] **✅ 2026-08-02 正式論文骨架完成**：`docs/paper_outline.md`——把phase1_story.md/phase2_story.md併入Intro→Related Work→Methods→Results→Discussion→Limitations正式論文章節結構，並明確標記所有**[GAP]**（目前缺數字/待補的具體位置），核心結論：**唯一重大GAP是外部benchmark（DF40/FF++），其餘章節素材（敘事、gate對照表、XAI對照表、視覺化圖、pipeline demo、limitations文字）皆已就緒可直接使用**。依用戶指示的順序邏輯：先寫框架標出缺口→再依缺口精準設計DF40 benchmark，不要順序顛倒（避免先跑一堆benchmark數字，寫作時才發現subset選錯/跟敘事對不上要重跑）
- [ ] **下一步（Track C核心待辦）**：依`docs/paper_outline.md`標記的GAP，設計並執行DF40官方test split benchmark（見E2章節既有規劃：subset選擇、baseline數字查證、報告指標格式與現有gate表一致）
- [x] **✅ 2026-08-02 pipeline.py正式接上v8.11（Layer1c+Layer2雙模型串接推論）**：新增`hierarchical_predict()`函式統一封裝兩階段推論，對外輸出格式與v8.8舊版完全相容（`prediction`/`confidence`/`class_probs`欄位不變，新增`model_version`欄位標示版本）。class_probs為真實複合機率分布（P(real)=L1.P(real)；P(fake)=L1.P(manip)×L2.P(fake)；P(filter)=L1.P(manip)×L2.P(filter)，三者相加=1，可與舊版v8.8輸出直接比較）。Grad-CAM++依最終決策層動態選擇（real預測→Layer1的real類別；fake/filter預測→Layer2對應類別），artifact classifier + region head + explanation template全部沿用不變。
  - **驗證**：單張圖片模式與資料夾批次模式皆測試通過；抽測20張AIGuard/real圖片得15/20=75%正確率，與本session稍早獨立測得的shadow real recall（75.5%）一致，證實接線正確、無重複計算或模型載入錯誤等整合bug
  - 舊版v8.8單模型權重（`shufflenet_v2_3class_v88.pth`）保留在磁碟供對照，不再是pipeline.py預設路徑
- [x] **✅ 2026-08-02 移除pipeline.py裡的FakeVLM region head，讓現役系統跟Phase 2結論一致**（不再是「工程pipeline裡偷偷留著已知失敗路線」）：
  - 完全刪除`RegionHead`類別、`predict_regions()`函式、`region_head`參數與載入邏輯；fake class的`suspicious_regions`固定回傳`[]`，explanation改為`TEMPLATES["ai_generated"]`固定的global-level句子（不再列6個region名字），對應論文claim「fake explainability is global-level, heuristic」
  - `ARTIFACT_REGION_MAP`：`eye_enlarging`保留`["left_eye","right_eye"]`（唯一有region-level GT支持的類型）；`whitening`/`smoothing`/`face_reshaping`全部改成`["face"]`（whole-face marker），對應template文字同步改為「across the face」「spanning the whole face」等全臉語氣，不再列出3-4個具體region名字
  - 驗證：eye_enlarging/whitening/smoothing/face_reshaping/fake五種情境全部重跑，explanation文字與suspicious_regions輸出符合預期
- [x] **✅ 2026-08-02 GT（LAB diff）vs Grad-CAM++對照圖（debug/論文figure）**：`generate_gt_vs_gradcam_figures.py`，`results/gt_vs_gradcam/gt_vs_gradcam_{eye_enlarging,whitening}.png`，各2張樣本。視覺化直接佐證pipeline新設計：eye_enlarging的LAB diff GT清楚集中在雙眼，whitening的LAB diff GT完整填滿整個臉部橢圓——與新的`ARTIFACT_REGION_MAP`（eye_enlarging保留雙眼region、whitening改whole-face）設計完全吻合，可直接當論文Figure使用
- [x] **✅ 2026-08-02 demo composite圖更新**：`generate_demo_composites.py`重跑，`results/pipeline_demo/demo_{real,fake,filter}.png`，fake案例的explanation現在正確顯示為global-level句子（不再假裝有region定位）
- [ ] **DF40官方test split外部benchmark**（v8.11候選確定後執行，見E2章節）
- [ ] **持續：不要解封 Ultimate Held-out Test Set**，直到v8.11通過完整驗收流程（含DF40 benchmark）

## 🔒 Ultimate Held-out Test Set（本次 session 主線，2026-07-31）

- [x] 確認 Real 來源：VGGFace2 test split（Kaggle greatgamedota/vggface2-test，原始解析度）
- [x] 確認 Fake-GAN 來源：DF40 版 StyleGAN3（`Downloads/StyleGAN3.zip`，從未解壓的封存資料）
- [x] 確認 Fake-Diffusion 來源：DiffusionFace DiffSwap（Zenodo 10865300）
- [x] 下載 + 抽樣 VGGFace2（300→補抽至500→清洗後 275 張）
- [x] 解壓 + 抽樣 StyleGAN3 cdf 子集（300→清洗後 219 張）
- [x] 下載 + 抽樣 DiffSwap.tar（300→清洗後 289 張）
- [x] 發現並記錄 StyleGAN3 identity 重疊問題（與 SiT/DiT/ddim/pixart 共用 1,028 個 Celeb-DF/FF++ identity，100% overlap）
- [x] StyleGAN3 降級命名為「unseen-generator, seen-identity」，記入 docs/Dataset 清單.md
- [x] Filter 來源確認：Tencent RetouchingFFHQ 需正式申請，過去申請未核准；改用自建 filter pipeline 套用於 VGGFace2 真實照片
- [x] 生成 VGGFace2 filter 測試集（273→清洗後 269 張，4 類型平均分布）
- [x] Filter 降級標註為「unseen-identity, seen-algorithm」
- [x] MD5 全面查重（比對 788,881 張既有 pool，0 真實重複）
- [x] 100% 人工雙重審查（人工檢查 kept 資料夾，刪除不合格圖片）
- [x] 產出 `splits/ultimate_clean_test.txt`（1,052 張，3-class：real 275/fake 508/filter 269）
- [x] **pHash 近似重複查重**：全 756,996 張既有 pool 掃完，寬鬆閾值（d≤6）1,086 筆命中，但嚴格範圍（d≤3）僅 18 筆，且全部是 StyleGAN3 對到 DiT/pixart/SiT（已知身份重疊，非新問題）；VGGFace2、DiffSwap 在 d≤3 零命中；抽查多組 d≤6 案例（含最可疑的 VGGFace2↔LFW Kamal_Kharrazi 撞名案例）皆視覺確認為不同人，屬 pHash 對人像構圖的系統性誤報，非真實重複
- [x] **封存 `splits/ultimate_clean_test.txt`**：MD5+pHash 雙重查重通過，Lockbox 規則生效——論文定稿前不得評估此測試集；若因 bug 被迫重跑，須降級為 Dev-Test 並重新抽一組全新資料

## 📋 資料集/文件維護（今日完成）

- [x] `docs/dataset.md` 重寫對齊 v8.8 現況（原文件停留在約 v8.1，含多項已知過時/錯誤資訊）
- [x] IINC 公式修正並記入 `docs/Dataset 清單.md`（先前引用版本因編碼問題顯示錯誤）
- [x] 讀完 `docs/research_log.md` 全文，補齊對過去實驗歷程的理解
- [x] 更正先前錯誤陳述：「H.264 domain gap 沒人動過」→ 實際上 v8.2 已嘗試（Celeb-DF-v2 real 加入訓練），因代價過大（filter/whitening/FakeClue/unseen 全面下降）未採用

## A｜Eval 方法論 & 資料完整性（Phase 1 收尾）

- [x] 建立乾淨靜態圖 held-out 主評集 → **Ultimate Held-out Test Set 已封存**（2026-07-31）
- [x] Celeb-DF-v2 定位修正：CLAUDE.md/docs/dataset.md/docs/Dataset 清單.md 三份文件核對一致，皆已移出主評表
- [x] DF40 train/test split 確認：code review + 實測 v88_train_real_fake.txt 與 truetest_fake.txt 0 重疊（15,000 DF40 rows 全數乾淨）
- [x] hard_neg 生成腳本補顯式 truetest 排除防呆：`generate_fake_filter_hard_neg.py` 已加 `_load_truetest_exclusion()`
- [x] EFS 訓練政策完整文件化：完整理由（Phase1可用/Phase2不可用的任務粒度差異）已寫入 docs/Dataset 清單.md
- [x] MidJourney 訓練風險評估：`AIGuard/eval_midjourney_risk.py` 實測，v8.8 對 632 張 MidJourney/fake 100% 正確判為 fake，P(real) mean=0.033，無 CelebA-style shortcut 風險，結論已寫入 docs/Dataset 清單.md
- [ ] True Test contamination bias 標記：需在論文 Limitations 明確標註 v7+ 選型曾參考此結果（純寫作任務，待論文草稿開始時處理）
- [ ] Alibaba OOD confound 排除實驗：找 confound-free 對照組（非 FFHQ 底圖來源）驗證 100% 是否為 shortcut（需新資料來源，成本較高）

## B｜Region Head 架構（Phase 2）

- [x] **P0-2：Region head 改用 pre-pool 空間 feature map**（conv5 7×7×1024，逐region幾何窗口pooling）：`train_region_head_v3.py`，直接修正 Spatial-Global Mismatch 結構性矛盾
- [x] 用 v8.8 backbone 重新訓練 region head，消除 train/serve 特徵漂移
- [x] **v2/v3 不穩定根因診斷：找到了，是 label distribution，不是 learning rate**——查訓練資料發現 6/8 region（forehead/eyes/mouth/jaw）正樣本比例 99.5-100%（近乎常數標籤），left_cheek/right_cheek 只有 0.4%（14/3,959筆）。架構修正後 cheek F1 僅從 0.000→0.013-0.016，證實瓶頸是 FakeVLM 標籤稀疏/退化，非架構問題；v1 的 F1=0.842 重新詮釋為「6/8常數標籤灌水，非真實定位能力」
- [ ] **新 TODO（取代原 region_head_v2 部署項）**：解決 FakeVLM cheek 標籤稀疏問題——① 重新設計 FakeVLM prompt 引導更常描述臉頰、② 或接受 cheek 定位在目前 pseudo-label distillation 路線下不可行，論文誠實揭露此限制（成本評估：①需重跑FakeVLM inference，較貴；②純寫作，立即可做）
- [ ] region_head_v3.pth **未達部署標準，暫不接上 pipeline.py**（macro F1=0.413，且val_loss訓練不穩定，best checkpoint在epoch4即出現），`REGION_HEAD_PATH` 維持指向 v1
- [ ] FakeVLM pseudo-label noise 量化（人工抽樣驗證 teacher 標籤品質；現在有更急迫理由——需了解為何模板幾乎不提cheek）

## C｜Filter 可解釋性（Phase 2，本次談論主題）

- [ ] **Landmark Displacement GT pipeline 藍圖**（設計已定案，待Phase 1收尾後實作，零額外資料成本——自建filter pipeline本身已產生before/after landmark座標）：
  1. Keypoint 選取：眼角、嘴角、鼻尖、下巴輪廓、臉頰輪廓（沿用MediaPipe FaceLandmarker既有468點，取子集）
  2. 對每張 paired filter 圖跑 landmark detector，取得 filter 前後座標
  3. 計算逐 keypoint 位移量，設定閾值（例如 >X px 視為該 keypoint 被修改）
  4. 位移量映射回 region-level GT mask（forehead/eyes/cheeks/jaw/nose/mouth，沿用 `ARTIFACT_REGION_MAP` 既有 region 定義）
  5. 依 filter 類型分流：eye_enlarging/face_reshaping 主要靠 landmark 位移（幾何形變明顯）；whitening/smoothing 需搭配 pixel-level diff（色彩/紋理變化，landmark 位移量小或無）
- [ ] 用 landmark displacement GT + IINC 指標評估 Grad-CAM/region head 對 filter 的定位品質（公式已記錄於 Dataset 清單.md）
- [x] **XAI 評估 protocol：metric函式已實作+驗證完成**：`xai_eval_protocol.py`實作IoU、Pointing Game、IINC三個method-agnostic函式，皆通過synthetic data self-test。**修正一個公式校準問題**：IINC公式的I/U/M_gt/M_att必須是面積比例（除以總像素數正規化），不能用raw pixel count代入，否則算出的數字（測試中得到-17.667）遠超論文參考範圍（0.015-0.311）；正規化後完美重疊情境算出0.153，落在合理區間，已記入`docs/Dataset 清單.md`。
- [x] **LRP baseline實作完成（用Gradient×Input近似，已誠實記錄近似原因）**：`explainability/lrp_baseline.py`。實測captum的`LRP`模組對ShuffleNetV2架構直接失敗（`nn.Sequential`類型的複合容器沒有預設propagation rule，channel shuffle/grouped conv在LRP文獻中也沒有canonical規則），手動逐層指定規則的工程成本相對於「只是四個對照方法之一」不成比例。改用captum的`InputXGradient`——對ReLU網路而言數學上等價於LRP-0規則在輸入層的結果（Montavon et al. 2019, LRP Overview, Sec 10.2.3），是文獻中常見的實務近似選擇，非精確multi-rule LRP。已通過self-test，並完成與`xai_eval_protocol.py`的end-to-end整合測試（真實filter圖片跑出heatmap→binary mask→IoU/Pointing Game/IINC全部正常計算，無報錯）。
- [x] **XAI 評估正式執行完成（eye_enlarging範圍，100張）— 誠實負面結果：region_head_v4未明顯贏過Grad-CAM++**：
  - 結果：Grad-CAM++ IoU=0.467/PointGame=0.820/IINC=0.076；LRP-approx IoU=0.130/PointGame=0.390/IINC=0.214；region_head_v4 IoU=0.261/PointGame=0.850/IINC=0.157；pixel-diff baseline（配對，額外資訊）IoU=0.311/PointGame=0.880/IINC=0.024
  - **在三個公平對照（僅看單張圖）方法中，Grad-CAM++的IoU/IINC都明顯優於region_head_v4，region_head_v4僅Pointing Game小勝**——代表v8.8分類器本身的Grad-CAM++ attention已有不錯定位能力，訓練額外region head不一定能超越post-hoc方法，此為誠實記錄的負面/中性結果，非隱藏
  - 完整分析見`docs/Dataset 清單.md` 2026-08-02條目
  - **✅ 一致性檢查（face_reshaping/whitening，各100張）確認同一模式成立**：Grad-CAM++ IoU/IINC全面優於region_head_v4（3類型×100張=300次獨立比較一致），region_head_v4至多打平Pointing Game，LRP-approx三類型皆最差。**拍板：不投入IoU-based loss重訓，直接寫入論文Discussion**（理由：歷史上「換loss不換資料」類改動效益普遍不大；此中性結果本身有方法論貢獻價值——Pointing Game vs IoU的落差揭示指標選擇會導向不同結論）
- [ ] **論文Discussion段落撰寫**：把此XAI對照結果（含一致性檢查）整理成正式段落，定位為「v8.8分類器的Grad-CAM++ attention在filter定位任務上已相當程度可解釋，訓練額外region head的成本效益不明顯」，數字表格見`docs/Dataset 清單.md` 2026-08-02條目
- [ ] Filter region mapping（`ARTIFACT_REGION_MAP`）論文中包裝為「解剖學先驗引導」設計決策，明確承認非動態定位
- [x] **Phase 2 論文 claim 框架草稿（2026-08-02 依LAB diff視覺化發現修正為兩級粒度）**：
  - Filter（局部形變類，僅eye_enlarging）：「For eye enlargement, we provide region-level, GT-backed explanations grounded in pixel-level LAB color displacement measured directly from the paired before/after generation pipeline, validated against a physically self-scaling warp radius (proportional to detected eye width).」
  - Filter（全臉效果類，whitening/smoothing/face_reshaping）：「For whitening, smoothing, and face reshaping, we provide whole-face, GT-backed explanations rather than fine-grained per-region localization -- pixel-level diff analysis (visualized in Fig. X) shows these operations' true effect area spans nearly the entire face oval (whitening/smoothing, by design of the underlying skin mask) or saturates across most regions at dataset scale due to a fixed (non-face-size-adaptive) warp radius (face_reshaping), making region-level ground truth non-discriminative for these three operations specifically.」
  - Fake：「For synthetic faces, explanations remain global-level (image-wide texture/frequency anomalies) due to the absence of paired pre-/post-manipulation ground truth for identity-swap and diffusion-based synthesis.」
  - 此為Phase 2撰稿權威版本（`docs/phase1_story.md`範圍限定Phase 1分類器演進，不含此節）

## C1｜Filter 域泛化研究支線（Bonus，主線穩定後再開）

- [ ] **Shadow filter domain gap診斷**：拆解VGGFace2底圖風格（光線/構圖/解析度）與訓練filter來源（RetouchingFFHQ/self-built pipeline原始底圖FFHQ-like）之間的分布差異，量化「filter generator是否針對特定底圖風格設計，套用在VGGFace2上產生風格失配」
- [ ] **擴充filter訓練來源**（類比real class在v8.9系列的路徑）：把FFHQR/RetouchingFFHQ原始資料集當filter訓練主來源之一，自建VGGFace2+filter pipeline降級為「額外OOD補充來源」而非唯一根據；視情況再找第三個filter來源（例如商用美顏app輸出）做cross-dataset驗證
- [ ] 驗證擴充filter來源後，Shadow filter recall能否從22-28%有感提升（例如40-50%），有進步則寫入論文正文；若擴到多來源仍卡在30%左右，改寫為誠實的Limitation + Future Work

## C2｜Open-set 行為設計（Phase 1/2 皆可用，低成本）

- [ ] `unknown_filter` 類別設計：對 3-class（或 v8.11 的 Layer1+Layer2）輸出加 confidence threshold，低於閾值時輸出 `unknown` 而非強制三選一/二選一
- [ ] Unseen filter/fake 資料集上的 open-set 評估：對 AIGuard/unseen 之外的新子集（候選：FFHQR、新收集的商業 app 濾鏡樣本）跑 precision/recall/coverage 三指標，驗證 unknown 判定是否有效攔住模型沒把握的樣本，而非單純拉低整體 recall

## E2｜外部 Benchmark（DF40 官方 test split，成本中等）

- [x] **✅ 2026-08-02 DF40官方協定查證完成，發現本專案訓練資料已跟官方Protocol-2衝突，設計替代benchmark**：
  - **官方協定查證**（WebSearch+WebFetch，`github.com/YZY-stack/DF40`官方repo + arXiv:2406.13495論文全文）：DF40共40種方法（10 face-swap/13 reenactment/12 EFS/5 face editing），4種標準協定，其中**Protocol-2**明確定義為「train on FF domain, test on CDF domain（同forgery method，跨資料域）」——本專案sd2.1/DiT/SiT/ddim/pixart五個頂層資料夾底下的`ff`/`cdf`子資料夾，剛好完全對應DF40官方的domain切分。
  - **❌ 關鍵發現：本專案訓練資料已經破壞官方Protocol-2的domain邊界**——實測`v88_train_real_fake.txt`顯示訓練時cdf/ff兩域混用（例：DiT用了2,527張cdf+473張ff；ddim用了2,652張cdf+348張ff），並非官方要求的「只用ff訓練」。**因此無法直接復用cdf當乾淨的官方Protocol-2 test set**，若硬用會有train/test洩漏。
  - **替代方案（已執行，誠實標註非官方協定複製）**：改用「從未被v8.5/v8.8/v8.10a任何訓練split用過」的leftover pool（每方法16K-35K張）抽樣1,000/method（5方法共5,000張），配對CelebA test 3,000張real，計算per-method recall+AUROC。腳本：`eval_df40_benchmark.py`，已在script docstring與輸出報告中明確聲明「非DF40官方Protocol-2複製，是誠實的held-out pool評估」，避免誤導讀者以為是可直接對照文獻的官方數字。
  - **已查證的參考baseline數字**（DF40論文Protocol-2，EFS類別，FF訓練/CDF測試）：Xception AUC=0.586、CLIP=0.617、SRM=0.589、SPSL=0.635、RECCE=0.623、RFM=0.644——**僅供粗略背景參考，非同協定/同方法子集，不可直接宣稱贏過或輸給這些數字**（論文的EFS類別涵蓋12種方法，本專案僅訓練5種；協定本身也不同）
  - 執行方式：`eval_df40_benchmark.py [layer1_weights] [layer2_weights]`，用v8.11（Layer1c+Layer2）跑
  - **✅ 執行完成，結果：overall AUROC=0.9999（5方法各99.5-99.9%recall），但❌發現重大方法論陷阱，已誠實記錄不可誤用**：此benchmark測的是「同method+同domain混合分布下的held-out樣本」（in-distribution），跟DF40論文Protocol-2測的「跨domain泛化」（train FF/test CDF，真正distribution shift）難度天差地遠，**不可拿來跟論文baseline（0.586-0.644）比較宣稱贏過文獻**，那會是嚴重overclaim。此benchmark真正證明的只是①無train/test洩漏②對已訓練方法有近乎完美in-distribution recall（sanity check性質）。**論文中真正該用的跨分布泛化證據仍是AIGuard/unseen AUROC=0.8112**。完整分析見`docs/Dataset 清單.md` 2026-08-02條目
  - **待辦**：`docs/paper_outline.md`的4.1節GAP需要更新措辭——外部benchmark數字有了，但要誠實框定成「sanity check」而非「文獻對照勝出」，避免論文寫作時掉入overclaim陷阱
- [x] **✅ 2026-08-02 Alibaba filter OOD雙重查證+v8.11補測完成 — 真正跨域headline證據**：用戶提出跟DF40同等懷疑態度質疑既有的Megvii/Alibaba 99.9-100%數字，查證兩件事：①identity overlap（Megvii訓練FFHQ index 60002-69999 vs Alibaba eval index 17000-19999，**完全不相交，overlap=0**，非identity shortcut）②eval pipeline一致性（`eval_ali_ood.py`本就用`preprocess_jpeg`匹配pipeline.py，非v8.7踩過的前處理陷阱）。兩項查證皆通過後，補測v8.11實際數字（原數字只測過v8.6-v8.8）：`AIGuard/eval_ali_ood_v811.py`，**overall recall=97.8%**（21,151張，4類型96.5-99.8%，3強度97.7-98.1%）。**拍板：Alibaba OOD 97.8%是可信的headline跨域證據，與AIGuard/unseen AUROC=0.8112並列成filter/fake兩側的「真正跨域泛化」代表數字**，filter類跨域證據缺口已填上，不需要再追Tencent或RetouchingFFHQ MAM文獻對照。完整查證過程見`docs/Dataset 清單.md` 2026-08-02條目
- [x] **✅ 2026-08-02 CelebA real OOD雙重查證完成（比照Alibaba同等級）— 第三個headline跨域數字**：①identity/partition overlap——CelebA官方`list_eval_partition.txt`本身identity-disjoint設計（train/val/test三個partition的身分完全不重疊，官方協定非本專案自訂），本地逐一驗證celeba_train/celeba_test/celeba_val三個資料夾100%對應各自partition、零混用；②eval pipeline一致性——`eval_v811_gates.py`直接import`pipeline.preprocess_jpeg`，架構與`hierarchical_predict()`邏輯一致。**拍板：CelebA real recall=99.7%（v8.11）可信，與Alibaba OOD=97.8%、AIGuard/unseen AUROC=0.8112並列成三個class（real/filter/fake）各自的headline跨域證據**。同時明確保留Shadow real recall=75.5%（v8.11）誠實揭露的trade-off框定，不與CelebA混為一談（兩者難度與定位不同：CelebA是「同樣網路人臉照片不同partition」的OOD，Shadow real是「完全不同身分來源+更貼近部署場景」的robustness壓力測試）。至此C線（外部/跨域驗證）三個class皆已收斂完整，正式可關閉，回頭進入論文框架整合。完整查證見`docs/Dataset 清單.md` 2026-08-02條目

## 🧩 Phase 2（解釋性與 XAI，主線）

- [x] **Landmark displacement GT pipeline 開發中，發現並修復一個真實bug，但區辨力問題仍未解決**：`generate_landmark_gt.py`，對filter_data/{smoothing,whitening,eye_enlarging,face_reshaping}跑MediaPipe landmark detector計算前後位移+LAB pixel diff，輸出region-level GT。
  - **✅ 已修復的真實bug（座標系統錯位）**：原本沿用`train_region_head_v3.py`/`pipeline.py`的`FACE_REGIONS_PX`（假設臉部緊貼填滿224x224畫面的絕對像素框），但AIGuard/real原圖並非這樣裁切——診斷發現實際人臉landmark bbox只佔y=59-209（224中的一部分），導致「forehead」框（y:10-65）大部分落在頭髮/背景上，不是真正額頭皮膚。**已改為以每張圖自己偵測到的人臉bbox為基準，用比例（fraction）定義8個region框**（`FACE_REGIONS_FRAC`），不再假設固定裁切方式，這個修正是正確且必要的，與filter類型無關。
  - **✅ 已確認：純landmark位移不是可靠訊號**——即使幾何形變濾鏡（eye_enlarging），landmark最大位移也僅0.8-1.6px（224x224空間），因為MediaPipe偵測器會「跟著」形變後的特徵重新定位，不是釘在原始像素位置。已將pixel-level LAB色彩diff訂為主要GT訊號。
  - **✅ 2026-08-02 視覺化（A3）後推翻「校準bug」假說，重新框定為架構性發現**：`visualize_lab_diff_bleed.py`畫出LAB diff heatmap疊加region框後肉眼確認：85-100% positive rate不是雜訊/bleed，是**真實濾鏡效果**——whitening的LAB diff完整填滿`_skin_mask`橢圓遮罩（前額到下巴全臉），smoothing同樣接近全臉；這兩種濾鏡本來就是全臉效果，用ARTIFACT_REGION_MAP（使用者解釋文字用的簡化規則列表）當驗證基準本身就是錯的參照標準。face_reshaping進一步查出根因：`apply_face_reshaping`的warp半徑是**固定60px常數**（未依人臉尺寸縮放），全量7,997張統計顯示各region正樣本率飽和在77-100%；相對地`apply_eye_enlarging`的半徑=`eye_width×radius_factor`會隨偵測到的人臉尺寸自動縮放，這正是為什麼eye_enlarging在全量7,999張統計中仍保持清楚區辨力（眼睛97%、鼻頰88-100%因半徑溢出、嘴巴/下巴僅17-18%，額頭29%）的原因。
  - **決策：region-level 8分類GT只對eye_enlarging有意義**（whitening/smoothing原生就是全臉效果，face_reshaping因固定半徑bug在資料集尺度上也失去區辨力），三個原訂的calibration小實驗（縮框/統計檢定/視覺化）取消，因為問題根本不是校準精度，是這三種濾鏡的物理效應本來就不具備region級別的可分性。
- [x] **region_head_v4 訓練完成（eye_enlarging專用）— 確認為真實訊號，非label degeneracy重演**：`AIGuard/train_region_head_v4.py`，沿用v3已驗證的`SpatialRegionHead`架構，訓練資料為eye_enlarging的Landmark GT（train 6,398/val 1,599），backbone凍結自v8.8，30 epochs，best checkpoint在epoch 21（val loss最低）。
  - **Per-region F1（best checkpoint）**：forehead=0.438、left_eye=0.833、right_eye=0.817、nose=0.994、left_cheek=0.772、right_cheek=0.832、mouth=0.475、jaw=0.431。Macro F1=0.699。
  - **No-image trivial baseline對照**（比照v1的驗證方法論，用「永遠猜該region的多數類別」計算）：forehead/mouth/jaw三個region的正樣本率都<30%，trivial baseline在這三個region上F1恆為0（猜多數類別=全部猜負，完全抓不到任何正樣本）；trivial baseline macro F1=0.607。**實際模型macro F1=0.699，比trivial高0.092**，且關鍵是forehead/mouth/jaw這三個trivial baseline拿0分的region，模型實際達到0.43-0.48的F1——**證明模型真的在學習辨識這幾個region裡的稀疏正樣本，不是重演v1「6/8 region常數標籤灌水」的label degeneracy問題**。
  - **結論：v4是Phase 2 region head系列（v1→v2→v3→v4）第一個確認帶有真實圖像判讀訊號的版本**，雖然macro F1（0.699）低於v1的表面數字（0.842），但v1的0.842有87%（0.732/0.842）是trivial baseline灌水，真實訊號僅0.11；v4的0.092訊號量級與v1相近，但v4只在eye_enlarging這個誠實選定的、真正具有region區辨力的資料子集上訓練與報告，不像v1混雜了6個近乎常數標籤的region去墊高數字。
- [ ] **XAI評估：Grad-CAM++ / LRP-approx / region_head_v4 / pixel-diff baseline，用IoU、Pointing Game、IINC三指標評估對比**（協定與函式已實作於`xai_eval_protocol.py`，待region_head_v4訓練完成後執行`compare_methods()`，範圍限定eye_enlarging）
- [ ] **Filter解釋性論文claim改寫（原C章節文字需修正，見下）**：不能再籠統宣稱四種濾鏡皆有「region-level, GT-backed explanation」，需拆成兩級——eye_enlarging用region-level GT-backed；whitening/smoothing/face_reshaping改用「whole-face, GT-backed」（仍是真實GT，只是粒度較粗，誠實反映這些濾鏡的物理效應範圍）
- [ ] **Fake解釋性論文claim撰寫**：global-level explanation, 無region GT（見C章節已定稿文字，誠實說明資料限制原因）

## D｜跨資料集泛化誠實框架（純寫作任務，成本低）

- [x] **AIGuard/unseen AUROC、Celeb-DF-v2、FakeClue 三項誠實框架文字已寫成論文可直接引用的草稿**：`docs/limitations_framing.md`（含 [NEEDS CITATION] 標記，文獻數字查證前不可照抄）
- [ ] StyleGAN3 identity-overlap / VGGFace2-filter algorithm-overlap 的雙重限制在論文 Limitations 對稱呈現（可併入 limitations_framing.md，待論文草稿階段一起整理）

## E｜文獻對照實驗（成本較高，價值大）

- [ ] 跑 FF++ benchmark（binary real/fake，與文獻 SOTA 直接可比較的數字）
- [ ] RetouchingFFHQ MAM 頭對頭比較實驗（同資料集下 vs 你的 ShuffleNetV2+FFT，量化「輕量替代」主張）
- [ ] 查證 FF++/SBI/MLFF+CNN/FAME 等文獻數字（目前皆未驗證，寫論文前需核實）

## F｜StyleGAN3 身份重疊後續診斷（低成本，可選）

- [x] **ArcFace embedding + logistic regression identity-only baseline**（`AIGuard/arcface_identity_baseline.py`）：150個共用身份，(a)real vs SiT-fake AUROC=0.570、(b)real vs StyleGAN3-fake AUROC=0.592，皆接近隨機，遠低於實際分類器99.7%+——沒有證據支持identity shortcut是主因；StyleGAN3降級標註仍保留（誠實揭露原則）
- [x] **1a: identity manifest 精確統計**：Celeb-real 588/590（99.7%）、Youtube-real 300/300（100%）身份已透過DF40訓練覆蓋，比原推論更精確
- [x] **1c: same-identity real-source sanity test（已做，但結果不可用）**：`AIGuard/identity_sanity_check.py` 測得 real recall 僅6.8%（17/250），但實驗設計有confound——樣本全來自Celeb-DF-v2影片幀，跟已知獨立的H.264 domain gap問題（該資料集官方holdout real recall本就是0/200）綁在一起，無法拆分是身份效應還是壓縮域效應，**結果不可用於下結論**，需要靜態照片對照組才能做乾淨測試（目前無此資料源，未排入範圍）
- [ ] 官方 NVIDIA StyleGAN3 pretrained checkpoint + random latent 生成零身份依賴補充驗證集（需 GPU，本機 RTX 6000 Ada 49GB 可用）
- [ ] （大型/獨立專案，非本輪範圍）Identity-disjoint retrain：DF40 全部方法依 1,028 identity 切 train/test disjoint 後重新訓練

## G｜Tencent RetouchingFFHQ（使用者行動項）

- [ ] Tencent 子集（[申請表](https://fdmas.github.io/Application_RetouchingFFHQ_new.pdf)），核准後可補真正跨演算法 filter OOD

## H｜Ablation 系統性（低優先）

- [ ] 2×2 或 3×2 ablation matrix（spatial-only vs spatial+FFT × hard_neg 強度 × class weight），非大規模重訓，目的是佐證設計選擇而非找最佳超參


## J｜Phase 3 Robustness 其他項

- [ ] DF40 Face Editing (FE) 歸類決策（語義偏 filter；若加入需重新確認標籤）
- [ ] H.264 domain gap 進階：Wavelet Transform 取代 FFT branch（架構改動大，augmentation 不足時再考慮）

## K｜Phase 3 研究計畫草稿（2026-08-02，下一個研究專案，不是本輪Phase 1+2論文範圍）

> 定位：Phase 1+2已具備完整論文條件（架構：三分類trade-off→v8.11 hierarchical；XAI：FakeVLM失敗→Landmark GT+Grad-CAM++→pipeline對齊），主線先收斂成論文（見TODO最下方＋docs/phase1_story.md/docs/phase2_story.md），Phase 3是收斂完成後才開始的新研究線，此處僅先定調不動手。

**1. 研究目標**：維持輕量/可邊緣部署前提下，引入高品質vision-language teacher，建立attribute-level/region-level explainability，超越目前Grad-CAM filter explainability的粒度與語意表達。系統輸出結構：主分類(real/fake/filter) + 多標籤attribute(texture_smoothing/brightness_elevation/eye_geometry_change等) + region-level權重 + teacher-guided自然語言解釋。

**2. Teacher選型與比較**（小規模、不需訓練，只看text回答）：
- 候選：FakeShield類專門deepfake-VLM、GPT-4V同級多模態模型、開源VLM(LLaVA/Qwen-VL)當baseline
- 實驗設計：50-100張代表樣本(real/fake/4種filter)，固定prompt問「哪裡不自然」「哪種濾鏡影響哪些部位」，比較語義粒度、區域一致性、標籤分布健康度（避免重演FakeVLM 6/8 region常數標籤degenerate分布）
- **✅ 2026-08-02 P3-M0 pilot完成，第一個candidate（Qwen2-VL-7B-Instruct，本地跑，無API key情況下的替代方案）— 決定性負面結果，重演FakeVLM degeneracy問題**：`run_teacher_qwen2vl.py`，90張樣本（real/fake/4種filter各15張）× 2固定prompt = 180次推論，回應存於`results/p3m0_qwen2vl_responses.jsonl`。量化分析：
  - **fake_prompt完全退化**：「這張臉是否被AI生成/修改」問題上，**real和fake兩類影像都是100%（15/15）回答「可能是AI生成」**——對真實照片和假照片給出完全相同的判斷分布，是零區辨力的常數輸出，且回答文字本身高度模板化（不同real圖片幾乎逐字相同的「額頭平滑無皺紋、眼睛對稱缺乏光影」等描述）。這比FakeVLM原本的問題更嚴重——FakeVLM至少6/8 region有近常數標籤但其餘2個region有效，這裡的「是否AI生成」主問題本身就完全无区辨力。
  - **filter_prompt miss rate偏高**：對真正有套濾鏡的圖片，模型判斷「沒有濾鏡」（漏判）的比例：eye_enlarging 60%、whitening 80%、smoothing 67%、face_reshaping 53%；相對地對真實無濾鏡圖片100%（15/15）正確判斷「沒有濾鏡」——模型呈現強烈保守偏誤，寧可漏判也不誤判，且即使正確抓到濾鏡，回答也籠統列出全部4種類型而非具體指出實際套用的那一種。
  - **拍板（v1）：Qwen2-VL-7B-Instruct（未微調的base instruct版本）用free-text生成方式不可直接當Phase 3 teacher**，直接套用會重演FakeVLM label degeneracy的同一個陷阱。
  - **✅ 2026-08-02 v2 follow-up：確認v1的退化主因是「yes-bias」（文獻已知VLM在自由文字生成yes/no問題上的系統性偏誤），不是模型完全不懂任務**。改用`run_teacher_qwen2vl_v2.py`（同一批90張樣本）：① fake_prompt改為token-logit二元判斷（比較"A.真實"/"B.生成"兩個token的logits取softmax，繞過自由文字生成的yes-bias），② filter_prompt加2個few-shot範例（whitening+smoothing各一）。結果存於`results/p3m0_qwen2vl_v2_responses.jsonl`：
    - **fake_prompt logit法：pairwise AUROC=0.811**（real p_fake均值0.606, fake p_fake均值0.735）——**確實存在可用的區辨訊號**，v1的完全退化是free-text生成的yes-bias造成，不是模型不懂任務。但原始@0.5閾值準確率僅57%（17/30），因為整體分布系統性偏向「fake」——需要校準（例如在held-out set上學一個閾值），不能直接當pseudo-label用。
    - **filter_prompt few-shot法：漏判率明顯下降**（eye_enlarging 60%→33%、whitening 80%→33%、smoothing 67%→13%、face_reshaping 53%→33%），但**real圖片假陽性率從0%飆升到60%**——few-shot範例把模型推向「傾向說有濾鏡」，從保守偏誤換成寬鬆偏誤，同樣需要校準。
  - **拍板（v2，最終）**：Qwen2-VL-7B-Instruct **有可用的底層訊號，但off-the-shelf zero/few-shot都需要額外校準才能當teacher**，不是「模型完全不適合」而是「需要一個校準步驟」。下一步建議：①在額外的held-out樣本上學習p_fake的最佳分類閾值（而非0.5），驗證校準後的準確率能否達標；②filter_prompt做few-shot數量/範例選擇的消融，尋找recall/precision的平衡點；③若校準後準確率/miss rate仍不理想，才轉向其他candidate（FakeShield、72B）或weak supervision路線
  - **⚠️ 2026-08-02 v2發現並修正bf16量化bug，訊號經驗證仍成立**：使用者複查v2完整JSON明細，發現90筆`fake_prompt_v2_p_fake`只有24個獨立值，且在logit空間精確以0.125（=2⁻³）等間隔量化——典型bf16 mantissa（7-bit，相對精度2⁻⁷）捨入指紋。根因：直接讀`model()`輸出的bf16 logits張量做`.item()`，圖片內容造成的真實差異量級可能小於捨入步長被抹平。修正版`run_teacher_qwen2vl_v2_fix.py`改取lm_head投影前的hidden state，只針對A/B兩個候選token用fp32手動重算投影（避免整個7B模型跑fp32爆VRAM）。**驗證結果**：fp32修正後90筆變回90個獨立值（bug確認修好），同時腳本內重跑bf16路徑做對照仍是24個值（確認量化可重現、非隨機雜訊）；**修正後AUROC=0.804（修正前0.811，幾乎沒變）——原本的區辨訊號是真的，不是量化網格巧合造成的假訊號**，@0.5準確率18/30（60%，修正前57%）同樣偏低，校準需求結論不變。P3-M0 v2核心判斷在抓出並修正bug後依然成立，且數字可信度更高。
  - **✅❌ 2026-08-02 閾值校準（fake_prompt成功）+ few-shot消融（filter_prompt失敗）**：為避免用同一批90張既發現訊號又拿來校準+驗證的資料洩漏風險，另建120張獨立校準集（`select_p3m0_calibration_samples.py`，60 real+60 fake，與原90張零重疊）。**fake_prompt**：`run_teacher_calibration.py`跑fp32 logit法，校準集掃描找出最佳閾值0.676，套用到完全獨立的原90張held-out set驗證，**準確率從naive 0.5閾值的60%（18/30）提升到73.3%（22/30）**——乾淨的獨立驗證結果，校準確實有效。**filter_prompt**：`run_teacher_filter_ablation.py`用75張新樣本（60 filter+15 real）比較兩種few-shot設計：`pos_only`（2正例）漏判率23%但real假陽性率飆到93%（14/15）；`pos_neg`（2正例+1負例）假陽性率降到7%但漏判率反彈到75%（比純zero-shot的65%還差）。**發現free-text few-shot對這個模型是不穩定的校準旋鈕**——加一個負例讓模型整體「態度」在兩極端跳動，找不到中間平衡點，跟fake_prompt能用連續機率值細緻校準的情況完全不同。
  - **P3-M0最終結論**：fake_prompt路線經bug修正+獨立閾值校準後**初步驗證可行**（held-out準確率73.3%，方向正確但仍有進步空間）；filter_prompt的free-text/few-shot路線**已證實走不通**，需要改造成token-logit二元判斷方式（比照fake_prompt的做法，針對每種濾鏡類型分別取token機率）才有機會，屬於未完成的後續工作，尚未執行

**3. Attribute/Region Schema設計**（純設計階段，teacher選定前就可以做）：
- Attribute taxonomy：Geometric（eye/nose/jaw/lip/eyebrow_geometry_change）、Texture/Color（texture_smoothing/brightness_elevation/skin_tone_shift/makeup_artifact/color_grading）、Global（overall_sharpness_change/overall_color_shift/unknown_artifact）
- Region schema：forehead/eye_area/nose/cheek_area/mouth/jawline + whole-face（whitening/smoothing/face_reshaping用）+ 非臉區域候選（background/hairline/neck_shoulder，服務fake explainability的「背景合成感」描述）
- 教師輸出→學生label的mapping規則需設計（例：「皮膚平滑無毛孔」→texture_smoothing + region=face）

**4. 蒸餾資料來源與標註策略**：
- 候選資料集：AIGuard real+fake、DF40 EFS、StyleGAN2/3、RetouchingFFHQ+自建filter pipeline、FakeClue/Celeb-DF
- Phase 3.1 pilot：每類500-1,000張跑teacher標註，檢查分布健康度，排除degenerate label
- Phase 3.2擴充：健康子集確認後擴到1-2萬張正式蒸餾集
- 注意：fake類部分attribute只能做到global而非region，須在schema誠實標註，不可假裝有精確定位

**5. 學生模型與訓練目標**：
- backbone沿用v8.11 DualBranch（ShuffleNetV2+FFT），新增attribute head（multi-label sigmoid）+ region head（conv5 feature map + region pooling）
- 訓練目標：主分類CE（不變）+ attribute BCE/focal loss + region loss（filter類混合teacher soft label與LAB diff/landmark硬GT；fake類純teacher蒸餾）

**6. 評估指標與驗證計畫**：
- 分類性能：維持Phase 1既有7項gate，確認加explainability head不讓主分類退步
- Filter explainability：attribute層面teacher/學生一致率（Jaccard/F1）；region層面沿用IoU/Pointing Game/IINC（eye_enlarging等局部濾鏡）+ whole-face覆蓋率簡化指標
- Fake explainability（無GT）：cross-teacher一致性 + human evaluation（Likert scale小型user study）
- 整體：N=20量級user study比較新解釋 vs 現有Phase 2 template explainer

**7. 里程碑草案**：P3-M0選型與schema定稿（1-2週）→ P3-M1 pilot蒸餾資料集（2-3週）→ P3-M2學生模型head設計+初版蒸餾（3-4週）→ P3-M3擴充+完整評估+user study（4週+）

---

## 已解決（歷史記錄，供查閱）

- [x] v8.4 三項資料完整性 bug（MidJourney 洩漏/val重疊/filter重複）→ v8.5 修復
- [x] Eval 腳本前處理不一致 → 統一修正（v8.6 重新量測後保留，v8.7 訓練端修改捨棄）
- [x] Fake+filter 誤判連續惡化（v8.4→v8.6：0.22%→1.48%）→ v8.8 擴充 hard_neg 首次止跌（1.35%）
- [x] RetouchingFFHQ 公司分類錯誤（誤把「four」當公司）→ 修正為 3公司(Megvii/Alibaba/Tencent)×4類型
- [x] CelebA real recall 4.1% → 99.6%（v8.4，根因 LFW×11 oversampling）
- [x] H.264 domain gap 修復嘗試（v8.2，Celeb-DF-v2 real 加入訓練）→ 代價過大未採用，根本解法待 Phase 3 架構重設計
