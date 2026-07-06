"""
3-class classification: Real / Fake / Filter-processed
執行環境：base env
    python AIGuard/train_3class.py
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
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, confusion_matrix, classification_report
from PIL import Image
import pandas as pd


class FocalLoss(nn.Module):
    """聚焦難分樣本，alpha 對各 class 加權，gamma 控制聚焦強度。"""
    def __init__(self, alpha=None, gamma=2.0):
        super().__init__()
        self.alpha = alpha  # tensor of shape [num_classes]
        self.gamma = gamma

    def forward(self, logits, targets):
        ce = F.cross_entropy(logits, targets, weight=self.alpha, reduction='none')
        pt = torch.exp(-ce)
        loss = ((1 - pt) ** self.gamma) * ce
        return loss.mean()

BASE         = r"C:\My_Project\AIGC"
REAL_DIR     = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR     = os.path.join(BASE, "AIGuard", "fake")
FILTER_DIR   = os.path.join(BASE, "filter_data")
WEIGHTS_PATH = os.path.join(BASE, "shufflenet_v2_3class_focal.pth")

CLASSES = ["real", "fake", "filter"]   # label 0 / 1 / 2
N_PER_SUBFOLDER = 6000
EPOCHS     = 15
BATCH_SIZE = 128

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
    def __init__(self, image_paths, labels, transform=None):
        self.image_paths = image_paths
        self.labels = labels
        self.transform = transform

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img = Image.open(self.image_paths[idx]).convert("RGB")
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
        elif sub.lower().endswith(('.jpg', '.jpeg', '.png')):
            paths.append(os.path.join(root, sub))
            labels.append(label)
    return paths, labels


if __name__ == '__main__':
    # collect data
    real_paths,   real_labels   = collect_from_subfolders(REAL_DIR,  0, N_PER_SUBFOLDER)
    fake_paths,   fake_labels   = collect_from_subfolders(FAKE_DIR,  1, N_PER_SUBFOLDER)
    filter_paths, filter_labels = collect_from_flat(FILTER_DIR, 2)

    print(f"Real:   {len(real_paths)}")
    print(f"Fake:   {len(fake_paths)}")
    print(f"Filter: {len(filter_paths)}")

    if not filter_paths:
        print("\n[ERROR] filter_data/ is empty.")
        print("Run first: conda activate mediapipe_env && python filters/generate_filter_dataset.py")
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

    model = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    model.fc = nn.Linear(model.fc.in_features, 3)   # 3 classes
    model = model.to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)

    # Focal Loss：alpha 對 filter class 加重（real=1, fake=1, filter=1.5）
    alpha = torch.tensor([1.0, 1.0, 1.5]).to(device)
    criterion = FocalLoss(alpha=alpha, gamma=2.0)

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
    all_preds, all_labels_eval = [], []
    with torch.no_grad():
        for imgs, lbls in val_loader:
            imgs = imgs.to(device)
            preds = model(imgs).argmax(dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_labels_eval.extend(lbls.numpy())

    print("\n=== Validation Results ===")
    print(classification_report(all_labels_eval, all_preds, target_names=CLASSES))

    cm = confusion_matrix(all_labels_eval, all_preds)
    print("Confusion Matrix (rows=actual, cols=pred):")
    header = f"{'':12}" + "".join(f"{c:>10}" for c in CLASSES)
    print(header)
    for i, row in enumerate(cm):
        print(f"{CLASSES[i]:12}" + "".join(f"{v:>10}" for v in row))

    df = pd.DataFrame({"path": val_paths, "actual": all_labels_eval, "pred": all_preds})
    df.to_csv(os.path.join(BASE, "results", "3class_val_results.csv"), index=False)
    print(f"\nSaved to results/3class_val_results.csv")
