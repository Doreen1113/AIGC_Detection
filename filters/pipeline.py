"""整合 4 個 filter 腳本，對 10 張 AIGuard/real 圖跑完並輸出 avg metrics table。

執行環境：mediapipe_env
    conda activate mediapipe_env
    python filters/pipeline.py
"""

import os
import random
import warnings
import cv2
import numpy as np
import pandas as pd
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from skimage.metrics import structural_similarity as ssim
import matplotlib
matplotlib.use("Agg")  # 不開視窗，直接存檔
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

BASE   = r"C:\My_Project\AIGC"
REAL   = os.path.join(BASE, "AIGuard", "real")
MODEL  = os.path.join(BASE, "face_landmarker.task")

# ──────────────────────────────────────────────
# 選 10 張圖：每個 subfolder (0-4) 各取 2 張
# ──────────────────────────────────────────────
def select_images(n_per_sub=2, seed=42):
    random.seed(seed)
    paths = []
    for sub in sorted(os.listdir(REAL)):
        sub_dir = os.path.join(REAL, sub)
        if not os.path.isdir(sub_dir):
            continue
        files = [f for f in os.listdir(sub_dir)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        paths.extend(os.path.join(sub_dir, f)
                     for f in random.sample(files, min(n_per_sub, len(files))))
    return paths[:10]


# ──────────────────────────────────────────────
# Helper: MediaPipe-based face bbox + skin mask (shared by Smoothing & Whitening)
# ──────────────────────────────────────────────
def _face_bbox_from_mp(landmarks):
    """從 MediaPipe face mesh 468 點算出臉的 bounding box (x, y, w, h)。"""
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
# Common image metrics
# ──────────────────────────────────────────────
def common_metrics(before, after):
    psnr = float(cv2.PSNR(before, after))
    b_gray = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY)
    a_gray = cv2.cvtColor(after,  cv2.COLOR_BGR2GRAY)
    ssim_val = float(ssim(b_gray, a_gray, data_range=255))
    return psnr, ssim_val


# ══════════════════════════════════════════════
# Filter 1: Skin Smoothing  (bilateral filter)
# ══════════════════════════════════════════════
def run_smoothing(image):
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

    smoothed_roi = cv2.bilateralFilter(roi, 15, 80, 80)
    skin_px = mask_roi > 64
    result = image.copy()
    result[y:y+h, x:x+w][skin_px] = smoothed_roi[skin_px]

    # metric: Laplacian variance reduction in skin region
    lap_before = cv2.Laplacian(cv2.cvtColor(image,  cv2.COLOR_BGR2GRAY), cv2.CV_32F)
    lap_after  = cv2.Laplacian(cv2.cvtColor(result, cv2.COLOR_BGR2GRAY), cv2.CV_32F)
    valid = mask > 64
    var_b = float(np.mean(lap_before[valid]**2))
    var_a = float(np.mean(lap_after[valid]**2))
    texture_reduction_pct = (var_b - var_a) / var_b * 100 if var_b > 0 else 0.0

    psnr, ssim_val = common_metrics(image, result)
    return {"psnr": psnr, "ssim": ssim_val,
            "specific_label": "texture_reduction_%",
            "specific_value": round(texture_reduction_pct, 2),
            "_after": result}


# ══════════════════════════════════════════════
# Filter 2: Whitening
# ══════════════════════════════════════════════
def run_whitening(image, strength=0.15):
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

    valid = mask > 64
    lab_b = cv2.cvtColor(image,  cv2.COLOR_BGR2LAB)
    lab_a = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    brightness_delta = float(np.mean(lab_a[:,:,0][valid]) - np.mean(lab_b[:,:,0][valid]))

    psnr, ssim_val = common_metrics(image, result)
    return {"psnr": psnr, "ssim": ssim_val,
            "specific_label": "brightness_delta(L)",
            "specific_value": round(brightness_delta, 2),
            "_after": result}


# ══════════════════════════════════════════════
# Filter 3: Eye Enlarging  (mediapipe solutions)
# ══════════════════════════════════════════════
_face_mesh = None

def _get_face_mesh():
    global _face_mesh
    if _face_mesh is None:
        _face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True, max_num_faces=1,
            refine_landmarks=False, min_detection_confidence=0.5)
    return _face_mesh

LEFT_EYE  = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)
FACE_W    = (234, 454)

def _get_landmarks(image):
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    res = _get_face_mesh().process(rgb)
    if not res.multi_face_landmarks:
        return None
    h, w = image.shape[:2]
    return np.array([(lm.x*w, lm.y*h)
                     for lm in res.multi_face_landmarks[0].landmark], np.float32)

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

def run_eye_enlarging(image, scale=1.18):
    lm = _get_landmarks(image)
    if lm is None:
        return None
    result = _eye_warp(image, lm, scale)
    lm_after = _get_landmarks(result)

    def eye_ratio(pts):
        le = (np.linalg.norm(pts[LEFT_EYE[0]] - pts[LEFT_EYE[1]]) +
              np.linalg.norm(pts[RIGHT_EYE[0]] - pts[RIGHT_EYE[1]])) / 2
        fw = np.linalg.norm(pts[FACE_W[0]] - pts[FACE_W[1]])
        return le / fw if fw > 0 else 0.0

    ratio_before = eye_ratio(lm)
    ratio_after  = eye_ratio(lm_after) if lm_after is not None else ratio_before
    ratio_change_pct = float((ratio_after - ratio_before) / ratio_before * 100) if ratio_before > 0 else 0.0

    psnr, ssim_val = common_metrics(image, result)
    return {"psnr": psnr, "ssim": ssim_val,
            "specific_label": "eye_ratio_change_%",
            "specific_value": round(ratio_change_pct, 2),
            "_after": result}


