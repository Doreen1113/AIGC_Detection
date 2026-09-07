"""
p1a1_interference_20260905 -- Layer1 trainer with task-interference mitigation.

COPIED FROM `AIGuard/train_advmine_layer1.py` (P1REPRO recipe: Adam 2e-5, batch 256,
mixup a=0.2 p=0.5, CE + label smoothing 0.1, inverse-frequency class weights, cosine,
10 epochs, init = production Layer1 v817sbi, val = splits/v811_layer1_val.txt).
The base recipe is untouched; each arm ADDS exactly one mechanism:

  LWF   learning-without-forgetting: KL(teacher=v817sbi || student), T=2, lambda=1,
        applied to the NON-FF++ rows only (teacher has never seen FF++ and calls swap
        frames real, so distilling it there would teach the wrong thing).
  FAM3  family head: 3-way softmax [real, manip_EFS+filter, manip_swap]; p_manip =
        1 - p_real at inference. Init: final layer's manip row duplicated into both
        family rows with bias - ln2 so the initial p_real is exactly production's.
  L2SP  parameter anchoring: + lambda/2 * ||theta - theta_prod||^2, lambda = 1e-2.

Family tag: a training row is 'swap' iff its path contains 'FaceForensics'.

python train_interference_layer1.py --arm LWF --seed 20260905
"""
import argparse
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as tv_models
from PIL import Image
from sklearn.metrics import accuracy_score, f1_score
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

BASE = Path(r"C:\My_Project\AIGC")
ROUND = "backbone_hier_20260907"
CKPT_DIR = BASE / "checkpoints" / "research" / ROUND
RES = BASE / "results" / "research" / ROUND
INIT_WEIGHTS = BASE / "shufflenet_v2_layer1_v817sbi.pth"  # production Layer1, read-only
TRAIN_SPLIT = BASE / "splits" / "v811_layer1_train.txt"
VAL_SPLIT = BASE / "splits" / "v811_layer1_val.txt"
EPOCHS, BATCH_SIZE, MIXUP_ALPHA, LR = 10, 256, 0.2, 2e-5
KD_T, KD_LAMBDA, L2SP_LAMBDA = 2.0, 1.0, 1e-2

transform_train = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.ColorJitter(0.2, 0.2, 0.2),
    transforms.RandomGrayscale(p=0.05),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3),
])
transform_val = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3)])


class FaceDataset(Dataset):
    def __init__(self, paths, labels, fam, transform=None):
        self.paths, self.labels, self.fam, self.transform = paths, labels, fam, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.labels[idx], self.fam[idx]


