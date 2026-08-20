"""
Evaluate filter recall by type on the true held-out test set.
Reports smoothing / whitening / eye_enlarging / face_reshaping separately.

Usage:
  python AIGuard/eval_filter_recall.py --ckpt shufflenet_v2_3class_v6.pth
  python AIGuard/eval_filter_recall.py --ckpt shufflenet_v2_3class_v7.pth
  python AIGuard/eval_filter_recall.py --ckpt shufflenet_v2_3class_v73.pth --tribranch
"""
import argparse, io, torch, torch.nn as nn, torch.nn.functional as F
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from pathlib import Path
from collections import defaultdict


def preprocess_jpeg(img_pil, quality=85):
    """Matches pipeline.py's inference-time JPEG canonicalization (2026-07-29 preprocessing unification)."""
    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

parser = argparse.ArgumentParser()
parser.add_argument("--ckpt", default="shufflenet_v2_3class_v6.pth")
parser.add_argument("--tribranch", action="store_true",
                    help="Use TriBranchModel (v7.3+) instead of DualBranchModel")
args = parser.parse_args()

BASE   = Path(r"C:\My_Project\AIGC")
CKPT   = BASE / args.ckpt
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
FTYPES = ["smoothing", "whitening", "eye_enlarging", "face_reshaping"]

EYE_Y0, EYE_Y1, EYE_X0, EYE_X1 = 65, 125, 20, 204


class FFTBranch(nn.Module):
    def __init__(self, d=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(2048, d), nn.ReLU())

    def forward(self, x):
        fft = torch.fft.fft2(x, norm="ortho")
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
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, 3))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


class EyeROIBranch(nn.Module):
    def __init__(self, out_dim=128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d((4,4)),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        return self.net(x)


class TriBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch     = FFTBranch(256)
        self.eye_branch     = EyeROIBranch(128)
        self.classifier = nn.Sequential(
            nn.Linear(1024 + 256 + 128, 512), nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(512, 3))

    def forward(self, full, eye):
        feat = torch.cat([self.spatial_branch(full),
                          self.fft_branch(full),
                          self.eye_branch(eye)], dim=1)
        return self.classifier(feat)


# Geometric transform now matches pipeline.py's transform_infer exactly (was Resize+CenterCrop, mismatched vs training's direct square Resize)
tf = T.Compose([T.Resize((224, 224)),
                T.ToTensor(), T.Normalize([0.5]*3, [0.5]*3)])
eye_resize = T.Resize((64, 128))

if args.tribranch:
    model = TriBranchModel().to(DEVICE)
else:
    model = DualBranchModel().to(DEVICE)
model.load_state_dict(torch.load(CKPT, map_location=DEVICE))
model.eval()
print(f"Loaded: {CKPT.name}  ({'TriBranch' if args.tribranch else 'DualBranch'}, {DEVICE})")

filter_dir = BASE / "test_set_true" / "filter"
correct = defaultdict(int)
total   = defaultdict(int)

for p in sorted(filter_dir.glob("*.jpg")):
    ftype = next((ft for ft in FTYPES if p.name.startswith(ft + "_")), None)
    if ftype is None:
        continue
    try:
        pil = preprocess_jpeg(Image.open(p).convert("RGB"), quality=85)
        x = tf(pil).unsqueeze(0).to(DEVICE)
        if args.tribranch:
            eye_pil = pil.crop((EYE_X0, EYE_Y0, EYE_X1, EYE_Y1))
            eye = tf(eye_resize(eye_pil)).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                pred = model(x, eye).argmax(1).item()
        else:
            with torch.no_grad():
                pred = model(x).argmax(1).item()
        total[ftype] += 1
        if pred == 2:
            correct[ftype] += 1
    except Exception as e:
        print(f"  [warn] {p.name}: {e}")

print(f"\n=== Filter Recall by Type — {CKPT.name} ===")
all_c, all_t = 0, 0
for ft in FTYPES:
    c, t = correct[ft], total[ft]
    all_c += c; all_t += t
    pct = c / t * 100 if t else 0
    print(f"  {ft:<20s}: {c:3d}/{t:3d} = {pct:.1f}%")
print(f"  {'Overall':<20s}: {all_c:3d}/{all_t:3d} = {all_c/all_t*100:.1f}%")
