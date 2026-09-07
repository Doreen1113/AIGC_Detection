"""
train_layer2_arm.py -- removal_ablation_20260904.

The production Layer 2 recipe, copied from `AIGuard/train_v811_layer2.py`
(same ShuffleNetV2 spatial + FFT dual branch, 15 epochs, BATCH_SIZE 256,
Adam LR 2e-5 + CosineAnnealingLR, mixup alpha 0.2 at p=0.5, CE with auto
inverse-frequency class weights + label_smoothing 0.1, best-macro-F1
checkpointing).

Deltas from that trainer, and ONLY these:

  1. `--arm {CTRL,REMOVE,DOWNWEIGHT,RELABEL3}` selects this round's split file.
     The recipe itself is unchanged; the arms differ ONLY in the treatment of
     the 17,725 `fake_filter_hardneg` rows (see PRE_DECLARED.md).
  2. Warm start is `shufflenet_v2_layer2_v811.pth` (production lineage, what the
     four FIX rounds used), not v8.8 -- production's Layer 2 head is already
     2-class so nothing is discarded for the 2-class arms; RELABEL3 grows the
     head to 3 and its classifier tail is re-initialised (reported explicitly).
  3. DOWNWEIGHT reads a 4th `weight` column and applies it as a per-sample
     multiplier on element-wise CE (reduction='none'), mixup-consistent:
     w_eff = lam*w_a + (1-lam)*w_b. The sampling distribution is untouched;
     the change is purely in the loss. For every other arm all weights are 1.0,
     which is arithmetically identical to the stock `reduction='mean'` path.
  4. RELABEL3 model selection: the shared val split contains no `fake+filter`
     rows (production never labelled any), so its 3-way argmax is projected to
     the production 2-way space (class 2 -> fake) BEFORE macro-F1 is computed.
     That is the same projection declared for evaluation, so selection means
     the same thing in all four arms.
  5. Checkpoint / log / meta filenames carry the arm and seed, per the
     project's 2026-08-11 rule that an output file must be named by what
     actually produced it.

Production `pipeline.py` and production checkpoints are read-only here.
"""
import argparse
import json
import os
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

BASE = Path(r"C:\My_Project\AIGC")
ROUND = BASE / "results" / "research" / "backbone_hier_20260907"
CKPT_DIR = BASE / "checkpoints" / "research" / "backbone_hier_20260907"
VAL_SPLIT = BASE / "splits" / "v811_layer2_val.txt"
INIT_WEIGHTS = str(BASE / "shufflenet_v2_layer2_v811.pth")
EPOCHS = 15
BATCH_SIZE = 256
MIXUP_ALPHA = 0.2
LR = 2e-5
ARM_CLASSES = dict(BASE=2)

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3),
])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3),
])


class FaceDataset(Dataset):
    def __init__(self, paths, labels, weights, transform=None):
        self.paths, self.labels, self.weights, self.transform = paths, labels, weights, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx], self.weights[idx]


def load_split(p):
    paths, labels, weights, missing = [], [], [], 0
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t") or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        if not os.path.isfile(parts[0]):
            missing += 1
            continue
        paths.append(parts[0])
        labels.append(int(parts[1]))
        weights.append(float(parts[3]) if len(parts) >= 4 else 1.0)
    print(f"  {Path(p).name}: kept {len(paths):,}, dropped {missing:,} missing files")
    return paths, labels, weights, missing


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU(),
        )

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho")
        f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


def _build_spatial(arch, pretrained=True):
    """ShuffleNetV2 (production) or MobileNetV4 (timm mobilenetv4_conv_small.e2400_r224_in1k,
    the same model benchmarked on FF++/cross-dataset). Output width measured by a forward pass."""
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT if pretrained else None)
        bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k", pretrained=pretrained, num_classes=0)
    m.eval()
    with torch.no_grad():
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]
    return m, int(dim)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


