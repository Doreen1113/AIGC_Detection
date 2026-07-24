"""
Build v7.7 real/fake split: same as v7.4 but LFW real oversample ×6 (was ×4).

Root cause of v7.6 real recall drop (91.6% → 86.8%):
  LFW domain imbalance:
    LFW filter lines: 72,000  (eye_enlarging + whitening + face_reshaping, each ×4)
    LFW real lines:   24,012  (×4)
  Ratio 1:3 → model sees same LFW face 3× more as filter than as real.

v7.7 fix: LFW real ×6 → 36,018 lines, ratio becomes 1:2 (72,000 filter vs 36,018 real).
  Mid-point between v7.5 (×4, ratio 1:3) and matching (×12, ratio 1:1).

python build_v77_splits.py
"""
from pathlib import Path
from collections import Counter

BASE       = Path(r"C:\My_Project\AIGC")
SPLITS     = BASE / "splits"
LFW_EYE_DIR = BASE / "filter_data" / "lfw_eye_enlarging"

REAL_OVERSAMPLE = 6   # was 4 in v7.4/v7.5/v7.6

# ── load v6 original real/fake split ──
def load_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("path\t")]

base_lines = load_lines(SPLITS / "v6_train_real_fake.txt")
print(f"v6 real/fake base: {len(base_lines)} lines")

# ── recover LFW real paths from lfw_eye_enlarging filenames ──
lfw_real_paths = []
for img in sorted(LFW_EYE_DIR.glob("lfw_eye_*.jpg")):
    stem = img.stem[len("lfw_eye_"):]   # e.g. Tony_Blair_0025
    parts = stem.rsplit("_", 1)         # ['Tony_Blair', '0025']
    if len(parts) == 2:
        person_dir, imgid = parts
        # LFW naming: person/person_NNNN.jpg
        lfw_path = BASE / "lfw" / person_dir / f"{stem}.jpg"
        if lfw_path.exists():
            lfw_real_paths.append(str(lfw_path))

print(f"LFW real source images: {len(lfw_real_paths)}")

# ── build new real/fake split ──
new_lines = list(base_lines)

for _ in range(REAL_OVERSAMPLE):
    for p in lfw_real_paths:
        new_lines.append(f"{p}\t0")

# count
labels = [int(l.split("\t")[1]) for l in new_lines if "\t" in l]
cnt = Counter(labels)
print(f"\nv77_train_real_fake.txt:")
print(f"  real={cnt[0]}  fake={cnt[1]}  total={len(new_lines)}")
print(f"  LFW real lines: {len(lfw_real_paths) * REAL_OVERSAMPLE}")
print(f"  LFW filter lines: 72,000 (from v7.6)")
print(f"  LFW real:filter ratio = 1:{72000 / (len(lfw_real_paths)*REAL_OVERSAMPLE):.1f}")

out = SPLITS / "v77_train_real_fake.txt"
out.write_text("\n".join(new_lines), encoding="utf-8")
print(f"\nWrote: {out}")

# gradient preview
filter_count = 166771  # v7.6 filter split (unchanged)
real_count   = cnt[0]
fake_count   = cnt[1]
total        = real_count + fake_count + filter_count
aw_real   = total / (3 * real_count)
aw_filter = total / (3 * filter_count)
print(f"\nGradient preview (no cap):")
print(f"  auto_w: real={aw_real:.3f}  filter={aw_filter:.3f}")
print(f"  Total real gradient:   {real_count*aw_real:.0f}")
print(f"  Total filter gradient: {filter_count*aw_filter:.0f}")
print(f"  LFW real gradient:     {len(lfw_real_paths)*REAL_OVERSAMPLE*aw_real:.0f}")
print(f"  LFW filter gradient:   {72000*aw_filter:.0f}")
