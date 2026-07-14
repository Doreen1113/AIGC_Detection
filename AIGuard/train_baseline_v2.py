"""
Baseline 4-model comparison v2.
Changes from v1:
  - Loads from clean_paths.txt (post-cleaning)
  - 80/10/10 train/val/test split
  - JPEG compression augmentation (quality 40-95, found effective in Problem 2)
  - Val monitoring + best-model checkpoint per model
  - Test metrics reported on held-out test set only

python AIGuard/train_baseline_v2.py
"""
import torch
import torch.nn as nn
import timm
import torchvision.models as tv_models
import time
import os
import io
import random
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, accuracy_score
from PIL import Image
import pandas as pd

BASE      = r"C:\My_Project\AIGC"
REAL_TXT  = os.path.join(BASE, "AIGuard", "real",  "clean_output", "clean_paths.txt")
FAKE_TXT  = os.path.join(BASE, "AIGuard", "fake",  "clean_output", "clean_paths.txt")
CKPT_DIR  = os.path.join(BASE, "results", "baseline_v2_ckpts")
RESULTS_CSV = os.path.join(BASE, "results", "baseline_comparison_v2.csv")

EPOCHS     = 15
BATCH_SIZE = 128


class JPEGAug:
    """Re-encode PIL image at random JPEG quality 40-95."""
    def __call__(self, img):
        q = random.randint(40, 95)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=q)
        buf.seek(0)
        return Image.open(buf).convert("RGB")


transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    JPEGAug(),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


class FaceDataset(Dataset):
    def __init__(self, paths, labels, transform=None):
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self): return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform: img = self.transform(img)
        return img, self.labels[idx]


def build_model(name):
    if name == "MobileNetV4":
        return timm.create_model("mobilenetv4_conv_small", pretrained=True, num_classes=2)
    elif name == "EfficientNet-lite":
        return timm.create_model("efficientnet_lite0", pretrained=True, num_classes=2)
    elif name == "ResNet-lite":
        return timm.create_model("resnet18", pretrained=True, num_classes=2)
    elif name == "ShuffleNetV2":
        m = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, 2)
        return m
    raise ValueError(name)


def evaluate(model, loader, device):
    model.eval()
    preds, labels, probs = [], [], []
    with torch.no_grad():
        for imgs, lbs in loader:
            imgs, lbs = imgs.to(device), lbs.to(device)
            out = model(imgs)
            p = torch.softmax(out, dim=1)[:, 1]
            probs.extend(p.cpu().tolist())
            preds.extend(out.argmax(1).cpu().tolist())
            labels.extend(lbs.cpu().tolist())
    acc   = accuracy_score(labels, preds)
    f1    = f1_score(labels, preds)
    prec  = precision_score(labels, preds, zero_division=0)
    rec   = recall_score(labels, preds, zero_division=0)
    auroc = roc_auc_score(labels, probs)
    return acc, f1, prec, rec, auroc


if __name__ == '__main__':
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    real_paths = [p for p in Path(REAL_TXT).read_text(encoding="utf-8").splitlines() if p]
    fake_paths = [p for p in Path(FAKE_TXT).read_text(encoding="utf-8").splitlines() if p]
    print(f"Real: {len(real_paths)}  Fake: {len(fake_paths)}")

    all_paths  = real_paths + fake_paths
    all_labels = [0] * len(real_paths) + [1] * len(fake_paths)

    # 80/10/10 split
    tr_p, te_p, tr_l, te_l = train_test_split(
        all_paths, all_labels, test_size=0.10, random_state=42, stratify=all_labels)
    tr_p, va_p, tr_l, va_l = train_test_split(
        tr_p, tr_l, test_size=0.111, random_state=42, stratify=tr_l)

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

    os.makedirs(CKPT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)

    model_names = ["MobileNetV4", "EfficientNet-lite", "ResNet-lite", "ShuffleNetV2"]
    summary_rows = []

    for name in model_names:
        print(f"\n{'='*55}\nTraining {name}\n{'='*55}")
        model = build_model(name).to(device)
        n_params = sum(p.numel() for p in model.parameters()) / 1e6

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        criterion = nn.CrossEntropyLoss()
        ckpt_path = os.path.join(CKPT_DIR, f"{name.replace(' ', '_')}_best.pth")

        best_val_f1 = 0.0
        for epoch in range(1, EPOCHS + 1):
            model.train()
            total_loss = 0.0
            for imgs, lbs in train_loader:
                imgs, lbs = imgs.to(device), lbs.to(device)
                optimizer.zero_grad()
                loss = criterion(model(imgs), lbs)
                loss.backward(); optimizer.step()
                total_loss += loss.item() * imgs.size(0)

            val_acc, val_f1, val_prec, val_rec, val_auroc = evaluate(model, val_loader, device)
            avg_loss = total_loss / len(train_ds)
            print(f"  [{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  "
                  f"val_Acc={val_acc:.4f}  val_F1={val_f1:.4f}  val_AUROC={val_auroc:.4f}")

            if val_f1 > best_val_f1:
                best_val_f1 = val_f1
                torch.save(model.state_dict(), ckpt_path)

        # Final evaluation on test set
        if device == "cuda":
            torch.cuda.reset_peak_memory_stats()
        model.load_state_dict(torch.load(ckpt_path, map_location=device))
        t0 = time.time()
        acc, f1, prec, rec, auroc = evaluate(model, test_loader, device)
        elapsed = time.time() - t0
        ms_per_img = elapsed / len(test_ds) * 1000
        vram_gb = torch.cuda.max_memory_allocated() / 1e9 if device == "cuda" else 0

        print(f"\n  [TEST SET] Acc={acc:.4f}  F1={f1:.4f}  Prec={prec:.4f}  "
              f"Rec={rec:.4f}  AUROC={auroc:.4f}  {ms_per_img:.2f}ms/img  {vram_gb:.2f}GB")

        summary_rows.append({
            "model": name, "params_M": round(n_params, 2),
            "acc": round(acc, 4), "f1": round(f1, 4),
            "precision": round(prec, 4), "recall": round(rec, 4),
            "auroc": round(auroc, 4),
            "ms_per_img": round(ms_per_img, 2), "vram_gb": round(vram_gb, 2),
        })

    print("\n" + "="*70)
    print("BASELINE COMPARISON SUMMARY v2 (TEST SET, clean data, 80/10/10)")
    print("="*70)
    df = pd.DataFrame(summary_rows).set_index("model")
    print(df.to_string())
    df.to_csv(RESULTS_CSV)
    print(f"\nSaved to {RESULTS_CSV}")
