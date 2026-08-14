"""
Phase 2F -- Fake Evidence Discovery: diagnostic figures.
python make_figures.py
"""
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "phase2" / "fake_evidence_discovery_v811d_20260814"
FIG_DIR = OUT_DIR / "figures"

df = pd.read_csv(OUT_DIR / "raw_features.csv")
metrics = pd.read_csv(OUT_DIR / "evidence_metrics_sourcewise.csv")

FAKE_SOURCES = ["aiguard_unseen", "stylegan2_ood", "df40_dit", "df40_sit",
                "df40_ddim", "df40_pixart", "df40_sd21", "midjourney"]
ALL_SOURCES_ORDER = ["celeba_test", "lfw", "aiguard_unseen_real"] + FAKE_SOURCES

# ── 1. distribution plots (one representative feature per family) ──
REP_FEATURES = {
    "frequency": "freq_spectral_entropy",
    "texture": "tex_local_variance_std",
    "landmark_geometry": "lm_symmetry_score",
    "boundary": "bnd_ring_mean_diff",
}

for fam, feat in REP_FEATURES.items():
    fig, ax = plt.subplots(figsize=(12, 5))
    data, labels, colors = [], [], []
    for src in ALL_SOURCES_ORDER:
        vals = df[(df.source == src)][feat].dropna().values
        if len(vals) == 0:
            continue
        data.append(vals)
        labels.append(src)
        colors.append("#3b7dd8" if src in ("celeba_test", "lfw", "aiguard_unseen_real") else "#d85c3b")
    parts = ax.violinplot(data, showmedians=True)
    for i, pc in enumerate(parts["bodies"]):
        pc.set_facecolor(colors[i])
        pc.set_alpha(0.6)
    ax.set_xticks(range(1, len(labels) + 1))
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel(feat)
    ax.set_title(f"{fam}: {feat} by source (blue=real, red=fake)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"dist_{fam}_{feat}.png", dpi=130)
    plt.close(fig)

# ── 2. source x candidate AUROC heatmap ──
feat_order = metrics["evidence_feature"].drop_duplicates().tolist()
mat = metrics.pivot(index="evidence_feature", columns="fake_source", values="auroc")
mat = mat.reindex(index=feat_order, columns=FAKE_SOURCES)
fig, ax = plt.subplots(figsize=(10, 9))
im = ax.imshow(mat.values, cmap="RdBu_r", vmin=0.2, vmax=0.8, aspect="auto")
ax.set_xticks(range(len(FAKE_SOURCES))); ax.set_xticklabels(FAKE_SOURCES, rotation=45, ha="right")
ax.set_yticks(range(len(feat_order))); ax.set_yticklabels(feat_order, fontsize=8)
for i in range(mat.shape[0]):
    for j in range(mat.shape[1]):
        v = mat.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=6,
                     color="white" if abs(v - 0.5) > 0.2 else "black")
fig.colorbar(im, label="AUROC (real=0, fake=1)")
ax.set_title("Evidence feature x fake source: AUROC (0.5=chance)")
fig.tight_layout()
fig.savefig(FIG_DIR / "heatmap_auroc.png", dpi=130)
plt.close(fig)

# ── 3. effect-size forest plots, one per family ──
FAMILIES = ["frequency", "texture", "landmark_geometry", "boundary"]
for fam in FAMILIES:
    sub = metrics[metrics.family == fam].copy()
    sub = sub.dropna(subset=["effect_size"])
    if sub.empty:
        continue
    feats = sub["evidence_feature"].unique().tolist()
    fig, ax = plt.subplots(figsize=(9, max(4, 0.5 * len(feats) * len(FAKE_SOURCES))))
    y = 0
    yticks, ylabels = [], []
    for feat in feats:
        fsub = sub[sub.evidence_feature == feat]
        for _, r in fsub.iterrows():
            # rough CI proxy for effect size using n's (not bootstrap -- AUROC CI already bootstrapped;
            # effect size shown as point estimate, sized by n)
            ax.errorbar(r["effect_size"], y, xerr=0, fmt="o",
                        color="#d85c3b" if r["effect_size"] > 0 else "#3b7dd8",
                        markersize=4 + 0.05 * min(r["n_fake"], 100))
            yticks.append(y); ylabels.append(f"{feat} | {r['fake_source']}")
            y += 1
        y += 0.5
    ax.axvline(0, color="gray", lw=0.8)
    ax.set_yticks(yticks); ax.set_yticklabels(ylabels, fontsize=6)
    ax.invert_yaxis()
    ax.set_xlabel("Cohen's d (positive = higher-in-fake)")
    ax.set_title(f"{fam}: effect size by feature x fake source")
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"forest_{fam}.png", dpi=130)
    plt.close(fig)

# ── 4. resolution-confound scatter for CONDITIONAL/REJECT-by-confound features ──
decision = pd.read_csv(OUT_DIR / "evidence_candidate_decision_table.csv")
flag_feats = decision[decision.decision.isin(["CONDITIONAL"])]["evidence_feature"].tolist()
flag_feats += ["tex_local_variance_std"]  # ACCEPT but borderline between-source rho, show anyway
for feat in set(flag_feats):
    fig, ax = plt.subplots(figsize=(7, 5))
    for cls, color in [("real", "#3b7dd8"), ("fake", "#d85c3b")]:
        sub = df[df["class"] == cls]
        ax.scatter(sub["orig_resolution"], sub[feat], s=10, alpha=0.5, color=color, label=cls)
    ax.set_xscale("log")
    ax.set_xlabel("original resolution (px^2, log scale)")
    ax.set_ylabel(feat)
    ax.set_title(f"Resolution confound check: {feat}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"confound_{feat}.png", dpi=130)
    plt.close(fig)

# ── 5. contact sheet: 3 real + 3 fake per source, evidence values annotated ──
ANNOT_FEATS = ["freq_spectral_entropy", "tex_local_variance_std", "lm_symmetry_score"]
sources_for_sheet = ALL_SOURCES_ORDER
n_rows = len(sources_for_sheet)
fig, axes = plt.subplots(n_rows, 3, figsize=(9, 3 * n_rows))
for i, src in enumerate(sources_for_sheet):
    sub = df[df.source == src].sample(n=min(3, len(df[df.source == src])), random_state=1)
    for j in range(3):
        ax = axes[i, j] if n_rows > 1 else axes[j]
        ax.axis("off")
        if j >= len(sub):
            continue
        row = sub.iloc[j]
        try:
            img = Image.open(row["image_path"]).convert("RGB").resize((160, 160))
            ax.imshow(img)
        except Exception:
            pass
        txt = "\n".join(f"{f.split('_',1)[1] if '_' in f else f}={row[f]:.3f}" for f in ANNOT_FEATS if pd.notna(row.get(f, np.nan)))
        ax.set_title(f"{src}/{row['class']}\n{txt}", fontsize=6)
fig.tight_layout()
fig.savefig(FIG_DIR / "contact_sheet_evidence_sanity.png", dpi=130)
plt.close(fig)

print("figures written to", FIG_DIR)
print(list(FIG_DIR.glob("*.png")))
