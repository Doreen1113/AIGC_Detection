# Dataset 清單

> 最後更新：2026-07-14

---

## 目前使用中（訓練資料）

### Real 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| AIGuard real | Real | **25,753** | `AIGuard/real/0~4/` | ✅ Step1+2+人工複查 |

**AIGuard real 組成**：主要來自 FFHQ（140k Real and Fake Faces dataset 的 real 部分）+ 其他網路人臉圖。

### Fake 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| AIGuard fake | Fake | **20,552** | `AIGuard/fake/0~4/` | ✅ Step1+2+人工複查 |

**AIGuard fake 組成（6 個 source dataset，全部 GAN / face-swap，無 diffusion）**：

| 子 dataset | 生成方法 |
|-----------|---------|
| OpenForensics | StyleGAN + Adversarial Latent Autoencoders（face synthesis + face swap）|
| CDDB | ProGAN / StyleGAN / BigGAN / CycleGAN / GauGAN / CRN / IMLE / SAN + FF++ face swap |
| WildDeepfake | in-the-wild face swap（autoencoder/GAN，影片截幀）|
| 140k Fake Faces | StyleGAN 生成 |
| Pretty Face | StyleGAN2（中國明星）|
| Deepfake and Real | OpenForensics 變體（GAN face synthesis）|

⚠️ **全部為 2022 年前資料，不含 Stable Diffusion / MidJourney 等 diffusion 生成臉**

### Filter 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| filter_data 自建 | Filter | **25,213** | `filter_data/` | ✅ Step1+2 |
| RetouchingFFHQ four_process | Filter | **7,731** | `FFHQ_four_process/` | ✅ Step1+FFHQ exclusion |
| RetouchingFFHQ megvii | Filter | **13,139** | `FFHQ_megvii_four_process/` | ✅ Step1+FFHQ exclusion |
| RetouchingFFHQ ali | Filter | **23,795** | `FFHQ_ali_process/` | ✅ Step1+FFHQ exclusion |

**v3 訓練實際用量：Real 25,753 / Fake 20,552 / Filter 69,878**

---

## v4 訓練實際使用（已完成）

> v4 結果：cross-dataset 無改善（unseen 0.638 / FakeClue 0.518 / WildDeepfake 0.216），v3 仍最佳。注意：v3 本身在 WildDeepfake AUROC=0.9378，是 v3.1 的 JPEG aug 把表現破壞（→0.216 inverted）。

### WildDeepfake（已加入 v4 訓練）

| Dataset | Class | 實際可用 | 路徑 | 清洗狀態 |
|---------|-------|---------|------|---------|
| WildDeepfake train real | Real | **1,279** | `WildDeepfake_subset/images/real/train_*` | ✅ Step1+2 |
| WildDeepfake train fake | Fake | **1,637** | `WildDeepfake_subset/images/fake/train_*` | ✅ Step1+2 |

### FakeClue train（備用，Phase 2 知識蒸餾用）

> FakeClue 不進 detection 訓練（image quality 差 + FF++ 與 AIGuard 重疊）。但 24,300 張標注資料可供 Phase 2 FakeVLM distillation 使用。

| Dataset | Class | 實際可用 | 路徑 | 清洗狀態 |
|---------|-------|---------|------|---------|
| FakeClue human real | Real | **4,428** | `FakeClue/train_clean/labels.csv` label=1 | ✅ Step1+2 完成 |
| FakeClue deepfake（FF++） | Fake | **19,566** | `FakeClue/train_clean/labels.csv` label=0, cate=deepfake | ✅ Step1+2 完成 |
| FakeClue human fake（GenImage AIGC） | Fake | **306** | `FakeClue/train_clean/labels.csv` label=0, cate=human | ✅ Step1+2 完成 |
| **合計** | — | **24,300** | — | ✅ |

---

## Cross-dataset Dev Benchmarks（已多次用於模型比較，非最終 test）

> 這三個 set 已被用來比較 v2/v3/v3.1/v4，實質上是 validation 的角色。Paper 中定位為「cross-dataset generalization benchmarks」，不作為最終 held-out test 報告。

