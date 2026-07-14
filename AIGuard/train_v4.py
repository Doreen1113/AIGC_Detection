"""
v4: DualBranch 3-class, multi-source training.
Reads from splits/ files (AIGuard + WildDeepfake real/fake, FFHQ filter sources).
Inherits all v3.1 improvements: JPEG aug, Mixup, label smoothing, filter weight cap.

python AIGuard/train_v4.py
"""
import os, io, random, numpy as np
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from PIL import Image
import pandas as pd

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
WEIGHTS_PATH = str(BASE / "shufflenet_v2_3class_v4.pth")

CLASSES     = ["real", "fake", "filter"]
EPOCHS      = 20
BATCH_SIZE  = 64
MIXUP_ALPHA = 0.2


class RandomJPEGCompression:
    def __init__(self, quality_low=10, quality_high=85):
        self.lo, self.hi = quality_low, quality_high

    def __call__(self, img):
        q = random.randint(self.lo, self.hi)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q)
        buf.seek(0)
        return Image.open(buf).copy()


transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.RandomGrayscale(p=0.05),
    RandomJPEGCompression(10, 85),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])


class FaceDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths, self.labels, self.transform = paths, labels, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


def load_split_file(txt_path):
    """Read splits/<name>.txt (tab-sep: path label source). Returns (paths, labels)."""
    txt_path = Path(txt_path)
    if not txt_path.exists():
        print(f"  Warning: {txt_path} not found, skipping")
        return [], []
    paths, labels = [], []
    lines = txt_path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split("\t")
        if len(parts) >= 2:
            paths.append(parts[0])
            labels.append(int(parts[1]))
    return paths, labels


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
            nn.Linear(1024+256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


def mixup_batch(x, y, alpha=0.2):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], y, y[idx], lam


def mixup_loss(criterion, logits, ya, yb, lam):
    return lam * criterion(logits, ya) + (1 - lam) * criterion(logits, yb)


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    # Load from pre-built splits (AIGuard + WildDeepfake)
    tr_rf_p, tr_rf_l = load_split_file(SPLITS / "train_real_fake.txt")
    va_rf_p, va_rf_l = load_split_file(SPLITS / "val_real_fake.txt")
    tr_ft_p, tr_ft_l = load_split_file(SPLITS / "train_filter.txt")
    va_ft_p, va_ft_l = load_split_file(SPLITS / "val_filter.txt")

    tr_p = tr_rf_p + tr_ft_p
    tr_l = tr_rf_l + tr_ft_l
    va_p = va_rf_p + va_ft_p
    va_l = va_rf_l + va_ft_l

    from collections import Counter
    tc = Counter(tr_l)
    vc = Counter(va_l)
    print(f"Train: {len(tr_p)}  (real={tc[0]} fake={tc[1]} filter={tc[2]})")
    print(f"Val:   {len(va_p)}  (real={vc[0]} fake={vc[1]} filter={vc[2]})")

    train_ds = FaceDataset(tr_p, tr_l, transform_train)
    val_ds   = FaceDataset(va_p, va_l, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)

    # Class weights with filter capped at 0.4
    total = len(tr_l)
    auto_w = [total / (len(CLASSES) * tc[i]) for i in range(len(CLASSES))]
    auto_w[2] = min(auto_w[2], 0.4)
    class_weights = torch.tensor(auto_w, dtype=torch.float).to(device)
    print(f"Class weights: real={class_weights[0]:.3f}  fake={class_weights[1]:.3f}  filter={class_weights[2]:.3f}")

    model     = DualBranchModel(num_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()

            if random.random() < 0.5:
                imgs_m, ya, yb, lam = mixup_batch(imgs, labels, MIXUP_ALPHA)
                loss = mixup_loss(criterion, model(imgs_m), ya, yb, lam)
            else:
                loss = criterion(model(imgs), labels)

            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
                trues.extend(labels.tolist())

        acc      = accuracy_score(trues, preds)
        f1_macro = f1_score(trues, preds, average='macro')
        f1_per   = f1_score(trues, preds, average=None)
        avg_loss = total_loss / len(train_ds)

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  Acc={acc:.4f}  "
              f"F1_macro={f1_macro:.4f}  F1=[real={f1_per[0]:.3f} fake={f1_per[1]:.3f} filter={f1_per[2]:.3f}]")
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1_macro:.4f}",
                     f"{f1_per[0]:.4f}", f"{f1_per[1]:.4f}", f"{f1_per[2]:.4f}"])

        if f1_macro > best_f1:
            best_f1 = f1_macro
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  -> Saved (F1_macro={best_f1:.4f})")

    print(f"\nBest F1_macro={best_f1:.4f}  Weights: {WEIGHTS_PATH}")

    print("\n--- Val Set Classification Report ---")
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
            trues.extend(labels.tolist())
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(str(BASE / "results"), exist_ok=True)
    pd.DataFrame(rows, columns=["epoch","loss","acc","f1_macro","f1_real","f1_fake","f1_filter"]) \
      .to_csv(str(BASE / "results" / "v4_val_results.csv"), index=False)
    print(f"Results -> results/v4_val_results.csv")
