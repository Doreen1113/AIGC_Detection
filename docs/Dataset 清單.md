# Dataset 清單

> 最後更新：2026-08-10（**v8.11 Layer1d + 原始Layer2 hierarchical分類器為目前production版本，`pipeline.py` 已指向 Layer1d**。v8.8為舊flat 3-class架構的最佳版，已被hierarchical架構取代，保留為reference baseline。v8.11演進：Layer1c（2026-08-02拍板）→ Layer1d（2026-08-10，round4 hard-neg fine-tune後取代）。完整過程見下方及`TODO.md`。）

---

## 🔴 2026-08-11 三項重大發現：邊緣部署 blocker 解除、兩個 filter benchmark 的配對設計問題、Shadow 域泛化根因查清

### 1. ✅ 邊緣部署 blocker 解除（原本整個「可部署到手機」主張是不成立的）

`FFTBranch` 的 `torch.fft.fft2`/`fftshift` 轉 TFLite 後是無法解析的 custom op（`ONNX_DFT`），檔案轉得出來但**標準 runtime 載入直接失敗**。改用固定尺寸 DFT ⇒ 常數矩陣乘法（`mobile_fft.py`），`fftshift` 摺入常數矩陣，全程只用 TFLite builtin op。**數學等價、零重訓**。

| 產出物 | 載入 | 大小 | CPU 延遲 | True Test filter/real/fake |
|---|---|---:|---:|---|
| PyTorch fp32（參考） | — | — | — | 93.6% / 68.4% / 99.6% |
| **TFLite fp32** | ✅ | **20.91 MB** | **14.4 ms/張** | **完全相同，769/769 決策逐張一致** |
| TFLite fp16 | ❌ | 10.5 MB | — | 整圖 fp16，stock CPU kernel 拒絕，需 GPU delegate |
| TFLite int8 | ⚠️ 輸出 NaN | 6.74 MB | 614 ms | 模型失效 |

**int8 失效根因（過程中推翻自己的第一個假設）**：先假設是 DFT 常數矩陣量化受損，實測**被推翻**（量化 DFT 常數只造成 0/30 決策翻轉）。真因是 **activation 量化**——FFT magnitude 動態範圍 **7.6×10⁹**，per-tensor int8 步長 1.187 把 **98.08% 頻譜 bin 壓成 0**，誤差是權重量化的 813 倍。**這是把原始 FFT 頻譜放進量化圖的本質限制**，非工具 bug。

### 2. ⚠️ True Test 與 Shadow 都是配對設計，單邊 filter recall 不可作為偵測能力證據

`audit_truetest_pairing.py` 查出 True Test 的 249 張 filter 圖**100% 是 real 那 250 張的同源濾鏡版本**；Shadow 同樣（279 對，清洗後）。**資料本身乾淨**（photo-level 洩漏 0/250、0/249，三份 filter split 都查過；身份層級 39.1% 重疊屬既知較弱 confound），問題純在報告方式——**永遠回答 filter 的退化模型在 True Test 上 filter recall 會是 100%，照樣過 ≥92% gate**。

| 測試集（同一套自建濾鏡演算法） | 配對數 | balanced | strict | filter rec | real rec |
|---|---:|---:|---:|---:|---:|
| True Test（LFW 底圖） | 249 | 81.1% | 62.2% | 93.6% | 68.7% |
| Shadow（VGGFace2 底圖） | **279** | **43.5%** | **7.2%** | **10.0%** | **77.1%** |
| 退化基線 | — | 50.0% | 0% | — | — |

> ⚠️ **Shadow 一列於 2026-08-11 修正一次**：初版誤用**未清洗**的 `shadow_*/` 原始資料夾（472 對），官方評測腳本實際讀的是 `clean_output/clean_paths.txt`（279 對）。**修正後 real recall 77.1% 與文件既有的 76.9% 吻合**，證實現在用的是正確集合。

錯誤方向完全相反：True Test 是 filter-biased（31.3% 乾淨照被判 manipulated）、Shadow 是 real-biased（61.4% 濾鏡照被判 real + 25.2% 兩張都錯）。**Shadow balanced 41.4% 低於退化基線 = 反資訊**，比原本文件記的「recall 卡在 15-28%」嚴重。

**副效果**：Layer1c→Layer1d 的決策在修正指標下**更站得住腳**（balanced 80.5%→81.1%、strict 61.0%→62.2%，兩項都贏；原本只看 filter recall 時 Layer1d 看似小輸 0.4pp）。

### 3. ✅ Shadow 域泛化根因查清：兩個平凡解釋都被實測排除

| 假設 | 檢驗 | 結果 |
|---|---|---|
| 濾鏡效果太弱／沒套上 | LAB ΔE 配對量測（全量 279 對、清洗後，per-type 比值） | **排除**：Shadow 四種類型**全部更強**（1.15–2.15x，平均 1.46x），改動像素 46.0% vs 36.2% |
| 生成幾何尺度不同（固定 60px 半徑） | 量測各來源影像尺寸／人臉佔比／換算到 224 的等效半徑 | **排除**：VGGFace2 等效半徑 45.9px，落在訓練來源區間內（LFW 53.8、AIGuard 52.5） |
| JPEG 寫出品質不同 | 比對生成腳本 | **排除**：LFW 與 VGGFace2 filter 皆 q90，同一段程式碼 |

> 過程備註：ΔE 首次量測時樣本上限設 250 對，在取到任何 whitening 之前就截斷，整體比值被型別組成帶偏；已改全量 + per-type 比值。
> 附帶查到一項小不一致：`filters/generate_filter_dataset.py` 的 `cv2.imwrite` 未指定品質參數（OpenCV 預設 95），與其餘生成腳本的 q90 不同；因 True Test 與 Shadow 兩邊同為 q90，不影響上述結論，但記錄備查。

**結論：跨濾鏡演算法泛化良好（Alibaba OOD 98.1%，不同公司演算法），跨底圖攝影風格泛化失敗。** 現有 filter 訓練底圖（FFHQ / LFW / AIGuard-real）全是對齊裁切的一致構圖；唯一 in-the-wild 的 VGGFace2 就是失敗的那個（landmark 偵測成功率 82% vs 其餘 100%，直接反映難度差異）。

### 3b. ✅ 因果驗證：v8.12（底圖多樣性）確認診斷正確，但有代價，暫不上 production

對 **IMDB-WIKI**（唯一與 VGGFace2 難度相近、且原本 filter class 完全沒有的 in-the-wild 底圖來源）套用**完全相同**的自建濾鏡函式生成 6,000 張，**同時**加入 Layer1（manipulated）與 Layer2（filter）——因診斷顯示 Shadow filter 損失為 55% Layer1 / 45% Layer2。VGGFace2/Shadow 完全未動仍為 held-out。

| 指標 | v8.11 | **v8.12** | Δ |
|---|---:|---:|---|
| **Shadow balanced accuracy** | 43.5% | **55.7%** | **+12.2pp，首次越過 50% 退化基線** |
| Shadow strict per-pair | 7.2% | 24.0% | +16.8pp（3.3 倍）|
| Shadow filter recall | 10.0% | 38.4% | +28.4pp |
| Shadow real→fake（誤指控） | 19.0% | 16.5% | 改善 |
| True Test balanced | 81.1% | 80.5% | −0.6pp |
| True Test filter recall | 93.6% | 94.0% | +0.4pp |
| AIGuard/unseen AUROC / CelebA / StyleGAN2 | 0.8150 / 99.7% / 99.6% | 0.8136 / 99.6% / 99.6% | 雜訊範圍 |
| **fake+filter 端到端誤判** | **3.71%** | **5.29%** | **❌ +1.58pp** |

**僅新增佔 Layer1 訓練集 2.5% 的不同底圖來源樣本，就讓完全 held-out 的域從「反資訊」變成「有資訊」**——證明失效主因是底圖來源多樣性不足，不是濾鏡特徵難學。

**代價與收益同源（機制清楚）**：退步集中在 smoothing（0.7%→2.1~3.5%）與 combined，正是 Shadow 上進步最大的類型（smoothing strict 4.8%→**54.0%**）；whitening/eye_enlarging 反而略有改善。「更願意判 filter」同時救回真實濾鏡、也讓 fake+平滑濾鏡更易被判成 filter。

**決策：維持 v8.11 為 production**（fake+filter 是安全性相關且已未達標的 gate，不宜再退 1.58pp；Shadow 55.7% 也尚未到可宣稱解決）。v8.12 的價值是**證明診斷正確並指出下一步**。下一步 v8.13：沿用 v8.12 資料，另針對 wild 底圖生成 fake+filter hard negative 直接對沖退步類型。

**⚠️ 撰稿注意**：IMDB-WIKI 與 VGGFace2 同屬 in-the-wild 名人攝影，是可取得的最接近代理，**本實驗證明的是「從相近 wild 域遷移有效」，不等於對任意新底圖分布都成立**。

### 4. ❌ Phase 3 P3-M0 filter teacher 路線正式關閉（token-logit 版也失敗）

`run_teacher_filter_logit.py`：30 張來源照片 × 5 狀態（乾淨 + 4 濾鏡）× 4 類型專屬問題 = 600 次 fp32 token-logit 推論，**內容控制設計**（同一張臉比較）。逐類型偵測 AUROC：smoothing 0.703、whitening 0.500、eye_enlarging 0.529、face_reshaping 0.489（對照 fake_prompt 同法 0.804）。**specificity 矩陣顯示 smoothing 那一欄推高了全部四個問題**——模型只察覺「被動過」，不知道「被套哪一種」，對 attribute-level 標註致命。

**由此修訂 Phase 3 監督策略為混合監督**：filter attributes 改用**程式化 GT**（自建 pipeline 有 before/after 配對，Phase 2 已驗證 LAB diff / landmark 位移可靠），VLM teacher **只用於 fake**（唯一有訊號處，AUROC 0.804 / 校準後 73.3%）。這不是退而求其次，而是讓每種監督訊號用在它可靠的地方，且兩邊可靠度都有量化證據。

---

## ✅ 2026-08-10 Layer1d取代Layer1c，完整成績單重新驗證＋FFHQ_four_process OOD審計

**Layer1d rollout**：round4挖到383張全新來源hard-neg（`AIGuard/fake`未用過的圖，套whitening/eye_enlarging/face_reshaping後用Layer1c評分篩選P(real)≥0.35），從Layer1c checkpoint繼續fine-tune 5 epochs（`AIGuard/train_v811_layer1d.py`）。完整7項gate（明確指定`shufflenet_v2_layer1_v811d.pth`+`shufflenet_v2_layer2_v811.pth`跑出，非沿用舊數字）：

| 測試來源 | Layer1c | Layer1d | Gate | 判定 |
|---|---:|---:|---|---|
| True Test filter recall（總） | 94.0% | 93.6% | ≥92% | ✅ 過關（打平內雜訊範圍）|
| ├ smoothing / whitening / eye_enlarging / face_reshaping | — | 100.0% / 95.2% / 82.3% / 96.8% | — | eye_enlarging最弱，跟其他來源同型別偏弱方向一致 |
| Alibaba OOD filter recall（21,151張，index-disjoint演算法OOD） | 97.8% | **98.1%** | — | 略升，非退步 |
| AIGuard/unseen fake AUROC | 0.8112 | 0.8150 | ≥0.70 | ✅ 過關，更好 |
| CelebA real recall (n=3000) | 99.7% | 99.7% | ≥95% | ✅ 打平 |
| StyleGAN2 fake recall (n=3000) | 99.7% | 99.6% | ≥95% | ✅ 過關 |
| Shadow real recall | 75.5% | 76.9% | ≥80% | 未過但持續逼近（+1.4pp）|
| fake+filter端到端誤判 | 4.06% | 3.71% | ≤2% | 未過但持續改善 |

**沒有任何一項退步超過雜訊範圍，判定為淨正向改善，已正式取代Layer1c成為production Layer1**（`pipeline.py`的`LAYER1_WEIGHTS_PATH`已指向`shufflenet_v2_layer1_v811d.pth`，Layer1c保留在磁碟供對照）。

**Filter recall跨來源對照，證實Shadow低是domain gap而非模型普遍弱**：True Test（93.6%）與Alibaba OOD（98.1%）都是93%+高分，且用的是完全不同的濾鏡演算法（自建pipeline vs Alibaba API）跟不同底圖來源，唯獨Shadow set（VGGFace2真人照片+自建filter pipeline）卡在15.7-28.1%。同一套自建filter pipeline在True Test（LFW底圖）拿93.6%、在Shadow（VGGFace2底圖）只拿51.2%（Layer1 isolated的filter→manipulated recall），差異只在底圖照片風格——問題定位在模型對VGGFace2這種「野生」照片風格的泛化能力，不是濾鏡辨識力本身。

**❌ FFHQ_four_process 859張未用圖片審計失敗，不可用作新filter OOD來源**：依序審計路徑/身份重疊 → 演算法重疊，兩關都沒過：
1. `FFHQ_four_process`（無品牌）與已訓練的`FFHQ_megvii_four_process`（Megvii）共用**完全相同**的FFHQ base index range（60002-69999），不像Alibaba（17000-19999）是獨立不重疊的company分區——這兩個資料夾是同一批10K張FFHQ底圖，各自套用不同濾鏡pipeline。
2. 859張未用圖片中，**727張（84.6%）的base FFHQ index已透過megvii版本用進`v811_layer2_train.txt`訓練**，即同一張人臉照片訓練時已見過（濾鏡演算法不同），不構成identity-disjoint OOD。
3. 剩餘132張即使身份未撞，套用的仍是`v86_train_filter.txt`裡6,872張同源訓練資料用過的同一套「four」濾鏡演算法，樣本量小、演算法不新，不足以構成獨立OOD benchmark。

**判定：不採用此資料源做inference、不因此觸發round5挖礦**。稽核腳本：`check_ffhq_four_process_overlap.py`（未用清單）、`check_ffhq_four_identity_overlap.py`（身份重疊比對）。目前唯一驗證過的乾淨filter algorithm-OOD只有Alibaba一組。

---

## ⚠️ 2026-08-10 Phase 1 全面健檢：查出並修正2個資料品質問題，1個措辭精確度問題

**問題1（已修正）：`stress_test_v811_pipeline.json` 是用已淘汰的Layer2c權重跑的，不是最終版**——檔案時間戳（Aug 2 01:10）落在Layer2c訓練完成（00:52）之後、拍板改回原始Layer2之前，該檔案從未在最終決策後重新用正確權重跑過。舊檔案算出的端到端誤判率4.33%，精確吻合文件裡記錄的「Layer2c誤判4.33%，比原始差」——同一組數字被誤植成「v8.11最終版最新壓力測試結果」，之前的fake+filter誤判方向分析（whitening/eye_enlarging/face_reshaping誤判集中）就是建立在這份錯誤資料上。**已用明確指定的最終權重（`shufflenet_v2_layer1_v811c.pth`+`shufflenet_v2_layer2_v811.pth`）重新執行`AIGuard/stress_test_v811_pipeline.py`**：修正後端到端誤判率93/2289=**4.06%**（原記錄3.93%，差0.13pp，雜訊範圍內可接受）；per-filter-type質性結論不變（whitening 13.2%/eye_enlarging 10.1%/face_reshaping 8.7%最差，誤判方向仍集中real；smoothing/combined系列<1.1%很穩）。相關圖表`fake_filter_misclass.png`與`TODO.md`裡Irene任務二的數字已同步修正。**教訓：任何"重新產生的評測檔案"在模型版本反覆迭代/回退的專案裡都要核對檔案時間戳與當時實際載入的權重，不能只看檔名。**

**問題2（已確認，影響極小）：`pipeline.py`的`hierarchical_predict()`與`eval_v811_gates.py`的`predict()`，判斷real/manipulated的決策規則數學上不保證一致**——`eval_v811_gates.py`嚴格先看Layer1自己的二分類argmax，Layer1說manipulated才進Layer2；`pipeline.py`則是算出P(real)/P(fake)/P(filter)三個複合機率後直接三選一argmax。因為P(real)可能小於P(manipulated)=P(fake)+P(filter)的總和（Layer1判manipulated），但拆開後P(real)卻可能同時大於P(fake)和P(filter)個別的數值（兩個被拆分的機率各自變小），這種邊界情況下兩個函式會給出不同判斷。**實測**（True Test set，769張）：769張裡只有1張（0.13%）兩種決策規則給出不同結果（`lfw/Rudolph_Giuliani/Rudolph_Giuliani_0024.jpg`，L1機率[0.487,0.513]非常接近決策邊界）。**結論：問題真實存在，但實際影響可忽略**，現有gate數字（True Test filter recall 94.0%等）不需要因此重新計算，但如果之後要嚴謹地寫進論文方法論章節，應該誠實註明這個理論上的不一致與其實測發生率。

**問題3（措辭精確度，非bug）：`eval_df40_benchmark.py`「從未訓練過的leftover pool」宣稱的範圍，只精確到v8.11自己的血緣（v8.5→v8.8→v8.10a→v8.11），沒有涵蓋v8.1-v8.4這些更早期、已棄用版本用過的DF40圖片**——實測v81-v84的split檔案裡，各有約3,653張DF40圖片不在`eval_df40_benchmark.py`的排除清單（`v85/v88/v810a_train_real_fake.txt`）裡。這些圖片v8.11本身從未看過，不影響v8.11的DF40 sanity check有效性，但如果論文文字寫成「never used anywhere in this project」而非更精確的「not used in v8.11's training lineage」，會是精確度上的overclaim。**建議**：論文措辭改成明確限定「相對v8.11訓練血緣的held-out pool」，不要泛稱「整個專案史上都沒用過」。

**健檢過程中確認沒問題的部分**：CelebA/StyleGAN2 gate數字用`random.shuffle`+`[:3000]`子抽樣（非全量19,962/10,000張），抽樣邏輯正確、`random.seed(42)`可重現，數字本身已在print陳述裡誠實標註是subsample，非隱藏資訊。

**尚未測試的robustness面向（找遍全專案，確認完全沒有對應腳本）**：姿態角度（非正臉）、光線條件、解析度/模糊、額外JPEG壓縮層級的敏感度測試，目前完全空白，僅有的preprocessing統一（`preprocess_jpeg(quality=85)`）只解決了固定壓縮品質這一項，其餘維度從未系統性測過。

---

## 📋 v8.11 True Test Set 完整3×3混淆矩陣（2026-08-03，首次產出）

**背景**：既有的v8.11 gate評估腳本（`eval_v811_gates.py`）只對各class分別跑不同資料集（True Test filter recall、AIGuard/unseen fake AUROC、CelebA real recall、StyleGAN2 fake recall），從未在同一批同時含real+fake+filter三類的資料上跑出完整混淆矩陣。True Test Set（`splits/truetest_{real,fake,filter}.txt`，共769張：LFW real 250 + DF40 diffusion fake 270 + LFW+filter 249）是唯一同時具備三個class的held-out集，用`generate_v811_confusion_matrix.py`（直接呼叫`pipeline.hierarchical_predict()`，與正式pipeline完全一致）補上。