| Dataset | 組成 | 清洗後張數 | 路徑 | 清洗狀態 |
|---------|------|-----------|------|---------|
| AIGuard/unseen | 和 AIGuard train 同源但另行收集，靜態圖（real 238 / fake 216）| **454** | `AIGuard/unseen/` | ✅ Step1 only |
| FakeClue test | deepfake：FF++ c23 影片幀（Deepfakes/FaceSwap/Face2Face/NeuralTextures）+ human：GenImage AIGC + Chameleon AIGC | **1,166** | `FakeClue/test/`；`test_clean/labels.csv` | ✅ Step1+2 |
| WildDeepfake test | in-the-wild face swap 影片截幀（real 400 / fake 400）| **800** | `WildDeepfake_subset/images/` test_ 前綴 | ✅ Step1+2 |

---

## 計畫中的 Held-out True Test Set（尚未建立，2026-07-14 決定）

> 完全未被任何模型決策使用過的乾淨 test set。每 class 目標 200–300 張。

| Class | 來源 | 理由 | 申請狀態 |
|-------|------|------|---------|
| **Real** | **LFW**（Labeled Faces in the Wild）| 非 FFHQ / 非 AIGuard 來源，網路新聞人臉，免費下載 | ✅ 無需申請 |
| **Fake** | **DF40 EFS — diffusion 子集**（SD 2.1 / MidJourney v6 / DiT-XL / PixArt-α）| AIGuard fake 無 diffusion，無重疊；靜態圖；最新技術 | ⏳ 待填 Google Form |
| **Filter** | **LFW real 圖 + 我們的 filter pipeline** | 底圖（LFW）與訓練 filter（FFHQ base）不同，artifact 類型相同 | ✅ 無需申請，自行生成 |

**不能用的項目：**
- DF40 EFS StyleGAN2/3 → AIGuard fake 已含 StyleGAN/StyleGAN2，distribution 重疊
- FFHQ real → 已是訓練 filter 的底圖來源，data leakage

---

## 已有，待整合

| Dataset | 用途 | 狀態 | 備注 |
|---------|------|------|------|
| FFHQ real（RetouchingFFHQ 原始圖） | 擴充 Real 多樣性 | ⚠️ 待確認 | RetouchingFFHQ 的 base images，需確認取得方式 |

---

## 候選（Fake 多樣性擴充）

