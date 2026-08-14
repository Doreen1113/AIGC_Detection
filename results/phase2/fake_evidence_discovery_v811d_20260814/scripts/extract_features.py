"""
Phase 2F -- Fake Evidence Discovery: per-image feature extraction.

Samples source-balanced real/fake images from read-only project data, applies
the SAME preprocessing pipeline.py uses for inference (JPEG q85 re-encode +
MediaPipe face gate), then computes hand-computable evidence-candidate
features (frequency / texture / landmark-geometry / boundary families).
Also runs the read-only v8.11 production classifier to get fake_probability
(for correlation only -- NOT used to compute any evidence feature).

Outputs: raw_features.csv (one row per image, all feature columns + confound
columns), run_manifest.json.

python extract_features.py
"""
import io
import json
import os
import random
import sys
import time
import warnings
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "phase2" / "fake_evidence_discovery_v811d_20260814"
sys.path.insert(0, str(BASE))

SEED = 20260814
random.seed(SEED)
np.random.seed(SEED)

N_REAL_PER_SOURCE = 70
N_FAKE_PER_SOURCE = 60

# ──────────────────────────────────────────────
# pipeline.py imports (read-only reference model + preprocessing)
# ──────────────────────────────────────────────
import torch
os.chdir(str(BASE))
import pipeline as pl

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"device={device}")

l1_model = pl.DualBranchModel(num_classes=2).to(device).eval()
l1_model.load_state_dict(torch.load(pl.LAYER1_WEIGHTS_PATH, map_location=device))
l2_model = pl.DualBranchModel(num_classes=2).to(device).eval()
l2_model.load_state_dict(torch.load(pl.LAYER2_WEIGHTS_PATH, map_location=device))
print("v8.11 layer1/layer2 loaded (read-only reference)")

# ──────────────────────────────────────────────
# MediaPipe FaceLandmarker (reuse generate_landmark_gt.py pattern)
# ──────────────────────────────────────────────
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

_landmarker = None
def get_landmarker():
    global _landmarker
    if _landmarker is None:
        with open(str(BASE / "face_landmarker.task"), "rb") as f:
            model_data = f.read()
        opts = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data),
            num_faces=1)
        _landmarker = mp_vision.FaceLandmarker.create_from_options(opts)
    return _landmarker

IMG_SIZE = 224

