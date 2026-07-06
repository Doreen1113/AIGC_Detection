# AIGC & Filter Detection

Lightweight + explainable AIGC/filter detection targeting edge devices (<8GB VRAM).

**Output:** Real / Fake / Filter-processed + structured natural language explanation

---

## Environments

| Environment | Purpose |
|---|---|
| `base` (Anaconda) | Baseline training, Grad-CAM — has torch, timm, torchvision |
| `mediapipe_env` | Filter pipeline — has mediapipe 0.10.9, cv2, numpy |

---

## Project Structure

```
AIGC_Detection/
├── AIGuard/                        # 資料集 + 訓練腳本
│   ├── train.py                    # Baseline training (4 models)
│   ├── real/ fake/ unseen/         # Dataset (gitignored)
│
├── filters/                        # Filter 相關腳本
│   ├── Smoothing/
│   │   └── Skin-Smoothing.ipynb    # Skin smoothing (bilateral filter)
│   ├── whitening.py                # Whitening (LAB + YCrCb mask)
│   ├── eye_enlarging.py            # Eye enlarging (MediaPipe solutions)
│   ├── face_reshaping.py           # Face reshaping (MediaPipe Tasks API)
│   └── pipeline.py                 # Unified filter pipeline (all 4 filters)
│
├── explainability/
│   └── gradcam.py                  # Grad-CAM on ShuffleNetV2
│
├── results/                        # 實驗數據輸出
│   ├── baseline_comparison.csv
│   ├── filter_metrics.csv
│   └── filter_metrics_detail.csv
│
├── assets/                         # 測試用圖片
│   └── face.jpg
│
├── docs/                           # 論文、proposal、學姊回饋
│   ├── Paper 清單.md
│   ├── tip.txt
│   └── AIGC_Detection_Final V._Proposal .pdf
│
└── README.md
```

---

## Baseline Results

4 models trained on DeepFake-450K (3000 real + 3000 fake, 5 epochs):

| Model | Params | Acc | F1 | Precision | Recall | AUROC | ms/img | VRAM |
|---|---|---|---|---|---|---|---|---|
| MobileNetV4 | 2.50M | 0.8508 | 0.8482 | 0.8636 | 0.8333 | 0.9217 | 5.13 | 0.18GB |
| EfficientNet-lite | 3.37M | 0.8750 | 0.8777 | 0.8594 | 0.8967 | 0.9463 | 5.27 | 0.48GB |
| ResNet-lite | 11.18M | 0.9292 | 0.9277 | 0.9478 | 0.9083 | 0.9728 | 5.67 | 0.43GB |
| **ShuffleNetV2** | **1.26M** | **0.9167** | **0.9132** | **0.9529** | **0.8767** | **0.9737** | **4.74** | **0.13GB** |

→ **ShuffleNetV2 selected** as main backbone: lowest params, lowest VRAM, highest AUROC.

---


## Filter Pipeline

Runs all 4 filters on images and outputs metrics + before/after comparison images.

```bash
conda activate mediapipe_env
python filters/pipeline.py
```

**Average metrics (10 real images from AIGuard/real):**

| Filter | PSNR | SSIM | Key Metric |
|---|---|---|---|
| Smoothing | 37.65 dB | 0.9726 | texture_reduction = 43.26% |
| Whitening | 31.02 dB | 0.9904 | brightness_delta(L) = +15.10 |
| Eye Enlarging | 34.38 dB | 0.9783 | eye_ratio_change = +0.33% |
| Face Reshaping | 26.22 dB | 0.8866 | cheek_width_shrink = 8.0% |

Output images saved to `filter_output/<image_name>/`.

---

## Grad-CAM (Explainability)

Trains ShuffleNetV2 (or loads saved weights) and runs Grad-CAM to highlight suspicious regions.

```bash
# base env
python explainability/gradcam.py
```

- Target layer: `model.conv5` (final feature map before global avg pool)
- Saves model weights to `shufflenet_v2.pth` on first run
- Output: `gradcam_output/` — Original + heatmap overlay (red = high attention)

> Grad-CAM format will be updated after reviewing FakeShield paper.

---

## Baseline Output Format

The baseline is a binary retouching detector. It only reports whether the image
was retouched and the confidence of that prediction. Retouching type, severity,
location, and natural-language explanations are intentionally left for later
versions.

```json
{
  "schema_version": "1.0.0",
  "is_retouched": true,
  "confidence": 0.94
}
```

The dependency-free Python contract is in `baseline_output.py`; its JSON Schema
is `docs/baseline-output.schema.json`.

### Detailed Output Format (future version)

The original detailed contract is also retained for later development. It
separates real, AI-generated, and filter-processed images, and reports the
retouching operation, level, suspicious regions, and explanation.

```json
{
  "schema_version": "1.0.0",
  "prediction": "filter_processed",
  "confidence": 0.94,
  "retouching": {
    "eye_enlarging": {"level": 30, "level_name": "slight", "confidence": 0.91},
    "face_lifting": {"level": 0, "level_name": "off", "confidence": 0.88},
    "skin_smoothing": {"level": 60, "level_name": "medium", "confidence": 0.87},
    "face_whitening": {"level": 0, "level_name": "off", "confidence": 0.95}
  },
  "suspicious_regions": [
    {"region": "eye_area", "confidence": 0.91},
    {"region": "cheek", "confidence": 0.87}
  ],
  "artifact_types": ["eye_enlarging", "skin_smoothing"],
  "explanation": "Slight eye enlargement and medium skin smoothing detected."
}
```

The detailed Python contract remains in `structured_output.py`; its JSON Schema
is `docs/structured-output.schema.json`.

---

## TODO

- [x] Baseline (4 models) with full metrics
- [x] Filter pipeline (4 filters, 10 images, avg metrics)
- [x] Grad-CAM on ShuffleNetV2
- [x] Define structured output format (after RetouchingFFHQ labels)
- [ ] Wait for RetouchingFFHQ dataset → train filter branch
- [ ] Knowledge distillation: FakeVLM → ShuffleNetV2
