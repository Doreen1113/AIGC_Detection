"""
P1-R1.5 Resolution Causal Audit -- Stage 1: build resolution-controlled
manifests and generate the canonical_256 / canonical_512 / canonical_1024
composite images.

For each of the 200 unique clean base images in the existing, unmodified
`splits/v815_replication_set.tsv` (the same batch P1-R1 used), this script:
  1. Loads the CLEAN base image (never a filtered one -- filtering always
     starts fresh from clean to guarantee "same base image, same filter
     operation" traceability).
  2. Resizes it to each of 3 canonical square resolutions (256/512/1024),
     using cv2.INTER_AREA for downsizing and cv2.INTER_CUBIC for upsizing
     (the standard OpenCV convention for each direction).
  3. Re-detects face landmarks fresh at that resolution (MediaPipe cannot
     reuse landmarks from a different pixel grid).
  4. Re-applies each of the 4 filter functions used by the project's own
     stress-test/mining pipeline, IMPORTED UNMODIFIED from
     filters/stress_test_filter_functions.py (not reimplemented here) --
     smoothing_medium, whitening_medium, eye_enlarging, face_reshaping,
     same parameter defaults as v815_replication_set was built with.
  5. Saves the resulting composite as PNG (lossless; the model's own
     preprocess_jpeg(quality=85) is applied uniformly at inference time for
     ALL four resolution conditions, so JPEG policy does not vary by
     condition and is not baked into these stored files).
  6. Records full manifest fields: source image SHA256 (of the CLEAN base
     used), base resolution, resized resolution, face bbox, crop size (N/A
     -- this pipeline never crops, only resizes+filters, consistent with
     pipeline.py's own transform_infer), final model input shape (always
     224x224 after pipeline.py's transform_infer, recorded for clarity),
     filter type, filter parameters, JPEG quality policy, output SHA256.

The "native" resolution condition reuses the EXISTING v815_replication_set/
files completely unmodified (no regeneration) -- this maximizes fidelity to
P1-R1's original measurements for that leg of the comparison.

Does not modify filters/stress_test_filter_functions.py, splits/v815_replication_set.tsv,
or any existing image file. All new files are written under
results/research/p1_r1_5_resolution_causal_audit_20260814/.

python p1_r1_5_build_resolution_manifests.py
"""
import hashlib
import sys
import warnings
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE / "filters"))
import stress_test_filter_functions as fltr  # noqa: E402 -- unmodified, reused as-is

OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"
IMG_DIR = OUT_DIR / "resolution_controlled_images"
IMG_DIR.mkdir(parents=True, exist_ok=True)

REPLICATION_TSV = BASE / "splits" / "v815_replication_set.tsv"

CANONICAL_SIZES = [256, 512, 1024]

# same filter parameter defaults used to build v815_replication_set (matches
# filters/stress_test_filter_functions.py's own FILTERS dict / defaults)
FILTER_SPECS = {
    "smoothing_medium": dict(fn=lambda x: fltr.apply_smoothing(x, "medium"),
                              params={"strength": "medium", "bilateral_d_sigmaColor_sigmaSpace": [15, 80, 80]}),
    "whitening_medium": dict(fn=lambda x: fltr.apply_whitening(x, "medium"),
                              params={"strength": "medium", "lab_L_shift_fraction": 0.15}),
    "eye_enlarging": dict(fn=fltr.apply_eye_enlarging,
                           params={"scale": 1.18, "radius_factor": 1.70}),
    "face_reshaping": dict(fn=fltr.apply_face_reshaping,
                            params={"shrink_ratio": 0.92, "radius_px_FIXED": 60.0}),
}

JPEG_POLICY = "N/A at storage time (PNG, lossless); pipeline.py's preprocess_jpeg(quality=85) applied uniformly at inference time for ALL resolution conditions, see p1_r1_5_score_resolution_conditions.py"


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_of_array(arr_bgr):
    ok, buf = cv2.imencode(".png", arr_bgr)
    h = hashlib.sha256(buf.tobytes())
    return h.hexdigest()


def face_bbox_from_landmarks(lm):
    x0, y0 = float(lm[:, 0].min()), float(lm[:, 1].min())
    x1, y1 = float(lm[:, 0].max()), float(lm[:, 1].max())
    return x0, y0, x1 - x0, y1 - y0