def get_landmarks_224(bgr224):
    rgb = cv2.cvtColor(bgr224, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    lm = np.array([[p.x * IMG_SIZE, p.y * IMG_SIZE] for p in res.face_landmarks[0]], np.float32)
    return lm

# ──────────────────────────────────────────────
# skimage
# ──────────────────────────────────────────────
from skimage.feature import local_binary_pattern, graycomatrix, graycoprops
import skimage
print("skimage version:", skimage.__version__)


# ──────────────────────────────────────────────
# Sampling
# ──────────────────────────────────────────────
def sample_real_sources():
    sources = {}

    # celeba_test
    celeba_dir = BASE / "celeba_test"
    all_celeba = sorted(os.listdir(celeba_dir))
    rng = random.Random(SEED + 1)
    rng.shuffle(all_celeba)
    sources["celeba_test"] = [celeba_dir / f for f in all_celeba[: N_REAL_PER_SOURCE * 3]]

    # lfw (nested person folders)
    lfw_dir = BASE / "lfw"
    people = [p for p in lfw_dir.iterdir() if p.is_dir()]
    rng2 = random.Random(SEED + 2)
    rng2.shuffle(people)
    lfw_paths = []
    for p in people:
        imgs = list(p.glob("*.jpg"))
        if imgs:
            lfw_paths.append(rng2.choice(imgs))
        if len(lfw_paths) >= N_REAL_PER_SOURCE * 3:
            break
    sources["lfw"] = lfw_paths

    # AIGuard unseen real (held-out slice, documented choice)
    clean_paths_file = BASE / "AIGuard" / "unseen" / "clean_output" / "clean_paths.txt"
    lines = clean_paths_file.read_text(encoding="utf-8").splitlines()
    real_lines = [l.strip() for l in lines if Path(l.strip()).name.startswith("Real_")]
    rng3 = random.Random(SEED + 3)
    rng3.shuffle(real_lines)
    sources["aiguard_unseen_real"] = [Path(l) for l in real_lines]

    return sources


def sample_fake_sources():
    sources = {}

    # aiguard_unseen fake
    clean_paths_file = BASE / "AIGuard" / "unseen" / "clean_output" / "clean_paths.txt"
    lines = clean_paths_file.read_text(encoding="utf-8").splitlines()
    fake_lines = [l.strip() for l in lines if Path(l.strip()).name.startswith("fake_")]
    rng = random.Random(SEED + 10)
    rng.shuffle(fake_lines)
    sources["aiguard_unseen"] = [Path(l) for l in fake_lines]

    # stylegan2_ood
    sg2_dir = BASE / "stylegan2_test" / "fake"
    all_sg2 = sorted(os.listdir(sg2_dir))
    rng2 = random.Random(SEED + 11)
    rng2.shuffle(all_sg2)
    sources["stylegan2_ood"] = [sg2_dir / f for f in all_sg2[: N_FAKE_PER_SOURCE * 3]]

    # df40 + midjourney from splits/truetest_fake.txt
    tt_lines = (BASE / "splits" / "truetest_fake.txt").read_text(encoding="utf-8").splitlines()
    method_map = {"sd2.1": "df40_sd21", "DiT": "df40_dit", "SiT": "df40_sit",
                  "ddim": "df40_ddim", "pixart": "df40_pixart", "MidJourney": "midjourney"}
    by_method = {v: [] for v in method_map.values()}
    for l in tt_lines:
        l = l.strip()
        if not l:
            continue
        parts = Path(l).parts
        idx = parts.index("AIGC")
        method = parts[idx + 1]
        label = method_map.get(method)
        if label:
            by_method[label].append(Path(l))
    for label, paths in by_method.items():
        sources[label] = paths  # all 45, already <= N_FAKE_PER_SOURCE

    return sources


# ──────────────────────────────────────────────
# Feature families
# ──────────────────────────────────────────────
def freq_features(gray):
    """gray: float32 [0,1] 224x224."""
    F = np.fft.fft2(gray)
    Fs = np.fft.fftshift(F)
    mag = np.abs(Fs)
    logmag = np.log(mag + 1e-8)
    power = mag ** 2

    h, w = gray.shape
    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    r_int = r.astype(int)
    max_r = r_int.max()

    radial_sum = np.bincount(r_int.ravel(), weights=power.ravel(), minlength=max_r + 1)
    radial_count = np.bincount(r_int.ravel(), minlength=max_r + 1)
    radial_profile = radial_sum / np.maximum(radial_count, 1)

    total_energy = power.sum()
    # bands as fraction of max radius (exclude DC bin r=0..1)
    def band_energy(f0, f1):
        r0, r1 = int(f0 * max_r), int(f1 * max_r)
        mask = (r_int >= r0) & (r_int < r1)
        return power[mask].sum()

    low_e = band_energy(0.02, 0.15)
    mid_e = band_energy(0.15, 0.5)
    high_e = band_energy(0.5, 1.0)

    # spectral entropy (Shannon, normalized power spectrum as distribution)
    p = power.ravel() / (total_energy + 1e-12)
    p = p[p > 0]
    spectral_entropy = float(-(p * np.log(p)).sum() / np.log(len(p)))  # normalized [0,1]

    # power-law (1/f) fit in log-log space, radii 2..max_r (skip DC)
    valid = np.arange(2, max_r)
    rp = radial_profile[valid]
    rp = np.maximum(rp, 1e-12)
    log_r = np.log(valid.astype(np.float64))
    log_p = np.log(rp)
    slope, intercept = np.polyfit(log_r, log_p, 1)
    fit = slope * log_r + intercept
    residual_std = float(np.std(log_p - fit))

    return {
        "freq_spectral_entropy": spectral_entropy,
        "freq_band_ratio_high_mid": float(high_e / (mid_e + 1e-8)),
        "freq_band_ratio_high_low": float(high_e / (low_e + 1e-8)),
        "freq_band_ratio_mid_low": float(mid_e / (low_e + 1e-8)),
        "freq_high_energy_frac": float(high_e / (total_energy + 1e-8)),
        "freq_radial_powerlaw_slope": float(slope),
        "freq_powerlaw_residual_std": residual_std,
        "freq_logmag_mean": float(logmag.mean()),
    }


def texture_features(gray_u8):
    """gray_u8: uint8 224x224."""
    gray_f = gray_u8.astype(np.float32)

    # local variance map (5x5 sliding window)
    mean = cv2.blur(gray_f, (5, 5))
    sq_mean = cv2.blur(gray_f ** 2, (5, 5))
    var_map = np.maximum(sq_mean - mean ** 2, 0)
    local_var_mean = float(var_map.mean())
    local_var_std = float(var_map.std())

    # LBP (uniform)
    lbp = local_binary_pattern(gray_u8, P=8, R=1, method="uniform")
    n_bins = 10  # P+2 for uniform P=8
    hist, _ = np.histogram(lbp, bins=n_bins, range=(0, n_bins), density=True)
    hist = hist[hist > 0]
    lbp_entropy = float(-(hist * np.log(hist)).sum())
    lbp_uniformity = float((hist ** 2).sum())

    # GLCM (downsize + quantize to 32 levels for speed)
    small = cv2.resize(gray_u8, (96, 96))
    quant = (small.astype(np.float32) / 256.0 * 32).astype(np.uint8)
    glcm = graycomatrix(quant, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4],
                         levels=32, symmetric=True, normed=True)
    glcm_contrast = float(graycoprops(glcm, "contrast").mean())
    glcm_homogeneity = float(graycoprops(glcm, "homogeneity").mean())
    glcm_energy = float(graycoprops(glcm, "energy").mean())

    # high-pass residual (image - gaussian blur)
    blurred = cv2.GaussianBlur(gray_f, (0, 0), sigmaX=2.0)
    residual = gray_f - blurred
    highpass_energy = float(np.mean(np.abs(residual)))

    # 2D autocorrelation of residual -> peak sharpness (ratio of central peak
    # to mean of ring at radius 4-8px, high ratio = sharp/non-periodic peak,
    # low ratio = flatter/periodic patterning)
    resid_norm = residual - residual.mean()
    F = np.fft.fft2(resid_norm)
    autocorr = np.fft.fftshift(np.real(np.fft.ifft2(F * np.conj(F))))
    ch, cw = autocorr.shape[0] // 2, autocorr.shape[1] // 2
    center_val = autocorr[ch, cw]
    yy, xx = np.mgrid[0:autocorr.shape[0], 0:autocorr.shape[1]]
    rr = np.sqrt((yy - ch) ** 2 + (xx - cw) ** 2)
    ring_mask = (rr >= 4) & (rr < 8)
    ring_mean = autocorr[ring_mask].mean() if ring_mask.any() else 1e-8
    autocorr_peak_sharpness = float(center_val / (abs(ring_mean) + 1e-8))

    return {
        "tex_local_variance_mean": local_var_mean,
        "tex_local_variance_std": local_var_std,
        "tex_lbp_entropy": lbp_entropy,
        "tex_lbp_uniformity": lbp_uniformity,
        "tex_glcm_contrast": glcm_contrast,
        "tex_glcm_homogeneity": glcm_homogeneity,
        "tex_glcm_energy": glcm_energy,
        "tex_highpass_energy": highpass_energy,
        "tex_autocorr_peak_sharpness": autocorr_peak_sharpness,
    }


