"""
3-class + FFT branch v3: loads from clean_paths.txt (post-cleaning data).

Changes from v2:
  - All datasets loaded via clean_paths.txt instead of directory scan
  - Class weights in CrossEntropyLoss to handle real/fake/filter imbalance

python AIGuard/train_3class_ffhq_v3.py
"""
import os, random
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from PIL import Image
import pandas as pd

BASE         = r"C:\My_Project\AIGC"
WEIGHTS_PATH = os.path.join(BASE, "shufflenet_v2_3class_ffhq_v3.pth")

CLASSES    = ["real", "fake", "filter"]
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
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, self.labels[idx]


def load_clean_txt(txt_path, label):
    if not os.path.exists(txt_path):
        print(f"  Warning: {txt_path} not found, skipping")
        return [], []
    paths = [p for p in Path(txt_path).read_text(encoding="utf-8").splitlines() if p]
    return paths, [label] * len(paths)


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


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    rp, rl = load_clean_txt(os.path.join(BASE, "AIGuard", "real",   "clean_output", "clean_paths.txt"), 0)
    fp, fl = load_clean_txt(os.path.join(BASE, "AIGuard", "fake",   "clean_output", "clean_paths.txt"), 1)

    flt_p,  flt_l  = load_clean_txt(os.path.join(BASE, "filter_data",                "clean_output", "clean_paths.txt"), 2)
    ffhq_p, ffhq_l = load_clean_txt(os.path.join(BASE, "FFHQ_four_process",          "clean_output", "clean_paths.txt"), 2)
    mgv_p,  mgv_l  = load_clean_txt(os.path.join(BASE, "FFHQ_megvii_four_process",   "clean_output", "clean_paths.txt"), 2)
    ali_p,  ali_l  = load_clean_txt(os.path.join(BASE, "FFHQ_ali_process",           "clean_output", "clean_paths.txt"), 2)

    filter_paths  = flt_p + ffhq_p + mgv_p + ali_p
    filter_labels = flt_l + ffhq_l + mgv_l + ali_l

    print(f"Real:   {len(rp)}")
    print(f"Fake:   {len(fp)}")
    print(f"Filter: {len(filter_paths)}"
          f"  (self={len(flt_p)}, ffhq={len(ffhq_p)}, megvii={len(mgv_p)}, ali={len(ali_p)})")

    all_paths  = rp + fp + filter_paths
    all_labels = rl + fl + filter_labels

    # 80/10/10 split: trainval → train+val, then split trainval into 80/10
    tr_p, te_p, tr_l, te_l = train_test_split(
        all_paths, all_labels, test_size=0.10, random_state=42, stratify=all_labels)
    tr_p, va_p, tr_l, va_l = train_test_split(
        tr_p, tr_l, test_size=0.111, random_state=42, stratify=tr_l)  # 0.111 * 0.9 ≈ 0.10

    train_ds = FaceDataset(tr_p, tr_l, transform_train)
    val_ds   = FaceDataset(va_p, va_l, transform_val)
    test_ds  = FaceDataset(te_p, te_l, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}  Test: {len(test_ds)}")

    # Class weights to handle imbalance
    count = Counter(all_labels)
    total = len(all_labels)
    class_weights = torch.tensor(
        [total / (len(CLASSES) * count[i]) for i in range(len(CLASSES))],
        dtype=torch.float).to(device)
    print(f"Class weights: real={class_weights[0]:.3f}  fake={class_weights[1]:.3f}  filter={class_weights[2]:.3f}")

    model     = DualBranchModel(num_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        model.eval()
        preds, trues = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
                trues.extend(labels.tolist())

        acc       = accuracy_score(trues, preds)
        f1_macro  = f1_score(trues, preds, average='macro')
        f1_filter = f1_score(trues, preds, average=None)[2]
        avg_loss  = total_loss / len(train_ds)

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  "
              f"Acc={acc:.4f}  F1_macro={f1_macro:.4f}  F1_filter={f1_filter:.4f}")
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1_macro:.4f}", f"{f1_filter:.4f}"])

        if f1_filter > best_f1:
            best_f1 = f1_filter
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  -> Saved (filter F1={best_f1:.4f})")

    print(f"\nBest filter F1={best_f1:.4f}  Weights: {WEIGHTS_PATH}")

    # Final evaluation on held-out test set
    print("\n--- Classification Report (TEST SET) ---")
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for imgs, labels in test_loader:
            preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
            trues.extend(labels.tolist())
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
    pd.DataFrame(rows, columns=["epoch", "loss", "acc", "f1_macro", "f1_filter"]) \
      .to_csv(os.path.join(BASE, "results", "3class_ffhq_v3_val_results.csv"), index=False)
    print(f"\nResults -> results/3class_ffhq_v3_val_results.csv")
