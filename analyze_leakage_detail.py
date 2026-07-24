"""
Detailed analysis of pHash near-matches: AIGuard fake vs FakeClue test.

Goals:
  1. Deduplicate FakeClue test (MD5 dedup)
  2. Identify which FakeClue subdirectory each match comes from
  3. Cross-reference with official 1,166 eval set (labels.csv)
  4. Break down by pHash distance bucket
  5. Save example image pairs for visual inspection

Usage:
    python analyze_leakage_detail.py
"""

import hashlib, shutil
from pathlib import Path, PurePosixPath
from collections import defaultdict
import imagehash
from PIL import Image

BASE        = Path(r"C:\My_Project\AIGC")
FC_TEST     = BASE / "FakeClue" / "test"
FC_LABELS   = BASE / "FakeClue" / "test_clean" / "labels.csv"
TRAIN_SPLIT = BASE / "splits" / "v6_train_real_fake.txt"
OUT_DIR     = BASE / "results" / "leakage_analysis"
IMG_EXTS    = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
THRESHOLD   = 8


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_phash(path):
    try:
        return imagehash.phash(Image.open(path).convert("RGB"))
    except Exception:
        return None


def collect_images(directory):
    return [p for p in Path(directory).rglob("*") if p.suffix.lower() in IMG_EXTS]


