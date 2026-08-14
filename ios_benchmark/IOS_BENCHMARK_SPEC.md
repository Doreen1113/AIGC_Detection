# iOS Benchmark Spec — extracted from the production Python pipeline

Source of truth for every value below: `pipeline.py`, `mobile_fft.py`,
`export_mobile_tflite.py`, `benchmark_mobile_artifacts.py`, and
`results/mobile_deployment_benchmark.json`, all read on 2026-08-13. Anything
that could not be confirmed from these files is marked **TODO** — do not
guess or invent a value for those.

## 1. Model files

| Layer | Checkpoint (PyTorch, training) | fp32 TFLite (verified deployable) | Role |
|---|---|---|---|
| Layer1 | `shufflenet_v2_layer1_v811d.pth` | `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite` | real vs manipulated (2-class) |
| Layer2 | `shufflenet_v2_layer2_v811.pth` | `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite` | fake vs filter (2-class), only runs if Layer1 says manipulated |

Both are `DualBranchModel(num_classes=2)`: a ShuffleNetV2-x1.0 spatial branch
(1024-dim, ImageNet-pretrained backbone, `fc` replaced with `Identity`)
concatenated with a 256-dim FFT branch, fed into `Linear(1280,512)→ReLU→
Dropout(0.3)→Linear(512,2)`. The FFT branch used for TFLite export is
`FFTBranchMobile` (`mobile_fft.py`) — a fixed-size DFT reformulated as
constant matrix multiplications (`MatMul`/`Mul`/`Add`/`Sqrt`/`Log` only, all
TFLite builtin ops), mathematically exact vs. the training-time
`torch.fft.fft2`+`fftshift` branch (~1e-5 max abs error on log-magnitude,
verified in `verify_mobile_fft.py`). **No retraining was needed** — the
original `.pth` weights load into the mobile module unchanged.

**Combined size**: 20.91 MB fp32 (both `.tflite` files together — confirmed
in `results/mobile_deployment_benchmark.json`, `tflite_float32.size_mb =
20.913387298583984`).

**fp16**: confirmed NOT usable — `tflite_float16` fails to load
(`RuntimeError: ... CONV_2D ... failed to prepare`, per
`mobile_deployment_benchmark.json`). Do not attempt fp16 on iOS without
first fixing this on the export side (out of scope for this package).

**int8 (dynamic-range quant)**: loads, but is not usable — True Test recall
collapses to filter=0.0%, fake=0.0%, real=100.0% (i.e. it always predicts
"real"), confirmed in the same JSON. Do not use for the benchmark.

**Only the fp32 artifacts are in scope for the iPhone benchmark.**

**Desktop reference numbers** (fp32 TFLite, CPU, from
`mobile_deployment_benchmark.json`, for iOS-vs-desktop comparison):
- size: 20.91 MB combined
- latency: 14.4 ms/image (Windows desktop CPU, two-stage worst case)
- decision agreement vs PyTorch reference: 100% (1.0)
- True Test recall: filter 93.6%, real 68.4%, fake 99.6%

> Note: the 68.4% "real" recall here is measured under
> `benchmark_mobile_artifacts.py`'s simplified strict-gate routing rule
> (see §4 below), which is **not** the exact rule `pipeline.py` uses in
> production. Don't conflate the two — see the routing note in §4.

## 2. Input preprocessing (must match exactly)

Source: `pipeline.py` `preprocess_jpeg()` + `transform_infer`.

1. Load image, convert to **RGB** (`Image.open(path).convert("RGB")`).
2. **JPEG canonicalization**: re-encode the image as JPEG at **quality=85**
   in memory, then re-decode it back to a PIL RGB image
   (`img_pil.save(buf, format="JPEG", quality=85)` → reopen). This step is
   controlled by a `jpeg_preprocess` flag and is **on by default** in
   production (`--no_jpeg_preproc` to disable, not used in production
   runs). The iOS benchmark should replicate this: re-encode each test
   image through `UIImage.jpegData(compressionQuality:)`-equivalent
   **before** feeding it to the model, matching quality≈85. TODO: confirm
   the exact iOS JPEG quality parameter that best matches libjpeg quality=85
   used by Pillow — quality scales are not perfectly portable across
   encoders; treat as "close" not "bit-exact," and note this as a possible
   (probably negligible) source of numeric drift vs. desktop.
