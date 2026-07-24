"""
Data leakage check: AIGuard fake (incl. CDDB) vs FakeClue test set.

MD5  → exact byte-level duplicate
pHash→ perceptual near-duplicate (catches resize / re-encode)

Usage:
    python check_leakage_cddb_fakeclue.py

Output:
    results/leakage_cddb_fakeclue.txt
"""

import hashlib, os, json
from pathlib import Path
from collections import defaultdict

# ── pHash via imagehash (install: pip install imagehash Pillow) ──
try:
    import imagehash
    from PIL import Image
    HAS_PHASH = True
except ImportError:
    HAS_PHASH = False
    print("[WARN] imagehash not installed; pHash check skipped. Run: pip install imagehash Pillow")

BASE       = Path(r"C:\My_Project\AIGC")
FAKE_DIR   = BASE / "AIGuard" / "fake"          # contains CDDB among other sources
FAKE_CLEAN = BASE / "splits" / "v6_train_real_fake.txt"  # use actual training set paths
FC_TEST    = BASE / "FakeClue" / "test"
OUT_FILE   = BASE / "results" / "leakage_cddb_fakeclue.txt"
IMG_EXTS   = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PHASH_THRESHOLD = 8   # hamming distance ≤ 8 → near-duplicate

# ─────────────────────────────────────────────────────────────────


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def phash(path: Path):
    if not HAS_PHASH:
        return None
    try:
        return imagehash.phash(Image.open(path).convert("RGB"))
    except Exception:
        return None


def collect_images(directory: Path) -> list[Path]:
    imgs = []
    for p in directory.rglob("*"):
        if p.suffix.lower() in IMG_EXTS:
            imgs.append(p)
    return imgs


def load_training_fake_paths() -> list[Path]:
    """Load only the fake (label=1) paths from the training split."""
    paths = []
    p = FAKE_CLEAN
    if not p.exists():
        print(f"[WARN] {p} not found, scanning AIGuard/fake/ directly")
        return collect_images(FAKE_DIR)
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("path\t"):
            continue
        parts = line.split("\t")
        if len(parts) >= 2 and parts[1].strip() == "1":
            paths.append(Path(parts[0].strip()))
    return paths


def main():
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("=" * 60)
    log("Data Leakage Check: AIGuard fake  ↔  FakeClue test")
    log("=" * 60)

    # ── Collect FakeClue test images ─────────────────────────────
    log(f"\n[1] Scanning FakeClue test: {FC_TEST}")
    fc_imgs = collect_images(FC_TEST)
    log(f"    Found {len(fc_imgs)} images")

    if not fc_imgs:
        log("ERROR: No FakeClue test images found. Check path.")
        OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
        return

    log(f"\n[2] Computing MD5 for FakeClue test ...")
    fc_md5 = {}
    for i, p in enumerate(fc_imgs):
        fc_md5[md5(p)] = p
        if (i + 1) % 200 == 0:
            print(f"    {i+1}/{len(fc_imgs)}", end="\r")
    log(f"    Done. Unique MD5: {len(fc_md5)}")

    fc_phash = {}
    if HAS_PHASH:
        log(f"\n[3] Computing pHash for FakeClue test ...")
        for i, p in enumerate(fc_imgs):
            h = phash(p)
            if h is not None:
                fc_phash[p] = h
            if (i + 1) % 200 == 0:
                print(f"    {i+1}/{len(fc_imgs)}", end="\r")
        log(f"    Done. pHash computed: {len(fc_phash)}")
    else:
        log("\n[3] pHash skipped (imagehash not installed)")

    # ── Collect AIGuard fake training images ─────────────────────
    log(f"\n[4] Loading AIGuard fake training paths ...")
    train_imgs = load_training_fake_paths()
    log(f"    Found {len(train_imgs)} fake training images")

    # ── MD5 comparison ───────────────────────────────────────────
    log(f"\n[5] MD5 comparison (exact duplicates) ...")
    md5_hits = []
    for i, p in enumerate(train_imgs):
        if not p.exists():
            continue
        h = md5(p)
        if h in fc_md5:
            md5_hits.append((p, fc_md5[h]))
        if (i + 1) % 1000 == 0:
            print(f"    {i+1}/{len(train_imgs)}", end="\r")

    log(f"\n    *** MD5 exact matches: {len(md5_hits)} ***")
    if md5_hits:
        log("    OVERLAP FOUND:")
        for train_p, test_p in md5_hits[:20]:
            log(f"      TRAIN: {train_p}")
            log(f"      TEST : {test_p}")
        if len(md5_hits) > 20:
            log(f"      ... and {len(md5_hits)-20} more")
    else:
        log("    No exact duplicates found. ✅")

    # ── pHash comparison ─────────────────────────────────────────
    if HAS_PHASH and fc_phash:
        log(f"\n[6] pHash comparison (near-duplicates, threshold={PHASH_THRESHOLD}) ...")
        fc_phash_list = list(fc_phash.items())   # [(path, hash), ...]
        phash_hits = []
        for i, train_p in enumerate(train_imgs):
            if not train_p.exists():
                continue
            th = phash(train_p)
            if th is None:
                continue
            for test_p, fh in fc_phash_list:
                if th - fh <= PHASH_THRESHOLD:
                    phash_hits.append((train_p, test_p, int(th - fh)))
            if (i + 1) % 500 == 0:
                print(f"    {i+1}/{len(train_imgs)}", end="\r")

        log(f"\n    *** pHash near-matches: {len(phash_hits)} ***")
        if phash_hits:
            log("    NEAR-DUPLICATES FOUND:")
            for train_p, test_p, dist in sorted(phash_hits, key=lambda x: x[2])[:20]:
                log(f"      dist={dist}  TRAIN: {train_p.name}")
                log(f"                   TEST : {test_p.name}")
            if len(phash_hits) > 20:
                log(f"      ... and {len(phash_hits)-20} more")
        else:
            log("    No near-duplicates found. ✅")
    else:
        log("\n[6] pHash comparison skipped")

    # ── Summary ──────────────────────────────────────────────────
    log("\n" + "=" * 60)
    log("SUMMARY")
    log("=" * 60)
    log(f"  AIGuard fake training images : {len(train_imgs)}")
    log(f"  FakeClue test images         : {len(fc_imgs)}")
    log(f"  MD5 exact matches            : {len(md5_hits)}")
    if HAS_PHASH and fc_phash:
        log(f"  pHash near-matches (≤{PHASH_THRESHOLD})     : {len(phash_hits)}")

    if len(md5_hits) == 0 and (not HAS_PHASH or len(phash_hits) == 0):
        log("\n  ✅ No leakage detected between AIGuard fake training and FakeClue test.")
        log("     FakeClue AUROC results are trustworthy.")
    else:
        log("\n  ⚠️  LEAKAGE DETECTED. Check the overlapping files above.")
        log("     FakeClue AUROC may be inflated. Re-eval on non-overlapping subset needed.")

    OUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nResults saved: {OUT_FILE}")


if __name__ == "__main__":
    main()