| Actual \ Predicted | real | fake | filter |
|---|---|---|---|
| real (n=250) | 168 | 0 | 82 |
| fake (n=270) | 2 | 268 | 0 |
| filter (n=249) | 15 | 0 | 234 |

- **True Test real recall = 67.2%（168/250）**——⚠️ **這跟gate表引用的「Shadow real recall 75.5%」不是同一份eval資料**，Shadow是AIGuard-based樣本，True Test是LFW-based的769張獨立策展集，兩者不可互換引用，論文/簡報中若要放這兩個數字必須清楚標明各自的資料來源。
- Real class誤判**全部**流向filter（82/250=32.8%），**沒有**流向fake（0/250）——與fake+filter誤判分析的方向一致：real跟filter之間的邊界比real跟fake之間鬆散得多。
- fake recall=99.3%（268/270，極高），filter recall=94.0%（234/249，與既有gate表記錄一致，交叉驗證分數吻合）。

**結論**：True Test real recall（67.2%）比Shadow real recall（75.5%）低8.3pp，方向合理（True Test是更嚴格的乾淨策展集，非訓練時同分布shadow資料），但這是一個新發現的數字，需要在論文/簡報明確區分兩個eval集合，避免讀者誤以為是同一份資料的兩次測量。

---

## ❌ Phase 3 P3-M0 Teacher Pilot：Qwen2-VL-7B-Instruct 決定性負面結果（2026-08-02）

**背景**：Phase 3 蒸餾路線第一步（P3-M0）需先確認可用的 teacher VLM。因環境內無 API key（OPENAI/DASHSCOPE/QWEN/ANTHROPIC 皆未設定），第一個candidate改用本地跑的 Qwen2-VL-7B-Instruct（`run_teacher_qwen2vl.py`），對 90 張代表樣本（real/fake/4種filter各15張）跑固定中文prompt × 2（「是否AI生成/哪裡不自然」、「有沒有濾鏡/哪種/哪些部位」），結果存於 `results/p3m0_qwen2vl_responses.jsonl`。

**量化結果**：
- **fake_prompt 完全退化**：real 和 fake 兩類都是 **100%（15/15）回答「可能是AI生成」**——對真實照片和AI生成照片給出完全相同的判斷分布，零區辨力；且不同real圖片的回答文字高度模板化（幾乎逐字重複「額頭平滑無皺紋、眼睛對稱缺乏光影」等描述）。比 FakeVLM 原本的 region label degeneracy 更嚴重——FakeVLM 至少 6/8 region 是常數標籤但其餘 2 個有效，這裡的主問題本身就完全無區辨力。
- **filter_prompt miss rate偏高**：對真正套用濾鏡的圖片判斷「沒有濾鏡」（漏判）比例：eye_enlarging 60%、whitening 80%、smoothing 67%、face_reshaping 53%；對真實無濾鏡圖片則 100%（15/15）正確判斷「沒有濾鏡」——模型呈現強烈保守偏誤，即使正確抓到濾鏡也籠統列出全部4種類型而非具體指出實際套用的那一種。

**拍板（v1）**：Qwen2-VL-7B-Instruct（未微調 base instruct 版本）用 free-text 生成方式**不能直接當 Phase 3 teacher**，直接套用會重演 FakeVLM 的 label degeneracy 陷阱。

## 🔄 P3-M0 v2 follow-up：yes-bias 校正實驗（2026-08-02）

**動機**：查文獻發現 v1 的 fake_prompt 完全退化，很可能是 VLM 領域已知的「yes-bias」（自由文字生成 yes/no 問題時的系統性偏誤），不是模型完全不懂任務。改用兩個獨立修正，同一批 90 張樣本、同一個模型：

1. **fake_prompt → token-logit 二元判斷**：不再看生成文字，改比較模型對「A.真實照片」/「B.AI生成」兩個 token 的 logits，softmax 正規化後取 p_fake，繞開自由生成的 yes-bias。
2. **filter_prompt → few-shot（2範例：whitening + smoothing 各一）**：驗證漏判偏誤是否為「不熟悉濾鏡視覺特徵」造成，而非 yes-bias。

腳本：`run_teacher_qwen2vl_v2.py`，結果：`results/p3m0_qwen2vl_v2_responses.jsonl`。

**結果**：
- **fake_prompt logit法：pairwise AUROC = 0.811**（real p_fake 均值 0.606，fake p_fake 均值 0.735）——**確實有可用的區辨訊號**，證實 v1 完全退化的根因是 free-text 生成的 yes-bias，不是模型不具備判斷能力。但整體分布系統性偏向「fake」，原始 @0.5 閾值準確率僅 57%（17/30）——**需要額外校準（例如在held-out set上學一個分類閾值），不能直接當 pseudo-label 用**。
- **filter_prompt few-shot法：漏判率明顯改善**（eye_enlarging 60%→33%、whitening 80%→33%、smoothing 67%→13%、face_reshaping 53%→33%），但**real 圖片假陽性率從 0% 飆升到 60%**——few-shot 範例把模型整體推向「傾向回答有濾鏡」，從保守偏誤換成寬鬆偏誤，同樣是校準問題而非能力問題。

**拍板（v2，最終）**：Qwen2-VL-7B-Instruct **具備可用的底層區辨訊號，但 off-the-shelf zero-shot / few-shot 都存在系統性偏誤，需要額外校準步驟才能當 teacher**——結論不是「模型不適合」而是「需要校準」，比 v1 的判斷更精確也更有建設性。已寫入 `TODO.md` K.2。下一步：①在額外 held-out 樣本上學習 p_fake 最佳分類閾值並驗證校準後準確率、②對 filter_prompt few-shot 數量/範例選擇做消融找 recall/precision 平衡點、③若校準後仍不理想才轉向其他 candidate 或 weak supervision 路線。

## ⚠️ P3-M0 v2 bf16 量化 bug 發現與修正（2026-08-02）

**發現**（使用者複查完整 JSON 明細時發現）：v2 的 `fake_prompt_v2_p_fake` 90 筆資料只有 **24 個獨立值**，而且在 logit 空間上精確以 **0.125（=2⁻³）為間隔量化**（少數例外落在 0.25/0.5，代表網格上部分點未被使用，非隨機分佈）——不同臉孔、不同 real/fake/filter 類別的圖片常拿到位元級完全相同的 p_fake 數值。這是典型的 **bf16 精度指紋**（7-bit mantissa，相對精度 2⁻⁷；若原始 logit 量級約 16，絕對量化步長恰為 16×2⁻⁷=0.125）。

**根因**：`run_teacher_qwen2vl_v2.py` 直接讀取模型 `out.logits`（dtype=bf16）張量做 `.item()`，這個張量本身已經是模型內部最後投影層（`lm_head`，`nn.Linear(3584→152064)`，bf16，無 bias）算出並捨入過的結果——圖片內容造成的真實差異，量級可能小於這個捨入步長，因此被抹平到共用網格上。

**修正**：`run_teacher_qwen2vl_v2_fix.py`——不直接讀 bf16 logits，改為取 lm_head 投影前的 last hidden state（`output_hidden_states=True`），連同 lm_head 權重中 A/B 兩個候選 token 對應的兩列，都手動 cast 成 float32 後做點積，只在最後這一步用 fp32 精度重算，避免整個 7B 模型跑 fp32（VRAM 會爆）。

**驗證結果**（`results/p3m0_qwen2vl_v2fix_responses.jsonl`）：
- fp32 修正後 90 筆資料 **90 個獨立值**（原本量化網格消失，確認 bug 抓對了）；同時腳本內也重新讀了一次 bf16 路徑作對照，**仍然是 24 個值**，證實量化重現一致，不是隨機雜訊。
- **修正後 AUROC = 0.804**（修正前 0.811，幾乎沒變）——**這是好消息**：原本的區辨訊號是真實的，不是量化網格巧合造成的假訊號，使用者的懷疑（訊號可能因抽樣巧合而膨脹）在這個案例中沒有成立，但這個查證仍然是必要且正確的動作。
- @0.5 閾值準確率 18/30（60%，修正前 17/30=57%，同樣偏低），校準需求的結論不變。

**結論**：p3-M0 v2 的核心判斷（訊號存在但需要校準）**在抓出並修正 bf16 量化 bug 後依然成立**，數字本身可信度提升（不再有量化網格的疑慮）。已寫入 `TODO.md` K.2。

---

## ✅❌ P3-M0 閾值校準（fake_prompt 成功）+ few-shot 消融（filter_prompt 失敗）（2026-08-02）

**背景**：v2/v2fix 用的 90 張樣本同時拿來「發現訊號」又「算 AUROC」，若直接在同一批上找最佳閾值再驗證準確率會有資料洩漏、過度擬合疑慮。改用獨立的新樣本集做校準，原本 90 張保留為完全獨立的 held-out 驗證集。

**fake_prompt 閾值校準（`select_p3m0_calibration_samples.py` + `run_teacher_calibration.py`）**：
- 新建 120 張校準樣本（60 real + 60 fake，`results/p3m0_calibration_samples.txt`），與原本 90 張完全不重疊（已用 path exclusion 驗證）
- 用 fp32 修正版 logit 方法（同 `run_teacher_qwen2vl_v2_fix.py` 的技巧）跑校準集，掃描閾值 0.30-0.70（step 0.004），最佳閾值 **0.676**（校準集上 accuracy=65.8%）
- **在原本90張held-out set（完全獨立、未參與校準）套用此閾值驗證**：準確率從 naive 0.5 閾值的 **60%（18/30）提升到 73.3%（22/30）**，fake recall=10/15、real recall(TNR)=12/15、real false positive=3/15
- **結論：閾值校準確實有效，是乾淨的獨立驗證結果，非資料洩漏產物** —— fake_prompt 這條路線的可用性進一步提升

**filter_prompt few-shot 消融（`run_teacher_filter_ablation.py`，75張新樣本：60 filter + 15 real，`results/p3m0_filter_ablation_samples.txt`）**：
- 比較兩種 few-shot 設計：`pos_only`（v2 原本用的2個正例：whitening+smoothing）vs `pos_neg`（正例+1個負例：真實無濾鏡照片）
- **pos_only**：filter漏判率 23%（14/60，優於v2整體的~65%），但 **real 假陽性率飆到 93%（14/15）**——比v2的60%更誇張
- **pos_neg**：real假陽性率降到 **7%（1/15）**，但 filter 漏判率反彈到 **75%（45/60）**——比純 zero-shot v1 的平均65%還差
- **關鍵發現：free-text few-shot 對這個模型是不穩定的校準旋鈕**——加一個負例讓模型整體「態度」在「傾向說有濾鏡」跟「傾向說沒有濾鏡」兩極端跳動，不是漸進式微調效果，找不到中間平衡點。跟 fake_prompt 不同：fake_prompt 換成 token-logit 連續機率值後才能做精細閾值校準；filter_prompt 目前仍依賴自由文字生成，沒有這種連續可調旋鈕，所以 few-shot 設計對它的校準效果很差
- **拍板**：filter_prompt **需要同樣改造成 token-logit 二元判斷方式**（例如針對每種濾鏡類型分別問「是/否」，取token機率），而非繼續嘗試調整 few-shot 範例數量/組合，才有機會複製 fake_prompt 校準的成功模式

**P3-M0 總結**：Qwen2-VL-7B-Instruct 經過完整的 bug 修正+閾值校準流程後，**fake_prompt 路線初步驗證可行**（獨立held-out準確率73.3%，仍有進步空間但方向正確）；**filter_prompt 路線目前不可行**（free-text/few-shot 這條路已證實走不通，需要改造成 logit-based 方法才有機會，屬於未完成的後續工作）。已寫入 `TODO.md` K.2。

---

## ✅ v8.8 完整 Eval 結果（2026-07-29）——hard_neg 擴充，fake+filter 誤判止跌

**起因**：fake+filter 誤判連續三版惡化（v8.4=0.22% → v8.5=1.22% → v8.6=1.48%），根因確認是 `fake_filter_hard_neg`（8,779張固定不變）佔 fake class 比例被 DF40 配額提升（v8.5起800→3,000/method）持續稀釋，從 v8.4 的 25.9% 降到 v8.6 的 20.0%。

**修復**：`generate_fake_filter_hard_neg.py --n 6000`（原 n=3000）重新生成，Step1+Step2 清洗後 8,779→**17,725張**（約2倍），佔 fake class 比例回升至 **33.6%**。其餘不變（filter split、real class、DF40、MidJourney皆與v8.6相同），init from v8.6。

| 指標 | v8.6（修正前處理後基準）| v8.8（hard_neg擴充後）| 變化 |
|------|------|------|------|
| True Test filter recall | 94.0%（234/249）| **94.4%（235/249）** | +0.4pp ↑ |
| ├─ eye_enlarging | 85.5% | 83.9% | -1.6pp |
| AIGuard/unseen AUROC | **0.7252** | 0.7043 | -0.021（唯一退步指標）|
| FakeClue AUROC | 0.5470 | **0.5551** | +0.008 ↑ |
| StyleGAN2 OOD | 99.8% | 99.7% | 持平 |
| CelebA real recall | 99.6% | 99.7% | 持平 |
| **Fake+filter 誤判（stress test）**| 1.48%（34/2,294）| **1.35%（31/2,294）** | **+0.13pp ↑（自v8.4以來首次改善）**|
| Alibaba filter OOD | 100.0% | 99.9%（21,137/21,151）| 持平 |

**結論**：v8.8 在 5/7 指標打平或優於 v8.6，僅 AIGuard/unseen 小幅退步（-0.021），換得 fake+filter 誤判止跌回升——判定為淨正向 tradeoff，**v8.8 定為當前 Phase 1 最佳版本**。

⚠️ **殘留限制**：fake+filter 誤判（1.35%）仍未回到 v8.4 的 0.22% 水準，代表 hard_neg 稀釋不是唯一原因，可能還有其他因素（例如整體資料分布、filter class縮量的間接影響）；AIGuard/unseen argmax real recall 仍待閾值調整。

---

## 🔍 v8.7 前處理統一實驗（2026-07-29）——結論：eval bug 是真正問題，訓練端修改是彎路

**起因**：使用者質疑「圖片大小不統一有沒有問題」，查證發現我們自己的 eval 腳本前處理彼此不一致：`eval_stylegan2.py`/`eval_celeba_real.py`/`stress_test_held_out.py`（走`pipeline.py`）有套用 JPEG q85 正規化，但 `eval_crossdataset_v3_1.py`/`eval_filter_recall.py`/`eval_ali_ood.py` 沒有，且幾何變換（Resize+CenterCrop vs 訓練用的直接Resize成正方形）也不一致；另外發現 real class 原生解析度全部≤256px，但部分fake/filter達1024px，有FFT branch學到「降採樣痕跡」捷徑的風險。

**第一步（正確）**：統一三個 eval 腳本前處理，改成跟 `pipeline.py` 完全一致（JPEG q85 + `Resize((224,224))`）。

**第二步（走了彎路）**：額外訓練 v8.7——在訓練時也加入 JPEG q85 canonicalization + 隨機降採樣增強（防止解析度捷徑），init from v8.6。

**結果對比**（全部用修正後的統一前處理量測，公平比較）：

| 指標 | v8.6（模型不變，僅eval腳本修正）| v8.7（訓練也加了JPEG+解析度增強）|
|------|------|------|
| True Test filter recall | **94.0%**（234/249，↑↑ from 舊量測90.4%）| 92.8% |
| ├─ eye_enlarging | **85.5%**（↑↑ from 舊量測74.2%）| 82.3% |
| AIGuard/unseen AUROC | **0.7252**（↑ from 舊量測0.7157）| 0.6163（大幅退步）|
| FakeClue AUROC | **0.5470**（↑ from 舊量測0.5134）| 0.5063 |
| StyleGAN2 OOD | **99.8%** | 98.3%（退步）|
| CelebA real recall | 99.6% | 99.8%（微幅較好，可忽略）|
| Fake+filter 誤判 | **1.48%** | 2.57%（幾乎翻倍，退步）|
| Alibaba filter OOD | 100.0% | 100.0%（打平——**解析度捷徑增強沒有改變這個數字，弱化了「Alibaba 100%是解析度取巧」的假說，比較可能是真實泛化能力**）|

**結論**：**v8.6 在 5/7 指標領先，v8.7 只有CelebA微幅領先（可忽略）。真正的問題出在 eval 腳本量測不一致，不是模型本身——光修 eval 腳本、完全不碰模型，v8.6 的數字就大幅提升（filter recall 90.4%→94.0%、AIGuard/unseen 0.7157→0.7252）。v8.7 額外加的訓練端修改（JPEG重編碼+解析度增強）淨效果是負面的，可能磨損了FFT branch需要的細緻頻率痕跡。**

**已保留**：三個eval腳本的前處理統一修正（`eval_crossdataset_v3_1.py`/`eval_filter_recall.py`/`eval_ali_ood.py`，這是正確性修復，永久保留）。
**已捨棄**：v8.7 的訓練端修改（JPEG+解析度增強），`pipeline.py` 已改回指向 v8.6。
**v8.6 為當前 Phase 1 最佳版本**（所有數字均為修正後的一致量測）。

**教訓**：發現一個 eval 量測問題時，先窮盡「只修量測、不動模型」這條路徑並重新驗證基準，再決定是否需要動訓練——這次因為沒有先重新量測 v8.6 就直接開始訓練 v8.7，多跑了一輪不必要（且結果是負面）的訓練。

---

## ⚠️ v8.6 完整 Eval 結果（2026-07-29，原始量測，前處理不一致，已被上方修正取代）——filter OOD 補強

**目的**：filter class 先前完全沒有 OOD 評估（True Test filter 只是同分布 held-out）。查證 RetouchingFFHQ 官方論文（arXiv:2307.10642）後確認，該資料集本身就是設計給 Alibaba/Tencent/Megvii 三家公司互相 hold-out 做 generalization testing 用的。我們手上沒有 Tencent，因此把 `FFHQ_ali_process`（Alibaba，21,151張，4種filter類型×3種強度）整批從訓練移除，改當 held-out OOD eval，訓練只保留 Megvii + 不掛名的 four_process + 自建 filter。

