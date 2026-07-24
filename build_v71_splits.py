"""
Build v7.1 filter training split: oversample eye_enlarging × 8, face_reshaping × 3.

v7 used ×4 for eye_enlarging → 41.9% recall.
v7.1 increases to ×8 to check ceiling effect.

python build_v71_splits.py
"""
import random
from pathlib import Path
from collections import Counter

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"

SEED = 42
random.seed(SEED)

src = (SPLITS / "v5_train_filter.txt").read_text(encoding="utf-8").splitlines()
header = src[0] if src[0].startswith("path\t") else None
lines  = [l for l in src if not l.startswith("path\t") and l.strip()]

oversampled = []
for line in lines:
    oversampled.append(line)
    path = line.split("\t")[0]
    if "eye_enlarging" in path:
        oversampled.extend([line] * 7)   # total 8×
    elif "face_reshaping" in path:
        oversampled.extend([line] * 2)   # total 3×

random.shuffle(oversampled)

out_lines = ([header] if header else []) + oversampled
(SPLITS / "v71_train_filter.txt").write_text(
    "\n".join(out_lines) + "\n", encoding="utf-8")

def ftype(line):
    p = line.split("\t")[0]
    for t in ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]:
        if t in p: return t
    return "other"

counts = Counter(ftype(l) for l in oversampled)
print("=== v71_train_filter.txt ===")
for t in ["smoothing", "whitening", "eye_enlarging", "face_reshaping", "other"]:
    print(f"  {t:<20s}: {counts[t]:6d}")
print(f"  {'Total':<20s}: {len(oversampled):6d}")
print("Saved -> splits/v71_train_filter.txt")
