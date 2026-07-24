"""
Build v8.1 real split: LFW real ×11 (was ×10 in v7.9/v8).

Motivation:
  v8 added LFW eye ×8 → eye 58.1%→62.9% (+4.8%) but real 87.6%→85.2% (-2.4%).
  LFW real:LFW filter dropped from 0.833:1 to 0.625:1.
  ×11 → 66,000:96,000 = 0.6875:1 — moves back toward balance.
  Filter split: reuse v8_train_filter.txt unchanged (190,771, LFW eye ×8).

python build_v81_splits.py
"""
from pathlib import Path
from collections import Counter

BASE        = Path(r"C:\My_Project\AIGC")
SPLITS      = BASE / "splits"
LFW_EYE_DIR = BASE / "filter_data" / "lfw_eye_enlarging"
REAL_OS     = 11

def load_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("path\t")]

base_lines = load_lines(SPLITS / "v6_train_real_fake.txt")

lfw_real_paths = []
for img in sorted(LFW_EYE_DIR.glob("lfw_eye_*.jpg")):
    stem = img.stem[len("lfw_eye_"):]
    parts = stem.rsplit("_", 1)
    if len(parts) == 2:
        lfw_path = BASE / "lfw" / parts[0] / f"{stem}.jpg"
        if lfw_path.exists():
            lfw_real_paths.append(str(lfw_path))

new_lines = list(base_lines)
for _ in range(REAL_OS):
    for p in lfw_real_paths:
        new_lines.append(f"{p}\t0")

labels = [int(l.split("\t")[1]) for l in new_lines if "\t" in l]
cnt = Counter(labels)
out = SPLITS / "v81_train_real_fake.txt"
out.write_text("\n".join(new_lines), encoding="utf-8")

lfw_n = len(lfw_real_paths)
print(f"v81: real={cnt[0]}  fake={cnt[1]}  LFW real lines={lfw_n*REAL_OS}")
print(f"LFW real:LFW filter = {lfw_n*REAL_OS}:{96000} = {lfw_n*REAL_OS/96000:.3f}:1")
print(f"  (v8 was {lfw_n*10}:{96000} = {lfw_n*10/96000:.3f}:1)")
print(f"Wrote: {out}")
