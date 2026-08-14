"""
P1-R1 Cross-Source Failure Anatomy -- Stage 1: score every image in the
DF40-cdf replication set (splits/v815_replication_set.tsv) with Layer1(v812)
+ Cell C + v816, and cache per-image scores to a CSV for all downstream
analysis scripts in this research round.

This is a NEW, read-only analysis script (does not modify eval_replication_set_v816.py,
eval_replication_auroc_v816.py, threshold_sweep_v816.py, or threshold_sweep_v815.py --
it reuses their model-loading pattern but is an independent file). No checkpoint,
split file, or existing result file is written to or altered.

python p1_r1_score_replication_set.py
"""
import sys
import warnings
from pathlib import Path

import numpy as np
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

OUT_DIR = BASE / "results" / "research" / "p1_r1_cross_source_failure_anatomy_20260814"
OUT_DIR.mkdir(parents=True, exist_ok=True)

L1_CKPT = BASE / "shufflenet_v2_layer1_v812.pth"
CELLC_CKPT = BASE / "shufflenet_v2_layer2_v815ablation_cellC_unfreeze1_inv0.pth"
V816_CKPT = BASE / "shufflenet_v2_layer2_v816_mixedlineage.pth"

# calibration thresholds -- reused from results/threshold_sweep_v815.log and
# results/threshold_sweep_v816.log (both already-existing, unmodified result
# files; NOT recomputed here, just cited)
CELLC_THRESHOLD = 0.85
V816_THRESHOLD_CALIBRATED = 0.95
V816_THRESHOLD_UNCALIBRATED = 0.85  # kept for direct apples-to-apples reference

REPLICATION_TSV = BASE / "splits" / "v815_replication_set.tsv"

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
    """Layer1 architecture (real vs manipulated, 2-class softmax)."""
    def __init__(self, num_classes=2):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


class DualHeadModel(nn.Module):
    """Cell C / v816 architecture (independent fake-head + filter-head sigmoids)."""
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
    print(f"Layer1 loaded: {L1_CKPT.name}")

    cellc = DualHeadModel().to(device)
    cellc.load_state_dict(torch.load(CELLC_CKPT, map_location=device)); cellc.eval()
    print(f"Cell C loaded: {CELLC_CKPT.name}")

    v816 = DualHeadModel().to(device)
    v816.load_state_dict(torch.load(V816_CKPT, map_location=device)); v816.eval()
    print(f"v816 loaded: {V816_CKPT.name}")

    rows = []
    for line in REPLICATION_TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("id\t") or not line.strip():
            continue
        parts = line.split("\t")
        rows.append(dict(id=parts[0], path=parts[1], fake_label=int(parts[2]),
                          filter_attr=int(parts[3]), ftype=parts[4],
                          source=parts[5], used_in_v815_training=parts[6],
                          source_stem=parts[7]))
    print(f"Rows to score: {len(rows)}")

    out_rows = []
    for i, r in enumerate(rows, 1):
        try:
            pil_raw = Image.open(r["path"]).convert("RGB")
            pil = preprocess_jpeg(pil_raw, quality=85)
        except Exception as e:
            print(f"  SKIP {r['id']}: {e}")
            continue
        x = transform_infer(pil).unsqueeze(0).to(device)
        with torch.no_grad():
            l1_probs = torch.softmax(l1(x), dim=1)[0].cpu().numpy()
            p_real, p_manip = float(l1_probs[0]), float(l1_probs[1])
            p_fake_c, p_filter_c = [float(v) for v in torch.sigmoid(cellc(x))[0].cpu().numpy()]
            p_fake_v, p_filter_v = [float(v) for v in torch.sigmoid(v816(x))[0].cpu().numpy()]
        out_rows.append({
            **r,
            "l1_p_real": p_real, "l1_p_manip": p_manip,
            "cellc_p_fake": p_fake_c, "cellc_p_filter": p_filter_c,
            "v816_p_fake": p_fake_v, "v816_p_filter": p_filter_v,
        })
        if i % 200 == 0:
            print(f"  {i}/{len(rows)} scored ...")

    df = pd.DataFrame(out_rows)
    out_path = OUT_DIR / "per_image_scores.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df)} scored rows -> {out_path}")


if __name__ == "__main__":
    main()
