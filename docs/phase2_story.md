# Phase 2 論文骨架：從 label degeneracy 到誠實的 XAI 評估方法論

> 這份文件是論文 Methods/Results/Discussion 對應章節的骨架草稿，供撰稿時直接改寫成正式論文文字。數字皆已在 `docs/Dataset 清單.md` 逐版記錄過，此處只做敘事整理。與 `docs/phase1_story.md`（分類器演進）相對應，這裡是可解釋性（explainability/XAI）這條線的完整故事。

## 核心敘事：一個「假設被證偽但過程本身很嚴謹」的研究故事

Phase 2 最初的假設是：分類器能判斷「是什麼」（real/fake/filter），但無法回答「哪裡」（哪個臉部區域被修改），需要一個額外訓練的 region head 來補上定位能力。這條線走了三個主要版本（v1→v3→v4）加上一次系統性的方法對照，最終結論與最初假設相反——但推導過程本身建立了一套可重用的誠實評估方法論（trivial baseline 校正 + 跨指標交叉驗證），這是整條線真正的 contribution。

## 敘事結構（建議段落順序）

### 1. 問題陳述：可信定位解釋的監督訊號從哪來

分類器輸出「filter」判斷後，使用者想知道具體是哪個區域被修改（forehead/eyes/cheeks/...）。Grad-CAM 類方法可以做 post-hoc 定位，但缺乏 ground truth 驗證其定位品質是否可信；訓練一個專門的 region head 需要 region-level 標籤，但這類標籤天然稀缺。

### 2. 方法演進與失敗診斷：v1→v3 的 label degeneracy 故事

- **v1**：用 FakeVLM 生成 pseudo-label 訓練 region head，表面 macro F1=0.842，一度被視為成功。
- **決定性驗證**：計算「完全不看圖、每個 region 永遠猜訓練集多數類別」的 no-image baseline，得到 macro F1=0.732——v1 的 0.842 裡有 87%（0.732/0.842）是 label 退化灌水，真實訊號僅 0.11。查訓練資料發現 6/8 region（forehead/eyes/mouth/jaw）正樣本比例 99.5-100%（近乎常數標籤），只有 cheek 兩個 region 是真正判別任務，但正樣本量在統計上幾乎不可學（3,959 筆記錄中僅 14 筆，0.4%）。
- **v2/v3**：v3 針對「Spatial-Global Mismatch」做架構修正（改用 conv5 pre-pool feature map + geographic window pooling，取代會摧毀空間資訊的 global average pooling），架構修正本身是必要且正確的，但 cheek F1 僅從 0.000 微升到 0.013-0.016，證實瓶頸不在架構，而在 FakeVLM pseudo-label 對 cheek 類別的標註稀疏（模板幾乎不提「臉頰」）。

**這段的方法論價值**：no-image baseline 校正法本身是一個可重用的診斷工具，用來揭穿「看起來不錯的 F1 數字」是否只是 label 分布退化的產物，而非模型真的學到定位能力。

### 3. Landmark GT 的建構與校準：從假設 bug 到發現真實物理限制

放棄 FakeVLM pseudo-label 路線後，改用自建 filter pipeline 本身就有的 before/after 配對資料，計算真實（非模型生成）的 landmark 位移 + LAB 色彩差異作為 ground truth：

- **座標系統 bug**：初版沿用既有 `FACE_REGIONS_PX`（假設臉部緊貼填滿 224×224 畫面），但實際來源圖片並非這樣裁切，導致「forehead」框大部分落在頭髮/背景上。改為以每張圖自己偵測到的人臉 bbox 為基準、用比例定義 region 框，修正了這個真實 bug。
- **純位移訊號不足**：即使幾何形變濾鏡，landmark 最大位移也僅 0.8-1.6px，因為偵測器會「跟著」形變後的特徵重新定位。改用 pixel-level LAB 色彩 diff 作為主要訊號。
- **視覺化推翻「校準 bug」假說**：手動檢視 LAB diff heatmap 疊加 region 框後發現，85-100% 的高 positive rate 不是雜訊/bleed，而是**真實濾鏡物理效應**——whitening/smoothing 的效果天生覆蓋整個臉部橢圓（對應 filter pipeline 的 skin mask 設計）；face_reshaping 則查出 `apply_face_reshaping` 的 warp 半徑是固定 60px 常數（未依人臉尺寸縮放），在資料集尺度上對小尺寸人臉造成近乎全臉的效應溢出，而 `apply_eye_enlarging` 的半徑會隨偵測人臉尺寸自動縮放，這正是 eye_enlarging 能維持清楚 region 區辨力的技術原因。
- **決策**：region-level 8 分類 GT 只對 eye_enlarging 有意義；其餘三種濾鏡改用「whole-face, GT-backed」的較粗粒度 explanation claim，誠實反映這些濾鏡的實際物理效應範圍。

**這段的方法論價值**：三個原訂的 calibration 小實驗（縮框/統計檢定/視覺化）最終只需要視覺化這一步就找到答案——這說明「先便宜診斷、再決定要不要投入複雜修正」的原則本身值得強調：問題有時不是統計精度不夠，而是對「異常」的預期本身就錯了。

### 4. region_head_v4 的驗證：trivial baseline 校正證明真訊號

在 eye_enlarging 子集上重訓 region head（沿用 v3 已修正的架構），得到 macro F1=0.699。單看數字容易誤判進退步，因此比照 v1 的驗證方法論，計算這組標籤分布下的 trivial baseline（forehead/mouth/jaw 三個低正樣本率 region 上，trivial baseline 的 F1 恆為 0）：trivial macro F1=0.607。**實際模型比 trivial 高 0.092**，且關鍵在於 forehead/mouth/jaw 這三個 trivial baseline 拿 0 分的 region，v4 實際達到 0.43-0.48 的 F1——證明模型真的學到辨識這些 region 裡的稀疏正樣本。訊號量級（0.092）與 v1 的真實訊號（0.11）相近，但沒有混入其他近乎常數標籤的 region 去墊高數字。

