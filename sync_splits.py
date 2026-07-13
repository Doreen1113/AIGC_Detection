"""
Run AFTER manually deleting images from review_all/<dataset>/<class>/.

What it does:
  1. Reads each sub-folder's _manifest.json
  2. Detects which images were deleted
  3. Updates source clean_paths.txt / labels.csv accordingly
  4. Per-source 8:1 train/val split
  5. Outputs:
       splits/train_real_fake.txt   (path  label  source)
       splits/val_real_fake.txt
     label: 0=real, 1=fake
     Filter splits are also written:
       splits/train_filter.txt
       splits/val_filter.txt

Usage:
  python sync_splits.py [--dry-run]
"""

import os
import csv
import json
import random
import argparse
from pathlib import Path
from collections import defaultdict

BASE     = Path(r"C:\My_Project\AIGC")
REVIEW   = BASE / "review_all"
SPLITS   = BASE / "splits"
SEED     = 42


# ── helpers ──────────────────────────────────────────────────────────────────

def _norm(p):
    return os.path.abspath(str(p))


def load_remaining(folder):
    """Returns set of absolute paths that still exist in folder."""
    folder = Path(folder)
    m_path = folder / "_manifest.json"
    if not m_path.exists():
        return set(), 0
    manifest = json.loads(m_path.read_text(encoding="utf-8"))
    total = len(manifest)
    kept = set()
    for fname, abspath in manifest.items():
        if (folder / fname).exists():
            kept.add(_norm(abspath))
    return kept, total


def update_clean_paths(txt_path, kept_abspaths, dry_run):
    txt_path = Path(txt_path)
    if not txt_path.exists():
        return 0, 0
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    before = len(lines)
    kept = [l for l in lines if _norm(l) in kept_abspaths]
    after = len(kept)
    if not dry_run:
        txt_path.write_text("\n".join(kept), encoding="utf-8")
    return before, after


def update_labels_csv(csv_path, kept_abspaths, dry_run):
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return 0, 0
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    before = len(rows)
    kept_rows = [r for r in rows if _norm(r["path"]) in kept_abspaths]
    after = len(kept_rows)
    if not dry_run:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["path", "label", "cate"])
            w.writeheader()
            w.writerows(kept_rows)
    return before, after


