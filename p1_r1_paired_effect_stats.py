"""
P1-R1 Cross-Source Failure Anatomy -- paired before/after (clean vs filtered)
effect statistics on the DF40-cdf replication set. Pure image analysis, no
model inference. New, read-only analysis script; does not modify any
existing file.

For each (source_dataset x filter_type) combination, pairs each filtered
image with its own clean counterpart (matched by source_stem, i.e. same
underlying base fake image) and computes: LAB mean/median delta-E,
changed-pixel proportion (delta-E > 2.3 JND), face-region coverage,
eye-region coverage, a frequency-domain (log-magnitude FFT) difference
summary, and image resolution / face-bbox size stats.

Face landmarks via MediaPipe FaceLandmarker (same model/pattern already used
project-wide, e.g. AIGuard/stress_test_v811_pipeline.py) -- detected once per
clean base image and reused for all its filtered variants, since the filters
only locally warp/tone-shift a small region and the base face position does
not move.

python p1_r1_paired_effect_stats.py
"""
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_cross_source_failure_anatomy_20260814"
OUT_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = str(BASE / "face_landmarker.task")
REPLICATION_TSV = BASE / "splits" / "v815_replication_set.tsv"

LEFT_EYE = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)
DELTA_E_JND = 2.3  # just-noticeable-difference threshold, standard CIE76 rule of thumb

_landmarker = None


def get_landmarker():
    global _landmarker
    if _landmarker is None:
        with open(MODEL_PATH, "rb") as f:
            model_data = f.read()
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data), num_faces=1)
        _landmarker = vision.FaceLandmarker.create_from_options(opts)
    return _landmarker


