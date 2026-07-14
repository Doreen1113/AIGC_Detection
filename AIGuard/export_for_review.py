"""
Export rejected / kept images to flat folders for manual inspection.
Uses hard links — no extra disk space.

Usage:
  python AIGuard/export_for_review.py --dir AIGuard/fake            # rejected only
  python AIGuard/export_for_review.py --dir AIGuard/fake --kept     # kept only
  python AIGuard/export_for_review.py --dir AIGuard/fake --all      # both
"""

import os
import csv
import json
import argparse
from pathlib import Path

BASE = r"C:\My_Project\AIGC"


def link_images(src_list, dest_dir, label_fn=None):
    os.makedirs(dest_dir, exist_ok=True)
    manifest = {}  # hard-link filename → original absolute path
    ok, skip, fail = 0, 0, 0
    for i, src in enumerate(src_list):
        if not os.path.exists(src):
            fail += 1
            continue
        stem = Path(src).stem
        suffix = Path(src).suffix
        prefix = label_fn(i) if label_fn else ""
        fname = f"{prefix}{i:06d}_{stem}{suffix}"
        dest = os.path.join(dest_dir, fname)
        manifest[fname] = os.path.abspath(src)
        if os.path.exists(dest):
            skip += 1
            continue
        try:
            os.link(src, dest)
            ok += 1
        except Exception:
            import shutil
            shutil.copy2(src, dest)
            ok += 1
        if (ok + skip + fail) % 500 == 0:
            print(f"  {ok+skip+fail} done...")
    # save manifest so sync_clean_paths.py can map filenames back to originals
    manifest_path = os.path.join(dest_dir, "_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    return ok, skip, fail


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    parser.add_argument("--kept",   action="store_true", help="Export kept images")
    parser.add_argument("--all",    action="store_true", help="Export both rejected and kept")
    args = parser.parse_args()

    do_rejected = not args.kept or args.all
    do_kept     = args.kept or args.all

    scan_dir = args.dir if os.path.isabs(args.dir) else os.path.join(BASE, args.dir)
    out_dir  = os.path.join(scan_dir, "clean_output")

    if do_rejected:
        rejected_csv = os.path.join(out_dir, "rejected.csv")
        if not os.path.exists(rejected_csv):
            print("rejected.csv not found — run clean_dataset.py first")
        else:
            rows = []
            with open(rejected_csv, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    rows.append(row)

            # Group by reason prefix
            by_reason = {}
            for row in rows:
                r = row["reason"].split(" ")[0]
                by_reason.setdefault(r, []).append(row["path"])

            for reason, paths in sorted(by_reason.items()):
                dest = os.path.join(out_dir, f"review_rejected_{reason}")
                print(f"\nExporting {len(paths)} rejected ({reason}) → {dest}")
                ok, skip, fail = link_images(paths, dest)
                print(f"  linked={ok}  skipped={skip}  failed={fail}")
                print(f"  Open in Explorer: {dest}")

    if do_kept:
        clean_txt = os.path.join(out_dir, "clean_paths.txt")
        if not os.path.exists(clean_txt):
            print("clean_paths.txt not found")
        else:
            paths = open(clean_txt).read().splitlines()
            dest = os.path.join(out_dir, "review_kept")
            print(f"\nExporting {len(paths)} kept → {dest}")
            ok, skip, fail = link_images(paths, dest)
            print(f"  linked={ok}  skipped={skip}  failed={fail}")
            print(f"  Open in Explorer: {dest}")

    print("\nDone. Open the folders above in Windows Explorer → View → Extra large icons")


if __name__ == "__main__":
    main()
