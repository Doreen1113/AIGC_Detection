"""
Eval ablation models on cross-dataset benchmarks.
Usage:
  python AIGuard/eval_ablation.py --ckpt shufflenet_v2_3class_ablation_a.pth --tag ablation_a
  python AIGuard/eval_ablation.py --ckpt shufflenet_v2_3class_ablation_b.pth --tag ablation_b
"""
import csv, argparse, torch, torch.nn as nn, torch.nn.functional as F
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score
from collections import defaultdict

BASE   = Path(r"C:\My_Project\AIGC")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

transform = T.Compose([
    T.Resize(224), T.CenterCrop(224), T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2,-1))
        return self.net(torch.log(torch.abs(fft)+1e-8))


class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(nn.Linear(1280,512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512,3))
    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


def predict(model, paths):
    probs_notreal, preds3 = [], []
    for p in paths:
        try:
            x = transform(Image.open(p).convert("RGB")).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                soft = F.softmax(model(x), dim=1)[0]
            probs_notreal.append((soft[1]+soft[2]).item())
            preds3.append(soft.argmax().item())
        except Exception:
            probs_notreal.append(0.5); preds3.append(0)
    return probs_notreal, preds3


def report(name, labels, probs, preds3):
    auroc = roc_auc_score(labels, probs)
    dist = defaultdict(int)
    for p in preds3: dist[["real","fake","filter"][p]] += 1
    print(f"  {name}: AUROC={auroc:.4f}  "
          f"(real={labels.count(0)} notreal={labels.count(1)})  "
          f"3cls: real={dist['real']} fake={dist['fake']} filter={dist['filter']}")
    return auroc


def eval_unseen(model):
    txt = BASE / "AIGuard/unseen/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        name = Path(p).name.lower()
        if name.startswith("real"):   labels.append(0); paths.append(p)
        elif name.startswith("fake"): labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths)
    return report("AIGuard/unseen", labels, probs, preds3)


def eval_fakeclue(model):
    rows = list(csv.DictReader(open(BASE/"FakeClue/test_clean/labels.csv", encoding="utf-8")))
    paths  = [r["path"] for r in rows]
    labels = [1-int(r["label"]) for r in rows]
    probs, preds3 = predict(model, paths)
    return report("FakeClue/test ", labels, probs, preds3)


def eval_wilddeepfake(model):
    txt = BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        if not Path(p).name.startswith("test_"): continue
        norm = p.replace("\\", "/")
        if "/real/" in norm:   labels.append(0); paths.append(p)
        elif "/fake/" in norm: labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths)
    return report("WildDeepfake  ", labels, probs, preds3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", required=True)
    parser.add_argument("--tag",  required=True)
    args = parser.parse_args()

    ckpt = BASE / args.ckpt
    print(f"\n{'='*60}")
    print(f"  [{args.tag}]  {ckpt.name}")
    print(f"{'='*60}")

    model = DualBranchModel().to(DEVICE)
    model.load_state_dict(torch.load(str(ckpt), map_location=DEVICE))
    model.eval()

    u = eval_unseen(model)
    f = eval_fakeclue(model)
    w = eval_wilddeepfake(model)

    print(f"\n  Summary: unseen={u:.4f}  fakeclue={f:.4f}  wilddeepfake={w:.4f}")
