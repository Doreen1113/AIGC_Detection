# MAM Integration Notes

## Summary

This update adds a lightweight Multi-granularity Attention Module (MAM) to the
current AIGC/filter detection architecture.

The original main model was:

```text
image
  -> ShuffleNetV2 spatial branch
  -> FFT frequency branch
  -> concat
  -> Real / Fake / Filter classifier
```

The MAM model is:

```text
image
  -> ShuffleNetV2 conv feature map
  -> MAM attention
  -> attended spatial feature
  -> FFT frequency branch
  -> concat
  -> Real / Fake / Filter classifier
```

The old non-MAM model remains available. The pipeline only uses MAM when
`--use_mam` is passed.

## Added Files

### `AIGuard/models_mam.py`

Shared model definitions for training and inference:

- `FFTBranch`: same FFT magnitude branch used by the current 3-class model.
- `MultiGranularityAttention`: lightweight MAM v1.
- `ShuffleNetMAMBranch`: exposes ShuffleNetV2 feature maps, applies MAM, then
  global-pools the attended feature.
- `DualBranchMAMModel`: combines MAM spatial features with FFT features and
  outputs 3-class logits.

The model keeps `model.spatial_branch.conv5`, so the existing Grad-CAM++ target
layer still works.

### `AIGuard/train_3class_mam.py`

New training script for:

- Real / Fake / Filter classification.
- MAM attention supervision with pseudo masks.
- RetouchingFFHQ filter data already used by `train_3class_ffhq_v2.py`.

The script saves:

```text
shufflenet_v2_3class_mam.pth
results/3class_mam_val_results.csv
```

## Modified Files

### `pipeline.py`

Added:

- `MAM_WEIGHTS_PATH = os.path.join(BASE, "shufflenet_v2_3class_mam.pth")`
- `--use_mam` CLI flag.
- MAM model loading path.
- MAM attention visualization output when `--save_heatmap` is enabled.

Example:

```bash
python pipeline.py --image path/to/image.jpg --use_mam --save_heatmap
```

This produces the normal outputs plus:

```text
<image>_mam_attention.jpg
```

## Training Data Requirement

MAM works best with paired data:

```text
original FFHQ image <-> retouched FFHQ image
```

The training script searches these original-image folders:

```python
ORIGINAL_DIR_CANDIDATES = [
    os.path.join(BASE, "FFHQ"),
    os.path.join(BASE, "ffhq"),
    os.path.join(BASE, "ffhq_original"),
    os.path.join(BASE, "FFHQ_original"),
]
```

After extracting `FFHQ.zip`, place the original images in one of those folders,
or edit `ORIGINAL_DIR_CANDIDATES`.

For each filter image, the script tries to find a matching original by:

- exact filename
- filename stem
- first underscore-separated stem segment

If no original is found, the sample still trains classification, but its MAM
mask is all zeros.

## Pseudo Mask Generation

For paired filter images:

```text
mask = abs(retouched_image - original_image) > threshold
```

The current threshold is:

```python
MASK_DIFF_THRESHOLD = 18
```

This creates weak localization supervision for the MAM attention map.

## Loss

The MAM training objective is:

```text
loss = classification_loss + 0.2 * mam_attention_loss
```

Where:

- `classification_loss`: cross entropy for Real/Fake/Filter.
- `mam_attention_loss`: binary cross entropy between the MAM attention map and
  the pseudo manipulation mask.

The weight is controlled by:

```python
MAM_LOSS_WEIGHT = 0.2
```

## How To Train

1. Update `BASE` in `AIGuard/train_3class_mam.py`.
2. Make sure the normal dataset folders are present:

```text
AIGuard/real
AIGuard/fake
filter_data
FFHQ_four_process
FFHQ_megvii_four_process
FFHQ_ali_process
```

3. Extract FFHQ originals into one of the `ORIGINAL_DIR_CANDIDATES` folders.
4. Run:

```bash
python AIGuard/train_3class_mam.py
```

During startup, check:

```text
Paired filter images for MAM masks: X/Y
```

Higher `X` means better attention supervision.

## How To Run Inference

Use the old model:

```bash
python pipeline.py --image path/to/image.jpg
```

Use the MAM model:

```bash
python pipeline.py --image path/to/image.jpg --use_mam
```

Use the MAM model and save visualizations:

```bash
python pipeline.py --image path/to/image.jpg --use_mam --save_heatmap
```

## Notes

- Existing `.pth` weights are not compatible with `DualBranchMAMModel`.
- Train `shufflenet_v2_3class_mam.pth` before using `--use_mam`.
- Artifact type and level classifiers are unchanged.
- Grad-CAM++ is still available; MAM attention is an additional learned
  localization signal, not a replacement for the current explanation pipeline.

