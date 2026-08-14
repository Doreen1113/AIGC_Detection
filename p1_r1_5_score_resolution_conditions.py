"""
P1-R1.5 -- Stage 3: score every image referenced in resolution_manifest.csv
(native + canonical_256/512/1024, clean + 4 filter types) with the same
frozen checkpoints P1-R1 used: Layer1(v812), Cell C, v816. Inference only,
no training. New, read-only script.

python p1_r1_5_score_resolution_conditions.py
"""
import sys
import warnings
from pathlib import Path

import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from torchvision import transforms
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))
from pipeline import preprocess_jpeg  # noqa: E402

OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"

L1_CKPT = BASE / "shufflenet_v2_layer1_v812.pth"
CELLC_CKPT = BASE / "shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth"
V816_CKPT = BASE / "shufflenet_v2_layer2_v816_mixedlineage.pth"

transform_infer = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3)])


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU())

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho"); f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


class DualHeadModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.trunk = nn.Sequential(nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3))
        self.fake_head = nn.Linear(512, 1); self.filter_head = nn.Linear(512, 1)

    def forward(self, x):
        feat = torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1)
        h = self.trunk(feat)
        return torch.cat([self.fake_head(h), self.filter_head(h)], 1)


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    l1 = DualBranchModel(num_classes=2).to(device)
    l1.load_state_dict(torch.load(L1_CKPT, map_location=device)); l1.eval()
    cellc = DualHeadModel().to(device)
    cellc.load_state_dict(torch.load(CELLC_CKPT, map_location=device)); cellc.eval()
    v816 = DualHeadModel().to(device)
    v816.load_state_dict(torch.load(V816_CKPT, map_location=device)); v816.eval()
    print("All 3 checkpoints loaded")

    man = pd.read_csv(OUT_DIR / "resolution_manifest.csv")
    scoreable = man[man["status"].isin(["OK_GENERATED", "OK_REUSED_EXISTING"])].copy()
    print(f"Rows to score: {len(scoreable)} / {len(man)} manifest rows")

    out_rows = []
    for i, (_, r) in enumerate(scoreable.iterrows(), 1):
        try:
            pil_raw = Image.open(r["output_path"]).convert("RGB")
            pil = preprocess_jpeg(pil_raw, quality=85)
        except Exception as e:
            continue
        x = transform_infer(pil).unsqueeze(0).to(device)
        with torch.no_grad():
            l1_probs = torch.softmax(l1(x), dim=1)[0].cpu().numpy()
            p_real, p_manip = float(l1_probs[0]), float(l1_probs[1])
            p_fake_c, p_filter_c = [float(v) for v in torch.sigmoid(cellc(x))[0].cpu().numpy()]
            p_fake_v, p_filter_v = [float(v) for v in torch.sigmoid(v816(x))[0].cpu().numpy()]
        out_rows.append({
            "base_id": r["base_id"], "source": r["source"], "source_stem": r["source_stem"],
            "resolution_condition": r["resolution_condition"], "filter_type": r["filter_type"],
            "output_path": r["output_path"], "output_sha256": r["output_sha256"],
            "l1_p_real": p_real, "l1_p_manip": p_manip,
            "cellc_p_fake": p_fake_c, "cellc_p_filter": p_filter_c,
            "v816_p_fake": p_fake_v, "v816_p_filter": p_filter_v,
        })
        if i % 300 == 0:
            print(f"  {i}/{len(scoreable)} scored ...")

    df = pd.DataFrame(out_rows)
    out_path = OUT_DIR / "per_image_scores_by_resolution.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df)} scored rows -> {out_path}")


if __name__ == "__main__":
    main()
