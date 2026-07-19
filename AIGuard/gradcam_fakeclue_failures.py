"""
Grad-CAM++ on FakeClue failure cases for paper figures.

Samples FF++ deepfake frames that v3 misclassifies as 'filter' (OOD→filter problem),
plus some correct cases for contrast. Output: gradcam_failures/ with 3-panel figures.

Usage:
    python AIGuard/gradcam_fakeclue_failures.py
"""
import csv, os, random
import cv2, numpy as np, torch, torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
import torch.nn.functional as F
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from pathlib import Path

BASE    = Path(r"C:\My_Project\AIGC")
CKPT    = BASE / "shufflenet_v2_3class_ffhq_v3.pth"
OUT_DIR = BASE / "gradcam_failures"
CLASSES = ["real", "fake", "filter"]
DEVICE  = "cuda" if torch.cuda.is_available() else "cpu"

transform = T.Compose([T.Resize((224,224)), T.ToTensor(), T.Normalize([0.5]*3,[0.5]*3)])


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3,32,3,padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32,64,3,padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64,128,3,padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128*4*4, out_dim), nn.ReLU())
    def forward(self, x):
        fft = torch.fft.fft2(x, norm='ortho')
        fft = torch.fft.fftshift(fft, dim=(-2,-1))
        return self.net(torch.log(torch.abs(fft)+1e-8))


class DualBranchModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None)
        bb.fc = nn.Identity()
        self.spatial_branch = bb
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280,512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512,3))
    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], dim=1))


class GradCAMPlusPlus:
    def __init__(self, model, target_layer):
        self.model = model
        self._act = None; self._grad = None
        target_layer.register_forward_hook(lambda m,i,o: setattr(self,'_act',o.detach()))
        target_layer.register_full_backward_hook(lambda m,gi,go: setattr(self,'_grad',go[0].detach()))

    def generate(self, inp, class_idx=None):
        self.model.eval()
        inp = inp.to(DEVICE)
        inp.requires_grad_(True)
        out = self.model(inp)
        probs = F.softmax(out, 1)[0]
        if class_idx is None:
            class_idx = out.argmax(1).item()
        self.model.zero_grad()
        out[0, class_idx].backward()
        features = self._act; gradients = self._grad
        g2 = gradients**2; g3 = gradients**3
        sf = features.sum(dim=[2,3], keepdim=True)
        denom = 2*g2 + sf*g3
        denom = torch.where(denom!=0, denom, torch.ones_like(denom))
        alpha = g2/denom
        weights = (alpha * torch.relu(gradients)).sum(dim=[2,3], keepdim=True)
        cam = torch.relu((weights*features).sum(1)).squeeze().cpu().numpy()
        cam = cv2.resize(cam, (224,224))
        if cam.max() > cam.min():
            cam = (cam-cam.min())/(cam.max()-cam.min())
        return cam, class_idx, probs.detach().cpu().numpy()


