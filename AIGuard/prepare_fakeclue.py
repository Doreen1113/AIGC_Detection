"""
FakeClue dataset preparation — filter face-relevant categories, run resolution
and multi-face checks, output clean_paths.txt + labels.csv.

Categories kept:
  deepfake → ff++/fake (FF++ deepfake) + ff++/real (FF++ real)
  human    → genimage/fake (AIGC-generated) + genimage/real (ImageNet real)

Usage:
    python AIGuard/prepare_fakeclue.py --split test
    python AIGuard/prepare_fakeclue.py --split train
"""

import os
import json
import csv
import argparse
import cv2
from pathlib import Path

BASE          = r"C:\My_Project\AIGC"
FAKECLUE_DIR  = os.path.join(BASE, "FakeClue")
META_DIR      = os.path.join(BASE, "FakeClue_meta", "data_json")
YUNET_PATH    = os.path.join(BASE, "face_detection_yunet.onnx")

FACE_CATES    = {"deepfake", "human"}
MIN_SIDE      = 128
MAX_FACES     = 1


def check_resolution(path):
    img = cv2.imread(path)
    if img is None:
        return False, "unreadable"
    h, w = img.shape[:2]
    if min(h, w) < MIN_SIDE:
        return False, f"low_res ({w}x{h})"
    return True, None


def check_face_count(path, detector):
    img = cv2.imread(path)
    if img is None:
        return True, None
    h, w = img.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    n = 0 if faces is None else len(faces)
    if n > MAX_FACES:
        return False, f"multi_face ({n})"
    return True, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["test", "train"], default="test")
    args = parser.parse_args()

    split_dir = os.path.join(FAKECLUE_DIR, args.split)
    out_dir   = os.path.join(FAKECLUE_DIR, f"{args.split}_clean")
    os.makedirs(out_dir, exist_ok=True)

    meta_path = os.path.join(META_DIR, f"{args.split}.json")
    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    print(f"\n=== FakeClue {args.split} preparation ===")
    print(f"  Total entries in JSON: {len(meta)}")

    # Filter face-relevant categories
    face_items = [m for m in meta if m["cate"] in FACE_CATES]
    print(f"  Face-relevant (deepfake+human): {len(face_items)}")
    for cate in FACE_CATES:
        n = sum(1 for m in face_items if m["cate"] == cate)
        n0 = sum(1 for m in face_items if m["cate"] == cate and m["label"] == 0)
        n1 = sum(1 for m in face_items if m["cate"] == cate and m["label"] == 1)
        print(f"    {cate}: {n}  (fake={n0}, real={n1})")

    # Check files exist
    face_items = [m for m in face_items
                  if os.path.exists(os.path.join(split_dir, m["image"]))]
    print(f"  Files found on disk: {len(face_items)}")

    # Load YuNet
    detector = None
    if os.path.exists(YUNET_PATH):
        detector = cv2.FaceDetectorYN.create(YUNET_PATH, "", (320, 320), score_threshold=0.6)
        print(f"  Face detector: YuNet")
    else:
        print("  [warn] YuNet not found, skipping face count check")

    # Clean
    kept, rejected = [], []
    counts = {"low_res": 0, "multi_face": 0, "unreadable": 0}

    for i, m in enumerate(face_items):
        if (i + 1) % 200 == 0:
            print(f"  [{i+1}/{len(face_items)}] kept={len(kept)} rejected={len(rejected)}")

        full_path = os.path.join(split_dir, m["image"])

        ok, reason = check_resolution(full_path)
        if not ok:
            key = "unreadable" if reason == "unreadable" else "low_res"
            rejected.append({"path": full_path, "reason": reason, **m})
            counts[key] += 1
            continue

        if detector is not None:
            ok, reason = check_face_count(full_path, detector)
            if not ok:
                rejected.append({"path": full_path, "reason": reason, **m})
                counts["multi_face"] += 1
                continue

        kept.append({"path": full_path, "label": m["label"], "cate": m["cate"]})

    print(f"\n=== Results ===")
    print(f"  Kept    : {len(kept)}")
    print(f"  Rejected: {len(rejected)}")
    for k, v in counts.items():
        if v: print(f"    {k}: {v}")

    # Label breakdown
    for lbl, name in [(0, "fake"), (1, "real")]:
        n = sum(1 for k in kept if k["label"] == lbl)
        print(f"  {name}: {n}")

    # Write clean_paths.txt (paths only, for clean_dataset compatibility)
    clean_txt = os.path.join(out_dir, "clean_paths.txt")
    with open(clean_txt, "w") as f:
        f.write("\n".join(k["path"] for k in kept))

    # Write labels.csv (path + label + cate)
    labels_csv = os.path.join(out_dir, "labels.csv")
    with open(labels_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "label", "cate"])
        writer.writeheader()
        writer.writerows(kept)

    print(f"\n  clean_paths.txt → {clean_txt}")
    print(f"  labels.csv      → {labels_csv}")


if __name__ == "__main__":
    main()
