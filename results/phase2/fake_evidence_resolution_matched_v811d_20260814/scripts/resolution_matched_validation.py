"""
Phase 2F-R1 -- Resolution-matched validation of tex_local_variance_std.

Reuses the per-image raw_features.csv produced by Phase 2F
(results/phase2/fake_evidence_discovery_v811d_20260814/raw_features.csv),
which was computed with pl.preprocess_jpeg(q=85) + pl.has_face() +
224x224 resize, i.e. the exact same feature definition and face-gate this
round is required to reuse. No re-extraction is performed: all columns
needed for this round (tex_local_variance_std, orig_width/height,
face_bbox_x0/x1/y0/y1, face_size_confound) are already present per-image.

Outputs (all under results/phase2/fake_evidence_resolution_matched_v811d_20260814/):
  matched_pairs_manifest.csv
  matching_balance_table.csv
  resolution_matched_results.csv       (4-way comparison table)
  regression_sensitivity_results.csv
  regression_sensitivity_results.json
  figures/balance_love_plot.png
  figures/auroc_by_source_by_condition.png
  figures/scatter_texvar_vs_resolution_pre_post.png
  run_manifest.json
"""
import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment
from scipy import stats as sps
from sklearn.metrics import roc_auc_score
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

SEED = 20260814
RNG = np.random.default_rng(SEED)
N_BOOT = 1000

SRC_DIR = Path(r"C:\My_Project\AIGC\results\phase2\fake_evidence_discovery_v811d_20260814")
OUT_DIR = Path(r"C:\My_Project\AIGC\results\phase2\fake_evidence_resolution_matched_v811d_20260814")
FIG_DIR = OUT_DIR / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

FEATURE = "tex_local_variance_std"
FAKE_SOURCES = ["aiguard_unseen", "stylegan2_ood", "df40_dit", "df40_sit",
                "df40_ddim", "df40_pixart", "df40_sd21", "midjourney"]

# caliper: max standardized Euclidean distance allowed for a match, expressed
# as "0.2 SD per matching dimension" -> for k standardized dims, caliper on
# the Euclidean norm = 0.2 * sqrt(k) (norm of a vector whose every component
# is exactly at the 0.2-SD tolerance). Documented explicitly per task spec.
CALIPER_PER_DIM = 0.20

# minimum valid-matched n for a source/condition to be treated as a reliable
# estimate at all (Cohen's d / AUROC on n<10 per arm is not interpretable,
# even if a handful of matches happen to clear the caliper) -- documented
# threshold, applied on top of the per-pair caliper.
MIN_RELIABLE_N = 10

CONDITIONS = {
    "resolution_matched": ["log_resolution"],
    "facesize_matched": ["log_fbw", "log_fbh", "crop_scale"],
    "joint_matched": ["log_resolution", "log_fbw", "log_fbh", "crop_scale"],
}


def load_data():
    df = pd.read_csv(SRC_DIR / "raw_features.csv")
    df["face_bbox_width"] = df["face_bbox_x1"] - df["face_bbox_x0"]
    df["face_bbox_height"] = df["face_bbox_y1"] - df["face_bbox_y0"]
    df["crop_scale"] = df["face_size_confound"]  # face_bbox_area / (224*224), scale-invariant
    before = len(df)
    df = df.dropna(subset=[FEATURE, "crop_scale", "face_bbox_width", "face_bbox_height",
                            "orig_resolution"]).copy()
    dropped = before - len(df)
    df["log_resolution"] = np.log(df["orig_resolution"])
    df["log_fbw"] = np.log(df["face_bbox_width"].clip(lower=1e-3))
    df["log_fbh"] = np.log(df["face_bbox_height"].clip(lower=1e-3))
    df["fake_label"] = (df["class"] == "fake").astype(int)
    return df, dropped


def cohend(fake_vals, real_vals):
    nf, nr = len(fake_vals), len(real_vals)
    vf, vr = np.var(fake_vals, ddof=1), np.var(real_vals, ddof=1)
    pooled_sd = np.sqrt(((nf - 1) * vf + (nr - 1) * vr) / (nf + nr - 2))
    if pooled_sd == 0:
        return np.nan
    return (np.mean(fake_vals) - np.mean(real_vals)) / pooled_sd


