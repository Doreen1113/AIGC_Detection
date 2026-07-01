# AIGC & Filter Detection Project

## Goal
Lightweight + explainable AIGC/filter detection on edge devices (<8GB VRAM).
Output: Real/Fake/Filter-processed + structured natural language explanation.

## Stack
- Python, PyTorch, timm, torchvision, OpenCV, MediaPipe
- Base conda env: training/inference
- mediapipe_env: filter study scripts only

## Dataset
- DeepFake-450K (AIGuard): `C:\CVLab\AIGC\AIGuard\` → real/0~4, fake/0~4
- FakeClue: pending download (HuggingFace lingcco/FakeClue)
- RetouchingFFHQ: pending approval (fudanmaslab@gmail.com)
- CelebA: real face baseline

## Completed
1. Baseline comparison (4 models, DeepFake-450K 3000 real + 3000 fake, 5 epochs) — full metrics re-run 2026-07-01:
   - MobileNetV4 (mobilenetv4_conv_small):  Acc=0.8508 F1=0.8482 Prec=0.8636 Rec=0.8333 AUROC=0.9217 5.13ms 0.18GB  2.50M params
   - EfficientNet-lite (efficientnet_lite0): Acc=0.8750 F1=0.8777 Prec=0.8594 Rec=0.8967 AUROC=0.9463 5.27ms 0.48GB  3.37M params
   - ResNet-lite (resnet18):                Acc=0.9292 F1=0.9277 Prec=0.9478 Rec=0.9083 AUROC=0.9728 5.67ms 0.43GB 11.18M params
   - ShuffleNetV2 (torchvision x1_0):       Acc=0.9167 F1=0.9132 Prec=0.9529 Rec=0.8767 AUROC=0.9737 4.74ms 0.13GB  1.26M params ← BEST overall
   - ShuffleNetV2 selected: lowest VRAM (0.13GB), lowest params (1.26M), highest AUROC (0.9737), fastest inference (4.74ms)
   - timm model names confirmed: mobilenetv4_conv_small / efficientnet_lite0 / resnet18 / ShuffleNetV2 via torchvision

2. FakeVLM inference tested on Kaggle T4: 7.24GB VRAM, ~10s/image (too heavy for edge)

3. Filter study (3 types defined, matching RetouchingFFHQ categories):
   - Skin Smoothing: Skin-Smoothing.ipynb (OpenCV bilateral filter)
   - Whitening: whitening.py (LAB + YCrCb mask, RetouchingFFHQ levels 0/30/60/90)
   - Eye Enlarging: eye_enlarging.py (MediaPipe solutions API, needs mediapipe==0.10.21)
   - Face Reshaping: face_reshaping_test.py (MediaPipe Tasks API, mediapipe_env)

## TODO (in order)
1. ✅ Re-run baseline with Precision/Recall/AUROC added (sklearn roc_auc_score) — done 2026-07-01
2. ✅ Integrate 4 filter scripts into one pipeline: run on 10 images, output avg metrics table — done 2026-07-01
   - Script: filter_pipeline.py (run in mediapipe_env)
   - All 4 filters use mediapipe_env (0.10.9 supports both solutions + Tasks API)
   - Face Reshaping Tasks API path bug fix: use model_asset_buffer instead of model_asset_path
   - All 4 filters use MediaPipe face mesh for detection (10/10 success on all)
   - Results (10 AIGuard/real images):
     Smoothing:     10/10 PSNR=37.65dB  SSIM=0.9726  texture_reduction=43.26%
     Whitening:     10/10 PSNR=31.02dB  SSIM=0.9904  brightness_delta(L)=+15.10
     Eye Enlarging: 10/10 PSNR=34.38dB  SSIM=0.9783  eye_ratio_change=+0.33%
     Face Reshaping:10/10 PSNR=26.22dB  SSIM=0.8866  cheek_width_shrink=8.0%
   - Output: filter_metrics.csv (avg), filter_metrics_detail.csv (per-image)
3. ✅ Add Grad-CAM to ShuffleNetV2 (explainability module) — done 2026-07-01
   - Script: gradcam.py (base env), target layer: model.conv5
   - Model weights saved: shufflenet_v2.pth
   - Output: gradcam_output/ (10 images: 5 real + 5 fake)
   - Sample results: Real 5/5 correct, Fake 4/5 correct (1 misclassified at 94%)
4. Define structured output format: suspicious_region / artifact_type / confidence / explanation
5. Wait for RetouchingFFHQ → train filter branch
6. Knowledge distillation: FakeVLM artifact clues → ShuffleNetV2

## Architecture Plan (Pipeline)
Step 1: Input face image
Step 2: ShuffleNetV2 backbone → feature map
Step 3: Filter branch (detect smoothing/whitening/reshaping/eye enlarging)
Step 4: Facial prior branch (MediaPipe landmarks)
Step 5: Grad-CAM → suspicious region
Step 6: Template-based explanation (artifact tags → sentence)
Step 7: Output: Real/Fake/Filter + explanation

## Key Files
- `C:\CVLab\AIGC\AIGuard\test.py` - baseline training script
- `C:\CVLab\AIGC\whitening.py`
- `C:\CVLab\AIGC\eye_enlarging.py`
- `C:\CVLab\AIGC\face_reshaping_test.py`
- `C:\CVLab\AIGC\Smoothing\Skin-Smoothing.ipynb`

## Notes
- ShuffleNetV2 must use torchvision.models NOT timm (timm doesn't have it)
- MediaPipe Tasks API (0.10.30+) has ctypes DLL bug on Windows base env → use mediapipe_env
- eye_enlarging.py needs mediapipe==0.10.21 with solutions API
- FakeVLM: transformers==4.45.2 required, load with BitsAndBytesConfig 4-bit


