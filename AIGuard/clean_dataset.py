"""
Dataset cleaning script — removes low-resolution and multi-face images.

Checks (in order):
  1. Resolution  : short side < MIN_SIDE → reject
  2. Multi-face  : OpenCV Haar cascade detects > MAX_FACES → reject
  3. FFHQ exclude: image ID found in exclusion lists (babies/eyes/sunglasses) → reject
     (only active when --ffhq_exclude flag is used)

Outputs (written to --out_dir, default = <input_dir>/clean_output/):
  clean_paths.txt  — one path per line, images that passed all checks
  rejected.csv     — rejected images with reason
  summary.txt      — counts per check

Usage (base conda env):
  python AIGuard/clean_dataset.py --dir AIGuard/real
  python AIGuard/clean_dataset.py --dir FFHQ_four_process --ffhq_exclude
  python AIGuard/clean_dataset.py --dir filter_data --min_side 100 --max_faces 1
"""

import os
import csv
import argparse
import re
import cv2
from pathlib import Path

BASE         = r"C:\My_Project\AIGC"
EXCLUDE_DIR  = os.path.join(BASE, "FFHQ_settings", "excluded_images_list")
EXCLUDE_FILES = [
    "00_34_baby.txt",
    "00_34_closingeye.txt",
    "child_35.txt",
    "eye_close.txt",
    "sunglasses.txt",
]
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def load_ffhq_exclusion_set():
    excluded = set()
    for fname in EXCLUDE_FILES:
        fpath = os.path.join(EXCLUDE_DIR, fname)
        if not os.path.exists(fpath):
            print(f"  [warn] exclusion file not found: {fpath}")
            continue
        with open(fpath, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    excluded.add(line)
    print(f"  Loaded {len(excluded)} FFHQ excluded IDs from {len(EXCLUDE_FILES)} files")
    return excluded


def get_ffhq_id(path):
    """Extract 5-digit zero-padded FFHQ ID from filename."""
    stem = Path(path).stem
    m = re.search(r"(\d{5})", stem)
    return m.group(1) if m else None


def scan_images(root):
    paths = []
    for dirpath, _, files in os.walk(root):
        for f in files:
            if Path(f).suffix.lower() in IMG_EXTS:
                paths.append(os.path.join(dirpath, f))
    return sorted(paths)


def check_resolution(img_path, min_side):
    img = cv2.imread(img_path)
    if img is None:
        return False, "unreadable"
    h, w = img.shape[:2]
    if min(h, w) < min_side:
        return False, f"low_res ({w}x{h})"
    return True, None


def check_face_count(img_path, detector, max_faces):
    img = cv2.imread(img_path)
    if img is None:
        return True, None
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    n = 0 if faces is None else len(faces)
    if n > max_faces:
        return False, f"multi_face ({n} faces)"
    return True, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",          required=True,  help="Directory to scan (relative to BASE or absolute)")
    parser.add_argument("--out_dir",      default=None,   help="Output directory (default: <dir>/clean_output)")
    parser.add_argument("--min_side",     type=int, default=128, help="Min short-side px (default 128)")
    parser.add_argument("--max_faces",    type=int, default=1,   help="Max allowed faces (default 1)")
    parser.add_argument("--ffhq_exclude", action="store_true",   help="Apply FFHQ exclusion lists")
    parser.add_argument("--skip_face",    action="store_true",   help="Skip face detection (faster)")
    args = parser.parse_args()

    scan_dir = args.dir if os.path.isabs(args.dir) else os.path.join(BASE, args.dir)
    out_dir  = args.out_dir or os.path.join(scan_dir, "clean_output")
    os.makedirs(out_dir, exist_ok=True)

    print(f"\n=== Dataset Cleaning ===")
    print(f"  Input : {scan_dir}")
    print(f"  Output: {out_dir}")
    print(f"  min_side={args.min_side}  max_faces={args.max_faces}  ffhq_exclude={args.ffhq_exclude}\n")

    # Load resources
    excluded_ids = load_ffhq_exclusion_set() if args.ffhq_exclude else set()

    cascade = None
    if not args.skip_face:
        yunet_path = os.path.join(BASE, "face_detection_yunet.onnx")
        if os.path.exists(yunet_path):
            cascade = cv2.FaceDetectorYN.create(yunet_path, "", (320, 320), score_threshold=0.6)
            print(f"  Face detector: YuNet ({yunet_path})")
        else:
            print("  [warn] YuNet model not found, skipping face detection.")
            print("         Download face_detection_yunet.onnx to BASE dir to enable it.")

    # Scan
    all_paths = scan_images(scan_dir)
    print(f"  Found {len(all_paths)} images\n")

    kept = []
    rejected = []
    counts = {"low_res": 0, "multi_face": 0, "ffhq_exclude": 0, "unreadable": 0}

    for i, path in enumerate(all_paths):
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(all_paths)}] kept={len(kept)} rejected={len(rejected)}")

        # 1. FFHQ exclusion (fast, no I/O)
        if args.ffhq_exclude:
            fid = get_ffhq_id(path)
            if fid and fid in excluded_ids:
                rejected.append((path, "ffhq_exclude"))
                counts["ffhq_exclude"] += 1
                continue

        # 2. Resolution
        ok, reason = check_resolution(path, args.min_side)
        if not ok:
            key = "unreadable" if reason == "unreadable" else "low_res"
            rejected.append((path, reason))
            counts[key] += 1
            continue

        # 3. Face count
        if cascade is not None:
            ok, reason = check_face_count(path, cascade, args.max_faces)
            if not ok:
                rejected.append((path, reason))
                counts["multi_face"] += 1
                continue

        kept.append(path)

    # Write outputs
    clean_txt = os.path.join(out_dir, "clean_paths.txt")
    with open(clean_txt, "w") as f:
        f.write("\n".join(kept))

    rejected_csv = os.path.join(out_dir, "rejected.csv")
    with open(rejected_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "reason"])
        writer.writerows(rejected)

    summary_lines = [
        f"Total scanned : {len(all_paths)}",
        f"Kept          : {len(kept)}  ({len(kept)/len(all_paths)*100:.1f}%)",
        f"Rejected      : {len(rejected)}",
        f"  low_res     : {counts['low_res']}",
        f"  multi_face  : {counts['multi_face']}",
        f"  ffhq_exclude: {counts['ffhq_exclude']}",
        f"  unreadable  : {counts['unreadable']}",
    ]
    summary_txt = os.path.join(out_dir, "summary.txt")
    with open(summary_txt, "w") as f:
        f.write("\n".join(summary_lines))

    print("\n=== Summary ===")
    print("\n".join(summary_lines))
    print(f"\nOutputs:")
    print(f"  {clean_txt}")
    print(f"  {rejected_csv}")
    print(f"  {summary_txt}")


if __name__ == "__main__":
    main()