### 5. 四方法系統性對照與核心發現：反直覺但站得住腳

用 IoU、Pointing Game、IINC 三個指標（`xai_eval_protocol.py`，皆通過 synthetic data self-test；IINC 公式的面積比例正規化問題也在此階段被發現並修正），系統性比較 Grad-CAM++、LRP-approx（InputXGradient 近似）、region_head_v4、pixel-diff baseline（作為有額外資訊的下限參考）：

| 濾鏡 | Grad-CAM++ IoU | region_head IoU | Grad-CAM++ IINC | region_head IINC | Pointing Game |
|---|---|---|---|---|---|
| eye_enlarging | 0.467 | 0.261 | 0.076 | 0.157 | GC 0.820 / RH 0.850 |
| face_reshaping | 0.466 | 0.391 | 0.027 | 0.051 | GC 0.920 / RH 0.920 |
| whitening | 0.448 | 0.280 | 0.017 | 0.089 | GC 0.880 / RH 0.890 |

三種濾鏡類型（300 次獨立比較）一致顯示：Grad-CAM++ 在 IoU 和 IINC 都明顯優於 region_head_v4，region_head_v4 至多打平 Pointing Game。LRP-approx 在所有類型上都是最差方法。**這是結構性發現，不是 eye_enlarging 的偶然結果。**

**核心方法論觀察**：Pointing Game（只檢查峰值是否落在 GT 內）與 IoU（要求整個熱區形狀貼合 GT 邊界）給出完全不同的排名結論——若只報 Pointing Game，會誤導讀者以為 region_head_v4 優於 Grad-CAM++；用更嚴格的 IoU 才揭穿這個誤導。**這個指標選擇如何影響結論的發現，本身就是可以貢獻給 XAI 評估方法論討論的一段。**

### 6. 對論文的定位：Discussion 段落（可直接使用）

> We systematically compared four explanation methods (Grad-CAM++, InputXGradient as an LRP-0 approximation, a purpose-trained region head, and a paired pixel-diff reference) against landmark-displacement ground truth across three filter types (eye_enlarging, face_reshaping, whitening; n=100 each). Contrary to our initial hypothesis that a purpose-trained region head would outperform post-hoc gradient-based methods, Grad-CAM++ consistently achieved higher IoU and lower IINC than the trained region head across all three filter types, with the region head only matching or narrowly exceeding Grad-CAM++ on the coarser Pointing Game metric. This divergence between Pointing Game and IoU is itself methodologically informative: evaluating explanation quality with only a peak-activation metric would have suggested the region head was superior, while the stricter region-overlap metric reveals its activation is less tightly localized than the classifier's own gradient-based attention. We interpret this as evidence that v8.8's backbone already encodes sufficiently discriminative spatial features for these filter operations, such that post-hoc attribution recovers comparable localization quality to a dedicated supervised head — making the additional training cost of a region head difficult to justify for this specific explanation task.

**這條線的 contribution 定位**：不是「我們訓練了一個更好的定位模型」，而是「我們建立了一套誠實的 XAI 評估方法論（no-image/trivial baseline 校正 + 跨指標交叉驗證 + 跨濾鏡類型一致性檢查），並用它得出一個反直覺但經得起檢驗的結論：對這個任務，現有分類器的 post-hoc attention 已經足夠好」。

### 7. `ARTIFACT_REGION_MAP` 的定位：解剖學先驗引導，而非動態定位（2026-08-11 撰寫）

論文必須誠實說明 `pipeline.py` 裡 `ARTIFACT_REGION_MAP` 的性質——它是一張**固定的查表**（eye_enlarging → 雙眼；whitening/smoothing/face_reshaping → whole-face），不是模型逐張推論出來的定位結果。若不說明，讀者容易誤以為 region 是動態預測的。

建議的框定方式（三點，皆有本文既有證據支撐，非事後合理化）：

1. **這是設計決策，不是能力缺口的遮掩**。第 3 節的 LAB diff 量測已證明：whitening/smoothing 的物理效應天生覆蓋整個臉部橢圓（對應 filter pipeline 的 skin mask 設計），face_reshaping 因固定 60px warp 半徑在資料集尺度上同樣飽和。**對這三種操作而言，region-level ground truth 本身就不具區辨力**，因此輸出 whole-face 是對物理事實的忠實反映，輸出更細的 region 反而是虛假精確（false precision）。
2. **粒度隨證據強度而變，而非一律套用**。唯一保留 region-level 的 eye_enlarging，正是唯一具備 region 區辨力的類型（眼睛 97%、嘴巴/下巴僅 17-18%），技術原因也已查明——它的 warp 半徑會隨偵測到的人臉尺寸自動縮放。**「有 GT 支持才給細粒度，沒有就退回粗粒度」本身就是可辯護的方法論立場**。
3. **與 XAI 對照結果的分工要講清楚**。第 5 節顯示 Grad-CAM++ 的定位品質已優於專門訓練的 region head，因此系統的**視覺化定位**交給 Grad-CAM++（動態、逐張），而 `ARTIFACT_REGION_MAP` 只負責**自然語言解釋模板要提哪些部位**（固定、類型層級）。兩者是不同用途，不是重複或互相取代——論文須明確區分，避免讀者把查表誤讀成定位結果。

