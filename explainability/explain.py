"""
Structured explanation pipeline for 3-class detection.
Input : image path
Output: JSON with prediction / confidence / artifact_type / suspicious_region / explanation

Usage (base env):
    python explainability/explain.py --image path/to/face.jpg
    python explainability/explain.py --image path/to/face.jpg --save_heatmap
"""

import argparse
import json
import os
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tv_models
from torchvision import transforms
from PIL import Image
import cv2

BASE                  = r"C:\My_Project\AIGC"
WEIGHTS_PATH          = os.path.join(BASE, "shufflenet_v2_3class_fft.pth")
ARTIFACT_WEIGHTS_PATH = os.path.join(BASE, "artifact_classifier.pth")
CLASSES          = ["real", "fake", "filter"]
ARTIFACT_CLASSES = ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]
ARTIFACT_TAG_MAP = {
    "eye_enlarging":  "eye_enlarging",
    "face_reshaping": "face_reshaping",
    "smoothing":      "over_smoothing",
    "whitening":      "whitening",
}

# ──────────────────────────────────────────────
# Model (must match train_3class_fft.py)
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
        self.fft_branch = FFTBranch(out_dim=256)
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256, 512), nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        spatial = self.spatial_branch(x)
        freq    = self.fft_branch(x)
        return self.classifier(torch.cat([spatial, freq], dim=1))


# ──────────────────────────────────────────────
# Grad-CAM
# ──────────────────────────────────────────────
class GradCAM:
    def __init__(self, model, target_layer):
        self.model = model
        self.gradients = None
        self.activations = None
        target_layer.register_forward_hook(self._save_activation)
        target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, class_idx):
        self.model.zero_grad()
        output = self.model(input_tensor)
        output[0, class_idx].backward()

        weights = self.gradients.mean(dim=(2, 3), keepdim=True)  # GAP over spatial
        cam = (weights * self.activations).sum(dim=1, keepdim=True)
        cam = F.relu(cam)
        cam = F.interpolate(cam, size=(224, 224), mode='bilinear', align_corners=False)
        cam = cam.squeeze().cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
        return cam


# ──────────────────────────────────────────────
# Facial region map (rough pixel zones on 224×224)
# ──────────────────────────────────────────────
FACE_REGIONS = {
    "forehead":    (10,  65,  40, 184),   # (y0, y1, x0, x1)
    "left_eye":    (60, 100,  30, 110),
    "right_eye":   (60, 100, 114, 194),
    "nose":        (90, 150,  75, 149),
    "left_cheek":  (100, 175,  15,  90),
    "right_cheek": (100, 175, 134, 209),
    "mouth":       (148, 185,  65, 159),
    "jaw":         (170, 214,  40, 184),
}


def top_activated_regions(cam, top_k=2):
    scores = {}
    for name, (y0, y1, x0, x1) in FACE_REGIONS.items():
        scores[name] = float(cam[y0:y1, x0:x1].mean())
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [r[0] for r in ranked[:top_k]]


# ──────────────────────────────────────────────
# Artifact classifier
# ──────────────────────────────────────────────
def build_artifact_model():
    model = tv_models.shufflenet_v2_x1_0()
    model.fc = nn.Linear(model.fc.in_features, len(ARTIFACT_CLASSES))
    return model

_artifact_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])