| 指標 | v8.5 | v8.6 | 變化 |
|------|------|------|------|
| True Test filter recall | 89.6%（223/249）| **90.4%（225/249）** | +0.8pp ↑ |
| ├─ smoothing | 96.8% | 98.4% | +1.6pp |
| ├─ whitening | 91.9% | 91.9% | 持平 |
| ├─ eye_enlarging | 72.6% | 74.2% | +1.6pp |
| └─ face_reshaping | 96.8% | 96.8% | 持平 |
| AIGuard/unseen AUROC | 0.7195 | 0.7157 | -0.0038（誤差範圍內）|
| FakeClue AUROC | 0.5100 | 0.5134 | +0.0034（誤差範圍內）|
| StyleGAN2 OOD fake | 99.8%（9,975/10,000）| 99.8%（9,976/10,000）| 持平 |
| CelebA OOD real recall | 99.6%（19,885/19,962）| 99.6%（19,887/19,962）| 持平 |
| **Fake+filter 誤判（stress test）**| 1.22%（28/2,294）| **1.48%（34/2,294）** | **-0.26pp，連續三版惡化中**|
| **Alibaba filter OOD（新增）**| 未測過 | **100.0%（21,147/21,151）** | 新指標，見下方保留說明 |

**Alibaba OOD 100.0% 明細**：EyeEnlarging 100.0%（5,340/5,340）、FaceLifting 100.0%（5,264/5,265）、Smoothing 100.0%（5,267/5,268）、Whitening 100.0%（5,276/5,278）；強度 30/60/90 三個等級皆 100.0%。

> ⚠️ **保留解讀**：查證發現 Alibaba 圖片解析度為 1024×1024，跟訓練集裡的 Megvii 圖片完全相同（也是1024×1024，都基於同一批 FFHQ 底圖）。這代表 100% 不是靠「從沒見過這種解析度/底圖來源」的取巧線索達成（模型確實見過同規格的圖），但也代表這個測試沒有完全獨立於「FFHQ底圖+高解析度商業演算法」這個共同模式之外——比較確定的結論是「模型泛化到不同公司的實作，不是單純記住Megvii的指紋」，但還不能完全排除模型部分依賴解析度/底圖來源這類非語意線索。

**Fake+filter 誤判持續惡化的原因**：hard_neg（8,779張）張數三個版本都沒變，但 fake class（v8.5起）和後續 filter class 縮減，讓 hard_neg 在整體訓練資料裡的相對影響力被稀釋。v8.4→v8.5→v8.6：0.22%→1.22%→1.48%，尚未止跌。

**目前建議**：v8.6 的 filter OOD 驗證有價值、True Test 也進步了，但 fake+filter 誤判連續三版惡化已經是需要優先處理的問題，下一步應該是擴充 hard_neg 資料量而非繼續做新的資料調整，待 hard_neg 補強後才正式定案哪個版本作為 Phase 1 最終最佳模型。

---

## ✅ v8.5 完整 Eval 結果（2026-07-29）

修復資料完整性問題後重訓，`pipeline.py` 已切換至 v8.5。全部 eval 皆確認以 `shufflenet_v2_3class_v85.pth` 執行（每個腳本輸出都印出 checkpoint 名稱）。

| 指標 | v8.4（有洩漏/重複資料）| v8.5（已修復）| 變化 |
|------|---------------------|--------------|------|
| True Test filter recall | 90.4%（225/249）| **89.6%（223/249）** | -0.8pp |
| ├─ smoothing | 96.8% | 96.8% | 持平 |
| ├─ whitening | 93.5% | 91.9% | -1.6pp |
| ├─ eye_enlarging | 74.2% | 72.6% | -1.6pp |
| └─ face_reshaping | 96.8% | 96.8% | 持平 |
| AIGuard/unseen AUROC（靜態圖主評）| 0.7127 | **0.7195** | +0.0068 ↑ |
| StyleGAN2 OOD fake（靜態圖主評）| 99.7%（9,974/10,000）| **99.8%（9,975/10,000）** | +0.1pp ↑ |
| CelebA OOD real recall | 99.6%（19,875/19,962）| 99.6%（19,885/19,962）| 持平 |
| FakeClue AUROC（H.264輔助）| 0.4981 | 0.5100 | +0.0119 ↑ |
| WildDeepfake AUROC（deprecated，僅供參考）| 0.5759 | 0.5293 | -0.0466（非主評，不影響結論）|

**結論**：v8.5 在兩個靜態圖主評指標（AIGuard/unseen、StyleGAN2）都比 v8.4 略好；filter recall 小幅下降 0.8pp——這是**預期且健康的變化**，因為 v8.4 的 90.4% 是建立在 53% 重複資料（部分圖片被訓練 8 次）之上的膨脹數字，v8.5 的 89.6% 是在乾淨、無重複、無洩漏資料上的真實結果，且 True Test fake 245/270 已確認不再有任何訓練集重疊（v8.4 有 45 張 MidJourney 洩漏）。

**訓練過程**：15 epochs，init from v8.4，Best macro F1=0.9861（epoch 11，val set 已修復無train重疊，數字首次真正可信）。

---

## ⚠️ v8.5 資料完整性修復（2026-07-29 全面審查）

v8.4 完整審查發現多項資料層級問題，v8.5 已修復，重訓進行中：

| # | 問題 | v8.4 影響 | v8.5 修復 |
|---|------|----------|----------|
| 1 | `build_v84_splits.py` MidJourney/fake 未排除 `truetest_fake` | **45/270（16.7%）True Test fake 圖片同時在訓練集** → True Test fake 相關數字不可信 | 加入 `- tt_fake` 排除，0 重疊已驗證 |
| 2 | val set 沿用 `v6_val_real_fake.txt`，但 v8.4 訓練用了**全部** AIGuard real/fake | 5,146/9,740（52.8%）val 資料同時在訓練集，**val F1=0.9839 不是有效的 out-of-sample 指標** | val 改用 AIGuard real/fake 各 5% 全新切分（held-out，非用於任何 eval 報告）+ CelebA val，0 重疊已驗證 |
| 3 | `v83_train_filter.txt`（v8.3 起繼承進 v8.4）內部有 **53% 重複路徑**，部分圖片重複達 8 次 | Filter class 真實唯一圖片僅 94,483 張（非文件記錄的 202,667），個別圖片梯度訊號被放大最多 8 倍 | 依路徑去重複，202,667→94,483（唯一），0 重複已驗證 |
| 4 | DF40 5 個 diffusion 方法配額僅 800/method（利用率 2-4%），早期文件誤植「~800 total」| Fake class 生成式多樣性嚴重不足 | 800→3,000/method（共 15,000 張，仍排除 truetest_fake）|
| 5 | DF40 5 方法（sd2.1/DiT/SiT/ddim/pixart）文件誤標為部分 FS/FR | 分類錯誤 | 官方 DF40 Table 2 確認：**全部 8 個來源（含 StyleGAN2/3、MidJourney）都是 EFS** |