def auroc_with_ci(fake_vals, real_vals, seed):
    y = np.concatenate([np.zeros(len(real_vals)), np.ones(len(fake_vals))])
    s = np.concatenate([real_vals, fake_vals])
    try:
        point = roc_auc_score(y, s)
    except ValueError:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    boots = []
    nf, nr = len(fake_vals), len(real_vals)
    for _ in range(N_BOOT):
        fi = rng.integers(0, nf, nf)
        ri = rng.integers(0, nr, nr)
        yb = np.concatenate([np.zeros(nr), np.ones(nf)])
        sb = np.concatenate([real_vals[ri], fake_vals[fi]])
        if len(np.unique(yb)) < 2 or len(np.unique(sb)) < 2:
            continue
        try:
            boots.append(roc_auc_score(yb, sb))
        except ValueError:
            continue
    if len(boots) < 10:
        return point, np.nan, np.nan
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, lo, hi


def smd(a, b):
    va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
    pooled = np.sqrt((va + vb) / 2)
    if pooled == 0:
        return 0.0
    return (np.mean(a) - np.mean(b)) / pooled


def optimal_match(fake_df, real_pool, covs, source_idx):
    """1:1 optimal (min total distance) matching without replacement,
    real supply always >= fake demand here. Returns matched real indices
    (into real_pool, aligned to fake_df row order) and per-pair standardized
    distance, with caliper applied (NaN entries = no valid match)."""
    combo = pd.concat([fake_df[covs], real_pool[covs]], axis=0)
    mu = combo.mean()
    sd = combo.std(ddof=0).replace(0, 1.0)
    Xf = ((fake_df[covs] - mu) / sd).to_numpy()
    Xr = ((real_pool[covs] - mu) / sd).to_numpy()

    # cost matrix: fake x real, Euclidean distance in standardized space
    diff = Xf[:, None, :] - Xr[None, :, :]
    cost = np.sqrt((diff ** 2).sum(axis=2))

    row_ind, col_ind = linear_sum_assignment(cost)
    dists = cost[row_ind, col_ind]

    caliper = CALIPER_PER_DIM * np.sqrt(len(covs))
    matched_real_idx = np.full(len(fake_df), -1, dtype=int)
    matched_dist = np.full(len(fake_df), np.nan)
    for r, c, d in zip(row_ind, col_ind, dists):
        matched_dist[r] = d
        if d <= caliper:
            matched_real_idx[r] = real_pool.index[c]
    return matched_real_idx, matched_dist, caliper


def analyze_condition(fake_df, real_sel_df, label):
    fv = fake_df[FEATURE].to_numpy()
    rv = real_sel_df[FEATURE].to_numpy()
    d = cohend(fv, rv)
    auroc, lo, hi = auroc_with_ci(fv, rv, seed=SEED + abs(hash(label)) % 100000)
    direction = "higher-in-real" if d < 0 else ("higher-in-fake" if d > 0 else "no-diff")
    clears_bar = (auroc <= 0.40) or (auroc >= 0.60)
    reliable_n = (len(fv) >= MIN_RELIABLE_N) and (len(rv) >= MIN_RELIABLE_N)
    if not reliable_n:
        direction = f"UNRELIABLE_N<{MIN_RELIABLE_N} ({direction})"
        clears_bar = False
    return {
        "n_fake": len(fv), "n_real": len(rv),
        "cohens_d": d, "auroc": auroc, "auroc_ci_lower": lo, "auroc_ci_upper": hi,
        "direction": direction, "clears_060_bar": bool(clears_bar),
        "reliable_n": bool(reliable_n),
    }