def load_split(p):
    paths, labels, fam = [], [], []
    for line in Path(p).read_text(encoding="utf-8").splitlines():
        if line.startswith("path\t"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2:
            paths.append(parts[0]); labels.append(int(parts[1]))
            fam.append(1 if "FaceForensics" in parts[0] else 0)
    return paths, labels, fam


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


def mixup_batch(x, y, alpha=0.2):
    lam = np.random.beta(alpha, alpha) if alpha > 0 else 1.0
    idx = torch.randperm(x.size(0), device=x.device)
    return lam * x + (1 - lam) * x[idx], y, y[idx], lam


def mixup_loss(crit, logits, ya, yb, lam):
    return lam * crit(logits, ya) + (1 - lam) * crit(logits, yb)


def build_fam3_from_prod(sd):
    """Expand the 2-way final layer [real, manip] to [real, manip_efs, manip_swap]
    so that softmax p_real is unchanged at init: both family rows = manip row, bias - ln2."""
    w, b = sd["classifier.3.weight"], sd["classifier.3.bias"]
    w3 = torch.stack([w[0], w[1], w[1]])
    b3 = torch.stack([b[0], b[1] - math.log(2.0), b[1] - math.log(2.0)])
    sd = dict(sd); sd["classifier.3.weight"] = w3; sd["classifier.3.bias"] = b3
    return sd


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["LWF", "FAM3", "L2SP", "BASE"])
    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])
    ap.add_argument("--tag", default=None)
    ap.add_argument("--epochs", type=int, default=EPOCHS)
    ap.add_argument("--seed", type=int, default=20260905)
    a = ap.parse_args()
    tag = a.tag or a.arm

    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    torch.cuda.manual_seed_all(a.seed)
    CKPT_DIR.mkdir(parents=True, exist_ok=True); RES.mkdir(parents=True, exist_ok=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"

    tr_p, tr_l, tr_f = load_split(TRAIN_SPLIT)
    va_p, va_l, va_f = load_split(VAL_SPLIT)
    n_swap = sum(1 for l, f in zip(tr_l, tr_f) if l == 1 and f == 1)
    tc, vc = Counter(tr_l), Counter(va_l)
    print(f"[{tag}] arm={a.arm} seed={a.seed} train={len(tr_p):,} real={tc[0]:,} manip={tc[1]:,} "
          f"(swap-family manip={n_swap:,}, ffpp rows={sum(tr_f):,}) | val={len(va_p):,} real={vc[0]:,} manip={vc[1]:,}", flush=True)

    if a.arm == "FAM3":
        tr_y = [0 if l == 0 else (2 if f == 1 else 1) for l, f in zip(tr_l, tr_f)]
        n_cls = 3
    else:
        tr_y = list(tr_l); n_cls = 2
    yc = Counter(tr_y); total = len(tr_y)
    cw = torch.tensor([total / (n_cls * yc[i]) for i in range(n_cls)], dtype=torch.float).to(device)
    print(f"[{tag}] class weights {[round(float(x), 4) for x in cw]} counts {dict(yc)}", flush=True)

    train_loader = DataLoader(FaceDataset(tr_p, tr_y, tr_f, transform_train), batch_size=BATCH_SIZE,
                              shuffle=True, num_workers=8, pin_memory=True, persistent_workers=True)
    val_loader = DataLoader(FaceDataset(va_p, va_l, va_f, transform_val), batch_size=BATCH_SIZE,
                            shuffle=False, num_workers=8, pin_memory=True, persistent_workers=True)

    model = DualBranchModel(n_cls, a.arch).to(device)
    if a.arch == "shufflenet":
        prod_sd = torch.load(INIT_WEIGHTS, map_location=device)
        model.load_state_dict(build_fam3_from_prod(prod_sd) if a.arm == "FAM3" else prod_sd)
    else:
        prod_sd = None   # MobileNetV4: ImageNet-initialised spatial branch, fresh FFT branch and head
        print(f"[{tag}] arch={a.arch}: no production warm start (ImageNet init)", flush=True)
    teacher = None
    if a.arm == "LWF":
        teacher = DualBranchModel(2, a.arch).to(device); teacher.load_state_dict(prod_sd); teacher.eval()
        for p_ in teacher.parameters():
            p_.requires_grad_(False)
    anchor = {k: v.detach().clone() for k, v in model.named_parameters()} if a.arm == "L2SP" else None

    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=a.epochs)
    criterion = nn.CrossEntropyLoss(weight=cw, label_smoothing=0.1)

    best_f1, rows = 0.0, []
    best_path = CKPT_DIR / f"layer1_{tag}_{a.arch}.pth"
    last_path = CKPT_DIR / f"layer1_{tag}_{a.arch}_last.pth"
    for epoch in range(1, a.epochs + 1):
        model.train(); tot = tot_aux = 0.0
        for imgs, labels, fam in train_loader:
            imgs, labels, fam = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True), fam.to(device)
            optimizer.zero_grad()
            if random.random() < 0.5:
                im, ya, yb, lam = mixup_batch(imgs, labels, MIXUP_ALPHA)
                loss = mixup_loss(criterion, model(im), ya, yb, lam)
            else:
                loss = criterion(model(imgs), labels)
            aux = torch.zeros((), device=device)
            if a.arm == "LWF":
                keep = fam == 0
                if keep.any():
                    with torch.no_grad():
                        t_log = teacher(imgs[keep])
                    s_log = model(imgs[keep])
                    aux = F.kl_div(F.log_softmax(s_log / KD_T, 1), F.softmax(t_log / KD_T, 1),
                                   reduction="batchmean") * (KD_T ** 2) * KD_LAMBDA
            elif a.arm == "L2SP":
                aux = sum(((p_ - anchor[k]) ** 2).sum() for k, p_ in model.named_parameters()) * (L2SP_LAMBDA / 2)
            (loss + aux).backward(); optimizer.step()
            tot += loss.item() * imgs.size(0); tot_aux += float(aux) * imgs.size(0)
        scheduler.step()
        model.eval(); preds, trues = [], []
        with torch.no_grad():
            for imgs, labels, _ in val_loader:
                pr = torch.softmax(model(imgs.to(device)), 1)
                p_manip = (1.0 - pr[:, 0]) if n_cls == 3 else pr[:, 1]
                preds.extend((p_manip >= 0.5).long().cpu().tolist())
                trues.extend(labels.tolist())
        f1 = f1_score(trues, preds, average="macro"); f1p = f1_score(trues, preds, average=None)
        acc = accuracy_score(trues, preds); avg = tot / len(tr_p); avg_aux = tot_aux / len(tr_p)
        print(f"[{tag}][{epoch:02d}/{a.epochs}] loss={avg:.4f} aux={avg_aux:.4f} acc={acc:.4f} "
              f"F1={f1:.4f} [real={f1p[0]:.3f} manip={f1p[1]:.3f}]", flush=True)
        rows.append([epoch, avg, avg_aux, acc, f1, f1p[0], f1p[1]])
        if f1 > best_f1:
            best_f1 = f1
            torch.save(model.state_dict(), best_path)
            print(f"  -> saved best ({best_f1:.4f})", flush=True)
    torch.save(model.state_dict(), last_path)
    pd.DataFrame(rows, columns=["epoch", "loss", "aux", "acc", "f1_macro", "f1_real",
                                "f1_manipulated"]).to_csv(RES / f"train_log_{tag}.csv", index=False)
    print(f"[{tag}] best macro F1={best_f1:.4f} -> {best_path}", flush=True)
