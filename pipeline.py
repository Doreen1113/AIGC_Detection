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
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
BASE                  = r"C:\My_Project\AIGC"
# v8.11 hierarchical classifier (2026-08-02 拍板，Phase 1最終候選，取代v8.8單一3-class模型):
#   Layer1: real vs manipulated (fake ∪ filter) 二分類
#   Layer2: 僅在Layer1判為manipulated時啟動，fake vs filter 二分類
# 對外輸出schema維持與v8.8相容（同樣是real/fake/filter三選一 + class_probs），
# 差別只在內部推論改成兩階段串接。舊的v8.8單模型權重仍保留於磁碟供對照，不再是預設路徑。
# 2026-08-10：Layer1 更新為 v811d（round4 hard-neg fine-tune，全部6項gate對照Layer1c
# 無退步、Shadow real recall +1.4pp、fake+filter端到端誤判4.06%→3.71%），完整對照見
# TODO.md「Layer 2（fake vs filter）辨識瓶頸」章節。Layer1c保留在磁碟供對照，不再是預設路徑。
# 2026-08-20：Layer1 更新為 v8.17（P1-R9 Self-Blended Images pilot 候選，
# shufflenet_v2_layer1_v817sbi.pth，SHA256 e3057270...），為v8.11凍結後第一個
# 正式核准並套用的production變更。核准依據：Freeze-Gate A全過（True Test filter
# recall 91.97%仍≥90%門檻，唯一退步項）、Freeze-Gate C穩健性20種擾動條件下
# 同一trade-off無放大、fp32 TFLite合併20.913MB/14.22ms未退步、threshold-only
# frontier 9/9勝出、雙陷阱檢查皆過。完整證據見
# docs/team/change_proposals/20260820_p1_r9_sbi_layer1_sbiaug.md，
# 研究過程見 results/research/p1_r9_sbi_pilot_20260819/。
# v811d 保留在磁碟供對照/rollback，不再是預設路徑。
LAYER1_WEIGHTS_PATH   = os.path.join(BASE, "shufflenet_v2_layer1_v817sbi.pth")
LAYER2_WEIGHTS_PATH   = os.path.join(BASE, "shufflenet_v2_layer2_v811.pth")
ARTIFACT_WEIGHTS_PATH = os.path.join(BASE, "artifact_classifier_v3.pth")
CLASSES          = ["real", "fake", "filter"]
# 2026-08-11: pipeline.py previously had NO face-detection gate at all -- any
# input (a landscape photo, a cat, a blank image) was forced through the
# real/fake/filter classifier and given a confident-looking answer. Every
# other face-processing script in this project (stress_test_v811_pipeline.py,
# generate_vggface2_filters.py, etc.) already gates on MediaPipe face
# detection before doing anything else; production inference did not. Added
# below using the exact same MediaPipe FaceLandmarker pattern already used
# project-wide, not a new detector.
FACE_LANDMARKER_PATH = os.path.join(BASE, "face_landmarker.task")
# ImageFolder alphabetical order → matches training class index
ARTIFACT_CLASSES = ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]
# Map classifier output to artifact tag used in templates
ARTIFACT_TAG_MAP = {
    "eye_enlarging":  "eye_enlarging",
    "face_reshaping": "face_reshaping",
    "smoothing":      "smoothing",
    "whitening":      "whitening",
}
IMG_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}

# Rule-based: artifact_type -> suspicious_regions for filter class.
# eye_enlarging is the ONLY filter type with region-level, GT-backed
# localization support (see docs/phase2_story.md, docs/Dataset 清單.md
# 2026-08-02 entry): visualizing LAB-diff heatmaps against the self-built
# filter pipeline's own before/after pairs showed whitening/smoothing
# genuinely affect nearly the entire face oval (the skin mask used at
# generation time IS an ellipse spanning most of the face), and
# face_reshaping's fixed 60px warp radius saturates most regions at dataset
# scale (unlike eye_enlarging's self-scaling radius). Listing specific
# sub-regions for these three would misrepresent them as more localized than
# they actually are, so they map to a single whole-face marker instead.
ARTIFACT_REGION_MAP = {
    "eye_enlarging":  ["left_eye", "right_eye"],
    "face_reshaping": ["face"],
    "smoothing":      ["face"],
    "whitening":      ["face"],
    "unknown_filter": [],
}

# ──────────────────────────────────────────────
# Face-presence gate (2026-08-11, new)
# ──────────────────────────────────────────────
_face_landmarker = None


