"""
arch1_unified_20260826 gate harness. Copied verbatim from
`eval_pcand_v2_full_gates.py` (production_candidate_v2_20260823) -- same
decision rule, same populations, same output shape, same FF++ zero-shot /
official-test metrics -- with ONE addition on top of that file's existing
`--layer1-backbone {shufflenet,repvit}` flag: a matching `--layer2-backbone
{shufflenet,repvit}` flag, so a RepViT Layer2 VIEW (exported by
`AIGuard/train_arch1_unified.py`'s `export_split_checkpoints()` -- same
spatial_branch+fft_branch weights as the Layer1 view, different classifier
head) can be scored by this harness without reimplementing any gate logic.
Output directory changed to this round's folder; everything else unchanged.

python eval_arch1_unified_gates.py --arm S1 \
       --layer1 <...layer1view.pth> --layer2 <...layer2view.pth> \
       --layer1-backbone repvit --layer2-backbone repvit [--gates all|comma,list]

=============================================================================
fix_paired_contrast_layer2_20260901 EXTENSION -- documented in full.

Copied verbatim from `filter2_realfilter_train_20260831/eval_gates.py`. Changes,
and ONLY these:

  1. ROUND_OUT -> "fix_paired_contrast_layer2_20260901".
  2. A new `--layer2-type threeclass` value, for this round's 3-class Layer2
     (index convention 0=fake, 1=filter, 2=real).

How (2) is implemented WITHOUT touching a single gate body or call site:
  * `Scorer.__init__` builds a 3-class DualBranchModel when l2_type ==
    "threeclass".
  * `Scorer.score` returns, in the SAME 5-slot shape as before:
        pf, pfl = softmax over the {fake, filter} logits only -- i.e. exactly
                  the production conditional p_fake|manip / p_filter|manip, so
                  every AUROC / composite / low-FPR gate keeps its meaning;
        pfb     = Layer2's 3-way p_real. The `pfb` slot is otherwise the
                  optional SECOND-Layer2 probability, which is unused in this
                  round (`--layer2b` is never passed, so it would be all
                  zeros). Reusing it means no gate body changes.
  * `decide()` gains a "threeclass" branch, and every existing call site
    already forwards `pfb` positionally, so nothing else changes.

DECISION RULE FOR THE 3-CLASS LAYER2 (explicit, and candidate-only):
      Layer1 gate as usual: p_manip < tm  ->  "real"
      otherwise Layer2's 3-way argmax, where Layer2 predicting `real` makes the
      final label "real" -- this is precisely the capability being added.
      Otherwise "fake"/"filter" by the fake-vs-filter ordering, unchanged.
  Because pf/pfl are the CONDITIONAL probabilities, "3-way argmax == real" is
  evaluated in the algebraically identical form
      p_real / (1 - p_real)  >  max(p_fake|m, p_filter|m)
  (using p_fake3 = (1-p_real)*p_fake|m and p_filter3 = (1-p_real)*p_filter|m).
  This changes decision_rule semantics FOR THIS CANDIDATE ONLY and must NOT be
  silently applied to production, whose Layer2 has no `real` output at all.

⚠️ The `alibaba` gate is CONTAMINATED for this candidate -- see
   contamination_check.json (1,706/1,706 gate FFHQ base ids, and 1,325 exact
   image paths, are in this round's training data). Its number is recorded for
   completeness and is NON-COMPARABLE.
=============================================================================
"""
import argparse
import hashlib
import json
import random
import sys
import warnings
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from sklearn.metrics import roc_auc_score, roc_curve
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

warnings.filterwarnings("ignore")
BASE = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"
ROUND = "p1_r8_shadow_composite_tradeoff_20260819"   # read-only: stress cache + stressdev live here
ROUND_OUT = "backbone_hier_20260907"  # COPIED VERBATIM from fix_grain_robust_20260903/eval_gates.py; only this line changed
STRESSDIR = BASE / "results" / "research" / ROUND
OUTDIR = BASE / "results" / "research" / ROUND_OUT
FFPP_MANIFEST = BASE / "FaceForensics_frames" / "manifest.txt"
FFPP_TEST_SPLIT = BASE / "splits" / "research" / "ffpp_protocol_20260823" / "ffpp_test.txt"
sys.path.insert(0, str(BASE))
from pipeline import preprocess_jpeg  # noqa: E402

