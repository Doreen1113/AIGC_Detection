# Dataset 清單

> 最後更新：2026-07-13

---

## 目前使用中（訓練資料）

### Real 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| AIGuard real | Real | **25,753** | `AIGuard/real/0~4/` | ✅ Step1+2+人工複查 |

### Fake 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| AIGuard fake | Fake | **20,552** | `AIGuard/fake/0~4/` | ✅ Step1+2+人工複查 |

### Filter 類（v3 訓練用，清洗後）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| filter_data 自建 | Filter | **25,213** | `filter_data/` | ✅ Step1+2 |
| RetouchingFFHQ four_process | Filter | **7,731** | `FFHQ_four_process/` | ✅ Step1+FFHQ exclusion |
| RetouchingFFHQ megvii | Filter | **13,139** | `FFHQ_megvii_four_process/` | ✅ Step1+FFHQ exclusion |
| RetouchingFFHQ ali | Filter | **23,795** | `FFHQ_ali_process/` | ✅ Step1+FFHQ exclusion |

**v3 訓練實際用量：Real 25,753 / Fake 20,552 / Filter 69,878**

---

## 新增資料集（v4 計畫中）

### 用於擴充 Real + Fake（改善 cross-dataset 泛化）

| Dataset | Class | 清洗後可用 | 路徑 | 清洗狀態 |
|---------|-------|-----------|------|---------|
| FakeClue human real | Real | ~2,430（估計） | `FakeClue/train_clean/` label=1, cate=human | ✅ Step1，⚠️ Step2 跑中 |
| FakeClue deepfake（FF++） | Fake | ~19,166（估計） | `FakeClue/train_clean/` label=0, cate=deepfake | ✅ Step1，⚠️ Step2 跑中 |
| FakeClue human fake（GenImage AIGC）| Fake | ~6,647（估計）| `FakeClue/train_clean/` label=0, cate=human | ✅ Step1，⚠️ Step2 跑中 |
| WildDeepfake real | Real | **~1,715**（估計） | `WildDeepfake_subset/images/real/` | ✅ Step1+2 |
| WildDeepfake fake | Fake | **~1,715**（估計） | `WildDeepfake_subset/images/fake/` | ✅ Step1+2 |

> ⚠️ FakeClue train Step2（31,489 張）目前背景跑中，跑完後更新確切數字

---

## Held-out Test Sets（不得進訓練）

| Dataset | 用途 | 清洗後張數 | 路徑 | 清洗狀態 |
|---------|------|-----------|------|---------|
| AIGuard/unseen | Cross-dataset eval | **454** | `AIGuard/unseen/` | ✅ Step1 only |
| FakeClue test（face 類） | Cross-dataset eval | **1,166** | `FakeClue/test/`；labels: `test_clean/labels.csv` | ✅ Step1+2 |
| WildDeepfake test（`test_` 前綴）| Cross-dataset eval | ~800（估計） | `WildDeepfake_subset/images/` | ✅ Step1+2 |

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
| DF40 dataset | 40 種生成方式 | 論文附 link | NeurIPS 2024，多樣性最高 |

---

## 候選（Real 多樣性擴充）

| Dataset | 圖片數 | 取得方式 | 備注 |
|---------|--------|---------|------|
| FFHQ | 70,000 | [GitHub](https://github.com/NVlabs/ffhq-dataset) | 高品質真實人臉，RetouchingFFHQ 的 base |
| VGGFace2 | 3.3M | [VGGFace2](https://github.com/ox-vgg/vgg_face2) | 多年齡/種族/光線，多樣性高 |
| LFW (Labeled Faces in the Wild) | 13,233 | [官網](http://vis-www.cs.umass.edu/lfw/) | 偏舊但多樣，輕量 |

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
