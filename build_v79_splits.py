"""Build v7.9 real split: LFW real ×10."""
from pathlib import Path
from collections import Counter

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
LFW_EYE_DIR  = BASE / "filter_data" / "lfw_eye_enlarging"
REAL_OVERSAMPLE = 10

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
for _ in range(REAL_OVERSAMPLE):
    for p in lfw_real_paths:
        new_lines.append(f"{p}\t0")

labels = [int(l.split("\t")[1]) for l in new_lines if "\t" in l]
cnt = Counter(labels)
out = SPLITS / "v79_train_real_fake.txt"
out.write_text("\n".join(new_lines), encoding="utf-8")
print(f"v79: real={cnt[0]}  fake={cnt[1]}  LFW real lines={len(lfw_real_paths)*REAL_OVERSAMPLE}")
print(f"LFW real:filter = 1:{72000/(len(lfw_real_paths)*REAL_OVERSAMPLE):.2f}")
print(f"Wrote: {out}")
