"""
Cross-dataset eval for v3.1 DualBranch model.
Binary AUROC: P(not-real) = P(fake) + P(filter)

Datasets:
  1. AIGuard/unseen  (filename-based label: Real_/Fake_)
  2. FakeClue/test   (labels.csv, 0=fake→flip to 1, 1=real→0)
  3. WildDeepfake/test_ prefix (path-based: /real/ or /fake/)

Compare with v3:  unseen=0.640  FakeClue=0.540  WildDeepfake=N/A

python AIGuard/eval_crossdataset_v3_1.py
"""
import csv, torch, torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from collections import defaultdict

import argparse
_p = argparse.ArgumentParser()
_p.add_argument("--ckpt", default="shufflenet_v2_3class_v3_1.pth")
_args, _ = _p.parse_known_args()

BASE   = Path(r"C:\My_Project\AIGC")
CKPT   = BASE / _args.ckpt
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

transform = T.Compose([
    T.Resize(224), T.CenterCrop(224), T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2, -1))
        return self.net(torch.log(torch.abs(fft) + 1e-8))


class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1024+256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, 3))
    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


def load_model():
    m = DualBranchModel().to(DEVICE)
    m.load_state_dict(torch.load(CKPT, map_location=DEVICE))
    m.eval()
    return m


def predict(model, paths):
    """Returns (prob_not_real, pred_3class) per image."""
    probs_notreal, preds3 = [], []
    import torch.nn.functional as F
    for p in paths:
        try:
            x = transform(Image.open(p).convert("RGB")).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                soft = F.softmax(model(x), dim=1)[0]
            probs_notreal.append((soft[1] + soft[2]).item())
            preds3.append(soft.argmax().item())
        except Exception:
            probs_notreal.append(0.5); preds3.append(0)
    return probs_notreal, preds3


def report(name, labels, probs, preds3=None, groups=None):
    auroc = roc_auc_score(labels, probs)
    bin_preds = [1 if p > 0.5 else 0 for p in probs]
    acc = accuracy_score(labels, bin_preds)
    f1  = f1_score(labels, bin_preds, zero_division=0)
    print(f"\n{'='*55}")
    print(f"  {name}")
    print(f"  n={len(labels)}  real={labels.count(0)}  notreal={labels.count(1)}")
    print(f"  AUROC={auroc:.4f}  Acc={acc:.4f}  F1={f1:.4f}")
    if preds3 and labels:
        dist = defaultdict(int)
        for p in preds3: dist[["real","fake","filter"][p]] += 1
        print(f"  3-class dist: real={dist['real']}  fake={dist['fake']}  filter={dist['filter']}")
        filter_pct = 100 * dist['filter'] / len(preds3)
        print(f"  OOD→filter: {filter_pct:.1f}%")
    if groups:
        for g, (gl, gp) in groups.items():
            if len(set(gl)) > 1:
                print(f"    [{g}] n={len(gl)}  AUROC={roc_auc_score(gl, gp):.4f}")
    return auroc


def eval_unseen(model):
    txt = BASE / "AIGuard/unseen/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        name = Path(p).name.lower()
        if name.startswith("real"):   labels.append(0); paths.append(p)
        elif name.startswith("fake"): labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths)
    report("AIGuard/unseen  [v3.1]", labels, probs, preds3)


def eval_fakeclue(model):
    rows = list(csv.DictReader(open(BASE / "FakeClue/test_clean/labels.csv", encoding="utf-8")))
    paths  = [r["path"] for r in rows]
    labels = [1 - int(r["label"]) for r in rows]
    cates  = [r["cate"] for r in rows]
    probs, preds3 = predict(model, paths)
    groups = defaultdict(lambda: ([], []))
    for l, p, c in zip(labels, probs, cates):
        groups[c][0].append(l); groups[c][1].append(p)
    report("FakeClue/test  [v3.1]", labels, probs, preds3,
           groups={k: (v[0], v[1]) for k, v in groups.items()})


def eval_wilddeepfake(model):
    txt = BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        if not Path(p).name.startswith("test_"): continue
        norm = p.replace("\\", "/")
        if "/real/" in norm:   labels.append(0); paths.append(p)
        elif "/fake/" in norm: labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths)
    report("WildDeepfake/test  [v3.1]", labels, probs, preds3)


if __name__ == "__main__":
    print(f"Device: {DEVICE}  |  Checkpoint: {CKPT.name}")
    model = load_model()

    eval_unseen(model)
    eval_fakeclue(model)
    eval_wilddeepfake(model)

    print("\n" + "="*55)
    print("  Reference: v3 DualBranch")
    print("    AIGuard/unseen:    AUROC=0.640  OOD→filter ~?%")
    print("    FakeClue/test:     AUROC=0.540  OOD→filter 58%")
    print("    WildDeepfake/test: AUROC=0.418  (binary v2 ref)")
