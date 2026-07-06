"""
TTA + Preprocessing 組合測試。
對 unseen held-out set 試不同 preprocessing 組合，觀察哪個能改善 domain gap。
"""
import torch
import torch.nn as nn
import torchvision.models as tv_models
import os
import io
import random
import numpy as np
import cv2
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score, confusion_matrix
from PIL import Image

# ───────── 設定 ─────────
base_path    = r"C:\My_Project\AIGC\AIGuard"
weights_path = r"C:\My_Project\AIGC\shufflenet_v2_30k_aug.pth"
UNSEEN_DIR   = os.path.join(base_path, "unseen")
TTA_N        = 8       # TTA 次數
BATCH_SIZE   = 64

# ───────── MediaPipe face crop ─────────
def get_face_crop(img_pil, padding=0.25):
    """用 MediaPipe 偵測人臉並裁切，找不到就回傳原圖。"""
    try:
        import mediapipe as mp
        mp_face = mp.solutions.face_detection
        with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.3) as det:
            arr = np.array(img_pil.convert("RGB"))
            res = det.process(arr)
            if res.detections:
                d  = res.detections[0].location_data.relative_bounding_box
                h, w = arr.shape[:2]
                x1 = max(0, int((d.xmin - padding * d.width)  * w))
                y1 = max(0, int((d.ymin - padding * d.height) * h))
                x2 = min(w, int((d.xmin + (1+padding) * d.width)  * w))
                y2 = min(h, int((d.ymin + (1+padding) * d.height) * h))
                cropped = arr[y1:y2, x1:x2]
                if cropped.size > 0:
                    return Image.fromarray(cropped)
    except Exception:
        pass
    return img_pil

# ───────── Preprocessing 函式 ─────────
def preprocess_jpeg(img_pil, quality=75):
    """Re-encode at fixed JPEG quality（統一壓縮程度）。"""
    buf = io.BytesIO()
    img_pil.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return Image.open(buf).convert("RGB")

def preprocess_clahe(img_pil, clip_limit=2.0, tile_grid=(8, 8)):
    """CLAHE 直方圖均衡（統一亮度/對比）。"""
    arr  = np.array(img_pil.convert("RGB"))
    lab  = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
    l     = clahe.apply(l)
    lab   = cv2.merge([l, a, b])
    rgb   = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)
    return Image.fromarray(rgb)

# ───────── Transform ─────────
transform_base = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

transform_tta = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
    transforms.ToTensor(),
    transforms.Normalize([0.5]*3, [0.5]*3)
])

# ───────── Dataset ─────────
class UnseenRaw(Dataset):
    """回傳 PIL image + label，preprocessing 在外部做。"""
    def __init__(self, folder):
        self.samples = []
        for fname in os.listdir(folder):
            if not fname.lower().endswith(('.jpg', '.jpeg', '.png', '.jfif')):
                continue
            label = 0 if fname.lower().startswith('real') else 1
            self.samples.append((os.path.join(folder, fname), label))

    def __len__(self): return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        return Image.open(path).convert("RGB"), label

