## 目前完成進度

### 模型
| 模型 | 說明 | 結果 |
|------|------|------|
| Baseline 4模型比較 | MobileNetV4 / EfficientNet / ResNet18 / ShuffleNetV2 | ShuffleNetV2 最佳，AUROC=0.9987 |
| **v3 DualBranch（目前最佳）** | ShuffleNetV2 + FFT branch，3-class（real/fake/filter） | In-dist Macro F1=0.9521，unseen AUROC=0.640 |
| Artifact classifier v3 | 細分 filter 類型（smoothing/whitening/eye_enlarging/face_reshaping） | Macro F1=0.9823 |
| Grad-CAM | 視覺化可疑區域 | 串接 v3，15/15 正確 |

**目前最佳 weights：** `shufflenet_v2_3class_ffhq_v3.pth`

### Cross-dataset eval 結果（持續優化中）
| 測試集 | v3 AUROC | 狀態 |
|--------|---------|------|
| AIGuard unseen | 0.640 | 主要 OOD eval |
| FakeClue test | 0.540 | 待改善 |
| WildDeepfake test | 0.216 (inverted) | domain gap 過大，需找方法 |

已試過：JPEG augmentation（v3.1）和多來源訓練（v4），兩者結果均更差——JPEG aug 讓 model 把壓縮品質當判斷依據，WildDeepfake（影片幀）AUROC 反降至 0.216。目前嘗試不需重訓的方向。

---

## 目標

**改善 OOD 泛化（cross-dataset AUROC），同時完成 pipeline 整合與 paper。**

可嘗試方向（Irene 負責，不需重訓）：
1. **Image quality normalization 前處理**：inference 前統一圖片品質（CLAHE / 固定 JPEG 重壓）→ 降低 compression shortcut 影響
2. **TTA（Test-Time Augmentation）**：flip + multi-crop ensemble
3. **Two-stage inference**：P(real) > 0.6 直接輸出 real，否則再判 fake/filter → 減少 OOD 圖被推入 filter class

---

## 分工（截止 7/21）

### Yu

**前置：`git pull origin dev` 拿到所有腳本即可，不需要圖片資料**

- [ ] **更新 Structured output JSON schema**
  - 舊版 schema（`docs/structured-output.schema.json`）含有 `retouching.level` 欄位，已決定不輸出 level 資訊（只輸出 artifact type），需移除並對齊目前 pipeline 實際輸出
  - 現在 pipeline 輸出欄位：`prediction` / `confidence` / `artifact_type` / `suspicious_region` / `explanation`
  - 更新 schema，並在 `docs/` 補一份簡短說明文件，供 Irene 串接時參考
  - Explanation 範本在 `pipeline.py` 的 `build_explanation()`，確認涵蓋 3 class × 4 artifact × 常見 region（eyes/cheek/jaw/forehead），有缺的補上

- [ ] **Qwen2-VL control group 腳本**（不需 GPU，寫腳本讓 Doreen 跑）
  - 載入 Qwen2-VL，對 20 張測試圖做 inference
  - 輸出：fake/real 判斷 + 原因說明（NL），存成 JSON
  - 用於 paper qualitative comparison table

- [ ] **Paper Method + Experiment 章節草稿**
  - 架構說明：ShuffleNetV2 spatial branch（1024-dim）+ FFT CNN branch（256-dim）→ 3-class classifier
  - 數據：Baseline 比較表（ShuffleNetV2 AUROC 0.9987）、v3 in-dist F1=0.9521、cross-dataset AUROC 表（unseen 0.640 / FakeClue 0.540）

---

### Irene

**前置：**
- `git pull origin dev` — 拿到所有腳本
-  `https://drive.google.com/file/d/1hZxUApfHT67YLo15R74vBoJj71BErwj_/view?usp=drive_link` 載 zip（約 2–3GB）內含：
  - `AIGuard/unseen/`（454 張）
  - `FakeClue/test_clean/`（1,166 張 + labels.csv）
  - `WildDeepfake_subset/images/test_*/`（800 張）
  - `shufflenet_v2_3class_ffhq_v3.pth`
  - `artifact_classifier_v3.pth`
- 解壓縮後對應 `C:\My_Project\AIGC\`（或自行修改 eval 腳本頂部的 `BASE` 路徑）

- [ ] **Image quality normalization 前處理實驗**
  - 在現有 v3 weights 不重訓的前提下，inference 前加 CLAHE / 固定 JPEG quality 重壓
  - 在 `eval_crossdataset_v3_1.py` 的 `transform` 前加前處理，跑三個 eval set 比較 AUROC
  - 記錄：前處理方式 + 三個 eval set AUROC（與 v3 baseline 比較）

- [ ] **TTA（Test-Time Augmentation）實驗**
  - flip + multi-crop ensemble（不需重訓）
  - 跑三個 eval set，記錄是否改善 OOD AUROC

- [ ] **Two-stage inference 實作**（改 `pipeline.py`）
  - Stage 1：P(real) > 0.6 → 直接輸出 real
  - Stage 2：否則再判 fake vs filter
  - 跑 FakeClue + WildDeepfake 確認 OOD→filter 比例有無下降

- [ ] **Pipeline 端到端整合**（等 Yu 的 schema 完成後）
  - v3 detection → artifact classifier → Grad-CAM → JSON output 全部串起來
  - 在 8GB 機器跑 10 張圖驗證格式正確

---

## 關鍵路徑

```
Yu 完成 JSON schema
       ↓
Irene 串接 pipeline（整合測試）
       ↓
Irene 跑 quality normalization / TTA 實驗 → 回報結果
       ↓
Doreen run Qwen2-VL（Yu 腳本準備好後）
       ↓
確認最終 cross-dataset 結果 → 決定是否再試其他方向
```

## 規則
- 每次跑完實驗請記錄在 `docs/test_log.md`，格式：測試了什麼 / AUROC 結果 / 與 v3 比較