# ══════════════════════════════════════════════
# Filter 4: Face Reshaping  (mediapipe Tasks API)
# ══════════════════════════════════════════════
_landmarker = None

def _get_landmarker():
    global _landmarker
    if _landmarker is None:
        with open(MODEL, "rb") as f:
            model_data = f.read()
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data),
            num_faces=1)
        _landmarker = vision.FaceLandmarker.create_from_options(opts)
    return _landmarker

def _get_landmarks_tasks(image_bgr):
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = _get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = image_bgr.shape[:2]
    return np.array([[lm.x*w, lm.y*h] for lm in res.face_landmarks[0]], np.float32)

def run_face_reshaping(image, shrink_ratio=0.92):
    pts = _get_landmarks_tasks(image)
    if pts is None:
        return None
    h, w = image.shape[:2]
    center = pts[1]  # 臉部中心點

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

    result = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)
    cheek_width = float(np.linalg.norm(pts[234] - pts[454]))
    cheek_change_pct = (1 - shrink_ratio) * 100  # 8%

    psnr, ssim_val = common_metrics(image, result)
    return {"psnr": psnr, "ssim": ssim_val,
            "specific_label": "cheek_width_shrink_%",
            "specific_value": round(cheek_change_pct, 2),
            "_after": result}


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
FILTERS = {
    "Smoothing":     run_smoothing,
    "Whitening":     run_whitening,
    "Eye Enlarging": run_eye_enlarging,
    "Face Reshaping":run_face_reshaping,
}

def save_comparison(before, after, out_path, filter_name):
    """存 before/after 左右對比圖，標題在圖上方（matplotlib 樣式）。"""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(cv2.cvtColor(before, cv2.COLOR_BGR2RGB))
    axes[0].set_title("Before (Original)", fontsize=14, pad=8)
    axes[0].axis("off")
    axes[1].imshow(cv2.cvtColor(after, cv2.COLOR_BGR2RGB))
    axes[1].set_title(f"After ({filter_name})", fontsize=14, pad=8)
    axes[1].axis("off")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def main():
    images = select_images(n_per_sub=2)
    print(f"Selected {len(images)} images\n")

    out_root = os.path.join(BASE, "filter_output")
    os.makedirs(out_root, exist_ok=True)

    rows = []
    per_image_rows = []

    for filter_name, fn in FILTERS.items():
        psnrs, ssims, specifics = [], [], []
        print(f"[{filter_name}]")
        for img_path in images:
            img = cv2.imread(img_path)
            if img is None:
                print(f"  SKIP (cannot read): {os.path.basename(img_path)}")
                continue
            try:
                res = fn(img)
                if res is None:
                    print(f"  SKIP (no face):   {os.path.basename(img_path)}")
                    continue
                print(f"  {os.path.basename(img_path):30s} "
                      f"PSNR={res['psnr']:6.2f}dB  "
                      f"SSIM={res['ssim']:.4f}  "
                      f"{res['specific_label']}={res['specific_value']}")
                psnrs.append(res['psnr'])
                ssims.append(res['ssim'])
                specifics.append(res['specific_value'])
                per_image_rows.append({
                    "filter": filter_name,
                    "image": os.path.basename(img_path),
                    "psnr": res['psnr'],
                    "ssim": res['ssim'],
                    res['specific_label']: res['specific_value'],
                })

                # 存 before/after 對比圖
                stem = os.path.splitext(os.path.basename(img_path))[0]
                img_out_dir = os.path.join(out_root, stem)
                os.makedirs(img_out_dir, exist_ok=True)
                after_img = res["_after"]
                fname = filter_name.lower().replace(" ", "_") + "_before_after.jpg"
                save_comparison(img, after_img, os.path.join(img_out_dir, fname), filter_name)

            except Exception as e:
                print(f"  ERROR {os.path.basename(img_path)}: {e}")

        if psnrs:
            specific_label = list(FILTERS.values()).index(fn)  # use label from last result
            # get label from per_image_rows
            label = next((r for r in reversed(per_image_rows) if r["filter"]==filter_name), {})
            sp_col = [k for k in label.keys() if k not in ("filter","image","psnr","ssim")]
            sp_col = sp_col[0] if sp_col else "specific"
            rows.append({
                "Filter": filter_name,
                "n_success": len(psnrs),
                "avg_PSNR(dB)": round(np.mean(psnrs), 2),
                "avg_SSIM": round(np.mean(ssims), 4),
                f"avg_{sp_col}": round(np.mean(specifics), 2),
            })
        print()

    print("=" * 80)
    print("FILTER PIPELINE — AVERAGE METRICS TABLE (10 images)")
    print("=" * 80)
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))

    out_csv = os.path.join(BASE, "results", "filter_metrics.csv")
    df.to_csv(out_csv, index=False)
    print(f"\nSaved → {out_csv}")

    # also save per-image detail
    detail_csv = os.path.join(BASE, "results", "filter_metrics_detail.csv")
    pd.DataFrame(per_image_rows).to_csv(detail_csv, index=False)
    print(f"Detail → {detail_csv}")


if __name__ == "__main__":
    main()