| Dataset | 圖片數 | 取得方式 | 備注 |
|---------|--------|---------|------|
| FaceForensics++ (FF++) | ~1,000 影片 | [GitHub](https://github.com/ondyari/FaceForensics) 申請 | 最常用 deepfake benchmark，含 Deepfakes/Face2Face/FaceSwap/NeuralTextures |
| DFDC (Deepfake Detection Challenge) | 128K 影片片段 | Kaggle 下載 | Facebook 釋出，多樣性高 |
| CelebDF v2 | 6,229 影片 | [GitHub](https://github.com/yuezunli/celeb-deepfakeforensics) | 高品質 deepfake |
| WildDeepfake | 7,314 片段 | [GitHub](https://github.com/deepfakeinthewild/deepfake-in-the-wild) | 真實野外蒐集，非實驗室生成 |
| **DF40 dataset（EFS diffusion 子集）** | SD 2.1 / MidJourney v6 / DiT-XL / PixArt-α | Google Form 申請 | ✅ **已決定用於 true test set fake class**（只取 diffusion 方法，StyleGAN 子集不用）|

---

## 候選（Real 多樣性擴充）

| Dataset | 圖片數 | 取得方式 | 備注 |
|---------|--------|---------|------|
| FFHQ | 70,000 | [GitHub](https://github.com/NVlabs/ffhq-dataset) | ❌ 不用：已是訓練 filter 底圖，data leakage |
| VGGFace2 | 3.3M | [VGGFace2](https://github.com/ox-vgg/vgg_face2) | 備選，若 LFW 不夠多樣 |
| **LFW (Labeled Faces in the Wild)** | **13,233** | 免費下載 | ✅ **已決定用於 true test set real class** |

---

## 候選（Manipulation / Explanation）

| Dataset | 圖片數 | 來源 | 優先度 | 備注 |
|---------|--------|------|--------|------|
| [MMTD-Set](https://huggingface.co/datasets/zhipeixu/MMTD-Set-34k) | 34K | HuggingFace `zhipeixu/MMTD-Set-34k` | 🟡 中 | 三類篡改：PhotoShop (copy-move/splicing/removal)、DeepFake (FaceApp)、AIGC-Editing (SD-inpainting)；每筆含篡改圖 + mask + GPT-4o 說明文字。Mask 可用於定位訓練，GPT-4o 說明可用於第二階段知識蒸餾 |

---

## 排除（已試，不採用）

| Dataset | 原因 |
|---------|------|
| CelebA (30K) | 加入後 AUROC 0.673 → 0.608，風格與 unseen 差異太大，決策邊界更混亂 |

---

## 資料清洗注意事項

下列問題需在任何 dataset 加入訓練前處理：

1. **低解析度**：短邊 < 128px 的圖片刪除
2. **多人臉**：face count > 1 的圖片刪除（用 face detector 掃）
3. **FFHQ exclusion list**：`FFHQ_settings/excluded_images_list/` 有嬰兒、閉眼、墨鏡清單（共 ~6K 張），套用到 four_process / megvii / ali
4. **Train/Test split 規則**：每個 dataset source 先獨立切出 10% 作為 held-out test，之後不得進訓練
5. 

---

## 各 dataset 的定義合法性

> 最後驗證：2026-07-14

### 類別定義基準
- **Real**：真實拍攝、未修改的臉
- **Fake**：臉部內容被合成或操控（face swap、GAN 生成、facial reenactment）
- **Filter**：身份保留的美化處理，且被拍攝的表情行為是真實的

Face2Face（facial reenactment）歸入 **Fake**：雖身份不變，但表情/行為是合成的，content 本身是假的。這與 Filter（authentic moment + 美化外觀）的本質不同。

### Real class ✅

| 來源 | 說明 | 定義是否正確 |
|------|------|------------|
| Celeb-DF real split | 真實名人影片幀 | ✅ |
| DeeperForensics real split | 真實拍攝 | ✅ |
| Kaggle 140K real | 真實人臉圖片 | ✅ |

### Filter class ✅

| 來源 | 說明 | 定義是否正確 |
|------|------|------------|
| RetouchingFFHQ (four/megvii/ali) | FFHQ 真實臉 + 商業 beauty app（磨皮/美白/大眼） | ✅ |
| 自建 filter_data | 真實臉 + OpenCV/MediaPipe 效果 | ✅ |

### Fake class ✅

| 來源 | 方法 | 定義是否正確 |
|------|------|------------|
| FF++ DeepFakes / FaceSwap / FaceShifter | 換臉（identity 替換） | ✅ 明確 fake |
| FF++ Face2Face | 把 A 的表情貼到 B 臉上 | ✅ 表情是合成的，content 是假的 |
| FF++ NeuralTextures | Rendering-based 表情操控 | ✅ 同 Face2Face 邏輯 |
| CDDB | 多個 GAN/deepfake 資料集合輯（DFDC、FF++、DFD、Celeb-DF 等） | ✅ 全為 face swap + GAN-generated face，無 beauty app 類型 |
| WildDeepfake | 野外蒐集的 face swap | ✅ 明確 face swap |

### Train / Test 重疊驗證 ✅

MD5 hash 比對結果（2026-07-14）：

| 比對對象 | 訓練集 | 測試集 | 重疊 |
|----------|--------|--------|------|
| WildDeepfake fake | AIGuard fake 20,550 張 | WildDeepfake test fake 399 張 | **0** |
| WildDeepfake real | AIGuard real 25,747 張 | WildDeepfake test real 400 張 | **0** |

Paper 可寫：*"We verified no image-level overlap between training and test sets via MD5 hash comparison."*