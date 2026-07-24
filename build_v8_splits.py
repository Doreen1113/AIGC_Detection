"""
Build v8 filter split = v76 filter split + LFW eye_enlarging ×4 extra (total ×8).

Rationale:
  eye_enlarging is currently 58.1% on true test (26/62 misclassified as real).
  Root cause: LFW domain real:eye = 60,000:24,000 = 2.5:1 — model biased toward real.
  Fix: increase LFW eye to ×8 total → real:eye = 60,000:48,000 = 1.25:1

v76 breakdown (166,770):
  - FFHQ-based filters + LFW eye ×4 (24,000) + LFW whitening ×4 (24,000) + LFW reshape ×4 (24,000)

v8 adds:
  - LFW eye ×4 more → LFW eye total = ×8 (48,000)
  → v8_train_filter.txt total = 190,770

Real split: reuse v79_train_real_fake.txt unchanged (real=87,891, fake=22,819)

python build_v8_splits.py
"""
from pathlib import Path
from collections import Counter

BASE          = Path(r"C:\My_Project\AIGC")
SPLITS        = BASE / "splits"
LFW_EYE_DIR  = BASE / "filter_data" / "lfw_eye_enlarging"
FILTER_LABEL  = 2
EXTRA_OS      = 4   # add 4 more → total ×8

def load_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("path\t")]

base_lines = load_lines(SPLITS / "v76_train_filter.txt")
print(f"v76 filter split: {len(base_lines)} lines")

lfw_eye_paths = sorted(LFW_EYE_DIR.glob("lfw_eye_*.jpg"))
print(f"LFW eye_enlarging unique images: {len(lfw_eye_paths)}")

new_lines = list(base_lines)
for _ in range(EXTRA_OS):
    for p in lfw_eye_paths:
        new_lines.append(f"{p}\t{FILTER_LABEL}")

out = SPLITS / "v8_train_filter.txt"
out.write_text("\n".join(new_lines), encoding="utf-8")

labels = [int(l.split("\t")[1]) for l in new_lines if "\t" in l]
cnt = Counter(labels)
print(f"\nv8_train_filter.txt: {len(new_lines)} lines  (filter={cnt[2]})")
print(f"  v76 base: {len(base_lines)}")
print(f"  + LFW eye ×{EXTRA_OS} extra: {len(lfw_eye_paths)*EXTRA_OS}")
print(f"  LFW eye total in split: {len(lfw_eye_paths)*8} (×8)")

# gradient balance preview
real_count   = 87891   # v79 real split
fake_count   = 22819
filter_count = len(new_lines)
total        = real_count + fake_count + filter_count
aw_r = total / (3 * real_count)
aw_k = total / (3 * fake_count)
aw_f = total / (3 * filter_count)
print(f"\nGradient balance (no cap):")
print(f"  auto_w: real={aw_r:.3f}  fake={aw_k:.3f}  filter={aw_f:.3f}")
print(f"  LFW eye:real ratio = {len(lfw_eye_paths)*8}/{real_count} in LFW domain = "
      f"{len(lfw_eye_paths)*8 / 60000:.2f}:1  (v7.9 was {24000/60000:.2f}:1)")
print(f"Wrote: {out}")