def main():
    rows = []
    for line in REPLICATION_TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("id\t") or not line.strip():
            continue
        parts = line.split("\t")
        rows.append(dict(id=parts[0], path=parts[1], fake_label=int(parts[2]),
                          filter_attr=int(parts[3]), ftype=parts[4],
                          source=parts[5], used_in_v815_training=parts[6],
                          source_stem=parts[7]))

    clean_rows = [r for r in rows if r["ftype"] == "none"]
    print(f"Clean base images: {len(clean_rows)}")

    manifest_rows = []
    n_ok, n_landmark_fail, n_err = 0, 0, 0

    for i, r in enumerate(clean_rows, 1):
        base_path = Path(r["path"])
        if not base_path.is_file():
            n_err += 1
            manifest_rows.append({
                "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                "resolution_condition": "ALL", "filter_type": "ALL",
                "status": "MISSING_BASE_FILE", "note": f"base file not found: {base_path}",
            })
            continue

        base_sha256 = sha256_of_file(base_path)
        clean_bgr_native = cv2.imread(str(base_path))
        if clean_bgr_native is None:
            n_err += 1
            continue
        native_h, native_w = clean_bgr_native.shape[:2]

        # --- record the "native" condition: reuse existing file, no regeneration ---
        manifest_rows.append({
            "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
            "resolution_condition": "native", "filter_type": "clean",
            "base_image_sha256": base_sha256, "base_resolution": f"{native_w}x{native_h}",
            "resized_resolution": f"{native_w}x{native_h}", "resize_method": "N/A (reused existing file, not regenerated)",
            "face_bbox": "", "final_model_input_shape": "224x224 (pipeline.py transform_infer, applied uniformly at inference)",
            "filter_params": "{}", "jpeg_policy": JPEG_POLICY,
            "output_path": str(base_path), "output_sha256": base_sha256,
            "status": "OK_REUSED_EXISTING",
        })

        for size in CANONICAL_SIZES:
            interp = cv2.INTER_AREA if size < max(native_w, native_h) else cv2.INTER_CUBIC
            resized_clean = cv2.resize(clean_bgr_native, (size, size), interpolation=interp)

            lm = fltr._get_landmarks(resized_clean)
            if lm is None:
                n_landmark_fail += 1
                manifest_rows.append({
                    "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                    "resolution_condition": f"canonical_{size}", "filter_type": "ALL",
                    "base_image_sha256": base_sha256, "base_resolution": f"{native_w}x{native_h}",
                    "resized_resolution": f"{size}x{size}", "resize_method": interp,
                    "status": "LANDMARK_DETECTION_FAILED",
                    "note": "no face detected at this resolution -- excluded, not guessed",
                })
                continue

            bbox = face_bbox_from_landmarks(lm)

            # save the resized-but-unfiltered clean version too (for clean-fake
            # false-filter-rate measurement at each resolution)
            clean_out_name = f"{r['id']}_canonical{size}_clean.png"
            clean_out_path = IMG_DIR / clean_out_name
            cv2.imwrite(str(clean_out_path), resized_clean)
            manifest_rows.append({
                "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                "resolution_condition": f"canonical_{size}", "filter_type": "clean",
                "base_image_sha256": base_sha256, "base_resolution": f"{native_w}x{native_h}",
                "resized_resolution": f"{size}x{size}", "resize_method": str(interp),
                "face_bbox": f"{bbox[0]:.1f},{bbox[1]:.1f},{bbox[2]:.1f},{bbox[3]:.1f}",
                "final_model_input_shape": "224x224 (pipeline.py transform_infer, applied uniformly at inference)",
                "filter_params": "{}", "jpeg_policy": JPEG_POLICY,
                "output_path": str(clean_out_path), "output_sha256": sha256_of_array(resized_clean),
                "status": "OK_GENERATED",
            })

            for ftype, spec in FILTER_SPECS.items():
                try:
                    rgb_in = cv2.cvtColor(resized_clean, cv2.COLOR_BGR2RGB)
                    filtered_rgb = spec["fn"](rgb_in)
                except Exception as e:
                    n_err += 1
                    manifest_rows.append({
                        "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                        "resolution_condition": f"canonical_{size}", "filter_type": ftype,
                        "status": "FILTER_EXCEPTION", "note": str(e),
                    })
                    continue
                if filtered_rgb is None:
                    n_landmark_fail += 1
                    manifest_rows.append({
                        "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                        "resolution_condition": f"canonical_{size}", "filter_type": ftype,
                        "status": "FILTER_RETURNED_NONE", "note": "filter function's own landmark check failed",
                    })
                    continue
                filtered_bgr = cv2.cvtColor(filtered_rgb, cv2.COLOR_RGB2BGR)
                out_name = f"{r['id']}_canonical{size}_{ftype}.png"
                out_path = IMG_DIR / out_name
                cv2.imwrite(str(out_path), filtered_bgr)
                manifest_rows.append({
                    "base_id": r["id"], "source": r["source"], "source_stem": r["source_stem"],
                    "resolution_condition": f"canonical_{size}", "filter_type": ftype,
                    "base_image_sha256": base_sha256, "base_resolution": f"{native_w}x{native_h}",
                    "resized_resolution": f"{size}x{size}", "resize_method": str(interp),
                    "face_bbox": f"{bbox[0]:.1f},{bbox[1]:.1f},{bbox[2]:.1f},{bbox[3]:.1f}",
                    "final_model_input_shape": "224x224 (pipeline.py transform_infer, applied uniformly at inference)",
                    "filter_params": str(spec["params"]), "jpeg_policy": JPEG_POLICY,
                    "output_path": str(out_path), "output_sha256": sha256_of_array(filtered_bgr),
                    "status": "OK_GENERATED",
                })
                n_ok += 1

        if i % 40 == 0:
            print(f"  {i}/{len(clean_rows)} base images processed (ok={n_ok}, landmark_fail={n_landmark_fail}, err={n_err}) ...")

    print(f"\nDone. ok={n_ok}  landmark_fail={n_landmark_fail}  err={n_err}")
    df = pd.DataFrame(manifest_rows)
    out_path = OUT_DIR / "resolution_manifest.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} manifest rows -> {out_path}")


if __name__ == "__main__":
    main()
