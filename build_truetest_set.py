"""
Build true held-out test set from DF40 EFS diffusion fakes.

Phase 1 (can run now):
  DF40 fake → splits/truetest_fake.txt   (target ~270 images, 6 methods × 45)

Phase 2 (run after downloading LFW):
  LFW real  → splits/truetest_real.txt   (target 250 images)
  Set LFW_DIR below to your LFW folder, then rerun with --phase real

Phase 3 (run after phase 2):
  LFW real + filter pipeline → splits/truetest_filter.txt
  Run with --phase filter

Only Step 1 cleaning: resolution ≥ 128px + face count ≤ 1.

Usage:
  python build_truetest_set.py              # Phase 1 (fake)
  python build_truetest_set.py --phase real    # Phase 2 (real, LFW needed)
  python build_truetest_set.py --phase filter  # Phase 3 (filter from real)
"""

import argparse, random, cv2, shutil
from pathlib import Path

BASE = Path(r"C:\My_Project\AIGC")

# ── Phase 1 config ───────────────────────────────────────────────────────────
# DF40 EFS diffusion fake directories (ff = FaceForensics source, cdf = CelebDF source)
FAKE_DIRS = {
    "sd2.1":      [BASE / "sd2.1/ff",      BASE / "sd2.1/cdf"],
    "DiT":        [BASE / "DiT/ff",        BASE / "DiT/cdf"],
    "SiT":        [BASE / "SiT/ff",        BASE / "SiT/cdf"],
    "ddim":       [BASE / "ddim/ff",       BASE / "ddim/cdf"],
    "pixart":     [BASE / "pixart/ff",     BASE / "pixart/cdf"],
    "MidJourney": [BASE / "MidJourney/fake"],
}
TARGET_PER_METHOD = 45    # 6 × 45 = 270 total
CANDIDATE_SAMPLE  = 800   # random pre-select before cleaning (avoids scanning all ~150k)

# ── Phase 2 config ───────────────────────────────────────────────────────────
LFW_DIR      = BASE / "lfw"   # ← set this to your LFW root after download
TARGET_REAL  = 250

# ── Phase 3 config ───────────────────────────────────────────────────────────
TARGET_FILTER = 250

# ── Shared ───────────────────────────────────────────────────────────────────
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MIN_SIDE  = 128
SEED      = 42


def load_detector():
    yunet = BASE / "face_detection_yunet.onnx"
    if not yunet.exists():
        raise FileNotFoundError(f"YuNet not found: {yunet}")
    det = cv2.FaceDetectorYN.create(str(yunet), "", (320, 320), score_threshold=0.6)
    print(f"  YuNet loaded: {yunet}")
    return det


def check_image(path, detector):
    """Return True if image passes: readable, resolution ok, ≤1 face."""
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
        else:
            print(f"  [warn] directory not found: {d}")
    return imgs


# ── Phase 1: DF40 fake ───────────────────────────────────────────────────────

def build_fake(detector):
    print("\n=== Phase 1: DF40 EFS diffusion fake ===")
    out_path = BASE / "splits/truetest_fake.txt"
    out_path.parent.mkdir(exist_ok=True)

    rng = random.Random(SEED)
    kept = []

    for method, dirs in FAKE_DIRS.items():
        all_imgs = list_images(dirs)
        if not all_imgs:
            print(f"  {method:12s}: no images found, skip")
            continue

        candidates = rng.sample(all_imgs, min(CANDIDATE_SAMPLE, len(all_imgs)))
        method_kept = []
        for img in candidates:
            if check_image(img, detector):
                method_kept.append(img)
            if len(method_kept) >= TARGET_PER_METHOD:
                break

        print(f"  {method:12s}: {len(method_kept):3d} kept  "
              f"(scanned {min(len(candidates), len(method_kept) + (CANDIDATE_SAMPLE - len(method_kept))):3d} "
              f"of {len(all_imgs):6d} available)")
        kept.extend(method_kept)

    with open(out_path, "w", encoding="utf-8") as f:
        for p in kept:
            f.write(str(p) + "\n")

    print(f"\n  Total fake test images: {len(kept)}")
    print(f"  Saved to: {out_path}")


