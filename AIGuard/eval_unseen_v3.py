"""
Evaluate DualBranchModel (v3, 3-class) on the unseen held-out set.
Reads clean_paths.txt (if exists) for cleaned image list; falls back to all images.

Binary eval: real=0, fake/filter both=1 (not-real).
Also prints 3-class prediction distribution.

Usage:
    conda run -n base python AIGuard/eval_unseen_v3.py
"""

import os
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, confusion_matrix, classification_report
import numpy as np

BASE          = r"C:\My_Project\AIGC"
CKPT          = os.path.join(BASE, "shufflenet_v2_3class_ffhq_v3.pth")
UNSEEN_DIR    = os.path.join(BASE, "AIGuard", "unseen")
CLEAN_TXT     = os.path.join(UNSEEN_DIR, "clean_output", "clean_paths.txt")
BATCH_SIZE    = 64
CLASSES       = ["real", "fake", "filter"]


# ── Model (must match train_3class_ffhq_v3.py architecture) ──────────────────

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
        self.fft_branch = FFTBranch(out_dim=256)
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])


# ── Dataset ───────────────────────────────────────────────────────────────────

class UnseenDataset(Dataset):
    def __init__(self, paths, transform=None):
        self.samples = []
        for p in paths:
            fname = os.path.basename(p).lower()
            label = 0 if fname.startswith("real") else 1   # real=0, fake=1
            self.samples.append((p, label))
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label


def load_paths():
    if os.path.exists(CLEAN_TXT):
        paths = [p.strip() for p in open(CLEAN_TXT).readlines() if p.strip()]
        print(f"  Using clean_paths.txt: {len(paths)} images")
    else:
        exts = {".jpg", ".jpeg", ".png", ".jfif"}
        paths = [os.path.join(UNSEEN_DIR, f) for f in os.listdir(UNSEEN_DIR)
                 if os.path.splitext(f)[1].lower() in exts]
        print(f"  No clean_paths.txt found — using all {len(paths)} images")
    return paths


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Load model
    print(f"Loading model from {CKPT} ...")
    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device, weights_only=False))
    model.eval()

    # Dataset
    paths = load_paths()
    dataset = UnseenDataset(paths, transform=transform)
    loader  = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False,
                         num_workers=0, pin_memory=True)

    n_real = sum(1 for _, lbl in dataset.samples if lbl == 0)
    n_fake = sum(1 for _, lbl in dataset.samples if lbl == 1)
    print(f"  Samples: {len(dataset)} total  (real={n_real}, fake={n_fake})\n")

    # Inference
    all_labels, all_preds3, all_probs = [], [], []
    with torch.no_grad():
        for imgs, lbls in loader:
            imgs = imgs.to(device)
            out  = model(imgs)
            probs3 = torch.softmax(out, dim=1).cpu().numpy()   # (B, 3)
            preds3 = out.argmax(dim=1).cpu().numpy()
            all_labels.extend(lbls.numpy())
            all_preds3.extend(preds3)
            all_probs.extend(probs3)

    all_labels = np.array(all_labels)
    all_preds3 = np.array(all_preds3)
    all_probs  = np.array(all_probs)   # (N, 3)

    # 3-class prediction distribution
    print("=== 3-class prediction distribution ===")
    for ci, cname in enumerate(CLASSES):
        n = (all_preds3 == ci).sum()
        print(f"  {cname:8s}: {n:4d}  ({n/len(all_preds3)*100:.1f}%)")

    # Binary eval: real=0, fake/filter=1
    binary_preds  = (all_preds3 != 0).astype(int)          # 0=real, 1=not-real
    prob_not_real = 1.0 - all_probs[:, 0]                   # P(not real) = P(fake)+P(filter)

    acc   = (binary_preds == all_labels).mean()
    f1    = f1_score(all_labels, binary_preds)
    prec  = precision_score(all_labels, binary_preds)
    rec   = recall_score(all_labels, binary_preds)
    auroc = roc_auc_score(all_labels, prob_not_real)
    cm    = confusion_matrix(all_labels, binary_preds)

    print(f"\n=== Binary Eval (real vs not-real) ===")
    print(f"  Acc={acc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  AUROC={auroc:.4f}")
    print(f"\nConfusion Matrix (rows=actual, cols=pred):")
    print(f"               Pred Real  Pred Not-Real")
    print(f"  Actual Real  {cm[0][0]:9d}  {cm[0][1]:13d}   (real→fake errors: {cm[0][1]})")
    print(f"  Actual Fake  {cm[1][0]:9d}  {cm[1][1]:13d}")

    # Breakdown: where did actual-fake images get predicted?
    fake_mask = (all_labels == 1)
    print(f"\nActual-fake predictions by 3-class model:")
    for ci, cname in enumerate(CLASSES):
        n = (all_preds3[fake_mask] == ci).sum()
        print(f"  → {cname:8s}: {n}")
