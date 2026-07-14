"""
對 AIGuard real 圖批量跑 4 種濾鏡，生成 Filter class 資料集。

執行環境：mediapipe_env
    conda activate mediapipe_env
    python filters/generate_filter_dataset.py

輸出：C:\\My_Project\\AIGC\\filter_data\\
    smoothing\\       (filtered images)
    whitening\\
    eye_enlarging\\
    face_reshaping\\
"""

import os
import sys
import random
import warnings
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

warnings.filterwarnings("ignore")

BASE        = r"C:\My_Project\AIGC"
REAL_DIR    = os.path.join(BASE, "AIGuard", "real")
MODEL_PATH  = os.path.join(BASE, "face_landmarker.task")
OUT_ROOT    = os.path.join(BASE, "filter_data")

N_PER_FILTER = 5000  # 每種濾鏡產出張數 → 共 20000 張 filter data


# ──────────────────────────────────────────────
# MediaPipe helpers — Tasks API only (0.10.35+)
# ──────────────────────────────────────────────
LEFT_EYE  = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)

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
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = _get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = image_bgr.shape[:2]
    return np.array([[lm.x*w, lm.y*h] for lm in res.face_landmarks[0]], np.float32)

def _face_bbox_from_mp(landmarks):
    xs, ys = landmarks[:, 0], landmarks[:, 1]
    x, y = int(np.min(xs)), int(np.min(ys))
    w, h = int(np.max(xs)) - x, int(np.max(ys)) - y
    return (x, y, w, h)

def _skin_mask_mp(image, face):
    x, y, w, h = face
    fmask = np.zeros(image.shape[:2], np.uint8)
    cv2.ellipse(fmask, (x+w//2, y+int(h*0.52)), (int(w*0.44), int(h*0.48)), 0, 0, 360, 255, -1)
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    smask = cv2.inRange(ycrcb, np.array([0,133,77]), np.array([255,173,127]))
    mask = cv2.bitwise_and(fmask, smask)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7,7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)
    mask = cv2.GaussianBlur(mask, (21,21), 0)
    return mask if np.count_nonzero(mask > 32) > 300 else None


# ──────────────────────────────────────────────
# 4 Filters
# ──────────────────────────────────────────────
def apply_smoothing(image):
    lm = _get_landmarks(image)
    if lm is None:
        return None
    face = _face_bbox_from_mp(lm)
    mask = _skin_mask_mp(image, face)
    if mask is None:
        return None
    x, y, w, h = face
    roi = image[y:y+h, x:x+w].copy()
    mask_roi = mask[y:y+h, x:x+w]
    smoothed = cv2.bilateralFilter(roi, 15, 80, 80)
    result = image.copy()
    result[y:y+h, x:x+w][mask_roi > 64] = smoothed[mask_roi > 64]
    return result

def apply_whitening(image, strength=0.15):
    lm = _get_landmarks(image)
    if lm is None:
        return None
    face = _face_bbox_from_mp(lm)
    mask = _skin_mask_mp(image, face)
    if mask is None:
        return None
    mask_f = mask.astype(np.float32) / 255.0
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:,:,0] += strength * (255.0 - lab[:,:,0])
    brightened = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(brightened, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:,:,1] *= 1.0 - 0.18 * strength
    whitened = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    blend = mask_f[:,:,None]
    result = np.clip(image.astype(np.float32)*(1-blend) + whitened.astype(np.float32)*blend, 0, 255).astype(np.uint8)
    return result

