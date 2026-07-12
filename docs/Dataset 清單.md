# Dataset 清單

---

## 目前使用中

| Dataset | Class | 圖片數 | 路徑 | 備注 |
|---------|-------|--------|------|------|
| AIGuard real | Real | 30,000 | `AIGuard/real/0~4/` | 來源：Celeb-DF、DeeperForensics、Kaggle 140K |
| AIGuard fake | Fake | 30,000 | `AIGuard/fake/0~4/` | 來源：FaceForensics++、CDDB、WildDeepfake |
| filter_data 自建 | Filter | 32,000 | `filter_data/` | OpenCV 模擬：smoothing/whitening/eye/reshaping，各 8K |
| RetouchingFFHQ four_process | Filter | 10,000 | `FFHQ_four_process/` | 4 種濾鏡同時套用，30/60/90 強度 |
| RetouchingFFHQ megvii | Filter | 16,737 | `FFHQ_megvii_four_process/` | Megvii（Face++）app |
| RetouchingFFHQ ali | Filter | 35,998 | `FFHQ_ali_process/` | 阿里美顏 app，有 FilterType_Level 標注 |

**目前總量：Real 30K / Fake 30K / Filter 94.7K**

---

## 已有，待正式整合

| Dataset | 用途 | 狀態 | 備注 |
|---------|------|------|------|
| AIGuard unseen (622 張) | Domain gap 測試 held-out | ✅ 已用 | 外部來源圖片，最佳 AUROC 0.673 |
| FFHQ real（RetouchingFFHQ 原始圖） | 擴充 Real 多樣性 | ⚠️ 待確認 | RetouchingFFHQ 的 base images，需確認取得方式 |

---

## 待下載

| Dataset | Class | 來源 | 優先度 | 備注 |
|---------|-------|------|--------|------|
| FakeClue | Fake + Explanation | HuggingFace `lingcco/FakeClue` | 🔴 高 | VLM 標注的 artifact 說明，第二階段蒸餾需要 |

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
