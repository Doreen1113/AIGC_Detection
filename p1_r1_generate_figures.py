"""
P1-R1 -- generate the 6 diagnostic figures from the CSVs already produced in
this research round (per_image_scores.csv, source_by_filter_metrics.csv,
routing_failure_breakdown.csv, per_image_paired_effect_raw.csv). New,
read-only script; writes only PNGs into the figures/ subfolder.

python p1_r1_generate_figures.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_cross_source_failure_anatomy_20260814"
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

CELLC_THRESHOLD = 0.85
V816_THRESHOLD_CAL = 0.95

scores = pd.read_csv(OUT_DIR / "per_image_scores.csv")
metrics = pd.read_csv(OUT_DIR / "source_by_filter_metrics.csv")
failures = pd.read_csv(OUT_DIR / "routing_failure_breakdown.csv")
paired = pd.read_csv(OUT_DIR / "per_image_paired_effect_raw.csv")

SOURCES = sorted(scores["source"].unique())
FTYPES = sorted(t for t in scores["ftype"].unique() if t != "none")


# ---- Figure 1: source x filter-type heatmap (joint recognition), CellC vs v816 ----
def fig1():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for ax, model_name, title in [
        (axes[0], "CellC@0.85", "v8.15 Cell C @0.85\njoint recognition rate"),
        (axes[1], "v816@0.95_calibrated", "v8.16 mixed-lineage @0.95 (calibrated)\njoint recognition rate"),
    ]:
        sub = metrics[metrics["model"] == model_name]
        mat = sub.pivot(index="source", columns="filter_type", values="joint_recognition_rate")
        mat = mat.reindex(index=SOURCES, columns=FTYPES)
        im = ax.imshow(mat.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(range(len(FTYPES))); ax.set_xticklabels(FTYPES, rotation=30, ha="right")
        ax.set_yticks(range(len(SOURCES))); ax.set_yticklabels(SOURCES)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat.values[i, j]
                if not np.isnan(v):
                    ax.text(j, i, f"{v*100:.0f}%", ha="center", va="center",
                            color="black", fontsize=9)
        ax.set_title(title)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Figure 1: Source x Filter-Type Joint Recognition Heatmap (DF40-cdf replication set)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig1_source_x_filtertype_heatmap.png", dpi=140)
    plt.close(fig)
    print("wrote fig1")


# ---- Figure 2: v8.15 vs v8.16 calibrated comparison, by filter type ----
def fig2():
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(FTYPES))
    width = 0.35
    for model_name, offset, color, label in [
        ("CellC@0.85", -width/2, "#4C72B0", "v8.15 Cell C @0.85"),
        ("v816@0.95_calibrated", width/2, "#DD8452", "v8.16 mixed-lineage @0.95 (calibrated)"),
    ]:
        sub = metrics[metrics["model"] == model_name]
        vals = [sub[sub["filter_type"] == t]["joint_recognition_rate"].mean() * 100 for t in FTYPES]
        ax.bar(x + offset, vals, width, label=label, color=color)
    ax.set_xticks(x); ax.set_xticklabels(FTYPES, rotation=20, ha="right")
    ax.set_ylabel("Joint recognition rate (%), averaged across 5 DF40-cdf sources")
    ax.set_title("Figure 2: v8.15 Cell C vs v8.16 (calibrated) -- per filter type,\nDF40-cdf replication set")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig2_cellc_vs_v816_by_filtertype.png", dpi=140)
    plt.close(fig)
    print("wrote fig2")


# ---- Figure 3: filter-probability distributions (clean vs composite), per model ----
def fig3():
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, col, thresh, title in [
        (axes[0], "cellc_p_filter", CELLC_THRESHOLD, "v8.15 Cell C"),
        (axes[1], "v816_p_filter", V816_THRESHOLD_CAL, "v8.16 mixed-lineage"),
    ]:
        clean = scores[scores["ftype"] == "none"][col]
        comp = scores[scores["ftype"] != "none"][col]
        bins = np.linspace(0, 1, 41)
        ax.hist(clean, bins=bins, alpha=0.6, label=f"clean fake (n={len(clean)})", color="#4C72B0", density=True)
        ax.hist(comp, bins=bins, alpha=0.6, label=f"fake+filter composite (n={len(comp)})", color="#DD8452", density=True)
        ax.axvline(thresh, color="red", linestyle="--", label=f"calibrated threshold={thresh}")
        ax.set_xlabel("filter_head sigmoid probability")
        ax.set_title(title)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("density")
    fig.suptitle("Figure 3: filter_head probability distributions, clean-fake vs fake+filter composite\n(DF40-cdf replication set, all sources/types pooled)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig3_filter_probability_distributions.png", dpi=140)
    plt.close(fig)
    print("wrote fig3")


# ---- Figure 4: reliability / calibration plot ----
def fig4():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, col, title in [
        (axes[0], "cellc_p_filter", "v8.15 Cell C"),
        (axes[1], "v816_p_filter", "v8.16 mixed-lineage"),
    ]:
        comp = scores[scores["ftype"] != "none"].copy()
        comp["bin"] = pd.cut(comp[col], bins=np.linspace(0, 1, 11), include_lowest=True)
        rel = comp.groupby("bin", observed=True).agg(
            mean_pred=(col, "mean"), n=(col, "size"))
        # "observed accuracy" here = fraction of that bin that IS a true composite
        # (all rows in `comp` are true composites by construction, so instead we
        # report bin occupancy vs the ideal diagonal using clean-fake as the
        # counter-distribution to show separation, i.e. a coverage-style reliability
        # curve: fraction of composites whose score falls at/above each decile)
        rel = rel.dropna()
        ax.bar(range(len(rel)), rel["n"], color="#55A868")
        ax.set_xticks(range(len(rel)))
        ax.set_xticklabels([f"{iv.left:.1f}-{iv.right:.1f}" for iv in rel.index], rotation=45, ha="right", fontsize=8)
        ax.set_xlabel("filter_head probability bin")
        ax.set_ylabel("count of fake+filter composites in bin")
        ax.set_title(f"{title}\n(bin population -- ideal = mass at right side, near 1.0)")
    fig.suptitle("Figure 4: Reliability view -- where do TRUE fake+filter composites' filter-probabilities land?\n(a well-calibrated, well-discriminating model would concentrate mass near 1.0)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig4_reliability_calibration.png", dpi=140)
    plt.close(fig)
    print("wrote fig4")


# ---- Figure 5: routing failure stacked bar chart ----
def fig5():
    fig, ax = plt.subplots(figsize=(9, 5))
    models = ["CellC@0.85", "v816@0.85_uncalibrated_reference", "v816@0.95_calibrated"]
    modes = ["layer1_real", "fake_head_miss", "filter_head_miss", "threshold_calibration_miss", "other_unclassifiable"]
    colors = ["#8172B2", "#C44E52", "#4C72B0", "#DD8452", "#999999"]
    bottoms = np.zeros(len(models))
    x = np.arange(len(models))
    for mode, color in zip(modes, colors):
        vals = []
        for m in models:
            sub = failures[(failures["model"] == m) & (failures["failure_mode"] == mode)]
            total_fail = failures[failures["model"] == m].groupby("model")["count"].sum().get(m, 0)
            cnt = sub["count"].sum()
            vals.append(cnt / total_fail * 100 if total_fail > 0 else 0)
        ax.bar(x, vals, bottom=bottoms, label=mode, color=color)
        bottoms += np.array(vals)
    ax.set_xticks(x); ax.set_xticklabels(["Cell C\n@0.85", "v816\n@0.85 (uncal.)", "v816\n@0.95 (cal.)"])
    ax.set_ylabel("% of all joint-recognition failures")
    ax.set_title("Figure 5: Routing/failure-mode breakdown of joint-recognition failures\n(DF40-cdf replication set composites)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig5_routing_failure_stacked_bar.png", dpi=140)
    plt.close(fig)
    print("wrote fig5")


# ---- Figure 6: paired-effect distribution plot ----
def fig6():
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    order = FTYPES
    data = [paired[paired["ftype"] == t]["lab_deltaE_mean"].values for t in order]
    axes[0].boxplot(data, tick_labels=order, showfliers=False)
    axes[0].set_ylabel("mean LAB delta-E (per image)")
    axes[0].set_title("LAB delta-E by filter type\n(clean vs filtered, all sources pooled)")
    axes[0].tick_params(axis="x", rotation=20)
    axes[0].set_yscale("log")

    data2 = [paired[paired["ftype"] == t]["changed_pixel_proportion"].values for t in order]
    axes[1].boxplot(data2, tick_labels=order, showfliers=False)
    axes[1].set_ylabel("changed-pixel proportion (delta-E > 2.3 JND)")
    axes[1].set_title("Changed-pixel proportion by filter type")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle("Figure 6: Paired before/after physical effect size by filter type\n(994-image DF40-cdf replication set, 792 valid pairs)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / "fig6_paired_effect_distributions.png", dpi=140)
    plt.close(fig)
    print("wrote fig6")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6()
    print("All figures written to", FIG_DIR)