FTYPES = ("smoothing", "whitening", "eye_enlarging", "face_reshaping")
transform_infer = transforms.Compose([
    transforms.Resize((224, 224)), transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3)])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(), nn.AdaptiveAvgPool2d(4),
            nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU())

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho")
        f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


def _build_spatial(arch, pretrained=False):
    """ShuffleNetV2 (production) or MobileNetV4 (timm mobilenetv4_conv_small.e2400_r224_in1k,
    the same model benchmarked on FF++/cross-dataset). Output width measured by a forward pass."""
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=tv_models.ShuffleNet_V2_X1_0_Weights.DEFAULT if pretrained else None)
        bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k", pretrained=pretrained, num_classes=0)
    m.eval()
    with torch.no_grad():
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]
    return m, int(dim)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=2, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch, pretrained=False)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


class DualBranchModelRepViT(nn.Module):
    """RepViT-M0.9 spatial branch (Stream-2 candidate architecture)."""
    def __init__(self, num_classes=2):
        super().__init__()
        import timm
        self.spatial_branch = timm.create_model("repvit_m0_9.dist_300e_in1k", pretrained=False, num_classes=0)
        with torch.no_grad():
            dim = self.spatial_branch(torch.zeros(2, 3, 224, 224)).shape[1]
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


class DualBranchProtoModel(nn.Module):
    """p1_prototype_20260828 Layer1 candidate: production backbone + RCDN-style
    embedding head (Linear 512->128, L2-normalized) + 2-class classifier on the
    normalized embedding. Forward emits 2-class logits -> drop-in for Layer1."""
    def __init__(self, num_classes=2):
        super().__init__()
        import torch.nn.functional as F  # noqa: F401
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.trunk = nn.Sequential(nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3))
        self.embed = nn.Linear(512, 128)
        self.cls = nn.Linear(128, num_classes)

    def forward(self, x):
        import torch.nn.functional as F
        h = self.trunk(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))
        zhat = F.normalize(self.embed(h), dim=1)
        return self.cls(zhat)


class DualHeadModel(nn.Module):
    def __init__(self):
        super().__init__()
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        self.spatial_branch = bb; self.fft_branch = FFTBranch(256)
        self.trunk = nn.Sequential(nn.Linear(1280, 512), nn.ReLU(), nn.Dropout(0.3))
        self.fake_head = nn.Linear(512, 1); self.filter_head = nn.Linear(512, 1)

    def forward(self, x):
        h = self.trunk(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))
        return torch.cat([self.fake_head(h), self.filter_head(h)], 1)


class PathDataset(Dataset):
    def __init__(self, paths):
        self.paths = list(paths)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        p = self.paths[i]
        try:
            pil = Image.open(p).convert("RGB")
        except Exception:
            return torch.zeros(3, 224, 224), i, 0
        return transform_infer(preprocess_jpeg(pil, quality=85)), i, 1


