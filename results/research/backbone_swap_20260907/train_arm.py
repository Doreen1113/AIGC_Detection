"""
flat3class_revisit_20260828 -- train a flat 3-class model (arm F1) or a
multi-label two-sigmoid-head model (arm ML) on the CURRENT production-era
training corpus.

Recipe is the same as p1a3_ratio_sweep_20260827/train_p1a3_ratio.py
(RECIPEGAP lineage recipe: Adam LR=1e-4, 10 epochs, batch 192, mixup off,
CosineAnnealingLR, inverse-frequency class weights, label smoothing 0.1, same
transforms). The only differences are structural and unavoidable:
  * one model instead of two, with a 3-way head (F1) or two 1-way sigmoid
    heads (ML) instead of two 2-way heads;
  * warm start from the last flat 3-class production model (v8.8) rather than
    from the Layer1/Layer2 pair, since those have 2-way heads.

python train_flat3.py --arm F1 --seed 20260828
python train_flat3.py --arm ML --seed 20260828
"""
import argparse
import random
import time
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
ROUND = "backbone_swap_20260907"
CKPT_DIR = BASE / "checkpoints" / "research" / ROUND
RES = BASE / "results" / "research" / ROUND
TRAIN_SPLIT = BASE / "results" / "research" / "flat3class_revisit_20260828" / "flat3_train.txt"
VAL_SPLIT = BASE / "results" / "research" / "flat3class_revisit_20260828" / "flat3_val.txt"
WARMSTART = BASE / "archive" / "checkpoints_legacy_v3_v89" / "shufflenet_v2_3class_v88.pth"

transform_train = transforms.Compose([
    transforms.Resize((224, 224)), transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2, 0.2), transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(), transforms.Normalize([0.5] * 3, [0.5] * 3)])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3)])


def load_split(p):
    paths, labels, multi = [], [], []
    n_missing = 0
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t") or not line.strip():
            continue
        f, lab, _src, syn, hf = line.split("\t")
        if not Path(f).is_file():
            n_missing += 1
            continue
        paths.append(f)
        labels.append(int(lab))
        multi.append((int(syn), int(hf)))
    if n_missing:
        print(f"[load_split] {p}: dropped {n_missing:,} rows with missing files", flush=True)
    return paths, labels, multi


class Flat3Dataset(Dataset):
    def __init__(self, paths, labels, transform):
        self.paths, self.labels, self.transform = paths, labels, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        return self.transform(Image.open(self.paths[i]).convert("RGB")), self.labels[i]


class MultiLabelDataset(Dataset):
    def __init__(self, paths, multi, transform):
        self.paths, self.multi, self.transform = paths, multi, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        y = torch.tensor(self.multi[i], dtype=torch.float)
        return self.transform(Image.open(self.paths[i]).convert("RGB")), y


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4), nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU())

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho")
        f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


