# v8.11 Production — Reproduction Commands

> Every command below was confirmed by reading the target script's own usage docstring
> and/or argument-parsing code in this pass — not guessed. Where a script takes optional
> positional weight arguments, **both forms are given**: the explicit-args form (always
> safe) and the default-args form (marked with its actual default, which for several
> scripts is the SUPERSEDED `v811c` checkpoint — see the warning below). Run all commands
> from the repo root (`c:\My_Project\AIGC`) using the project's base conda env.

## ⚠️ Critical warning before running anything

Several `v811`-named scripts **default to `shufflenet_v2_layer1_v811c.pth`** (superseded)
when invoked with no arguments — confirmed by reading their source in this pass:

- `eval_v811_gates.py`
- `AIGuard/stress_test_v811_pipeline.py`
- `AIGuard/eval_ali_ood_v811.py`
- `AIGuard/eval_robustness.py`

**Always pass the production weights explicitly** for these four, as shown below.
`eval_truetest_paired.py` is the exception — it correctly defaults to v811d/v811.

## Core v8.11 gate evaluation

```
python eval_v811_gates.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth
```

Confirmed from source (`eval_v811_gates.py` line 13 docstring: `python eval_v811_gates.py
[layer1_weights] [layer2_weights]`; lines 29-30 show the default is v811c, so explicit args
are required for a production-valid run). Reproduces: True Test filter recall, AIGuard/unseen
AUROC, CelebA real recall, StyleGAN2 fake recall — matches `results/eval_v811d_gates.log`.

## True Test paired evaluation

```
python eval_truetest_paired.py
```

Confirmed from source (`eval_truetest_paired.py` line 19 docstring: `python
eval_truetest_paired.py [layer1_weights] [layer2_weights]`; lines 36-37 show the **default is
already v811d/v811**, so no explicit args are required — though passing them explicitly is
still fine/safer as a habit). **Caveat**: this script prints to stdout only (no `--output`
flag or file-write call found in this pass); to archive a result, redirect output yourself,
e.g. `python eval_truetest_paired.py > results/truetest_paired_v811_rerun.log` (this
redirection is standard shell usage, not a script feature, and was not run in this pass per
the read-only/no-rerun constraint).

## Robustness evaluation

```
python AIGuard/eval_robustness.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth
```

Confirmed from source (`AIGuard/eval_robustness.py` line 12 docstring; lines 33-34 show default
is v811c). Auto-names its own output based on the loaded weights (per the 2026-08-11 fix
recorded in TODO.md) — reproduces `results/robustness_eval_v811d.json`.

## Fake+filter stress test

```
python AIGuard/stress_test_v811_pipeline.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth
```

Confirmed from source (`AIGuard/stress_test_v811_pipeline.py` line 11 docstring; lines 34-35
show default is v811c). Auto-names output by loaded weights. Reproduces
`results/stress_test_v811d_pipeline.log` + `results/stress_test_v811_pipeline.json`
(3.71% aggregate).

## Production Filter XAI validation

```
python phase2_p0_v811_filter_gradcam_validation.py
```

Confirmed from source (line 40-42 docstring: `python
phase2_p0_v811_filter_gradcam_validation.py`, output documented as
`results/phase2_p0_v811_filter_gradcam_validation_20260813.json`). No arguments — the script
`import pipeline as pl` and reads `pl.LAYER1_WEIGHTS_PATH`/`pl.LAYER2_WEIGHTS_PATH` directly,
so it always tracks whatever `pipeline.py` currently declares as production, with no risk of
the v811c-default footgun described above. **Note**: re-running this will overwrite the
dated-named output file if today's date matches; the script's naming convention
(`..._20260813.json`) is date-based, not run-based, so re-running on a different day produces
a differently-named file rather than a silent overwrite. Re-running on the SAME day as an
existing archived result would overwrite it — check the date before running.

## Whitening diagnostic

```
python phase2_whitening_pointinggame_diagnostic.py
```

Confirmed from source (`SRC_JSON = BASE / "results" /
"phase2_p0_v811_filter_gradcam_validation_20260813.json"` — this script **depends on** the
above script's output already existing; run the Filter XAI validation first). No arguments;
also `import pipeline as pl` directly. Reproduces
`results/phase2_whitening_peak_diagnostic_20260813/` (summary.json + contact_sheet.png +
peak_classification.csv).

## TFLite export / desktop validation

```
python export_mobile_tflite.py
```

Confirmed from source (line 24 docstring: `python export_mobile_tflite.py`). No arguments;
`BASE = Path(r"C:\My_Project\AIGC")` and the v811d/v811 checkpoint filenames are hardcoded
constants in the script (not CLI-configurable) — confirmed by reading past the docstring.
Runs the documented G1-G4 gate chain (ONNX export → TFLite conversion → load-check →
numerical-match-check) rather than treating file creation alone as success.

```
python verify_mobile_fft.py
```

Confirmed from source (line 12 docstring: `python verify_mobile_fft.py`; lines 17-19 hardcode
`L1 = BASE / "shufflenet_v2_layer1_v811d.pth"`, `L2 = BASE / "shufflenet_v2_layer2_v811.pth"`
— explicitly production checkpoints, not configurable). Three-level equivalence check
(spectrum tensor → full model logits → end-to-end hierarchical decision agreement).

```
python benchmark_mobile_artifacts.py
```

Confirmed from source (line 14 docstring: `python benchmark_mobile_artifacts.py`; `BASE`
hardcoded same as above). Produces fp32/fp16/dynamic-range-quant TFLite variants and evaluates
each over the full 769-image True Test Set — reproduces `results/mobile_deployment_benchmark.json`.

## Not confirmed — do not guess

- **Alibaba OOD filter recall for v8.11d specifically**: `AIGuard/eval_ali_ood_v811.py`
  defaults to v811c (line 31-32); the production-valid invocation would be:
  ```
  python AIGuard/eval_ali_ood_v811.py shufflenet_v2_layer1_v811d.pth shufflenet_v2_layer2_v811.pth
  ```
  This command IS confirmed runnable from the script's own docstring/arg-parsing (line 18:
  `python AIGuard/eval_ali_ood_v811.py [layer1_weights] [layer2_weights]`), so it is not a
  "TODO" in the sense of an unknown command — but no archived result from running it with
  these explicit args was found under `results/`, which is why the 98.1% figure is flagged
  UNVERIFIABLE in `RELEASE_RESULTS.md`. Running this command would be the correct way to
  produce that missing evidence (not done in this pass — read-only, no reruns).
- **True Test filter-recall-by-type breakdown**: `eval_truetest_filter_bytype_v811.py`
  defaults correctly to v811d/v811 (confirmed, lines 23-24), so:
  ```
  python eval_truetest_filter_bytype_v811.py
  ```
  is a confirmed-runnable command, but likewise has no archived output file found in
  `results/` in this pass.
- **iPhone on-device benchmark**: TODO — no script found in the repo that performs on-device
  (as opposed to desktop CPU) benchmarking. This is consistent with TODO.md's own statement
  that this Freeze Gate item is still pending.
