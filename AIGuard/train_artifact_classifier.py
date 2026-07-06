"""
Train a lightweight 4-class artifact type classifier.
Classes: smoothing / whitening / eye_enlarging / face_reshaping
Data   : filter_data/ (8000 images per class, 32K total)
Output : artifact_classifier.pth
"""

import os, time, csv
import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms
from torchvision.datasets import ImageFolder
from torch.utils.data import DataLoader, random_split
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
import numpy as np

DATA_DIR    = r"C:\My_Project\AIGC\filter_data"
SAVE_PATH   = r"C:\My_Project\AIGC\artifact_classifier.pth"
RESULTS_CSV = r"C:\My_Project\AIGC\results\artifact_classifier_results.csv"

EPOCHS     = 15
BATCH_SIZE = 64
LR         = 1e-3
VAL_RATIO  = 0.2
NUM_CLASSES = 4


def build_model():
    model = tv_models.shufflenet_v2_x1_0(
        weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, NUM_CLASSES)
    return model


def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            logits = model(imgs)
            probs  = torch.softmax(logits, dim=1)
            preds  = probs.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())

    all_preds  = np.array(all_preds)
    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)

    acc   = (all_preds == all_labels).mean()
    f1    = f1_score(all_labels, all_preds, average='macro')
    prec  = precision_score(all_labels, all_preds, average='macro', zero_division=0)
    rec   = recall_score(all_labels, all_preds, average='macro', zero_division=0)
    auroc = roc_auc_score(all_labels, all_probs, multi_class='ovr', average='macro')
    return acc, f1, prec, rec, auroc


if __name__ == '__main__':
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {device}")

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

    full_dataset = ImageFolder(DATA_DIR, transform=transform_train)
    print(f"Classes: {full_dataset.classes}")  # alphabetical order

    n_val   = int(len(full_dataset) * VAL_RATIO)
    n_train = len(full_dataset) - n_val
    train_ds, val_ds = random_split(
        full_dataset, [n_train, n_val],
        generator=torch.Generator().manual_seed(42))

    # Use val transform for val split
    val_ds.dataset = ImageFolder(DATA_DIR, transform=transform_val)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)

    model = build_model().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        avg_loss = total_loss / n_train
        acc, f1, prec, rec, auroc = evaluate(model, val_loader, device)
        elapsed = time.time() - t0

        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  "
              f"Acc={acc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  "
              f"Rec={rec:.4f}  AUROC={auroc:.4f}  ({elapsed:.1f}s)")

        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1:.4f}",
                     f"{prec:.4f}", f"{rec:.4f}", f"{auroc:.4f}"])

        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), SAVE_PATH)
            print(f"  → Saved (F1={best_f1:.4f})")

    print(f"\nTraining complete. Best F1={best_f1:.4f}  Weights: {SAVE_PATH}")

    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    with open(RESULTS_CSV, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['epoch', 'loss', 'acc', 'f1_macro', 'prec_macro', 'rec_macro', 'auroc'])
        w.writerows(rows)
    print(f"Results saved to {RESULTS_CSV}")

    # Per-class breakdown on val set
    print("\n--- Per-class F1 ---")
    model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            preds = model(imgs.to(device)).argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
    per_class_f1 = f1_score(all_labels, all_preds, average=None)
    for cls, f in zip(full_dataset.classes, per_class_f1):
        print(f"  {cls:20s}: F1={f:.4f}")