**可直接使用的英文段落草稿**：

> Our region mapping for filter explanations is a fixed, operation-level anatomical prior rather than a per-image localization output, and we report it as such. This choice follows directly from our ground-truth measurements: pixel-level LAB displacement shows that whitening and smoothing act across the entire facial oval by construction (both are applied through a skin mask), and that face reshaping saturates across most regions at dataset scale because its warp radius is a fixed pixel constant rather than a face-size-adaptive one. For these three operations, region-level ground truth is not discriminative, so emitting specific sub-regions would constitute false precision. We therefore emit whole-face markers for them and reserve region-level claims for eye enlargement, the only operation whose effect remains spatially discriminative at dataset scale (97% positive rate at the eyes versus 17-18% at mouth and jaw), which we trace to its warp radius scaling with detected eye width. Dynamic, per-image localization is handled separately by Grad-CAM++, which our four-method comparison found to localize filter effects more accurately than a purpose-trained region head; the anatomical prior governs only which regions the natural-language template mentions.

### 8. XAI 證據分級架構（Tier A-D，2026-08-13 定案）

前面幾節分別做了 paired GT、region head 對照、faithfulness test、RetouchingFFHQ 稽核，這節把它們收斂成一個單一、可辯護的證據分級表，取代「各種方法散在一起」的狀態。每一筆 `xai_evidence.jsonl`（`build_xai_evidence.py`，見 `docs/xai_evidence_schema.md`）記錄都可以歸到下面四級之一，決定文字解釋能宣稱到什麼強度。

| Tier | 資料來源 | 有 before/after pair？ | Pixel-level GT？ | Faithfulness 可測？ | 可宣稱的文字強度 |
|---|---|---|---|---|---|
| **A** | 自建 filter pipeline（`filter_data/`，`generate_landmark_gt.py`） | ✅ 本專案自己生成，兩邊都有 | ✅ landmark 位移 + LAB diff，逐張計算 | ✅ | 「修改區域與 X 一致」（eye_enlarging 是 region-level；其餘三種是 GT-backed 的 whole-face，見第 7 節） |
| **B** | RetouchingFFHQ 真實 App 輸出（four/megvii/ali） | ❌（2026-08-12 稽核確認：本地無原始 FFHQ 底圖，44,662 張 clean 圖 reliable pair count = 0，見 `results/retouchingffhq_pair_audit_20260812.json`） | ❌ | 理論上可測（尚未對 FFHQ 圖跑過，目前 faithfulness sample 是 filter_data + AIGuard） | 只能做 class/type 層級（filter type 分類、OOD recall），**不可宣稱任何 pixel-level 定位** |
| **C** | 一般 fake（AIGuard、DF40 diffusion/EFS） | ❌ 無官方 mask | ❌ | ✅（2026-08-13 已測，見下） | 只能說「模型主要依賴 X 區域做判斷」的**前提是 explanation 有指名區域**；但目前 `pipeline.py` 對 fake 刻意不輸出 region_claim（見 `pipeline.py` 第 488-501 行註解），所以現行文字停在「偵測到全圖層級異常」（global_only）。faithfulness 測試結果可以支持「若日後要對 fake 補上 attention-based 區域敘述，這個 tier 在方法論上是站得住的」，但目前沒有這樣的輸出 |
| **D** | FF++ 官方 manipulation mask | ✅（3/4 method 已核准，見下方 2026-08-20 更新）| ✅ 有官方 mask，已取用 | ✅ | **Deepfakes/FaceSwap/NeuralTextures 3 個 method 已核准升級為 GT-backed localization 措辭**（`GT_BACKED_LOCALIZATION`，即原提案所稱 Status C）**；證據已於 2026-08-20 對帳到 production checkpoint `v817sbi`，逐 method 雙 checkpoint 數字見下方對帳表**；Face2Face 因 detection gate fake recall 56.7%<60% 門檻（v811d 量測）維持 `DETECTION_INSUFFICIENT_NO_CLAIM`（等同 Tier C，只能 global_only）——**注意：在 v817sbi 下該數字為 68.0%，已過門檻但尚未核准，狀態不變**；FaceShifter 官方無 mask，未評估，維持 Tier C |

**Tier B 的決策**：2026-08-12 稽核發現本地沒有原始 FFHQ 底圖後，決定**不現在下載官方 70K FFHQ 資料集**——不是因為它不重要，而是因為現有的 Tier A（自建 pair）已經能回答「熱圖定位是否合理」，Tier C 的 faithfulness test 已經能回答「熱圖是否影響模型判斷」，兩者合起來已構成完整、可辯護的 XAI 驗證鏈；下載官方 FFHQ 只有在**要把「真實 app 濾鏡的 pixel-level 定位」當論文主貢獻**時才是必要的高成本擴充，目前不是 blocker。RetouchingFFHQ 三批繼續用於現有用途（filter OOD recall eval、filter classifier 訓練資料），只是不能再往上加「定位驗證」這個用途。

**Tier C 的 faithfulness test 結果（2026-08-13，回應「random mask 分數下降 > hot-region mask」的異常發現）**：

第一版 faithfulness test（`xai_faithfulness_test.py`，constant-fill 遮罩，見 `results/xai_faithfulness_v1_20260812.json`）發現一個違反直覺的結果：**scattered random 遮罩造成的分數下降（k20 mean=0.641）大於 Grad-CAM++ 熱區遮罩（k20 mean=0.235）**——標準 deletion test 假設完全相反。診斷：這個模型的 `FFTBranch` 對原始像素做 `torch.fft.fft2`，scattered random 遮罩（大量小面積、硬邊界的 constant-fill patch）會在頻譜裡注入寬頻高頻雜訊，很可能比一塊連續遮罩（即使是熱區）更擾動 FFT branch，與該遮罩是否真的「重要」無關——這是雙分支（spatial+frequency）架構對標準 spatial-CNN faithfulness test 方法論的一個混淆因子。

