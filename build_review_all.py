"""
Build per-dataset review folders for manual inspection before v4 training.

Structure:
  review_all/
    AIGuard/
      real/          <- 25,753 images
      fake/          <- 20,552 images
    FakeClue_train/
      real/          <- FakeClue human real
      fake/          <- FakeClue deepfake + human fake
    WildDeepfake/
      real/          <- WD real (train_ prefix only)
      fake/          <- WD fake (train_ prefix only)
    filter_data/
      filter/        <- self-built filter (4 types)
    FFHQ_four/
      filter/
    FFHQ_megvii/
      filter/
    FFHQ_ali/
      filter/

All via hard links — no extra disk space.
Filename prefix: {i:07d}_{stem}{suffix}

After manual deletion in any sub-folder, run:
  python sync_splits.py
to update source clean_paths.txt and generate train/val splits.

Usage:
  python build_review_all.py [--dataset all|AIGuard|FakeClue|WildDeepfake|filter]
"""

import os
import json
import csv
import argparse
from pathlib import Path

BASE     = Path(r"C:\My_Project\AIGC")
OUT_DIR  = BASE / "review_all"


def hardlink_batch(entries, dest_dir, tag):
    """
    entries: list of absolute path strings
    dest_dir: Path
    tag: short string used in progress prints
    """
    dest_dir = Path(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    manifest_path = dest_dir / "_manifest.json"

    manifest = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    existing = set(manifest.keys())
    ok = skip = fail = 0

    for i, src in enumerate(entries):
        src = str(src)
        stem = Path(src).stem
        suffix = Path(src).suffix
        fname = f"{i:07d}_{stem}{suffix}"

        if fname in existing:
            skip += 1
            continue

        dest = dest_dir / fname
        if dest.exists():
            skip += 1
        else:
            if not os.path.exists(src):
                fail += 1
                continue
            try:
                os.link(src, str(dest))
                ok += 1
            except Exception:
                import shutil
                shutil.copy2(src, str(dest))
                ok += 1

        manifest[fname] = os.path.abspath(src)

        total = ok + skip + fail
        if total % 2000 == 0 and total > 0:
            print(f"    [{tag}] {total}  linked={ok}  skipped={skip}")

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"    [{tag}] total={len(entries)}  linked={ok}  skipped={skip}  failed={fail}")
    return ok, skip, fail


def read_clean_paths(txt_path):
    p = Path(txt_path)
    if not p.exists():
        return []
    return p.read_text(encoding="utf-8").splitlines()


def build_aigc(args):
    print("\n=== AIGuard ===")
    real = read_clean_paths(BASE / "AIGuard/real/clean_output/clean_paths.txt")
    print(f"  real: {len(real)}")
    hardlink_batch(real, OUT_DIR / "AIGuard/real", "AG-real")

    fake = read_clean_paths(BASE / "AIGuard/fake/clean_output/clean_paths.txt")
    print(f"  fake: {len(fake)}")
    hardlink_batch(fake, OUT_DIR / "AIGuard/fake", "AG-fake")


def build_fakeclue(args):
    print("\n=== FakeClue train ===")
    fc_labels = BASE / "FakeClue/train_clean/labels.csv"
    if not fc_labels.exists():
        print("  labels.csv not found, skipping")
        return
    real_paths, fake_paths = [], []
    with open(fc_labels, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["label"] == "1":
                real_paths.append(row["path"])
            else:
                fake_paths.append(row["path"])
    print(f"  real: {len(real_paths)}  fake: {len(fake_paths)}")
    hardlink_batch(real_paths, OUT_DIR / "FakeClue_train/real", "FC-real")
    hardlink_batch(fake_paths, OUT_DIR / "FakeClue_train/fake", "FC-fake")


def build_wilddeepfake(args):
    print("\n=== WildDeepfake (train_ prefix only) ===")
    all_paths = read_clean_paths(BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt")
    real_paths, fake_paths = [], []
    for p in all_paths:
        name = Path(p).name
        if not name.startswith("train_"):
            continue
        if "/real/" in p.replace("\\", "/"):
            real_paths.append(p)
        elif "/fake/" in p.replace("\\", "/"):
            fake_paths.append(p)
    print(f"  real: {len(real_paths)}  fake: {len(fake_paths)}")
    hardlink_batch(real_paths, OUT_DIR / "WildDeepfake/real", "WD-real")
    hardlink_batch(fake_paths, OUT_DIR / "WildDeepfake/fake", "WD-fake")


def build_filter(args):
    print("\n=== Filter datasets ===")
    sources = [
        ("filter_data",      BASE / "filter_data/clean_output/clean_paths.txt"),
        ("FFHQ_four",        BASE / "FFHQ_four_process/clean_output/clean_paths.txt"),
        ("FFHQ_megvii",      BASE / "FFHQ_megvii_four_process/clean_output/clean_paths.txt"),
        ("FFHQ_ali",         BASE / "FFHQ_ali_process/clean_output/clean_paths.txt"),
    ]
    for name, txt in sources:
        paths = read_clean_paths(txt)
        print(f"  {name}: {len(paths)}")
        hardlink_batch(paths, OUT_DIR / name / "filter", f"{name}-filter")


BUILDERS = {
    "AIGuard":      build_aigc,
    "FakeClue":     build_fakeclue,
    "WildDeepfake": build_wilddeepfake,
    "filter":       build_filter,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", default="all",
        help="Which dataset(s) to build: all | AIGuard | FakeClue | WildDeepfake | filter"
    )
    args = parser.parse_args()

    targets = list(BUILDERS.keys()) if args.dataset == "all" else [args.dataset]
    for t in targets:
        if t in BUILDERS:
            BUILDERS[t](args)
        else:
            print(f"Unknown dataset: {t}")

    print(f"""
=== Done ===
Review folders at: {OUT_DIR}

Structure:
  AIGuard/real/ fake/
  FakeClue_train/real/ fake/
  WildDeepfake/real/ fake/
  filter_data/filter/
  FFHQ_four/filter/
  FFHQ_megvii/filter/
  FFHQ_ali/filter/

After deleting unwanted images, run:
  python sync_splits.py
""")


if __name__ == "__main__":
    main()
