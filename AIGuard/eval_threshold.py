"""
掃 decision threshold，找 unseen held-out 最佳切點。
使用現有 JPEG-aug 模型：shufflenet_v2_30k_aug.pth
"""
import torch
import torch.nn as nn
import torchvision.models as tv_models
import os
import numpy as np
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, confusion_matrix
from PIL import Image

base_path   = r"C:\My_Project\AIGC\AIGuard"
weights_path = r"C:\My_Project\AIGC\shufflenet_v2_30k_aug.pth"

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

class UnseenDataset(Dataset):
    def __init__(self, folder, transform=None):
        self.transform = transform
        self.samples = []
        for fname in os.listdir(folder):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.jfif')):
                continue
            label = 0 if fname.lower().startswith('real') else 1
            self.samples.append((os.path.join(folder, fname), label))

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

def build_shufflenet():
    m = tv_models.shufflenet_v2_x1_0(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m

if __name__ == '__main__':
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = build_shufflenet().to(device)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()

    unseen_folder = os.path.join(base_path, "unseen")
    loader = DataLoader(UnseenDataset(unseen_folder, transform),
                        batch_size=128, shuffle=False, num_workers=4, pin_memory=True)
    print(f"Unseen samples: {len(loader.dataset)}")

    all_probs, all_labels = [], []
    with torch.no_grad():
        for imgs, lbls in loader:
            imgs = imgs.to(device)
            out = model(imgs)
            probs = torch.softmax(out, dim=1)[:, 1]   # P(fake)
            all_probs.extend(probs.cpu().numpy())
            all_labels.extend(lbls.numpy())

    all_probs  = np.array(all_probs)
    all_labels = np.array(all_labels)

    auroc = roc_auc_score(all_labels, all_probs)
    print(f"\nAUROC = {auroc:.4f}")
    print(f"\n{'Thresh':>7}  {'Acc':>6}  {'F1':>6}  {'Prec':>6}  {'Rec':>6}  "
          f"{'Real→Fake':>10}  {'Fake→Real':>10}")
    print("-" * 70)

    best_f1, best_thresh = 0, 0.5
    for t in np.arange(0.1, 0.91, 0.05):
        preds = (all_probs >= t).astype(int)
        acc  = (preds == all_labels).mean()
        f1   = f1_score(all_labels, preds, zero_division=0)
        prec = precision_score(all_labels, preds, zero_division=0)
        rec  = recall_score(all_labels, preds, zero_division=0)
        cm   = confusion_matrix(all_labels, preds)
        real2fake = cm[0][1] if cm.shape[0] > 1 else 0
        fake2real = cm[1][0] if cm.shape[0] > 1 else 0
        marker = " ←" if f1 > best_f1 else ""
        print(f"  {t:.2f}   {acc:.4f}  {f1:.4f}  {prec:.4f}  {rec:.4f}  "
              f"{real2fake:>10}  {fake2real:>10}{marker}")
        if f1 > best_f1:
            best_f1, best_thresh = f1, t

    print(f"\n最佳 threshold = {best_thresh:.2f}  (F1={best_f1:.4f})")

    # 最佳 threshold 的詳細 confusion matrix
    preds = (all_probs >= best_thresh).astype(int)
    cm = confusion_matrix(all_labels, preds)
    print(f"\nConfusion Matrix at threshold={best_thresh:.2f}:")
    print(f"           Pred Real  Pred Fake")
    print(f"Actual Real   {cm[0][0]:5d}      {cm[0][1]:5d}")
    print(f"Actual Fake   {cm[1][0]:5d}      {cm[1][1]:5d}")
