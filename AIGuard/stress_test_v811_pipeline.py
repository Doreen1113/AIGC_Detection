"""
v8.11 chained pipeline stress test: Layer1 (real vs manipulated) -> Layer2
(fake vs filter), run end-to-end on the same AIGuard/unseen fake+filter
stress set used throughout this project (stress_test_held_out.py). This is
the number directly comparable to v8.8's original fake+filter confusion rate
(1.35%) -- an image is "correct" only if it ends up classified as "fake"
after passing through both layers; if Layer1 says "real", that's already a
miss (Layer2 never runs); if Layer1 says "manipulated" but Layer2 says
"filter", that's also a miss.

python AIGuard/stress_test_v811_pipeline.py [layer1_weights] [layer2_weights]
"""
import argparse, sys, json, hashlib, subprocess, warnings
from datetime import datetime, timezone
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
MODEL_PATH = str(BASE / "face_landmarker.task")
sys.path.insert(0, str(BASE))

import torch
import torch.nn as nn
import torchvision.models as tv_models
from torchvision import transforms
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


_landmarker = None

def _get_landmarker():
    global _landmarker
    if _landmarker is None:
        with open(MODEL_PATH, "rb") as f:
            model_data = f.read()
        opts = vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_buffer=model_data),
            num_faces=1)
        _landmarker = vision.FaceLandmarker.create_from_options(opts)
    return _landmarker


def _get_landmarks(image_bgr):
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    res = _get_landmarker().detect(mp_img)
    if not res.face_landmarks:
        return None
    h, w = image_bgr.shape[:2]
    return np.array([[lm.x * w, lm.y * h] for lm in res.face_landmarks[0]], np.float32)


def apply_smoothing(rgb, strength):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    lm = _get_landmarks(bgr)
    if lm is None:
        return None
    d = {"light": (9, 50, 50), "medium": (15, 80, 80), "heavy": (21, 100, 100)}[strength]
    return cv2.cvtColor(cv2.bilateralFilter(bgr, *d), cv2.COLOR_BGR2RGB)


def apply_whitening(rgb, strength):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    s = {"medium": 0.15, "heavy": 0.25}[strength]
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    lab[:, :, 0] += s * (255.0 - lab[:, :, 0])
    return cv2.cvtColor(cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR), cv2.COLOR_BGR2RGB)


def apply_combined(x, strength):
    smoothed = apply_smoothing(x, strength)
    if smoothed is None:
        return None
    return apply_whitening(smoothed, strength)


def apply_eye_enlarging(rgb, scale=1.18, radius_factor=1.70):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    lm = _get_landmarks(bgr)
    if lm is None:
        return None
    h, w = bgr.shape[:2]
    result = bgr.copy()
    LEFT_EYE = (33, 133, 159, 145)
    RIGHT_EYE = (362, 263, 386, 374)
    for eye_idx in (LEFT_EYE, RIGHT_EYE):
        pts = lm[list(eye_idx)]
        center = np.mean(pts, axis=0)
        eye_w = np.linalg.norm(lm[eye_idx[0]] - lm[eye_idx[1]])
        radius = max(eye_w * radius_factor, 8.0)
        cx, cy = center
        x0 = max(0, int(cx - radius)); x1 = min(w, int(cx + radius + 1))
        y0 = max(0, int(cy - radius)); y1 = min(h, int(cy + radius + 1))
        gx, gy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
        dx, dy = gx - cx, gy - cy
        nd = np.clip(np.sqrt(dx**2 + dy**2) / radius, 0.0, 1.0)
        ls = 1.0 + (scale - 1.0) * (1.0 - nd) ** 2
        map_x = (cx + dx / ls).astype(np.float32)
        map_y = (cy + dy / ls).astype(np.float32)
        roi = cv2.remap(bgr, map_x, map_y, cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT_101)
        alpha = np.clip((1.0 - nd) / 0.18, 0.0, 1.0)[:, :, None]
        blended = (result[y0:y1, x0:x1].astype(np.float32) * (1 - alpha) + roi.astype(np.float32) * alpha)
        result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return cv2.cvtColor(result, cv2.COLOR_BGR2RGB)


def apply_face_reshaping(rgb, shrink_ratio=0.92):
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    lm = _get_landmarks(bgr)
    if lm is None:
        return None
    h, w = bgr.shape[:2]
    center = lm[1]
    map_x, map_y = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    radius = 60.0
    for cheek_idx in (234, 454):
        cx, cy = lm[cheek_idx]
        x0, x1 = max(0, int(cx - radius)), min(w, int(cx + radius))
        y0, y1 = max(0, int(cy - radius)), min(h, int(cy + radius))
        gx = map_x[y0:y1, x0:x1]
        gy = map_y[y0:y1, x0:x1]
        dx, dy = gx - cx, gy - cy
        dist = np.sqrt(dx**2 + dy**2)
        within = dist < radius
        factor = np.where(within, 1 - (1 - shrink_ratio) * (1 - dist / radius), 1.0)
        map_x[y0:y1, x0:x1] = np.where(within, center[0] + (gx - center[0]) * factor, gx)
        map_y[y0:y1, x0:x1] = np.where(within, center[1] + (gy - center[1]) * factor, gy)
    return cv2.cvtColor(
        cv2.remap(bgr, map_x, map_y, cv2.INTER_LINEAR),
        cv2.COLOR_BGR2RGB)