# ── Phase 2: LFW real ────────────────────────────────────────────────────────

def build_real(detector):
    print("\n=== Phase 2: LFW real ===")
    if not LFW_DIR.exists():
        print(f"  ERROR: LFW directory not found: {LFW_DIR}")
        print("  Download LFW first:")
        print("    http://vis-www.cs.umass.edu/lfw/lfw.tgz  (173 MB)")
        print("  Extract to: C:\\My_Project\\AIGC\\lfw\\")
        print("  Then rerun: python build_truetest_set.py --phase real")
        return

    out_path = BASE / "splits/truetest_real.txt"
    all_imgs = list_images([LFW_DIR])
    print(f"  Found {len(all_imgs)} LFW images")

    rng = random.Random(SEED)
    candidates = rng.sample(all_imgs, min(TARGET_REAL * 5, len(all_imgs)))

    kept = []
    for img in candidates:
        if check_image(img, detector):
            kept.append(img)
        if len(kept) >= TARGET_REAL:
            break

    with open(out_path, "w", encoding="utf-8") as f:
        for p in kept:
            f.write(str(p) + "\n")

    print(f"  Kept: {len(kept)} real images")
    print(f"  Saved to: {out_path}")


# ── Phase 3: LFW + filter ────────────────────────────────────────────────────

def build_filter():
    print("\n=== Phase 3: LFW real → filter ===")
    real_txt = BASE / "splits/truetest_real.txt"
    if not real_txt.exists():
        print("  ERROR: truetest_real.txt not found. Run Phase 2 first.")
        return

    real_paths = [Path(l.strip()) for l in real_txt.read_text().splitlines() if l.strip()]
    print(f"  Loaded {len(real_paths)} real images from Phase 2")

    import sys
    sys.path.insert(0, str(BASE / "filters"))
    try:
        from generate_filter_dataset import (
            apply_smoothing, apply_whitening,
            apply_eye_enlarging, apply_face_reshaping,
        )
    except ImportError as e:
        print(f"  ERROR importing filter functions: {e}")
        return

    filter_fns = [
        ("smoothing",      apply_smoothing),
        ("whitening",      apply_whitening),
        ("eye_enlarging",  apply_eye_enlarging),
        ("face_reshaping", apply_face_reshaping),
    ]

    out_dir = BASE / "test_set_true/filter"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = BASE / "splits/truetest_filter.txt"

    rng = random.Random(SEED)
    # Cycle through filter types to get balanced mix
    fn_cycle = (filter_fns * ((TARGET_FILTER // len(filter_fns)) + 1))[:TARGET_FILTER]
    rng.shuffle(fn_cycle)

    kept = []
    for src, (filter_name, fn) in zip(real_paths, fn_cycle):
        img = cv2.imread(str(src))
        if img is None:
            continue
        try:
            filtered = fn(img)
            if filtered is None:
                continue
            dst = out_dir / f"{filter_name}_{src.name}"
            cv2.imwrite(str(dst), filtered)
            kept.append(dst)
        except Exception as e:
            print(f"  [warn] {src.name}: {e}")

    with open(out_path, "w", encoding="utf-8") as f:
        for p in kept:
            f.write(str(p) + "\n")

    print(f"  Generated: {len(kept)} filter test images → {out_dir}")
    print(f"  Saved list to: {out_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="fake",
                        choices=["fake", "real", "filter", "all"],
                        help="Which phase to run (default: fake)")
    args = parser.parse_args()

    if args.phase in ("fake", "real", "all"):
        detector = load_detector()
        if args.phase in ("fake", "all"):
            build_fake(detector)
        if args.phase in ("real", "all"):
            build_real(detector)

    if args.phase in ("filter", "all"):
        build_filter()

    print("\nDone.")


if __name__ == "__main__":
    main()
