# AIGC & Filter Detection

Lightweight + explainable AIGC/filter detection targeting edge devices (<8GB VRAM).

**Output:** Real / Fake / Filter-processed + structured natural language explanation

---

## Configuration

All scripts use a `BASE` variable pointing to the root of this repo on your local machine.
**Each team member must update this to match their own path** before running any script.

Files to update:

| File | Line | Variable |
|---|---|---|
| `pipeline.py` | 40 | `BASE = r"C:\Your\Path\AIGC"` |
| `explainability/gradcam.py` | 22 | `BASE = r"C:\Your\Path\AIGC"` |
| `explainability/explain.py` | 23 | `BASE = r"C:\Your\Path\AIGC"` |
| `filters/pipeline.py` | 24 | `BASE = r"C:\Your\Path\AIGC"` |
| `filters/generate_filter_dataset.py` | 27 | `BASE = r"C:\Your\Path\AIGC"` |
| `AIGuard/train_*.py` | top | `BASE = r"C:\Your\Path\AIGC"` |

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
├── pipeline.py                     # Main entry: Real/Fake/Filter detection + explanation
├── baseline_output.py              # Output format contract (binary baseline)
│
├── AIGuard/                        # Dataset + training scripts
│   ├── train.py                    # Baseline training (4 models, Real/Fake)
│   ├── train_3class_ffhq_v2.py     # 3-class model (Real/Fake/Filter) — current best
│   ├── train_artifact_classifier.py# Artifact type classifier (4-class) — current best
│   ├── real/ fake/ unseen/         # Dataset (gitignored)
│
├── filters/                        # Filter scripts
│   ├── generate_filter_dataset.py  # Generate filter training data (32K images)
│   ├── Smoothing/
│   │   └── Skin-Smoothing.ipynb
│   ├── whitening.py
│   ├── eye_enlarging.py
│   ├── face_reshaping.py
│   └── pipeline.py                 # Unified filter pipeline (metrics only)
│
├── explainability/
│   ├── gradcam.py                  # Grad-CAM++ on 3-class model (standalone)
│   └── explain.py                  # Full explanation pipeline (alternative entry)
│
├── docs/
│   ├── research_log.md             # Experiment log
│   ├── baseline-output.schema.json # JSON Schema (baseline output)
│   └── structured-output.schema.json # JSON Schema (detailed output, future)
│
├── results/                        # Experiment CSVs
│
└── README.md
```

---

## Baseline Results

4 models trained on DeepFake-450K (30000 real + 30000 fake, 15 epochs):

| Model | Params | Acc | F1 | Precision | Recall | AUROC | ms/img | VRAM |
|---|---|---|---|---|---|---|---|---|
| MobileNetV4 | 2.50M | 0.9723 | 0.9717 | 0.9958 | 0.9487 | 0.9981 | 3.22 | 0.55GB |
| EfficientNet-lite | 3.37M | 0.9834 | 0.9834 | 0.9817 | 0.9852 | 0.9981 | 2.35 | 1.69GB |
| ResNet-lite | 11.18M | 0.9832 | 0.9832 | 0.9867 | 0.9797 | 0.9984 | 2.11 | 1.10GB |
| **ShuffleNetV2** | **1.26M** | **0.9838** | **0.9837** | **0.9868** | **0.9807** | **0.9987** | **2.14** | **0.43GB** |

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

## Grad-CAM++ (Explainability)

Loads the 3-class model and runs Grad-CAM++ on 5 real + 5 fake + 5 filter images.

```bash
# base env
python explainability/gradcam.py
```

- Model: `shufflenet_v2_3class_ffhq_v2.pth` (Real/Fake/Filter, filter F1=0.980)
- Target layer: `model.spatial_branch.conv5`
- Output: `gradcam_output/` — 3-panel per image: **Input | Grad-CAM++ heatmap | FakeShield binary mask**
- Grad-CAM++ uses 2nd/3rd-order gradients (alpha weighting) for more precise localization than Grad-CAM
- Binary mask: threshold=115 on CAM → white=suspicious region, black=background

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

The JSON Schema for the detailed format is `docs/structured-output.schema.json`.

---

## TODO

- [x] Baseline (4 models) with full metrics
- [x] Filter pipeline (4 filters, 10 images, avg metrics)
- [x] 3-class model (Real/Fake/Filter) — filter F1=0.980 with RetouchingFFHQ
- [x] Artifact type classifier (4-class, F1=0.985)
- [x] Grad-CAM++ on 3-class model (15/15 correct, 3-panel output)
- [x] Grad-CAM++ integrated into pipeline.py (heatmap + binary mask)
- [x] RetouchingFFHQ dataset integrated (cross-domain filter detection 12% → 100%)
- [x] Structured output format defined (baseline + detailed schema)
- [ ] Artifact level prediction (0/30/60/90) to complete detailed output format
- [ ] MAM attention module (needs FFHQ.zip for pair-based training)
- [ ] Knowledge distillation: FakeVLM → ShuffleNetV2
