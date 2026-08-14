"""
Run the remaining v8.11 acceptance gates against the chained Layer1+Layer2
hierarchical pipeline (locked-in candidate: Layer1c + original Layer2):
  - True Test filter recall (>=92%)
  - AIGuard/unseen fake-class AUROC (>=0.70)
  - CelebA real recall (>=95%, 3,000-image subsample)
  - StyleGAN2 fake recall (>=95%, 3,000-image subsample)

3-class-equivalent decision: Layer1 real/manipulated -> if manipulated,
Layer2 fake/filter. P(fake) score for AUROC = P(manipulated) * P(fake|manipulated),
continuous composite score across both layers.

python eval_v811_gates.py [layer1_weights] [layer2_weights]
"""
import argparse, hashlib, json, subprocess, sys, random
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from torchvision import transforms
from sklearn.metrics import roc_auc_score

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))
from pipeline import preprocess_jpeg

# ── P0 Production Evaluation Integrity Repair (2026-08-13) ──────────────────
# This script previously defaulted L1_WEIGHTS to the SUPERSEDED
# shufflenet_v2_layer1_v811c.pth when invoked with no arguments -- a silent
# fallback that produced results/v811_gates_output.txt (Layer1c numbers,
# stale, do not cite as v8.11d production evidence; see
# docs/releases/v8.11_production/ORPHAN_AND_UNVERIFIABLE_REGISTER.md).
# Fail-closed now: explicit --layer1-weights / --layer2-weights are required,
# no default of any kind.
def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE),
                              capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _weight_tag(path):
    s = Path(path).stem
    for pre in ("shufflenet_v2_layer1_", "shufflenet_v2_layer2_", "shufflenet_v2_"):
        if s.startswith(pre):
            return s[len(pre):]
    return s


_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument("--layer1-weights", default=None, help="Path to Layer1 checkpoint (.pth). Required -- no default.")
_parser.add_argument("--layer2-weights", default=None, help="Path to Layer2 checkpoint (.pth). Required -- no default.")
_args = _parser.parse_args()

if not _args.layer1_weights or not _args.layer2_weights:
    print("ERROR: --layer1-weights and --layer2-weights are required. Refusing to fall back to a default checkpoint.")
    sys.exit(1)

L1_WEIGHTS = _args.layer1_weights
L2_WEIGHTS = _args.layer2_weights

if not Path(L1_WEIGHTS).is_file():
    print(f"ERROR: Layer1 weights not found: {L1_WEIGHTS}")
    sys.exit(1)
if not Path(L2_WEIGHTS).is_file():
    print(f"ERROR: Layer2 weights not found: {L2_WEIGHTS}")
    sys.exit(1)

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_SHA256 = _sha256(SCRIPT_PATH)
L1_SHA256 = _sha256(L1_WEIGHTS)
L2_SHA256 = _sha256(L2_WEIGHTS)
GIT_COMMIT = _git_commit()
RUN_TIMESTAMP = datetime.now(timezone.utc).isoformat()
RUN_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
COMMAND_LINE = " ".join(sys.argv)
RELEASE_DIR = BASE / "results" / "releases" / "v8.11_production_20260813"
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

PROVENANCE = {
    "layer1_weights_path": str(Path(L1_WEIGHTS).resolve()),
    "layer1_weights_sha256": L1_SHA256,
    "layer2_weights_path": str(Path(L2_WEIGHTS).resolve()),
    "layer2_weights_sha256": L2_SHA256,
    "script_path": str(SCRIPT_PATH),
    "script_sha256": SCRIPT_SHA256,
    "git_commit": GIT_COMMIT,
    "command_line": COMMAND_LINE,
    "timestamp_utc": RUN_TIMESTAMP,
}
print(f"Layer1: {L1_WEIGHTS}")
print(f"Layer1 SHA256: {L1_SHA256}")
print(f"Layer2: {L2_WEIGHTS}")
print(f"Layer2 SHA256: {L2_SHA256}")
print(f"Script: {SCRIPT_PATH}")
print(f"Script SHA256: {SCRIPT_SHA256}")
print(f"Git commit: {GIT_COMMIT}")
print(f"Timestamp (UTC): {RUN_TIMESTAMP}")
print(f"Command: {COMMAND_LINE}\n")

transform_infer = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3),
])


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU(),
        )

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho")
        f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes)
        )

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


random.seed(42)
device = "cuda" if torch.cuda.is_available() else "cpu"
l1 = DualBranchModel(num_classes=2).to(device)
l1.load_state_dict(torch.load(L1_WEIGHTS, map_location=device))
l1.eval()
l2 = DualBranchModel(num_classes=2).to(device)
l2.load_state_dict(torch.load(L2_WEIGHTS, map_location=device))
l2.eval()
print(f"Device: {device}\n")


