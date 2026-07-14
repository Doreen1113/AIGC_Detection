"""
Face attribute filtering using MediaPipe FaceMesh + InsightFace age estimation.
Detects: closed eyes / sunglasses / baby-child faces.

Run in base env:
  conda run -n base python AIGuard/face_attr_filter.py --dir AIGuard/real
  conda run -n base python AIGuard/face_attr_filter.py --dir AIGuard/real --dry_run

Thresholds:
  --ear_thresh   0.18   EAR below this → closed eyes
  --dark_thresh  30     eye-region mean brightness below this → sunglasses
  --age_thresh   18     InsightFace estimated age below this → baby/child
"""

import os
import csv
import json
import argparse
import math
import cv2
import numpy as np
from pathlib import Path

import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

from insightface.app import FaceAnalysis

BASE      = r"C:\My_Project\AIGC"
# MediaPipe FaceLandmarker model path
LANDMARKER_MODEL = os.path.join(BASE, "face_landmarker.task")

# MediaPipe 468-landmark indices for eyes
# Left eye  (from viewer's right)
LEFT_EYE_TOP    = [159, 160, 161]
LEFT_EYE_BOT    = [145, 144, 163]
LEFT_EYE_INNER  = 133
LEFT_EYE_OUTER  = 33
# Right eye
RIGHT_EYE_TOP   = [386, 385, 384]
RIGHT_EYE_BOT   = [374, 380, 381]
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Face outline for height
FACE_TOP    = 10    # forehead center
FACE_BOTTOM = 152   # chin


def load_landmarker():
    if not os.path.exists(LANDMARKER_MODEL):
        raise FileNotFoundError(
            f"face_landmarker.task not found at {LANDMARKER_MODEL}\n"
            f"Download from: https://storage.googleapis.com/mediapipe-models/"
            f"face_landmarker/face_landmarker/float16/1/face_landmarker.task"
        )
    opts = mp_vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_path=LANDMARKER_MODEL),
        num_faces=1,
        min_face_detection_confidence=0.4,
        min_face_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    )
    return mp_vision.FaceLandmarker.create_from_options(opts)


def lm_xy(lms, idx, w, h):
    l = lms[idx]
    return l.x * w, l.y * h


def eye_aspect_ratio(lms, top_ids, bot_ids, inner_id, outer_id, w, h):
    top_pts = [lm_xy(lms, i, w, h) for i in top_ids]
    bot_pts = [lm_xy(lms, i, w, h) for i in bot_ids]
    inner   = lm_xy(lms, inner_id, w, h)
    outer   = lm_xy(lms, outer_id, w, h)
    vert = np.mean([math.dist(t, b) for t, b in zip(top_pts, bot_pts)])
    horiz = math.dist(inner, outer)
    return vert / (horiz + 1e-6)


def eye_region_brightness(img, lms, top_ids, bot_ids, inner_id, outer_id, w, h, pad=4):
    xs = [lm_xy(lms, i, w, h)[0] for i in top_ids + bot_ids + [inner_id, outer_id]]
    ys = [lm_xy(lms, i, w, h)[1] for i in top_ids + bot_ids + [inner_id, outer_id]]
    x1, y1 = max(0, int(min(xs)) - pad), max(0, int(min(ys)) - pad)
    x2, y2 = min(w, int(max(xs)) + pad), min(h, int(max(ys)) + pad)
    if x2 <= x1 or y2 <= y1:
        return 255.0
    patch = img[y1:y2, x1:x2]
    gray  = cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY) if patch.ndim == 3 else patch
    return float(np.mean(gray))


def baby_score(lms, w, h):
    """
    Ratio: eye_center_y / face_height.
    Adults: eyes ~40-45% down the face → ratio ~0.40-0.45.
    Babies: eyes higher up → ratio > 0.47.
    """
    left_eye_y  = np.mean([lm_xy(lms, i, w, h)[1] for i in LEFT_EYE_TOP + LEFT_EYE_BOT])
    right_eye_y = np.mean([lm_xy(lms, i, w, h)[1] for i in RIGHT_EYE_TOP + RIGHT_EYE_BOT])
    eye_y = (left_eye_y + right_eye_y) / 2

    top_y = lm_xy(lms, FACE_TOP, w, h)[1]
    bot_y = lm_xy(lms, FACE_BOTTOM, w, h)[1]
    face_h = bot_y - top_y + 1e-6
    return (eye_y - top_y) / face_h


