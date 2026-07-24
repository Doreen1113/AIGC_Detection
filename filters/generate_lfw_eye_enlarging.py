"""
Generate eye_enlarging training data from LFW images.
Excludes all images already used in truetest_filter.txt or truetest_real.txt.

Output: filter_data/lfw_eye_enlarging/  (up to N_TARGET images, label=2)

python filters/generate_lfw_eye_enlarging.py
"""
import os, random, warnings
import cv2, numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from pathlib import Path

warnings.filterwarnings("ignore")

BASE        = Path(r"C:\My_Project\AIGC")
LFW_DIR     = BASE / "lfw"
MODEL_PATH  = str(BASE / "face_landmarker.task")
OUT_DIR     = BASE / "filter_data" / "lfw_eye_enlarging"
SPLITS_DIR  = BASE / "splits"
N_TARGET    = 6000
SEED        = 42

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
        roi = cv2.remap(image, map_x, map_y, cv2.INTER_CUBIC,
                        borderMode=cv2.BORDER_REFLECT_101)
        alpha = np.clip((1.0 - nd) / 0.18, 0.0, 1.0)[:, :, None]
        blended = (image[y0:y1, x0:x1].astype(np.float32) * (1 - alpha)
                   + roi.astype(np.float32) * alpha)
        result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return result


def collect_excluded():
    """Return set of absolute path strings that appear in truetest splits."""
    excluded = set()
    for fname in ("truetest_real.txt", "truetest_filter.txt",
                  "truetest_fake.txt"):
        p = SPLITS_DIR / fname
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    excluded.add(line.lower())
    # Also exclude by (person, img_id) pairs derived from filter test names
    excluded_pairs = set()
    p = SPLITS_DIR / "truetest_filter.txt"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            name = Path(line.strip()).stem  # e.g. eye_enlarging_Tony_Blair_0025
            parts = name.split("_", 1)     # ['eye', 'enlarging_Tony_Blair_0025']
            # handle multi-word filter types
            for ft in ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]:
                if name.startswith(ft + "_"):
                    person_img = name[len(ft)+1:]  # e.g. Tony_Blair_0025
                    excluded_pairs.add(person_img.lower())
                    break
    return excluded, excluded_pairs


def collect_lfw_candidates(excluded_paths, excluded_pairs):
    candidates = []
    for person_dir in sorted(LFW_DIR.iterdir()):
        if not person_dir.is_dir():
            continue
        for img_path in sorted(person_dir.glob("*.jpg")):
            # Exclude by exact path
            if str(img_path).lower() in excluded_paths:
                continue
            # Exclude by (person_imgid) pair
            stem_lower = img_path.stem.lower()
            if stem_lower in excluded_pairs:
                continue
            candidates.append(img_path)
    return candidates


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    excluded_paths, excluded_pairs = collect_excluded()
    print(f"Excluded: {len(excluded_paths)} paths, {len(excluded_pairs)} (person,img) pairs")

    candidates = collect_lfw_candidates(excluded_paths, excluded_pairs)
    print(f"LFW candidates: {len(candidates)}")

    random.seed(SEED)
    random.shuffle(candidates)

    done, skip = 0, 0
    for src_path in candidates:
        if done >= N_TARGET:
            break
        img = cv2.imread(str(src_path))
        if img is None:
            skip += 1
            continue
        lm = _get_landmarks(img)
        if lm is None:
            skip += 1
            continue
        result = _eye_warp(img, lm)
        out_name = f"lfw_eye_{src_path.stem}.jpg"
        cv2.imwrite(str(OUT_DIR / out_name), result, [cv2.IMWRITE_JPEG_QUALITY, 90])
        done += 1
        if done % 500 == 0:
            print(f"  {done}/{N_TARGET}  (skipped {skip})")

    print(f"\nDone: {done} images → {OUT_DIR}")
    print(f"Skipped (no face / read error): {skip}")