class Scorer:
    def __init__(self, l1_path, l2_path, l2_type, device, batch=128, workers=6,
                 l2b_path=None, l1_backbone="shufflenet", l2_backbone="shufflenet"):
        self.device, self.batch, self.workers, self.l2_type = device, batch, workers, l2_type
        if l1_backbone == "proto":
            L1Cls = DualBranchProtoModel
        elif l1_backbone == "repvit":
            L1Cls = DualBranchModelRepViT
        else:
            L1Cls = DualBranchModel
        l1_sd = torch.load(l1_path, map_location=device)
        self.l1_classes = int(l1_sd["classifier.3.bias"].shape[0])  # 2 (prod) or 3 (FAM3 family head)
        self.l1 = (DualBranchModel(self.l1_classes, l1_backbone) if l1_backbone == "mobilenetv4" else L1Cls(self.l1_classes)).to(device)
        l1_sd.pop("_prototype", None)  # proto checkpoints carry the center vector
        self.l1.load_state_dict(l1_sd); self.l1.eval()
        if l2_type == "dualhead":
            self.l2 = DualHeadModel().to(device)
        else:
            L2Cls = DualBranchModelRepViT if l2_backbone == "repvit" else DualBranchModel
            self.l2 = (DualBranchModel(3 if l2_type == "threeclass" else 2, l2_backbone) if l2_backbone == "mobilenetv4" else L2Cls(3 if l2_type == "threeclass" else 2)).to(device)
        self.l2.load_state_dict(torch.load(l2_path, map_location=device)); self.l2.eval()
        self.l2b = None
        if l2b_path:
            self.l2b = DualBranchModel(2).to(device)
            self.l2b.load_state_dict(torch.load(l2b_path, map_location=device)); self.l2b.eval()

    def score(self, paths):
        n = len(paths)
        pm = np.zeros(n); pf = np.zeros(n); pfl = np.zeros(n)
        pfb = np.zeros(n); ok = np.zeros(n, bool)
        dl = DataLoader(PathDataset(paths), batch_size=self.batch, num_workers=self.workers,
                        shuffle=False, pin_memory=True)
        with torch.no_grad():
            for x, idx, good in dl:
                x = x.to(self.device, non_blocking=True)
                s1 = torch.softmax(self.l1(x), 1)
                o1 = (1.0 - s1[:, 0]) if s1.shape[1] == 3 else s1[:, 1]
                o2 = self.l2(x)
                if self.l2_type == "dualhead":
                    s = torch.sigmoid(o2)
                    a, b = s[:, 0], s[:, 1]
                elif self.l2_type == "threeclass":
                    # conditional fake-vs-filter (production semantics for pf/pfl)
                    s = torch.softmax(o2[:, :2], 1)
                    a, b = s[:, 0], s[:, 1]
                else:
                    s = torch.softmax(o2, 1)
                    a, b = s[:, 0], s[:, 1]
                i = idx.numpy()
                pm[i] = o1.cpu().numpy(); pf[i] = a.cpu().numpy(); pfl[i] = b.cpu().numpy()
                if self.l2_type == "threeclass":
                    # 5th slot carries Layer2's 3-way p_real (see module docstring)
                    pfb[i] = torch.softmax(o2, 1)[:, 2].cpu().numpy()
                elif self.l2b is not None:
                    pfb[i] = torch.softmax(self.l2b(x), 1)[:, 0].cpu().numpy()
                ok[i] = good.numpy().astype(bool)
        return pm, pf, pfl, ok, pfb


def decide(pm, pf, pfl, l2_type, thr, pfb=None, tau=None, tf=0.5, tm=0.5):
    out = np.full(len(pm), "real", dtype=object)
    manip = pm >= tm
    if l2_type == "dualhead":
        is_fake = manip & (pf > tf)
        if pfb is not None and tau is not None:
            is_fake = is_fake | (manip & (pfb > tau))
        out[is_fake] = "fake"
        out[manip & ~is_fake & (pfl > thr)] = "filter"
    elif l2_type == "threeclass":
        # pfb carries Layer2's 3-way p_real. "3-way argmax == real" <=>
        # p_real/(1-p_real) > max(p_fake|m, p_filter|m). Candidate-only rule.
        pr = np.clip(np.asarray(pfb, float), 0.0, 1.0 - 1e-12)
        l2_says_real = (pr / (1.0 - pr)) > np.maximum(pf, pfl)
        out[manip & l2_says_real] = "real"
        out[manip & ~l2_says_real & (pf >= pfl)] = "fake"
        out[manip & ~l2_says_real & (pf < pfl)] = "filter"
    else:
        out[manip & (pf >= pfl)] = "fake"
        out[manip & (pf < pfl)] = "filter"
    return out


def composite(pm, pf, tm=0.5):
    return np.where(pm < tm, pm * 0.5, pm * pf)


def read_lines(p):
    return [l.strip().split("\t")[0] for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("path\t")]


def clean_list(folder):
    return read_lines(BASE / folder / "clean_output" / "clean_paths.txt")


def strip_type(stem):
    for ft in FTYPES:
        if stem.startswith(ft + "_"):
            return stem[len(ft) + 1:], ft
    return stem, "unknown"


def collect_truetest_pairs():
    real = {Path(p).stem: p for p in read_lines(SPLITS / "truetest_real.txt")}
    pairs = []
    for p in read_lines(SPLITS / "truetest_filter.txt"):
        s, ft = strip_type(Path(p).name.rsplit(".", 1)[0])
        if s in real:
            pairs.append((real[s], p, ft))
    return pairs


def collect_shadow_pairs():
    real = {Path(p).stem: p for p in clean_list("shadow_vggface2_real")}
    pairs = []
    for p in clean_list("shadow_filter"):
        s, ft = strip_type(Path(p).stem)
        if s in real and ft != "unknown":
            pairs.append((real[s], p, ft))
    return pairs