3. **Resize**: `transforms.Resize((224, 224))` — this is a direct resize to
   224×224, **not** a resize-then-center-crop (both target dims are given
   explicitly, so `Resize` stretches/squashes to exactly 224×224 rather than
   preserving aspect ratio). No cropping step exists anywhere in
   `transform_infer`.
4. **Tensor conversion**: `transforms.ToTensor()` — HWC uint8 [0,255] → CHW
   float32 [0,1].
5. **Normalization**: `transforms.Normalize([0.5,0.5,0.5], [0.5,0.5,0.5])` —
   i.e. `(x - 0.5) / 0.5`, mapping [0,1] → **[-1, 1]** per channel.
6. **Channel order at the PyTorch/ONNX boundary**: **RGB**, **NCHW**
   (batch, channel, height, width) — this is what `torch.onnx.export` sees.
7. **Channel order at the TFLite boundary**: `onnx2tf` converts the graph to
   **NHWC** (channels-last). `export_mobile_tflite.py` and
   `benchmark_mobile_artifacts.py` both explicitly transpose
   `(0,2,3,1)` (NCHW→NHWC) before calling `interpreter.set_tensor()`,
   detected via `input_details[0]["shape"][-1] == 3`. **The iOS app must
   feed the `.tflite` interpreter NHWC RGB float32 tensors, normalized to
   [-1,1]**, not NCHW.
8. Face-presence gate (`has_face()`, MediaPipe FaceLandmarker) runs in
   production **before** the classifier, on the JPEG-canonicalized image.
   Whether to replicate the face gate in the benchmark harness: **TODO** —
   the benchmark test set (`test_assets_manifest.csv`) is expected to be
   pre-vetted face crops, so this is likely fine to skip for a pure
   inference-latency benchmark, but confirm intent before excluding it if
   the Mac-side harness will also be used for accuracy validation, not just
   latency.

No mean/std other than 0.5/0.5/0.5 is used anywhere in the inference path.
There is no per-channel ImageNet normalization despite the ShuffleNetV2
backbone being ImageNet-pretrained — confirmed from `transform_infer` in
`pipeline.py`, used consistently for both training-shape inference and the
mobile TFLite path (`transform_infer` is identical in
`export_mobile_tflite.py` / `benchmark_mobile_artifacts.py`).

## 3. Layer1 output → real / manipulated decision

`DualBranchModel(num_classes=2)` for Layer1 outputs 2 logits. Class index
convention (from `hierarchical_predict()` in `pipeline.py` and
`CLASSES = ["real", "fake", "filter"]`): **index 0 = real, index 1 =
manipulated** (fake ∪ filter, collapsed into one class for Layer1's
training).

```
l1_probs = softmax(l1_logits)
p_real   = l1_probs[0]
p_manip  = l1_probs[1]
```

## 4. Layer2 output → fake / filter decision, and final routing rule

Layer2 also outputs 2 logits, index convention **0 = fake, 1 = filter**
(from `p_fake_given_manip, p_filter_given_manip = l2_probs[0], l2_probs[1]`
in `pipeline.py`).

**Production routing rule** (`hierarchical_predict()` in `pipeline.py`,
this is what a faithful iOS replica should implement):

```
l1_probs = softmax(layer1(x))
p_real, p_manip = l1_probs[0], l1_probs[1]

l2_probs = softmax(layer2(x))   # Layer2 ALWAYS runs, unconditionally
p_fake_given_manip, p_filter_given_manip = l2_probs[0], l2_probs[1]

p_fake   = p_manip * p_fake_given_manip
p_filter = p_manip * p_filter_given_manip

prediction = argmax([p_real, p_fake, p_filter])   # composite 3-way softmax
```

Note this is a **composite-probability argmax**, not a hard "if Layer1 says
real, stop" gate — Layer2 always runs and both models' outputs are combined
into one 3-way distribution before taking argmax. In the vast majority of
cases this is equivalent to a strict Layer1 gate (`p_real > 0.5` almost
always wins outright, since then both manipulated components must sum to
`< 0.5`), but it is not exactly identical at the margin.

