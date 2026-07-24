# Dataset 清單

> 最後更新：2026-07-22（更新至 v8.1 最終版本）

---

## v8.1 訓練資料總覽（Phase 1 最終）

> v8.1 為 Phase 1 最終最佳模型（True Test Binary AUROC=1.0000，Filter recall=87.6%）。
> 訓練以 v5.1 weights 為初始化，純靜態 JPEG 圖片（無影片幀）。

### Real 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 |
|---------|-------|-----------|------|---------|
| AIGuard real | Real | **25,753** | `AIGuard/real/0~4/` | v3 |
| **LFW (Labeled Faces in the Wild)** | Real | **13,233** | `lfw/` | v5 |

LFW 在訓練 split 中的 oversample 倍數隨版本調整：v5.1 ×1 → v7.4 ×4 → v7.7 ×6 → v7.8 ×8 → v7.9 ×10（甜蜜點）→ v8.1 ×11（最終）

### Fake 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 |
|---------|-------|-----------|------|---------|
| AIGuard fake | Fake | **20,552** | `AIGuard/fake/0~4/` | v3 |
| **DF40 Diffusion** | Fake | ~5,000（訓練用）| `DF40/` diffusion 子集 | v5 |

**AIGuard fake 組成（6 個 source dataset，全部 GAN / face-swap，無 diffusion）**：

| 子 dataset | 生成方法 |
|-----------|---------|
| OpenForensics | StyleGAN + Adversarial Latent Autoencoders（face synthesis + face swap）|
| CDDB | ProGAN / StyleGAN / BigGAN / CycleGAN / GauGAN / CRN / IMLE / SAN + FF++ face swap |
| WildDeepfake | in-the-wild face swap（autoencoder/GAN，影片截幀）|
| 140k Fake Faces | StyleGAN 生成 |
| Pretty Face | StyleGAN2（中國明星）|
| Deepfake and Real | OpenForensics 變體（GAN face synthesis）|

⚠️ AIGuard fake 全部為 2022 年前資料，不含 Stable Diffusion / MidJourney 等 diffusion 生成臉。DF40 Diffusion 從 v5 起補充此缺口。

### Filter 類

| Dataset | Class | 清洗後可用 | 路徑 | 加入版本 |
|---------|-------|-----------|------|---------|
| filter_data 自建 | Filter | **25,213** | `filter_data/` | v3 |
| RetouchingFFHQ four_process | Filter | **7,731** | `FFHQ_four_process/` | v3 |
| RetouchingFFHQ megvii | Filter | **13,139** | `FFHQ_megvii_four_process/` | v3 |
| RetouchingFFHQ ali | Filter | **23,795** | `FFHQ_ali_process/` | v3 |
| **LFW + smoothing** | Filter | ~13,233 | 自行生成（`filters/generate_lfw_filters.py`）| v5.1 |
| **LFW + whitening** | Filter | ~13,233 × 4 oversample | 同上 | v7.6 |
| **LFW + face_reshaping** | Filter | ~13,233 × 4 oversample | 同上 | v7.6 |
| **LFW + eye_enlarging** | Filter | ~13,233 × 8 oversample | `filters/generate_lfw_eye_enlarging.py` | v7.2（×4）→ v8（×8）|

**v8.1 filter split 行數：190,771**（含所有 oversample）

---

## 版本演進記錄

| 版本 | 相對 v3 的主要資料變動 | Binary AUROC | Filter Recall |
|------|----------------------|-------------|--------------|
| v3 | 基準 | 0.1061（True Test 反轉）| — |
| v4 | +WildDeepfake train（後棄用）| — | — |
| v5 | +LFW real + DF40 Diffusion fake | 0.9990 | 0% |
| v5.1 | +LFW filter | 1.0000 | 31% |
| v6 | -WildDeepfake train（純靜態）| 1.0000 | 67.5% |
| v7.2 | +LFW eye ×4 | 0.9978 | 83.9% |
| v7.5 | 移除 filter weight cap | 1.0000 | 72.7% |
| v7.6 | +LFW whitening ×4 + reshape ×4 | 1.0000 | 81.5% |
| v7.9 | LFW real ×10 | 1.0000 | 85.5% |
| v8 | LFW eye ×8 | 1.0000 | 86.7% |
| **v8.1** | LFW real ×11 | **1.0000** | **87.6%** |
| v8.2（棄用）| +Celeb-DF-v2 4,711 H.264 real | 1.0000 | 85.5% ↓ |

