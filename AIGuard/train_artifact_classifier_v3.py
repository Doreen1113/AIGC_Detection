"""
4-class artifact type classifier v3: loads from clean_paths.txt.
Classes: eye_enlarging / face_reshaping / smoothing / whitening  (alphabetical)
Data   : filter_data/clean_output/clean_paths.txt  (~25K post-cleaning)
Split  : 80/10/10 train/val/test

python AIGuard/train_artifact_classifier_v3.py
"""
import os, time, csv
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, classification_report, confusion_matrix
import numpy as np

BASE        = r"C:\My_Project\AIGC"
CLEAN_TXT   = os.path.join(BASE, "filter_data", "clean_output", "clean_paths.txt")
SAVE_PATH   = os.path.join(BASE, "artifact_classifier_v3.pth")
RESULTS_CSV = os.path.join(BASE, "results", "artifact_classifier_v3_results.csv")

EPOCHS     = 15
BATCH_SIZE = 64
LR         = 1e-3
NUM_CLASSES = 4
CLASSES     = ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]  # alphabetical
CLASS_MAP   = {c: i for i, c in enumerate(CLASSES)}

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


class ArtifactDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        from PIL import Image
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, self.labels[idx]


def build_model():
    model = tv_models.shufflenet_v2_x1_0(
        weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    return model


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            preds = model(imgs.to(device)).argmax(1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    acc  = (all_preds == all_labels).mean()
    f1   = f1_score(all_labels, all_preds, average='macro')
    prec = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    rec  = recall_score(all_labels, all_preds, average='macro', zero_division=0)
    return acc, f1, prec, rec


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

    raw_paths = [p for p in Path(CLEAN_TXT).read_text(encoding="utf-8").splitlines() if p]
    paths, labels = [], []
    skip = 0
    for p in raw_paths:
        cls = Path(p).parent.name.lower()
        if cls in CLASS_MAP:
            paths.append(p)
            labels.append(CLASS_MAP[cls])
        else:
            skip += 1
    if skip:
        print(f"  Skipped {skip} paths with unknown class")

    from collections import Counter
    print(f"Total: {len(paths)}")
    for c, i in CLASS_MAP.items():
        print(f"  {c}: {Counter(labels)[i]}")

    # 80/10/10 split
    tr_p, te_p, tr_l, te_l = train_test_split(
        paths, labels, test_size=0.10, random_state=42, stratify=labels)
    tr_p, va_p, tr_l, va_l = train_test_split(
        tr_p, tr_l, test_size=0.111, random_state=42, stratify=tr_l)

    train_ds = ArtifactDataset(tr_p, tr_l, transform_train)
    val_ds   = ArtifactDataset(va_p, va_l, transform_val)
    test_ds  = ArtifactDataset(te_p, te_l, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    test_loader  = DataLoader(test_ds,  batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}  Test: {len(test_ds)}")

    model     = build_model().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        total_loss = 0.0
        for imgs, labels_b in train_loader:
            imgs, labels_b = imgs.to(device), labels_b.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels_b)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        acc, f1, prec, rec = evaluate(model, val_loader, device)
        avg_loss = total_loss / len(train_ds)
        elapsed  = time.time() - t0

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  "
              f"Acc={acc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  Rec={rec:.4f}  ({elapsed:.1f}s)")
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1:.4f}",
                     f"{prec:.4f}", f"{rec:.4f}"])

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  -> Saved (F1={best_f1:.4f})")

    print(f"\nTraining complete. Best val F1={best_f1:.4f}  Weights: {SAVE_PATH}")

    # Final evaluation on held-out test set
    print("\n--- Classification Report (TEST SET) ---")
    model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for imgs, labels_b in test_loader:
            preds.extend(model(imgs.to(device)).argmax(1).cpu().tolist())
            trues.extend(labels_b.tolist())
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    with open(RESULTS_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['epoch', 'loss', 'acc', 'f1_macro', 'prec_macro', 'rec_macro'])
        w.writerows(rows)
    print(f"Results -> {RESULTS_CSV}")
