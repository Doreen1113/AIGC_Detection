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
# Grad-CAM++
# ──────────────────────────────────────────────
class GradCAMPlusPlus:
    def __init__(self, model, target_layer):
        self.model = model
        self._act  = None
        self._grad = None
        # 依然使用 Hook 捕捉前向與反向傳播的特徵圖與梯度
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

        # ───【Grad-CAM++ 數學原理核心實作】───
        # 1. 取得特徵圖與梯度
        features = self._act         # Shape: [1, C, H, W]
        gradients = self._grad       # Shape: [1, C, H, W]

        # 2. 計算一階、二階、三階梯度，用來求解 Grad-CAM++ 的 alpha 權重
        grads_power_2 = gradients ** 2
        grads_power_3 = gradients ** 3

        # 計算特徵圖在空間維度 (H, W) 的總和
        sum_features = torch.sum(features, dim=[2, 3], keepdim=True)

        # 根據 Grad-CAM++ 論文公式，計算每個像素梯度的加權係數 (alpha)
        alpha_denom = 2 * grads_power_2 + sum_features * grads_power_3
        # 避免除以 0
        alpha_denom = torch.where(alpha_denom != 0, alpha_denom, torch.ones_like(alpha_denom))
        
        alpha = grads_power_2 / alpha_denom

        # 3. 計算正向梯度的權重 (只考慮對預測有正向貢獻的梯度)
        weights = torch.sum(alpha * torch.relu(gradients), dim=[2, 3], keepdim=True)

        # 4. 對特徵圖進行加權求和，並套用 ReLU
        cam = torch.relu((weights * features).sum(dim=1)).squeeze()
        
        # ───【後處理：縮放與歸一化】───
        cam = cam.cpu().numpy()
        cam = cv2.resize(cam, (224, 224))
        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
            
        return cam, class_idx, probs[class_idx].item()

def overlay_heatmap(img_bgr, cam, alpha=0.45):
    """cam 疊在原圖上，紅色=高激活（可疑），藍色=低激活。"""
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    img_resized = cv2.resize(img_bgr, (224, 224))
    gradcam_blended = cv2.addWeighted(img_resized, 1 - alpha, heat, alpha, 0)
    """
    將 Grad-CAM++ 矩陣轉化為 FakeShield 風格的黑白精準遮罩 (Binary Mask)。
    輸出將會是純黑白的影像：白色代表模型認定的偽造篡改區域，黑色為背景。
    """
    cam_gray = (cam * 255).astype(np.uint8)
    _, binary_mask = cv2.threshold(cam_gray, 115, 255, cv2.THRESH_BINARY)
    binary_mask_resized = cv2.resize(binary_mask, (224, 224))
    fakeshield_mask = cv2.cvtColor(binary_mask_resized, cv2.COLOR_GRAY2BGR)

    return gradcam_blended, fakeshield_mask

def save_gradcam_figure(img_bgr, cam, pred_label, confidence, out_path, title):
    """
    橫向三圖併排排版：
    [ 1. 原始圖片 ] ---> [ 2. Grad-CAM++ 漸層 ] ---> [ 3. FakeShield 二值化遮罩 ]
    符合 FakeShield 邏輯的排版：
    - 若模型預測為 Fake：顯示二值化 Mask。
    - 若模型預測為 Real：不生成定位，Mask 顯示全黑。
    """
    # 呼叫修改後的函數，同時取得「漸層疊加圖」與「黑白遮罩」
    gradcam_blended, fakeshield_mask = overlay_heatmap(img_bgr, cam)

    if pred_label == "Real":
        # 如果模型判定是真圖，將 Mask 強行清空為全黑 (與原圖同尺寸)
        fakeshield_mask = np.zeros_like(gradcam_blended)
        mask_title = "3. FakeShield Mask (No Fake Detected)"
    else:
        # 如果是假圖，維持原本算出來的二值化遮罩
        mask_title = f"3. FakeShield Mask ({pred_label})"
    
    # 修改為 1 列 3 欄 (1, 3)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    # 圖 1：原始輸入圖
    axes[0].imshow(cv2.cvtColor(cv2.resize(img_bgr, (224, 224)), cv2.COLOR_BGR2RGB))
    axes[0].set_title("1. Input Image", fontsize=12, pad=8)
    axes[0].axis("off")
    
    # 圖 2：Grad-CAM++ 漸層熱圖
    axes[1].imshow(cv2.cvtColor(gradcam_blended, cv2.COLOR_BGR2RGB))
    axes[1].set_title(f"2. Grad-CAM++ ({confidence:.1%})", fontsize=12, pad=8)
    axes[1].axis("off")
    
    # 圖 3：FakeShield 黑白二值化精準遮罩
    axes[2].imshow(cv2.cvtColor(fakeshield_mask, cv2.COLOR_BGR2RGB))
    axes[2].set_title(f"3. FakeShield Mask ({pred_label})", fontsize=12, pad=8)
    axes[2].axis("off")
    
    # 排版與標題優化
    plt.suptitle(title, fontsize=11, y=1.02)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
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

    # ---- Grad-CAM++：target = conv5（最後 1x1 conv 後的 feature map）----
    gradcam = GradCAMPlusPlus(model, model.conv5)

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

    print(f"\nRunning Grad-CAM++ on {len(samples)} images...")
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
