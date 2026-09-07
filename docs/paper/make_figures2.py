"""Second figure set: pipeline diagram (PNG, no LaTeX needed), qualitative comparison grid with
faces (one row per filter operation), and a ranked false-accusation bar chart.
Consistent palette and typography. Every number/verdict is read from results/. ASCII-only prints.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from PIL import Image

BASE = Path(r"C:\My_Project\AIGC")
R = BASE / "results" / "research"
EXT = R / "external_baselines_20260905"
OUT = BASE / "docs" / "paper" / "figs"
OUT.mkdir(parents=True, exist_ok=True)

OURS, PUB, ACC = "#1b9e77", "#8a8a8a", "#d95f02"          # teal / grey / orange
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 9, "axes.labelsize": 9.5, "axes.titlesize": 10, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False,
    "pdf.fonttype": 42, "ps.fonttype": 42})
NAME = {"univfd": "UnivFD", "npr": "NPR", "sbi": "SBI", "xception": "Xception", "effnb4": "EffNet-B4",
        "spsl": "SPSL", "f3net": "F3Net", "ucf": "UCF", "recce": "RECCE", "core": "CORE", "srm": "SRM",
        "ours": "Ours (3-way)", "ours_ffpp": "Ours-arch, binary", "ours_ffpp_repvit": "Ours-arch RepViT, binary"}
FILTER_TYPES = ["smoothing", "whitening", "eye_enlarging", "face_reshaping"]
FILTER_LABEL = {"smoothing": "+ skin smoothing", "whitening": "+ whitening",
                "eye_enlarging": "+ eye enlarging", "face_reshaping": "+ face reshaping"}


def save(fig, name):
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig); print(name)


def scores(tag):
    d, h = {}, None
    for l in (EXT / "scores" / f"{tag}.tsv").read_text(encoding="utf-8").splitlines():
        x = l.split("\t")
        if h is None:
            h = x; continue
        d[x[0]] = dict(zip(h[1:], x[1:]))
    return d


def read_split(name):
    return [l.split("\t")[0] for l in (BASE / "splits" / name).read_text(encoding="utf-8").splitlines() if l.strip()]


# ------------------------------------------------------------------ pipeline
def fig_pipeline():
    fig, ax = plt.subplots(figsize=(8.4, 3.2))
    ax.set_xlim(0, 100); ax.set_ylim(0, 40); ax.axis("off")

    def box(x, y, w, h, text, fc="#ffffff", ec="#444444", fs=8, lw=1.0):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.2", fc=fc, ec=ec, lw=lw))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, linespacing=1.25)

    def arrow(x0, y0, x1, y1, ls="-", col="#333333"):
        ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle="-|>", mutation_scale=10,
                                     lw=1.0, color=col, linestyle=ls, shrinkA=0, shrinkB=0))

    im = Image.open(read_split("truetest_real.txt")[2]).convert("RGB").resize((160, 160))
    ax.imshow(np.asarray(im), extent=(1, 9, 15, 25), zorder=3)
    ax.text(5, 26.2, "face image\n224$\\times$224", ha="center", va="bottom", fontsize=7.5)

    box(14, 25, 17, 8, "spatial branch\nMobileNetV4 / ShuffleNetV2\n$\\mathbf{f}_{\\mathrm{spatial}}$", fc="#e3ecf7")
    box(14, 7, 17, 8, "spectral branch\n$\\log|\\mathrm{DFT}(X)|\\rightarrow$ CNN$_3$\n$\\mathbf{f}_{\\mathrm{freq}}$", fc="#fdebd3")
    arrow(9.2, 21.5, 14, 29); arrow(9.2, 18.5, 14, 11)
    box(35, 16, 9, 8, "concat\n1280-d")
    arrow(31, 29, 35, 21); arrow(31, 11, 35, 19)

    box(48, 16, 13, 8, "Layer 1\nreal vs. manipulated\n$\\tau = 0.5$", fc="#e2f3ea")
    arrow(44, 20, 48, 20)
    box(65, 27, 12, 8, "Layer 2\nfake vs. filter", fc="#e2f3ea")
    box(81, 27, 12, 8, "artifact head\n4 operations", fc="#e2f3ea")
    arrow(61, 22, 65, 31); ax.text(59.5, 27.0, "$p_{\\mathrm{manip}}\\geq\\tau$", fontsize=6.5, rotation=42, ha="right")
    arrow(77, 31, 81, 31); ax.text(78.4, 32.3, "filter", fontsize=6.5)

    box(64, 4, 14.5, 8, "patch evidence head\n7$\\times$7, centre-prior\nsubtracted", fc="#efe3f5", fs=7.3)
    arrow(61, 18, 64, 9)

    box(81, 12, 17, 10, "structured record\nclass $\\cdot$ type $\\cdot$ region\nraw score $\\cdot$ sentence", ec="#222222", lw=1.3)
    arrow(93, 27, 93, 22); arrow(77, 8, 81, 15)
    arrow(61, 20, 81, 17, ls="--", col="#777777"); ax.text(70, 15.2, "real", fontsize=6.5, color="#555555")
    box(81, 0.5, 17, 7, "ONNX / TFLite export\nDFT as constant matmul\n$\\approx$26 MB fp32, browser & Android", fc="#f0f0f0", fs=7)
    arrow(89.5, 12, 89.5, 7.5, ls="--", col="#777777")

    for x, y, t in ((22.5, 35.2, "shared dual-branch backbone"), (60, 37.5, "hierarchical decision"), (71, 1.2, "explanation")):
        ax.text(x, y, t, ha="center", fontsize=7.5, color="#666666", style="italic")
    fig.tight_layout(pad=0.2)
    save(fig, "fig_pipeline")


# ------------------------------------------------------------------ qualitative grid
def fig_qualgrid():
    """One row per filter operation: genuine face | same face + that filter | an AI-generated face.
    True Test applies exactly one operation per person, so rows are different people."""
    S = json.loads((EXT / "summary.json").read_text(encoding="utf-8"))
    ours, xc, sbi, ucf = scores("ours"), scores("xception"), scores("sbi"), scores("ucf")
    thr = {m: S["P3"]["models"][m]["matched"]["threshold"] for m in ("xception", "sbi", "ucf")}
    reals = {Path(p).stem: p for p in read_split("truetest_real.txt")}
    man = BASE / "results/research/p1_r8_shadow_composite_tradeoff_20260819/stress_cache_manifest.tsv"
    fakes = [l.split("\t")[2] for l in man.read_text(encoding="utf-8").splitlines()[1:]
             if l.split("\t")[1] == "base" and l.split("\t")[2] != "SKIP"]

    def verdict(sc, p, m):
        return "fake" if float(sc[p]["p_fake"]) >= thr[m] else "real"

    def ok(p):
        return p in ours and p in xc and p in sbi and p in ucf

    rows = []
    for ft in FILTER_TYPES:
        cands = [(reals[Path(f).stem[len(ft) + 1:]], f) for f in read_split("truetest_filter.txt")
                 if Path(f).stem.startswith(ft + "_") and Path(f).stem[len(ft) + 1:] in reals]
        cands = [(s, f) for s, f in cands if ok(s) and ok(f) and ours[s]["label"] == "real" and ours[f]["label"] == "filter"]
        strict = [(s, f) for s, f in cands if verdict(xc, s, "xception") == "real" and verdict(xc, f, "xception") == "fake"]
        pick = (strict or cands)[0] if (strict or cands) else None
        if pick:
            rows.append((ft, *pick))
    fake_pick = [k for k in fakes if ok(k) and ours[k]["label"] == "fake"][:len(rows)]
    n = len(rows)
    assert n > 0, "no qualifying rows"

    fig, axes = plt.subplots(n, 3, figsize=(6.4, 2.35 * n), squeeze=False)
    for r, (ft, src, filt) in enumerate(rows):
        for c, (p, title, truth) in enumerate(((src, "genuine", "REAL"), (filt, FILTER_LABEL[ft], "FILTER"),
                                               (fake_pick[r], "AI-generated", "FAKE"))):
            ax = axes[r, c]
            ax.imshow(Image.open(p).convert("RGB")); ax.set_xticks([]); ax.set_yticks([])
            for s in ax.spines.values():
                s.set_visible(False)
            ax.set_title(title, fontsize=9, pad=3)
            o = ours[p]["label"].upper()
            lines = [f"Xception  {verdict(xc, p, 'xception')}", f"SBI       {verdict(sbi, p, 'sbi')}",
                     f"UCF       {verdict(ucf, p, 'ucf')}", f"Ours      {o}"]
            col = OURS if o == truth else ACC
            ax.text(0.03, 0.03, "\n".join(lines), transform=ax.transAxes, fontsize=6.4, va="bottom",
                    family="monospace", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=col, lw=1.4, alpha=0.93))
    fig.suptitle("All models read at 5% FPR on clean genuine faces. Binary detectors accuse the beautified\n"
                 "genuine face (middle column); the three-way detector labels it filter.", fontsize=8.5, y=0.995)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    save(fig, "fig_qualgrid")
    print("  rows:", [(ft, Path(s).stem) for ft, s, _ in rows])


# ------------------------------------------------------------------ FA bar chart
def fig_fa_bar():
    S = json.loads((EXT / "summary.json").read_text(encoding="utf-8"))
    rows = []
    for m, v in S["P3"]["models"].items():
        if m.startswith("cand_") or m == "ours_ffpp_repvit":
            continue
        pt, ci = v["matched"]["filtered_real_false_fake_pct"]
        rows.append((NAME.get(m, m), pt, ci, m))
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(3.5, 3.4))
    for i, (lab, pt, ci, m) in enumerate(rows):
        col = OURS if m == "ours" else ("#4a6fa5" if m == "ours_ffpp" else PUB)
        ax.barh(i, min(pt, 45), color=col, height=0.66)
        if pt <= 45:
            ax.errorbar(pt, i, xerr=[[max(0, pt - ci[0])], [max(0, min(ci[1], 45) - pt)]],
                        fmt="none", ecolor="#333333", elinewidth=0.8, capsize=2)
            ax.text((min(ci[1], 45) + 1.0) if pt > 0 else 1.0, i, f"{pt:.1f}%", va="center", fontsize=7)
        else:
            ax.text(45.5, i, "100% (degenerate)", va="center", fontsize=6.5, color="#555555")
    ax.set_yticks(range(len(rows))); ax.set_yticklabels([r[0] for r in rows], fontsize=7.5)
    ax.set_xlim(0, 60); ax.set_ylim(-1.7, len(rows) - 0.4)
    ax.set_xlabel("beautified genuine faces called fake (%)")
    ax.axvline(5, color="#999999", lw=0.8, ls=":")
    ax.text(5.8, -1.0, "5% FPR on clean faces (operating point)", fontsize=6.5, color="#666666", va="center")
    ax.grid(axis="x", alpha=0.25, lw=0.5)
    fig.tight_layout()
    save(fig, "fig_fa_bar")


if __name__ == "__main__":
    fig_pipeline(); fig_qualgrid(); fig_fa_bar()
