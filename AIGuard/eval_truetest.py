"""
Evaluate v3 DualBranch model on the true held-out test set.
Test set: LFW real (250) + DF40 EFS diffusion fake (270) + LFW+filter (249) = 769 images.

Output:
  results/truetest_v3_results.csv   per-image predictions
  results/truetest_v3_summary.txt   AUROC / Accuracy / per-class breakdown
"""

import csv, sys
import torch, torch.nn as nn, torch.nn.functional as F
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import numpy as np

import argparse
_parser = argparse.ArgumentParser()
_parser.add_argument("--ckpt", default="shufflenet_v2_3class_ffhq_v3.pth")
_parser.add_argument("--out",  default="truetest_v3_results.csv")
_args, _ = _parser.parse_known_args()

BASE   = Path(r"C:\My_Project\AIGC")
CKPT   = BASE / _args.ckpt
OUT_CSV = _args.out
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CLASSES = ["real", "fake", "filter"]

tf = T.Compose([
    T.Resize(224), T.CenterCrop(224),
    T.ToTensor(), T.Normalize([0.5]*3, [0.5]*3)
])


class FFTBranch(nn.Module):
    def __init__(self, d=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(2048, d), nn.ReLU())

    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2,-1))
        return self.net(torch.log(torch.abs(fft) + 1e-8))


class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, 3))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


def load_split(txt_path, label):
    paths = []
    with open(txt_path, encoding="utf-8") as f:
        for line in f:
            p = line.strip()
            if p:
                paths.append((p, label))
    return paths


def infer(model, path):
    try:
        img = Image.open(path).convert("RGB")
        x = tf(img).unsqueeze(0).to(DEVICE)
        with torch.no_grad():
            logits = model(x)
            probs = F.softmax(logits, dim=1)[0].cpu().numpy()
        return probs
    except Exception as e:
        print(f"  [warn] {Path(path).name}: {e}")
        return None


def main():
    print(f"Device: {DEVICE}")
    print(f"Loading model: {CKPT}")
    model = DualBranchModel().to(DEVICE)
    model.load_state_dict(torch.load(CKPT, map_location=DEVICE))
    model.eval()

    # Load splits: real=0, fake=1, filter=2
    data = []
    data += load_split(BASE / "splits/truetest_real.txt",   label=0)
    data += load_split(BASE / "splits/truetest_fake.txt",   label=1)
    data += load_split(BASE / "splits/truetest_filter.txt", label=2)
    print(f"Total images: {len(data)}  (real={sum(1 for _,l in data if l==0)}  "
          f"fake={sum(1 for _,l in data if l==1)}  filter={sum(1 for _,l in data if l==2)})")

    results = []
    for i, (path, gt) in enumerate(data):
        if (i+1) % 100 == 0:
            print(f"  [{i+1}/{len(data)}]")
        probs = infer(model, path)
        if probs is None:
            continue
        pred = int(probs.argmax())
        results.append({
            "path": path,
            "gt": gt,
            "gt_name": CLASSES[gt],
            "pred": pred,
            "pred_name": CLASSES[pred],
            "p_real": float(probs[0]),
            "p_fake": float(probs[1]),
            "p_filter": float(probs[2]),
            "correct": int(pred == gt),
        })

    # Save per-image CSV
    out_dir = BASE / "results"
    out_dir.mkdir(exist_ok=True)
    csv_path = out_dir / OUT_CSV
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader(); w.writerows(results)

    # Compute metrics
    gt_arr   = np.array([r["gt"]   for r in results])
    pred_arr = np.array([r["pred"] for r in results])
    p_real   = np.array([r["p_real"]   for r in results])
    p_fake   = np.array([r["p_fake"]   for r in results])
    p_filter = np.array([r["p_filter"] for r in results])

    acc = (gt_arr == pred_arr).mean()

    # Binary AUROCs (one-vs-rest)
    real_mask   = (gt_arr == 0)
    fake_mask   = (gt_arr == 1)
    filter_mask = (gt_arr == 2)

    # Real vs non-real
    auroc_real = roc_auc_score((gt_arr == 0).astype(int), p_real)
    # Fake vs non-fake
    auroc_fake = roc_auc_score((gt_arr == 1).astype(int), p_fake)
    # Filter vs non-filter
    auroc_filter = roc_auc_score((gt_arr == 2).astype(int), p_filter)

    # Binary: real+filter (non-fake) vs fake — key metric for deepfake detection
    bin_gt    = (gt_arr == 1).astype(int)          # 1=fake, 0=real/filter
    auroc_bin = roc_auc_score(bin_gt, p_fake)

    summary_lines = [
        "=== v3 DualBranch — True Held-out Test Set ===",
        f"  Images: {len(results)}  (real={real_mask.sum()} / fake={fake_mask.sum()} / filter={filter_mask.sum()})",
        "",
        f"  3-class Accuracy : {acc:.4f}",
        "",
        "  AUROC (one-vs-rest):",
        f"    real   vs rest : {auroc_real:.4f}",
        f"    fake   vs rest : {auroc_fake:.4f}",
        f"    filter vs rest : {auroc_filter:.4f}",
        "",
        f"  Binary AUROC (fake vs real+filter) : {auroc_bin:.4f}",
        "",
        "  Classification Report:",
        classification_report(gt_arr, pred_arr, target_names=CLASSES),
        "  Confusion Matrix (rows=GT, cols=Pred):",
        "    real / fake / filter",
    ]
    cm = confusion_matrix(gt_arr, pred_arr)
    for i, row in enumerate(cm):
        summary_lines.append(f"    {CLASSES[i]:6s}: {list(row)}")

    summary = "\n".join(summary_lines)
    print("\n" + summary)

    txt_path = out_dir / OUT_CSV.replace("_results.csv", "_summary.txt")
    txt_path.write_text(summary, encoding="utf-8")
    print(f"\nSaved:\n  {csv_path}\n  {txt_path}")


if __name__ == "__main__":
    main()
