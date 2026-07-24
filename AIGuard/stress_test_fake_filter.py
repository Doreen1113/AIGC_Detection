"""
Stress test: fake image + beauty filter → pipeline
測試 fake 圖加美顏 filter 後是否被誤判為 real 或 filter。

Usage:
    python AIGuard/stress_test_fake_filter.py
"""

import sys, json, random, io
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))

# ── 從 pipeline 匯入所需元件 ──────────────────────────────────────────────
from pipeline import (
    DualBranchModel, GradCAMPlusPlus, build_artifact_model,
    transform_infer, preprocess_jpeg,
    top_activated_regions, infer_artifact_type, build_explanation,
    CLASSES, WEIGHTS_PATH, ARTIFACT_WEIGHTS_PATH
)
import torch
import os

# ── Filter functions ──────────────────────────────────────────────────────

def apply_smoothing(img_np, strength="medium"):
    """Bilateral filter — 磨皮效果"""
    d = {"light": (9, 50, 50), "medium": (15, 80, 80), "heavy": (25, 120, 120)}[strength]
    bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    out = cv2.bilateralFilter(bgr, d[0], d[1], d[2])
    return cv2.cvtColor(out, cv2.COLOR_BGR2RGB)

def apply_whitening(img_np, strength="medium"):
    """Brightness + saturation 降低 — 美白效果"""
    factor = {"light": 1.10, "medium": 1.20, "heavy": 1.35}[strength]
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB).astype(np.float32)
    lab[:, :, 0] = np.clip(lab[:, :, 0] * factor, 0, 255)
    out = cv2.cvtColor(lab.astype(np.uint8), cv2.COLOR_LAB2RGB)
    return out

def apply_combined(img_np, strength="medium"):
    """smoothing + whitening 合體"""
    return apply_whitening(apply_smoothing(img_np, strength), strength)


FILTERS = {
    "smoothing_light":  lambda x: apply_smoothing(x, "light"),
    "smoothing_medium": lambda x: apply_smoothing(x, "medium"),
    "smoothing_heavy":  lambda x: apply_smoothing(x, "heavy"),
    "whitening_medium": lambda x: apply_whitening(x, "medium"),
    "combined_medium":  lambda x: apply_combined(x, "medium"),
    "combined_heavy":   lambda x: apply_combined(x, "heavy"),
}

# ── Pipeline inference (inline, no Grad-CAM for speed) ───────────────────

def run_inference(pil_img, model, device):
    pil_img = preprocess_jpeg(pil_img, quality=85)
    t = transform_infer(pil_img).unsqueeze(0).to(device)
    with torch.no_grad():
        probs = torch.softmax(model(t), dim=1)[0]
    idx = int(probs.argmax())
    return CLASSES[idx], float(probs[idx]), {c: round(float(p), 3) for c, p in zip(CLASSES, probs)}


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()
    print(f"Model loaded ({WEIGHTS_PATH})")

    # 從 AIGuard fake 取 20 張
    fake_dir = BASE / "AIGuard" / "fake"
    fake_imgs = []
    for sub in sorted(fake_dir.iterdir()):
        for f in sub.iterdir():
            if f.suffix.lower() in {".jpg", ".jpeg", ".png"}:
                fake_imgs.append(f)
        if len(fake_imgs) >= 20:
            break
    random.seed(42)
    fake_imgs = random.sample(fake_imgs, min(20, len(fake_imgs)))
    print(f"Using {len(fake_imgs)} fake images\n")

    results = []
    changed = {fname: 0 for fname in FILTERS}

    print(f"{'Image':<25} {'Original':>8}  " + "  ".join(f"{k:<20}" for k in FILTERS))
    print("-" * 170)

    for img_path in fake_imgs:
        pil = Image.open(img_path).convert("RGB")
        img_np = np.array(pil.resize((224, 224)))

        orig_pred, orig_conf, orig_probs = run_inference(pil, model, device)

        row = {"image": img_path.name, "original": orig_pred, "probs": orig_probs, "filters": {}}
        filter_results = []

        for fname, ffunc in FILTERS.items():
            filtered_np = ffunc(img_np)
            filtered_pil = Image.fromarray(filtered_np)
            pred, conf, probs = run_inference(filtered_pil, model, device)
            row["filters"][fname] = {"pred": pred, "conf": round(conf, 3)}
            filter_results.append(f"{pred}({conf:.2f})")
            if pred != orig_pred:
                changed[fname] += 1

        results.append(row)
        print(f"{img_path.name:<25} {orig_pred:>8}  " + "  ".join(f"{r:<20}" for r in filter_results))

    # Summary
    print(f"\n{'='*60}")
    print(f"Total fake images: {len(fake_imgs)}")
    print(f"\nPrediction changes (fake → other) per filter type:")
    for fname, cnt in changed.items():
        pct = cnt / len(fake_imgs) * 100
        print(f"  {fname:<22}: {cnt:2d}/{len(fake_imgs)} ({pct:.0f}%) changed")

    # Save
    out = BASE / "results" / "stress_test_fake_filter.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDetailed results → {out}")


if __name__ == "__main__":
    main()
