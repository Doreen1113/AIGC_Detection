"""
Generate LFW-domain whitening and face_reshaping training data.

Root cause: True test filter set (249 images) are ALL LFW faces with filters applied.
  - smoothing:     100% recall (spatial effect generalizes fine)
  - whitening:      51.6% in v7.5 (only FFHQ whitening in training → domain gap)
  - face_reshaping: 85.5% in v7.5 (geometric effect helps, but can improve)
  - eye_enlarging:  53.2% in v7.5 (has LFW training data already)

This script generates 6,000 LFW+whitening and 6,000 LFW+face_reshaping,
excluding all images in truetest_real.txt / truetest_filter.txt.

Output:
  filter_data/lfw_whitening/      lfw_white_{stem}.jpg
  filter_data/lfw_face_reshaping/ lfw_reshape_{stem}.jpg

python filters/generate_lfw_filters.py
"""
import os, random, warnings
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from pathlib import Path

warnings.filterwarnings("ignore")

BASE       = Path(r"C:\My_Project\AIGC")
LFW_DIR    = BASE / "lfw"
MODEL_PATH = str(BASE / "face_landmarker.task")
SPLITS_DIR = BASE / "splits"
N_TARGET   = 6000
SEED       = 42

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

def _face_bbox(landmarks):
    xs, ys = landmarks[:, 0], landmarks[:, 1]
    x, y = int(np.min(xs)), int(np.min(ys))
    return (x, y, int(np.max(xs)) - x, int(np.max(ys)) - y)

def _skin_mask(image, face):
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

def apply_whitening(image, strength=0.15):
    lm = _get_landmarks(image)
    if lm is None:
        return None
    mask = _skin_mask(image, _face_bbox(lm))
    if mask is None:
        return None
    blend = mask.astype(np.float32)[:, :, None] / 255.0
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:,:,0] += strength * (255.0 - lab[:,:,0])
    brightened = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)
    hsv = cv2.cvtColor(brightened, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:,:,1] *= 1.0 - 0.18 * strength
    whitened = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)
    return np.clip(image.astype(np.float32)*(1-blend) + whitened.astype(np.float32)*blend, 0, 255).astype(np.uint8)

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
        factor = np.where(within, 1 - (1-shrink_ratio)*(1-dist/radius), 1.0)
        map_x[y0:y1, x0:x1] = np.where(within, center[0]+(gx-center[0])*factor, gx)
        map_y[y0:y1, x0:x1] = np.where(within, center[1]+(gy-center[1])*factor, gy)
    return cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)


def collect_excluded():
    excluded, excluded_pairs = set(), set()
    for fname in ("truetest_real.txt", "truetest_filter.txt", "truetest_fake.txt"):
        p = SPLITS_DIR / fname
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    excluded.add(line.lower())
    p = SPLITS_DIR / "truetest_filter.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            name = Path(line.strip()).stem
            for ft in ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]:
                if name.startswith(ft + "_"):
                    excluded_pairs.add(name[len(ft)+1:].lower())
                    break
    return excluded, excluded_pairs

def collect_lfw_candidates(excluded_paths, excluded_pairs):
    candidates = []
    for person_dir in sorted(LFW_DIR.iterdir()):
        if not person_dir.is_dir():
            continue
        for img_path in sorted(person_dir.glob("*.jpg")):
            if str(img_path).lower() in excluded_paths:
                continue
            if img_path.stem.lower() in excluded_pairs:
                continue
            candidates.append(img_path)
    return candidates

def generate_filter(candidates, apply_fn, out_dir, prefix):
    out_dir.mkdir(parents=True, exist_ok=True)
    done, skip = 0, 0
    for src in candidates:
        if done >= N_TARGET:
            break
        img = cv2.imread(str(src))
        if img is None:
            skip += 1
            continue
        try:
            result = apply_fn(img)
        except Exception:
            skip += 1
            continue
        if result is None:
            skip += 1
            continue
        out_name = f"{prefix}_{src.stem}.jpg"
        cv2.imwrite(str(out_dir / out_name), result, [cv2.IMWRITE_JPEG_QUALITY, 90])
        done += 1
        if done % 500 == 0:
            print(f"  [{prefix}] {done}/{N_TARGET}  skipped={skip}")
    print(f"  [{prefix}] Done: {done} images  (skipped {skip})")
    return done


if __name__ == "__main__":
    excluded_paths, excluded_pairs = collect_excluded()
    print(f"Excluded: {len(excluded_paths)} paths, {len(excluded_pairs)} (person,img) pairs")
    candidates = collect_lfw_candidates(excluded_paths, excluded_pairs)
    print(f"LFW candidates: {len(candidates)}")

    random.seed(SEED)
    random.shuffle(candidates)

    print("\n--- Generating LFW whitening ---")
    n_white = generate_filter(
        candidates,
        apply_whitening,
        BASE / "filter_data" / "lfw_whitening",
        "lfw_white")

    print("\n--- Generating LFW face_reshaping ---")
    n_reshape = generate_filter(
        candidates,
        apply_face_reshaping,
        BASE / "filter_data" / "lfw_face_reshaping",
        "lfw_reshape")

    print(f"\nTotal generated: whitening={n_white}  face_reshaping={n_reshape}")
    print("Next: python build_v76_splits.py")
