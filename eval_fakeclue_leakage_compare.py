"""
Compare FakeClue AUROC: full eval set vs. leaked images removed.

Leaked images (dist ≤ 2, training fake ≈ test real):
  FakeClue/test/ff++/real/youtube/c23/frames/700/214.png   (dist=0)
  FakeClue/test/ff++/real/youtube/c23/frames/835/329.png   (dist=2)
  FakeClue/test/ff++/real/youtube/c23/frames/882/053.png   (dist=2)

Usage:
    python eval_fakeclue_leakage_compare.py [--ckpt shufflenet_v2_3class_v81.pth]
"""

import os, csv, argparse
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from sklearn.metrics import roc_auc_score
import numpy as np

_p = argparse.ArgumentParser()
_p.add_argument("--ckpt", default="shufflenet_v2_3class_v81.pth")
_args, _ = _p.parse_known_args()

BASE       = r"C:\My_Project\AIGC"
CKPT       = os.path.join(BASE, _args.ckpt)
LABELS_CSV = os.path.join(BASE, "FakeClue", "test_clean", "labels.csv")

LEAKED = {
    os.path.normcase(os.path.join(BASE, r"FakeClue\test\ff++\real\youtube\c23\frames\700\214.png")),
    os.path.normcase(os.path.join(BASE, r"FakeClue\test\ff++\real\youtube\c23\frames\835\329.png")),
    os.path.normcase(os.path.join(BASE, r"FakeClue\test\ff++\real\youtube\c23\frames\882\053.png")),
}


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
    def __init__(self, num_classes=3):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch     = FFTBranch(out_dim=256)
        self.classifier     = nn.Sequential(
            nn.Linear(1024+256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


transform = T.Compose([
    T.Resize((224, 224)), T.ToTensor(), T.Normalize([0.5]*3, [0.5]*3)])


class SimpleDataset(Dataset):
    def __init__(self, rows):
        self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, idx):
        path, label = self.rows[idx]
        return transform(Image.open(path).convert("RGB")), label, path


def collate(batch):
    imgs   = torch.stack([b[0] for b in batch])
    labels = torch.tensor([b[1] for b in batch])
    paths  = [b[2] for b in batch]
    return imgs, labels, paths


def run_eval(model, rows, device, label):
    ds     = SimpleDataset(rows)
    loader = DataLoader(ds, batch_size=64, shuffle=False, num_workers=0, collate_fn=collate)
    all_labels, all_probs = [], []
    leaked_scores = []

    model.eval()
    with torch.no_grad():
        for imgs, lbls, paths in loader:
            out   = model(imgs.to(device))
            probs = torch.softmax(out, dim=1).cpu().numpy()
            all_labels.extend(lbls.numpy())
            all_probs.extend(probs)
            for i, p in enumerate(paths):
                if os.path.normcase(p) in LEAKED:
                    pred_cls = out[i].argmax().item()
                    leaked_scores.append({
                        "path": os.path.basename(p),
                        "label": lbls[i].item(),
                        "pred_class": ["real","fake","filter"][pred_cls],
                        "p_real": f"{probs[i][0]:.3f}",
                        "p_fake": f"{probs[i][1]:.3f}",
                    })

    all_labels = np.array(all_labels)
    all_probs  = np.array(all_probs)
    prob_fake  = 1.0 - all_probs[:, 0]
    lbl_fake   = 1 - all_labels
    auroc = roc_auc_score(lbl_fake, prob_fake)
    print(f"\n  [{label}]  n={len(rows)}  AUROC={auroc:.4f}")
    return auroc, leaked_scores


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device : {device}")
    print(f"Weights: {CKPT}")

    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device, weights_only=False))

    # Load full eval set
    all_rows = []
    with open(LABELS_CSV, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            p = r["path"].replace("/", os.sep)
            if os.path.exists(p):
                all_rows.append((p, int(r["label"])))
    print(f"\nLoaded {len(all_rows)} rows from labels.csv")

    # Full eval — also captures per-image scores for the 3 leaked images
    auroc_full, leaked_scores = run_eval(model, all_rows, device, "FULL (1166)")

    # Clean eval — remove the 3 leaked images
    clean_rows = [(p, l) for p, l in all_rows if os.path.normcase(p) not in LEAKED]
    auroc_clean, _ = run_eval(model, clean_rows, device, f"CLEAN ({len(clean_rows)})")

    print(f"\n{'='*50}")
    print(f"AUROC full  : {auroc_full:.4f}")
    print(f"AUROC clean : {auroc_clean:.4f}")
    print(f"Difference  : {auroc_clean - auroc_full:+.4f}")

    if leaked_scores:
        print(f"\nModel scores for the 3 leaked images:")
        for s in leaked_scores:
            correct = "✅" if (s["label"]==1 and s["pred_class"]=="real") or \
                               (s["label"]==0 and s["pred_class"]!="real") else "❌"
            print(f"  {correct} {s['path']:12s}  label={'real' if s['label']==1 else 'fake'}"
                  f"  pred={s['pred_class']}  p_real={s['p_real']}  p_fake={s['p_fake']}")
    else:
        print("\n[WARN] Could not find leaked images in eval set (path mismatch?)")
