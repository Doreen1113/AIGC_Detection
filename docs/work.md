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
| AIGuard unseen | 0.640 | OOD eval |
| FakeClue test | 0.540 | 待改善 |
| WildDeepfake test | 0.216 (inverted) | domain gap 過大，需找方法 |

v3.1（JPEG aug）和 v4（多來源）已跑，結果更差（見 research_log P22–P23）。目前方向是嘗試 domain gap 解法。

---

## 目標

v3 DualBranch detection backbone 已完成，但 cross-dataset 泛化仍不足。
**目前方向：改善 OOD 泛化，同時推進 pipeline 整合 + paper。**

可嘗試的方向（不需重訓或小改）：
1. **Image quality normalization 前處理**：inference 前統一圖片品質（histogram eq / CLAHE / 固定 JPEG quality）→ 降低 compression shortcut
2. **TTA（Test-Time Augmentation）**：multi-scale + flip ensemble，不需重訓
3. **Two-stage inference**：先判 real/not-real（高 threshold），再判 fake/filter → 減少 OOD→filter 錯誤
4. **Structured output + pipeline 整合**：detection → artifact classifier → Grad-CAM → JSON

---

## 分工（截止 7/23）

### Yu（無 GPU）

- [ ] **Structured output JSON schema 設計 + 實作**
  - Input：class（real/fake/filter）、artifact_type、confidence、grad_cam_region
  - Output：JSON + 一句英文 explanation
  - 範例格式：
    ```json
    {
      "verdict": "filter",
      "artifact_type": "skin_smoothing",
      "confidence": 0.91,
      "suspicious_region": "cheek",
      "explanation": "Detected skin smoothing artifact on the cheek region (91% confidence)."
    }
    ```
  - 需涵蓋所有組合：3 class × 4 artifact types × 常見 region（eyes/cheek/jaw/forehead）
  - 純 Python template logic，完成後給 Irene 串接

- [ ] **Qwen2-VL control group 腳本設計**（不需 GPU，寫腳本讓用戶跑）
  - 載入 Qwen2-VL，對 20 張測試圖做 inference
  - 輸出：fake/real 判斷 + 原因說明（NL）
  - 用於 paper qualitative comparison

- [ ] **Paper Method + Experiment 章節草稿**
  - 數據全在 `docs/research_log.md`（P14–P23）
  - 重點：DualBranch 架構說明 + baseline 比較表 + cross-dataset eval 結果

---

### Irene（8GB GPU）

- [ ] **Image quality normalization 前處理實驗**
  - 在現有 v3 weights 不重訓的前提下，inference 前加 CLAHE / 固定 JPEG quality 重壓
  - 測：AIGuard/unseen + FakeClue/test + WildDeepfake/test 的 AUROC 有無提升
  - 用 `eval_crossdataset_v3_1.py` 改前處理部分即可

- [ ] **TTA（Test-Time Augmentation）實驗**
  - flip + multi-crop ensemble（不需重訓）
  - 同樣跑三個 eval set，確認是否改善 OOD AUROC

- [ ] **Two-stage inference 實作**（改 `pipeline.py`）
  - Stage 1：P(real) > 0.6 → 直接輸出 real
  - Stage 2：不是 real → 再判 fake vs filter
  - 跑 FakeClue + WildDeepfake 確認 OOD→filter 比例有沒有下降

- [ ] **Pipeline 端到端整合**
  - v3 detection → artifact classifier → Grad-CAM → Yu 的 JSON output 全部串起來
  - 在 8GB 機器跑 10 張圖驗證輸出格式

---

## 關鍵路徑

```
Yu 完成 JSON schema
       ↓
Irene 串接 pipeline（整合測試）
       ↓
Irene 跑 quality normalization / TTA 實驗
       ↓
用戶 run Qwen2-VL（Yu 腳本準備好後）
       ↓
確認最終 cross-dataset 結果 → 決定是否再試其他方向
```

## 規則
- `docs/research_log.md` 每次跑完實驗立刻更新，不 push 到 git
- 所有新 weights / 實驗結果備份到 N 槽（用戶負責）
