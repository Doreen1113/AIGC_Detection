"""
Robustness stress test: pose angle, lighting, resolution/blur, and multi-stage
JPEG compression, run against the v8.11 hierarchical pipeline (Layer1c +
Layer2) on the True Test set (769 images, known ground truth).

Fills the robustness gap flagged 2026-08-10 in TODO.md: pipeline.py's
preprocess_jpeg only tests a single fixed quality (q85); pose, lighting,
blur, and repeated/social-media-style re-compression were completely
untested before this script. All perturbations are applied at eval time
only (no new training data, no model changes) -- pure inference cost.

python AIGuard/eval_robustness.py [layer1_weights] [layer2_weights]
"""
import argparse
import hashlib
import json
import subprocess
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from torchvision import transforms

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))
from pipeline import preprocess_jpeg

# ── P0 Production Evaluation Integrity Repair (2026-08-13) ──────────────────
# Previously defaulted L1_WEIGHTS to the SUPERSEDED shufflenet_v2_layer1_v811c.pth
# when invoked with no arguments. Fail-closed now: explicit --layer1-weights /
# --layer2-weights are required, no default.
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


def _wtag(path):
    """Name outputs after the weights actually loaded -- see the 2026-08-11 note
    in AIGuard/stress_test_v811_pipeline.py. A script that takes weights as
    arguments but writes to a fixed filename is a version-mismatch trap."""
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

MODEL_PATH = str(BASE / "face_landmarker.task")
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

OUT_JSON = RELEASE_DIR / f"robustness_eval_{_wtag(L1_WEIGHTS)}_layer2{_wtag(L2_WEIGHTS)}_{RUN_DATE}.json"
if OUT_JSON.exists():
    print(f"ERROR: refusing to overwrite existing result file: {OUT_JSON}")
    sys.exit(1)

CLASS_NAMES = ["real", "fake", "filter"]

transform_infer = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3),
])


# ── model (same arch as eval_v811_gates.py) ──────────────────────────────
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


device = "cuda" if torch.cuda.is_available() else "cpu"
l1 = DualBranchModel(num_classes=2).to(device)
l1.load_state_dict(torch.load(L1_WEIGHTS, map_location=device))
l1.eval()
l2 = DualBranchModel(num_classes=2).to(device)
l2.load_state_dict(torch.load(L2_WEIGHTS, map_location=device))
l2.eval()
print(f"Layer1: {L1_WEIGHTS}")
print(f"Layer1 SHA256: {L1_SHA256}")
print(f"Layer2: {L2_WEIGHTS}")
print(f"Layer2 SHA256: {L2_SHA256}")
print(f"Script: {SCRIPT_PATH}")
print(f"Script SHA256: {SCRIPT_SHA256}")
print(f"Git commit: {GIT_COMMIT}")
print(f"Timestamp (UTC): {RUN_TIMESTAMP}")
print(f"Command: {COMMAND_LINE}")
print(f"Device: {device}\n")


