"""
Filter OOD eval for v8.11 (Layer1c + Layer2): FFHQ_ali_process (Alibaba
retouching API), held out entirely from training since v8.6.

Verified 2026-08-02 (identity overlap check): Megvii training data spans
FFHQ base-image indices 60002-69999; Alibaba eval data spans indices
17000-19999 -- disjoint ranges (RetouchingFFHQ partitions the 70K FFHQ pool
into non-overlapping index blocks per company), so this IS a genuine
cross-identity, cross-algorithm OOD test, not an identity shortcut (unlike
the StyleGAN3 case where identity overlap required the "unseen-algorithm,
seen-identity" caveat).

Uses pipeline.py's hierarchical_predict() and preprocess_jpeg() directly, so
preprocessing is guaranteed consistent with the current v8.11 pipeline (not
a stale/divergent eval script -- the exact concern raised before citing this
number).

python AIGuard/eval_ali_ood_v811.py [layer1_weights] [layer2_weights]
"""
import argparse, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import torch
from PIL import Image

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))
import pipeline as pl

# ── P0 Production Evaluation Integrity Repair (2026-08-13) ──────────────────
# Previously defaulted L1_WEIGHTS to the SUPERSEDED shufflenet_v2_layer1_v811c.pth
# when invoked with no arguments -- this is exactly how results/ali_ood_v811_output.txt
# ended up being a stale Layer1c (97.8%) run instead of v8.11d evidence. Fail-closed
# now: explicit --layer1-weights / --layer2-weights are required, no default.
def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _git_commit():
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(BASE),
                              capture_output=True, text=True, timeout=10)
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _weight_tag(path):
    s = Path(path).stem
    for pre in ("shufflenet_v2_layer1_", "shufflenet_v2_layer2_", "shufflenet_v2_"):
        if s.startswith(pre):
            return s[len(pre):]
    return s


_parser = argparse.ArgumentParser(description=__doc__)
_parser.add_argument("--layer1-weights", default=None, help="Path to Layer1 checkpoint (.pth). Required -- no default.")
_parser.add_argument("--layer2-weights", default=None, help="Path to Layer2 checkpoint (.pth). Required -- no default.")
_args = _parser.parse_args()

if not _args.layer1_weights or not _args.layer2_weights:
    print("ERROR: --layer1-weights and --layer2-weights are required. Refusing to fall back to a default checkpoint.")
    sys.exit(1)

L1_WEIGHTS = _args.layer1_weights
L2_WEIGHTS = _args.layer2_weights

if not Path(L1_WEIGHTS).is_file():
    print(f"ERROR: Layer1 weights not found: {L1_WEIGHTS}")
    sys.exit(1)
if not Path(L2_WEIGHTS).is_file():
    print(f"ERROR: Layer2 weights not found: {L2_WEIGHTS}")
    sys.exit(1)

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_SHA256 = _sha256(SCRIPT_PATH)
L1_SHA256 = _sha256(L1_WEIGHTS)
L2_SHA256 = _sha256(L2_WEIGHTS)
GIT_COMMIT = _git_commit()
RUN_TIMESTAMP = datetime.now(timezone.utc).isoformat()
RUN_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
COMMAND_LINE = " ".join(sys.argv)
RELEASE_DIR = BASE / "results" / "releases" / "v8.11_production_20260813"
RELEASE_DIR.mkdir(parents=True, exist_ok=True)