def per_source_split(entries, ratio=8):
    """entries: list of (path, label, source). Per-source shuffle + split."""
    by_source = defaultdict(list)
    for e in entries:
        by_source[e[2]].append(e)

    train, val = [], []
    rng = random.Random(SEED)
    for source, items in sorted(by_source.items()):
        rng.shuffle(items)
        cut = max(1, len(items) * ratio // (ratio + 1))
        train.extend(items[:cut])
        val.extend(items[cut:])
        print(f"  {source:45s}  n={len(items):6d}  train={cut:6d}  val={len(items)-cut:5d}")

    return train, val


def write_split_file(path, entries):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("path\tlabel\tsource\n")
        for p, lbl, src in entries:
            f.write(f"{p}\t{lbl}\t{src}\n")
    print(f"  → {path}  ({len(entries)} rows)")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    dry = args.dry_run
    if dry:
        print("=== DRY RUN — no files will be modified ===\n")

    real_fake_entries = []   # (path, label 0/1, source_name)
    filter_entries    = []   # (path, 2, source_name)

    # ── AIGuard ──────────────────────────────────────────────────────────────
    print("=== AIGuard ===")
    ag_real_kept, ag_real_total = load_remaining(REVIEW / "AIGuard/real")
    ag_fake_kept, ag_fake_total = load_remaining(REVIEW / "AIGuard/fake")
    print(f"  real: {ag_real_total} → {len(ag_real_kept)}  deleted={ag_real_total - len(ag_real_kept)}")
    print(f"  fake: {ag_fake_total} → {len(ag_fake_kept)}  deleted={ag_fake_total - len(ag_fake_kept)}")

    b, a = update_clean_paths(BASE / "AIGuard/real/clean_output/clean_paths.txt", ag_real_kept, dry)
    if not dry: print(f"  Updated AIGuard/real clean_paths.txt: {b}→{a}")
    b, a = update_clean_paths(BASE / "AIGuard/fake/clean_output/clean_paths.txt", ag_fake_kept, dry)
    if not dry: print(f"  Updated AIGuard/fake clean_paths.txt: {b}→{a}")

    for p in ag_real_kept:
        real_fake_entries.append((p, 0, "AIGuard-real"))
    for p in ag_fake_kept:
        real_fake_entries.append((p, 1, "AIGuard-fake"))

    # FakeClue excluded from v4 training:
    # - deepfake-cate (FF++) overlaps with AIGuard fake
    # - human-cate (GenImage) image quality inconsistent (full-body shots, small faces)
    # - FakeClue's value is artifact-level annotations for explainability distillation (Phase 2)
    print("\n=== FakeClue train: SKIPPED (reserved for explainability distillation) ===")

    # ── WildDeepfake ─────────────────────────────────────────────────────────
    print("\n=== WildDeepfake ===")
    wd_real_kept, wd_real_total = load_remaining(REVIEW / "WildDeepfake/real")
    wd_fake_kept, wd_fake_total = load_remaining(REVIEW / "WildDeepfake/fake")
    print(f"  real: {wd_real_total} → {len(wd_real_kept)}  deleted={wd_real_total - len(wd_real_kept)}")
    print(f"  fake: {wd_fake_total} → {len(wd_fake_kept)}  deleted={wd_fake_total - len(wd_fake_kept)}")

    all_wd_kept = wd_real_kept | wd_fake_kept
    b, a = update_clean_paths(
        BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt", all_wd_kept, dry
    )
    if not dry: print(f"  Updated WildDeepfake clean_paths.txt: {b}→{a}")

    for p in wd_real_kept:
        real_fake_entries.append((p, 0, "WildDeepfake-real"))
    for p in wd_fake_kept:
        real_fake_entries.append((p, 1, "WildDeepfake-fake"))

    # ── Filter datasets ──────────────────────────────────────────────────────
    print("\n=== Filter ===")
    filter_sources = [
        ("filter_data",   BASE / "filter_data/clean_output/clean_paths.txt"),
        ("FFHQ_four",     BASE / "FFHQ_four_process/clean_output/clean_paths.txt"),
        ("FFHQ_megvii",   BASE / "FFHQ_megvii_four_process/clean_output/clean_paths.txt"),
        ("FFHQ_ali",      BASE / "FFHQ_ali_process/clean_output/clean_paths.txt"),
    ]
    for src_name, txt_path in filter_sources:
        kept, total = load_remaining(REVIEW / src_name / "filter")
        print(f"  {src_name:20s}: {total} → {len(kept)}  deleted={total-len(kept)}")
        b, a = update_clean_paths(txt_path, kept, dry)
        if not dry: print(f"    Updated clean_paths.txt: {b}→{a}")
        for p in kept:
            filter_entries.append((p, 2, src_name))

    # ── Generate splits ──────────────────────────────────────────────────────
    print("\n=== Train/Val split (8:1 per source) ===")
    print("--- Real/Fake ---")
    rf_train, rf_val = per_source_split(real_fake_entries)
    print("\n--- Filter ---")
    ft_train, ft_val = per_source_split(filter_entries)

    print(f"\nReal+Fake: train={len(rf_train)}  val={len(rf_val)}")
    print(f"Filter:    train={len(ft_train)}  val={len(ft_val)}")

    if not dry:
        write_split_file(SPLITS / "train_real_fake.txt", rf_train)
        write_split_file(SPLITS / "val_real_fake.txt",   rf_val)
        write_split_file(SPLITS / "train_filter.txt",    ft_train)
        write_split_file(SPLITS / "val_filter.txt",      ft_val)
        print(f"\nSplit files written to: {SPLITS}/")


if __name__ == "__main__":
    main()