def _get_face_landmarker():
    """Lazy singleton, same MediaPipe FaceLandmarker pattern used project-wide
    (e.g. stress_test_v811_pipeline.py, generate_vggface2_filters.py)."""
    global _face_landmarker
    if _face_landmarker is None:
        with open(FACE_LANDMARKER_PATH, "rb") as f:
            model_data = f.read()
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data),
            num_faces=1)
        _face_landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
    return _face_landmarker


def has_face(pil_img):
    """True if MediaPipe detects a face in the image. Every real/fake/filter
    classification this pipeline makes is only meaningful for a face crop;
    previously there was no check at all, so a non-face input (landscape,
    object, blank image) silently got a confident real/fake/filter verdict
    anyway. See TODO.md / non-face gate discussion, 2026-08-11."""
    rgb = np.array(pil_img.convert("RGB"))
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = _get_face_landmarker().detect(mp_img)
    return bool(res.face_landmarks)


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

    def extract_features(self, x):
        """Return 1280-dim features (before classifier)."""
        with torch.no_grad():
            spatial = self.spatial_branch(x)
            freq    = self.fft_branch(x)
        return torch.cat([spatial, freq], dim=1)


def hierarchical_predict(input_tensor, l1_model, l2_model, requires_grad=False):
    """Runs the v8.11 Layer1(real vs manipulated) -> Layer2(fake vs filter)
    chain and returns a result dict shaped to match the old 3-class model's
    output exactly (prediction/confidence/class_probs), so downstream code
    (artifact classification, region head, explanation templates) doesn't
    need to know the classifier is now two-stage.

    class_probs are a genuine composite distribution, not just the winning
    layer's raw softmax: P(real)=L1.P(real); P(fake)=L1.P(manip)*L2.P(fake);
    P(filter)=L1.P(manip)*L2.P(filter) -- these sum to 1 and are directly
    comparable to the old single-model output.
    """
    ctx = torch.enable_grad() if requires_grad else torch.no_grad()
    with ctx:
        l1_logits = l1_model(input_tensor)
        l1_probs = torch.softmax(l1_logits, dim=1)[0]
        p_real, p_manip = float(l1_probs[0].detach()), float(l1_probs[1].detach())

        l2_logits = l2_model(input_tensor)
        l2_probs = torch.softmax(l2_logits, dim=1)[0]
        p_fake_given_manip, p_filter_given_manip = float(l2_probs[0].detach()), float(l2_probs[1].detach())

    p_fake = p_manip * p_fake_given_manip
    p_filter = p_manip * p_filter_given_manip
    class_probs_arr = [p_real, p_fake, p_filter]

    pred_idx = int(np.argmax(class_probs_arr))
    prediction = CLASSES[pred_idx]
    confidence = class_probs_arr[pred_idx]

    # which layer's decision actually determined the final label -- used to
    # pick which model/class-index Grad-CAM++ should explain
    if prediction == "real":
        gradcam_layer, gradcam_class_idx = "l1", 0
    else:
        gradcam_layer = "l2"
        gradcam_class_idx = 0 if prediction == "fake" else 1

    return {
        "prediction": prediction,
        "confidence": confidence,
        "class_probs": {c: p for c, p in zip(CLASSES, class_probs_arr)},
        "gradcam_layer": gradcam_layer,
        "gradcam_class_idx": gradcam_class_idx,
    }

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
    "face": "the face",  # whole-face marker, see ARTIFACT_REGION_MAP note
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

# 2026-08-11: `classify_artifact` is a closed-set 4-way softmax classifier --
# it has no "none of the above" output, so a filter type we never trained on
# (or any other out-of-distribution input reaching this path) was previously
# always forced into one of the 4 known classes, with a confidence number
# that looks legitimate but is meaningless for OOD input. This threshold adds
# the missing open-set behavior (TODO.md C2章節): below it, report
# "unknown_filter" instead of guessing.
# NOTE: 0.6 is a reasoned default (comfortably above the 0.25 4-class random
# baseline, not so strict it rejects confident correct calls), NOT a
# calibrated value -- there is no held-out "genuinely novel filter type"
# dataset yet to calibrate against (see TODO.md C2 "Unseen filter/fake
# 資料集上的open-set評估", still open). Revisit once that eval exists.
ARTIFACT_UNKNOWN_THRESHOLD = 0.6


