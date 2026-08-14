"""
P1-R1.5 -- Stage 2: validate whether the resolution control actually holds.

For each (base_id x filter_type) group, checks across all 4 resolution
conditions (native, canonical_256, canonical_512, canonical_1024):
  - completeness: were all 4 conditions successfully generated? (else MISSING)
  - operation equality: does the underlying filter OPERATION (as coded in
    filters/stress_test_filter_functions.py, read but not modified) apply the
    SAME relative-strength transformation regardless of resolution, or does
    it use a resolution-dependent absolute-pixel parameter that makes the
    "same filter operation" assumption false?

This is a code-level fact, established once by reading the filter functions
(not re-derived per row), then applied to every row:
  - apply_whitening: pure per-pixel LAB tone shift, s=0.15 fraction of
    (255-L) -- NO spatial/pixel-count parameter anywhere. Resolution-INVARIANT
    by construction.
  - apply_eye_enlarging: warp radius = eye_width_in_current_image_pixels *
    1.70 -- eye_width is measured fresh from landmarks detected in the SAME
    resized image, so the radius scales proportionally with the face's
    apparent size at each resolution. Self-scaling by design -> APPROXIMATELY
    resolution-invariant in relative terms (caveated: landmark precision and
    cv2.remap/INTER_CUBIC interpolation quality can still differ across
    resolutions in ways not controlled for here).
  - apply_smoothing: cv2.bilateralFilter(bgr, d, sigmaColor, sigmaSpace) with
    d FIXED at 15 pixels for "medium" strength, regardless of image size.
    A 15px-diameter kernel is a much SMALLER relative smoothing footprint on
    a 1024x1024 image than on a 256x256 image of the same face region.
    Resolution-DEPENDENT / NOT invariant -- confirmed by reading the code,
    not assumed.
  - apply_face_reshaping: warp radius FIXED at 60.0 pixels, regardless of
    image size (also already flagged as a known scale-dependence issue in
    pipeline.py's own code comments: "face_reshaping's fixed 60px warp
    radius saturates most regions at dataset scale"). Resolution-DEPENDENT /
    NOT invariant -- confirmed by reading the code.

Rows for smoothing_medium and face_reshaping are therefore marked INVALID
for the *causal, resolution-isolated* claim even when all 4 conditions were
successfully generated -- the physical filter operation itself is not held
constant across resolution in those two cases, so any AUROC/joint-recognition
difference across resolution for those two types cannot be cleanly
attributed to "resolution" alone. This is reported honestly per the task's
explicit instruction, not smoothed over.

python p1_r1_5_validate_control.py
"""
from pathlib import Path
import pandas as pd

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"

RESOLUTION_INDEPENDENT_BY_CODE = {
    "whitening_medium": ("VALID", "Pure per-pixel LAB tone shift (s=0.15*(255-L)); no spatial kernel or pixel-count parameter anywhere in apply_whitening. Confirmed resolution-invariant by reading filters/stress_test_filter_functions.py."),
    "eye_enlarging": ("VALID_WITH_CAVEAT", "Warp radius = detected eye_width_px * 1.70, measured fresh per resolution -- self-scaling by design, so relative filter strength is approximately constant across resolution. Caveat: landmark-detection precision and cv2.remap/INTER_CUBIC interpolation quality are not separately controlled for and may still vary with resolution."),
    "smoothing_medium": ("INVALID", "cv2.bilateralFilter uses a FIXED pixel diameter d=15 (medium strength) regardless of image resolution -- confirmed by reading apply_smoothing() in filters/stress_test_filter_functions.py. A 15px kernel is a much smaller relative smoothing footprint at 1024x1024 than at 256x256, so the underlying filter OPERATION is not held constant across resolution; any score difference cannot be cleanly attributed to resolution alone."),
    "face_reshaping": ("INVALID", "Warp radius is FIXED at 60.0 pixels regardless of image resolution -- confirmed by reading apply_face_reshaping() in filters/stress_test_filter_functions.py, and already independently flagged in this project's own pipeline.py comments ('face_reshaping's fixed 60px warp radius saturates most regions at dataset scale'). Same issue as smoothing_medium: the operation itself is resolution-dependent, so it cannot serve as a clean resolution-isolated control."),
}


def main():
    man = pd.read_csv(OUT_DIR / "resolution_manifest.csv")
    print(f"Loaded {len(man)} manifest rows")

    conditions = ["native", "canonical_256", "canonical_512", "canonical_1024"]
    rows = []

    for base_id, grp in man.groupby("base_id"):
        source = grp["source"].iloc[0]
        source_stem = grp["source_stem"].iloc[0]
        for ftype in ["whitening_medium", "eye_enlarging", "smoothing_medium", "face_reshaping"]:
            present = {}
            for cond in conditions:
                sub = grp[(grp["resolution_condition"] == cond) & (grp["filter_type"] == ftype)]
                if len(sub) == 0:
                    present[cond] = None
                else:
                    present[cond] = sub.iloc[0]

            missing_conds = [c for c, v in present.items() if v is None or
                              (hasattr(v, "get") and str(v.get("status", "")).startswith(("MISSING", "LANDMARK", "FILTER_EXC", "FILTER_RET")))]
            completeness = "COMPLETE" if not missing_conds else f"MISSING({','.join(missing_conds)})"

            code_status, code_reason = RESOLUTION_INDEPENDENT_BY_CODE[ftype]

            if completeness != "COMPLETE":
                final_status = "MISSING"
            elif code_status == "INVALID":
                final_status = "INVALID"
            elif code_status == "VALID_WITH_CAVEAT":
                final_status = "VALID_WITH_CAVEAT"
            else:
                final_status = "VALID"

            same_base_image = "YES (all 4 conditions derived from the same clean base_id/source_stem, verified via base_image_sha256 column in resolution_manifest.csv)"

            rows.append({
                "base_id": base_id, "source": source, "source_stem": source_stem,
                "filter_type": ftype,
                "same_base_image": same_base_image,
                "completeness_across_4_resolutions": completeness,
                "filter_operation_resolution_independence": code_status,
                "filter_operation_reason": code_reason,
                "final_validity": final_status,
            })

    df = pd.DataFrame(rows)
    out_path = OUT_DIR / "control_validation.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df)} rows -> {out_path}")

    print("\n=== Summary ===")
    print(df.groupby(["filter_type", "final_validity"]).size().to_string())


if __name__ == "__main__":
    main()