def predict(path):
    """Returns (pred_class, p_fake_composite) where pred_class in {0:real,1:fake,2:filter}."""
    pil = Image.open(path).convert("RGB")
    pil = preprocess_jpeg(pil, quality=85)
    t = transform_infer(pil).unsqueeze(0).to(device)
    with torch.no_grad():
        l1_probs = torch.softmax(l1(t), dim=1)[0].cpu().numpy()
    p_manip = float(l1_probs[1])
    if l1_probs.argmax() == 0:
        return 0, p_manip * 0.5  # real; still give a soft score for AUROC continuity
    with torch.no_grad():
        l2_probs = torch.softmax(l2(t), dim=1)[0].cpu().numpy()
    p_fake_given_manip = float(l2_probs[0])
    cls = 1 if l2_probs.argmax() == 0 else 2
    return cls, p_manip * p_fake_given_manip


# ── True Test filter recall ──────────────────────────────────────────────
tt_filter_txt = BASE / "splits" / "truetest_filter.txt"
paths = [l.strip() for l in tt_filter_txt.read_text(encoding="utf-8").splitlines() if l.strip()]
correct = 0
for p in paths:
    cls, _ = predict(p)
    if cls == 2:
        correct += 1
tt_filter_recall = correct / len(paths) * 100
print(f"True Test filter recall: {correct}/{len(paths)} = {tt_filter_recall:.1f}%  (gate: >=92%)")

# ── AIGuard/unseen fake-class AUROC ──────────────────────────────────────
unseen_txt = BASE / "AIGuard" / "unseen" / "clean_output" / "clean_paths.txt"
lines = [l.strip() for l in unseen_txt.read_text(encoding="utf-8").splitlines() if l.strip()]
y_true, y_score = [], []
for line in lines:
    parts = line.split("\t") if "\t" in line else [line]
    p = parts[0]
    label = 1 if "fake" in Path(p).parts[-2].lower() or "fake" in p.lower() else 0
    _, score = predict(p)
    y_true.append(label)
    y_score.append(score)
if len(set(y_true)) > 1:
    unseen_auroc = roc_auc_score(y_true, y_score)
    print(f"AIGuard/unseen fake AUROC: {unseen_auroc:.4f}  (gate: >=0.70, n={len(lines)})")
else:
    print(f"AIGuard/unseen: could not compute AUROC (label parsing issue), n={len(lines)}")

# ── CelebA real recall (subsample 3000 for speed) ────────────────────────
celeba_dir = BASE / "celeba_test"
celeba_imgs = sorted(celeba_dir.glob("*.jpg"))
random.shuffle(celeba_imgs)
celeba_sample = celeba_imgs[:3000]
correct = 0
for p in celeba_sample:
    cls, _ = predict(p)
    if cls == 0:
        correct += 1
celeba_recall = correct / len(celeba_sample) * 100
print(f"CelebA real recall (n={len(celeba_sample)} subsample): {correct}/{len(celeba_sample)} = {celeba_recall:.1f}%  (gate: >=95%)")

# ── StyleGAN2 fake recall (subsample 3000 for speed) ─────────────────────
sg2_dir = BASE / "stylegan2_test" / "fake"
sg2_imgs = sorted(sg2_dir.glob("*.jpg")) + sorted(sg2_dir.glob("*.png"))
random.shuffle(sg2_imgs)
sg2_sample = sg2_imgs[:3000]
correct = 0
for p in sg2_sample:
    cls, _ = predict(p)
    if cls != 0:
        correct += 1
sg2_recall = correct / len(sg2_sample) * 100
print(f"StyleGAN2 not-real recall (n={len(sg2_sample)} subsample): {correct}/{len(sg2_sample)} = {sg2_recall:.1f}%  (gate: >=95%)")

# ── save (P0 Production Evaluation Integrity Repair, 2026-08-13) ──────────
# Never overwrites an existing file: name includes both weight tags and the
# run date. Written only under results/releases/v8.11_production_20260813/.
out_record = {
    "provenance": PROVENANCE,
    "eval_name": "core_gates",
    "gates": {
        "true_test_filter_recall_pct": tt_filter_recall,
        "aiguard_unseen_fake_auroc": unseen_auroc if "unseen_auroc" in dir() else None,
        "celeba_real_recall_pct": celeba_recall,
        "stylegan2_not_real_recall_pct": sg2_recall,
    },
    "sample_sizes": {
        "true_test_filter_n": len(paths),
        "aiguard_unseen_n": len(lines),
        "celeba_n": len(celeba_sample),
        "stylegan2_n": len(sg2_sample),
    },
}

out_name = f"core_gates_{_weight_tag(L1_WEIGHTS)}_layer2{_weight_tag(L2_WEIGHTS)}_{RUN_DATE}.json"
out_path = RELEASE_DIR / out_name
if out_path.exists():
    print(f"ERROR: refusing to overwrite existing result file: {out_path}")
    sys.exit(1)
out_path.write_text(json.dumps(out_record, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n[out] core gate results -> {out_path}")