修正（`xai_faithfulness_blur_test.py`，見 `results/xai_faithfulness_blur_v1_20260813.json`）：把 masking 方法換成**模糊化內容 + 羽化（Gaussian-blur alpha）邊界**（不注入新邊緣），並把 random control 換成**與熱區完全同形狀/同面積、只是隨機平移到別處**的 matched-random（不再是散點），同一批 30 張樣本重跑。**結果：hot_drop > cold_drop 且 hot_drop > matched_random_drop 在 k=5%/10%/20% 全部成立**（hot vs cold margin：+0.108/+0.193/+0.300；hot vs matched-random margin：+0.102/+0.059/+0.106），標準 faithfulness 排序**完全恢復**。這支持（但不證明）第一版的反常結果是 masking 方法本身的頻域混淆因子，不是 Grad-CAM++ 真的不可信。

**這對 Tier C 的意義**：Grad-CAM++ 熱圖在「模型依賴哪裡做判斷」這個意義上是可信的（attention_faithfulness 站得住），但這**不等於**「那裡就是 fake 真正被生成/修改的位置」（仍需 paired GT，Tier C 沒有），所以 `pipeline.py` 現行「fake 只給全圖層級異常敘述、不點名區域」的設計決策**不需要因此改變**——faithfulness 通過只是把「若未來要加 attention-based 區域敘述」這條路的方法論基礎打好，不是現在就要加。

**尚待做（記入 TODO.md，非本節範圍）**：spatial-only ablation（移除 FFT branch 後 masking 排序是否依然穩定）刻意延後——會混入 Phase 1 架構改動與重訓練，跟 Phase 2 的「熱圖驗證」目的不同層次，只有在 blur-based 修正後仍矛盾時才需要動用。目前 blur-based 結果已一致，暫不需要。

**Tier D 正式啟用（2026-08-20 核准）**：change proposal
`docs/team/change_proposals/20260819_fake_xai_status_c_upgrade_ffpp.md`（Reviewer:
Member A，2026-08-20 核准）首次把 FF++ 官方 manipulation mask 真正用起來，完整跑過
Stage 1-5（mask 有效性 → frame-mask 配對 → detection gate → GT-backed
localization → faithfulness 交叉驗證），並加了一輪 Skeptical Review 排除評估
瑕疵。過程中兩次自我修正：① 初版曾用 Pointing Game=1.000 當主要證據，Skeptical
Review 發現該指標對這批資料（trivial 中心點 baseline 拿到相同分數）完全不具
鑑別力，已撤回，只保留 IoU（0.33-0.42，顯著優於隨機）與 faithfulness 交叉驗證
（12/12 組通過，bootstrap 95% CI 不含零）兩條獨立證據鏈 ② 8/19 發現 Stage 3
前處理不一致（未用生產環境的 `preprocess_jpeg(quality=85)` 順序），B2 版重跑後
**Face2Face 的 final fake recall 確認僅 56.7%，低於 60% ELIGIBLE 門檻，從候選
名單移除**，範圍收斂為 Deepfakes（77.3%）/FaceSwap（68.0%，faithfulness 在
top5% 最小遮罩範圍不顯著，claim wording 需限定範圍）/NeuralTextures（72.5%）
3 個 method。**適用範圍限制**（必須隨 claim 一併標註，不可省略）：僅適用於
c23 輕壓縮、PAIRED_OK、且模型本身已正確判斷為 fake 的子集，不代表整個 FF++
母體；mask 覆蓋率偏高（24-31% of face crop），不可直接套用到覆蓋率明顯更小的
操縱類型當通用基準。完整證據見
`results/phase2/ffpp_mask_verified_localization_20260818/`、
`results/phase2/ffpp_mask_verified_localization_B2_20260819/`、
`results/phase2/ffpp_full_set_recall_reconciliation_20260819/`、
`results/phase2/ffpp_gt_localization_eval_20260818/SKEPTICAL_REVIEW.md`。
**本次核准只是政策文件層級（哪些文字被允許輸出），未修改 `pipeline.py`、
checkpoint、threshold、routing 或 preprocessing 本身**——若後續要讓 production
explanation 輸出實際套用這個新措辭，需要另外走一輪 change control。

**⚠️ Checkpoint 標註（2026-08-20 補正，務必連同數字一起引用）**：上一段所有
Stage 3/4/4b 數字（detection recall 77.3/68.0/72.5%、IoU@10%=0.33-0.42、
faithfulness）都是在 **`shufflenet_v2_layer1_v811d.pth`** 選出的子母體上算的。
同日 `shufflenet_v2_layer1_v817sbi.pth` 升為 production Layer1（P1-7），
detection gate recall 全面提升，**代表被部署的系統實際會選出的子母體已經不同
（各 method 多 12-13 支影片）**。因此已對 3 個 method 完整重跑 Stage 4/4b 做
checkpoint 對帳，結果見下表與
`results/phase2/ffpp_v817sbi_reconciliation_20260820/RECONCILIATION_FINDINGS.md`
（決策規則於讀到任何候選數字前先寫死在同資料夾的 `PRE_DECLARED_PROTOCOL.md`）。

**Tier D 逐 method 證據（雙 checkpoint 標註版，2026-08-20 對帳後）**

