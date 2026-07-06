"""
Artifact type classifier v2: adds RetouchingFFHQ ali_process data.

Classes: eye_enlarging / face_reshaping / smoothing / whitening
Data:
  - filter_data/    : 32K self-generated (8K × 4)
  - FFHQ_ali_process: 36K real app (9K × 4 types, 3 levels each)

python AIGuard/train_artifact_classifier_v2.py
"""
import os, csv, time
import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, classification_report
from PIL import Image
import numpy as np

BASE        = r"C:\My_Project\AIGC"
FILTER_DIR  = os.path.join(BASE, "filter_data")
ALI_DIR     = os.path.join(BASE, "FFHQ_ali_process")
SAVE_PATH   = os.path.join(BASE, "artifact_classifier_v2.pth")
RESULTS_CSV = os.path.join(BASE, "results", "artifact_classifier_v2_results.csv")

# Must match ImageFolder alphabetical order of filter_data
CLASSES     = ["eye_enlarging", "face_reshaping", "smoothing", "whitening"]
CLASS_INDEX = {c: i for i, c in enumerate(CLASSES)}

# Ali folder prefix → class name
ALI_PREFIX_MAP = {
    "EyeEnlarging": "eye_enlarging",
    "FaceLifting":  "face_reshaping",
    "Smoothing":    "smoothing",
    "Whitening":    "whitening",
}

EPOCHS      = 15
BATCH_SIZE  = 64
LR          = 1e-3
VAL_RATIO   = 0.2
NUM_CLASSES = 4


class ArtifactDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, self.labels[idx]


def collect_filter_data(root):
    """filter_data/class_name/images"""
    paths, labels = [], []
    for cls in os.listdir(root):
        if cls not in CLASS_INDEX: continue
        cls_path = os.path.join(root, cls)
        if not os.path.isdir(cls_path): continue
        for f in os.listdir(cls_path):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                paths.append(os.path.join(cls_path, f))
                labels.append(CLASS_INDEX[cls])
    return paths, labels


def collect_ali_data(root):
    """FFHQ_ali_process/FilterType_Level/subfolder/images"""
    paths, labels = [], []
    for type_level in os.listdir(root):
        tl_path = os.path.join(root, type_level)
        if not os.path.isdir(tl_path): continue
        # parse prefix before underscore+number
        prefix = type_level.rsplit("_", 1)[0]  # e.g. EyeEnlarging_30 → EyeEnlarging
        cls = ALI_PREFIX_MAP.get(prefix)
        if cls is None: continue
        for sub in os.listdir(tl_path):
            sub_path = os.path.join(tl_path, sub)
            if not os.path.isdir(sub_path): continue
            for f in os.listdir(sub_path):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    paths.append(os.path.join(sub_path, f))
                    labels.append(CLASS_INDEX[cls])
    return paths, labels


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
            logits = model(imgs.to(device))
            probs  = torch.softmax(logits, dim=1)
            preds  = probs.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
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

    # collect data
    flt_paths, flt_labels = collect_filter_data(FILTER_DIR)
    ali_paths, ali_labels = collect_ali_data(ALI_DIR)

    all_paths  = flt_paths  + ali_paths
    all_labels = flt_labels + ali_labels

    print(f"filter_data: {len(flt_paths)}")
    print(f"ali_process: {len(ali_paths)}")
    print(f"Total:       {len(all_paths)}")

    # per-class counts
    from collections import Counter
    cnt = Counter(all_labels)
    for i, c in enumerate(CLASSES):
        print(f"  {c}: {cnt[i]}")

    # train/val split
    from sklearn.model_selection import train_test_split
    tr_p, va_p, tr_l, va_l = train_test_split(
        all_paths, all_labels, test_size=VAL_RATIO,
        random_state=42, stratify=all_labels)

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

    train_loader = DataLoader(ArtifactDataset(tr_p, tr_l, transform_train),
                              batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(ArtifactDataset(va_p, va_l, transform_val),
                              batch_size=BATCH_SIZE, shuffle=False,
                              num_workers=4, pin_memory=True)
    print(f"Train: {len(tr_p)}  Val: {len(va_p)}")

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
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward(); optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        acc, f1, prec, rec, auroc = evaluate(model, val_loader, device)
        avg_loss = total_loss / len(tr_p)
        elapsed  = time.time() - t0

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
        w.writerow(['epoch','loss','acc','f1_macro','prec_macro','rec_macro','auroc'])
        w.writerows(rows)

    # per-class breakdown
    print("\n--- Per-class F1 (val) ---")
    model.load_state_dict(torch.load(SAVE_PATH, map_location=device))
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for imgs, labels in val_loader:
            preds = model(imgs.to(device)).argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.numpy())
    print(classification_report(all_labels, all_preds, target_names=CLASSES, digits=4))
