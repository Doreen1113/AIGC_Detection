"""
Stress test: fake image + beauty filter → pipeline
測試 fake 圖加美顏 filter 後是否被誤判為 real 或 filter。
涵蓋全部 4 種 filter 類型（smoothing / whitening / eye_enlarging / face_reshaping）。

Usage:
    python AIGuard/stress_test_fake_filter.py
"""

import sys, json, random, warnings
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
MODEL_PATH = str(BASE / "face_landmarker.task")
sys.path.insert(0, str(BASE))

from pipeline import (
    DualBranchModel, GradCAMPlusPlus, build_artifact_model,
    transform_infer, preprocess_jpeg,
    top_activated_regions, infer_artifact_type, build_explanation,
    CLASSES, WEIGHTS_PATH, ARTIFACT_WEIGHTS_PATH
)
import torch
import os

# ── MediaPipe landmarker ──────────────────────────────────────────────────────

_landmarker = None

def _get_landmarker():
    global _landmarker
    if _landmarker is None:
        with open(MODEL_PATH, "rb") as f:
            model_data = f.read()
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data),
            num_faces=1)
        _landmarker = vision.FaceLandmarker.create_from_options(opts)
    return _landmarker


def _get_landmarks(image_bgr):
    """Returns (N,2) float32 array or None if no face detected."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = _get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = image_bgr.shape[:2]
    return np.array([[lm.x * w, lm.y * h] for lm in res.face_landmarks[0]], np.float32)


# ── Pixel-level filters (RGB in → RGB out, always succeed) ───────────────────

def apply_smoothing(img_rgb, strength="medium"):
    d = {"light": (9, 50, 50), "medium": (15, 80, 80), "heavy": (25, 120, 120)}[strength]
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    return cv2.cvtColor(cv2.bilateralFilter(bgr, d[0], d[1], d[2]), cv2.COLOR_BGR2RGB)


def apply_whitening(img_rgb, strength="medium"):
    factor = {"light": 1.10, "medium": 1.20, "heavy": 1.35}[strength]
    lab = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[:, :, 0] = np.clip(lab[:, :, 0] * factor, 0, 255)
    return cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)


def apply_combined(img_rgb, strength="medium"):
    return apply_whitening(apply_smoothing(img_rgb, strength), strength)


# ── Geometric filters (RGB in → RGB out or None if no landmarks) ──────────────

_LEFT_EYE  = (33, 133, 159, 145)
_RIGHT_EYE = (362, 263, 386, 374)


def apply_eye_enlarging(img_rgb, scale=1.18, radius_factor=1.70):
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    lm = _get_landmarks(bgr)
    if lm is None:
        return None
    h, w = bgr.shape[:2]
    result = bgr.copy()
    for eye_idx in (_LEFT_EYE, _RIGHT_EYE):
        pts = lm[list(eye_idx)]
        center = np.mean(pts, axis=0)
        eye_w  = np.linalg.norm(lm[eye_idx[0]] - lm[eye_idx[1]])
        radius = max(eye_w * radius_factor, 8.0)
        cx, cy = center
        x0, x1 = max(0, int(cx - radius)), min(w, int(cx + radius + 1))
        y0, y1 = max(0, int(cy - radius)), min(h, int(cy + radius + 1))
        gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                              np.arange(y0, y1, dtype=np.float32))
        dx, dy = gx - cx, gy - cy
        nd = np.clip(np.sqrt(dx**2 + dy**2) / radius, 0.0, 1.0)
        ls = 1.0 + (scale - 1.0) * (1.0 - nd)**2
        map_x = (cx + dx / ls).astype(np.float32)
        map_y = (cy + dy / ls).astype(np.float32)
        roi   = cv2.remap(bgr, map_x, map_y, cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REFLECT_101)
        alpha   = np.clip((1.0 - nd) / 0.18, 0.0, 1.0)[:, :, None]
        blended = (bgr[y0:y1, x0:x1].astype(np.float32) * (1 - alpha)
                   + roi.astype(np.float32) * alpha)
        result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_BGR2RGB)


def apply_face_reshaping(img_rgb, shrink_ratio=0.92):
    bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    pts = _get_landmarks(bgr)
    if pts is None:
        return None
    h, w = bgr.shape[:2]
    center = pts[1]
    map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32),
                                np.arange(h, dtype=np.float32))
    radius = 60.0
    for cheek_idx in (234, 454):
        cx, cy = pts[cheek_idx]
        x0, x1 = max(0, int(cx - radius)), min(w, int(cx + radius))
        y0, y1 = max(0, int(cy - radius)), min(h, int(cy + radius))
        gx = map_x[y0:y1, x0:x1]
        gy = map_y[y0:y1, x0:x1]
        dx, dy = gx - cx, gy - cy
        dist    = np.sqrt(dx**2 + dy**2)
        within  = dist < radius
        factor  = np.where(within, 1 - (1 - shrink_ratio) * (1 - dist / radius), 1.0)
        map_x[y0:y1, x0:x1] = np.where(within, center[0] + (gx - center[0]) * factor, gx)
        map_y[y0:y1, x0:x1] = np.where(within, center[1] + (gy - center[1]) * factor, gy)
    return cv2.cvtColor(
        cv2.remap(bgr, map_x, map_y, cv2.INTER_LINEAR),
        cv2.COLOR_BGR2RGB
    )


# ── Filter registry ───────────────────────────────────────────────────────────

FILTERS = {
    "smoothing_light":    lambda x: apply_smoothing(x, "light"),
    "smoothing_medium":   lambda x: apply_smoothing(x, "medium"),
    "smoothing_heavy":    lambda x: apply_smoothing(x, "heavy"),
    "whitening_medium":   lambda x: apply_whitening(x, "medium"),
    "combined_medium":    lambda x: apply_combined(x, "medium"),
    "combined_heavy":     lambda x: apply_combined(x, "heavy"),
    "eye_enlarging":      apply_eye_enlarging,
    "face_reshaping":     apply_face_reshaping,
}


# ── Pipeline inference ────────────────────────────────────────────────────────

def run_inference(pil_img, model, device):
    pil_img = preprocess_jpeg(pil_img, quality=85)
    t = transform_infer(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(model(t), dim=1)[0]
    idx = int(probs.argmax())
    return CLASSES[idx], float(probs[idx]), {c: round(float(p), 3) for c, p in zip(CLASSES, probs)}


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    print(f"Model loaded ({WEIGHTS_PATH})")

    # 初始化 MediaPipe（只初始化一次）
    _get_landmarker()
    print("MediaPipe landmarker ready")

    # 排除 hard neg 訓練時已用過的圖（避免在訓練資料上測試）
    manifest = BASE / "splits" / "fake_filter_hard_neg.txt"
    used_stems = set()
    if manifest.exists():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if parts:
                # hard neg 路徑形如 .../fake_1234_1_smoothing.jpg
                # 原圖 stem = 去掉最後的 _smoothing / _whitening 等
                stem = Path(parts[0]).stem
                for suffix in ("_smoothing", "_whitening", "_eye_enlarging", "_face_reshaping"):
                    if stem.endswith(suffix):
                        stem = stem[: -len(suffix)]
                        break
                used_stems.add(stem)
    print(f"Excluding {len(used_stems)} stems used in hard neg training")

    # 收集未用過的 AIGuard fake 圖
    fake_dir = BASE / "AIGuard" / "fake"
    all_fake = []
    for sub in sorted(fake_dir.iterdir()):
        for f in sub.rglob("*"):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                if f.stem not in used_stems:
                    all_fake.append(f)

    # 加入 DF40 diffusion fake（從未參與 hard neg 生成）
    df40_dir = BASE / "DF40"
    if df40_dir.exists():
        for f in df40_dir.rglob("*"):
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                all_fake.append(f)

    random.seed(99)  # 不同 seed，避免和 hard neg generation (seed=42) 重疊
    N = 200
    fake_imgs = random.sample(all_fake, min(N, len(all_fake)))
    print(f"Using {len(fake_imgs)} held-out fake images "
          f"(AIGuard unseen + DF40, excluded hard neg training set)\n")

    results = []
    changed = {fname: 0 for fname in FILTERS}
    skipped = {fname: 0 for fname in FILTERS}

    header = f"{'Image':<28} {'Original':>8}  " + "  ".join(f"{k:<22}" for k in FILTERS)
    print(header)
    print("-" * len(header))

    for img_path in fake_imgs:
        pil      = Image.open(img_path).convert("RGB")
        img_np   = np.array(pil.resize((224, 224)))
        orig_pred, orig_conf, orig_probs = run_inference(pil, model, device)

        row = {"image": img_path.name, "original": orig_pred, "probs": orig_probs, "filters": {}}
        filter_results = []

        for fname, ffunc in FILTERS.items():
            filtered_np = ffunc(img_np)

            if filtered_np is None:
                # Geometric filter failed (no landmarks found on this fake face)
                skipped[fname] += 1
                row["filters"][fname] = {"pred": "skip", "conf": 0.0}
                filter_results.append(f"{'skip(no lm)':<22}")
                continue

            filtered_pil = Image.fromarray(filtered_np)
            pred, conf, probs = run_inference(filtered_pil, model, device)
            row["filters"][fname] = {"pred": pred, "conf": round(conf, 3)}
            filter_results.append(f"{pred}({conf:.2f}){'':<10}")
            if pred != orig_pred:
                changed[fname] += 1

        results.append(row)
        print(f"{img_path.name:<28} {orig_pred:>8}  " + "  ".join(filter_results))

    n_valid = len(fake_imgs)
    print(f"\n{'='*60}")
    print(f"Total fake images: {n_valid}\n")
    print(f"{'Filter type':<24} {'Changed':>8}  {'Skipped(no lm)':>16}  {'Change%':>8}")
    print("-" * 62)
    for fname in FILTERS:
        valid_n = n_valid - skipped[fname]
        pct = changed[fname] / valid_n * 100 if valid_n > 0 else 0
        print(f"  {fname:<22}: {changed[fname]:2d}/{valid_n:2d}  ({skipped[fname]:3d} skipped)  {pct:6.0f}%")

    out = BASE / "results" / "stress_test_fake_filter.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetailed results → {out}")


if __name__ == "__main__":
    main()