def detect_landmarks(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = bgr.shape[:2]
    return np.array([[lm.x * w, lm.y * h] for lm in res.face_landmarks[0]], np.float32)


def face_oval_mask(shape, lm):
    """Convex hull over all 468 landmarks as a face-region mask."""
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    hull = cv2.convexHull(lm.astype(np.int32))
    cv2.fillConvexPoly(mask, hull, 1)
    return mask.astype(bool)


def eye_region_mask(shape, lm, radius_factor=1.9):
    h, w = shape[:2]
    mask = np.zeros((h, w), np.uint8)
    for eye_idx in (LEFT_EYE, RIGHT_EYE):
        pts = lm[list(eye_idx)]
        center = np.mean(pts, axis=0)
        eye_w = np.linalg.norm(lm[eye_idx[0]] - lm[eye_idx[1]])
        radius = max(eye_w * radius_factor, 8.0)
        cv2.circle(mask, (int(center[0]), int(center[1])), int(radius), 1, -1)
    return mask.astype(bool)


def fft_log_mag(gray):
    f = np.fft.fft2(gray.astype(np.float32))
    f = np.fft.fftshift(f)
    return np.log(np.abs(f) + 1e-8)


def main():
    rows = []
    for line in REPLICATION_TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("id\t") or not line.strip():
            continue
        parts = line.split("\t")
        rows.append(dict(id=parts[0], path=parts[1], ftype=parts[4],
                          source=parts[5], source_stem=parts[7]))

    clean_rows = {(r["source"], r["source_stem"]): r for r in rows if r["ftype"] == "none"}
    filtered_rows = [r for r in rows if r["ftype"] != "none"]
    print(f"Clean bases: {len(clean_rows)}  filtered rows to pair: {len(filtered_rows)}")

    # cache landmarks/masks per clean base (keyed by (source, stem))
    base_cache = {}

    out_rows = []
    n_ok, n_no_landmark, n_err = 0, 0, 0
    for i, r in enumerate(filtered_rows, 1):
        key = (r["source"], r["source_stem"])
        clean_r = clean_rows.get(key)
        if clean_r is None:
            n_err += 1
            continue
        try:
            clean_bgr = cv2.imread(clean_r["path"])
            filt_bgr = cv2.imread(r["path"])
            if clean_bgr is None or filt_bgr is None:
                n_err += 1
                continue
            if clean_bgr.shape != filt_bgr.shape:
                filt_bgr = cv2.resize(filt_bgr, (clean_bgr.shape[1], clean_bgr.shape[0]))

            if key not in base_cache:
                lm = detect_landmarks(clean_bgr)
                if lm is None:
                    base_cache[key] = None
                else:
                    face_mask = face_oval_mask(clean_bgr.shape, lm)
                    eye_mask = eye_region_mask(clean_bgr.shape, lm)
                    x0, y0 = lm[:, 0].min(), lm[:, 1].min()
                    x1, y1 = lm[:, 0].max(), lm[:, 1].max()
                    bbox_w, bbox_h = float(x1 - x0), float(y1 - y0)
                    base_cache[key] = dict(face_mask=face_mask, eye_mask=eye_mask,
                                            bbox_w=bbox_w, bbox_h=bbox_h)
            cached = base_cache[key]
            if cached is None:
                n_no_landmark += 1
                continue

            # LAB delta-E (CIE76: euclidean distance in Lab space)
            clean_lab = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
            filt_lab = cv2.cvtColor(filt_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
            delta_e = np.sqrt(np.sum((clean_lab - filt_lab) ** 2, axis=2))

            changed = delta_e > DELTA_E_JND
            changed_prop = float(changed.mean())

            face_mask = cached["face_mask"]
            eye_mask = cached["eye_mask"]
            face_changed_prop = float(changed[face_mask].mean()) if face_mask.any() else np.nan
            eye_changed_prop = float(changed[eye_mask].mean()) if eye_mask.any() else np.nan
            # "coverage" = what fraction of all changed pixels fall inside the region
            total_changed = changed.sum()
            face_coverage = float(changed[face_mask].sum() / total_changed) if total_changed > 0 else np.nan
            eye_coverage = float(changed[eye_mask].sum() / total_changed) if total_changed > 0 else np.nan

            clean_gray = cv2.cvtColor(clean_bgr, cv2.COLOR_BGR2GRAY)
            filt_gray = cv2.cvtColor(filt_bgr, cv2.COLOR_BGR2GRAY)
            fft_diff = fft_log_mag(filt_gray) - fft_log_mag(clean_gray)

            h, w = clean_bgr.shape[:2]
            out_rows.append({
                "id": r["id"], "source": r["source"], "ftype": r["ftype"],
                "source_stem": r["source_stem"],
                "lab_deltaE_mean": float(delta_e.mean()),
                "lab_deltaE_median": float(np.median(delta_e)),
                "changed_pixel_proportion": changed_prop,
                "face_region_changed_proportion": face_changed_prop,
                "eye_region_changed_proportion": eye_changed_prop,
                "face_region_coverage_of_changed_pixels": face_coverage,
                "eye_region_coverage_of_changed_pixels": eye_coverage,
                "fft_logmag_diff_mean": float(fft_diff.mean()),
                "fft_logmag_diff_std": float(fft_diff.std()),
                "fft_logmag_diff_absmean": float(np.abs(fft_diff).mean()),
                "image_width": w, "image_height": h,
                "face_bbox_w": cached["bbox_w"], "face_bbox_h": cached["bbox_h"],
                "face_bbox_area_frac": float((cached["bbox_w"] * cached["bbox_h"]) / (w * h)),
            })
            n_ok += 1
        except Exception as e:
            n_err += 1
            continue
        if i % 200 == 0:
            print(f"  {i}/{len(filtered_rows)} processed (ok={n_ok}, no_landmark={n_no_landmark}, err={n_err}) ...")

    print(f"\nDone. ok={n_ok}  no_landmark={n_no_landmark}  err={n_err}")
    df = pd.DataFrame(out_rows)
    out_path = OUT_DIR / "per_image_paired_effect_raw.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} paired rows -> {out_path}")


if __name__ == "__main__":
    main()
