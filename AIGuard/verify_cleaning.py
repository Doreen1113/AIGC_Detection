"""
Quick verification of dataset cleaning results.

Usage:
  python AIGuard/verify_cleaning.py --dir AIGuard/fake
  python AIGuard/verify_cleaning.py --dir FFHQ_ali_process --n 10
"""

import os
import csv
import argparse
import random
import cv2
import numpy as np
from pathlib import Path

BASE = r"C:\My_Project\AIGC"


def load_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


def make_grid(images, labels, cell_w=200, cell_h=200, cols=5):
    rows = (len(images) + cols - 1) // cols
    canvas = np.zeros((rows * cell_h, cols * cell_w, 3), dtype=np.uint8)
    for i, (img, label) in enumerate(zip(images, labels)):
        r, c = divmod(i, cols)
        if img is None:
            cell = np.zeros((cell_h, cell_w, 3), dtype=np.uint8)
        else:
            cell = cv2.resize(img, (cell_w, cell_h))
        # draw label
        cv2.putText(cell, label[:28], (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 1)
        y1, x1 = r * cell_h, c * cell_w
        canvas[y1:y1+cell_h, x1:x1+cell_w] = cell
    return canvas


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--n", type=int, default=20, help="Samples per category")
    args = parser.parse_args()

    scan_dir = args.dir if os.path.isabs(args.dir) else os.path.join(BASE, args.dir)
    out_dir = os.path.join(scan_dir, "clean_output")

    # Print summary
    summary_path = os.path.join(out_dir, "summary.txt")
    if os.path.exists(summary_path):
        print("\n=== Summary ===")
        print(open(summary_path).read())

    # Load rejected
    rejected_path = os.path.join(out_dir, "rejected.csv")
    if not os.path.exists(rejected_path):
        print("rejected.csv not found")
        return
    rejected = load_csv(rejected_path)

    # Group by reason
    by_reason = {}
    for row in rejected:
        r = row["reason"].split(" ")[0]  # e.g. "multi_face" from "multi_face (2 faces)"
        by_reason.setdefault(r, []).append(row)

    print(f"\nRejected breakdown:")
    for reason, rows in sorted(by_reason.items()):
        print(f"  {reason}: {len(rows)}")

    # Load clean paths
    clean_path = os.path.join(out_dir, "clean_paths.txt")
    clean_paths = open(clean_path).read().splitlines()

    # Sample and visualise each rejection reason
    for reason, rows in sorted(by_reason.items()):
        sample = random.sample(rows, min(args.n, len(rows)))
        imgs, labels = [], []
        for row in sample:
            img = cv2.imread(row["path"])
            imgs.append(img)
            labels.append(f'{reason} | {Path(row["path"]).name}')
        grid = make_grid(imgs, labels)
        save_path = os.path.join(out_dir, f"verify_rejected_{reason}.jpg")
        cv2.imwrite(save_path, grid)
        print(f"  Saved: {save_path}")

    # Sample kept images
    kept_sample = random.sample(clean_paths, min(args.n, len(clean_paths)))
    imgs, labels = [], []
    for p in kept_sample:
        img = cv2.imread(p)
        imgs.append(img)
        labels.append(f'kept | {Path(p).name}')
    grid = make_grid(imgs, labels)
    save_path = os.path.join(out_dir, "verify_kept.jpg")
    cv2.imwrite(save_path, grid)
    print(f"  Saved: {save_path}")

    print("\nDone. Open the .jpg files in clean_output/ to visually inspect.")


if __name__ == "__main__":
    main()