def _build_spatial(arch, pretrained=True):
    """Same spatial backbones as AIGuard/train_ffpp_improve.py, so the MobileNetV4 branch is
    exactly the one benchmarked on FF++ and cross-dataset (timm
    mobilenetv4_conv_small.e2400_r224_in1k, 960-d features)."""
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights="IMAGENET1K_V1" if pretrained else None)
        bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k",
                          pretrained=pretrained, num_classes=0)
    m.eval()
    with torch.no_grad():                     # num_features is the pre-head width (960);
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]   # the forward output is 1280
    return m, int(dim)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["BIN_N", "BIN_R", "BIN_F", "TERN"])
    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])
    ap.add_argument("--seed", type=int, default=20260906)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch", type=int, default=192)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()

    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    torch.cuda.manual_seed_all(a.seed)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    RES.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tr_p, tr_l, tr_m = load_split(TRAIN_SPLIT)
    va_p, va_l, va_m = load_split(VAL_SPLIT)
    multilabel = False

    def remap(paths, labels):
        """Label space of this arm. Source labels: 0 real, 1 fake, 2 filter."""
        if a.arm == "TERN":
            return list(paths), list(labels)
        if a.arm == "BIN_N":                       # drop filter rows entirely
            keep = [(p, l) for p, l in zip(paths, labels) if l != 2]
            return [p for p, _ in keep], [l for _, l in keep]
        if a.arm == "BIN_R":                       # filter -> real
            return list(paths), [0 if l == 2 else l for l in labels]
        if a.arm == "BIN_F":                       # filter -> fake
            return list(paths), [1 if l == 2 else l for l in labels]
        raise ValueError(a.arm)

    n_before = len(tr_p)
    tr_p, tr_l = remap(tr_p, tr_l)
    va_p, va_l = remap(va_p, va_l)
    NC = 3 if a.arm == "TERN" else 2

    model = DualBranchModel(NC, a.arch).to(device)
    sd = torch.load(WARMSTART, map_location=device) if a.arch == "shufflenet" else {}
    # EVERY arm re-initialises the final Linear layer, so no arm gets a head-shaped
    # advantage from the 3-class warm start (see PRE_DECLARED).
    sd = {k: v for k, v in sd.items() if not k.startswith("classifier.3.")}
    res = model.load_state_dict(sd, strict=False)
    print(f"[{a.arm}] classes={NC} rows {n_before:,} -> {len(tr_p):,}  warm start "
          f"{WARMSTART.name}: partial load, reinit={list(res.missing_keys)}", flush=True)

    if multilabel:
        tr_ds = MultiLabelDataset(tr_p, tr_m, transform_train)
        va_ds = MultiLabelDataset(va_p, va_m, transform_val)
        ys = np.array(tr_m)
        pw = torch.tensor([(len(ys) - ys[:, j].sum()) / max(ys[:, j].sum(), 1)
                           for j in range(2)], dtype=torch.float).to(device)
        crit = nn.BCEWithLogitsLoss(pos_weight=pw)
        print(f"[{a.arm}] rows={len(tr_p):,} is_synthetic_pos={int(ys[:, 0].sum()):,} "
              f"has_filter_pos={int(ys[:, 1].sum()):,} both={int((ys.sum(1) == 2).sum()):,} "
              f"pos_weight={[round(x, 4) for x in pw.tolist()]}", flush=True)
    else:
        tr_ds = Flat3Dataset(tr_p, tr_l, transform_train)
        va_ds = Flat3Dataset(va_p, va_l, transform_val)
        counts = Counter(tr_l)
        n = len(tr_l)
        cw = torch.tensor([n / (NC * counts[i]) for i in range(NC)], dtype=torch.float).to(device)
        crit = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.1)
        print(f"[{a.arm}] rows={n:,} counts={dict(sorted(counts.items()))} "
              f"class_weight={[round(x, 4) for x in cw.tolist()]}", flush=True)

    tl = DataLoader(tr_ds, batch_size=a.batch, shuffle=True, num_workers=a.workers,
                    pin_memory=True, persistent_workers=True)
    vl = DataLoader(va_ds, batch_size=a.batch, shuffle=False, num_workers=max(2, a.workers // 2),
                    pin_memory=True, persistent_workers=True)

    opt = torch.optim.Adam(model.parameters(), lr=a.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=a.epochs)

    best_f1, rows_log, best_sd = -1.0, [], None
    t0 = time.time()
    for epoch in range(1, a.epochs + 1):
        model.train()
        tot = 0.0
        for imgs, lab in tl:
            imgs, lab = imgs.to(device, non_blocking=True), lab.to(device, non_blocking=True)
            opt.zero_grad()
            loss = crit(model(imgs), lab)
            loss.backward()
            opt.step()
            tot += loss.item() * imgs.size(0)
        sched.step()

        model.eval()
        pv, tv_ = [], []
        with torch.no_grad():
            for imgs, lab in vl:
                o = model(imgs.to(device))
                if multilabel:
                    pv.extend((torch.sigmoid(o) > 0.5).int().cpu().tolist())
                    tv_.extend(lab.int().tolist())
                else:
                    pv.extend(o.argmax(1).cpu().tolist())
                    tv_.extend(lab.tolist())
        f1 = f1_score(tv_, pv, average="macro")
        acc = accuracy_score(tv_, pv)
        avg = tot / len(tr_p)
        print(f"[{a.arm}][{epoch:02d}/{a.epochs}] loss={avg:.4f} acc={acc:.4f} F1={f1:.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)
        rows_log.append([epoch, avg, acc, f1])
        if f1 > best_f1:
            best_f1 = f1
            best_sd = {k: v.detach().clone() for k, v in model.state_dict().items()}
            print(f"  -> new best (F1={best_f1:.4f})", flush=True)

    pd.DataFrame(rows_log, columns=["epoch", "loss", "acc", "f1"]).to_csv(
        RES / f"train_log_{a.arm}.csv", index=False)
    out = CKPT_DIR / f"tern_{a.arm}_{a.arch}_seed{a.seed}.pth"
    torch.save(best_sd, out)
    print(f"[{a.arm}] done best_F1={best_f1:.4f} "
          f"params={sum(p.numel() for p in model.parameters()):,} "
          f"wall={time.time() - t0:.0f}s -> {out}", flush=True)


if __name__ == "__main__":
    main()
