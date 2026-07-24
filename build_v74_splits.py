"""
Build v7.4 real split: v6_train_real_fake.txt + LFW real images (×4).

Problem in v7.2: 24,000 LFW eye_enlarging in filter, but LFW real in training is small.
Fix: add the original LFW images (sources of lfw_eye_enlarging) to real split × 4.

This directly teaches the model:
  LFW_Person_XXXX.jpg (original) = real
  lfw_eye_LFW_Person_XXXX.jpg   = filter

Excludes images already in truetest_real.txt.

python build_v74_splits.py
"""
import random
from pathlib import Path

BASE     = Path(r"C:\My_Project\AIGC")
SPLITS   = BASE / "splits"
LFW_EYE  = BASE / "filter_data" / "lfw_eye_enlarging"
LFW_DIR  = BASE / "lfw"

SEED = 42
random.seed(SEED)

# Load excluded test images (path-based)
excluded = set()
for f in ("truetest_real.txt", "truetest_filter.txt", "truetest_fake.txt"):
    p = SPLITS / f
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                excluded.add(line.lower())

# Recover original LFW source paths from lfw_eye_enlarging filenames
# Pattern: lfw_eye_{stem}.jpg  where stem = original LFW stem e.g. Tony_Blair_0025
lfw_real_paths = []
for img in sorted(LFW_EYE.glob("*.jpg")):
    # strip prefix "lfw_eye_"
    stem = img.stem[len("lfw_eye_"):]          # e.g. Tony_Blair_0025
    # find person directory: everything up to last _XXXX
    parts = stem.rsplit("_", 1)
    if len(parts) != 2:
        continue
    person, num = parts[0], parts[1]           # e.g. "Tony_Blair", "0025"
    src = LFW_DIR / person / f"{stem}.jpg"
    if src.exists() and str(src).lower() not in excluded:
        lfw_real_paths.append(str(src))

print(f"LFW real candidates recovered: {len(lfw_real_paths)}")

# Build new real split = original v6 real/fake + LFW real × 4
orig = (SPLITS / "v6_train_real_fake.txt").read_text(encoding="utf-8").splitlines()
header = orig[0] if orig[0].startswith("path\t") else None
orig_lines = [l for l in orig if not l.startswith("path\t") and l.strip()]

# Count original
n_real_orig = sum(1 for l in orig_lines if l.split("\t")[1] == "0")
n_fake_orig = sum(1 for l in orig_lines if l.split("\t")[1] == "1")
print(f"Original real/fake split: real={n_real_orig}  fake={n_fake_orig}")

# Add LFW real × 4
new_real_lines = []
for p in lfw_real_paths:
    entry = f"{p}\t0"
    new_real_lines.extend([entry] * 4)

print(f"Adding LFW real: {len(lfw_real_paths)} imgs × 4 = {len(new_real_lines)} lines")

all_lines = orig_lines + new_real_lines
random.shuffle(all_lines)

out = ([header] if header else []) + all_lines
(SPLITS / "v74_train_real_fake.txt").write_text(
    "\n".join(out) + "\n", encoding="utf-8")

from collections import Counter
labels = Counter(l.split("\t")[1] for l in all_lines)
print(f"\n=== v74_train_real_fake.txt ===")
print(f"  real  : {labels['0']:6d}  (+{len(new_real_lines)} LFW real)")
print(f"  fake  : {labels['1']:6d}")
print(f"  Total : {len(all_lines):6d}")
print("Saved -> splits/v74_train_real_fake.txt")
