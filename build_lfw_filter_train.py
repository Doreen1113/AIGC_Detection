"""
Generate LFW+filter training images for v5.1.
Takes 2,000 images from v5_extra_real.txt (LFW train), applies 4 filter types,
outputs to test_set_true/lfw_filter_train/ and appends to splits/v5_train_filter.txt.

Usage: python build_lfw_filter_train.py
"""
import sys, random, cv2, shutil
from pathlib import Path

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE / "filters"))

from generate_filter_dataset import (
    apply_smoothing, apply_whitening,
    apply_eye_enlarging, apply_face_reshaping,
)

FILTER_FNS = [
    ("smoothing",      apply_smoothing),
    ("whitening",      apply_whitening),
    ("eye_enlarging",  apply_eye_enlarging),
    ("face_reshaping", apply_face_reshaping),
]

N_SOURCE   = 2000   # LFW source images to use (500 per filter type)
SEED       = 77

# Load LFW train paths (from v5 splits, excluding test)
src_txt = BASE / "splits/v5_extra_real.txt"
all_lfw = [Path(l.strip()) for l in src_txt.read_text(encoding="utf-8").splitlines() if l.strip()]
print(f"LFW train pool: {len(all_lfw)} images")

rng = random.Random(SEED)
selected = rng.sample(all_lfw, min(N_SOURCE, len(all_lfw)))

# Split evenly across 4 filter types
per_filter = len(selected) // len(FILTER_FNS)
chunks = [selected[i*per_filter:(i+1)*per_filter] for i in range(len(FILTER_FNS))]

out_dir = BASE / "test_set_true/lfw_filter_train"
out_dir.mkdir(parents=True, exist_ok=True)

kept_paths = []
for (fname, fn), src_list in zip(FILTER_FNS, chunks):
    ok = 0
    for src in src_list:
        img = cv2.imread(str(src))
        if img is None:
            continue
        try:
            filtered = fn(img)
            if filtered is None:
                continue
            dst = out_dir / f"{fname}_{src.name}"
            cv2.imwrite(str(dst), filtered)
            kept_paths.append(dst)
            ok += 1
        except Exception as e:
            pass
    print(f"  {fname:15s}: {ok} images generated")

print(f"\nTotal LFW+filter train images: {len(kept_paths)}")

# Append to filter split as label=2 (filter class)
v5_filter_txt = BASE / "splits/v5_train_filter.txt"
# Start from original train_filter.txt
orig = BASE / "splits/train_filter.txt"
if not v5_filter_txt.exists():
    shutil.copy(orig, v5_filter_txt)
    print(f"Copied train_filter.txt → v5_train_filter.txt")

with open(v5_filter_txt, "a", encoding="utf-8") as f:
    for p in kept_paths:
        f.write(f"{p}\t2\tLFW-filter\n")

print(f"Appended {len(kept_paths)} lines to {v5_filter_txt}")
print("Done. Now run: python AIGuard/train_v5_1.py")