| Method | Stage3 recall v811d → **v817sbi(production)** | n(子母體) v811d → **v817sbi** | IoU@10% v811d → **v817sbi** | Faithfulness（k=5/10/20%）|
|---|---|---|---|---|
| Deepfakes | 77.3% → **86.0%** | 116 → **129** | 0.4194 → **0.4193**（Δ −0.0001）| 3/3 通過，兩 checkpoint 一致 |
| FaceSwap | 68.0% → **76.0%** | 102 → **114** | 0.3323 → **0.3321**（Δ −0.0002）| **k=5% 不通過**（兩 checkpoint 皆然），k=10/20% 通過 |
| NeuralTextures | 72.5% → **80.5%** | 108 → **120** | 0.3310 → **0.3307**（Δ −0.0003）| 3/3 通過，兩 checkpoint 一致 |

對帳結論：**核准當時的證據在實際部署的 checkpoint 上完全成立，且子母體更大、
detection 基礎更強**。事前宣告的「materially different」門檻為 |ΔIoU@10%| > 0.030；
實測最大偏移 0.0003，低兩個數量級，判為 CONSISTENT（不是「數字更好」，是
「同一結論、n 更大」）。9/9 個 faithfulness 格子 pass/fail 判定完全未變，**沒有
任何指標從「可接受」跨到「需重審」**。控制組（用 v811d 重跑新腳本）與已發表的
B2 數字逐位元完全相同（Δ=0.00000），排除「新腳本重寫錯誤」這個替代解釋。
**FaceSwap 的 k=5% 範圍限定 wording 必須原封保留**——它在 v8.17 下依然不通過
（hot−random CI 下界 −0.0006 → −0.0000，更靠近零但仍未跨過），不得因此放寬。
原核准的全部適用範圍限制（c23 輕壓縮、PAIRED_OK、僅模型已正確判為 fake 的子集、
mask 覆蓋率 23.7-30.4% 偏高）**一併沿用，未擴大任何宣稱**。

> Face2Face 在 v8.17 下 detection recall 升到 68.0%（>60% 門檻）且 Stage 4/4b
> 證據齊備（見 `results/phase2/ffpp_detection_gate_v817sbi_20260820/`），但
> **尚未核准**，需另走一輪 change control；本表與上方 Tier D 表格對 Face2Face
> 的排除狀態維持不變。

### 9. Composite（fake+filter）解釋驗證：P2-1/P2-2（2026-08-13）

延續 Tier A-D 分級，這節把驗證延伸到「一張圖同時是 fake 又疑似套了 filter」的情況——這是 v8.15 dual-head 研究基準（`shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth` + threshold=0.85，尚未過 production gate，見 TODO.md）想要輸出的 `final_class=fake, filter_status=detected/not_confident`。

**P2-1（composite explanation protocol，`phase2_composite_explanation.py`）核心發現**：`fake_filter_hard_neg/`（fake 來源套自建濾鏡的 hard negative）跟 `filter_data/` 一樣有已知的 before/after pair（before 是 `AIGuard/fake` 的原圖），所以 `generate_landmark_gt.py` 的 pair GT 方法**不需要修改，只要把 base_dir 換成 fake 來源**就能沿用——filter 的部分仍是 Tier A（`paired_GT_supported`），即使整張圖最終判 fake。

**⚠️ 報告方式須拆成兩段，不可合併成一句話（2026-08-13 收斂）**：40 張樣本中 filter_status=detected 只有 31 張（77.5%），另外 9 張模型沒偵測到 filter、無從輸出 heatmap/explanation。IoU=0.398、PointingGame=0.774 這兩個數字**只算在那 31 張「模型已經說有 filter」的子集上**，不能直接讀成「fake+filter 的定位 IoU=0.398」，那會蓋掉沒偵測到的 9 張。論文可直接使用的措辭：

> Among the composite samples for which the model detected filter presence, Grad-CAM++ achieved mean IoU 0.398 and Pointing Game 0.774 against the paired filter GT; filter attribute coverage was 77.5% on this diagnostic subset.

同一批樣本的 blur-based faithfulness 卻出現 mean_hot_drop 接近零甚至負值。更精確的機制描述：blur 遮罩不只是「刪除證據」，對 smoothing 這個型別而言，模糊化本身**就是又疊加了一層 smoothing 訊號**——不管遮在熱區或隨機處，都可能讓已經高分飽和的 filter_head 分數持平甚至上升，所以 hot vs cold vs random 的差異被這個訊號注入蓋過了。這代表 blur-based faithfulness 對 filter_head 是錯的遮罩選擇（跟第 8 節 fake_head/Layer1 的結論相反——不同 target class 需要不同的介入方式，不是同一套遮罩對誰都適用）。**更合適但尚未實作的替代方案是 dose-response test**：對同一張 base fake 套遞增強度的 filter（light/medium/heavy），檢查 filter_head 分數是否隨強度單調上升、fake_head 分數是否維持穩定、heatmap 是否逐漸收斂到真正變化的區域——這是用已知可控的真實濾鏡操作做因果測試，而非人工遮罩破壞影像。**刻意不在本輪做**：v8.15-cellC 的 filter head 尚未驗證跨 fake 來源是否泛化（見下），此時精修它的 faithfulness 方法論優先度較低。

