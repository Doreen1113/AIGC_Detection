"""
AIGC & Filter Detection Pipeline — 主入口
==========================================
Usage:
    # 單張圖片
    python pipeline.py --image path/to/face.jpg

    # 整個資料夾
    python pipeline.py --folder path/to/images/ --save_heatmap

    # 指定輸出目錄
    python pipeline.py --folder path/to/images/ --output_dir results/pipeline_out/

Output:
    - 每張圖的 JSON（prediction / confidence / artifact_type / suspicious_region / explanation）
    - summary.csv（整批結果摘要）
    - Grad-CAM heatmap（--save_heatmap 時）
"""

import argparse
import io
import json
import os
import sys
import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tv_models
from torchvision import transforms
from PIL import Image
import cv2

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
BASE                  = r"C:\My_Project\AIGC"
WEIGHTS_PATH          = os.path.join(BASE, "shufflenet_v2_3class_v6.pth")
ARTIFACT_WEIGHTS_PATH = os.path.join(BASE, "artifact_classifier_v3.pth")
CLASSES          = ["real", "fake", "filter"]
# ImageFolder alphabetical order → matches training class index
ARTIFACT_CLASSES = ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]
# Map classifier output to artifact tag used in templates
ARTIFACT_TAG_MAP = {
    "eye_enlarging":  "eye_enlarging",
    "face_reshaping": "face_reshaping",
    "smoothing":      "over_smoothing",
    "whitening":      "whitening",
}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}

# ──────────────────────────────────────────────
# Preprocessing
# ──────────────────────────────────────────────
def preprocess_jpeg(img_pil, quality=85):
    """Re-encode at fixed JPEG quality — 統一壓縮程度，改善 domain gap。"""
    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

# ──────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────
class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, out_dim), nn.ReLU(),
        )

    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        mag = torch.log(torch.abs(fft) + 1e-8)
        return self.net(mag)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        backbone = tv_models.shufflenet_v2_x1_0(
            weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        backbone.fc = nn.Identity()
        self.spatial_branch = backbone
        self.fft_branch     = FFTBranch(out_dim=256)
        self.classifier     = nn.Sequential(
            nn.Linear(1024 + 256, 512), nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        spatial = self.spatial_branch(x)
        freq    = self.fft_branch(x)
        return self.classifier(torch.cat([spatial, freq], dim=1))

# ──────────────────────────────────────────────
# Grad-CAM++
# ──────────────────────────────────────────────
class GradCAMPlusPlus:
    def __init__(self, model, target_layer):
        self.model = model
        self._act  = None
        self._grad = None
        target_layer.register_forward_hook(
            lambda m, i, o: setattr(self, '_act', o.detach()))
        target_layer.register_full_backward_hook(
            lambda m, gi, go: setattr(self, '_grad', go[0].detach()))

    def generate(self, inp, class_idx):
        self.model.zero_grad()
        out = self.model(inp)
        out[0, class_idx].backward()

        features  = self._act
        gradients = self._grad

        grads_power_2 = gradients ** 2
        grads_power_3 = gradients ** 3
        sum_features  = torch.sum(features, dim=[2, 3], keepdim=True)

        alpha_denom = 2 * grads_power_2 + sum_features * grads_power_3
        alpha_denom = torch.where(alpha_denom != 0, alpha_denom, torch.ones_like(alpha_denom))
        alpha   = grads_power_2 / alpha_denom
        weights = torch.sum(alpha * torch.relu(gradients), dim=[2, 3], keepdim=True)

        cam = torch.relu((weights * features).sum(dim=1)).squeeze()
        cam = cam.cpu().numpy()
        cam = cv2.resize(cam, (224, 224))
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        return cam

# ──────────────────────────────────────────────
# Region analysis
# ──────────────────────────────────────────────
FACE_REGIONS = {
    "forehead":    (10,  65,  40, 184),
    "left_eye":    (60, 100,  30, 110),
    "right_eye":   (60, 100, 114, 194),
    "nose":        (90, 150,  75, 149),
    "left_cheek":  (100, 175,  15,  90),
    "right_cheek": (100, 175, 134, 209),
    "mouth":       (148, 185,  65, 159),
    "jaw":         (170, 214,  40, 184),
}

REGION_DISPLAY = {
    "forehead": "forehead", "left_eye": "left eye area",
    "right_eye": "right eye area", "nose": "nose area",
    "left_cheek": "left cheek", "right_cheek": "right cheek",
    "mouth": "mouth area", "jaw": "jaw area",
}

def top_activated_regions(cam, top_k=2):
    scores = {name: float(cam[y0:y1, x0:x1].mean())
              for name, (y0, y1, x0, x1) in FACE_REGIONS.items()}
    return [r for r, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]]

# ──────────────────────────────────────────────
# Artifact classifier (4-class, runs only when prediction == "filter")
# ──────────────────────────────────────────────
def build_artifact_model():
    model = tv_models.shufflenet_v2_x1_0()
    model.fc = nn.Linear(model.fc.in_features, len(ARTIFACT_CLASSES))
    return model

transform_artifact = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])

