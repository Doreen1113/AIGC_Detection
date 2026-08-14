"""
P1-R1.5 -- Stage 4: compute per (model x source x filter_type x resolution)
metrics from per_image_scores_by_resolution.csv. New, read-only script.

python p1_r1_5_compute_metrics.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"

CELLC_THRESHOLD = 0.85
V816_THRESHOLD_CAL = 0.95
V816_THRESHOLD_UNCAL = 0.85

RNG = np.random.default_rng(20260814)
N_BOOT = 2000
MIN_N_FOR_CI = 20


def bootstrap_ci(values, n_boot=N_BOOT, alpha=0.05):
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < MIN_N_FOR_CI:
        return None
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        boot_means[i] = RNG.choice(values, size=n, replace=True).mean()
    lo, hi = np.percentile(boot_means, [2.5, 97.5])
    return float(lo), float(hi)


def bootstrap_auroc_ci(neg_scores, pos_scores, n_boot=N_BOOT):
    n_neg, n_pos = len(neg_scores), len(pos_scores)
    if n_neg < MIN_N_FOR_CI or n_pos < MIN_N_FOR_CI:
        return None
    neg_scores = np.asarray(neg_scores); pos_scores = np.asarray(pos_scores)
    aucs = []
    for _ in range(n_boot):
        neg_s = RNG.choice(neg_scores, size=n_neg, replace=True)
        pos_s = RNG.choice(pos_scores, size=n_pos, replace=True)
        y = np.concatenate([np.zeros(n_neg), np.ones(n_pos)])
        s = np.concatenate([neg_s, pos_s])
        try:
            aucs.append(roc_auc_score(y, s))
        except Exception:
            continue
    if len(aucs) < n_boot * 0.5:
        return None
    lo, hi = np.percentile(aucs, [2.5, 97.5])
    return float(lo), float(hi)


def main():
    df = pd.read_csv(OUT_DIR / "per_image_scores_by_resolution.csv")
    print(f"Loaded {len(df)} scored rows")

    sources = sorted(df["source"].unique())
    ftypes = ["whitening_medium", "eye_enlarging", "smoothing_medium", "face_reshaping"]
    resolutions = ["native", "canonical_256", "canonical_512", "canonical_1024"]

    models = [
        ("CellC@0.85", "cellc_p_fake", "cellc_p_filter", CELLC_THRESHOLD),
        ("v816@0.95_calibrated", "v816_p_fake", "v816_p_filter", V816_THRESHOLD_CAL),
        ("v816@0.85_uncalibrated_reference", "v816_p_fake", "v816_p_filter", V816_THRESHOLD_UNCAL),
    ]

    metric_rows = []
    for model_name, fake_col, filter_col, thresh in models:
        for source in sources:
            for resolution in resolutions:
                clean_grp = df[(df["source"] == source) & (df["resolution_condition"] == resolution) & (df["filter_type"] == "clean")]
                n_clean = len(clean_grp)
                clean_p_filter = clean_grp[filter_col].values
                false_filter_rate = float((clean_p_filter > thresh).mean()) if n_clean > 0 else np.nan
                ffr_ci = bootstrap_ci((clean_p_filter > thresh).astype(float)) if n_clean > 0 else None

                for ftype in ftypes:
                    comp_grp = df[(df["source"] == source) & (df["resolution_condition"] == resolution) & (df["filter_type"] == ftype)]
                    n = len(comp_grp)
                    if n == 0:
                        continue
                    p_fake = comp_grp[fake_col].values
                    p_filter = comp_grp[filter_col].values

                    fake_recall = float((p_fake > 0.5).mean())
                    joint = ((p_fake > 0.5) & (p_filter > thresh)).astype(float)
                    joint_rate = float(joint.mean())
                    joint_ci = bootstrap_ci(joint)

                    if n_clean >= MIN_N_FOR_CI and n >= MIN_N_FOR_CI:
                        y = np.concatenate([np.zeros(n_clean), np.ones(n)])
                        s = np.concatenate([clean_p_filter, p_filter])
                        try:
                            auroc = float(roc_auc_score(y, s))
                        except Exception:
                            auroc = np.nan
                        auroc_ci = bootstrap_auroc_ci(clean_p_filter, p_filter)
                    else:
                        auroc = np.nan; auroc_ci = None

                    metric_rows.append({
                        "model": model_name, "source": source, "filter_type": ftype,
                        "resolution_condition": resolution,
                        "n_clean_fake": n_clean, "n_fake_filter": n,
                        "clean_fake_false_filter_rate": false_filter_rate,
                        "clean_fake_false_filter_rate_95ci": (f"[{ffr_ci[0]:.4f}, {ffr_ci[1]:.4f}]" if ffr_ci else f"insufficient_n(<{MIN_N_FOR_CI})"),
                        "filter_head_auroc": auroc,
                        "filter_head_auroc_95ci": (f"[{auroc_ci[0]:.4f}, {auroc_ci[1]:.4f}]" if auroc_ci else f"insufficient_n(<{MIN_N_FOR_CI} per class)"),
                        "joint_recognition_rate": joint_rate,
                        "joint_recognition_95ci": (f"[{joint_ci[0]:.4f}, {joint_ci[1]:.4f}]" if joint_ci else f"insufficient_n(<{MIN_N_FOR_CI})"),
                        "fake_head_recall": fake_recall,
                        "mean_filter_probability": float(p_filter.mean()),
                        "median_filter_probability": float(np.median(p_filter)),
                        "calibration_threshold": thresh,
                    })

    out_df = pd.DataFrame(metric_rows)
    out_path = OUT_DIR / "source_by_filter_by_resolution_metrics.csv"
    out_df.to_csv(out_path, index=False)
    print(f"Wrote {len(out_df)} rows -> {out_path}")

    print("\n=== Quick read: v816 calibrated, AUROC by source x resolution, whitening_medium (VALID control) ===")
    sub = out_df[(out_df["model"] == "v816@0.95_calibrated") & (out_df["filter_type"] == "whitening_medium")]
    piv = sub.pivot(index="source", columns="resolution_condition", values="filter_head_auroc")
    piv = piv.reindex(columns=resolutions)
    print(piv.round(3).to_string())

    print("\n=== Quick read: v816 calibrated, AUROC by source x resolution, eye_enlarging (VALID_WITH_CAVEAT control) ===")
    sub2 = out_df[(out_df["model"] == "v816@0.95_calibrated") & (out_df["filter_type"] == "eye_enlarging")]
    piv2 = sub2.pivot(index="source", columns="resolution_condition", values="filter_head_auroc")
    piv2 = piv2.reindex(columns=resolutions)
    print(piv2.round(3).to_string())


if __name__ == "__main__":
    main()
