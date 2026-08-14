# Fake-XAI Claim Policy — v8.11d Level 1/2 Audit (2026-08-14)

Three allowed statuses for any natural-language claim about a `fake`-class
explanation, consistent with `docs/xai_evidence_schema.md`'s
`text_evidence_level` enum:

- **A. GLOBAL_ONLY** — may describe global visual patterns; may NOT mention
  texture or frequency specifically; may NOT mention any part/region of the
  face.
- **B. GLOBAL_FAITHFULNESS_SUPPORTED** — may say model attention
  contributes to the fake prediction (backed by a passing deletion/insertion
  faithfulness test); may NOT claim manipulation location or a mask.
- **C. GT_BACKED_LOCALIZATION** — NOT usable this round; must be explicitly
  marked pending credible ground-truth masks (e.g. FF++ official masks, if
  ever added to training/eval sources — `docs/xai_evidence_schema.md` Tier D).

## Per-source status, based on this audit's Task 2/3 results

| Source | Status | Why |
|---|---|---|
| aiguard_unseen | **B. GLOBAL_FAITHFULNESS_SUPPORTED** | Deletion: hot_drop > bottom_drop and > mean_random_drop at every k=5/10/20%, bootstrap 95% CI excludes zero (k20: Cohen's d=1.43 / 1.21). Insertion: hot-first AUC (0.927) significantly > bottom-first AUC (0.835), CI excludes zero (d=1.88). |
| stylegan2_ood | **B. GLOBAL_FAITHFULNESS_SUPPORTED** | Deletion: k20 Cohen's d=2.12 (vs bottom) / 1.41 (vs random), both CIs exclude zero — the largest effect of the 3 sources. Insertion: hot-first AUC 0.932 vs bottom-first 0.831, CI excludes zero (d=2.15). |
| truetest_df40 | **B. GLOBAL_FAITHFULNESS_SUPPORTED** | Deletion: k20 Cohen's d=0.64 (vs bottom) / 0.54 (vs random) — smaller effect than the other two sources but still clearly significant (both CIs exclude zero). Insertion: hot-first AUC 0.938 vs bottom-first 0.908, CI excludes zero (d=1.13). |

All 3 fake sources currently qualify for **Status B**. None qualify for
Status C — no fake-class ground-truth manipulation mask exists for any
current source (Tier C, `docs/xai_evidence_schema.md`); Status C remains
explicitly pending real masks and is not addressed by this audit.

## What Status B still forbids, even though it's earned here

Status B lets explanation text say the model's attention *contributes* to
the decision (e.g. "the model's attention, tested for faithfulness via
deletion/insertion, measurably contributes to this classification"). It
does **not** permit:
- Naming a specific facial region ("the eyes", "the jawline", etc.) for the
  `fake` class — Grad-CAM++ here only visualizes `spatial_branch.conv5`
  activations, and even where it's faithful, no GT confirms that region is
  where a manipulation physically happened.
- A texture-specific claim — not tested by this audit (see findings doc).
- Any comparison-with-original-image framing — production inference never
  has access to a "before" image (see `docs/xai_evidence_schema.md`'s
  runtime-vs-offline-evidence section); this audit's deletion/insertion
  tests are OFFLINE evaluation evidence about the single-image heatmap's
  faithfulness, not a live before/after comparison the running system
  performs.

## Note on Task 4 (stability)

Stability/position-bias results are not part of the A/B/C claim tiers
above (those tiers are about the faithfulness/localization claim strength,
not robustness). They are reported separately in the findings doc because
they surfaced a real per-source disagreement (translation robustness:
aiguard_unseen 0.68 / stylegan2_ood 0.42 / truetest_df40 0.90 class
consistency under ±8px shift) that any future claim-strength decision
should be aware of, even though it doesn't change the A/B/C tier itself.