# ───────── Model ─────────
def build_shufflenet():
    m = tv_models.shufflenet_v2_x1_0(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    return m

# ───────── Inference with TTA ─────────
def infer_tta(model, images, device, n_tta, use_tta):
    """
    images: list of PIL images
    回傳 P(fake) numpy array
    """
    if not use_tta:
        tensors = torch.stack([transform_base(im) for im in images]).to(device)
        with torch.no_grad():
            out   = model(tensors)
            probs = torch.softmax(out, dim=1)[:, 1].cpu().numpy()
        return probs

    # TTA: 跑 n_tta 次，取平均
    all_runs = []
    for _ in range(n_tta):
        tensors = torch.stack([transform_tta(im) for im in images]).to(device)
        with torch.no_grad():
            out  = model(tensors)
            prob = torch.softmax(out, dim=1)[:, 1].cpu().numpy()
        all_runs.append(prob)
    return np.mean(all_runs, axis=0)

# ───────── Evaluate one config ─────────
def evaluate_config(model, raw_dataset, device, cfg):
    use_face_crop = cfg.get("face_crop", False)
    use_jpeg      = cfg.get("jpeg",      False)
    use_clahe     = cfg.get("clahe",     False)
    use_tta       = cfg.get("tta",       False)

    all_probs, all_labels = [], []
    batch_imgs, batch_lbls = [], []

    def flush():
        probs = infer_tta(model, batch_imgs, device, TTA_N, use_tta)
        all_probs.extend(probs)
        all_labels.extend(batch_lbls)
        batch_imgs.clear(); batch_lbls.clear()

    for img_pil, label in raw_dataset:
        if use_face_crop:
            img_pil = get_face_crop(img_pil)
        if use_jpeg:
            img_pil = preprocess_jpeg(img_pil, quality=75)
        if use_clahe:
            img_pil = preprocess_clahe(img_pil)
        batch_imgs.append(img_pil)
        batch_lbls.append(label)
        if len(batch_imgs) >= BATCH_SIZE:
            flush()
    if batch_imgs:
        flush()

    all_probs  = np.array(all_probs)
    all_labels = np.array(all_labels)
    auroc = roc_auc_score(all_labels, all_probs)

    # threshold=0.5
    preds = (all_probs >= 0.5).astype(int)
    acc   = (preds == all_labels).mean()
    f1    = f1_score(all_labels, preds, zero_division=0)
    cm    = confusion_matrix(all_labels, preds)
    real2fake = cm[0][1]
    fake2real = cm[1][0]
    return auroc, acc, f1, real2fake, fake2real

# ───────── Main ─────────
if __name__ == '__main__':
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Using device:", device)

    model = build_shufflenet().to(device)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.eval()

    raw_ds = UnseenRaw(UNSEEN_DIR)
    print(f"Unseen samples: {len(raw_ds)}\n")

    configs = [
        {"name": "Baseline (no preproc, no TTA)",     "face_crop": False, "jpeg": False, "clahe": False, "tta": False},
        {"name": "TTA only",                           "face_crop": False, "jpeg": False, "clahe": False, "tta": True},
        {"name": "JPEG re-encode only",                "face_crop": False, "jpeg": True,  "clahe": False, "tta": False},
        {"name": "CLAHE only",                         "face_crop": False, "jpeg": False, "clahe": True,  "tta": False},
        {"name": "Face crop only",                     "face_crop": True,  "jpeg": False, "clahe": False, "tta": False},
        {"name": "JPEG + TTA",                         "face_crop": False, "jpeg": True,  "clahe": False, "tta": True},
        {"name": "CLAHE + TTA",                        "face_crop": False, "jpeg": False, "clahe": True,  "tta": True},
        {"name": "JPEG + CLAHE + TTA",                 "face_crop": False, "jpeg": True,  "clahe": True,  "tta": True},
        {"name": "Face crop + JPEG + TTA",             "face_crop": True,  "jpeg": True,  "clahe": False, "tta": True},
        {"name": "Face crop + JPEG + CLAHE + TTA",     "face_crop": True,  "jpeg": True,  "clahe": True,  "tta": True},
    ]

    print(f"{'Config':<42} {'AUROC':>6} {'Acc':>6} {'F1':>6} {'R→F':>6} {'F→R':>5}")
    print("-" * 75)

    results = []
    for cfg in configs:
        auroc, acc, f1, r2f, f2r = evaluate_config(model, raw_ds, device, cfg)
        results.append((cfg["name"], auroc, acc, f1, r2f, f2r))
        print(f"{cfg['name']:<42} {auroc:.4f}  {acc:.4f}  {f1:.4f}  {r2f:>5}  {f2r:>4}")

    best = max(results, key=lambda x: x[1])
    print(f"\n最佳 AUROC: {best[0]}  → AUROC={best[1]:.4f}, F1={best[3]:.4f}")
