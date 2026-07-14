"""
Cross-dataset eval using binary ShuffleNetV2 (baseline v2).
Compares with v3 DualBranch to check if 3-class filter absorption is the OOD problem.

Runs on:
  1. AIGuard/unseen (454 images, real=238 fake=216)
  2. FakeClue/test  (1166 images, from test_clean/labels.csv)
  3. WildDeepfake test_ prefix (506 images)
"""

import os, csv, sys
import torch
import torch.nn.functional as F
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from collections import defaultdict

BASE   = Path(r"C:\My_Project\AIGC")
CKPT   = BASE / "results/baseline_v2_ckpts/ShuffleNetV2_best.pth"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

transform = T.Compose([
    T.Resize(256), T.CenterCrop(224), T.ToTensor(),
    T.Normalize([0.485,0.456,0.406],[0.229,0.224,0.225]),
])


def load_model():
    model = tv_models.shufflenet_v2_x1_0(weights=None)
    model.fc = torch.nn.Linear(1024, 2)
    state = torch.load(CKPT, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE).eval()
    return model


def predict_batch(model, paths):
    probs_fake = []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB")
            x = transform(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits = model(x)
                prob = F.softmax(logits, dim=1)[0, 1].item()  # P(fake)
            probs_fake.append(prob)
        except Exception:
            probs_fake.append(0.5)
    return probs_fake


def report(name, labels, probs, groups=None):
    auroc = roc_auc_score(labels, probs)
    preds = [1 if p > 0.5 else 0 for p in probs]
    acc = accuracy_score(labels, preds)
    f1  = f1_score(labels, preds, zero_division=0)
    print(f"\n{'='*50}")
    print(f"  {name}")
    print(f"  n={len(labels)}  (real={labels.count(0)}  fake={labels.count(1)})")
    print(f"  AUROC={auroc:.4f}  Acc={acc:.4f}  F1={f1:.4f}")
    if groups:
        for gname, (glabels, gprobs) in groups.items():
            if len(set(glabels)) > 1:
                gauc = roc_auc_score(glabels, gprobs)
                print(f"    [{gname}] n={len(glabels)}  AUROC={gauc:.4f}")
    return auroc


def eval_unseen(model):
    txt = BASE / "AIGuard/unseen/clean_output/clean_paths.txt"
    paths = txt.read_text().splitlines()
    labels, valid_paths = [], []
    for p in paths:
        name = Path(p).name.lower()
        if name.startswith("real"):
            labels.append(0); valid_paths.append(p)
        elif name.startswith("fake"):
            labels.append(1); valid_paths.append(p)
    probs = predict_batch(model, valid_paths)
    report("AIGuard/unseen  [Binary v2]", labels, probs)


def eval_fakeclue(model):
    labels_csv = BASE / "FakeClue/test_clean/labels.csv"
    rows = list(csv.DictReader(open(labels_csv, encoding="utf-8")))
    paths  = [r["path"] for r in rows]
    labels = [1 - int(r["label"]) for r in rows]  # labels.csv: 0=fake,1=real → flip to 0=real,1=fake
    cates  = [r["cate"] for r in rows]
    probs  = predict_batch(model, paths)

    groups = defaultdict(lambda: ([], []))
    for lbl, prob, cate in zip(labels, probs, cates):
        groups[cate][0].append(lbl)
        groups[cate][1].append(prob)

    report("FakeClue/test  [Binary v2]", labels, probs,
           groups={k: (v[0], v[1]) for k, v in groups.items()})


def eval_wilddeepfake(model):
    txt = BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt"
    paths = txt.read_text().splitlines()
    valid_paths, labels = [], []
    for p in paths:
        name = Path(p).name
        if not name.startswith("test_"):
            continue
        norm = p.replace("\\", "/")
        if "/real/" in norm:
            labels.append(0); valid_paths.append(p)
        elif "/fake/" in norm:
            labels.append(1); valid_paths.append(p)
    probs = predict_batch(model, valid_paths)
    report("WildDeepfake/test  [Binary v2]", labels, probs)


if __name__ == "__main__":
    print(f"Device: {DEVICE}")
    print(f"Checkpoint: {CKPT}")
    if not CKPT.exists():
        print("ERROR: checkpoint not found"); sys.exit(1)

    model = load_model()
    print("Model loaded.")

    eval_unseen(model)
    eval_fakeclue(model)
    eval_wilddeepfake(model)

    print("\n=== Reference: v3 DualBranch results ===")
    print("  AIGuard/unseen:    AUROC=0.640")
    print("  FakeClue/test:     AUROC=0.540  (deepfake=0.512  human=0.636)")
    print("  WildDeepfake/test: not yet evaluated")
