"""
Build v7 filter training split: oversample eye_enlarging × 4, face_reshaping × 3.

Root cause from filter recall analysis (2026-07-20):
  smoothing     29,875 samples → 100% recall
  whitening     29,959 samples →  61% recall
  eye_enlarging  6,229 samples →  27% recall  ← main bottleneck
  face_reshaping 5,989 samples →  81% recall

Strategy: oversample geometric filter types to match skin-processing types.
real+fake split unchanged (v6_train_real_fake.txt).

python build_v7_splits.py
"""
import random
from pathlib import Path

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
        oversampled.extend([line] * 3)   # total 4×
    elif "face_reshaping" in path:
        oversampled.extend([line] * 2)   # total 3×

random.shuffle(oversampled)

out_lines = ([header] if header else []) + oversampled
(SPLITS / "v7_train_filter.txt").write_text(
    "\n".join(out_lines) + "\n", encoding="utf-8")

# Stats
from collections import Counter
def ftype(line):
    p = line.split("\t")[0]
    for t in ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]:
        if t in p: return t
    return "other"

counts = Counter(ftype(l) for l in oversampled)
print("=== v7_train_filter.txt ===")
for t in ["smoothing", "whitening", "eye_enlarging", "face_reshaping", "other"]:
    print(f"  {t:<20s}: {counts[t]:6d}")
print(f"  {'Total':<20s}: {len(oversampled):6d}")
print(f"Saved -> splits/v7_train_filter.txt")
