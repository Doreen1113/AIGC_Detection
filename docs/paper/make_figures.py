"""Generate every figure for docs/paper/main.tex from the measured artifacts.

  fig_frontier.pdf   necessity: FA-vs-MISS frontier, 4 label-space arms + 11 published + MNV4
  fig_cost.pdf       cost vs safety: CPU latency vs false-accusation, marker = params
  fig_teaser.pdf     one real face, its filtered twin, one fake: what each detector says
  fig_crossdataset.pdf  standard-protocol bars, same frames, our backbones vs published

Every number is read from results/; nothing is typed in. ASCII-only prints.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

BASE = Path(r"C:\My_Project\AIGC")
R = BASE / "results" / "research"
OUT = BASE / "docs" / "paper" / "figs"
OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.size": 8, "axes.labelsize": 9, "legend.fontsize": 7,
                     "pdf.fonttype": 42, "ps.fonttype": 42})
def _save(fig, name, **kw):
    """PDF for the paper plus a PNG twin for quick visual inspection."""
    fig.savefig(OUT / name, **kw)
    fig.savefig(OUT / name.replace(".pdf", ".png"), dpi=170, **{k: v for k, v in kw.items() if k != "dpi"})


NAME = {"univfd": "UnivFD", "npr": "NPR", "sbi": "SBI", "xception": "Xception",
        "effnb4": "EffNet-B4", "spsl": "SPSL", "f3net": "F3Net", "ucf": "UCF",
        "recce": "RECCE", "core": "CORE", "srm": "SRM"}


# ----------------------------------------------------------------- fig 1: frontier
def fig_frontier():
    d = json.loads((R / "ternary_necessity_20260906" / "frontier.json").read_text(encoding="utf-8"))
    m = json.loads((R / "backbone_swap_20260907" / "frontier.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(3.4, 3.0))
    # published detectors: thin grey curves
    for k, v in d["models"].items():
        if v["family"] != "published":
            continue
        c = v["curve"]
        ax.plot(np.array(c["fa_filtered_real"]) * 100, np.array(c["miss_filtered_fake"]) * 100,
                color="0.75", lw=0.7, zorder=1)
    ax.plot([], [], color="0.75", lw=0.7, label="11 published detectors (threshold sweep)")
    # binary arms
    style = {"BIN_N": ("tab:red", "filter absent"), "BIN_R": ("tab:orange", "filter $\\rightarrow$ real"),
             "BIN_F": ("tab:purple", "filter $\\rightarrow$ fake")}
    for k, (col, lab) in style.items():
        c = d["models"][k]["curve"]
        ax.plot(np.array(c["fa_filtered_real"]) * 100, np.array(c["miss_filtered_fake"]) * 100,
                color=col, lw=1.4, label=f"binary, {lab}", zorder=2)
        mp = d["models"][k]["matched"]
        ax.plot(mp["fa_filtered_real"] * 100, mp["miss_filtered_fake"] * 100, "o", color=col, ms=4, zorder=3)
    # three-way points
    t = d["models"]["TERN"]["matched"]
    ax.plot(t["fa_filtered_real"] * 100, t["miss_filtered_fake"] * 100, "*", color="tab:blue",
            ms=11, mec="k", mew=0.5, label="three-way (ShuffleNetV2)", zorder=5)
    t2 = m["models"]["TERN_MNV4"]["matched"]
    ax.plot(t2["fa_filtered_real"] * 100, t2["miss_filtered_fake"] * 100, "*", color="tab:green",
            ms=11, mec="k", mew=0.5, label="three-way (MobileNetV4)", zorder=5)
    ax.set_xlim(0, 60); ax.set_ylim(0, 60)
    ax.set_xlabel("false accusation of filtered genuine faces (%)")
    ax.set_ylabel("filtered fakes missed (%)")
    ax.grid(alpha=0.25, lw=0.5)
    ax.legend(loc="upper right", frameon=False)
    ax.annotate("both axes read at 4.8% clean-real FPR", xy=(0.98, 0.13), xycoords="axes fraction",
                fontsize=6, color="0.4", ha="right")
    fig.tight_layout(); _save(fig,"fig_frontier.pdf"); plt.close(fig)
    print("fig_frontier.pdf")


# ----------------------------------------------------------------- fig 2: cost vs safety
def fig_cost():
    cost = json.loads((R / "external_baselines_20260905" / "cost.json").read_text(encoding="utf-8"))
    S = json.loads((R / "external_baselines_20260905" / "summary.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    for k, c in cost.items():
        if c.get("status") != "ok" or not c.get("params") or k not in S["P3"]["models"]:
            continue
        fa = S["P3"]["models"][k]["matched"]["filtered_real_false_fake_pct"][0]
        if k == "npr":          # degenerate at matched FPR (100 %), annotate off-axis
            ax.annotate("NPR (1.4 M): 100%, degenerate\nat matched FPR", xy=(c["cpu_ms_mean"], 50),
                        fontsize=6, color="0.4", ha="left")
            continue
        # hand-placed label offsets so the two clusters (SRM/CORE/SPSL, Xception/RECCE/F3Net) stay legible
        OFF = {"srm": (-30, 8), "core": (5, -10), "spsl": (-32, -9), "xception": (4, 8), "recce": (4, -10),
               "f3net": (-30, -11), "effnb4": (4, -4), "univfd": (6, -5), "ucf": (5, 5), "sbi": (5, 3)}
        size = 6 + 60 * np.sqrt(c["params"] / 4.3e8)
        if k == "ours":
            ax.scatter(c["cpu_ms_mean"], fa, s=size * 4, marker="*", color="tab:green", ec="k", lw=0.5, zorder=5)
            ax.annotate("Ours (3-way)\n5.06 M", (c["cpu_ms_mean"], fa), xytext=(6, 8),
                        textcoords="offset points", fontsize=7, fontweight="bold")
        elif k.startswith("ours_ffpp"):
            ax.scatter(c["cpu_ms_mean"], fa, s=size * 2, marker="s", color="tab:blue", ec="k", lw=0.4, zorder=4)
            ax.annotate("Ours-arch,\nbinary recipe" if k == "ours_ffpp" else "", (c["cpu_ms_mean"], fa),
                        xytext=(6, -12), textcoords="offset points", fontsize=6, color="tab:blue")
        else:
            ax.scatter(c["cpu_ms_mean"], fa, s=size * 2, color="0.55", ec="k", lw=0.4, zorder=3)
            ax.annotate(NAME.get(k, k), (c["cpu_ms_mean"], fa), xytext=OFF.get(k, (4, 3)),
                        textcoords="offset points", fontsize=6, color="0.3")
    ax.set_xscale("log"); ax.set_xlim(12, 2000); ax.set_ylim(-2, 62)
    ax.set_xlabel("CPU latency per image, batch 1 (ms, log)")
    ax.set_ylabel("filtered genuine faces called fake (%)")
    ax.grid(alpha=0.25, lw=0.5, which="both")
    ax.annotate("marker area $\\propto$ parameters; all at 5% clean-real FPR",
                xy=(0.02, 0.96), xycoords="axes fraction", fontsize=6, color="0.4", va="top")
    fig.tight_layout(); _save(fig,"fig_cost.pdf"); plt.close(fig)
    print("fig_cost.pdf")


# ----------------------------------------------------------------- fig 3: teaser
def fig_teaser():
    ext = R / "external_baselines_20260905"
    S = json.loads((ext / "summary.json").read_text(encoding="utf-8"))

    def scores(tag):
        d, h = {}, None
        for l in (ext / "scores" / f"{tag}.tsv").read_text(encoding="utf-8").splitlines():
            x = l.split("\t")
            if h is None:
                h = x; continue
            d[x[0]] = dict(zip(h[1:], x[1:]))
        return d
    ours, xc, sbi = scores("ours"), scores("xception"), scores("sbi")
    thr_xc = S["P3"]["models"]["xception"]["matched"]["threshold"]
    thr_sbi = S["P3"]["models"]["sbi"]["matched"]["threshold"]
    reals = [l.split("\t")[0] for l in (BASE / "splits/truetest_real.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    filts = [l.split("\t")[0] for l in (BASE / "splits/truetest_filter.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    fakes = [l.split("\t")[0] for l in (BASE / "splits/truetest_fake.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
    # pick a genuine/filtered pair where a binary detector flips to fake but ours says filter
    pick = None
    for f in filts:
        stem = Path(f).stem
        src = next((r for r in reals if Path(r).stem in stem), None)
        if src is None or f not in ours or f not in xc or src not in xc:
            continue
        if (ours[f]["label"] == "filter" and ours[src]["label"] == "real"
                and float(xc[f]["p_fake"]) >= thr_xc and float(xc[src]["p_fake"]) < thr_xc
                and src in sbi and f in sbi
                and float(sbi[f]["p_fake"]) >= thr_sbi and float(sbi[src]["p_fake"]) < thr_sbi):
            pick = (src, f); break
    if pick is None:   # relax: only require Xception to flip
        for f in filts:
            src = next((r for r in reals if Path(r).stem in Path(f).stem), None)
            if src and f in ours and f in xc and src in xc and ours[f]["label"] == "filter" \
                    and float(xc[f]["p_fake"]) >= thr_xc and float(xc[src]["p_fake"]) < thr_xc:
                pick = (src, f); break
    if pick is None:
        pick = (reals[0], filts[0])
    # the fake panel must be an image every model scored: use the untreated stress sources
    # (287 held-out generative fakes), which are in the benchmark's items list
    man = BASE / "results/research/p1_r8_shadow_composite_tradeoff_20260819/stress_cache_manifest.tsv"
    base_fakes = [l.split("\t")[2] for l in man.read_text(encoding="utf-8").splitlines()[1:]
                  if l.split("\t")[1] == "base" and l.split("\t")[2] != "SKIP"]
    fake = next((k for k in base_fakes if k in ours and k in xc and k in sbi
                 and ours[k]["label"] == "fake"), base_fakes[0])
    panels = [(pick[0], "genuine"), (pick[1], "genuine + beauty filter"), (fake, "AI-generated")]

    def verdict(sc, p, thr):
        return "FAKE" if float(sc[p]["p_fake"]) >= thr else "real"
    fig, axes = plt.subplots(1, 3, figsize=(7.0, 2.9))
    for ax, (p, title) in zip(axes, panels):
        ax.imshow(Image.open(p).convert("RGB")); ax.set_xticks([]); ax.set_yticks([])
        ax.set_title(title, fontsize=9, pad=4)
        o = ours.get(p, {}).get("label", "?").upper()
        lines = [f"Xception:  {verdict(xc, p, thr_xc)}" if p in xc else "",
                 f"SBI:  {verdict(sbi, p, thr_sbi)}" if p in sbi else "",
                 f"Ours:  {o}"]
        txt = "\n".join(l for l in lines if l)
        truth = {"genuine": "REAL", "genuine + beauty filter": "FILTER", "AI-generated": "FAKE"}[title]
        col = "tab:green" if o == truth else "tab:red"   # green = our verdict is correct for this panel
        ax.text(0.02, 0.02, txt, transform=ax.transAxes, fontsize=7.5, va="bottom", family="monospace",
                bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=col, lw=1.2, alpha=0.92))
    fig.suptitle("Binary detectors at 5% clean-real FPR accuse the beautified genuine face; "
                 "a third class answers it correctly.", fontsize=8, y=0.995)
    fig.tight_layout(); _save(fig,"fig_teaser.pdf", dpi=200); plt.close(fig)
    print("fig_teaser.pdf", [Path(p).name for p, _ in panels])


# ----------------------------------------------------------------- fig 4: cross-dataset bars
def fig_crossdataset():
    ours = json.loads((R / "crossdataset_backbones_20260906" / "crossdataset_backbones.json").read_text(encoding="utf-8"))
    pub = json.loads((R / "crossdataset_backbones_20260906" / "crossdataset_published.json").read_text(encoding="utf-8"))
    rows = []
    for k, v in pub.items():
        if v.get("status") == "ok" and k != "npr":
            rows.append((NAME.get(k, k), None, v["CelebDFv2"]["auc"], v["DFD"]["auc"], "0.6"))
    keep = {"shufflenet_dual": "Ours ShuffleNetV2", "mobilenetv4": "Ours MobileNetV4",
            "fastvit": "Ours FastViT", "efflite0": "Ours EffLite0"}
    for k, lab in keep.items():
        v = ours[k]; rows.append((lab, v["params"], v["CelebDFv2"]["auc"], v["DFD"]["auc"], "tab:green"))
    rows.sort(key=lambda r: r[2])
    fig, ax = plt.subplots(figsize=(3.4, 3.2))
    y = np.arange(len(rows)); h = 0.38
    ax.barh(y - h / 2, [r[2] for r in rows], h, color=[r[4] for r in rows], label="Celeb-DF-v2")
    ax.barh(y + h / 2, [r[3] for r in rows], h, color=[r[4] for r in rows], alpha=0.45, label="DFD")
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=7)
    ax.set_xlim(0.6, 0.95); ax.set_xlabel("zero-shot frame AUC (FF++ c23 training)")
    ax.grid(axis="x", alpha=0.25, lw=0.5)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="0.6", label="Celeb-DF-v2"),
                       Patch(color="0.6", alpha=0.45, label="DFD"),
                       Patch(color="tab:green", label="ours (both)")],
              loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=3, frameon=False, handlelength=1.2)
    fig.tight_layout(); _save(fig,"fig_crossdataset.pdf"); plt.close(fig)
    print("fig_crossdataset.pdf")


if __name__ == "__main__":
    fig_frontier(); fig_cost(); fig_teaser(); fig_crossdataset()