**Separate, simplified rule used only for the desktop TFLite benchmark
script** (`benchmark_mobile_artifacts.py`'s `hierarchical()`), included here
because it's the source of the 14.4ms/93.6%/68.4%/99.6% desktop reference
numbers in §1 — **do not use this as the iOS implementation**, it's a
cheaper approximation used only to skip Layer2 compute when Layer1 is
confident:

```
if argmax(softmax(l1_logits)) == 0:  # real
    return "real"
else:
    return "fake" if argmax(softmax(l2_logits)) == 0 else "filter"
```

This strict-gate version only invokes Layer2 when Layer1's argmax is
"manipulated" — cheaper on-device (skips Layer2 for confident-real images),
and is the reason the README's benchmark protocol separates "real path"
(Layer1-only cost) from "manipulated path" (Layer1+Layer2 cost) as two
different latency measurements. **TODO for the Mac implementation**: decide
whether the iOS benchmark app implements the exact production composite-
probability rule (§ "production routing rule" above, always runs both
layers) or the strict-gate approximation (skips Layer2 for real images) —
they very rarely disagree on the final label, but they have **different
latency profiles** for real images (one always pays the Layer2 cost, the
other doesn't), which materially changes what "real path p50" means. The
benchmark protocol in `BENCHMARK_ACCEPTANCE_GATE.md` assumes the
Layer1-only cost for the real path, i.e. the **strict-gate rule** — confirm
this matches what's actually shipped in `pipeline.py` before treating the
gate numbers as comparable to production behavior.

## 5. Output schema (informational, not required for a benchmark-only app)

The full production JSON schema (`schema_version: "2.1.0"`, includes
`artifact_types`, `suspicious_regions`, `explanation` text, Grad-CAM
heatmap paths) is defined in `pipeline.py`'s `run_single()`. **Out of
scope** for this benchmark harness — the benchmark app only needs
prediction (real/fake/filter) + per-layer confidence to compute
`prediction_consistency` against desktop fp32 TFLite output; it does not
need to reproduce artifact-type classification, region heatmaps, or
explanation text.

## 6. Confirmed vs TODO summary

**Confirmed from source:**
- Input: 224×224 RGB, direct resize (no crop), ToTensor, Normalize(0.5,0.5).
- JPEG canonicalization at quality=85 before resize.
- NCHW at the PyTorch/ONNX layer; **NHWC** at the TFLite interpreter layer.
- Value range fed to the model: [-1, 1] per channel.
- Layer1 classes: [0]=real, [1]=manipulated. Layer2 classes: [0]=fake,
  [1]=filter.
- Production composite-probability routing rule (§4).
- Model sizes: 20.91 MB combined fp32; fp16 unusable; int8 unusable.
- Desktop CPU fp32 latency reference: 14.4 ms/image two-stage worst case.

**TODO — must be resolved on the Mac / by whoever owns the iOS work, not
guessed:**
- Exact iOS-side JPEG quality parameter that best matches Pillow
  quality=85 (encoder differences).
- Whether the benchmark harness should apply the MediaPipe face-presence
  gate, or assume all test images are pre-vetted face crops.
- Whether the iOS implementation should use the exact production
  composite-probability rule (always runs Layer2) or the strict-gate
  approximation (skips Layer2 for confident-real) — this changes what the
  "real path" latency number in `BENCHMARK_ACCEPTANCE_GATE.md` actually
  measures.
- CoreML vs LiteRT (TensorFlowLiteSwift) as the on-device runtime — this
  package assumes LiteRT since that's the format already exported and
  verified (`.tflite`), but CoreML conversion was never attempted or
  verified in this project. If CoreML is preferred for iOS performance
  reasons, a new conversion + G1-G4-style verification pass (see
  `export_mobile_tflite.py`'s gate methodology) is needed first — do not
  assume CoreML conversion "just works" without re-verifying numerics,
  the same way the original ONNX→TFLite path silently produced an
  unloadable artifact (`ONNX_DFT` custom op) before this was caught.
- Device model(s) to test on, iOS version(s), and number of threads to
  configure the LiteRT interpreter with — none of these are specified
  anywhere in the existing Python code (which only ever ran on desktop
  CPU) and must be decided when the physical device is available.