PROVENANCE = {
    "layer1_weights_path": str(Path(L1_WEIGHTS).resolve()),
    "layer1_weights_sha256": L1_SHA256,
    "layer2_weights_path": str(Path(L2_WEIGHTS).resolve()),
    "layer2_weights_sha256": L2_SHA256,
    "script_path": str(SCRIPT_PATH),
    "script_sha256": SCRIPT_SHA256,
    "git_commit": GIT_COMMIT,
    "command_line": COMMAND_LINE,
    "timestamp_utc": RUN_TIMESTAMP,
}


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    l1 = pl.DualBranchModel(num_classes=2).to(device)
    l1.load_state_dict(torch.load(L1_WEIGHTS, map_location=device))
    l1.eval()
    l2 = pl.DualBranchModel(num_classes=2).to(device)
    l2.load_state_dict(torch.load(L2_WEIGHTS, map_location=device))
    l2.eval()
    print(f"Layer1: {L1_WEIGHTS}")
    print(f"Layer1 SHA256: {L1_SHA256}")
    print(f"Layer2: {L2_WEIGHTS}")
    print(f"Layer2 SHA256: {L2_SHA256}")
    print(f"Script: {SCRIPT_PATH}")
    print(f"Script SHA256: {SCRIPT_SHA256}")
    print(f"Git commit: {GIT_COMMIT}")
    print(f"Timestamp (UTC): {RUN_TIMESTAMP}")
    print(f"Command: {COMMAND_LINE}")
    print(f"Device: {device}")

    rows = [l for l in (BASE / "splits" / "ood_filter_ali.txt").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("path\t")]
    print(f"Alibaba OOD filter images: {len(rows)}")

    correct_type = defaultdict(int)
    total_type = defaultdict(int)
    correct_int = defaultdict(int)
    total_int = defaultdict(int)
    all_correct = 0

    for i, line in enumerate(rows, 1):
        path = line.split("\t")[0]
        p = Path(path)
        combo = p.parent.parent.name  # e.g. "Whitening_90"
        ftype, intensity = combo.rsplit("_", 1)

        try:
            pil = Image.open(path).convert("RGB")
            pil = pl.preprocess_jpeg(pil, quality=85)
            t = pl.transform_infer(pil).unsqueeze(0).to(device)
            hp = pl.hierarchical_predict(t, l1, l2)
            pred = hp["prediction"]
        except Exception:
            continue

        total_type[ftype] += 1
        total_int[intensity] += 1
        if pred == "filter":
            correct_type[ftype] += 1
            correct_int[intensity] += 1
            all_correct += 1

        if i % 3000 == 0:
            print(f"  {i}/{len(rows)} done ...")

    print(f"\n{'='*55}")
    print(f"  Filter OOD -- Alibaba (FFHQ_ali_process), v8.11")
    print(f"{'='*55}")
    print(f"  Overall recall: {all_correct}/{len(rows)} = {all_correct/len(rows)*100:.1f}%")

    print("\n  By filter type:")
    for ftype in sorted(total_type):
        c, t = correct_type[ftype], total_type[ftype]
        print(f"    {ftype:<15s}: {c:5d}/{t:5d} = {c/t*100:.1f}%")

    print("\n  By intensity:")
    for intensity in sorted(total_int):
        c, t = correct_int[intensity], total_int[intensity]
        print(f"    {intensity:<15s}: {c:5d}/{t:5d} = {c/t*100:.1f}%")

    # ── save (P0 Production Evaluation Integrity Repair, 2026-08-13) ───────
    out_record = {
        "provenance": PROVENANCE,
        "eval_name": "alibaba_filter_ood",
        "overall": {
            "correct": all_correct,
            "total": len(rows),
            "recall_pct": all_correct / len(rows) * 100,
        },
        "by_filter_type": {
            ftype: {"correct": correct_type[ftype], "total": total_type[ftype],
                    "recall_pct": correct_type[ftype] / total_type[ftype] * 100}
            for ftype in sorted(total_type)
        },
        "by_intensity": {
            intensity: {"correct": correct_int[intensity], "total": total_int[intensity],
                        "recall_pct": correct_int[intensity] / total_int[intensity] * 100}
            for intensity in sorted(total_int)
        },
    }
    out_name = f"alibaba_filter_ood_{_weight_tag(L1_WEIGHTS)}_layer2{_weight_tag(L2_WEIGHTS)}_{RUN_DATE}.json"
    out_path = RELEASE_DIR / out_name
    if out_path.exists():
        print(f"ERROR: refusing to overwrite existing result file: {out_path}")
        sys.exit(1)
    out_path.write_text(json.dumps(out_record, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[out] Alibaba OOD results -> {out_path}")


if __name__ == "__main__":
    main()
