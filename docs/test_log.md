# Test Log

## 2026-07-14/15 - Cross-dataset inference experiments

Goal: improve OOD generalization without retraining, especially FakeClue AUROC and FakeClue OOD-to-filter over-assignment.

### Summary

Best current inference-only setting:

```powershell
python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.5
```

| Setting | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter |
|---|---:|---:|---:|---:|
| baseline | 0.6490 | 0.5187 | 0.9411 | 55.8% |
| best inference-only candidate: JPEG q80 + filter bias 1.5 | 0.6423 | 0.5863 | 0.9079 | 13.3% |

Main improvement:

- FakeClue AUROC improves from 0.5187 to 0.5863.
- FakeClue OOD-to-filter drops from 55.8% to 13.3%.
- WildDeepfake remains above 0.90.
- AIGuard remains close to the v3 reference.

Important caveat:

Filter logit bias may reduce true filter-class recall. Before making this the final pipeline default, evaluate on real filter validation data such as `filter_data/clean_output/clean_paths.txt` or FFHQ processed filter images.

## Baseline

```powershell
python AIGuard\eval_crossdataset_v3_1.py
```

| Setting | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter |
|---|---:|---:|---:|---:|
| baseline | 0.6490 | 0.5187 | 0.9411 | 55.8% |

## JPEG Quality Sweep

| Setting | Command | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter | Notes |
|---|---|---:|---:|---:|---:|---|
| JPEG q90 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 90` | 0.6627 | 0.5544 | 0.9270 | 35.0% | Conservative setting; best AIGuard/WildDeepfake preservation among JPEG settings. |
| JPEG q85 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 85` | 0.6299 | 0.5781 | 0.9208 | 27.6% | Middle setting; good FakeClue improvement with WildDeepfake above 0.92. |
| JPEG q80 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80` | 0.6420 | 0.5833 | 0.9078 | 21.4% | Best JPEG-only FakeClue AUROC while keeping WildDeepfake above 0.90. |
| JPEG q75 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 75` | 0.6363 | 0.5781 | 0.8783 | 19.8% | Not recommended; WildDeepfake drops below 0.90 and FakeClue is worse than q80. |
| JPEG q70 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 70` | 0.6365 | 0.5803 | 0.8763 | 16.8% | Stronger filter-bias reduction, but WildDeepfake drops too much. |

Conclusion: q80 is the best JPEG-only tradeoff.

## Filter Logit Bias Sweep

All rows below use JPEG normalization q80. Filter logit bias subtracts a constant from the filter-class logit before softmax:

```text
logit_filter = logit_filter - bias
```

| Setting | Command | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter | Notes |
|---|---|---:|---:|---:|---:|---|
| q80 + filter bias 0.2 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 0.2` | 0.6419 | 0.5834 | 0.9080 | 20.5% | Small improvement over q80. |
| q80 + filter bias 0.4 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 0.4` | 0.6429 | 0.5838 | 0.9080 | 19.4% | Good balanced setting. |
| q80 + filter bias 0.6 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 0.6` | 0.6418 | 0.5844 | 0.9080 | 18.3% | Improves FakeClue and filter-bias reduction. |
| q80 + filter bias 0.8 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 0.8` | 0.6419 | 0.5848 | 0.9081 | 17.4% | Continues improving with stable WildDeepfake. |
| q80 + filter bias 1.0 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.0` | 0.6420 | 0.5853 | 0.9080 | 16.1% | Strong candidate with a moderate penalty. |
| q80 + filter bias 1.2 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.2` | 0.6421 | 0.5858 | 0.9079 | 14.6% | Stronger OOD-to-filter reduction. |
| q80 + filter bias 1.5 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.5` | 0.6423 | 0.5863 | 0.9079 | 13.3% | Best setting so far for FakeClue AUROC and OOD-to-filter reduction. |

Conclusion: q80 + filter bias 1.5 is currently best on cross-dataset OOD metrics, but true filter recall must be checked before final deployment.

## Other Inference Experiments

| Setting | Command | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter | Notes |
|---|---|---:|---:|---:|---:|---|
| CLAHE | `python AIGuard\eval_crossdataset_v3_1.py --preprocess clahe` | 0.5974 | 0.5304 | 0.9371 | 30.0% | Slight FakeClue improvement, but AIGuard drops heavily. |
| CLAHE + JPEG q90 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess clahe-jpeg --jpeg-quality 90` | 0.6331 | 0.5636 | 0.9060 | 16.6% | Good filter-bias reduction, but worse FakeClue than q80+bias and more WildDeepfake loss than q90. |
| TTA five-crop + flip | `python AIGuard\eval_crossdataset_v3_1.py --tta` | 0.5909 | 0.5084 | 0.7696 | 2.8% | Not recommended; AUROC drops on all datasets. |
| Two-stage inference | `python AIGuard\eval_crossdataset_v3_1.py --two-stage` | 0.6490 | 0.5187 | 0.9411 | 56.5% | Not recommended; does not reduce FakeClue filter bias. |
| JPEG q90 + two-stage inference | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 90 --two-stage` | 0.6627 | 0.5544 | 0.9270 | 37.6% | Same AUROC as JPEG q90, but worse OOD-to-filter than JPEG q90 alone. |

## Fake-prior Rule Sweep

All rows below use JPEG normalization q80. Rule:

```text
if P(real) > 0.6: predict real
elif P(filter) - P(fake) < margin: predict fake
else: predict filter
```

| Setting | Command | AIGuard unseen AUROC | FakeClue test AUROC | WildDeepfake test AUROC | FakeClue OOD->filter | Notes |
|---|---|---:|---:|---:|---:|---|
| q80 + fake-prior margin 0.05 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --fake-prior-margin 0.05` | 0.6420 | 0.5833 | 0.9078 | 23.8% | Not recommended; increases filter bias versus q80 baseline. |
| q80 + fake-prior margin 0.10 | `python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --fake-prior-margin 0.10` | 0.6420 | 0.5833 | 0.9078 | 23.7% | Not recommended. |

Conclusion: fake-prior changes final class decisions but does not improve AUROC and does not reduce OOD-to-filter versus q80 baseline.

## Current Recommendation

Use JPEG q80 + filter logit bias as the main inference-only calibration approach.

Recommended final candidate:

```powershell
python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.5
```

More conservative fallback:

```powershell
python AIGuard\eval_crossdataset_v3_1.py --preprocess jpeg --jpeg-quality 80 --filter-logit-bias 1.0
```

Before finalizing `filter-logit-bias 1.5`, run a filter validation check to measure whether true filter images are being pushed into `fake`.
