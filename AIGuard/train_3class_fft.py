"""
3-class + FFT branch: ShuffleNetV2 (spatial) + FFT magnitude (frequency)
Real / Fake / Filter-processed

python AIGuard/train_3class_fft.py
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

BASE         = r"C:\My_Project\AIGC"
REAL_DIR     = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR     = os.path.join(BASE, "AIGuard", "fake")
FILTER_DIR   = os.path.join(BASE, "filter_data")
WEIGHTS_PATH = os.path.join(BASE, "shufflenet_v2_3class_fft.pth")

CLASSES    = ["real", "fake", "filter"]
N_PER_SUB  = 6000
EPOCHS     = 15
BATCH_SIZE = 64   # FFT branch 多吃一點記憶體，batch 稍微降低

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


# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────
class FaceDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths = paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx]


def collect_from_subfolders(root, label, max_per_sub):
    paths, labels = [], []
    for sub in os.listdir(root):
        sub_path = os.path.join(root, sub)
        if not os.path.isdir(sub_path):
            continue
        files = [f for f in os.listdir(sub_path)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(42)
        random.shuffle(files)
        for f in files[:max_per_sub]:
            paths.append(os.path.join(sub_path, f))
            labels.append(label)
    return paths, labels

def collect_from_flat(root, label):
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


# ──────────────────────────────────────────────
# Model: ShuffleNetV2 + FFT branch
# ──────────────────────────────────────────────
class FFTBranch(nn.Module):
    """Log-magnitude spectrum → lightweight CNN → 256-dim feature."""
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(4),           # 224 → 56
            nn.Conv2d(32, 64, 3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.MaxPool2d(2),           # 56 → 28
            nn.Conv2d(64, 128, 3, padding=1),
            nn.BatchNorm2d(128),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),   # → 4×4
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, out_dim),
            nn.ReLU(),
        )

    def forward(self, x):
        # x: (B, 3, 224, 224), normalized to ~[-1, 1]
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))   # zero-freq to center
        mag = torch.log(torch.abs(fft) + 1e-8)        # log magnitude
        return self.net(mag)


class DualBranchModel(nn.Module):
    """Spatial branch (ShuffleNetV2 1024-dim) + Frequency branch (FFT 256-dim)."""
    def __init__(self, num_classes=3):
        super().__init__()
        backbone = tv_models.shufflenet_v2_x1_0(
            weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        backbone.fc = nn.Identity()   # output 1024-dim spatial feature
        self.spatial_branch = backbone

        self.fft_branch = FFTBranch(out_dim=256)

        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        spatial = self.spatial_branch(x)      # (B, 1024)
        freq    = self.fft_branch(x)          # (B, 256)
        return self.classifier(torch.cat([spatial, freq], dim=1))


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
if __name__ == '__main__':
    real_paths,   real_labels   = collect_from_subfolders(REAL_DIR,  0, N_PER_SUB)
    fake_paths,   fake_labels   = collect_from_subfolders(FAKE_DIR,  1, N_PER_SUB)
    filter_paths, filter_labels = collect_from_flat(FILTER_DIR, 2)

    print(f"Real:   {len(real_paths)}")
    print(f"Fake:   {len(fake_paths)}")
    print(f"Filter: {len(filter_paths)}")

    if not filter_paths:
        print("[ERROR] filter_data/ is empty. Run generate_filter_dataset.py first.")
        exit(1)

    all_paths  = real_paths + fake_paths + filter_paths
    all_labels = real_labels + fake_labels + filter_labels

    train_paths, val_paths, train_labels, val_labels = train_test_split(
        all_paths, all_labels, test_size=0.2, stratify=all_labels, random_state=42
    )
    print(f"Train: {len(train_paths)} | Val: {len(val_paths)}\n")

    train_loader = DataLoader(
        FaceDataset(train_paths, train_labels, transform_train),
        batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        FaceDataset(val_paths, val_labels, transform_val),
        batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = DualBranchModel(num_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(EPOCHS):
        model.train()
        total_loss = 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"Epoch {epoch+1}/{EPOCHS} - Loss: {total_loss/len(train_loader):.4f}")

    torch.save(model.state_dict(), WEIGHTS_PATH)
    print(f"\nWeights saved to {WEIGHTS_PATH}")

    # validation
    model.eval()
    all_preds, all_true = [], []
    with torch.no_grad():
        for imgs, lbls in val_loader:
            imgs = imgs.to(device)
            preds = model(imgs).argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_true.extend(lbls.numpy())

    print("\n=== Validation Results ===")
    print(classification_report(all_true, all_preds, target_names=CLASSES))

    cm = confusion_matrix(all_true, all_preds)
    print("Confusion Matrix (rows=actual, cols=pred):")
    print(f"{'':12}" + "".join(f"{c:>10}" for c in CLASSES))
    for i, row in enumerate(cm):
        print(f"{CLASSES[i]:12}" + "".join(f"{v:>10}" for v in row))

    pd.DataFrame({"path": val_paths, "actual": all_true, "pred": all_preds})\
      .to_csv(os.path.join(BASE, "results", "3class_fft_val_results.csv"), index=False)
    print(f"\nSaved to results/3class_fft_val_results.csv")
