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
import argparse, csv, io, torch, torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score
from collections import defaultdict

BASE   = Path(r"C:\My_Project\AIGC")
CKPT = BASE / "shufflenet_v2_3class_ffhq_v3.pth"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
IMG_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".webp"}
REAL_DIRECT_THRESHOLD = 0.6

transform = T.Compose([
    T.Resize(224), T.CenterCrop(224), T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])
tta_resize = T.Resize(256)
to_tensor = T.Compose([
    T.ToTensor(),
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


def apply_clahe(img):
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("CLAHE needs opencv-python. Install it with: pip install opencv-python") from exc
    rgb = np.array(img)
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab = cv2.merge((clahe.apply(l_chan), a_chan, b_chan))
    return Image.fromarray(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB))


def apply_jpeg_normalization(img, quality):
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=False)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def preprocess_image(img, mode, jpeg_quality):
    if mode in {"clahe", "clahe-jpeg"}:
        img = apply_clahe(img)
    if mode in {"jpeg", "clahe-jpeg"}:
        img = apply_jpeg_normalization(img, jpeg_quality)
    return img


def make_input_batch(img, use_tta):
    if not use_tta:
        return transform(img).unsqueeze(0)
    crops = T.FiveCrop(224)(tta_resize(img))
    crops = list(crops) + [crop.transpose(Image.FLIP_LEFT_RIGHT) for crop in crops]
    return torch.stack([to_tensor(crop) for crop in crops])


def two_stage_pred(soft, real_threshold=REAL_DIRECT_THRESHOLD):
    if float(soft[0]) > real_threshold:
        return 0
    return 1 if float(soft[1]) >= float(soft[2]) else 2


def fake_prior_pred(soft, real_threshold=REAL_DIRECT_THRESHOLD, margin=0.1):
    if float(soft[0]) > real_threshold:
        return 0
    return 1 if float(soft[2]) - float(soft[1]) < margin else 2


def predict(model, paths, preprocess="none", jpeg_quality=90, use_tta=False,
            two_stage=False, filter_logit_bias=0.0, fake_prior_margin=None):
    """Returns (prob_not_real, pred_3class) per image."""
    probs_notreal, preds3 = [], []
    import torch.nn.functional as F
    for p in paths:
        try:
            img = Image.open(p).convert("RGB")
            img = preprocess_image(img, preprocess, jpeg_quality)
            x = make_input_batch(img, use_tta).to(DEVICE)
            with torch.no_grad():
                logits = model(x)
                if filter_logit_bias:
                    logits[:, 2] -= filter_logit_bias
                soft = F.softmax(logits, dim=1).mean(dim=0)
            probs_notreal.append((soft[1] + soft[2]).item())
            if fake_prior_margin is not None:
                preds3.append(fake_prior_pred(soft, margin=fake_prior_margin))
            elif two_stage:
                preds3.append(two_stage_pred(soft))
            else:
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


def eval_unseen(model, args):
    txt = BASE / "AIGuard/unseen/clean_output/clean_paths.txt"
    paths, labels = [], []
    if txt.exists():
        raw_paths = [p for p in txt.read_text().splitlines() if p.strip()]
    else:
        root = BASE / "AIGuard/unseen"
        raw_paths = [str(p) for p in root.iterdir() if p.suffix.lower() in IMG_EXTS]
        print(f"  No clean_paths.txt found for AIGuard/unseen -- using all {len(raw_paths)} images")
    for p in raw_paths:
        name = Path(p).name.lower()
        if name.startswith("real"):   labels.append(0); paths.append(p)
        elif name.startswith("fake"): labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths, args.preprocess, args.jpeg_quality, args.tta,
                            args.two_stage, args.filter_logit_bias, args.fake_prior_margin)
    report("AIGuard/unseen  [v3.1]", labels, probs, preds3)


def eval_fakeclue(model, args):
    rows = list(csv.DictReader(open(BASE / "FakeClue/test_clean/labels.csv", encoding="utf-8")))
    paths  = [r["path"] for r in rows]
    labels = [1 - int(r["label"]) for r in rows]
    cates  = [r["cate"] for r in rows]
    probs, preds3 = predict(model, paths, args.preprocess, args.jpeg_quality, args.tta,
                            args.two_stage, args.filter_logit_bias, args.fake_prior_margin)
    groups = defaultdict(lambda: ([], []))
    for l, p, c in zip(labels, probs, cates):
        groups[c][0].append(l); groups[c][1].append(p)
    report("FakeClue/test  [v3.1]", labels, probs, preds3,
           groups={k: (v[0], v[1]) for k, v in groups.items()})


def eval_wilddeepfake(model, args):
    txt = BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt"
    paths, labels = [], []
    if txt.exists():
        raw_paths = [p for p in txt.read_text().splitlines() if p.strip()]
    else:
        root = BASE / "WildDeepfake_subset/images"
        raw_paths = [str(p) for p in root.rglob("*") if p.suffix.lower() in IMG_EXTS]
        print(f"  No clean_paths.txt found for WildDeepfake -- using all {len(raw_paths)} images")
    for p in raw_paths:
        if txt.exists() and not Path(p).name.startswith("test_"): continue
        norm = p.replace("\\", "/")
        if "/real/" in norm:   labels.append(0); paths.append(p)
        elif "/fake/" in norm: labels.append(1); paths.append(p)
    probs, preds3 = predict(model, paths, args.preprocess, args.jpeg_quality, args.tta,
                            args.two_stage, args.filter_logit_bias, args.fake_prior_margin)
    report("WildDeepfake/test  [v3.1]", labels, probs, preds3)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preprocess", choices=["none", "clahe", "jpeg", "clahe-jpeg"], default="none")
    parser.add_argument("--jpeg-quality", type=int, default=90)
    parser.add_argument("--tta", action="store_true", help="Use five-crop + horizontal flip ensemble.")
    parser.add_argument("--two-stage", action="store_true",
                        help="Use P(real)>0.6 direct real, otherwise fake-vs-filter prediction.")
    parser.add_argument("--filter-logit-bias", type=float, default=0.0,
                        help="Subtract this value from the filter logit before softmax.")
    parser.add_argument("--fake-prior-margin", type=float, default=None,
                        help="Use fake-prior rule: if P(filter)-P(fake) is below this margin, predict fake.")
    args = parser.parse_args()

    print(f"Device: {DEVICE}  |  Checkpoint: {CKPT.name}")
    print(f"Preprocess: {args.preprocess}  |  JPEG quality: {args.jpeg_quality}  |  TTA: {args.tta}  |  Two-stage: {args.two_stage}")
    print(f"Filter logit bias: {args.filter_logit_bias}  |  Fake-prior margin: {args.fake_prior_margin}")
    model = load_model()

    eval_unseen(model, args)
    eval_fakeclue(model, args)
    eval_wilddeepfake(model, args)

    print("\n" + "="*55)
    print("  Reference: v3 DualBranch")
    print("    AIGuard/unseen:    AUROC=0.640  OOD→filter ~?%")
    print("    FakeClue/test:     AUROC=0.540  OOD→filter 58%")
    print("    WildDeepfake/test: AUROC=0.418  (binary v2 ref)")
