"""
P1-R1.5 -- Stage 5: generate the 5 diagnostic figures. New, read-only script.

python p1_r1_5_generate_figures.py
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

metrics = pd.read_csv(OUT_DIR / "source_by_filter_by_resolution_metrics.csv")
scores = pd.read_csv(OUT_DIR / "per_image_scores_by_resolution.csv")

SOURCES = sorted(scores["source"].unique())
FTYPES = ["whitening_medium", "eye_enlarging", "smoothing_medium", "face_reshaping"]
RESOLUTIONS = ["native", "canonical_256", "canonical_512", "canonical_1024"]
MODEL = "v816@0.95_calibrated"

CONFOUND_NOTE = {
    "whitening_medium": "VALID control",
    "eye_enlarging": "VALID_WITH_CAVEAT control",
    "smoothing_medium": "INVALID (confounded -- fixed-px kernel)",
    "face_reshaping": "INVALID (confounded -- fixed-px radius)",
}


# ---- Fig 1: source x resolution x filter-type heatmap (2x2 grid, one per filter type) ----
def fig1():
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    sub_all = metrics[metrics["model"] == MODEL]
    for ax, ftype in zip(axes.flat, FTYPES):
        sub = sub_all[sub_all["filter_type"] == ftype]
        mat = sub.pivot(index="source", columns="resolution_condition", values="filter_head_auroc")
        mat = mat.reindex(index=SOURCES, columns=RESOLUTIONS)
        im = ax.imshow(mat.values, cmap="RdYlGn", vmin=0.3, vmax=1.0, aspect="auto")
        ax.set_xticks(range(len(RESOLUTIONS))); ax.set_xticklabels(RESOLUTIONS, rotation=20, ha="right")
        ax.set_yticks(range(len(SOURCES))); ax.set_yticklabels(SOURCES, fontsize=8)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat.values[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8)
        ax.set_title(f"{ftype}\n({CONFOUND_NOTE[ftype]})", fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Figure 1: Source x Resolution x Filter-Type AUROC heatmap (v8.16 @0.95 calibrated)\nDF40-cdf replication set base images, resolution-controlled")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_source_x_resolution_x_filtertype_heatmap.png", dpi=140)
    plt.close(fig)
    print("wrote fig1")


# ---- Fig 2: pixart / sd2.1 before-after resolution comparison ----
def fig2():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, source in zip(axes, ["DF40-cdf-pixart", "DF40-cdf-sd2.1"]):
        sub = metrics[(metrics["model"] == MODEL) & (metrics["source"] == source)]
        x = np.arange(len(FTYPES))
        width = 0.2
        for i, res in enumerate(RESOLUTIONS):
            vals = [sub[(sub["filter_type"] == t) & (sub["resolution_condition"] == res)]["filter_head_auroc"].mean() for t in FTYPES]
            ax.bar(x + (i - 1.5) * width, vals, width, label=res)
        ax.axhline(0.5, color="gray", linestyle=":", linewidth=1, label="chance (0.5)")
        ax.set_xticks(x); ax.set_xticklabels(FTYPES, rotation=25, ha="right", fontsize=8)
        ax.set_ylabel("filter_head AUROC")
        ax.set_ylim(0, 1.05)
        ax.set_title(source)
        ax.legend(fontsize=7)
    fig.suptitle("Figure 2: pixart / sd2.1 -- before (native) vs after resolution canonicalization\n(v8.16 @0.95 calibrated)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_pixart_sd21_before_after.png", dpi=140)
    plt.close(fig)
    print("wrote fig2")


# ---- Fig 3: DiT/SiT/ddim reference comparison (native=256, what happens when upsampled) ----
def fig3():
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharey=True)
    for ax, source in zip(axes, ["DF40-cdf-DiT", "DF40-cdf-SiT", "DF40-cdf-ddim"]):
        sub = metrics[(metrics["model"] == MODEL) & (metrics["source"] == source)]
        x = np.arange(len(FTYPES))
        width = 0.2
        for i, res in enumerate(RESOLUTIONS):
            vals = [sub[(sub["filter_type"] == t) & (sub["resolution_condition"] == res)]["filter_head_auroc"].mean() for t in FTYPES]
            ax.bar(x + (i - 1.5) * width, vals, width, label=res)
        ax.axhline(0.5, color="gray", linestyle=":", linewidth=1)
        ax.set_xticks(x); ax.set_xticklabels(FTYPES, rotation=25, ha="right", fontsize=8)
        ax.set_title(f"{source} (native=256px)")
        ax.set_ylim(0, 1.05)
    axes[0].set_ylabel("filter_head AUROC")
    axes[-1].legend(fontsize=7, loc="upper right")
    fig.suptitle("Figure 3: 256px-native reference sources -- what happens when upsampled?\n(v8.16 @0.95 calibrated)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_dit_sit_ddim_reference.png", dpi=140)
    plt.close(fig)
    print("wrote fig3")


# ---- Fig 4: probability distribution plot ----
def fig4():
    fig, axes = plt.subplots(1, 4, figsize=(18, 4.5), sharey=True)
    for ax, res in zip(axes, RESOLUTIONS):
        clean = scores[(scores["resolution_condition"] == res) & (scores["filter_type"] == "clean")]["v816_p_filter"]
        comp_good = scores[(scores["resolution_condition"] == res) & (scores["filter_type"] == "smoothing_medium") &
                            (scores["source"].isin(["DF40-cdf-DiT", "DF40-cdf-SiT", "DF40-cdf-ddim"]))]["v816_p_filter"]
        comp_bad = scores[(scores["resolution_condition"] == res) & (scores["filter_type"] == "smoothing_medium") &
                           (scores["source"].isin(["DF40-cdf-pixart", "DF40-cdf-sd2.1"]))]["v816_p_filter"]
        bins = np.linspace(0, 1, 26)
        ax.hist(clean, bins=bins, alpha=0.5, label=f"clean (n={len(clean)})", color="gray", density=True)
        ax.hist(comp_good, bins=bins, alpha=0.5, label=f"smoothing, 256px-native src (n={len(comp_good)})", color="#55A868", density=True)
        ax.hist(comp_bad, bins=bins, alpha=0.5, label=f"smoothing, pixart/sd2.1 (n={len(comp_bad)})", color="#C44E52", density=True)
        ax.axvline(0.95, color="red", linestyle="--", linewidth=1)
        ax.set_title(res, fontsize=10)
        ax.set_xlabel("v816 filter_head probability")
        ax.legend(fontsize=6)
    axes[0].set_ylabel("density")
    fig.suptitle("Figure 4: filter_head probability distributions by resolution condition\n(smoothing_medium: 256px-native sources vs pixart/sd2.1, v8.16)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_probability_distributions.png", dpi=140)
    plt.close(fig)
    print("wrote fig4")


# ---- Fig 5: effect-size plot with CI (AUROC vs resolution, per source, smoothing) ----
def fig5():
    fig, ax = plt.subplots(figsize=(9, 6))
    sub = metrics[(metrics["model"] == MODEL) & (metrics["filter_type"] == "smoothing_medium")]
    x_pos = {r: i for i, r in enumerate(RESOLUTIONS)}
    for source in SOURCES:
        s = sub[sub["source"] == source].set_index("resolution_condition").reindex(RESOLUTIONS)
        y = s["filter_head_auroc"].values
        ci_lo, ci_hi = [], []
        for ci_str in s["filter_head_auroc_95ci"].values:
            if isinstance(ci_str, str) and ci_str.startswith("["):
                lo, hi = ci_str.strip("[]").split(",")
                ci_lo.append(float(lo)); ci_hi.append(float(hi))
            else:
                ci_lo.append(np.nan); ci_hi.append(np.nan)
        yerr = [np.array(y) - np.array(ci_lo), np.array(ci_hi) - np.array(y)]
        xs = [x_pos[r] for r in RESOLUTIONS]
        ax.errorbar(xs, y, yerr=yerr, marker="o", capsize=4, label=source)
    ax.axhline(0.5, color="gray", linestyle=":", label="chance")
    ax.set_xticks(range(len(RESOLUTIONS))); ax.set_xticklabels(RESOLUTIONS)
    ax.set_ylabel("filter_head AUROC (95% bootstrap CI)")
    ax.set_title("Figure 5: smoothing_medium AUROC vs resolution, with 95% CI, per source\n(v8.16 @0.95 calibrated -- OBSERVATIONAL, confounded control, see control_validation.csv)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_effect_size_with_ci.png", dpi=140)
    plt.close(fig)
    print("wrote fig5")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
    print("All figures written to", FIG_DIR)