def _eye_warp(image, landmarks, scale=1.18, radius_factor=1.70):
    h, w = image.shape[:2]
    result = image.copy()
    for eye_idx in (LEFT_EYE, RIGHT_EYE):
        pts = landmarks[list(eye_idx)]
        center = np.mean(pts, axis=0)
        eye_w = np.linalg.norm(landmarks[eye_idx[0]] - landmarks[eye_idx[1]])
        radius = max(eye_w * radius_factor, 8.0)
        cx, cy = center
        x0 = max(0, int(cx - radius)); x1 = min(w, int(cx + radius + 1))
        y0 = max(0, int(cy - radius)); y1 = min(h, int(cy + radius + 1))
        gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                              np.arange(y0, y1, dtype=np.float32))
        dx, dy = gx - cx, gy - cy
        nd = np.clip(np.sqrt(dx**2 + dy**2) / radius, 0.0, 1.0)
        ls = 1.0 + (scale - 1.0) * (1.0 - nd)**2
        map_x = (cx + dx / ls).astype(np.float32)
        map_y = (cy + dy / ls).astype(np.float32)
        roi = cv2.remap(image, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
        alpha = np.clip((1.0 - nd) / 0.18, 0.0, 1.0)[:,:,None]
        blended = image[y0:y1, x0:x1].astype(np.float32)*(1-alpha) + roi.astype(np.float32)*alpha
        result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return result

def apply_eye_enlarging(image):
    lm = _get_landmarks(image)
    if lm is None:
        return None
    return _eye_warp(image, lm)

def apply_face_reshaping(image, shrink_ratio=0.92):
    pts = _get_landmarks(image)
    if pts is None:
        return None
    h, w = image.shape[:2]
    center = pts[1]
    map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32),
                                np.arange(h, dtype=np.float32))
    radius = 60.0
    for cheek_idx in (234, 454):
        cx, cy = pts[cheek_idx]
        x0, x1 = max(0, int(cx-radius)), min(w, int(cx+radius))
        y0, y1 = max(0, int(cy-radius)), min(h, int(cy+radius))
        gx = map_x[y0:y1, x0:x1]; gy = map_y[y0:y1, x0:x1]
        dx, dy = gx - cx, gy - cy
        dist = np.sqrt(dx**2 + dy**2)
        within = dist < radius
        factor = np.where(within, 1 - (1 - shrink_ratio) * (1 - dist / radius), 1.0)
        map_x[y0:y1, x0:x1] = np.where(within, center[0] + (gx - center[0]) * factor, gx)
        map_y[y0:y1, x0:x1] = np.where(within, center[1] + (gy - center[1]) * factor, gy)
    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)


FILTERS = {
    "smoothing":      apply_smoothing,
    "whitening":      apply_whitening,
    "eye_enlarging":  apply_eye_enlarging,
    "face_reshaping": apply_face_reshaping,
}


# ──────────────────────────────────────────────
# Collect real image paths
# ──────────────────────────────────────────────
def collect_real_images(n_total):
    paths = []
    for sub in sorted(os.listdir(REAL_DIR)):
        sub_path = os.path.join(REAL_DIR, sub)
        if not os.path.isdir(sub_path):
            continue
        files = [os.path.join(sub_path, f) for f in os.listdir(sub_path)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        paths.extend(files)
    random.seed(42)
    random.shuffle(paths)
    return paths[:n_total]


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == "__main__":
    for name in FILTERS:
        os.makedirs(os.path.join(OUT_ROOT, name), exist_ok=True)

    # 需要處理的總圖片量（每種濾鏡各要 N_PER_FILTER 張成功）
    candidate_paths = collect_real_images(n_total=N_PER_FILTER * 2)
    print(f"Candidate real images: {len(candidate_paths)}")
    print(f"Target: {N_PER_FILTER} per filter × 4 = {N_PER_FILTER*4} total\n")

    counts = {name: 0 for name in FILTERS}
    skipped = 0

    for i, img_path in enumerate(candidate_paths):
        all_done = all(c >= N_PER_FILTER for c in counts.values())
        if all_done:
            break

        img = cv2.imread(img_path)
        if img is None:
            skipped += 1
            continue

        fname = os.path.splitext(os.path.basename(img_path))[0]

        for filter_name, fn in FILTERS.items():
            if counts[filter_name] >= N_PER_FILTER:
                continue
            try:
                result = fn(img)
                if result is None:
                    continue
                out_path = os.path.join(OUT_ROOT, filter_name, f"{fname}_{filter_name}.jpg")
                cv2.imwrite(out_path, result)
                counts[filter_name] += 1
            except Exception:
                continue

        if (i + 1) % 50 == 0:
            print(f"[{i+1}/{len(candidate_paths)}] "
                  + " | ".join(f"{k}: {v}" for k, v in counts.items()))

    print("\n=== Done ===")
    for name, count in counts.items():
        print(f"  {name}: {count} images → {os.path.join(OUT_ROOT, name)}")
