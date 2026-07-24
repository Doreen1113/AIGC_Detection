"""
Phase 2 — Parse FakeVLM explanations into suspicious_regions labels.

Input : results/fakevlm_teacher_outputs.jsonl
Output: results/fakevlm_region_labels.jsonl  (path + subdir + suspicious_regions)
        results/fakevlm_region_labels_stats.txt

Usage:
    python AIGuard/parse_region_labels.py
"""

import json
from collections import Counter
from pathlib import Path

BASE = Path(r"C:\My_Project\AIGC")
IN_PATH  = BASE / "results" / "fakevlm_teacher_outputs.jsonl"
OUT_PATH = BASE / "results" / "fakevlm_region_labels.jsonl"
STAT_PATH = BASE / "results" / "fakevlm_region_labels_stats.txt"

# Schema enum order (kept for consistent label ordering)
REGIONS = ["forehead", "left_eye", "right_eye", "nose",
           "left_cheek", "right_cheek", "mouth", "jaw"]

# Keyword → region(s).  Order matters: check longer phrases first.
KEYWORD_MAP = [
    ("hairline",   ["forehead"]),
    ("eyebrow",    ["forehead"]),
    ("brow",       ["forehead"]),
    ("forehead",   ["forehead"]),
    ("hair",       ["forehead"]),

    ("left eye",   ["left_eye"]),
    ("right eye",  ["right_eye"]),
    ("eyelid",     ["left_eye", "right_eye"]),
    ("eye",        ["left_eye", "right_eye"]),

    ("nostril",    ["nose"]),
    ("nose",       ["nose"]),

    ("cheek",      ["left_cheek", "right_cheek"]),

    ("mouth",      ["mouth"]),
    ("lip",        ["mouth"]),
    ("teeth",      ["mouth"]),

    ("jawline",    ["jaw"]),
    ("beard",      ["jaw"]),
    ("chin",       ["jaw"]),
    ("jaw",        ["jaw"]),
]


def extract_regions(explanation: str) -> list[str]:
    low = explanation.lower()
    found = set()
    for keyword, regions in KEYWORD_MAP:
        if keyword in low:
            found.update(regions)
    # Return in schema enum order
    return [r for r in REGIONS if r in found]


def main():
    data = [json.loads(l) for l in IN_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"Loaded {len(data)} records")

    results = []
    region_counter = Counter()
    empty_count = 0

    for r in data:
        regions = extract_regions(r["explanation"])
        if not regions:
            empty_count += 1
        region_counter.update(regions)
        results.append({
            "path":    r["path"],
            "subdir":  r["subdir"],
            "suspicious_regions": regions,
        })

    OUT_PATH.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8"
    )
    print(f"Saved {len(results)} records → {OUT_PATH}")

    # Stats
    lines = [
        f"FakeVLM Region Label Stats",
        f"Total : {len(results)}",
        f"Empty (no region found) : {empty_count} ({empty_count/len(results)*100:.1f}%)",
        f"",
        f"Per-region counts:",
    ]
    for reg in REGIONS:
        c = region_counter[reg]
        lines.append(f"  {reg:15s}: {c:5d}  ({c/len(results)*100:.1f}%)")

    lines += ["", "By subdir:"]
    by_sub = {}
    for r, rec in zip(results, data):
        by_sub.setdefault(rec["subdir"], []).append(r["suspicious_regions"])

    for sd, recs in sorted(by_sub.items()):
        empty = sum(1 for r in recs if not r)
        lines.append(f"  {sd}: {len(recs)} total, {empty} empty ({empty/len(recs)*100:.0f}% empty)")

    stat_text = "\n".join(lines)
    STAT_PATH.write_text(stat_text, encoding="utf-8")
    print("\n" + stat_text)


if __name__ == "__main__":
    main()
