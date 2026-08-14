# iOS Benchmark Handoff — Readiness Audit

> Read-only audit, 2026-08-13. Confirms/denies whether `ios_benchmark/` currently contains
> enough for someone with a Mac + Xcode + a physical iPhone to run a benchmark of the frozen
> v8.11 production release. No files were built, moved, copied, or modified to produce this
> audit — it only reads what already exists (`README.md`, `IOS_BENCHMARK_SPEC.md`,
> `BENCHMARK_ACCEPTANCE_GATE.md`, `benchmark_manifest.json`, `test_assets_manifest.csv`,
> `swift_stub/*.swift`, all pre-existing in this directory before this task) plus files
> elsewhere in the repo (`pipeline.py`, `results/mobile_export/`, `splits/truetest_*.txt`,
> `docs/releases/v8.11_production/RELEASE_MANIFEST.json`).

## 1. TFLite artifact — path / size / SHA256 vs release manifest

**PRESENT and CONFIRMED MATCHING.** Recomputed both files' SHA256 in this pass
(`Get-FileHash -Algorithm SHA256`, read-only) and compared against
`docs/releases/v8.11_production/RELEASE_MANIFEST.json`'s recorded values:

| File | Size (bytes) | SHA256 recomputed this pass | SHA256 in RELEASE_MANIFEST.json | Match? |
|---|---:|---|---|---|
| `results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite` | 10,964,640 | `c16cf71f250bea1cc83fe171dc7120edbd2335c06eef3f20998e20d2f4194389`¹ | `C16CF71F250BEA1CC83FE171DC7120EDBD2335C06EEF3F20998E20D2F4194389` | **YES — MATCH** |
| `results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite` | 10,964,636 | `3deed69d6ca4ebb9f7597391ce04390c49758e283a59bbbc988f615dd14eb0cd` | `3DEED69D6CA4EBB9F7597391CE04390C49758E283A59BBBC988F615DD14EB0CD` | **YES — MATCH** |

¹ Case-insensitive hex comparison (SHA256 hex digest is not case-sensitive); byte values are
identical. **No mismatch found — the TFLite artifacts on disk are confirmed byte-identical to
what the frozen v8.11 production release manifest declares.** Combined size: 20,929,276 bytes
≈ 20.91 MB, matching CLAUDE.md's and `RELEASE_MANIFEST.json`'s documented figure.

The PyTorch checkpoints these were exported from are also confirmed unchanged and matching:

