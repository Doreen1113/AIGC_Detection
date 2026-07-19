## 目前完成進度

### 模型
| 模型 | 說明 | 結果 |
|------|------|------|
| Baseline 4模型比較 | MobileNetV4 / EfficientNet / ResNet18 / ShuffleNetV2 | ShuffleNetV2 最佳，AUROC=0.9987 |
| v3 DualBranch | ShuffleNetV2 + FFT branch，3-class（real/fake/filter） | In-dist Macro F1=0.9521，True test AUROC=0.1061（inverted）|
| v5.1 DualBranch | +LFW +DF40 diffusion +filter fix | True test AUROC=1.0000，filter recall 31% |
| **v6 DualBranch（目前最佳）** | 純靜態訓練，移除 WildDeepfake | True test AUROC=1.0000，filter recall 67.5%，WildDeepfake 0.889 |
| Artifact classifier v3 | 細分 filter 類型（smoothing/whitening/eye_enlarging/face_reshaping） | Macro F1=0.9823 |

**目前最佳 weights：** `shufflenet_v2_3class_v6.pth`

### Cross-dataset eval 結果
| 測試集 | v3 | v5.1 | v6 |
|--------|-----|------|-----|
| AIGuard unseen | 0.640 | 0.740 | 0.722 |
| FakeClue test | 0.540 | 0.528 | 0.524 |
| WildDeepfake test | 0.938 | 0.741 | **0.889** |
| True test AUROC | 0.1061 | 1.0000 | **1.0000** |

### Qwen2-VL 控制組（2026-07-19）
| 評估集 | 整體準確率 | Filter recall | Binary AUROC |
|--------|-----------|--------------|--------------|
| 80 張（3-class） | 46.25% | 0% | — |
| True test 769 張 | 39.5% | 0% | 0.6497 |

→ 結果存於 `results/qwen2vl_results_3class.json` / `results/qwen2vl_truetest.json`

---

## 目標

**持續改善 OOD 泛化與 filter recall，完成 pipeline 整合與 paper。**

待優化方向：
1. **v7**：過採樣 eye_enlarging × 4 / face_reshaping × 3（目前 eye_enlarging recall 只有 27.4%，訓練樣本只有 smoothing 的 1/5）
2. **v8**：H.264 壓縮模擬 augmentation，改善 FakeClue AUROC（目前 0.524，root cause：影片壓縮 domain gap）
3. **解釋性**：Qwen2-VL verbose mode（--verbose flag 呼叫 Qwen2-VL 生成詳細解釋）

---

## 分工（截止 9月初）

### Yu

**前置：`git pull origin dev` 拿到所有腳本即可，不需要圖片資料**

- [x] **更新 Structured output JSON schema v2.0.0**
  - `docs/structured-output.schema.json`：prediction enum real/fake/filter，移除 retouching.level
  - 說明文件：`docs/README_structured-output.md`

- [ ] **Paper Method + Experiment 章節草稿**
  - 架構說明：ShuffleNetV2 spatial branch（1024-dim）+ FFT CNN branch（256-dim）→ 3-class classifier
  - 數據：Baseline 比較表、v3→v6 cross-dataset AUROC 歷程、True test 結果、Qwen2-VL 控制組對比
  - 注意：backbone 改為 ShuffleNetV2（Proposal 寫 MobileNetV4，需說明選擇原因）

---

### Irene

**前置：**
- `git pull origin dev` — 拿到所有腳本
- 下載 v6：`[https://drive.google.com/file/d/1kDvV8996DzzunqSH2R8q_xa-eMACu9el/view?usp=sharing]`
  - 新增：`shufflenet_v2_3class_v6.pth`
  - 其餘同舊包：irene_eval_package.zip（unseen / FakeClue / WildDeepfake test 資料）

- [x] **Image quality normalization 前處理實驗**（完成，2026-07-15）
  - 結果：JPEG q80 最佳（v5.1）；v6 最佳為 q85
  - 詳見 `docs/test_log.md`（feature/FFHQ branch）

- [x] **TTA（Test-Time Augmentation）實驗**（完成，不推薦）
  - five-crop + flip → 三個 dataset AUROC 全部下降

- [x] **Two-stage inference 實驗**（完成，不推薦）
  - Filter logit bias=1.5 效果更好；但 v6 中 filter bias 幾乎無效（OOD→filter 只有 2.6%）

- [x] **Pipeline 端到端整合**（Doreen 完成，2026-07-20）
  - weights：`shufflenet_v2_3class_v6.pth`，JPEG quality=85
  - schema v2.0.0 對齊，heatmap 生成正常
  - VRAM：0.033 GB（DualBranch inference）

---

## 關鍵路徑

```
[本週 TODO ] → v7 訓練（eye_enlarging 過採樣）
       ↓
v7 eval → 若 filter recall > 80%，成為新最佳
       ↓
v8 訓練（H.264 aug）+ 解釋性 Qwen2-VL verbose mode
       ↓
Yu 寫 paper Method + Experiment
       ↓
Demo / Presentation 準備（8月中）
```

## 規則
- Schema / pipeline 改動記在各自的 `docs/` 說明文件
