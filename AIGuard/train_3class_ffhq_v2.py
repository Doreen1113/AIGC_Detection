"""
3-class + FFT branch, Round 2: all RetouchingFFHQ sources added to filter class.

Filter class:
  - filter_data/            : 32K self-generated
  - FFHQ_four_process       : 10K (4-filter combined, standard)
  - FFHQ_megvii_four_process: 16.7K (4-filter combined, Megvii app)
  - FFHQ_ali_process        : 36K (single-filter per subfolder, Ali app)

python AIGuard/train_3class_ffhq_v2.py
"""
import torch
import torch.nn as nn
import torchvision.models as tv_models
import os, random
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from PIL import Image
import pandas as pd

BASE             = r"C:\My_Project\AIGC"
REAL_DIR         = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR         = os.path.join(BASE, "AIGuard", "fake")
FILTER_DIR       = os.path.join(BASE, "filter_data")
FFHQ_DIR         = os.path.join(BASE, "FFHQ_four_process",
                                 "Whitening_Smoothing_FaceLifting_EyeEnlarging")
MEGVII_DIR       = os.path.join(BASE, "FFHQ_megvii_four_process",
                                 "Whitening_Smoothing_FaceLifting_EyeEnlarging")
ALI_DIR          = os.path.join(BASE, "FFHQ_ali_process")
WEIGHTS_PATH     = os.path.join(BASE, "shufflenet_v2_3class_ffhq_v2.pth")

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
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, self.labels[idx]


def collect_subfolders(root, label, max_per_sub=None):
    """root/subfolder/images — one level of subfolders."""
    paths, labels = [], []
    for sub in sorted(os.listdir(root)):
        sp = os.path.join(root, sub)
        if not os.path.isdir(sp): continue
        files = [f for f in os.listdir(sp)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(42); random.shuffle(files)
        for f in (files[:max_per_sub] if max_per_sub else files):
            paths.append(os.path.join(sp, f)); labels.append(label)
    return paths, labels


def collect_flat_types(root, label):
    """filter_data structure: root/type_name/images."""
    paths, labels = [], []
    for sub in os.listdir(root):
        sp = os.path.join(root, sub)
        if os.path.isdir(sp):
            for f in os.listdir(sp):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    paths.append(os.path.join(sp, f)); labels.append(label)
    return paths, labels


def collect_ali(root, label):
    """ali structure: root/FilterType_Level/subfolder/images (3 levels)."""
    paths, labels = [], []
    for type_level in os.listdir(root):
        tl_path = os.path.join(root, type_level)
        if not os.path.isdir(tl_path): continue
        for sub in os.listdir(tl_path):
            sp = os.path.join(tl_path, sub)
            if os.path.isdir(sp):
                for f in os.listdir(sp):
                    if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                        paths.append(os.path.join(sp, f)); labels.append(label)
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


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    rp, rl = collect_subfolders(REAL_DIR, 0, N_PER_SUB)
    fp, fl = collect_subfolders(FAKE_DIR, 1, N_PER_SUB)

    flt_p,  flt_l  = collect_flat_types(FILTER_DIR, 2)
    ffhq_p, ffhq_l = collect_subfolders(FFHQ_DIR, 2)
    mgv_p,  mgv_l  = collect_subfolders(MEGVII_DIR, 2)
    ali_p,  ali_l  = collect_ali(ALI_DIR, 2)

    filter_paths  = flt_p + ffhq_p + mgv_p + ali_p
    filter_labels = flt_l + ffhq_l + mgv_l + ali_l

    print(f"Real:   {len(rp)}")
    print(f"Fake:   {len(fp)}")
    print(f"Filter: {len(filter_paths)}"
          f"  (self={len(flt_p)}, ffhq={len(ffhq_p)}, megvii={len(mgv_p)}, ali={len(ali_p)})")

    all_paths  = rp + fp + filter_paths
    all_labels = rl + fl + filter_labels

    tr_p, va_p, tr_l, va_l = train_test_split(
        all_paths, all_labels, test_size=0.1, random_state=42, stratify=all_labels)

    train_ds = FaceDataset(tr_p, tr_l, transform_train)
    val_ds   = FaceDataset(va_p, va_l, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}")

    model     = DualBranchModel(num_classes=3).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

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
            print(f"  → Saved (filter F1={best_f1:.4f})")

    print(f"\nBest filter F1={best_f1:.4f}  Weights: {WEIGHTS_PATH}")

    print("\n--- Classification Report (val) ---")
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
            trues.extend(labels.tolist())
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(os.path.join(BASE, "results"), exist_ok=True)
    pd.DataFrame(rows, columns=["epoch","loss","acc","f1_macro","f1_filter"])\
      .to_csv(os.path.join(BASE, "results", "3class_ffhq_v2_val_results.csv"), index=False)
    print(f"\nResults → results/3class_ffhq_v2_val_results.csv")