def classify_artifact(pil_img, artifact_model, device):
    """Return (artifact_tag, confidence) using the trained classifier.
    Returns ("unknown_filter", confidence) if the top class's confidence is
    below ARTIFACT_UNKNOWN_THRESHOLD, rather than forcing a guess."""
    tensor = transform_artifact(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(artifact_model(tensor), dim=1)[0]
    idx  = int(probs.argmax())
    conf = float(probs[idx])
    if conf < ARTIFACT_UNKNOWN_THRESHOLD:
        return "unknown_filter", conf
    cls  = ARTIFACT_CLASSES[idx]
    tag  = ARTIFACT_TAG_MAP[cls]
    return tag, conf



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
        return []

    texture_var, brightness_L = compute_skin_stats(image_np)

    activated = set(regions)
    eye_r     = {"left_eye", "right_eye"}
    cheek_r   = {"left_cheek", "right_cheek", "jaw"}

    artifacts = []

    # Primary: image statistics for skin-processing filters
    if texture_var < _SMOOTH_TEXTURE_THR:
        artifacts.append("smoothing")
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
    "non_face":      "No face detected in this image. This pipeline only classifies face crops; real/fake/filter labels are not meaningful for non-face input.",
    "real":          "No significant manipulation artifacts detected. The image appears authentic.",
    # fake: global-level only (no {region} -- see run_single's regions=[]
    # note; Phase 2 found no reliable ground truth for fake region
    # localization, so we don't claim any).
    "ai_generated":  "Unnatural global texture and frequency patterns detected across the image, consistent with AI-generated (synthetic) facial imagery.",
    # whole-face filters (smoothing/whitening/face_reshaping): {region}
    # resolves to "the face" via REGION_DISPLAY["face"] -- see
    # ARTIFACT_REGION_MAP note on why these are whole-face, not per-region.
    "smoothing":     "Skin texture variance is reduced across {region}. Bilateral filter artifacts detected — unnatural surface smoothness spanning the whole face.",
    "whitening":     "Abnormal brightness elevation detected across {region}. Skin tone whitening filter artifacts identified.",
    "face_reshaping":"Unnatural facial contour detected across {region}, most consistent with geometric compression around the jawline and cheeks (face-slimming filter).",
    # eye_enlarging: the one filter type with region-level, GT-backed localization
    "eye_enlarging": "Abnormal eye-to-face ratio detected in {region}. Geometric distortion consistent with eye enlargement filter.",
    "unknown_filter":"Subtle manipulation artifacts detected. Filter type undetermined.",
}

def build_explanation(prediction, artifact_types, regions):
    if prediction == "non_face":
        return TEMPLATES["non_face"]
    if prediction == "real":
        return TEMPLATES["real"]
    if prediction == "fake":
        return TEMPLATES["ai_generated"]
    region_str = " and ".join(REGION_DISPLAY.get(r, r) for r in regions)
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