def paired_block(name, pairs, sc, l2_type, thr, dump, tau=None, tf=0.5, tm=0.5):
    reals = [a for a, _, _ in pairs]; filts = [b for _, b, _ in pairs]
    types = [t for _, _, t in pairs]
    prm, pfr, pflr, _, pfbr = sc.score(reals)
    pmf, pff, pflf, _, pfbf = sc.score(filts)
    dr = decide(prm, pfr, pflr, l2_type, thr, pfbr, tau, tf, tm)
    df = decide(pmf, pff, pflf, l2_type, thr, pfbf, tau, tf, tm)
    real_ok = dr == "real"; filt_ok = df == "filter"
    by_type = defaultdict(lambda: [0, 0, 0])
    for i, t in enumerate(types):
        by_type[t][0] += 1
        by_type[t][1] += int(filt_ok[i])
        by_type[t][2] += int(real_ok[i] and filt_ok[i])
    res = dict(
        n=len(pairs),
        real_recall=float(real_ok.mean() * 100),
        filter_recall=float(filt_ok.mean() * 100),
        balanced=float((real_ok.mean() + filt_ok.mean()) / 2 * 100),
        strict=float((real_ok & filt_ok).mean() * 100),
        by_type={t: dict(n=v[0], filter_recall=v[1] / v[0] * 100, strict=v[2] / v[0] * 100)
                 for t, v in sorted(by_type.items())},
    )
    dump[name] = dict(
        real_paths=reals, filter_paths=filts, types=types,
        real_correct=real_ok.astype(int).tolist(), filter_correct=filt_ok.astype(int).tolist(),
        real_p_manip=prm.tolist(), filter_p_manip=pmf.tolist(),
        real_p_fake=pfr.tolist(), filter_p_fake=pff.tolist(),
        real_p_filter=pflr.tolist(), filter_p_filter=pflf.tolist(),
    )
    return res


def tpr_at_fpr(y, s, target):
    neg = np.sort(s[y == 0])[::-1]
    k = int(np.floor(target * len(neg)))
    thr = neg[k] if k < len(neg) else -np.inf
    return float((s[y == 1] > thr).mean())


def pauc(y, s, maxfpr=0.05):
    fpr, tpr, _ = roc_curve(y, s)
    m = fpr <= maxfpr
    if m.sum() < 2:
        return 0.0
    return float(np.trapz(tpr[m], fpr[m]) / maxfpr)


