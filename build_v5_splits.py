"""
Build v5 training splits by adding:
  - LFW real images (excluding truetest_real.txt)
  - DF40 EFS diffusion fake images (excluding truetest_fake.txt)

Outputs:
  splits/v5_extra_real.txt    new LFW real paths to ADD to train
  splits/v5_extra_fake.txt    new DF40 diffusion fake paths to ADD to train
  splits/v5_train_real_fake.txt  full real+fake train (orig + new)
  splits/v5_val_real_fake.txt    val (orig unchanged)

Usage:
  python build_v5_splits.py
"""

import random, cv2
from pathlib import Path

BASE = Path(r"C:\My_Project\AIGC")

# Targets
TARGET_LFW_TRAIN  = 5000   # LFW real to add (from 13,233 - 250 test)
TARGET_DF40_PER_METHOD = 800  # per diffusion method (6 methods → ~4,800 total)

# DF40 directories (same as build_truetest_set.py)
FAKE_DIRS = {
    "sd2.1":      [BASE / "sd2.1/ff",      BASE / "sd2.1/cdf"],
    "DiT":        [BASE / "DiT/ff",        BASE / "DiT/cdf"],
    "SiT":        [BASE / "SiT/ff",        BASE / "SiT/cdf"],
    "ddim":       [BASE / "ddim/ff",       BASE / "ddim/cdf"],
    "pixart":     [BASE / "pixart/ff",     BASE / "pixart/cdf"],
    "MidJourney": [BASE / "MidJourney/fake"],
}

LFW_DIR  = BASE / "lfw"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_SIDE = 128
SEED     = 123   # different from build_truetest_set.py (42) to avoid same picks


def load_detector():
    yunet = BASE / "face_detection_yunet.onnx"
    det = cv2.FaceDetectorYN.create(str(yunet), "", (320, 320), score_threshold=0.6)
    print(f"  YuNet loaded")
    return det


def check_image(path, detector):
    img = cv2.imread(str(path))
    if img is None:
        return False
    h, w = img.shape[:2]
    if min(h, w) < MIN_SIDE:
        return False
    detector.setInputSize((w, h))
    _, faces = detector.detect(img)
    n = 0 if faces is None else len(faces)
    return n <= 1


def list_images(dirs):
    imgs = []
    for d in dirs:
        d = Path(d)
        if d.exists():
            for f in d.rglob("*"):
                if f.suffix.lower() in IMG_EXTS:
                    imgs.append(f)
    return imgs


def load_exclusion_set(txt_path):
    """Load paths to exclude (truetest splits)."""
    excluded = set()
    p = Path(txt_path)
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                excluded.add(str(Path(line).resolve()))
    print(f"  Loaded {len(excluded)} exclusions from {txt_path.name}")
    return excluded


def main():
    detector = load_detector()
    rng = random.Random(SEED)

    # Load exclusion sets (test images must not enter training)
    exclude_real = load_exclusion_set(BASE / "splits/truetest_real.txt")
    exclude_fake = load_exclusion_set(BASE / "splits/truetest_fake.txt")

    # ── LFW real ────────────────────────────────────────────────────────────
    print(f"\n=== LFW real (target: {TARGET_LFW_TRAIN}) ===")
    all_lfw = list_images([LFW_DIR])
    print(f"  Total LFW images: {len(all_lfw)}")

    # Exclude test images
    all_lfw = [p for p in all_lfw if str(p.resolve()) not in exclude_real]
    print(f"  After excluding test set: {len(all_lfw)}")

    rng.shuffle(all_lfw)
    lfw_kept = []
    for img in all_lfw:
        if check_image(img, detector):
            lfw_kept.append(img)
        if len(lfw_kept) >= TARGET_LFW_TRAIN:
            break
        if len(lfw_kept) % 500 == 0 and len(lfw_kept) > 0:
            print(f"  [{len(lfw_kept)}/{TARGET_LFW_TRAIN}]")

    print(f"  LFW real kept: {len(lfw_kept)}")

    # ── DF40 diffusion fake ──────────────────────────────────────────────────
    print(f"\n=== DF40 diffusion fake (target: {TARGET_DF40_PER_METHOD}/method) ===")
    df40_kept = []

    for method, dirs in FAKE_DIRS.items():
        all_imgs = list_images(dirs)
        # Exclude test images
        all_imgs = [p for p in all_imgs if str(p.resolve()) not in exclude_fake]
        rng.shuffle(all_imgs)

        method_kept = []
        for img in all_imgs:
            if check_image(img, detector):
                method_kept.append(img)
            if len(method_kept) >= TARGET_DF40_PER_METHOD:
                break

        print(f"  {method:12s}: {len(method_kept):4d} kept  (from {len(all_imgs):6d} available)")
        df40_kept.extend(method_kept)

    print(f"  DF40 total: {len(df40_kept)}")

    # ── Write extra split files ──────────────────────────────────────────────
    splits_dir = BASE / "splits"

    extra_real_path = splits_dir / "v5_extra_real.txt"
    extra_fake_path = splits_dir / "v5_extra_fake.txt"

    with open(extra_real_path, "w", encoding="utf-8") as f:
        for p in lfw_kept:
            f.write(str(p) + "\n")

    with open(extra_fake_path, "w", encoding="utf-8") as f:
        for p in df40_kept:
            f.write(str(p) + "\n")

    # ── Build v5 full train split (orig + new) ───────────────────────────────
    orig_train = splits_dir / "train_real_fake.txt"
    v5_train   = splits_dir / "v5_train_real_fake.txt"

    orig_lines = []
    header = "path\tlabel\tsource"
    if orig_train.exists():
        lines = orig_train.read_text(encoding="utf-8").splitlines()
        # Keep header separate
        orig_lines = [l for l in lines if not l.startswith("path\t")]
        print(f"\n  Original train_real_fake.txt: {len(orig_lines)} data lines")

    # format: path\tlabel\tsource  (same as original split)
    new_real_lines = [f"{p}\t0\tLFW-real" for p in lfw_kept]
    new_fake_lines = [f"{p}\t1\tDF40-diffusion" for p in df40_kept]

    all_lines = orig_lines + new_real_lines + new_fake_lines
    rng.shuffle(all_lines)

    with open(v5_train, "w", encoding="utf-8") as f:
        f.write(header + "\n")
        f.write("\n".join(all_lines) + "\n")

    # Val stays the same
    import shutil
    v5_val = splits_dir / "v5_val_real_fake.txt"
    shutil.copy(splits_dir / "val_real_fake.txt", v5_val)

    print(f"\n=== Done ===")
    print(f"  v5_extra_real.txt  : {len(lfw_kept)} images  → {extra_real_path}")
    print(f"  v5_extra_fake.txt  : {len(df40_kept)} images → {extra_fake_path}")
    print(f"  v5_train_real_fake : {len(all_lines)} lines  → {v5_train}")
    print(f"  v5_val_real_fake   : (copied from original) → {v5_val}")


if __name__ == "__main__":
    main()