def load_training_fake_paths():
    paths = []
    for line in Path(TRAIN_SPLIT).read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("path\t"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip() == "1":
            p = Path(parts[0].strip())
            if p.exists():
                paths.append(p)
    return paths


def load_fc_eval_set():
    """Load the 1,166 official eval paths as a set of normalized absolute strings."""
    if not FC_LABELS.exists():
        print(f"[WARN] {FC_LABELS} not found")
        return set()
    eval_paths = set()
    for line in FC_LABELS.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("path"):
            continue
        raw = line.split(",")[0].strip()
        # normalize: replace forward slash with backslash, then resolve
        normalized = str(Path(raw.replace("/", "\\")))
        eval_paths.add(normalized.lower())
    return eval_paths


def subdir_of(path: Path) -> str:
    """Return the immediate subdirectory under FakeClue/test/."""
    try:
        rel = path.relative_to(FC_TEST)
        return rel.parts[0] if rel.parts else "?"
    except ValueError:
        return "?"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_lines = []

    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    log("=" * 60)
    log("Detailed Leakage Analysis: AIGuard fake ↔ FakeClue test")
    log("=" * 60)

    # ── 1. FakeClue test: deduplicate by MD5 ─────────────────────
    log("\n[1] Scanning and deduplicating FakeClue test ...")
    all_fc = collect_images(FC_TEST)
    md5_to_canonical = {}
    fc_unique = []
    for p in all_fc:
        h = md5(p)
        if h not in md5_to_canonical:
            md5_to_canonical[h] = p
            fc_unique.append(p)

    log(f"  Total files     : {len(all_fc)}")
    log(f"  Unique (MD5)    : {len(fc_unique)}")
    log(f"  Internal dups   : {len(all_fc) - len(fc_unique)}")

    subdir_counts = defaultdict(int)
    for p in fc_unique:
        subdir_counts[subdir_of(p)] += 1
    log(f"  By subdirectory: " + ", ".join(f"{k}:{v}" for k, v in sorted(subdir_counts.items())))

    # ── 2. Load official eval set ─────────────────────────────────
    log(f"\n[2] Loading official eval set (labels.csv) ...")
    fc_eval = load_fc_eval_set()
    log(f"  Eval set size   : {len(fc_eval)} paths")

    def in_eval(p: Path) -> bool:
        return str(p).lower() in fc_eval

    # ── 3. pHash for deduplicated FC test ─────────────────────────
    log(f"\n[3] Computing pHash for {len(fc_unique)} unique test images ...")
    fc_phash = {}
    for i, p in enumerate(fc_unique):
        h = get_phash(p)
        if h is not None:
            fc_phash[p] = h
        if (i+1) % 500 == 0:
            print(f"  {i+1}/{len(fc_unique)}", end="\r")
    log(f"  Done: {len(fc_phash)}")

    # ── 4. Training fake paths ────────────────────────────────────
    log(f"\n[4] Loading training fake paths ...")
    train_imgs = load_training_fake_paths()
    log(f"  {len(train_imgs)} fake training images")

    # ── 5. pHash comparison ───────────────────────────────────────
    log(f"\n[5] Running pHash comparison ...")
    fc_list = list(fc_phash.items())
    hits = defaultdict(list)    # train_path → [(test_path, dist)]
    for i, train_p in enumerate(train_imgs):
        th = get_phash(train_p)
        if th is None:
            continue
        for test_p, fh in fc_list:
            dist = int(th - fh)
            if dist <= THRESHOLD:
                hits[train_p].append((test_p, dist))
        if (i+1) % 500 == 0:
            print(f"  {i+1}/{len(train_imgs)}", end="\r")
    log("  Done.")

    # ── 6. Analyze ────────────────────────────────────────────────
    log(f"\n[6] Analysis ...")

    unique_train = set(hits.keys())
    unique_test  = set()
    for matches in hits.values():
        for tp, _ in matches:
            unique_test.add(tp)

    # by bucket
    buckets = {(0,0): [], (1,2): [], (3,4): [], (5,8): []}
    for train_p, matches in hits.items():
        for test_p, dist in matches:
            for (lo, hi) in buckets:
                if lo <= dist <= hi:
                    buckets[(lo,hi)].append((train_p, test_p, dist))
                    break

    log(f"\n  Unique training imgs with any match : {len(unique_train)}")
    log(f"  Unique test imgs    with any match : {len(unique_test)}")

    # which subdir
    subdir_hits = defaultdict(set)
    for p in unique_test:
        subdir_hits[subdir_of(p)].add(p)
    log(f"\n  Matched test images by subdirectory:")
    for sd, imgs in sorted(subdir_hits.items()):
        in_ev = sum(1 for p in imgs if in_eval(p))
        log(f"    {sd:20s}  {len(imgs):4d} unique matched  ({in_ev} in official eval)")

    log(f"\n  By pHash distance:")
    for (lo, hi), pairs in buckets.items():
        unique_tr = len(set(p[0] for p in pairs))
        unique_te = len(set(p[1] for p in pairs))
        in_ev     = sum(1 for _, tp, _ in pairs if in_eval(tp))
        log(f"    dist {lo}-{hi}: {len(pairs):4d} pairs  "
            f"({unique_tr} train / {unique_te} test unique)  "
            f"{in_ev} test in official eval")

    # high-confidence (dist ≤ 2)
    hc_test_in_eval = set()
    for (lo, hi) in [(0,0), (1,2)]:
        for _, tp, _ in buckets[(lo,hi)]:
            if in_eval(tp):
                hc_test_in_eval.add(tp)
    log(f"\n  High-confidence (dist≤2) leaked imgs in official eval: {len(hc_test_in_eval)}")
    if hc_test_in_eval:
        log(f"  Affected eval fraction: {len(hc_test_in_eval)}/1166 = "
            f"{len(hc_test_in_eval)/1166*100:.1f}%")

    # ── 7. Save examples ──────────────────────────────────────────
    log(f"\n[7] Saving image pair examples ...")
    ex_dir = OUT_DIR / "examples"
    ex_dir.mkdir(exist_ok=True)
    for (lo, hi), pairs in buckets.items():
        tier = ex_dir / f"dist_{lo}-{hi}"
        tier.mkdir(exist_ok=True)
        for n, (tr, te, dist) in enumerate(pairs[:5]):
            shutil.copy(tr, tier / f"pair{n+1}_d{dist}_TRAIN_{tr.name}")
            shutil.copy(te, tier / f"pair{n+1}_d{dist}_TEST_{te.name}")
        if pairs:
            log(f"  dist {lo}-{hi}: {min(5,len(pairs))} pairs → {tier}")

    # ── 8. Save TSV ───────────────────────────────────────────────
    tsv = OUT_DIR / "all_hits.tsv"
    with open(tsv, "w", encoding="utf-8") as f:
        f.write("dist\tin_eval\ttest_subdir\ttrain_path\ttest_path\n")
        for tr_p, matches in sorted(hits.items(), key=lambda x: str(x[0])):
            for te_p, dist in sorted(matches, key=lambda x: x[1]):
                f.write(f"{dist}\t{in_eval(te_p)}\t{subdir_of(te_p)}\t{tr_p}\t{te_p}\n")
    log(f"\n  Full hit list: {tsv}")

    # ── Summary ───────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("FINAL SUMMARY")
    log("=" * 60)
    log(f"  Training fake scanned           : {len(train_imgs)}")
    log(f"  FakeClue test unique images     : {len(fc_unique)}")
    log(f"  Official eval set               : {len(fc_eval)}")
    log(f"  Unique training imgs w/ match   : {len(unique_train)}")
    log(f"  Unique test imgs w/ match       : {len(unique_test)}")
    log(f"  High-conf leaked in eval (≤d2)  : {len(hc_test_in_eval)} / 1166")

    if len(hc_test_in_eval) == 0:
        log("\n  ✅ No high-confidence leakage in official eval set.")
        log("     773 raw matches were false positives (similar-looking faces).")
    elif len(hc_test_in_eval) < 50:
        log(f"\n  ⚠️  Minor leakage: {len(hc_test_in_eval)} eval images contaminated.")
        log("     Re-eval on clean subset to quantify AUROC impact.")
    else:
        log(f"\n  ❌ Significant leakage: {len(hc_test_in_eval)} eval images contaminated.")
        log("     FakeClue AUROC results require correction.")

    (OUT_DIR / "summary.txt").write_text("\n".join(log_lines), encoding="utf-8")
    print(f"\nAll outputs saved to: {OUT_DIR}")


if __name__ == "__main__":
    main()
