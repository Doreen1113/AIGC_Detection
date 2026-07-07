"""
Artifact level classifier v3: multi-task regression.

Instead of 12-class CrossEntropy, use two heads:
  - type_head : 4-class CE (eye_enlarging / face_reshaping / smoothing / whitening)
  - level_head: regression (predict level as continuous 0.0/0.5/1.0 = 30/60/90)
  Loss = CE(type) + MSE(level)

The level head learns ordinal relationships (30 < 60 < 90) explicitly,
which plain CrossEntropy ignores.

Output: artifact_level_classifier_v3.pth

    python AIGuard/train_level_classifier_v3.py
"""
import os, time
import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, classification_report
from PIL import Image
import numpy as np

BASE      = r"C:\My_Project\AIGC"
ALI_DIR   = os.path.join(BASE, "FFHQ_ali_process")
SAVE_PATH = os.path.join(BASE, "artifact_level_classifier_v3.pth")

# folder → (class_12_idx, type_idx, level_norm)
# level_norm: 30→0.0, 60→0.5, 90→1.0
ALI_MAP = {
    "EyeEnlarging_30": (0,  0, 0.0),
    "EyeEnlarging_60": (1,  0, 0.5),
    "EyeEnlarging_90": (2,  0, 1.0),
    "FaceLifting_30":  (3,  1, 0.0),
    "FaceLifting_60":  (4,  1, 0.5),
    "FaceLifting_90":  (5,  1, 1.0),
    "Smoothing_30":    (6,  2, 0.0),
    "Smoothing_60":    (7,  2, 0.5),
    "Smoothing_90":    (8,  2, 1.0),
    "Whitening_30":    (9,  3, 0.0),
    "Whitening_60":    (10, 3, 0.5),
    "Whitening_90":    (11, 3, 1.0),
}
NUM_TYPES   = 4
NUM_CLASSES = 12
CLASS_NAMES = [k for k in sorted(ALI_MAP, key=lambda x: ALI_MAP[x][0])]

EPOCHS     = 30
BATCH_SIZE = 64
LR         = 1e-3
VAL_RATIO  = 0.2


class LevelDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        # labels: list of (class_12, type_idx, level_norm)
        self.paths     = paths
        self.labels    = labels
        self.transform = transform

    def __len__(self): return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        cls12, type_idx, level_norm = self.labels[idx]
        return img, cls12, type_idx, level_norm


def collect_data(root):
    paths, labels = [], []
    for folder, (cls12, type_idx, level_norm) in ALI_MAP.items():
        folder_path = os.path.join(root, folder)
        if not os.path.isdir(folder_path):
            print(f"  [WARN] missing: {folder_path}")
            continue
        for sub in os.listdir(folder_path):
            sub_path = os.path.join(folder_path, sub)
            if not os.path.isdir(sub_path): continue
            for f in os.listdir(sub_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    paths.append(os.path.join(sub_path, f))
                    labels.append((cls12, type_idx, level_norm))
    return paths, labels


class MultiTaskModel(nn.Module):
    def __init__(self):
        super().__init__()
        backbone = tv_models.shufflenet_v2_x1_0(
            weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        backbone.fc = nn.Identity()
        self.backbone   = backbone
        self.type_head  = nn.Linear(1024, NUM_TYPES)
        self.level_head = nn.Linear(1024, 1)

    def forward(self, x):
        feat = self.backbone(x)
        return self.type_head(feat), self.level_head(feat).squeeze(1)


transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


def preds_to_class12(type_pred_idx, level_pred_raw):
    """Convert (type_idx, level regression output) → 12-class index."""
    # clamp and round level to nearest 0 / 0.5 / 1.0
    level_clamped = np.clip(level_pred_raw, 0.0, 1.0)
    level_idx = np.round(level_clamped * 2).astype(int)   # 0→0, 0.5→1, 1→2
    level_idx = np.clip(level_idx, 0, 2)
    return type_pred_idx * 3 + level_idx


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    paths, labels = collect_data(ALI_DIR)
    print(f"Total images: {len(paths)}  Classes: {NUM_CLASSES}")

    from collections import Counter
    cls12_list = [l[0] for l in labels]
    cnt = Counter(cls12_list)
    for name, (idx, *_) in sorted(ALI_MAP.items(), key=lambda x: x[1][0]):
        print(f"  {name:20s}: {cnt[idx]}")

    tr_p, va_p, tr_l, va_l = train_test_split(
        paths, labels, test_size=VAL_RATIO,
        stratify=cls12_list, random_state=42)
    print(f"Train: {len(tr_p)}  Val: {len(va_p)}")

    train_loader = DataLoader(LevelDataset(tr_p, tr_l, transform_train),
                              batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(LevelDataset(va_p, va_l, transform_val),
                              batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)

    model     = MultiTaskModel().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    ce_loss   = nn.CrossEntropyLoss()
    mse_loss  = nn.MSELoss()

    best_f1 = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        total_loss = 0.0
        for imgs, cls12, type_lbl, level_lbl in train_loader:
            imgs      = imgs.to(device)
            type_lbl  = type_lbl.to(device)
            level_lbl = level_lbl.float().to(device)

            optimizer.zero_grad()
            type_out, level_out = model(imgs)
            loss = ce_loss(type_out, type_lbl) + mse_loss(level_out, level_lbl)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        model.eval()
        preds12, trues12 = [], []
        with torch.no_grad():
            for imgs, cls12, type_lbl, level_lbl in val_loader:
                type_out, level_out = model(imgs.to(device))
                type_idx   = type_out.argmax(1).cpu().numpy()
                level_raw  = level_out.cpu().numpy()
                pred12     = preds_to_class12(type_idx, level_raw)
                preds12.extend(pred12.tolist())
                trues12.extend(cls12.tolist())

        f1  = f1_score(trues12, preds12, average='macro')
        acc = (np.array(preds12) == np.array(trues12)).mean()
        print(f"[{epoch:02d}/{EPOCHS}] loss={total_loss/len(tr_p):.4f}  "
              f"Acc={acc:.4f}  F1={f1:.4f}  ({time.time()-t0:.1f}s)")

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  → Saved (F1={best_f1:.4f})")

    print(f"\nBest F1={best_f1:.4f}  Weights: {SAVE_PATH}")

    print("\n--- Per-class report (val) ---")
    model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
    model.eval()
    preds12, trues12 = [], []
    with torch.no_grad():
        for imgs, cls12, type_lbl, level_lbl in val_loader:
            type_out, level_out = model(imgs.to(device))
            type_idx  = type_out.argmax(1).cpu().numpy()
            level_raw = level_out.cpu().numpy()
            pred12    = preds_to_class12(type_idx, level_raw)
            preds12.extend(pred12.tolist())
            trues12.extend(cls12.tolist())
    print(classification_report(trues12, preds12, target_names=CLASS_NAMES, digits=4))
