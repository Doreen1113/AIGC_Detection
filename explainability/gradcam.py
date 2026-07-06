"""Grad-CAM++ for 3-class DualBranchModel (Real / Fake / Filter detector).

Uses shufflenet_v2_3class_ffhq_v2.pth (filter F1=0.980).
Runs on 5 real + 5 fake + 5 filter images.
Output: gradcam_output/ (3-panel: Input | Grad-CAM++ | FakeShield Mask)

    python explainability/gradcam.py
"""

import os, random
import cv2
import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

BASE     = r"C:\My_Project\AIGC"
CKPT     = os.path.join(BASE, "shufflenet_v2_3class_ffhq_v2.pth")
OUT_DIR  = os.path.join(BASE, "gradcam_output")
REAL_DIR = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR = os.path.join(BASE, "AIGuard", "fake")
FILT_DIR = os.path.join(BASE, "filter_data")
CLASSES  = ["real", "fake", "filter"]
device   = "cuda" if torch.cuda.is_available() else "cpu"

# ──────────────────────────────────────────────
# Model (same architecture as train_3class_ffhq_v2.py)
# ──────────────────────────────────────────────
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
        self.fft_branch = FFTBranch(out_dim=256)
        self.classifier = nn.Sequential(
            nn.Linear(1024+256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))
    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])

# ──────────────────────────────────────────────
# Grad-CAM++ (C's implementation, target: spatial_branch.conv5)
# ──────────────────────────────────────────────
class GradCAMPlusPlus:
    def __init__(self, model, target_layer):
        self.model = model
        self._act  = None
        self._grad = None
        target_layer.register_forward_hook(
            lambda m, i, o: setattr(self, '_act', o.detach()))
        target_layer.register_full_backward_hook(
            lambda m, gi, go: setattr(self, '_grad', go[0].detach()))

    def generate(self, inp, class_idx=None):
        self.model.eval()
        inp = inp.to(device).requires_grad_(False)
        out = self.model(inp)
        probs = torch.softmax(out, 1)[0]

        if class_idx is None:
            class_idx = out.argmax(1).item()

        self.model.zero_grad()
        out[0, class_idx].backward()

        features  = self._act
        gradients = self._grad

        grads_power_2 = gradients ** 2
        grads_power_3 = gradients ** 3
        sum_features  = torch.sum(features, dim=[2, 3], keepdim=True)

        alpha_denom = 2 * grads_power_2 + sum_features * grads_power_3
        alpha_denom = torch.where(alpha_denom != 0, alpha_denom, torch.ones_like(alpha_denom))
        alpha   = grads_power_2 / alpha_denom
        weights = torch.sum(alpha * torch.relu(gradients), dim=[2, 3], keepdim=True)

        cam = torch.relu((weights * features).sum(dim=1)).squeeze()
        cam = cam.cpu().numpy()
        cam = cv2.resize(cam, (224, 224))
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())

        return cam, class_idx, probs[class_idx].item()


def overlay_heatmap(img_bgr, cam, alpha=0.45):
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    img_resized = cv2.resize(img_bgr, (224, 224))
    gradcam_blended = cv2.addWeighted(img_resized, 1 - alpha, heat, alpha, 0)

    cam_gray = (cam * 255).astype(np.uint8)
    _, binary_mask = cv2.threshold(cam_gray, 115, 255, cv2.THRESH_BINARY)
    binary_mask_resized = cv2.resize(binary_mask, (224, 224))
    fakeshield_mask = cv2.cvtColor(binary_mask_resized, cv2.COLOR_GRAY2BGR)

    return gradcam_blended, fakeshield_mask


def save_gradcam_figure(img_bgr, cam, pred_label, confidence, out_path, title):
    gradcam_blended, fakeshield_mask = overlay_heatmap(img_bgr, cam)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    axes[0].imshow(cv2.cvtColor(cv2.resize(img_bgr, (224, 224)), cv2.COLOR_BGR2RGB))
    axes[0].set_title("1. Input Image", fontsize=12, pad=8)
    axes[0].axis("off")

    axes[1].imshow(cv2.cvtColor(gradcam_blended, cv2.COLOR_BGR2RGB))
    axes[1].set_title(f"2. Grad-CAM++ ({confidence:.1%})", fontsize=12, pad=8)
    axes[1].axis("off")

    axes[2].imshow(cv2.cvtColor(fakeshield_mask, cv2.COLOR_BGR2RGB))
    axes[2].set_title(f"3. FakeShield Mask ({pred_label})", fontsize=12, pad=8)
    axes[2].axis("off")

    plt.suptitle(title, fontsize=11, y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    print(f"Loading 3-class model from {CKPT}")
    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(CKPT, map_location=device))

    gradcam = GradCAMPlusPlus(model, model.spatial_branch.conv5)

    # 5 real + 5 fake + 5 filter
    samples = []

    for label_dir, label_name, cls in [(REAL_DIR, "Real", 0), (FAKE_DIR, "Fake", 1)]:
        paths = []
        for sub in os.listdir(label_dir):
            sp = os.path.join(label_dir, sub)
            if os.path.isdir(sp):
                paths += [os.path.join(sp, f) for f in os.listdir(sp)
                          if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(0); random.shuffle(paths)
        for p in paths[:5]:
            samples.append((p, label_name, cls))

    # filter: pick 1~2 images from each of the 4 filter types
    filter_paths = []
    for ftype in ["smoothing", "whitening", "eye_enlarging", "face_reshaping"]:
        fdir = os.path.join(FILT_DIR, ftype)
        if not os.path.isdir(fdir): continue
        files = [f for f in os.listdir(fdir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(0); random.shuffle(files)
        filter_paths += [os.path.join(fdir, f) for f in files[:2]]
    random.seed(0); random.shuffle(filter_paths)
    for p in filter_paths[:5]:
        samples.append((p, "Filter", 2))

    print(f"\nRunning Grad-CAM++ on {len(samples)} images (5 real / 5 fake / 5 filter)...")
    correct = {c: 0 for c in CLASSES}
    total   = {c: 0 for c in CLASSES}

    for img_path, true_label, true_cls in samples:
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            continue

        inp = transform(Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))).unsqueeze(0)
        cam, pred_cls, conf = gradcam.generate(inp)
        pred_label = CLASSES[pred_cls]
        ok = pred_cls == true_cls
        if ok: correct[CLASSES[true_cls]] += 1
        total[CLASSES[true_cls]] += 1

        stem  = os.path.splitext(os.path.basename(img_path))[0]
        fname = f"{true_label.lower()}_{stem}.jpg"
        title = f"GT: {true_label}  |  Pred: {pred_label} ({conf:.1%})  {'OK' if ok else 'X'}"
        save_gradcam_figure(img_bgr, cam, pred_label, conf,
                            os.path.join(OUT_DIR, fname), title)
        print(f"  [{true_label:6s}] {os.path.basename(img_path):40s} "
              f"pred={pred_label:6s} ({conf:.1%}) {'[OK]' if ok else '[X]'}")

    print(f"\nAccuracy: Real {correct['real']}/{total['real']}  "
          f"Fake {correct['fake']}/{total['fake']}  "
          f"Filter {correct['filter']}/{total['filter']}")
    print(f"Output → {OUT_DIR}")


if __name__ == "__main__":
    main()
