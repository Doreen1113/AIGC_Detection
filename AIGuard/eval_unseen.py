"""
Evaluate ShuffleNetV2 on the unseen/ held-out set.
Trains on real/ + fake/ (30K each), then tests on unseen/.
"""
import torch
import torch.nn as nn
import torchvision.models as tv_models
import os
import random
import io
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, confusion_matrix
from PIL import Image
import pandas as pd


class RandomJPEGCompression:
    """隨機 JPEG 壓縮，模擬網路圖片的壓縮失真。"""
    def __init__(self, quality_range=(40, 95)):
        self.quality_range = quality_range

    def __call__(self, img):
        quality = random.randint(*self.quality_range)
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality)
        buf.seek(0)
        return Image.open(buf).convert("RGB")

base_path = r"C:\My_Project\AIGC\AIGuard"
weights_path = r"C:\My_Project\AIGC\shufflenet_v2_30k_celeba.pth"
CELEBA_DIR  = r"C:\My_Project\AIGC\celeba_real"

EPOCHS = 15
BATCH_SIZE = 128

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.RandomGrayscale(p=0.05),
    RandomJPEGCompression(quality_range=(40, 95)),   # 模擬網路圖片壓縮
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

transform = transforms.Compose([
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

class UnseenDataset(Dataset):
    def __init__(self, folder, transform=None):
        self.transform = transform
        self.samples = []
        for fname in os.listdir(folder):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.jfif')):
                continue
            label = 0 if fname.lower().startswith('real') else 1
            self.samples.append((os.path.join(folder, fname), label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label

def collect_images(label_dir, max_per_subfolder=6000):
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

def build_shufflenet():
    m = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m

def evaluate(model, loader, device):
    model.eval()
    all_preds, all_labels, all_probs = [], [], []
    with torch.no_grad():
        for imgs, lbls in loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            out = model(imgs)
            probs = torch.softmax(out, dim=1)[:, 1]
            preds = out.argmax(dim=1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(lbls.cpu().numpy())
            all_probs.extend(probs.cpu().numpy())
    acc = sum(p == l for p, l in zip(all_preds, all_labels)) / len(all_labels)
    f1 = f1_score(all_labels, all_preds)
    prec = precision_score(all_labels, all_preds)
    rec = recall_score(all_labels, all_preds)
    auroc = roc_auc_score(all_labels, all_probs)
    cm = confusion_matrix(all_labels, all_preds)
    return acc, f1, prec, rec, auroc, cm

if __name__ == '__main__':
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = build_shufflenet().to(device)

    if os.path.exists(weights_path):
        print(f"Loading saved weights from {weights_path}")
        model.load_state_dict(torch.load(weights_path, map_location=device))
    else:
        print("Training ShuffleNetV2 on AIGuard + CelebA real...")
        real_paths = collect_images("real", max_per_subfolder=6000)
        fake_paths = collect_images("fake", max_per_subfolder=6000)

        # 加入 CelebA 作為額外 real 來源
        celeba_paths = [os.path.join(CELEBA_DIR, f)
                        for f in os.listdir(CELEBA_DIR)
                        if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        real_paths = real_paths + celeba_paths
        print(f"Real: {len(real_paths)} (AIGuard {len(real_paths)-len(celeba_paths)} + CelebA {len(celeba_paths)}) | Fake: {len(fake_paths)}")

        image_paths = real_paths + fake_paths
        labels = [0] * len(real_paths) + [1] * len(fake_paths)
        train_paths, val_paths, train_labels, val_labels = train_test_split(
            image_paths, labels, test_size=0.2, stratify=labels, random_state=42
        )

        train_loader = DataLoader(FaceDataset(train_paths, train_labels, transform_train),
                                  batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True)

        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        criterion = nn.CrossEntropyLoss()

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

        torch.save(model.state_dict(), weights_path)
        print(f"Weights saved to {weights_path}")

        # val set result
        val_loader = DataLoader(FaceDataset(val_paths, val_labels, transform),
                                batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)
        acc, f1, prec, rec, auroc, cm = evaluate(model, val_loader, device)
        print(f"\n[Val set] Acc={acc:.4f} F1={f1:.4f} Prec={prec:.4f} Rec={rec:.4f} AUROC={auroc:.4f}")

    # unseen evaluation
    print("\n" + "="*60)
    print("UNSEEN HELD-OUT EVALUATION")
    print("="*60)
    unseen_folder = os.path.join(base_path, "unseen")
    unseen_loader = DataLoader(UnseenDataset(unseen_folder, transform),
                               batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True)
    print(f"Unseen samples: {len(unseen_loader.dataset)}")

    acc, f1, prec, rec, auroc, cm = evaluate(model, unseen_loader, device)
    print(f"Acc={acc:.4f} F1={f1:.4f} Prec={prec:.4f} Rec={rec:.4f} AUROC={auroc:.4f}")
    print(f"\nConfusion Matrix (rows=actual, cols=pred):")
    print(f"           Pred Real  Pred Fake")
    print(f"Actual Real   {cm[0][0]:5d}      {cm[0][1]:5d}")
    print(f"Actual Fake   {cm[1][0]:5d}      {cm[1][1]:5d}")