def classify_artifact(pil_img, artifact_model, device):
    """Return (artifact_tag, confidence) using the trained classifier."""
    tensor = transform_artifact(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(artifact_model(tensor), dim=1)[0]
    idx  = int(probs.argmax())
    cls  = ARTIFACT_CLASSES[idx]
    tag  = ARTIFACT_TAG_MAP[cls]
    return tag, float(probs[idx])



# ──────────────────────────────────────────────
# Image statistics for artifact discrimination
# ──────────────────────────────────────────────
def compute_skin_stats(image_np):
    """
    Compute texture variance and brightness in central skin region.
    Returns (texture_var, brightness_L).
    Note: FFT high-freq analysis was tested but JPEG preprocessing normalizes
    frequency content, making it ineffective for smoothing detection.
    """
    h, w = image_np.shape[:2]
    y0, y1 = int(h * 0.15), int(h * 0.85)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    skin_rgb = image_np[y0:y1, x0:x1]

    # Texture: Laplacian variance (smoothing reduces this significantly)
    gray = cv2.cvtColor(skin_rgb, cv2.COLOR_RGB2GRAY)
    texture_var = float(cv2.Laplacian(gray.astype(np.uint8), cv2.CV_32F).var())

    # Brightness: LAB L channel (whitening raises this)
    lab = cv2.cvtColor(skin_rgb, cv2.COLOR_RGB2LAB)
    brightness_L = float(lab[:, :, 0].mean())

    return texture_var, brightness_L

# Thresholds calibrated on AIGuard real baseline:
# Real images: texture 360~1070, brightness 105~144
_SMOOTH_TEXTURE_THR  = 210   # below → smoothing (strongly smoothed: ~194)
_WHITE_BRIGHT_THR    = 147   # above → whitening (strongly whitened: ~149)

# ──────────────────────────────────────────────
# Artifact inference
# ──────────────────────────────────────────────
def infer_artifact_type(prediction, regions, image_np):
    if prediction == "real":
        return []
    if prediction == "fake":
        return ["ai_generated"]

    texture_var, brightness_L = compute_skin_stats(image_np)

    activated = set(regions)
    eye_r     = {"left_eye", "right_eye"}
    cheek_r   = {"left_cheek", "right_cheek", "jaw"}

    artifacts = []

    # Primary: image statistics for skin-processing filters
    if texture_var < _SMOOTH_TEXTURE_THR:
        artifacts.append("over_smoothing")
    if brightness_L > _WHITE_BRIGHT_THR:
        artifacts.append("whitening")

    # Secondary: Grad-CAM regions for geometric filters
    # Statistics take priority; Grad-CAM used as best-effort fallback
    if not artifacts:
        if activated & eye_r:
            artifacts.append("eye_enlarging")
        elif activated & cheek_r:
            artifacts.append("face_reshaping")

    return artifacts or ["unknown_filter"]

# ──────────────────────────────────────────────
# Explanation templates
# ──────────────────────────────────────────────
TEMPLATES = {
    "real":          "No significant manipulation artifacts detected. The image appears authentic.",
    "ai_generated":  "Unnatural facial structure detected in {region}. Features consistent with AI-generated imagery.",
    "over_smoothing":"Skin texture variance significantly reduced in {region}. Bilateral filter artifacts detected — unnatural surface smoothness.",
    "whitening":     "Abnormal brightness elevation detected in {region}. Skin tone whitening filter artifacts identified.",
    "eye_enlarging": "Abnormal eye-to-face ratio detected in {region}. Geometric distortion consistent with eye enlargement filter.",
    "face_reshaping":"Unnatural facial contour detected in {region}. Geometric compression consistent with face slimming filter.",
    "unknown_filter":"Subtle manipulation artifacts detected in {region}. Filter type undetermined.",
}

def build_explanation(prediction, artifact_types, regions):
    if prediction == "real":
        return TEMPLATES["real"]
    region_str = " and ".join(REGION_DISPLAY.get(r, r) for r in regions)
    if prediction == "fake":
        return TEMPLATES["ai_generated"].format(region=region_str)
    if not artifact_types:
        return TEMPLATES["unknown_filter"].format(region=region_str)
    return " ".join(
        TEMPLATES.get(a, TEMPLATES["unknown_filter"]).format(region=region_str)
        for a in artifact_types
    )

# ──────────────────────────────────────────────
# Single-image inference
# ──────────────────────────────────────────────
transform_infer = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])

