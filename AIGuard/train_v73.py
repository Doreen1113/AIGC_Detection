"""
v7.3: TriBranch = DualBranch (spatial 1024 + FFT 256) + EyeROI 128.

EyeROI branch:
  - Fixed crop from 224x224 face: y=[65:125], x=[20:204] (60x184 px eye strip)
  - Resize to 64x128
  - Small CNN -> 128-dim feature
  - Captures warp artifacts that are invisible at full-image scale

Init: spatial + FFT from v6, EyeROI random init.
Use v72 filter split (includes LFW eye_enlarging).

python AIGuard/train_v73.py
"""
import os, random, numpy as np
from pathlib import Path
from collections import Counter

import torch, torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import f1_score, accuracy_score, classification_report, confusion_matrix
from PIL import Image
import pandas as pd

BASE         = Path(r"C:\My_Project\AIGC")
SPLITS       = BASE / "splits"
INIT_WEIGHTS = str(BASE / "shufflenet_v2_3class_v6.pth")
WEIGHTS_PATH = str(BASE / "shufflenet_v2_3class_v73.pth")

CLASSES     = ["real", "fake", "filter"]
EPOCHS      = 15
BATCH_SIZE  = 256
MIXUP_ALPHA = 0.2
LR          = 5e-4   # higher than v7/v7.1 because EyeROI branch is randomly initialised

# Eye strip region (in 224x224 face image)
EYE_Y0, EYE_Y1 = 65, 125
EYE_X0, EYE_X1 = 20, 204
EYE_H, EYE_W   = 64, 128

transform_color = transforms.Compose([
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.RandomGrayscale(p=0.05),
])
to_tensor_norm = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])
eye_resize = transforms.Resize((EYE_H, EYE_W))


class FaceDatasetWithEye(Dataset):
    def __init__(self, paths, labels, augment=False):
        self.paths   = paths
        self.labels  = labels
        self.augment = augment

    def __len__(self): return len(self.paths)

    def __getitem__(self, idx):
        # Resize+CenterCrop gives consistent face positioning for eye crop accuracy
        pil = Image.open(self.paths[idx]).convert("RGB")
        w, h = pil.size
        short = min(w, h)
        scale = 256 / short
        pil = pil.resize((round(w*scale), round(h*scale)), Image.BILINEAR)
        # CenterCrop to 224×224
        cw, ch = pil.size
        left = (cw - 224) // 2
        top  = (ch - 224) // 2
        pil = pil.crop((left, top, left+224, top+224))

        if self.augment:
            if random.random() < 0.5:
                pil = pil.transpose(Image.FLIP_LEFT_RIGHT)
            pil = transform_color(pil)

        # Full image tensor
        full = to_tensor_norm(pil)

        # Eye strip crop -> 64x128
        eye_pil = pil.crop((EYE_X0, EYE_Y0, EYE_X1, EYE_Y1))
        eye_pil = eye_resize(eye_pil)
        eye = to_tensor_norm(eye_pil)

        return full, eye, self.labels[idx]


def load_split(txt_path):
    paths, labels = [], []
    for line in Path(txt_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t"): continue
        parts = line.split("\t")
        if len(parts) >= 2:
            paths.append(parts[0]); labels.append(int(parts[1]))
    return paths, labels


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2,-1))
        return self.net(torch.log(torch.abs(fft)+1e-8))


class EyeROIBranch(nn.Module):
    """Small CNN on 64x128 eye strip -> 128-dim."""
    def __init__(self, out_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d((4,4)),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        return self.net(x)


class TriBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch     = FFTBranch(256)
        self.eye_branch     = EyeROIBranch(128)
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256 + 128, 512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 3))

    def forward(self, full, eye):
        feat = torch.cat([
            self.spatial_branch(full),
            self.fft_branch(full),
            self.eye_branch(eye),
        ], dim=1)
        return self.classifier(feat)

    def load_dual_branch_weights(self, ckpt_path, device):
        """Load spatial + FFT weights from v6 DualBranch, leave eye_branch random."""
        old = torch.load(ckpt_path, map_location=device)
        new = self.state_dict()
        # classifier input dim changed (1280→1408), exclude it + eye_branch
        loaded = {k: v for k, v in old.items()
                  if k in new
                  and not k.startswith("eye_branch")
                  and not k.startswith("classifier")}
        new.update(loaded)
        self.load_state_dict(new)
        n_eye = sum(1 for k in new if k.startswith("eye_branch"))
        n_cls = sum(1 for k in new if k.startswith("classifier"))
        print(f"  Loaded {len(loaded)}/{len(new)} params from {ckpt_path}")
        print(f"  Randomly initialised: eye_branch ({n_eye} tensors) + classifier ({n_cls} tensors)")


