"""Binary-vs-ternary frontier evaluation (see PRE_DECLARED.md).

Four paired held-out sets, identical image bytes for every model (ours and the 11 published
baselines already scored in external_baselines_20260905/scores/):

  clean_real     250 True Test LFW real            -> operating point is matched here (FPR = 5 %)
  filtered_real  249 True Test LFW + our filters   -> FA axis  (paired with clean_real)
  clean_fake     287 stress `base` AIGuard/unseen  -> sanity axis
  filtered_fake  2,289 stress filtered             -> MISS axis (paired with clean_fake)

Outputs: perimage_<model>.tsv, frontier.json, frontier.png, tables.md.  ASCII-only prints.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torchvision.models as tv_models
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

BASE = Path(r"C:\My_Project\AIGC")
HERE = Path(__file__).resolve().parent
CKPT = BASE / "checkpoints" / "research" / "backbone_swap_20260907"
EXT = BASE / "results" / "research" / "external_baselines_20260905"
STRESS_MAN = BASE / "results/research/p1_r8_shadow_composite_tradeoff_20260819/stress_cache_manifest.tsv"
SPLITS = BASE / "splits"
NB, SEED, FPR_TARGET = 10000, 20260907, 0.05
RNG = np.random.default_rng(SEED)
ARMS = ["TERN_MNV4"]
BASELINES = []   # the control comes from the necessity round, re-used verbatim

transform_infer = transforms.Compose([transforms.Resize((224, 224)), transforms.ToTensor(),
                                      transforms.Normalize([0.5] * 3, [0.5] * 3)])


def preprocess_jpeg(img, quality=85):
    import io
    buf = io.BytesIO(); img.save(buf, format="JPEG", quality=quality); buf.seek(0)
    return Image.open(buf).convert("RGB")


class PathDataset(Dataset):
    def __init__(self, paths):
        self.paths = list(paths)

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        try:
            im = Image.open(self.paths[i]).convert("RGB")
        except Exception:
            return torch.zeros(3, 224, 224), i, 0
        return transform_infer(preprocess_jpeg(im)), i, 1


class FFTBranch(nn.Module):
    def __init__(self, out_dim=256):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(3, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(4),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.BatchNorm2d(128), nn.ReLU(),
            nn.AdaptiveAvgPool2d(4), nn.Flatten(), nn.Linear(128 * 16, out_dim), nn.ReLU())

    def forward(self, x):
        f = torch.fft.fft2(x, norm="ortho")
        f = torch.fft.fftshift(f, dim=(-2, -1))
        return self.net(torch.log(torch.abs(f) + 1e-8))


def _build_spatial(arch):
    if arch == "shufflenet":
        bb = tv_models.shufflenet_v2_x1_0(weights=None); bb.fc = nn.Identity()
        return bb, 1024
    import timm
    m = timm.create_model("mobilenetv4_conv_small.e2400_r224_in1k",
                          pretrained=False, num_classes=0)
    m.eval()
    with torch.no_grad():                     # num_features is the pre-head width (960);
        dim = m(torch.zeros(2, 3, 224, 224)).shape[1]   # the forward output is 1280
    return m, int(dim)


class DualBranchModel(nn.Module):
    def __init__(self, num_classes=3, arch="shufflenet"):
        super().__init__()
        self.spatial_branch, dim = _build_spatial(arch)
        self.fft_branch = FFTBranch(256)
        self.classifier = nn.Sequential(
            nn.Linear(dim + 256, 512), nn.ReLU(), nn.Dropout(0.3), nn.Linear(512, num_classes))

    def forward(self, x):
        return self.classifier(torch.cat([self.spatial_branch(x), self.fft_branch(x)], 1))


def read_lines(p):
    return [l.strip().split("\t")[0] for l in Path(p).read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("path\t")]


def build_sets():
    rows = [l.split("\t") for l in STRESS_MAN.read_text(encoding="utf-8").splitlines()[1:] if l.strip()]
    base = [(r[2], r[0]) for r in rows if r[1] == "base" and r[2] != "SKIP"]
    filt = [(r[2], r[0]) for r in rows if r[1] != "base" and r[2] != "SKIP"]
    tt_real = read_lines(SPLITS / "truetest_real.txt")
    tt_filt = read_lines(SPLITS / "truetest_filter.txt")
    return {
        "clean_real":    dict(paths=tt_real, cluster=[Path(p).stem for p in tt_real]),
        "filtered_real": dict(paths=tt_filt, cluster=[Path(p).stem for p in tt_filt]),
        "clean_fake":    dict(paths=[p for p, _ in base], cluster=[s for _, s in base]),
        "filtered_fake": dict(paths=[p for p, _ in filt], cluster=[s for _, s in filt]),
    }


def score_arm(arm, all_paths, device="cpu"):
    ck = CKPT / f"tern_TERN_mobilenetv4_seed{SEED}.pth"
    sd = torch.load(ck, map_location="cpu")
    nc = int(sd["classifier.3.bias"].shape[0])
    m = DualBranchModel(nc, "mobilenetv4").to(device); m.load_state_dict(sd); m.eval()
    p_fake = np.full(len(all_paths), np.nan); argmax_lab = np.full(len(all_paths), -1)
    dl = DataLoader(PathDataset(all_paths), batch_size=128, num_workers=6, shuffle=False, pin_memory=True)
    with torch.no_grad():
        for x, idx, ok in dl:
            s = torch.softmax(m(x.to(device)), 1).cpu().numpy()
            i = idx.numpy(); good = ok.numpy() == 1
            p_fake[i] = np.where(good, s[:, 1], np.nan)
            argmax_lab[i] = np.where(good, s.argmax(1), -1)
    del m; torch.cuda.empty_cache()
    return p_fake, argmax_lab, nc, ck


def load_baseline(name, all_paths):
    f = EXT / "scores" / f"{name}.tsv"
    if not f.is_file():
        return None
    d = {}
    h = None
    for l in f.read_text(encoding="utf-8").splitlines():
        x = l.split("\t")
        if h is None:
            h = x; continue
        d[x[0]] = float(x[1])
    miss = sum(1 for p in all_paths if p not in d)
    if miss:
        print(f"  [{name}] {miss} paths missing from its score dump - skipped", flush=True)
        return None
    return np.array([d[p] for p in all_paths])


def curve(scores, sets, idx):
    """Threshold sweep -> arrays of (fpr_clean_real, fa_filtered_real, miss_filtered_fake, rec_clean_fake, thr)."""
    s = {k: scores[idx[k]] for k in sets}
    ths = np.unique(np.concatenate([v for v in s.values()]))
    ths = np.concatenate([[-np.inf], ths, [np.inf]])
    return dict(
        thr=ths,
        fpr_clean_real=np.array([(s["clean_real"] >= t).mean() for t in ths]),
        fa_filtered_real=np.array([(s["filtered_real"] >= t).mean() for t in ths]),
        miss_filtered_fake=np.array([(s["filtered_fake"] < t).mean() for t in ths]),
        rec_clean_fake=np.array([(s["clean_fake"] >= t).mean() for t in ths]),
    )


def matched_point(c):
    """Lowest threshold whose clean-real FPR <= target (most permissive point still at <=5% FPR)."""
    ok = np.where(c["fpr_clean_real"] <= FPR_TARGET)[0]
    j = ok[0]
    return {k: float(v[j]) for k, v in c.items()}


def boot_rate(ind, clusters):
    ind = np.asarray(ind, float); cl = np.asarray(clusters)
    uc = np.unique(cl); idx = {c: np.where(cl == c)[0] for c in uc}
    sums = np.array([ind[idx[c]].sum() for c in uc]); ns = np.array([len(idx[c]) for c in uc])
    d = RNG.integers(0, len(uc), size=(NB, len(uc)))
    r = sums[d].sum(1) / ns[d].sum(1)
    return float(ind.mean() * 100), [float(np.percentile(r, 2.5) * 100), float(np.percentile(r, 97.5) * 100)]


def main():
    sets = build_sets()
    all_paths, idx = [], {}
    for k, v in sets.items():
        idx[k] = np.arange(len(all_paths), len(all_paths) + len(v["paths"]))
        all_paths.extend(v["paths"])
    print({k: len(v["paths"]) for k, v in sets.items()}, "total", len(all_paths), flush=True)

    models = {}
    for arm in ARMS:
        if not (CKPT / f"tern_TERN_mobilenetv4_seed{SEED}.pth").is_file():
            print(f"  [{arm}] checkpoint missing - skipped", flush=True); continue
        pf, am, nc, ck = score_arm(arm, all_paths)
        models[arm] = dict(score=pf, argmax=am, n_classes=nc, ckpt=str(ck), family="ours")
        print(f"  [{arm}] scored, classes={nc}", flush=True)
    for b in BASELINES:
        sc = load_baseline(b, all_paths)
        if sc is not None:
            models[b] = dict(score=sc, argmax=None, n_classes=2, ckpt=str(EXT / "scores" / f"{b}.tsv"), family="published")

    out = dict(sets={k: len(v["paths"]) for k, v in sets.items()}, fpr_target=FPR_TARGET, models={})
    for name, m in models.items():
        c = curve(m["score"], sets, idx)
        mp = matched_point(c)
        rec = dict(family=m["family"], n_classes=m["n_classes"], ckpt=m["ckpt"], matched=mp)
        # CI at the matched threshold
        t = mp["thr"]
        rec["ci"] = dict(
            fa_filtered_real=boot_rate(m["score"][idx["filtered_real"]] >= t, sets["filtered_real"]["cluster"]),
            miss_filtered_fake=boot_rate(m["score"][idx["filtered_fake"]] < t, sets["filtered_fake"]["cluster"]),
            rec_clean_fake=boot_rate(m["score"][idx["clean_fake"]] >= t, sets["clean_fake"]["cluster"]),
        )
        # sub-sampled curve for the figure/JSON
        step = max(1, len(c["thr"]) // 400)
        rec["curve"] = {k: [float(x) for x in v[::step]] for k, v in c.items() if k != "thr"}
        if m["argmax"] is not None and m["n_classes"] == 3:
            am = m["argmax"]
            rec["native_argmax"] = dict(
                fpr_clean_real=float((am[idx["clean_real"]] == 1).mean()),
                fa_filtered_real=float((am[idx["filtered_real"]] == 1).mean()),
                miss_filtered_fake=float((am[idx["filtered_fake"]] != 1).mean()),
                rec_clean_fake=float((am[idx["clean_fake"]] == 1).mean()),
                filtered_real_as_filter=float((am[idx["filtered_real"]] == 2).mean()),
            )
        out["models"][name] = rec
        print(f"{name:10s} @FPR<={FPR_TARGET:.0%}: FA_filt_real={mp['fa_filtered_real'] * 100:6.2f}  "
              f"MISS_filt_fake={mp['miss_filtered_fake'] * 100:6.2f}  clean_fake_rec={mp['rec_clean_fake'] * 100:6.2f}  "
              f"(clean_real_FPR={mp['fpr_clean_real'] * 100:.2f})", flush=True)

    # dominance test (pre-declared verdict rule)
    if "TERN" in out["models"]:
        t = out["models"]["TERN"]["matched"]
        dominators = []
        for name, r in out["models"].items():
            if name == "TERN":
                continue
            cu = r["curve"]
            dom = [(fa, mi) for fa, mi in zip(cu["fa_filtered_real"], cu["miss_filtered_fake"])
                   if fa <= t["fa_filtered_real"] + 1e-12 and mi <= t["miss_filtered_fake"] + 1e-12]
            if dom:
                dominators.append(dict(model=name, points=len(dom), best=min(dom, key=lambda x: x[0] + x[1])))
        out["verdict"] = dict(
            rule="NECESSARY iff no other model has ANY threshold dominating TERN on both axes",
            tern_matched=t, dominators=dominators,
            result="NECESSARY" if not dominators else "NOT_NECESSARY_OR_PARTIAL")
        print("\nVERDICT:", out["verdict"]["result"], "dominators:", [d["model"] for d in dominators], flush=True)

    (HERE / "frontier_s2.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    for name, m in models.items():
        with open(HERE / f"perimage_{name}_s2.tsv", "w", encoding="utf-8") as f:
            f.write("path\tset\tscore\targmax\n")
            for k, v in sets.items():
                for j, p in zip(idx[k], v["paths"]):
                    f.write(f"{p}\t{k}\t{m['score'][j]:.6f}\t{m['argmax'][j] if m['argmax'] is not None else ''}\n")
    print("wrote frontier.json + per-image dumps", flush=True)


if __name__ == "__main__":
    main()
