"""
flat3class_revisit_20260828 gate harness.

Copied VERBATIM from results/research/p1a3_seed2_20260828/eval_p1a3_seed2_gates.py
(which itself is a verbatim copy of the production_candidate_v2_20260823 harness)
and extended -- WITHOUT modifying any existing gate logic, population, decision
rule or metric -- with a single new scoring path for FLAT 3-CLASS models
(single softmax over real/fake/filter, as used by v8.3-v8.8).

The existing two-model hierarchical path is untouched: pass --layer1/--layer2 as
before and byte-identical results are produced. The new path is opt-in via
--flat3 <checkpoint.pth>.

Flat-3-class mapping into the harness's (pm, pf, pfl) score triple:
    pm  = 1 - p_real      (probability the image is manipulated at all)
    pf  = p_fake          (raw, NOT renormalised)
    pfl = p_filter        (raw, NOT renormalised)
Decision rule for flat models is PLAIN ARGMAX over the three logits -- the
native rule these models were trained and historically evaluated with. The
session's decision_rule.decide()/tm=0.5 unification applies only to the
hierarchical cascade and is deliberately NOT imposed here.

Continuous score for AUROC gates: for flat models the natural end-to-end fake
score is p_fake itself. Both that and the hierarchical-style composite are
recorded (auroc / auroc_alt) so neither choice can hide a result.

python eval_flat3_gates.py --arm V88 --flat3 <...v88.pth> [--gates all|comma,list]
python eval_flat3_gates.py --arm PROD --layer1 <...> --layer2 <...>
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
ROUND_OUT = "backbone_swap_20260907"
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


ARCH = "shufflenet"   # set from --arch in main(); read when models are built


def _build_spatial(arch):
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k", pretrained=False, num_classes=0)
    m.eval()
    with torch.no_grad():
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]
    return m, int(dim)


class DualBranchModel(nn.Module):
    """Spatial branch per ARCH (ShuffleNetV2 = production; MobileNetV4 = backbone_swap)."""
    def __init__(self, num_classes=2):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(ARCH)
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
        L1Cls = DualBranchModelRepViT if l1_backbone == "repvit" else DualBranchModel
        self.l1 = L1Cls(2).to(device)
        self.l1.load_state_dict(torch.load(l1_path, map_location=device)); self.l1.eval()
        if l2_type == "dualhead":
            self.l2 = DualHeadModel().to(device)
        else:
            L2Cls = DualBranchModelRepViT if l2_backbone == "repvit" else DualBranchModel
            self.l2 = L2Cls(2).to(device)
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
                o1 = torch.softmax(self.l1(x), 1)[:, 1]
                o2 = self.l2(x)
                if self.l2_type == "dualhead":
                    s = torch.sigmoid(o2)
                    a, b = s[:, 0], s[:, 1]
                else:
                    s = torch.softmax(o2, 1)
                    a, b = s[:, 0], s[:, 1]
                i = idx.numpy()
                pm[i] = o1.cpu().numpy(); pf[i] = a.cpu().numpy(); pfl[i] = b.cpu().numpy()
                if self.l2b is not None:
                    pfb[i] = torch.softmax(self.l2b(x), 1)[:, 0].cpu().numpy()
                ok[i] = good.numpy().astype(bool)
        return pm, pf, pfl, ok, pfb



class Flat3Scorer:
    """Scoring path for a single flat 3-class DualBranchModel checkpoint.

    Exposes exactly the same .score(paths) contract as Scorer so every gate
    block in this file works unchanged.
    """

    def __init__(self, ckpt_path, device, batch=128, workers=6):
        self.device, self.batch, self.workers = device, batch, workers
        self.m = DualBranchModel(3).to(device)
        self.m.load_state_dict(torch.load(ckpt_path, map_location=device))
        self.m.eval()

    def score(self, paths):
        n = len(paths)
        pm = np.zeros(n); pf = np.zeros(n); pfl = np.zeros(n)
        pfb = np.zeros(n); ok = np.zeros(n, bool)
        dl = DataLoader(PathDataset(paths), batch_size=self.batch, num_workers=self.workers,
                        shuffle=False, pin_memory=True)
        with torch.no_grad():
            for x, idx, good in dl:
                x = x.to(self.device, non_blocking=True)
                s = torch.softmax(self.m(x), 1)          # [real, fake, filter]
                i = idx.numpy()
                pm[i] = (1.0 - s[:, 0]).cpu().numpy()
                pf[i] = s[:, 1].cpu().numpy()
                pfl[i] = s[:, 2].cpu().numpy()
                ok[i] = good.numpy().astype(bool)
        return pm, pf, pfl, ok, pfb


class MLScorer(Flat3Scorer):
    """Multi-label arm: two independent sigmoid heads [is_synthetic, has_filter].
    pm = P(any manipulation) = 1-(1-s)(1-f); pf = s; pfl = f."""

    def __init__(self, ckpt_path, device, batch=128, workers=6):
        self.device, self.batch, self.workers = device, batch, workers
        self.m = DualBranchModel(2).to(device)
        self.m.load_state_dict(torch.load(ckpt_path, map_location=device))
        self.m.eval()

    def score(self, paths):
        n = len(paths)
        pm = np.zeros(n); pf = np.zeros(n); pfl = np.zeros(n)
        pfb = np.zeros(n); ok = np.zeros(n, bool)
        dl = DataLoader(PathDataset(paths), batch_size=self.batch, num_workers=self.workers,
                        shuffle=False, pin_memory=True)
        with torch.no_grad():
            for x, idx, good in dl:
                x = x.to(self.device, non_blocking=True)
                s = torch.sigmoid(self.m(x))              # [is_synthetic, has_filter]
                i = idx.numpy()
                pf[i] = s[:, 0].cpu().numpy()
                pfl[i] = s[:, 1].cpu().numpy()
                pm[i] = 1.0 - (1.0 - pf[i]) * (1.0 - pfl[i])
                ok[i] = good.numpy().astype(bool)
        return pm, pf, pfl, ok, pfb


def decide(pm, pf, pfl, l2_type, thr, pfb=None, tau=None, tf=0.5, tm=0.5):
    if l2_type == "ml":
        # Native rule for the multi-label arm: synthetic head wins (a filtered
        # fake is still fake); filter only when not synthetic; else real.
        out = np.full(len(pm), "real", dtype=object)
        out[(pf <= tf) & (pfl > thr)] = "filter"
        out[pf > tf] = "fake"
        return out
    if l2_type == "flat3":
        # Native rule for flat 3-class models: plain argmax over
        # (p_real, p_fake, p_filter). p_real is recovered as 1 - pm.
        stack = np.stack([1.0 - pm, pf, pfl], axis=1)
        return np.array(["real", "fake", "filter"], dtype=object)[stack.argmax(1)]
    out = np.full(len(pm), "real", dtype=object)
    manip = pm >= tm
    if l2_type == "dualhead":
        is_fake = manip & (pf > tf)
        if pfb is not None and tau is not None:
            is_fake = is_fake | (manip & (pfb > tau))
        out[is_fake] = "fake"
        out[manip & ~is_fake & (pfl > thr)] = "filter"
    else:
        out[manip & (pf >= pfl)] = "fake"
        out[manip & (pf < pfl)] = "filter"
    return out


FLAT3 = False


def composite(pm, pf, tm=0.5):
    if FLAT3:
        # For a flat 3-class model the end-to-end "is this a fake" score is
        # simply p_fake; there is no gate to compose through.
        return pf
    return np.where(pm < tm, pm * 0.5, pm * pf)


def composite_hier(pm, pf, tm=0.5):
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
    ap.add_argument("--layer1")
    ap.add_argument("--layer2")
    ap.add_argument("--flat3", help="flat 3-class checkpoint (mutually exclusive with --layer1/--layer2)")
    ap.add_argument("--arch", default="shufflenet", choices=["shufflenet", "mobilenetv4"])
    ap.add_argument("--ml", help="multi-label two-sigmoid-head checkpoint (arm ML)")
    ap.add_argument("--layer1-backbone", default="shufflenet", choices=["shufflenet", "repvit"])
    ap.add_argument("--layer2-backbone", default="shufflenet", choices=["shufflenet", "repvit"])
    ap.add_argument("--layer2-type", default="twoclass", choices=["twoclass", "dualhead"])
    ap.add_argument("--filter-threshold", type=float, default=None)
    ap.add_argument("--manip-threshold", type=float, default=0.5)
    ap.add_argument("--gates", default="all")
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    global ARCH
    ARCH = a.arch

    global FLAT3
    if a.ml:
        if a.layer1 or a.layer2 or a.flat3:
            print("ERROR: --ml is mutually exclusive with --layer1/--layer2/--flat3"); sys.exit(1)
        FLAT3 = True
        a.flat3 = a.ml
        a.layer2_type = "ml"
    elif a.flat3:
        if a.layer1 or a.layer2:
            print("ERROR: --flat3 is mutually exclusive with --layer1/--layer2"); sys.exit(1)
        FLAT3 = True
        a.layer2_type = "flat3"
    else:
        if not (a.layer1 and a.layer2):
            print("ERROR: need either --flat3 or both --layer1 and --layer2"); sys.exit(1)
    thr = a.filter_threshold if a.filter_threshold is not None else 0.5

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if FLAT3:
        fp = Path(a.flat3)
        if not fp.is_file():
            print(f"ERROR: checkpoint not found: {fp}"); sys.exit(1)
        is_ml = a.layer2_type == "ml"
        sc = (MLScorer if is_ml else Flat3Scorer)(str(fp), device, a.batch, a.workers)
        prov = dict(arm=a.arm,
                    architecture=("multilabel_two_sigmoid_heads" if is_ml else "flat_3class_single_softmax"),
                    decision_rule=("fake if p_synth>0.5 else filter if p_filter>0.5 else real" if is_ml
                                   else "argmax(p_real,p_fake,p_filter)"),
                    flat3=str(fp.resolve()), flat3_sha256=sha256(fp),
                    layer2_type=a.layer2_type, filter_threshold=None, manip_threshold=None,
                    script=str(Path(__file__).resolve()), script_sha256=sha256(Path(__file__)),
                    device=device)
    else:
        l1p, l2p = Path(a.layer1), Path(a.layer2)
        for p in (l1p, l2p):
            if not p.is_file():
                print(f"ERROR: checkpoint not found: {p}"); sys.exit(1)
        sc = Scorer(str(l1p), str(l2p), a.layer2_type, device, a.batch, a.workers,
                    l1_backbone=a.layer1_backbone, l2_backbone=a.layer2_backbone)
        prov = dict(arm=a.arm, architecture="hierarchical_layer1_layer2",
                    decision_rule="p_manip>=tm then argmax(p_fake,p_filter)",
                    layer1=str(l1p.resolve()), layer1_sha256=sha256(l1p),
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
        s_alt = pf if not FLAT3 else composite_hier(pm, pf, 0.5)
        R["aiguard_unseen_auroc"] = dict(
            n=len(lines), auroc=float(roc_auc_score(y, s)),
            auroc_alt_score=float(roc_auc_score(y, s_alt)),
            score_used="p_fake" if FLAT3 else "composite(p_manip,p_fake)",
            score_alt="composite(p_manip,p_fake)" if FLAT3 else "p_fake")
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

    OUTDIR.mkdir(parents=True, exist_ok=True)
    out = OUTDIR / f"gates_{a.arm}.json"
    out.write_text(json.dumps(dict(provenance=prov, gates=R), indent=2), encoding="utf-8")
    (OUTDIR / f"perimage_{a.arm}.json").write_text(json.dumps(dump), encoding="utf-8")
    print(f"\n[out] {out}")


if __name__ == "__main__":
    main()