**P2-2（filter type accuracy on composites，`phase2_composite_filtertype_accuracy.py`）核心發現**：ground truth 直接來自 `fake_filter_hard_neg/{type}/` 資料夾標籤（免費、精確）。200 張樣本上，`artifact_classifier_v3.pth` 的 type accuracy **在四種濾鏡型別上劣化程度極不均勻**：face_reshaping 92%、smoothing 94% 維持可靠，但 **whitening 崩到 6%、eye_enlarging 掉到 70%**；混淆矩陣顯示 whitening 幾乎全部被誤判成 eye_enlarging 或 face_reshaping，是系統性偏移，不是隨機失準。這直接證實：artifact classifier 只在乾淨 real+filter pair 上驗證過，type 判斷不能直接套用到 fake+filter composite。**決策**：目前 whitening/eye_enlarging 在判定為 fake 的圖上不輸出具體 type，退回 P2-1 的通用「偵測到可能存在後製 filter」措辭；face_reshaping/smoothing 暫時可信。

**⚠️ 範圍限定，不可誇大（2026-08-13 收斂，2026-08-13 二次修正）**：這 92%/94% 是**單一 fake 來源（`AIGuard/fake`）的 in-domain composite type accuracy**，不是「一般化的 fake+filter type recognition」。P2-1/P2-2 本身**完全沒有測試過 DF40 composite**——`fake_filter_hard_neg/` 全部來自 `AIGuard/fake`，兩支腳本與輸出都沒有 DF40/cdf 引用，這點屬實。

**但跨 fake 來源會崩潰這件事本身不是未驗證假說——它是 Phase 1 已經做過、有完整 provenance 的既定事實，只是屬於另一條實驗線，不是 P2-1/P2-2 產生的**。同一顆 v8.15-cellC checkpoint，Phase 1 用獨立建立的 `v815_replication_set`（200 個從未進 training/threshold selection 的全新 **DF40-cdf** 來源，`build_v815_replication_set.py`，`splits/v815_replication_set.tsv` 逐張標記 `used_in_v815_training=False`）測過：joint recognition 56.99%（canonical val）→ **2.02%**（DF40-cdf replication），filter_head AUROC=**0.5304**（幾乎亂猜，whitening_medium 甚至 0.4620，比亂猜還差）。完整記錄與 provenance 見 `TODO.md`「重大修正：C@0.85 的 joint recognition 完全不能跨 fake 來源泛化」條目，以及跨 Phase 統一索引 `docs/EXPERIMENT_REGISTRY.md`（P1-1 條目）。

**這裡曾經發生過一次跨 session 的錯誤歸屬**：對話中一度把這個 Phase 1 P1-1 結果直接寫成「Phase 2 composite explanation 的實驗結果」，事後核對程式碼與輸出後修正——P2-1/P2-2 從未跑過 DF40，它們的 in-domain 數字本身沒錯，錯的是把另一條實驗線的結論誤植到這裡。這正是建立 `docs/EXPERIMENT_REGISTRY.md` 的直接原因：往後任何跨來源/跨 checkpoint 的宣稱，先查登錄檔，避免同樣的誤植再發生一次。

兩者都只是研究基準（v8.15-cellC）上的量測，**不接入 `pipeline.py`**，也不因此觸發任何 production 變更。

### 10. Runtime vs. offline evaluation evidence（2026-08-13，重要區分，避免措辭誤導）

Tier A 的 `paired_gt` claim 容易被誤讀成「系統在正式使用時會拿原圖跟修圖後的圖做比對」——**這不是事實，必須明確澄清**：

- **Runtime（正式推論，`pipeline.py` / `hierarchical_predict()` / `run_single()`）**：模型每次只收到**一張圖**，沒有原圖可用，pipeline 也從未在推論時去抓或比對任何「原圖」。Runtime 能用的證據只有：classifier 機率、filter/type head 預測、單張圖算出來的 Grad-CAM++ heatmap、以及查表得到的 evidence tier。
- **Offline evaluation（`generate_landmark_gt.py`、`xai_eval_protocol.py`、`phase2_composite_explanation.py`）**：研究者用已知的 before/after pair（`filter_data/`、`fake_filter_hard_neg/`）**離線、一次性**算出 GT，檢查「跟 production 會產生的同一種單張圖 heatmap」是否落在 pair GT 標出的真正變化區域。這個 pair 比對只發生在評估腳本裡，從未進入 model 的 `forward()`，也不會對使用者送進來的圖（本來就沒有已知原圖）做比對。

`paired_gt` tier 的意思是「這個 claim 背後有離線驗證過的證據支持」，不是「這次推論做了比對」。可用/不可用措辭對照：
- ✅「模型主要依賴雙眼附近的影像特徵做出判斷。」（runtime 證據：單張圖的 Grad-CAM++ + faithfulness）
- ✅「在可取得配對資料的離線驗證中，這類 filter 的變化通常集中於雙眼附近。」（offline 證據：`results/xai_filter_localization_results_v1_20260812.csv`）
- ❌「系統透過比較原圖與修圖後圖片發現……」「模型與原圖比較後確認……」——這句話錯誤描述了 runtime 行為，正式推論時沒有原圖可比對。

已核對 `pipeline.py` 現有 `TEMPLATES`（"detected"／"consistent with"／"identified" 等措辭）本來就沒有這個問題，不需要修改；本節只是把界線寫清楚，避免未來（包含任何 VLM 改寫 `build_explanation()` 的版本）不小心寫出違反這個界線的句子。完整版見 `docs/xai_evidence_schema.md`「Runtime evidence vs. offline evaluation evidence」章節。

### 11. Phase 2 現況（2026-08-13 定案，2026-08-13 收斂為鎖定版）

**已完成**：
- Tier A paired-filter GT 框架（`generate_landmark_gt.py` + real+filter、fake+filter 兩種來源）
- Grad-CAM++ vs region head 系統性對照（v8.8，第 5 節）+ production v8.11 重跑驗證（第 12 節）
- production hierarchical 模型的 faithfulness test（blur + matched-random control）
- RetouchingFFHQ 本地無原圖的稽核
- evidence schema／JSONL／跨 Phase 實驗登錄檔（`docs/EXPERIMENT_REGISTRY.md`）
- AIGuard fake+filter in-domain composite explanation pilot（P2-C1/P2-C2）

