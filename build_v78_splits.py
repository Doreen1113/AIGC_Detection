"""
Build v7.8 real split: LFW real ×8 (was ×6 in v7.7).

Trend so far:
  ×4 (v7.6): real 86.8%, filter 81.5%
  ×6 (v7.7): real 88.8%, filter 83.9%  ← both improved!
  ×8 (v7.8): target real ~90%+, filter ~85%+?

Filter split unchanged (v76_train_filter.txt, 166,771 lines).
Init from v7.7.

python build_v78_splits.py
"""
from pathlib import Path
from collections import Counter

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
LFW_EYE_DIR  = BASE / "filter_data" / "lfw_eye_enlarging"
REAL_OVERSAMPLE = 8

def load_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("path\t")]

base_lines = load_lines(SPLITS / "v6_train_real_fake.txt")
print(f"v6 real/fake base: {len(base_lines)} lines")

lfw_real_paths = []
for img in sorted(LFW_EYE_DIR.glob("lfw_eye_*.jpg")):
    stem = img.stem[len("lfw_eye_"):]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2:
        person_dir, _ = parts
        lfw_path = BASE / "lfw" / person_dir / f"{stem}.jpg"
        if lfw_path.exists():
            lfw_real_paths.append(str(lfw_path))
print(f"LFW real source images: {len(lfw_real_paths)}")

new_lines = list(base_lines)
for _ in range(REAL_OVERSAMPLE):
    for p in lfw_real_paths:
        new_lines.append(f"{p}\t0")

labels = [int(l.split("\t")[1]) for l in new_lines if "\t" in l]
cnt = Counter(labels)
print(f"\nv78_train_real_fake.txt: real={cnt[0]}  fake={cnt[1]}  total={len(new_lines)}")
print(f"  LFW real lines: {len(lfw_real_paths)*REAL_OVERSAMPLE}")
print(f"  LFW real:filter ratio = 1:{72000/(len(lfw_real_paths)*REAL_OVERSAMPLE):.2f}")

out = SPLITS / "v78_train_real_fake.txt"
out.write_text("\n".join(new_lines), encoding="utf-8")
print(f"Wrote: {out}")

filter_count = 166771
real_count, fake_count = cnt[0], cnt[1]
total = real_count + fake_count + filter_count
aw_real = total / (3*real_count); aw_filter = total / (3*filter_count)
lfw_r_lines = len(lfw_real_paths)*REAL_OVERSAMPLE
print(f"\nGradient (no cap): real={aw_real:.3f}  filter={aw_filter:.3f}")
print(f"  LFW real gradient:   {lfw_r_lines*aw_real:.0f}")
print(f"  LFW filter gradient: {72000*aw_filter:.0f}")
print(f"  LFW ratio: {lfw_r_lines*aw_real/(72000*aw_filter):.3f}")
