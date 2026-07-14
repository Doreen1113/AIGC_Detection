"""
Evaluate DualBranchModel v3 on FakeClue face-category test set.
Reads FakeClue/test_clean/labels.csv for paths + labels (0=fake, 1=real).

Reports overall + per-category (deepfake / human) binary AUROC.

Usage:
    python AIGuard/eval_fakeclue.py
"""

import os
import csv
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score, confusion_matrix
import numpy as np

BASE        = r"C:\My_Project\AIGC"
CKPT        = os.path.join(BASE, "shufflenet_v2_3class_ffhq_v3.pth")
LABELS_CSV  = os.path.join(BASE, "FakeClue", "test_clean", "labels.csv")
BATCH_SIZE  = 64


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


class FakeClueDataset(Dataset):
    def __init__(self, rows, transform=None):
        self.rows = rows   # list of (path, label, cate)
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        path, label, cate = self.rows[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label, cate


def collate_fn(batch):
    imgs    = torch.stack([b[0] for b in batch])
    labels  = torch.tensor([b[1] for b in batch])
    cates   = [b[2] for b in batch]
    return imgs, labels, cates


def eval_binary(labels, preds3, probs):
    """real=1(positive), fake/filter=0. AUROC: P(not-real)=1-P(real) scoring fake higher."""
    binary_preds = (np.array(preds3) == 0).astype(int)   # pred fake=1, pred real=0  → invert for fake-positive
    # Actually: label 0=fake (positive class for AUROC), label 1=real (negative)
    # AUROC: higher score = more likely fake
    prob_fake = 1.0 - np.array(probs)[:, 0]              # P(not real) = P(fake or filter)
    binary_pred_fake = (np.array(preds3) != 0).astype(int)   # 1=model says not-real(fake/filter)

    # For standard metrics, fake=1, real=0 (invert the original label convention)
    lbl_fake_pos = (1 - np.array(labels))   # original: 0=fake→1, 1=real→0

    auroc = roc_auc_score(lbl_fake_pos, prob_fake)
    f1    = f1_score(lbl_fake_pos, binary_pred_fake)
    prec  = precision_score(lbl_fake_pos, binary_pred_fake)
    rec   = recall_score(lbl_fake_pos, binary_pred_fake)
    cm    = confusion_matrix(lbl_fake_pos, binary_pred_fake)
    return auroc, f1, prec, rec, cm


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Loading model from {CKPT}")
    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device, weights_only=False))
    model.eval()

    # Load labels
    rows = []
    with open(LABELS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append((r["path"], int(r["label"]), r["cate"]))
    print(f"Total samples: {len(rows)}")
    for cate in ["deepfake", "human"]:
        n = sum(1 for r in rows if r[2] == cate)
        nf = sum(1 for r in rows if r[2] == cate and r[1] == 0)
        nr = sum(1 for r in rows if r[2] == cate and r[1] == 1)
        print(f"  {cate}: {n}  (fake={nf}, real={nr})")

    dataset = FakeClueDataset(rows, transform=transform)
    loader  = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False,
                         num_workers=0, pin_memory=True, collate_fn=collate_fn)

    all_labels, all_preds3, all_probs, all_cates = [], [], [], []
    with torch.no_grad():
        for imgs, lbls, cates in loader:
            out   = model(imgs.to(device))
            probs = torch.softmax(out, dim=1).cpu().numpy()
            preds = out.argmax(dim=1).cpu().numpy()
            all_labels.extend(lbls.numpy())
            all_preds3.extend(preds)
            all_probs.extend(probs)
            all_cates.extend(cates)

    all_labels = np.array(all_labels)
    all_preds3 = np.array(all_preds3)
    all_probs  = np.array(all_probs)

    print("\n=== 3-class prediction distribution ===")
    for ci, cname in enumerate(["real", "fake", "filter"]):
        n = (all_preds3 == ci).sum()
        print(f"  {cname}: {n} ({n/len(all_preds3)*100:.1f}%)")

    print("\n=== Binary Eval: Overall (fake vs real) ===")
    auroc, f1, prec, rec, cm = eval_binary(all_labels, all_preds3, all_probs)
    print(f"  AUROC={auroc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  Rec={rec:.4f}")
    print(f"  CM (fake-pos): TN={cm[0,0]} FP={cm[0,1]} FN={cm[1,0]} TP={cm[1,1]}")

    for cate in ["deepfake", "human"]:
        mask = np.array([c == cate for c in all_cates])
        if mask.sum() == 0:
            continue
        c_labels = all_labels[mask]
        c_preds  = all_preds3[mask]
        c_probs  = all_probs[mask]
        lbl_fake = 1 - c_labels
        if len(np.unique(lbl_fake)) < 2:
            print(f"\n=== {cate} ===  (only one class, skip AUROC)")
            continue
        auroc, f1, prec, rec, cm = eval_binary(c_labels, c_preds, c_probs)
        print(f"\n=== {cate} ({mask.sum()} samples) ===")
        print(f"  AUROC={auroc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  Rec={rec:.4f}")
