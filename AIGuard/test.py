import torch
import torch.nn as nn
import timm
import torchvision.models as tv_models
import time
import os
import random
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from PIL import Image
import pandas as pd

# ---- Step 1: 收集圖片路徑 ----
base_path = r"C:\CVLab\AIGC\AIGuard"

def collect_images(label_dir, max_per_subfolder=600):
    paths = []
    full_dir = os.path.join(base_path, label_dir)
    for sub in os.listdir(full_dir):
        sub_path = os.path.join(full_dir, sub)
        if os.path.isdir(sub_path):
            files = [f for f in os.listdir(sub_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            random.seed(42)
            random.shuffle(files)
            files = files[:max_per_subfolder]
            paths.extend([os.path.join(sub_path, f) for f in files])
    return paths

real_paths = collect_images("real", max_per_subfolder=600)
fake_paths = collect_images("fake", max_per_subfolder=600)

print(f"Real: {len(real_paths)} | Fake: {len(fake_paths)}")

image_paths = real_paths + fake_paths
labels = [0] * len(real_paths) + [1] * len(fake_paths)

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

train_paths, test_paths, train_labels, test_labels = train_test_split(
    image_paths, labels, test_size=0.2, stratify=labels, random_state=42
)
print(f"Train: {len(train_paths)} | Test: {len(test_paths)}")

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

train_dataset = FaceDataset(train_paths, train_labels, transform)
test_dataset = FaceDataset(test_paths, test_labels, transform)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True, num_workers=0)
test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False, num_workers=0)

device = "cuda" if torch.cuda.is_available() else "cpu"
print("Using device:", device)

EPOCHS = 5

# 對應先前四個 baseline 模型的建構方式（用參數量比對確認過）：
# MobileNetV4      -> timm: mobilenetv4_conv_small
# EfficientNet-lite -> timm: efficientnet_lite0
# ResNet-lite      -> timm: resnet18
# ShuffleNetV2     -> torchvision: shufflenet_v2_x1_0（timm 沒有這個模型）
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
    else:
        raise ValueError(name)

model_names = ["MobileNetV4", "EfficientNet-lite", "ResNet-lite", "ShuffleNetV2"]
results = {}

for name in model_names:
    print(f"\n{'='*50}\nTraining {name}\n{'='*50}")

    model = build_model(name).to(device)
    n_params = sum(p.numel() for p in model.parameters()) / 1e6

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    criterion = torch.nn.CrossEntropyLoss()

    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            optimizer.zero_grad()
            out = model(imgs)
            loss = criterion(out, lbls)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch+1}/{EPOCHS} - Loss: {total_loss/len(train_loader):.4f}")

    model.eval()
    correct, total = 0, 0
    all_preds, all_labels, all_probs = [], [], []
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()

    start = time.time()
    with torch.no_grad():
        for imgs, lbls in test_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            out = model(imgs)
            probs = torch.softmax(out, dim=1)[:, 1]  # P(fake)
            pred = out.argmax(dim=1)
            correct += (pred == lbls).sum().item()
            total += lbls.size(0)
            all_preds.extend(pred.cpu().numpy())
            all_labels.extend(lbls.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    elapsed_total = time.time() - start
    ms_per_image = (elapsed_total / total) * 1000
    vram_gb = torch.cuda.max_memory_allocated() / 1e9 if device == "cuda" else 0

    acc = correct / total
    f1 = f1_score(all_labels, all_preds)
    precision = precision_score(all_labels, all_preds)
    recall = recall_score(all_labels, all_preds)
    auroc = roc_auc_score(all_labels, all_probs)

    results[name] = {
        "params_M": round(n_params, 2),
        "accuracy": round(acc, 4),
        "f1": round(f1, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "auroc": round(auroc, 4),
        "ms_per_image": round(ms_per_image, 2),
        "vram_gb": round(vram_gb, 2),
    }
    print(f"  Acc={acc:.4f} F1={f1:.4f} Precision={precision:.4f} Recall={recall:.4f} "
          f"AUROC={auroc:.4f} {ms_per_image:.2f}ms/img {vram_gb:.2f}GB VRAM")

print("\n" + "="*70 + "\nBASELINE COMPARISON SUMMARY (4 models)\n" + "="*70)
df = pd.DataFrame(results).T
print(df.to_string())
df.to_csv("baseline_comparison.csv")
print("\nSaved to baseline_comparison.csv")