def mixup_batch(x, y, alpha=0.2):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam*x + (1-lam)*x[idx], y, y[idx], lam

def mixup_loss(criterion, logits, ya, yb, lam):
    return lam*criterion(logits, ya) + (1-lam)*criterion(logits, yb)


def collate_fn(batch):
    fulls, eyes, labels = zip(*batch)
    return torch.stack(fulls), torch.stack(eyes), torch.tensor(labels)


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    tr_rf_p, tr_rf_l = load_split(SPLITS / "v6_train_real_fake.txt")
    va_rf_p, va_rf_l = load_split(SPLITS / "v6_val_real_fake.txt")
    tr_ft_p, tr_ft_l = load_split(SPLITS / "v72_train_filter.txt")
    va_ft_p, va_ft_l = load_split(SPLITS / "val_filter.txt")

    tr_p = tr_rf_p + tr_ft_p;  tr_l = tr_rf_l + tr_ft_l
    va_p = va_rf_p + va_ft_p;  va_l = va_rf_l + va_ft_l

    tc = Counter(tr_l); vc = Counter(va_l)
    print(f"Train: {len(tr_p)}  real={tc[0]} fake={tc[1]} filter={tc[2]}")
    print(f"Val  : {len(va_p)}  real={vc[0]} fake={vc[1]} filter={vc[2]}")

    train_ds = FaceDatasetWithEye(tr_p, tr_l, augment=True)
    val_ds   = FaceDatasetWithEye(va_p, va_l, augment=False)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=8, pin_memory=True, collate_fn=collate_fn)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=8, pin_memory=True, collate_fn=collate_fn)

    total  = len(tr_l)
    auto_w = [total / (len(CLASSES) * tc[i]) for i in range(3)]
    auto_w[2] = min(auto_w[2], 0.4)
    class_weights = torch.tensor(auto_w, dtype=torch.float).to(device)
    print(f"Class weights: real={class_weights[0]:.3f}  fake={class_weights[1]:.3f}  filter={class_weights[2]:.3f}")

    model = TriBranchModel().to(device)
    model.load_dual_branch_weights(INIT_WEIGHTS, device)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss(weight=class_weights, label_smoothing=0.1)

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train(); total_loss = 0.0
        for full, eye, labels in train_loader:
            full, eye, labels = full.to(device), eye.to(device), labels.to(device)
            optimizer.zero_grad()
            if random.random() < 0.5:
                full_m, ya, yb, lam = mixup_batch(full, labels, MIXUP_ALPHA)
                eye_m = lam * eye + (1 - lam) * eye[torch.randperm(eye.size(0), device=device)]
                loss = mixup_loss(criterion, model(full_m, eye_m), ya, yb, lam)
            else:
                loss = criterion(model(full, eye), labels)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * full.size(0)
        scheduler.step()

        model.eval(); preds, trues = [], []
        with torch.no_grad():
            for full, eye, labels in val_loader:
                preds.extend(model(full.to(device), eye.to(device)).argmax(1).cpu().tolist())
                trues.extend(labels.tolist())

        acc = accuracy_score(trues, preds)
        f1  = f1_score(trues, preds, average="macro")
        f1p = f1_score(trues, preds, average=None)
        avg_loss = total_loss / len(train_ds)

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  Acc={acc:.4f}  "
              f"F1={f1:.4f}  [real={f1p[0]:.3f} fake={f1p[1]:.3f} filter={f1p[2]:.3f}]")
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1:.4f}",
                     f"{f1p[0]:.4f}", f"{f1p[1]:.4f}", f"{f1p[2]:.4f}"])

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  -> Saved (F1={best_f1:.4f})")

    print(f"\nBest F1={best_f1:.4f}  Weights: {WEIGHTS_PATH}")

    print("\n--- Val Classification Report ---")
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval(); preds, trues = [], []
    with torch.no_grad():
        for full, eye, labels in val_loader:
            preds.extend(model(full.to(device), eye.to(device)).argmax(1).cpu().tolist())
            trues.extend(labels.tolist())
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(str(BASE / "results"), exist_ok=True)
    pd.DataFrame(rows, columns=["epoch","loss","acc","f1_macro","f1_real","f1_fake","f1_filter"]) \
      .to_csv(str(BASE / "results/v73_val_results.csv"), index=False)
    print("Results -> results/v73_val_results.csv")