---

## True Held-out Test Set（已建立，v5 起使用）

> ⚠️ 從 v5 起開始使用，v7 起訓練決策參考了此 test set 結果，存在輕微 contamination bias。最終論文評估考慮以 Celeb-DF-v2 blind holdout 補充。

| Class | 來源 | 張數 | 路徑 |
|-------|------|------|------|
| Real | LFW（非 AIGuard / 非 FFHQ 來源）| **250** | `lfw/` 子集 |
| Fake | DF40 Diffusion（SD 2.1 / MidJourney v6 / DiT-XL / PixArt-α）| **270** | DF40 diffusion 子集 |
| Filter | LFW real + 我們的 filter pipeline（4 種）| **249** | 自行生成 |
| **合計** | | **769** | |

---

## Cross-dataset OOD Benchmarks

> AIGuard/unseen、FakeClue、WildDeepfake 已被用來比較 v2~v8 各版本，實質上是 cross-domain validation 角色。Paper 中定位為「cross-dataset generalization benchmarks」。
> Celeb-DF-v2 blind holdout 為**真正 blind test**（從未參與任何訓練或版本決策）。

| Dataset | 組成 | 張數 | 路徑 | v8.1 AUROC | 角色 |
|---------|------|------|------|-----------|------|
| AIGuard/unseen | 靜態圖（real 238 / fake 216）| **454** | `AIGuard/unseen/` | 0.722 | OOD eval |
| FakeClue test | FF++ + GenImage AIGC + Chameleon AIGC | **1,166** | `FakeClue/test_clean/labels.csv` | 0.5254 | OOD eval |
| WildDeepfake test | in-the-wild face swap 影片幀（real 400 / fake 400）| **800** | `WildDeepfake_subset/` | 0.889（real=0/400）| OOD eval |
| **Celeb-DF-v2 blind holdout** | 影片幀（real 200 / fake 200）；**從未參與任何決策** | **400** | `splits/celebdf_v2_blind_holdout.txt` | **0.5736（real=0/200）** | Blind test ✅ |

> ⚠️ WildDeepfake、FakeClue、Celeb-DF-v2 的低 real recall（≈0）均為 H.264 domain gap：FFT branch 把 H.264 壓縮特徵當 fake 特徵。Phase 3 修復目標。

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
| CelebA (30K) | 加入後 AUROC 0.673 → 0.608，風格與 unseen 差異太大，決策邊界更混亂 |
| **Celeb-DF-v2**（4,711 清洗後 H.264 real 幀）| v8.2 實驗：WildDeepfake real 0→157/400（改善），但 filter recall −2.1%、FakeClue AUROC 0.480（↓ from 0.527）。H.264 問題為架構限制，加資料無法根治，且代價傷害核心指標 → 不採用 |
| WildDeepfake train（v4 試用）| 影片幀讓 FFT branch 學到 H.264=fake shortcut，WildDeepfake AUROC 從 0.9378 反跌至 0.216 → v6 起永久移除 |

---

## 候選（Fake 多樣性擴充，待 Phase 3）

| Dataset | 圖片數 | 取得方式 | 備注 |
|---------|--------|---------|------|
| FaceForensics++ (FF++) | ~1,000 影片 | GitHub 申請 | 最常用 deepfake benchmark |
| DFDC (Deepfake Detection Challenge) | 128K 影片片段 | Kaggle 下載 | Facebook 釋出，多樣性高 |

---

## 候選（Manipulation / Explanation，Phase 2）