**Filter XAI evidence-tier 規則（鎖定版，按 filter type 分級，依據 `docs/EXPERIMENT_REGISTRY.md` P2-P0 條目）**：

| Filter type | Evidence tier | 可宣稱的文字強度 |
|---|---|---|
| eye_enlarging | Tier A，region-level GT-backed | 可指名具體區域（雙眼），定位品質在 production 上持平或優於舊版 |
| face_reshaping | Tier A，whole-face／有限定位支持 | 全臉敘述，不做超出 whole-face 的精確主張，定位品質在 production 上持平或更好 |
| whitening | Tier A，whole-face GT-backed，**不用峰值做精確局部主張** | 全臉敘述；已知 production 上 Grad-CAM++ 峰值定位不穩（PointingGame 0.880→0.357），因此絕對不能把「熱圖最亮點」讀成精確修改位置 |
| smoothing | Tier A，whole-face GT-backed，**不用峰值做精確局部主張** | 全臉敘述；理由同 whitening，且濾鏡本身物理效應就是全臉，熱區精確度本來就沒有意義（第 7 節） |

**Fake region-level 定位：正式標記為 pending，不是暫停也不是放棄**：
- **現況**：只能 global-level explanation（全域紋理/頻率異常敘述），不做任何 region claim。
- **卡住的原因**：缺乏可信的 fake manipulation mask——目前訓練來源（AIGuard、DF40 diffusion/EFS）沒有官方 mask；FF++ 有官方 mask（Deepfakes/Face2Face/FaceSwap/NeuralTextures）但目前未下載、未訓練。
- **解除條件**：① 取得 FF++ masks，② Layer1 對 FF++ 來源要先有基本辨識能力（見 `docs/EXPERIMENT_REGISTRY.md` 的 Phase 1 stretch goal「FF++ fake recall ≥70%」，目前未達）。這兩個條件都不成立前，`pending` 狀態不變。
- **這不是空白狀態**：Fake+Filter 組合圖的 filter 部分已經可以用 Tier A（見 P2-C1），fake 部分維持 global-level——兩者分開陳述，不互相拖累。

**目前不可宣稱**：
- 跨來源（非 AIGuard）的 fake+filter filter attribution（見 `docs/EXPERIMENT_REGISTRY.md` P1-1/P1-2：v8.16 校準後跨來源 joint recognition 僅 4.53%，5/9 型別/方法組合完全零轉移）
- 跨來源 fake+filter filter type recognition
- 一般 GAN/diffusion fake 的 region-level 定位（見上，pending）
- 真實 app 濾鏡的 pixel-level 定位 GT（Tier B，見第 8 節）
- VLM 產生的文字當 ground truth

**暫停，不主動開始**：新 region head 訓練、FakeVLM 訓練、VLM 自由生成 explanation、下載官方 FFHQ 資料集、Phase 2 新模型架構。

**下一步先準備、不執行**：source-stratified composite explanation adapter（AIGuard fake / DF40-ff / DF40-cdf frozen replication 分開報告 coverage、filter-head AUROC、type accuracy、conditional 定位指標、faithfulness），見 `phase2_source_stratified_eval_adapter.py`——**尚未執行**，等 Phase 1 產出並完成 gate 驗收的 v8.16 checkpoint 後才跑。

**⚠️ 2026-08-13 發現一個尚未驗證的產出物，記錄但不採用**：磁碟上已出現 `shufflenet_v2_layer2_v816_mixedlineage.pth`（連同 `splits/v816_manifest.tsv`，16,145 筆，`build_v816_manifest.py` 已跑過），時間戳是本節撰寫當下才剛產生，推測是平行的 Phase 1 session 訓練出來的。**這不構成「v8.16 checkpoint 已就緒」**——`TODO.md` 目前沒有任何對應的訓練記錄、canonical val 或 DF40-cdf frozen replication 的 gate 數字，比照本專案一貫的 checkpoint 驗收紀律（v8.11 上線前跑滿 7 項 gate 才拍板），一個檔案出現不等於它已通過驗證。Phase 2 在 Phase 1 正式記錄這顆 checkpoint 的驗收結果之前，不會拿它跑任何新的 XAI 宣稱。

### 12. Priority 0：重新驗證 production v8.11 的 filter Grad-CAM++（2026-08-13）

第 5 節「Grad-CAM++ 優於 region_head_v4」的結論，是在 `shufflenet_v2_3class_v88.pth`（v8.8 舊版單一 3-class 模型）上量測出來的，**不是**目前 production 的 v8.11 hierarchical（Layer1 real/manipulated + Layer2 fake/filter）。架構不同、決策邊界不同，熱圖不能自動假設一樣好。`phase2_p0_v811_filter_gradcam_validation.py` 用同一套 `generate_landmark_gt.py` paired GT，直接對 production checkpoint（`shufflenet_v2_layer1_v811d.pth` + `shufflenet_v2_layer2_v811.pth`）重跑一次，四種濾鏡類型各 100 張。

**三段式拆解**（避免把「根本沒判到 filter」跟「判到 filter 但熱圖看錯位置」混在一起）：

| 濾鏡類型 | Layer1 routing | Layer2 favor filter | **最終 filter 準確率** | 定位樣本數（conditional）|
|---|---:|---:|---:|---:|
| eye_enlarging | 85.0% | 96.0% | 81.0% | 81 |
| face_reshaping | 96.0% | 97.0% | 94.0% | 94 |
| whitening | 86.9% | 98.0% | 84.9% | 84 |
| smoothing | 100.0% | 100.0% | 100.0% | 98 |