修復後分布（`build_v85_splits.py`）：Real 27.1% / Fake 23.1% / Filter 49.8%（v8.4 為 18.2%/11.7%/**70.0%**，去重複本身即解決失衡問題）。

**另發現 Phase 2 region head 的兩個獨立問題（尚未修復，待 Phase 1 穩定後處理）**：
- `region_head_v1.pth` 的 FakeVLM teacher inference 樣本中 **21.2%（1,064/5,023）來自 EFS 來源**（chameleon UUID命名疑似EFS + genimage 確認EFS，含 adm/biggan 等純生成方法），這批圖片沒有「正常 vs 竄改區域」的對比基礎，FakeVLM 給出的可疑區域標籤語意上站不住腳，噪聲已混入訓練
- `region_head_v1.pth` 訓練時用 **v8.1** backbone 抽特徵（`train_region_head_v1.py`），但 `pipeline.py` 實際推論時用 **v8.4** backbone 抽特徵餵給它——特徵空間漂移，無 error 但可能悄悄劣化 region 預測品質

---

## v8.4 訓練資料總覽（Phase 1 前一版本，見上方修復記錄）

> v8.4 為 Phase 1 前一版本（True Test Binary AUROC=1.0000，Filter recall=90.4%，**但 True Test fake 45 張洩漏、val F1 無效、filter 53% 重複，數字需在 v8.5 重新驗證**）。
> v8.3 改為 filter recall 87.6% 的前一個里程碑；v8.4 解決 real class OOD 泛化不足根本問題。
> 訓練以 v8.3 weights 為初始化，純靜態 JPEG 圖片（無影片幀）。

### Real 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 | 備注 |
|---------|-------|-----------|------|---------|------|
| AIGuard real | Real | **25,753** | `AIGuard/real/0~4/` | v3 | 影片截幀+對齊+JPEG |
| **LFW (Labeled Faces in the Wild)** | Real | **8,918**（v84 clean pool） | `lfw/` | v5 | v8.4 改為 ×1，不過採樣 |
| **CelebA train** | Real | **18,315** | `celeba_train/` | **v8.4（新加）** | partition=0，多樣化靜態人像 |

> v3→v8.3 的 LFW oversample 歷史：×1（v5）→ ×4（v7.4）→ ×6（v7.7）→ ×8（v7.8）→ ×10（v7.9 甜蜜點）→ ×11（v8.1）→ **×1（v8.4，回歸）**。
> CelebA 加入前（v8.3）：real class 幾乎全由 LFW 定義 → CelebA OOD real recall=4.1%。

### Fake 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 |
|---------|-------|-----------|------|---------|
| AIGuard fake | Fake | **20,552** | `AIGuard/fake/0~4/` | v3 |
| **DF40 EFS**（v8.4: 800/method）| Fake | 4,000（800×5 方法）| `sd2.1/` `DiT/` `SiT/` `ddim/` `pixart/`（各為獨立頂層資料夾，非 `DF40/` 子目錄）| v5 |
| **DF40 EFS**（v8.5: 3,000/method）| Fake | **15,000**（3,000×5 方法）| 同上 | v8.5 |
| **MidJourney** | Fake | 594（v8.4 未排除 truetest，45張洩漏）→ **549**（v8.5 已排除）| `MidJourney/` | v8.4（新加，v8.5修正） |
| **fake_filter hard neg** | Fake | **8,779** | `fake_filter_hard_neg/` | v8.3 |

> ✅ **2026-07-31 MidJourney 訓練風險評估完成**（`AIGuard/eval_midjourney_risk.py`）：擔心 MidJourney 高畫質人像風格是否與 CelebA 網路照片相近、加劇 real/fake 邊界混淆。實測 v8.8 模型對 632 張 MidJourney/fake 的判斷：**100% 正確判為 fake（632/632）**，P(real) mean=0.033／median=0.032，遠低於 CelebA real 過去的 P(real) mean=0.079／median=0.029（且方向相反——CelebA real 是「應該高卻低」，MidJourney fake 是「正確地低」）。**結論：無風險，可安心保留在訓練集，不需額外處理**。

**AIGuard fake 組成（6 個 source dataset，全部 GAN / face-swap，無 diffusion）**：

| 子 dataset | 生成方法 |
|-----------|---------|
| OpenForensics | StyleGAN + Adversarial Latent Autoencoders（face synthesis + face swap）|
| CDDB | ProGAN / StyleGAN / BigGAN / CycleGAN / GauGAN / CRN / IMLE / SAN + FF++ face swap |
| WildDeepfake | in-the-wild face swap（autoencoder/GAN，影片截幀；語義包含在 AIGuard fake 中）|
| 140k Fake Faces | StyleGAN 生成 |
| Pretty Face | StyleGAN2（中國明星）|
| Deepfake and Real | OpenForensics 變體（GAN face synthesis）|

⚠️ AIGuard fake 全部為 2022 年前資料，不含 Stable Diffusion / MidJourney 等 diffusion 生成臉。DF40 Diffusion 從 v5 起補充此缺口。
⚠️ fake_filter hard neg 11,970 張（v8.3 生成）→ v8.4 清洗後剩 8,779 張。

### Filter 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 |
|---------|-------|-----------|------|---------|
| filter_data 自建 | Filter | **25,213** | `filter_data/` | v3 |
| RetouchingFFHQ four_process | Filter | **7,731** | `FFHQ_four_process/` | v3 |
| RetouchingFFHQ megvii_four_process | Filter | **13,139** | `FFHQ_megvii_four_process/` | v3 |
| RetouchingFFHQ ali_process | Filter | **23,795** | `FFHQ_ali_process/` | v3 |

> ⚠️ **2026-07-29 分類修正**：查證官方論文（RetouchingFFHQ: A Large-scale Dataset for Fine-grained Face Retouching Detection, arXiv:2307.10642）後發現，先前把「four/megvii/ali」當成三個平行來源是**錯的**。官方結構是：**三家公司來源**（Alibaba / **Tencent** / Megvii）× **四種美顏類型組合維度**（smoothing/whitening/face lifting/eye enlarging，可用 process/dual/three/four_process 表示套用1~4種組合）。「four」不是公司，是套用全部4種類型的意思，跟 megvii/ali 不是同一個維度。
> **我們完全沒有 Tencent 來源的資料**——這代表 filter class 訓練目前只涵蓋 Alibaba + Megvii 兩家（+ 我們自己的 MediaPipe-based 生成），**Tencent 是尚未使用、可作為乾淨 filter OOD eval 候選的第三方演算法來源**（詳見下方「Filter OOD 尚未測試」章節）。
> Sources: [RetouchingFFHQ paper (arXiv:2307.10642)](https://arxiv.org/abs/2307.10642)
| **LFW + smoothing** | Filter | ~8,918 | 自行生成（`filters/generate_lfw_filters.py`）| v5.1 |
| **LFW + whitening** | Filter | ~8,918（×4 oversample）| 同上 | v7.6 |
| **LFW + face_reshaping** | Filter | ~8,918（×4 oversample）| 同上 | v7.6 |
| **LFW + eye_enlarging (scale=1.18)** | Filter | ~8,918（×8 oversample）| `filters/generate_lfw_eye_enlarging.py` | v7.2（×4）→ v8.1（×8）|
| **LFW + eye_enlarging s110** | Filter | **4,168**（清洗後）| `filter_data/lfw_eye_enlarging_s110/` | v8.4（新加）|
| **LFW + eye_enlarging s125** | Filter | **4,277**（清洗後）| `filter_data/lfw_eye_enlarging_s125/` | v8.4（新加）|
| **LFW + eye_enlarging s135** | Filter | **4,304**（清洗後）| `filter_data/lfw_eye_enlarging_s135/` | v8.4（新加）|

> v8.4 multi-scale eye 從全部 LFW（非 clean pool）生成，各約 30% 因閉眼剔除（step2 清洗）。

> ⚠️ **v8.4 filter split 53% 重複資料 bug**（2026-07-29 發現）：`v83_train_filter.txt`（v8.3 起繼承進 v8.4，未重建）內部有 108,184/202,667 筆重複路徑，部分圖片重複達 8 次。真實唯一圖片數僅 **94,483** 張，非文件記錄的 202,667。v8.5 已依路徑去重複修復（`build_v85_splits.py`），0 重複已驗證。

**v8.4 split 行數**：real+fake 86,703 | filter 202,667（**唯一僅94,483，53%重複**）| val 9,740（AIGuard 5,146 [100%與訓練重疊] + CelebA val 4,594）
**Class weights（v8.4）**：real=1.828（vs v8.3=1.13）、fake=2.843、filter=0.476

**v8.5 split 行數**：real+fake 95,342 | filter **94,483（已去重複）** | val 6,910（AIGuard held-out 5% [real 1,288+fake 1,028，全新切分，0與訓練重疊] + CelebA val 4,594）
**Class weights（v8.5）**：real=1.229、fake=1.443、filter=0.670
**Class 分布（v8.5）**：Real 27.1% / Fake 23.1% / Filter 49.8%（v8.4 為 18.2%/11.7%/70.0%）

---

## 版本演進記錄

| 版本 | 相對前版的主要資料變動 | True Test Binary AUROC | Filter Recall（True Test） |
|------|----------------------|------------------------|--------------------------|
| v3 | DualBranch 基準（AIGuard only）| 0.1061（LFW 全判 fake）| — |
| v5 | +LFW real + DF40 Diffusion fake | 0.9990 | 0%（LFW domain confusion）|
| v5.1 | +LFW+filter | **1.0000** | 31% |
| v6 | 純靜態（移除 WildDeepfake），init from v3 | **1.0000** | 67.5% |
| v7.2 | +LFW domain-matched eye_enlarging | 0.9978 | 83.9%（real recall ↓ 70%）|
| v7.5 | 移除 filter weight cap | **1.0000** | 72.7% |
| v7.6 | +LFW whitening ×4 + reshape ×4 | **1.0000** | 81.5% |
| v7.9 | LFW real ×10（甜蜜點）| **1.0000** | 85.5% |
| v8 | LFW eye ×8 | **1.0000** | 86.7% |
| v8.1 | LFW real ×11 | **1.0000** | **87.6%**（eye=66.1%）|
| v8.2（棄用）| +Celeb-DF-v2 4,711 H.264 real | 1.0000 | 85.5% ↓ |
| v8.3 | +fake+filter hard neg 11,970 張 | **1.0000** | 87.6%（eye=67.7%，fake+filter 誤判 ~50%→0.22%）|
| **v8.4** | 全資料清洗 + CelebA train 18K + multi-scale eye s110/s125/s135 | **1.0000** | **90.4%**（eye=74.2%）|

---

## True Held-out Test Set（v5 起使用）

> ⚠️ v7+ 訓練決策曾參考此 test set 結果（hyperparameter selection bias），建議論文中標注。
> ⚠️ 主要參照指標：Binary AUROC（fake vs real+filter），不是 3-class accuracy。

| Class | 來源 | 張數 | 路徑 |
|-------|------|------|------|
| Real | LFW（非 AIGuard / 非 FFHQ 來源）| **250** | `lfw/` 子集 |
| Fake | DF40 Diffusion（SD 2.1 / MidJourney v6 / DiT-XL / PixArt-α）| **270** | DF40 diffusion 子集 |
| Filter | LFW real + 我們的 filter pipeline（4 種）| **249** | 自行生成 |
| **合計** | | **769** | |

### True Test 各版本結果

| 模型 | Binary AUROC | Real | Fake | Filter recall | Smoothing | Whitening | Eye | Reshape |
|------|-------------|------|------|--------------|-----------|-----------|-----|---------|
| v6 | 1.0000 | 235/250（94%）| 269/270 | 168/249（67.5%）| 100% | 61.3% | 27.4% | 80.6% |
| v7.9 | 1.0000 | 219/250（87.6%）| 268/270 | 213/249（85.5%）| 100% | 90.3% | 58.1% | 93.5% |
| v8.1 | 1.0000 | 207/250（82.8%）| 269/270 | 218/249（87.6%）| 100% | 90.3% | 66.1% | 93.5% |
| v8.3 | 1.0000 | — | — | 218/249（87.6%）| 98.4% | 90.3% | 67.7% | 93.5% |
| **v8.4** | **1.0000** | — | — | **225/249（90.4%）**| 96.8% | **93.5%** | **74.2%** | **96.8%** |

> ⚠️ v8.3/v8.4 True test real recall 未重新測量（val set 改了，real 已整合進 val；紙面 real recall 只在 CelebA 19,962 張有意義）。
> ⚠️ v7.9 之後的 real recall 下降趨勢（87.6%→82.8%）為 LFW real 過採樣 vs filter 資料的 tradeoff，v8.4 用 CelebA 根本修復。

---

## Cross-dataset OOD Benchmarks

> **靜態圖主評**（主要評估指標）：AIGuard/unseen AUROC + StyleGAN2 OOD fake detection。
> 影片幀（FakeClue、Celeb-DF-v2、WildDeepfake）受 H.264 domain gap 影響，定位為輔助評估。

### 靜態圖主評

| Dataset | 組成 | 張數 | v8.3 AUROC | v8.4 AUROC | 備注 |
|---------|------|------|-----------|-----------|------|
| **AIGuard/unseen** | 靜態圖（real 238 / fake 216）| **454** | **0.7356** | 0.7127 | ↑ from v3 0.640；v8.4 tradeoff（real boundary 放寬）|
| **StyleGAN2 OOD fake** | StyleGAN2 靜態生成（10K）| **10,000** | 99.9% correct | 99.7% correct | 全靜態，零 H.264；FFT branch OOD 泛化確認 |

**AIGuard/unseen 說明**：
- `AIGuard/unseen/` 從未進入任何訓練 split（完全 held-out），454 張均通過 Step1 清洗
- Argmax 下 real recall=23/238（6.7%）→ 閾值問題（P(real) 分布全部極低），不代表 ranking 失效；AUROC=0.7356 有效
- 真正 OOD：這 454 張是 DeepFake-450K 資料集中從未被使用的保留評估集

**CelebA 說明**（v8.4 eval，非主評）：
- CelebA partition=2（19,962 張）：v8.4 將 partition=0（18,315 張）加入訓練，partition=2 是同分布 held-out
- **non-OOD**（partition=0 和 2 來自同一 CelebA 資料集，非真正 OOD）
- v8.3 real recall 4.1% → v8.4 **99.6%**：此改善是「修復了訓練分布覆蓋不足」，非 OOD 泛化突破

### 影片幀輔助評估（H.264 domain gap）

| Dataset | 組成 | 張數 | v8.3 AUROC | 備注 |
|---------|------|------|-----------|------|
| **FakeClue test** | FF++ + GenImage AIGC + Chameleon AIGC | **1,166** | 0.5117 | H.264 壓縮域差異；Phase 2 distillation 用 |
| Celeb-DF-v2 blind holdout | 影片幀（real 200 / fake 200）| **400** | 0.5736（real=0/200）| H.264；非主評 |

> ⚠️ **WildDeepfake 從主評移除**（2026-07-28）：AIGuard/fake 官方文件確認使用 WildDeepfake 作為來源之一 → 不同幀但同分布（semantic overlap）；加上 H.264 domain gap，real recall=0/400 → 完整記錄見 Data Leakage 驗證。
> ⚠️ FakeClue / Celeb-DF-v2 low real recall（≈0）均為 H.264 domain gap：FFT branch 將 H.264 壓縮特徵誤認為 fake。Phase 3 修復目標。

---

## Phase 2 備用資料（知識蒸餾）

| Dataset | Class | 實際可用 | 路徑 | 用途 |
|---------|-------|---------|------|------|
| FakeClue human real | Real | **4,428** | `FakeClue/train_clean/labels.csv` label=1 | Phase 2 distillation |
| FakeClue deepfake（FF++）| Fake | **19,566** | `FakeClue/train_clean/labels.csv` label=0, cate=deepfake | Phase 2 FakeVLM teacher inference |
| FakeClue human fake（GenImage AIGC）| Fake | **306** | `FakeClue/train_clean/labels.csv` label=0, cate=human | Phase 2 distillation |
| **合計** | — | **24,300** | — | ✅ |

> FakeClue 不進 Phase 1 detection 訓練（image quality 差 + FF++ 與 AIGuard 重疊）。

---

## 排除（已試，不採用）

| Dataset | 原因 |
|---------|------|
| ~~CelebA 30K（v3 時代試驗）~~ | v3（binary 2-class）era：AUROC 0.673→0.608，風格不匹配；⚠️ v8.4 已重新以 18,315 張 CelebA train partition=0 加入 real class，效果顯著（CelebA OOD real recall 4.1%→99.6%） |
| **Celeb-DF-v2**（4,711 清洗後 H.264 real 幀）| v8.2 實驗：WildDeepfake real 0→157/400（改善），但 filter recall −2.1%、FakeClue AUROC 0.480（↓ from 0.527）。H.264 問題為架構限制，加資料無法根治，且代價傷害核心指標 → 不採用 |
| WildDeepfake train（v4 試用）| 影片幀讓 FFT branch 學到 H.264=fake shortcut，WildDeepfake AUROC 從 0.9378 反跌至 0.216 → v6 起永久移除 |
| v3.1 JPEG augmentation | quality 10-85 aug 加深 compression shortcut，WildDeepfake AUROC 0.938→0.216（反轉）；廢棄 |

---

## 候選（Fake 多樣性擴充，待 Phase 3）

| Dataset | 圖片數 | 取得方式 | 備注 |
|---------|--------|---------|------|
| FaceForensics++ (FF++) | ~1,000 影片 | GitHub 申請 | 最常用 deepfake benchmark |
| DFDC (Deepfake Detection Challenge) | 128K 影片片段 | Kaggle 下載 | Facebook 釋出，多樣性高 |
| DF40 StarGAN / StarGANv2 | 待確認 | Google Drive | OOD fake eval 用；無 per-image attribute label |

---

## 候選（Manipulation / Explanation，Phase 2）

| Dataset | 圖片數 | 來源 | 優先度 | 備注 |
|---------|--------|------|--------|------|
| [MMTD-Set](https://huggingface.co/datasets/zhipeixu/MMTD-Set-34k) | 34K | HuggingFace | 🟡 中 | 三類篡改：PhotoShop / DeepFake / AIGC-Editing；含 GPT-4o 說明文字，可供知識蒸餾 |

### Region-level GT 評估指標參考（尚未實作，供未來 landmark displacement GT 方案使用）

**IINC（Inverse Intersection Non-Containment）**，出自 [Dang et al., "On the Detection of Digital Face Manipulation", CVPR 2020](https://openaccess.thecvf.com/content_CVPR_2020/papers/Dang_On_the_Detection_of_Digital_Face_Manipulation_CVPR_2020_paper.pdf)（DFFD）：

$$\text{IINC} = \frac{1}{3} - |U| \times \left( \frac{I}{|M_{gt}|} + \frac{I}{|M_{att}|} \right)$$

其中 $I$ 為 attention map 與 ground-truth mask 的交集，$U$ 為聯集，$M_{gt}$ 為 GT mask，$M_{att}$ 為模型輸出的 attention/region map。**IINC 越低越好**。

> ⚠️ 2026-07-31 修正：先前在別處引用時公式因文字編碼問題顯示錯誤，本條目依使用者提供的原始論文截圖核對修正，為目前確認正確的版本。DFFD 論文中的參考數字：All Real=0.015、All Fake=0.147、Partial manipulation=0.311、Complete manipulation=0.077。
> 用途：待 C2（filter class landmark displacement GT，見 CLAUDE.md TODO）或 Phase 2 region head 有 pixel/region-level GT 後，可直接用此指標評估 Grad-CAM/region head 的定位品質，不需自己發明新指標。
> ✅ 2026-08-02 實作補充：`xai_eval_protocol.py`已將公式寫成可執行函式並用synthetic data驗證。**關鍵校準發現**：I/U/M_gt/M_att必須是「佔全圖面積的比例」而非raw pixel count——用pixel count直接代入會得到-17.667這種遠超論文參考值範圍（All Real=0.015~Complete=0.311）的離譜數字；改為除以總像素數正規化後，完美重疊（perfect overlap）情境算出0.153，落在論文參考值合理區間內，驗證公式實作正確。此腳本同時實作了IoU、Pointing Game兩個指標的reusable函式，皆已通過self-test，等Landmark GT校準修復後即可直接用於Grad-CAM++/region_head_v4/LRP/pixel-diff baseline四種方法的正式比較。

---

## 資料清洗 SOP

1. **Step 1 — `clean_dataset.py`（YuNet ONNX）**：過濾短邊 < 128px；過濾 face count > 1
2. **Step 2 — `face_attr_filter.py`（MediaPipe + InsightFace）**：過濾閉眼（EAR < 0.18）/ 墨鏡（亮度 < 30）/ 嬰兒（age < 18）
3. **原則**：原始資料夾永不刪除，只產生 `clean_paths.txt` 名單，訓練時讀名單
4. **FFHQ exclusion list**：`FFHQ_settings/excluded_images_list/` 套用到 four_process / megvii / ali
5. **嚴格規則（v8.4 起）**：所有訓練圖必須通過完整兩步驟清洗才可進 split

**v8.4 全資料清洗結果（`run_full_cleaning.py`）**：

| Dataset | 清洗前 | 清洗後 | 剔除率 | 主因 |
|---------|--------|--------|--------|------|
| DiT | 5,000+ | ~3,000 | 39.5% | 多臉 / 低解析度 |
| SiT | 5,000+ | ~3,150 | 37.0% | 同上 |
| LFW | 13,233 | 8,918 | 32.6% | 閉眼 / 嬰兒 |
| fake_filter_hard_neg | 11,970 | 8,779 | 26.6% | 閉眼（fake 圖套 filter 後）|
| sd2.1 | 5,000+ | ~3,550 | 29.1% | 多臉 |

---

## 各 dataset 的定義合法性

> 最後驗證：2026-07-29

### 類別定義基準

- **Real**：真實拍攝、未修改的臉
- **Fake**：臉部內容被合成或操控（face swap、GAN 生成、diffusion 生成、facial reenactment）
- **Filter**：身份保留的外觀美化處理，且被拍攝的表情行為是真實的

### Deepfake 四大生成技術 × 我們的類別對應

DF40（及學術文獻）將 deepfake 生成方法分為四類，以下逐一定義並對應到我們的 real / fake / filter 標籤：

| 縮寫 | 全名 | 技術說明 | 我們的標籤 | 理由 |
|------|------|---------|-----------|------|
| **FS** | Face Swapping | 把 source `xs` 的**身份**移植到 target `xt` 上，target 的 pose/expression 保留，但臉是別人的 | **Fake** | 身份被替換 |
| **FR** | Face Reenactment | 保留 target 的**身份** `it`，但用 driven variable `ca` 替換其表情/嘴形/動作 | **Fake** | 行為是捏造的（本人沒有做過）|
| **FE** | Face Editing | 保留身份，只修改外觀屬性（makeup、眼鏡、年齡、髮型等）| **語義偏 Filter**（⚠️ 目前**未加入**訓練或測試）| 若未來加入需重新評估 |
| **EFS** | Entire Face Synthesis | GAN / Diffusion 從頭生成一張**不存在的人**的臉（StyleGAN、SD 生成）| **Fake** | 身份不存在，100% 合成 |

### 各 Dataset 對應的生成類型

> ⚠️ **2026-07-29 修正**：官方 DF40 論文 Table 2 確認，我們使用的 sd2.1 / DiT / SiT / ddim / pixart **全部 5 個方法都屬於 EFS**（Entire Face Synthesis，Latent Diffusion 子類）。曾經根據檔名規律（sd2.1/ddim/pixart 重用來源幀檔名 vs DiT/SiT 用任意編號）推論前三者是 conditional FS/FR——這個推論被官方表格推翻，檔名重用很可能只是 img2img 用真實幀當初始噪聲參考、但 denoising strength 夠高導致身分完全改變（生成結果仍是不存在的新身分）。DiT/SiT 用來源幀無關的獨立編號，同樣是 EFS，只是 benchmark bookkeeping 方式不同。

| Dataset | 包含方法 | 標籤 | 是否在訓練集 | 是否在 eval |
|---------|---------|------|------------|------------|
| AIGuard fake（CDDB、OpenForensics 等）| FS + EFS（GAN-based，2022年前）| Fake | ✅ train | — |
| DF40 sd2.1 / DiT / SiT / ddim / pixart | **EFS**（Latent Diffusion，官方 Table 2 確認）| Fake | ✅ train | True Test fake（135張 sd2.1+ddim+pixart + 90張 DiT+SiT，皆EFS）|
| DF40 MidJourney6 | **EFS**（Popular Application）| Fake | ✅ train（v8.5起排除test 45張）| True Test fake（45張）|
| StyleGAN2 / StyleGAN3（DF40版，`Downloads/StyleGAN2.zip`等）| **EFS**（GAN based，seed取樣，未解壓）| Fake | ❌ 未加入（維持不解壓，理由見下）| — |
| StyleGAN2（`stylegan2_test/fake/`，140k Real-Fake Faces 版）| EFS（StyleGAN2 靜態，非DF40同源）| Fake | ❌ 未加入 | ✅ OOD eval（99.7%） |
| FakeClue fake（FF++, cate=deepfake）| FR + FS | Fake | ❌ Phase1；✅ Phase2 region head 蒸餾來源之一 | ✅ 輔助 eval（H.264）|
| FakeClue fake（chameleon + genimage, cate=human）| **⚠️ 非人臉內容混雜**（見下方視覺驗證）| Fake | ❌ Phase1；⚠️ **Phase2 region head 蒸餾污染來源**（見下方修正數字）| ✅ test 219張同樣混入cross-dataset AUROC |

> ⚠️ **2026-07-29 視覺驗證發現更嚴重問題**：直接開圖檢查 genimage/chameleon 樣本（train + test 皆同），發現 `cate=human` 這個標籤不代表「一定是人臉」——genimage 是 GenImage benchmark（VQDM/BigGAN/Wukong/GLIDE/ADM/SD等方法，涵蓋任意物體/場景的通用AI生成圖偵測資料集，非人臉限定），實際樣本包含嬰兒床家具、加油站、鯊魚水下照等完全無人臉內容；chameleon 樣本混合非人臉場景（室內設計）與全身動漫cosplay（臉部僅佔畫面一小部分，非特寫）。
> - **Phase2 region head 修正估計**：原估計21.2%（1,064/5,023）污染是基於原始抽樣數，未考慮下游`load_records()`已有的空區域自動過濾（chameleon 987/988即99.9%因空區域被自動排除）；重新計算後實際混入訓練的僅**76/4,035（1.9%）**（genimage 75張 + chameleon 1張漏網）。`train_region_head_v2.py` 已修復：明確排除 genimage/chameleon 來源（不只因為EFS缺乏局部對比，更因為這些常非人臉，region-head框架完全不適用）。
> - **Phase1 FakeClue AUROC 額外caveat**：test set 219張「human」分類（用於算`[human] AUROC=0.5818`子項）同樣混雜非人臉內容 → FakeClue AUROC偏低（~0.51）不能只歸因H.264 domain gap，部分是在測人臉偵測器對非人臉圖片的表現（未定義任務）；FakeClue AUROC本就非主評指標，此為額外佐證，不影響主評（AIGuard/unseen、StyleGAN2）結論。
| WildDeepfake | FS（in-the-wild）| Fake | ❌（v4 試用後棄用）| ⚠️ deprecated（語義重疊）|

**EFS 訓練政策**（2026-07-29 確立，2026-07-31 補完整理由）：EFS 圖片可留在 **Phase 1 分類器訓練**，但應排除在 **Phase 2 region head explainability 蒸餾**之外。StyleGAN2/StyleGAN3 的 DF40 版本暫不解壓、不加入任何訓練，維持 `stylegan2_test/fake` 作為乾淨、未觸碰過的 detection-only OOD 指標。

**完整理由（可供論文 Methods/Data section 引用）**：

- **Phase 1（分類）為什麼可以用 EFS**：Phase 1 的任務是「這張圖整體是不是被合成/操縱過」的全域判斷（real/fake/filter 三選一），不需要局部對比或定位。EFS（Entire Face Synthesis，整張臉從雜訊/latent code 生成，非以某張真實臉為基礎做局部修改）在紋理、頻域上會留下 GAN/diffusion 特有的合成痕跡（checkerboard artifact、頻域不規則性、融合邊界不連續），這正是 FFT branch 設計要捕捉的訊號。EFS 圖片是有效的「全圖皆假」訓練樣本，跟分類任務的粒度完全匹配。
- **Phase 2（region head 定位）為什麼不能用 EFS**：Phase 2 的任務是「操縱發生在圖片的哪個區域」，這個問題的前提是「存在一張未操縱的原圖可以比較」。EFS 圖片的問題在於：**整張臉都是生成的，沒有『原圖』可以比較，也就沒有『這裡被改了、那裡沒被改』的語意基礎**。FakeVLM teacher 對 EFS 圖片給出的「可疑區域」（例如「眼睛有不自然的痕跡」）本質上是對整張合成臉的局部隨意歸因，不是基於真實局部差異的判斷，用這種標籤去訓練 region head，等於教它學一個沒有 ground truth 支撐的任務。
- **對比 FS/FR/filter**：Face Swap（换臉）、Face Reenactment（表情驅動）、filter（美顏）都是「以一張真實臉為基礎做局部修改」，操縱區域有明確語意（換臉的邊界、表情驅動的五官、美顏的眼周/臉頰），region-level 標籤在這些類別上才站得住腳，這也是 Phase 2 蒸餾資料只用這些類別的原因。
- **不對稱待遇的自洽性**：這不是雙重標準，是因為 Phase 1 跟 Phase 2 問的是不同粒度的問題（「有沒有」vs「在哪裡」），EFS 對前者是有效訊號、對後者是語意不成立的訊號，兩邊政策不同完全符合各自的任務定義。

> ⚠️ **2026-07-31 StyleGAN3 identity 重疊發現（Ultimate Held-out Test Set 建置過程中）**：解壓 `Downloads/StyleGAN3.zip`（DF40版）後確認其 `cdf`（Fake_from_Celeb-real 588 + Fake_from_Youtube-real 300）與 `ff`（FaceForensics++ 140）三個子集的 identity 資料夾名稱，跟已進訓練的 SiT/DiT/ddim/pixart 完全相同（實測 588/588、300/300、140/140 全部 100% 重疊）——這是 DF40 benchmark 的設計方式：全部生成方法共用同一批 ~1,028 個 Celeb-DF/FF++ real identity 作為條件生成依據。**結論：StyleGAN3 只能證明「未見過的生成架構」，不能證明「未見過的身份」**，因為訓練集透過 SiT/DiT/ddim/pixart（各 3,000 張，統計上幾乎必然覆蓋這 1,028 人的大部分）早已看過同一批人臉的（不同方法）合成版本。
> - **命名降級**：StyleGAN3（以及原本 `stylegan2_test/fake` 的 99.7-99.9% OOD 數字）論文中不可稱為「identity-blind 泛化證明」，應標註為 **「unseen-generator, seen-identity」** 評測，跟 True Test 的 contamination bias 標註同一等級處理，不可過度宣稱。
> - **後續診斷 TODO（尚未執行，成本低，非阻塞）**：① ArcFace embedding + logistic regression 的 identity-only baseline，檢驗單靠身份能不能預測 fake/real（結果需謹慎解讀，因 ArcFace 對 GAN 生成臉的 embedding 本身可能因合成瑕疵失真，高準確率不等於確診 identity shortcut）；② 用官方 NVIDIA StyleGAN3 pretrained checkpoint 以 random Gaussian latent 生成全新、零身份依賴的補充驗證集（仍需留意 FFHQ style/quality 的 shortcut 風險，見 v3 教訓）。
> - **完整修復（identity-disjoint retrain，範圍大，另立專案，非本次 Ultimate Test Set 任務範圍）**：若診斷確認問題存在，需將 DF40 全部方法依 1,028 個 identity 切 train/test disjoint 後重新訓練，成本遠高於單純建 eval set，暫不排入本輪工作。

> ⚠️ **2026-07-31 Region Head v3 實驗（spatial feature map 架構修正）— 混合/負面結果，但找到更精確的根因**：`train_region_head_v3.py` 實作 conv5 pre-pool feature map（B,1024,7,7）+ 逐 region 幾何窗口 pooling，取代 v1/v2 的 pooled vector，直接修正 Spatial-Global Mismatch 結構問題；backbone 換成 v8.8（修正 backbone drift）。**結果**：left_cheek F1 0.000→0.016、right_cheek 0.000→0.013（技術上非零但仍近乎無法使用）；left_eye 反而退化到 0.000；macro F1=0.413（遠低於 v1 的 0.842，但 v1 數字已知有問題）；val_loss 在早期 epoch 後同樣不穩定爬升（best checkpoint 落在 epoch 4），與 v2 的不穩定模式一致，換架構沒有解決這個訓練動態問題。
> - **關鍵新發現：FakeVLM 標籤本身近乎退化，不是純架構問題**。查訓練資料（3,959 筆可用記錄）逐 region 正樣本比例：forehead/left_eye/right_eye/mouth **100.0%**、jaw **99.5%**、nose 75.6%，但 **left_cheek 與 right_cheek 都只有 0.4%（14/3,959）**。6 個 region 幾乎是全圖常數標籤（不看圖都能猜對），只有 cheek 是真正的判別任務，而其正樣本量（訓練集裡實際可能僅個位數到十餘筆）在統計上幾乎不可學。
> - **v1 的 F1=0.842 重新詮釋**：不只是「student 模仿 teacher 模板」，更精確地說是「6/8 的 label 在這批資料裡是近乎常數的退化分布，任何模型不看圖都能拿高分，只有 cheek 這 2/8 真正測試模型能力且必然失敗」——這是比先前「模板崩潰」說法更具體、更有殺傷力的量化證據，兩者同一根源（FakeVLM 輸出高度模板化）在不同角度的呈現。
> - **結論與後續**：架構修正是必要但不充分的；真正的瓶頸是 FakeVLM pseudo-label 對 cheek 類別的標註稀疏（模板幾乎不提「臉頰」），要解決需要：① 增加 cheek 相關訓練樣本（可能需要重新設計 FakeVLM prompt 或後處理引導它更常描述臉頰）、② 或接受 cheek 定位在 pseudo-label distillation 路線下不可行，論文誠實揭露此限制。**v3 未達部署標準，暫不接上 pipeline.py**，`REGION_HEAD_PATH` 維持指向 v1。

> ✅ **2026-07-31 No-image baseline 決定性驗證**：計算「完全不看圖、每個 region 永遠只猜訓練集多數類別」的 baseline，macro F1=**0.732**（forehead/left_eye/right_eye/mouth=1.000, jaw=0.998, nose=0.861, cheek兩項=0.000）。對比 v1 的 F1=0.842，**看圖帶來的實際資訊量只有 0.11**——v1 那個「看起來不錯」的數字裡，87%（0.732/0.842）是label退化白撿的分數，不是模型真的學到定位能力。這是目前對「F1=0.842是假象」最直接、可放進論文的量化證據。

> ✅ **2026-08-01 v8.10a（real規模擴大隔離實驗）完成 — real recall大幅逼近門檻，fake+filter如預期惡化**：Splits `v810a_train_real_fake.txt`（118,364，v8.8原始real+fake基礎 + round1 IMDB-WIKI 1,720+VGGFace2-train 297 + round2 IMDB-WIKI-expanded 12,059）+ filter class沿用`v86_train_filter.txt`完全不變（純real規模隔離實驗）。Init from v8.8。Best macro F1=0.9867。
> - **Gates**：shadow real recall **74.1%**（v8.9d-mini是61.4%，+12.7pp，最接近80%門檻的一版）；shadow filter recall 28.1%（與v8.8的26.3%幾乎打平，符合預期——filter class本輪完全未動）；True Test filter 94.0%✅；**fake+filter誤判5.67%（大幅惡化，未過≤2%，符合計畫預期"預期fake+filter會先惡化"）**；AIGuard/unseen AUROC **0.8180**✅（全系列最高，real多樣性擴大意外讓fake邊界更清楚）；CelebA 99.7%✅；StyleGAN2 99.8%✅。**4/7過關，v8.10a不部署（僅為過渡實驗）**。
> - **結論：real規模擴大假說方向確認正確**——單純把diverse real從2,017張加到14,076張（filter/fake完全不動），shadow real recall從v8.9d-mini的61.4%跳到74.1%，且AIGuard/unseen AUROC意外大幅提升。fake+filter誤判惡化到5.67%在計畫預期內，交由v8.10c處理。
> - **⚠️ 2026-08-03 補測v8.9d-mini/v8.10a的AIGuard/unseen AUROC，發現並解決方法論不一致問題**：簡報製作時發現這兩版當初沒記錄AUROC，第一次用`AIGuard/eval_crossdataset_v3_1.py --ckpt`補測得到v8.9d-mini=0.7410、v8.10a=0.8042，但複查時發現`AIGuard/train_v810b*.py`等多份訓練腳本docstring早已記錄v8.10a官方數字為**0.8180**，與補測結果不符。**根因查證**：`eval_crossdataset_v3_1.py`用`P(fake)+P(filter)`（not-real）當AUROC分數；而原始gate追蹤用的`eval_v89a_gates.py`（現因pipeline.py已為v8.11重構、`WEIGHTS_PATH`等介面不存在而無法直接執行）用的是**純`P(fake)`**——兩種是不同定義的指標，都正確、但不能混用比較。用`verify_v810a_auroc_methodology.py`獨立重現兩種算法：v8.10a同一個checkpoint，`P(fake)only`=**0.8180**（精確吻合歷史記錄），`P(fake)+P(filter)`=0.8042（吻合第一次補測）；再用`verify_v89d_mini_auroc_methodology.py`同法測v8.9d-mini：`P(fake)only`=**0.7846**。額外查證`eval_v811_gates.py`（v8.11的0.8112來源）計分邏輯，確認同樣是`P(fake)`（複合機率`p_manip*p_fake_given_manip`，不含filter）——**故v8.8(0.7043)/v8.9d-mini(0.7846)/v8.10a(0.8180)/v8.11(0.8112)這條ablation數列，正確、一致的版本是`P(fake)only`算法**，`P(fake)+P(filter)`版本（0.7410/0.8042）屬於方法論不一致的誤植，不應該混進同一欄比較，已在簡報與本文件更正。
> - **下一步**：v8.10b——在v8.10a的real基礎上，為round2新增的IMDB-WIKI-expanded真實照片生成對應matching filter class資料，測shadow filter recall能否跟進提升；之後v8.10c用targeted mined hard_neg（在更大real基礎上重新mining）修復fake+filter邊界。

> ⚠️ **2026-08-01 v8.10b（在v8.10a基礎上加matching filter）完成 — filter recall大躍進，但real recall意外倒退+fake+filter嚴重惡化**：Splits `v810b_train_filter.txt`（86,689，v86 filter基礎73,332 + round1 IMDB-WIKI-filter 1,622+VGGFace2-train-filter 289（沿用v8.9a既有資料）+ round2新生成IMDB-WIKI-expanded-filter 11,446）+ real+fake完全沿用`v810a_train_real_fake.txt`不變。Init from v8.10a（在其real-scale基礎上繼續fine-tune 5 epochs，非重新從v8.8開始）。Best macro F1=0.9882。
> - **Gates**：shadow real recall **61.7%**（v8.10a是74.1%，**意外倒退-12.4pp**，計畫原先預期real class不動應該維持不變，但實際上受filter class大量新增資料影響）；shadow filter recall **60.9%**（v8.10a是28.1%，**+32.8pp大躍進**，最接近70%門檻的一版）；True Test filter recall **95.2%**✅（全系列最高）；**fake+filter誤判10.20%（v8.10a是5.67%，進一步惡化近2倍，符合方向但幅度超出預期）**；AIGuard/unseen AUROC 0.8027✅；CelebA 99.6%✅；StyleGAN2 99.8%✅。**4/7過關（與v8.10a同數但體質更差）**。
> - **關鍵發現：filter規模擴大不是「只影響filter recall」的乾淨變數，而是全面挪動了三個類別的決策邊界**——filter recall大漲的代價不只是fake+filter誤判惡化（計畫預期內），還多了一個計畫外的real recall倒退（-12.4pp）。合理推測：round2新增的11,446張filter圖與round2的12,059張real圖來自同一批照片（僅差一個filter算法），模型可能學到「這批IMDB-WIKI-expanded照片的視覺特徵→傾向filter」的捷徑，連帶把部分真正的real也往filter方向拉。
> - **與v8.10a對照的完整7項門檻**：real 74.1%→61.7%（退）、filter 28.1%→60.9%（進）、True Test 94.0%→95.2%（進）、fake+filter 5.67%→10.20%（退，超出預期幅度）、AUROC 0.8180→0.8027（微退）、CelebA/StyleGAN2打平。**v8.10b不部署，且新出現的real倒退問題需要先與用戶討論再決定是否照原計畫進入v8.10c**（v8.10c設計是修fake+filter，但目前real recall倒退是計畫外的新問題，可能需要調整v8.10c範圍或先做歸因實驗）。

> 🔬 **2026-08-01 v8.10b-lite（round2 filter子取樣1/3，歸因實驗）完成 — 量與shortcut皆有貢獻，非單一因素**：`v810b_lite_train_filter.txt`（79,058，round2 filter從11,446子取樣至3,815=1/3），real+fake沿用v810a不變。Init from v8.10a。**Shadow結果**：real recall **70.0%**（v8.10a 74.1%、v8.10b 61.7%，介於兩者之間）；real→filter誤判16.6%（v8.10a是8.6%、v8.10b是24.1%，同樣介於兩者之間，未完全回到v8.10a水準）；filter recall **49.5%**（v8.10a 28.1%、v8.10b 60.9%，同樣介於兩者間）。**結論：real recall倒退是「量」與「paired-base shortcut」共同作用，非單一因素**——單靠減量無法完全解決，需要驗證disjoint-base設計是否能在不犧牲real recall的前提下拉高filter recall。下一步：v8.10b-disjoint，filter base改用從未進real class訓練的IMDB-WIKI照片（驗證發現：leftover pool達270,746張、7,033個identity，round1+round2合計僅用15,200張，餘量充足）。

> 🔬 **2026-08-01 v8.10b-disjoint（disjoint-base filter歸因實驗）完成 — paired-base shortcut假說未獲支持，根因是純filter資料量效應**：`v810b_disjoint_train_filter.txt`（81,559，v86 filter基礎 + round1 filter 1,911 + 新disjoint-base filter 6,316——base來源為IMDB-WIKI leftover pool中**從未進real class訓練**的照片，identity-level排除shadow/Ultimate重疊158個identity）。real+fake沿用v810a不變。Init from v8.10a。
> - **Shadow結果**：real recall **66.9%**、filter recall **52.7%**、fake+filter誤判**8.72%**。
> - **與v8.10b-lite（相近規模，paired-base，3,815張）對照**：lite在filter量少42%的情況下（3,815 vs 6,316），real recall反而更高（70.0% vs 66.9%）、filter recall相近（49.5% vs 52.7%）、fake+filter也相近（8.85% vs 8.72%）。**disjoint-base在volume更大的前提下，沒有展現出優於paired-base的real recall保護力**。
> - **量化驗證**：用v8.10a(0張,74.1%)→v8.10b(11,446張,61.7%)的paired-base趨勢線性內插至6,316張，預測real recall≈67.3%，與disjoint實測66.9%幾乎完全吻合——**disjoint-base的real recall完全落在paired-base的量-recall趨勢線上，沒有額外保護效果**。
> - **結論：「real與filter用同一批照片會造成shortcut」假說未獲支持**。真正機制更可能是單純的filter class資料量效應——filter class相對real class的規模／多樣性越大，決策邊界本身就會往real方向侵蝕，與filter base是否跟real共用照片無關。這是一個誠實的負面結果，推翻了v8.10b後提出的disjoint-base假說，避免後續繼續投入更多disjoint-base變體實驗。
> - **v8.10 系列現況彙整**（new filter volume / shadow real / shadow filter / fake+filter）：v8.10a（0 / 74.1% / 28.1% / 5.67%）、v8.10b-lite（3,815 / 70.0% / 49.5% / 8.85%）、v8.10b-disjoint（6,316 / 66.9% / 52.7% / 8.72%）、v8.10b（11,446 / 61.7% / 60.9% / 10.20%）——四個版本呈現清楚的Pareto trade-off，同一條real-vs-filter規模曲線上，沒有版本三個指標同時最佳。**v8.10b-lite在同時考慮real/filter/fake+filter三者的情況下是目前最均衡的選擇**，且不需要disjoint-base的額外資料工程。
> - **下一步**：以v8.10b-lite為基礎做v8.10c targeted hard_neg mining，修復fake+filter誤判（目標從8.85%壓回≤2%），filter recall（49.5%）雖仍未達70%門檻，但已是可控範圍內的最佳平衡點，留待後續視情況決定是否需要更大filter規模。

> 🔬 **2026-08-01 v8.10b dose-response（劑量反應）實驗完成 — fake+filter是門檻效應非線性劑量效應，dose-response策略未找到甜蜜點**：測試新增filter量600（dose600）與1,200（dose1200），init v8.10a，其餘沿用v8.10b系列設計（paired-base，round1 filter不變）。
> - **完整劑量-反應曲線**（新增filter量 → shadow real / shadow filter / fake+filter）：0（v8.10a）→74.1%/28.1%/5.67%；**600→72.4%/43.8%/8.20%**；**1,200→71.4%/37.4%/6.63%**；3,815（lite）→70.0%/49.5%/8.85%；6,316（disjoint）→66.9%/52.7%/8.72%；11,446（v8.10b）→61.7%/60.9%/10.20%。
> - **關鍵發現：fake+filter誤判不是劑量的平滑函數，而更像門檻效應**——僅新增600張filter（相對round2的11,446是5%的量），fake+filter就從5.67%跳到8.20%，跳升幅度已經接近3,815張（lite，8.85%）與6,316張（disjoint，8.72%）的水準。600→1,200→3,815→6,316之間fake+filter在6.6-8.9%區間震盪、無單調趨勢（dose1200的6.63%甚至低於dose600的8.20%，儘管量是兩倍），只有到達完整11,446張時才進一步惡化到10.20%。**shadow filter recall同樣不是嚴格單調**（dose600的43.8% > dose1200的37.4%），推測5-epoch單次fine-tune訓練本身的隨機性（mixup、資料洗牌）已經足以解釋這個量級的波動，不是量本身的因果反轉。
> - **對v8.10c mining策略的影響**：原本設計的dose-response策略假設能找到一個fake+filter落在4-5%（mining射程內）的低劑量甜蜜點，但**測試結果顯示：只要新增任何新filter資料，fake+filter幾乎立刻跳到6.6-8.9%區間，沒有更低的可行劑量**（除非完全不加新filter資料，回到v8.10a的5.67%起點，但那樣shadow filter recall完全沒有進步，等於没解決filter recall的問題）。按v8.9系列mining歷史（一輪約改善0.5-0.9pp），即使從最低的dose1200（6.63%）起跳，mining後預估落點約5.7-6.1%，仍達不到≤2%門檻。
> - **誠實結論：這是一個負面結果**，dose-response無法把mining起點壓進4-5%射程內，且v8.10系列目前所有「有filter recall實質進步」的分支，fake+filter都落在6.6%以上。需要與用戶討論根本策略調整（例如：mining目標是否要放寬、是否要接受目前v8.10a水準的filter recall先部署接受trade-off、或需要全新的方法而非「調filter量+mining」這個方向）。

> ✅ **2026-08-01 dose1200雜訊驗證（3次獨立重跑）完成 — 核心結論在雜訊範圍內仍然成立，但相鄰劑量比較不可信**：同一份`v810b_dose1200_train_filter.txt`（1,200張），init v8.10a，僅隨機種子不同（PyTorch/numpy預設不固定seed），重跑3次。
> - **結果**：原始跑=real 71.4%/filter 37.4%/fake+filter 6.63%；run2=real 69.7%/filter 43.8%/fake+filter 7.59%；run3=real 69.0%/filter 43.1%/fake+filter 7.93%。**Spread**：real跨度2.4pp（69.0-71.4%）、filter跨度6.4pp（37.4-43.8%）、fake+filter跨度1.3pp（6.63-7.93%）。
> - **診斷**：filter recall雜訊幅度（6.4pp）已經大到吃掉dose600(43.8%)與dose1200原始跑(37.4%)之間6.4pp的表面差異——**dose600 vs dose1200的相鄰劑量比較不可信**，run2/run3的filter recall（43.1-43.8%）反而更接近dose600，顯示dose1200原始跑的37.4%本身可能是雜訊低點，不是真實的「劑量越高filter recall反而越低」效應。
> - **但核心結論存活**：fake+filter三次重跑範圍6.63-7.93%，**沒有一次落在4-5%射程內**，最低點（6.63%）仍明顯高於mining可實際觸及的範圍（按v8.9歷史mining一輪約改善0.5-0.9pp，起點需≤3pp才有機會壓進≤2%）。**「任何新增filter資料都會讓fake+filter跳進6.6-8%區間、且dose-response策略找不到4-5%甜蜜點」這個結論在雜訊範圍內仍然成立**，因為即使是雜訊分佈的下界（6.63%）也遠高於4-5%目標區間。
> - **決策**：正式放棄「調整filter劑量+targeted mining」這條路線去解決fake+filter誤判。三條獨立路線（v8.9系列real擴充、v8.10系列filter擴充、本次劑量微調）都撞到同一個瓶頸，指向real/fake/filter三類別在同一個softmax機率空間內互相競爭是更根本的幾何限制，不是資料層面的量能解決。**下一步：v8.11-hierarchical classifier**——拆成兩層決策（Layer1: real vs manipulated；Layer2: manipulated情況下再判fake vs filter），讓real/manipulated邊界與fake/filter邊界解耦、各自獨立優化。作為全新獨立版本分支（不與v8.10系列的資料變動混合），以保持架構改動本身的乾淨歸因。

> 🔬 **2026-08-01 v8.11 Layer1（real vs manipulated二分類）訓練+驗證完成 — real recall達標，但暴露新的fake+filter洩漏問題**：`v811_layer1_train.txt`（191,696，v8.10a real+fake 118,364 + v86 filter 73,332，fake與filter合併為manipulated單一標籤）。Backbone/FFT從v8.8初始化（361 tensors載入，僅classifier head因shape不同隨機初始化）。15 epochs，best macro F1=0.9799（epoch 8）。
> - **Shadow eval（二分類）**：real recall **77.6%**（超越v8.10a的74.1%，且是純架構效應——資料配置完全來自v8.10a，代表拆成二分類確實讓real邊界受益，沒有被filter/fake內部競爭拖累）；fake_gan→manipulated 99.0%；fake_diffusion→manipulated 66.3%；filter→manipulated **50.2%**（遠優於v8.10a三分類下filter class僅28.1%的水準）；AUROC 0.7715。
> - **關鍵驗證：Layer1對fake+filter held-out stress圖片的洩漏率（錯誤累積天花板檢查）**：AIGuard/unseen fake基礎圖（未套濾鏡）就有**13.94%（40/287）被Layer1誤判為real**；套用8種濾鏡後平均洩漏率**6.25%（143/2,289）**，其中whitening_medium 18.8%、eye_enlarging 17.1%、face_reshaping 12.6%三種類型洩漏最嚴重，跟v8.8/v8.9/v8.10系列fake+filter誤判最弱的濾鏡類型高度重疊。
> - **誠實對照：這個洩漏率本身就已經比v8.8原本3-class的fake+filter總誤判率（1.35%，含real+filter兩種誤判方向）更差**——Layer1單獨的real洩漏（6.25%）已經超過v8.8三分類版本「誤判為real或filter」的總和。這代表hierarchical拆分雖然解決了real recall問題，但沒有自動繼承v8.8原本優秀的fake+filter防禦力；洩漏到real的圖片永遠到不了Layer2，是Layer2無論設計多好都無法挽救的硬天花板。
> - **結論：Layer1尚未達到可以直接進入Layer2設計階段的品質**，需要先処理這個新發現的洩漏問題（可能方向：把v8.8/v8.9d-mini驗證有效的fake+filter hard_neg資料，以"manipulated"標籤形式加入Layer1訓練，加強「濾鏡後的fake」在real/manipulated邊界上的辨識度）。

> 🔬 **2026-08-01 v8.11 Layer1-b（加入mined hard_neg修復洩漏）完成 — 洩漏率改善但未達中期目標，real recall完全沒被拖累**：交叉比對v8.9d-mini的1,050張targeted-mined hard_neg濾鏡類型分布（whitening 37.5%/eye_enlarging 34.7%/face_reshaping 25.3%/smoothing 2.5%），與Layer1洩漏最嚴重的三種類型（whitening 18.8%/eye_enlarging 17.1%/face_reshaping 12.6%）高度吻合，確認可直接沿用不需重新mining。`v811_layer1b_train.txt`（207,446，Layer1 base 191,696 + mined hard_neg 1,050×15x oversample=15,750）。Init from Layer1 checkpoint（同2-class head，完整load），5 epochs fine-tune。
> - **Leak-to-real結果**：AIGuard/unseen基礎fake洩漏13.94%→**8.01%**；套濾鏡後總洩漏6.25%→**5.11%**（-1.14pp）。個別類型：whitening_medium 18.8%→15.7%、eye_enlarging 17.1%→14.3%、face_reshaping 12.6%→10.1%，三者皆有改善但都還在10%以上，**未達≤3%中期目標**。
> - **Shadow real recall結果**：77.6%→**77.2%**（幾乎打平，僅-0.4pp），**沒有出現v8.9/v8.10系列反覆出現的翹翹板效應**——加入manipulated class的hard_neg沒有拖累real邊界；意外收穫：fake_diffusion→manipulated recall 66.3%→**75.9%**（+9.6pp）、AUROC 0.7715→**0.8024**。
> - **結論：方向正確、單輪改善幅度不足**。這符合v8.9系列mining的歷史模式（一輪約改善0.5-1.5pp，不是一次到位）。與v8.9系列不同的關鍵好消息是：**這次改善manipulated判斷力沒有以犧牲real recall為代價**，證實hierarchical拆分確實讓兩條決策邊界互相解耦——這是三分類架構做不到的。
> - **待決策**：是否再加一輪mining（例如擴大oversample倍率、或針對whitening/eye_enlarging/face_reshaping三種仍然洩漏最重的類型做更精準的第二輪margin mining）以求真正逼近≤3%，或接受5.11%為Layer1當前基線、先進入Layer2設計階段（因為Layer1已證明拆分本身有效，洩漏率可以是後續持續優化項目，不一定要在進Layer2前完全解決）。

> ✅ **2026-08-01 v8.11 Layer1-c（第2輪targeted mining）完成 — 洩漏率逼近≤3%目標，real recall穩定維持70%以上**：從v89d candidate pool剩餘26,829張候選（僅whitening/eye_enlarging/face_reshaping三種類型）用Layer1b打分，margin閾值P(real)≥0.35，挖到303張新困難樣本（yield 1.13%，per-type：face_reshaping 121/whitening 92/eye_enlarging 90）。`v811_layer1c_train.txt`（211,991，Layer1b base + 303×15x oversample=4,545）。Init from Layer1b，5 epochs fine-tune。
> - **Layer1系列完整演進**（leak-to-real套濾鏡後總計 / 基礎未套濾鏡leak / shadow real recall）：Layer1（無mining）→6.25% / 13.94% / 77.6%；Layer1b（+1,050張round1 mined）→5.11% / 8.01% / 77.2%；**Layer1c（+303張round2 mined）→3.93% / 6.27% / 75.5%**。
> - **個別濾鏡類型洩漏率演進**：whitening_medium 18.8%→15.7%→**13.2%**；eye_enlarging 17.1%→14.3%→**9.4%**；face_reshaping 12.6%→10.1%→**7.7%**——三輪迭代持續改善，未出現天花板效應。
> - **Real recall代價可控**：77.6%→77.2%→75.5%，兩輪mining總共只讓real recall掉2.1pp，遠低於v8.9/v8.10系列動輒10+pp的翹翹板幅度，且始終遠高於70%驗收底線。
> - **結論：Layer1已非常接近≤3%中期目標（差0.93pp），且沒有出現real recall被拖累的結構性風險**。兩輪mining呈現穩定遞減但非停滯的改善曲線（-1.14pp→-1.18pp），暗示還有繼續逼近的空間，但邊際樣本量已經很小（第2輪只挖到303張，遠少於第1輪的1,050張，反映真正困難樣本池正在收斂）。**判定：可以視為Layer1目前狀態已足夠進入Layer2設計階段**，剩餘的3.93%可以留待Layer1+Layer2完整串接後的系統性驗收再視情況決定是否要再迭代。

> 🔬 **2026-08-02 v8.11 Layer2（fake vs filter）訓練+完整pipeline驗證 — fake+filter defense仍未追平v8.8，且發現Layer2嚴重filter recall退化**：`v811_layer2_train.txt`（146,425，base fake 52,798 + base filter 73,332 + hard core（v89d mined 1,050 + round2 mined 303）×15x oversample=20,295，佔訓練資料13.9%）。Init from v8.8，15 epochs，best macro F1=0.9981（val集上fake=0.997/filter=1.000，看似極佳）。
> - **Shadow eval（Layer2單獨、忽略Layer1閘門，直接測真實fake/filter標籤）**：fake_gan→fake 100.0%；fake_diffusion→fake 69.4%；**filter→filter僅15.7%（84.3%的真實filter圖被誤判為fake）**；AUROC僅**0.5186（幾乎等同隨機）**。
> - **根因診斷**：15x oversample的hard core（fake+filter邊界樣本，正確標籤是fake）大量出現在訓練集中，這批樣本的視覺特徵天生就介於fake和filter之間；模型為了正確分類這些邊界樣本，把決策邊界大幅往「fake」方向推，代價是犧牲了對真正filter class的辨識力。這跟v8.9/v8.10系列「一個類別佔比變大會侵蝕另一類別」的根本問題是同一種機制，只是現在發生在Layer2內部而非Layer1。
> - **完整pipeline端到端結果（Layer1c+Layer2串接，AIGuard/unseen fake+filter stress test）**：TOTAL誤判率**3.93%**——與Layer1c單獨的洩漏率完全相同（3.93%=3.93%），代表**Layer2在這個特定測試集上沒有貢獻額外錯誤，也沒有修正任何Layer1的洩漏**（因為凡是通過Layer1的圖片，Layer2幾乎都正確判fake——這正是Layer2「傾向predict fake」偏見的正面效果，剛好符合這個測試集的需求）。**與v8.8原始1.35%相比，v8.11目前的end-to-end fake+filter defense仍然更差（3.93% > 1.35%）**。
> - **誠實結論：v8.11 hierarchical目前不能视為可替代v8.8的候選**。雖然real recall大幅超越（75.5% vs v8.8的16.2%），但代價是①fake+filter defense尚未追平（3.93% vs 1.35%）②Layer2對真實filter圖片的辨識力嚴重受損（shadow filter recall 15.7%，這是全新發現的問題，會直接影響filter class的可解釋性輸出正確性）。**需要先修復Layer2的oversample策略**（可能方向：降低15x oversample倍率、或在Layer2訓練中額外納入更多易分辨的filter正樣本做平衡、或改用class-balanced loss取代簡單oversample），重新驗證filter recall回升後，再評估完整pipeline的end-to-end數字是否能追上或超越v8.8。

> ⚠️ **2026-08-02 v8.11 Layer2-b calibration（降oversample+filter class weight加權）— 幾乎無效，且發現更根本的重新框定**：`v811_layer2b_train.txt`（132,895，hard core oversample 15x→5x，佔比13.9%→~7.6%）+ 訓練時額外對filter class weight手動再乘2.5x（auto weight基礎上）。Init重新從v8.8（非從有偏見的Layer2 checkpoint fine-tune），5 epochs快速驗證。
> - **Shadow eval結果**：filter recall 15.7%→**22.4%**（+6.7pp，仍遠低於50%中期目標）；fake_diffusion recall **69.4%→59.8%（-9.6pp，反而退步）**；AUROC 0.5186→0.5124（幾乎沒變，依然接近隨機）。
> - **重新框定：問題可能不是（純粹）oversample倍率，而是shadow_filter本身對filter class而言就是一個持續存在的OOD/domain gap來源**——回顧全專案歷史：v8.8（3-class，未受任何v8.11 hard_neg汙染）shadow filter recall僅**26.3%**；v8.10a（real擴大、filter未變）shadow filter recall**28.1%**；兩者都遠低於True Test filter recall的94%+。這代表「shadow_filter（自建filter pipeline套用於VGGFace2）」這個特定OOD來源，對filter class來說本身就難、且是貫穿v8.8→v8.10→v8.11的持續現象，不是Layer2 hard_neg新引入的問題。Layer2b的22.4%其實與v8.8/v8.10a的基準（26-28%）已經接近同一量級，**oversample/class weight的校準空間可能本來就有限，因為真正瓶頸是filter class的域泛化，不是loss/sampling設計**。
> - **待決策**：50%中期目標可能設定過於樂觀（因為連未受汙染的v8.8基準都只有26.3%），需要與用戶討論是否調整目標、或改研究filter class domain gap本身（類似real class在v8.9系列走過的路徑：診斷→擴充多元filter來源），而非繼續在Layer2內部做loss/sampling微調。
> - **✅ 2026-08-02 拍板：Gate重新框定**——Shadow filter recall從「必須過的P0 gate（原訂≥70%）」重新定位為「robustness stress test / OOD benchmark」，不再是v8.11部署的阻斷條件。Phase 1主要gate維持：True Test filter recall（≥92%，訓練分布內的filter偵測能力）、fake+filter誤判（≤2%）、Shadow real recall、AIGuard/unseen AUROC、CelebA real recall、StyleGAN2 fake recall。Shadow filter的數字（22-28%區間）誠實報告+分析原因，寫入論文Limitations/Future Work，不擋主線；filter域泛化若要進一步研究，另立獨立支線（見TODO.md C1章節），非本輪Layer2 calibration範圍。此決策已同步寫入 `TODO.md` 最高優先區塊，兩份文件保持一致。

> ✅ **2026-08-02 v8.11 Layer2 calibration系列結論：原始Layer2（無手動加權）才是最佳選擇，calibration嘗試net-negative**：Layer2c（oversample 2x + filter weight×1.5，比Layer2b更保守）訓練完成，shadow filter recall 21.0%（與Layer2b的22.4%接近，calibration強度不敏感）、fake_diffusion recall **60.5%（仍比原始Layer2的69.4%低8.9pp，沒有隨著加權倍率降低而回升）**。
> - **完整Layer2變體對照表**：
>
> | 變體 | oversample | 手動filter權重 | Shadow filter | Shadow fake_diffusion | Shadow AUROC | End-to-end fake+filter |
> |---|---|---|---|---|---|---|
> | Layer2（原始） | 15x | 無（auto≈1.0，天然balance） | 15.7% | **69.4%** | 0.5186 | **3.93%**（最佳）|
> | Layer2b | 5x | ×2.5 | 22.4% | 59.8% | 0.5124 | 未測 |
> | Layer2c | 2x | ×1.5 | 21.0% | 60.5% | 0.5054 | 4.33%（比原始差）|
>
> - **關鍵發現：手動filter class weight加權（不論2.5x或1.5x）對filter recall的邊際貢獻很小（15.7%→21-22%，calibration強度不敏感、兩種倍率結果幾乎相同），卻穩定犧牲約9pp的fake_diffusion recall**，且在生產最關鍵的end-to-end fake+filter誤判率上，Layer2c（4.33%）反而比不加任何手動權重的原始Layer2（3.93%）更差。**這代表對Layer2做loss/sampling層面的手動干預是net-negative的**——filter recall的域泛化瓶頸（詳見Layer2-b條目分析）沒辦法透過調整訓練時的類別權重解決，反而會擾動fake_diffusion這個原本表現良好的子類別。
> - **拍板：v8.11 Phase 1候選正式鎖定為 Layer1c + 原始Layer2（無手動加權）**，不再繼續在Layer2內部做calibration微調。End-to-end fake+filter誤判3.93%（仍未追平v8.8的1.35%，但real recall大幅超越：75.5% vs 16.2%）。Shadow filter recall 15.7%（低於v8.8的26.3%/v8.10a的28.1%基準，但已依2026-08-02拍板重新框定為非P0 robustness benchmark，不阻擋主線）。
> - **下一步**：以 Layer1c + Layer2（原始版）為v8.11最終候選，執行完整7項gate評估（True Test filter recall、AIGuard/unseen AUROC、CelebA real recall、StyleGAN2 fake recall），產出v8.8 vs v8.11完整對照表。

> ✅ **2026-08-02 v8.11完整7項gate評估完成（Layer1c + 原始Layer2）— 4/6硬性gate過關，全面優於v8.8的4項AUROC/CelebA/StyleGAN2/TrueTest表現**：
>
> | Gate | v8.8 | v8.11（Layer1c+Layer2） | 判定 |
> |---|---|---|---|
> | Shadow real recall（≥80%） | 16.2% | **75.5%** | ❌ 未過但+59.3pp巨幅進步 |
> | Shadow filter recall（原≥70%，已重新框定為非P0 robustness benchmark） | 26.3% | 15.7% | 不阻擋主線，見上方框定說明 |
> | True Test filter recall（≥92%） | 94.4% | **94.0%** | ✅ 打平 |
> | fake+filter誤判（≤2%） | 1.35% | 3.93% | ❌ 未過，但遠優於v8.9a的5.84%起點 |
> | AIGuard/unseen AUROC（≥0.70） | 0.7043 | **0.8112** | ✅ 大幅優於，全系列最佳等級 |
> | CelebA real recall（≥95%） | 99.7% | **99.7%** | ✅ 打平 |
> | StyleGAN2 fake recall（≥95%） | 99.8% | **99.7%** | ✅ 打平 |
>
> - **⚠️ 2026-08-02 複查修正：原記錄誤寫「6項中5項過關」，實際核對表格為4項過關（True Test/AUROC/CelebA/StyleGAN2）+2項未過（Shadow real/fake+filter）=4/6，非5/6，此處更正**（Shadow filter已重新框定不計入硬性gate）。**整體判定：v8.11在幾乎所有維度追平或大幅超越v8.8，唯二尚未達標的是Shadow real recall（75.5% vs 80%門檻，僅差4.5pp）與fake+filter誤判（3.93% vs 2%門檻）**——但兩者都遠優於三分類時期任何嘗試過的中間版本（v8.9a的real 54.5%/fake+filter 5.84%）。
> - **對比v8.8的核心trade-off**：v8.11用fake+filter誤判從1.35%惡化到3.93%（+2.58pp）的代價，換來real recall從16.2%暴增到75.5%（+59.3pp）、AIGuard/unseen AUROC從0.7043提升到0.8112（+0.1069）。這是一個in-domain防禦力小幅犧牲換取OOD real泛化能力巨幅提升的交換，且沒有三分類時期那種「怎麼調都在同一條Pareto線上打轉」的僵局——hierarchical拆分證實了架構本身可以突破三分類的結構性限制。
> - **是否可替代v8.8的判斷**：技術上v8.11在4/6硬性gate與所有「打平或更好」的指標上明顯優於v8.8，唯一的疑慮是fake+filter誤判仍未達≤2%門檻。這是否構成部署阻斷，需要與用戶討論——若接受3.93%（仍是個位數低誤判率，且對應的real recall/AUROC進步幅度極大），v8.11可視為Phase 1新的最佳候選；若堅持≤2%不可退讓，則需要回頭專注在fake+filter邊界修復（例如更深入的Layer2域研究，或考慮Layer1閘門加上信心閾值降低誤放manipulated入Layer2但誤判為real的比例）。

> ✅ **2026-08-02 Region Head v4（eye_enlarging專用，Landmark GT訓練）完成 — Phase 2 region head系列首次確認真實訊號**：`AIGuard/train_region_head_v4.py`，沿用v3已修正的`SpatialRegionHead`架構（conv5 pre-pool feature map + geographic window pooling），標籤來源改為`generate_landmark_gt.py`產出的Landmark/LAB-diff GT（僅eye_enlarging子集，7,999張，train 6,398/val 1,599），backbone凍結v8.8，30 epochs，best checkpoint epoch 21。
> - **前置發現（視覺化A3）推翻了「85-100% positive rate是校準bug」的假說**：`visualize_lab_diff_bleed.py`人工檢視LAB diff heatmap疊加region框後確認，whitening/smoothing的高positive rate是真實全臉效果（LAB diff完整填滿filter pipeline的`_skin_mask`橢圓遮罩），不是mask羽化bleed或雜訊；face_reshaping則查出根因是`apply_face_reshaping`的warp半徑為**固定60px常數**（未依人臉尺寸縮放），全量7,997張統計顯示各region正樣本率飽和在77-100%。相對地`apply_eye_enlarging`的半徑=`eye_width×radius_factor`自動隨偵測人臉尺寸縮放，這正是why eye_enlarging在全量7,999張統計仍保持清楚區辨力（眼睛97%、鼻頰88-100%因warp溢出、嘴巴/下巴僅17-18%、額頭29%）的技術原因。**決策：region-level 8分類GT只對eye_enlarging有意義，其餘三種濾鏡改用「whole-face, GT-backed」的較粗粒度explanation claim**（見TODO.md論文claim草稿）。
> - **Region Head v4結果**：Per-region F1：forehead 0.438、left_eye 0.833、right_eye 0.817、nose 0.994、left_cheek 0.772、right_cheek 0.832、mouth 0.475、jaw 0.431。Macro F1=0.699。
> - **No-image trivial baseline對照**（沿用v1驗證時的方法論）：forehead/mouth/jaw三個region正樣本率均<30%，trivial「永遠猜多數類別」baseline在這三個region上F1恆為0，baseline macro F1=0.607。**實際模型macro F1=0.699，高於trivial 0.092**，且forehead/mouth/jaw這三個trivial baseline拿0分的region，v4實際達到0.43-0.48——證明模型真的學到辨識這些region裡的稀疏正樣本，非重演v1「6/8 region近乎常數標籤」的label degeneracy問題。
> - **與v1/v3對照**：v1表面macro F1=0.842，但87%（0.732/0.842）是trivial baseline灌水，真實訊號僅0.11；v3（FakeVLM標籤，8-region全部訓練）macro F1=0.413，cheek F1僅0.013-0.016，瓶頸在FakeVLM pseudo-label對cheek稀疏。**v4是Phase 2 region head系列（v1→v2→v3→v4）第一個確認帶有真實圖像判讀訊號、且誠實限定在真正具區辨力資料子集（eye_enlarging）上訓練與報告的版本**，訊號量級（0.092）與v1的真實訊號（0.11）相近，但沒有混入其他5個近乎常數標籤的region去墊高數字。

> 📋 **2026-08-02 XAI方法正式對照（Grad-CAM++ vs LRP-approx vs region_head_v4 vs pixel-diff baseline）完成 — 誠實負面結果：region_head_v4未明顯贏過Grad-CAM++**：`xai_eval_protocol.py`的`compare_methods()`，範圍限定eye_enlarging（唯一驗證過region-level GT具區辨力的濾鏡類型），100張paired樣本，top_frac=0.15二值化，GT為landmark/LAB-diff pipeline產出的positive region聯集。
>
> | 方法 | IoU↑ | Pointing Game↑ | IINC↓ | 資訊量 |
> |---|---|---|---|---|
> | Grad-CAM++ | **0.467** | 0.820 | **0.076** | 僅看filtered圖 |
> | LRP-approx（InputXGradient） | 0.130 | 0.390 | 0.214 | 僅看filtered圖 |
> | region_head_v4 | 0.261 | **0.850** | 0.157 | 僅看filtered圖 |
> | pixel-diff baseline | 0.311 | 0.880 | 0.024 | **看base+filtered配對**（額外資訊，非同條件對照，僅供下限參考） |
>
> - **在三個「僅看單張filtered圖」的公平對照方法中，Grad-CAM++在IoU和IINC兩項指標上都明顯優於region_head_v4**（IoU 0.467 vs 0.261；IINC 0.076 vs 0.157，越低越好）；region_head_v4僅在Pointing Game上以些微差距領先（0.850 vs 0.820）。LRP-approx（InputXGradient近似）三項指標都是三者中最差。
> - **誠實解讀**：Pointing Game只檢查「單一最大激活點是否落在GT區域內」，是較粗略的指標；IoU要求整個高激活區域的形狀/範圍都要跟GT對齊，是更嚴格的定位品質指標。region_head_v4贏Pointing Game、輸IoU的組合，代表它的峰值位置抓得到眼睛，但整體熱區的形狀/範圍比Grad-CAM++鬆散、不夠貼合GT邊界。**這代表v8.8分類器本身的Grad-CAM++ attention，在eye_enlarging這個任務上已經有相當不錯的定位能力，不一定需要額外訓練一個region head才能做到好的定位**——這跟原先「需要專門訓練的region head才能解決定位問題」的預設有落差，是一個對論文而言重要、值得誠實揭露的發現，而非可以隱藏的失敗結果。
> - **✅ 2026-08-02 一致性檢查（face_reshaping、whitening）完成 — 確認為結構性現象，非eye_enlarging特例，拍板直接寫入論文不重訓**：低成本sanity check，用region_head_v4（僅在eye_enlarging訓練過，這裡是分布外泛化測試）對另外兩種濾鏡類型各跑100張。
>
> | 濾鏡 | Grad-CAM++ IoU | region_head IoU | Grad-CAM++ IINC | region_head IINC | Pointing Game（兩者）|
> |---|---|---|---|---|---|
> | eye_enlarging | 0.467 | 0.261 | 0.076 | 0.157 | GC 0.820 / RH 0.850 |
> | face_reshaping | 0.466 | 0.391 | 0.027 | 0.051 | GC 0.920 / RH 0.920（平手）|
> | whitening | 0.448 | 0.280 | 0.017 | 0.089 | GC 0.880 / RH 0.890 |
>
> **三種濾鏡類型上Grad-CAM++在IoU和IINC都一致優於region_head_v4，region_head_v4至多打平或小勝Pointing Game，同一個模式重複出現300次獨立比較（3類型×100張）**——確認這是結構性發現（v8.8分類器的Grad-CAM++ attention本身已有不錯定位能力），不是eye_enlarging這個資料子集的偶然結果。LRP-approx（InputXGradient）在三種類型上都是最差方法，同樣一致。
> - **拍板：不投入IoU-based loss重訓region_head_v4**，直接把此發現寫入論文Discussion。理由：①歷史上這類「同資料換個loss/監督訊號」的改動在本專案中效益普遍不大（呼應v8.9c加49% hard_neg僅換0.44pp的報酬遞減教訓）；②這個中性/負面結果本身已經是高品質、有貢獻的科研發現——Pointing Game vs IoU的落差揭示了「解釋方法評估時指標選擇會導向完全不同結論」這個方法論議題本身值得討論；③v1→v3→v4的label degeneracy故事線鋪陳下，v4已證明是「真訊號版本」（vs trivial baseline +0.092），這次的結果更精確的說法是「即使學到合理訊號，也沒有勝過現成的Grad-CAM++」，而非「region head失敗了」。

> ⚠️ **2026-08-02 DF40 EFS held-out benchmark執行完成 — 數字極高但發現重大方法論陷阱，不可直接與文獻比較**：`eval_df40_benchmark.py`，v8.11對sd2.1/DiT/SiT/ddim/pixart五種EFS方法各抽1,000張（從v8.5/v8.8/v8.10a訓練split皆未用過的leftover pool），配對3,000張CelebA test real，計算per-method recall+AUROC。
>
> | Method | Fake recall | AUROC (vs CelebA real) |
> |---|---|---|
> | sd2.1 | 99.5% | 0.9999 |
> | DiT | 99.9% | 1.0000 |
> | SiT | 99.9% | 0.9999 |
> | ddim | 99.9% | 0.9999 |
> | pixart | 99.9% | 1.0000 |
> | **Overall** | — | **0.9999** |
>
> - **❌ 關鍵誠實檢查：這個數字不能拿來跟DF40論文的Protocol-2 baseline（Xception 0.586~RFM 0.644）比較，比較會嚴重誤導讀者**。原因：論文的Protocol-2測的是**跨domain泛化**（train on FF domain, test on CDF domain，訓練時完全沒見過CDF這個資料域的任何樣本，是真正的distribution shift測試）；而本次benchmark測的是**同method+同domain混合分布下的held-out樣本**（v8.11訓練時cdf/ff兩域都用了，這次只是抽從未被抽樣進訓練的「剩餘」圖片，本質上仍是同一個訓練分布內的held-out set，不是跨域泛化測試）。這兩個任務難度天差地遠——我們的0.9999是「在已見過的方法+域混合分布下考剩下的題目」，論文的0.586-0.644是「在完全沒見過的域上考試」，**用我們的數字宣稱「贏過文獻SOTA」會是嚴重的overclaim，不可放進論文当作正面比較結果**。
> - **這個benchmark真正證明的是**：①沒有train/test洩漏（乾淨排除已用樣本）；②v8.11對已訓練過的5種EFS方法有近乎完美的in-distribution held-out recall，是一個健全性檢查（sanity check），不是新發現。**真正有意義的跨分布泛化證據仍是AIGuard/unseen AUROC=0.8112**（AIGuard/unseen是完全獨立的資料來源，才是本專案真正的「unseen」測試）。
> - **論文寫法建議**：不要把這組數字跟論文Protocol-2 baseline並列比較；可以誠實描述為「in-distribution held-out sanity check，確認方法層面無資料洩漏且對已訓練方法保有近乎完美召回率」，並明確區分於AIGuard/unseen這個真正的跨分布評估。

> ✅ **2026-08-02 Alibaba filter OOD雙重查證+v8.11實測完成 — 確認是真正跨域證據，可與AIGuard/unseen並列成兩項headline跨域結果**：用戶提出跟DF40同等懷疑態度質疑「Megvii/Alibaba的99.9-100%是否又是identity shortcut或eval pipeline不一致造成」，逐一查證：
> - **✅ Identity overlap查證（乾淨）**：比對訓練用Megvii資料（`FFHQ_megvii_four_process`+`FFHQ_four_process`，7,694個唯一FFHQ底圖index，範圍60002-69999）與Alibaba OOD eval資料（`FFHQ_ali_process`，3,000個唯一FFHQ底圖index，範圍17000-19999）——**兩者index範圍完全不相交，overlap=0**。RetouchingFFHQ資料集本身把70K FFHQ底圖池切成不重疊的index區塊分給各公司，不是巧合。**確認Alibaba OOD不是identity shortcut**，跟StyleGAN3那種需要「unseen-algorithm, seen-identity」降級標註的情況不同，這裡是真正的跨身份+跨演算法泛化測試。
> - **✅ Eval pipeline一致性查證**：`AIGuard/eval_ali_ood.py`原本就用`preprocess_jpeg(quality=85)`（明確標註「Matches pipeline.py's inference-time JPEG canonicalization」），與目前pipeline.py一致，不是v8.7踩過的那種前處理不一致陷阱。
> - **✅ 補測v8.11實際數字**（原99.9-100%數字僅測過v8.6/v8.7/v8.8，從未在v8.11上跑過）：`AIGuard/eval_ali_ood_v811.py`，21,151張，**overall recall=97.8%**（EyeEnlarging 97.9%、FaceLifting 96.5%、Smoothing 99.8%、Whitening 97.2%；三種強度30/60/90皆97.7-98.1%，強度間無明顯差異）。比v8.6-v8.8的99.9-100%略低，方向與True Test filter recall（v8.11的94.0% vs v8.8的94.4%）的小幅下降一致，合理。
> - **結論：Alibaba OOD 97.8%是可信、可引用的headline跨域證據**，可與AIGuard/unseen AUROC=0.8112並列成本文filter/fake兩側的「真正跨域泛化」代表數字（相對地，DF40 benchmark的0.9999已誠實框定為in-distribution sanity check，不算跨域證據）。Filter類的跨域證據缺口至此已被現有資料填上，不需要再追Tencent（申請未核准）或勉強套用RetouchingFFHQ MAM文獻數字。

> ✅ **2026-08-02 CelebA real OOD雙重查證完成 — 確認第三個headline跨域數字**：用戶要求對CelebA 99.7%（v8.11）比照Alibaba做同等級查證，避免論文出現「有些數字查過overlap、有些沒查」的不對稱嚴謹度。
> - **✅ Identity/partition overlap查證**：CelebA官方`list_eval_partition.txt`協定本身就是identity-disjoint設計（前8,000個身分=train、接下來1,000個=val、最後1,000個=test，身分完全不重疊，這是CelebA論文的官方切分，非本專案自訂）。本地檔案層級逐一驗證：`celeba_train`（20,000張）100%屬於partition=0、`celeba_test`（19,962張）100%屬於partition=2、`celeba_val`（5,000張）100%屬於partition=1，**零混用**，未重演v8.10系列hard_neg資料夾那種意外搞混的風險。
> - **✅ Eval pipeline一致性查證**：`eval_v811_gates.py`（產出v8.11 99.7%數字的腳本）直接import `pipeline.preprocess_jpeg`，其`transform_infer`/`DualBranchModel`/Layer1→Layer2決策邏輯與pipeline.py的`hierarchical_predict()`架構與數值完全一致（並行實作但邏輯相同），非v8.7踩過的前處理分岔陷阱。
> - **結論：CelebA real recall=99.7%（v8.11）是可信的第三個headline跨域證據**，與Alibaba filter OOD=97.8%、AIGuard/unseen fake AUROC=0.8112並列成三個class各自的「真正跨域泛化」代表數字。**Shadow real recall=75.5%（v8.11）維持誠實框定為「未達80%門檻的robustness benchmark」，不與CelebA混為一談**——CelebA測的是「同樣是網路自然人臉照片、不同partition」的OOD，Shadow real測的是「完全不同身分來源+更貼近未來部署場景」的robustness壓力測試，兩者難度與定位不同，論文中應分開陳述，不可只挑CelebA漂亮數字而略去Shadow real的落差。

> ⚠️ **2026-08-01 資料完整性bug：重新命名hard_neg資料夾意外弄斷v8.8舊split — 已修復**：建v8.9c時把原始`fake_filter_hard_neg`資料夾改名為`_v88_backup`後在原路徑生成新的大池，導致`v88_train_real_fake.txt`裡~17,725筆指向原hard_neg檔案的路徑全部失效（訓練v8.10a時才被DataLoader FileNotFoundError揭露）。**修復**：用robocopy merge（`/XC /XN /XO`，只補缺不覆蓋）把backup資料夾內容合併回現有`fake_filter_hard_neg`，兩批hard_neg（v8.8原始17,725 + v8.9c新增26,447）現在並存於同一資料夾。修復後驗證：`v88_train_real_fake.txt`全部104,288筆路徑、`v810a_train_real_fake.txt`全部118,364筆路徑皆100%存在。**教訓：重新命名/搬移任何已被split檔案引用（絕對路徑）的資料夾前，必須先確認沒有split正在依賴該路徑**，這類重構應優先用複製而非移動/改名。

> 📋 **2026-08-01 v8.9e-focal（focal loss實驗）— 無效，甚至略差於CE loss**：`FocalLoss`（gamma=1.0，per-class weight同CE版本）取代`CrossEntropyLoss`，資料/epoch/LR/init完全同v8.9d-plus（1,242張mined，15x oversample，from v8.9c）。結果：fake+filter **3.01%**（v8.9d-plus的CE版本是2.75%，v8.9d-mini的CE版本是2.70%——focal loss不但沒改善,還略差於兩個CE基準）。其餘gates打平（shadow real 63.4%、AUROC 0.7905✅、CelebA 99.8%✅、StyleGAN2 99.9%✅、True Test filter 94.0%✅）。**結論：目前v8.9系列表現最好的仍是v8.9d-mini（fake+filter 2.70%，離≤2%差0.7pp），focal loss這條路未證實有效，需與用戶討論下一步（換gamma值、換loss設計、或接受目前最佳結果討論Pareto tradeoff）。**

> 📋 **2026-08-01 v8.9d Paired mining + 歸因實驗 — paired mining無增量，轉向focal loss**：
> - Paired filter-sensitivity mining（`mine_v89d_paired.py`，條件A/B/C：base自信但filtered信心崩潰/P(real)大升/P(fake)大降）：檢查20,000張base×2變體=40,000次評估，僅選中**192張（0.48%）**，比原本margin<0.5的789張更少——條件比預期嚴格。方法別分布極不均：ddim 128/8,000(1.6%)遠高於其他方法（sd2.1 0.20%/DiT 0.26%/SiT 0.33%/pixart 0.01%），但部分confound檢查（濾鏡後P(fake)平均分布，5方法皆0.889-0.908相近，ddim非離群值）不支持「ddim濾鏡後普遍信心低」的簡單解釋，真正原因待查（base scores未保留，無法完整驗證），**記錄為hypothesis非結論**。
> - **v8.9d-plus歸因實驗**：合併margin-mined(1,050)+paired-mined(192)=1,242張，15x oversample，CE loss，從v8.9c訓練。結果fake+filter **2.75%**（v8.9d-mini是2.70%，幾乎持平/雜訊範圍內）——**確認paired mining的192張與margin-mined重疊，無增量訊號**。
> - **下一步**：轉向v8.9e-focal（focal loss gamma=1.0，沿用1,242張mined set，其餘不變），利用已挖到的難樣本放大其梯度權重，而非繼續挖更多樣本。

> ✅ **2026-08-01 v8.9d-mini sanity check 完成 — mining方向確認有效**：1,050張mined hard examples（margin<0.5，兩輪mining合併）×15 oversample，從v8.9c fine-tune 5 epochs。**fake+filter誤判 3.31%→2.70%（-0.61pp）**，優於v8.9c暴力加大hard_neg 49%換來的0.44pp改善，且成本低很多（1,050 vs 8,722張）。副產物：fake_diffusion recall意外跳升48.8%→63.2%，AIGuard/unseen AUROC提升至0.8428（四版最佳）。Shadow real recall微降63.8%→61.4%（雜訊範圍內）。**仍未達≤2%門檻（差0.7pp），但訊號強，證實targeted mining方向正確**，待決策是否投入更大規模的cross-fit mining（6個temporary miner model，3-6小時）。

> 🔬 **2026-08-01 v8.9d Hard Example Mining 兩輪 + 診斷 — 挖不到足夠難樣本，且問題被證實是混合性質**：
> - **Round 1（seen-source, AIGuard/fake）**：candidate pool 26,285張（多強度變體），v8.9c打分後 margin<0.5僅261張（1.0%）、真正判錯僅53張（0.2%）——模型對訓練見過的來源已處理得很好。
> - **Round 2（proxy-unseen, DF40 leftover）**：盤點發現DF40五方法清洗後剩餘合計**~118K張從未進訓練**（sd2.1 34,933/DiT 16,286/SiT 17,084/ddim 28,406/pixart 21,370）。抽樣4,000/method生成candidate pool 38,536張，v8.9c打分後 margin<0.5為789張（2.0%）、真正判錯228張（0.6%）——yield rate翻倍但仍遠低於8-12K目標。
> - **關鍵診斷（base fake vs filtered fake）**：對stress test 40張至少一種濾鏡失敗的圖片，查base（未套濾鏡）版本判斷——**15張（37.5%）base本身就判錯（純fake generalization問題，非filter interaction，hard_neg mining救不了）；25張（62.5%）base判對、套濾鏡才翻車（真正的fake+filter邊界問題）**。
> - **結論**：DF40（diffusion）分布的fake+filter模型已泛化得很好，真正的弱點集中在AIGuard-style（GAN/face-swap）held-out分布，且是混合問題（62.5%邊界+37.5%泛化）。繼續放大DF40 mining pool沒有意義。
> - **下一步（待執行）**：① v8.9d-mini sanity check（現有~1,000張mined samples 10-20x oversample，低成本快速驗證mining方向）；② Cross-fit mining（AIGuard fake依6個子來源切折，各訓練一個temporary miner model故意不看該來源，模擬「沒見過這個子來源」情境來挖真正對應stress test失敗模式的hard_neg，成本較高，需訓練6個暫時模型）。

> 🔬 **2026-08-01 v8.9c（v8.9b + 擴大hard_neg）完成 — 報酬遞減，仍不部署**：Splits `v89c_train_real_fake.txt`（115,027，v8.9b的real不變 + hard_neg由17,725擴大至26,447清洗後，來源`--n 9000`重新生成，佔fake class比例33.6%→43.0%）+ filter class沿用v86不變。Init from v8.8。Best macro F1=0.9859。
> - **Gates**：shadow real recall **63.8%**（v8.9b是53.4%，持續進步但仍未過80%；意外的是只動hard_neg、real class完全沒變，real recall卻自己上升，推測是fake/real邊界整體收斂的間接效果）；shadow filter recall 25.3%（與v8.9b持平，filter class未動符合預期）；True Test filter 94.0%✅；**fake+filter誤判3.75%→3.31%（僅改善0.44pp，報酬遞減明顯）**，仍未過≤2%；AIGuard/unseen AUROC 0.7896✅；CelebA 99.7%✅；StyleGAN2 99.8%✅。**4/7過關，v8.9c不部署**。
> - **結論：hard_neg量增加49%只換來fake+filter誤判改善0.44pp，邊際效益低，這條路可能已接近天花板**，離≤2%門檻仍有~1.3pp差距。單純繼續加大同類型hard_neg可能不是最有效的下一步，需考慮其他方向（例如loss設計、real資料量進一步擴大同時觀察是否需要對應提高hard_neg強度、或重新檢視fake+filter誤判在v8.9c的錯誤方向是否有新模式）。

> 🔬 **2026-08-01 v8.9b-real-only 隔離實驗完成 — 乾淨歸因，仍不部署**：Splits `v89b_train_real_fake.txt`（106,305，同v8.9a的real部分）+ filter class 完全沿用 `v86_train_filter.txt`（73,332，v8.8原始，不加新filter）。Init from v8.8。Best macro F1=0.9854。
> - **Gates**：shadow real recall 53.4%（未過80%，與v8.9a的54.5%幾乎相同）；shadow filter recall **26.3%（與v8.8完全相同，未變）**；True Test filter 94.0%✅；fake+filter誤判**3.75%**（未過≤2%，但優於v8.9a的5.84%）；AIGuard/unseen AUROC **0.8044**✅（三版最佳）；CelebA 99.6%✅；StyleGAN2 99.9%✅。**4/7過關，v8.9b同樣不部署**。
> - **乾淨歸因結論**（v8.9a vs v8.9b 對照得出）：① real recall進步（16.2%→~54%）確定由新real資料獨立貢獻，與filter無關；② **filter recall進步（26.3%→46.3%）是新filter資料自己的功勞，不是real-domain-gap修復的連帶效應**——先前`diagnose_filter_carryover.py`得出的「連帶效應」假說在此乾淨對照下被推翻；③ fake+filter誤判惡化由real與filter新增資料共同造成（僅real：1.35%→3.75%；+filter再惡化至5.84%），非單一原因；④ 意外發現：AIGuard/unseen AUROC在純real-only版本最佳（0.8044），暗示新filter資料對此指標可能有輕微負面影響。
> - **下一步（待決策）**：v8.9c需同時解決①real量仍不足以過80%門檻、②real/filter新增資料造成的fake+filter邊界擾動，可能方向包括：擴大新real資料量、為新real來源生成matching hard_neg（用新real的fake版本重新校正邊界）。

> 🔬 **2026-08-01 v8.9a 訓練完成 + Acceptance Gates 評估 — 4/7過關，不部署，且發現real+filter混合改動無法歸因**：
> - Splits: `v89a_train_real_fake.txt`（106,305，+IMDB-WIKI 1,720+VGGFace2-train 297至real class）+ `v89a_train_filter.txt`（75,243，+IMDB-WIKI-filter 1,622+VGGFace2-train-filter 289）。Init from v8.8，其餘超參數/架構/fake class完全不變。Best macro F1=0.9861（epoch10，開發集數字）。
> - **Acceptance Gates 結果**：VGGFace2 shadow real recall 16.2%→**54.5%**（未過80%門檻，但+38.3pp方向正確）；shadow filter recall 26.3%→**46.3%**（未過70%）；True Test filter 94.4%（打平）；**fake+filter誤判 1.35%→5.84%（大幅惡化，未過≤2%門檻）**；AIGuard/unseen AUROC 0.7043→**0.7692**（意外進步）；CelebA 99.7%（打平）；StyleGAN2 99.8%（打平）。**4/7過關，按事前規則v8.9a不取代v8.8**。
> - **hard_neg稀釋假說已排除**：fake class完全未變動，hard_neg/fake class比例仍為33.6%（與v8.8完全相同），fake+filter惡化不是v8.4→v8.6那次的hard_neg稀釋重演。
> - **fake+filter誤判方向**：74張誤判filter、60張誤判real，接近各半非單一方向，顯示real與filter邊界可能同時被影響。
> - **⚠️ 方法論問題**：v8.9a同時加了新real（2,017張）跟新matching filter（1,911張），**無法歸因fake+filter惡化是哪一個造成**。filter carry-over分析結果也從v8.8的清晰模式（base判對real組filter recall較高：46.8% vs 22.2%）反轉為v8.9a的混亂模式（40.5% vs 53.1%，方向相反）——支持「real+filter同時改動使邊界互動變複雜、無法簡單解釋」的判斷。
> - **下一步：v8.9b-real-only 隔離實驗**（只加新real，filter class完全沿用v8.8原始的v86_train_filter.txt不變），用來判斷fake+filter惡化究竟是新real還是新filter造成的。

> 📋 **2026-08-01 Error Audit（v8.9規劃前置）**：VGGFace2 real誤判方向71.4%→fake、12.4%→filter（非均勻誤判，主要被判fake）；DiffSwap誤判方向30.2%→real、23.4%→filter（雙向擴散，跟real不同模式）；filter四子類型breakdown均勻（smoothing71.9%/whitening69.1%/face_reshaping62.0%/eye_enlarging61.5%皆→fake，24-28%正確），**排除「特定濾鏡類型失效」可能，確認filter低分主因是real-domain gap連帶**。⚠️ FFHQ候選來源已否決：v3時代已有FFHQ風格綁架real class的災難紀錄（Binary AUROC崩至0.1061，Problem 23再次確認過），且FFHQ底圖同時是filter訓練資料來源，改用其他in-the-wild來源。v8.9資料來源與範圍尚待進一步討論，暫不動手重訓。

> 🔬 **2026-08-01 VGGFace2 real-domain gap 四項診斷完成 — 排除兩個廉價修法，確認需要重訓**：
> 1. **Face-crop ablation**（`diagnose_face_crop.py`）：pipeline.py 的 `transform_infer` 確認無任何face detection/crop/align，只有整圖 Resize(224,224)。用 MediaPipe 偵測臉部bbox+40%margin裁切後測試，real recall 16.2%→21.1%，**幾乎沒有改善，推翻crop-mismatch假說**。
> 2. **Face-area-ratio相關性分析**：face佔畫面比例與P(fake)相關係數僅0.077，且方向與假說相反（面積越大bucket，mean P(fake)反而越高：[0.15,0.30)=0.641、[0.30,0.50)=0.739、[0.50,1.0)=0.874），**完全不支持「臉太小被誤判」的解釋**。
> 3. **FFT-branch ablation**（`diagnose_fft_branch.py`）：spatial-only（FFT輸出歸零）real recall僅16.2%→22.4%，FFT-only（spatial歸零）1.0%（分布外輸入，數字本身不重要，僅供對照）。**spatial branch單獨測試依然爛，推翻FFT branch過敏假說**。
> 4. **Filter連帶效應分析**（`diagnose_filter_carryover.py`）：281張filter配對回base真人照片，依base是否被判real分兩組——base判對real組filter recall 46.8%，base已判錯組僅22.2%，**確認filter低分主要是real-domain gap的連帶效應**（但46.8%仍遠低於開發集94.4%，代表filter本身可能還有额外的獨立gap，非100%carry-over可解釋）。
> - **結論**：兩個推論端廉價修法（crop、FFT權重）皆被系統性排除，問題根源在 spatial branch 學到的「real」特徵原型本身沒有涵蓋 VGGFace2 這種攝影風格（in-the-wild、活動/新聞照、非標準構圖），**需要 v8.9 加入更多元real訓練資料來源才可能修復，無法靠推論端調整解決**。這是比先前認知更嚴重、更需要投入的問題，Ultimate Held-out Test Set 繼續暫緩解封。

> 🚨 **2026-07-31 Shadow Set 風險評估 — 抓到重大問題，Ultimate 暫緩解封**：建立與 Ultimate 同源但不鎖定的 Shadow Set（`build_shadow_set.py`，VGGFace2同身份不同照片290張、StyleGAN3 ff子集102張、DiffSwap 291張、自建filter套shadow VGGFace2 281張），跑 v8.8 評估（`eval_shadow_set.py`）：
> - **real（VGGFace2）recall 僅 16.2%**（vs 開發集 CelebA 的 99.7%，兩者性質相近卻天差地遠）——已直接驗證非腳本bug（單張圖raw機率確認：VGGFace2真人照P(fake)=0.79-0.92，同手法測CelebA卻P(real)=0.905）
> - fake_gan（StyleGAN3/ff，全新身份）recall **99.0%**——完全沒問題
> - fake_diffusion（DiffSwap）recall 僅 **46.4%**（30.2%誤判real、23.4%誤判filter）
> - filter（自建pipeline套VGGFace2）recall 僅 **26.3%**（65.8%被判成fake）——很可能是底圖（VGGFace2）本身已被判fake，套濾鏡沒能救回來
> - **可能根因（尚未確診）**：VGGFace2是「in-the-wild」人臉辨識資料集，跟訓練real class用的LFW/CelebA train相比，照片風格差異大（構圖不標準、可能有其他人臉部分入鏡、活動/紅毯照片常見、壓縮/縮放來源不一致）；CelebA fix（v8.4，LFW×11→CelebA train）很可能只修好了「CelebA這種風格的real」，沒有真正解決「任意來源真實照片」的泛化，這是比先前認知更窄的修復範圍
> - **決策：Ultimate Held-out Test Set 暫緩解封**，先查清楚VGGFace2 domain gap根因，避免把僅有一次的解封機會用在還沒排除已知風險的狀態下；filter/fake_diffusion的低分很可能是real class問題的連帶效應，不代表各自獨立故障
> - Shadow Set 達成了設計目的：用可重複抽樣、不鎖定的資料，提前抓到會讓Ultimate難看的問題,而沒有浪費那次性解封機會

> ⚠️ **2026-07-31 Step 1a/1c 補做，1c 實驗設計有 confound，結果不可用於下結論**：
> - **1a（identity manifest，已完成）**：實測 DF40-shared identity 池與訓練集重疊率——Celeb-real **588/590（99.7%）**、Youtube-real **300/300（100%）**已透過至少一種 DF40 方法（sd2.1/DiT/SiT/ddim/pixart）進入訓練，比先前「統計上幾乎必然覆蓋」的推論更精確、且方向一致（未高估）。
> - **1c（same-identity real-source sanity test，`AIGuard/identity_sanity_check.py`）**：直接測 v8.8 對這 1,028 個共用身份的「真實照片」（取自 Celeb-DF-v2/YouTube-real mp4）的判斷，結果 real recall 僅 **6.8%（17/250）**，遠低於 CelebA 的 99.7%，乍看像是身份記憶的鐵證。**但這個實驗設計有嚴重 confound：抽樣來源全部是 Celeb-DF-v2 的影片幀（H.264 壓縮），而影片幀本身早已確認有獨立、嚴重的 domain gap 問題（Celeb-DF-v2 官方 holdout real recall 本就是 0/200、WildDeepfake 同樣近乎 0）**。這代表 6.8% 這個數字很可能只是在重現已知的 H.264 問題，跟身份無關——因為「同一批身份」跟「影片幀來源」這兩個變因在這個實驗裡完全綁在一起，無法拆開判斷是哪個造成的。
> - **結論**：1c 目前的執行方式**不可用於支持或推翻 identity shortcut 假說**，屬於實驗設計缺陷,已誠實記錄。若要做出乾淨的 1c，需要這些相同 1,028 個身份的**靜態網路照片**（非影片幀）作為對照，目前專案沒有這樣的資料源（找到這些人的靜態照片本身是額外的資料蒐集工作，非本次範圍）。1b（ArcFace baseline，AUROC 0.57-0.59接近隨機）仍是目前唯一乾淨、可信的 identity shortcut 診斷證據。

> ✅ **2026-07-31 ArcFace identity-only baseline 診斷完成**（`AIGuard/arcface_identity_baseline.py`）：抽樣 150 個 cdf 共用身份（同時存在於 Celeb-DF-v2 真實影片、SiT 訓練用渲染、StyleGAN3 測試用渲染），只用 ArcFace 512-dim embedding（無 texture/frequency 資訊）訓練 logistic regression 做 real vs fake，50 個 held-out 身份測試：**(a) real vs SiT-fake（見過的方法）AUROC=0.570；(b) real vs StyleGAN3-fake（沒見過的方法）AUROC=0.592**，兩者皆接近隨機（0.5），遠低於實際分類器在 StyleGAN3 上的 ~99.7% 準確率。**結論：沒有證據顯示身份/臉部幾何記憶是 StyleGAN3 高準確率的主要成因，模型應該是真的在偵測合成痕跡**；(a)(b) 數字相近也顯示身份層級沒有隨生成方法轉移的規律訊號。此結果緩解（但不完全排除）identity overlap 的疑慮，StyleGAN3 的「unseen-generator, seen-identity」降級標註仍保留（誠實揭露原則，不因單次診斷結果撤銷限制標註）。

> ✅ **2026-07-31 Ultimate Held-out Test Set 封存**：`splits/ultimate_clean_test.txt`（1,052張，real 275 / fake 508（GAN 219+diffusion 289）/ filter 269）完成 MD5（788,881張既有pool，0重複）+ pHash（756,996張，寬鬆閾值d≤6命中1,086筆，但嚴格閾值d≤3僅18筆且全部是StyleGAN3對DiT/pixart/SiT的已知身份重疊，VGGFace2與DiffSwap在d≤3零命中）雙重查重，抽查多組d≤6案例（含最可疑的VGGFace2↔LFW撞名案例）皆視覺確認為不同人，屬pHash對人像構圖相似度的系統性誤報。**Lockbox規則正式生效：論文定稿前不得評估此測試集**，若因bug被迫重跑須降級為Dev-Test並重新抽一組。

---

## Train / Test 重疊驗證

| 比對對象 | 方法 | 結果 | 日期 |
|----------|------|------|------|
| WildDeepfake fake ↔ AIGuard fake train | MD5 | **0 重疊** ✅（但同分布，語義重疊）| 2026-07-14 |
| LFW True Test (250張) ↔ LFW 訓練 split | Code review | **已正確隔離** ✅ | 2026-07-22 |
| DF40 diffusion True Test ↔ DF40 訓練 split | Code review | **已正確隔離** ✅ | 2026-07-22 |
| AIGuard fake (CDDB) ↔ FakeClue test | MD5 + pHash | **Minor: 3/1166 (0.3%)** ⚠️ | 2026-07-22 |
| AIGuard real ↔ LFW | MD5 | **0 重疊** ✅ | 2026-07-22 |
| StyleGAN2 fake ↔ v8.4 training fake | 來源確認 | **0 重疊** ✅（v84 training: AIGuard + DF40 + MidJourney + hardneg，無 StyleGAN2）| 2026-07-28 |
| MidJourney/fake ↔ truetest_fake（v8.4）| Code review | **❌ 45/270（16.7%）洩漏**（`build_v84_splits.py` 缺少 `- tt_fake`）→ v8.5 已修復並驗證 0 重疊 | 2026-07-29 |
| val_real_fake_v84（AIGuard部分）↔ v84 訓練集 | Path 比對 | **❌ 5,146/9,740（52.8%）完全重疊**（v6 舊val，v8.4改用全部AIGuard進訓練後未同步更新val）→ v8.5 改用全新 held-out 5% 切分，0 重疊已驗證 | 2026-07-29 |
| v84_train_filter.txt 內部重複路徑 | Path 計數 | **❌ 108,184/202,667（53%）重複**，部分圖片重複達8次，繼承自 v8.3 未修復 → v8.5 已去重複至 94,483 唯一，0 重複已驗證 | 2026-07-29 |

**LFW / DF40 隔離確認細節（2026-07-22）**：
- `build_v5_splits.py` 在加入 LFW 訓練圖前，先從 `splits/truetest_real.txt` 載入排除名單，確保 True Test 的 250 張 LFW 圖不進訓練
- `generate_lfw_eye_enlarging.py` 同樣排除 `truetest_real.txt` + `truetest_filter.txt`（雙重：path 比對 + person/img_id pair 比對）
- DF40 fake 同樣在 `build_v5_splits.py` 中排除 `truetest_fake.txt`

**AIGuard fake (CDDB) ↔ FakeClue test 比對細節（2026-07-22）**：
- MD5 完全相同：**0** 對
- pHash 高信心 (dist ≤ 2)：**3 張 eval 圖（0.3%）**，全部來自 `ff++/` 子目錄
- 原因：CDDB 包含 FF++ face-swap 衍生圖；FakeClue test 的 `ff++/` 子集亦為 FF++ 幀
- 影響評估：3 張均為 fake 類，不影響 real/fake 判別；AUROC 結果有效

Paper 可寫：
> *"We verified training/test isolation via MD5 and perceptual hash comparison. Three images (<0.3% of FakeClue test) were identified as near-duplicates between the CDDB subset of AIGuard training data and FakeClue's FF++ subset. Removing these images does not materially affect reported metrics."*