| Dataset | 圖片數 | 來源 | 優先度 | 備注 |
|---------|--------|------|--------|------|
| [MMTD-Set](https://huggingface.co/datasets/zhipeixu/MMTD-Set-34k) | 34K | HuggingFace | 🟡 中 | 三類篡改：PhotoShop / DeepFake / AIGC-Editing；含 GPT-4o 說明文字，可供知識蒸餾 |

---

## 資料清洗 SOP

1. **Step 1 — `clean_dataset.py`**：過濾短邊 < 128px；過濾 face count > 1
2. **Step 2 — `face_attr_filter.py`**：InsightFace 標記閉眼 / 墨鏡 / 嬰兒
3. **原則**：原始資料夾永不刪除，只產生 `clean_paths.txt` 名單，訓練時讀名單
4. **FFHQ exclusion list**：`FFHQ_settings/excluded_images_list/` 套用到 four_process / megvii / ali

---

## 各 dataset 的定義合法性

> 最後驗證：2026-07-22

### 類別定義基準

- **Real**：真實拍攝、未修改的臉
- **Fake**：臉部內容被合成或操控（face swap、GAN 生成、diffusion 生成、facial reenactment）
- **Filter**：身份保留的美化處理，且被拍攝的表情行為是真實的

### Deepfake 四大生成技術 × 我們的類別對應

DF40（及學術文獻）將 deepfake 生成方法分為四類，以下逐一定義並對應到我們的 real / fake / filter 標籤：

| 縮寫 | 全名 | 技術說明 | 我們的標籤 | 理由 |
|------|------|---------|-----------|------|
| **FS** | Face Swapping | 把 source `xs` 的**身份**移植到 target `xt` 上，target 的 pose/expression 保留，但臉是別人的 | **Fake** | 身份被替換，觀看者看到的不是 `xt` 本人的臉 |
| **FR** | Face Reenactment | 保留 target 的**身份** `it`，但用 driven variable `ca`（通常是另一段影片）替換其表情/嘴形/動作 `at`，結果是 `x̃t(it, ãs, bt)` | **Fake** | 雖然是本人的臉，但這個人根本沒有做過這些動作，content 是捏造的 |
| **FE** | Face Editing | 保留身份，只修改外觀屬性（makeup transfer、眼鏡、年齡、髮型等），是身份保留的 appearance 操作 | **語義偏 Filter**（⚠️ 目前**未加入**任何訓練或測試資料）| 如果未來加入需重新評估：「authentic moment + 外觀修改」接近 filter 定義 |
| **EFS** | Entire Face Synthesis | GAN / Diffusion 從頭生成一張**不存在的人**的臉（不基於任何真實影片），如 StyleGAN、SD 生成臉 | **Fake** | 身份不存在，100% 合成 |

**判斷核心**：是「這個行為是不是真實發生過的」。
- FS / FR / EFS：行為或臉都是假的 → **Fake**
- FE：行為是真的，只修改外觀 → 語義接近 **Filter**（但目前不在資料中）
- Filter（我們的）：行為是真的，只加美顏效果 → **Filter**

**FR vs Filter 關鍵區別**（常被混淆）：

| | FR（Face Reenactment）| Filter（我們的）|
|-|----------------------|----------------|
| 身份 | 保留 ✅ | 保留 ✅ |
| 行為/動作 | 合成的（被替換）❌ | 真實發生過的 ✅ |
| 嘴形/表情 | 由另一段影片驅動 | 本人真實表情 |
| 標籤 | **Fake** | **Filter** |

### 各 Dataset 對應的生成類型

| Dataset | 包含方法 | 標籤 | 是否在訓練集 | 是否在 eval |
|---------|---------|------|------------|------------|
| AIGuard fake（CDDB、OpenForensics 等）| FS + EFS（GAN-based）| Fake | ✅ train | — |
| DF40 Diffusion | EFS（SD / MidJourney / DiT / PixArt）| Fake | ✅ train | True Test fake |
| FakeClue fake（FF++）| FR（Face2Face, NeuralTextures）+ FS（FaceSwap, DeepFakes）| Fake | ❌ | ✅ OOD eval |
| WildDeepfake | FS（in-the-wild）| Fake | ❌（v4 試用後棄用）| ✅ OOD eval |
| DF40 FE（Face Editing）| FE（makeup, attribute）| 語義偏 Filter | ❌ | ❌ |

### Real class ✅

| 來源 | 說明 | 定義是否正確 |
|------|------|------------|
| AIGuard real | FFHQ + 其他網路人臉圖 | ✅ |
| LFW | 真實新聞人臉圖 | ✅ |

### Filter class ✅

| 來源 | 說明 | 定義是否正確 |
|------|------|------------|
| RetouchingFFHQ (four/megvii/ali) | FFHQ 真實臉 + 商業 beauty app（磨皮/美白/大眼）| ✅ |
| 自建 filter_data | 真實臉 + OpenCV/MediaPipe 效果 | ✅ |
| LFW + filter pipeline | LFW 真實臉 + 同一套 filter 效果 | ✅ |

### Fake class ✅

| 來源 | 方法 | 定義是否正確 |
|------|------|------------|
| AIGuard fake（各 GAN/face-swap 子集）| FS / GAN synthesis | ✅ 明確 fake |
| DF40 Diffusion | SD 2.1 / MidJourney v6 / DiT-XL / PixArt-α 生成 | ✅ AI 合成臉，身份不存在 |
| FakeClue fake（FF++）| Face2Face / FaceSwap / NeuralTextures | ✅ reenactment 歸 fake（見上方定義基準）|

### Train / Test 重疊驗證

| 比對對象 | 方法 | 結果 | 日期 |
|----------|------|------|------|
| WildDeepfake fake ↔ AIGuard fake train | MD5 | **0 重疊** ✅ | 2026-07-14 |
| WildDeepfake real ↔ AIGuard real train | MD5 | **0 重疊** ✅ | 2026-07-14 |
| LFW True Test (250張) ↔ LFW 訓練 split | Code review | **已正確隔離** ✅ | 2026-07-22 |
| DF40 diffusion True Test ↔ DF40 訓練 split | Code review | **已正確隔離** ✅ | 2026-07-22 |
| AIGuard fake (CDDB) ↔ FakeClue test | MD5 + pHash | **Minor: 3/1166 (0.3%)** ⚠️ | 2026-07-22 |
| AIGuard real ↔ LFW | MD5 | **0 重疊** ✅ | 2026-07-22 |

**LFW / DF40 隔離確認細節（2026-07-22）**：
- `build_v5_splits.py` 在加入 LFW 訓練圖前，先從 `splits/truetest_real.txt` 載入排除名單，確保 True Test 的 250 張 LFW 圖不進訓練
- `generate_lfw_eye_enlarging.py` 同樣排除 `truetest_real.txt` + `truetest_filter.txt`（雙重：path 比對 + person/img_id pair 比對）
- DF40 fake 同樣在 `build_v5_splits.py` 中排除 `truetest_fake.txt`

**AIGuard fake (CDDB) ↔ FakeClue test 比對細節（2026-07-22）**：
- 工具：`check_leakage_cddb_fakeclue.py` + `analyze_leakage_detail.py`
- FakeClue test 6,282 張（MD5 去重後 5,000 張）；22,819 張 AIGuard fake 訓練圖
- MD5 完全相同：**0** 對
- pHash 高信心 (dist ≤ 2)：**3 張 eval 圖（0.3%）**，全部來自 `ff++/` 子目錄
- pHash dist=5-8：403 對，為 FF++ 幀間感知相似的 false positive
- 原因：CDDB 包含 FF++ face-swap 衍生圖；FakeClue test 的 `ff++/` 子集亦為 FF++ 幀
- 影響評估：3 張均為 fake 類，不影響 real/fake 判別；AUROC 結果有效

Paper 可寫：
> *"We verified training/test isolation via MD5 and perceptual hash comparison. Three images (<0.3% of FakeClue test) were identified as near-duplicates between the CDDB subset of AIGuard training data and FakeClue's FF++ subset. Removing these images does not materially affect reported metrics."*
