"""
3-class + FFT branch, with RetouchingFFHQ filter images added to filter class.

Filter class:
  - filter_data/      : 32K self-generated (smoothing/whitening/eye/face)
  - FFHQ_four_process : 10K real beauty-app filtered images

python AIGuard/train_3class_ffhq.py
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tv_models
import os
import random
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from PIL import Image
import pandas as pd

BASE            = r"C:\My_Project\AIGC"
REAL_DIR        = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR        = os.path.join(BASE, "AIGuard", "fake")
FILTER_DIR      = os.path.join(BASE, "filter_data")
FFHQ_FILTER_DIR = os.path.join(BASE, "FFHQ_four_process",
                                "Whitening_Smoothing_FaceLifting_EyeEnlarging")
WEIGHTS_PATH    = os.path.join(BASE, "shufflenet_v2_3class_ffhq.pth")

CLASSES    = ["real", "fake", "filter"]
N_PER_SUB  = 6000
EPOCHS     = 15
BATCH_SIZE = 64

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.RandomGrayscale(p=0.05),
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
        self.paths   = paths
        self.labels  = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


def collect_from_subfolders(root, label, max_per_sub=None):
    paths, labels = [], []
    for sub in sorted(os.listdir(root)):
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue
        files = [f for f in os.listdir(sub_path)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(42)
        random.shuffle(files)
        selected = files[:max_per_sub] if max_per_sub else files
        for f in selected:
            paths.append(os.path.join(sub_path, f))
            labels.append(label)
    return paths, labels


def collect_from_flat(root, label):
    """filter_data structure: root/type_name/images"""
    paths, labels = [], []
    if not os.path.exists(root):
        return paths, labels
    for sub in os.listdir(root):
        sub_path = os.path.join(root, sub)
        if os.path.isdir(sub_path):
            for f in os.listdir(sub_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    paths.append(os.path.join(sub_path, f))
                    labels.append(label)
    return paths, labels


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, out_dim), nn.ReLU(),
        )

    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        mag = torch.log(torch.abs(fft) + 1e-8)
        return self.net(mag)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3):
        super().__init__()
        backbone = tv_models.shufflenet_v2_x1_0(
            weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        backbone.fc = nn.Identity()
        self.spatial_branch = backbone
        self.fft_branch     = FFTBranch(out_dim=256)
        self.classifier     = nn.Sequential(
            nn.Linear(1024 + 256, 512), nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        return self.classifier(
            torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    # ── collect paths ──
    real_paths, real_labels = collect_from_subfolders(REAL_DIR, 0, N_PER_SUB)
    fake_paths, fake_labels = collect_from_subfolders(FAKE_DIR, 1, N_PER_SUB)

    # filter: self-generated (32K) + RetouchingFFHQ (10K)
    flt_paths,  flt_labels  = collect_from_flat(FILTER_DIR, 2)
    ffhq_paths, ffhq_labels = collect_from_subfolders(FFHQ_FILTER_DIR, 2)

    filter_paths  = flt_paths  + ffhq_paths
    filter_labels = flt_labels + ffhq_labels

    print(f"Real:   {len(real_paths)}")
    print(f"Fake:   {len(fake_paths)}")
    print(f"Filter: {len(filter_paths)}  "
          f"(self={len(flt_paths)}, ffhq={len(ffhq_paths)})")

    all_paths  = real_paths  + fake_paths  + filter_paths
    all_labels = real_labels + fake_labels + filter_labels

    # ── train/val split ──
    tr_paths, va_paths, tr_labels, va_labels = train_test_split(
        all_paths, all_labels, test_size=0.1, random_state=42,
        stratify=all_labels)

    train_ds = FaceDataset(tr_paths, tr_labels, transform_train)
    val_ds   = FaceDataset(va_paths, va_labels, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)

    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}")

    # ── model ──
    model     = DualBranchModel(num_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_filter_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        # ── eval ──
        model.eval()
        all_preds, all_true = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                preds = model(imgs.to(device)).argmax(dim=1)
                all_preds.extend(preds.cpu().tolist())
                all_true.extend(labels.tolist())

        from sklearn.metrics import f1_score, accuracy_score
        acc       = accuracy_score(all_true, all_preds)
        f1_macro  = f1_score(all_true, all_preds, average='macro')
        f1_filter = f1_score(all_true, all_preds, average=None)[2]
        avg_loss  = total_loss / len(train_ds)

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  "
              f"Acc={acc:.4f}  F1_macro={f1_macro:.4f}  F1_filter={f1_filter:.4f}")
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}",
                     f"{f1_macro:.4f}", f"{f1_filter:.4f}"])

        if f1_filter > best_filter_f1:
            best_filter_f1 = f1_filter
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  → Saved (filter F1={best_filter_f1:.4f})")

    print(f"\nBest filter F1={best_filter_f1:.4f}  Weights: {WEIGHTS_PATH}")

    # ── final report ──
    print("\n--- Classification Report (val) ---")
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    all_preds, all_true = [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            preds = model(imgs.to(device)).argmax(dim=1)
            all_preds.extend(preds.cpu().tolist())
            all_true.extend(labels.tolist())
    print(classification_report(all_true, all_preds,
                                target_names=CLASSES, digits=4))
    print("Confusion matrix:")
    print(confusion_matrix(all_true, all_preds))

    # ── save CSV ──
    os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
    pd.DataFrame(rows, columns=["epoch","loss","acc","f1_macro","f1_filter"])\
      .to_csv(os.path.join(BASE, "results", "3class_ffhq_val_results.csv"), index=False)
    print(f"\nResults → results/3class_ffhq_val_results.csv")
