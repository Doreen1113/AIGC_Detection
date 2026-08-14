"""
P1-R1.5 -- bugfix patch: resolution_manifest.csv was missing rows for the
"native" resolution condition's FILTERED images (only native clean rows were
recorded; the filtered native images already exist in v815_replication_set/
from P1-R1's source data and just need to be referenced, not regenerated).
This script adds those rows and rewrites resolution_manifest.csv (a file
created fresh by this round -- not a prior round's result file, so updating
it here is not an "overwrite an existing result" violation).

No image file is created, moved, or modified -- this only adds manifest rows
pointing at the already-existing v815_replication_set/*.jpg files.

python p1_r1_5_fix_native_filtered_rows.py
"""
import hashlib
from pathlib import Path
import pandas as pd

BASE = Path(r"C:\My_Project\AIGC")
OUT_DIR = BASE / "results" / "research" / "p1_r1_5_resolution_causal_audit_20260814"
REPLICATION_TSV = BASE / "splits" / "v815_replication_set.tsv"


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    rows = []
    for line in REPLICATION_TSV.read_text(encoding="utf-8").splitlines():
        if line.startswith("id\t") or not line.strip():
            continue
        parts = line.split("\t")
        rows.append(dict(id=parts[0], path=parts[1], ftype=parts[4],
                          source=parts[5], source_stem=parts[7]))

    clean_by_key = {(r["source"], r["source_stem"]): r for r in rows if r["ftype"] == "none"}
    filtered_rows = [r for r in rows if r["ftype"] != "none"]

    man = pd.read_csv(OUT_DIR / "resolution_manifest.csv")
    print(f"Existing manifest rows: {len(man)}")

    new_rows = []
    for r in filtered_rows:
        key = (r["source"], r["source_stem"])
        clean_r = clean_by_key.get(key)
        base_id = clean_r["id"] if clean_r else ""
        p = Path(r["path"])
        if not p.is_file():
            new_rows.append({
                "base_id": base_id, "source": r["source"], "source_stem": r["source_stem"],
                "resolution_condition": "native", "filter_type": r["ftype"],
                "status": "MISSING_BASE_FILE", "note": f"native filtered file not found: {p}",
            })
            continue
        sha = sha256_of_file(p)
        # native resolution == whatever the original replication-set image's
        # resolution is; read it to record accurately
        try:
            from PIL import Image
            with Image.open(p) as im:
                w, h = im.size
        except Exception:
            w, h = None, None
        new_rows.append({
            "base_id": base_id, "source": r["source"], "source_stem": r["source_stem"],
            "resolution_condition": "native", "filter_type": r["ftype"],
            "base_image_sha256": sha, "base_resolution": f"{w}x{h}" if w else "",
            "resized_resolution": f"{w}x{h}" if w else "",
            "resize_method": "N/A (reused existing v815_replication_set file, not regenerated)",
            "face_bbox": "", "final_model_input_shape": "224x224 (pipeline.py transform_infer, applied uniformly at inference)",
            "filter_params": "{} (original v815_replication_set generation parameters, not re-derived)",
            "jpeg_policy": "N/A at storage time (original file format); pipeline.py's preprocess_jpeg(quality=85) applied uniformly at inference time",
            "output_path": str(p), "output_sha256": sha,
            "status": "OK_REUSED_EXISTING",
        })

    new_df = pd.DataFrame(new_rows)
    combined = pd.concat([man, new_df], ignore_index=True)
    combined.to_csv(OUT_DIR / "resolution_manifest.csv", index=False)
    print(f"Added {len(new_df)} native-filtered rows. New total: {len(combined)}")


if __name__ == "__main__":
    main()
