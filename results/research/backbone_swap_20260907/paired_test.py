"""Paired bootstrap of MobileNetV4 (this round) vs ShuffleNetV2 (ternary_necessity_20260906
TERN arm) on the two safety axes. Same images, same matched operating point rule, clustered by
source image, NB = 10,000. ASCII-only prints.

Pre-declared verdict (PRE_DECLARED.md):
  KEEP   - neither safety axis degrades outside its paired CI
  TRADE  - one axis degrades significantly
  REJECT - both degrade significantly
"""
import json
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CTRL = HERE.parent / "ternary_necessity_20260906"
NB, RNG = 10000, np.random.default_rng(20260907)


def load(round_dir, tag):
    """path -> (score, set) from a per-image dump."""
    sc, st = {}, {}
    for l in (round_dir / f"perimage_{tag}.tsv").read_text(encoding="utf-8").splitlines()[1:]:
        f = (l.split("\t") + ["", ""])[:4]
        sc[f[0]] = float(f[2]); st[f[0]] = f[1]
    return sc, st


def thr_of(round_dir, tag):
    d = json.loads((round_dir / "frontier.json").read_text(encoding="utf-8"))
    return d["models"][tag]["matched"]["thr"], d["models"][tag]["matched"]


def cluster(paths, axis):
    """filtered fakes: 8 conditions share one source image; filtered reals: one each."""
    if axis == "MISS":
        return np.array([re.sub(r"__.*", "", Path(p).stem) for p in paths])
    return np.array([Path(p).stem for p in paths])


def paired(axis):
    setname = "filtered_real" if axis == "FA" else "filtered_fake"
    sc_a, st_a = load(HERE, "TERN_MNV4")
    sc_b, _ = load(CTRL, "TERN")
    ta, ma = thr_of(HERE, "TERN_MNV4")
    tb, mb = thr_of(CTRL, "TERN")
    paths = sorted(p for p in sc_a if st_a[p] == setname and p in sc_b)
    if axis == "FA":                      # called fake = score >= threshold
        ia = np.array([sc_a[p] >= ta for p in paths], float)
        ib = np.array([sc_b[p] >= tb for p in paths], float)
    else:                                 # missed = score < threshold
        ia = np.array([sc_a[p] < ta for p in paths], float)
        ib = np.array([sc_b[p] < tb for p in paths], float)
    cl = cluster(paths, axis)
    uc = np.unique(cl); idx = {c: np.where(cl == c)[0] for c in uc}
    diffs = []
    for _ in range(NB):
        d = RNG.integers(0, len(uc), size=len(uc))
        ii = np.concatenate([idx[uc[j]] for j in d])
        diffs.append(ia[ii].mean() - ib[ii].mean())
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    pt = (ia.mean() - ib.mean()) * 100
    # degradation means MORE false accusations / MORE misses, i.e. delta > 0
    if lo * 100 > 0:
        verdict = "DEGRADES (significant)"
    elif hi * 100 < 0:
        verdict = "IMPROVES (significant)"
    else:
        verdict = "no significant change"
    return dict(axis=axis, n=len(paths), clusters=len(uc),
                mnv4_pct=round(ia.mean() * 100, 3), shufflenet_pct=round(ib.mean() * 100, 3),
                delta_pp=round(pt, 3), ci95=[round(lo * 100, 3), round(hi * 100, 3)],
                verdict=verdict)


def main():
    out = {}
    for axis in ("FA", "MISS"):
        r = paired(axis)
        out[axis] = r
        print(f"{axis:5s} MobileNetV4={r['mnv4_pct']:6.2f}%  ShuffleNetV2={r['shufflenet_pct']:6.2f}%  "
              f"delta={r['delta_pp']:+6.2f} pp  CI [{r['ci95'][0]:+6.2f}, {r['ci95'][1]:+6.2f}]  "
              f"{r['verdict']}  (n={r['n']}, clusters={r['clusters']})", flush=True)
    deg = [a for a in ("FA", "MISS") if out[a]["verdict"].startswith("DEGRADES")]
    verdict = "KEEP" if not deg else ("REJECT" if len(deg) == 2 else "TRADE")
    out["degraded_axes"] = deg
    out["verdict"] = verdict
    print(f"\nPRE-DECLARED VERDICT: {verdict}"
          f"{' (degraded: ' + ', '.join(deg) + ')' if deg else ''}", flush=True)
    (HERE / "paired_test.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
