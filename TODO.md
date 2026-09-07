# TODO

> 完成立刻打 `[x]`；新 TODO 立刻加入。這份檔案是全專案 TODO 的唯一彙整（整合自舊 TODO 區塊 + 2026-07-31 session 新發現）。

## 🔥 2026-09-01/02 session 六輪結果與「已診斷但未修」欠款清單（最新，優先看這段）

> 這段是 2026-09-01 一整輪「挖設計說不通的地方並解決」的產出。**六輪全部有
> PRE_DECLARED + FINDINGS + registry 條目**，數字皆經第二次獨立重算核對。
> ⚠️ **重點是下面「欠款」三項：已經診斷清楚、但還沒修好的洞，不是 limitation，
> 是待辦。** 完整證據見 `docs/EXPERIMENT_REGISTRY.md` 對應條目。

**已完成的六輪（結論已寫入 registry 與 MASTER_PLAN）**
- [x] `DESIGN-AUDIT-20260901`——三個「說不通」實測命中：①Layer2 無 real 輸出但
      production 餵它 real 圖 ②配對對照推翻「Layer2 會認濾鏡」（唯一混淆全控的
      比較 AUROC 0.4755＝隨機）③棄權機制任何門檻皆不可用（信心對自身正確性
      OOD AUROC 0.5368＝隨機）
- [x] `FIX-PAIRED-CONTRAST-20260901`——把配對放進訓練：方向翻轉（反向率
      41.8%→8.0%，介入性證據）但幅度不足，stress 退步 FAIL
- [x] `FIX-PWMARGIN-20260901`——pairwise margin：held-out 幅度 +0.075→+0.208、
      反向率再降到 4.0%、B-LFW 四輪來首次移動（0.66→2.98%），但硬閘更差
      （stress 5.33、TT filter 89.56<90），不可促升
- [x] `AXIS-DECISION-20260901`——階層軸向 **VINDICATED**：現行軸
      cross-corpus mean AUROC 0.6631 vs 語義軸 0.3778，Δ=−0.2853、seed 不重疊。
      「為什麼這樣切」自此有事前宣告的證據級答案，取代「歷史因素」
- [x] `R12-POSTPROCESS-20260901`——**R12 首次有答案，PARTIAL confound**：溫和/
      幾何濾鏡（eye/whitening/reshaping）跟一般後處理 AUROC 僅 0.38-0.52 分不開；
      強力磨皮可分但方向顛倒。附帶：後處理誤判會附送無關但看似有據的型別說明
- [x] `R1R13-IDENTITY-20260901`——**R13 首次有量化下游證據，CONFIRMED**：
      ArcFace 身分距離 pooled AUROC 0.99997（filter 中位數 0.0335 vs
      identity-swap fake 0.9855）；R1 次要判定亦通過（自建 vs Alibaba
      Cliff's δ=0.097 negligible）

**🟡 欠款一：R12 訓練資料缺口——指標層已關閉，產品層未解（2026-09-02 `FIX-TRIPLET-POSTPROC-20260902`）**
- [x] 三元組訓練（同底圖：原圖→real／原圖+後處理→**仍是 real**／原圖+濾鏡→filter）
      使「有沒有被改」變成無資訊。**R12 指標從 production 0.4363（隨機）跳到
      0.9158 / 0.8850（兩 seed BUILD）**，且泛化到完全未見的 unsharp 家族。
      **這是介入性因果證據**，證實根因假設正確。防呆已驗證：訓練 14 種後處理
      與評測 5 種參數層級零重疊
- [x] 🔬 **機制發現：兩種能力可分離**——R12 閉合成功但 Primary B（配對幅度）
      REJECT 兩 seed。「分得出美化 vs 後處理」與「對濾鏡版給更高 p_filter」
      **不互相蘊含**。⇒ **修幅度必須用別的槓桿，補負樣本不會順便修好**
- [ ] **仍未解：產品層**。端到端只有約一半純後處理影像被判 real
      （53.4% vs production 48.2%，僅改善 5pp）。**指標層閉合 ≠ 使用者重存檔
      不會被誤標**。UI 已就此顯示誠實警語，但根本問題還在
- [ ] **仍未解：stress 閘門**，4.28%/3.98% vs 門檻 3.76%（production 2.80%）。
      三輪連續改善 5.33→4.67→**3.98**，**只差 0.22pp**。下一步明確：
      fake 側補後處理腿（「被壓縮過的假圖仍是假」），與本輪同一邏輯，
      PWMARGIN 已證明該類資料能收斂（hinge epoch 3 飽和）
- [ ] **新代價需處理**：①方向穩定性比 PWMARGIN 退步（反向率 seed1 13.65%／
      **seed2 48.19% 近擲硬幣**，PWMARGIN 是 4.0%）②**B-LFW 跨家族增益完全流失**
      （PWMARGIN 2.98% → 0.008%/0.31%，低於 production）③seed 變異大
      （conditional 空間差 0.18 AUROC），促升前須先確認配方穩定性
- [x] **`eye_enlarging` attractor——修復輪完成（2026-09-03
      `ARTIFACT-NONFILTER-20260903`）：PARTIAL，JPEG 幾乎修好、resize 幾乎沒動**。
      給 artifact_classifier 加真正的第五類「不認識」（`none_postproc`），非再修
      信心門檻（該路已被 `FIX-ABSTENTION-OOD-20260902` 十法窮盡證明修不好）。
      JPEG q40/q60 正確路由到「不認識」達 **92.7-98.0%**，代價對 4 known 類幾乎
      可忽略（≤1.15pp）；但 **resize round-trip 本質上沒動**（2.8-3.2%，跟修復前
      的 0% 幾乎沒差）、sharpen/blur 僅部分修復（9-21%）
- [ ] **新代價需決策（尚未裁定）**：在 Alibaba 跨演算法濾鏡上，39-66% 真實濾鏡被
      貼「不認識」，eye_enlarging 正確率 83.8%→48-50%——是「更誠實」還是「更多
      recall 損失」是未來需要裁定的取捨，本輪只量化沒裁決
- [ ] **後續**：resize round-trip 的 attractor 為何完全不受影響（訓練資料裡已含
      兩種 resize 規格）需要新診斷，不是加更多同類資料能解的（本輪已加過）

**✅ 欠款二：棄權機制——已清償（2026-09-02 `FIX-ABSTENTION-OOD-20260902`）**
- [x] 十種零重訓方法（MSP/energy/max-logit/entropy/Mahalanobis×2/deep-kNN/
      TTA×3）**全部 REJECT**，最佳 0.5627（production 0.5369，差距在 CI 內），
      **操作點十種皆不存在**。但本輪的價值不在「又失敗一次」而在
      **升級了限制的性質**：oracle 天花板量測（允許作弊、拿 Alibaba 自身標籤
      訓練）只有 0.6658，其中 0.6074 光靠「輸出了哪一類」查表即得 ⇒
      **表徵僅承載 +0.058 AUROC 能力資訊**，不是不夠聰明是資訊不存在。
      機制亦被指名：`face_reshaping` 上信心 AUROC **0.232（反向）**——
      信心越高越可能錯。**論文措辭改為「表徵層限制」而非「校準問題」。**
- [x] Phase 2（outlier exposure）已設計已事前宣告，**依事前訂的規則刻意未執行**
      （天花板落 0.60-0.75 低勝率帶；且 OE 規範 far-OOD 而 Alibaba 是 near-OOD，
      機制性失敗預測已事前記錄）。若未來要執行，`PRE_DECLARED_PHASE2.md` 完整可用
- [ ] ⚠️ **不得重跑**：該輪 agent 建議的「參數隨機化」與「多廠牌訓練」兩個方向
      **經覆核皆已做過且皆 NO-GO**（`FILTER1-PARAMRAND-20260827`、
      `filter1b_multivendor_20260828`）。連同底圖多樣性、增強、class weight
      共六個獨立失敗機制。**未來提新方向前先查 registry**

**✅ 欠款三：Layer2 real-vs-filter 對比——已清償為「四機制證據鏈的結構性限制」（2026-09-02 `FIX-TRIPLET-V2-20260902`）**
- [x] 身分輔助監督（Arm B idaux，2 seed）真的跑了（30,149/44,341 列有目標）——
      **跨語料幅度依然不動**（TT 中位數 0.0074/0.0021，門檻 0.10）。至此四種互異機制
      全部 REJECT：配對 CE／pairwise margin／三元組負樣本／身分輔助監督。
      **論文寫法：attacked with four independent mechanisms → 結構性限制。修法線收線。**
- [x] 同輪 Arm A（假圖側後處理腿）亦 REJECT：stress 4.33/3.93 落在對照組雜訊內，
      R12 閉合反而跌破 0.885。「stress 只差 0.22pp」不是補資料能補的。
- [ ] ⚠️ **不得重跑**：Arm B 兩枚 checkpoint 含 Celeb-real 衍生資料，在 Celeb-DF-B
      基準上已污染。方向穩定性 seed 2 系統性差（44-48% 反向）——若未來有人
      想再開此線，先解釋這個再說
- [ ] FIX 線 step 4（PWMARGIN 消融＋第二 seed）：候選已全部 REJECT，促升動機不存在；
      僅在論文需要「PWMARGIN 4.0% 方向最佳」這句話帶第二 seed 時才補

**🆕 2026-09-03 Celeb-DF-B 外部基準揭露的三個新洞（`CELEBDFB-EXTERNAL-20260903`，數字經逐幀 TSV 獨立重算）**
- [x] **grain 型濾鏡擊穿 Layer1——消融輪完成（2026-09-03 `GRAIN-ABLATION-20260903`）：
      H1（純顆粒＝相機真實感）NOT CONFIRMED，但揭露更值得寫的三件事**：①合成顆粒在
      **跨域假圖（AIGuard/unseen）中劑量效應真實顯著**（逃逸率 +15.33pp [+10.80,+20.21]，
      CI 排除 0），in-domain TT fake 只有 +2.22pp（CI 含 0）——同一處理對「沒見過的
      生成方式」殺傷力遠大於見過的，獨立安全發現值得寫；②**TT real 上方向與
      Celeb-DF-B 相反**（顆粒讓真照片更像操弄，real recall 57.6%→37.6%/8.4%），
      hawaii_grain 真正機制非純顆粒；③**銳化在高劑量更乾淨復現 Celeb-DF-B 模式**
      （unseen_fake 逃逸 +56.10pp、TT real recall 衝到 90%），可能是更接近的候選
- [x] **分支探針推翻原假設方向**：元兇是**空間分支不是 FFT 分支**——純空間分支決策
      隨顆粒劑量推向「更像操弄」（TT real 高劑量 Δp_manip +0.47），純 FFT 分支反而
      推向「更真」（同劑量 −0.19）。**論文任何「頻域分支＝雜訊漏洞」的機制敘述需
      修正為空間分支**
- [x] **修復輪完成（2026-09-03 `GRAIN-ROBUST-FIX-20260903`）：in-house BUILD／
      外部 PARTIAL／stress 硬閘 FAIL，不可促升**。把顆粒/銳化當強健性增強加進
      Layer1 訓練：AIGuard/unseen 上 grain_g8 逃逸率從 +15.33pp 修正到 **−8.36%**
      （矯枉過正）、sharpen_p200 從 +44.60pp 中和到 +1.74pp（CI 含 0）。**分支探針
      證實機制修復真實**（空間分支 swap 分量 −0.043→+0.015 翻正，對應診斷）。
      但**外部驗證不轉移**：Celeb-DF-B hawaii_grain 逃逸率 57.59%→54.14%，CI 大幅
      重疊（PARTIAL），呼應顆粒消融輪已預告「真照片方向相反，機制非純顆粒」。
      **且傷到 stress 閘門**（2.80%→4.85%，集中在 whitening_medium 15.68%／
      eye_enlarging 11.89%／face_reshaping 10.14%）⇒ 依規則不可促升
- [ ] **後續（由本輪證據推導，尚未執行）**：①銳化消融的完整劑量-反應曲線已有
      （`grain_ablation_20260903/tables.md`）——既然銳化比顆粒更接近 Celeb-DF-B
      的內容無關偏移模式，下一個候選是把銳化也納入強健性增強，需獨立 PRE_DECLARED
      驗證是否能同時修好 stress 閘門的傷害；②空間分支的具體漏洞位置（哪一層/
      哪個統計量）尚未定位，若要提出防禦需要進一步探針
- [ ] **filter 類在影片幀材料上永不觸發**：Celeb-DF-B 12 個 folder×arm 格 **0 個 filter 標籤**
      （RES-MATCHED），美顏讓 real/fake 幀都「更真」（Δp_manip −0.07，內容無關），AUROC(p_filter)
      0.361 反向。Layer2「無 real 類」的錯誤流向依語料而異（True Test→filter 100%、Celeb-DF→fake
      100%）。**論文 filter 主張範圍須明寫「靜態影像、本專案定義之美顏語義」**；影片幀上的
      Instagram 式調色/顆粒不在偵測範圍內，是 scope finding 非 bug
- [ ] **安全性 headline 框架收窄（純寫作，但必做）**：in-house 2.80% **不得單獨作為外部安全性
      主張**；外部美顏可歸因增量 +13.8pp 幀／+16.4pp 影片（5–7 倍）。改寫為「本專案濾鏡庫＋
      Celeb-DF-B 四預設中三個維持低 ASR（10–14%）；grain 型濾鏡可擊穿；仍遠低於 Saeed et al.
      ≈64.6%」。Libourel 的 ≈0.07 向 real 偏移在 production 精確復現→可作跨系統一致性證據

## 📌 全部未解決問題總覽（2026-08-10 盤點，2026-08-11 更新）

> 這是掃描全文件所有未打勾（`[ ]`）項目的索引，每項只列一行摘要+關鍵字，完整說明在文件對應章節（用關鍵字 Ctrl+F 可找到）。組員分工的兩個任務（手機端FFT相容性、Layer 2瓶頸）已在下方獨立成節。

> **2026-08-11 本輪完成／關閉的項目**：① 手機端部署 blocker 解除（任務一，原為整個「邊緣部署」主張的結構性障礙）② True Test 配對設計有效度問題查出並改用配對指標 ③ Shadow 域泛化根因查清（兩個平凡解釋均以實測排除）④ Phase 3 P3-M0 filter teacher 路線以決定性負面結果關閉，並據此修訂為混合監督策略 ⑤ Landmark GT / XAI 六項「疑似已完成」條目逐項查證後補打勾。**新增未解項目**：v8.12 base 多樣性實驗的結論（進行中）、XAI 結果缺機器可讀檔、三篇文獻待讀原文查證。

**Phase 1 收尾／驗收關卡**
- [x] ⚠️ **2026-08-11 查出 True Test 主 gate 的報告方式有效度問題（資料本身乾淨，是報告方式不完整）**：True Test 是**配對設計**——249 張 filter 圖 100% 是 real 那 250 張**同一批來源照片**的濾鏡版本。因此「filter recall 93.6%」無法單獨證明濾鏡偵測能力（永遠回答 filter 的退化模型也能拿 100%）。修正後的誠實數字：**balanced accuracy 81.1%、strict per-pair accuracy 62.2%**。詳見下方專節
- [x] ✅ **2026-08-11 手機端部署 blocker 已解除**：FFT 分支改用等價的常數矩陣 DFT（`mobile_fft.py`），零重訓，fp32 TFLite 產出物實測可載入可推論、True Test recall 與 PyTorch 逐張相同（769/769），20.91 MB / 14.4 ms 每張。int8 因 FFT 頻譜動態範圍 7.6e9 而不可用（根因已查清）。詳見「任務一」章節
- [x] ✅ **2026-08-31 int8 解鎖（arch2_int8_split_20260831，零重訓）**：上行「int8 不可用」已過時——圖切分（頻譜計算留 float 前處理）＋靜態校準 full-int8 後全過：0 NaN、決策一致 95.19-95.71%、三類 recall 全在 3pp 帶內、**5.41MB（比 fp32 小 3.9 倍）**。過程中診斷出第二個一直被遮蔽的 blocker（stage2.0 depthwise conv 的 dynamic-range 量化不穩定，現役 artifact 本來就有、被 FFT 塌陷遮蔽；靜態校準下完全免疫）。切分 fp32 本身亦更小更快（19.38MB/8.91ms）。接線 release 為獨立 change-control 決定，未做。完整證據見 registry ARCH2-INT8SPLIT1、results/research/arch2_int8_split_20260831/FINDINGS.md
- [x] ✅ **2026-08-22 v8.17 production stack（Layer1=v817sbi＋Layer2=v811＋Artifact classifier=v6）重新匯出手機格式，三個模型 G1-G4 全過，769 張 True Test 全鏈路 TFLite vs PyTorch 決策 100% 一致**：Artifact classifier 為首次匯出。三模型合計 fp32 25.75 MB（Layer1+Layer2 兩模型子集 20.91 MB 與舊數字打平）。完整報告 `results/mobile_export/v817_20260822/EXPORT_AND_VERIFY_REPORT.md`，詳見「任務一」章節新增段落
- [ ] DF40官方test split外部benchmark 尚未執行（v8.11候選確定後才做，見「E2｜外部Benchmark」）
- [ ] ~~Ultimate Held-out Test Set 持續暫緩解封，直到v8.11通過完整驗收（含DF40 benchmark）~~ ⚠️ **2026-08-26：`splits/ultimate_clean_test.txt` 已 DOWNGRADED TO DEV-TEST**——`p2_abstention_20260823/scripts/task3_generalization.py` 直接讀此 split 對 783 張 real+fake 子集（VGGFace2 real 275／DiffSwap 289／StyleGAN3 219）跑了 gate head 與 production `p_fake`（registry P2-R8）。依 2026-07-31 自訂 lockbox 規則（被打開即降級），整份 split 不再是 blind held-out（filter 269 張雖未被讀，但同一份 split 不拆分認定）。需從未用來源重抽新 lockbox（MASTER_PLAN 新增項）。

**論文寫作任務（純寫作，成本低）**
- [x] ✅ **2026-08-11 Robustness 段落已撰寫，並升級為有解釋力的核心論述**（`docs/paper_outline.md` 4.4 節）：重新檢視 `results/robustness_eval.json` 後發現它與配對設計發現**指向同一機制**——擾動幾乎不動 fake recall（94-100% 全程穩定），卻讓 real 與 filter recall 反向大幅擺盪，**real−filter 落差從 −68.4（blur k9）擺盪到 +19.7（lighting −50%），跨度 88pp，但擾動完全沒改變影像裡有沒有濾鏡**。機制自洽：模糊/降採樣抹平皮膚紋理≈smoothing 效果 → 乾淨照被推向 manipulated；壓縮/壓暗破壞濾鏡痕跡 → 濾鏡照被推向 real。**這把三個原本獨立的觀察（True Test filter-biased、Shadow real-biased、擾動反向擺盪）統一成「同一條一維決策邊界隨影像統計平移」**，是本文最有解釋力的論述。附帶：overall accuracy 全程 70-89% 看似 robust，只有拆 per-class 才看得到邊界擺盪——本文第三次遇到聚合指標掩蓋真實行為。
  - ⚠️ **自我檢查後曾修正一次 overclaim**（保留過程記錄）：當時因 `lighting −30%` real 與 filter recall 同時下降、且 JSON 無混淆矩陣無法判定流向，故把敘事保守限縮到銳利度與壓縮兩族群
- [x] ✅ **2026-08-11 已補跑 3×3 混淆矩陣，疑慮排除，敘事可回到完整版**（`AIGuard/eval_robustness.py` 加記混淆矩陣、`analyse_robustness_confusion.py` 分析、`results/robustness_eval_v811d.json`）：True Test 上 **20 種擾動情境的 `real→fake` 與 `filter→fake` 幾乎恆為 0**，real 損失全流向 filter、filter 損失全流向 real，**全部都是 Layer1 閘門效應，Layer2 在此測試集幾乎從不是錯誤來源**。光照 −30% 也是 Layer1（filter→real 38 vs filter→fake 僅 3），它的特殊之處是**邊界同時平移與變鈍**（兩方向錯誤同時上升＝可分性下降），不是機制不同
- [x] 🔴 **2026-08-11 修正一個差點成立的錯誤安全性主張（重要）**：True Test 上 `real→fake = 0/250`（全部擾動皆 0）很容易寫成「本系統不會把真人照指控為 AI 生成」這個賣點。**在 Shadow（VGGFace2）重跑後完全不成立——53/279（19.0%）的乾淨真人照被判成 fake**（`analyse_shadow_error_destination.py`）。這是最嚴重的部署錯誤型態，而**只看 True Test 完全看不到**。論文任何 false-accusation 安全性陳述必須以 Shadow 為準，並說明 LFW 的 0 是資料集特性非系統性質
- [x] ✅ **同時釐清 C1 修法必須雙層並進**：Shadow 的 251 筆 filter 損失中 **55% 是 `filter→real`（Layer1 攔掉、根本沒進 Layer2）、45% 是 `filter→fake`（進了 Layer2 判錯）**，與 True Test 的 100% Layer1 完全不同 → 只補 Layer2 修不好被 Layer1 攔掉的那一半，只調 Layer1 也修不好另一半。v8.12 實驗同時加入兩層，方向與診斷一致
- [ ] True Test contamination bias 需在論文Limitations明確標註（v7+選型曾參考此結果）
- [ ] Alibaba confound排除實驗：找confound-free對照組驗證100%是否為shortcut（需新資料來源，成本較高）
      > ⚠️ **2026-08-21 更正兼優先度上調**：原標題寫「Alibaba **OOD** confound排除實驗」。
      > 該集**已確認非 OOD**——P1-R11 內容層級稽核測得與訓練資料 **23.5%（4,980/21,151）內容重疊**，
      > 也就是說**這個 confound 已經不是「待驗證的疑慮」而是「已量化的事實」**。
      > 本待辦的內容不變（仍需 confound-free 對照組），但其動機從「查證是否有問題」
      > 變成「量化一個已確認存在的問題有多大」。新對照組的篩選必須用內容金鑰查重，
      > 不可只比對 FFHQ index-range。證據：`results/research/p1_r11_leakage_scaling_20260820/TASK1_LEAKAGE_AUDIT.md`
- [x] ✅ **2026-08-21 F1 稽核完成：「Alibaba 是否 identity-disjoint」判定為 CANNOT BE
      DETERMINED WITH AVAILABLE DATA**——FFHQ 系列資料集本身無身份標籤（爬蟲資料，連原作者
      都不知道哪些照片是同一人），專案內既有身份比對腳本（`arcface_identity_baseline.py`、
      `identity_sanity_check.py`）都只涵蓋 Celeb-DF-v2 影格身份，不適用於 FFHQ，且沒有
      ground truth 可校準任何相似度門檻，故不可能像上面 pixel-content 那樣給出可信的
      identity-level 重疊百分比。補充跑了一個非判定性的 ArcFace embedding 相似度探測
      （400 Alibaba vs. 1,200 訓練相關樣本），bulk noise floor 0.16-0.29、2.75%（11/400）
      超過 cosine 0.4，其中最高兩筆很可能只是重新偵測到已知的像素重疊，中段 0.3-0.7
      （約5-8%）無法判定是否為真身份重疊——誠實報告為「無法判定」，不用弱代理方法灌水成
      一個假的百分比。完整方法與數字：`results/research/f1f2_audit_20260821/F1F2_AUDIT_FINDINGS.md`，
      `docs/EXPERIMENT_REGISTRY.md` F1F2-AUDIT-20260821 條目，`docs/Dataset 清單.md` 對應
      2026-08-02 條目已加註。
- [x] ✅ **2026-08-21 F2 稽核完成：Alibaba 98.1% 三份文件分歧已解決，根因確認為文件過期，
      非事實衝突**——`ORPHAN_AND_UNVERIFIABLE_REGISTER.md`（mtime 2026-08-13 11:42）寫成的
      時候確實還沒有備份檔案；同一天 12:07 P0 repair 產出
      `alibaba_filter_ood_v811d_layer2v811_20260813.json`，12:38 `EVALUATION_INTEGRITY_REPAIR.md`
      正確記錄「已解決」，但沒有人回頭把 register 對應三列更新。獨立重新開啟並核對該備份
      JSON（不只信引用）：SHA256 provenance 與 `RELEASE_RESULTS.md` 完全吻合，
      20,743/21,151=98.071%（四捨五入為 98.1%）數字真實存在。已在 register 與
      `REPRODUCTION_COMMANDS.md`（同樣過期，mtime 11:41）用 append-only 方式加註修正，
      `RELEASE_RESULTS.md`／`EVALUATION_INTEGRITY_REPAIR.md` 本身不需改動（兩者互相一致、
      皆晚於 repair）。完整記錄：`results/research/f1f2_audit_20260821/F1F2_AUDIT_FINDINGS.md`。
- [ ] StyleGAN3 identity-overlap / VGGFace2-filter algorithm-overlap 雙重限制需在Limitations對稱呈現

**Region Head / FakeVLM 標籤問題**
- [ ] FakeVLM cheek標籤稀疏問題未解決（重新設計prompt，或誠實揭露此限制二選一）
- [ ] region_head_v3.pth 未達部署標準，pipeline.py `REGION_HEAD_PATH` 仍指向v1
- [ ] FakeVLM pseudo-label noise 尚未量化（人工抽樣驗證teacher標籤品質）

**Landmark GT / XAI 相關**（2026-08-11 逐項查證完畢，多數其實早已完成，只是沒同步打勾）
- [x] Landmark Displacement GT pipeline：**已完成**，`generate_landmark_gt.py` 存在且「🧩 Phase 2」章節已記錄完整執行結果（含座標系統 bug 修復與「純位移訊號不可靠→改用 LAB diff」的結論）
- [x] 用landmark displacement GT + IINC評估Grad-CAM/region head定位品質：**已完成**，3 種濾鏡類型 × 100 張 × 4 方法 = 300 次獨立比較，結果表見 `docs/phase2_story.md` 第 5 節
- [x] `compare_methods()`是否已對region_head_v4完整跑過：**已確認完成**（eye_enlarging + face_reshaping + whitening 三類型皆跑過，結論一致）
- [x] XAI論文Discussion段落：**已完成**，可直接使用的英文段落在 `docs/phase2_story.md` 第 6 節
- [x] Filter解釋性論文claim改寫（eye_enlarging region-level／其餘三種 whole-face）：**已完成**，定稿文字在 C 章節「Phase 2 論文 claim 框架草稿」，且 `pipeline.py` 的 `ARTIFACT_REGION_MAP` 已同步改好
- [x] Fake解釋性論文claim撰寫：**已完成**，定稿文字同上（global-level, 誠實說明無 paired GT）
- [x] ✅ **2026-08-11 Filter region mapping「解剖學先驗引導」段落已寫**（`docs/phase2_story.md` 第 7 節，含可直接使用的英文段落）：三點框定——① 這是設計決策非能力遮掩（LAB diff 已證明 whitening/smoothing/face_reshaping 的 region GT 本身不具區辨力，給細 region 是 false precision）② 粒度隨證據強度而變（只有 eye_enlarging 保留 region-level，因其 warp 半徑隨人臉尺寸縮放）③ 明確區分 `ARTIFACT_REGION_MAP`（固定查表，只決定解釋模板提哪些部位）與 Grad-CAM++（動態逐張視覺化定位）的分工，避免讀者把查表誤讀成定位結果
- [x] ✅ **2026-08-12 XAI 對照結果補上機器可讀檔**：`build_xai_localization_csv.py` 把 `results/xai_comparison_eye_face_white.json`（既有數字，未重算）轉成 `results/xai_filter_localization_results_v1_20260812.csv`
- [x] ✅ **2026-08-12 XAI evidence contract schema 設計完成並跑出範例**：`docs/xai_evidence_schema.md` 定義 image→class→method→GT→evidence-level 的完整可追溯欄位；`build_xai_evidence.py` 用 production `pipeline.py`（未改動）跑 30 張樣本（5 real/5 fake/4 filter type×5），輸出 `results/xai_evidence_v1_20260812.jsonl`
- [x] ✅ **2026-08-12 Grad-CAM++ faithfulness（deletion test）首次實作，對象是 production v8.11 hierarchical（非舊版 v8.8）**：`xai_faithfulness_test.py`，k=5/10/20% top-heat masking + cold-region/random control，輸出 `results/xai_faithfulness_v1_20260812.{json,csv}`。**意外發現（誠實記錄，未回避）**：k20 時 mean_random_drop（0.640）> mean_hot_drop（0.235），與標準 deletion test 假設相反；最可能原因是 `FFTBranch` 對隨機散點遮罩（大量小邊緣→寬頻高頻噪聲注入頻譜）比對連續熱區遮罩更敏感，這是雙分支（spatial+FFT）架構對標準 spatial-CNN faithfulness test 的潛在混淆因子，需要 spatial-only ablation 或 blur-based masking 才能排除，本次未做（記在該 json 的 `key_finding` 欄位）。cold_drop 全程接近 0 且 hot_drop 明顯為正，這部分仍支持「熱區確實比冷區重要」，只是 hot vs random 的比較還不能直接讀成「heatmap 不可信」
- [x] ✅ **2026-08-12 RetouchingFFHQ pair audit 完成，結論明確**：`audit_retouchingffhq_full_pairing.py` → `results/retouchingffhq_pair_audit_20260812.json`。**reliable pair count = 0（four/megvii/ali 三批合計 44,662 張 clean 圖全部 unusable）**，原因比原先預期的 crop/align/JPEG confound 更根本——**本地完全沒有任何未修圖的原始 FFHQ 底圖**（`ffhq/` 資料夾其實是論文 LaTeX 模板素材，不是圖片；`pipeline_test_input/ffhq_test/60106.png` 逐 byte 比對後證實是 `FFHQ_four_process` 處理後輸出的複製品，不是原圖，mean abs diff=0.0）。Filter GT 應繼續依賴 `filter_data/` 自建 pipeline 的 before/after pair（`generate_landmark_gt.py`），RetouchingFFHQ 三批仍可繼續用於現有用途（filter OOD recall eval、filter classifier 訓練資料），但不可作 pixel-level GT。四/megvii 額外確認 base index 87.1% 重疊（60002-69999 共用範圍），ali 與兩者完全不重疊（17001-19999）
- [x] ✅ **2026-08-13 拍板：暫不下載官方 FFHQ 70K 資料集**。理由：Tier A（`filter_data/` 自建 pair，有 pixel-level GT）+ Tier C（fake/filter 的 faithfulness test，見下）已構成完整、可辯護的 XAI 驗證鏈；下載官方 FFHQ 是「要把真實 app 濾鏡的 pixel-level 定位當論文主貢獻」時才需要的高成本擴充，非現在的 blocker。完整 Tier A-D 分級架構見 `docs/phase2_story.md` 第 8 節、`docs/xai_evidence_schema.md`「Evidence tiers」章節
- [x] ✅ **2026-08-13 Grad-CAM++ faithfulness 異常發現已修正（blur-based masking），標準排序恢復**：新增 `xai_faithfulness_blur_test.py` → `results/xai_faithfulness_blur_v1_20260813.{json,csv}`，把 constant-fill 遮罩換成「模糊化內容 + 羽化邊界」，random control 從散點改為與熱區同形狀/同面積、只換隨機位置的 matched-random。**結果：hot_drop > cold_drop 且 hot_drop > matched_random_drop 在 k=5%/10%/20% 全部成立**（margin 分別 +0.108/+0.193/+0.300 與 +0.102/+0.059/+0.106），支持「08-12 版本的反常結果是 masking 方法的頻域混淆因子（FFTBranch 對散點硬邊界的高頻噪聲敏感），不是 Grad-CAM++ 真的不可信」。**同時修了兩個實作 bug**：① 原本 `hash((str(img_path), k))` 用 Python 內建 `hash()` 對字串做種子，因 `PYTHONHASHSEED` 預設隨機化，每次執行結果其實不可重現（已改用 `hashlib.md5` 的 `stable_seed()`，兩支 faithfulness 腳本共用）② 08-12 版 `key_finding` 文字有 `%` 格式化字串忘記套用參數的 bug（顯示成字面 `%.3f` 而非數字），已修正。決定**暫緩 spatial-only ablation**（會混入 Phase 1 架構改動，且 blur-based 修正後排序已一致，非必要）
- [x] ✅ **2026-08-13 Tier A-D XAI 證據分級架構定案**：`docs/phase2_story.md` 第 8 節——Tier A=自建 filter pair（有 pixel GT）／Tier B=RetouchingFFHQ（無 pixel GT，僅 class/type 層級，見上）／Tier C=一般 fake（無 GT，faithfulness 已驗證但 production 不輸出 region claim，維持 global_only）／Tier D=FF++ 官方 mask（未用，暫緩）。`docs/xai_evidence_schema.md` 同步新增「Evidence tiers」與「Faithfulness tests」章節，`build_xai_evidence.py` 的 `faithfulness_metrics` 欄位已合併 constant-fill 與 blur 兩份結果
- [x] ✅ **2026-08-13 P2-1 Composite Explanation Protocol（fake+filter）首次實作**：`phase2_composite_explanation.py`。**用戶指定的「v8.16」目前尚不存在，本次改用已存在、語意完全對應的 v8.15 dual-head 研究基準**（`shufflenet_v2_layer1_v812.pth` 凍結 + `shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth`，filter threshold=0.85，見 TODO.md「v8.15 clean 2x2 ablation」條目——尚未過 production gate，僅研究基準）。**關鍵發現：`fake_filter_hard_neg/` 的 fake+filter composite 圖，其「before」是已知的 `AIGuard/fake` 來源圖，等於也能套用 `generate_landmark_gt.py` 的同一套 pair GT 方法（只是 base_dir 換成 fake 而非 real）**——filter 部分因此仍是 Tier A（`paired_GT_supported`），即使整張圖最終判 fake。40 張樣本（4 型別×10）結果：filter_status=detected 31/40（77.5%），對這 31 張跑 IoU/PointingGame 得 mean IoU=0.398、mean PointingGame=0.774（與既有 filter_data 研究量級相近，定位品質有延續）。faithfulness（blur-based，k=20%）卻出現 mean_hot_drop 接近零甚至負值（-0.0396）——**與 fake_head/Layer1 那次 blur test 相反的異常，已記錄新假設**：filter 四型別之一「smoothing」本身就是模糊，blur-based masking 可能直接模擬/強化 smoothing 訊號，讓 filter_head 在近飽和分數下對任何位置的模糊都不太掉分，代表 blur-based faithfulness 對 filter_head 是錯的遮罩方法（跟 fake_head 的結論相反），需要換一種不像任何濾鏡操作的遮罩法才能乾淨測 filter_head faithfulness，本次未做，只記錄異常。IoU/PointingGame 兩項定位指標不受此影響，仍是 filter_evidence_level=paired_GT_supported 的主要依據。輸出：`results/phase2_composite_explanation_v1_20260813.jsonl` + `_summary.json`
- [x] ✅ **2026-08-13 P2-2（輕量版）filter type accuracy 在 fake+filter composite 上的驗證，發現重大且不均勻的劣化**：`phase2_composite_filtertype_accuracy.py`，ground truth 直接來自 `fake_filter_hard_neg/{type}/` 資料夾標籤（免費、精確，不需另外的 GT pipeline），對 200 張樣本（4 型別×50）跑 production 的 `artifact_classifier_v3.pth`。**結果：face_reshaping（92%）／smoothing（94%）維持可靠，但 whitening 崩到 6%、eye_enlarging 掉到 70%**。混淆矩陣顯示 whitening 不是隨機失準，而是系統性被誤判成 eye_enlarging（33/50）與 face_reshaping（11/50）——代表 artifact classifier 只在乾淨 real+filter pair 上驗證過，套到 fake+filter composite 後對至少 2/4 型別的 type 判斷不可信，**直接證實使用者 P2-2 提出的疑慮成立**。**決策**：whitening/eye_enlarging 在 fake 判定的圖上目前不可輸出具體 type，退回 P2-1 的通用「偵測到可能存在後製 filter」；face_reshaping/smoothing 型別暫時可信（已用 0.80 佔位門檻標記，非正式校準值）。輸出：`results/phase2_composite_filtertype_accuracy_v1_20260813.json`
  - **⚠️ 2026-08-13 範圍修正，2026-08-13 二次修正（重要，不可跳過）**：92%/94% 是**單一 fake 來源（`AIGuard/fake`）的 in-domain 數字**，不是「一般化的 fake+filter type recognition」。`fake_filter_hard_neg/` 的來源全部是 `AIGuard/fake`，P2-1/P2-2 本輪**完全沒有測試 DF40**——已核對 `phase2_composite_explanation.py`／`phase2_composite_filtertype_accuracy.py` 兩支腳本與其輸出，沒有任何 DF40/cdf 引用，這點屬實。**但「跨 fake 來源會崩潰」這件事本身不是未驗證假說——它是同一顆 v8.15-cellC checkpoint 在 Phase 1 已經用獨立 DF40-cdf replication set 測過、有完整 provenance 的既定事實（見上方「重大修正：C@0.85 的 joint recognition 完全不能跨 fake 來源泛化」條目：joint recognition 56.99%→2.02%、filter_head AUROC=0.5304 接近亂猜），只是屬於 Phase 1 那條實驗線，不是本輪 P2-1/P2-2 產生的**。之前一版文字誤把「P2-1/P2-2 沒測過 DF40」跟「DF40 跨來源是否崩潰未知」劃上等號，是錯的——沒測過（P2-1/P2-2 的事實）不等於未知（因為 P1-1 已經測過）。完整對照見 `docs/EXPERIMENT_REGISTRY.md`（P1-1 vs P2-C1/P2-C2 條目），新增此檔正是為了避免同類誤植再發生
  - **P2-1 報告方式收斂**：IoU=0.398／PointingGame=0.774 只算在 filter_status=detected 的 31/40（77.5%）子集上，須與「filter attribute coverage 77.5%」分開報告，不可合併成單一句「fake+filter 定位 IoU=0.398」（會蓋掉沒偵測到的 9 張）。論文用句見 `docs/phase2_story.md` 第 9 節
  - **P2-1 faithfulness 異常的更精確機制**：blur 遮罩對 smoothing 型別而言不只是刪除證據，本身就是疊加一層 smoothing 訊號，可能讓 filter_head 分數不降反升——不同 target class（fake_head vs filter_head）需要不同的介入測試方式，不是同一套遮罩對誰都適用。更合適的替代方案是 **dose-response test**（同一張 base fake 套遞增強度 filter，看 filter_head 分數是否隨強度單調上升），但刻意不搶在跨來源驗證資料就緒前做，優先度較低
- [ ] **P2-3/P2-4/P2-5 待辦（依 P2-2 結果 + P1-1 finding，非本輪範圍）**：schema 尚未接入 `pipeline.py`（v8.15-cellC 非 production，不動 production code）。type 是否可開放輸出，卡在兩層：① P2-2 的 in-domain 準確度（whitening/eye_enlarging 已知不可信，見上）② P1-1 已證明同顆 checkpoint 的 filter_head 本身跨 DF40-cdf 就崩潰（AUROC=0.5304），**在 filter_head 本身泛化前，討論 type 準確度是否跨來源泛化沒有意義**。等 v8.16 有 checkpoint 且通過跨來源 joint recognition 驗收後，才依 P2-4 重新用同一套方法（P2-1/P2-2 script）在 DF40 composite 上重跑，決定能否開放輸出 type；在此之前維持 P2-5（只輸出 has_filter，不輸出 type）
- [ ] **後續（依附 v8.16，非獨立 blocker）**：v8.16 若通過跨來源驗收，用 P2-1/P2-2 現有腳本（`phase2_composite_explanation.py`／`phase2_composite_filtertype_accuracy.py`）搭配 DF40 composite 重跑一次，兩支腳本已經是 source-agnostic（只要改樣本來源路徑），不需重寫
- [x] ✅ **2026-08-13 已預先寫好（未執行）v8.16 的 source-stratified composite explanation adapter**：`phase2_source_stratified_eval_adapter.py`，對 AIGuard-fake／DF40-ff／DF40-cdf frozen replication 三個 stratum 分開報告 filter attribute coverage、filter_head AUROC、type accuracy、conditional IoU/PointingGame。**刻意加了 `--i-have-verified-gates` 必填參數擋住誤用**：不給就直接 argparse 報錯退出，逼呼叫者先引用 `TODO.md` 裡這顆 checkpoint 的 gate 驗收記錄，而不是看到檔案存在就直接跑。**已用語法檢查+無參數呼叫驗證過會正確擋下，未執行任何實際推論**。⚠️ 磁碟上已出現 `shufflenet_v2_layer2_v816_mixedlineage.pth`（似為平行 Phase 1 session 剛訓練出來），但**沒有任何 gate 數字記錄，不構成「v8.16 已就緒」**，Phase 2 在 Phase 1 正式記錄驗收結果前不會拿它跑新宣稱，詳見 `docs/EXPERIMENT_REGISTRY.md`
- [x] ✅ **2026-08-13 Phase 2 Priority 0：重新驗證 production v8.11（非 v8.8）的 filter Grad-CAM++，結果混合，whitening 有新問題**：`phase2_p0_v811_filter_gradcam_validation.py`。第 5 節「Grad-CAM++ 優於 region head」的既有結論是在**已淘汰的 v8.8 flat 3-class 模型**上量測的，這次直接對 production checkpoint（`shufflenet_v2_layer1_v811d.pth`+`shufflenet_v2_layer2_v811.pth`）重跑同一套 paired GT，四型別各 100 張，**拆成三段報告**（Layer1 routing coverage／Layer2 favor-filter coverage／最終 filter 準確率），定位指標只算在「最終真的判成 filter」的子集上（避免「沒判到」跟「判到但看錯位置」混在一起）。**結果**：eye_enlarging（IoU 0.467→0.549，+0.082）、face_reshaping（0.466→0.516，+0.050）在 v8.11 上定位品質持平或更好，第 5 節結論可合理延伸到 production；**whitening 是例外**：IoU 只小降（0.448→0.372），但 **PointingGame 從 0.880 崩到 0.357**——熱圖形狀大致還蓋到 GT，但最亮像素常落在 GT 外，是 v8.11 specific 的新問題，v8.8 沒有。coverage 面也對得上：whitening 的 Layer1 routing coverage 四型別最低（86.9%），跟已知的「real recall 偏低」模式一致。smoothing coverage 100% 但 IoU/PointingGame 都偏低（0.398/0.296），延續第 7 節「smoothing 是 whole-face GT，熱區精確度本來就沒有意義」的既有判斷。完整輸出：`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`（含逐張 per_image，供後續診斷 whitening 峰值問題）
  - **✅ 2026-08-13 診斷已完成（原列為低優先，撿起來做了），找到明確根因：peak 位置不隨圖片變化，不是 GT/preprocessing bug**：`phase2_whitening_pointinggame_diagnostic.py`，對 20 張 whitening PointingGame==0 失敗案例逐張重跑推論，取熱圖峰值座標並分類落點（人臉 bbox 內/外、8 個命名 region box 內/間隙）。**結果：20 張中 17 張（85%）的熱圖峰值座標落在同一個絕對像素點（224×224 標準化座標系下的 (80,111)）3px 範圍內**——不管人臉在畫面中的實際位置、縮放、髮型、眼鏡、背景為何，峰值幾乎釘死在同一點（`results/phase2_whitening_peak_diagnostic_20260813/contact_sheet.png` 目視確認：不同人臉尺寸/位置下，白色星號標記幾乎都落在畫面中同一相對位置）。**這排除了原本設計要區分的兩種結果**（① GT/preprocessing 對齊 bug ② 峰值落在合理但不精確的臉部位置），指向第三種、更明確的成因：**Grad-CAM++ 對 whitening 的峰值定位被一個近乎常數的位置偏誤主導，不是圖片內容驅動的定位**。**決策：不修正**（本次任務性質是診斷不是修復），但這個發現**強化（而非削弱）現行 whitening whole-face、不做精確定位主張的政策**——峰值定位若不隨圖片內容變化，本來就不該被讀成「指向了什麼」，現行政策的假設完全正確。完整記錄見 `docs/EXPERIMENT_REGISTRY.md` P2-P0 條目的 follow-up 段落
- [x] ✅ **2026-08-13 Phase 2 收斂：filter XAI evidence-tier 規則鎖定 + fake region localization 正式標記 pending**：`docs/phase2_story.md` 第 11 節新增按 filter type 分級的鎖定表（eye_enlarging=region-level／face_reshaping/whitening/smoothing=whole-face 且不可用峰值做精確主張），fake region-level 定位明確標記 `pending`（非暫停非放棄），解除條件是①取得 FF++ masks ②Layer1 對 FF++ 來源先有基本辨識能力（stretch goal FF++ fake recall≥70%，目前未達）。同時在 `docs/EXPERIMENT_REGISTRY.md` 新增「Cross-Phase Decision: Phase 1 Freeze Gate」章節（純記錄，Phase 1 才是執行/驗收方）——A類 freeze gate（v8.11 核心指標幾乎全過，僅缺 iPhone 實測）／B類 stretch goal（不阻擋凍結）／C類 robustness gate（要求逐 class recall，不能只看 overall accuracy）。**已用 TODO.md 核對確認 v8.16 校準後數字（joint recognition 2.02%→4.53%）為真實記錄，非誤植**，新增 P1-2 registry 條目取代先前「v8.16 尚未驗證」的暫時性記錄
- [x] ✅ **2026-08-13 新增 runtime vs offline evaluation 措辭規範**：`docs/xai_evidence_schema.md` 與 `docs/phase2_story.md` 第 10 節，明確禁止「系統透過比較原圖與修圖後圖片發現……」這類措辭——正式推論永遠只收到一張圖，pair 比對只發生在離線評估腳本裡。已核對 `pipeline.py` 現有 `TEMPLATES` 本來就沒有這個問題，不需改動


**Filter 域泛化研究（C1，已從 Bonus 升級為有明確依據的主線方向）**
- [x] ✅ **2026-08-11 Shadow filter domain gap 診斷完成**：確認 Shadow 為配對設計、balanced accuracy 僅 43.5%（**低於 50% 退化基線 = 反資訊**）、錯誤方向與 True Test 完全相反；並以 LAB ΔE 量測**排除**「濾鏡效果太弱」的平凡解釋（Shadow 濾鏡反而強 1.46x）。結論：跨濾鏡演算法泛化良好（Alibaba 98.1%）、**跨底圖攝影風格泛化失敗**。詳見「Shadow filter recall 卡住之謎」專節
- [ ] 擴充filter訓練來源的**底圖多樣性**（依上述診斷，這是證據唯一指向的修法；RetouchingFFHQ原始資料當主來源，VGGFace2 pipeline降級為補充）
- [ ] 驗證擴充來源後Shadow **balanced accuracy** 能否拉回 50% 基線以上（改用配對指標，不再用會誤導的單邊 filter recall）

**Open-set 行為設計（C2，低成本）**
- [ ] `unknown_filter` 類別設計（信心閾值，低於門檻輸出unknown）
- [ ] Unseen filter/fake資料集上的open-set評估（precision/recall/coverage三指標）

**文獻對照實驗（E，成本較高）**
- [x] ✅ **2026-08-23 跑FF++ benchmark（與文獻SOTA直接可比較的數字）—— 已完成，見下方 E 章節詳細條目**
- [ ] RetouchingFFHQ MAM頭對頭比較實驗（量化「輕量替代」主張）— **2026-08-23 判定為目前不可執行**，五個獨立阻礙（缺未修圖原圖／Megvii 無 level 標註／標籤空間不相容／官方 split 未公開／無 Tencent），見下方 E 章節
- [ ] 查證FF++/SBI/MLFF+CNN/FAME等文獻數字（**2026-08-23 部分完成**：FF++ 原論文數字已核實，SBI/MLFF+CNN/FAME 仍未驗證）

**StyleGAN3身份重疊後續（F，低成本可選）**
- [ ] 官方NVIDIA StyleGAN3 pretrained checkpoint + random latent零身份依賴驗證集
- [ ] （大型/獨立專案）Identity-disjoint retrain：DF40全部方法依1,028 identity切分重訓

**外部資源申請（G，使用者行動項）**
- [ ] Tencent RetouchingFFHQ子集申請（[申請表](https://fdmas.github.io/Application_RetouchingFFHQ_new.pdf)）

**其他低優先**
- [ ] 2×2或3×2 ablation matrix（spatial-only vs spatial+FFT × hard_neg強度 × class weight）
- [ ] DF40 Face Editing (FE) 歸類決策（語義偏filter，若加入需重新確認標籤）— **2026-08-23 taxonomy對照完成，決策維持不變**：`results/research/df40_taxonomy_followup_20260823/FINDINGS.md` Task B 已把 FE vs. 本專案 fake/filter 的對照寫清楚——FE 語義上偏identity-preserving（近filter），但屬通用屬性編輯（表情/配件等），非本專案filter定義的消費級美顏語義（磨皮/美白/大眼/瘦臉），**不建議在無新GT標籤前併入任一類別**，本輪未推翻此決策，只是把理由書面化並附上DFFD/FF++/DF40三方對照表。
- [ ] H.264 domain gap進階：Wavelet Transform取代FFT branch（架構改動大）

---


>  `dev` 分支後，`splits/`、`shufflenet_v2_layer1_v811c.pth`、`shufflenet_v2_layer2_v811.pth` 已一併推送，可直接用來 fine-tune，不用從頭訓練。

### 任務一：手機端 FFT 分支相容性問題 — ✅ **2026-08-11 已完全解決**

> **結論先講**：blocker 已解除。用「固定尺寸 DFT ⇒ 常數矩陣乘法」重寫 FFT 分支，數學上**完全等價**（非近似），因此**現有權重零重訓直接沿用**。fp32 TFLite 產出物已通過「真的載入 + 真的推論 + 準確率不變」的驗證，**True Test 三個 class 的 recall 與 PyTorch 完全相同**。專案「可在邊緣裝置部署」的核心主張現在是真的、且有可執行的產出物佐證。

**解法**：`mobile_fft.py`。對固定 224×224 輸入，2D DFT 可寫成固定矩陣乘法 `X = W_H @ x @ W_W / sqrt(HW)`，拆成實部/虛部後只用 MatMul/Mul/Add/Sqrt/Log（全部是 TFLite builtin op）。`fftshift` 是固定的循環索引置換，直接**摺進常數矩陣**（把 W_H 的列、W_W 的行 roll `N//2`），執行期零成本、也少一個 op。成本：4 個 224×224 fp32 常數矩陣（約 800 KB）+ 6 次 batched matmul。

**驗證（`verify_mobile_fft.py`，三層檢查全過）**：
| 檢查 | 結果 |
|---|---|
| 頻譜 vs `torch.fft` | max abs err 4.7e-4（random）/ 8.0e-4（真實照片），log-spectrum 值域 [-10.2, 4.1] |
| 完整模型 logits（真實訓練權重） | max\|Δlogit\|=2.4e-7、max\|Δprob\|=6.0e-8，argmax 完全相同 |
| 端到端階層決策（120 張真實圖） | **120/120 一致**，max\|Δconfidence\|=1.6e-5 |

**TFLite 產出物驗證（`export_mobile_tflite.py` + `benchmark_mobile_artifacts.py`）**——不把「有產生檔案」當成功，每個產出物必須通過 G1 ONNX 匯出 → G2 TFLite 轉換 → **G3 stock `tf.lite.Interpreter` 真的載入並 allocate**（原本 `ONNX_DFT` 就是死在這關）→ G4 數值與 PyTorch 相符：

| 產出物 | 載入 | 大小 | 延遲 | True Test filter / real / fake recall |
|---|---|---|---|---|
| PyTorch fp32（參考） | — | — | — | 93.6% / 68.4% / 99.6% |
| **TFLite fp32** ✅ | **OK** | **20.91 MB**（兩層各 10.46） | **14.4 ms/張**（含兩階段，Layer2 觸發 581/769=76%） | **93.6% / 68.4% / 99.6%（與 PyTorch 完全相同，769/769 決策一致）** |
| TFLite fp16 ❌ | **失敗** | 10.5 MB | — | 整張 graph（含 input）都是 fp16，stock CPU runtime 的 CONV_2D kernel 拒絕（`input_type == kTfLiteFloat32 \|\| ... was not true`）→ 需 GPU delegate 才能跑，不是 CPU 可攜產出物 |
| TFLite dynamic-range int8 ❌ | 載入OK但**輸出 NaN** | 6.74 MB | 614 ms（比 fp32 慢 40x） | 0% / 100% / 0%（全部判 real，模型實質毀掉）|

**int8 失敗的根因已查清（`diagnose_int8_collapse.py` → `diagnose_int8_collapse2.py`，過程中推翻了自己第一個假設）**：
- 第一個假設「DFT 常數矩陣量化受損」**被自己的數據推翻**：模擬 int8 量化 DFT 常數，max\|Δprob\|=0.013、**decision flips=0/30**，幾乎無傷；量化 conv+linear 權重也只有 1/30 翻轉。**權重量化解釋不了整個模型崩潰**。
- 真正原因是 **activation 量化**（dynamic-range quantization 會在執行期對啟動值做 per-tensor int8，前一個測試完全沒模擬到）：FFT magnitude tensor 值域 `1.98e-08 ~ 1.51e+02`，**動態範圍 7.6×10⁹ 倍**；per-tensor int8 的 step = 1.187，導致 **98.08% 的頻譜 bin 被量化成 0**，log-spectrum 誤差 mean=14.4（比權重量化的 0.018 差 **813 倍**），實測 int8 產出物輸出直接是 **NaN**。
- **這是「把原始 FFT magnitude 頻譜放進量化 graph」的本質性問題，不是我們匯出流程的 bug**——任何 per-tensor 量化都無法同時涵蓋 10 個數量級的動態範圍。
- **若日後真的需要壓到 int8**：已知可行路徑是**選擇性量化**（conv stack 走 int8、頻譜計算保持 float），證據是上面兩個隔離實驗（DFT 常數 int8 → 0/30 翻轉、conv+linear int8 → 1/30 翻轉），但目前 fp32 的 20.91 MB / 14.4 ms 對手機部署已完全可接受，不急。

**部署建議（可直接寫進論文）**：出 **fp32 TFLite，兩模型合計 20.91 MB、桌機 CPU 14.4 ms/張**，準確率與 PyTorch 逐張相同（769/769）。fp16 需 GPU delegate；int8 因 FFT 頻譜動態範圍問題不可用（附上述量化分析）。

**未改動 `pipeline.py` 的 `FFTBranch`**：桌機/GPU 上 `torch.fft`（cuFFT）比 matmul DFT 快，兩者已驗證數值等價，故維持「訓練與桌機推論用 torch.fft、部署匯出走 `mobile_fft.py`」的標準做法，非分歧實作。

**新增檔案**：`mobile_fft.py`（等價 DFT 實作）、`verify_mobile_fft.py`（等價性驗證）、`export_mobile_tflite.py`（四關匯出驗證）、`benchmark_mobile_artifacts.py`（三種精度 × True Test gate 對照，輸出 `results/mobile_deployment_benchmark.json`）、`diagnose_int8_collapse.py` / `diagnose_int8_collapse2.py`（int8 根因分析）。

- [x] ✅ **2026-08-22 v8.17 production stack 重新匯出＋驗證完成（Layer1=v817sbi + Layer2=v811 不變 + Artifact classifier=v6，後兩者第一次／首次匯出手機格式）**：三個模型 G1-G4 全過（ONNX 匯出→TFLite 轉換→`tf.lite.Interpreter` 真的載入→數值與 PyTorch 相符，誤差皆比 1e-3 門檻小 2-4 個數量級）。額外做了比單模型 8 張圖更嚴謹的**全鏈路 True Test（769 張）決策一致性驗證**：TFLite 三階段串接 vs PyTorch 三階段串接，label **769/769（100%）一致**，filter 圖的濾鏡子型別 **298/298（100%）一致**；recall 數字（fake 99.63% / filter 91.97% / real 72.40%）與濾鏡子型別準確率（225/249=90.36%）在 PyTorch 與 TFLite 兩邊完全相同，且與既有 v8.17／v6 核准文件數字吻合。Artifact classifier（純 ShuffleNetV2 + Linear 頭，無 FFT 分支）確認不需要 `mobile_fft.py` 的等價改寫，ONNX 圖 15 個 op type、0 個 FFT/DFT op，直接可轉。**大小/延遲新數字**：Layer1+Layer2 兩模型（與舊數字對照組）20.91 MB（舊 20.913 MB，打平）、16.72 ms/張（舊 14.37 ms/張，高約 2.35ms，判斷為桌機背景負載雜訊而非架構退化，因為同一組模型架構完全沒變，建議之後在空機重測一次再寫進論文精確數字）；**三模型合計首次量測 = 25.75 MB**（Layer1+Layer2+Artifact，比 Freeze Gate 表原本只針對兩模型量測的 ≤25MB 門檻高出 0.75MB/3%——⚠️ **待 reviewer 裁定**：該門檻範圍是否本來就該含 artifact classifier，見完整報告 §5，本輪不擅自認定）；三階段平均延遲（依 True Test 真實類別比例，Layer2 觸發 74%、Artifact 觸發 39%）15.68 ms/張，最壞情況（每張都跑滿三階段）22.97 ms/張。完整報告、六支可重跑腳本、含 side-by-side 對照表的桌機示範腳本（`desktop_tflite_demo.py`，8/8 張 PyTorch/TFLite 決策一致）皆在 `results/mobile_export/v817_20260822/`（`EXPORT_AND_VERIFY_REPORT.md` 為完整版）。未修改任何 production checkpoint 或 `pipeline.py`。

<details><summary>原始問題描述（保留供對照）</summary>

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

（採用了方向 1「矩陣乘法手動實作 DFT」，並確認它是**數學等價而非精度取捨**，所以方向 2「砍掉 FFT 分支換取可部署」的犧牲完全不需要付，方向 3 的 Flex delegate 相容性風險也不用承擔。）

</details>

### 任務二：Layer 2（fake vs filter）辨識瓶頸

- **現況**：Layer 2 的filter recall卡在15.7%-28.1%，多輪嘗試無實質突破：
  | 嘗試 | 結果 |
  |---|---|
  | Layer2b（降oversample+加權） | filter recall 22.4%，但fake_diffusion recall退步9.6pp |
  | Layer2c（更保守加權） | filter recall 21.0%，同樣無淨改善 |
  | 原始Layer2（無手動加權，目前部署版） | filter recall 15.7% |
- **已知根因**：訓練資料裡hard negative（fake+filter邊界樣本）比例拉高，模型會把決策邊界推向「fake」，犧牲對真正filter class的辨識力——純調loss weighting/oversample比例已證實無效。
- **2026-08-10新發現線索（⚠️ 2026-08-10複查時發現並修正一次資料錯誤，見下方說明）**：v8.11壓力測試顯示，fake套濾鏡後的誤判**不是均勻分布在所有濾鏡類型**，而是集中在3種，且誤判方向幾乎都是「誤判成real」：
  | 濾鏡類型 | 誤判率 | 誤判方向 |
  |---|---|---|
  | whitening | 13.2%（最差） | 幾乎全部→real |
  | eye_enlarging | 10.1% | 幾乎全部→real |
  | face_reshaping | 8.7% | →real為主 |
  | smoothing/combined系列 | <1.1%（很穩） | — |
  端到端total（含base）：93/2289=4.06%，與原記錄3.93%差0.13pp（雜訊範圍內，可接受）。
  建議下一輪不要對所有filter類型平均施力，**針對whitening/eye_enlarging/face_reshaping這三種類型加強hard negative挖礦**。
  - **⚠️ 資料完整性修正**：這批數字原本用的`results/stress_test_v811_pipeline.json`檔案，經查證是用**已淘汰的Layer2c權重**跑出來的（檔案時間戳落在Layer2c訓練完成後、拍板改回原始Layer2之前，該版本從未重新用最終權重跑過），舊檔案算出的端到端誤判率4.33%精確吻合文件裡記錄的「Layer2c誤判4.33%，比原始差」——同一個數字被誤植成「原始Layer2最新壓力測試結果」。已用明確指定的最終權重（`shufflenet_v2_layer1_v811c.pth`+`shufflenet_v2_layer2_v811.pth`）重新執行`AIGuard/stress_test_v811_pipeline.py`，本表為修正後數字，質性結論（whitening/eye_enlarging/face_reshaping最差、誤判方向集中real）不變，僅精確百分比修正。`generate_fake_filter_misclass_chart.py`圖表已同步用修正後資料重繪。
- **要解決的問題**：在不犧牲real recall跟fake_diffusion recall的前提下拉高filter recall，且要能通過完整7項gate評估才能取代目前v8.11。
- **素材**：
  - `results/stress_test_v811_pipeline.json`（原始壓力測試資料，2026-08-10已用最終權重重跑修正過）
  - `generate_fake_filter_misclass_chart.py`（分析腳本，可直接跑或改）
  - `AIGuard/train_v811_layer2.py`、`train_v811_layer2b.py`、`train_v811_layer2c.py`（過去三次嘗試，避免重複）
  - `splits/v811_layer2_train.txt` 及變體

**⚠️ 2026-08-10 重要重新框定：這其實是Layer 1的問題，不是Layer 2的**——`stress_test_v811_pipeline.py`的`run_pipeline()`邏輯顯示，凡是最終判成「real」的案例，全部是Layer1單獨決定的（Layer1判real就直接return，根本不會進Layer2；Layer2只可能輸出fake或filter，永遠不會輸出real）。既然誤判方向幾乎全部是「→real」，代表**真正的漏洞在Layer1，不是Layer2的fake/filter辨識力**。本節標題「Layer2瓶頸」有誤導性，實際要修的是Layer1對fake+filter組合圖的辨識力，Layer1既有的round1/round2 mining（見下方「已解決」章節v8.11 Layer1三輪迭代）其實已經是同一個方向的嘗試。

**2026-08-10 新增分析：3×3轉移矩陣（套濾鏡前 base_pred × 套濾鏡後 filtered_pred）**，把「濾鏡真的造成新失敗」跟「base本身就判錯、濾鏡沒救回來」拆開看：
| 套濾鏡前\後 | fake | real | filter |
|---|---|---|---|
| fake（套濾鏡前判對） | 2099 | 52 | 1 |
| real（套濾鏡前就已判錯） | 97 | 40 | 0 |

真正「濾鏡造成的新失敗」只有53筆（2.3%）；137筆（6.0%）是套濾鏡前就已經判錯，其中97筆（70.8%）套上濾鏡後反而被「救回來」。**依類型拆解「濾鏡造成的新失敗」數量**：whitening_medium=24（最多，真正的主要禍首）、eye_enlarging=15、face_reshaping=13、smoothing/combined系列=0-1（幾乎不造成新失敗）。這比單純的誤判率表格更精確，建議hard-neg挖礦優先鎖定whitening。

**2026-08-10 架構層級的重要發現（跟7/24 meeting舊投影片數字對照後發現）**：v8.11階層式架構上線前（flat 3-class，約v8.8時期）測過的舊版fake+filter壓力測試（`AIGuard/stress_test_fake_filter.py`最初commit版本，20張圖×6種濾鏡=120次推論），誤判方向剛好相反——**0%誤判成real，最高50%誤判成filter**。兩次測試用的是不同模型架構（flat softmax vs 階層式Layer1/Layer2），這代表**架構改動本身把fake+filter的失敗路徑從「filter方向」換成了「real方向」**：flat softmax時代，濾鏡抹掉fake痕跡後剩餘訊號被误判成"filter"（同一層競爭）；階層式架構下，濾鏡把fake痕跡洗得夠乾淨時，Layer1直接判real，根本輪不到Layer2判fake/filter。**這是hierarchical架構解決real recall問題的同時，引入的一條新失敗路徑，值得寫進論文Discussion當作誠實的架構trade-off**，目前完全沒有文件記錄這個對比。

**2026-08-10 已排除的假說：不是hard-neg資料量不足**——查證Layer1c訓練資料裡，whitening/smoothing/eye_enlarging/face_reshaping四種類型的hard-neg數量幾乎相等（4250-4516張），不是whitening被少練。

**✅ 2026-08-10 Layer1d訓練完成，確認改善且無副作用，準備跑完整gate評估**：用round4新挖到的383張hard neg（全新來源，見下方）+ 原Layer1c訓練資料，從Layer1c checkpoint繼續fine-tune 5 epochs（`AIGuard/train_v811_layer1d.py`，best macro F1=0.9802）。
- **fake+filter端到端誤判**：4.06%→**3.71%**（whitening 13.2%→11.1%、face_reshaping 8.7%→7.7%、eye_enlarging 10.1%→9.8%，三種目標類型全面改善，smoothing/combined維持不變）
- **Shadow real recall**：75.5%→**76.9%（不降反升+1.4pp）**；filter→manipulated 50.2%→51.2%；binary AUROC=0.7907
- **無蹺蹺板效應，兩邊都變好**。

**✅ 2026-08-10 完整gate評估通過，Layer1d正式取代Layer1c，拍板成為v8.11新版本**：
| Gate | Layer1c（原） | Layer1d（新） | 門檻 | 判定 |
|---|---|---|---|---|
| Shadow real recall | 75.5% | 76.9% | ≥80% | 未過但更接近 |
| True Test filter recall | 94.0% | 93.6% | ≥92% | ✅ 過關 |
| fake+filter端到端誤判 | 4.06% | 3.71% | ≤2% | 未過但持續改善 |
| AIGuard/unseen AUROC | 0.8112 | 0.8150 | ≥0.70 | ✅ 過關，更好 |
| CelebA real recall | 99.7% | 99.7% | ≥95% | ✅ 打平 |
| StyleGAN2 fake recall | 99.7% | 99.6% | ≥95% | ✅ 過關 |

沒有任何一項退步超過雜訊範圍，是淨正向改善。**已更新`pipeline.py`的`LAYER1_WEIGHTS_PATH`指向`shufflenet_v2_layer1_v811d.pth`**，Layer1c保留在磁碟供對照。fake+filter誤判跟Shadow real recall兩項硬性gate仍未達標，但方向持續正確。

**✅ 2026-08-10 補齊Layer1d完整成績單**（前次gate評估用的是`eval_v811_gates.py`聚合數字，這次補上per-type拆解＋獨立algorithm-OOD重新驗證，全部明確指定`shufflenet_v2_layer1_v811d.pth`+`shufflenet_v2_layer2_v811.pth`跑出）：

| 測試來源 | 結果 | 備註 |
|---|---|---|
| True Test filter recall（總） | 233/249 = **93.6%** | gate ≥92% ✅ |
| ├ smoothing | 63/63 = 100.0% | `eval_truetest_filter_bytype_v811.py` |
| ├ whitening | 59/62 = 95.2% | |
| ├ eye_enlarging | 51/62 = 82.3% | 相對最弱，跟Alibaba/Shadow同型別偏弱方向一致 |
| ├ face_reshaping | 60/62 = 96.8% | |
| Alibaba filter recall（總，21,151張，跟訓練資料底圖同分布但演算法完全獨立；⚠️ **2026-08-21 更正：非 OOD**——原標題為「Alibaba OOD filter recall」，實測與訓練資料有 23.5%（4,980/21,151）**內容**重疊，不只是「底圖同分布」而是同一批照片） | **98.1%**（20,743/21,151） | 比Layer1c時期的97.8%略升，不是退步；`eval_ali_ood_v811.py` |
| ├ EyeEnlarging / FaceLifting / Smoothing / Whitening | 98.1% / 97.0% / 99.9% / 97.3% | 各強度(30/60/90)均在97.8-98.3%區間，無明顯強度依賴 |
| AIGuard/unseen fake AUROC | 0.8150 | gate ≥0.70 ✅ |
| CelebA real recall (n=3000) | 99.7% | gate ≥95% ✅ |
| StyleGAN2 fake recall (n=3000) | 99.6% | gate ≥95% ✅ |
| Shadow real recall | 76.9% | gate ≥80%，未過但持續逼近 |
| Shadow filter→manipulated recall | 51.2% | 非deployment gate，見下方Shadow filter recall域差討論 |
| fake+filter端到端誤判（AIGuard/unseen×8種filter壓力測試） | 3.71% | gate ≤2%，未過但持續改善 |

**結論：True Test跟Alibaba兩個filter評測來源都在93%+，跟Shadow set的15-28%形成強烈對比，證實Shadow偏低是VGGFace2底圖風格造成的domain gap，不是模型filter辨識力普遍弱（完整推理見對話記錄）。**

**❌ 2026-08-10 FFHQ_four_process 859張未用圖片審計失敗，判定不可用作filter OOD**：依使用者指示的審計流程（路徑/身份重疊 → 演算法重疊 → 才跑推論，任一關不過就不當OOD benchmark）逐項檢查：
1. `FFHQ_four_process`（無品牌）與`FFHQ_megvii_four_process`（Megvii）兩個資料夾的base FFHQ index range**完全相同**（皆為60002-69999），並非像Alibaba（17000-19999）那樣是獨立不重疊的company index區塊——這兩個資料夾是同一批10K張FFHQ底圖，各自套用不同濾鏡pipeline（無品牌"four"組合 vs Megvii"four"組合）。
2. 859張未用圖片中，**727張（84.6%）的base FFHQ index已經以megvii版本用進`v811_layer2_train.txt`訓練**——即同一張人臉照片，訓練時看過megvii濾鏡版本，現在要當「OOD」測的是同一張臉的無品牌濾鏡版本，不構成identity-disjoint。
3. 剩餘132張即使身份沒撞，套用的仍是`v86_train_filter.txt`裡已有6,872張同源訓練資料的**同一套「four」濾鏡演算法**，樣本量小且演算法不新，不足以構成獨立OOD benchmark。
- **判定：不跑推論、不採用此資料源、不因此觸發round5**。稽核腳本：`check_ffhq_four_process_overlap.py`（859張未用清單）、`check_ffhq_four_identity_overlap.py`（身份重疊比對，727/859）。
- ~~目前唯一驗證過的乾淨filter algorithm-OOD只有Alibaba一組（見上方98.1%）。~~若要新增新的filter OOD來源，需要另找index-range與現有訓練資料（four/megvii/ali三個block）都不重疊的RetouchingFFHQ分支，或完全不同的第三方filter資料集。
  > ⚠️ **2026-08-21 更正**：刪除線那句已不成立。P1-R11 內容層級稽核證實 Alibaba
  > （`FFHQ_ali_process`）本身與訓練資料有 **23.5%（4,980/21,151）內容重疊**（`AIGuard/real`
  > 與 `filter_data/*` 含相同 FFHQ 底圖照片、以不同檔名存在），**不是乾淨的 filter
  > algorithm-OOD**。正確說法：**本專案目前沒有任何一組經內容層級驗證為乾淨的
  > filter algorithm-OOD 資料源。** 且**新來源的篩選條件必須升級**——只比對 index-range
  > 不夠（那正是這次漏掉的路徑），必須用內容金鑰（解碼像素 SHA256 + 感知雜湊篩選後以
  > NCC/MAD 裁決，見 Known trap #3）對**全部**訓練 split 查重。
  > filter 側目前有效的跨域對照是 **True Test vs Shadow**（同一套自建濾鏡程式碼、不同底圖攝影風格）。

**2026-08-10 round3挖礦確認：舊候選池已榨乾，下一步必須換全新來源**——用現任Layer1c重新掃描round2用過的同一個候選池（`v89d_candidate_pool.txt`，26,526張target-type候選圖，`mine_v811_layer1_round3.py`），結果yield=**0.03%**（僅9張，eye_enlarging 1/face_reshaping 7/whitening 1），對比round2用layer1b掃同一池子的yield=1.16%（303張），**掉了30幾倍，證實這個候選池已經被前兩輪挖乾**，剩下的圖對現在的模型來說幾乎都不夠難，繼續在這裡挖沒有意義。**下一步（尚未執行）**：需要一個全新來源的candidate pool——例如從`AIGuard/fake`裡找還沒被`v89d_candidate_pool`用過的圖，重新套用whitening/eye_enlarging/face_reshaping濾鏡產生新的候選圖，再用layer1c掃描挖礦。產出的9張路徑存在`splits/v811_layer1_round3_mined.txt`，量太少不足以單獨拿去訓練。

**2026-08-10 順便查證確認、影響很小的問題**：`pipeline.py`的`hierarchical_predict()`（production用，3個複合機率直接三選一）跟`eval_v811_gates.py`的`predict()`（gate評測用，嚴格Layer1優先二階段）決策邏輯數學上不保證完全一致。實測True Test set（769張）僅1張（0.13%）受影響，確認問題真實存在但可忽略，現有gate數字不用重跑，但論文方法論章節若要嚴謹應註明。完整說明見`docs/Dataset 清單.md` 2026-08-10條目。

---

## ⚠️ True Test 配對設計問題（2026-08-11 發現，影響主 gate 的報告方式）

**怎麼發現的**：跑手機端 benchmark 時，順手把 True Test 三個 class 的 recall 一起印出來，發現 **real recall 只有 68.4%，但 CelebA real recall 是 99.7%**——兩個都是「真實照片」，差 31pp，而現有 gate 清單裡沒有任何一項解釋得了這個落差。v8.11 混淆矩陣顯示 real 的 82 個錯誤**全部**跑去 filter、沒有一個跑去 fake，方向性太乾淨，不像隨機誤差。

**查證結果（`audit_truetest_pairing.py`）**：
| 檢查 | 結果 |
|---|---|
| True Test filter 與 real 是否同一批來源照片 | **是，249/249（100%）完全配對**；215 個 real 身份 / 214 個 filter 身份也 100% 重疊 |
| True Test real 的照片有無「濾鏡雙胞胎」洩漏進訓練 | **0/250（0.0%）**，photo-level 乾淨（v811_layer2 / v86 / v85 三份 filter split 都查過） |
| True Test filter 的來源照片有無進訓練 | **0/249（0.0%）**，乾淨 |
| 身份層級重疊 | 84/215（39.1%）身份曾以「濾鏡版本」出現在訓練資料（較弱的 confound，本專案既有已知模式） |

**資料本身是乾淨的（無 photo-level 洩漏），問題純粹在報告方式**：既然是配對設計，「filter recall 93.6%」不能單獨當作濾鏡偵測能力的證據——**一個永遠回答「filter」的退化模型，在這個測試集上 filter recall 會是 100%、照樣通過 ≥92% 的 gate**。

**配對設計該用的指標（`eval_truetest_paired.py`，249 對）**：
| 指標 | Layer1c | **Layer1d（現役）** | 說明 |
|---|---:|---:|---|
| filter recall（原本的 headline gate） | 94.0% | 93.6% | 單看會誤導 |
| 同一批來源照片的 real recall | 67.1% | 68.7% | 從未跟 filter recall 並列報告過 |
| **balanced accuracy** | 80.5% | **81.1%** | 誠實的整體數字 |
| **strict per-pair accuracy（兩張都要對）** | 61.0% | **62.2%** | 最嚴格 |
| 退化基線（永遠答 filter / 永遠答 real） | — | 50.0% balanced | 模型確實有在辨別，遠高於基線 |

**逐對結果拆解（Layer1d）**：both correct 62.2%、**filter-biased 31.3%（乾淨照片也被判成 manipulated，這些 pair 的「filter」答案不構成偵測到濾鏡的證據）**、missed filter 6.4%、**both wrong 0.0%（從無反向錯誤，是好訊號）**。

**逐濾鏡類型的誠實偵測率（both ok，非 filter recall）**：face_reshaping 67.7% > whitening 64.5% > smoothing 63.5% > eye_enlarging 53.2%。注意 smoothing 的 filter recall 是 100%（missed 0%）但 filter-biased 高達 36.5%——**它漂亮的 recall 有超過三分之一是「反正都會說 filter」貢獻的**。

**副作用：Layer1c→Layer1d 的決策在修正後的指標下反而更站得住腳**。原本 Layer1d 在 filter recall 上看起來小輸 0.4pp（94.0%→93.6%），一度被記為「打平內雜訊」；改用配對指標後 Layer1d **兩項都贏**（balanced +0.6pp、strict +1.2pp），因為它換來的 real recall 提升（+1.6pp）比讓出的 filter recall 更多。原決策無需推翻，且理由更硬。

**⚠️ 另一個需要在論文誠實揭露的前提問題**：LFW 是名人新聞照，本來就大量存在專業修圖／妝容／調色。所以「real」這個 ground truth 實際意義是「**我們沒有對它套濾鏡**」，不是「經查證未經任何修飾」。31.3% 的 filter-biased 裡有多少其實是模型判對、而是 GT 標籤過於寬鬆，目前無從得知。這個限制對 real recall 是系統性不利，撰稿時應與配對設計一併說明，不要只把它寫成模型缺陷。

**論文建議措辭**：主表改報 **balanced accuracy（81.1%）與 strict per-pair accuracy（62.2%）**，filter recall 與 real recall 併列為子項並明確標註兩者來自同一批來源照片；不要單獨引用 93.6%。既有各版本的比較（v6→v8.11）皆使用同一測試集與同一指標定義，**歷史比較的相對關係不受影響**，只是絕對數字的解讀要換框架。

- [ ] **待辦（純寫作）**：把上述配對設計說明與 balanced/strict 指標補進 `docs/paper_outline.md` 的 Results 與 Limitations，並更新 `docs/phase1_story.md` 對應段落
- [ ] **待辦（可選，成本低）**：若要一個**非配對**的乾淨 filter gate，可用 Alibaba filter recall（98.1%，底圖與 real gate 無配對關係）當主要 filter 偵測證據，True Test 改定位為「同源照片配對辨別難度測試」
      > ⚠️ **2026-08-21 更正**：原文寫「Alibaba **OOD**」。該集**非 OOD**（與訓練資料
      > 23.5% 內容重疊）。「非配對」這個性質**仍然成立**（底圖與 real gate 無配對關係），
      > 所以本待辦的用途沒有失效；但若採用，必須同時揭露 23.5% 內容重疊，
      > 且**不可**把它當成跨域／分布外證據。

---

## 🔬 Shadow filter recall 卡住之謎：2026-08-11 查清，是真實域泛化失敗（且比原本認知更嚴重）

> 這一項在 TODO 裡掛了很多版（C1 章節、Layer2b/2c 三次嘗試都失敗）。用配對分析 + 效應量量測終於把成因釘死，並**推翻了我自己中途提出的一個假設**。

**關鍵發現：Shadow 也是配對設計**（`shadow_filter/eye_enlarging_n000001_0109_03.jpg` ↔ `shadow_vggface2_real/n000001_0109_03.jpg`），而且**跟 True Test 用的是同一套自建濾鏡演算法**——只有底圖照片風格不同（VGGFace2 vs LFW）。這讓兩者可以做嚴格的對照實驗（`eval_paired_both_domains.py`）：

> ⚠️ **2026-08-11 本節數字已修正一次（重要方法錯誤，自己查出）**：初版分析直接 glob `shadow_*/` **原始資料夾**（472 對），但官方 Shadow 評測腳本 `eval_v811_layer1_shadow.py` 讀的是 `clean_output/clean_paths.txt`（Step1+Step2 清洗後，real 289/500、filter 280/472，剔除無臉/閉眼/墨鏡/嬰兒/低解析）。用未清洗資料會**灌大錯誤率且與既有文件數字不可比**。已全部改用清洗後清單重跑（**279 對**）。**驗證修正正確的證據：修正後 Shadow real recall = 77.1%，與文件既有的 76.9% 吻合**（未修正版是 69.5%，對不上）。下列全為修正後數字。

| 資料集（同一套濾鏡演算法） | 配對數 | filter recall | real recall | **balanced** | **strict** |
|---|---:|---:|---:|---:|---:|
| True Test（LFW 底圖） | 249 | 93.6% | 68.7% | **81.1%** | 62.2% |
| Shadow（VGGFace2 底圖） | **279** | **10.0%** | **77.1%** | **43.5%** | **7.2%** |

**錯誤方向完全相反**（headline recall 完全看不出這件事）：
| 資料集 | both ok | filter-biased（乾淨照也判 manipulated） | missed filter（濾鏡照判 real） | both wrong |
|---|---:|---:|---:|---:|
| True Test | 62.2% | **31.3%** | 6.4% | 0.0% |
| Shadow | 7.2% | 2.9% | **69.9%** | **20.1%** |

**⚠️ 最嚴重的一點：Shadow balanced accuracy = 43.5%，低於 50% 的退化基線**（永遠答 real 也有 50%）。也就是說在 VGGFace2 風格上，模型的 manipulated 判斷不只是「保守」，而是**反資訊（anti-informative）**——它偏離「一律答 real」的那些決策，多數是錯的。這比文件裡原本記的「filter recall 卡在 15-28%」嚴重，因為原本的寫法讓人以為只是靈敏度不足。

**❌ 我中途提的「這只是決策邊界平移（calibration 問題）」假設被數據推翻**：如果只是邊界平移，balanced accuracy 應該兩邊接近、只是 recall 分配不同。實測 balanced 差距 37.6pp（81.1% vs 43.5%），**接近 headline 差距（83.5pp）的一半，不是可忽略的殘差**，而且 Shadow 掉到基線以下——這不是平移能解釋的，是真的失去辨別力。

**✅ 已排除「Shadow 的濾鏡根本沒套上去／效果太弱」這個平凡解釋**（`audit_shadow_filter_strength.py`，量測配對影像在中央臉部區域的 LAB ΔE）：
| 濾鏡類型 | True Test mean ΔE | Shadow mean ΔE | 比值 |
|---|---:|---:|---:|
| smoothing | 2.53 | 3.33 | 1.32x |
| whitening | 5.87 | 6.74 | 1.15x |
| eye_enlarging | 1.11 | 2.39 | 2.15x |
| face_reshaping | 6.96 | 8.55 | 1.23x |
| **平均（type-mix 無關）** | — | — | **1.46x** |

**四種類型無一例外，Shadow 的濾鏡效應都比 True Test 更強**（改動像素比例 46.0% vs 36.2%），**效果更明顯卻更偵測不到**——徹底排除資料生成失敗的可能，確認是底圖域泛化問題。
> 過程備註：第一次跑這個量測時我把樣本上限設在 250 對，剛好在取到任何 whitening 之前就截斷了，導致整體比值被 face_reshaping 的型別組成帶偏。已改為全量並改採 per-type 比值；② 第二次發現用的是**未清洗資料夾**，已改用 `clean_output/clean_paths.txt`。上表為兩次修正後的最終數字。

### ✅ 2026-08-11 C1 修法已驗證有效：v8.12（底圖多樣性）——診斷正確，但有明確代價，**暫不上production**

依上述診斷做的介入：對 **IMDB-WIKI**（in-the-wild 名人照，本專案唯一與 VGGFace2 難度相近、且原本 filter class 完全沒有的底圖來源）套用**完全相同的**自建濾鏡函式（直接 import `generate_vggface2_filters.py` 的正式實作，不重寫），生成 6,000 張（4 類型 × 1,500），**同時**加入 Layer1（label=manipulated）與 Layer2（label=filter）訓練——因為診斷顯示 Shadow 的 filter 損失是 55% Layer1 / 45% Layer2，只修一層無效。VGGFace2/Shadow 完全未動，仍是乾淨 held-out。腳本：`generate_imdbwiki_filters.py`、`build_v812_diverse_base_splits.py`（含 held-out 汙染防呆，比對 4,991 個 held-out stem 全數通過）、`AIGuard/train_v812_layer1.py` / `train_v812_layer2.py`。

**結果：診斷確認正確，Shadow 大幅改善且首次越過退化基線**
| 指標 | v8.11 | **v8.12** | Δ |
|---|---:|---:|---|
| **Shadow balanced accuracy** | 43.5% | **55.7%** | **+12.2pp，首次高於 50% 退化基線（從反資訊變成有資訊）** |
| Shadow strict per-pair | 7.2% | **24.0%** | +16.8pp（3.3 倍）|
| Shadow filter recall | 10.0% | **38.4%** | +28.4pp |
| Shadow real recall | 77.1% | 73.1% | −4.0pp（代價）|
| Shadow real→fake（誤指控） | 19.0% | **16.5%** | 改善 |
| Shadow filter 損失的 Layer1/Layer2 佔比 | 55%/45% | 69%/31% | Layer2 那半修掉較多，剩下以 Layer1 為主 |
| True Test balanced | 81.1% | 80.5% | −0.6pp |
| True Test filter recall | 93.6% | **94.0%** | +0.4pp |
| AIGuard/unseen AUROC | 0.8150 | 0.8136 | −0.0014（雜訊）|
| CelebA real recall | 99.7% | 99.6% | −0.1pp（雜訊）|
| StyleGAN2 | 99.6% | 99.6% | 持平 |
| **fake+filter 端到端誤判** | **3.71%** | **5.29%** | **❌ +1.58pp，明確退步** |

**逐類型 Shadow strict**：smoothing 4.8%→**54.0%**、whitening 4.4%→**22.1%**、eye_enlarging 6.5%→11.7%、face_reshaping 12.7%→12.7%（唯一沒動的）。

**fake+filter 退步的機制清楚且與上表自洽**：逐類型看，whitening（11.1%→10.1%）與 eye_enlarging（9.8%→9.4%）其實**略有改善**，退步**集中在 smoothing（0.7%→2.1~3.5%）與 combined（0~0.3%→1.7~2.4%）**——正好就是 v8.12 在 Shadow 上進步最多的類型（smoothing strict 4.8%→54.0%）。**同一個機制的兩面：模型變得更願意把「平滑過的臉」判為 filter，這救回大量真實濾鏡圖，但也讓「fake + 平滑濾鏡」更容易被判成 filter 而非 fake。**

**🔸 決策：暫不將 v8.12 上 production，維持 v8.11（Layer1d + Layer2v811）**。理由：fake+filter 從 3.71% 退到 5.29%（gate 為 ≤2%，已是未達標項目，再退 1.58pp 方向錯誤），這是安全性相關指標；而 Shadow 雖大幅改善，仍只有 55.7%，尚未到可宣稱「解決」的程度。**v8.12 的價值在於它證明了診斷正確、且指出了明確的下一步**，而非它本身該被部署。

- [x] ✅ **順手修掉一個系統性陷阱（同一個 bug 今天又復發一次）**：`AIGuard/stress_test_v811_pipeline.py` 過去**不論傳入哪組權重，都固定寫到 `results/stress_test_v811_pipeline.json`**。這正是先前「用已淘汰的 Layer2c 權重跑出的結果被當成 v8.11 最終數字」的成因，而今天跑 v8.12 時**又一次**把 v8.11 的 baseline 檔案覆蓋掉。已改為**依實際載入的權重自動命名**（`stress_test_<layer1tag>_<layer2tag>.json`）並在執行時印出檔名。v8.11 baseline 已重跑還原（3.71%，與文件數字完全吻合），v8.12 結果另存 `results/stress_test_v812_pipeline.json`。**教訓：接受權重當參數、卻把輸出寫死成固定檔名的腳本，就是版本錯配陷阱**。已掃描全專案同模式腳本並一併修好：`AIGuard/eval_robustness.py`、`AIGuard/stress_test_layer1.py` 也改為依權重命名（三個腳本皆通過語法檢查）
- [x] 🔄 **v8.13 進行中（2026-08-11 開始執行）**：不是重新生成 hard negative 再訓練，而是**用 v8.12 模型主動挖礦**——發現訓練資料本身就有缺口：`generate_fake_filter_hard_neg.py`（過去所有版本用的 hard-neg 生成腳本）只涵蓋 4 種濾鏡類型、單一強度（medium 等級），從未產生 `smoothing_light/heavy`、`combined_medium/heavy` 這 4 種組合，但 `stress_test_v811_pipeline.py` 實際測的是全部 8 種——**模型從未被訓練對抗它被評分的其中一半條件**。
  - 已把 stress test 的濾鏡函式**逐位元組抽取**成獨立模組 `filters/stress_test_filter_functions.py`（不重寫、不憑記憶），確保挖出的 hard negative 跟 eval 測的完全一致
  - 挖礦邏輯：對新的 AIGuard/fake 來源圖套全部 8 種條件，用 v8.12 完整 pipeline 評分，**只保留 v8.12 判錯的**（prediction != fake）
  - **第一輪**（6,000張來源圖，`fake_filter_hardneg_v813.txt`）：47,734 次評分，找到 147 個 hard negative（yield 0.3%）。**逐條件分布不均**——combined_heavy 僅 3 個、combined_medium 僅 7 個（正是退步最嚴重的兩型），樣本太薄不足訓練
  - **第二輪**（20,000張新來源圖，`fake_filter_hardneg_v813_round2.txt`）：擴大挖礦池以補齊 combined/smoothing_heavy 樣本量，執行中
  - `build_v813_splits.py` 已改為自動合併所有 `fake_filter_hardneg_v813*.txt`（依輸出路徑去重），加入 Layer1（label=manipulated）與 Layer2（label=fake）訓練，沿用 v8.12 checkpoint 微調（`train_v813_layer1.py`/`train_v813_layer2.py`，皆已通過語法檢查）
  - **✅ 2026-08-11 v8.13 完整評測完成，判定：不上 production，是誠實的負面結果，不是單純失敗**：第二輪挖礦（20,000張，`fake_filter_hardneg_v813_round2.txt`）找到 609 個 hard negative，合併第一輪去重後共 705 筆（combined_heavy 3→24、combined_medium 7→44、smoothing_heavy 7→42，樣本量補齊）。訓練 Layer1/Layer2（皆從 v8.12 fine-tune，5 epochs，F1 分別 0.9605/0.9873）。

  **三版本核心指標對照**：
  | 指標 | v8.11（production）| v8.12 | v8.13 |
  |---|---:|---:|---:|
  | True Test filter recall | 93.6% | 94.0% | 92.0%（貼著≥92%門檻）|
  | AIGuard/unseen AUROC | 0.8150 | 0.8136 | 0.8104 |
  | CelebA real recall | 99.7% | 99.6% | 99.7% |
  | StyleGAN2 fake recall | 99.6% | 99.6% | 99.7% |
  | Shadow balanced accuracy | 43.5% | 55.7% | **57.9%（持續進步）**|
  | Shadow real recall | 77.1% | 73.1% | **78.9%（回升）**|
  | **fake+filter 端到端誤判** | **3.71%** | 5.29% | **5.72%（比v8.12更差）**|

  **關鍵發現：挖礦確實命中瞄準的缺口，但代價轉移到未瞄準的類型，整體加總是負的**——逐條件拆開比對 v8.12→v8.13：
  - **改善**：smoothing_light（4.5%→2.4%）、smoothing_medium（2.4%→1.4%）、smoothing_heavy（3.8%→3.1%）、combined_medium（2.8%→2.1%）、combined_heavy（2.1%→1.7%）——正是這次挖礦針對性補強的類型，補到了
  - **新增退步**：whitening_medium（10.1%→13.9%）、eye_enlarging（9.8%→11.8%）、face_reshaping（9.1%→11.5%，且誤判方向從「偏real」轉為「偏filter」）——這幾型同樣有拿到 hard negative（whitening 137筆、eye 118筆、face 150筆，數量不算少），但訓練後反而變差
  - 加總後 v8.13 總誤判 138/2296（此為含skip的手動核對數字，腳本本身回報 131/2289=5.72%）> v8.12 的 128/2296（5.57%手動核對，腳本回報5.29%）> v8.11 的 92/2296（4.01%手動核對，腳本回報3.71%）

  **判定**：這不是「挖礦沒用」，是「局部補丁把問題挪位而非解決」——v8.12→v8.13 連續兩輪，Shadow 泛化改善與 fake+filter 精確度都朝同一個方向移動（Shadow更好、fake+filter更差），暗示兩者背後可能共用同一個決策機制。**單靠針對性補資料無法解開這個糾纏，繼續往這個方向加 round3/round4 挖礦預期只會重演同樣模式，不建議再做**。

  **v8.13 產出物**（保留供對照，不刪除）：`shufflenet_v2_layer1_v813.pth`、`shufflenet_v2_layer2_v813.pth`、`results/stress_test_v813_v813.json`、`splits/v813_layer1_train.txt`、`splits/v813_layer2_train.txt`

- [x] ✅ **決策：v8.13 不上 production，`pipeline.py` 維持指向 v8.11（Layer1d + Layer2v811）不變**
- [x] ✅ **2026-08-11 A/B/C/D checkpoint 交叉組合診斷完成，精確定位問題出在哪一層**（不重訓，純推論，`eval_ABCD_cross_combination.py`）：使用者質疑「v8.12/v8.13 的 trade-off 到底是 Layer1 造成還是 Layer2 造成」，設計 2×2 交叉實驗排除混淆——A=L1(v811d)+L2(v811)、B=L1(v812)+L2(v811)、C=L1(v811d)+L2(v812)、D=L1(v812)+L2(v812)，四組跑齊 Shadow配對／True Test配對／fake+filter stress test 三份評測，逐樣本記錄完整路由（L1_real / L1_manip_L2_fake / L1_manip_L2_filter）。

  **核心數字**：
  | combo | L1 | L2 | Shadow balanced | fake+filter stress err | →real(L1miss) | →filter(L2miss) |
  |---|---|---|---:|---:|---:|---:|
  | A | v811d | v811 | 43.5% | 3.73% | 95 | 1 |
  | B | v812 | v811 | 42.5%（幾乎不動）| **2.21%（變好！）**| 56 | 1 |
  | C | v811d | v812 | **54.5%（+11.0pp，幾乎是全部Shadow增益）**| **5.98%（大幅變差）**| 95 | 59 |
  | D | v812 | v812 | 55.7% | 5.20% | 56 | 78 |

  **結論：Shadow 改善跟 fake+filter 退步，兩者主要都是 Layer2(v812) 造成的，不是 Layer1**（C 單獨換 Layer2 就重現了 11pp 的 Shadow 增益跟大部分 fake+filter 退步）。**Layer1(v812) 是淨正向**——單獨換上去，fake+filter stress err 反而從 3.73%降到2.21%（B），Shadow 幾乎不受影響。這推翻了先前「v8.12 的 trade-off 是一個整體介入的副作用」這種籠統歸因，兩層的因果方向其實相反。

  **多算一步發現的交互作用（比單純「H2：Layer2單獨背鍋」更精確）**：同一個 Layer2(v812) checkpoint，逐樣本錯誤率在 D 組（78/2520=3.10%）比 C 組（59/2481=2.38%）更高——因為 Layer1(v812) 修好了一部分原本被誤判成 real 的邊界樣本、正確送進 Layer2，但這些「新被放行」的樣本剛好是 Layer2(v812) 特別容易誤判成 filter 的那批。**Layer1 的改善改變了 Layer2 看到的樣本難度分布**，兩層合併的退步不是兩個獨立效應的簡單相加。這不是 checkpoint 不相容（D 的數字落在 B、C 之間，沒有出現組合後才冒出的全新失敗模式），是 H2 加上一個可解釋的樣本篩選交互作用。

  **回頭檢查 v8.13 挖礦邏輯，發現一個可能是稀釋修復效果的原因**：`mine_fake_filter_hardneg_v813.py` 的收錄條件是 `pred != "fake"`（第173行），**沒有區分是 Layer1 誤判成 real、還是 Layer2 誤判成 filter，兩種來源混在同一批訓練資料裡**。既然 ABCD 診斷已經確認問題主要在 Layer2 對「Layer1 放行的難樣本」的誤判傾向，若要更精準地修，下一輪挖礦應該**只保留「Layer1(v812)正確判manipulated、但Layer2(v812)誤判成filter」這個子集**當 Layer2 的訓練訊號，而不是把 Layer1-miss 和 Layer2-miss 混在一起稀釋訓練訊號。

  **產出物**：`eval_ABCD_cross_combination.py`（可重用的診斷框架）、`results/abcd_cross_combination/*.jsonl`（逐樣本路由記錄）、`results/abcd_cross_combination_summary.json`

- [x] ✅ **2026-08-11 級聯錯誤假說已用四格交叉表驗證，非猜測（使用者要求先驗證再動手，正確流程）**：`analyze_L1_routing_shift.py`，直接重用 ABCD 三份 JSONL（不重跑模型），把 fake+filter stress test 的每個樣本按「L1(v811d) 判real/manip」×「L1(v812) 判real/manip」交叉分成四格，比較「共同放行子集」vs「v8.12新放行子集」各自的 Layer2(v812) filter 誤判率：

  | 子集 | n | L2(v812) filter 誤判率 |
  |---|---:|---:|
  | 共同放行（兩版 L1 都判 manip） | 2,487 | 2.37% |
  | **v8.12 新放行（v811d判real、v812判manip）** | 40 | **47.50%** |
  | v8.12 攔下的舊放行（v811d判manip、v812判real） | 1 | 0.00%（樣本太少不可用）|

  **差距 +45.13pp，遠超雜訊範圍，級聯錯誤假說證實成立**（n=40 不算大，但效應量大到就算用寬鬆的信心區間估計也不會跟 2.37% 重疊）。新放行子集依類型拆解：face_reshaping 61.5%、eye_enlarging 40.0%、whitening_medium 36.4%——**正是 v8.13 沒修好、反而變差的那三型**，這條線把「v8.13 為什麼失敗」跟「ABCD 定位出的機制」精確對上了。

- [x] ✅ **v8.14 完整評測完成（2026-08-11）：判定為淨正向、但不晉升 production 的部分成功**（`shufflenet_v2_layer1_v812.pth` + `shufflenet_v2_layer2_v814.pth`）。Layer1 凍結在 v812（不訓練），只用 route-filtered 挖礦重新微調 Layer2。挖礦條件明確改成 `L1_v812=manipulated AND L2_v812=filter`（純 Layer2 失敗模式），**明確排除** `L1_v812=real` 的樣本（那是 Layer1 的失敗模式，v8.13 錯誤地把兩者混在一起）。
  - 腳本：`mine_route_filtered_v814.py` + `mine_route_filtered_v814_round2.py`，來源池排除 True Test、v8.13 兩輪已用過的圖、並明確斷言 AIGuard/fake（挖礦來源）與 AIGuard/unseen（stress test 評測來源）互斥資料夾（程式碼內 assert，不是假設）
  - 按 8 種條件分層抽樣（目標 200-300 張/型），兩輪合計耗盡整個來源池（56,572 張，round1取25,000+round2取剩餘31,572）才停止 — **不是達標停止，是自然池子耗盡**：smoothing_light 300（達標）、face_reshaping 249、eye_enlarging 134、smoothing_medium 111、smoothing_heavy 93、combined_medium 91、combined_heavy 61、whitening_medium 69（最少，全池只有這麼多天然樣本）。whitening/combined 類的稀少不是挖礦沒做好，是此 cascade error 在 AIGuard/fake 自然分布裡真的罕見（訓練/建 splits：`build_v814_splits.py`，Layer2-only，`AIGuard/train_v814_layer2.py` from v812 init，5 epochs best F1=0.9852）
  - **完整評測結果 vs v8.11/v8.12/v8.13**：

    | 指標 | v8.11 | v8.12 | v8.13 | v8.14 | 標準 | 結果 |
    |---|---:|---:|---:|---:|---|---|
    | True Test filter recall | 93.6% | 94.4% | 92.0% | 94.0% | ≥92% | 過 |
    | AIGuard/unseen AUROC | 0.8150 | — | 0.8104 | 0.8108 | ≥0.8136 | 未達（僅差0.003）|
    | CelebA real recall | 99.7% | 99.7% | 99.7% | 99.6% | ≥95% | 持平 |
    | StyleGAN2 fake recall | 99.6% | 99.6% | 99.7% | 99.6% | ≥95% | 持平 |
    | Shadow balanced acc | — | 55.7% | 57.9% | 55.6% | ≥55.7% | 差0.1pp，實質持平但按門檻算未過 |
    | Shadow real recall | 76.9-77.1% | 73.1% | 78.9% | 73.1% | 理想≥77.1% | 與v8.12完全相同，未回升 |
    | fake+filter 端到端誤判 | **3.71%** | 5.29% | 5.72% | **4.33%** | <5.29%，目標≤3.71% | 有改善但未達標，補回約60.8%的退步幅度 |

  - **`Shadow real recall=73.1%` 與 v8.12 完全相同，是很乾淨的凍結驗證**：real/manipulated 判斷完全由 Layer1 決定，這次 Layer1 真的沒被動到，所有數字改變都純粹來自 Layer2。
  - **per-condition 拆解（v8.12→v8.14 stress test 誤判率）**：smoothing_light 4.53%→1.0%、smoothing_medium 2.44%→0.0%、smoothing_heavy 3.83%→1.7%、combined_medium 2.79%→1.4%、combined_heavy 2.09%→1.0%（以上皆大幅改善，且都是挖礦樣本充足的類型）；face_reshaping 9.06%→8.7%、eye_enlarging 9.76%→9.1%（幾乎持平，僅微幅改善）；**whitening_medium 10.10%→11.5%（不進反退，唯一惡化的條件，也是挖礦量最少的69張）**。
  - **正確判定（非過度推論）**：route-filtered mining 對 coverage 充足的條件（smoothing/combined）確實有效修復；但對低產量（whitening）或幾何型困難條件（eye/face_reshaping，即使挖到249張face_reshaping仍幾乎沒改善）不足。**目前只能說「coverage 修復部分有效、殘留錯誤成因尚待 dual-head 驗證」，不能說「已證明剩下全是 fake/filter XOR 結構問題」**——whitening樣本本身就不足，eye數量中等但可能缺關鍵 hard mode，face_reshaping 挖到不少仍幾乎沒改善是目前最強但仍不充分的訊號。
  - **決策：v8.14 保留為研究基準（route-filtered mining 有效性的證據），不替換 v8.11 production，`pipeline.py` 維持指向 v8.11 不變**。下一步：v8.15a dual-head pilot（見下方新條目）。

- [x] ✅ **2026-08-11 等待挖礦期間的並行測試：直接證實「混合訓練訊號稀釋」假說，不只是理論**（`test_v813_on_known_hard_subset.py`）：把 v8.13 的 Layer2（訓練時混了 L1-miss 跟 L2-miss 兩種樣本）拿去測 ABCD 診斷抓出的那個確切 40 筆已知病灶子集（`L1_v811d=real, L1_v812=manip`），固定 Layer1=v812 不變：
  | Layer2 版本 | 該子集 filter 誤判率 |
  |---|---:|
  | v812（原始，未修） | 19/40 = 47.50% |
  | **v813（v8.13混合挖礦後）** | **24/40 = 60.00%（+12.5pp，變得更差）**|

  **v8.13 不只是沒修好這個真正的病灶，是主動把它惡化了。** 這解釋了為什麼 v8.13 明明命中 smoothing/combined 這些容易改善的條件，整體加總卻是負的——訓練訊號被 L1-miss 樣本拉往錯誤方向，在真正困難的子集上代價比表面看到的更大。這是 v8.14 route-filtered 方法（明確排除 L1-miss 樣本）的直接證據支持，不只是理論推導。

- [x] ✅ **2026-08-11 v8.15a dual-head pilot 完整評測完成，判定：誠實負面結果，frozen-backbone 拆 head 不足**（`train_v815a_dualhead.py` + `eval_v815a_dualhead.py`）。假設：把 Layer2 的 `fake XOR filter` 2-class softmax改成兩個獨立 sigmoid head（fake attribute + filter attribute），backbone 凍結不動，只訓練新 trunk+heads（656,898 可訓練參數 vs 1,871,844 凍結參數）。訓練資料 `build_v815a_dualhead_splits.py` 合併全部歷史 fake+filter composite 來源（v8.3原始35,884+v8.13兩輪705+v8.14的1,107，去重後共37,696張，train/val 33,927/3,769），確保正例量足夠、不只靠 v8.14 這輪的錯誤樣本。兩個 pilot 差異只在凍結哪個 backbone：
  | 指標 | v812 baseline（現有2-class）| v813（誤導混合挖礦）| **v815a-12**（凍結v812 backbone）| **v815a-14**（凍結v814 backbone）|
  |---|---:|---:|---:|---:|
  | 40張已知病灶子集 fake-head 錯誤率 | 47.50% | 60.00% | **52.50%（更差）** | **70.00%（最差）** |
  | Fake-head recall on fake+filter | — | — | 98.30% | 99.36% |
  | Joint recognition rate（fake=1 AND filter=1 皆對）| — | — | 36.64% | 39.06% |
  | Filter-head recall on fake+filter | — | — | 38.34% | 39.69% |
  | Clean fake 的 false filter rate | — | — | 5.35% | 5.45% |

  **判讀**：filter head 不是失控亂開火（clean fake 上只有 5.3-5.5% 誤報，有基本判別力），但對真正的 fake+filter composite 只有 38-39% recall——保守低估，不是隨機噪音，代表 frozen backbone 抽出的 feature 裡，filter 訊號在跟 fake 訊號競爭時被壓過去了。**最關鍵的 40 張病灶子集不但沒改善，還變差**（v815a-12 52.50%、v815a-14 70.00%，比 v813 的 60.00% 更差），v814 backbone（已修過部分 coverage）疊加 dual-head 後反而最差，兩種修法互相干擾而非疊加互補。
  **決策（依使用者訂的決策樹第三分支）**：「僅拆 head 不夠，需要 paired consistency loss、最後 stage 微調，或 geometry/residual feature branch」——frozen-backbone 的線性 probe 級 dual-head 已被排除，不繼續往這個方向做小改動；下一步若要驗證 factorization 假說，需要 unfreeze backbone 微調 + fake/filter 配對 consistency loss（v8.15b 規格），而非再嘗試更多 frozen-head 變體。

- [x] ✅ **2026-08-11/12 v8.15b-14（partial unfreeze conv5 + FFT最後層 + fake-invariance consistency loss，init v814）完整評測：40張病灶子集 70.00%（跟v815a-14一樣差），但一般 fake+filter joint recognition 從 39%躍升到72.54%、filter-head recall 72.91%**。判讀：partial unfreeze+invariance loss 對「一般」fake+filter 語義解耦真的有效，但完全沒碰到病灶子集——暗示病灶子集困難度不是表徵糾纏機制，可能是天生邊界案例。**但補做 clean-fake false-filter rate 發現關鍵問題：40.37%（v815a的5.35-5.45%的7-8倍）**，代表 filter head 大幅過度觸發,72.91% recall 提升很可能是假的。

- [x] 🐛 **2026-08-12 根因找到：v8.15a/v8.15b 訓練標籤有嚴重矛盾 bug，先前 v8.15a/v8.15b 全部結果作廢**。`build_v815a_dualhead_splits.py`/`build_v815b_splits.py` 把 `v812_layer2_train.txt` 的舊 2-class label（`0=fake`）直接翻譯成 dual-head 的 `(fake=1, filter=0)`，但舊 label `0=fake` 只代表「2-class 正確答案是fake」，對已經套過濾鏡的 fake+filter composite 圖（v8.3起刻意標成fake以修正誤判）而言，這個翻譯是錯的。量化：v812_layer2_train.txt 的 label=0 池中 **52.0%（38,020/73,093）路徑本身帶濾鏡字樣**；重建後的 v815b 訓練集裡 **15,866 張圖（10.5% unique path）同一張圖出現兩次、標籤直接矛盾**（一次(1,0)一次(1,1)）。完全解釋 40.37% false-filter rate 的來源。
  - **修法**：`build_v815_canonical_labels.py` 建立唯一標籤真相表——優先序：① 明確 composite manifest（37,710張，(1,1)）② 路徑無濾鏡字樣且未在manifest中的label=0（35,516張，verified clean_fake，(1,0)）③ 路徑有濾鏡字樣但未在manifest確認的（20,349張，**寧可排除不猜測**）④ label=1（84,456張，real+filter，(0,1)，反向檢查0張污染）。全部 assert 通過（無衝突重複、無held-out碰撞）。
  - **視覺人工抽樣驗證**：修正後 clean-fake false-filter rate 40.37%→23.43%（v815a-v814clean pilot），false positive 94.5%集中在AIGuard/fake原始池,人工看兩張確認真的乾淨無濾鏡痕跡→**23.43%是真實模型校準行為,不是殘留污染**；舊的5%基準本身也建立在同樣污染的資料上，不可信，不該當回歸目標。
  - 已重新生成 paired consistency 資料（`generate_v815b_paired_consistency.py` 改source自canonical clean_fake，4,995 clean配9,986 filtered，0污染）、建立乾淨 splits（`build_v815_splits_v2.py`：`v815_clean_train/val.txt` 157,682→141,915/15,767，`v815_clean_pairs_train/val.txt`）。

- [x] ✅ **2026-08-12 乾淨標籤下的 2×2 機制診斷完成**（`AIGuard/train_v815_ablation.py`，統一超參數LR=5e-5/6epoch/batch192，唯一變因unfreeze與invariance loss on/off，init皆v814）：

  | Cell | 設定 | false-filter率 | joint recognition | real-filter recall | AUROC | TT balanced | Shadow balanced | 40張診斷(僅參考)|
  |---|---|---:|---:|---:|---:|---|---|---:|
  | A | frozen,無inv | **2.51%**(最好) | 12.89%(最差) | 99.86% | 0.8015 | 80.5% | 56.1% | 70.00% |
  | B | frozen,+inv | 40.75%(最差) | 68.60% | 99.86% | 0.8051 | 80.5% | 55.4% | 62.50% |
  | C | unfreeze,無inv | 26.27% | 82.55% | 99.85% | 0.8064 | 80.5% | 55.9% | 70.00% |
  | D | unfreeze,+inv | 36.33% | **83.85%**(最好) | **99.98%**(最好) | 0.8050 | 80.5% | **57.3%**(略最好) | 80.00%(最差) |

  True Test 四格數字相同非bug——real/manip判斷幾乎全由凍結的Layer1決定。**判讀**：B（frozen+invariance）明顯最差，排除；A太保守（joint recognition僅12.89%，沒解決XOR問題）；unfreeze（C、D）是主要驅動力，invariance loss單獨疊加在frozen上（B）有嚴重副作用；D相對C：joint+1.3pp、real-filter+0.13pp、Shadow+1.4pp，但false-filter率壞化+10.06pp、40張診斷壞化+10pp——**收益小、代價大**。
  **決策：C（unfreeze、無invariance）保留為目前最佳研究候選；D、B、A暫不繼續；production維持v8.11不變**。C的26.27% false-filter rate仍不能接受（若輸出`filter_detected`屬性會有約1/4機率對乾淨fake圖誤加濾鏡說明），**不能直接晉升**，下一步是threshold sweep（僅用canonical validation set，不用40張/AIGuard-unseen/Shadow/TrueTest做校準）；若threshold仍無法讓C同時達到低false-filter+合理joint recognition，才有理由做paired contrastive learning或獨立filter-specific projection branch等新架構方向。

- [x] ✅ **2026-08-12 Threshold sweep 完成：確認 trade-off 有一大部分是校準問題，不是純架構限制；鎖定 `C@threshold=0.85` 為正式研究基準**（`threshold_sweep_v815.py`，門檻範圍0.50-0.95，**只用 `v815_clean_val.txt` canonical validation set 選門檻，未使用40張病灶子集/AIGuard-unseen/Shadow/TrueTest**，provenance明確可追溯）：

  | Cell | 最佳門檻 | false-filter率 | joint recognition | real-filter recall |
  |---|---:|---:|---:|---:|
  | A | 0.50（提高門檻只會更差,非校準問題,模型本身無能力）| 2.51% | **12.89%**（上限）| 99.86% |
  | **C** | **0.85** | **4.59%**（達標≤5%）| **56.99%** | 98.74% |
  | D | 0.90 | 4.00% | 50.01%（同等false-filter預算下輸給C）| 99.48% |

  Per-type recall @ C的0.85門檻：whitening 98.6%、eye_enlarging 99.2%、face_reshaping 97.9%、smoothing 99.2%——四類均衡,無崩潰。**A 無論門檻怎麼調 joint recognition 都上不去雙位數高段,證實A的問題是模型能力不足而非校準;C/D 則能透過拉高門檻換取低false-filter,證實這部分trade-off可用校準解決**。

- [x] ✅ **2026-08-12 `C@0.85` 最終獨立驗證完成（`eval_C_0.85_final_confirmation.py`，True Test/Shadow 用鎖定門檻重新測，不再用來調參，純confirmatory）**：

  | 指標 | C@0.85 | 對照 |
  |---|---:|---|
  | True Test filter recall | **94.0%** | 幾乎持平 v8.11 的93.6% |
  | True Test balanced | 80.5% | — |
  | Shadow filter recall | 38.4% | — |
  | Shadow balanced | **55.7%** | 幾乎持平 v8.12 的55.7% |
  | AIGuard/unseen AUROC | 0.8064（門檻不影響此指標,由fake_head@0.5決定）| 低於0.8136目標 |
  | 40張病灶子集 fake-head 錯誤率 | 70.00%（僅供診斷參考,不用於選模型）| 高於v812的47.50% |

  **鎖定為正式研究基準：`shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` + Layer1凍結於v812 + filter threshold=0.85**。已完成：clean fake false-filter ≤5%、fake+filter joint recognition ~57%、real-filter與per-type recall維持高、True Test/Shadow與既有production數字持平不退步。尚未達成：AIGuard/unseen AUROC未過0.8136 gate、40張病灶子集仍差、不是所有fake+filter都能被抓到filter attribute。**明確定位：dual-head研究基準,不是production candidate,production維持v8.11不變**。

  **建議輸出schema（設計提案,尚未接入pipeline.py，因C非production）**：不要用 `has_filter: true/false` 二元輸出（因約43%的真實fake+filter會被誤標為false，等於「沒偵測到」被錯誤解讀成「不存在」）；改用三態 `filter_status`：
  ```json
  {"final_class": "fake", "filter_status": "detected"}      // 門檻以上,系統有信心
  {"final_class": "fake", "filter_status": "not_confident"} // 門檻以下,不代表一定沒有filter
  ```

  **下一步不是新架構**（paired contrastive learning / geometry branch / residual branch 暫緩）——C@0.85已證明dual-head在安全門檻下能提供有用的filter attribute,現階段先把資料切分、門檻選擇provenance、獨立測試、輸出schema這四項固定下來,作為未來任何新方法都必須擊敗的乾淨基準。

- [x] ⚠️ **2026-08-13 重大修正：`C@0.85` 的 joint recognition 完全不能跨 fake 來源泛化,上述「已驗證研究基準」的定位需要限縮**。建立獨立 composite replication set（`build_v815_replication_set.py`，200個從未被v815訓練/門檻選擇/任何既有eval碰過的DF40-cdf來源,各配clean+4種filter共994張,provenance完整記錄fake_label/filter_attribute_label/filter_type_label/source_dataset/used_in_v815_training）測試：

  | 指標 | Canonical validation set | **獨立replication set（全新DF40-cdf）**|
  |---|---:|---:|
  | Fake-head recall | ~99% | 100% |
  | Clean-fake false-filter率 | 4.59% | 0.00%（過度保守）|
  | **Joint recognition** | **56.99%** | **2.02%（幾乎完全失效）**|

  按類型全面崩潰：eye_enlarging 0.0%、face_reshaping 0.0%、whitening_medium 0.0%、smoothing_medium 8.1%。**P1-1 追加 filter-head AUROC/PR-AUC 分析（`eval_replication_auroc.py`）排除「只是threshold調錯」的可能**：整體 AUROC=0.5304（幾乎亂猜），whitening_medium甚至0.4620（比亂猜還差）；clean_fake與fake+filter的p_filter分數分布幾乎完全重疊（mean 0.0695 vs 0.1148）。**確認是真正的表徵失效,不是校準問題**——filter head 學到的是「AIGuard/fake 底圖風格 × 自建filter管線」的組合痕跡，不是可跨fake來源辨識的filter屬性本身,呼應本專案先前在Shadow vs True Test已發現過的同一種「底圖風格域依賴」模式。
  **P1-0 一併確認**：`v815_clean_train/val.txt` 目前仍混有DF40 cdf（train 10,111筆+val 1,143筆=11,254筆，與先前canonical_labels統計一致）——**C@0.85現況須標記為mixed-domain,不能主張乾淨的ff/cdf Protocol-2隔離**。
  **措辭修正**：不再寫「dual-head已成功解決fake+filter filter attribute」；改為「dual-head解決了表達能力問題（能同時輸出fake=1且filter=1),但尚未解決跨fake-source的filter attribute泛化問題」。`C@0.85`重新定位為**in-domain（AIGuard/fake風格）已校準基準**，DF40-cdf跨域泛化失敗是已驗證事實，不是待驗證假設。
  **決策：啟動 v8.16（Source-Diverse Composite Training）**——不做geometry branch、不加強invariance loss（AUROC接近亂猜代表問題不在門檻或表徵細修，而在訓練資料的來源多樣性）。規格：AIGuard/fake + DF40-ff（sd2.1/DiT/SiT/ddim/pixart）六個來源、每來源目標300張base、完整8種filter條件（不只4種）、同一張fake同時保留filter前後成對監督、DF40 cdf全域排除只作frozen replication test、初始化沿用C checkpoint、Layer1繼續凍結v812、繼續partial unfreeze不加invariance loss（一次只改資料變因）。建置腳本 `build_v816_manifest.py` 已啟動。

**結論與後續方向**：
- Shadow filter recall 低**不是** Layer2 的 sampling/class weight 問題（Layer2b/2c 兩次嘗試失敗已先證實），**也不是**濾鏡強度問題（本次排除），而是**Layer1/Layer2 都建立在特定底圖攝影風格上的域依賴**。
- 對照 Alibaba filter recall（98.1%，FFHQ 底圖、完全不同公司的濾鏡演算法）可知：**跨濾鏡演算法泛化良好，跨底圖風格泛化失敗**。這是很乾淨的一組對照，值得直接寫進論文——本專案的 filter 偵測器學到的主要是「這個底圖分布上的濾鏡痕跡」，而非「濾鏡痕跡本身」。
  > ⚠️ **2026-08-21 措辭更正（結論不變）**：原文寫「Alibaba **OOD**」。該集非 OOD
  > （與訓練資料 23.5% 內容重疊）。**本條結論反而更站得住腳**——「底圖同分布、只有演算法不同 ⇒ 高分」
  > 正是這條推論所需要的前提，內容重疊只是讓「底圖同分布」比原本以為的更強。
  > 要修的只有「OOD」一詞；**True Test vs Shadow 這組跨底圖風格對照本身完全乾淨**。
- [ ] **後續（C1 主要方向，已有明確依據）**：擴充 filter 訓練的**底圖來源多樣性**（而非增加濾鏡演算法種類），這是現有證據唯一指向的修法
- [ ] **論文 Limitations 必寫**：Shadow balanced 43.5%（低於基線）需誠實呈現，不可只寫「recall 偏低」

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
  - **⚠️ 2026-08-13 provenance 修正 + 一個流程失誤記錄**：查證發現這批圖用的是 **Layer1c**（依檔案時間戳：`shufflenet_v2_layer1_v811c.pth` 2026-08-01 建立，`v811d` 要到 2026-08-10 才建立，Aug 2 產圖當下 pipeline.py 只可能指向 c 版），不是現在的 production Layer1d。因為 `generate_gt_vs_gradcam_figures.py` 動態讀 `pl.LAYER1_WEIGHTS_PATH`，已重跑取得真正對應現行 v8.11（Layer1d+Layer2 v811）的版本。**流程失誤**：重跑時直接覆蓋了 `results/gt_vs_gradcam/` 原檔，違反本專案「不覆蓋既有 results、一律新檔名」的規則；該資料夾從未進 git，Layer1c 版本已無法復原。已誠實記錄，未隱瞞。實際影響低（純視覺化輔助圖，沒有任何量化數字依賴它），新版視覺上與 Layer1c 版一致（whitening 熱區集中上臉/額頭附近，與同日 whitening peak 診斷發現的 position-invariant peak 現象吻合）
- [x] **✅ 2026-08-02 demo composite圖更新**：`generate_demo_composites.py`重跑，`results/pipeline_demo/demo_{real,fake,filter}.png`，fake案例的explanation現在正確顯示為global-level句子（不再假裝有region定位）
- [ ] **DF40官方test split外部benchmark**（v8.11候選確定後執行，見E2章節）
- [ ] ~~**持續：不要解封 Ultimate Held-out Test Set**，直到v8.11通過完整驗收流程（含DF40 benchmark）~~ ⚠️ **2026-08-26：已被 P2-R8（`p2_abstention_20260823`）打開 783 張 real+fake 子集 → 依 lockbox 規則 DOWNGRADED TO DEV-TEST**（見 §🔒 Ultimate 段落與 MASTER_PLAN「重抽新 lockbox」項）。

## 🔒 Ultimate Held-out Test Set（本次 session 主線，2026-07-31）

> ⚠️ **2026-08-26 狀態：`splits/ultimate_clean_test.txt` DOWNGRADED TO DEV-TEST。**
> 事實：`results/research/p2_abstention_20260823/scripts/task3_generalization.py`（registry P2-R8）
> 直接讀取此 split，對 783 張（VGGFace2 real 275／DiffSwap 289／StyleGAN3 219）計算 abstention gate
> head 與 production `p_fake`。下方第 598 行自訂規則明寫「被迫重跑須降級為 Dev-Test 並重新抽一組」，
> 「只被非 production head 觸碰」的豁免不成立（production `p_fake` 也算過了）。filter 子集（269 張）
> 未被讀取，但不拆分認定——整份 split 降級；新 lockbox 必須從未用來源重抽（需新資料，MASTER_PLAN 已列項）。
> 本節以下內容為歷史記錄，保留不改。

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
- [x] **封存 `splits/ultimate_clean_test.txt`**：MD5+pHash 雙重查重通過，Lockbox 規則生效——論文定稿前不得評估此測試集；若因 bug 被迫重跑，須降級為 Dev-Test 並重新抽一組全新資料（⚠️ 2026-08-26：規則已觸發，P2-R8 讀取了 783 張 → 本 split 降級為 Dev-Test）

## 📋 資料集/文件維護（今日完成）

- [x] `docs/dataset.md` 重寫對齊 v8.8 現況（原文件停留在約 v8.1，含多項已知過時/錯誤資訊）
- [x] IINC 公式修正並記入 `docs/Dataset 清單.md`（先前引用版本因編碼問題顯示錯誤）
- [x] 讀完 `docs/research_log.md` 全文，補齊對過去實驗歷程的理解
- [x] 更正先前錯誤陳述：「H.264 domain gap 沒人動過」→ 實際上 v8.2 已嘗試（Celeb-DF-v2 real 加入訓練），因代價過大（filter/whitening/FakeClue/unseen 全面下降）未採用

## 🔒 Phase 1 Freeze Gate（2026-08-13 定案，結束無限迭代循環）

**背景**：每次新版本都會挖出新的 OOD failure（Shadow domain gap、v8.13混合挖礦、v8.15 label bug、v8.16跨來源泛化不足…），若沒有明確收斂條件，Phase 1 會無限被拉回重訓。本節把 Phase 1 拆成「必須全過的凍結門檻」與「不阻擋凍結的 stretch goal」兩層,並正式凍結版本。

**Phase 1 最終範圍定義**：
> 一個可部署候選的、針對單張靜態人臉圖片的 real / fake / filter classifier；它在固定的 core test、real/fake/filter OOD test 與 paired filter test 上達到預先定義的最低門檻，但**不宣稱**能泛化至所有 cross-source fake+filter 組合、FF++ 影片 deepfake 或未知 filter pipeline。

### A. Phase1-Freeze Gate（必須全過，凍結 `v8.11` 為 `Phase1-v8.11-freeze`）

| 類別 | 指標 | Freeze gate | v8.11 現況 | 通過？| **v8.17 現況**（2026-08-21 補列）| 統計檢定力（2026-08-21 稽核註記）|
|---|---|---:|---:|---|---:|---|
| Core 三分類 | True Test fake recall | ≥95% | ~99% | ✅ | **99.63%** | **決策級**（v8.17 n=270，CI [97.93, 99.93]，不跨門檻）|
| Core 三分類 | True Test filter recall | ≥90% | 93.6% | ✅ | **91.97%** ⚠️ | ⚠️ **無法統計確認**（n=249；v8.17 91.97% CI [87.92, 94.74] **跨 90% 門檻**；需 n≈890。擴充至 n=998 後 cluster bootstrap [89.80, 94.20] **仍跨線**）|
| Paired filter | True Test paired balanced accuracy | ≥80% | 81.1% | ✅ | **82.13%** | ⚠️ **無法統計確認**（n=249；v8.17 82.13% CI [79.12, 84.94] **跨 80% 門檻**；需 n≈1,340）|
| Fake OOD | AIGuard-unseen AUROC | ≥0.80 | 0.815 | ✅ | **0.8410** | ⚠️ **邊際通過**（v8.17 0.8410，下界 0.8034，僅高於門檻 0.003；不應視為有安全邊際）|
| Real OOD | CelebA real recall | ≥95% | 99.7% | ✅ | 持平（未於本次稽核重測）| **決策級**（v8.17 n=3,000，CI [98.97, 99.57]）|
| GAN fake detection（**非 OOD**，見下註）| StyleGAN2 fake recall | ≥95% | 99.6% | ✅ | 持平（未於本次稽核重測）| **決策級**（CI [99.26, 99.75]）；但 CI 只涵蓋抽樣誤差，**不涵蓋 63.8% 內容重疊偏誤**（P1-R11）|
| 跨濾鏡演算法 filter recall（**非 OOD**，見下註）| Alibaba filter recall | ≥95% | 98.1% | ✅ | **98.17%** | 判定不翻，但 **n=21,151 具誤導性**（4 型別×3 強度共用底圖，觀測不獨立）→ **不可引用其 CI 寬度宣稱精度**；亦不涵蓋 23.5% 內容重疊偏誤 |
| Mobile artifact | fp32 TFLite 合計大小 | ≤25 MB | 20.91 MB | ✅ | **20.913 MB** | **決定性量測**，無抽樣誤差 |
| Deployment | 真實裝置（iPhone）實測 | 必須完成 | 尚未測 | ⏳ **未過，待補** | 尚未測 | n/a |

> 📌 **2026-08-21 更正註記〇（現況版本，F3）**：本表原本只有「v8.11 現況」一欄，
> 但 production 自 2026-08-20 起已是 **v8.17**（`shufflenet_v2_layer1_v817sbi.pth`
> + `shufflenet_v2_layer2_v811.pth`），讀者容易誤把 v8.11 欄當成現行 production 數字。
> **v8.11 欄位刻意保留不動**——它是 `Phase1-v8.11-freeze` 的凍結紀錄，屬歷史事實；
> 新增的「v8.17 現況」欄才是現行 production。未於本次稽核重新量測的項目誠實標為
> 「持平（未於本次稽核重測）」，不填入未經本輪驗證的數字。
>
> ✅ **爭議已裁定（F4，2026-08-21，Member A）**：True Test filter recall 的
> gate 門檻正式定為 **≥90%**。背景：2026-08-02 的 gate 重新框定拍板寫 ≥92%
> （`TODO.md` 本檔稍早段落、`docs/Dataset 清單.md`），2026-08-13 的 Phase1-Freeze
> Gate 表（即本表）寫 ≥90%，未查到調降的說明紀錄。裁定理由：P1-R17 對每個
> 種子、兩個候選 arm、以及 frozen production 本身重算後，數字全部落在
> 90.76–91.97%，**沒有任何一個能在 ≥92% 下通過，包括 production 自己**——
> 用 92% 會讓已上線版本回溯性不通過，不合理，故採 ≥90%。**v8.17 = 91.97%，
> 對此門檻通過**（CI [87.92, 94.74] 仍跨門檻，統計上無法完全排除實際低於
> 90% 的可能，此為已知限制，見 `results/research/p1_bench_power_20260820/`，
> 建議寫入論文 Limitations）。是否改用配對式判準留待未來版本評估，不影響
> 本次裁定。

> 📌 **2026-08-21 更正註記一（gate 命名）**：上表原本的「GAN OOD」「Filter OOD」兩個類別名稱**不正確**。
> P1-R11 內容層級稽核證實 `stylegan2_test/fake/` 有 **63.8%（6,376/10,000）**、
> `FFHQ_ali_process` 有 **23.5%（4,980/21,151）** 與訓練資料內容重疊（含逐位元組相同的圖片），
> 兩者皆**不是分布外（out-of-distribution）測試集**。**數字本身未變、pass/fail 判定未變**
> （去污染後 StyleGAN2 ≈99.07%，仍過門檻），變的只是可宣稱的框架：
> 應稱「StyleGAN2 fake detection」與「Alibaba filter recall（跨濾鏡演算法，非 OOD——與訓練資料有 23.5% 內容重疊）」。
> 證據：`results/research/p1_r11_leakage_scaling_20260820/TASK1_LEAKAGE_AUDIT.md`。
> **仍然乾淨的跨域證據**：CelebA real recall 與 AIGuard/unseen AUROC 皆已各自查證乾淨；
> True Test vs Shadow（同一套自建濾鏡程式碼、不同底圖攝影風格）仍是專案內有效的跨域對照。
>
> 📌 **2026-08-21 更正註記二（統計檢定力）**：新增的最右欄來自
> `results/research/p1_bench_power_20260820/BENCHMARK_POWER_REPORT.md` §3。
> **本註記不改動上表任何一格已記錄的 pass/fail 判定**，只標示哪些 gate 是決策級、
> 哪些在統計上從未被確立。報告 §3.1 明確指出：True Test filter recall 與 paired balanced
> accuracy 這兩項「在 v8.11 凍結當下宣告的『✅ 通過』在統計上從來沒有被確立過，v8.17 也一樣」。
>
> 📌 **2026-08-22 更正註記三（Mobile artifact 門檻範圍不明確，待 reviewer 裁定）**：
> 上表「Mobile artifact｜fp32 TFLite 合計大小｜≤25 MB」這一格，寫下與量測時都只涵蓋
> **Layer1+Layer2 兩個模型**（20.91 MB）——當時 artifact classifier（濾鏡子型別分類器）
> 還沒匯出過手機格式，不在這個門檻的量測範圍內。**2026-08-22 首次把 artifact
> classifier（v6）也匯出手機格式後，三模型合計 = 25.75 MB，比 ≤25MB 高出
> 0.75MB（3%）**。這格原本的 pass/fail 判定**不因此自動改判**——本註記不擅自認定
> 「≤25MB」原意是否本來就該含 artifact classifier，只誠實記錄兩種讀法都成立
> （① 門檻只管核心 real/fake/filter 分類器，20.91MB 仍過；② 門檻管的是「濾鏡情境
> 端到端要跑完全部要載入的東西」，25.75MB 需要重新裁定門檻或拆成獨立項目），
> 留待 reviewer 裁定要採哪一種框架，比照 F4 的既有裁定模式處理。完整量測與雙讀法
> 說明見 `results/mobile_export/v817_20260822/EXPORT_AND_VERIFY_REPORT.md` §5。
> 同輪也首次把 Layer1（v8.17sbi）從**production 路徑**（而非先前只在研究資料夾下
> 用同一份檔案的副本匯出過）完整跑過 G1-G4，並把 Layer2（v8.11，不變）重新驗證
> 仍可載入且數值相符；三模型的全鏈路決策（不只個別模型）在完整 769 張 True Test
> 上與 PyTorch 逐張一致（769/769），是本專案至今對匯出正確性做過最大規模的驗證。
>
> 🚧 **樣本數天花板（為何不能靠加資料解決）**：13,328 張 LFW 之中，通過本專案標準清洗的
> 8,918 張**全部**已被某個 split 使用（交集為 0）；剩下 1,835 張「未使用」影像實測
> Step1 僅存 30.1%、Step2 後為 **0**。**可新增的乾淨 LFW base 影像數 = 0，這是硬天花板**。
> 把每張底圖的濾鏡型別從 1 種加到 4 種（n=249→998）足以解析「兩個模型之間的配對差異」，
> 但無法確立「單一模型對絕對門檻是否通過」——後者需要更多**互相獨立的底圖**。
> ⇒ **建議把這兩項寫進論文 Limitation，不要因此再開一輪訓練。**

**狀態**：核心靜態指標全數達標,唯獨缺真實裝置實測,故目前正式稱呼為 `Phase1-v8.11-freeze`（frozen research baseline / pre-deployment production baseline），不是「已完全驗證的 mobile production model」。iPhone 實測補完後可升格為正式 production release。（⚠️ 2026-08-21 補充：「全數達標」中的 True Test filter recall 與 paired balanced accuracy 兩項為**未能統計確認**的達標，見上表最右欄。）

### B. Stretch goals（不阻擋凍結，列為下一輪研究目標/論文 Limitation）

| Stretch goal | 合理目標 | 現況 |
|---|---:|---|
| Shadow paired balanced accuracy | ≥60% | v8.11 為 43.5%~56% |
| Shadow filter recall | ≥40% | 偏低（22-28%~） |
| Fake+filter 最終誤判 | ≤2% | v8.11 為 3.71% |
| Cross-source `has_filter` joint recognition | ≥25% | v8.16 為 4.53%（未達） |
| FF++ fake recall | ≥70% | 不達標（Layer1 video-domain 問題，非本Phase範圍）|
| int8 mobile deployment | 正確性不退化 | FFT branch 動態範圍問題仍 blocked |

這些未達標**不阻擋** Phase 1 收版，寫入論文/文件的 Limitation & Future Work 章節。

> 📌 **2026-08-21 統計檢定力註記**（來源同 A 表，`BENCHMARK_POWER_REPORT.md` §3）：
> Shadow paired balanced（v8.17 43.55%，CI [40.50, 46.59]）、Shadow filter recall
> （12.19%，CI [8.85, 16.55]）、fake+filter 誤判（2.80%，CI [2.20, 3.55]）三項的
> **FAIL 判定皆為決策級**（離門檻夠遠，CI 不跨線），判定不受樣本數影響。
> 但 **fake+filter stress 的 n=2,289 具誤導性**——2,289 張是 8 種濾鏡條件作用在共用底圖池上，
> 觀測不獨立，**不可引用其 CI 寬度宣稱精度**（同 Alibaba 的問題）。本註記不改動任何判定。

> 📌 **2026-08-19 更新（P1-R8，見下方 C1.7）**：其中「Shadow paired balanced ≥60%」
> 與「fake+filter 最終誤判 ≤2%」兩項已證實是**同一個 operating point 的兩端**，
> 不是兩個各自獨立可優化的目標——六種訓練介入全部落在單一門檻旋鈕畫出的曲線上或
> 之下。要同時推進兩者需要 in-the-wild 底圖生成的 fake 訓練資料（目前沒有的
> generator），細節與證據見 C1.7 與 registry P1-6。

### Robustness Gate（獨立於分類 gate，不可混報 overall accuracy）

| 擾動 | Gate | 備註 |
|---|---:|---|
| JPEG q70 | 不可全面崩潰,需完整報每類recall | 不能只報overall accuracy |
| JPEG q50 | 報告為stress test,不要求pass | 極端壓縮情境 |
| Downscale 4× | filter/real recall不可嚴重單邊崩壞 | 特別注意real→filter錯誤方向 |
| Blur k5 | 報告為stress test | filter紋理線索本就會受影響 |
| Blur k9 | failure characterization | 不當正式pass gate |
| Lighting | 報告三類recall與錯誤流向 | 特別看Layer1是否把real導到manipulated |

**規則**：任何 robustness 結果必須拆三類 recall（real/fake/filter）逐類報告，不可只報單一 overall accuracy——因為已知某些擾動下會出現 real↔filter 方向性錯誤，這在產品意義上比 overall accuracy 小幅下降更重要。

### 未來新版本的收斂規則

> 任何新版本只有「**所有 Phase1-Freeze Gate（A）不退步**」且「**至少一個 stretch goal（B）有實質改善**」，才值得啟動下一輪訓練；否則記錄為 negative result，不再追加迭代。

### 研究支線最終定位（進論文研究結果章節，不進 production）

```text
v8.15-C@0.85： in-domain（AIGuard/fake風格）已校準的dual-head research baseline
v8.16-mixed-lineage@0.95： 跨來源composite training的負面但有資訊量結果
                          （DF40-cdf joint recognition 2.02%→4.53%，
                           whitening/幾何filter/pixart/sd2.1完全無殘留效果）
```

兩者共同構成「為什麼 compositional fake+filter 跨來源泛化仍然困難」的論文證據，不硬塞進 production。

## A｜Eval 方法論 & 資料完整性（Phase 1 收尾）

- [x] 建立乾淨靜態圖 held-out 主評集 → **Ultimate Held-out Test Set 已封存**（2026-07-31）
- [x] Celeb-DF-v2 定位修正：CLAUDE.md/docs/dataset.md/docs/Dataset 清單.md 三份文件核對一致，皆已移出主評表
- [x] DF40 train/test split 確認：code review + 實測 v88_train_real_fake.txt 與 truetest_fake.txt 0 重疊（15,000 DF40 rows 全數乾淨）
- [x] hard_neg 生成腳本補顯式 truetest 排除防呆：`generate_fake_filter_hard_neg.py` 已加 `_load_truetest_exclusion()`
- [x] EFS 訓練政策完整文件化：完整理由（Phase1可用/Phase2不可用的任務粒度差異）已寫入 docs/Dataset 清單.md
- [x] MidJourney 訓練風險評估：`AIGuard/eval_midjourney_risk.py` 實測，v8.8 對 632 張 MidJourney/fake 100% 正確判為 fake，P(real) mean=0.033，無 CelebA-style shortcut 風險，結論已寫入 docs/Dataset 清單.md
- [ ] True Test contamination bias 標記：需在論文 Limitations 明確標註 v7+ 選型曾參考此結果（純寫作任務，待論文草稿開始時處理）
- [ ] Alibaba confound 排除實驗：找 confound-free 對照組（非 FFHQ 底圖來源）驗證 100% 是否為 shortcut（需新資料來源，成本較高）。⚠️ **2026-08-21：該集已確認非 OOD（23.5% 內容重疊），confound 已從「疑慮」變成「已量化的事實」；同上方重複條目的更正註記**

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

- [x] ✅ **2026-08-17～18 P1-R3.0 → R3.0b → R3 autonomous → R3.4 → R5：scale-normalized filter generator 全鏈完成，狀態全部為 `NEGATIVE_BUT_INFORMATIVE`（不是失敗、也不是成功，是有明確價值的負面結果）**。完整記錄見 `docs/EXPERIMENT_REGISTRY.md`「P1-3」條目，這裡只列摘要：
  - **P1-R3.0/R3.0b**（`results/research/p1_r3_0_scale_normalized_generator_calibration_20260817/`、`..._p1_r3_0b_selective_generator_revision_20260817/`）：修好 v1 filter generator 固定像素參數的問題。face_reshaping_v2（CV 0.547→0.041）、smoothing_S2（CV 0.068→0.045）、whitening_W5（CV 0.051→0.00072）三種通過 scale-stability gate；**eye_enlarging 未過（CV 0.269），維持 REFERENCE_UNCHANGED 不動**。
  - **P1-R3 autonomous / P1-R3.4**（`results/research/p1_r3_autonomous_20260818/`、`..._p1_r3_4_scale_normalized_heldout_20260818/`）：用新 generator 訓練的候選（C1/C2/C3）在**舊版 v1 generator 測試集**上看起來大贏 v8.16（14.6-15.1% vs 4.53%），但門檻對齊後發現是假象（v8.16 在對齊 threshold 下 7/7 全贏）。改用**跟訓練 generator 對齊、全新建立的第二個 held-out 測試集**重測後，新候選對 v8.16 全部不顯著，**`NEGATIVE_CONFIRMED`**。附帶重要修正：dose 對齊後 v8.16 跨來源 AUROC 標準差從 0.088 收縮到 0.025（pixart 0.528→0.687、sd2.1 0.537→0.636），代表原本支持「該做 source disentanglement／DID／GRL」的證據，很大一部分其實是舊測試集的 generator dose 錯位造成的假象，**不是真的 source-identity 訊號**。因此 DID/GRL/source-invariance 這條路線目前正式列為**暫緩、不是試過失敗**，未來要重新提出需要新證據，不能只憑舊的跨來源落差數字。
  - **P1-R5**（`results/research/p1_r5_filter_type_anatomy_20260818/`）：dose confound 排除後，殘餘的最大失敗軸是**濾鏡型別**，不是來源——smoothing AUROC=0.905 遠好於 whitening=0.586／eye_enlarging=0.603／face_reshaping=0.594。**根因（有量化證據支持）：不是 whitening 等三種效果強度比較弱**（whitening 跟 smoothing 的 LAB ΔE 效果強度只差 7%），**是效果強度相對於「同一張臉在沒套濾鏡時分數本身的自然波動」的比例太小**（signal/nuisance ratio：smoothing 1.182 vs whitening 0.242／eye 0.330／reshaping 0.405）。模型不是看不到這三種濾鏡的訊號——配對比較下勝率 78-84%——是單張圖沒有參考基準時，這個訊號會被淹沒在跨圖片的自然變異裡。已排除的假說：H-DOSE（效果強度不平衡）、H-AUG（ColorJitter 訓練增強造成的假象）、H-DATA（樣本量不平衡）、H-CAL（純粹是 threshold 沒調好）全部被直接量測推翻；H-GEOM（eye/reshape 是幾何位移在 224px 輸入下已逼近次像素等級）成立，**但這個「逼近 landmark 偵測器雜訊下限（0.24px vs 0.45px）」的結論只在本專案自建的乾淨、控制良好的合成資料上成立，不可直接套用到真實使用者上傳的雜亂照片**（那種場景下 landmark 偵測誤差通常明顯更高）。四個針對性介入方法（K0 純校準／K1 margin loss／K2 variance penalty／K3 輔助 dose 回歸監督）**全部在 held-out DF40-cdf 上沒有顯著改善**，K0 更直接證明「這不是決策層/threshold 問題」（temperature scaling 數學上不可能改變 AUROC，實測 T=1.00 印證）。
  - **⚠️ 已知陷阱模式，寫下來避免第四次犯錯：threshold-matched comparison（換到同一個決策點比較）是任何「新候選 vs 既有 checkpoint」比較的強制檢查項，不可省略，只看單一 shared threshold 下的結果不算數。** 這條研究鏈已經連續三次抓到「表面贏、換到公平比較點後輸」的假象：v8.16 未校準的 11.21%（P1-2）、P1-R3.4 的 C1/C2/C3、P1-R5 的 K1（K1 在 shared threshold 下 7/7 全贏，換算成同樣的 false-filter 誤報率比較後 0/6 顯著贏、4-5/6 顯著輸——它是靠拉高誤報率換來的假贏，不是真的學到更好的表徵）。
  - **對 production v8.11 完全無影響**：每一輪結束都有重新算 hash 確認兩個 frozen checkpoint 逐位元組未變，沒有任何一個新 checkpoint 被提議升級為 production。

## C1.5｜Reference-Region Noise Correction（P1-R6）— ❌ CLOSED - NEGATIVE，不再列為候選方向

> **2026-08-18 結案**：Stage 0 判定 whitening/eye_enlarging（背景逐位元組穩定）、
> face_reshaping（有界可排除）三種型別方法論成立，smoothing_S2 因濾鏡本身沒加臉部
> 遮罩（全圖套用，非局部）明確排除出這輪範圍。Stage 1-2 對三種型別測了 M1_bgz
> （背景 z-score 校正）、M1b_bgstat（背景物理統計量回歸）、M2_refhead（表徵學習，
> 讓模型自己學怎麼用背景參考訊號）。**核心機制結論**：`corr(z_full, z_bg)=-0.0127`，
> 背景統計量只解釋得了 0.85% 的 clean-fake 分數變異——**背景區域幾何上真的沒被動過，
> 但統計上是空的，P1-R5 找到的「淹沒訊號的雜訊」根源在臉部區域本身，不是可以用
> 同張圖背景代理的全域圖片屬性**。這代表被否證的是整個「用同張圖背景當參考」這
> 個方法論方向，不只是這三個具體實作，**不建議在同一假設下再嘗試變體版本**。
> 唯一有學到東西的 M2 版本，在 held-out DF40-cdf 上 threshold-matched 後 12/12
> 全輸（本專案第四次抓到「換 threshold/靠誤報率買表現」陷阱），而且額外抓到一種
> **新的陷阱變體**：M2 的整體 AUROC 是三版最高（0.6211），但在真正會部署的低誤報
> 率區間（FPR=1%）TPR 反而最差（0.0084 vs 對照組 0.0421），只贏在沒人會用的
> FPR≥20% 區間——這跟「換 threshold 造假」是不同性質的陷阱，已寫入
> `docs/EXPERIMENT_REGISTRY.md` 開頭新增的「Known Traps」全域規則區塊（Known
> trap #2），往後任何候選方法比較都要同時檢查這兩種陷阱，缺一不可。完整記錄見
> `docs/EXPERIMENT_REGISTRY.md`「P1-4」條目、`results/research/
> p1_r6_reference_region_20260818/P1_R6_FINAL_FINDINGS.md`。

- [ ] **⚠️ 下一輪 milestone 開跑前必須先做的事：重新檢視 P1-R1 到 P1-R6 全部證據，
  找出還沒試過、性質不同的第三個槓桿方向**——到 P1-R6 為止，whitening/eye_enlarging/
  face_reshaping 這個弱點已經系統性排除了兩整條方向：loss 側四種調整（K0-K3，
  P1-R5）全滅、reference-region 正規化三種變體（M0-M2，P1-R6）全滅。**不建議下一輪
  再自動延伸同一兩個方向的變體**，該先停下來想清楚要瞄準哪裡，候選方向包括但不限於：
  ① 更高解析度輸入（P1-R5 已量出 eye/reshape 位移量逼近 landmark 偵測器雜訊下限，
  但會實質衝擊 20.91MB/14.4ms 手機部署預算，需明確權衡）② 更大規模 fake-source
  diversity（P1-R3.4 目前唯一還有顯著正向效果、且未測試過更大規模的槓桿）
  ③ 重新定義可接受範圍（例如接受 whitening/eye/reshape 維持現狀，資源轉去其他
  問題）。這個方向選擇需要人類決策，不建議讓 agent 自動選——前兩輪已經證明「自動
  延伸同一方向」容易越挖越深卻沒有新方向。
  > **2026-08-18 已由人類 project lead 拍板選定方向 ②（更大規模 fake-source
  > diversity），並已執行完成 → 見下方 C1.6（P1-R7）。方向 ① 高解析度輸入與 ③
  > 重新定義可接受範圍仍未動，維持候選狀態。**

## C1.6｜Fake-Source Diversity Scaling（P1-R7）— ⚠️ PARTIAL_SUCCESS，**不建議追加 10x 輪次**

> **2026-08-18 結案**：把 v8.16 唯一被證實有效的槓桿（加入 DF40-ff 五種來源的
> composite 訓練資料）從每來源 300 張 base image 放大到 600（T600_2x）與 900
> （T900_3x），**除了資料量以外，架構／loss／init（Cell C）／optimizer／LR／
> schedule／epochs／batch／seed／augmentation／v1 filter generator／來源家族／
> Layer1 全部與 `AIGuard/train_v816.py` 逐項相同**，三個 tier 為巢狀關係
> （v8.16 的 300 張 ⊂ T600 ⊂ T900，且 v8.16 原本的 composite 逐位元組重用）。
> 完整記錄見 `docs/EXPERIMENT_REGISTRY.md`「P1-5」條目與
> `results/research/p1_r7_diversity_scaling_20260818/P1_R7_FINAL_FINDINGS.md`。
>
> **結果摘要**：held-out DF40-cdf filter-head AUROC 隨規模單調上升——primary
> 0.6720→0.6826→0.6868、secondary 0.6182→0.6404\*→0.6547\*（\*=顯著）；fake-head
> recall 完全不退（99.9%/100.0%，Δ=0.00pp）。**Known trap #2（低誤報率區間）兩個
> tier 都乾淨通過**：20 個低 FPR 比較點中顯著較好 3 個、顯著較差 **0** 個，
> TPR@FPR1%／pAUC 全部隨規模單調上升——**這是 P1-R2→R7 整條鏈第一個在真正會部署的
> 低誤報區間守得住優勢的候選**（跟 P1-R6 的 M2_refhead 正好相反）。
> **但 Known trap #1（對齊誤報預算）沒有乾淨過關**：T600 在 12 個預算點中顯著贏
> 9 輸 2、T900 贏 10 輸 2，輸的都是 primary set 最緊的 ≤1% 預算點，判定 MIXED，
> 未達預先宣告的 STRONG_SUCCESS 條件。
>
> **⚠️ 這輪最重要的方法論教訓（trap #1 第五次發作）**：用各自 frozen threshold 看，
> joint recognition 是 0.38%→4.92%→**10.61%**（看起來像 28 倍暴漲）；換算到**同一個
> 5% false-filter 誤報預算**後只有 21.8%→23.4%→**24.0%**。**約 5/6 的表面提升來自
> 決策點不同，不是模型變強——frozen-threshold 那組數字絕對不可以拿去引用。**
>
> **提升集中在 smoothing（+ 少量 whitening），eye_enlarging／face_reshaping 在任何
> 規模下都完全沒動**（secondary eye 0.5811→0.5827），也就是說這個槓桿買到的是本來
> 就已經做得到的能力，沒有碰到 P1-R5 診斷出、P1-R6 確認修不好的那個真正瓶頸。
> 附帶一個有機制意義的觀察：clean-fake logit SD（P1-R5 認定的 nuisance variance
> 本體）隨規模單調下降（1.555→0.827→0.754→0.730）。

- [x] ✅ **P1-R7 執行完成，端狀態 `PARTIAL_SUCCESS`**（2026-08-18）
- [x] ✅ **啟動前抓到並修掉一個真實資料完整性缺陷（不是繞過，是重建）**：第一版只用
  **路徑**比對新增影像與 v8.16 原始 300 張，漏掉 **266 筆 stem 撞號**——不同 DF40
  generator 會用**同一個檔名 stem 重繪同一張底層 FF++ 影格**
  （`pixart/ff/970/100_340.png` vs `ddim/ff/970/100_340.png`），其中 **38 筆撞到
  v8.16 的 VAL 影像**，會讓同一張來源影格同時出現在候選的訓練資料與共用的 in-domain
  門檻選擇集裡。v8.16 自己的 manifest 是 0 train/val stem 重疊（已驗證），所以這等於
  比專案自己的標準退步。已改為 stem-strict 選圖、替換 281 筆、新增 **G7 gate（每個
  tier 的 train/val stem 重疊必須為 0）**，7 項 gate 全過。**⚠️ 這是 v8.16 當初也踩過
  的同一類 bug，只要混用多個 DF40 method 就會復發——日後任何 DF40 多方法建資料的腳本
  一律要用 stem 比對，不可只比路徑。**
- [ ] **決策已記錄：不建議追加 10x（3,000/source）輪次**。理由三項：① 每翻倍的邊際
  效益只有約 1pp 的對齊後 joint recognition 與 0.005-0.015 AUROC，且在 dose-aligned
  primary set 上還在衰減（+0.0106→+0.0041）② 提升只發生在 smoothing，沒有碰到真正的
  弱點型別 ③ **資料池已接近見底**——扣掉所有排除條件後 DF40-ff 每來源只剩 3,288
  （DiT/SiT）／3,705（ddim/pixart）張可用，3,000/source 等於 6 個來源裡有 4 個直接
  貼到天花板、毫無餘裕，真要放大只能加**新的來源家族**，那是 diversity **composition**
  的問題，跟這輪測的 **scale** 是兩回事。
- [ ] 若之後仍要處理 whitening/eye_enlarging/face_reshaping 弱點，現在還活著的變數是
  ① diversity **composition**（新增來源家族，未測過）② 方向①高解析度輸入（需明確
  對 20.91MB/14.4ms 手機預算計價）③ 方向③重新定義可接受範圍。**資料量本身這條路
  已經量到底了，不要再加同一批來源的量。**
- [ ] （可選）論文 Limitation 章節可直接引用這輪：作為「data-scaling 對 cross-source
  filter attribution 的邊際效益量測」以及 trap #1／trap #2 雙重檢查方法論的示範案例

## C1.7｜Shadow vs fake+filter 拉鋸戰（P1-R8）— ✅ 已結案：**不是訓練問題，是一個 operating point**

> **2026-08-19 結案**：從 v8.12 起「改善 Shadow 就一定惡化 fake+filter 壓力測試」
> 這件事，本輪用**單一 threshold 掃描**證明它根本不是表徵/資料/loss 的問題——
> 拿**一顆凍結不動的 checkpoint**（Cell A）只掃 fake head 的判斷門檻，畫出的曲線
> 就已經涵蓋（且多半優於）v8.12→P1-R7 這一整串花了大量算力訓練出來的所有候選。
> 完整記錄見 `docs/EXPERIMENT_REGISTRY.md`「P1-6」與
> `results/research/p1_r8_shadow_composite_tradeoff_20260819/P1_R8_FINAL_FINDINGS.md`。
> **production v8.11 完全未動**（`pipeline.py` 與兩顆 checkpoint 皆 byte-identical，
> hash 與 P1-R6/P1-R7 記錄一致），**未做任何 git commit**。

- [x] ✅ **Round 1：P1-R7 的 T900_3x 與 v8.16 首次跑完整 gate suite（過去只測過
  DF40-cdf 跨來源指標），判定不可晉升**。T900_3x 是所有 arm 裡 fake+filter 壓力
  測試**最差**的一個（5.94% vs production 3.71%），而且 Shadow 完全沒有比 Cell C
  更好（55.91% vs 55.73%）；Alibaba filter OOD 全部 dual-head arm 都掉約 2pp
  （98.17%→95.4-96.3%）。**「加大 fake 來源多樣性」這條槓桿對本問題完全無效**，
  與 P1-R7 自己「不要跑 10x」的建議互相印證（但是從完全不同的角度）。
- [x] ✅ **關鍵機制發現：兩條血緣的錯誤來自不同元件**。把壓力測試錯誤拆成
  「Layer1 閘門漏放」與「Layer2 fake head 判錯」：production 是 **84 / 1**
  （98.8% 是 Layer1 問題，它的 Layer2 fake head 幾乎完美）；Cell C 血緣是
  **48 / 78**（Layer1 反而更好，但多出一整批 Layer2 fake head 的失誤）。
  Layer2 fake head 失誤數隨著「trunk 被推去表示 filter 的程度」單調上升：
  凍結 64 < 解凍 78 < 2-3 倍 composite 資料 86/88 < 明確加 invariance loss 109。
- [x] ✅ **Round 2：fake-invariance consistency loss（Cell D）首次被壓力測試，
  結果與預測相反——它讓 fake head 更差（109 個失誤、6.86%）**。這是 label bug
  修好之後的乾淨量測，補上了 v8.15b 當時無法乾淨歸因的那一格。附帶發現：
  Cell A（凍結 trunk、無 invariance）在**兩個軸上同時**優於 Cell C，代表這條
  frontier 從來就不是緊的。
- [x] ✅ **Round 3：用 production 的 2-class Layer2 當「高信心 fake 證人」否決
  dual head**。事先宣告的選擇規則（in-domain filter recall 損失 ≤1.0pp，只用
  dev 資料選）選出 τ=0.95，等於證人永遠不出手 → **依規則判定無候選，規則不事後
  放寬**。另跑一組明確標示為 sensitivity 的 τ=0.85：壓力測試 **2.36%（本專案史上
  最佳）** 但 Shadow 只剩 47.67%，與事前寫下的預測（2.3% / 46%）吻合。
- [x] ✅ **Round 4：Layer2 從來沒看過「未經修改的真實照片」——(0,0) 這個標籤組合
  訓練資料量是 0**，但 Shadow 有 27% 的乾淨真實照會被 Layer1 送進 Layer2。補進
  12,000 張 in-the-wild 乾淨真人照（IMDB-WIKI + celeba_train，與所有 gate stem
  互斥）標成 (0,0)：**Shadow real recall 73.12%→81.36%，本專案首次越過 ≥80% 的
  stretch 門檻**，CelebA 也微升——機制完全如假設預測。但抑制效果**沒有停在乾淨
  真人照上**：fake+filter composite 被判成 real 的從 48 暴增到 151，壓力測試退到
  **7.12%（最差）**，Shadow filter recall 也掉 15.4pp。假設 H4 被否證。
  - 附帶方法論收穫：control arm 用同一支腳本、未改動的 splits 重訓，產出的權重與
    原始 Cell A checkpoint **bit-identical（365 個 tensor 最大差 0.0）**，證明
    唯一變因真的只有資料。
- [x] ✅ **Round 5（決定性）：一顆凍結 checkpoint、只掃 fake head 門檻畫出的曲線，
  涵蓋了全部訓練出來的候選**。把每個 arm 拿去跟「曲線在該 arm 自己的壓力測試
  錯誤率上的 Shadow 值」比：Cell A **+0.00pp**、Cell D −0.36、T600 −1.08、
  Cell C −1.25、T900 −1.25、v8.16 −2.15、證人否決 −2.33、R4 wild-real −5.56、
  v8.11 −11.83——**沒有任何一個 arm 在曲線之上**。也就是說 diversity scaling、
  partial unfreeze、invariance loss、route-filtered mining、dual-head 拆頭、
  in-the-wild clean-real negatives 這六種介入，買到的東西**一個免費的門檻旋鈕
  全都已經給了**，多數還買得更差。
- [x] ✅ **量到了背後的原因（不是推測）**：Layer1 放行的影像上，fake 證據的分布
  依底圖攝影風格分裂——True Test filter 0.079 / True Test 乾淨真人照 0.078 /
  Shadow filter 0.892 / **Shadow 乾淨真人照 0.906** / 真正的 fake+filter
  composite 0.917。**在 VGGFace2 風格的照片上，fake 通道對「真的」「套了濾鏡的真的」
  「真的假圖+濾鏡」給出幾乎一樣的分數，等於沒有訊號**。所以唯一讓 Shadow 濾鏡圖
  不被打成 fake 的，就是模型「對 fake 不確定」，而這正是 composite 得以逃脫的原因。
  提高 fake 信心 → 抓到 composite、冤枉 Shadow 真人照；降低 → 救回 Shadow、放走
  composite。**濾鏡側的任何努力都碰不到這件事**，這正是 v8.12→v8.16→P1-R7 各自
  獨立撞到的同一面牆。
- [x] ✅ **唯一真的有轉移的東西：把 operating point 選對**。只用 dev 資料選 fake
  門檻（`stressdev`：300 張 AIGuard/**fake** 來源圖 ×8 條件，與所有 gate、所有
  Layer2 train/val stem 互斥；規則＝在 dev 上追平 production 安全水準的最大門檻
  → `t_f*`=0.14），然後 gate 只讀一次：用**磁碟上已經存在的兩顆 checkpoint、
  零重訓、模型數量與大小不變**得到 —— 壓力測試 **3.71%→2.97%**（配對 bootstrap
  −0.74pp，95% CI [−1.27, −0.26]）、Shadow balanced **43.55%→52.69%**
  （+9.13pp [+6.27, +12.01]）。**本專案史上第一個在兩個爭議軸上同時勝過
  production 的組態**。
- [ ] ⚠️ **但提案人自己不建議晉升，已送出待人工審核**：
  `docs/team/change_proposals/20260819_p1_r8_layer1v812_cellA_dualhead_tf014.md`
  （八節齊全，**Approval Record 刻意留白——agent 不得自我核准**）。理由：三項
  Freeze-Gate A 指標退步幅度超過本輪事前宣告的雜訊容忍度（True Test paired
  balanced −0.80pp、AUROC −0.0136、Alibaba −1.56pp），雖然三者都仍通過絕對門檻
  （80.32% ≥80%、0.8014 ≥0.80、96.61% ≥95%）但 AUROC 與 paired balanced 的餘裕
  已經很薄；且 Layer2 換成 dual-head 後，20.91MB / 14.4ms 的手機數字**必須重測**
  才能談部署。
- [ ] **下一個真正不同的槓桿必須長什麼樣（本輪的結論性建議）**：不是更多濾鏡資料、
  不是再加一個 loss、不是再拆一顆 head、也不是再調門檻——那些都只是在同一條曲線上
  移動。曲線本身是被「fake 通道在沒訓練過的攝影風格上分不出真假」決定的。要移動它
  只有三條路：① **取得以 in-the-wild 底圖（VGGFace2/IMDB-WIKI 風格）生成的 fake
  訓練資料**——本專案現有的每一個 fake 來源都自帶特定攝影風格，等於每一列訓練資料
  裡「fake」與「攝影風格」都是混淆的，這需要一個目前沒有的 generator，是打開這個
  僵局**單一價值最高**的取得項目；② **重新界定產品主張**：在域外攝影風格上只輸出
  `manipulated` vs `real`、保留 fake/filter 的區分不做（dual head 本來就支援三態
  輸出）；③ 接受這條曲線、把 operating point 當成一個明確的產品決策（即上面那份
  提案）。
- [ ] （可選，純寫作）論文 Limitation 章節可直接引用本輪：作為「六種訓練介入 vs
  一個門檻旋鈕」的對照示範，以及 operating-point 紀律（trap #1）的教科書案例。

## C1.5-OLD｜（已併入上方結案摘要，保留原始候選內容供追溯）

> 承接 P1-R5：loss 側四種介入（校準／margin／variance/輔助監督）已全部證實無效，這是唯一還沒試過、且有明確理論根據的槓桿。**核心思路不是這個團隊自創的**——「比較改動區域跟同一張圖裡未改動區域的統計特徵差異」是影像取證領域已驗證超過 15 年的經典原理（noise-residual/PRNU 系列鑑識方法即是此邏輯），近年在 Face X-ray（CVPR 2020，比較影像內部不同區域邊界一致性）與 BG-REAL benchmark（matched authentic control + self-comparison baseline）都有直接對應的現代版本。P1-R5 已經量出「配對比較下模型勝率 78-84%」，代表模型內部其實有能力分辨，只是單張圖推論時沒有參考基準可比——這正是 reference-region 方法要補的那塊。

- [ ] **P1-R6 核心設計**：用同一張圖片裡未被濾鏡動過的區域（背景／頭髮／脖子，濾鏡操作全部是 face-masked，這些區域理論上保持原狀）建立 per-image 的雜訊參考基準，把 filter head 的判斷從「這張圖的絕對分數」改成「臉部區域相對於同圖背景基準的偏移量」
- [ ] 需要先確認：untouched 區域（背景/頭髮/脖子）在四種濾鏡操作下是否真的保持不變（P1-R5 沒有驗證這件事，是新設計前的必要 sanity check）
- [ ] 對照組設計沿用 P1-R5 的紀律：至少一個近乎零架構改動的版本（例如單純算 face-region 分數相對 background-region 分數的差值/比值，不需重訓）+ 至少一個涉及表徵學習的版本（例如把 self-referential contrast 訊號當 auxiliary input 或 attention 訊號）
- [ ] 驗證方式沿用 P1-R5 的規範：held-out 一次性評測、**threshold-matched 換算成同一 false-filter 誤報率再比較，不可只看單一 shared threshold**（見上方「已知陷阱模式」）
- [ ] eye_enlarging / face_reshaping 兩種幾何型濾鏡另有 information-theoretic 上限（P1-R5 量出位移量已逼近 landmark 偵測器雜訊下限），reference-region 方法對這兩種的改善空間可能有限，須另外評估是否值得用更高解析度輸入換取（會實質衝擊 20.91MB / 14.4ms 手機部署預算，需明確權衡不能假設沒代價）

- [x] ✅ **2026-08-13 v8.16-mixed-lineage（Source-Diverse Composite Training）完整驗證，判定：負面但有資訊量的結果,不升級,不追v8.17**。假設：v8.15-C的filter head學到的是「AIGuard/fake底圖風格×自建filter管線」的組合痕跡而非可跨fake來源辨識的filter屬性（由獨立`v815_replication_set`上AUROC=0.5304、joint recognition=2.02%確立,幾乎亂猜）。介入：init自Cell C,加入AIGuard/fake+DF40-ff（sd2.1/DiT/SiT/ddim/pixart）六來源×8種filter條件的成對composite訓練資料（每來源300張base,共16,144筆new pairs,`build_v816_manifest.py`）,只改資料不改架構（沿用Cell C的unfreeze conv5+FFT最後層、無invariance loss）。
  - **啟動前checkpoint ancestry audit**（`audit_cellC_checkpoint_ancestry.py`）：Cell C整條血緣（回溯至v812 base）本身就帶約11,000-11,700筆DF40-cdf,不是這輪才混入——結論標記為`v816-mixed-lineage`,不宣稱乾淨的Protocol-2隔離（v816自己的新split本身已驗證0筆cdf洩漏）。
  - **啟動前3項assert抓到1個真bug**：DF40方法間檔名撞號（不同generator共用同一套底層FF++影格編號,如sd2.1與ddim都有「766_360.png」）導致原本按來源各自獨立分train/val造成同一身份跨split——已修正為全域跨方法統一依stem分配,重跑後3項assert全過。
  - **完整結果（門檻校準前後對照，決定性教訓：未校準的提升是假象）**：

    | 指標 | Cell C@0.85 | v8.16@0.85（未校準）| **v8.16@0.95（正確校準）**|
    |---|---:|---:|---:|
    | DF40-cdf filter-head AUROC | 0.5304 | 0.6182 | （同,門檻不影響AUROC）|
    | DF40-cdf joint recognition | 2.02% | 11.21%（灌水）| **4.53%（真實殘留訊號）**|
    | In-domain clean-fake false-filter | 4.59% | 10.04%（惡化超過1倍）| **2.97%（正確控制）**|
    | In-domain joint recognition | 56.99% | 61.40%（灌水）| **42.33%** |

    **門檻選擇規範**：只用`v816_val.txt`（in-domain）做threshold sweep選0.95,DF40-cdf完全不參與門檻選擇,選定後才拿來做最終confirmatory測試（`threshold_sweep_v816.py`跑之前發現一個計數bug：v816新composite pairs的origin欄位標成`v816-{source}`而非`composite`,原本用origin字串比對會漏掉1,611筆新資料,已改用`fake_target`/`filter_target`數值分類修正）。
  - **按類型/來源拆解（校準後）**：殘留改善集中在smoothing_medium（18.2%）、ddim（15.0%）、SiT（4.2%）、DiT（3.5%）；**whitening_medium、eye_enlarging、face_reshaping、pixart、sd2.1 校準後全部是0.0%,完全沒有殘留效果**——證實只加一個額外fake來源、每來源約300張composite,不足以讓filter-head學到跨generator、跨filter類型的通用表徵。
  - **決策：v8.16-mixed-lineage定位為research candidate,不進pipeline、不取代v8.11、不宣稱解決跨來源泛化。不再為此追加資料、調threshold或訓練v8.17**——這是負面但有資訊量的結果,證明「加一種來源不夠」，但不代表「加多種來源沒用」，只是目前規模與方法尚未達到可用程度。

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
      > 🔴 **2026-08-21 更正（本條拍板結論已被推翻，數字不變）**：上方①的 identity overlap
      > 查證是**用 FFHQ index 範圍比對**做的，而 P1-R11 的內容層級稽核證實 index 比對
      > **看不見真正的重疊路徑**：`FFHQ_ali_process` 與訓練資料有 **23.5%（4,980/21,151）
      > 內容重疊**，來源是 `AIGuard/real` 與 `filter_data/*` 含相同 FFHQ 底圖照片、以不同檔名存在
      > （不是 Megvii——index 確實不相交）。
      > **仍成立**：97.8%／98.1% 數字、eval pipeline 一致性、「跨濾鏡演算法（不同公司實作）」主張。
      > **不再成立**：「OOD」「真正跨域泛化」「filter 類跨域證據缺口已填上」。
      > 追 Tencent／RetouchingFFHQ MAM 對照的優先度應**調回原本水準**（見 `docs/paper_outline.md` 對應更正）。
      > 證據：`results/research/p1_r11_leakage_scaling_20260820/TASK1_LEAKAGE_AUDIT.md`
- [x] **✅ 2026-08-02 CelebA real OOD雙重查證完成（比照Alibaba同等級）— 第三個headline跨域數字**：①identity/partition overlap——CelebA官方`list_eval_partition.txt`本身identity-disjoint設計（train/val/test三個partition的身分完全不重疊，官方協定非本專案自訂），本地逐一驗證celeba_train/celeba_test/celeba_val三個資料夾100%對應各自partition、零混用；②eval pipeline一致性——`eval_v811_gates.py`直接import`pipeline.preprocess_jpeg`，架構與`hierarchical_predict()`邏輯一致。**拍板：CelebA real recall=99.7%（v8.11）可信，與Alibaba OOD=97.8%、AIGuard/unseen AUROC=0.8112並列成三個class（real/filter/fake）各自的headline跨域證據**（⚠️ **2026-08-21 更正：Alibaba 那一項已降級為「跨濾鏡演算法，非 OOD」，見上一條目；CelebA 與 AIGuard/unseen 本身查證仍然有效、不受影響**。現況為 real/fake 兩組乾淨跨域證據 + filter 一組跨演算法證據，「三個 class 皆已收斂完整」不再成立）。同時明確保留Shadow real recall=75.5%（v8.11）誠實揭露的trade-off框定，不與CelebA混為一談（兩者難度與定位不同：CelebA是「同樣網路人臉照片不同partition」的OOD，Shadow real是「完全不同身分來源+更貼近部署場景」的robustness壓力測試）。至此C線（外部/跨域驗證）三個class皆已收斂完整，正式可關閉，回頭進入論文框架整合。完整查證見`docs/Dataset 清單.md` 2026-08-02條目

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

## ⚠️ 2026-08-11 修正：「fake 沒有 region-level GT」這句話不精確，FF++ 其實有 mask

之前在 Phase 2 文件與 pipeline.py 註解裡寫「fake 沒有 paired before/after ground truth，所以只能 global-level explanation」，這句話對**目前實際訓練用的 fake 來源（AIGuard/DF40 EFS）**是對的——這些是 diffusion 整臉生成，沒有官方 mask，DF40 官方也沒提供逐像素 manipulation mask。但**這句話不該泛化成「fake 天生沒有 region GT 可用」**，因為：

- **查證確認**：FF++ 官方對經典四種手法（Deepfakes/Face2Face/FaceSwap/NeuralTextures）都有提供 binary manipulation mask（`download-FaceForensics.py <path> -d <method> -t masks`）。Face2Face/FaceSwap 的 mask 較精確；Deepfakes 是矩形框（Poisson blending 套用範圍）；NeuralTextures 是追蹤區域。
- 這代表**如果之後真的把 FF++ 拉進來**（目前規劃是純 zero-shot OOD eval，不進訓練，見上方 FF++ 討論），會**同時解鎖一個目前完全沒有的能力**：用 FF++ 的官方 mask 當 fake 的 region-level ground truth，比照 Phase 2 對 filter 做的 LAB-diff/landmark GT 方法論，重新評估 Grad-CAM++ 對 fake 定位的準確度——這是目前完全空白、但技術上可行的方向。
- **但要精確限定範圍**：這只適用於 FF++ 的經典 identity-swap/reenactment 手法（有明確「被動過的區域」概念），**不適用於我們目前 fake class 主力的 DF40 EFS diffusion 方法**（整臉生成，沒有「哪個區域被動過」這個概念，也沒有官方 mask）。所以就算做了，也只能誠實框定為「FF++ 子集的探索性分析」，不能宣稱解決了「fake 的 region-level 解釋性」這個更大的問題。
- **待辦（等 FF++ 下載到位後）**：評估要不要做這個探索性分析；純寫作上，`docs/phase2_story.md`／`pipeline.py` 註解裡「fake 沒有 region GT」的措辭要修正為「目前訓練用的 fake 來源沒有 region GT；FF++ 經典手法有，但屬於不同的偽造家族，尚未整合」

## E｜文獻對照實驗（成本較高，價值大）

- [x] ✅ **2026-08-23 FF++ 官方 protocol benchmark 完成 —— 本專案第一組文獻可直接對照的數字，同時證偽「FF++ 表現差 = H.264 domain gap 架構限制」這個沿用數月的敘事**（輪次 `ffpp_protocol_20260823`，回應 paper-readiness 稽核的 D1 Disqualifying 項）
  - **Protocol 是 OFFICIAL 不是 reconstructed**：直接取自 `github.com/ondyari/FaceForensics` 的 `dataset/splits/{train,val,test}.json`（副本已存本輪資料夾），360/70/70 個 video-ID 配對 = **720/140/140 個唯一 real video ID**，與原論文所述一致；c23（文獻主報設定，raw/c40 未下載不報）。Fake `{a}_{b}.mp4` 僅在 a 與 b **皆屬同一 split** 時歸入，source 與 target 身份都不跨界
  - **抽幀**：新增 `extract_ffpp_protocol_frames.py`（既有 `extract_ffpp_frames.py` 每部影片只取 1 張中間幀、無 split 概念，遠不足以訓練，故不改寫、維持既有零樣本記錄可重現）。均勻間隔多幀、跳過前後 10%；人臉偵測/裁切**完全沿用專案既有方法**（MediaPipe FaceLandmarker + landmark hull + MARGIN=0.35 + JPEG q90），與 `pipeline.py` 前處理一致。實得 train 27,687 / val 1,059 / test 6,620 幀
  - **汙染稽核三項全 PASS（Known Trap #3 內容金鑰 = 解碼像素 SHA256）**：①磁碟實際檔案反推的身份 ID 三 split 兩兩交集 = 0/0/0 ②三 split 間像素金鑰重複 = 0/0/0（35,366 張全唯一）③FF++ **test 幀** vs. v8.17 production Layer1 **實際訓練語料**（`layer1_sbi_augreal_train.txt`，256,968 列）重複 = **0**。限制：該 split 有 20,295 列（7.9%）指向已刪除的 `v89d_candidate_pool/`，無法計算金鑰——與 `paper_readiness_execution_20260822` 記錄的是同一批既有缺檔，非本輪造成
  - **結果（官方 test split，frame-level pooled AUC / 逐 method frame acc，全部附 Wilson 95% CI）**：
    - 本專案 dual-branch **FF++ 同域訓練**：AUC **0.9155**，DF 85.93 / F2F 84.29 / FS 84.12 / NT 80.07；video-level pooled AUC **0.9467**
    - 本專案 spatial-only **FF++ 同域訓練**：AUC **0.9144**，DF 86.27 / F2F 83.99 / FS 84.35 / NT 80.82；video-level pooled AUC **0.9474**
    - **v8.17 production Layer1 零樣本**（從未見過 FF++）：AUC **0.5747**，acc 54.80%
    - **v8.17 完整 pipeline 零樣本**：AUC **0.5727**，acc 52.10%
    - **已核實文獻**：FF++ 原論文（Rossler et al., ICCV 2019, arXiv:1901.08971）**Table 5**（四種 manipulation 一起訓練，與本輪同類設定）HQ/c23 XceptionNet = DF **97.49** / F2F **97.69** / FS **96.79** / NT **92.19**。本輪落後 11.2–13.4pp
  - **核心結論**：同一個架構、同一批 test 影格，**只把訓練資料換成 FF++ 官方 train split，pooled AUC 就從 0.575 跳到 0.916（+0.34），架構未動一個位元組** → 「FF++ 接近亂猜」是**訓練資料涵蓋問題**，不是 H.264 domain gap 的架構限制
  - **FFT 分支第二次獨立複現「量不出貢獻」**：spatial-only 參數少 29.6%（1.78M vs 2.53M）、checkpoint 小 29.2%（7.30 vs 10.31 MB），FULL−SPATIAL 的 AUC 差在 4 個 method + pooled **5/5 個 scope 的配對 bootstrap 95% CI 全部含 0**；Trap #1 matched-FPR 5%/20% 下 spatial-only 不輸反略優。這是繼 `paper_readiness_execution_20260822` Task B 之後、在**完全不同資料集 + 完全不同訓練起點（ImageNet init 而非 production checkpoint）**下的第二次獨立複現，強化「可移除 FFT 分支」論據（連帶解鎖 int8——int8 失效根因正是 FFT magnitude 的 7.6e9 動態範圍）
  - **⚠️ 誠實記錄的反向訊號（Trap #2 部分不通過）**：在 **FPR ≤ 1%** 極低偽陽率區間 dual-branch **一致領先** spatial-only（pooled TPR@1% 0.4069 vs 0.3154，四個 method 全部同方向），FPR ≥ 5% 後差距消失甚至反轉。**不可宣稱 FFT 分支「完全無用」**，正確措辭是「在 FPR ≥ 5% 的一般操作區間與整體排序上量不出差異」
  - **不可宣稱**：不可宣稱在 FF++ 達到/接近 SOTA；不可把本輪數字放進原論文 **Table 4**（per-manipulation 專屬模型，設定不同）；不可宣稱本輪模型可取代 production（僅做 FF++ real-vs-fake 二分類）
  - **論文表格註腳必須寫的設定偏差**：訓練幀數比文獻少一到兩個數量級（本輪 27,687 張 vs 原論文每部影片 270 張訓練/100 張測試）；backbone 差一個數量級（1.78–2.53M vs Xception 約 22M）；未做文獻常用臉部對齊
  - **實作坑（已修）**：四種 manipulation **共用同一組 fake 檔名**（Deepfakes 與 FaceSwap 都有 `035_036.mp4`），video-level 聚合若只用 video_id 當 key 會把同一部影片的四種偽造併成一部「平均影片」，pooled 影片數從 544 塌成 136 → 已改 `(method, video_id)` 複合 key
  - **無 production 變更**：`pipeline.py` 與所有 production checkpoint 唯讀未改。完整寫作 `results/research/ffpp_protocol_20260823/FFPP_PROTOCOL_FINDINGS.md`，registry 條目 `docs/EXPERIMENT_REGISTRY.md` 的 `FFPP-PROTOCOL-20260823`
- [x] ✅ **2026-08-24 FF++ improvement round 完成 —— recipe/backbone/FFT 三個問題全部有明確答案**（輪次 `ffpp_improve_20260823`，承接上方 `ffpp_protocol_20260823`，val 選型、test 只評測一次）
  - **Recipe（Part 1）**：train 幀從 27,687→83,038（60/real影片、15/fake影片，`extract_ffpp_dense_train_frames.py` 沿用既有偵測/裁切邏輯，val/test 未觸碰）+ AdamW 20-epoch schedule，**顯著且可疊加**提升 AUC（test pooled AUC 0.9155→0.9331，+0.0175，95% CI 不含0）；JPEG/縮放/模糊增強（compressed-video 風格）**顯著變差**（val AUC −0.0189，CI 不含0）——與 CLAUDE.md 記錄的 v8.7（filter 任務盲目增強拖累 5/7 指標）同一教訓在 FF++ 任務上第二次獨立驗證
  - **Backbone（Part 2）**：MobileNetV4/EfficientNet-Lite0/RepViT/FastViT 全部在 test pooled AUC 上**顯著**贏過現行 ShuffleNetV2（CI 全不含0，最小 delta +0.0228）。**RepViT-M0.9 最佳**（test pooled AUC 0.9546，+0.0391），加 dense+long recipe 後 test pooled accuracy 91.86%（Deepfakes 93.57/Face2Face 91.90/FaceSwap 92.35/NeuralTextures 88.96），對 Xception 文獻差距從 baseline 的 −11~−13pp **縮小 57-73% 到 −3.2~−5.8pp**，參數量 5.67M（仍是 Xception 22M 的 1/3.7），CPU 延遲 28.9ms（vs ShuffleNetV2 19.0ms）。完整 params/ckpt大小/CPU-GPU延遲表見 `results/research/ffpp_improve_20260823/FINDINGS.md` §3
  - **FFT 分支（Part 3，回應上一輪「量不出貢獻但方向一致」的開放問題）**：跨 3 個獨立訓練種子 × 4 method + pooled（15 個 scope×seed 格），FULL−SPATIAL 的 TPR@FPR=1% delta **15/15 全部同號為正**（二項式 p≈0.00003），但只有 3/15 格 95% CI 不含0（皆在 seed=22）。**判決：FFT 分支對低 FPR 有真實、方向一致、可複現、但幅度中等且非每次顯著的貢獻**——這是繼 `paper_readiness_execution_20260822`、`ffpp_protocol_20260823` 之後第三次在不同資料集/訓練起點看到同一方向。建議：低 FPR 敏感部署保留 FFT 分支；追求 int8 量化與更小模型則可拿掉，整體 AUC/accuracy 無可量測代價
  - **無 production 變更**：`pipeline.py` 與所有 production checkpoint 唯讀未改，本輪不提 change proposal。完整寫作 `results/research/ffpp_improve_20260823/FINDINGS.md`，registry 條目 `docs/EXPERIMENT_REGISTRY.md` 的 `FFPP-IMPROVE-20260823`
  - **已知限制（誠實記錄）**：backbone 比較僅單一種子（RepViT 等未跨種子重跑，Part 2 顯著性建立在單一訓練實例）；dense+long recipe 只在 shufflenet 與 repvit 上各跑一次，其他 3 個 backbone 加 recipe 後數字未知；訓練幀密度（60/15）仍遠低於文獻（270/影片），是本輪與文獻差距最大的單一可解釋來源，受時間/磁碟限制未進一步加密
- [x] ✅ **2026-08-25 production candidate v2：FF++ 資料整合 + RepViT backbone swap，在完整 production 任務上評測——兩條 stream 皆 NO-GO，但都是真實、可複現、有建設性下一步的結論**（輪次 `production_candidate_v2_20260823`，承接 `ffpp_protocol_20260823`/`ffpp_improve_20260823` 的 benchmark-only 結果，回應「要真正的候選，不是又一輪測試」的要求）
  - **Stream 1（FF++ fake frames 加進 production 資料，P1-R9 原版 recipe 逐位元組沿用，2 seed）**：內容金鑰去重全過（0 碰撞）；既有 gate 全部持平或微幅提升，但 **FF++ official-test frame AUROC 0.568/0.577，跟零樣本 0.575 幾乎打平——沒有進步**（AUROC 與threshold無關，不是操作點問題）；FF++ 上 real recall 崩到 9-11%、fake catch 衝到 93-95%，說明加進去的資料只是把判斷閾值推向「全判manipulated」，沒有教會模型真正的可分性。**判定：NO-GO**
  - **Stream 1b（依協調者指示的修正 recipe 診斷跑，單一 seed，範圍限定）**：加 FF++ real frames 平衡類別 + LR 從 2e-5 提到 1e-4、5→10 epoch（沿用 `train_ffpp_improve.py` 已驗證的 ImageNet-init 適用 recipe，而非為續練converged checkpoint設計的低LR）。**成功修好排序能力**：FF++ official-test frame AUROC **0.808**、video AUROC **0.856**（在完整 6,620 幀官方 test split 上成立），但預設閾值下 fake+filter stress error 從 2.80% 惡化到 8.17%（近三倍）。**用 threshold sweep（0.05-0.95）逐格檢查，找不到任何單一閾值能同時達到 production 的 True Test real recall 與 stress error水準**——tm=0.25 時 stress error 2.27%（贏過 production）但 True Test real recall 崩到 47.2%（-25.5pp）；把 tm 推到 0.65-0.70 恢復 real recall 到 production 區間時，stress error 又回到 production 的 5-6 倍，FF++ 增益也消失大半。**這是整條 threshold frontier 的結構性 trade-off，不是校準問題，調閾值救不回來**。附帶發現：val split 完全不含 FF++ 資料列，導致「best macro-F1」選模規則對 FF++ 能力視而不見（選中的 epoch 1 遠弱於 epoch 10，AUROC 0.683 vs 0.808）。**判定：NO-GO**，但確認 Stream 1 的瓶頸是 recipe 太弱，不是「加 FF++ 資料」這個想法本身錯了
  - **Stream 2（RepViT-M0.9 backbone swap，用 production 實際多來源訓練資料，2 seed，ImageNet init + `train_ffpp_improve.py` 已驗證的 ImageNet-init LR/epoch regime——因為沒有 RepViT 相容的 production checkpoint 可續練）**：兩個 seed 一致的真實提升——True Test filter recall +4~4.4pp、fake recall +0.37pp、AIGuard-unseen AUROC +2.7~3.9pp，且 **FF++ 零樣本 frame AUROC 0.686-0.708（vs production 0.575），純粹 backbone swap 效果、零 FF++ 訓練資料**。兩個 seed 一致的真實退步——**Alibaba filter recall 82.6-86.7%（vs production ~98-100%，掉 12-15pp）**、Shadow filter recall 低於 production 既有 ~15.8% 天花板、fake+filter stress error 變差且 seed 間變異大（3.19%/5.68%）。TFLite 匯出 G1-G4 全過（22.43MB fp32 Layer1 單獨、17.4ms/張 CPU、數值誤差 max|dprob|=2.4e-7）。**判定：NO-GO 當作直接替換**（Alibaba/Shadow/stress 退步是真實的，非雜訊），但是誠實的 trade-off，不是單純輸給 production
  - **Combined candidate 未建立**（pre-declared：兩條 stream 都要先各自過 GO 才嘗試合併，兩者皆未過）
  - **無 production 變更**：`pipeline.py` 與所有 production checkpoint 唯讀未改，本輪不提 change proposal。10 個新 checkpoint 全部留存於 `checkpoints/research/production_candidate_v2_20260823/` 供未來參考，皆未升級。完整寫作 `results/research/production_candidate_v2_20260823/CANDIDATE_FINDINGS.md`，registry 條目 `docs/EXPERIMENT_REGISTRY.md` 的 `PRODUCTION-CANDIDATE-V2-20260823`
- [x] ✅ **2026-08-26 P1-A1 後續兩項皆完成，結論明確為 NO-GO——「配菜不當主菜」假說在 mission 指定 recipe 下被證偽，init 血緣混淆已排除**（輪次 `p1_a1_ffpp_dose_20260826`，承接上方輪次的兩項後續建議）
  - **文件更正**：發現 `AIGuard/train_pcand_v2_layer1.py`（上輪 Stream 1b 腳本）`--lr` 參數從未接進 optimizer（optimizer 用的是模組常數 2e-5，不是 CLI 傳入值）；weight-drift 鑑識確認 **Stream 1b 實際跑的是 LR=2e-5×10epoch，不是文件寫的 LR=1e-4**（測到的數字 AUROC 0.808／stress 8.17% 本身正確，只有 recipe 歸因錯了）。`production_candidate_v2_20260823/CANDIDATE_FINDINGS.md` §3 已加註更正。另確認**兩輪至今沒有任何一個 arm 真正從 production 初始化過**——S1/S2/S1b/RepViT/本輪前兩個 arm 全部從 `shufflenet_v2_layer1_v811d.pth`（P1-R9 自己的 init）或 ImageNet 開始
  - **Task 1（FF++ 劑量降階）**：4k fake+4k real（佔語料庫 3.27%，上輪 41.5K/41.5K 佔 13.0%），內容金鑰去重全過（0 碰撞/7 母體）。三個 arm（皆單一 seed 20260819）：`d4k_lr1e4_s1`（mission 指定 recipe LR=1e-4）、`d4k_lr2e5_s1`（S1b 實際 recipe LR=2e-5，劑量單一變數對照）、`d4k_lr2e5_prodinit_s1`（同上但 init=production，SHA256 已驗證）。**三個 arm 全部在 stress error（6.25-8.17% vs 門檻≤3.00%，production 2.80%）與 True Test real recall（64.3-69.1% vs 門檻≥70.7%，production 72.69%）雙雙未過，沒有邊界案例，依協議不需第二 seed**。Per-epoch 曲線顯示 stress 惡化在**第 1 個 epoch 就出現**（3.71%→7.43%）且 10 epoch 內未恢復——是 LR 造成的立即校準偏移，不是 FF++ 資料累積效應；threshold sweep（Known Trap #1）證實同上輪 S1b 一樣是結構性 trade-off，調不回來。**判定：「配菜不當主菜」假說在 mission 指定的 LR=1e-4 下被證偽（劑量降低對 stress 完全沒幫助）；在 LR=2e-5（S1b 實際 recipe）下部分成立但仍不足（劑量降低約可減半 stress 超出量，但代價是 FF++ AUROC 增益幾乎全部流失，0.808→0.66-0.67，仍低於本輪已放寬的 0.70 門檻）**
  - **Init 血緣混淆檢查（協調者中途加做）**：同資料/recipe/seed 下，production-init 與 v811d-init 每項 gate 差距 ≤0.81pp／≤0.0051 AUROC，小於或接近本專案一般 seed-to-seed 雜訊量級。**判定：init 血緣不能解釋任何觀察到的 trade-off**，production 訓練出的 Layer1 與 v811d 經過這個 fine-tune 後收斂到幾乎同一個地方，與起始點無關
  - **Task 2（Layer2 脫鉤驗證，純分析不訓練）**：Layer2 在 5 個 arm、全部母體上驗證輸出逐位元組一致。**Alibaba filter recall 退步（RepViT，-12~-15pp）100% 來自 Layer1 gating**（Layer2 在能收到的圖片上準確率 99.96-99.98%，Layer2 完全無責，上輪建議的「Layer2 側修法」無效）。**Shadow filter recall（各 arm 皆 10-12%）受 Layer2 天花板（15.77%，各 arm 皆同）限制**，Layer1 另外貢獻一個獨立、同量級的 gating 損失（僅 51-59% 的 Shadow filter 圖片會被送進 Layer2）；修 Shadow 需要動 Layer2 或架構本身（P1-B2），不是 FF++ 劑量問題。**Fake+filter stress 退步 100% 來自 Layer1 gating**（Layer2 每個 arm 都只誤判 1 張）
  - **無 production 變更**：12 個新 checkpoint（3 arm × best/last + per-epoch 快照）留存於 `checkpoints/research/p1_a1_ffpp_dose_20260826/`，皆未升級。完整數字見 registry 條目 `docs/EXPERIMENT_REGISTRY.md` 的 `P1-A1-FFPP-DOSE-20260826`（本輪 `results/research/p1_a1_ffpp_dose_20260826/FINDINGS.md` 因 subagent 工具限制未能落檔，完整內容已交付於對話紀錄，registry 條目為正式記錄來源）
- [ ] **P1-A1 下一步建議（承接本輪結論）**：不要再測「劑量」或「LR」這兩個維度本身——問題是「epoch 1 的決策面偏移量」需要被直接約束（例如明確的正則化項、或凍結/低 LR 保留安全相關子網路），MASTER_PLAN §6.1 原本的建議方向仍未測試；init 血緣已證實不是變數，未來輪次可放心用 v811d init 不必再論證；Alibaba 修法必須動 Layer1/gating，Shadow 修法必須動 Layer2 或架構本身
- [x] ✅ **2026-08-24 B1（缺負類）已解掉；量出 filter 任務第一個文獻可對照的二元修圖偵測數字——負面結果**（輪次 `retouching_benchmark_20260823`，回應下方 B1/B3 阻礙清單）：只下載 Alibaba 需要的 2,210 張 FFHQ 原圖（index 17001-19999，HuggingFace `marcosv/ffhq-dataset` 逐張下載，3.02GB，不下 90GB 全量；60002-69999 範圍**刻意不下載**——量測證實該範圍原圖與自己的修圖版本 99.48% 落在本專案自訂 NEAR_DUPLICATE 門檻內，且 100% base index 已進過 production Layer1/Layer2 train 或 val，下載了也不能當負類）。三層內容金鑰過濾（import 而非重寫 `p1_r11_leakage_scaling_20260820` 的稽核原語）：L1 base-index 揭露篩（four/megvii 存活 0、ali 存活 669）→ L2 正類 row 篩（重用 `ood_filter_ali_clean_20260821.txt`）→ L3 負類內容金鑰篩（527 候選中 87 張／16.5% 與 production 訓練照片近乎重複，已排除）。**最終乾淨子集：440 張原圖／4,162 張 Alibaba 修圖**。Harness 先用 CelebA／True Test 既有記錄數字驗證有效（99.66% vs 99.6-99.7%、72.80% vs 72.40%，皆吻合）。**結果：v8.17 二元「有無修圖」判斷 balanced accuracy 僅 50.7-51.2%（等同亂猜），specificity 僅 3.9-4.8%**——模型幾乎把所有臉都判成「有濾鏡」；唯一存活訊號是 paired 同底圖比較（retouched 分數較高 66.07%，CI 不含 50%），證明有方向正確的訊號但被系統性偏誤蓋過。型別辨識上界（type-argmax，非論文 TP）重新確認既有「Alibaba 跨演算法型別準確率 3-35%」結論（僅 eye_enlarging 78.6% 顯著優於隨機）。文獻對照：RetouchingFFHQ 原論文**從不報二元指標**（無格可對）；ND-IIITD/MDRF（Bharati et al., IJCB 2017）同域訓練 accuracy 79.3-97.5%，本專案零樣本落後 41-47pp，與 FF++ 那輪「零樣本代價非架構上限」同一故事第二次獨立複現。**B3（標籤空間不相容）依然開著，未解**——本輪只解 B1。無 production 變更。完整寫作 `results/research/retouching_benchmark_20260823/FINDINGS.md`，registry 條目 `docs/EXPERIMENT_REGISTRY.md` 的 `RETOUCHING-BENCHMARK-20260823`
- [ ] RetouchingFFHQ MAM 頭對頭比較實驗（同資料集下 vs 你的 ShuffleNetV2+FFT，量化「輕量替代」主張）— **⛔ 2026-08-23 判定：以目前手上資料 NOT protocol-faithfully evaluable，五個獨立阻礙**（`audit_retouchingffhq_protocol_feasibility.py` → `retouchingffhq_feasibility.json`，從磁碟實際內容判定非推測）：**B1（硬，2026-08-24 已解——見上方新條目）** ~~58,158 張未修圖 FFHQ 原圖完全不在專案磁碟上~~；**B2** `FFHQ_megvii_four_process`（33,474 張）無任何 level 標註檔（`FFHQ_four_process` 有 `four_process.txt`、`FFHQ_ali_process` 以資料夾名編碼，這兩個有）；**B3（硬，仍未解）** 標籤空間不相容——本專案 `artifact_classifier` 是 single-label 4-way head，該論文是 multi-label × multi-level（`four_process` 每張四型別同時開啟），TP/TN/AC **結構上無法輸出**；**B4** 官方 80/10/10 index 清單未公開（repo 以申請表擋住），自建 split 只能是 reconstructed；**B5** 專案只有 Megvii(60000–69999) 與 Alibaba(17000–19999)，Tencent 未取得，論文 headline 是 Megvii→Tencent 而專案只能 Megvii→Alibaba（另一格）。**因此 filter 側的 Alibaba 跨演算法評測必須標為「本專案自訂 protocol」，不得與 RetouchingFFHQ 的 TP/TN/AC 並列同一張表**。補齊仍需要：範圍限縮到有 level 標註的兩個子集 → 另訓 4-type×4-level multi-label head → 向作者索取官方 index 清單／Tencent 子集
- [ ] 查證 FF++/SBI/MLFF+CNN/FAME 等文獻數字（**2026-08-23 部分完成**：**FF++ 原論文（arXiv:1901.08971）Table 4 與 Table 5 的 HQ/c23 數字已從全文逐字核實並記錄**於 `results/research/ffpp_protocol_20260823/FFPP_PROTOCOL_FINDINGS.md` §5.1；**SBI / MLFF+CNN / FAME / RECCE / GSD / RCDN / FDML / CrossDF 仍全部未驗證，一律不得寫入任何對照表**）
- [x] ✅ **2026-08-11 RetouchingFFHQ/MAM 引用資訊已查證**（本專案三批 FFHQ 資料的來源、也是「輕量替代」主張的對照 baseline）：標題／作者（Qichao Ying 等 6 人）／**arXiv:2307.10642**／2023 年／ACM MM 2023 皆確認；MAM = Multi-granularity Attention Module，CNN backbone 的 plugin。**但摘要完全沒有給任何 accuracy/AUC 數值（只寫 "decent performance"），跨資料集泛化也未提及** → 引用資訊可安全使用，**任何效能數字或「我們達到相當效能」的主張在讀完全文表格前一律不得寫入**。另注意該工作任務定義是「多類型多強度細粒度估計」，與本文三分類不同，**即使補上數字也非同任務直接可比**。詳見 `docs/paper_outline.md` 2.x 節
- [x] ✅ **2026-08-11 四篇 domain-generalization 文獻查證完成（原三篇已讀全文取得數字，新增查獲一篇最貼題的）**：
  - **GSD**（`arXiv:2603.09242v2`）：已讀 HTML 全文，正確概念是作者自定義的 **"semantic fallback"**（先前誤記為「semantic shortcuts」），方法為 CLIP ViT-L/14 + SVD 語意子空間抑制，數字 AUC 93.4→96.3。**結論：不適用——綁定大模型，無 filter 任務，只能引用概念不能引用數字對照**
  - **RCDN**（`arXiv:2601.12111`）：已讀 HTML 全文，dual-branch FFT+Xception + real-centered prototype，跟本文架構理念相近，數字完整（cross-domain avg AUC 0.9369）。**可引用其「real 分布優先建模」設計哲學佐證 Layer1 架構選擇，數字不可比**
  - **FDML**（Neurocomputing 2023）：**仍卡在 ScienceDirect 付費牆（403）**，僅二手摘要，不可引用數字
  - **✅ CrossDF/DID**（`arXiv:2310.00359v3`，新查獲、非原定三篇之一）：已讀 HTML 全文，**本輪最貼題**——把特徵分解成 forgery-related vs irrelevant 並用 de-correlation 強迫獨立，跟本文 Shadow 診斷（底圖風格與濾鏡痕跡糾纏）幾乎鏡像對應，**數字完整可引用**（cross-dataset AUC 0.779，優於 NoiseDF 0.759/CFFs 0.742/MDD 0.674，EfficientNetV2-L backbone）
  - **Future Work 修正**：具體方向改為「參考 DID 的 de-correlation 設計解耦 filter 分支的濾鏡痕跡與底圖來源特徵」，是四篇裡唯一任務性質、數字、方法都核實到位的方向

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


## J｜Phase 1 Robustness 其他項（原標題「Phase 3 Robustness」，2026-08-21 改名——見下方更正註記）

- [ ] DF40 Face Editing (FE) 歸類決策（語義偏 filter；若加入需重新確認標籤）
- [ ] H.264 domain gap 進階：Wavelet Transform 取代 FFT branch（架構改動大，augmentation 不足時再考慮）

## K｜Phase 2 未來研究方向草稿（原標題「Phase 3 研究計畫草稿」，2026-08-02 寫成，2026-08-21 改名）

> ⚠️ **2026-08-21 命名更正（Member A 裁定）**：本節與上方 J 節原本標題為「Phase 3」，
> 但這與 `docs/team/TEAM_WORK_ALLOCATION.md` 對 Member C 的定位（Phase 3 = 部署／UI／
> 輕量化，Android 平台）**衝突**——本節內容（VLM teacher 蒸餾、H.264 domain gap 架構
> 研究、robustness 壓力測試等）**性質上屬於 Phase 2（解釋性／XAI）的未來延伸方向**，
> 不是部署工作，正式定名為 Phase 3 之前一直是專案內部命名不一致造成的混淆。往後
> 「Phase 3」一律專指 Member C 的部署/UI/輕量化工作；本節內容改稱「Phase 2 未來研究
> 方向」。內容本身（VLM 蒸餾拍板、混合監督策略等）不變,只改標題與定位敘述。
>
> 定位：Phase 1+2已具備完整論文條件（架構：三分類trade-off→v8.11 hierarchical；XAI：FakeVLM失敗→Landmark GT+Grad-CAM++→pipeline對齊），主線先收斂成論文（見TODO最下方＋docs/phase1_story.md/docs/phase2_story.md），本節是收斂完成後才開始的新研究線，此處僅先定調不動手。

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
  - **P3-M0階段結論（2026-08-02）**：fake_prompt路線經bug修正+獨立閾值校準後**初步驗證可行**（held-out準確率73.3%）；filter_prompt的free-text/few-shot路線**已證實走不通**，需要改造成token-logit二元判斷方式才有機會，屬於未完成的後續工作。
  - **✅❌ 2026-08-11 token-logit 版 filter_prompt 已執行完畢 — 決定性負面結果，此路線正式關閉**（`run_teacher_filter_logit.py`，30 個來源照片 × 5 種狀態（乾淨 + 4 種濾鏡）× 4 個類型專屬問題 = 600 次 forward，全部用 fp32 兩-token logit 讀取，避開既知的 bf16 mantissa 捨入 bug）。**設計上做了內容控制**：同一批照片同時出現在乾淨與各濾鏡狀態，因此偵測是跟「同一張臉」比較，風格/內容偏誤無法偽裝成濾鏡偵測。
    - **逐類型偵測 AUROC（濾鏡版 vs 同一張來源照片的乾淨版）**：smoothing **0.703**、whitening **0.500**、eye_enlarging **0.529**、face_reshaping **0.489**。對照 fake_prompt 同法的 0.804——**沒有任何一種濾鏡達到可用門檻，三種完全等同亂猜（含一個低於 0.5）**。
    - **specificity 矩陣揭露更根本的問題**：smoothing 那一欄對**全部四個問題**的 p(yes) 都被推高（0.739/0.564/0.718/0.529，對照乾淨版 0.640/0.393/0.666/0.406），而 whitening/eye_enlarging/face_reshaping 三欄跟乾淨版幾乎完全一樣。代表模型只在濾鏡效果視覺上最明顯時（smoothing）察覺「這張圖被動過」，然後對**每一個**問題都傾向回答「有」——它偵測的是「有沒有被處理」的籠統訊號，**不是「被套了哪一種」**。這對 attribute-level 標註是致命的，因為 Phase 3 要的正是「哪一種」。
    - **拍板：Qwen2-VL-7B-Instruct 不能提供 filter 類型的 pseudo-label，free-text 與 token-logit 兩種形式都已證實不行**，不需要再試 few-shot 變體或提示工程（兩種取值方式都試過，失敗模式一致且機制清楚）。
  - **✅ 由此得出 Phase 3 的監督策略修正（有證據支撐，比原計畫更合理）**：原計畫是「VLM teacher 同時供應 fake 與 filter 的 attribute 標籤」。實測顯示應改為**混合監督**——
    - **filter attributes → 用程式化 GT，不用 VLM**：自建濾鏡 pipeline 是我們自己控制的，before/after 配對本來就存在，Phase 2 已經驗證 LAB diff / landmark 位移可以產出可靠的 region-level GT（eye_enlarging）與 whole-face GT（其餘三種）。既然 GT 拿得到，本來就不該用一個 AUROC 0.5 的 teacher 去猜。
    - **fake attributes → 才用 VLM teacher**：fake 沒有 before/after 配對、無法程式化生成 GT，而這正好是 VLM 唯一有訊號的地方（fake_prompt AUROC 0.804 / 校準後 held-out 73.3%）。
    - 這個分工不是退而求其次，而是**讓每種監督訊號用在它真正可靠的地方**，且兩邊的可靠度都已有量化證據。論文可直接寫成 Phase 3 的方法論設計理由。
  - [x] ✅ **後續（Phase 3 下一步）**：K 章節第 4/5 節已依混合監督策略修訂（見上）

- [x] ✅ **2026-08-11 P3-M1 pilot 已執行（filter 側 + fake 側），提前於 K 章節原訂順序**：

  **filter 側（程式化 GT，`build_p3m1_filter_attributes.py`）**：重用 `generate_landmark_gt.py` 的 `process_pair()`（原封不動 import，非重寫）。**這是 Phase 2 landmark/LAB-diff GT 的全新用途**——Phase 2 只拿它當「評分 Grad-CAM++ 等解釋方法準不準」的評測基準，這裡第一次把它轉成**訓練標籤**。4 種濾鏡類型各 250 張正樣本（`filter_data/`）對應到 attribute taxonomy（smoothing→texture_smoothing、whitening→brightness_elevation、eye_enlarging→eye_geometry_change、face_reshaping→jaw_geometry_change），涵蓋範圍**刻意擴大到全部4型**（region_head_v4 當年只練eye_enlarging）。
  - **⚠️ 第一次跑出來的結果是100%退化標籤，自己抓到並修正**：初版只抽了「已套濾鏡」的正樣本，二元標籤當然全部是True——這不是GT本身壞掉，是抽樣設計漏了負樣本。補上等量 AIGuard/real 乾淨對照組（250張/屬性，同一批負樣本共用給4個屬性）後重跑，4個屬性標籤分布全部平衡在50%，非退化。
  - 逐部位細節與 Phase 2 既有發現完全一致：eye_enlarging集中眼睛區（forehead/eyes ~100%，mouth僅6.4%）、face_reshaping集中臉頰下巴（cheek/jaw ~100%，mouth 77%）、smoothing/whitening偏全臉。
  - 輸出：`results/p3m1_filter_pilot/manifest.jsonl`（2,000筆）

  **fake 側（Qwen2-VL 校準後 teacher，`build_p3m1_fake_labels.py`）**：重用 `run_teacher_calibration.py` 的 `fake_prob_via_logits_fp32()`，套用已校準閾值0.676。從 AIGuard/fake 全池（56,572張）扣掉 True Test 與所有先前P3-M0樣本後隨機抽 500 張**全新**圖片。
  - **⚠️ 重要發現：recall 從先前報告的 73.3%（90張精選held-out集）掉到 57.2%（286/500，全新大範圍抽樣）**。分布本身不退化（p_fake從0.289到0.962都有，非卡在單一值），但這代表**先前的73.3%是在小規模、精選過的樣本上量出來的，換到更大、更「野生」的樣本範圍後準確率明顯下降**。
  - **對 Phase 3 規劃的直接影響**：若真的要拿 Qwen 產生的標籤去訓練學生模型，目前品質（57.2% recall，代表43%的真fake圖會被teacher標錯）風險比先前認知的高，**pilot 產出的標籤不能直接當乾淨訓練資料用，需要先做二次過濾或品質控管**（例如只保留 p_fake 落在高信心區間的樣本，犧牲覆蓋率換取標籤品質）
  - 輸出：`results/p3m1_fake_pilot/manifest.jsonl`（500筆，含 p_fake/p_real/pseudo_label 逐筆記錄）
  - [ ] **待辦**：設計並驗證上述二次過濾/信心區間篩選策略，重新評估過濾後子集的標籤品質是否夠格進真正的蒸餾訓練

**3. Attribute/Region Schema設計**（純設計階段，teacher選定前就可以做）：
- Attribute taxonomy：Geometric（eye/nose/jaw/lip/eyebrow_geometry_change）、Texture/Color（texture_smoothing/brightness_elevation/skin_tone_shift/makeup_artifact/color_grading）、Global（overall_sharpness_change/overall_color_shift/unknown_artifact）
- Region schema：forehead/eye_area/nose/cheek_area/mouth/jawline + whole-face（whitening/smoothing/face_reshaping用）+ 非臉區域候選（background/hairline/neck_shoulder，服務fake explainability的「背景合成感」描述）
- 教師輸出→學生label的mapping規則需設計（例：「皮膚平滑無毛孔」→texture_smoothing + region=face）

**4. 蒸餾資料來源與標註策略**（⚠️ **2026-08-11 依 P3-M0 結果全面改寫為混合監督**，原「VLM teacher 同時供應 fake 與 filter 標籤」的計畫已作廢）：

**核心改動：filter 與 fake 兩側改用不同監督來源，理由各有量化證據**

| 類別 | 監督來源 | 依據 |
|---|---|---|
| **filter attributes / regions** | **程式化 GT（不用 VLM）**：自建 pipeline 的 before/after 配對 → LAB diff + landmark 位移 | Phase 2 已驗證可靠；且 P3-M0 實測 VLM 對 filter 類型 AUROC 僅 0.489-0.703（三種等同亂猜），**用 AUROC≈0.5 的 teacher 去猜一個我們本來就有 GT 的東西沒有道理** |
| **fake attributes** | **VLM teacher 蒸餾（保留原計畫）** | fake 無 before/after 配對、無法程式化生成 GT；且這正是 VLM 唯一有訊號處（AUROC 0.804、獨立校準後 held-out 73.3%） |

- **filter 側資料來源**：自建 filter pipeline 套用於**多樣底圖**（LFW / AIGuard-real / FFHQ / IMDB-WIKI；VGGFace2 保留為 held-out）。粒度依 Phase 2 結論分流——eye_enlarging 給 region-level，whitening/smoothing/face_reshaping 給 whole-face，不假裝有更細的定位
- **fake 側資料來源**：AIGuard fake、DF40 EFS、StyleGAN2/3；teacher 輸出須經**獨立校準集**學閾值（P3-M0 已證實 naive 0.5 閾值只有 60%、校準後 73.3%），且校準集與評估集必須零重疊
- **Phase 3.1 pilot 的驗收條件（依 P3-M0 教訓新增）**：任何 teacher 標籤在進入蒸餾前，必須先通過 ① **分布健康度檢查**（是否退化成常數／近常數標籤，比照 v1 的 6/8 region 灌水與 Qwen2-VL 的 100% yes-bias）② **內容控制的區辨力檢查**（同一張圖的 before/after 對照，AUROC 需明顯高於 0.5）。**兩項任一不過即不得使用該標籤，改走程式化 GT 或誠實揭露為限制**
- 注意：fake 類部分 attribute 只能做到 global 而非 region，須在 schema 誠實標註，不可假裝有精確定位

**5. 學生模型與訓練目標**（2026-08-11 同步修訂）：
- backbone沿用v8.11 DualBranch（ShuffleNetV2+FFT），新增attribute head（multi-label sigmoid）+ region head（conv5 feature map + region pooling）
- 訓練目標：主分類CE（不變）+ attribute BCE/focal loss + region loss。**修訂：filter 分支改為純 GT-supervised（LAB diff / landmark 硬 GT），不再混入 teacher soft label**（P3-M0 證實該 teacher 對 filter 類型無區辨力，混進去只會注入雜訊）；**fake 分支維持純 teacher-distilled**（唯一無 GT 可用、且 teacher 確有訊號處）
- ⚠️ **部署端相容性硬性限制（2026-08-11 新增）**：任何新增的 head 都必須維持 TFLite 可匯出。`mobile_fft.py` 已把 FFT 分支的 `ONNX_DFT` 障礙解掉，**不要在新 head 引入新的不可匯出算子而重新製造同一個問題**；另注意含原始 FFT magnitude 頻譜的圖無法做 per-tensor int8 量化（動態範圍 7.6e9），若 Phase 3 有量化需求須採選擇性量化（conv stack int8、頻譜保 float）

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
- [x] **2026-08-10 Robustness壓力測試首次執行**（姿態/光線/解析度/多重JPEG，`AIGuard/eval_robustness.py`，對True Test 769張跑v8.11 hierarchical pipeline）：核心發現real recall對模糊/解析度損失極度敏感（baseline 66.8%→重度模糊k9崩到24.0%、4x降採樣崩到20.8%，fake/filter幾乎不受影響），推測為模糊後real圖視覺上更接近smoothing濾鏡效果，被誤判為filter；JPEG quality對real/filter recall呈現明確tradeoff（q85對filter最有利但real recall全部JPEG條件裡最低，q70相反），目前pipeline固定q85是偏filter優先的設計取捨非中性值；姿態角度影響相對溫和，非最大弱點。完整表格見`docs/research_log.md` Problem 38，結果存於`results/robustness_eval.json`（⚠️ 2026-08-26 註：該檔 2026-08-10 16:16 產生、無權重 provenance，正是 Layer1c→1d 換版當天，**標為 UNVERIFIABLE**；引用請改用 `results/robustness_eval_v811d.json`（2026-08-11）或 v8.17 addendum（C1.9.9））

## C1.9 | P1-R9: Self-Blended Images (SBI) pilot - Layer1 (2026-08-19/20)

> Registry entry: `docs/EXPERIMENT_REGISTRY.md` -> **P1-7**.
> Findings: `results/research/p1_r9_sbi_pilot_20260819/P1_R9_FINAL_FINDINGS.md`.
> Status: **SUCCESS** - first arm in the P1-R2->R9 chain above a threshold-only
> frontier. **🚀 2026-08-20 PROMOTED to production as v8.17** - human project
> lead reviewed §2 evidence + the two addendum re-runs below, approved via
> direct instruction (Approval Record filled accordingly, see change proposal).
> `pipeline.py` `LAYER1_WEIGHTS_PATH` now points to
> `shufflenet_v2_layer1_v817sbi.pth`. Old `shufflenet_v2_layer1_v811d.pth`
> retained on disk unmodified for rollback (SHA256 `3c61cf68...` unchanged).
> This is the first production change approved since v8.11's 2026-08-13 freeze.

- [x] C1.9.1 Implement SBI generator on this project's own MediaPipe landmarker
      (`sbi/sbi_generator.py`; seeds, per-pair parameter/mask/hash logging,
      MISSING on landmark failure, blend masks written for a possible Phase 2
      handoff but unused in Phase 1).
- [x] C1.9.2 Round 1 validity check (450 pairs, 3 pools): all four pre-declared
      falsification criteria PASS - landmark failure <=0.66%, 0 blends identical
      to source, median in-mask |diff| 18.4-20.5/255, mask coverage IQR
      0.076-0.115.
- [x] C1.9.3 Round 2: +22,297 SBI pseudo-fakes on Layer1 (Layer2 byte-frozen).
      PARTIAL_SUCCESS - every manipulation metric up at matched operating points
      (FF++ +2.5..+7.0pp at 8/8; unseen AUROC +0.0181 significant; Layer1 Shadow
      routing above the frontier 9/9) but clean OOD real recall fell
      (CelebA 99.73->98.30, Shadow real 77.06->67.03).
- [x] C1.9.4 Round 3: diagnosed the cause (global degradations appeared only on
      the pseudo-fake branch => "degraded means manipulated") and added 22,297
      degradation-matched REAL negatives. **SUCCESS**: CelebA 99.33, Shadow real
      74.91, stress 3.71->2.80%, unseen AUROC 0.8410 (pAUC<=5% 0.0852->0.1630,
      TPR@FPR1% 0.0093->0.0370), True Test paired balanced 81.12->82.13,
      Shadow filter recall 10.04->12.19, FF++ AUROC 0.5275->0.5611. Above the
      threshold-only frontier at 9/9 budgets on BOTH views; both Known Traps
      pass; every Freeze-Gate A metric passes. Only consistent regression:
      True Test filter recall -1.60pp (still above its >=90 gate).
- [x] C1.9.5 CTRL arm (same recipe, same extra epochs, no SBI rows) is flat
      everywhere - the gain is the data, not the fine-tuning.
- [x] C1.9.6 Change proposal written, **Approval Record deliberately blank**:
      `docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md`.
- [x] C1.9.7 **RESOLVED 2026-08-20 by P1-R10 (see C1.10)** — the I/O blocker was
      diagnosed (external machine-level contention, not the generator) and engineered
      around (33 h -> 219 s, byte-identical output). **Answer: SBI does NOT plateau**;
      it keeps helping on every manipulation-side axis and keeps costing clean OOD
      real recall, monotonically. Original text below for traceability.
- [x] C1.9.7-ORIG **(was OPEN / highest-value follow-up)**: does SBI scale past ~22K pairs?
      A pre-declared 2x round (`build_p1_r9_r4_scale.py`, H5) was launched and
      **abandoned for infrastructure reasons only** - generator throughput
      collapsed from ~1,150 img/min to ~22 img/min (machine-level I/O; `ls` and
      `Get-Process` also timed out). No scaling evidence exists in either
      direction. Re-run unchanged when the machine is healthy.
- [x] C1.9.8 ✅ **2026-08-21 DONE (superseded by C1.11.7, see there for the
      corrected 2,644-row count and impact assessment)**: rebuild `splits/v811_layer1_val.txt` without the 1,538
      `FFHQ_ali_process` rows before the next Layer1 training round - that file
      is the val split production's Layer1 was epoch-selected on, and
      `FFHQ_ali_process` IS the Alibaba filter OOD gate (same base FFHQ photos,
      different filter type/strength). Pre-existing, not introduced by P1-R9.
- [x] C1.9.9 **DONE 2026-08-20 (reviewer-requested addendum)**: Robustness Gate
      (Freeze-Gate C: JPEG q70/q50, downscale 4x, blur k5/k9, lighting, 20
      conditions total) run for both candidate and production baseline via
      unmodified `AIGuard/eval_robustness.py`. Same trade-off as §2 (real
      recall up 20/20, fake flat, filter down 14/20), not amplified by any
      perturbation; largest single loss pose-extreme -4.8pp on n=58 (3 images).
      TFLite re-exported via unmodified `export_mobile_tflite.py` +
      `benchmark_mobile_artifacts.py`: combined fp32 20.913 MB (unchanged vs
      production, +4 bytes on Layer1 only), 14.22 ms/img (vs 14.37 production
      reference), G1-G4 all pass, 769/769 TFLite-vs-PyTorch decision match.
      Results appended to change proposal §2.1/§2.2 and
      `results/research/p1_r9_sbi_pilot_20260819/addendum_robustness_tflite/`.
- [x] C1.9.11 **DONE 2026-08-20**: post-promotion independent verification
      (`results/research/p1_r9_sbi_pilot_20260819/post_promotion_verification/`)
      re-ran test plan §6 items 1-3 against the NOW-LIVE `pipeline.py` -
      full-gate/FF++/frontier/trap numbers reproduce the proposal's §2
      **bit-for-bit** (per-image dump byte-identical to the original round's
      dump, not just matching to printed precision). Single + batch smoke test
      pass (exit 0, sane non-collapsed predictions, schema structurally
      unchanged). **Two pre-existing issues found, NOT caused by this
      promotion** (both trace to the uncommitted 2026-08-11 face-gate work,
      predate P1-R9): (a) `pipeline.py`'s `model_version` field is hardcoded
      `"v8.11"` at two call sites - now stale now that Layer1 is v8.17, worth a
      follow-up fix but out of this change's approved scope (§5 only lists
      `LAYER1_WEIGHTS_PATH`); (b) `docs/structured-output.schema.json` still
      declares `2.0.0` while the pipeline emits `2.1.0` and would reject live
      output on 4 counts - unrelated to this promotion, been stale since
      2026-08-11, needs its own fix/decision.
- [ ] C1.9.12 **NEW OPEN, found during C1.9.11**: fix `model_version` hardcode
      in `pipeline.py` (2 call sites) to reflect the actual live Layer1
      version instead of a stale `"v8.11"` literal - low cost, but needs its
      own change-control pass since it's outside this promotion's approved
      §5 file list.
- [ ] C1.9.13 **NEW OPEN, found during C1.9.11**: `docs/structured-output.schema.json`
      is out of date vs. the pipeline's actual `schema_version: "2.1.0"` output
      (4 discrepancies: `additionalProperties` set, region enum missing
      `"face"`, `"smoothing"` vs `"over_smoothing"`, prediction enum missing
      `non_face`) - has been stale since the 2026-08-11 face-gate work,
      independent of P1-R9/v8.17.
      > 🔴 **2026-08-21 升級為正式缺陷記錄（阻擋 Member C）**：見本檔末尾
      > 「🔴 DEFECT｜schema / output contract 不一致」章節，含逐項精確落差、
      > 影響範圍與為何修它需要走 change proposal。
- [ ] C1.9.10 **OPEN (Phase 2 handoff, do not act on in Phase 1)**: every SBI
      pair has a pixel-exact blend mask at
      `sbi_data/p1_r9_sbi_pilot_20260819/*/masks/*_mask.png` - a ready-made
      paired GT manipulated-region source for XAI/localisation work.

## C1.10 | P1-R10: SBI 2x scaling（解決 C1.9.7）+ 輸入解析度實測（2026-08-20）

> 完整報告 `results/research/p1_r10_sbi_scale_and_resolution_20260820/P1_R10_FINAL_FINDINGS.md`；
> 事前假設與判定規則 `PRE_DECLARED_PROTOCOL.md`；決策順序 `ROUND_LOG.md`；
> registry 條目 **P1-8**。`pipeline.py` 與三個 frozen checkpoint 於回合結束
> 重新雜湊**逐位元組相同**（`frozen_hashes_{start,end}.txt`，diff 乾淨）。無 git commit。

### 任務一：SBI scaling —— ✅ 完成，**H5 的「plateau」分支被推翻**，但有實測代價

- [x] C1.10.1 **先診斷、再繞道**：P1-R9 Round 4 的吞吐崩潰（~1,150 → ~22 img/min）
      根因確認為**這台共用機器的外部 I/O 競爭**，不是 generator 的問題。四項決定性測試：
      ① RSS 平坦（436→451 MB / 300 張），排除 leak；② 同 pool 同程式碼今天跑
      **1,592 img/min**，比中止那次全程都快，排除程式碼／pool；③ 把中止那次的
      輸出檔 mtime 還原成時間軸再對回原圖，**快速區 0.123 / 崩潰區 0.132 /
      回升區 0.131 Mpix（16-17 KB）分布完全相同**，排除資料效應；④ 時間軸是
      *階梯式*下跌 + 中途**回到 1,050 img/min 的滿速爆發**再下跌，任何單調的
      程序內成因都做不出這個形狀，加上 P1-R9 當時記錄 `ls`/`tasklist` 也逾時
      （全機停滯）。旁證：該時段無其他專案寫入（全樹 mtime 掃描僅 5 檔）、
      無 Windows Update 安裝、無 Defender 掃描、C: 尚有 96.6 GB。
      工具：`diagnose_p1_r10_sbi_throughput.py`（逐階段計時：imread / MediaPipe /
      numpy core / imwrite / sha256）。**關鍵發現：每張 ~37 ms 裡有 33 ms 是 CPU，
      只有 ~3.4 ms 是磁碟；而其中 7.2 ms（19%）是「為了算 provenance hash 而把
      來源檔和輸出檔各再讀一次整份」的純浪費。**
- [x] C1.10.2 **四項工程對策**（`sbi/sbi_fast.py`）：W1 多程序（1→**1,161**、
      8→**4,456**、14 worker→**5,129** img/min end-to-end，穩態 14,000-33,000）；
      W2 來源只讀一次 bytes（同一個 buffer 做 hash + decode）、輸出只編碼一次
      （同一個 buffer 做 hash + 寫檔），每張 4 次檔案操作降到 2 次；W3 分塊
      + 每塊 fsync checkpoint + 由 log 續跑（卡住只損失一塊，不再整輪重來）；
      W5 吞吐看門狗（低於 `--min-rate` 就指數退避並重跑該塊，並把 stall 記成證據）。
      **正確性關卡（事前宣告為 falsification condition）**：`verify_bit_identity()`
      拿原始序列版 `sbi_generator.generate()` 與平行版同 pool 同 seed 對跑，比對
      jpg bytes / mask bytes / `source_sha256` / `output_sha256` / index 對齊，
      **imdbwiki 與 lfw 皆 PASS，0 個不一致** → 規模化資料與 P1-R9 R4 會產出的
      完全相同，比較才成立。
- [x] C1.10.3 **實際產出**：44,297 SBI + 44,297 degradation-matched real negatives，
      **135 s + 84 s（共 219 秒）**，對照 P1-R9 對同一份工作的「~33 小時」推估。
      8 項 integrity gate 全 0；**98.3%** 的 SBI 底圖同時以 label-0 real 存在於 split。
      Split：`splits/research/p1_r10_sbi_scale_20260820/layer1_sbi_r10_train.txt`
      （300,968 列）。新增第五個底圖家族 `AIGuard/real`（12,000）。
- [x] C1.10.4 **H5 答案：SBI 不會 plateau**（⚠️ 2026-08-26 註：此主張已被 P1-R11／registry P1-9 收窄為「SBI 在 2x–2.92x 之間 plateau」，引用時只准用收窄後版本）。arm `SBIR10`（配方與 P1-R9 逐位元組相同，
      只改 `--train-split`）在 Layer1 primary endpoint 上，**9/9 個 matched budget
      都高於 threshold-only frontier，且 9/9 都優於現役 production**
      （SBIAUG +3.05..+4.48pp → SBIR10 **+3.94..+8.24pp**）；FF++ 8 個 matched
      real-recall 點 **8/8 勝過 SBIAUG、8/8 勝過 v8.11**（+4.3..+10.7pp）；
      **fake+filter 端到端誤判 2.36% → 0.79%，是本專案史上第一次達成 ≤2% 的
      stretch goal**（自 v8.4 開放至今）。這與 P1-5/P1-R7 對 fake-source diversity
      量出的「plateau」是不同性質。
- [x] C1.10.5 **代價也是真的，而且隨規模單調惡化**（trap #2 抓到的）：
      AIGuard-unseen AUROC 0.8411 → **0.8027**（Δ vs v8.11 −0.0122，不顯著），
      pAUC≤5% 0.1630 → **0.0696**，TPR@1% 0.0370 → **0.0139**；CelebA
      99.20 → **96.23**；Shadow real 73.48 → **64.52**。整條規模軸上，
      *偵測面全部變好、乾淨 OOD 真人面全部變差*：CelebA 99.73→99.20→96.23、
      Shadow real 77.06→73.48→64.52、unseen pAUC 0.0852→0.1630→0.0696。
      P1-R9 Round 3 的 degradation-matched negatives 在 1x 壓得住，**2x 且加入
      in-domain 底圖家族後壓不住**。
      ⚠️ 注意：SBIR10 在 tm=0.5 **並非** calibration-matched（dev false-manip
      2.895% vs production 6.369%），所有數字都取 dev 規則選出的 tm=0.355。
- [x] C1.10.6 **事前判定規則不足，據實記錄而非硬套**：`SCALE_HELPS` /
      `SCALE_PLATEAUS` / `SCALE_HURTS` 三選一無法描述本結果（margin 明顯勝出、
      無 gate 破線，但 trap #2 相對 1x arm 退步，而 `SCALE_HELPS` 禁止這點）。
      規則集記為 **incomplete**，結果以第四個明示標籤
      `SCALE_HELPS_ON_MANIPULATION_DETECTION_AND_COSTS_CLEAN_OOD_REAL` 呈現。
- [x] C1.10.7 Change proposal 已寫，**Approval Record 刻意留白**，且**提案人自己
      建議「預設不要 promote」**：`docs/team/change_proposals/20260820_p1_r10_sbi_scale_layer1_sbir10.md`。
      條件式採用情境：只有當部署的成本函數由 fake+filter 安全性主導、且能容忍
      乾淨 OOD 真人照多約 3pp 誤判時，SBIR10 才是較好的 checkpoint。
- [ ] C1.10.8 **OPEN（可選，不建議立即做）**：4x scaling 未測。依觀察到的單調
      方向，預期只會讓 trade 更陡而非收斂；除非先解決「乾淨 OOD 真人退化」的
      機制（例如更強的 degradation-matched / in-the-wild clean-real 配比），
      否則不建議直接加量。

### 任務二：輸入解析度 —— ❌ **RESOLUTION_CLOSED**，附上 P1-R5 當年要求的實測價目表

- [x] C1.10.9 **先把假設磨利再訓練**。用 P1-R5 自己的 landmark 資料、依來源
      **原生解析度**分層重算（DiT/SiT/ddim 256px、sd2.1 512px、pixart 1024px，
      訓練集與兩個 held-out set 皆同一分層），得出事前可算的
      `predeclared_displacement_resolution_table.csv`：eye_enlarging 的位移要到
      **R≈341-460** 才達到 0.5 input px，face_reshaping 在 **R≈85-119**、smoothing
      在 **R≈166-219** 就已經越過——也就是說 **224→448 之間只有 eye_enlarging
      有可能受惠**，而且**對 256px 原生的圖，>224 的輸入純粹是內插、不可能增加
      資訊**。這第三點是本輪的決定性對照組。arms = 224 / 320 / 448。
- [x] C1.10.10 **收斂 confound 事前修正（讀 held-out 之前記錄）**：6 epoch 下
      val meanF1 = 0.9344 / 0.8507 / 0.7660，高解析 arm 根本沒收斂（init 權重是
      224 訓練的、backbone 大部分凍結），直接評估等於製造保證的假陰性。
      主要比較改為**三個 arm 一律 30 epoch 的 matched budget**。
      結果：224 **0.9465** / 320 0.8957 / 448 0.8466 —— **即使 matched 30 epoch，
      高解析 arm 也追不上 224**，這本身就是一個部署相關的發現。
- [x] C1.10.11 **Held-out 一次性（兩個 DF40-cdf set，990 + 994 列，
      `used_in_training==False` 逐列 assert）**。per-type AUROC 的 paired
      bootstrap（10,000 次）ΔAUROC vs R224：**沒有任何一型在任何解析度顯著改善**；
      R448c 反而顯著變差（primary：smoothing −0.236*、whitening −0.092*、
      eye_enlarging −0.099*、face_reshaping −0.110*；secondary：eye −0.087*、
      reshape −0.099*）。
      **決定性分層對照**：所有顯著格子**全部是負的、而且全部落在 256px 原生來源**
      （內插區）；在 512/1024px 原生來源（真的有多餘像素的地方），**幾何型別
      沒有任何一格在任一方向顯著**。→ 提高輸入解析度**沒有**把次像素幾何訊號救回來。
- [x] C1.10.12 **實測部署代價（G1-G4 四關全過，9/9 產出物，ONNX 圖中無 DFT op，
      max|Δlogit| ≤ 1.7e-5）**，用產出 20.91 MB 那份數字的同一條程式路徑重測，
      不是外推：

      | 輸入 | 兩層 fp32 TFLite | 最壞情況 CPU 延遲 | FFT 常數矩陣 |
      |---|---:|---:|---:|
      | **224** | **20.91 MB**（與已公佈數字完全吻合，等於 harness 驗證）| **15.7 ms/張** | 0.80 MB |
      | 320 | 22.51 MB（+7.7%）| 36.9 ms/張（2.35×）| 1.64 MB |
      | 448 | 25.51 MB（+22.0%）| **84.3 ms/張（5.37×）** | 3.21 MB |

      代價結構如事前預測：matmul-DFT 分支的常數矩陣是 O(R²)、matmul 是 O(R³)，
      所以**延遲惡化 5.4 倍而檔案只大 22%**。
- [x] C1.10.13 **結論：P1-R5 標記的「唯一還有 headroom 的槓桿」正式關閉**，
      代價是 **5.37× 延遲換 0 增益**。範圍誠實限定：這關閉的是「本架構 +
      由 224 權重遷移 + 大部分凍結 backbone」這個組合，**不主張**對「原生高解析
      預訓練並從頭訓練」的模型也成立（未測，且以 5.4× 延遲而言對本專案也無部署意義）。


## C1.11 | P1-R11: 對抗式洩漏稽核 + v8.17 上 DF40-cdf + SBI 規模天花板（2026-08-20）

> 執行記錄：`results/research/p1_r11_leakage_scaling_20260820/P1_R11_FINAL_FINDINGS.md`、
> `TASK1_LEAKAGE_AUDIT.md`、`TASK2_V817_DF40CDF.md`、`PRE_DECLARED_PROTOCOL.md`。
> Registry 條目：`docs/EXPERIMENT_REGISTRY.md` **P1-9**，並新增全域 **Known trap #3**。
> 三個凍結 checkpoint 與 `pipeline.py` 於回合結束再次雜湊，**逐位元組不變**。無 git commit。

### 任務一：對抗式洩漏稽核 —— ⚠️ **CLEAN WITH CAVEATS，找到 6 個真實洩漏，但都不影響 v8.17 的升版依據**

- [x] C1.11.1 **本專案史上第一次用「內容金鑰」查重**（解碼後像素 SHA256 + dHash 篩選
      再用 64x64 NCC / 32x32 MAD 判定）。過去每一輪的 integrity gate（v8.16 build、
      P1-R7 的 G7、P1-R9/R10 的 `gate_stems()`）**全部只比對路徑或檔名 stem**，
      對「同一張照片換個檔名存放」結構性失明。
- [x] C1.11.2 **最大發現：`stylegan2_test/fake` 有 63.8%（6,376/10,000）與 Layer1
      訓練資料同源**——`AIGuard/fake` 與 `fake_filter_hard_neg` 都取自同一份
      140k Real-and-Fake-Faces StyleGAN2 語料，多組全解析度像素完全相同（MAD=0.0）。
      **⇒「StyleGAN2 OOD fake detection」自 v8.3 起在 CLAUDE.md、Freeze-Gate A 表
      與各版本結果區都被描述為 OOD 泛化結果，這個說法必須停止使用。**
- [x] C1.11.3 **第二發現：Alibaba gate 有 23.5%（4,980/21,151）與訓練資料同源**——
      `AIGuard/real` 與 `filter_data/*` 內含 FFHQ 照片，正是 `FFHQ_ali_process` 的底圖。
- [x] C1.11.4 **C1.9.8 的既有缺陷比記錄的更大**：`splits/v811_layer1_val.txt` 實際含
      **2,644** 列 `FFHQ_ali_process`（P1-R9 記錄為 1,538，**低估 1.7 倍**），
      且 Alibaba gate 有 69.6% 被 val 近重複覆蓋、8 組像素完全相同。
      **但 A2 假設（train 側也有同樣問題）已被否證：Layer1 train split 內 0 列 FFHQ_ali。**
- [x] C1.11.5 其餘四項：True Test fake 有 11/270（4.1%）與訓練資料近重複（含
      `sd2.1/ff/803/503_651.png` 與 `sd2.1/ff/572/503_651.png` 像素完全相同的
      dataset 內部重複）；CelebA train/test 分割重疊 41/19,962（含 1 組完全相同）；
      `AIGuard/fake` 與 `AIGuard/unseen` 近重複 4/454；LFW 同一拍攝 session 的
      不同幀（stem 不同，故 208 張 stem 封鎖擋不住）。
- [x] C1.11.6 **決定性測試：把污染圖片剔除後重算每個 gate**。全部 Freeze-Gate A
      門檻仍通過，arm 之間排序完全不變，且**v8.17 對 production 的 AUROC 增益
      「報告值 +0.0260 / 去污染值 +0.0263」——去污染後反而略大**。
      在 Alibaba 的污染子集上每個 arm 都比乾淨子集**更差**（-0.24 ~ -0.73pp），
      即污染是輕微不利、從未有利。**⇒ 不觸發 stop-trigger，v8.17 升版依據成立。**
- [x] C1.11.7 ✅ **2026-08-21 完成**：重建 `splits/v811_layer1_val.txt`，移除
      **2,644** 列 `FFHQ_ali_process` → `splits/v811_layer1_val_clean_20260821.txt`
      （12,031 列）。已連續三輪（P1-R9、P1-R10、P1-R11）只做迴避，本輪真正修復。
      **附帶做了任務書要求的影響評估**：用既有 checkpoint（CTRL/SBI/SBIAUG 各自
      best+last，6 個檔案）在乾淨 val 上重新評分，**未發現任何 checkpoint 選擇會
      被翻轉**（各 arm 的 best 仍優於 last，方向與污染 val 一致）。**過程中意外
      發現一個獨立的命名問題**：production 的 `shufflenet_v2_layer1_v817sbi.pth`
      經 sha256 核對，其真實身份是 P1-R9 的 **SBIAUG** arm（sha256 `e3057270...`），
      不是檔名/CLAUDE.md 簡稱暗示的「SBI」arm（`b5f25810...`，從未被用作
      production）。數字本身沒有錯（`P1_R9_FINAL_FINDINGS.md`與變更提案檔名從頭
      就正確記載勝出候選是 SBIAUG），純粹是最上層摘要文件的簡稱造成誤導，**待人
      決定是否更名**。完整證據見
      `results/research/contamination_cleanup_20260821/CLEANUP_AND_RETEST_REPORT.md`。
- [x] C1.11.8 ✅ **2026-08-21 完成（全文件掃描更正）**：修正文件中「StyleGAN2 = OOD」與（較弱的）
      「Alibaba = OOD」說法——`CLAUDE.md`（已於 2026-08-20 先行更正）、Freeze-Gate A 表
      （`TODO.md` + `docs/EXPERIMENT_REGISTRY.md` 兩份）、paper outline / paper draft、
      `docs/Dataset 清單.md`、`docs/dataset.md`、`docs/ACTIVE_ARTIFACTS.md`、
      `docs/PROJECT_CATALOG.md`、`docs/RESEARCH_JOURNEY.md`、`docs/phase1_story.md`、
      `docs/team/TEAM_WORK_ALLOCATION.md`、`docs/team/change_proposals/*`（已核准者一律
      append-only addendum，不改內文）。
      去污染後的 99.07%（StyleGAN2）仍過門檻，要修的是**框架敘述**不是數字——
      **本輪未更動任何數字、任何 pass/fail 判定、任何 checkpoint／split／`pipeline.py`**。
      統一措辭：**「StyleGAN2 fake detection」** 與
      **「Alibaba filter recall（跨濾鏡演算法，非 OOD——與訓練資料有 23.5% 內容重疊）」**。
      完整逐檔前後對照見 `results/research/doc_correction_sweep_20260821/CORRECTION_LOG.md`。
- [ ] C1.11.9 **NEW OPEN**：把內容金鑰查重加進所有 split builder 的 integrity gate
      （見 Known trap #3）。本輪 6 個洩漏中有 5 個對路徑/stem 完全隱形。

### 任務二：v8.17 首次上 DF40-cdf —— ✅ **SAME_CURVE（事前宣告的 null）**

- [x] C1.11.10 兩個 held-out set 各只開一次，門檻先寫入磁碟、逐列 assert
      `used_in_training == False`。dAUROC v8.17 - PROD：主集 **-0.0034
      CI[-0.0083,+0.0014]**、次集 **-0.0024 CI[-0.0069,+0.0021]**，皆不顯著。
      Trap #1（6 budgets × 2 sets）優 1/12、劣 4/12，|delta| 全部 ≤ 0.63pp；Trap #2 混合且極小。
- [x] C1.11.11 **結構性原因（事前宣告，非事後補解釋）**：`filter_auroc_layer2only`
      兩個 arm 到小數第四位完全相同（0.4972 / 0.4715），因為 Layer2 逐位元組凍結；
      而 Layer1 在這兩個全 fake 的資料集上 routing 已達 99.5-100%，**SBI 沒有可施力空間**。
- [x] C1.11.12 **重要範圍界線（registry 先前未載明）**：`joint recognition` 對
      production 架構**根本沒有定義**——兩個 arm 都讀 0.00%，因為階層式 argmax
      只能輸出 fake 或 filter、不可能同時。Cell C 2.02% / v8.16 4.53% / T600-T900 ~24%
      全部來自 **dual-head** Layer2。**這兩族數字不可當成同一條序列引用。**

### 任務三：SBI 規模推到 2.92x —— ❌ **CEILING_REACHED，天花板落在 2x 與 2.92x 之間**

- [x] C1.11.13 **事前宣告的 4x 在物理上不可達**：扣掉 gate 排除後全專案真實人臉庫
      共 65,145 張（imdbwiki 12,200 + celeba_train 18,315 + aiguard_real 25,623 +
      lfw 8,710 + vggface2 297），而 `sbi_fast.plan_sbi()` 不放回抽樣、一張底圖一張
      pseudo-fake。實得 **65,099 = 2.919x**。
      **⇒ `DIVERSITY_LEVER_EXHAUSTED`：這個槓桿的結構上限就是 2.92x，與任何指標無關。**
- [x] C1.11.14 bit-identity gate 重跑 **PASS**（2 個 pool，0 不一致）；訓練配方、seed、
      init、val split、門檻規則與 `train_p1_r9_layer1.py` 逐位元組相同，只有資料量變動。
      harness 先重現 SBIR10 已發表數字（filter 93.98 / CelebA 96.23 / stress 0.79 /
      AUROC 0.8031）才讀任何新數字。
- [x] C1.11.15 **SBIR11 是 P1-R2→R11 全鏈第一個直接違反 Freeze-Gate A 門檻的 arm，
      而且違反兩項**：True Test paired balanced **78.51（<80）**、
      AIGuard-unseen AUROC **0.7828（<0.80）**。
- [x] C1.11.16 **Trap #1（matched operating point）**：在 matched Shadow real recall 下，
      SBIR11 的 fake+filter stress error **6/6 budget 全部輸給 SBIR10**、5/6 輸給 v8.17、
      2/6 輸給 production。**安全指標不只是停止進步，是反轉**（0.79 → 1.14）。
- [x] C1.11.17 **Trap #2（low-FPR）**：AIGuard-unseen dAUROC vs production
      **-0.0321 且顯著**（2x 時 -0.0118 不顯著）。pAUC5 0.0852 → 0.1630 → 0.0696 → 0.0607。
- [x] C1.11.18 **趨勢判定（4 個點，末段以 0.545 doubling 正規化）**：
      manipulation 側 **飽和且兩項變號**——stress error +1.573 → **-0.641/doubling**、
      FF++ pAUC5 +0.0078 → **-0.0041**；FF++ AUROC 仍升但每 doubling 衰減 29%。
      clean 側成本**不減反加速**——unseen AUROC 以**固定速率**惡化（ratio 0.98），
      True Test paired balanced 每 doubling 惡化速度**變成前一段的 14.7 倍**。
      成本/收益比在所有 stress-error 配對上**變成負值**。
      **⇒ 不是 LINEAR（有變號）、也不只是 SATURATING（收益反轉而成本照走），
      是 `DIVERGING` 的最強型態：已經不再是 trade-off。**
- [x] C1.11.19 **回溯修正 P1-8 的標題主張**：P1-8 宣稱「SBI 不會 plateau」並以此
      與 P1-5/P1-R7 的 fake-source diversity 對比。加入第三個點後必須收窄為
      **「SBI 會 plateau，只是位置更靠後（2x 與 2.92x 之間）」**——P1-8 畫出的
      質性區別比當時陳述的弱。
- [x] C1.11.20 **建議：不推廣 SBIR11，且不再進行任何 SBI scaling 回合**。
      與 P1-R10 留下的開放問題不同，這題現在**兩個方向都已關閉**：更多資料量取不到
      （結構天花板），就算取得到也有害（指標 + 可行性天花板）。
      **v8.17（1x）仍是這條曲線上正確的作業點**——它是唯一同時改善 clean 側
      （unseen AUROC +0.0262 顯著、trap #2 乾淨）與 manipulation 側的 SBI arm。

## D｜Phase 1 統一問題狀態盤點（2026-08-20，對照使用者文獻回顧更新，v8.17 上線後）

> 使用者提供一份文獻回顧，主張 Phase 1 是兩層性質不同的問題疊在一起：①標準
> cross-dataset domain gap（文獻已大量驗證，部分有緩解方法）②fake+filter 組合
> 泛化（本專案自訂的更難任務，無現成文獻解法）。內部引用的所有專案自身數字
> （P1-R1 filter head 瓶頸、filter-type AUROC、Alibaba 27.5%、FF++ 24.7-44.0%、
> StyleGAN2 attribution 0.42）本 session 稍早已逐一查證，全部準確，不是誤植。
> ⚠️ 2026-08-26 註：「準確」指與來源 TSV 相符，**不代表可引用**——FF++ 24.7-44.0% 的 checkpoint
> 不明（V817_SCORECARD §264 已指出），勿引，v8.17 per-method 見 `contamination_cleanup_20260821` Task4
> 表（DF 65.3／F2F 36.0／FS 49.3／NT 52.7）；Alibaba 27.5% 已被 clean-split 量測（v3/v5/v6，
> `p2_artifact_crossalgo/completefix_20260821`）取代；StyleGAN2 0.42 的母體抽自 63.8% 污染集且用 v811d，未重測。
> 外部文獻引用（CrossDF、FreqNet、FreqDebias、Deepfake-Eval-2024、50-method
> 跨10資料集研究）未經本 session 獨立複查，視為使用者自行查證後提供的背景
> context，不重複驗證，但也不因此自動當作本專案已驗證的事實對待。

**A. 核心 gate 現況（v8.17 上線後更新，取代舊表）**：

| 測試 | v8.11（歷史）| **v8.17（現役，2026-08-20起）| Gate | 狀態 |
|---|---:|---:|---|---|
| True Test fake recall | 99.63% | 99.63% | ≥95% | ✅ |
| True Test filter recall | 93.57% | 91.97% | ≥90% | ✅ 唯一退步項 |
| True Test paired balanced | 81.12% | 82.13% | ≥80% | ✅ 進步 |
| AIGuard-unseen AUROC | 0.8150 | 0.8410 | ≥0.80 | ✅ 進步 |
| CelebA real recall | 99.73% | 99.33% | ≥95% | ✅ |
| StyleGAN2 fake recall | 99.60% | 99.57% | ≥95% | ✅ |
| Alibaba filter recall | 98.17% | 97.71% | ≥95% | ✅ |
| **fake+filter 端到端誤判** | 3.71% | **2.80%** | ≤5%（stretch ≤2%）| ✅ 改善，stretch 未達 |
| Shadow real recall | 77.06% | 74.91% | — | 兩者皆低於 stretch |
| Shadow filter recall | 10.04% | 12.19% | — | 進步但仍極低 |

**B. 使用者問題表逐項核對 + owner 標註**（Phase 1=Member A 範疇，Phase 2=Member B
範疇，本專案標準分工，見 `docs/team/TEAM_WORK_ALLOCATION.md`——不可越界處理）：

| 問題 | 使用者引用數字 | 核對結果 | Owner | 現況 |
|---|---|---|---|---|
| Fake+filter 最終誤判 | 3.71% | ✅ 準確（v8.11 時期），**v8.17 已改善至 2.80%，但過時** | **Phase 1** | 部分改善，stretch(≤2%)未達 |
| Shadow cross-base domain gap | 43.5% | ✅ 準確（Shadow paired balanced，v8.11/Cell C 等值）| **Phase 1** | v8.17 因 Layer2 未動，端到端上限仍受限，未解 |
| Cross-source fake+filter 泛化 | v8.16 校準後 4.53% | ✅ 準確 | **Phase 1** | P1-R3~R8 已窮盡 3 條方法路線，未解 |
| Filter-type 不均衡 | smoothing 0.905 vs 其他 0.586-0.603 | ✅ 準確（P1-R5）| **Phase 1** | 根因已查明(SNR)，2 種介入(loss/reference-region)已測試失敗 |
| External artifact type 分類 | 27.5% | ✅ 準確（`external_alibaba_artifact_validation_20260814`）| **⚠️ Phase 2（B）** | 不屬 Member A 範疇，不可接管 |
| FF++ 傳統手法 fake recall | 24.7-44.0% | ✅ 準確（本 session 已重新算過 TSV 逐項吻合）⚠️ **2026-08-26：checkpoint 不明，勿引**；v8.17 數字見 `contamination_cleanup_20260821/CLEANUP_AND_RETEST_REPORT.md` Task4 | 中性資料，非任一方獨有任務 | 現況不變 |
| Attribution 穩定性（StyleGAN2 0.42）| ±8px translation | ✅ 準確（`fake_xai_level12_v811d_20260814`）| **⚠️ Phase 2（B）** | 不屬 Member A 範疇，不可接管 |

**C. 補上使用者表格沒列出、但屬 Phase 1／Member A 範疇的既有未解項**：
- ~~eye_enlarging/face_reshaping ... 提高輸入解析度 ... 至今沒有人真的跑過~~
  **❌ 2026-08-20 P1-R10 已實測並關閉（C1.10.9-C1.10.13）**：224/320/448 三個
  收斂對齊（30 epoch matched）的 arm，兩個 DF40-cdf held-out set、paired
  bootstrap 10,000 次——**沒有任何型別在任何解析度顯著改善**，顯著的格子全是
  負的、且全部落在「>224 純屬內插」的 256px 原生來源；在真的有多餘像素的
  512/1024px 來源上幾何型別完全不顯著。實測代價：**20.91→25.51 MB、
  15.7→84.3 ms/張（5.37×）**。P1-R5 要求的「實測權衡數字」已補上，答案是不划算。
- ~~P1-R9 的 2x scaling 嘗試因機器 I/O 問題中止（C1.9.7）~~ **✅ 2026-08-20 P1-R10
  已解決並結案（C1.10.1-C1.10.7）**：根因是這台共用機器的外部 I/O 競爭（四項
  決定性測試），不是 generator；改寫成平行／低 I/O／可續跑／有看門狗的產生器後
  33 小時→**219 秒**，且以 bit-identity gate 證明輸出與原版逐位元組相同。
  **科學結論：SBI 不會 plateau**（⚠️ 2026-08-26 註：已被 P1-R11 收窄為「plateau 在 2x–2.92x」，見 C1.11.19）——2x 在 9/9 budget 上更高於 threshold-only
  frontier、FF++ 8/8 勝出、**首次達成 ≤2% fake+filter stretch goal（0.79%）**，
  但代價是乾淨 OOD 真人面隨規模單調退化（CelebA 96.23、Shadow real 64.52、
  unseen pAUC≤5% 減半）。候選 `SBIR10` **提案但建議不要 promote**，Approval Record 留白。
- `splits/v811_layer1_val.txt` 混入 Alibaba 同源圖片（C1.9.8）。
  **⚠️ 2026-08-20 P1-R11 獨立重算：實際是 2,644 列，不是 1,538（低估 1.7 倍），
  且 Alibaba gate 有 69.6% 被 val 近重複覆蓋、8 組像素完全相同**（見 C1.11.4/C1.11.7）。
  下一輪 Layer1 訓練前必須先重建。

**D. 下一輪任務：P1-R10** — ✅ **2026-08-20 完成，兩項任務皆結案**（執行記錄見
上方 C1.10；registry 條目 P1-8）。①②皆已完成並得出結論；③ 未新增第三方向，
因為①②各自產出了明確的後續優先序（見下方 E）。

**E. P1-R11 之後的 Phase 1 優先序（2026-08-20 再更新，取代原 P1-R10 版）**
1. **最高優先，且是資料正確性而非研究**：修 P1-R11 找到的 6 個內容洩漏中
   可行動的部分——① 重建 `splits/v811_layer1_val.txt`（移除 2,644 列 FFHQ_ali，
   C1.11.7，已連續三輪迴避未修）；② 修正文件中「StyleGAN2 = OOD」「Alibaba = OOD」
   的框架敘述（C1.11.8，數字仍過門檻、要修的是敘述）；③ 把內容金鑰查重加進所有
   split builder（C1.11.9，Known trap #3）。
2. **SBI 規模化的代價機制**——若能找到讓 clean-real 不退化的配方（更強的
   degradation-matched 比例、in-the-wild clean-real 補量、或對 SBI rows 做
   confidence-aware 加權），SBIR10 的 0.79% stretch goal 就有機會無代價拿到。
   ⚠️ 但 P1-R11 已證明**單純加量這條路本身已死**（見第 4 點），所以這裡的變數
   只能是「配方」，不能再是「規模」。
3. Layer2 仍是 Shadow 端到端的硬上限（~57.9%）。P1-R9/P1-R10/P1-R11 三輪都證明
   Layer1 側的改善無法在端到端表現出來；要動 Shadow 就必須動 Layer2。
   P1-R11 另外確認 DF40-cdf 那條軸線也完全是 Layer2 的問題（C1.11.11/C1.11.12）。
4. ❌ 已關閉、不要再排：loss-side 工程（P1-3/P1-R5）、reference-region
   normalisation（P1-R6）、fake-source diversity 加量（P1-5/P1-R7）、
   輸入解析度（P1-R10）、**SBI 資料量 scaling（P1-R11 本輪新增關閉——
   天花板在 2x 與 2.92x 之間，且 2.92x 已是整個相片庫的結構上限）**。

## E｜P1-R12（2026-08-20）：架構層介入試點 — 弱型別缺口是「表徵幾何」問題，不是架構問題

> 專案負責人本輪**解除**了「不得改動整體架構」的限制（僅限
> whitening/eye_enlarging/face_reshaping 弱型別缺口），因為四條留在現有架構內
> 的方法族（loss 重加權、reference-region 正規化、fake-source 多樣性加量、
> 輸入解析度）全部失敗。本輪據此提出並試點了一個真正的架構層改動。
> 完整記錄：`results/research/p1_r12_selfcal_probe_20260820/P1_R12_FINAL_FINDINGS.md`，
> registry 條目 **P1-10**。**結論：`NEGATIVE_BUT_INFORMATIVE`，但這是本鏈最強的
> 機制性結果。**

- [x] **E1 文獻導向設計（Phase 1）**：三個候選方向寫入設計文件後才動工
      （`PHASE1_DESIGN_DOC.md`）。選中 **A｜Self-Calibration Probe (SCP)**：把
      同一張照片跑兩次（原圖 + 用已知固定劑量濾鏡 `T_k` 再處理過的版本），
      共用同一個 trunk，讓學習到的 head 看 `[h(x) ; h(x) − h(T_k(x))]`。
      理論根據是**隱寫分析的 calibration**（Kodovský & Fridrich 2009）——那個
      領域的問題陳述跟本專案一模一樣（訊號極弱、影像間變異極大、偵測時拿不到
      乾淨參照），以及取證領域的 **near-idempotence**。B（RECCE 式重建殘差）
      列為次選未試；C（PatchCore 式 memory bank）**以機制理由直接否決**——它的
      參照是「別人的臉」，根本無法抵銷單張照片自身的 nuisance。
- [x] **E2 Stage 0（post-hoc、零重訓）：前提被證實，而且贏很大**。同一張照片的
      再處理版本帶有 **65.9%** 的 clean-fake logit between-photo 變異
      （corr=+0.795）——對照 P1-R6 的背景參照是 **0.0%**（corr=−0.0127）。
      三個預先宣告的 gate 全過。**P1-R6 §4 說的「參照要來自臉部區域而不是場景」
      作為前提是對的。**
- [x] **E3 Stage 0 同時否決了線性形式**：所有 post-hoc 校正 arm 都比原始分數
      **更差**（in-scope 0.5903→0.5298；smoothing 0.8045→0.6591），純差值 arm
      掉到接近亂猜（0.466–0.512）。
- [x] **E4 Stage 1（學習式雙視角 head，對照 byte-identical λ=0 control）**：
      in-scope AUROC 0.5898→0.5924/0.5938，**沒有任何一個 in-scope 差異顯著**。
      通過 **Known Trap #1**（matched false-filter，0/15 顯著變差——本鏈歷來
      matched operating point 表現最好的候選），但**沒有通過 Known Trap #2**
      （TPR@FPR=1% 在 4 個型別中有 3 個變差）。
- [x] **E5 held-out 依規則「刻意不開」**：預先宣告的規則要求同時通過 selection
      rule 與兩個 trap 才能開一次性 DF40-cdf；trap #2 沒過，因此保留該
      eval-only 資源給下一輪真的有訊號的候選。本輪沒有任何腳本讀取
      `splits/v815_replication_set.tsv` 或 P1-R3.4 dose-aligned manifest。
- [x] **E6 ★ 本輪真正的產出：失敗原因被量出來了，不是推論出來的**
      （`selfcal/stage2_why.py`）。在 512 維 trunk 特徵空間裡量 u=濾鏡效果方向、
      v=probe 效果方向、n=clean-fake 特徵的 PC1（nuisance 方向）：

      | 型別 | cos(u, n) | best cos(v, u) | in-domain AUROC |
      |---|---:|---:|---:|
      | smoothing | **−0.475** | +0.998 | **0.804** |
      | face_reshaping | −0.611 | +0.999 | 0.594 |
      | eye_enlarging | −0.806 | +0.999 | 0.587 |
      | whitening | **−0.979** | +0.937 | **0.580** |

      **|cos(u, n)| 完全正確地排出了各型別的表現順序**，而且每個 probe 的方向
      跟每個濾鏡的方向都幾乎平行（+0.65 ~ +0.999）。意思是：**在這個表徵裡，
      「這張照片被修圖了」跟「這是另一張不同的照片」根本就是同一個方向。**
      所以任何參照式架構在扣掉 nuisance 的同時，必然等比例扣掉訊號——這一個
      幾何事實同時解釋了 P1-R5 的 K2（變異數懲罰把訊號一起殺掉）、P1-R5 的
      78–84% paired win rate 卻換不到 population AUROC（配對把照片固定住，是
      唯一能只去 nuisance 不去訊號的構造，而推論時定義上拿不到）、Stage 0 的
      校正崩潰，以及本輪 head 只肯用 2.3% 權重在 delta 上。
- [x] **E7 實測部署成本**（`mobile_cost.json`）：**+512 參數 = +2.0 KB**
      （trunk 共用）、Layer2 延遲 **2.0×**（14.97→29.94 ms，對照 P1-R10 解析度
      的 5.37×）、`T_white` 濾鏡運算 +13.7 ms、`T_smooth` +615 ms（全幀 bilateral，
      **不可部署**）、`T_neutral` +0.6 ms 且**不需要 landmark**但也是 Stage 0
      **最弱**的 probe。**可匯出、無新 op type。** 這是本專案至今成本最低的架構
      層改動——問題純粹是它買不到東西。
- [x] **E8 生產環境零影響**：`pipeline.py` 與三個凍結 checkpoint 於輪次結束重新
      雜湊，`frozen_hashes_start.txt` == `frozen_hashes_end.txt`（驗證 IDENTICAL）。
      沒有修改任何既有 `splits/*`、`results/*`、`checkpoints/*`。沒有 git commit。

### E9｜下一輪建議（本輪交付的可證偽假說）

- [ ] **不要再排架構輪**。已關閉的方法族現在是五條：loss-side（P1-R5）、
      background reference（P1-R6）、fake-source diversity（P1-R7）、
      input resolution（P1-R10）、**reference-by-re-manipulation（P1-R12，本輪新增）**。
      前四條各自失敗；本輪額外給出**五條共同的失敗原因**。
- [ ] **下一輪應該是「表徵學習」輪，不是架構輪**：目標直接打 |cos(u, n)|，
      也就是讓「濾鏡方向」跟「底圖照片方向」在特徵空間裡不共線。具體候選：
      把 base photo / identity 當成明確的 nuisance factor 做 quotient
      （以 base photo 為不變群的 supervised contrastive），或 P1-R3.4 當初擱置、
      至今沒有任何一輪真的跑過的 disentanglement / GRL 家族。
- [ ] **可用的預先篩選工具（本輪副產品）**：`selfcal/stage2_why.py` 對單一
      checkpoint 幾分鐘就能算出 |cos(u, n)|。~~**可證偽預測：任何能降低
      |cos(u, n)| 的候選都應該提升該型別 AUROC，且提升幅度應與降幅相關。**
      這讓下一輪可以在**訓練前**篩掉沒希望的候選，而不是訓練完再驗屍。~~
      ⚠️ **2026-08-26 註：此篩檢已被 P1-R13 證偽（Known Trap #4，見下方 F2 段落）——
      |cos(u,n)| 與 per-type AUROC 無預測關係，不得再作為候選篩選工具推薦。**
- [ ] 候選 B（RECCE 式重建殘差）**只有在**先用上述工具確認「重建殘差方向與
      nuisance 方向不共線」時才值得跑；共線性論證預測它會以同樣方式失敗。

---


## G｜P1-R13（2026-08-20）：表徵學習 = 第六個關閉的方法族；真正的槓桿是 **read-out**，而且 P1-R12 的篩檢被證偽

完整記錄：`results/research/p1_r13_repgeom_20260820/P1_R13_FINAL_FINDINGS.md`；
registry 條目 **P1-11**；新增 **Known Trap #4**。程式在新模組 `repgeom/`。

### G1｜一句話結論
**弱型別（whitening / eye_enlarging / face_reshaping）辨識力偏弱不是「表徵學不到」，是「head 讀錯方向」。**
凍結的 512 維 trunk 裡，用 train 擬合、在 **val 上 out-of-sample** 評估的 Fisher 方向，
每一個型別都贏過模型自己的 filter logit **+0.10 ~ +0.21 AUROC**：

| 型別 | 模型自己的 logit | Fisher 方向（OOS） | 落差 |
|---|---:|---:|---:|
| smoothing | 0.8045 | **0.9496** | +0.1451 |
| whitening | 0.5714 | **0.7820** | **+0.2106** |
| eye_enlarging | 0.5970 | **0.6975** | +0.1005 |
| face_reshaping | 0.6024 | **0.7052** | +0.1028 |

train/val 已驗證 base photo、pair_id、輸出 sha256 三項重疊皆為 **0**。

### G2｜事前篩檢真的省下成本（這是 P1-R12 交付流程的正面驗證）
三個有文獻依據的表徵學習候選 —— R1 `ortho`（Domain Separation Networks 的
soft subspace orthogonality）、R2 `supcon`（SupCon / Fisher-ratio maximization）、
R3 `grl`（DANN）—— **全部在花任何訓練成本之前就被篩掉**，理由都是量測出來的而非猜的。
**代價：約 20 分鐘 GPU，取代三次完整訓練。**

### G3｜唯一通過篩檢的訓練候選也失敗了
`B2 fisher`（scale-invariant Fisher-ratio aux loss，刻意不同於 P1-R5 的 K2）：
batch 層級的 d' 從 0.33 拉到 **11.15（33 倍）**，population d' 只動 13~18%，
辨識力**完全沒動**（whitening −0.028、eye −0.032、reshaping +0.001，全部不顯著），
**20 個 matched false-filter budget 輸 17 個**，pAUC 4 個型別輸 3 個。

### G4｜為什麼「改善弱型別就一定傷到 smoothing」——現在有幾何解釋了
四個型別的 Fisher 方向在 Σ-metric 下**幾乎互相正交**
（smoothing·whitening = **0.024**，whitening·reshaping = 0.044）。
**一條純量根本不可能同時服務 smoothing 和弱型別。**
這回頭解釋了 P1-R5 的 K1（smoothing −0.041）、P1-R6 的 M2（−0.074）、
P1-R12 的 T_smooth（−0.015）為什麼都出現同一個模式。**解法是多條 read-out 方向，不是更好的單一條。**

另一個值得記住的量測：**目前部署的 filter head 方向，統計上跟「未白化的 mean-difference 方向」
無法區分**（差距 +0.0025 / +0.0022 / +0.0015 / −0.0002），而且在弱型別上**只略高於自己 trunk 的
隨機投影**（whitening 0.5714 vs 200 次隨機投影的中位數 0.5675）。Σ⁻¹ 白化才是整個槓桿。

### G5｜新開的方向：read-out 幾何（PARTIAL，尚未可升版）
`B1b_multidir_max4`（4 條標準化 Fisher 方向取 max，**推論時不需要知道濾鏡型別**，
+1,536 參數 ≈ +6 KB，無新 op type）：
- **Known Trap #1／threshold-only frontier：20/20 格全贏、0 格輸** ——
  whitening 在 5% false-filter budget 下偵測率 **14.07% → 48.89%**，10% budget 下 19.26% → 62.22%。
  對照 P1-R5 的 K1（0/6）跟 P1-R6 的 M2（0/12），**這是整條研究鏈第一個真正的 matched-operating-point 勝利**。
- real+filter guard 也變好（97.90% vs 97.47% @0.5%）。
- **Known Trap #2：沒過**。pAUC(FPR≤20%) 四個型別全改善，但 TPR@FPR=1% 在 whitening
  掉到 **0.0000（5/135 → 0/135）**。事前已宣告：135 張負樣本下 FPR=1% 由單張圖決定，
  但 5→0 已在可解析邊緣，**照實記為失敗，不打模糊仗**。
- **⛔ 阻擋升版的 guard 失效（本輪最可行動的發現）**：同一個 read-out 換到**重訓過的 trunk**
  上，20/20 matched budget 照樣全贏，但 **real+filter recall 崩到 3.25%**（logit 是 99.3%）。
  原因查清楚了：Fisher 方向只用 composite pairs + clean_fake 擬合，
  `real_filter`（train 有 15,533 列，是 composite 的 **5.08 倍**）根本不在擬合裡，沒有任何東西約束它落在哪。
  在凍結 trunk 上安全是**巧合，不是結構保證**。

### G6｜下一輪的第一件事（可證偽、成本低）
1. 把 multi-direction read-out 改成**把 `real_filter` 放進正樣本一起擬合**（或加第五條方向），
   在**重訓過的 trunk** 上重跑 real+filter guard。
2. guard 過了以後，才值得花掉那份 one-shot DF40-cdf held-out 去測「擬合出來的方向能不能跨來源轉移」。
3. **本輪刻意沒有開 held-out**（事前宣告、不論結果都綁定），理由是方向擬合在 in-domain 統計上，
   先開會把「槓桿是真的」跟「這條方向能轉移」兩件事混在一起。

### G7｜篩檢方法論的更新（請未來每一輪照這條走）
- ❌ **不要再用 |cos(u, n)| 當篩檢**（Known Trap #4）。
- ✅ **改用：凍結特徵上的 out-of-sample Fisher/LDA AUROC vs 模型實際達到的 AUROC**。
  落差大 → 是 read-out 問題，不要動表徵；落差小 → 表徵才是瓶頸。
  成本是一次 embedding pass，本輪就是靠它在 20 分鐘內把整輪方向轉正。

### G8｜合規
`pipeline.py` 與三個凍結 production checkpoint 於輪次開始／結束重新雜湊，**逐位元組相同**
（`frozen_hashes_start.txt` == `frozen_hashes_end.txt`）。沒有動任何既有 `splits/`、
`results/`、`checkpoints/` 內容。沒有 git commit。三個新 checkpoint 全部 research-tier，**未提名升版**。


## F｜主控現況總表（2026-08-20 統一盤點，取代舊版 D 節，之後每輪結束請在這裡同步）

> 這是全專案唯一的「現在到底做完了什麼、還缺什麼」總表。細節仍在各自章節，這裡只列
> 狀態 + 一行摘要 + 指到細節章節/檔案的指標，不重複貼數字。

### F1｜Production（已上線，可信）

- [x] **v8.17（`shufflenet_v2_layer1_v817sbi.pth` + `shufflenet_v2_layer2_v811.pth`）已正式上線**，
  是 v8.11 於 2026-08-13 凍結後第一個核准並套用的 production 變更（P1-7）。全部
  Freeze-Gate A 通過；核准後獨立重跑驗證數字逐位元組重現（不只印出精度吻合）。
- [x] Robustness Gate（20 種擾動）與 mobile TFLite（20.913MB／14.22ms）皆已針對 v8.17
  補測，無退步（C1.9.9）。
- [x] v8.17 訓練資料 leakage 稽核（P1-R11，內容比對，非僅路徑/檔名）：發現 6 個真實
  洩漏，皆為繼承自舊 base split、非 SBI 引入；去污染重算後所有 gate 仍過、排名不變 →
  **不構成 stop-trigger，promotion 依據成立**。
- [x] StyleGAN2／Alibaba「OOD」用詞已更正（`CLAUDE.md` 2026-08-20，C1.11.8）——數字本身
  不用改，只是不能再稱 OOD。

### F2｜已關閉的研究方向（有明確結論，不要重複嘗試）

| 方向 | 輪次 | 結論 |
|---|---|---|
| Scale-normalized filter generator | P1-R3.0~R3.4 | 生成器修好了，但訓練出的候選未贏過 v8.16；generator dose confound 已排除 |
| Loss-side 介入（reweighting/margin/variance） | P1-R5 | 全部失敗，根因是 SNR 問題不是 loss 設計問題 |
| 同圖背景當參考基準 | P1-R6 | 背景幾何上乾淨但統計上空白，機制性失敗，關閉整個方法族 |
| Fake-source diversity scaling（1x→3x） | P1-R7 | 只對 smoothing 有效，邊際效益遞減，不建議繼續加大 |
| Shadow vs fake+filter 訓練端修法 | P1-R8 | 六種介入全部只是換 threshold 的假象；問題是 operating point 不是訓練問題 |
| 輸入解析度（224→320→448px）| P1-R10 | 無顯著改善，448px 顯著更差，且要付 5.37x 延遲代價 |
| SBI 規模化上限 | P1-R11 | 上限落在 2~2.92 倍之間，第三輪（SBIR11）直接沒過硬性 gate，**確認關閉** |
| 架構層級參照式方法（self-calibration probe）| P1-R12 | 無顯著改善；找到統一根因：濾鏡訊號方向與雜訊方向在表徵空間裡幾乎平行，扣雜訊必連帶扣訊號 |
| **表徵學習介入（orthogonality / SupCon / GRL / Fisher-ratio loss）** | **P1-R13** | **三個候選在事前篩檢就被刷掉（沒花訓練成本），唯一通過篩檢的 Fisher-ratio aux loss 把自己的目標優化了 33 倍卻換不到任何辨識力，20 個 matched budget 輸 17 個。第六個關閉的方法族** |

**whitening/eye_enlarging/face_reshaping 三型別跨來源辨識力偏弱** = 以上 8 條路線的共同受害者。

> ✅ **2026-08-20 P1-R14 新增一條「沒關閉、而且是打開的」方向，請不要把它併進上表**：
> 上表全部 8 條都是 **Layer1 或未上線的 dual-head Layer2** 的介入。
> **production 的 2-class Layer2 從 P1-R7 到 P1-R11 一路被 byte-frozen，從來沒被訓練過。**
> P1-R14 訓練了它，並且是第一支贏過 threshold-only frontier 的 Layer2 arm。
> P1-R8「所有訓練端介入都只是沿著同一條曲線移動」這個推廣，**在 Layer2 上不成立**。

> ⚠️ **2026-08-20 起，`splits/v811_layer2_val.txt` 也要列為已知資料缺陷**（P1-R14 附帶發現）：
> 它已飽和到 macro-F1 0.998 / epoch 1，三支訓練資料不同的 arm 選出的 epoch 完全一樣，
> 等於 Layer2 的 epoch 選擇機制是空轉的。這是 `v811_layer1_val.txt`／`FFHQ_ali_process`
> 那個從 P1-R9 拖到現在還沒修的缺陷的 Layer2 版本。

> ⚠️ **2026-08-20 P1-R13 推翻了 P1-R12 留下的診斷框架，這段以前的敘述已不成立**：
> P1-R12 說「訊號方向與雜訊方向幾乎平行」，並交付一個可證偽的事前篩檢
> 「降低 |cos(u,n)| 就會改善 per-type AUROC」。P1-R13 用兩種互相獨立的方式證明**這個篩檢是錯的**：
> (a) 用投影法在閉式解裡把 |cos| 從 ~0.9 壓到 ~0.05，AUROC 只動 ≤ +0.02 且方向不一致；
> (b) **完全沒有任何介入**的普通續訓（λ=0 control）把 smoothing 的 |cos| 降了 10 倍、
> face_reshaping 降了 4.4 倍，結果兩者 AUROC 都**變差**；反而 whitening 的 |cos| 升高、AUROC 變好。
> 篩檢在 4 個型別裡只猜對 1 個。原始證據只有 n=4 的 rank correlation（ρ=−1.0，雙尾 p≈0.083，不顯著），
> 是**組間相關**而非**組內因果槓桿**。已寫成 registry 的 Known Trap #4。

### F3｜目前進行中（背景執行，尚無結果）

- [x] **P1-R14（2026-08-20 完成）｜Shadow filter recall 的真正瓶頸是 Layer2 的「語料庫捷徑」**。
  完整記錄：`results/research/p1_r14_layer2_corpus_shortcut_20260821/P1_R14_FINAL_FINDINGS.md`、
  registry 條目 **P1-12**。判定 **`PARTIAL`，這條軸線是「開著」的，不是關閉的**。
  - **診斷（最重要的產出）**：production 的 2-class Layer2 **根本不會偵測濾鏡**。
    它分辨的是「這張照片來自哪個攝影語料庫」：語料庫之間 AUROC **0.989–0.9995**，
    但在每個語料庫**內部**「有濾鏡 vs 沒濾鏡」只有 **0.476 / 0.550 / 0.581**（等於亂猜）。
    它會把**完全沒動過**的 LFW 真實照片 100% 判成 "filter"（p_filter≈0.921），
    把**完全沒動過**的 VGGFace2 照片判成 fake 側（p_filter≈0.089）。
    成因：Layer2 的 filter class 100% 是 LFW/FFHQ，fake class 100% 是 AIGuard 影格 + DF40，
    語料庫與類別完全相關 → 捷徑存在且 in-domain 夠用（本輪三支 arm 的 in-domain
    val macro-F1 全部 0.998，就是捷徑飽和的樣子）。
  - **可用空間探針（P1-R13 建議的篩檢法）**：用**同語料庫**負例（`shadow_diffswap_fake`）測，
    上線 head AUROC **0.380（比亂猜還差）**，但**同一組凍結特徵**的 out-of-sample LDA 是
    **0.994**，in-domain 方向轉移過去是 0.285。→ **這是 read-out／訓練資料問題，不是表徵問題**，
    +0.614 AUROC 的空間是本專案量過最大的。
  - **介入**：只動訓練資料、Layer1 凍結在 v8.17。C1（+5,400 張 in-the-wild 濾鏡圖進 filter class）
    是本專案史上**第一支贏過 threshold-only frontier 的 Layer2 arm**（9/9 matched budget，
    +2.51~+11.11pp），同配方 CTRL 對照組乖乖落在曲線上（1/9）。
    在與 production 對齊的 dev 安全預算下：Shadow filter recall **13.26 → 23.30%**
    （+10.04pp，CI [+6.09,+14.34]）、VGGFace2 語料庫的 DiffSwap fake recall
    **55.67 → 62.54%**（+6.87pp，CI [+4.12,+9.97]）、True Test filter recall 不變、
    **全部 Freeze-Gate A 通過**。
  - **為什麼不升級**：trap #2 低 FPR 區退步（pAUC≤5% 0.1626→0.1420、TPR@5% 0.324→0.269、
    TPR@10% 0.481→0.403，只有 TPR@1% 變好），事前寫死的 `SUCCESS` 規則禁止這種情況 →
    判 `PARTIAL`，**不提 change proposal，production 完全未動**。
  - **事前假設被推翻的一半**：原本預測「雙邊去混淆（C2：同語料庫也放進 fake class）會贏過
    單邊（C1）」——**方向是錯的**。C2 落在 frontier 上（4/9），但 C2 才是**安全**那一支：
    四項低 FPR 統計量全部改善、AUROC 0.8494（全場最佳）、stress 零代價。
  - **下一步（低成本、已寫進 findings §10）**：C1 與 C2 之間的**劑量／比例掃描**——
    C1 是「全濾鏡側」端點（贏 frontier、賠低 FPR），C2 是另一端點（打平 frontier、賺低 FPR）。
    另外 `splits/v811_layer2_val.txt` **已飽和**（三支 arm 都在 epoch 1 就 0.998），
    根本選不出任何東西，下輪 Layer2 訓練前應先建**依語料庫分層的 Layer2 val split**。
- [x] **P1-R13（2026-08-20 完成）**：表徵學習方向。結論見下方 G 節。
  **前提被自己的事前篩檢推翻**：問題不在表徵，在 read-out。表徵學習列為第六個關閉的方法族，
  但同時**開啟了第七個、前所未測的方向：read-out 幾何**（詳見 G 節）。
- [ ] **mixed_retouch Gate 1 重新設計**：原版觸發邏輯召回率 31.6%／精確率壓線 80.88%，
  且被證明 100% 依賴 softmax（跟設計初衷矛盾）——正在重新設計判斷訊號來源。

### F4｜等待人類決策（不會自動推進，需要你回答）

- [ ] **`mixed_retouch` Gate 2 政策**：entitlement table 要多嚴，取決於「真實用戶更像自建
  乾淨資料還是外部多重操作資料」——已給建議（傾向假設用戶更像外部/app-processed 家族），
  未正式拍板。
- [ ] **Face2Face 是否正式納入 FF++ Status C**：用 v8.17 重測後已跨過 60% 門檻並完成完整
  Stage 4/4b 驗證（IoU@10%=0.334，faithfulness 3/3 過），**尚未走過正式 change control 核准**。
  > ✅ **2026-08-22 已正式送審（P2-R6 Task B）**：證據已複核（checkpoint SHA256 與
  > production 相符、`contamination_cleanup_20260821` 稽核未發現新污染影響此證據）並
  > 整理成 §10 addendum，附於原已核准提案
  > `docs/team/change_proposals/20260819_fake_xai_status_c_upgrade_ffpp.md`。
  > **狀態仍為 PROPOSED，Approval Record 留白待專案負責人裁決**，本條目在核准前不打勾。
- [ ] **SBIR10（2 倍規模 SBI）是否要 promote**：已有正式提案（`docs/team/change_proposals/
  20260820_p1_r10_sbi_scale_layer1_sbir10.md`），Approval Record 留白，是安全性 vs 乾淨照片
  辨識力的取捨，不建議預設升級。
- [ ] **2026-08-21 新發現，待決**：production 的 `shufflenet_v2_layer1_v817sbi.pth`
  經 sha256 核對，真實身份是 P1-R9 的 **SBIAUG** arm（不是檔名/CLAUDE.md 簡稱暗示的
  「SBI」arm）。數字本身正確（`P1_R9_FINAL_FINDINGS.md` 與變更提案檔名從頭就正確
  記載勝出候選是 SBIAUG），純粹是頂層摘要文件的簡稱造成誤導。是否要把檔案改名為
  `shufflenet_v2_layer1_v817sbiaug.pth`（或至少把 CLAUDE.md 簡稱改為完整名稱）
  待人決定；本輪未動任何 production 檔案。詳見
  `results/research/contamination_cleanup_20260821/CLEANUP_AND_RETEST_REPORT.md`。

### F5｜低優先／已知限制（有明確原因，非目前重點）

- [ ] `model_version` 欄位寫死 `"v8.11"`，跟現在跑的 v8.17 不符（C1.9.12），純文字 bug，
  低成本可修，未修。
- [ ] `docs/structured-output.schema.json` 跟實際輸出的 schema 2.1.0 對不上（C1.9.13），
  2026-08-11 起就過期，跟本輪無關，未修。
- [ ] fp16／int8 TFLite：**結構性已知壞掉**（fp16 是 CONV_2D 型別衝突、int8 是 FFT branch
  動態範圍問題），根因都已查清，換版本不會變好，不需要重複測試。
- [ ] Android 真實裝置實測：**我沒有實體裝置**，是 Member C 的任務，整個專案至今沒人做過，
  不是這輪能補的缺口。
- [x] `v811_layer1_val.txt` 重建（移除 2,644 列 `FFHQ_ali_process`）：✅ **2026-08-21
  完成**，見 C1.11.7 與 `results/research/contamination_cleanup_20260821/`。

### F6｜還沒開始、但已知是低成本機會（可隨時排進下一輪）

- [x] ✅ **2026-08-20 三項全部執行完畢（Phase 2，Member B）**。事前協定
  `results/phase2/PRE_DECLARED_PROTOCOL_sbi_xai_20260820.md`（含 verdict 規則，跑數字前寫死）。
  **污染控制**：eval 一律用 `sbi_data/p1_r10_sbi_scale_20260820/sbi/aiguard_real/`——production
  Layer1（v8.17 = P1-R9 SBIAUG）的 SBI 來源池只有 imdbwiki/celeba/lfw/vggface2，**沒有
  aiguard_real**，所以這批 blend 影像 production 從未見過；region head 訓練用 p1_r9（與 eval
  來源照片 stem 交集 = 0，已 assert）。**三項全為負面／限制性結果，無一支持擴大 fake 的
  region 宣稱**，`pipeline.py` 的 `regions = []` for fake 維持不變、未被修改。
  - [x] **Step 0（新增，先做）8-region GT 退化稽核**（`phase2_sbi_region_gt_audit.py`，
    `results/phase2/regionhead_fake_sbi_20260820/region_gt_audit.json`）：SBI mask 是
    landmark convex hull，**幾何上本來就近似全臉**——mask 覆蓋人臉框中位數 62%，平均每張
    6.58/8 個 region 為正，56.9% 的圖 8/8 全正，800 張只有 21 種相異標籤向量。勉強通過事前
    退化門檻（僅 nose 一個 region ≥95%），但區辨力幾乎全部來自 hull_type 抽樣（type 3
    CENTRAL 才局部化，type 0/1/2 近全臉）。**這是後面兩項結果的共同根因。**
  - [x] **① Qwen-VL 重測 → `NO_USABLE_LOCALIZATION_SIGNAL`**（`phase2_qwenvl_sbi_localization.py`，
    `results/phase2/qwenvl_sbi_localization_20260820/`，n=60，1,080 次 fp32 two-token forward，
    free-text 依 P3-M0 既有定論一開始就排除）。**分類側是新的正面證據**：SBI vs
    **同一張底圖** AUROC=**0.735**、paired win rate 85.0%——P3-M0 的 0.804 並非 content-controlled
    （比的是不同的 real 與不同的 fake），這個 0.735 才是同照片配對的乾淨數字，兩者不可直接比大小。
    **定位側完全不成立**：pooled region AUROC=0.576（content-controlled 0.540），top-1 命中
    0.850 但「永遠答 nose」的平凡基線是 **1.000**、image-independent 平均圖也有 0.867。
    **機制與 `run_teacher_filter_logit.py` 完全相同**：blend 讓 8 個 region 的 p(yes) 一律
    上升 +0.099~+0.132（跨 region 全距僅 0.033），模型偵測到「這張被動過」後對**問哪裡都說有**。
    → 拍板：Qwen2-VL-7B-Instruct 的空間監督路線兩個家族（filter type、fake region）皆已關閉，
    §K.4 混合監督決策獲得更強支撐。
  - [x] **② fake 類 region head pilot → 輸給 no-image 平凡基線，且輸給「畫人臉框」**
    （`phase2_train_region_head_sbi.py` + `phase2_gradcam_vs_regionhead_sbi.py`，
    `results/phase2/regionhead_fake_sbi_20260820/`）。架構原封沿用
    `AIGuard/train_region_head_v4.SpatialRegionHead`，backbone 改用 production Layer1
    `v817sbi` 凍結；fit 5,100 / val 900 / test 600（照片互斥）。
    **macro F1：trained head 0.8311 vs no-image trivial baseline 0.8944（Δ −0.0632，8/8 個
    region 全輸）**——v1 的 label degeneracy 以新標籤來源重演，且比 v4 更糟（v4 至少 +0.092）。
    **像素級定位（IoU / PointingGame / IINC，`xai_eval_protocol.py`，top_frac=0.15，n=600）**：
    | 方法 | IoU | PointingGame | IINC |
    |---|---:|---:|---:|
    | trivial：畫人臉框（centroid 峰值）| **0.5499** | **0.9783** | **−0.0158** |
    | Grad-CAM++（Layer1 manipulated）| 0.4836 | 0.8850 | −0.0029 |
    | trivial：置中橢圓（完全不看圖）| 0.4571 | 0.9267 | 0.0008 |
    | region head（box paint）| 0.4429 | 0.8067 | 0.0065 |
    | region head（logit map）| 0.4270 | 0.8950 | 0.0253 |
    | Grad-CAM++（Layer2 fake，conditional n=268）| 0.5045 | 0.8881 | −0.0144 |
    Grad-CAM++ 贏 region head（ΔIoU=+0.0566，bootstrap 95% CI [0.0458, 0.0677] 不含 0），
    **v1→v4 的既有模式在 fake 側依然成立**；但**兩者都輸給「直接畫人臉框」**。
    **方法論結論（本輪最重要的一條）：SBI blend mask 不適合當 fake 定位品質的 benchmark**——
    它按建構方式就是人臉 landmark convex hull，任何對它算的 IoU/PointingGame 主要在量
    「有沒有找到臉」，不是「有沒有找到竄改處」。往後要量 fake 定位品質請用 FF++ 官方 mask
    （Tier D，覆蓋率 24-31%），不要用 SBI mask。
  - [x] **③ 量化特徵 → 可算，但無法落地成 runtime 模板**（`phase2_sbi_quantitative_features.py`，
    `results/phase2/fake_template_enrichment_design_20260820/features.json`，n=600）。
    配對（offline-only）特徵確實算得出來：mask 覆蓋人臉框 0.546、mask 內 ΔE 23.62、
    邊界帶 ΔE 20.23、boundary alpha gradient 0.0346。**但兩個發現讓「填進 fake 模板」這條路
    不成立**：(a) **mask 內外 ΔE 中位數比僅 1.13**（in 23.62 / out 19.47）——SBI 的全域
    JPEG/降採樣/HSV 增強讓遮罩外的像素改變幾乎跟遮罩內一樣大，所謂「blend 區域」在 ΔE
    上本來就不突出；(b) **沒有任何 runtime-legal（單張圖可算）特徵能預測任何 offline blend
    量值**，全部 |r| ≤ 0.122，連用了 GT mask 的 oracle 特徵也只有 +0.227。
    → **設計結論：不提出把數字填進 fake 模板的方案**。詳見下方 §「fake 模板量化增強：不採用
    的理由與唯一可行的替代設計」。**未修改 `pipeline.py` / `TEMPLATES` / `ARTIFACT_REGION_MAP` /
    任何 schema。**
  - [ ] **NEW OPEN（低優先）**：若日後仍想要 fake 側 region-level 監督，正確的資料來源是
    FF++ 官方 mask（已有 Tier D 證據鏈），不是 SBI mask；且需先確認 mask 覆蓋率明顯小於
    人臉框，否則會重蹈本輪「贏不了畫人臉框」的問題。


---

## 📊 P1-BENCH-POWER｜Benchmark 統計檢定力升級（2026-08-20 完成）

完整報告：`results/research/p1_bench_power_20260820/BENCHMARK_POWER_REPORT.md`
Registry：`docs/EXPERIMENT_REGISTRY.md`「P1-BENCH-POWER」條目。
**未修改任何凍結資產**（`splits/truetest_*.txt`、`ultimate_clean_test.txt`、Shadow、
`pipeline.py`、所有 checkpoint 皆唯讀）；新產出走新檔名 `splits/truetest_v2_*.txt`。

- [x] **重大發現：LFW 池已耗盡**。13,328 張 LFW 中通過專案標準清洗的 8,918 張
      **全部**已被某個 split 使用（交集 = 0）。未被使用的 1,835 張實測 Step1 只剩 30.1%
      （多臉打掉 1,283 張）、Step2 後為 **0**（543 closed_eye）。
      **⇒ 可新增的乾淨 LFW base 影像 = 0。** 任何「再多抽一點 LFW」的計畫都不可行。
- [x] **建立 True Test v2（附加基準，不取代 v1）**：real 250 / filter **998** / fake **921**。
      filter 為凍結 250 張 base × 4 種濾鏡的全交叉配對設計，per-type n 從 62 → 249/250，
      CI 半寬 2.9–9.4pp → **1.3–4.7pp**（達成 ±5pp 目標）。凍結 v1 為 v2 的嚴格子集，
      且在 v2 harness 上逐一重現已公布數字。濾鏡參數直接沿用
      `filters/generate_filter_dataset.py`（smoothing/whitening 重生成結果**逐位元組相同**，
      證明參數對上；兩個幾何 warp 差 ≤8/255，來自 MediaPipe landmark 次像素抖動）。
- [x] **內容層級 disjointness 稽核（Known Trap #3）**：K1 解碼像素 SHA256 + K2 dHash 篩選
      經 NCC/MAD 裁決。**抓到 1 張污染並剔除**——`sd2.1/ff/733/253_112.png` 與訓練中的
      `sd2.1/ff/569/253_112.png` 解碼像素完全相同（DF40 同影格存兩個來源目錄，
      路徑 disjoint 通過、內容 disjoint 沒通過）。dHash≤4 篩選偽陽性率 **99.6%**，
      再次驗證 registry 記載的 sub-trap。
- [x] **關鍵判定：v8.11d → v8.17 的 filter recall 差異，在 n=998 下統計顯著**。
      −1.20pp，exact McNemar **p = 0.0118**（b=4/c=16）、cluster permutation p = 0.0166、
      cluster bootstrap 差異 CI **[−2.10, −0.30]** 不含 0。
      同一比較在凍結 n=249 上是 b=0/c=4、**p = 0.1250、不顯著**——原始基準確實無法解析。
      **但**：v8.17 的 real recall 顯著較佳（+3.60pp，p = 0.0225），
      **paired balanced accuracy 差 +1.20pp、CI [−0.25, +2.80]，不顯著**。
      ⇒ 證據支持「同一條 real↔filter trade-off 曲線上換操作點」，不支持「淨退步」。
- [x] **Freeze-Gate 檢定力稽核 — 兩項 gate 無法確認通過**（詳表見報告 §3）：

      | gate | 門檻 | n | v8.17 | 95% CI | 判定 | 需要的 n |
      |---|---:|---:|---:|---|---|---:|
      | True Test fake recall | ≥95% | 270 | 99.63% | [97.93, 99.93] | PASS 已確認 | — |
      | **True Test filter recall** | **≥90%** | **249** | **91.97%** | **[87.92, 94.74]** | ❌ **無法確認** | **≈890** |
      | **True Test paired balanced acc** | **≥80%** | **249** | **82.13%** | **[79.12, 84.94]** | ❌ **無法確認** | **≈1,340** |
      | AIGuard-unseen AUROC | ≥0.80 | 454 | 0.8410 | [0.8034, 0.8760] | PASS（邊際，下界僅高 0.003） | — |
      | CelebA real recall | ≥95% | 3,000 | 99.33% | [98.97, 99.57] | PASS 已確認 | — |
      | StyleGAN2 fake recall | ≥95% | 3,000 | 99.57% | [99.26, 99.75] | PASS 已確認 | — |
      | Alibaba filter recall | ≥95% | 21,151 | 97.71% | [97.50, 97.90] | PASS 已確認（但區間寬度不可引用，見下） | — |
      | [stretch] Shadow paired balanced | ≥60% | 279 | 43.55% | [40.50, 46.59] | FAIL 已確認 | — |
      | [stretch] Shadow filter recall | ≥40% | 279 | 12.19% | [8.85, 16.55] | FAIL 已確認 | — |
      | [stretch] fake+filter 誤判 | ≤2% | 2,289 | 2.80% | [2.20, 3.55] | FAIL 已確認 | — |

      ⚠️ **Alibaba（21,151）與 fake+filter stress（2,289）的 n 具誤導性**：影像皆為
      多型別／多強度作用於共用底圖，並不獨立，區間被高估精度。點估計離門檻夠遠故判定不變,
      但**不可引用其區間寬度宣稱精度**。
- [x] **方法論結論（重要）**：換到 v2 的 998 張後，v8.17 filter recall 92.08%，
      **cluster bootstrap CI [89.80, 94.20] 仍跨 90% 門檻**。
      增加每張底圖的濾鏡型別能解析「兩模型之間的配對差異」，但無法確立
      「單一模型對絕對門檻是否通過」——後者需要更多**互相獨立的底圖**，而 LFW 已耗盡。
      ⇒ 建議寫進論文 Limitation，**不要**因此再開一輪訓練。

### 由本輪衍生的 OPEN 項目

- [ ] **（決策，需人類）v8.17 change proposal 的 caveat 措辭**。
      `docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md` 把 −1.60pp 稱為
      「the one metric that regresses consistently」。較大 n 的證據：
      **支持**「確實退步、非雜訊」與「這是唯一退步項」；
      **需微幅修正** −1.60pp（真實效應量 −1.20pp，CI [−2.10, −0.30]，−1.60pp 偏悲觀端）；
      **僅部分支持** "consistently"（逐型別 smoothing 0.00pp / whitening −0.80pp p=0.625 /
      face_reshaping −1.20pp p=0.250 / eye_enlarging −2.80pp p=0.092，**四格中 0 格自身顯著**，
      整體顯著來自四型別同號小效應累加，主要由 eye_enlarging 帶動）；
      **無法解析**其隱含的「淨退步」意涵（paired balanced 差異不顯著）。
      **本輪未修改該提案**——修訂已核准提案是人類決定。
- [ ] **若要讓 True Test filter recall gate 變成決策級**，唯一路徑是換語料庫取得
      ≥890 張獨立底圖，但會撞上 P1-R14 的 Layer2 語料庫捷徑問題（LFW 乾淨真人
      p_filter≈0.921 vs VGGFace2≈0.089）。建議與 P1-R16 的 Shadow-v2 工作合併評估,
      不要各自建集。
- [ ] **eye_enlarging 是 v8.17 filter 退步的主要來源**（−2.80pp，13 個不一致案例中 10 個
      不利於 v8.17）。若未來要對沖此退步，這是唯一值得針對的型別；
      其餘三型別的差異在 n≈250 下仍不可測。
- [ ] **使用 True Test v2 的前提條件**：本輪 disjointness 參照池限於 v8.17 production
      lineage（252,702 條路徑）。**若新模型訓練用到 v8.12–v8.16 支線資料，必須重跑
      `results/research/p1_bench_power_20260820/audit_v2_disjointness.py` 後才可使用。**

---

## 🧪 P1-R16｜Layer2 counter-row 劑量掃描（2026-08-20/21 完成）

> 完整報告：`results/research/p1_r16_layer2_ratio_sweep_20260820/P1_R16_FINAL_FINDINGS.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md` 「P1-13」條目
> Change proposal（**Approval Record 留白，提案人自己建議退回**）：
> `docs/team/change_proposals/20260821_p1_r16_layer2_counterrow_dose.md`

### 這輪回答了什麼

P1-R14 留下的唯一問題：`C1`（只在 filter 側加 in-the-wild 資料）打贏 frontier
9/9 但在 AIGuard-unseen 的 low-FPR 區間退步（Known Trap #2）；`C2`（兩側都加）
low-FPR 全好但打不贏 frontier。**這兩件事是必然綁死的嗎？**

**答案：不是。** 把兩者唯一的差異（fake 側 SBI counter-row 數量 `k`，劑量
`r = k/5400`）以 0 / 0.25 / 0.50 / 0.75 / 1 掃描：

| arm | r | frontier | AUROC | pAUC(FPR<=5%) | TPR@1% | dev-point Shadow filter recall |
|---|---:|---|---:|---:|---:|---:|
| PROD_v817 | — | — | 0.8410 | 0.1630 | 0.0370 | 13.26% (37/279) |
| C1 | 0.00 | 9/9 | 0.8200 | **0.1420** | 0.0741 | 23.30% (65/279) |
| R25 | 0.25 | 9/9 | 0.8384 | 0.2081 | 0.2130 | 19.35% (54/279) |
| R50 | 0.50 | 9/9 | 0.8390 | 0.2649 | 0.2731 | 19.00% (53/279) |
| **R75** | 0.75 | **9/9** | **0.8468** | **0.2646** | **0.2778** | **20.43% (57/279)** |
| C2 | 1.00 | 4/9 | 0.8493 | 0.2070 | 0.1157 | 15.05% (42/279) |
| R75s2 | 0.75（換種子）| 9/9 | 0.8465 | 0.2661 | 0.2731 | **19.35% (54/279)** |

所有內部劑量都以 **9/9** 打贏 frontier（最緊的 budget 上甚至比 C1 更強），
同時把 low-FPR 區間修回來並大幅超越 production（TPR@FPR=1% 是 production 的
**7.5 倍**）。C2 的 frontier 中性是 **r = 1 的端點效應**，不是每加一條
counter-row 就要付的代價。

### ⚠️ 最重要的一件事：R75 的 SUCCESS 換種子就沒了

`R75s2` = 同一份 split（逐位元組複製）只改隨機種子重訓：S1 / S2 / S4 **全部
複現**，**S3 差 3 張影像沒過**（19.35% vs 預先宣告的 20.00% 門檻）。
20.00% 相當於 279 張中的 55.8 張，兩個種子分別落在上方 1.2 張與下方 1.8 張。

**穩健成立的結論**：r = 0.75 可以在 matched dev-set safety 下穩定換到
**約 +6～+7 pp** 的 Shadow filter recall（兩個種子的 bootstrap CI 都不含 0），
並穩定修好 low-FPR 區間。**不穩健的是「有沒有跨過 20% 這條絕對線」。**

### 待辦（依優先序）

- [ ] **（阻擋 promotion）multi-seed 確認**：r = 0.50 與 r = 0.75 各跑 3–5 個
      種子，回報 dev-point Shadow filter recall 的**分布**而非點估計。
      每個 arm 約 25 分鐘。**在這件事做完之前，不要對 R75 做任何 production 決定。**
- [ ] **把 S3 這類「絕對門檻」判準換成 paired-significance 判準**。本輪
      「>= 20%」只分辨了 3 張影像，而所有內部劑量在兩個種子下的 bootstrap
      delta 都顯著。未來輪次應該以 CI 不含 0 為準，不要用整數門檻。
- [ ] **corpus-stratified Layer2 validation split**（P1-R14 就提出，仍未做）。
      本輪再次確認 in-domain val 完全飽和：所有 arm macro-F1 = 0.998、epoch 1
      就到頂，epoch selection 對本輪量測的任何東西都是盲的。
- [ ] **幾何型別（eye_enlarging / face_reshaping）是殘餘失敗軸**。本輪在
      n≈290/型別、區間可分離的條件下量到：介入把 photometric 型別拉 3–4 倍
      （smoothing 14.1→60.8、whitening 24.6→44.9），幾何型別不到 2 倍
      （eye 13.2→25.3、reshape 13.6→22.0）。**這是第一次有足夠檢定力的目標。**
- [ ] **重建 production Layer2 split 時要加 decoded-pixel dedup**：本輪依另一輪
      的通報實測，`sd2.1` 的 3,000 條路徑只對應 **2,966 張不同影像
      （34 組重複）**，全部是同一檔名出現在兩個 `sd2.1/ff/<dir>/` 目錄下。
      影響 = 該 split 的 0.022%，且**每個 arm 完全相同**（都來自同一份 v811
      base split），所以不影響本輪任何 arm 間比較，但它是 production split
      裡一個既存的小瑕疵。**dHash 不可當 dedup 判準**——本輪實測
      dHash<=4 的偽陽性率是 **99.98%**（4,172 命中只有 1 個不是偽陽性）。

### 新增的評測資產（次要確認集，非決策用）

- `shadow_v2a_filter/`（1,152 張，底圖 `vggface2_train_sample`，
  **與主 Shadow 集 identity-disjoint，0/297**）— **Shadow-v2 主層**
  ⚠️ **2026-08-26 註：S2A 已退休（`README_DEPRECATED`）。P2-R1／P1-R17 稽核發現其底圖
  100% 在 Layer1 訓練池、濾鏡後影像 71.4% 與訓練近重複——「與主 Shadow 集 identity-disjoint」
  對訓練洩漏毫無意義。P1-R16 所有 S2A 結論（含 +21.72pp、per-type 排名）視為已被 S2B 重驗取代。**
- `shadow_v2b_filter/`（1,114 張，底圖 `vggface2_test_sample`，photo-disjoint
  但 **287/287 identity 重疊**）— 較弱的第二層，**不可與 v2a 合併報數**
- 兩者都用建構原 Shadow 集的**同一個濾鏡模組**（`generate_vggface2_filters.FILTERS`），
  每張底圖套**全部 4 種**型別（原集是隨機 1 種），所以每型別 n 從 ~70 拉到 ~290
- 內容鍵稽核：對 Layer2 訓練集 138,283 條路徑做 decoded-pixel SHA256，
  **exact match = 0**；1 張 borderline 已剔除
- ⚠️ **整體 recall 必須用 cluster bootstrap**（每張底圖 4 個型別互相相關），
  per-type 才可用 Wilson

### 本輪發現的一個量測有效度問題

**主 Shadow 集（n≈70/型別）的 per-type 排序不可用。** production 在主集上
「最好的型別」是 face_reshaping（19.7%），在 4 倍大的 identity-disjoint 集上
變成 whitening（24.6%）、face_reshaping 掉到 13.6%。主集四個型別的 Wilson
區間互相重疊，那個排序從來就沒有統計支持。**論文不要引用主 Shadow 集的
per-type 排名。**

---

## 🟢 DEFECT｜schema / output contract 不一致（2026-08-21 記錄，**2026-08-22 已修復**）

**狀態**：RESOLVED（2026-08-22，Member A 直接修復並驗證）。原本記錄「不應直接修」是因為
當時研究 agent 不具備 production 變更權限；本次由 Member A（reviewer/approver 本人）
直接執行，非研究 agent 自我核准，符合 change control 精神。
關聯既有條目：**C1.9.13**、**C1.9.12** 皆已解決，見下方逐項標記。

**修復內容**：
1. `pipeline.py` 新增 `MODEL_VERSION` 常數（`"v8.17"`），取代兩處寫死的 `"v8.11"` 字串，
   往後只需改一處。
2. `docs/structured-output.schema.json` 更新為 2.1.0：`$id`/`schema_version` 改 2.1.0、
   新增 `model_version` 必要欄位、`prediction` enum 加入 `"non_face"`、`artifact_types`
   enum 的 `over_smoothing` 改回 `smoothing` 並加入 `"unknown_filter"`、
   `suspicious_regions` enum 加入 P2-R2 的 7 個 `emp_*` 經驗擬合區域鍵名（原 8 個解剖
   區域鍵名保留，供 Grad-CAM 等其他呼叫端相容）。
**驗證**：語法檢查通過；用 `jsonschema` 對兩張端到端跑出的真實 JSON 輸出（whitening、
eye_enlarging 各一張）驗證，`VALIDATES OK`。
**已知但本輪未動的殘留缺口**：`image`／`class_probs` 兩個欄位 pipeline.py 有輸出但
schema 從未宣告過（`additionalProperties: false` 會拒絕含這兩欄的嚴格驗證）——這是
本次稽核前就存在的既有缺口，不在 C1.9.12/C1.9.13 原始範圍內，未在本輪修復，留待下次
一併處理。

**證據**：`results/research/phase2_design_review_20260821/PHASE2_DESIGN_REVIEW.md`（設計審查）。

> ✅ **2026-08-22 已修復（Member A 直接執行）**：P2-R6 Task A 大規模重驗證（565 張
> 跨 real/fake/filter/non_face 全分支）發現殘留缺口為 100% 阻擋——`image`／
> `class_probs` 觸發 `additionalProperties: false`，`non_face` 的 `confidence: null`
> 不符合 `"type": "number"`。已直接修正 `docs/structured-output.schema.json`：
> 新增 `image`（string）、`class_probs`（object，含 real/fake/filter 三個機率鍵,
> 允許 null）為宣告欄位；`confidence` 改為 `["number", "null"]`。**驗證**：8 張涵蓋
> filter/real/fake/non_face 全分支（含合成雜訊圖觸發 non_face）的端到端輸出，
> `jsonschema.validate()` 全數通過。`pipeline.py` 未變動（純 schema 文件修正）。
> 完整數據見 `results/research/p2_followup_verify_20260822/FOLLOWUP_FINDINGS.md`，
> 登錄檔 `docs/EXPERIMENT_REGISTRY.md`「P2-R6」。上方「為何不能直接修」的舊結論已
> 「殘留缺口」的嚴重程度從「已知但未量化」升級為「已用完整批次數據證實 100%
> 阻擋」，供負責 production 介面的人優先排序時參考。

### 精確落差（4 項）

| # | `pipeline.py` 實際輸出 | `docs/structured-output.schema.json` 宣告 | 後果 |
|---|---|---|---|
| 1 | `"schema_version": "2.1.0"`（`pipeline.py:477`、`:532`）| `"const": "2.0.0"`（schema `:12`）| **const 不符 → 驗證直接失敗** |
| 2 | artifact type `smoothing` | enum 只有 `over_smoothing`（另含 `eye_enlarging`/`face_reshaping`/`whitening`）| **enum 不符 → 驗證失敗** |
| 3 | 可輸出 `unknown_filter` | artifact type enum 中**未定義** | **enum 不符 → 驗證失敗** |
| 4 | 可輸出 `non_face`（2026-08-11 face-gate 加入）| `prediction` enum 中**未定義** | **enum 不符 → 驗證失敗** |

**淨結論：目前 production 輸出無法通過本專案自己的 schema 驗證。**

### 影響

- **阻擋 Member C 的 deployment validation**：C 的驗收方式是拿 `pipeline.py` 的實際輸出
  對 `docs/structured-output.schema.json` 做驗證；在上述任一項未對齊之前，**驗證必然失敗**，
  且失敗原因是文件與 production 介面不同步，不是 C 的整合有問題。
  在修好之前，C 不應把驗證失敗當成自己端的 bug。
- **對外交付風險**：這是任何外部審閱者或整合方第一步就會撞到的不一致。

### 為何不能直接修

`pipeline.py` 的輸出與 `docs/structured-output.schema.json` **同屬 production output contract**。
- 改 schema 去遷就 pipeline ⇒ 對外契約變更（下游消費者的驗證行為會改變）。
- 改 pipeline 去遷就 schema ⇒ 直接改 production 行為。
兩者都**不是**文件衛生問題，都需要 change proposal + 人類核准。
**待辦**：由負責 production 介面的人開一份 change proposal，決定對齊方向
（建議方向為把 schema 升到 2.1.0 並補齊 `smoothing`／`unknown_filter`／`non_face`，
但**方向本身即為需核准的決策**，本記錄不代表任何已核准的決定）。
可與 C1.9.12（`model_version` 寫死 `"v8.11"`，實際跑 v8.17）合併為同一份提案處理。

---

## P2-R1｜Tier-A 解釋定位 benchmark（2026-08-21 完成，零訓練）

> 完整報告：`results/research/p2_r1_tierA_localization_20260821/P2_R1_FINDINGS.md`
> 登錄檔條目：`docs/EXPERIMENT_REGISTRY.md`「P2-R1」
> Change proposal（**Approval Record 留白，未核准、未套用**）：
> `docs/team/change_proposals/20260821_p2_r1_localization_consequences.md`
> 本輪**未修改** `pipeline.py`、任何 checkpoint、`splits/`、既有 `results/` 內容。

### 已完成

- [x] ✅ **建成 8,784 張逐像素配對 GT 的 Tier-A 定位 benchmark，涵蓋四種濾鏡與兩個底圖域**
  （S1 對齊/train-seen 4,000；S2 對齊/held-out 249；S3 VGGFace2 野外/held-out 2,535；
  另 P 池 2,000 只用於擬合常數遮罩基線）。GT = base 與 filtered 的 CIELAB ΔE76 逐像素差
  + 3×3 中值去雜訊 + τ=3.0；純 JPEG 重編碼控制組顯示該門檻的偽陽性像素 < 0.5%；
  τ ∈ {1.5,2,3,5,8} 全部重算，15 格中 13 格判定不隨門檻改變。
- [x] ✅ **更正一個文件層級的誤讀**：設計檢視引用的「31,993 列 paired GT」
  （`results/landmark_gt_summary.csv`）**是 8 個解剖框的 0/1 表，不是像素遮罩**，
  且 `generate_landmark_gt.py` 從未保存逐像素差異圖。像素級 GT 是本輪**重算**的，不是重用。
- [x] ✅ **跑完四種強制平凡基線**（whole-face box、face-centred box、center box/point、
  面積配對隨機框、**每型別常數遮罩**），外加把 production 真正在用的
  `ARTIFACT_REGION_MAP` 展開成像素框一起計分。
- [x] ✅ **裁決：Grad-CAM++ 與 `region_head_v4` 在 production 操作點上，15 個
  （層×型別）格子輸掉 13 格給「完全不看影像」的每型別常數遮罩。**
  唯一倖存的勝利是 S3（野外）/ whitening / 判成 filter 子集：
  ΔAPlift = +0.216 [+0.063,+0.367]（n=134；乾淨子集 +0.247 [+0.039,+0.453]，n=67），
  而該格效果量小、τ=8.0 會翻面、且 whitening 的 GT 已覆蓋人臉框 64%（弱定位）。
- [x] ✅ **Known Trap #1 再度命中，而且方向相反**：S3/smoothing 在「全部影像」上
  Grad-CAM++ 顯著勝出（+1.274），在 production 實際會輸出解釋的子集上**顯著落敗**（−0.635）。
  → **往後任何定位宣稱都必須同時報「全部影像」與「判成 filter 子集」兩個數字。**
- [x] ✅ **新結果（正面，適合寫論文）：解釋定位與分類崩潰是解耦的。**
  同一批圖上 filter recall 91.97% → 14.62%（6.3 倍），但 Grad-CAM++ 的 APlift 只掉 17.5%
  （6.717 → 5.539，仍為隨機的 5.5 倍），smoothing 甚至完全不掉。固定先驗掉得更多（−31.9%）。
- [x] ✅ **內容層級去重稽核（解碼像素 SHA256，Known Trap #3）**：S2 / S3a / S3c
  對 252,710 條訓練語料路徑**零命中**；S1 依建構 100% 是訓練資料（`filter_data` 全部
  25,212 張清洗後影像都在 `v811_layer2_train/val`，對齊域不存在 held-out 自建濾鏡子集）。
  層內內容重複 0。

### 新發現的問題（需要有人處理）

- [ ] ⚠️ **`shadow_v2a_filter` 的 1,148 張底圖全部在 Layer1 訓練集內**
  （`vggface2_train_sample` 的 297 張 wild real 於 P1-R8 進入 Layer1 real 類，
  P1-R9 又用同一批當 SBI fake 來源）。`generate_p1_r16_shadowv2.py` 當初只 assert
  「與 primary Shadow 不重疊」，**未對訓練語料做內容檢查**——正是 Known Trap #3 的形狀。
  Layer2 從未看過 VGGFace2（0 命中）。
  **P2-R1 的全部 S3 結論已在乾淨的 S3a+S3c 子集複核、逐項不變**，但
  **任何以 Shadow-v2a 為評估集的既有或未來數字都必須標註此事實**（P1-R16 / P1-R17 相關）。
  建議由 Phase 1 負責人確認 P1-R16 之後引用 Shadow-v2a 的結論是否需要加註。
- [ ] `docs/phase2_story.md` 第 5 節的 region head 對照表（n=100/型別、v8.8 backbone）
  應補一行指向 P2-R1，說明同一結論在 n=8,784、production checkpoint、且加入常數遮罩
  對照後的完整版本。**未修改該檔案**，交還文件負責人。
- [ ] Change proposal 的三項（C1 Grad-CAM++ 維持不進 JSON；C2 `ARTIFACT_REGION_MAP`
  保留但補記像素級落差；C3 歸檔 `region_head_v1..v4` + 四支訓練腳本）**待人類 reviewer 核准**。
  C3 執行時必須同步修正 `xai_eval_protocol.py:190` 與本輪
  `run_p2r1_methods.py` 的 `train_region_head_v4` import，否則會靜默斷掉。

### 本輪自己犯並修掉的 bug（記錄以免重蹈）

- [x] `np.argpartition(-flat, k-1)` 對 **uint8** 陣列取負會模 256 迴繞
  （`-0=0`、`-139=117`），**靜默把排序反轉**，導致所有連續方法的 top-k 二值化在挑最冷像素。
  靠「常數先驗在自己的擬合分布上 IoU@GT-面積只有 0.005」這個不合理的診斷值抓到，
  改成先轉 int32 後全部重算。**規則：絕不對 uint8 陣列取負來排序。**

---

## P2-R2｜`ARTIFACT_REGION_MAP` 經驗擬合座標：萃取、held-out 驗證、跨域檢查（2026-08-21 完成，零訓練）

> 完整報告：`results/research/p2_r2_empirical_region_map_20260821/P2_R2_FINDINGS.md`
> 登錄檔條目：`docs/EXPERIMENT_REGISTRY.md`「P2-R2」
> Change proposal（**Approval Record 留白，未核准、未套用**）：
> `docs/team/change_proposals/20260821_p2_r2_empirical_region_map.md`
> 本輪**未修改** `pipeline.py`、任何 checkpoint、`splits/`、既有 `results/` 內容。

### 已完成

- [x] ✅ **把 P2-R1 的連續 `const_prior` 經驗遮罩壓成 `pipeline.py` 能直接用的箱子清單格式**
  （每型別 1–2 個矩形，方法：取與 GT 平均面積相同的 top-k 遮罩 → 連通元件 → 外接矩形，
  次要元件 <5% 主元件面積則捨棄）。擬合僅用 P2-R1 既有的 P 池（500 張/型別，與 S1/S2/S3
  內容互斥，SHA256 已稽核過），本輪**未重新擬合**，只做轉換。
- [x] ✅ **在 P2-R1 從未評分過的 held-out 資料上驗證新箱子**（同一 `iou()`/`topk_mask()`
  函式，逐行複用 `score_p2r1.py`）：**15 個（層×型別）格子全部是新箱子贏，95% CI 全部不含 0**，
  含兩個 held-out 層（S2 對齊 249 張、S3 野外 2,531 張）的全部 4 個型別。
  S2 ALL：old 0.122 → new **0.313**（Δ+0.191 [+0.181,+0.201]，勝率 100.0%）；
  S3 ALL：old 0.153 → new **0.295**（Δ+0.142 [+0.138,+0.147]，勝率 87.5%）。
- [x] ✅ **跨域 generalization 檢查**：箱子只在對齊裁切域（P 池）擬合，但在完全不同的
  VGGFace2 in-the-wild 域（S3）依然顯著贏過現行框，四型別優勢衰減 2–57%（不翻轉方向）。
  最弱的兩格已誠實標註：eye_enlarging（S3 勝率 72.5%，15格最低，因為它是唯一真正局部的
  型別，對野外域臉部姿態變異最敏感）、face_reshaping（S3 跨域衰減 −57%，機制與 P2-R1
  已知的「只有 45–49% 變化像素落在臉框內」一致）。
- [x] ✅ **箱子化代價量化**（相對 P2-R1 連續 `const_prior@15` 數字）：非單調，
  S1/ALL 箱子反而更準（+0.058），S2/whitening 代價最大（−0.200，矩形無法貼合橢圓 GT），
  但代價從未大到推翻「新箱子仍贏現行框」的結論。
- [x] ✅ **寫出 change proposal**（`docs/team/change_proposals/20260821_p2_r2_empirical_region_map.md`），
  含 `ARTIFACT_REGION_MAP`/新增 `EMPIRICAL_FILTER_REGIONS`/`REGION_DISPLAY` 的逐字 before/after、
  held-out IoU 對照表、跨域檢查、blast-radius 界定（只影響 `suspicious_regions`/`explanation`
  文字欄位，不觸碰分類邏輯/checkpoint/threshold/JSON schema 結構）、rollback plan（常數字典，
  trivial）。**Approval Record 刻意留白，待人類 reviewer 核准。**

### 待人類 reviewer 處理

- [ ] 核准或退回 `docs/team/change_proposals/20260821_p2_r2_empirical_region_map.md`。
  若核准，依提案 §6 Test plan 執行：先確認變更前後分類輸出（`prediction`/`confidence`/
  `artifact_types`/`class_probs`）逐位元組不變，再檢查新 `suspicious_regions`/`explanation`
  文字是否需要潤飾（尤其新增的 `emp_*` 系列 `REGION_DISPLAY` 字串，本輪只驗證空間準確度，
  未做文字可讀性審查）。

---

## P2-R3｜`artifact_classifier_v3` whitening 修法擴大驗證：multi-seed + 大樣本 regression + 端到端量測（2026-08-21 完成）

> 完整報告：`results/research/p2_r3_whitening_validation_20260821/P2_R3_VALIDATION_FINDINGS.md`
> 登錄檔條目：`docs/EXPERIMENT_REGISTRY.md`「P2-R3」
> Change proposal 附加章節（**Approval Record 留白，未核准、未套用**）：
> `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md` §5
> 本輪**未修改** `pipeline.py`、production `artifact_classifier_v3.pth`。

補完 `p2_artifact_whitening_20260821` 提案人自己列出的三項缺口：

- [x] ✅ **Multi-seed 複現**（seed=42/123/2024，recipe 完全相同）：增益三種子一致，
  composite whitening 6.0%→68-74%（pooled 70.7%）、Alibaba 60/90 29.6%→86.9-89.4%
  （pooled 88.2%）、True Test whitening 56.5%→**三種子皆 100.0%**。不是單一種子雜訊。
- [x] ✅ **Regression 樣本數擴大至 400/class**（獨立 RNG reserve，與三種子 fit set
  皆驗證 0 重疊）：`eye_enlarging` 退步**證實為真**，98.25%→92.08%（pooled，95% CI
  不重疊），比原始 n=60 估計的 −3.3pp 更大（pooled 約 −6.2pp）。`face_reshaping`/
  `smoothing` 退步在此樣本數下不顯著。
- [x] ✅ **端到端 pipeline 量測**（`pl.run_single()`→`hierarchical_predict()`→
  `classify_artifact()`，production Layer1/2 不變，只換 artifact classifier）
  ——**本輪最重要發現，結果依母體而定**：
  - `fake_filter_hard_neg` composite whitening（fake+濾鏡，n=550）：Layer1/2
    **本來就把 99.6%（547/549）路由到 `fake`**，不是 `filter`——而且這是正確行為
    （`generate_fake_filter_hard_neg.py` 本來就是為了訓練這件事）。`classify_artifact()`
    在此母體端到端幾乎不會被呼叫（549 張只有 1 張），端到端正確率 0.0%→0.18%——
    **原提案孤立量測的 6%→76% 對這個母體的實際使用者體驗影響可忽略**。
  - 純濾鏡 whitening（真人底圖無 fake，`classify_artifact()` 實際服務的母體）：
    端到端增益大且三種子一致——True Test 端到端正確率 50.0%→**95.16%**（三種子皆同），
    Alibaba 純濾鏡樣本（n=600）24.8%→**84.3-85.7%**。
- [x] ✅ **更新 change proposal**：附加 2026-08-21 addendum 章節（原提案文字保留不刪），
  建議從「先不核准」更新為 **PROMOTE WITH CAVEATS**，推薦候選 seed=42（三種子
  whitening 增益相近，eye_enlarging 退步最小），存於
  `checkpoints/research/p2_r3_whitening_validation_20260821/RECOMMENDED_artifact_classifier_v3_whitediv_seed42.pth`。
  **Approval Record 依規則留白，未自我核准。**

### 待人類 reviewer 處理

- [ ] 核准或退回 `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md`
  §5 addendum 的建議（PROMOTE WITH CAVEATS，seed=42）。若核准，需將
  `pipeline.py` 的 `ARTIFACT_WEIGHTS_PATH` 指向新 checkpoint 並走完整 Production
  Change Control 流程（本輪只驗證未套用）。
- [ ] （可選，若要更完整再核准）補測 `eye_enlarging` 退步的端到端影響——本輪只測了
  whitening 的端到端鏈路，`eye_enlarging` 是否像 composite-whitening 那樣被
  Layer1/2 路由「稀釋」掉、還是會直接反映在使用者體驗上，尚未量測。

---

## 🚨 P2 緊急｜`artifact_classifier_v4` production 已核准並接線，端到端量測發現 smoothing／face_reshaping 災難級退步（2026-08-21 診斷完成，待人類決定是否回退）

> 完整報告：`results/research/p2_urgent_v4_diagnosis_20260821/DIAGNOSIS.md`
> 登錄檔條目：`docs/EXPERIMENT_REGISTRY.md`「P2-Urgent」
> 本輪**未修改** `pipeline.py`、任何 `.pth` 權重——只跑推論做診斷。

`artifact_classifier_v4.pth`（= P2-R3 推薦的 `..._seed42.pth`，SHA256 逐位元組確認
相同）已於今日核准並接線至 `pipeline.py` 的 `ARTIFACT_WEIGHTS_PATH`。促成核准的
isolated regression 測試（`filter_data/{cls}` 400 張 reserve）顯示 smoothing 99.5%／
face_reshaping 99.25%「退步不顯著」，但隨後的端到端量測
（`v817_scorecard_gapfill_20260821/eval_artifact_v4_gapfill.py`，`run_single()`→
`hierarchical_predict()`→`classify_artifact()` 全鏈路）測到 True Test smoothing
52.4%、face_reshaping 22.6%，落差巨大。

- [x] ✅ **四個候選根因逐一查證**：排除 routing 失敗（a 值兩邊皆 95-100%）、排除前
  處理不一致（同一支 `run_single()`，唯一變數是權重）、排除量測腳本 bug（8 張手動
  逐張人工驗證與聚合數字一致，權重路徑/標籤解析/呼叫方式皆正確）。**確認為 genuine
  v4 模型退步**。
- [x] ✅ **v3 control（同方法論、同母體、同 seed=777，只換回 v3 權重）**——
  `results/research/p2_urgent_v4_diagnosis_20260821/eval_artifact_v3_control.py`：
  - True Test smoothing：v3=**100.0%** → v4=52.38%（**−47.6pp，全新退步**）
  - True Test face_reshaping：v3=**95.16%** → v4=22.58%（**−72.6pp，全新退步**）
  - Alibaba smoothing：v3=28.4%→v4=18.40%（v3 本來就差，pre-existing OOD 問題，
    v4 又更差一點）
  - Alibaba face_reshaping：v3=3.21%→v4=1.00%（同上，pre-existing）
  - 混淆模式差異：v4 在 Alibaba 系統性誤判為 **whitening**（與微調把 whitening
    訓練資料拉到 4,100 張、其餘三類各 2,500 張的資料組成變化吻合）；v3 系統性誤判為
    **eye_enlarging**（既有、與本次微調無關的舊弱點）。
- [x] ✅ **根因確認**：isolated regression 的 400 張 reserve 直接取自
  `filter_data/{cls}`——也就是訓練資料來源池本身（held-out 但同分布），量到的是
  「模型在自己訓練分布內的準確率」，不是 True Test／Alibaba 這種不同演算法來源、
  `classify_artifact()` 在 production 實際會遇到的母體。母體選錯，不是統計力不足。
- [x] ✅ **影響量化**：True Test 母體下，約 47.6% 的 smoothing 濾鏡照片、約 77.4%
  的 face_reshaping 濾鏡照片會拿到錯誤型別標籤（v3 時代分別 0%／4.8%）。這兩型別
  合計約佔 True Test filter 母體一半。
- [x] ✅ **淨效益判定**：v4 在 4 類濾鏡型別中 1 類大幅進步（whitening）、1 類小幅
  退步（eye_enlarging，pooled −6.2pp，P2-R3 已知）、2 類災難級退步（smoothing、
  face_reshaping，本輪新發現）。以使用者實際拿到正確型別標籤的體驗衡量，**v4 是
  淨負向，不應維持在 production**。
- [x] ✅ **準備（未套用）回退**：`pipeline.py` 第 73 行
  `ARTIFACT_WEIGHTS_PATH = os.path.join(BASE, "artifact_classifier_v4.pth")` →
  改回 `"artifact_classifier_v3.pth"`，一行、trivial，未執行。

### 待人類 reviewer 處理

- [ ] **核准是否立即回退 `pipeline.py` 的 `ARTIFACT_WEIGHTS_PATH` 至
  `artifact_classifier_v3.pth`**（本診斷建議回退）。
- [ ] 若回退，需在 `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md`
  加註本次核准後發現嚴重退步、已回退的記錄，並更新 CLAUDE.md production 版本說明。
- [ ] 未來若要重新嘗試 whitening 修法，須要求同一輪內對全部四型別都做本輪這種
  True Test／Alibaba 端到端量測，不能只用 `filter_data/` 同分布 reserve 當
  regression 測試。

---

## 🔬 P2 跨演算法診斷｜`classify_artifact()` 型別命名在非自產濾鏡演算法/底圖上全面不可靠（2026-08-21 診斷完成）

> 完整報告：`results/research/p2_artifact_crossalgo_20260821/CROSSALGO_DIAGNOSIS.md`
> 登錄檔條目：`docs/EXPERIMENT_REGISTRY.md`「P2-CrossAlgo」
> 本輪**未修改** `pipeline.py`、任何 `.pth` 權重——只跑推論做診斷。
> ⚠️ 注意名詞區分：本項目談的是 `classify_artifact()` 型別命名準確率（b/c 值），
> **不是** Alibaba filter recall（Layer1+2 二元「是否為濾鏡」偵測，那個數字
> 96-100% 沒問題）。

延續今日稍早的 `p2_urgent_v4_diagnosis_20260821`（v4 production 退步、建議回退
v3），本輪把 v3 端到端型別準確率量測從原本只有的 smoothing／face_reshaping 兩型別
擴充到完整 4 型別，並建立完整 8-bucket 混淆矩陣。

- [x] ✅ **完整 4 型別 v3 end-to-end 準確率（True Test / Alibaba）**：
  - smoothing：True Test 100.0% ／ Alibaba 28.4%
  - face_reshaping：True Test 95.2% ／ Alibaba 3.2%
  - whitening：True Test 50.0% ／ Alibaba 24.8%
  - **eye_enlarging：True Test 4.8%（62 張中僅 3 張，全 4 型別最差）／
    Alibaba 78.8%（全 4 型別最好，方向與其他 3 型別相反）**
- [x] ✅ **更正任務背景中的基準線引用錯誤**：原本認知的「eye_enlarging
  True Test ~77-82%」其實是 CLAUDE.md 的 Layer1+2 filter-recall（是否為濾鏡）
  數字，被誤植為 `classify_artifact()` 的型別準確率基準；兩者是不同的量，
  已在報告中更正並區分。
- [x] ✅ **混淆矩陣顯示「域相關吸子」而非「型別相關吸子」**：True Test 域，
  whitening／eye_enlarging 錯判都集中吸向 `face_reshaping`；Alibaba 域，
  smoothing／face_reshaping／whitening 錯判都集中吸向 `eye_enlarging`。每個
  域各自把錯誤答案導向「在該域碰巧最準的那個型別」，不是固定的單一吸子。
- [x] ✅ **四個候選根因逐一查證**：
  - 訓練演算法過擬合：**確認**——查證
    `filter_data/clean_output/clean_paths.txt` 逐張來源，`classify_artifact_v3`
    全部 4 類 100% 只來自 `filter_data/{class}/`（單一腳本
    `filters/generate_filter_dataset.py` × 單一底圖池 `AIGuard/real/`），
    0 張來自任何 `filter_data/lfw_*` 變體（`train_artifact_classifier_v3.py`
    的類別名比對邏輯靜默跳過了這些資料夾）。但只能部分解釋：True Test 用
    「同演算法換底圖」，smoothing/face_reshaping 完全不受影響、
    whitening/eye_enlarging 卻大崩，效應在型別間極不均勻。
  - 特徵層視覺相似度：**部分確認**——eye_enlarging／face_reshaping 皆為輕微
    幾何形變，人工檢視圖片後認為視覺上高度相似，可解釋混淆「方向」但不能
    解釋「哪個域吸向哪個型別」。
  - 信心門檻/開放集拒答假影：**駁回**——`unknown_filter` 佔比最高僅 11.4%，
    遠不足以解釋崩壞幅度；真正的問題是「高信心猜錯」而非「不敢猜」。
  - 無聊的 bug：**排除**——`ARTIFACT_CLASSES` 順序、`ARTIFACT_TAG_MAP`
    恆等映射、母體篩選、聚合統計皆核對無誤。
- [x] ✅ **可修復性評估**：與 whitening 問題（P2-R3）同性質但範圍更廣——
  P2-R3 的 Trap #5（isolated regression 用 `filter_data/{cls}` reserve 測，
  量到的是訓練分布內準確率）不是 whitening 微調獨有的操作失誤，而是整個
  `classify_artifact_v3` 從訓練資料建構階段就繼承的結構性弱點。**不建議
  逐型別打補丁**（例如只加 eye_enlarging 多樣性資料）——4 型別在不同母體上
  各自有不同的弱點組合，沒有一個型別是全域穩健的。
- [x] ✅ **嚴重度評估／三層級結構性類比**：與 `docs/EXPERIMENT_REGISTRY.md`
  P1-R14（Layer2 corpus-shortcut，corpus AUROC 0.989-0.9995 vs
  filtered-vs-real AUROC 僅 0.476-0.581）及長期存在的 Shadow filter recall
  域落差（~15-28% vs True Test ~91-94%）在失敗「形狀」上高度相似（單一底圖/
  演算法訓練來源 → 換來源後崩壞），**同一類結構性弱點在管線三個獨立層級
  （Layer1 底圖域落差、Layer2 corpus-shortcut、本輪 artifact-type 崩壞）被
  觀察到，值得在論文中提出**。但誠實揭露：本輪未做等價於 P1-R14 的
  corpus-AUROC 直接量化（證明模型真的在學底圖來源特徵），證據強度弱於
  P1-R14 本身，措辭上只能說「觀察到相似的失敗形狀」，不能宣稱「證明同一
  根因」。

### 待後續處理

- [ ] 若日後要重新訓練 `classify_artifact()`，需擴充全部 4 類的底圖/演算法
  來源多樣性（不只 whitening），且核准前必須對全部 4 型別 × True Test +
  Alibaba 都做端到端量測，不能只驗證動到的型別（避免重蹈 Trap #5）。
- [ ] 考慮補做一輪 P1-R14 式的 corpus-classification AUROC 直接量測，驗證
  `classify_artifact()` 是否真的在學底圖來源特徵而非濾鏡演算法特徵，把
  本輪的類比從「形狀相似」提升到「機制證實」。
- [ ] CLAUDE.md／production 文件目前完全沒有記錄 `classify_artifact()` 的
  OOD 型別準確率（只記錄 Layer1/2 filter-recall）；建議揭露本輪數字，避免
  未來又把兩種指標搞混。

---

## 🧪 P1-R17｜Layer2 counter-row 劑量 5-seed 複現（2026-08-21 完成）

> 完整報告：`results/research/p1_r17_seed_replication_20260821/P1_R17_FINAL_FINDINGS.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md` 「P1-14」條目
> **本輪未提交 change proposal**（預宣告規則只在有 arm 達到 `ROBUST` 時才要求提案，
> 本輪兩個 arm 皆未達到）

### 這輪回答了什麼

P1-R16 的 `R75` 用「dev-point Shadow filter recall ≥ 20%」這種絕對門檻判定
`SUCCESS`，換一個種子就因為差 3 張影像（279 張中）翻盤。本輪把所有絕對門檻換成
跨種子區間判準，對 r=0.50 與 r=0.75 各跑 5 個種子（3 個沿用 P1-R16 現有跑次、
7 個新訓練），核心判準改成：**pooled 95% CI 排除 0，且至少 4/5 個種子個別顯著**
才算 robust gain（不是「平均值過線」）。

**結果：兩個劑量都沒有過。**

| arm | S1' frontier | S2' low-FPR | S3' Shadow gain | S4' 安全 | verdict |
|---|---|---|---|---|---|
| R50 | 過（9/9，全種子）| 過（全種子）| **敗**（CI [+0.64,+7.96] 排除0，但只 3/5 顯著）| 過 | `NO_ROBUST_GAIN` |
| R75 | 過（9/9，全種子）| 過（全種子）| **敗**（CI [+1.69,+7.91] 排除0，但只 3/5 顯著）| 過 | `NO_ROBUST_GAIN` |

**Round verdict: `SEED_VARIANCE_DOMINATES`**。R50 vs R75 也是
**`INDISTINGUISHABLE`**（Welch p=0.78，區間幾乎完全重疊）——本輪不挑贏家。

Shadow filter recall 種子間跨度：R50 是 13.26%–20.43%（其中一個種子的 delta
剛好是 +0.00pp），R75 是 14.70%–20.43%。顯著與不顯著的種子交錯出現，看不出規律。
造成 P1-R16 翻盤的那個種子（`R75s2`，本輪的 R75 s20260822）在這裡只是中段值，
不是異常點。

### ⚠️ 輪次進行中發現的評測集問題（已處理，不影響本輪結論機制）

P2-R1 稽核發現 `shadow_v2a_filter` 的底圖（`vggface2_train_sample`）**在 Layer1
訓練集內**（P1-R8 加入、P1-R9 當 SBI 來源用過）。P1-R16 建 Shadow-v2 時只查過
Layer2 訓練集（138,283 條路徑），沒查 Layer1。本輪對照 P2-R1 完整 v8.17
production lineage（**252,710 條路徑 / 249,864 張不同影像**）重新稽核：

| 集合 | train-seen 比例 |
|---|---:|
| S2A filtered | **71.4%**（比純底圖污染更糟——濾鏡只是底圖的輕微擾動，所以連濾鏡後影像也大量重複）|
| S2A bases | **100%**（297 張全部與訓練集像素相同）|
| S2B filtered/bases | 0.0% |
| **主 Shadow 集（filtered/bases）** | **0.0%**（本輪對完整範圍重新驗證，之前只驗證過較窄的 138,283 條）|

**處理方式**：協定不修改，寫進 `DEVIATION_LOG.md`。所有 per-type 陳述改用
**S2B**（乾淨，n≈273–287/型別）。S2A 剩餘 329 張「乾淨」影像**不可用**——存活條件是
濾鏡把像素推到離訓練底圖 RMSE>6，這剛好和「可偵測性」是同一件事，用它做推論
等於用篩選後的樣本製造想要的結論；型別分布也證實：smoothing 0 張、
eye_enlarging 0 張存活。**主 Shadow 集（本輪真正的決策依據）不受影響，且首次
針對完整 lineage 正向驗證乾淨。**

### 待辦（依優先序）

- [ ] **本輪的建議：不要再對同一把劑量重跑更多種子求解「哪個劑量比較好」**——
      依本輪量測的種子變異（R50 展幅 0.00–6.81pp，R75 展幅 1.43–7.17pp），
      粗估要到 8–10 個種子才可能把「4/5 顯著」這條線穩定跨過，這是概略估計、
      非正式檢定力計算。是否值得投入這個運算量（約本輪 8 倍），取決於專案對
      這個量級（pooled 約 +4–5pp）Shadow 增益的重視程度。
- [ ] **優先於重跑劑量掃描的下一步：S2B 確認的 per-type 發現**——smoothing
      (6.5–6.6×) > whitening (~2×) ≫ eye_enlarging (~1.7×) > face_reshaping
      (~1.5×)，兩個劑量、5 個種子 pooled 後區間互相分離，是本研究線第一個
      有檢定力支持的 per-type 排名。這指出「介入對哪類濾鏡真的有幫助」，
      不依賴先選定 r=0.50 還是 r=0.75。
- [x] **True Test filter recall 的 ≥90% / ≥92% 門檻分歧已由 Member A 裁定
      （2026-08-21）：正式門檻為 ≥90%**。理由：本輪對每個種子、兩個 arm、以及
      frozen production 本身都算了兩種門檻的結果，全部落在 90.76–91.97%
      （Wilson CI 都橫跨兩條線），沒有任何一個能在 ≥92% 門檻下過關，包括
      production 自己——用 92% 會讓所有已上線版本回溯性地「不通過」，
      判定為不合理，故採 ≥90%。**v8.17 = 91.97%，對此門檻通過**（注意：
      CI [87.92, 94.74] 仍跨門檻，統計上無法完全排除實際低於 90% 的可能，
      見 `results/research/p1_bench_power_20260820/`）。文件中殘留的 ≥92%
      字樣為歷史記錄，不再是現行門檻，不逐一改寫，以此條目為準。
- [ ] **幾何型別缺口在 S2B 上重新確認**（photometric mean lift 4.24–4.34× vs
      geometric mean lift 1.59–1.66×，兩劑量都成立），但**未達原訂「兩個
      stratum 都要分離」的標準**——本輪只剩一個乾淨 stratum。若要正式關閉這個
      問題，需要**再建一個獨立的、經過完整 lineage 驗證乾淨的 identity-disjoint
      confirmation set**，不能重用 S2A。
- [ ] **`generate_p1_r16_shadowv2.py` 類的評測集生成腳本，往後一律要對完整
      production lineage（Layer1+Layer2，非單一 Layer）做 disjointness 稽核**——
      這次的落差就是「只查了正在訓練的那一層，沒查 cascade 裡的另一層」。

---

## 🧪 P1-R18｜幾何型別 counter-row 介入試驗（2026-08-21 完成）

> 完整報告：`results/research/p1_r18_geometric_intervention_20260821/P1_R18_FINDINGS.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P1-15」條目
> **本輪未提交 change proposal**（預宣告規則只在 arm 達到 `PROMISING_CANDIDATE`
> 時才要求提案，本輪兩個 arm 皆為 `NO_GEOMETRIC_GAIN`）

### 這輪回答了什麼

P1-R17 確認（S2B，5-seed pooled，有檢定力）counter-row 介入對 photometric 型別
（smoothing 6.5–6.6×、whitening ~2×）的提升遠大於 geometric 型別
（eye_enlarging ~1.7×、face_reshaping ~1.5×）。本輪先讀 `sbi/sbi_generator.py`
診斷：SBI 的幾何擾動只有全域小幅仿射（±3%/±1.5%/scale 0.95–1.05）跟一般化
elastic 縫合形變，**沒有任何 landmark 區域定向的幾何扭曲**，跟
`apply_eye_enlarging`/`apply_face_reshaping`（鎖定眼部/臉頰 landmark 的局部
warp）本質不同——這給了假設一個機制上的立足點。於是設計了一個小型試驗：固定
劑量 r=0.75，把專案自己的 `apply_eye_enlarging`/`apply_face_reshaping`
（原封不動從 `filters/stress_test_filter_functions.py` 引入，不重寫）疊加到
0%/50%/100% 的 counter-row 影像上，單一 seed（跟 G0 共用 20260821，只有
counter-row 像素不同）。

**結果：兩個混合比例都沒有過幾何增益的預宣告門檻。**

| arm | P1 geo lift | P2 photo 保留 | P3 Freeze-Gate A | P4 low-FPR | P5 frontier | verdict |
|---|---|---|---|---|---|---|
| G50 | **敗**（CI 下界21.82 < G0點估計23.46）| 過 | 過 | 過（數值更好）| **敗**（0/9）| `NO_GEOMETRIC_GAIN` |
| G100 | **敗**（同上，G50/G100數字相同）| 過 | 過 | 過（數值更好）| **敗**（0/9）| `NO_GEOMETRIC_GAIN` |

**Round verdict: `NO_GEOMETRIC_GAIN`**。G50 vs G100 也是
**`INDISTINGUISHABLE`**（pooled geometric 數字完全相同、CI 完全重疊）。

**意外的次要發現**：兩個候選 arm 的**主 frozen Shadow set 整體 filter recall
顯著下降**（G0 20.43% → G50 15.05% / G100 14.34%，paired-bootstrap CI 皆排除
0），雖然仍高於 frozen production 的 13.26% 底線（不是退到介入前的水準以下，
只是相對 G0 退步）。Freeze-Gate A、low-FPR、photometric 型別皆未受影響。

### 待辦（依優先序）

- [ ] **不宣稱幾何介入本身無效**——本輪只測了 50%/100% 混合比例、單一劑量
      r=0.75、單一 seed。更低比例（如 10–25%）、把幾何濾鏡加到「額外新增」
      而非「取代既有」的 counter-row 上，都還沒做，見報告 §7 建議。
- [x] **Shadow set 退步的機制/穩定性已由 P1-R19 確認（2026-08-22 完成）：
      `INCONCLUSIVE`（既非證實也非否證）**。對 G50 做了 4 個新 seed 的
      replication（20260822/23/24/25，配對既有 G0/R75 5-seed 分布，見
      `docs/EXPERIMENT_REGISTRY.md`「P1-16」條目、
      `results/research/p1_r19_g50_seedcheck_20260822/P1_R19_FINDINGS.md`）：
      新 4 個 seed 的 delta 為 `[-1.08, +0.36, -0.36, -0.36]`pp，遠小於原始
      seed 20260821 的 -5.38pp，個別皆不顯著；5-seed 平均 delta -1.36pp，
      95% t 區間 `[-4.22, +1.49]` 跨過 0——依預宣告規則判定
      `INCONCLUSIVE`（區間跨零：非「整段皆負」不算 CONFIRMED，非「整段
      ≥0」也不算 REFUTED）。額外發現：G0 自己 5 個 seed 的 Shadow 數字
      散布達 5.73pp（14.70–20.43%），跟原始單一 seed 的 -5.38pp 幅度相近，
      顯示原始發現很可能是被 seed 雜訊放大的結果，但 n=5 仍無法完全排除
      殘留真實效果。**此問題視為已結案，不再列為 blocker；未進一步追加
      seed 或嘗試修復**（任務範圍明訂只做確認/否證，不做修復）。
- [ ] `build_p1_r18_geo_counter_rows.py` 產出的 3,998 張幾何增強 counter-row
      影像（`results/research/p1_r18_geometric_intervention_20260821/geo_counter_rows/`）
      與對應 split 檔可直接被未來回合重用，不需重新生成。

## 🧪 P1-R19｜G50 Shadow 退步 seed replication 確認（2026-08-22 完成）

> 完整報告：`results/research/p1_r19_g50_seedcheck_20260822/P1_R19_FINDINGS.md`
> 預宣告協議：`results/research/p1_r19_g50_seedcheck_20260822/PRE_DECLARED_PROTOCOL.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P1-16」條目
> **本輪未提交 change proposal**（verdict 為 `INCONCLUSIVE`，不觸發提案規則；
> 本輪任務範圍明訂只做確認/否證，即使退步被證實也不嘗試修復）

**這輪回答了什麼**：P1-R18 在單一 seed（20260821）觀察到 G50 讓主 frozen
Shadow set 整體 filter recall 顯著下降（20.43%→15.05%，-5.38pp），並明確標記
為未確認、需要 seed replication。本輪只跑 G50（G100 不在範圍內），在 4 個新
seed（20260822/23/24/25，刻意選用跟 P1-R17 既有 G0/R75 5-seed 分布完全相同的
seed pool，做到逐 seed 配對比較，G0 全部 5 個 seed 皆 read-only 重用、
零重新訓練）上重跑同一套 counter-row split + training recipe + Shadow 評測
公式（原封不動沿用 `analyse_p1_r18.py` 的 dev-threshold-matched 公式）。

**結果：`INCONCLUSIVE`**——新 4 個 seed 的 delta `[-1.08, +0.36, -0.36,
-0.36]`pp 遠小於原始 -5.38pp，個別皆不顯著；5-seed 平均 delta -1.36pp，
95% t 區間 `[-4.22, +1.49]` 跨零，依預宣告規則（區間全負才算 CONFIRMED、
區間全非負才算 REFUTED）判定為 `INCONCLUSIVE`。額外發現 G0 自己的 5-seed
Shadow 數字本身就有 5.73pp 散布（14.70–20.43%），跟原始 -5.38pp 的幅度相近，
顯示原始發現很可能被 seed 雜訊放大，但無法完全排除殘留效果。

**過程注記**：訓練途中曾因 session 限制被中斷（seed 20260825 訓練到
epoch 3 被砍斷），已從磁碟狀態逐一驗證每個 seed 的 checkpoint/manifest/
eval 輸出是否真正完整（tensor 數、NaN、sha256、記錄的 seed、shadow_n=279）
才繼續，未完成的部分（不完整的 epoch-1 checkpoint、無 manifest、無 eval）
直接捨棄重跑，未被誤判為「已完成」。

**待辦**：無——此問題視為已結案，不再列為 blocker。若未來要進一步縮小
`[-4.22, +1.49]` 的區間寬度，需要更多 seed（P1-R17 的經驗是超過 5 個 seed
後每多一個的區間縮窄幅度遞減），本輪未啟動此追加。

## 🧪 P1-R20｜Layer2 架構層級介入：DANN（`PARTIAL`）vs 特徵解耦（`FAIL`）（2026-08-22 完成）

> 完整報告：`results/research/p1_r20_domain_adversarial_20260822/P1_R20_FINDINGS.md`
> 預宣告協議：`results/research/p1_r20_domain_adversarial_20260822/PRE_DECLARED_PROTOCOL.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P1-17」條目
> **本輪未提交 change proposal、未動 `pipeline.py`、未動任何 production checkpoint**
> （DANN 為 `PARTIAL`，效果真實但未過預宣告的實質改善門檻，不觸發升版流程）

**這輪回答了什麼**：P1-R14→R19 六輪只用「訓練資料混合」處理 Layer2 corpus
shortcut（Shadow OOD 落差）問題，專案負責人明確要求嘗試架構層級的做法。本輪
真正訓練並評測兩個機制上完全不同的候選（各 3 seed，同一份基礎訓練資料，
byte-identical 沿用 P1-R14 `CTRL` 的 146,425 列 + 新增 12,000 張 CelebA-train
純 domain-only 列，無 task label）：
1. **DANN**（gradient-reversal domain-adversarial training）：19-domain
   分類頭經 GRL 接在 1280 維 spatial+FFT 特徵上。
2. **特徵解耦**（scoped CrossDF/DID-lite）：明確的統計去相關 loss，把
   task-relevant 隱藏層跟 domain-relevant 投影去相關。

**為什麼不是直接拿現有資料當 domain label**：現有 Layer2 訓練資料裡
corpus 跟 class 是同一個切分（filter=LFW/FFHQ，fake=AIGuard/DF40），直接用
這個當 domain label 會讓「去除 domain 資訊」的目標在數學上必然跟任務目標互斥。
本輪改用一個**沒有 task label 的第 19 個 domain bucket**（CelebA-train）
打破這個簡併，且刻意不用 Shadow/Shadow-v2 的底圖語料（會變相把 eval domain
的風格洩漏進訓練）。

**結果**：
- **DANN = `PARTIAL`**：frozen 主 Shadow set（dev-threshold-matched）3 個
  seed 全部正向（+2.51 / +2.15 / +4.30pp vs CTRL），95% t 區間
  `[+0.12, +5.85]pp` 完全不含 0（統計上真實），threshold-only frontier
  3 個 seed 都 7/9 過關，Shadow-v2 S2B 全部 4 個型別、3 個 seed 都優於
  frozen production（+4.3~+8.1pp），Freeze-Gate A 全過、trap#2 低 FPR
  區間不但沒退步反而變好。**但**平均效果 +2.99pp 未達預宣告的 +5pp
  實質顯著門檻（此門檻刻意設在低於 P1-R19 量到的 5.7pp seed 雜訊帶之下）。
  是 P1-R14→R20 這條研究鏈第一個「架構」而非「資料」槓桿在 Shadow 上
  做出方向正確、零代價的移動，但效果量不夠大，不建議直接升版。
- **特徵解耦 = `FAIL`**：3 個 seed 全部負向（-4.66 / -3.58 / -4.30pp），
  95% 區間 `[-5.54, -2.82]pp` 完全在 0 以下（真實的退步，不是雜訊），
  threshold-only frontier 3 個 seed 都 0/9。判斷：把 domain 資訊明確
  抽進一個側支路並跟 task 隱藏層去相關，連帶去掉了模型目前（即使不完美）
  賴以判斷較難 OOD 案例的 corpus 連動訊號，且沒有補上替代訊號。

**候選 checkpoint**（研究用，未升版）：
`checkpoints/research/p1_r20_domain_adversarial_20260822/layer2_p1_r20_dann_s{20260822,20260823,20260824}_taskonly.pth`
（production 相容格式，363 tensors，已驗證可 strict-load 進現有
`DualBranchModel`，但**未套用到 `pipeline.py`，未經負責人審核前不得升版**）。

**待辦（若要延續 DANN 這條線）**：
- [x] `w_domain`（本輪固定 0.3，未調參）做強度掃描，是最直接、成本最低的
      下一步，測試效果量是否隨權重擴大。→ **P1-R21 完成，結論：效果不隨強度
      擴大，反而縮小甚至反轉，見下方條目**
- [ ] DANN 的 domain-only bucket 設計跟 P1-R14 `C1`（labeled 目標域
      counter-row）理論上不互斥，兩者疊加未測試過。
- [ ] 任何升版討論前至少再加 3 個 seed（本輪 n=3 是本專案認定的最低可信門檻，
      不是足夠寬裕的邊界）。
- [ ] 特徵解耦本身的失敗不代表整個方法族關閉——只代表本輪這個 scoped
      實作、這個權重、這份資料下的結果；未來若要重開，應先解釋清楚為什麼
      corpus 連動訊號在解耦後沒有被替代訊號補上。

## 🧪 P1-R21｜DANN `w_domain` 強度掃描：**沒有任何強度可升版，效果隨強度縮小、4x 首次出現安全性倒退**（2026-08-23 完成）

> 完整報告：`results/research/p1_r21_dann_strength_sweep_20260822/P1_R21_FINDINGS.md`
> 預宣告協議：`results/research/p1_r21_dann_strength_sweep_20260822/PRE_DECLARED_PROTOCOL.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P1-18」條目
> **本輪未提交 change proposal、未動 `pipeline.py`、未動任何 production checkpoint**

**這輪回答了什麼**：P1-R20 的 DANN 機制（`w_domain=0.3` 固定值）Shadow 效果
+2.99pp 未過 +5pp 門檻，該輪明確點名「`w_domain` 強度掃描」是最便宜的下一步。
本輪沿用 P1-R20 完全相同的 DANN 機制（GRL/schedule/19-domain 切分/
CelebA-train-only bucket）跟完全相同的訓練資料（hash 驗證與 P1-R20 逐位元組
相同），只掃描 `w_domain ∈ {0.15, 0.30(沿用 P1-R20 未重訓), 0.60, 1.20}`
（0.5x/1x/2x/4x），每個強度 3 個 seed，共 12 個 seed-strength 組合。

**結果：效果不隨強度擴大，反而單調縮小後反轉**：
- w015（0.5x）：Shadow 均值 +3.82pp，95% 區間 `[+2.46, +5.18]pp`（全部研究
  鏈中最窄的區間），無安全性代價，S2B 與 threshold frontier 全鏈最佳，但
  仍未過 +5pp 門檻，也未過本輪自訂的 +4pp「值得加碼 seed」次級門檻（差 0.18pp）
- w030（1x，沿用 P1-R20）：+2.99pp，區間 `[+0.12, +5.85]pp`（=P1-R20 原始結果）
- w060（2x）：+0.60pp，區間 `[-1.46, +2.65]pp`，效果幾乎消失
- **w120（4x）：-0.36pp（轉負），且 trap#2（AIGuard-unseen 低 FPR）在 3/3
  個 seed 全部倒退超過容忍值**（TPR@FPR=5% 最多倒退 -12.96pp 絕對值）——
  這是本 DANN 研究線第一次出現真正的安全性代價，不是雜訊（3 個 seed 同方向）
- Freeze-Gate A 靜態核心指標：12 個組合全過，零倒退（唯獨 w120 的 trap#2 除外）

**判定**：沒有任何強度達到 PRIMARY 或本輪自訂的 SECONDARY 門檻，
不建議任何強度升版。w120 額外判定為 `FAIL`（有安全性代價、Shadow 效果反而
最差，無補償）。本輪同時誠實列出「+5pp 門檻是否校準得宜」的兩種讀法（詳見
findings §8），但未擅自套用較寬鬆的門檻——留給負責人裁定。

**候選 checkpoint**（研究用，未升版）：
`checkpoints/research/p1_r21_dann_strength_sweep_20260822/layer2_p1_r21_{w015,w060,w120}_s{20260822,20260823,20260824}_taskonly.pth`
（production 相容格式，未套用到 `pipeline.py`，未經負責人審核前不得升版）。

**待辦（若要延續這條線）**：
- [ ] w015（0.5x）是全鏈最一致的結果，若要繼續，優先幫它加 2-3 個 seed，
      而不是 w030。
- [ ] 0.10-0.20 之間更細的網格，確認 +3.82pp 是否為真的局部最佳，還是仍在
      seed 雜訊範圍內。
- [ ] +5pp 門檻校準問題（findings §8 Reading A/B）留待負責人明確裁定，
      本輪不擅自變更判準。
- [ ] DANN + P1-R14 `C1` 疊加（P1-R20 待辦，仍未測試）。

## 🔬 P2-R3｜`artifact_classifier_v3` whitening 型別分類崩潰診斷（2026-08-21 完成）

> 完整報告：`results/research/p2_artifact_whitening_20260821/WHITENING_DIAGNOSIS.md`
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P2-R3」條目
> Change proposal（Approval Record 留白，未核准）：
> `docs/team/change_proposals/20260821_p2_artifact_whitening_diversity.md`

`fake_filter_hard_neg/whitening` composite 壓力測試 whitening=6% 已重現
（`phase2_composite_filtertype_accuracy_v1_20260813.json`，跑原腳本逐位元組
重現）。**根因確認為演算法特定過擬合，不是「fake 疊加蓋掉 whitening 訊號」**：
純濾鏡、無 fake 底圖的 Alibaba `Whitening_30/60/90`（不同演算法）已經崩到
23-30%，且同樣系統性誤判為 `eye_enlarging`，跟 composite 條件是同一個失效
模式。分類器只學到訓練用的單一 whitening 演算法（`filters/generate_lfw_filters.py`
的 skin-masked+雙通道 blend）的特定訊號，換一種 whitening 實作就失效。

**順便修正一個文件誤讀**：CLAUDE.md「whitening 91.9%」是 v8.17
hierarchical 分類器的 filter recall，跟 `artifact_classifier_v3` 的型別
準確率是兩件事——本輪首次直接測 True Test 純濾鏡 whitening 子集，
`artifact_classifier_v3` 本身準確率只有 **56.5%**，從未被端到端驗證過。

**修法已產出並驗證（fit/eval 不重疊，程式碼 assertion 驗證 0 overlap）**：
只調整 whitening 類別訓練資料組成（加入 800 張 composite 額外樣本 + 800 張
Alibaba strength-30），其餘三類不變。三個獨立 held-out 條件全面改善
（composite 6%→76%、Alibaba 60+90 29.6%→88.8%、True Test 56.5%→100%），
其餘三類 regression ≤3.3pp（n=60）。**未推 production**——候選權重存於
`checkpoints/research/p2_artifact_whitening_20260821/`，`artifact_classifier_v3.pth`
與 `pipeline.py` 完全未變動。

- [ ] 若要推進：先做 multi-seed 複現 + 擴大 regression 樣本數（現在每類只
      n=60）+ 端到端 pipeline 評測（本輪只測 `classify_artifact()` 孤立
      type accuracy，未測 Layer1/2 先過濾後真正會被使用者看到的錯誤鏈路）。
- [ ] `eye_enlarging`（70%）composite 準確率也偏低，本輪未深入根因（confusion
      多為 face_reshaping），可能是相關的幾何濾鏡混淆問題，值得後續追查。

## 🔧 P2-DataFix｜`artifact_classifier` 訓練資料建構 bug 修復 + 完整性稽核 + 重訓候選（2026-08-21 完成，未推 production）

`p2_artifact_crossalgo_20260821` 診斷輪點名的根因（v3 全 4 類訓練資料 100%
來自單一底圖 `AIGuard/real` + 單一腳本 `generate_filter_dataset.py`，因為
`lfw_*` 系列資料夾被 `train_artifact_classifier_v3.py` 的精確字串比對靜默
跳過）本輪已修復。**更精確的根因**：三個原始 `lfw_*` 資料夾（`lfw_whitening`
`lfw_face_reshaping` `lfw_eye_enlarging`）其實從未跑過 Step1+Step2 清洗——
清洗流程執行時它們還不存在，不是被清單過濾掉，是清單裡本來就沒有它們。
本輪補跑清洗（4034/3984/4243 張通過）＋修正比對邏輯（通用
`normalize_class()` 規則，去 `lfw_` 前綴 + 去 `_s\d+` 尺度後綴，非硬編碼別名表）。

**訓練前完整性稽核（go/no-go gate，已過）**：修正後訓練池 50,223 張，
decoded-pixel SHA256 與 True Test（249張）／Alibaba clean（16,183張）零重疊；
與本 session 已清洗的 Layer1 val split 有 2,802 張路徑重疊，查證後確認是
v3 本來就有的舊重疊、非本輪新增，如實記錄不處理。3/4 類別（whitening／
face_reshaping／eye_enlarging）現有 2 個獨立底圖來源，**smoothing 依然
只有 1 個來源**（本專案從未生成 `lfw_smoothing`，獨立於本次 bug 之外的
資料缺口，本輪未修）。

**重訓候選 `artifact_classifier_v5.pth`**（`checkpoints/research/
p2_artifact_datafix_20260821/`，SHA256 `9596fb50...`）沿用 v3 架構/超參數，
唯一額外變更是加入 inverse-frequency class weighting（修正後
eye_enlarging 佔訓練池 46.7% vs smoothing 12.4%，3.8 倍不平衡，比造成
v4 production 事故的 64% 不平衡更極端，加權重是有實證理由的必要防範）。

**端到端驗證（True Test + Alibaba，正確母體，非訓練來源池）結果混合，
非全面淨改善**：
- True Test：whitening 50.0%→**91.9%**（+41.9pp，統計顯著）、eye_enlarging
  4.8%→**72.6%**（+67.7pp，統計顯著）大幅修復；face_reshaping 持平；
  **smoothing 新增顯著退步 100.0%→74.6%（−25.4pp，95% CI 不重疊，真實）**，
  機制未證實（假說：與 whitening 共訓後光度效應混淆增加，未做表徵層級驗證）。
- Alibaba（跨演算法）：四型別全部落在信賴區間重疊範圍、無顯著變化，3/4
  型別依然 <35% 正確。域相關吸子（`eye_enlarging`）幾乎沒變，其中一個方向
  （face_reshaping→eye_enlarging）還惡化 6pp——**跨演算法域泛化問題本輪
  完全沒有解決**，證實診斷輪點名的「第二個因素」是獨立於資料多樣性之外的
  真實限制。

**未推 production**。完整報告：`results/research/p2_artifact_datafix_20260821/
DATAFIX_FINDINGS.md`。登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P2-DataFix」條目。
Change proposal（Approval Record 留白，未核准）：
`docs/team/change_proposals/20260821_p2_artifact_datafix_candidate.md`。

- [x] ✅ **2026-08-21 P2-CompleteFix 全部完成**（`results/research/
      p2_artifact_completefix_20260821/COMPLETEFIX_FINDINGS.md`，登錄檔
      「P2-CompleteFix」條目）：
  - [x] 調查 smoothing 退步機制：2×2 控制變因實驗（D1=權重-only、
        `v6_fullweight`=資料-only）證實**資料多樣性不足（Gap 1）才是主要且
        足夠驅動因子**，權重公式（原假說重點）獨立效應真實但小、資料修好後
        不再是關鍵變因。
  - [x] 生成 `filter_data/lfw_smoothing`（`filters/generate_lfw_smoothing.py`，
        重用既有 `apply_smoothing` + LFW 候選收集邏輯，未重寫演算法），清洗後
        4,032 張，補上 smoothing 唯一缺乏的底圖多樣性缺口，4/4 類別現在都有
        2 個獨立底圖來源。
  - [x] 修復候選 `artifact_classifier_v6.pth`：True Test 全部 4 型別
        打平或優於 v3（smoothing 100.0%持平、face_reshaping 95.2%持平、
        whitening 50.0%→90.3%、eye_enlarging 4.8%→72.6%），Alibaba 全部
        4 型別在信賴區間內持平（無顯著改善也無顯著退步）。**本研究支線第一個
        True Test 全面淨改善且未讓 Alibaba 變差的候選**，change proposal
        （Approval Record 留白）：`docs/team/change_proposals/
        20260821_p2_artifact_completefix_v6.md`，**尚待人類核准，未接線
        `pipeline.py`**。
  - [x] Alibaba（跨演算法）域泛化：**嘗試訓練時強化增強（5 軸盲設計，未看過
        Alibaba 影像）作為獨立實驗臂，結果為明確負面**——3/4 型別顯著退步
        （機制：放大既有 eye_enlarging 吸子，非教會演算法不變表徵），`v6_aug`
        不採用。連同上一輪已證實「更多底圖來源」無效，本專案目前已測試的
        兩種方法（底圖多樣性、訓練時增強）皆無法移動 Alibaba 數字——**需要
        真正演算法多樣的訓練來源（非本專案自產、Alibaba 以外）或域適應
        技巧，本專案目前不具備，留給未來輪次**，不再是本輪範圍。

- [x] ✅ **2026-08-22 P2-R6 域泛化架構/訓練層級介入（`results/research/
      p2_r6_domaingeneralization_20260822/P2_R6_FINDINGS.md`，登錄檔
      「P2-DomainGen」條目）：明確負面結果，不採用任一候選**：
  - [x] 機制 A（`supcon`，metric-learning／prototype 精神：pre-fc embedding 上
        加 supervised contrastive 輔助損失，同型別跨底圖來源樣本互相拉近）
        × 2 seeds、機制 B（`dann`，domain-adversarial training + GRL，對抗式
        去除 2-way 底圖來源判別訊號）× 2 seeds，共 4 個候選，資料池/split/
        權重公式/epoch 與 v6 完全相同（唯一變因是訓練損失），存檔架構與
        `pipeline.build_artifact_model()` 逐位元組同構，經完整 production
        推論鏈（`pl.run_single→hierarchical_predict→classify_artifact`）驗證。
  - [x] True Test：4 候選 × 4 型別全部落在 v6 的 95% CI 內，無退步。
  - [x] Alibaba（核心目標）：**沒有任何型別出現跨兩個 seed 穩定複現的顯著
        改善**。唯一表面顯著的資料點（`dann_s42` smoothing 37.2% vs v6
        28.2%，CI 不重疊）在第二個 seed（`dann_s123`＝24.0%，CI 完全重疊）
        未重現，依 Known Trap #4 判定為訓練隨機性、非真正機制效應。
        face_reshaping（4型別最弱）在全部 4 候選上完全零移動（4.0-6.2% vs
        v6 6.41%）。eye_enlarging 域相關吸子模式原封不動（未像 v6_aug
        一樣被放大，屬中性但未解決）。
  - [x] 機制層級解讀：兩種表徵學習手法都只能學到訓練資料裡「實際存在」的
        跨域變異；Gap 1 之後每型別雖有 2 個底圖來源，但兩者用**同一支自製
        腳本、同一組寫死參數**，只有底圖人臉不同——資料裡從未真正變動過
        「演算法/參數本身」這個維度，任何表徵學習機制都沒有訊號可學。
  - [x] **本專案至此已用 3 種機制上互斥的槓桿（v6=底圖多樣性資料、v6_aug=
        盲增強、本輪=metric-learning/domain-adversarial 架構）處理同一個
        跨演算法泛化問題，三次收斂到同一個負面結論**：真正需要的是
        Alibaba 以外的第三方（非本專案自製）濾鏡演算法樣本混入訓練，資料
        或模型手段本身無法無中生有這個維度的泛化能力。4 個候選權重存檔於
        `checkpoints/research/p2_r6_domaingeneralization_20260822/`，
        **未接線 `pipeline.py`，僅供 project lead 個人審查**。


## 🔬 P2-R4｜Fake 類解釋忠實性 QA 框架：基準測量 + Grad-CAM++ 具名區域候選（2026-08-22 完成）

**背景**：`phase2_design_review_20260821` 指出 fake class 的解釋是一個 class
一句固定字串，`suspicious_regions` 永遠 `[]`，正確性從未被驗證。本輪建立一套
可重用的忠實性測試框架（ablation/deletion + 內容控制對照），量測現況，並測試
一個候選改法（Grad-CAM++ 具名區域 + 條件式模板句）。完整報告：
`results/research/p2_fake_explanation_qa_20260822/FAKE_EXPLANATION_QA_FINDINGS.md`。
登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P2-R4」條目。

### 已完成
- [x] 框架技術1（ablation/deletion，連續熱圖 + 本輪新增的離散具名區域兩種解析度）
      與技術2（FF++ real/fake 內容控制對照）皆實作並跑通，程式碼在
      `results/research/p2_fake_explanation_qa_20260822/scripts/`。
- [x] Baseline 1（現行固定句）：296/296 逐字相同（entropy=0），FF++ 對照上
      237 個真陽性與 194 個偽陽性也逐字相同——**直接證實**現行文字與是否
      真的有竄改無關。「texture」措辭的獨立紋理代理指標檢查：AUROC=0.2942
      （p=2.6e-18，跨母體、非配對，方向支持但有混淆因子未解）。
- [x] Baseline 2（Grad-CAM++ 原始連續熱圖）：在當前 production（v8.17）、
      n=444（3 來源各 ~150，取代 2026-08-14 舊稽核的 n=150/v8.11d）重跑，
      9/9 格通過 deletion 忠實性——**重現**既有結論，非新結論。
- [x] Part 3 候選（Grad-CAM++ top-2 具名 `FACE_REGIONS` 框）：離散忠實性
      測試 3/3 來源通過（n=444），**但區域多樣性嚴重崩塌**——top-1 眾數
      `nose` 佔 98.65%（438/444），在完全獨立的 FF++ 398 對樣本上以
      91.7-98.6% 逐方法複現，跟真正的竄改類型（換臉 vs 動嘴）無關。194 個
      FF++ 偽陽性（真實照片被錯判 fake）上，候選依然自信點名具體區域
      （常見 `nose+right_eye`）——具體的 overclaiming 案例。
- [x] Part 4 EFS/swap 政策書面化：明確記錄推論時刻無法判斷來源類型是真正
      的開放問題；候選在 EFS 與 FF++ swap 兩種來源上**都**出現同一種中心
      偏誤，故不建議作為任何來源類型的通用 fallback（不是分裂式建議，是
      同一個問題在兩種來源上都存在）。

### 判定
**候選未通過「可無代價替換現況」的門檻**——忠實性維度過關，但多樣性/
overclaiming 維度嚴重失敗。依任務指示，**未提出接線 change proposal**
（沒有正面結果需要留白核准；`pipeline.py` 全程唯讀）。

### 待後續處理
- [x] "always nose" 的中心偏誤可能是 `spatial_branch.conv5` Grad-CAM++
      本身的結構性問題（與 Qwen2-VL SBI、region_head 五輪比較獨立重現同一
      現象），若未來要做 fake 區域定位，可能需要換一個不受中心偏誤支配的
      定位方法——**2026-08-22 P2-R5 已直接驗證此假說（平均 fake CAM 與平均
      real CAM 峰值逐像素重合於幾何中心）並實作 4 種修法，見下方 P2-R5 條目**。
- [ ] FF++ 43.4% 偽陽性率（n=447，真實 target 照片被判成 fake）是本輪的
      副產品發現，值得未來單獨測量 AIGuard/unseen、StyleGAN2、True Test
      等母體是否有類似量級的偽陽性率（本輪未測）。
- [x] Baseline 1 既有的「texture」措辭獨立代理指標檢查（AUROC=0.2942）是
      跨母體、非配對設計，若要正式支持措辭修訂，需要補組內驗證（Known
      trap #4）——**2026-08-22 P2-R5 Task 3 已用 FF++ 447 對同源配對補上組內
      驗證（Wilcoxon p=1.7e-27，但按方法異質，FaceSwap 幾乎 null），見下方**。

## 🔬 P2-R5｜Fake 類解釋修復：4 種區域選擇修法 + 信心/紋理條件化文字 fallback（2026-08-22 完成）

**背景**：延續 P2-R4，驗證「always nose」的根因假說並實作評估 4 種修法
（Fix A 因果 ablation / Fix B 去中心偏誤 / Fix C 對比真實圖 / Fix D 因果效應量
棄權門檻），最後建立文字生成 fallback。完整報告：
`results/research/p2_fake_explanation_fix_20260822/FAKE_EXPLANATION_FIX_FINDINGS.md`。
登錄檔：`docs/EXPERIMENT_REGISTRY.md`「P2-R5」條目。

### 已完成
- [x] 根因驗證：平均 fake CAM（n=444）與平均 real CAM（n=260）峰值**逐像素
      重合**在 224×224 裁切的幾何中心 (112,112)——確認架構級中心偏誤，非
      fake 特有內容訊號。
- [x] Fix A（因果 ablation 選區，8 次額外前向傳遞，實測 +67.27ms/張）：唯一
      在主母體 3/3 來源與 FF++ 母體都通過忠實性測試的修法，多樣性中度改善
      （top-1 眾數 98.98%→54.92% 主母體、95.36%→31.22% FF++），但仍以 nose
      為眾數，FF++ 偽陽性 overclaiming 仍 100%。
- [x] Fix B（去中心偏誤）/ Fix C（對比真實圖平均圖）：多樣性大幅改善
      （entropy ratio 0.98），但**忠實性在 3 個主母體來源中的 2 個直接失敗**
      （aiguard_unseen、truetest_df40 CI 下界 ≤0）——去偏誤同時去掉真訊號，
      任務書預先示警的風險成真。
- [x] Fix D（Fix A + 因果效應量棄權門檻，獨立母體校準）：TP vs FP 效應量
      Mann-Whitney AUROC=0.5402（不顯著）——棄權會同等比例誤殺真陽性宣稱，
      無法選擇性只讓偽陽性棄權。
- [x] 4 種修法在 FF++ 偽陽性上**全部 100% overclaiming**，沒有任何修法解決
      P2-R4 認定最傷的失敗模式。
- [x] texture 措辭配對重驗證（FF++ 447 同源配對）：76.06% 配對中 fake 影格
      紋理低於自己配對的 real 影格（Wilcoxon p=1.67e-27），但按方法異質
      （Deepfakes 87.3%、NeuralTextures 95.3%、**FaceSwap 45.6%~null**）。
- [x] diffuseness 軸檢查：TP/FP 母體上近乎常數（std=0.034，無影像落入
      「集中」tier），TP vs FP AUROC=0.4951——誠實排除，不用於文字條件化。
- [x] 文字生成 fallback（confidence tier × 該圖片實際量測 texture_var，
      不具名任何區域）：entropy 0→1.4796 bits（4 種相異字串），152 對「同源
      real/fake 皆判成 fake」最嚴格配對中 34.87% 文字不同（非常數崩潰、非
      純噪音）。

### 判定
**4 種區域選擇修法全部未通過「可無代價替換現況」的門檻**（Fix A 最佳但仍有
殘留中心偏誤+100% overclaiming；Fix B/C 忠實性失敗；Fix D 無法選擇性棄權）
——`suspicious_regions`/區域宣稱維持現況（`[]`），不接線任何修法。**文字生成
fallback 判定為正向**，已提出 change proposal：
`docs/team/change_proposals/20260822_p2_fake_explanation_text_variation.md`。

> ✅ **2026-08-22 狀態更新（過期修正）**：上一句寫的「PROPOSED，未核准未套用」
> 已過期——該提案 §8 Approval Record 記載已由 Member A 於同日對話中直接核准並
> 套用（"往後此類研究驗證過的修復不再走書面提案流程"），`pipeline.py` 的
> `build_fake_explanation()` 現已是 production 程式碼（套用時發生一次
> `UnboundLocalError` 緊急修復，見 P2-R6 Task A）。P2-R6 的 n=565 大規模
> 再驗證（`results/research/p2_followup_verify_20260822/`）確認套用後的輸出
> 無崩潰、無破損欄位，entropy 在更大樣本（n=242）上仍 >0（1.4011 bits，
> 4 種相異句子）。**本行只更正狀態描述，不代表本輪重新核准或重新評估**。

- [x] ✅ **文字生成 fallback 已套用並經 P2-R6 大規模再驗證，不再是待辦**（見上）。

### 待後續處理
- [ ] Fix A 的因果選區機制若未來要接線，需先解決 overclaiming（100%，本輪
      未解決）與跨竄改方法的差異化訊號缺失（NeuralTextures 未比 Deepfakes/
      FaceSwap 更偏向 mouth/jaw）。
- [ ] Fix D 的棄權門檻只在 FF++（已知 domain gap 較大的母體）測試過，未在
      domain gap 較小的母體上驗證是否仍然無法選擇性棄權。
- [x] ✅ **change proposal 已核准並套用**（見上方過期修正說明）；分類輸出
      逐位元組是否不變本輪未重新驗證（P2-R6 Task A 驗證的是「不崩潰、格式
      正確、entropy>0」，不是「與套用前逐位元組比對」，兩者不同範疇）。
- [x] ✅ **P2-R6 Task C（2026-08-22）已把 EFS vs. swap/reenactment 政策
      與忠實性測試框架正式寫入 `docs/phase2_story.md` 第 13 節**，不再只是
      本輪 results 資料夾裡的一次性產出，見該節與
      `docs/EXPERIMENT_REGISTRY.md`「P2-R6」條目。

## 🔍 Paper-Readiness 稽核執行（2026-08-22）— D2/M3/D1 三項最高優先建議

> 對應 `results/research/paper_readiness_audit_20260822/PAPER_READINESS_AUDIT.md`。
> 完整報告：`results/research/paper_readiness_execution_20260822/EXECUTION_FINDINGS.md`。
> 登錄檔：`docs/EXPERIMENT_REGISTRY.md`「PAPER-READINESS-EXECUTION-20260822」條目。
> 唯讀 `pipeline.py` 與全部 production checkpoint；Task B 有一次真正訓練（spatial-only
> 消融），其餘為量測。未執行任何 git 操作。

- [x] ✅ **Task A：內容金鑰稽核推廣到 True Test/Shadow/FakeClue，發現新的嚴重污染**——
      **`shadow_v2a_filter`（1,152 張）約 99-100% 與 Layer1 現行 production 訓練池內容
      重複**（底圖 `vggface2_train_sample` 被 Layer1 real 類與 P1-R9 SBI fake 來源各用一次），
      嚴重度應比照 StyleGAN2（63.8%）/Alibaba（23.5%）加註 ⚠️ 已更正。`shadow_v2b_filter`
      完全乾淨可替代使用。次要發現：True Test fake 4.07%（11/270）、AIGuard/unseen 0.88%
      （4/454）、FakeClue 2.33%（35/1,503）皆為本輪首次用 Known Trap #3 等級方法查出，
      量級不影響現有結論方向；True Test real/filter、primary Shadow、FF++ frames 完全乾淨。
- [x] ✅ **2026-08-23 DF40 held-out leftover pool（sd2.1/DiT/SiT/ddim/pixart）vs 自己的
      訓練用部分——Task A 原定四個評測集中唯一未完成的一個，本輪補完**：用
      `manifest.tsv` 的 `used_in_training` 欄位直接切出 198 張從未訓練用的 DF40-cdf
      底圖（gate），對比 Layer1 v8.17sbi 與 Layer2 v8.11 實際訓練池（兩者共用同一批
      15,000 張 DF40 圖，已從 split 檔驗證非猜測），沿用 `audit_p1_r11_fullsplit.py`
      原始 fp/dHash/NCC/MAD 程式碼未重寫。**結果：confirmed 2/198（1.01%）、
      confirmed+borderline 9/198（4.55%）——遠低於 shadow_v2a_filter（99%+）/
      StyleGAN2（63.8%）/Alibaba（23.5%），不影響任何既有結論方向**。3組confirmed全為
      跨generator重複（同一段Celeb-DF來源影格被不同diffusion方法各自生成出近乎相同畫面），
      屬DF40-cdf語料本身的性質，非split抽樣bug。完整報告：
      `results/research/df40_taxonomy_followup_20260823/FINDINGS.md`。
- [ ] `shadow_v2a_filter` 需要專案負責人正式決定哪些既有結論（P1-R16/P1-R17/P2-R1）需要
      加註或改用 `shadow_v2b_filter` 重新驗證。
- [x] ✅ **Task B：FFT 分支 spatial-only 消融首次真正執行**（非事後歸零，Layer1/Layer2
      各重訓一次，配方與 production 完全一致，僅移除 `fft_branch`）——**結論：FFT 分支對
      True Test/AIGuard-unseen/Shadow 三個電池的邊際貢獻，95% CI 全部與完整雙分支模型重疊，
      方向不一致（True Test 略降 1.85-2.40pp、filter 打平、AIGuard-unseen/Shadow 反而略升），
      統計上量不出來**。直接回答「保留 FFT 分支換 int8 部署失敗值不值得」：目前證據不支持
      淨精度收益，但樣本數也不足以完全推翻。Spatial-only 消融 checkpoint：
      `checkpoints/research/paper_readiness_execution_20260822/{layer1,layer2}_spatial_only.pth`
      （研究用，不進 production）。
- [ ] 若要把「FFT 分支≈0 貢獻」升級為強結論，需要補資料量對稱的 apples-to-apples 對照
      （本輪消融訓練池比 production 少 3.3%/13.9%，因 `v89d_candidate_pool`/
      `v89d_proxy_unseen_pool` 原始影像已被清理、無法逐檔重現）。
- [ ] spatial-only 消融模型需補跑完整 gate 清單（CelebA/StyleGAN2/Alibaba/FF++/FakeClue/
      TFLite int8 匯出可行性驗證）才能升格為論文可用的「輕量替代方案」提案。
- [x] ✅ **Task C：FF++ 官方 protocol 對比執行，並誠實標註不可完全比較**——本專案的 FF++
      抽樣（900 張，c23 only，每片只取中間 1 幀，`SEED=20260812` 全語料庫隨機抽樣）**不是
      官方 train(720)/val(140)/test(140) 影片 ID split，只能算近似值**，論文正文不可寫成
      「FF++ official protocol」。複用今日既有推論（`v817_scorecard_gapfill_20260821`），
      整理成文獻常見格式：per-method paired-binary accuracy（Deepfakes 60.67%／Face2Face
      50.67%／FaceSwap 55.33%／NeuralTextures 55.78%，平均 55.61%），pooled accuracy
      51.89%（467/900）。搭配 Task A 稽核結果，可誠實聲稱訓練資料與這批 FF++ 幀零內容重疊。
- [ ] 找文獻常見的 FF++ c23 baseline（Xception/SBI/RECCE 等）來對照——本輪刻意不做，
      避免引用未查核數字，留給 D1 後續執行者。
- [ ] 若要讓 FF++ 數字升格為官方可比較，需下載官方 split 影片 ID 清單重新抽樣，並補 c40。


## 🟢 DECIDED｜DANN w015 Layer2 候選（2026-08-23，Member A 裁定：不核准上線）

**背景**：P1-R20/R21（`results/research/p1_r21_dann_strength_sweep_20260822/`）發現
w015（0.5x 域對抗損失強度）是全鏈最一致的正向結果——Shadow +3.82pp，95% CI
[+2.46, +5.18]（真實、不含零），零安全代價，門檻曲線與 S2B 表現全鏈最佳。未達
事先聲明的 +5pp 升版門檻。

**裁定：不核准上線，不再投入運算追這條線。**
- 理由：效果量雖真實但幅度中等（相對 Shadow 基準線 13-20%），Layer2 是安全關鍵
  分類器，本 session 剛發生 artifact_classifier_v4 同日上線又回退的事故，不值得
  為中等效果冒生產風險。
- 候選權重（`checkpoints/research/p1_r21_dann_strength_sweep_20260822/
  layer2_p1_r21_w015_s*_taskonly.pth`）保留在磁碟，供未來若出現新證據或更寬鬆的
  風險容忍度時重新評估，不刪除。
- 這條線（P1-R14→R21，共 8 輪）暫停，不代表結案為失敗——DANN 機制本身已證實
  有真實、零代價的效果，只是幅度不夠；未來若要重啟，建議方向是找出能放大這個
  效果同時不增加安全代價的變體，而不是重複本輪已經掃過的強度範圍。


---

## P2-R7｜Fake 類解釋 v2：三條新路線全部失敗，但查出「哪裡」這題在 FF++ 上幾乎是常數（2026-08-23/24 完成）

> 產出：`results/research/p2_explanation_v2_20260823/FINDINGS.md`、registry 條目 **P2-R7**。
> `pipeline.py` 與全部 production checkpoint 未動，本輪**不提任何 change proposal**。
> 新權重只在 `checkpoints/research/p2_explanation_v2_20260823/`。

### 這輪回答了什麼

- [x] ✅ **K 章節「沒試過受限輸出 VLM」這個開放問題，正式關閉為負面結果**。
      Qwen2-VL-7B 強制選擇 + fp32 two-token logit（**完全不做自由文字生成**）問 8 個
      fake 屬性，在 FF++ 內容控制配對（198 對）與 Celeb-DF（160 對）上跑事前宣告的
      G1–G5 閘門：**兩個語料都是 0/8 可用**。最高 AUROC 0.621（門檻 0.70），且
      **3 個屬性直接卡在分布健康度**（正答率 100.0% / 95.7% / 86.1%）——**yes-bias
      在受限格式下原樣重現**。2 題安慰劑（竄改前後答案不變的問題）落在 0.433–0.506，
      證明量測本身有效。**結論：退化來自任務，不是輸出格式。** 這比 FakeVLM／
      Qwen2-VL 前兩輪的負面結果更強，因為標準緩解手段已經試過並失敗。
- [x] ✅ **首次把 FF++ 官方 mask 當「訓練訊號」而非「驗證基準」**（過去只做 Tier D
      驗證）。真 GT 訓練的 head **贏過 Grad-CAM++**（面積對齊 IoU 0.856 vs 0.774，
      4 個方法一致）——但**輸給 per-method 常數 mask 4/4**（0.888，配對 bootstrap
      95% CI 全部不含 0）。事前門檻 BG1 要求 ≥3/4 → 未過。**P2-R1 的常數 mask 結論
      在一個用真 GT 訓練的 head 上再度重現**：換掉退化標籤解決了標籤問題，沒解決
      「FF++ 竄改區域本身近乎常數」（平均 GT 面積 23.61%）。
- [x] ✅ **本輪唯一的正面突破：第一個「選擇性」棄權機制**。真實配對幀以全零 mask
      一起訓練，給了 head 一個 saliency map 結構上不可能有的「這裡沒東西」通道。
      預測 mask 面積在「真陽性 fake vs 偽陽性 real」上的 AUROC = **0.7397
      （CI [0.702, 0.794]，B1）／0.7682（CI [0.749, 0.838]，B2）**，對照 FIX 輪
      Fix D 的 **0.5402（p=0.1512，不顯著）**。在 val 真實幀 p90 校準的門檻下，
      **偽陽性過度宣稱率 100% → 7.6%**（前五種機制全部是 100%）。跨語料衰減但存活
      （Celeb-DF 0.6368 / 0.6800）。BG3 忠實性兩臂皆過。
      ⚠️ BG2 仍未通過（該門檻下真陽性宣稱率只有 27.7%，事前要求 ≥80%）。
- [x] ✅ **26 個可程式化驗證的屬性：0/26 達到可用門檻**（AUROC ≥ 0.65 且 CI 下界
      > 0.55），最高 0.583；**但 22/26 在 BH 校正後顯著，有的到 p < 1e-90**。
      26 個一起做 logistic 也只有 **in-sample 0.620**、test 0.619 → 不是過擬合、
      不是樣本不足，是**低階統計量在單張層級就是分不開**。

### ⚠️ 需要有人裁定：上線文案的證據基礎要不要在論文裡更正

本輪在更大的獨立 FF++ 樣本上**重現了** FIX 輪的配對紋理效應（`lap_var` 配對符號
一致率 74.2%、BH p = 3.9e-95；FIX 輪是 76.06%、p = 1.7e-27），但同時量到 FIX 輪
沒量的那一半：**同一個屬性的單張影像 AUROC 只有 0.539**。

配對符號一致率回答「**同一張臉**的竄改版比原版平滑嗎」（是，74%）；上線模板做的
是另一件事——「**只給一張圖**，紋理值能不能指示竄改」（幾乎不能）。**該句子措辭
謹慎、沒點名區域、沒造成過度宣稱，因此本輪不要求改 production**，但這是論文
Limitation 必須寫的一條。決策者：Member A。

### 本輪自己犯並修掉的 bug（兩個都屬於「不會報錯但結果是錯的」）

1. **FF++ 檔名慣例不能直接信**。`{a}_{b}` 文件上是 target_source，Deepfakes 成立
   （背景邊框 MAE ≈0.7–1.5），**Face2Face 在本專案這份語料裡不一致**——部分影片
   用不同解析度重新編碼（`005_010` 是 474 幀 @704px，005 是 385 @720px、010 是
   474 @640px），無法與任何來源像素對齊。照慣例配對只活下 3/100 支 Face2Face，
   而且**只要幀數碰巧相同就會把 fake 幀跟不相關的真實幀配成一對且不報錯**。改成
   用量測決定（解析度須相同 + 背景邊框 MAE ≤ 12），逐對 MAE 寫進 index CSV。
2. **`stem` 跨 method 不唯一**（同一支影片 id 會被多個方法竄改）。用 `stem` 當鍵
   把 Approach A 抽樣的 200 對壓成 117 對。三支分析腳本全改用 `(method, stem)`。

### 下一輪建議（可證偽、且不要重做已關閉的東西）

- [x] **把 B 的棄權通道當成獨立目標重做一次**——已完成，見
      `results/research/p2_abstention_20260823/`（P2-R8，2026-08-24）。
      操作點從 27.7%/7.6% 推進到 val 選定、test 確認的約 **61-68% TP / 22-28%
      FP**（4-seed CI 穩定，PG0 可重現性通過）；換讀出統計量（`top10_mean`
      取代 `area05`）是唯一站得住的分離度改善，3 種訓練層級槓桿（loss 加權、
      顯式 gate head、換選模型準則）皆未擊敗 seed 基準。**跨母體測試的關鍵發現
      （非原訂的「不要崩」，而是主動查出偽訊號）**：閘門在 production 主力的
      EFS 母體（DF40 五種擴散法＋MidJourney＋StyleGAN3）表面 AUROC 高達
      0.91，但用三個獨立對照（平凡基線 `p_fake`、跨語料真實照片互測、
      同語料內 real vs fake）逐一拆穿，證明那是**語料指紋混淆**，控制後訊號
      崩到機會水準（AUROC 0.41-0.56）。真正可用範圍收斂到 swap/reenactment
      （FF++／Celeb-DF／DiffusionFace-DiffSwap 三語料，凍結骨幹版在 2/3 上
      通過門檻）。TFLite 四關全過，無 FFT 坑。**上線前提是先解決 §13.3 的
      EFS-vs-swap 推論時路由問題，本輪未解決，仍是開放問題。**
- [ ] **若還要做區域解釋，先換資料**：需要竄改區域會**實質變動**的 fake 語料
      （局部編修 / 局部 inpainting / 部分區域重繪）。在 FF++ 上「哪裡」的答案
      幾乎是常數，任何方法都只能重新發現那個常數——這是本輪的結構性結論。
- [ ] ⛔ **不要再做的**（累計）：自由文字 VLM 蒸餾（3 次）、受限 VLM 屬性標註
      （本輪）、Grad-CAM++ 衍生的區域選擇（4 種）、低階影像統計屬性（本輪 26 個）。

## 📚 DOCS-AUDIT｜`docs/` 全面稽核：staleness/redundancy + limitations_framing.md production/experimental 標籤修復（2026-08-23 完成）

**觸發原因**：專案負責人指出 `docs/limitations_framing.md`（尤其 2026-08-23
新增的 FF++、backbone 比較、棄權閘門段落）把**實驗性/研究用 checkpoint**（從
ImageNet 重新初始化、專門在 FF++ 官方 split 訓練的獨立模型；RepViT 等從未用於
production 的 backbone）的數字和**實際部署的 production checkpoint stack**
（`shufflenet_v2_layer1_v817sbi.pth` + `shufflenet_v2_layer2_v811.pth` +
`artifact_classifier_v6.pth`）的數字混寫在一起，沒有清楚標示讀者容易誤讀成
「production 已經達到這個表現」。

**已完成**：
- [x] 逐段稽核 `docs/limitations_framing.md` 全部 14 節，加上一致的
  **[PRODUCTION]** / **[PRODUCTION-HISTORICAL]** / **[EXPERIMENTAL CANDIDATE,
  NOT DEPLOYED]** 標籤，並在每個「限制被實驗候選證明可修復」的地方明確補上
  「**此限制對現行 production 仍完整成立**」的句子（棄權閘門整節、FF++
  backbone 比較整節是最嚴重的兩處，兩者皆從未寫入 `pipeline.py`）。
- [x] 對同日（2026-08-23）編輯過同類內容的 `docs/paper_draft_zh.md`、
  `docs/paper_outline.md`、`docs/phase1_story.md`、`docs/phase2_story.md`
  套用同一套標籤紀律。
- [x] 對全部 20 份 `docs/*.md` 逐一產出 KEEP-AUTHORITATIVE /
  KEEP-BUT-STALE-NEEDS-UPDATE / ARCHIVE-SUPERSEDED / ARCHIVE-OBSOLETE-PLANNING
  verdict；`docs/work.md`（早期團隊分工 scratch 文件，內容已被 CLAUDE.md/
  TODO.md/schema 文件取代）移至 `archive/docs_archived_20260823/`（含
  README 說明），其餘一律保留在 `docs/`，不確定的（`docs/REORGANIZATION_PLAN.md`
  家族 5 份文件的 production checkpoint 名稱已過時但屬未執行提案不宜擅自archive、
  `docs/研究路線圖：AIGC & Filter Detection 論文發表策略.md` 與
  `docs/paper_outline.md` 定位重疊但角度不同、`docs/RESEARCH_JOURNEY.md`
  停在 v8.13 但是獨立敘事整合非單純重複）列為「留待專案負責人裁定」。
- [x] 額外發現並標註：`docs/README_structured-output.md` 仍寫 schema v2.0.0
  與欄位 `suspicious_region`（單數），但 `pipeline.py` 實際輸出
  `schema_version="2.1.0"` 且欄位是 `suspicious_regions`（複數，第 667 行）——
  這是「文件與 pipeline.py 實際輸出不一致」的又一個具體案例，已在稽核報告中
  標為需要儘快修正（本輪僅標註，未動手改寫該文件內容）。
- [x] 同步在 `docs/dataset.md` 補上一則更正註記：該檔原有的「Celeb-DF-v2 real
  recall=0/200……確認架構限制」一句因果解釋已被 2026-08-23 的 `ffpp_protocol_20260823`
  推翻（見 `docs/limitations_framing.md` 第 2 節），該檔本身仍刻意保留原文
  不改寫（歷史快照），故用附註而非改寫原句處理。

**完整逐檔 verdict 表格、標籤修復明細、已執行的 archive 動作、留待人類裁定清單**：
`results/research/docs_audit_20260823/DOCS_AUDIT.md`。

- [x] 2026-09-07 Backbone 問題結案：MobileNetV4 flat（frontier KEEP，但 stress/Alibaba 不過）＋ hierarchical（6/8 gate 不過）→ KEEP-SHUFFLENET，論文最終版 = v8.17。證據 `results/research/backbone_swap_20260907/`、`backbone_hier_20260907/`。
- [x] 2026-09-07 網頁 demo 補上 evidence head（單檔 ONNX）＋逐字移植 pipeline.py 解釋文字；`docs/demo/` 可直接上 GitHub Pages；`docs/demo/reference_outputs/` 三張圖＋桌機 JSON 供比對。
- [ ] 手機端延遲數字（論文唯一紅色 TODO）：等 GitHub Pages 上線後用手機開 demo 跑 Latency benchmark，把 JSON 貼回。
