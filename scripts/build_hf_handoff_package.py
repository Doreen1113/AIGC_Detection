"""
Hugging Face handoff package planner -- READ-ONLY / STAGING-ONLY by default.

This script never touches git, never requires network access to run in its
default ("dry") mode, and never requires a Hugging Face token to produce a
plan. It reads the B and C handoff manifest CSVs
(manifests/team_data/B_phase2_xai_handoff_manifest_template.csv,
manifests/team_data/C_android_benchmark_handoff_manifest_template.csv),
checks what actually exists on disk, classifies each row as
upload-ready / license-blocked / size-flagged / missing, and writes a JSON
plan per member. It does NOT copy, move, or upload anything in dry mode.

Safety lesson this script is built around (2026-08-14 incident): a broad
`git add results/research/` once accidentally staged a 998MB directory of
derived per-image data (resolution_controlled_images/) before it was caught
in pre-commit review. This script never assumes a manifest row is small --
every row is sized before being marked upload-ready, and anything large is
routed to manual review instead of being silently included.

Size thresholds (manual-review flags, not hard blocks -- a human still
decides):
  - a single file > 100 MB
  - a directory-type manifest entry (aggregate) > 500 MB

License clearance rule (derived from what actually appears in the CSVs'
license_status column, not invented): a row is "cleared" only if its
license_status begins with "internal (project-owned)" or
"internal (project-generated" (this also matches the
"internal (project-generated manifest; ...)" variant used for one row).
Every other observed value -- anything starting with "third-party", "mixed",
or containing "NOT license-audited" / "not audited" / "not separately
audited" -- is treated as blocked. Rows whose license_status is about a
not-yet-existing file (e.g. "internal (would be project-generated)" for the
still-missing golden-predictions file) are handled by the existence check
first (they surface as MISSING, not as cleared-but-absent).

USAGE (dry mode, the only mode this session runs):
    python scripts/build_hf_handoff_package.py --member B
    python scripts/build_hf_handoff_package.py --member C
    python scripts/build_hf_handoff_package.py --member B --member C   (both)

USAGE (upload mode -- NOT run this session, no HF token available here):
    python scripts/build_hf_handoff_package.py --member B --upload
  This requires `huggingface_hub` to be installed AND an HF_TOKEN (or
  HUGGING_FACE_HUB_TOKEN) environment variable to be set. If either is
  missing, --upload refuses to run rather than silently falling back to dry
  mode or guessing credentials.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone

BASE = Path(r"C:\My_Project\AIGC")
MANIFEST_DIR = BASE / "manifests" / "team_data"
OUT_DIR = BASE / "results" / "team" / "hf_handoff_dry_run_20260815"

MANIFESTS = {
    "B": {
        "csv": MANIFEST_DIR / "B_phase2_xai_handoff_manifest_template.csv",
        "hf_repo_name": "aigc-team/phase2-xai-handoff-b (PROPOSED, not created)",
    },
    "C": {
        "csv": MANIFEST_DIR / "C_android_benchmark_handoff_manifest_template.csv",
        "hf_repo_name": "aigc-team/android-benchmark-handoff-c (PROPOSED, not created)",
    },
}

SINGLE_FILE_REVIEW_BYTES = 100 * 1024 * 1024   # 100 MB
DIRECTORY_REVIEW_BYTES = 500 * 1024 * 1024     # 500 MB

CLEARED_PREFIXES = ("internal (project-owned)", "internal (project-generated")


def sha256_of_file(path, chunk_size=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_asset_path(relative_path):
    if relative_path.startswith("<") or relative_path.startswith("FFHQ_ali_process/EyeEnlarging_30/ (representative"):
        return None, True
    return BASE / relative_path, False


def is_cleared(license_status):
    return license_status.strip().startswith(CLEARED_PREFIXES)


def classify_row(row):
    rel = row["relative_path"]
    required = row.get("required", "").strip().lower() == "yes"
    license_status = row.get("license_status", "")
    source = row.get("source", "")

    path, is_placeholder = resolve_asset_path(rel)

    entry = {
        "relative_path": rel,
        "required": required,
        "license_status": license_status,
        "asset_type": row.get("asset_type", ""),
    }

    if is_placeholder or "NOT YET GENERATED" in source or "MISSING" in row.get("distribution_status", ""):
        entry["status"] = "MISSING"
        entry["reason"] = "Asset does not exist yet (not a single resolvable path, or explicitly marked not-yet-generated)."
        return "missing", entry

    if not path.exists():
        entry["status"] = "MISSING"
        entry["reason"] = f"Path does not exist on disk: {path}"
        return "missing", entry

    cleared = is_cleared(license_status)

    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
        size = sum(p.stat().st_size for p in files)
        entry["size_bytes"] = size
        entry["size_mb"] = round(size / (1024 * 1024), 2)
        entry["file_count"] = len(files)
        entry["sha256"] = None
        entry["note"] = "Directory asset -- not hashed as a single file."
        size_flag = size > DIRECTORY_REVIEW_BYTES
    else:
        size = path.stat().st_size
        entry["size_bytes"] = size
        entry["size_mb"] = round(size / (1024 * 1024), 2)
        entry["file_count"] = 1
        entry["sha256"] = sha256_of_file(path)
        size_flag = size > SINGLE_FILE_REVIEW_BYTES

    if not cleared:
        entry["status"] = "LICENSE_BLOCKED"
        entry["reason"] = f"license_status does not start with a cleared prefix: '{license_status}'"
        return "license_blocked", entry

    if size_flag:
        entry["status"] = "SIZE_FLAGGED_FOR_MANUAL_REVIEW"
        threshold = "500MB (directory aggregate)" if path.is_dir() else "100MB (single file)"
        entry["reason"] = f"Exceeds the {threshold} manual-review threshold -- NOT auto-included even though license-cleared."
        return "size_flagged", entry

    entry["status"] = "CLEARED_FOR_UPLOAD"
    entry["reason"] = "License-cleared (self-generated or project-owned) and under size thresholds."
    return "cleared", entry


def build_plan(member):
    cfg = MANIFESTS[member]
    csv_path = cfg["csv"]
    if not csv_path.exists():
        print(f"ERROR: manifest not found for {member}: {csv_path}")
        return None

    with open(csv_path, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    buckets = {"cleared": [], "license_blocked": [], "size_flagged": [], "missing": []}
    for row in rows:
        bucket, entry = classify_row(row)
        buckets[bucket].append(entry)

    cleared_bytes = sum(e.get("size_bytes", 0) for e in buckets["cleared"])
    blocked_or_flagged_bytes = sum(e.get("size_bytes", 0) for e in buckets["license_blocked"] + buckets["size_flagged"])

    plan = {
        "member": member,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "DRY_RUN -- nothing uploaded, no network access used, no HF token required",
        "manifest_source": str(csv_path),
        "proposed_hf_repo": cfg["hf_repo_name"],
        "note": "Repo name is a PROPOSAL only. No Hugging Face repo was created or contacted this run.",
        "summary": {
            "total_manifest_rows": len(rows),
            "cleared_for_upload_count": len(buckets["cleared"]),
            "cleared_for_upload_mb": round(cleared_bytes / (1024 * 1024), 2),
            "license_blocked_count": len(buckets["license_blocked"]),
            "size_flagged_count": len(buckets["size_flagged"]),
            "size_flagged_or_blocked_mb": round(blocked_or_flagged_bytes / (1024 * 1024), 2),
            "missing_count": len(buckets["missing"]),
        },
        "cleared_for_upload": buckets["cleared"],
        "excluded_license_blocked": buckets["license_blocked"],
        "excluded_size_flagged_manual_review": buckets["size_flagged"],
        "missing_not_yet_available": buckets["missing"],
    }
    return plan


def do_upload(member, plan):
    """Real upload path -- NOT exercised this session. Requires huggingface_hub
    installed and HF_TOKEN/HUGGING_FACE_HUB_TOKEN set. Refuses otherwise."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not token:
        print(f"[{member}] --upload requested but no HF_TOKEN/HUGGING_FACE_HUB_TOKEN "
              f"environment variable is set. Refusing to proceed -- will NOT silently "
              f"fall back to dry mode or prompt for credentials.")
        return False
    try:
        import huggingface_hub  # noqa: F401
    except ImportError:
        print(f"[{member}] --upload requested but the `huggingface_hub` package is not "
              f"installed. Refusing to proceed. Install with: pip install huggingface_hub")
        return False

    print(f"[{member}] Token and huggingface_hub both present -- but this script does not "
          f"perform the actual upload calls in this delivered version. Implementing the "
          f"real upload_file()/create_repo() calls against {plan['proposed_hf_repo']} is "
          f"intentionally left as a follow-up once the repo name and structure in "
          f"docs/team/HF_HANDOFF_PLAN.md are confirmed by the team -- this placeholder "
          f"exists so --upload's preconditions (token, library) are checked and reported "
          f"clearly rather than the flag silently doing nothing.")
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--member", action="append", choices=["B", "C"], required=True,
                         help="Which member's manifest to plan. May be given twice for both.")
    parser.add_argument("--upload", action="store_true",
                         help="Attempt a real upload (requires HF_TOKEN + huggingface_hub). "
                              "NOT exercised in this session.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for member in args.member:
        plan = build_plan(member)
        if plan is None:
            continue
        out_path = OUT_DIR / f"hf_handoff_plan_{member}.json"
        out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        s = plan["summary"]
        print(f"[{member}] cleared={s['cleared_for_upload_count']} ({s['cleared_for_upload_mb']} MB)  "
              f"license_blocked={s['license_blocked_count']}  size_flagged={s['size_flagged_count']}  "
              f"missing={s['missing_count']}")
        print(f"[{member}] wrote -> {out_path}")

        if args.upload:
            do_upload(member, plan)


if __name__ == "__main__":
    main()