**定位品質（conditional on 最終判成 filter，跟 v8.8 舊結果並列）**：

| 濾鏡類型 | v8.8 IoU | **v8.11 IoU** | Δ | v8.8 PointingGame | **v8.11 PointingGame** | Δ |
|---|---:|---:|---:|---:|---:|---:|
| eye_enlarging | 0.467 | **0.549** | **+0.082** | 0.820 | 0.864 | +0.044 |
| face_reshaping | 0.466 | **0.516** | **+0.050** | 0.920 | 0.915 | −0.005 |
| whitening | 0.448 | 0.372 | −0.076 | 0.880 | **0.357** | **−0.523** |
| smoothing | — | 0.398 | n/a（v8.8 study 未測 smoothing 的 gradcam） | — | 0.296 | n/a |

**結論**：eye_enlarging、face_reshaping 在 v8.11 上定位品質**持平或更好**，Grad-CAM++ 優於 region head 的結論可以合理延伸到 production。**whitening 是例外，且問題明確**：IoU 只小幅下降（熱圖形狀大致還蓋到 GT），但 PointingGame 崩到 0.357（從 0.880）——代表熱圖最亮的單一像素，經常落在 GT 正例區域之外，即使整體熱區形狀還算合理。這跟 IoU 沒有同步崩潰，說明不是「熱圖整個看錯地方」，比較像是「峰值位置不穩定」。**這是 v8.11 specific 的新發現，v8.8 沒有這個問題，需要在論文誠實揭露，不能只延用第 5 節的結論**。coverage 面也看到同樣的訊號：whitening 的 Layer1 routing coverage 是四類最低（86.9%），與 v8.11 已知的「real recall 偏低、filter 容易被 Layer1 誤判成 real」模式一致（見 `TODO.md` Shadow/True Test 相關章節）。smoothing 雖然 coverage 100%（模型很有信心），但 IoU/PointingGame 兩項定位數字都偏低（0.398/0.296），與其 GT 本身是 whole-face（見第 7 節，smoothing 的物理效應覆蓋幾乎全臉）一致——熱區形狀的「精確度」對這種本來就沒有局部邊界的濾鏡意義有限，這點延續第 7 節「whole-face GT 不具區辨力」的既有判斷，不是新問題。

**✅ 2026-08-13 whitening 診斷已完成（原列為可延後，撿起來做了），找到明確、具體的根因**：`phase2_whitening_pointinggame_diagnostic.py`，對 20 張 whitening PointingGame==0 失敗案例逐張重跑，取 Grad-CAM++ 熱圖峰值座標，分類落在人臉 bbox 內／外、8 個命名 region box 內／間隙。**結果比原先設計要區分的兩種情境都更明確**：20 張中 **17 張（85%）的峰值座標落在同一個絕對像素點（224×224 標準化座標系的 (80,111)）3px 範圍內**——不管人臉在畫面中實際位置、縮放、髮型、眼鏡、背景為何，峰值幾乎釘死在同一點（`results/phase2_whitening_peak_diagnostic_20260813/contact_sheet.png` 目視確認）。這不是「GT/preprocessing 對齊 bug」（峰值確實在臉內），也不是「峰值落在合理但不精確的位置」（真正圖片內容驅動的定位應該會隨人臉位置移動），而是**峰值定位被一個近乎常數的位置偏誤主導，跟圖片內容無關**。

**這個發現強化（而非削弱）現行 whitening whole-face、不做精確定位主張的政策**：一個不隨圖片內容變化的熱圖峰值，本來就不該被讀成「指向了什麼」，現行政策的假設完全正確，不需要調整措辭或修正模型。本次任務性質是診斷不是修復，未嘗試找出造成這個位置偏誤的架構層原因（例如是否跟 FFT branch 有關），留待未來若有需要再深入。完整記錄見 `docs/EXPERIMENT_REGISTRY.md` P2-P0 條目的 follow-up 段落，輸出在 `results/phase2_whitening_peak_diagnostic_20260813/`（contact sheet、逐張 CSV、summary.json）。

完整輸出：`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`（含逐型別 summary、逐張 per_image、與 v8.8 study 的 delta table）。

**Phase 2 現況一句話總結（2026-08-13）**：Phase 2 現在已經能對 production v8.11 的 filter 解釋做「按 filter type 分級」的誠實主張——眼睛放大（eye_enlarging）較可信、瘦臉（face_reshaping）可做全臉解釋，美白（whitening）與磨皮（smoothing）不能把熱圖峰值當作精確修改位置。Fake XAI 尚未完成 region-level GT 驗證；Fake+Filter XAI 只有 AIGuard in-domain 的初步 paired GT 結果，跨來源仍要等 v8.16 通過驗收。文字輸出現在可以依 evidence tier 安全產生，但不該進入 VLM 自由生成階段。

## 待補（撰稿階段處理，非本節範圍）

- [ ] LAB diff heatmap 視覺化範例圖（`results/lab_diff_bleed_viz/`）選 2-4 張代表性樣本放入論文 Figure
- [ ] v1 no-image baseline 與 v4 trivial baseline 的對照圖表，視覺化呈現兩次校正的一致方法論
- [ ] 四方法 IoU/PG/IINC 對照表轉為正式論文 Table，含 face_reshaping/whitening 的「region_head_v4 未訓練於此類型」註記
- [ ] Filter 解釋性論文 claim 兩級粒度文字（region-level for eye_enlarging；whole-face for 其餘三種）與此節整合，避免正文重複
