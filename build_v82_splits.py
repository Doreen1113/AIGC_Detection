"""
v8.2 real split: v79 base (87,891 real + 22,819 fake)
              + Celeb-DF-v2 real 4,711 (4,911 clean - 200 blind holdout)

Filter split: reuse v8_train_filter.txt (190,771) unchanged.

Output:
  splits/celebdf_real_holdout.txt   (200 blind holdout, never used in training)
  splits/v82_train_real_fake.txt    (92,602 real + 22,819 fake = 115,421 lines)
"""
import random
from pathlib import Path

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"

# ── 1. Celeb-DF-v2 clean real paths ──────────────────────────────────────────
celeb_all = [
    p.strip()
    for p in (BASE / "Celeb-DF-v2/frames/real/clean_output/clean_paths.txt").read_text().splitlines()
    if p.strip()
]
print(f"Celeb-DF-v2 clean total: {len(celeb_all)}")

random.seed(42)
celeb_shuffled = celeb_all.copy()
random.shuffle(celeb_shuffled)

holdout   = celeb_shuffled[:200]
train_cel = celeb_shuffled[200:]

(SPLITS / "celebdf_real_holdout.txt").write_text("\n".join(holdout) + "\n")
print(f"Blind holdout : {len(holdout)}  → splits/celebdf_real_holdout.txt")
print(f"Training pool : {len(train_cel)}")

# ── 2. v79 base split ─────────────────────────────────────────────────────────
v79_lines = [
    l for l in (SPLITS / "v79_train_real_fake.txt").read_text().splitlines()
    if l.strip()
]
print(f"\nv79 base lines: {len(v79_lines)}")

# ── 3. Celeb-DF-v2 lines (format: path\t0\tCelebDF-real) ─────────────────────
celeb_lines = [f"{p}\t0\tCelebDF-real" for p in train_cel]

# ── 4. Merge & shuffle ────────────────────────────────────────────────────────
all_lines = v79_lines + celeb_lines
random.shuffle(all_lines)

out_path = SPLITS / "v82_train_real_fake.txt"
out_path.write_text("\n".join(all_lines) + "\n")

real_count = sum(1 for l in all_lines if "\t0" in l.split("\t")[1:2] or l.split("\t")[-1] == "0" or (len(l.split("\t")) == 2 and l.split("\t")[1] == "0"))
print(f"\nv82 split written: {len(all_lines)} lines")
print(f"  real  : {sum(1 for l in all_lines if l.split(chr(9))[1] == '0')} (v79 87,891 + CelebDF {len(train_cel)})")
print(f"  fake  : {sum(1 for l in all_lines if l.split(chr(9))[1] == '1')}")
print(f"  → splits/v82_train_real_fake.txt")
print(f"\nFilter split: reuse splits/v8_train_filter.txt (190,771 lines) — no change needed")