def save_figure(img_path, cam, probs, gt_label, out_path):
    img_bgr = cv2.imread(img_path)
    img_bgr = cv2.resize(img_bgr, (224,224))
    heat = cv2.applyColorMap((cam*255).astype(np.uint8), cv2.COLORMAP_JET)
    blend = cv2.addWeighted(img_bgr, 0.55, heat, 0.45, 0)

    pred_cls = int(np.argmax(probs))
    pred_lbl = CLASSES[pred_cls]
    conf = probs[pred_cls]

    fig, axes = plt.subplots(1, 3, figsize=(15,5))
    axes[0].imshow(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    axes[0].set_title(f"Input  (GT: {gt_label})", fontsize=12); axes[0].axis("off")
    axes[1].imshow(cv2.cvtColor(blend, cv2.COLOR_BGR2RGB))
    axes[1].set_title(f"Grad-CAM++ → {pred_lbl} ({conf:.1%})", fontsize=12); axes[1].axis("off")

    # softmax bar chart
    axes[2].barh(CLASSES, probs, color=["#2196F3","#F44336","#FF9800"])
    axes[2].set_xlim(0,1); axes[2].set_xlabel("P(class)")
    axes[2].set_title("Class Probabilities", fontsize=12)
    for i,p in enumerate(probs):
        axes[2].text(p+0.01, i, f"{p:.3f}", va="center")

    result = "CORRECT" if pred_lbl == gt_label else f"WRONG→{pred_lbl}"
    fig.suptitle(f"{Path(img_path).name}  [{result}]", fontsize=11)
    plt.tight_layout()
    plt.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    return pred_lbl, conf


def main():
    random.seed(42)
    OUT_DIR.mkdir(exist_ok=True)

    model = DualBranchModel().to(DEVICE)
    model.load_state_dict(torch.load(CKPT, map_location=DEVICE))
    model.eval()
    cam_gen = GradCAMPlusPlus(model, model.spatial_branch.conv5)

    rows = list(csv.DictReader(open(BASE/"FakeClue/test_clean/labels.csv", encoding="utf-8")))

    # Separate FF++ frames (deepfake cate) from others
    ffpp_fake = [r for r in rows if r["label"]=="0" and "ff++" in r["path"].replace("\\","/").lower()]
    ffpp_real = [r for r in rows if r["label"]=="1" and "ff++" in r["path"].replace("\\","/").lower()]
    genimage   = [r for r in rows if r["label"]=="0" and "genimage" in r["path"].replace("\\","/").lower()]

    print(f"FF++ fake frames: {len(ffpp_fake)}")
    print(f"FF++ real frames: {len(ffpp_real)}")
    print(f"GenImage fake:    {len(genimage)}")

    # Run inference and collect: FF++ fakes misclassified as filter
    print("\nFinding OOD→filter failure cases...")
    filter_failures, correct_fake, correct_real = [], [], []

    for r in random.sample(ffpp_fake, min(200, len(ffpp_fake))):
        try:
            x = transform(Image.open(r["path"]).convert("RGB")).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                probs = F.softmax(model(x),1)[0].cpu().numpy()
            pred = int(np.argmax(probs))
            entry = {"path":r["path"], "probs":probs, "pred":pred}
            if pred==2:   filter_failures.append(entry)  # FF++ fake → filter
            elif pred==1: correct_fake.append(entry)      # FF++ fake → fake (correct)
        except Exception: pass

    for r in random.sample(ffpp_real, min(50, len(ffpp_real))):
        try:
            x = transform(Image.open(r["path"]).convert("RGB")).unsqueeze(0).to(DEVICE)
            with torch.no_grad():
                probs = F.softmax(model(x),1)[0].cpu().numpy()
            pred = int(np.argmax(probs))
            if pred==0: correct_real.append({"path":r["path"],"probs":probs,"pred":pred})
        except Exception: pass

    print(f"OOD→filter failures: {len(filter_failures)} out of checked FF++ fakes")
    print(f"Correct fake preds:  {len(correct_fake)}")
    print(f"Correct real preds:  {len(correct_real)}")

    # Generate Grad-CAM for: 4 filter-failures, 2 correct-fake, 2 correct-real
    cases = [
        (random.sample(filter_failures, min(4, len(filter_failures))), "fake", "failure_filter"),
        (random.sample(correct_fake,    min(2, len(correct_fake))),    "fake", "correct_fake"),
        (random.sample(correct_real,    min(2, len(correct_real))),    "real", "correct_real"),
    ]

    summary = []
    for case_list, gt, prefix in cases:
        for i, entry in enumerate(case_list):
            p = entry["path"]
            x = transform(Image.open(p).convert("RGB")).unsqueeze(0).to(DEVICE)
            cam, pred_cls, probs = cam_gen.generate(x, class_idx=entry["pred"])
            out_path = OUT_DIR / f"{prefix}_{i+1}.png"
            pred_lbl, conf = save_figure(p, cam, entry["probs"], gt, out_path)
            summary.append({"file": out_path.name, "gt": gt,
                            "pred": CLASSES[pred_cls], "conf": f"{conf:.3f}"})
            print(f"  Saved: {out_path.name}  gt={gt} pred={CLASSES[pred_cls]} conf={conf:.3f}")

    print(f"\nAll figures saved to {OUT_DIR}")
    print("\nSummary:")
    print(f"{'file':40s} {'gt':6s} {'pred':6s} {'conf':6s}")
    for s in summary:
        print(f"  {s['file']:38s} {s['gt']:6s} {s['pred']:6s} {s['conf']}")


if __name__ == "__main__":
    main()