def predict_pil(pil_img, jpeg_quality=85, skip_canonical_jpeg=False):
    """Runs the full hierarchical pipeline on an already-perturbed PIL image.
    skip_canonical_jpeg=True lets the multi-JPEG test control compression
    itself instead of always re-encoding once more at q85."""
    if not skip_canonical_jpeg:
        pil_img = preprocess_jpeg(pil_img, quality=jpeg_quality)
    t = transform_infer(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        l1_probs = torch.softmax(l1(t), dim=1)[0].cpu().numpy()
    if l1_probs.argmax() == 0:
        return 0
    with torch.no_grad():
        l2_probs = torch.softmax(l2(t), dim=1)[0].cpu().numpy()
    return 1 if l2_probs.argmax() == 0 else 2


# ── True Test set ─────────────────────────────────────────────────────────
def load_truetest():
    items = []
    for fname, label in (("truetest_real.txt", 0), ("truetest_fake.txt", 1), ("truetest_filter.txt", 2)):
        p = BASE / "splits" / fname
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                items.append((line, label))
    return items


TRUETEST = load_truetest()
print(f"True Test set: {len(TRUETEST)} images "
      f"(real={sum(1 for _, l in TRUETEST if l == 0)}, "
      f"fake={sum(1 for _, l in TRUETEST if l == 1)}, "
      f"filter={sum(1 for _, l in TRUETEST if l == 2)})\n")


def recall_by_class(preds_labels):
    """preds_labels: list of (pred_cls, true_cls). Returns dict incl. overall + per-class recall."""
    total = len(preds_labels)
    correct = sum(1 for p, t in preds_labels if p == t)
    out = {"overall_acc": correct / total * 100, "n": total}
    for cls_idx, cls_name in enumerate(CLASS_NAMES):
        sub = [(p, t) for p, t in preds_labels if t == cls_idx]
        if sub:
            c = sum(1 for p, t in sub if p == t)
            out[f"{cls_name}_recall"] = c / len(sub) * 100
    # 2026-08-11: also record the full 3x3 confusion. Per-class recall alone
    # cannot tell WHERE a class's losses went, which left the lighting-family
    # behaviour undiagnosable (lighting -30% drops real AND filter recall
    # simultaneously -- impossible under a simple boundary shift, but without
    # the confusion matrix we could not tell whether filter losses went to
    # 'real' or to 'fake'). See docs/paper_outline.md 4.4.
    out["confusion"] = {
        f"true_{tn}": {f"pred_{pn}": sum(1 for p, t in preds_labels
                                         if t == ti and p == pi)
                       for pi, pn in enumerate(CLASS_NAMES)}
        for ti, tn in enumerate(CLASS_NAMES)
    }
    return out


def run_condition(name, transform_fn, jpeg_quality=85, skip_canonical_jpeg=False):
    results = []
    for path, label in TRUETEST:
        try:
            pil = Image.open(path).convert("RGB")
            pil = transform_fn(pil)
            pred = predict_pil(pil, jpeg_quality=jpeg_quality, skip_canonical_jpeg=skip_canonical_jpeg)
            results.append((pred, label))
        except Exception:
            continue
    stats = recall_by_class(results)
    print(f"  {name:<28} overall={stats['overall_acc']:.1f}%  "
          f"real={stats.get('real_recall', float('nan')):.1f}%  "
          f"fake={stats.get('fake_recall', float('nan')):.1f}%  "
          f"filter={stats.get('filter_recall', float('nan')):.1f}%  (n={stats['n']})")
    return stats


all_results = {}

# ── 0. Baseline (matches pipeline's normal q85 preprocessing) ─────────────
print("=== Baseline (q85, no perturbation) ===")
all_results["baseline"] = run_condition("baseline_q85", lambda im: im)

# ── 1. Lighting: brightness scaling ±30% / ±50% ────────────────────────────
print("\n=== Lighting (brightness scale) ===")


def scale_brightness(pil_img, factor):
    arr = np.asarray(pil_img).astype(np.float32)
    arr = np.clip(arr * factor, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


for label, factor in [("-50%", 0.5), ("-30%", 0.7), ("+30%", 1.3), ("+50%", 1.5)]:
    all_results[f"lighting_{label}"] = run_condition(
        f"brightness_{label}", lambda im, f=factor: scale_brightness(im, f))

# ── 2. Resolution / blur: Gaussian kernel 3/5/7/9px ────────────────────────
print("\n=== Blur (Gaussian kernel) ===")


def gaussian_blur(pil_img, ksize):
    arr = np.asarray(pil_img)
    blurred = cv2.GaussianBlur(arr, (ksize, ksize), 0)
    return Image.fromarray(blurred)


for k in (3, 5, 7, 9):
    all_results[f"blur_k{k}"] = run_condition(f"gaussian_blur_k{k}", lambda im, k=k: gaussian_blur(im, k))

# ── 2b. Downscale-upscale (simulates low native resolution source) ────────
print("\n=== Downscale-upscale (resolution loss) ===")


def downscale_upscale(pil_img, factor):
    w, h = pil_img.size
    small = pil_img.resize((max(1, w // factor), max(1, h // factor)), Image.BILINEAR)
    return small.resize((w, h), Image.BILINEAR)


for factor in (2, 4):
    all_results[f"downscale_{factor}x"] = run_condition(
        f"downscale_upscale_{factor}x", lambda im, f=factor: downscale_upscale(im, f))

# ── 3. JPEG quality sweep: q50/q70/q85/q95 (single compression) ───────────
print("\n=== JPEG quality (single compression) ===")
for q in (50, 70, 85, 95):
    all_results[f"jpeg_q{q}"] = run_condition(f"jpeg_q{q}", lambda im: im, jpeg_quality=q)

# ── 4. Multi-stage compression: simulates social-media re-upload chains ───
print("\n=== Multi-stage JPEG compression (re-upload simulation) ===")


def double_compress(pil_img, q1, q2):
    stage1 = preprocess_jpeg(pil_img, quality=q1)
    stage2 = preprocess_jpeg(stage1, quality=q2)
    return stage2


for label, (q1, q2) in [("q95->q70", (95, 70)), ("q85->q50->q70", (85, 50))]:
    if label == "q85->q50->q70":
        def triple(im):
            s1 = preprocess_jpeg(im, quality=85)
            s2 = preprocess_jpeg(s1, quality=50)
            return preprocess_jpeg(s2, quality=70)
        all_results[f"multijpeg_{label}"] = run_condition(
            f"multijpeg_{label}", triple, skip_canonical_jpeg=True)
    else:
        all_results[f"multijpeg_{label}"] = run_condition(
            f"multijpeg_{label}", lambda im, a=q1, b=q2: double_compress(im, a, b), skip_canonical_jpeg=True)

# ── 5. Pose angle (yaw/pitch via solvePnP on MediaPipe landmarks) ─────────
print("\n=== Pose angle (yaw/pitch buckets, natural True Test distribution) ===")
try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    with open(MODEL_PATH, "rb") as f:
        _model_data = f.read()
    _opts = vision.FaceLandmarkerOptions(
        base_options=mp_python.BaseOptions(model_asset_buffer=_model_data), num_faces=1)
    _landmarker = vision.FaceLandmarker.create_from_options(_opts)

    # Classic 6-point 3D face model (generic units) for solvePnP head pose.
    MODEL_3D = np.array([
        (0.0, 0.0, 0.0),          # nose tip
        (0.0, -330.0, -65.0),     # chin
        (-225.0, 170.0, -135.0),  # left eye left corner
        (225.0, 170.0, -135.0),   # right eye right corner
        (-150.0, -150.0, -125.0),  # left mouth corner
        (150.0, -150.0, -125.0),  # right mouth corner
    ], dtype=np.float64)
    LM_IDX = [1, 152, 33, 263, 61, 291]  # nose tip, chin, L-eye, R-eye, L-mouth, R-mouth

    def estimate_yaw_pitch(pil_img):
        bgr = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
        h, w = bgr.shape[:2]
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        res = _landmarker.detect(mp_img)
        if not res.face_landmarks:
            return None
        lm = res.face_landmarks[0]
        pts_2d = np.array([[lm[i].x * w, lm[i].y * h] for i in LM_IDX], dtype=np.float64)
        focal = w
        cam_matrix = np.array([[focal, 0, w / 2], [0, focal, h / 2], [0, 0, 1]], dtype=np.float64)
        dist_coeffs = np.zeros((4, 1))
        ok, rvec, tvec = cv2.solvePnP(MODEL_3D, pts_2d, cam_matrix, dist_coeffs,
                                       flags=cv2.SOLVEPNP_ITERATIVE)
        if not ok:
            return None
        rmat, _ = cv2.Rodrigues(rvec)
        sy = np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2)
        pitch = np.degrees(np.arctan2(-rmat[2, 0], sy))
        yaw = np.degrees(np.arctan2(rmat[1, 0], rmat[0, 0]))
        return yaw, pitch

    pose_buckets = {"frontal(<15deg)": [], "moderate(15-35deg)": [], "extreme(>35deg)": []}
    no_landmark = 0
    for path, label in TRUETEST:
        try:
            pil = Image.open(path).convert("RGB")
            yp = estimate_yaw_pitch(pil)
            if yp is None:
                no_landmark += 1
                continue
            yaw, pitch = yp
            angle_mag = max(abs(yaw), abs(pitch))
            pred = predict_pil(pil)
            if angle_mag < 15:
                pose_buckets["frontal(<15deg)"].append((pred, label))
            elif angle_mag < 35:
                pose_buckets["moderate(15-35deg)"].append((pred, label))
            else:
                pose_buckets["extreme(>35deg)"].append((pred, label))
        except Exception:
            continue

    print(f"  (no-landmark skipped: {no_landmark}/{len(TRUETEST)})")
    for bucket_name, items in pose_buckets.items():
        if items:
            stats = recall_by_class(items)
            all_results[f"pose_{bucket_name}"] = stats
            print(f"  {bucket_name:<22} overall={stats['overall_acc']:.1f}%  "
                  f"real={stats.get('real_recall', float('nan')):.1f}%  "
                  f"fake={stats.get('fake_recall', float('nan')):.1f}%  "
                  f"filter={stats.get('filter_recall', float('nan')):.1f}%  (n={stats['n']})")
        else:
            print(f"  {bucket_name:<22} n=0 (no True Test images fall in this range)")
except Exception as e:
    print(f"  Pose test skipped (mediapipe error): {e}")

# ── save ────────────────────────────────────────────────────────────────
out_record = {"provenance": PROVENANCE, "eval_name": "robustness_conditions", "conditions": all_results}
OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
if OUT_JSON.exists():
    print(f"ERROR: refusing to overwrite existing result file: {OUT_JSON}")
    sys.exit(1)
OUT_JSON.write_text(json.dumps(out_record, indent=2), encoding="utf-8")
print(f"\nWrote full results -> {OUT_JSON}")
