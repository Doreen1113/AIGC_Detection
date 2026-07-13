"""
After manually deleting images from review_kept/, run this to update clean_paths.txt.

Usage:
  python AIGuard/sync_clean_paths.py --dir AIGuard/real
  python AIGuard/sync_clean_paths.py --dir AIGuard/real --dry_run   # preview only
"""

import os
import json
import argparse
from pathlib import Path

BASE = r"C:\My_Project\AIGC"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--dry_run", action="store_true", help="Print changes without writing")
    args = parser.parse_args()

    scan_dir = args.dir if os.path.isabs(args.dir) else os.path.join(BASE, args.dir)
    out_dir  = os.path.join(scan_dir, "clean_output")
    review_dir = os.path.join(out_dir, "review_kept")
    manifest_path = os.path.join(review_dir, "_manifest.json")
    clean_txt = os.path.join(out_dir, "clean_paths.txt")

    if not os.path.exists(manifest_path):
        print("_manifest.json not found in review_kept/")
        print("Re-run: python AIGuard/export_for_review.py --dir <dir> --kept")
        return

    if not os.path.exists(clean_txt):
        print("clean_paths.txt not found")
        return

    manifest = json.load(open(manifest_path, encoding="utf-8"))
    # Normalize paths to avoid mixed-slash mismatch (os.path.abspath in manifest vs raw in txt)
    original_paths = {os.path.normpath(p) for p in open(clean_txt).read().splitlines() if p}

    # Find which originals are still in review_kept (not deleted)
    remaining_originals = set()
    for fname, orig in manifest.items():
        link_path = os.path.join(review_dir, fname)
        if os.path.exists(link_path):
            remaining_originals.add(os.path.normpath(orig))

    removed = original_paths - remaining_originals
    kept    = original_paths & remaining_originals

    print(f"\nOriginal clean_paths.txt : {len(original_paths)}")
    print(f"Still in review_kept     : {len(kept)}")
    print(f"Manually removed         : {len(removed)}")

    if removed:
        print("\nRemoved paths:")
        for p in sorted(removed):
            print(f"  - {p}")

    if args.dry_run:
        print("\n[dry_run] No changes written.")
        return

    # Write updated clean_paths.txt (preserve original order)
    new_paths = [p for p in open(clean_txt).read().splitlines() if p and os.path.normpath(p) in kept]
    with open(clean_txt, "w") as f:
        f.write("\n".join(new_paths))

    print(f"\nUpdated clean_paths.txt → {len(new_paths)} paths")


if __name__ == "__main__":
    main()