def landmark_geometry_features(lm):
    """lm: (468,2) landmarks in 224x224 space. MediaPipe FaceMesh indices."""
    # key indices (standard MediaPipe FaceMesh topology)
    LEFT_EYE_OUTER, LEFT_EYE_INNER = 33, 133
    RIGHT_EYE_INNER, RIGHT_EYE_OUTER = 362, 263
    MOUTH_LEFT, MOUTH_RIGHT = 61, 291
    NOSE_TIP = 1
    CHIN = 152
    FOREHEAD = 10

    x0, x1 = float(lm[:, 0].min()), float(lm[:, 0].max())
    y0, y1 = float(lm[:, 1].min()), float(lm[:, 1].max())
    face_w, face_h = x1 - x0, y1 - y0
    cx = (x0 + x1) / 2

    left_eye_c = (lm[LEFT_EYE_OUTER] + lm[LEFT_EYE_INNER]) / 2
    right_eye_c = (lm[RIGHT_EYE_INNER] + lm[RIGHT_EYE_OUTER]) / 2
    interocular = float(np.linalg.norm(left_eye_c - right_eye_c))
    mouth_width = float(np.linalg.norm(lm[MOUTH_LEFT] - lm[MOUTH_RIGHT]))

    # bilateral symmetry: for a set of paired L/R landmark indices, compare
    # each point's horizontal distance from the vertical midline (cx)
    PAIRS = [(LEFT_EYE_OUTER, RIGHT_EYE_OUTER), (LEFT_EYE_INNER, RIGHT_EYE_INNER),
              (61, 291), (105, 334), (50, 280), (36, 266)]
    diffs = []
    for li, ri in PAIRS:
        dl = abs(lm[li][0] - cx)
        dr = abs(lm[ri][0] - cx)
        diffs.append(abs(dl - dr))
    symmetry_score = float(np.mean(diffs) / (face_w + 1e-8))  # normalized

    pose_yaw_proxy = float((lm[NOSE_TIP][0] - cx) / (face_w / 2 + 1e-8))

    return {
        "lm_symmetry_score": symmetry_score,
        "lm_interocular_over_facewidth": float(interocular / (face_w + 1e-8)),
        "lm_mouthwidth_over_interocular": float(mouth_width / (interocular + 1e-8)),
        "lm_pose_yaw_proxy": pose_yaw_proxy,
        "face_bbox_x0": x0, "face_bbox_x1": x1, "face_bbox_y0": y0, "face_bbox_y1": y1,
    }


