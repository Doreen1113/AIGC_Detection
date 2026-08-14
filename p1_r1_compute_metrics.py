"""
P1-R1 Cross-Source Failure Anatomy -- Stage 2: compute source_by_filter_metrics.csv
and routing_failure_breakdown.csv from the cached per-image scores
(per_image_scores.csv, produced by p1_r1_score_replication_set.py).

New, read-only analysis script (reads only the CSV this research round already
produced plus splits/v815_replication_set.tsv for row counts already used;
writes nothing outside results/research/p1_r1_cross_source_failure_anatomy_20260814/).

python p1_r1_compute_metrics.py
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_cross_source_failure_anatomy_20260814"

CELLC_THRESHOLD = 0.85
V816_THRESHOLD_CAL = 0.95
V816_THRESHOLD_UNCAL = 0.85

RNG = np.random.default_rng(20260814)
N_BOOT = 2000
MIN_N_FOR_CI = 20


def bootstrap_ci(values, n_boot=N_BOOT, alpha=0.05):
    """values: 0/1 array (or any numeric). Returns (lo, hi) percentile bootstrap CI
    of the mean, or None if n < MIN_N_FOR_CI."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n < MIN_N_FOR_CI:
        return None
    boot_means = np.empty(n_boot)
    for i in range(n_boot):
        sample = RNG.choice(values, size=n, replace=True)
        boot_means[i] = sample.mean()
    lo, hi = np.percentile(boot_means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def bootstrap_auroc_ci(neg_scores, pos_scores, n_boot=N_BOOT, alpha=0.05):
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
        if len(set(y)) < 2:
            continue
        try:
            aucs.append(roc_auc_score(y, s))
        except Exception:
            continue
    if len(aucs) < n_boot * 0.5:
        return None
    lo, hi = np.percentile(aucs, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def main():
    df = pd.read_csv(OUT_DIR / "per_image_scores.csv")
    print(f"Loaded {len(df)} scored rows")

    sources = sorted(df["source"].unique())
    ftypes = sorted(t for t in df["ftype"].unique() if t != "none")

    models = [
        ("CellC@0.85", "cellc_p_fake", "cellc_p_filter", CELLC_THRESHOLD),
        ("v816@0.95_calibrated", "v816_p_fake", "v816_p_filter", V816_THRESHOLD_CAL),
        ("v816@0.85_uncalibrated_reference", "v816_p_fake", "v816_p_filter", V816_THRESHOLD_UNCAL),
    ]

    metric_rows = []
    failure_rows = []

    for model_name, fake_col, filter_col, thresh in models:
        for source in sources:
            clean_grp = df[(df["source"] == source) & (df["ftype"] == "none")]
            n_clean = len(clean_grp)
            clean_p_filter = clean_grp[filter_col].values
            false_filter_rate = float((clean_p_filter > thresh).mean()) if n_clean > 0 else np.nan
            false_filter_ci = bootstrap_ci((clean_p_filter > thresh).astype(float)) if n_clean > 0 else None

            for ftype in ftypes:
                comp_grp = df[(df["source"] == source) & (df["ftype"] == ftype)]
                n_fake_filter = len(comp_grp)
                if n_fake_filter == 0:
                    continue
                p_fake = comp_grp[fake_col].values
                p_filter = comp_grp[filter_col].values

                fake_head_recall = float((p_fake > 0.5).mean())
                has_filter_recall = float((p_filter > thresh).mean())
                joint = ((p_fake > 0.5) & (p_filter > thresh)).astype(float)
                joint_rate = float(joint.mean())
                joint_ci = bootstrap_ci(joint)

                # AUROC: clean (source-matched) vs this composite type, score = p_filter
                if n_clean >= MIN_N_FOR_CI and n_fake_filter >= MIN_N_FOR_CI:
                    y = np.concatenate([np.zeros(n_clean), np.ones(n_fake_filter)])
                    s = np.concatenate([clean_p_filter, p_filter])
                    try:
                        auroc = float(roc_auc_score(y, s))
                    except Exception:
                        auroc = np.nan
                    auroc_ci = bootstrap_auroc_ci(clean_p_filter, p_filter)
                else:
                    auroc = np.nan
                    auroc_ci = None

                metric_rows.append({
                    "model": model_name, "source": source, "filter_type": ftype,
                    "n_clean_fake": n_clean, "n_fake_filter": n_fake_filter,
                    "clean_fake_false_filter_rate": false_filter_rate,
                    "clean_fake_false_filter_rate_95ci": (
                        f"[{false_filter_ci[0]:.4f}, {false_filter_ci[1]:.4f}]" if false_filter_ci else
                        f"insufficient_n(<{MIN_N_FOR_CI})"),
                    "filter_head_auroc": auroc,
                    "filter_head_auroc_95ci": (
                        f"[{auroc_ci[0]:.4f}, {auroc_ci[1]:.4f}]" if auroc_ci else
                        f"insufficient_n(<{MIN_N_FOR_CI} per class)"),
                    "joint_recognition_rate": joint_rate,
                    "joint_recognition_95ci": (
                        f"[{joint_ci[0]:.4f}, {joint_ci[1]:.4f}]" if joint_ci else
                        f"insufficient_n(<{MIN_N_FOR_CI})"),
                    "fake_head_recall": fake_head_recall,
                    "has_filter_recall": has_filter_recall,
                    "mean_filter_probability": float(p_filter.mean()),
                    "median_filter_probability": float(np.median(p_filter)),
                    "calibration_threshold": thresh,
                })

                # ---- routing failure breakdown (composites that FAILED joint recognition) ----
                l1_manip = comp_grp["l1_p_manip"].values
                fail_mask = ~joint.astype(bool)
                n_fail = int(fail_mask.sum())
                modes = {"layer1_real": 0, "fake_head_miss": 0, "filter_head_miss": 0,
                         "threshold_calibration_miss": 0, "other_unclassifiable": 0}
                for j in range(n_fake_filter):
                    if not fail_mask[j]:
                        continue
                    if l1_manip[j] <= 0.5:
                        modes["layer1_real"] += 1
                    elif p_fake[j] <= 0.5:
                        modes["fake_head_miss"] += 1
                    elif p_filter[j] <= 0.5:
                        modes["filter_head_miss"] += 1
                    elif p_filter[j] <= thresh:
                        modes["threshold_calibration_miss"] += 1
                    else:
                        modes["other_unclassifiable"] += 1
                for mode, cnt in modes.items():
                    failure_rows.append({
                        "model": model_name, "source": source, "filter_type": ftype,
                        "n_failures": n_fail, "n_total_composites": n_fake_filter,
                        "failure_mode": mode, "count": cnt,
                        "pct_of_failures": (cnt / n_fail * 100) if n_fail > 0 else np.nan,
                        "pct_of_all_composites": cnt / n_fake_filter * 100,
                    })

    metrics_df = pd.DataFrame(metric_rows)
    metrics_path = OUT_DIR / "source_by_filter_metrics.csv"
    metrics_df.to_csv(metrics_path, index=False)
    print(f"Wrote {len(metrics_df)} rows -> {metrics_path}")

    failure_df = pd.DataFrame(failure_rows)
    failure_path = OUT_DIR / "routing_failure_breakdown.csv"
    failure_df.to_csv(failure_path, index=False)
    print(f"Wrote {len(failure_df)} rows -> {failure_path}")

    # console summary for sanity-checking against known EXPERIMENT_REGISTRY numbers
    print("\n=== Sanity check vs EXPERIMENT_REGISTRY.md known figures ===")
    for model_name, fake_col, filter_col, thresh in models:
        comp = df[df["ftype"] != "none"]
        p_fake = comp[fake_col].values; p_filter = comp[filter_col].values
        joint = ((p_fake > 0.5) & (p_filter > thresh)).mean() * 100
        print(f"  {model_name}: overall joint recognition = {joint:.2f}%")


if __name__ == "__main__":
    main()