def classify_artifact(pil_img, artifact_model, device):
    tensor = _artifact_transform(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(artifact_model(tensor), dim=1)[0]
    cls = ARTIFACT_CLASSES[int(probs.argmax())]
    return ARTIFACT_TAG_MAP[cls]


# ──────────────────────────────────────────────
# Image statistics for artifact discrimination
# ──────────────────────────────────────────────
def compute_skin_stats(image_np):
    h, w = image_np.shape[:2]
    y0, y1 = int(h * 0.15), int(h * 0.85)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    skin_rgb = image_np[y0:y1, x0:x1]
    gray = cv2.cvtColor(skin_rgb, cv2.COLOR_RGB2GRAY)
    texture_var = float(cv2.Laplacian(gray.astype(np.uint8), cv2.CV_32F).var())
    lab = cv2.cvtColor(skin_rgb, cv2.COLOR_RGB2LAB)
    brightness_L = float(lab[:, :, 0].mean())
    return texture_var, brightness_L

_SMOOTH_TEXTURE_THR = 210   # real images: 360+, smoothed: <200
_WHITE_BRIGHT_THR   = 147   # real images: <144, whitened: 148+

# ──────────────────────────────────────────────
# Artifact inference from region + image stats
# ──────────────────────────────────────────────
def infer_artifact_type(prediction, regions, image_np):
    if prediction == "real":
        return []
    if prediction == "fake":
        return ["ai_generated"]

    texture_var, brightness_L = compute_skin_stats(image_np)
    activated = set(regions)
    eye_r   = {"left_eye", "right_eye"}
    cheek_r = {"left_cheek", "right_cheek", "jaw"}

    artifacts = []

    if texture_var < _SMOOTH_TEXTURE_THR:
        artifacts.append("over_smoothing")
    if brightness_L > _WHITE_BRIGHT_THR:
        artifacts.append("whitening")

    if not artifacts:
        if activated & eye_r:
            artifacts.append("eye_enlarging")
        elif activated & cheek_r:
            artifacts.append("face_reshaping")

    return artifacts or ["unknown_filter"]


# ──────────────────────────────────────────────
# Template-based explanation
# ──────────────────────────────────────────────
TEMPLATES = {
    "real": "No significant manipulation artifacts detected. The image appears authentic.",
    "ai_generated": "Unnatural facial structure detected in {region}. Features consistent with AI-generated imagery.",
    "over_smoothing": "Skin texture variance significantly reduced in {region}. Bilateral filter artifacts detected — unnatural surface smoothness.",
    "whitening": "Abnormal brightness elevation detected in {region}. Skin tone whitening filter artifacts identified.",
    "eye_enlarging": "Abnormal eye-to-face ratio detected in {region}. Geometric distortion consistent with eye enlargement filter.",
    "face_reshaping": "Unnatural facial contour detected in {region}. Geometric compression consistent with face slimming filter.",
    "unknown_filter": "Subtle manipulation artifacts detected in {region}. Filter type undetermined.",
}

REGION_DISPLAY = {
    "forehead": "forehead",
    "left_eye": "left eye area",
    "right_eye": "right eye area",
    "left_cheek": "left cheek",
    "right_cheek": "right cheek",
    "nose": "nose area",
    "mouth": "mouth area",
    "jaw": "jaw area",
}


def build_explanation(prediction, artifact_types, regions):
    if prediction == "real":
        return TEMPLATES["real"]

    region_str = " and ".join(REGION_DISPLAY.get(r, r) for r in regions)
    sentences = []
    for art in artifact_types:
        tmpl = TEMPLATES.get(art, TEMPLATES["unknown_filter"])
        sentences.append(tmpl.format(region=region_str))
    return " ".join(sentences)


# ──────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────
def run_pipeline(image_path, save_heatmap=False):
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # load main model
    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()

    # load artifact classifier
    artifact_model = None
    if os.path.exists(ARTIFACT_WEIGHTS_PATH):
        artifact_model = build_artifact_model().to(device)
        artifact_model.load_state_dict(
            torch.load(ARTIFACT_WEIGHTS_PATH, map_location=device))
        artifact_model.eval()

    # Grad-CAM on spatial branch conv5
    gradcam = GradCAM(model, model.spatial_branch.conv5)

    # preprocess
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.5]*3, [0.5]*3),
    ])
    pil_img = Image.open(image_path).convert("RGB")
    image_np = np.array(pil_img.resize((224, 224)))
    input_tensor = transform(pil_img).unsqueeze(0).to(device)
    input_tensor.requires_grad_(True)

    # inference
    with torch.enable_grad():
        logits = model(input_tensor)
    probs = torch.softmax(logits, dim=1)[0].detach()
    pred_idx = int(probs.argmax())
    prediction = CLASSES[pred_idx]
    confidence = float(probs[pred_idx])

    # Grad-CAM
    cam = gradcam.generate(input_tensor, pred_idx)

    # region analysis
    regions = top_activated_regions(cam, top_k=2)

    if prediction == "filter" and artifact_model is not None:
        art_tag = classify_artifact(pil_img, artifact_model, device)
        artifact_types = [art_tag]
    else:
        artifact_types = infer_artifact_type(prediction, regions, image_np)

    explanation = build_explanation(prediction, artifact_types, regions)

    result = {
        "prediction": prediction,
        "confidence": round(confidence, 4),
        "artifact_type": artifact_types,
        "suspicious_region": regions,
        "explanation": explanation,
    }

    if save_heatmap:
        out_dir = os.path.join(BASE, "explanation_output")
        os.makedirs(out_dir, exist_ok=True)
        stem = os.path.splitext(os.path.basename(image_path))[0]

        heatmap = (cam * 255).astype(np.uint8)
        heatmap_color = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        overlay = cv2.addWeighted(
            cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR), 0.6,
            heatmap_color, 0.4, 0)

        out_path = os.path.join(out_dir, f"{stem}_explanation.jpg")
        cv2.imwrite(out_path, overlay)
        result["heatmap_path"] = out_path
        print(f"Heatmap saved to {out_path}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="Path to input face image")
    parser.add_argument("--save_heatmap", action="store_true", help="Save Grad-CAM overlay")
    args = parser.parse_args()

    result = run_pipeline(args.image, save_heatmap=args.save_heatmap)
    print(json.dumps(result, indent=2))