def analyze(img_path, landmarker, age_app, ear_thresh, dark_thresh, age_thresh):
    img = cv2.imread(img_path)
    if img is None:
        return None, "unreadable"
    h, w = img.shape[:2]
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = landmarker.detect(mp_img)
    if not result.face_landmarks:
        return None, "no_face"
    lms = result.face_landmarks[0]

    ear_l = eye_aspect_ratio(lms, LEFT_EYE_TOP,  LEFT_EYE_BOT,  LEFT_EYE_INNER,  LEFT_EYE_OUTER,  w, h)
    ear_r = eye_aspect_ratio(lms, RIGHT_EYE_TOP, RIGHT_EYE_BOT, RIGHT_EYE_INNER, RIGHT_EYE_OUTER, w, h)
    ear   = (ear_l + ear_r) / 2

    bright_l = eye_region_brightness(img, lms, LEFT_EYE_TOP,  LEFT_EYE_BOT,  LEFT_EYE_INNER,  LEFT_EYE_OUTER,  w, h)
    bright_r = eye_region_brightness(img, lms, RIGHT_EYE_TOP, RIGHT_EYE_BOT, RIGHT_EYE_INNER, RIGHT_EYE_OUTER, w, h)
    brightness = (bright_l + bright_r) / 2

    b_score = baby_score(lms, w, h)

    # Age estimation via InsightFace
    age = None
    if age_app is not None:
        faces_if = age_app.get(img)
        if faces_if:
            age = faces_if[0].age  # int or None

    flags = []
    if ear < ear_thresh:
        flags.append(f"closed_eye(EAR={ear:.3f})")
    if brightness < dark_thresh:
        flags.append(f"sunglasses(bright={brightness:.1f})")
    if age is not None and age < age_thresh:
        flags.append(f"baby(age={age})")

    details = {"ear": round(ear, 4), "brightness": round(brightness, 1), "age": age}
    return details, ",".join(flags) if flags else None


def export_samples(paths, dest_dir, n=30):
    import random
    os.makedirs(dest_dir, exist_ok=True)
    sample = random.sample(paths, min(n, len(paths)))
    for p in sample:
        import shutil
        shutil.copy2(p, os.path.join(dest_dir, Path(p).name))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",          required=True)
    parser.add_argument("--ear_thresh",   type=float, default=0.18,  help="EAR threshold for closed eyes")
    parser.add_argument("--dark_thresh",  type=float, default=30.0,  help="Eye brightness threshold for sunglasses")
    parser.add_argument("--age_thresh",   type=int,   default=18,    help="InsightFace age below this → baby/child")
    parser.add_argument("--dry_run",      action="store_true",       help="Print stats only, don't update clean_paths.txt")
    args = parser.parse_args()

    scan_dir = args.dir if os.path.isabs(args.dir) else os.path.join(BASE, args.dir)
    out_dir  = os.path.join(scan_dir, "clean_output")
    clean_txt = os.path.join(out_dir, "clean_paths.txt")

    if not os.path.exists(clean_txt):
        print("clean_paths.txt not found — run clean_dataset.py first")
        return

    paths = [p for p in open(clean_txt).read().splitlines() if p]
    print(f"\n=== Face Attribute Filter ===")
    print(f"  Input : {scan_dir}  ({len(paths)} images)")
    print(f"  EAR thresh={args.ear_thresh}  dark thresh={args.dark_thresh}  age thresh={args.age_thresh}\n")

    landmarker = load_landmarker()

    print("  Loading InsightFace (buffalo_l, detection+genderage only)...")
    age_app = FaceAnalysis(name='buffalo_l',
                           providers=['CUDAExecutionProvider', 'CPUExecutionProvider'],
                           allowed_modules=['detection', 'genderage'])
    age_app.prepare(ctx_id=0, det_size=(320, 320))
    print("  InsightFace loaded.\n")

    kept, flagged = [], []
    flag_counts = {"closed_eye": 0, "sunglasses": 0, "baby": 0, "no_face": 0, "no_age": 0}
    details_rows = []

    for i, p in enumerate(paths):
        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(paths)}] kept={len(kept)} flagged={len(flagged)}")
        details, flag = analyze(p, landmarker, age_app, args.ear_thresh, args.dark_thresh, args.age_thresh)
        if flag is None:
            kept.append(p)
        else:
            flagged.append((p, flag))
            for k in flag_counts:
                if k in flag:
                    flag_counts[k] += 1
            if details:
                details_rows.append({"path": p, "flag": flag, **details})

    print(f"\n=== Results ===")
    print(f"  Total   : {len(paths)}")
    print(f"  Kept    : {len(kept)}")
    print(f"  Flagged : {len(flagged)}")
    for k, v in flag_counts.items():
        print(f"    {k:12s}: {v}")

    # Save flagged CSV
    flagged_csv = os.path.join(out_dir, "face_attr_flagged.csv")
    with open(flagged_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "flag", "ear", "brightness", "age"])
        writer.writeheader()
        writer.writerows(details_rows)
    print(f"\n  Flagged CSV: {flagged_csv}")

    # Export sample of each flag type to review folder
    for flag_type in ["closed_eye", "sunglasses", "baby", "no_face"]:
        type_paths = [p for p, f in flagged if flag_type in f]
        if type_paths:
            rev_dir = os.path.join(out_dir, f"face_attr_review_{flag_type}")
            export_samples(type_paths, rev_dir, n=50)
            print(f"  Review sample ({flag_type}, {len(type_paths)} total): {rev_dir}")

    if args.dry_run:
        print("\n[dry_run] clean_paths.txt not updated.")
        return

    # Update clean_paths.txt
    with open(clean_txt, "w") as f:
        f.write("\n".join(kept))
    print(f"\n  Updated clean_paths.txt → {len(kept)} paths")


if __name__ == "__main__":
    main()
