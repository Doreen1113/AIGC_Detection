"""
P1-R1 -- aggregate per_image_paired_effect_raw.csv (produced by
p1_r1_paired_effect_stats.py) into paired_effect_statistics.csv, one row per
(source x filter_type). New, read-only script.

python p1_r1_aggregate_paired_stats.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_cross_source_failure_anatomy_20260814"

def main():
    df = pd.read_csv(OUT_DIR / "per_image_paired_effect_raw.csv")
    print(f"Loaded {len(df)} paired rows")

    rows = []
    for (source, ftype), grp in df.groupby(["source", "ftype"]):
        rows.append({
            "source": source, "filter_type": ftype, "n_pairs": len(grp),
            "lab_deltaE_mean_of_means": float(grp["lab_deltaE_mean"].mean()),
            "lab_deltaE_median_of_means": float(grp["lab_deltaE_mean"].median()),
            "lab_deltaE_std": float(grp["lab_deltaE_mean"].std()),
            "changed_pixel_proportion_mean": float(grp["changed_pixel_proportion"].mean()),
            "changed_pixel_proportion_median": float(grp["changed_pixel_proportion"].median()),
            "face_region_coverage_mean": float(grp["face_region_coverage_of_changed_pixels"].mean(skipna=True)),
            "face_region_coverage_median": float(grp["face_region_coverage_of_changed_pixels"].median(skipna=True)),
            "eye_region_coverage_mean": float(grp["eye_region_coverage_of_changed_pixels"].mean(skipna=True)),
            "eye_region_coverage_median": float(grp["eye_region_coverage_of_changed_pixels"].median(skipna=True)),
            "fft_logmag_diff_absmean_mean": float(grp["fft_logmag_diff_absmean"].mean()),
            "fft_logmag_diff_absmean_median": float(grp["fft_logmag_diff_absmean"].median()),
            "fft_logmag_diff_std_mean": float(grp["fft_logmag_diff_std"].mean()),
            "image_width_mean": float(grp["image_width"].mean()),
            "image_height_mean": float(grp["image_height"].mean()),
            "face_bbox_area_frac_mean": float(grp["face_bbox_area_frac"].mean()),
            "face_bbox_area_frac_median": float(grp["face_bbox_area_frac"].median()),
        })

    out_df = pd.DataFrame(rows).sort_values(["source", "filter_type"])
    out_path = OUT_DIR / "paired_effect_statistics.csv"
    out_df.to_csv(out_path, index=False)
    print(f"Wrote {len(out_df)} rows -> {out_path}")

    # also a filter-type-only rollup (across all sources) for quick reading
    rows2 = []
    for ftype, grp in df.groupby("ftype"):
        rows2.append({
            "filter_type": ftype, "n_pairs": len(grp),
            "lab_deltaE_mean_of_means": float(grp["lab_deltaE_mean"].mean()),
            "changed_pixel_proportion_mean": float(grp["changed_pixel_proportion"].mean()),
            "face_region_coverage_mean": float(grp["face_region_coverage_of_changed_pixels"].mean(skipna=True)),
            "eye_region_coverage_mean": float(grp["eye_region_coverage_of_changed_pixels"].mean(skipna=True)),
            "fft_logmag_diff_absmean_mean": float(grp["fft_logmag_diff_absmean"].mean()),
        })
    rollup_path = OUT_DIR / "paired_effect_statistics_by_filtertype_rollup.csv"
    pd.DataFrame(rows2).sort_values("filter_type").to_csv(rollup_path, index=False)
    print(f"Wrote rollup -> {rollup_path}")


if __name__ == "__main__":
    main()
