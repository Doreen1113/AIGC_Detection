"""
Build v7.6 filter split = v7.2 filter split + LFW whitening ×4 + LFW face_reshaping ×4.

  v7.2 filter split (118,771) already has:
    - AIGuard/FFHQ whitening, smoothing, face_reshaping, eye_enlarging (oversample)
    - LFW eye_enlarging ×4 (24,000)

  v7.6 adds:
    - LFW whitening ×4  (6,000 × 4 = 24,000)
    - LFW face_reshaping ×4  (6,000 × 4 = 24,000)
    → v76_train_filter.txt total = 166,771

  Real/Fake split: reuse v74_train_real_fake.txt unchanged (real=51,891, fake=22,819)
    LFW real (24,012) already present; real:filter gradient stays ~1:1 with no cap.

python build_v76_splits.py
"""
from pathlib import Path
from collections import Counter

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"

FILTER_LABEL    = 2
OVERSAMPLE      = 4

v72_filter_txt  = SPLITS / "v72_train_filter.txt"
out_filter_txt  = SPLITS / "v76_train_filter.txt"

lfw_white_dir   = BASE / "filter_data" / "lfw_whitening"
lfw_reshape_dir = BASE / "filter_data" / "lfw_face_reshaping"


def load_lines(p):
    return [l for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l and not l.startswith("path\t")]


# ── start from v7.2 filter split ──
base_lines = load_lines(v72_filter_txt)
print(f"v7.2 filter split: {len(base_lines)} lines")

new_lines = list(base_lines)

# ── add LFW whitening ×4 ──
white_paths = sorted(lfw_white_dir.glob("*.jpg"))
print(f"LFW whitening images: {len(white_paths)}")
for _ in range(OVERSAMPLE):
    for p in white_paths:
        new_lines.append(f"{p}\t{FILTER_LABEL}")

# ── add LFW face_reshaping ×4 ──
reshape_paths = sorted(lfw_reshape_dir.glob("*.jpg"))
print(f"LFW face_reshaping images: {len(reshape_paths)}")
for _ in range(OVERSAMPLE):
    for p in reshape_paths:
        new_lines.append(f"{p}\t{FILTER_LABEL}")

# ── count and write ──
total = len(new_lines)
print(f"v76_train_filter.txt total: {total}")
print(f"  base v7.2: {len(base_lines)}")
print(f"  + LFW whitening ×{OVERSAMPLE}: {len(white_paths)*OVERSAMPLE}")
print(f"  + LFW face_reshaping ×{OVERSAMPLE}: {len(reshape_paths)*OVERSAMPLE}")

out_filter_txt.write_text("\n".join(new_lines), encoding="utf-8")
print(f"\nWrote: {out_filter_txt}")

# ── gradient balance preview ──
real_count   = 51891  # from v74
fake_count   = 22819
filter_count = total
grand_total  = real_count + fake_count + filter_count
auto_w_real   = grand_total / (3 * real_count)
auto_w_fake   = grand_total / (3 * fake_count)
auto_w_filter = grand_total / (3 * filter_count)
print(f"\nGradient balance preview (no cap):")
print(f"  auto_w: real={auto_w_real:.3f}  fake={auto_w_fake:.3f}  filter={auto_w_filter:.3f}")
print(f"  Total real gradient:   {real_count * auto_w_real:.0f}")
print(f"  Total filter gradient: {filter_count * auto_w_filter:.0f}")
print(f"  Real:filter ratio:     {real_count*auto_w_real / (filter_count*auto_w_filter):.3f}")
