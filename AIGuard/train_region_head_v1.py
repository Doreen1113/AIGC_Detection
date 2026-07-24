"""
Phase 2 — Train explanation region head on FakeVLM-derived labels.

Architecture : DualBranch v8.1 (frozen) → RegionHead (Linear 1280→256→8)
Labels       : results/fakevlm_region_labels.jsonl  (from parse_region_labels.py)
Output       : region_head_v1.pth

Usage:
    python AIGuard/train_region_head_v1.py
"""

import json
import random
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as tv_models
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from PIL import Image
from sklearn.metrics import f1_score
import numpy as np

BASE         = Path(r"C:\My_Project\AIGC")
BACKBONE_PTH = BASE / "shufflenet_v2_3class_v81.pth"
LABELS_PATH  = BASE / "results" / "fakevlm_region_labels.jsonl"
OUT_PATH     = BASE / "region_head_v1.pth"

REGIONS = ["forehead", "left_eye", "right_eye", "nose",
           "left_cheek", "right_cheek", "mouth", "jaw"]
NUM_REGIONS = len(REGIONS)

UBU_PREFIX = "/home/intern_2603055/AIGC"
WIN_PREFIX = str(BASE)

EPOCHS    = 30
LR        = 1e-3
BATCH     = 32
VAL_RATIO = 0.2
SEED      = 42

transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])
transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


# ── Models ───────────────────────────────────────────────────────────────────

class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(),
            nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4),
            nn.Flatten(),
            nn.Linear(128 * 4 * 4, out_dim), nn.ReLU(),
        )
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        mag = torch.log(torch.abs(fft) + 1e-8)
        return self.net(mag)


class DualBranchBackbone(nn.Module):
    """v8.1 backbone — returns 1280-dim features, no classifier."""
    def __init__(self):
        super().__init__()
        backbone = tv_models.shufflenet_v2_x1_0(
            weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        backbone.fc = nn.Identity()
        self.spatial_branch = backbone
        self.fft_branch     = FFTBranch(out_dim=256)
        # classifier exists in checkpoint but we don't use it
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256, 512), nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 3),
        )
    def forward(self, x):
        spatial = self.spatial_branch(x)
        freq    = self.fft_branch(x)
        return torch.cat([spatial, freq], dim=1)  # 1280-dim


class RegionHead(nn.Module):
    def __init__(self, in_dim=1280, num_regions=NUM_REGIONS):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(in_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_regions),
        )
    def forward(self, x):
        return self.net(x)


# ── Dataset ──────────────────────────────────────────────────────────────────

def ubu_to_win(path: str) -> str:
    return path.replace(UBU_PREFIX, WIN_PREFIX).replace("/", "\\")


def load_records():
    records = []
    for line in LABELS_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if not r["suspicious_regions"]:
            continue  # skip chameleon empties
        win_path = ubu_to_win(r["path"])
        if not Path(win_path).exists():
            continue
        label = [1.0 if reg in r["suspicious_regions"] else 0.0 for reg in REGIONS]
        records.append((win_path, label))
    return records


class RegionDataset(Dataset):
    def __init__(self, records, transform):
        self.records   = records
        self.transform = transform
    def __len__(self):
        return len(self.records)
    def __getitem__(self, idx):
        path, label = self.records[idx]
        img = Image.open(path).convert("RGB")
        return self.transform(img), torch.tensor(label, dtype=torch.float32)


# ── Training ─────────────────────────────────────────────────────────────────

def compute_pos_weight(records):
    labels = np.array([r[1] for r in records])
    pos = labels.sum(axis=0)
    neg = len(labels) - pos
    w = neg / (pos + 1e-8)
    return torch.tensor(w, dtype=torch.float32)


def eval_epoch(backbone, head, loader, criterion, device):
    backbone.eval(); head.eval()
    total_loss = 0.0
    all_preds, all_targets = [], []
    with torch.no_grad():
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            feats  = backbone(imgs)
            logits = head(feats)
            total_loss += criterion(logits, labels).item() * len(imgs)
            preds = (torch.sigmoid(logits) > 0.5).cpu().numpy()
            all_preds.append(preds)
            all_targets.append(labels.cpu().numpy())
    all_preds   = np.vstack(all_preds)
    all_targets = np.vstack(all_targets)
    f1_macro = f1_score(all_targets, all_preds, average="macro", zero_division=0)
    f1_each  = f1_score(all_targets, all_preds, average=None, zero_division=0)
    return total_loss / len(loader.dataset), f1_macro, f1_each


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # Load and split data
    records = load_records()
    print(f"Usable records: {len(records)}")
    random.seed(SEED)
    random.shuffle(records)
    n_val      = int(len(records) * VAL_RATIO)
    val_recs   = records[:n_val]
    train_recs = records[n_val:]
    print(f"Train: {len(train_recs)}  Val: {len(val_recs)}")

    train_ds = RegionDataset(train_recs, transform_train)
    val_ds   = RegionDataset(val_recs,   transform_val)
    train_dl = DataLoader(train_ds, batch_size=BATCH, shuffle=True,
                          num_workers=2, pin_memory=True)
    val_dl   = DataLoader(val_ds,   batch_size=BATCH, shuffle=False,
                          num_workers=2, pin_memory=True)

    # Load backbone (frozen)
    backbone = DualBranchBackbone().to(device)
    ckpt = torch.load(BACKBONE_PTH, map_location=device)
    backbone.load_state_dict(ckpt, strict=False)
    backbone.eval()
    for p in backbone.parameters():
        p.requires_grad_(False)
    print(f"Backbone loaded from {BACKBONE_PTH} (frozen)")

    # Region head
    head = RegionHead().to(device)

    # Loss with pos_weight for class imbalance
    pos_weight = compute_pos_weight(train_recs).to(device)
    print("pos_weight:", {r: f"{w:.1f}" for r, w in zip(REGIONS, pos_weight.cpu())})
    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)

    optimizer = torch.optim.Adam(head.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    best_val_loss = float("inf")
    print(f"\n{'Ep':>3} {'TrainLoss':>10} {'ValLoss':>9} {'F1macro':>8}  Per-region F1")
    print("-" * 100)

    for epoch in range(1, EPOCHS + 1):
        # Train
        backbone.eval(); head.train()
        train_loss = 0.0
        for imgs, labels in train_dl:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            with torch.no_grad():
                feats = backbone(imgs)
            logits = head(feats)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(imgs)
        train_loss /= len(train_dl.dataset)
        scheduler.step()

        val_loss, f1_macro, f1_each = eval_epoch(backbone, head, val_dl, criterion, device)

        marker = " ← best" if val_loss < best_val_loss else ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(head.state_dict(), OUT_PATH)

        f1_str = " ".join(f"{r[:4]}:{v:.2f}" for r, v in zip(REGIONS, f1_each))
        print(f"{epoch:>3}  {train_loss:>10.4f}  {val_loss:>9.4f}  {f1_macro:>8.3f}  {f1_str}{marker}")

    print(f"\nBest val loss: {best_val_loss:.4f}")
    print(f"Saved → {OUT_PATH}")

    # Final per-region report
    print("\nFinal val F1 per region:")
    _, _, f1_each = eval_epoch(backbone, head, val_dl, criterion, device)
    for reg, f1 in zip(REGIONS, f1_each):
        print(f"  {reg:15s}: {f1:.3f}")


if __name__ == "__main__":
    main()