def run_single(image_path, model, gradcam, artifact_model, device,
               save_heatmap=False, output_dir=None, jpeg_preprocess=True):
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return {"error": str(e), "image": str(image_path)}

    if jpeg_preprocess:
        pil_img = preprocess_jpeg(pil_img, quality=85)

    image_np     = np.array(pil_img.resize((224, 224)))
    input_tensor = transform_infer(pil_img).unsqueeze(0).to(device)
    input_tensor.requires_grad_(True)

    with torch.enable_grad():
        logits = model(input_tensor)
    probs      = torch.softmax(logits, dim=1)[0].detach()
    pred_idx   = int(probs.argmax())
    prediction = CLASSES[pred_idx]
    confidence = float(probs[pred_idx])
    all_probs  = {c: round(float(p), 4) for c, p in zip(CLASSES, probs)}

    cam     = gradcam.generate(input_tensor, pred_idx)
    regions = top_activated_regions(cam, top_k=2)

    # Artifact type: use trained classifier for filter, heuristic for fake
    if prediction == "filter" and artifact_model is not None:
        art_tag, _ = classify_artifact(pil_img, artifact_model, device)
        artifact_types = [art_tag]
    else:
        artifact_types = infer_artifact_type(prediction, regions, image_np)

    explanation = build_explanation(prediction, artifact_types, regions)

    result = {
        "schema_version":    "2.0.0",
        "image":             os.path.basename(image_path),
        "prediction":        prediction,
        "confidence":        round(confidence, 4),
        "class_probs":       all_probs,
        "artifact_types":    artifact_types,
        "suspicious_regions": regions,
        "explanation":       explanation,
    }

    if save_heatmap and output_dir:
        stem     = Path(image_path).stem
        img_bgr  = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        hmap_col = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
        overlay  = cv2.addWeighted(img_bgr, 0.55, hmap_col, 0.45, 0)
        _, binary_mask = cv2.threshold((cam * 255).astype(np.uint8), 115, 255, cv2.THRESH_BINARY)

        hmap_path = os.path.join(output_dir, f"{stem}_heatmap.jpg")
        mask_path = os.path.join(output_dir, f"{stem}_mask.jpg")
        cv2.imwrite(hmap_path, overlay)
        cv2.imwrite(mask_path, binary_mask)
        result["heatmap_path"] = hmap_path
        result["mask_path"]    = mask_path

    return result

# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AIGC & Filter Detection Pipeline")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image",  help="Path to a single image")
    group.add_argument("--folder", help="Path to a folder of images")
    parser.add_argument("--save_heatmap",   action="store_true", help="Save Grad-CAM heatmap")
    parser.add_argument("--output_dir",     default=None,        help="Output directory")
    parser.add_argument("--no_jpeg_preproc",action="store_true", help="Disable JPEG preprocessing")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Loading model from {WEIGHTS_PATH} ...")

    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    gradcam = GradCAMPlusPlus(model, model.spatial_branch.conv5)

    artifact_model = None
    if os.path.exists(ARTIFACT_WEIGHTS_PATH):
        artifact_model = build_artifact_model().to(device)
        artifact_model.load_state_dict(
            torch.load(ARTIFACT_WEIGHTS_PATH, map_location=device))
        artifact_model.eval()
        print(f"Artifact classifier loaded from {ARTIFACT_WEIGHTS_PATH}")
    else:
        print("Artifact classifier not found — using heuristic fallback")

    jpeg_pre = not args.no_jpeg_preproc

    # ── single image ──
    if args.image:
        out_dir = args.output_dir or os.path.join(BASE, "explanation_output")
        os.makedirs(out_dir, exist_ok=True)
        result = run_single(args.image, model, gradcam, artifact_model, device,
                            save_heatmap=args.save_heatmap,
                            output_dir=out_dir,
                            jpeg_preprocess=jpeg_pre)
        print(json.dumps(result, indent=2, ensure_ascii=False))

        json_path = os.path.join(out_dir, Path(args.image).stem + "_result.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\nJSON saved to {json_path}")
        return

    # ── folder ──
    folder   = args.folder
    out_dir  = args.output_dir or os.path.join(folder, "pipeline_output")
    os.makedirs(out_dir, exist_ok=True)

    image_files = sorted([
        p for p in Path(folder).iterdir()
        if p.suffix.lower() in IMG_EXTS
    ])
    print(f"Found {len(image_files)} images in {folder}")

    results = []
    for i, img_path in enumerate(image_files, 1):
        r = run_single(str(img_path), model, gradcam, artifact_model, device,
                       save_heatmap=args.save_heatmap,
                       output_dir=out_dir,
                       jpeg_preprocess=jpeg_pre)
        results.append(r)
        print(f"[{i:3d}/{len(image_files)}] {r['image']:40s} "
              f"→ {r.get('prediction','ERR'):6s} "
              f"({r.get('confidence', 0):.3f})  "
              f"artifact: {r.get('artifact_type', [])}")

    # Save summary CSV
    csv_path = os.path.join(out_dir, "summary.csv")
    csv_fields = ["image", "prediction", "confidence",
                  "prob_real", "prob_fake", "prob_filter",
                  "artifact_types", "suspicious_regions", "explanation"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            probs = r.get("class_probs", {})
            row["prob_real"]   = probs.get("real",   "")
            row["prob_fake"]   = probs.get("fake",   "")
            row["prob_filter"] = probs.get("filter", "")
            row["artifact_types"]     = "|".join(r.get("artifact_types", []))
            row["suspicious_regions"] = "|".join(r.get("suspicious_regions", []))
            writer.writerow(row)

    # Save all JSONs
    json_path = os.path.join(out_dir, "all_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Print summary stats
    preds = [r.get("prediction") for r in results if "prediction" in r]
    print(f"\n{'='*50}")
    print(f"Summary: {len(results)} images")
    for cls in CLASSES:
        n = preds.count(cls)
        print(f"  {cls:8s}: {n:4d} ({n/len(preds)*100:.1f}%)")
    print(f"\nCSV  → {csv_path}")
    print(f"JSON → {json_path}")


if __name__ == "__main__":
    main()