def boundary_features(gray_f, lm):
    """Ring just outside vs just inside the face landmark bbox oval."""
    x0, x1 = float(lm[:, 0].min()), float(lm[:, 0].max())
    y0, y1 = float(lm[:, 1].min()), float(lm[:, 1].max())
    h, w = gray_f.shape
    margin_px = min(x0, y0, w - x1, h - y1)

    if margin_px < 10:
        return None, margin_px  # NOT_AVAILABLE: too tight a crop

    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    a, b = (x1 - x0) / 2, (y1 - y0) / 2  # ellipse semi-axes = bbox
    yy, xx = np.mgrid[0:h, 0:w]
    ellipse_dist = ((xx - cx) / (a + 1e-8)) ** 2 + ((yy - cy) / (b + 1e-8)) ** 2

    inner_ring = (ellipse_dist >= 0.85 ** 2) & (ellipse_dist < 1.0)
    outer_ring = (ellipse_dist >= 1.0) & (ellipse_dist < 1.25 ** 2)
    if inner_ring.sum() < 20 or outer_ring.sum() < 20:
        return None, margin_px

    inner_vals = gray_f[inner_ring]
    outer_vals = gray_f[outer_ring]

    # edge contrast: mean abs gradient magnitude across the boundary band
    gx = cv2.Sobel(gray_f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray_f, cv2.CV_32F, 0, 1, ksize=3)
    grad_mag = np.sqrt(gx ** 2 + gy ** 2)
    boundary_band = inner_ring | outer_ring
    boundary_edge_contrast = float(grad_mag[boundary_band].mean())

    ring_texture_diff = float(abs(inner_vals.std() - outer_vals.std()))
    ring_mean_diff = float(abs(inner_vals.mean() - outer_vals.mean()))

    return {
        "bnd_boundary_edge_contrast": boundary_edge_contrast,
        "bnd_ring_texture_diff": ring_texture_diff,
        "bnd_ring_mean_diff": ring_mean_diff,
    }, margin_px


def get_fake_probability(pil_img_224):
    tensor = pl.transform_infer(pil_img_224).unsqueeze(0).to(device)
    res = pl.hierarchical_predict(tensor, l1_model, l2_model)
    return res["class_probs"]["fake"]


