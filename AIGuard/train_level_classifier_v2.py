"""
Artifact level classifier v2: region-crop for geometric filters.

EyeEnlarging  → crop eye band (y=50-115, x=20-204)
FaceLifting   → crop cheek+jaw (y=100-224, x=10-214)
Smoothing / Whitening → full image (texture/color, global info needed)

12 classes = 4 filter types × 3 levels (30/slight, 60/medium, 90/heavy)
Data: FFHQ_ali_process (~36K images, ~3K per class)

Output: artifact_level_classifier_v2.pth

    python AIGuard/train_level_classifier_v2.py
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
SAVE_PATH = os.path.join(BASE, "artifact_level_classifier_v2.pth")

ALI_MAP = {
    "EyeEnlarging_30": (0,  "eye_enlarging",  30, "slight"),
    "EyeEnlarging_60": (1,  "eye_enlarging",  60, "medium"),
    "EyeEnlarging_90": (2,  "eye_enlarging",  90, "heavy"),
    "FaceLifting_30":  (3,  "face_reshaping", 30, "slight"),
    "FaceLifting_60":  (4,  "face_reshaping", 60, "medium"),
    "FaceLifting_90":  (5,  "face_reshaping", 90, "heavy"),
    "Smoothing_30":    (6,  "smoothing",       30, "slight"),
    "Smoothing_60":    (7,  "smoothing",       60, "medium"),
    "Smoothing_90":    (8,  "smoothing",       90, "heavy"),
    "Whitening_30":    (9,  "whitening",       30, "slight"),
    "Whitening_60":    (10, "whitening",       60, "medium"),
    "Whitening_90":    (11, "whitening",       90, "heavy"),
}
NUM_CLASSES = 12
CLASS_NAMES = [k for k in sorted(ALI_MAP, key=lambda x: ALI_MAP[x][0])]

EPOCHS     = 30
BATCH_SIZE = 64
LR         = 1e-3
VAL_RATIO  = 0.2

# Region crops applied on 224×224 image (y0, y1, x0, x1)
# PIL crop uses (left, upper, right, lower) = (x0, y0, x1, y1)
EYE_REGION  = (50, 115,  20, 204)   # both eyes band
CHEEK_JAW   = (100, 224, 10, 214)   # cheek + jaw

def region_for_class(cls_idx):
    if cls_idx in (0, 1, 2):    # EyeEnlarging
        return EYE_REGION
    elif cls_idx in (3, 4, 5):  # FaceLifting
        return CHEEK_JAW
    return None                  # full image


class LevelDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths   = paths
        self.labels  = labels
        self.transform = transform

    def __len__(self): return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        img = img.resize((224, 224), Image.BILINEAR)

        region = region_for_class(self.labels[idx])
        if region is not None:
            y0, y1, x0, x1 = region
            img = img.crop((x0, y0, x1, y1))   # PIL: (left, upper, right, lower)

        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


def collect_data(root):
    paths, labels = [], []
    for folder, (cls_idx, *_) in ALI_MAP.items():
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
                    labels.append(cls_idx)
    return paths, labels


def build_model():
    m = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    m.fc = nn.Linear(m.fc.in_features, NUM_CLASSES)
    return m


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


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    paths, labels = collect_data(ALI_DIR)
    print(f"Total images: {len(paths)}  Classes: {NUM_CLASSES}")

    from collections import Counter
    cnt = Counter(labels)
    for name, (idx, *_) in sorted(ALI_MAP.items(), key=lambda x: x[1][0]):
        region = region_for_class(idx)
        tag = "eye_crop" if idx < 3 else ("jaw_crop" if idx < 6 else "full")
        print(f"  {name:20s}: {cnt[idx]:4d}  [{tag}]")

    tr_p, va_p, tr_l, va_l = train_test_split(
        paths, labels, test_size=VAL_RATIO, stratify=labels, random_state=42)
    print(f"Train: {len(tr_p)}  Val: {len(va_p)}")

    train_loader = DataLoader(LevelDataset(tr_p, tr_l, transform_train),
                              batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(LevelDataset(va_p, va_l, transform_val),
                              batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)

    model     = build_model().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_f1 = 0.0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        total_loss = 0.0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), lbls)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for imgs, lbls in val_loader:
                preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
                trues.extend(lbls.tolist())

        f1  = f1_score(trues, preds, average='macro')
        acc = (np.array(preds) == np.array(trues)).mean()
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
    preds, trues = [], []
    with torch.no_grad():
        for imgs, lbls in val_loader:
            preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
            trues.extend(lbls.tolist())
    print(classification_report(trues, preds, target_names=CLASS_NAMES, digits=4))
