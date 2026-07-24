"""
Build Celeb-DF-v2 blind holdout eval set and run v8.1 eval.

Composition:
  Real : 200 frames from splits/celebdf_real_holdout.txt
  Fake : 200 frames sampled from frames/fake/clean_output/clean_paths.txt
         (diverse identity selection: sample across unique source IDs)
  Total: 400 frames

Output:
  splits/celebdf_v2_blind_holdout.txt   (path  label)
  results/celebdf_v2_blind_eval.txt     (eval results)
"""

import random, torch, torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from pathlib import Path
from collections import defaultdict
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import roc_auc_score, confusion_matrix
import numpy as np

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"
CKPT   = BASE / "shufflenet_v2_3class_v81.pth"
SEED   = 99   # new seed — never used in any prior split

N_FAKE = 200


# ── Model ────────────────────────────────────────────────────────────────────
class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        return self.net(torch.log(torch.abs(fft) + 1e-8))

class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch     = FFTBranch(256)
        self.classifier     = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))
    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))

transform = T.Compose([T.Resize((224,224)), T.ToTensor(), T.Normalize([0.5]*3,[0.5]*3)])

class HoldoutDataset(Dataset):
    def __init__(self, rows):   # rows: (path, label)
        self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        p, l = self.rows[i]
        return transform(Image.open(p).convert("RGB")), l

# ── Step 1: Build holdout split ───────────────────────────────────────────────
print("=" * 55)
print("Building Celeb-DF-v2 blind holdout")
print("=" * 55)

# Real: use existing 200-frame holdout
real_paths = [l.strip() for l in (SPLITS/"celebdf_real_holdout.txt").read_text().splitlines() if l.strip()]
real_paths = [p for p in real_paths if Path(p).exists()]
print(f"\nReal frames available: {len(real_paths)}")

# Fake: diverse-identity sampling
fake_pool = [l.strip() for l in (BASE/"Celeb-DF-v2/frames/fake/clean_output/clean_paths.txt").read_text().splitlines() if l.strip()]
fake_pool = [p for p in fake_pool if Path(p).exists()]
print(f"Fake frames available: {len(fake_pool)}")

# Group by source identity (first field: id0 in id0_id16_...)
by_src = defaultdict(list)
for p in fake_pool:
    stem = Path(p).stem   # e.g. id0_id16_0001_f00151
    src  = stem.split("_")[0]
    by_src[src].append(p)

print(f"Unique source identities: {len(by_src)}")

# Sample N_FAKE frames: round-robin across identities
rng = random.Random(SEED)
for lst in by_src.values():
    rng.shuffle(lst)
sorted_srcs = sorted(by_src.keys())
selected_fake = []
i = 0
while len(selected_fake) < N_FAKE:
    src = sorted_srcs[i % len(sorted_srcs)]
    if by_src[src]:
        selected_fake.append(by_src[src].pop())
    i += 1

print(f"Fake frames selected: {len(selected_fake)}")

# Write split file
holdout_path = SPLITS / "celebdf_v2_blind_holdout.txt"
with open(holdout_path, "w", encoding="utf-8") as f:
    f.write("path\tlabel\n")
    for p in real_paths:
        f.write(f"{p}\t0\n")   # label 0 = real (same convention as our model: 0=real,1=fake,2=filter)
    for p in selected_fake:
        f.write(f"{p}\t1\n")   # label 1 = fake

print(f"\nHoldout split saved: {holdout_path}")
print(f"  Real : {len(real_paths)}")
print(f"  Fake : {len(selected_fake)}")
print(f"  Total: {len(real_paths)+len(selected_fake)}")

# ── Step 2: Eval ──────────────────────────────────────────────────────────────
print(f"\n{'='*55}")
print(f"Evaluating v8.1 on blind holdout")
print(f"{'='*55}")

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device : {device}")
model = DualBranchModel(num_classes=3).to(device)
model.load_state_dict(torch.load(CKPT, map_location=device, weights_only=False))
model.eval()

rows = [(p, 0) for p in real_paths] + [(p, 1) for p in selected_fake]
ds   = HoldoutDataset(rows)
loader = DataLoader(ds, batch_size=64, shuffle=False, num_workers=0)

all_labels, all_probs, all_preds = [], [], []
with torch.no_grad():
    for imgs, lbls in loader:
        out   = model(imgs.to(device))
        probs = torch.softmax(out, dim=1).cpu().numpy()
        preds = out.argmax(dim=1).cpu().numpy()
        all_labels.extend(lbls.numpy())
        all_probs.extend(probs)
        all_preds.extend(preds)

all_labels = np.array(all_labels)
all_probs  = np.array(all_probs)
all_preds  = np.array(all_preds)

# Binary: fake=positive  (label 1=fake → positive; 0=real → negative)
prob_fake  = all_probs[:, 1] + all_probs[:, 2]   # P(fake) + P(filter) as "not-real" score
auroc      = roc_auc_score(all_labels, prob_fake)

# Real recall, Fake recall at threshold 0.5
real_mask = (all_labels == 0)
fake_mask = (all_labels == 1)
pred_real = (all_preds == 0)
pred_fake = (all_preds != 0)

real_recall = pred_real[real_mask].mean()
fake_recall = pred_fake[fake_mask].mean()

# 3-class distribution
print(f"\n3-class prediction distribution:")
for ci, cn in enumerate(["real","fake","filter"]):
    n = (all_preds==ci).sum()
    print(f"  {cn:6s}: {n:4d} ({n/len(all_preds)*100:.1f}%)")

print(f"\n{'='*55}")
print(f"Celeb-DF-v2 Blind Holdout — v8.1 Results")
print(f"{'='*55}")
print(f"  Binary AUROC        : {auroc:.4f}")
print(f"  Real recall (n={len(real_paths)}) : {real_recall:.1%}  ({pred_real[real_mask].sum()}/{len(real_paths)})")
print(f"  Fake recall (n={len(selected_fake)}) : {fake_recall:.1%}  ({pred_fake[fake_mask].sum()}/{len(selected_fake)})")

# Save result
out_txt = BASE / "results" / "celebdf_v2_blind_eval.txt"
out_txt.parent.mkdir(exist_ok=True)
out_txt.write_text(
    f"Celeb-DF-v2 Blind Holdout Eval — v8.1 (2026-07-22)\n"
    f"Real: {len(real_paths)}  Fake: {len(selected_fake)}  Total: {len(rows)}\n\n"
    f"Binary AUROC : {auroc:.4f}\n"
    f"Real recall  : {real_recall:.1%} ({pred_real[real_mask].sum()}/{len(real_paths)})\n"
    f"Fake recall  : {fake_recall:.1%} ({pred_fake[fake_mask].sum()}/{len(selected_fake)})\n",
    encoding="utf-8"
)
print(f"\nResults saved: {out_txt}")
