"""Grad-CAM for ShuffleNetV2 (Real/Fake detector).

Step 1: 訓練 ShuffleNetV2，存成 shufflenet_v2.pth（若已存在則跳過）
Step 2: 對 5 張 real + 5 張 fake 圖跑 Grad-CAM
Step 3: 輸出 heatmap overlay 到 gradcam_output/

執行環境：base conda env（有 torch, torchvision, timm）
    python explainability/gradcam.py
"""

import os, random, time
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
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, roc_auc_score

BASE     = r"C:\CVLab\AIGC"
CKPT     = os.path.join(BASE, "shufflenet_v2.pth")
OUT_DIR  = os.path.join(BASE, "gradcam_output")
REAL_DIR = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR = os.path.join(BASE, "AIGuard", "fake")
device   = "cuda" if torch.cuda.is_available() else "cpu"

# ──────────────────────────────────────────────
# Dataset
# ──────────────────────────────────────────────
def collect_images(label_dir, max_per_sub=600):
    paths = []
    for sub in os.listdir(label_dir):
        sub_path = os.path.join(label_dir, sub)
        if not os.path.isdir(sub_path):
            continue
        files = [f for f in os.listdir(sub_path)
                 if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        random.seed(42); random.shuffle(files)
        paths.extend(os.path.join(sub_path, f) for f in files[:max_per_sub])
    return paths

class FaceDataset(Dataset):
    def __init__(self, paths, labels, transform):
        self.paths, self.labels, self.transform = paths, labels, transform
    def __len__(self):
        return len(self.paths)
    def __getitem__(self, idx):
        img = Image.open(self.paths[idx]).convert("RGB")
        return self.transform(img), self.labels[idx]

transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.5]*3, [0.5]*3),
])

# ──────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────
def build_model():
    m = tv_models.shufflenet_v2_x1_0(
        weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m.to(device)

# ──────────────────────────────────────────────
# Train
# ──────────────────────────────────────────────
def train():
    real_paths = collect_images(REAL_DIR)
    fake_paths = collect_images(FAKE_DIR)
    all_paths = real_paths + fake_paths
    all_labels = [0]*len(real_paths) + [1]*len(fake_paths)
    tr_p, te_p, tr_l, te_l = train_test_split(
        all_paths, all_labels, test_size=0.2, stratify=all_labels, random_state=42)

    tr_loader = DataLoader(FaceDataset(tr_p, tr_l, transform),
                           batch_size=32, shuffle=True, num_workers=0)
    te_loader = DataLoader(FaceDataset(te_p, te_l, transform),
                           batch_size=32, shuffle=False, num_workers=0)
    print(f"Train: {len(tr_p)} | Test: {len(te_p)} | Device: {device}")

    model = build_model()
    opt   = torch.optim.Adam(model.parameters(), lr=1e-4)
    crit  = nn.CrossEntropyLoss()

    for epoch in range(5):
        model.train(); total_loss = 0
        for imgs, lbls in tr_loader:
            imgs, lbls = imgs.to(device), lbls.to(device)
            opt.zero_grad()
            loss = crit(model(imgs), lbls)
            loss.backward(); opt.step()
            total_loss += loss.item()
        print(f"  Epoch {epoch+1}/5  loss={total_loss/len(tr_loader):.4f}")

    model.eval()
    preds, probs, trues = [], [], []
    with torch.no_grad():
        for imgs, lbls in te_loader:
            imgs = imgs.to(device)
            out  = model(imgs)
            p    = torch.softmax(out, 1)[:, 1].cpu()
            preds.extend(out.argmax(1).cpu().tolist())
            probs.extend(p.tolist())
            trues.extend(lbls.tolist())
    from sklearn.metrics import accuracy_score, precision_score, recall_score
    print(f"  Acc={accuracy_score(trues,preds):.4f}  "
          f"F1={f1_score(trues,preds):.4f}  "
          f"AUROC={roc_auc_score(trues,probs):.4f}")

    torch.save(model.state_dict(), CKPT)
    print(f"Model saved → {CKPT}")
    return model

# ──────────────────────────────────────────────
# Grad-CAM
# ──────────────────────────────────────────────
class GradCAM:
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
        score = out[0, class_idx]
        score.backward()

        weights = self._grad.mean(dim=[2, 3], keepdim=True)
        cam = torch.relu((weights * self._act).sum(dim=1)).squeeze()
        cam = cam.cpu().numpy()
        cam = cv2.resize(cam, (224, 224))
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        return cam, class_idx, probs[class_idx].item()


def overlay_heatmap(img_bgr, cam, alpha=0.45):
    """cam 疊在原圖上，紅色=高激活（可疑），藍色=低激活。"""
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    img_resized = cv2.resize(img_bgr, (224, 224))
    return cv2.addWeighted(img_resized, 1 - alpha, heat, alpha, 0)


def save_gradcam_figure(img_bgr, cam, pred_label, confidence, out_path, title):
    overlay = overlay_heatmap(img_bgr, cam)
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    axes[0].imshow(cv2.cvtColor(cv2.resize(img_bgr, (224, 224)), cv2.COLOR_BGR2RGB))
    axes[0].set_title("Original", fontsize=13, pad=8)
    axes[0].axis("off")
    axes[1].imshow(cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB))
    axes[1].set_title(
        f"Grad-CAM  →  {pred_label}  ({confidence:.1%})", fontsize=13, pad=8)
    axes[1].axis("off")
    plt.suptitle(title, fontsize=11, y=1.01)
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # ---- 訓練 / 載入 ----
    if os.path.exists(CKPT):
        print(f"Loading weights from {CKPT}")
        model = build_model()
        model.load_state_dict(torch.load(CKPT, map_location=device))
    else:
        print("No checkpoint found, training from scratch...")
        model = train()

    # ---- Grad-CAM：target = conv5（最後 1x1 conv 後的 feature map）----
    gradcam = GradCAM(model, model.conv5)

    # ---- 選測試圖：5 real + 5 fake ----
    samples = []
    for label_dir, label_name, cls in [(REAL_DIR, "Real", 0),
                                        (FAKE_DIR, "Fake", 1)]:
        paths = []
        for sub in os.listdir(label_dir):
            sp = os.path.join(label_dir, sub)
            if os.path.isdir(sp):
                paths += [os.path.join(sp, f) for f in os.listdir(sp)
                          if f.lower().endswith(('.jpg','.jpeg','.png'))]
        random.seed(0); random.shuffle(paths)
        for p in paths[:5]:
            samples.append((p, label_name, cls))

    LABEL_MAP = {0: "Real", 1: "Fake"}

    print(f"\nRunning Grad-CAM on {len(samples)} images...")
    for img_path, true_label, true_cls in samples:
        img_bgr = cv2.imread(img_path)
        if img_bgr is None:
            continue

        inp = transform(Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))).unsqueeze(0)
        cam, pred_cls, conf = gradcam.generate(inp)
        pred_label = LABEL_MAP[pred_cls]
        correct = "[OK]" if pred_cls == true_cls else "[X]"

        stem = os.path.splitext(os.path.basename(img_path))[0]
        fname = f"{true_label.lower()}_{stem}.jpg"
        title = f"GT: {true_label}  |  Pred: {pred_label} ({conf:.1%})  {correct.strip('[]')}"
        save_gradcam_figure(img_bgr, cam, pred_label, conf,
                            os.path.join(OUT_DIR, fname), title)
        print(f"  [{true_label}] {os.path.basename(img_path):30s}  "
              f"pred={pred_label} ({conf:.1%}) {correct}")

    print(f"\nDone. Output → {OUT_DIR}")


if __name__ == "__main__":
    main()