def process_image(path, cls_label, source_label):
    try:
        pil = Image.open(path).convert("RGB")
    except Exception as e:
        return None
    orig_w, orig_h = pil.size

    pil_jpeg = pl.preprocess_jpeg(pil, quality=85)
    if not pl.has_face(pil_jpeg):
        return None

    pil_224 = pil_jpeg.resize((IMG_SIZE, IMG_SIZE))
    bgr224 = cv2.cvtColor(np.array(pil_224), cv2.COLOR_RGB2BGR)
    gray_u8 = cv2.cvtColor(bgr224, cv2.COLOR_BGR2GRAY)
    gray_f01 = gray_u8.astype(np.float32) / 255.0

    row = {"image_path": str(path), "class": cls_label, "source": source_label,
           "orig_width": orig_w, "orig_height": orig_h,
           "orig_resolution": orig_w * orig_h}

    row.update(freq_features(gray_f01))
    row.update(texture_features(gray_u8))

    lm = get_landmarks_224(bgr224)
    if lm is not None:
        geo = landmark_geometry_features(lm)
        row.update(geo)
        face_area_frac = ((geo["face_bbox_x1"] - geo["face_bbox_x0"]) *
                           (geo["face_bbox_y1"] - geo["face_bbox_y0"])) / (IMG_SIZE * IMG_SIZE)
        row["face_size_confound"] = face_area_frac
        bf, margin_px = boundary_features(gray_u8.astype(np.float32), lm)
        row["boundary_margin_px"] = margin_px
        if bf is not None:
            row.update(bf)
        else:
            row["bnd_boundary_edge_contrast"] = np.nan
            row["bnd_ring_texture_diff"] = np.nan
            row["bnd_ring_mean_diff"] = np.nan
    else:
        row["lm_symmetry_score"] = np.nan
        row["lm_interocular_over_facewidth"] = np.nan
        row["lm_mouthwidth_over_interocular"] = np.nan
        row["lm_pose_yaw_proxy"] = np.nan
        row["face_size_confound"] = np.nan
        row["boundary_margin_px"] = np.nan
        row["bnd_boundary_edge_contrast"] = np.nan
        row["bnd_ring_texture_diff"] = np.nan
        row["bnd_ring_mean_diff"] = np.nan

    if cls_label == "fake":
        try:
            row["v811_fake_prob"] = get_fake_probability(pil_224)
        except Exception:
            row["v811_fake_prob"] = np.nan
    else:
        row["v811_fake_prob"] = np.nan

    return row


def main():
    t0 = time.time()
    real_sources = sample_real_sources()
    fake_sources = sample_fake_sources()

    manifest = {"seed": SEED, "n_real_requested": N_REAL_PER_SOURCE,
                "n_fake_requested": N_FAKE_PER_SOURCE,
                "skimage_version": skimage.__version__,
                "torch_version": torch.__version__,
                "device": str(device),
                "sources_requested": {},
                "sources_achieved": {}}

    rows = []
    for label, paths in real_sources.items():
        manifest["sources_requested"][label] = min(len(paths), N_REAL_PER_SOURCE)
        n_ok = 0
        print(f"[real:{label}] candidates={len(paths)}")
        for p in paths:
            if n_ok >= N_REAL_PER_SOURCE:
                break
            r = process_image(p, "real", label)
            if r is not None:
                rows.append(r)
                n_ok += 1
        manifest["sources_achieved"][f"real:{label}"] = n_ok
        print(f"  achieved {n_ok}/{N_REAL_PER_SOURCE}  elapsed={time.time()-t0:.0f}s")

    for label, paths in fake_sources.items():
        target = N_FAKE_PER_SOURCE
        manifest["sources_requested"][label] = min(len(paths), target)
        n_ok = 0
        print(f"[fake:{label}] candidates={len(paths)}")
        for p in paths:
            if n_ok >= target:
                break
            r = process_image(p, "fake", label)
            if r is not None:
                rows.append(r)
                n_ok += 1
        manifest["sources_achieved"][f"fake:{label}"] = n_ok
        print(f"  achieved {n_ok}/{target}  elapsed={time.time()-t0:.0f}s")

    df = pd.DataFrame(rows)
    out_csv = OUT_DIR / "raw_features.csv"
    df.to_csv(out_csv, index=False)
    manifest["total_images"] = len(df)
    manifest["elapsed_sec"] = time.time() - t0
    manifest["output_csv"] = str(out_csv)
    (OUT_DIR / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nDone. {len(df)} rows -> {out_csv}")
    print(json.dumps(manifest["sources_achieved"], indent=2))


if __name__ == "__main__":
    main()
