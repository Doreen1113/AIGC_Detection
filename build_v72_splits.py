"""
Build v7.2 filter training split:
  - Original filter_data/eye_enlarging × 4  (same as v7)
  - NEW lfw_eye_enlarging × 4               (domain-matched LFW data)
  - face_reshaping × 3
  - smoothing / whitening / FFHQ: unchanged

Total eye_enlarging ~48,900 vs v7.1 49,832, but with real LFW diversity.

python build_v72_splits.py
"""
import random
from pathlib import Path
from collections import Counter

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"
LFW_EYE_DIR = BASE / "filter_data" / "lfw_eye_enlarging"

SEED = 42
random.seed(SEED)

# Load original v5 filter split
src = (SPLITS / "v5_train_filter.txt").read_text(encoding="utf-8").splitlines()
header = src[0] if src[0].startswith("path\t") else None
lines  = [l for l in src if not l.startswith("path\t") and l.strip()]

# Oversample original lines (same as v7: eye ×4, face ×3)
oversampled = []
for line in lines:
    oversampled.append(line)
    path = line.split("\t")[0]
    if "eye_enlarging" in path:
        oversampled.extend([line] * 3)   # total 4×
    elif "face_reshaping" in path:
        oversampled.extend([line] * 2)   # total 3×

# Add LFW eye_enlarging × 4
lfw_imgs = sorted(LFW_EYE_DIR.glob("*.jpg"))
print(f"LFW eye_enlarging images: {len(lfw_imgs)}")
for img_path in lfw_imgs:
    entry = f"{img_path}\t2"
    oversampled.extend([entry] * 4)

random.shuffle(oversampled)

out_lines = ([header] if header else []) + oversampled
(SPLITS / "v72_train_filter.txt").write_text(
    "\n".join(out_lines) + "\n", encoding="utf-8")

def ftype(line):
    p = line.split("\t")[0]
    if "lfw_eye" in p:         return "lfw_eye_enlarging"
    if "eye_enlarging" in p:   return "eye_enlarging(orig)"
    if "face_reshaping" in p:  return "face_reshaping"
    if "smoothing" in p:       return "smoothing"
    if "whitening" in p:       return "whitening"
    return "other(FFHQ)"

counts = Counter(ftype(l) for l in oversampled)
print("=== v72_train_filter.txt ===")
for t in ["smoothing", "whitening", "eye_enlarging(orig)", "lfw_eye_enlarging",
          "face_reshaping", "other(FFHQ)"]:
    print(f"  {t:<25s}: {counts[t]:6d}")
print(f"  {'eye_enlarging TOTAL':<25s}: {counts['eye_enlarging(orig)']+counts['lfw_eye_enlarging']:6d}")
print(f"  {'Total':<25s}: {len(oversampled):6d}")
print("Saved -> splits/v72_train_filter.txt")
