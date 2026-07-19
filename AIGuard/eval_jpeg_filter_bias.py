"""
Inference-time experiment: JPEG normalization + filter logit bias.
No retraining needed — tests preprocessing and logit adjustment on v5.1 weights.

JPEG quality: re-encode image at fixed quality before inference
Filter bias:  subtract value from filter logit before softmax (reduces OOD→filter)

python AIGuard/eval_jpeg_filter_bias.py
python AIGuard/eval_jpeg_filter_bias.py --jpeg_q 75 --filter_bias 1.0
python AIGuard/eval_jpeg_filter_bias.py --jpeg_q 0  --filter_bias 0.0   # baseline
"""
import io, csv, argparse
import torch, torch.nn as nn, torch.nn.functional as F
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score
from collections import defaultdict

BASE   = Path(r"C:\My_Project\AIGC")
CKPT   = BASE / "shufflenet_v2_3class_v5_1.pth"
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


def jpeg_preprocess(pil_img, quality):
    """Re-encode at fixed JPEG quality to normalize compression artifacts."""
    if quality <= 0:
        return pil_img
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def predict(model, paths, jpeg_q, filter_bias):
    probs_notreal, preds3 = [], []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB")
            if jpeg_q > 0:
                img = jpeg_preprocess(img, jpeg_q)
            x = transform(img).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                logits = model(x)[0]
                if filter_bias != 0.0:
                    logits[2] -= filter_bias
                soft = F.softmax(logits, dim=0)
            probs_notreal.append((soft[1]+soft[2]).item())
            preds3.append(soft.argmax().item())
        except Exception:
            probs_notreal.append(0.5); preds3.append(0)
    return probs_notreal, preds3


def report(name, labels, probs, preds3):
    auroc = roc_auc_score(labels, probs)
    dist = defaultdict(int)
    for p in preds3: dist[["real","fake","filter"][p]] += 1
    filter_pct = 100 * dist["filter"] / max(1, len(preds3))
    print(f"  {name}: AUROC={auroc:.4f}  "
          f"[real={dist['real']} fake={dist['fake']} filter={dist['filter']} ({filter_pct:.1f}%)]")
    return auroc


def eval_unseen(model, jpeg_q, filter_bias):
    txt = BASE / "AIGuard/unseen/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        name = Path(p).name.lower()
        if name.startswith("real"):   labels.append(0); paths.append(p)
        elif name.startswith("fake"): labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths, jpeg_q, filter_bias)
    return report("AIGuard/unseen", labels, probs, preds3)


def eval_fakeclue(model, jpeg_q, filter_bias):
    rows = list(csv.DictReader(open(BASE/"FakeClue/test_clean/labels.csv", encoding="utf-8")))
    paths  = [r["path"] for r in rows]
    labels = [1-int(r["label"]) for r in rows]
    probs, preds3 = predict(model, paths, jpeg_q, filter_bias)
    return report("FakeClue/test ", labels, probs, preds3)


def eval_wilddeepfake(model, jpeg_q, filter_bias):
    txt = BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt"
    paths, labels = [], []
    for p in txt.read_text().splitlines():
        if not Path(p).name.startswith("test_"): continue
        norm = p.replace("\\", "/")
        if "/real/" in norm:   labels.append(0); paths.append(p)
        elif "/fake/" in norm: labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths, jpeg_q, filter_bias)
    return report("WildDeepfake  ", labels, probs, preds3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--jpeg_q",     type=int,   default=75,  help="JPEG re-encode quality (0=off)")
    parser.add_argument("--filter_bias",type=float, default=1.0, help="Subtract from filter logit (0=off)")
    parser.add_argument("--ckpt",       type=str,   default=str(CKPT))
    args = parser.parse_args()

    model = DualBranchModel().to(DEVICE)
    model.load_state_dict(torch.load(args.ckpt, map_location=DEVICE))
    model.eval()

    configs = [
        (0,           0.0,           "baseline (no change)"),
        (args.jpeg_q, 0.0,           f"jpeg_q={args.jpeg_q} only"),
        (0,           args.filter_bias, f"filter_bias={args.filter_bias} only"),
        (args.jpeg_q, args.filter_bias, f"jpeg_q={args.jpeg_q} + filter_bias={args.filter_bias}"),
    ]

    print(f"\nCheckpoint: {Path(args.ckpt).name}")
    print(f"{'='*65}")

    results = {}
    for jq, fb, label in configs:
        print(f"\n[{label}]")
        u = eval_unseen(model, jq, fb)
        f = eval_fakeclue(model, jq, fb)
        w = eval_wilddeepfake(model, jq, fb)
        results[label] = (u, f, w)

    print(f"\n{'='*65}")
    print(f"{'Config':<40} {'unseen':>8} {'fakeclue':>9} {'wilddf':>8}")
    print(f"{'-'*65}")
    for label, (u, f, w) in results.items():
        print(f"{label:<40} {u:>8.4f} {f:>9.4f} {w:>8.4f}")