FILTERS = {
    "smoothing_light":  lambda x: apply_smoothing(x, "light"),
    "smoothing_medium": lambda x: apply_smoothing(x, "medium"),
    "smoothing_heavy":  lambda x: apply_smoothing(x, "heavy"),
    "whitening_medium": lambda x: apply_whitening(x, "medium"),
    "combined_medium":  lambda x: apply_combined(x, "medium"),
    "combined_heavy":   lambda x: apply_combined(x, "heavy"),
    "eye_enlarging":    apply_eye_enlarging,
    "face_reshaping":   apply_face_reshaping,
}


def run_pipeline(pil_img, l1_model, l2_model, device):
    pil_img = preprocess_jpeg(pil_img, quality=85)
    t = transform_infer(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        l1_probs = torch.softmax(l1_model(t), dim=1)[0]
    l1_pred = "real" if l1_probs.argmax().item() == 0 else "manipulated"
    if l1_pred == "real":
        return "real"
    with torch.no_grad():
        l2_probs = torch.softmax(l2_model(t), dim=1)[0]
    return "fake" if l2_probs.argmax().item() == 0 else "filter"


def main():
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

    _get_landmarker()
    print("MediaPipe ready\n")

    unseen_dir = BASE / "AIGuard" / "unseen"
    all_fake = [
        f for f in unseen_dir.rglob("*")
        if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".jfif"}
        and f.stem.lower().startswith("fake")
    ]
    print(f"AIGuard/unseen fake images: {len(all_fake)}\n")

    results = []
    misclassified = {fname: 0 for fname in FILTERS}
    skipped = {fname: 0 for fname in FILTERS}
    base_wrong = 0

    for img_path in sorted(all_fake):
        try:
            pil = Image.open(img_path).convert("RGB")
        except Exception:
            continue
        img_np = np.array(pil.resize((224, 224)))
        base_pred = run_pipeline(pil, l1, l2, device)
        if base_pred != "fake":
            base_wrong += 1

        row = {"image": img_path.name, "base_pred": base_pred, "filters": {}}
        for fname, ffunc in FILTERS.items():
            filtered_np = ffunc(img_np)
            if filtered_np is None:
                skipped[fname] += 1
                row["filters"][fname] = {"pred": "skip"}
                continue
            filtered_pil = Image.fromarray(filtered_np)
            pred = run_pipeline(filtered_pil, l1, l2, device)
            row["filters"][fname] = {"pred": pred}
            if pred != "fake":
                misclassified[fname] += 1
        results.append(row)

    n = len(results)
    print(f"\n{'='*60}")
    print(f"Held-out fake images tested: {n}")
    print(f"Base (unfiltered) misclassified (not 'fake'): {base_wrong}/{n} ({base_wrong/n*100:.2f}%)\n")
    print(f"{'Filter type':<24} {'Misclassified':>14}  {'Skipped':>8}  {'Error%':>8}")
    print("-" * 62)
    total_wrong, total_valid = 0, 0
    for fname in FILTERS:
        valid_n = n - skipped[fname]
        pct = misclassified[fname] / valid_n * 100 if valid_n > 0 else 0
        total_wrong += misclassified[fname]
        total_valid += valid_n
        print(f"  {fname:<22}: {misclassified[fname]:3d}/{valid_n:<3d}  ({skipped[fname]:3d} skipped)  {pct:6.1f}%")
    print(f"\n  {'TOTAL (end-to-end)':<22}: {total_wrong}/{total_valid}  ({total_wrong/total_valid*100:.2f}%)")
    print(f"\n  Comparable directly to v8.8's original fake+filter confusion rate: 1.35%")

    # 2026-08-11: derive the filename from the weights actually loaded (kept).
    # 2026-08-13 P0 repair: also route output exclusively to the isolated
    # release directory (never overwrite an existing results/ file), and wrap
    # the per-image results with full provenance metadata.
    def _tag(path):
        s = Path(path).stem
        for pre in ("shufflenet_v2_layer1_", "shufflenet_v2_layer2_", "shufflenet_v2_"):
            if s.startswith(pre):
                return s[len(pre):]
        return s

    summary = {
        "n_images": n,
        "base_misclassified": base_wrong,
        "base_misclassified_pct": base_wrong / n * 100,
        "per_condition": {
            fname: {
                "misclassified": misclassified[fname],
                "valid_n": n - skipped[fname],
                "skipped": skipped[fname],
                "error_pct": (misclassified[fname] / (n - skipped[fname]) * 100) if (n - skipped[fname]) > 0 else None,
            }
            for fname in FILTERS
        },
        "total_end_to_end": {
            "misclassified": total_wrong,
            "valid_n": total_valid,
            "error_pct": total_wrong / total_valid * 100,
        },
    }
    out_record = {"provenance": PROVENANCE, "eval_name": "stress_test_fake_filter", "summary": summary, "per_image_results": results}

    out_name = f"stress_test_{_tag(L1_WEIGHTS)}_layer2{_tag(L2_WEIGHTS)}_{RUN_DATE}.json"
    out = RELEASE_DIR / out_name
    if out.exists():
        print(f"ERROR: refusing to overwrite existing result file: {out}")
        sys.exit(1)
    print(f"[out] results file is named after the loaded weights: {out.name}")
    out.write_text(json.dumps(out_record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetailed results -> {out}")


if __name__ == "__main__":
    main()