def mixup_batch(x, y, w, alpha=0.2):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], y, y[idx], w, w[idx], lam


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARM_CLASSES))
    ap.add_argument("--seed", type=int, default=20260904)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])
    a = ap.parse_args()
    SEED, ARM = a.seed, a.arm
    NUM_CLASSES = ARM_CLASSES[ARM]
    TRAIN_SPLIT = BASE / "splits" / "v811_layer2_train.txt"
    WEIGHTS_PATH = str(CKPT_DIR / f"layer2_{ARM}_{a.arch}_s{SEED}.pth")

    random.seed(SEED); np.random.seed(SEED)
    torch.manual_seed(SEED); torch.cuda.manual_seed_all(SEED)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}  arm={ARM}  seed={SEED}  num_classes={NUM_CLASSES}", flush=True)

    tr_p, tr_l, tr_w, tr_miss = load_split(TRAIN_SPLIT)
    va_p, va_l, va_w, va_miss = load_split(VAL_SPLIT)
    tc, vc = Counter(tr_l), Counter(va_l)
    print(f"Train: {len(tr_p):,}  {dict(sorted(tc.items()))}  (dropped {tr_miss:,})")
    print(f"Val:   {len(va_p):,}  {dict(sorted(vc.items()))}  (dropped {va_miss:,})")
    n_dw = sum(1 for w in tr_w if w != 1.0)
    print(f"Rows with sample weight != 1.0: {n_dw:,}"
          f"{' (weight=%.2f)' % tr_w[[i for i,w in enumerate(tr_w) if w!=1.0][0]] if n_dw else ''}")

    train_ds = FaceDataset(tr_p, tr_l, tr_w, transform_train)
    val_ds = FaceDataset(va_p, va_l, va_w, transform_val)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,
                              num_workers=a.workers, pin_memory=True, persistent_workers=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False,
                            num_workers=a.workers, pin_memory=True, persistent_workers=True)

    total = len(tr_l)
    auto_w = [total / (NUM_CLASSES * tc[i]) for i in range(NUM_CLASSES)]
    cw = torch.tensor(auto_w, dtype=torch.float).to(device)
    print("Class weights:", [round(float(x), 4) for x in cw])

    model = DualBranchModel(num_classes=NUM_CLASSES, arch=a.arch).to(device)
    init_state = torch.load(INIT_WEIGHTS, map_location=device) if a.arch == "shufflenet" else {}
    own_state = model.state_dict()
    loaded_keys, fresh_keys = [], []
    for k in own_state:
        if k in init_state and own_state[k].shape == init_state[k].shape:
            own_state[k] = init_state[k]; loaded_keys.append(k)
        else:
            fresh_keys.append(k)
    model.load_state_dict(own_state)
    unused = [k for k in init_state if k not in own_state
              or own_state[k].shape != init_state[k].shape]
    print(f"Warm start from {Path(INIT_WEIGHTS).name}: {len(loaded_keys)} loaded, "
          f"{len(fresh_keys)} fresh: {fresh_keys}", flush=True)

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.1, reduction="none")

    best_f1, best_epoch, rows = 0.0, -1, []
    log_path = ROUND / f"train_{ARM}_s{SEED}_log.csv"

    for epoch in range(1, EPOCHS + 1):
        model.train(); total_loss = 0.0
        for imgs, labels, sw in train_loader:
            imgs = imgs.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            sw = sw.to(device, non_blocking=True).float()
            optimizer.zero_grad()
            if random.random() < 0.5:
                imgs_m, ya, yb, wa, wb, lam = mixup_batch(imgs, labels, sw, MIXUP_ALPHA)
                logits = model(imgs_m)
                w_eff = lam * wa + (1 - lam) * wb
                loss = (w_eff * (lam * criterion(logits, ya)
                                 + (1 - lam) * criterion(logits, yb))).mean()
            else:
                loss = (sw * criterion(model(imgs), labels)).mean()
            loss.backward(); optimizer.step()
            total_loss += loss.item() * imgs.size(0)
        scheduler.step()

        model.eval(); preds, trues = [], []
        with torch.no_grad():
            for imgs, labels, _ in val_loader:
                out = model(imgs.to(device, non_blocking=True)).argmax(1).cpu().numpy()
                if NUM_CLASSES == 3:
                    out = np.where(out == 2, 0, out)   # declared projection: fake+filter -> fake
                preds.extend(out.tolist()); trues.extend(labels.tolist())

        f1 = f1_score(trues, preds, average="macro")
        f1p = f1_score(trues, preds, average=None, labels=[0, 1], zero_division=0)
        acc = accuracy_score(trues, preds)
        avg_loss = total_loss / len(train_ds)
        print(f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f}  Acc={acc:.4f}  F1={f1:.4f}"
              f"  [fake={f1p[0]:.3f} filter={f1p[1]:.3f}]", flush=True)
        rows.append([epoch, f"{avg_loss:.4f}", f"{acc:.4f}", f"{f1:.4f}",
                     f"{f1p[0]:.4f}", f"{f1p[1]:.4f}"])
        pd.DataFrame(rows, columns=["epoch", "loss", "acc", "f1_macro",
                                    "f1_fake", "f1_filter"]).to_csv(log_path, index=False)
        if f1 > best_f1:
            best_f1, best_epoch = f1, epoch
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  -> Saved (F1={best_f1:.4f})", flush=True)

    (ROUND / f"train_meta_{ARM}_s{SEED}.json").write_text(json.dumps(dict(
        round="backbone_hier_20260907", arm=ARM, seed=SEED, epochs=EPOCHS,
        batch_size=BATCH_SIZE, lr=LR, mixup_alpha=MIXUP_ALPHA, num_classes=NUM_CLASSES,
        label_convention=({0: "fake", 1: "filter"} if NUM_CLASSES == 2
                          else {0: "fake", 1: "filter", 2: "fake+filter"}),
        init_weights=INIT_WEIGHTS, warm_start_mode="strict=False (name+shape match)",
        n_tensors_loaded=len(loaded_keys), n_tensors_fresh=len(fresh_keys),
        fresh_tensors=fresh_keys, init_tensors_unused=unused,
        weights_out=WEIGHTS_PATH, train_split=str(TRAIN_SPLIT), val_split=str(VAL_SPLIT),
        train_rows_kept=len(tr_p), train_rows_dropped_missing=tr_miss,
        train_label_counts={str(k): v for k, v in sorted(tc.items())},
        n_rows_with_nonunit_weight=n_dw,
        val_rows_kept=len(va_p), val_label_counts={str(k): v for k, v in sorted(vc.items())},
        class_weights=[float(x) for x in cw],
        val_selection_note=("3-way argmax projected to 2-way (class2->fake) before macro-F1"
                            if NUM_CLASSES == 3 else "plain 2-way macro-F1"),
        best_macro_f1=best_f1, best_epoch=best_epoch), indent=2), encoding="utf-8")
    print(f"\nBest macro F1: {best_f1:.4f} (epoch {best_epoch})\nWeights: {WEIGHTS_PATH}")
