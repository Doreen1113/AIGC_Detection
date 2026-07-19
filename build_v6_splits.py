"""
Build v6 training splits: pure static images only.
Filters out WildDeepfake entries from v5 splits.

v6 composition:
  real:   AIGuard-real (22,891) + LFW-real (5,000)          = 27,891
  fake:   AIGuard-fake (18,268) + DF40-diffusion (4,551)    = 22,819
  filter: unchanged from v5_train_filter.txt (64,106)

WildDeepfake moves to eval-only (not removed from eval benchmarks).

python build_v6_splits.py
"""
from pathlib import Path

BASE   = Path(r"C:\My_Project\AIGC")
SPLITS = BASE / "splits"


def filter_no_wilddeepfake(src_path, dst_path):
    lines = Path(src_path).read_text(encoding="utf-8").splitlines()
    header = [l for l in lines if l.startswith("path\t")]
    data   = [l for l in lines if not l.startswith("path\t") and l.strip()]

    kept    = [l for l in data if "WildDeepfake" not in l]
    removed = len(data) - len(kept)

    with open(dst_path, "w", encoding="utf-8") as f:
        if header:
            f.write(header[0] + "\n")
        f.write("\n".join(kept) + "\n")

    sources = {}
    for l in kept:
        parts = l.split("\t")
        src = parts[2] if len(parts) > 2 else "unknown"
        sources[src] = sources.get(src, 0) + 1

    print(f"\n{Path(dst_path).name}: {len(kept)} lines  (removed {removed} WildDeepfake entries)")
    for k, v in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {k}: {v}")
    return len(kept)


if __name__ == "__main__":
    print("=== Building v6 static splits ===")

    n_train = filter_no_wilddeepfake(
        SPLITS / "v5_train_real_fake.txt",
        SPLITS / "v6_train_real_fake.txt",
    )
    n_val = filter_no_wilddeepfake(
        SPLITS / "v5_val_real_fake.txt",
        SPLITS / "v6_val_real_fake.txt",
    )

    print(f"\n=== Done ===")
    print(f"  v6_train_real_fake.txt : {n_train}")
    print(f"  v6_val_real_fake.txt   : {n_val}")
    print(f"  Filter splits          : reuse v5_train_filter.txt + val_filter.txt (unchanged)")
    print(f"\nNext: python AIGuard/train_v6.py")
