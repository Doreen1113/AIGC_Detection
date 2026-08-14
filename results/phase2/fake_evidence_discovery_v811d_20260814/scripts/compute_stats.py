"""
Phase 2F -- Fake Evidence Discovery: statistics computation.

Reads raw_features.csv, computes per (evidence_feature, fake_source) stats
(Cohen's d, bootstrap AUROC CI, direction, correlations with v8.11
fake_probability and prior CAM faithfulness hot_drop@k20, resolution/face-size
confound correlations), and applies the decision rubric to produce
evidence_candidate_decision_table.csv.

python compute_stats.py
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as sstats

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "phase2" / "fake_evidence_discovery_v811d_20260814"

RNG_SEED = 20260814
N_BOOT = 1000

FAMILY_MAP = {
    "freq_spectral_entropy": "frequency", "freq_band_ratio_high_mid": "frequency",
    "freq_band_ratio_high_low": "frequency", "freq_band_ratio_mid_low": "frequency",
    "freq_high_energy_frac": "frequency", "freq_radial_powerlaw_slope": "frequency",
    "freq_powerlaw_residual_std": "frequency", "freq_logmag_mean": "frequency",
    "tex_local_variance_mean": "texture", "tex_local_variance_std": "texture",
    "tex_lbp_entropy": "texture", "tex_lbp_uniformity": "texture",
    "tex_glcm_contrast": "texture", "tex_glcm_homogeneity": "texture",
    "tex_glcm_energy": "texture", "tex_highpass_energy": "texture",
    "tex_autocorr_peak_sharpness": "texture",
    "lm_symmetry_score": "landmark_geometry", "lm_interocular_over_facewidth": "landmark_geometry",
    "lm_mouthwidth_over_interocular": "landmark_geometry", "lm_pose_yaw_proxy": "landmark_geometry",
    "bnd_boundary_edge_contrast": "boundary", "bnd_ring_texture_diff": "boundary",
    "bnd_ring_mean_diff": "boundary",
}
EVIDENCE_FEATURES = list(FAMILY_MAP.keys())

REAL_SOURCES = ["celeba_test", "lfw", "aiguard_unseen_real"]
FAKE_SOURCES = ["aiguard_unseen", "stylegan2_ood", "df40_dit", "df40_sit",
                "df40_ddim", "df40_pixart", "df40_sd21", "midjourney"]


def cohens_d(a, b):
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    pooled_std = np.sqrt(((na - 1) * a.var(ddof=1) + (nb - 1) * b.var(ddof=1)) / (na + nb - 2))
    if pooled_std == 0:
        return 0.0
    return float((b.mean() - a.mean()) / pooled_std)  # real=a, fake=b: positive = higher-in-fake


def auroc(real_vals, fake_vals):
    """real=0, fake=1. Mann-Whitney U based AUROC."""
    real_vals = np.asarray(real_vals, dtype=float); fake_vals = np.asarray(fake_vals, dtype=float)
    n_r, n_f = len(real_vals), len(fake_vals)
    if n_r == 0 or n_f == 0:
        return np.nan
    u, _ = sstats.mannwhitneyu(fake_vals, real_vals, alternative="two-sided")
    return float(u / (n_r * n_f))


def bootstrap_auroc_ci(real_vals, fake_vals, n_boot=N_BOOT, seed=RNG_SEED):
    rng = np.random.RandomState(seed)
    real_vals = np.asarray(real_vals, dtype=float); fake_vals = np.asarray(fake_vals, dtype=float)
    n_r, n_f = len(real_vals), len(fake_vals)
    if n_r < 3 or n_f < 3:
        return np.nan, np.nan
    boots = np.empty(n_boot)
    for i in range(n_boot):
        rs = real_vals[rng.randint(0, n_r, n_r)]
        fs = fake_vals[rng.randint(0, n_f, n_f)]
        boots[i] = auroc(rs, fs)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return float(lo), float(hi)


def spearman(x, y):
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    mask = ~(np.isnan(x) | np.isnan(y))
    if mask.sum() < 5:
        return np.nan
    if np.std(x[mask]) == 0 or np.std(y[mask]) == 0:
        return np.nan
    rho, _ = sstats.spearmanr(x[mask], y[mask])
    return float(rho)


def main():
    df = pd.read_csv(OUT_DIR / "raw_features.csv")

    # join CAM faithfulness hot_drop@k20 blur from prior XAI audit
    prior_csv = BASE / "results" / "phase2" / "fake_xai_level12_v811d_20260814" / "fake_xai_deletion_metrics.csv"
    prior = pd.read_csv(prior_csv)
    hot20 = prior[(prior.condition == "hot") & (prior.k == 0.20) & (prior.masking_method == "blur")]
    hot20 = hot20[["image_path", "drop"]].drop_duplicates(subset="image_path").rename(
        columns={"drop": "hot_drop_k20"})
    df = df.merge(hot20, on="image_path", how="left")
    n_matched = df["hot_drop_k20"].notna().sum()
    print(f"CAM faithfulness join: {n_matched} / {len(df)} rows matched (fake images only expected to match)")

    real_pool = df[df["class"] == "real"]
    print("Real pool composition:", real_pool["source"].value_counts().to_dict())

    rows = []
    for feat in EVIDENCE_FEATURES:
        family = FAMILY_MAP[feat]
        for fsrc in FAKE_SOURCES:
            fake_df = df[(df["class"] == "fake") & (df["source"] == fsrc)]
            fvals_all = fake_df[feat].dropna()
            rvals_all = real_pool[feat].dropna()
            n_fake, n_real = len(fvals_all), len(rvals_all)

            if n_fake < 5 or n_real < 5:
                rows.append({
                    "evidence_feature": feat, "family": family, "fake_source": fsrc,
                    "n_fake": n_fake, "n_real": n_real, "effect_size": np.nan,
                    "auroc": np.nan, "auroc_ci_lower": np.nan, "auroc_ci_upper": np.nan,
                    "direction": "INCONCLUSIVE_N", "corr_with_v811_fake_prob": np.nan,
                    "corr_with_cam_faithfulness": np.nan, "n_matched_cam": 0,
                    "resolution_confound_corr_real": np.nan, "resolution_confound_corr_fake": np.nan,
                    "face_size_confound_corr_real": np.nan, "face_size_confound_corr_fake": np.nan,
                })
                continue

            d = cohens_d(rvals_all, fvals_all)  # positive = higher in fake
            au = auroc(rvals_all, fvals_all)
            lo, hi = bootstrap_auroc_ci(rvals_all, fvals_all)
            direction = "higher-in-fake" if d > 0 else ("higher-in-real" if d < 0 else "no-diff")

            corr_prob = spearman(fake_df[feat], fake_df["v811_fake_prob"])

            joined = fake_df.dropna(subset=["hot_drop_k20"])
            n_matched_cam = len(joined)
            corr_cam = spearman(joined[feat], joined["hot_drop_k20"]) if n_matched_cam >= 5 else np.nan

            res_corr_real = spearman(rvals_all, real_pool.loc[rvals_all.index, "orig_resolution"])
            res_corr_fake = spearman(fvals_all, fake_df.loc[fvals_all.index, "orig_resolution"])
            fs_corr_real = spearman(rvals_all, real_pool.loc[rvals_all.index, "face_size_confound"])
            fs_corr_fake = spearman(fvals_all, fake_df.loc[fvals_all.index, "face_size_confound"])

            rows.append({
                "evidence_feature": feat, "family": family, "fake_source": fsrc,
                "n_fake": n_fake, "n_real": n_real, "effect_size": d,
                "auroc": au, "auroc_ci_lower": lo, "auroc_ci_upper": hi,
                "direction": direction, "corr_with_v811_fake_prob": corr_prob,
                "corr_with_cam_faithfulness": corr_cam, "n_matched_cam": n_matched_cam,
                "resolution_confound_corr_real": res_corr_real, "resolution_confound_corr_fake": res_corr_fake,
                "face_size_confound_corr_real": fs_corr_real, "face_size_confound_corr_fake": fs_corr_fake,
            })

    metrics = pd.DataFrame(rows)

    # direction consistency: sign of effect_size same across ALL sources w/ valid data
    def dir_consistent(sub):
        d = sub["effect_size"].dropna()
        if len(d) < 2:
            return np.nan
        signs = np.sign(d[d != 0])
        if len(signs) == 0:
            return True
        return bool((signs == signs.iloc[0]).all())

    consist = metrics.groupby("evidence_feature").apply(dir_consistent).rename("direction_consistent_across_sources")
    metrics = metrics.merge(consist, on="evidence_feature", how="left")

    # ── between-source (cross-source) resolution confound ──
    # Within-class Spearman (resolution_confound_corr_real/fake above) is
    # structurally blind whenever a source has a single fixed native
    # resolution (df40/midjourney/stylegan2/celeba/lfw all do -- see
    # raw_features.csv orig_resolution nunique==1 for those sources), because
    # there is no within-source variance to correlate against. But sources
    # DO differ hugely from each other in native resolution (celeba
    # 178x218, lfw 250x250 vs df40_pixart/midjourney 1024x1024,
    # df40_sd21 512x512, others 256x256) -- an evidence feature that tracks
    # resolution could look like a real/fake signal purely because fake
    # sources here happen to be captured at systematically different native
    # resolution than the real sources. This computes, per feature, the
    # Spearman correlation between each source's MEDIAN feature value (across
    # all 11 real+fake sources) and that source's log(native resolution) --
    # a between-source confound diagnostic the per-source-pair table can't
    # see on its own.
    all_sources_df = df.copy()
    med = all_sources_df.groupby("source")[EVIDENCE_FEATURES + ["orig_resolution"]].median()
    med["log_res"] = np.log(med["orig_resolution"])
    between_source_confound = {}
    for feat in EVIDENCE_FEATURES:
        vals = med[feat].dropna()
        if len(vals) < 5:
            between_source_confound[feat] = np.nan
            continue
        rho, _ = sstats.spearmanr(med.loc[vals.index, "log_res"], vals)
        between_source_confound[feat] = float(rho)
    metrics["between_source_resolution_confound_spearman"] = metrics["evidence_feature"].map(between_source_confound)

    metrics.to_csv(OUT_DIR / "evidence_metrics_sourcewise.csv", index=False)
    print(f"wrote evidence_metrics_sourcewise.csv ({len(metrics)} rows)")

    # per-real-source breakdown (secondary table)
    real_rows = []
    for feat in EVIDENCE_FEATURES:
        for rsrc in REAL_SOURCES:
            vals = real_pool[real_pool["source"] == rsrc][feat].dropna()
            real_rows.append({"evidence_feature": feat, "real_source": rsrc, "n": len(vals),
                               "mean": float(vals.mean()) if len(vals) else np.nan,
                               "std": float(vals.std()) if len(vals) else np.nan})
    pd.DataFrame(real_rows).to_csv(OUT_DIR / "real_source_breakdown.csv", index=False)
    print("wrote real_source_breakdown.csv")

    # ── decision table ──
    AUROC_BAR = 0.60  # "clearly above chance" (or <=0.40 for higher-in-real direction)
    MIN_SOURCES_FOR_MOST = 5  # of 8 fake sources -> "most"
    RES_CONFOUND_BAR = 0.35  # |spearman| above this = "strongly resolution confounded"

    decision_rows = []
    for feat in EVIDENCE_FEATURES:
        sub = metrics[metrics["evidence_feature"] == feat].copy()
        family = FAMILY_MAP[feat]
        valid = sub[sub["direction"] != "INCONCLUSIVE_N"]
        n_valid_sources = len(valid)
        if n_valid_sources == 0:
            decision_rows.append({"evidence_feature": feat, "family": family,
                                   "decision": "INCONCLUSIVE",
                                   "reason": "No fake source had n>=5 usable (non-NaN) values for this feature."})
            continue

        consistent = bool(valid["direction_consistent_across_sources"].iloc[0]) if len(valid) else False
        # count of sources clearing the AUROC bar in the majority direction
        maj_dir = valid["direction"].mode().iloc[0] if not valid["direction"].mode().empty else None
        if maj_dir == "higher-in-fake":
            clears = valid[valid["auroc"] >= AUROC_BAR]
        elif maj_dir == "higher-in-real":
            clears = valid[valid["auroc"] <= (1 - AUROC_BAR)]
        else:
            clears = valid.iloc[0:0]
        n_clear = len(clears)

        # confound flag: within the sources that clear the bar, is resolution
        # confound correlation (|value|, real+fake combined magnitude) large?
        if n_clear > 0:
            res_conf_vals = pd.concat([clears["resolution_confound_corr_real"].abs(),
                                        clears["resolution_confound_corr_fake"].abs()]).dropna()
            strong_confound = bool((res_conf_vals >= RES_CONFOUND_BAR).mean() >= 0.5) if len(res_conf_vals) else False
        else:
            strong_confound = False
        between_src = between_source_confound.get(feat, np.nan)
        strong_between_confound = bool(not np.isnan(between_src) and abs(between_src) >= 0.5)

        if not consistent:
            decision = "REJECT"
            reason = (f"Effect direction (sign of Cohen's d) flips across fake sources "
                      f"(signs: {dict(zip(valid['fake_source'], np.sign(valid['effect_size'].round(4))))}). "
                      "Direction-inconsistent candidates are rejected per rubric regardless of AUROC magnitude.")
        elif n_clear >= MIN_SOURCES_FOR_MOST:
            if strong_confound or strong_between_confound:
                decision = "CONDITIONAL"
                reason_parts = [f"Direction-consistent AUROC>={AUROC_BAR} (or <=~{1-AUROC_BAR:.2f}) on {n_clear}/{n_valid_sources} "
                                 f"fake sources (>= {MIN_SOURCES_FOR_MOST} bar met), but"]
                if strong_confound:
                    reason_parts.append(f" within-source resolution/face-size confound correlation |rho|>={RES_CONFOUND_BAR} on >=50% of clearing sources;")
                if strong_between_confound:
                    reason_parts.append(f" between-source median-vs-log(resolution) confound |rho|={abs(between_src):.2f}>=0.5 "
                                          "(sources differ in native resolution and this feature tracks that difference across "
                                          "sources, not just within one) --")
                reason_parts.append(" downgraded from ACCEPT until confound is controlled (e.g. resolution-matched resampling).")
                reason = "".join(reason_parts)
            else:
                decision = "ACCEPT_FOR_NEXT_STAGE"
                reason = (f"Direction-consistent across all {n_valid_sources} sources with usable data; "
                          f"AUROC clears {AUROC_BAR} bar on {n_clear}/{n_valid_sources} fake sources (>= "
                          f"{MIN_SOURCES_FOR_MOST} required); no strong within-source or between-source "
                          f"resolution/face-size confound detected (between-source median-vs-log(resolution) "
                          f"rho={between_src:.2f}).")
        elif n_clear >= 1:
            decision = "CONDITIONAL"
            reason = (f"Direction-consistent but only clears AUROC bar on {n_clear}/{n_valid_sources} fake sources "
                      f"(< {MIN_SOURCES_FOR_MOST} required for ACCEPT) -- discriminates some generators/sources "
                      "but not most; source-specific fingerprint, not a general fake signal on current evidence.")
        else:
            decision = "REJECT"
            reason = (f"Direction-consistent but AUROC stays near chance (< {AUROC_BAR} / > {1-AUROC_BAR:.2f}) "
                      f"on all {n_valid_sources} sources with usable data.")

        if n_valid_sources < len(FAKE_SOURCES):
            reason += f" (Note: only {n_valid_sources}/{len(FAKE_SOURCES)} fake sources had n>=5 usable values.)"

        decision_rows.append({"evidence_feature": feat, "family": family, "decision": decision, "reason": reason})

    decision_df = pd.DataFrame(decision_rows)
    decision_df.to_csv(OUT_DIR / "evidence_candidate_decision_table.csv", index=False)
    print(f"wrote evidence_candidate_decision_table.csv ({len(decision_df)} rows)")
    print(decision_df[["evidence_feature", "decision"]].to_string(index=False))

    manifest_extra = {
        "rubric": {
            "auroc_bar": AUROC_BAR, "min_sources_for_most": MIN_SOURCES_FOR_MOST,
            "resolution_confound_bar": RES_CONFOUND_BAR, "n_boot": N_BOOT, "boot_seed": RNG_SEED,
        },
        "cam_faithfulness_join_n_matched": int(n_matched),
        "real_pool_sources": REAL_SOURCES, "fake_sources": FAKE_SOURCES,
    }
    manifest_path = OUT_DIR / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update(manifest_extra)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("updated run_manifest.json")


if __name__ == "__main__":
    main()