def ffpp_block(name, paths, cls, meth, sc, l2_type, thr, tm):
    pm, pf, pfl, ok, pfb = sc.score(paths)
    d = decide(pm, pf, pfl, l2_type, thr, pfb, None, 0.5, tm)
    y = np.array([0 if c == "real" else 1 for c in cls])
    s_l1 = pm; s_e2e = composite(pm, pf, tm)
    per = defaultdict(lambda: [0, 0])
    for m, c, pred in zip(meth, cls, d):
        per[m][0] += 1
        per[m][1] += int(pred == "real" if c == "real" else pred != "real")
    return dict(
        n=len(paths),
        auroc_layer1=float(roc_auc_score(y, s_l1)), auroc_end2end=float(roc_auc_score(y, s_e2e)),
        pauc5_layer1=pauc(y, s_l1, 0.05), pauc5_end2end=pauc(y, s_e2e, 0.05),
        tpr_at_fpr1_layer1=tpr_at_fpr(y, s_l1, 0.01), tpr_at_fpr5_layer1=tpr_at_fpr(y, s_l1, 0.05),
        tpr_at_fpr1_end2end=tpr_at_fpr(y, s_e2e, 0.01), tpr_at_fpr5_end2end=tpr_at_fpr(y, s_e2e, 0.05),
        per_method={k: dict(n=v[0], rate=v[1] / v[0] * 100) for k, v in sorted(per.items())},
        fake_catch_rate=float(np.mean([d[i] != "real" for i in range(len(d)) if cls[i] != "real"]) * 100),
        real_recall=float(np.mean([d[i] == "real" for i in range(len(d)) if cls[i] == "real"]) * 100),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arm", required=True)
    ap.add_argument("--layer1", required=True)
    ap.add_argument("--layer2", required=True)
    ap.add_argument("--layer1-backbone", default="shufflenet", choices=["shufflenet", "repvit", "proto", "mobilenetv4"])
    ap.add_argument("--layer2-backbone", default="shufflenet", choices=["shufflenet", "repvit", "mobilenetv4"])
    ap.add_argument("--layer2-type", default="twoclass",
                    choices=["twoclass", "dualhead", "threeclass"])
    ap.add_argument("--filter-threshold", type=float, default=None)
    ap.add_argument("--manip-threshold", type=float, default=0.5)
    ap.add_argument("--gates", default="all")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()

    l1p, l2p = Path(a.layer1), Path(a.layer2)
    for p in (l1p, l2p):
        if not p.is_file():
            print(f"ERROR: checkpoint not found: {p}"); sys.exit(1)
    thr = a.filter_threshold if a.filter_threshold is not None else 0.5

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sc = Scorer(str(l1p), str(l2p), a.layer2_type, device, a.batch, a.workers,
                l1_backbone=a.layer1_backbone, l2_backbone=a.layer2_backbone)
    prov = dict(arm=a.arm, layer1=str(l1p.resolve()), layer1_sha256=sha256(l1p),
                layer1_backbone=a.layer1_backbone,
                layer2=str(l2p.resolve()), layer2_sha256=sha256(l2p),
                layer2_backbone=a.layer2_backbone,
                layer2_type=a.layer2_type, filter_threshold=thr, manip_threshold=a.manip_threshold,
                script=str(Path(__file__).resolve()), script_sha256=sha256(Path(__file__)), device=device)
    print(json.dumps(prov, indent=2))
    want = set(x.strip() for x in a.gates.split(",")) if a.gates != "all" else None

    def on(g):
        return want is None or g in want

    R = {}
    dump = {}

    if on("truetest"):
        tt = collect_truetest_pairs()
        R["truetest_paired"] = paired_block("truetest", tt, sc, a.layer2_type, thr, dump, tf=0.5, tm=a.manip_threshold)
        fake_paths = read_lines(SPLITS / "truetest_fake.txt")
        pm, pf, pfl, _, pfb = sc.score(fake_paths)
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        R["truetest_fake_recall"] = dict(n=len(fake_paths), recall=float((d == "fake").mean() * 100))
        print("  truetest:", json.dumps({k: v for k, v in R["truetest_paired"].items() if k != "by_type"}),
              R["truetest_fake_recall"])

    if on("truetest_lowfpr"):
        real_paths = read_lines(SPLITS / "truetest_real.txt")
        fake_paths = read_lines(SPLITS / "truetest_fake.txt")
        pmr, pfr, _, _, _ = sc.score(real_paths)
        pmf, pff, _, _, _ = sc.score(fake_paths)
        sr = composite(pmr, pfr, a.manip_threshold)
        sf = composite(pmf, pff, a.manip_threshold)
        y = np.array([0] * len(sr) + [1] * len(sf))
        s = np.concatenate([sr, sf])
        R["truetest_lowfpr"] = dict(
            n=len(y), auroc=float(roc_auc_score(y, s)),
            tpr_at_fpr1=tpr_at_fpr(y, s, 0.01), tpr_at_fpr5=tpr_at_fpr(y, s, 0.05),
            pauc5=pauc(y, s, 0.05))
        print("  truetest_lowfpr:", R["truetest_lowfpr"])

    if on("shadow"):
        sh = collect_shadow_pairs()
        R["shadow_paired"] = paired_block("shadow", sh, sc, a.layer2_type, thr, dump, tf=0.5, tm=a.manip_threshold)
        print("  shadow:", json.dumps({k: v for k, v in R["shadow_paired"].items() if k != "by_type"}))

    if on("unseen"):
        lines = read_lines(BASE / "AIGuard" / "unseen" / "clean_output" / "clean_paths.txt")
        y = [1 if "fake" in Path(p).parts[-2].lower() or "fake" in p.lower() else 0 for p in lines]
        pm, pf, pfl, _, pfb = sc.score(lines)
        s = composite(pm, pf, a.manip_threshold)
        R["aiguard_unseen_auroc"] = dict(n=len(lines), auroc=float(roc_auc_score(y, s)))
        print("  unseen AUROC:", R["aiguard_unseen_auroc"])

    if on("celeba"):
        random.seed(42)
        imgs = sorted((BASE / "celeba_test").glob("*.jpg"))
        random.shuffle(imgs)
        sample = [str(p) for p in imgs[:3000]]
        pm, pf, pfl, _, pfb = sc.score(sample)
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        R["celeba_real_recall"] = dict(n=len(sample), recall=float((d == "real").mean() * 100))
        print("  celeba:", R["celeba_real_recall"])

    if on("stylegan2"):
        random.seed(42)
        imgs = sorted((BASE / "stylegan2_test" / "fake").glob("*.jpg")) + \
            sorted((BASE / "stylegan2_test" / "fake").glob("*.png"))
        random.shuffle(imgs)
        sample = [str(p) for p in imgs[:3000]]
        pm, pf, pfl, _, pfb = sc.score(sample)
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        R["stylegan2_notreal_recall"] = dict(n=len(sample), recall=float((d != "real").mean() * 100))
        print("  stylegan2:", R["stylegan2_notreal_recall"])

        # Decontaminated variant (mission ask: use canonical exclusion list from
        # remeasure_sweep_20260826 if it states one). Same 3000-sample draw,
        # canonical-contaminated basenames dropped before scoring.
        excl_path = BASE / "results" / "research" / "remeasure_sweep_20260826" / "stylegan2_decontam_exclusion_CANONICAL.json"
        if excl_path.is_file():
            excl = set(json.loads(excl_path.read_text(encoding="utf-8"))["canonical_exclusion_basenames"])
            clean_imgs = [p for p in imgs if p.name not in excl]
            random.seed(42); random.shuffle(clean_imgs)
            csample = [str(p) for p in clean_imgs[:3000]]
            pmc, pfc, pflc, _, pfbc = sc.score(csample)
            dc = decide(pmc, pfc, pflc, a.layer2_type, thr, pfbc, None, 0.5, a.manip_threshold)
            R["stylegan2_decontam_notreal_recall"] = dict(
                n=len(csample), n_excluded_from_pool=len(imgs) - len(clean_imgs),
                recall=float((dc != "real").mean() * 100))
            print("  stylegan2_decontam:", R["stylegan2_decontam_notreal_recall"])

    if on("stress"):
        man = STRESSDIR / "stress_cache_manifest.tsv"
        rows = [l.split("\t") for l in man.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        valid = [r for r in rows if r[2] != "SKIP" and r[1] != "base"]
        pm, pf, pfl, _, pfb = sc.score([r[2] for r in valid])
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        per = defaultdict(lambda: [0, 0])
        for r, pred in zip(valid, d):
            per[r[1]][0] += 1; per[r[1]][1] += int(pred != "fake")
        R["fake_filter_stress"] = dict(
            n=len(valid), misclassified=int((d != "fake").sum()), error_pct=float((d != "fake").mean() * 100),
            per_condition={k: dict(n=v[0], misclassified=v[1], error_pct=v[1] / v[0] * 100) for k, v in sorted(per.items())})
        print("  stress:", R["fake_filter_stress"]["error_pct"])

    if on("alibaba"):
        rows = read_lines(SPLITS / "ood_filter_ali.txt")
        pm, pf, pfl, _, pfb = sc.score(rows)
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        bt = defaultdict(lambda: [0, 0])
        for p, pred in zip(rows, d):
            combo = Path(p).parent.parent.name
            ft = combo.rsplit("_", 1)[0]
            bt[ft][0] += 1; bt[ft][1] += int(pred == "filter")
        R["alibaba_filter_recall"] = dict(
            n=len(rows), recall=float((d == "filter").mean() * 100),
            by_type={k: dict(n=v[0], recall=v[1] / v[0] * 100) for k, v in sorted(bt.items())})
        print("  alibaba:", R["alibaba_filter_recall"]["recall"])

    if on("stressdev"):
        man = SPLITS / "research" / ROUND / "stressdev_manifest.tsv"
        rows = [l.split("\t") for l in man.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        pm, pf, pfl, _, pfb = sc.score([r[2] for r in rows])
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        per = defaultdict(lambda: [0, 0])
        for r, pred in zip(rows, d):
            per[r[1]][0] += 1; per[r[1]][1] += int(pred != "fake")
        R["stressdev"] = dict(n=len(rows), error_pct=float((d != "fake").mean() * 100),
                              per_condition={k: dict(n=v[0], error_pct=v[1] / v[0] * 100) for k, v in sorted(per.items())})
        print("  stressdev:", R["stressdev"]["error_pct"])

    if on("indomain_filter"):
        rows = [l.split("\t") for l in
                (SPLITS / "v815_clean_val.txt").read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        rf = [r[0] for r in rows if r[3] == "real_filter"]
        cf = [r[0] for r in rows if r[3] == "clean_fake"]
        pm, pf, pfl, _, pfb = sc.score(rf)
        d = decide(pm, pf, pfl, a.layer2_type, thr, pfb, None, 0.5, a.manip_threshold)
        pm2, pf2, pfl2, _, pfb2 = sc.score(cf)
        d2 = decide(pm2, pf2, pfl2, a.layer2_type, thr, pfb2, None, 0.5, a.manip_threshold)
        R["indomain_filter"] = dict(
            real_filter_n=len(rf), real_filter_recall=float((d == "filter").mean() * 100),
            clean_fake_n=len(cf), clean_fake_fake_recall=float((d2 == "fake").mean() * 100),
            clean_fake_false_filter=float((d2 == "filter").mean() * 100))
        print("  indomain_filter:", R["indomain_filter"])

    if on("ffpp_zeroshot"):
        rows = [l.split("\t") for l in FFPP_MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
        paths = [r[0] for r in rows]; cls = [r[1] for r in rows]; meth = [r[2] for r in rows]
        R["ffpp_zeroshot_900frame"] = ffpp_block("ffpp_zs", paths, cls, meth, sc, a.layer2_type, thr, a.manip_threshold)
        print("  ffpp_zeroshot(900f):", {k: v for k, v in R["ffpp_zeroshot_900frame"].items() if k not in ("per_method",)})

    if on("ffpp_official_test"):
        rows = [l.split("\t") for l in FFPP_TEST_SPLIT.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
        paths = [r[0] for r in rows]; cls = ["real" if r[1] == "0" else r[2] for r in rows]; meth = [r[2] for r in rows]
        R["ffpp_official_test_frame"] = ffpp_block("ffpp_test", paths, cls, meth, sc, a.layer2_type, thr, a.manip_threshold)
        print("  ffpp_official_test(frame):", {k: v for k, v in R["ffpp_official_test_frame"].items() if k not in ("per_method",)})
        # video-level: average score per (method, video_id)
        pm, pf, pfl, _, pfb = sc.score(paths)
        s_e2e = composite(pm, pf, a.manip_threshold)
        vids = [(r[2], r[3]) for r in rows]
        agg = defaultdict(list); ycls = {}
        for (m, v), score, c in zip(vids, s_e2e, cls):
            agg[(m, v)].append(score); ycls[(m, v)] = 0 if c == "real" else 1
        keys = list(agg.keys())
        vs = np.array([np.mean(agg[k]) for k in keys])
        vy = np.array([ycls[k] for k in keys])
        R["ffpp_official_test_video"] = dict(n=len(keys), auroc=float(roc_auc_score(vy, vs)))
        print("  ffpp_official_test(video AUROC):", R["ffpp_official_test_video"])

    # ---- contamination flagging (PRE_DECLARED mandate) -------------------
    cc_path = OUTDIR / "contamination_check.json"
    if "alibaba_filter_recall" in R and cc_path.is_file():
        cc = json.loads(cc_path.read_text(encoding="utf-8"))
        ov = cc["alibaba_gate_raw_split_used_by_eval_gates"]["base_id_overlap_with_training"]
        R["alibaba_filter_recall"]["CONTAMINATED"] = ov > 0
        R["alibaba_filter_recall"]["contamination_note"] = (
            f"NON-COMPARABLE: {ov} FFHQ base ids of splits/ood_filter_ali.txt "
            f"(and "
            f"{cc['alibaba_gate_raw_split_used_by_eval_gates']['exact_path_overlap_with_training_images']}"
            " exact image paths) are in this candidate's training data. "
            "This number must NOT be cited as a passing gate."
            if ov > 0 else "clean")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"gates_{a.arm}.json"
    out.write_text(json.dumps(dict(provenance=prov, gates=R), indent=2), encoding="utf-8")
    (OUTDIR / f"perimage_{a.arm}.json").write_text(json.dumps(dump), encoding="utf-8")
    print(f"\n[out] {out}")


if __name__ == "__main__":
    main()