def run_single(image_path, l1_model, l2_model, gradcam_l1, gradcam_l2,
               artifact_model, device,
               save_heatmap=False, output_dir=None, jpeg_preprocess=True):
    try:
        pil_img = Image.open(image_path).convert("RGB")
    except Exception as e:
        return {"error": str(e), "image": str(image_path)}

    if jpeg_preprocess:
        pil_img = preprocess_jpeg(pil_img, quality=85)

    # 2026-08-11: face-presence gate, checked BEFORE any classifier runs (both
    # for correctness -- a non-face input has no meaningful real/fake/filter
    # answer -- and to skip wasted inference on inputs we're about to reject).
    if not has_face(pil_img):
        return {
            "schema_version":     "2.1.0",
            "model_version":      "v8.11",
            "image":              os.path.basename(image_path),
            "prediction":         "non_face",
            "confidence":         None,
            "class_probs":        None,
            "artifact_types":     [],
            "suspicious_regions": [],
            "explanation":        TEMPLATES["non_face"],
        }

    image_np     = np.array(pil_img.resize((224, 224)))
    input_tensor = transform_infer(pil_img).unsqueeze(0).to(device)

    hp = hierarchical_predict(input_tensor, l1_model, l2_model, requires_grad=save_heatmap)
    prediction = hp["prediction"]
    confidence = hp["confidence"]
    all_probs  = {c: round(p, 4) for c, p in hp["class_probs"].items()}

    # suspicious_regions: source depends on prediction class.
    # fake -> intentionally always []: our CURRENT fake-class training sources
    # (AIGuard, DF40 diffusion/EFS methods) are whole-face synthesis with no
    # official manipulation mask, so there is no region-level ground truth to
    # train or validate against for these (the FakeVLM-distilled region head
    # this used to call was found to be near-total label degeneracy -- 6/8
    # regions at 99.5-100% positive rate, no-image baseline already explained
    # 87% of its reported F1). NOTE (2026-08-11): this is a property of our
    # current fake sources, not of "fake" in general -- FaceForensics++
    # DOES ship official binary manipulation masks for its classic methods
    # (Deepfakes/Face2Face/FaceSwap/NeuralTextures), which we don't currently
    # train on. If FF++ is added later, region-level fake explanations become
    # possible for that subset specifically -- see TODO.md 2026-08-11 entry.
    # Fake explanations are global-level only for now (Grad-CAM++ heatmap +
    # a single non-localized sentence), not per-region claims.
    if prediction in ("real", "fake"):
        regions = []
    else:
        # filter: derive from artifact_type after classification (below)
        regions = []  # filled in after artifact_types determined below

    # Artifact type
    if prediction == "filter" and artifact_model is not None:
        art_tag, _ = classify_artifact(pil_img, artifact_model, device)
        artifact_types = [art_tag]
    else:
        image_np_for_stat = np.array(pil_img.resize((224, 224)))
        artifact_types = infer_artifact_type(prediction, regions, image_np_for_stat)

    # filter regions: rule-based from artifact_type
    if prediction == "filter":
        regions = ARTIFACT_REGION_MAP.get(artifact_types[0] if artifact_types else "unknown_filter", [])

    explanation = build_explanation(prediction, artifact_types, regions)

    result = {
        "schema_version":    "2.1.0",
        "model_version":     "v8.11",
        "image":             os.path.basename(image_path),
        "prediction":        prediction,
        "confidence":        round(confidence, 4),
        "class_probs":       all_probs,
        "artifact_types":    artifact_types,
        "suspicious_regions": regions,
        "explanation":       explanation,
    }

    if save_heatmap and output_dir:
        gradcam = gradcam_l1 if hp["gradcam_layer"] == "l1" else gradcam_l2
        cam      = gradcam.generate(input_tensor, hp["gradcam_class_idx"])
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
    print(f"Loading v8.11 hierarchical classifier:")
    print(f"  Layer1 (real vs manipulated): {LAYER1_WEIGHTS_PATH}")
    print(f"  Layer2 (fake vs filter):      {LAYER2_WEIGHTS_PATH}")

    l1_model = DualBranchModel(num_classes=2).to(device)
    l1_model.load_state_dict(torch.load(LAYER1_WEIGHTS_PATH, map_location=device))
    l1_model.eval()
    gradcam_l1 = GradCAMPlusPlus(l1_model, l1_model.spatial_branch.conv5)

    l2_model = DualBranchModel(num_classes=2).to(device)
    l2_model.load_state_dict(torch.load(LAYER2_WEIGHTS_PATH, map_location=device))
    l2_model.eval()
    gradcam_l2 = GradCAMPlusPlus(l2_model, l2_model.spatial_branch.conv5)

    artifact_model = None
    if os.path.exists(ARTIFACT_WEIGHTS_PATH):
        artifact_model = build_artifact_model().to(device)
        artifact_model.load_state_dict(
            torch.load(ARTIFACT_WEIGHTS_PATH, map_location=device))
        artifact_model.eval()
        print(f"Artifact classifier loaded from {ARTIFACT_WEIGHTS_PATH}")
    else:
        print("Artifact classifier not found — using heuristic fallback")

    # NOTE: the FakeVLM-distilled region head (region_head_v1.pth) that used
    # to provide "fake" class suspicious_regions has been removed (2026-08-02).
    # Phase 2 found it was near-total label degeneracy (docs/phase2_story.md);
    # fake explanations are now intentionally global-level only.

    jpeg_pre = not args.no_jpeg_preproc

    # ── single image ──
    if args.image:
        out_dir = args.output_dir or os.path.join(BASE, "explanation_output")
        os.makedirs(out_dir, exist_ok=True)
        result = run_single(args.image, l1_model, l2_model, gradcam_l1, gradcam_l2,
                            artifact_model, device,
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
        r = run_single(str(img_path), l1_model, l2_model, gradcam_l1, gradcam_l2,
                       artifact_model, device,
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
