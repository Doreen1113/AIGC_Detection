# PRE_DECLARED — does the better backbone keep the filter-side properties? (`backbone_swap_20260907`)

Written 2026-09-07 before training. Not revised after results.

## Why this is the highest-value remaining experiment

Every backbone comparison this project has run says ShuffleNetV2 is the weakest of the
candidates, and all of that evidence is on the **forgery-detection** axis only:

| backbone | params | FF++ in-domain AUC | Celeb-DF-v2 | DFD |
|---|---|---|---|---|
| ShuffleNetV2 (current production) | 2.53 M | 0.9155 | 0.7286 | 0.8487 |
| **MobileNetV4** | 3.90 M | **0.9383** | **0.7932 / 0.8325**$^{*}$ | **0.9062 / 0.8916**$^{*}$ |
| RepViT | 5.67 M | 0.9546 | 0.7846 | 0.8783 |
| FastViT | 4.40 M | 0.9509 | 0.7854 | 0.9015 |

$^{*}$two seeds; the 3.93-point Celeb-DF-v2 spread between them is recorded in
`FILTER-AUX-20260907` and is the reason no ordinal claim is made here.

MobileNetV4 is also **faster on CPU despite having more parameters** (14.1 ms vs 19.0 ms,
`ffpp_improve_20260823/efficiency.json`), and it is the backbone the project's own proposal
originally specified before we deviated to ShuffleNetV2.

**But no MobileNetV4 model has ever been trained on the filter-aware task.** The entire
safety case --- 0.0 % false accusation, 91.97 % filter recall, 2.80 % composite stress --- rests
on ShuffleNetV2. Substituting the backbone is therefore an *untested* change, and the paper
currently cannot say whether the better detector backbone keeps the safety properties or
trades them away. This round answers exactly that, and nothing else.

## Arms — identical except the backbone

Recipe, data pool, label space, optimiser, schedule, epochs, augmentation and seed are those
of `ternary_necessity_20260906`'s TERN arm (Adam 1e-4, 10 epochs, batch 192, cosine, label
smoothing 0.1, inverse-frequency class weights, final layer re-initialised), data
`flat3class_revisit_20260828/flat3_train.txt` (211,991 rows: 65,566 real / 73,093 fake /
73,332 filter), seed 20260906.

| arm | backbone | on disk? |
|---|---|---|
| **TERN** (control) | ShuffleNetV2 + FFT branch | **yes** --- `tern_TERN_seed20260906.pth`, already scored on the full frontier |
| **TERN_MNV4** | MobileNetV4 + FFT branch | to train |

Because the control already exists and was produced by the same script under the same seed,
the comparison isolates the backbone.

## Primary criterion --- the safety properties must survive

Read on the same paired held-out sets and at the same matched operating point as
`ternary_necessity_20260906` (4.80 % FPR on 250 clean real faces):

| axis | TERN (control) | bar for TERN\_MNV4 |
|---|---|---|
| FA --- 249 filtered genuine faces called `fake` | 8.84 % | $\le$ 8.84 % **or** paired-difference CI including zero |
| MISS --- 2,289 filtered fakes not called `fake` | 1.97 % | $\le$ 1.97 % **or** paired-difference CI including zero |
| clean fake recall (287) | 98.61 % | no drop outside its CI |

* **KEEP** --- neither safety axis degrades outside its paired CI. The backbone can then be
  switched on the strength of the forgery-axis evidence, and the paper's cost table is
  updated to MobileNetV4.
* **TRADE** --- one axis degrades significantly. Reported as a second Pareto frontier
  (backbone quality versus filter safety), not resolved by preference.
* **REJECT** --- both degrade significantly. ShuffleNetV2 stays, and the reason the weaker
  detector backbone is retained becomes a documented finding rather than an accident of
  history.

Differences are paired bootstrap, clustered by source image, $N_B = 10{,}000$, seed 20260907,
the same estimator as the necessity round.

## Secondary, reported regardless

Full Freeze-Gate battery (True Test filter/fake/real, CelebA, StyleGAN2, AIGuard-unseen
AUROC, composite stress with CI), parameter count, on-disk size, CPU latency measured the
same way as `external_baselines_20260905/measure_cost.py`, and the native three-way
decision point (fraction of filtered reals assigned to `filter`).

## Non-claims fixed now

Single seed per arm --- and given the 3.93-point seed spread already measured on a 389-frame
cross-dataset holdout, a *positive* result here is a candidate requiring a second seed, not a
promotion; the in-house paired sets are larger (249 and 2,289 with 287 source clusters) so
they are better conditioned, but the caveat stands. No production change from this round
alone; no claim that RepViT or FastViT would behave the same; the FFT branch is retained in
both arms so this round says nothing about dropping it. LOCKBOX never read, no git,
ASCII-only prints.
