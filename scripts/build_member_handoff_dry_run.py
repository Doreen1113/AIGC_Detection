"""
Member B / Member C minimal handoff package -- DRY RUN ONLY.

This script NEVER copies, moves, or uploads any file. It reads the manifest
templates under manifests/team_data/, checks whether each `required=yes`
asset actually exists on disk, computes SHA256 for assets that exist (files
only -- directories are reported as file-count + total-size, not a single
hash), and writes a JSON report per member. It also explicitly scans for a
fixed list of items that must NEVER appear in a handoff package (raw dataset
directories, full training sets, .env files, tokens/API keys, any v8.12-v8.16
checkpoint, the DF40-cdf replication set) and flags them if found referenced
anywhere in the manifests, even though none of the current manifest rows are
expected to trigger these flags.

Windows-safe: uses pathlib throughout, no POSIX-only assumptions, no network
access (hashing is local-file-only).

Location note: placed under scripts/ rather than the project root, since this
is a team-process/tooling script, not a research script -- the rest of this
project's convention (per docs/ROOT_FILE_MANIFEST.csv) keeps ad hoc research
scripts at repo root; this is a deliberate, noted exception for durable team
tooling.

python scripts/build_member_handoff_dry_run.py
"""
import csv
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\My_Project\AIGC")
MANIFEST_DIR = BASE / "manifests" / "team_data"
OUT_DIR = BASE / "manifests" / "team_data"

MANIFESTS = {
    "B": MANIFEST_DIR / "B_phase2_xai_handoff_manifest_template.csv",
    "C": MANIFEST_DIR / "C_ios_benchmark_handoff_manifest_template.csv",
}

# Fixed forbidden-item patterns -- never allowed in a handoff package,
# regardless of which member. Checked against every manifest row's
# relative_path (case-insensitive substring match) plus a full scan is NOT
# performed (this is a dry-run over manifest CONTENTS, not a filesystem
# crawl) -- the intent is to catch an accidental manifest entry, not to audit
# the whole repo.
FORBIDDEN_PATTERNS = [
    "aiguard/real", "aiguard/fake",  # raw/full training set directories
    "filter_data/eye_enlarging", "filter_data/whitening", "filter_data/smoothing",
    "filter_data/face_reshaping",  # full self-built training folders (as opposed to small XAI samples)
    ".env", "token", "api_key", "apikey", "secret",
    "v815ablation", "v815a", "v815b", "v816", "v812", "v813", "v814",  # v8.12-v8.16 research checkpoints
    "v815_replication_set",  # the DF40-cdf replication set, splits/*.tsv or the image directory
]

# Checkpoints that are legitimately v8.11 production and must NOT be flagged
# even though some forbidden substrings could false-positive against them.
PRODUCTION_ALLOWLIST = {
    "shufflenet_v2_layer1_v811d.pth",
    "shufflenet_v2_layer2_v811.pth",
    "artifact_classifier_v3.pth",
    "face_landmarker.task",
}


def sha256_of_file(path, chunk_size=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_asset_path(relative_path):
    """Manifest rows sometimes contain a real relative path, sometimes a
    descriptive placeholder (e.g. '<golden prediction output, ...>' or
    '<40 images listed in ...>') for an asset that isn't a single fixed path.
    Returns (Path or None, is_placeholder: bool)."""
    if relative_path.startswith("<") or relative_path.startswith("FFHQ_ali_process/EyeEnlarging_30/ (representative"):
        return None, True
    return BASE / relative_path, False


def check_forbidden(relative_path):
    lower = relative_path.lower()
    fname = Path(relative_path).name.lower()
    if fname in {p.lower() for p in PRODUCTION_ALLOWLIST}:
        return []
    hits = [pat for pat in FORBIDDEN_PATTERNS if pat in lower]
    return hits


def process_manifest(member, manifest_path):
    rows = []
    with open(manifest_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    results = []
    total_files = 0
    total_bytes = 0
    missing_required = []
    forbidden_flags = []

    for row in rows:
        rel = row["relative_path"]
        required = row.get("required", "").strip().lower() == "yes"

        forbidden_hits = check_forbidden(rel)
        if forbidden_hits:
            forbidden_flags.append({"relative_path": rel, "matched_patterns": forbidden_hits})

        path, is_placeholder = resolve_asset_path(rel)

        if is_placeholder:
            results.append({
                "relative_path": rel, "required": required, "status": "PLACEHOLDER_NOT_A_SINGLE_PATH",
                "note": "Manifest row describes a not-yet-materialized or multi-file asset; not independently checkable by path existence.",
                "sha256": None, "size_bytes": None, "file_count": None,
            })
            if required:
                missing_required.append(rel)
            continue

        if not path.exists():
            results.append({
                "relative_path": rel, "required": required, "status": "MISSING",
                "sha256": None, "size_bytes": None, "file_count": None,
            })
            if required:
                missing_required.append(rel)
            continue

        if path.is_dir():
            files = [p for p in path.rglob("*") if p.is_file()]
            size = sum(p.stat().st_size for p in files)
            total_files += len(files)
            total_bytes += size
            results.append({
                "relative_path": rel, "required": required, "status": "FOUND_DIRECTORY",
                "sha256": None, "size_bytes": size, "file_count": len(files),
                "note": "Directory asset -- not hashed as a single file; file_count/size_bytes are aggregate.",
            })
        else:
            size = path.stat().st_size
            sha = sha256_of_file(path)
            total_files += 1
            total_bytes += size
            results.append({
                "relative_path": rel, "required": required, "status": "FOUND_FILE",
                "sha256": sha, "size_bytes": size, "file_count": 1,
            })

    report = {
        "member": member,
        "manifest_source": str(manifest_path),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "dry_run": True,
        "note": "No file was copied, moved, or uploaded to produce this report. Existence/hash checks only.",
        "summary": {
            "total_manifest_rows": len(rows),
            "total_files_found": total_files,
            "total_bytes_found": total_bytes,
            "total_mb_found": round(total_bytes / (1024 * 1024), 2),
            "missing_required_count": len(missing_required),
            "missing_required_assets": missing_required,
            "forbidden_pattern_flags": forbidden_flags,
        },
        "assets": results,
    }
    return report


def main():
    for member, manifest_path in MANIFESTS.items():
        if not manifest_path.exists():
            print(f"ERROR: manifest not found for {member}: {manifest_path}")
            continue
        report = process_manifest(member, manifest_path)
        out_path = OUT_DIR / f"{member}_handoff_dry_run_report.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        s = report["summary"]
        print(f"[{member}] rows={s['total_manifest_rows']} files_found={s['total_files_found']} "
              f"size={s['total_mb_found']}MB missing_required={s['missing_required_count']} "
              f"forbidden_flags={len(s['forbidden_pattern_flags'])}")
        print(f"[{member}] wrote -> {out_path}")


if __name__ == "__main__":
    main()
