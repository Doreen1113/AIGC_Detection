# Artifact Taxonomy Alignment — Self-Built 4-Type Scheme vs. RetouchingFFHQ

> Design-proposal document only. Does not modify `artifact_classifier_v3.pth`, `pipeline.py`,
> `ARTIFACT_REGION_MAP`, or the JSON schema. All claims below are traced to specific files
> read during this audit.

## The two taxonomies, side by side

| This project's 4-type scheme (`CLASSES` in `AIGuard/train_artifact_classifier_v3.py`) | RetouchingFFHQ's operation dimensions (per `four_process.txt`'s parameter-dict keys) |
|---|---|
| `eye_enlarging` | `EyeEnlarging` |
| `face_reshaping` | `FaceLifting` |
| `smoothing` | `Smoothing` |
| `whitening` | `Whitening` |

## Which are one-to-one?

**Three of four look like clean naming matches**: `eye_enlarging`↔`EyeEnlarging`,
`smoothing`↔`Smoothing`, `whitening`↔`Whitening`. `face_reshaping`↔`FaceLifting` is a naming
correspondence this project's own docs already use informally (e.g. TODO.md's Alibaba
per-type breakdown table lists "FaceLifting" as if it were the direct RetouchingFFHQ
equivalent of "face_reshaping" without further comment) — but **no operational-equivalence
check was found anywhere in this repo**. "One-to-one by name" is not the same claim as
"one-to-one by pixel operation," and this audit did not find evidence the latter was ever
verified: this project's `apply_face_reshaping()` uses a fixed 60px cheek-warp radius (see
`filters/stress_test_filter_functions.py`); RetouchingFFHQ's `FaceLifting` is produced by
Alibaba/Megvii's actual commercial APIs, whose internal algorithm is not published and was
never compared against this project's warp implementation. **Verdict: the name mapping is a
reasonable, already-adopted working assumption, but it is UNVERIFIED as an operational
equivalence claim** — flagged here explicitly rather than silently continuing to treat it as
settled.

## Which are one-to-many / mixed-operation?

**FFHQ_four_process and FFHQ_megvii_four_process are not one-to-one with anything** — every
image in these two families has all 4 operations applied simultaneously at independently
randomized intensities (confirmed directly from `FFHQ_four_process/four_process.txt`'s
per-image record, e.g. `{'Whitening': 60, 'Smoothing': 30, 'FaceLifting': 30,
'EyeEnlarging': 60}`). There is no image in these two families for which "the" applied
operation is any single one of the 4 self-built types — asking "is this a whitening image or
a smoothing image" is a category error for this data, not an answerable question the model
got right or wrong.

**FFHQ_ali_process is the one external family that IS single-operation** — its folder
structure (`EyeEnlarging_{30,60,90}`, `FaceLifting_{30,60,90}`, `Smoothing_{30,60,90}`,
`Whitening_{30,60,90}`) applies exactly one named operation per image, at one of 3 intensity
levels. This is the closest external analog to the self-built taxonomy's granularity.

## Which don't align at all?

Nothing in the located data actively contradicts the 4-type naming scheme (no RetouchingFFHQ
operation was found that has no analog in the 4 self-built types) — the alignment problem
found in this audit is not "wrong categories" but **"external data mostly can't be cleanly
assigned to a single category at all"** (families B/C) or **"can be assigned, but that
assignment has never been validated against the deployed classifier"** (family D).

## Is `artifact_classifier_v3`'s 4-class output semantically reasonable when applied to external retouch sources?

**For families B/C (four_process combined blocks): no — it is semantically forced.** Feeding
a `FFHQ_four_process` image (which has whitening+smoothing+face-lifting+eye-enlarging all
applied at once) through a 4-way *single-label* softmax classifier and reporting one winning
type is answering a question the data cannot honestly support. The model isn't necessarily
"wrong" in a normal accuracy sense — there's no ground truth to be wrong against — but the
OUTPUT FORMAT itself (a forced single choice) misrepresents what's actually in the image.
This is a data/taxonomy mismatch, not a model-quality problem, and no amount of retraining
`artifact_classifier_v3` on more B/C data would fix it without also changing the output format
away from single-label.

**For family D (Alibaba, single-operation): plausible, but currently unverified.** The
taxonomy alignment is clean at the label level (4 folder names ↔ 4 model classes), but per
`FILTER_XAI_CLAIM_MATRIX.md`, no experiment in this repo has ever scored `artifact_classifier_v3`
against family D's own ground-truth folder labels — `AIGuard/eval_ali_ood_v811.py` only checks
the coarse filter/not-filter decision. Whether the 4-way classifier's output is *actually*
reasonable on this family (not just structurally compatible) is an open, cheaply-answerable
question — the ground truth already exists, it just hasn't been used for this purpose yet.

## Should future output classes be added?

Based on what this audit found, three additions would directly close gaps identified above,
each targeted at a specific, evidenced problem rather than a generic "add more classes" move:

1. **`mixed_retouch` (or equivalent)** — directly addresses families B/C's structural mismatch.
   Rather than forcing a single-label answer onto genuinely multi-operation images, an explicit
   "multiple beautification effects detected, individual types not separated" output would be
   an honest description of what B/C actually contain. This is the single most directly
   evidenced proposed addition in this audit (the four_process.txt parameter dict makes the
   multi-operation nature a settled fact, not an inference).
2. **`unknown_retouch`** — pipeline.py already has this exact concept for the artifact
   sub-classifier (`ARTIFACT_UNKNOWN_THRESHOLD = 0.6`, `"unknown_filter"` fallback, confirmed
   by reading `pipeline.py`'s `classify_artifact()` — **not modified by this audit**). The
   design pattern already exists and works; the gap is that it's currently calibrated/used
   only in the self-built-data context. Whether its threshold/behavior generalizes to
   external-source low-confidence cases (e.g. family D images where the model may be
   genuinely uncertain rather than just below threshold on familiar data) has not been tested.
3. **`app_processed` (coarse, non-specific)** — a genuinely useful middle ground between
   "filter" (too vague to be informative) and one of the 4 exact types (too specific to be
   honest for B/C). This would let the pipeline output something more useful than silence for
   external sources without overclaiming a type it can't support — directly matches the
   `FILTER_XAI_CLAIM_MATRIX.md` "coarse retouch/app-family label" claim type that's already
   rated ALLOWED_WITH_CAVEAT for families B/C/D but has no corresponding output class today.

**This is a design proposal only.** No changes were made to `pipeline.py`, `ARTIFACT_REGION_MAP`,
the JSON schema, or `artifact_classifier_v3.pth` to produce this section — implementing any of
the above would require new training data curation (e.g. explicit multi-label ground truth for
B/C) and is out of scope for this read-only audit.