def main():
    df, n_dropped_nan = load_data()
    real_pool = df[df["class"] == "real"].copy()

    manifest_rows = []
    balance_rows = []
    results_rows = []
    reg_rows = []
    scatter_records = []
    resolution_matched_records = []

    all_covs = ["log_resolution", "log_fbw", "log_fbh", "crop_scale"]

    per_source_stage_counts = {}

    for src in FAKE_SOURCES:
        fake_df = df[(df["class"] == "fake") & (df["source"] == src)].copy()
        n_requested_gate_passed = len(fake_df)

        # ---- (a) unmatched, recomputed here for internal consistency ----
        res_a = analyze_condition(fake_df, real_pool, f"{src}__unmatched")
        results_rows.append({"source": src, "condition": "a_unmatched_recomputed", **res_a})

        # pre-match balance (unmatched full real pool vs this fake source)
        for cov, cov_label in [("log_resolution", "resolution"), ("crop_scale", "crop_scale"),
                                ("log_fbw", "face_bbox_width"), ("log_fbh", "face_bbox_height")]:
            balance_rows.append({
                "source": src, "condition": "pre_match_unmatched",
                "covariate": cov_label,
                "smd": smd(fake_df[cov].to_numpy(), real_pool[cov].to_numpy()),
            })

        stage_counts = {"requested_face_gate_passed": n_requested_gate_passed}

        for cond_name, covs in CONDITIONS.items():
            matched_real_idx, matched_dist, caliper = optimal_match(fake_df, real_pool, covs, src)
            valid_mask = matched_real_idx >= 0
            n_valid = int(valid_mask.sum())
            n_missing = int((~valid_mask).sum())
            stage_counts[f"{cond_name}_valid_matched"] = n_valid
            stage_counts[f"{cond_name}_missing_insufficient_match"] = n_missing

            # manifest rows (per fake image)
            for i, (idx, ridx, dist) in enumerate(zip(fake_df.index, matched_real_idx, matched_dist)):
                frow = fake_df.loc[idx]
                rrow = real_pool.loc[ridx] if ridx >= 0 else None
                manifest_rows.append({
                    "source": src, "condition": cond_name,
                    "fake_image_path": frow["image_path"],
                    "fake_orig_resolution": frow["orig_resolution"],
                    "fake_crop_scale": frow["crop_scale"],
                    "fake_tex_local_variance_std": frow[FEATURE],
                    "matched_real_image_path": rrow["image_path"] if rrow is not None else None,
                    "matched_real_source": rrow["source"] if rrow is not None else None,
                    "matched_real_orig_resolution": rrow["orig_resolution"] if rrow is not None else None,
                    "matched_real_crop_scale": rrow["crop_scale"] if rrow is not None else None,
                    "matched_real_tex_local_variance_std": rrow[FEATURE] if rrow is not None else None,
                    "standardized_distance": dist,
                    "caliper": caliper,
                    "valid_match": bool(ridx >= 0),
                })

            if n_valid == 0:
                results_rows.append({
                    "source": src, "condition": cond_name,
                    "n_fake": n_valid, "n_real": n_valid,
                    "cohens_d": np.nan, "auroc": np.nan,
                    "auroc_ci_lower": np.nan, "auroc_ci_upper": np.nan,
                    "direction": "MISSING_INSUFFICIENT_MATCH", "clears_060_bar": False,
                    "reliable_n": False,
                })
                for cov, cov_label in [("log_resolution", "resolution"), ("crop_scale", "crop_scale"),
                                        ("log_fbw", "face_bbox_width"), ("log_fbh", "face_bbox_height")]:
                    balance_rows.append({"source": src, "condition": cond_name, "covariate": cov_label,
                                          "smd": np.nan})
                continue

            matched_fake = fake_df.loc[fake_df.index[valid_mask]]
            matched_real_indices = matched_real_idx[valid_mask]
            matched_real = real_pool.loc[matched_real_indices]

            res = analyze_condition(matched_fake, matched_real, f"{src}__{cond_name}")
            results_rows.append({"source": src, "condition": cond_name, **res})

            for cov, cov_label in [("log_resolution", "resolution"), ("crop_scale", "crop_scale"),
                                    ("log_fbw", "face_bbox_width"), ("log_fbh", "face_bbox_height")]:
                balance_rows.append({
                    "source": src, "condition": cond_name, "covariate": cov_label,
                    "smd": smd(matched_fake[cov].to_numpy(), matched_real[cov].to_numpy()),
                })

            if cond_name == "joint_matched":
                pooled_df = pd.concat([
                    matched_fake.assign(fake_label=1),
                    matched_real.assign(fake_label=0),
                ], axis=0)
                pooled_df["source_group"] = src
                scatter_records.append(pooled_df)

            if cond_name == "resolution_matched":
                pooled_df_res = pd.concat([
                    matched_fake.assign(fake_label=1),
                    matched_real.assign(fake_label=0),
                ], axis=0)
                pooled_df_res["source_group"] = src
                resolution_matched_records.append(pooled_df_res)

        per_source_stage_counts[src] = stage_counts

    manifest_df = pd.DataFrame(manifest_rows)
    balance_df = pd.DataFrame(balance_rows)
    results_df = pd.DataFrame(results_rows)

    manifest_df.to_csv(OUT_DIR / "matched_pairs_manifest.csv", index=False)
    balance_df.to_csv(OUT_DIR / "matching_balance_table.csv", index=False)
    results_df.to_csv(OUT_DIR / "resolution_matched_results.csv", index=False)

    # ---------------- Pooled joint-matched dataset for regression ----------------
    pooled = pd.concat(scatter_records, axis=0, ignore_index=True) if scatter_records else pd.DataFrame()
    pooled.to_csv(OUT_DIR / "joint_matched_pooled_for_regression.csv", index=False)

    reg_results = run_regressions(pooled)
    reg_results["_note"] = ("PRIMARY analysis: pooled joint (resolution+face-size) matched set. " +
                             f"n is small (see per-source n) because the joint caliper (0.20 SD/dim, "
                             f"{len(CONDITIONS['joint_matched'])} dims) is strict relative to sample size.")

    pooled_res = pd.concat(resolution_matched_records, axis=0, ignore_index=True) if resolution_matched_records else pd.DataFrame()
    pooled_res.to_csv(OUT_DIR / "resolution_matched_pooled_for_regression.csv", index=False)
    reg_results_secondary = run_regressions(pooled_res)
    reg_results_secondary["_note"] = ("SECONDARY/supplementary robustness analysis: pooled "
                                       "resolution-ONLY matched set (larger n, face-size not "
                                       "separately controlled here -- see joint result as the "
                                       "primary, stricter check).")
    reg_results_all = {"primary_joint_matched": reg_results,
                        "secondary_resolution_matched": reg_results_secondary}

    with open(OUT_DIR / "regression_sensitivity_results.json", "w", encoding="utf-8") as f:
        json.dump(reg_results_all, f, indent=2, default=float)
    pd.json_normalize(reg_results_all, sep="__").to_csv(
        OUT_DIR / "regression_sensitivity_results.csv", index=False)

    # ---------------- pooled-across-sources matched metrics (joint condition) ----
    pooled_metrics = {}
    if len(pooled) > 0:
        fv = pooled.loc[pooled.fake_label == 1, FEATURE].to_numpy()
        rv = pooled.loc[pooled.fake_label == 0, FEATURE].to_numpy()
        d = cohend(fv, rv)
        auroc, lo, hi = auroc_with_ci(fv, rv, seed=SEED + 999)
        pooled_metrics = {
            "n_fake": len(fv), "n_real": len(rv), "cohens_d": d,
            "auroc": auroc, "auroc_ci_lower": lo, "auroc_ci_upper": hi,
            "direction": "higher-in-real" if d < 0 else "higher-in-fake",
        }
    with open(OUT_DIR / "pooled_joint_matched_metrics.json", "w", encoding="utf-8") as f:
        json.dump(pooled_metrics, f, indent=2, default=float)

    make_figures(df, real_pool, manifest_df, results_df, balance_df)

    run_manifest = {
        "seed": SEED,
        "n_boot": N_BOOT,
        "feature": FEATURE,
        "caliper_per_dim_sd": CALIPER_PER_DIM,
        "matching_method": "1:1 optimal assignment (scipy.optimize.linear_sum_assignment) "
                            "on standardized Euclidean distance, without replacement, "
                            "real pool = pooled real (celeba_test+lfw+aiguard_unseen_real, n=210) "
                            "for every fake source (documented consistent choice; no cross-source "
                            "borrowing of fake images, each fake source matched independently "
                            "against the full real pool using its own covariate distribution)",
        "caliper_definition": "match discarded (MISSING_INSUFFICIENT_MATCH) if optimal standardized "
                               "Euclidean distance > 0.20 * sqrt(n_covariate_dims) "
                               "(equivalent to an average per-dimension tolerance of 0.20 SD)",
        "conditions": {k: v for k, v in CONDITIONS.items()},
        "source_data": str(SRC_DIR / "raw_features.csv"),
        "source_data_reused_not_reextracted": True,
        "n_rows_dropped_missing_covariates": int(n_dropped_nan),
        "n_real_pool": int(len(real_pool)),
        "fake_sources": FAKE_SOURCES,
        "per_source_stage_counts": per_source_stage_counts,
        "package_versions": {
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": __import__("scipy").__version__,
            "sklearn": __import__("sklearn").__version__,
            "statsmodels": __import__("statsmodels").__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    with open(OUT_DIR / "run_manifest.json", "w", encoding="utf-8") as f:
        json.dump(run_manifest, f, indent=2, default=str)

    print("Done.")
    print(results_df.to_string())


def run_regressions(pooled):
    import statsmodels.api as sm

    out = {"per_source": {}, "pooled_naive": None, "pooled_source_fixed_effects": None}
    if len(pooled) == 0:
        return out

    def fit_logit(X, y, label):
        Xc = sm.add_constant(X, has_constant="add")
        try:
            model = sm.Logit(y, Xc).fit(disp=0, maxiter=200)
            coef = model.params.get(FEATURE, np.nan)
            se = model.bse.get(FEATURE, np.nan)
            pval = model.pvalues.get(FEATURE, np.nan)
            ci = model.conf_int().loc[FEATURE].tolist() if FEATURE in model.params.index else [np.nan, np.nan]
            return {"method": "statsmodels.Logit (MLE)", "n": int(len(y)),
                    "coef_tex_local_variance_std": float(coef), "se": float(se),
                    "p_value": float(pval), "ci_lower": float(ci[0]), "ci_upper": float(ci[1]),
                    "converged": bool(getattr(model.mle_retvals, "get", lambda *a: True)("converged", True))
                    if hasattr(model, "mle_retvals") else True}
        except Exception as e:
            try:
                model = sm.Logit(y, Xc).fit_regularized(alpha=1.0, disp=0)
                coef = model.params.get(FEATURE, np.nan)
                return {"method": "statsmodels.Logit fit_regularized (fallback, MLE failed/separated)",
                        "n": int(len(y)), "coef_tex_local_variance_std": float(coef),
                        "se": None, "p_value": None, "ci_lower": None, "ci_upper": None,
                        "converged": False, "mle_error": str(e)}
            except Exception as e2:
                return {"method": "FAILED", "n": int(len(y)), "error": f"{e} / {e2}"}

    # standardize covariates for numerical stability / comparable coefficients
    covs = [FEATURE, "log_resolution", "log_fbw", "log_fbh"]
    z = pooled.copy()
    for c in covs:
        z[c] = (z[c] - z[c].mean()) / z[c].std(ddof=0)

    # per-source
    for src, g in z.groupby("source_group"):
        y = g["fake_label"].to_numpy()
        X = g[[FEATURE, "log_resolution", "log_fbw"]]
        if len(np.unique(y)) < 2 or len(g) < 2 * MIN_RELIABLE_N:
            out["per_source"][src] = {"method": "SKIPPED_INSUFFICIENT_N", "n": int(len(g))}
            continue
        out["per_source"][src] = fit_logit(X, y, src)

    # pooled naive (no source control)
    y = z["fake_label"].to_numpy()
    X = z[[FEATURE, "log_resolution", "log_fbw"]]
    out["pooled_naive"] = fit_logit(X, y, "pooled_naive")

    # pooled with source fixed effects (dummy variables)
    dummies = pd.get_dummies(z["source_group"], prefix="src", drop_first=True).astype(float)
    X_fe = pd.concat([z[[FEATURE, "log_resolution", "log_fbw"]], dummies], axis=1)
    out["pooled_source_fixed_effects"] = fit_logit(X_fe, y, "pooled_fe")
    out["pooled_source_fixed_effects"]["note"] = (
        "Fixed-effects (source dummy) logistic regression used instead of a true "
        "random-intercept MixedLM: per-source matched n (44-70, further reduced by "
        "the joint caliper) is too small for a stable random-effects variance "
        "estimate; a fixed-effects model is a documented, more conservative "
        "substitute that still absorbs source-level baseline differences."
    )
    return out


def make_figures(df, real_pool, manifest_df, results_df, balance_df):
    # 1. Love plot: pre vs post SMD per source (joint_matched) for resolution + face-size
    fig, ax = plt.subplots(figsize=(9, 6))
    conds = ["pre_match_unmatched", "resolution_matched", "facesize_matched", "joint_matched"]
    colors = {"pre_match_unmatched": "#999999", "resolution_matched": "#4C72B0",
              "facesize_matched": "#DD8452", "joint_matched": "#55A868"}
    sub = balance_df[(balance_df.covariate == "resolution")]
    sources = FAKE_SOURCES
    y_pos = np.arange(len(sources))
    width = 0.2
    for i, cond in enumerate(conds):
        vals = [sub[(sub.source == s) & (sub.condition == cond)]["smd"].values for s in sources]
        vals = [v[0] if len(v) else np.nan for v in vals]
        ax.barh(y_pos + (i - 1.5) * width, vals, height=width, label=cond, color=colors[cond])
    ax.set_yticks(y_pos)
    ax.set_yticklabels(sources)
    ax.axvline(0, color="black", lw=0.8)
    ax.axvline(0.1, color="red", ls="--", lw=0.8, alpha=0.6)
    ax.axvline(-0.1, color="red", ls="--", lw=0.8, alpha=0.6)
    ax.set_xlabel("Standardized Mean Difference (resolution, fake - real)")
    ax.set_title("Covariate balance (resolution): pre- vs post-match SMD by source")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "balance_love_plot.png", dpi=150)
    plt.close(fig)

    # 2. AUROC by source across 4 conditions
    fig, ax = plt.subplots(figsize=(11, 6))
    cond_order = ["a_unmatched_recomputed", "resolution_matched", "facesize_matched", "joint_matched"]
    width = 0.2
    for i, cond in enumerate(cond_order):
        vals, errs_lo, errs_hi = [], [], []
        for s in sources:
            row = results_df[(results_df.source == s) & (results_df.condition == cond)]
            if len(row) == 0 or pd.isna(row.iloc[0]["auroc"]):
                vals.append(np.nan); errs_lo.append(0); errs_hi.append(0)
                continue
            r = row.iloc[0]
            vals.append(r["auroc"])
            lo = r["auroc"] - r["auroc_ci_lower"] if not pd.isna(r["auroc_ci_lower"]) else 0
            hi = r["auroc_ci_upper"] - r["auroc"] if not pd.isna(r["auroc_ci_upper"]) else 0
            errs_lo.append(max(lo, 0)); errs_hi.append(max(hi, 0))
        x = np.arange(len(sources)) + (i - 1.5) * width
        ax.bar(x, vals, width=width, label=cond, yerr=[errs_lo, errs_hi], capsize=2)
    ax.axhline(0.40, color="red", ls="--", lw=0.8, label="0.40 / 0.60 bar")
    ax.axhline(0.60, color="red", ls="--", lw=0.8)
    ax.axhline(0.50, color="black", lw=0.6)
    ax.set_xticks(np.arange(len(sources)))
    ax.set_xticklabels(sources, rotation=30, ha="right")
    ax.set_ylabel("AUROC (real=0, fake=1)")
    ax.set_title("tex_local_variance_std AUROC by source, across matching conditions")
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "auroc_by_source_by_condition.png", dpi=150)
    plt.close(fig)

    # 3. scatter tex_local_variance_std vs resolution, before/after matching
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    ax = axes[0]
    for s in sources:
        fd = df[(df["class"] == "fake") & (df["source"] == s)]
        ax.scatter(fd["orig_resolution"], fd[FEATURE], s=10, alpha=0.5, label=s)
    ax.scatter(real_pool["orig_resolution"], real_pool[FEATURE], s=10, alpha=0.5,
               color="black", marker="x", label="real (pooled)")
    ax.set_xscale("log")
    ax.set_xlabel("original resolution (px^2, log scale)")
    ax.set_ylabel(FEATURE)
    ax.set_title("Before matching (all fake sources + pooled real)")

    ax = axes[1]
    jm = manifest_df[(manifest_df.condition == "joint_matched") & (manifest_df.valid_match)]
    ax.scatter(jm["fake_orig_resolution"], jm["fake_tex_local_variance_std"], s=10, alpha=0.5,
               color="tab:orange", label="fake (matched)")
    ax.scatter(jm["matched_real_orig_resolution"], jm["matched_real_tex_local_variance_std"], s=10,
               alpha=0.5, color="black", marker="x", label="real (matched partner)")
    ax.set_xscale("log")
    ax.set_xlabel("original resolution (px^2, log scale)")
    ax.set_title("After joint (resolution+face-size) matching, all sources pooled")
    for a in axes:
        a.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(FIG_DIR / "scatter_texvar_vs_resolution_pre_post.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    main()