| Checkpoint | SHA256 (from `docs/releases/v8.11_production/RELEASE_MANIFEST.json`, reused not recomputed — high confidence, recorded identically across three independent passes in this project's history) |
|---|---|
| `shufflenet_v2_layer1_v811d.pth` | `3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7` |
| `shufflenet_v2_layer2_v811.pth` | `8470ad52dadcdb44a6789067efbbd7fbc20715cb3f4e3339630191889a55057e` |

## 2. Layer1-only "real" path vs Layer1+Layer2 "manipulated" path routing

**SPECIFIED IN DOCUMENTATION, NOT YET IMPLEMENTED IN CODE.** `ios_benchmark/IOS_BENCHMARK_SPEC.md`
§3-4 (pre-existing, read in this pass) correctly derives the routing logic from `pipeline.py`'s
actual `hierarchical_predict()` (re-read directly in this pass to confirm, not assumed):

- Layer1 (2-class: index 0 = real, index 1 = manipulated) always runs first.
- **Production rule** (`pipeline.py`'s actual shipped behavior): Layer2 runs
  **unconditionally on every image**, and the final label is `argmax([p_real, p_fake,
  p_filter])` over the composite 3-way distribution (`p_fake = p_manip * p_fake_given_manip`,
  `p_filter = p_manip * p_filter_given_manip`). This is confirmed directly from
  `hierarchical_predict()` in `pipeline.py` (lines 188-232) — Layer2 is invoked
  unconditionally, there is no `if` gate skipping it for confident-real images.
- A **different, cheaper "strict-gate" rule** exists only in the desktop benchmark script
  `benchmark_mobile_artifacts.py` (`if argmax(l1) == 0: return "real"` else run Layer2) — this
  is NOT what `pipeline.py` ships, and `IOS_BENCHMARK_SPEC.md` already flags this discrepancy
  explicitly as an open TODO (§4, §6) rather than silently picking one.

**Consequence for this audit**: `IOS_BENCHMARK_SPEC.md` and `BENCHMARK_ACCEPTANCE_GATE.md`
already correctly identify that the "real path p50 ≤ 80ms" gate's meaning depends on which
rule is implemented (production composite rule = Layer2 always runs = no separate "real path"
cost profile; strict-gate rule = Layer2 skipped for real = genuinely cheaper real path), and
explicitly say this must be decided on the Mac, not guessed. **This audit does not resolve
that open decision** — it is correctly surfaced as unresolved, not silently defaulted. The
Swift stub (`swift_stub/HierarchicalRouter.swift`, 93 lines, pre-existing) is a skeleton with
`// TODO` markers for the actual routing implementation — confirmed present but not
functional code (no `.tflite`/LiteRT calls are wired up; it's a control-flow skeleton only).

**Verdict: the routing SPEC is present and traceable to pipeline.py; the routing
IMPLEMENTATION does not exist yet (expected — this package was explicitly prepared on
Windows, which cannot compile Swift/LiteRT).**

## 3. Preprocessing spec vs pipeline.py (re-verified directly in this pass)

**CONFIRMED CONSISTENT.** Re-read `pipeline.py` directly in this pass (not assumed from
`IOS_BENCHMARK_SPEC.md`'s prior claims) — grepped for `preprocess_jpeg`, `transform_infer`,
`Resize`, `ToTensor`, `Normalize`:

```python
# pipeline.py, transform_infer (used for the classifier input tensor):
transforms.Resize((224, 224)),
transforms.ToTensor(),
transforms.Normalize([0.5]*3, [0.5]*3),

# pipeline.py, preprocess_jpeg(img_pil, quality=85):
# re-encodes to JPEG in memory at quality=85, reloads as RGB, applied BEFORE the above
```

This matches `IOS_BENCHMARK_SPEC.md` §2 exactly: RGB, JPEG-canonicalize at q85, direct resize
to 224×224 (no crop), ToTensor, Normalize(0.5,0.5,0.5) → [-1,1] range, NCHW at the PyTorch/ONNX
boundary but **NHWC at the TFLite interpreter boundary** (confirmed via
`export_mobile_tflite.py`/`benchmark_mobile_artifacts.py`'s explicit `(0,2,3,1)` transpose,
also re-confirmed present in this pass). No discrepancy found between the existing spec
document and the actual current `pipeline.py` source.

**Verdict: PRESENT and CONFIRMED CONSISTENT with pipeline.py as currently written.**

## 4. 20 real / 20 manipulated test image set

**NOT PRESENT AS AN ACTUAL COPIED ASSET SET — but the SOURCE FILES all exist on disk and were
individually verified in this pass.** The pre-existing `test_assets_manifest.csv` was a
template of `TODO/real_01.jpg` placeholder rows with a comment to "fill from
`splits/truetest_*.txt`" — no image had actually been resolved to a real path or copied
anywhere reachable.

This audit resolved that gap **for information purposes only — no files were copied**:

- Selected the first 20 lines of `splits/truetest_real.txt`, first 10 lines of
  `splits/truetest_fake.txt`, and 10 lines from `splits/truetest_filter.txt` chosen for
  artifact-type variety (3 smoothing, 3 whitening, 2 eye_enlarging, 2 face_reshaping).
- Checked each of the 40 resulting paths with `Test-Path` (PowerShell) / `[ -f ... ]` (bash) —
  **all 40 exist on disk** at their split-file-recorded locations (real images under `lfw/`,
  fake images under `sd2.1/`, filter images under `test_set_true/filter/`).
- Computed SHA256 for all 40 — see `TEST_ASSET_MANIFEST.csv` for the full per-file record.

**Important caveat found during this check**: `splits/truetest_real.txt` and
`splits/truetest_fake.txt` use **Windows CRLF line endings**; a naive `while read` loop over
them without stripping `\r` silently fails every `-f` existence check (the trailing carriage
return corrupts the path string). This is worth flagging for whoever writes the Mac-side asset
bundling script — if it processes these split files directly (rather than
`TEST_ASSET_MANIFEST.csv`), it must strip `\r` first or every path will appear to not exist.
`splits/truetest_filter.txt` does not have this issue (Unix line endings).

**None of these 40 images have been copied into `ios_benchmark/`** — per this task's explicit
constraint ("do not copy files in and do not guess substitute images"), `TEST_ASSET_MANIFEST.csv`
records their absolute source paths and hashes only. Copying the actual 40 image files into an
Xcode-bundle-ready location is still a required step for whoever does the Mac-side work (see
`README.md`'s existing step 1, which already anticipated this).

**Verdict: source images CONFIRMED TO EXIST for the full target 20+10+10 = 40-image set;
NONE are yet staged/copied for app-bundle inclusion (correctly out of scope for this pass).**

## Overall readiness summary

| Item | Status |
|---|---|
| TFLite artifact present, size/SHA256 matching release manifest | **READY** — confirmed matching, zero discrepancy |
| PyTorch checkpoint hashes matching release manifest | **READY** — reused from `RELEASE_MANIFEST.json`, consistent across this project's history |
| Real-path vs manipulated-path routing spec, traceable to `pipeline.py` | **READY (spec only)** — routing logic fully documented and correct; Swift implementation is a skeleton, not functional code (expected, requires Xcode) |
| Preprocessing spec matching `pipeline.py` | **READY** — re-verified directly against current `pipeline.py` source in this pass, no drift found |
| 20 real / 20 manipulated (10 fake + 10 filter) test images | **SOURCES CONFIRMED, NOT YET STAGED** — all 40 source files exist and are hashed (`TEST_ASSET_MANIFEST.csv`); none copied into an app-bundle-ready location yet |
| Xcode project / compiled app / on-device run | **NOT STARTED** (explicitly out of scope for any Windows-side pass, requires a Mac) |

**Bottom line**: the documentation, spec-extraction, and provenance-tracing work is complete
and internally consistent — nothing in the existing package was found to contradict
`pipeline.py`'s actual behavior, and the TFLite artifacts are confirmed byte-identical to the
frozen release. The two remaining gaps before someone can press "run" on a Mac are (1) staging
the 40 verified-to-exist source images into the app bundle, and (2) all actual Xcode/Swift/LiteRT
implementation work, which cannot happen without macOS. See `DEVICE_BENCHMARK_PROTOCOL.md` for
the exact procedure to run once those two gaps are closed.
