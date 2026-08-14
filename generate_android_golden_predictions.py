"""
Stage the 40 Android benchmark test images and generate golden predictions.

Reads android_benchmark/TEST_ASSET_MANIFEST.csv, verifies each source image's
SHA256 against the manifest, copies it into android_benchmark/test_assets/,
then runs the frozen fp32 TFLite Layer1/Layer2 production checkpoints over
each image (same TFLiteRunner + hierarchical-routing logic as
benchmark_mobile_artifacts.py) to produce a golden-prediction reference file
for on-device parity comparison.

python generate_android_golden_predictions.py
"""
import csv
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import transforms

BASE = Path(r"C:\My_Project\AIGC")
sys.path.insert(0, str(BASE))
from pipeline import preprocess_jpeg  # noqa: E402

MANIFEST_CSV = BASE / "android_benchmark" / "TEST_ASSET_MANIFEST.csv"
ASSETS_DIR = BASE / "android_benchmark" / "test_assets"
GOLDEN_OUT = BASE / "android_benchmark" / "golden_outputs" / "golden_predictions_v811d_layer2v811.json"

L1_TFLITE = BASE / "results" / "mobile_export" / "layer1_v811d_tf" / "layer1_v811d_float32.tflite"
L2_TFLITE = BASE / "results" / "mobile_export" / "layer2_v811_tf" / "layer2_v811_float32.tflite"

transform_infer = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3),
])


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class TFLiteRunner:
    def __init__(self, path):
        import tensorflow as tf
        self.interp = tf.lite.Interpreter(model_path=str(path))
        self.interp.allocate_tensors()
        self.inp = self.interp.get_input_details()[0]
        self.outp = self.interp.get_output_details()[0]
        self.nhwc = list(self.inp["shape"])[-1] == 3
        self.dtype = self.inp["dtype"]

    def __call__(self, x_nchw):
        a = x_nchw.numpy() if torch.is_tensor(x_nchw) else x_nchw
        if self.nhwc:
            a = np.transpose(a, (0, 2, 3, 1))
        self.interp.set_tensor(self.inp["index"], a.astype(self.dtype))
        self.interp.invoke()
        return self.interp.get_tensor(self.outp["index"])


def softmax(v):
    e = np.exp(v - v.max(axis=-1, keepdims=True))
    return e / e.sum(axis=-1, keepdims=True)


def main():
    print(f"Loading fp32 TFLite artifacts...")
    for f in (L1_TFLITE, L2_TFLITE):
        assert f.exists(), f"missing TFLite artifact: {f}"
    l1_sha = sha256_of(L1_TFLITE)
    l2_sha = sha256_of(L2_TFLITE)
    print(f"  layer1 sha256: {l1_sha}")
    print(f"  layer2 sha256: {l2_sha}")
    r1, r2 = TFLiteRunner(L1_TFLITE), TFLiteRunner(L2_TFLITE)

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    GOLDEN_OUT.parent.mkdir(parents=True, exist_ok=True)

    rows = list(csv.DictReader(open(MANIFEST_CSV, encoding="utf-8")))
    print(f"\nManifest rows: {len(rows)}")

    records = []
    mismatches = []
    routing_mismatches = []

    for i, row in enumerate(rows, start=1):
        src = Path(row["asset_path"])
        category = row["category"]
        subtype = row["artifact_subtype"] or None
        expected_sha = row["sha256"].strip().lower()
        expected_routing = row["notes"].split("target routing: ")[-1].strip()

        assert src.exists(), f"source image missing: {src}"
        actual_sha = sha256_of(src)
        if actual_sha != expected_sha:
            mismatches.append(str(src))

        # stage a copy with a stable, ordered name
        subtype_tag = f"_{subtype}" if subtype else ""
        dest_name = f"{i:02d}_{category}{subtype_tag}_{src.name}"
        dest = ASSETS_DIR / dest_name
        shutil.copy2(src, dest)

        # inference: same preprocessing + hierarchical routing as production
        pil = preprocess_jpeg(Image.open(src).convert("RGB"), quality=85)
        x = transform_infer(pil).unsqueeze(0)

        o1 = r1(x)[0]
        p1 = softmax(o1)
        if int(np.argmax(p1)) == 0:
            pred = "real"
            actual_routing = "layer1_only"
            p_real, p_fake, p_filter = float(p1[0]), None, None
            confidence = float(p1[0])
        else:
            o2 = r2(x)[0]
            p2 = softmax(o2)
            cls_idx = int(np.argmax(p2))
            pred = "fake" if cls_idx == 0 else "filter"
            actual_routing = f"layer1_then_layer2_{pred}"
            p_real = float(p1[0])
            p_fake = float(p2[0])
            p_filter = float(p2[1])
            confidence = float(p1[1] * p2[cls_idx])

        if actual_routing != expected_routing:
            routing_mismatches.append((str(src), expected_routing, actual_routing))

        records.append({
            "index": i,
            "staged_filename": dest_name,
            "source_path": str(src),
            "source_sha256": actual_sha,
            "category": category,
            "artifact_subtype": subtype,
            "expected_routing": expected_routing,
            "prediction": pred,
            "routing_taken": actual_routing,
            "p_real": p_real,
            "p_fake": p_fake,
            "p_filter": p_filter,
            "confidence": confidence,
        })
        print(f"  [{i:2d}/40] {category:<11s} {subtype_tag[1:] or '-':<15s} -> {pred:<7s} "
              f"(conf={confidence:.4f})  {'OK' if actual_sha == expected_sha else 'SHA MISMATCH'}")

    print(f"\nSHA256 mismatches: {len(mismatches)}")
    print(f"Routing mismatches vs manifest's declared target: {len(routing_mismatches)}")
    for src, exp, act in routing_mismatches:
        print(f"  {src}: expected={exp} actual={act}")

    output = {
        "release": "v8.11_production",
        "checkpoint_layer1": "shufflenet_v2_layer1_v811d.pth",
        "checkpoint_layer1_sha256": "3c61cf6886d2f9d4871b52749a15fd4e1b979d121c664ba85d9b069194c290b7",
        "checkpoint_layer2": "shufflenet_v2_layer2_v811.pth",
        "checkpoint_layer2_sha256": "8470ad52dadcdb44a6789067efbbd7fbc20715cb3f4e3339630191889a55057e",
        "tflite_layer1_path": "results/mobile_export/layer1_v811d_tf/layer1_v811d_float32.tflite",
        "tflite_layer1_sha256": l1_sha,
        "tflite_layer2_path": "results/mobile_export/layer2_v811_tf/layer2_v811_float32.tflite",
        "tflite_layer2_sha256": l2_sha,
        "source_manifest": "android_benchmark/TEST_ASSET_MANIFEST.csv",
        "generated_by": "generate_android_golden_predictions.py (desktop fp32 TFLite, CPU)",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "comparison_policy": "label-level only (real/fake/filter match) -- see DEVICE_BENCHMARK_PROTOCOL.md gate 7; bit-exact probability match is NOT required",
        "n_images": len(records),
        "n_sha256_mismatches": len(mismatches),
        "n_routing_mismatches_vs_manifest": len(routing_mismatches),
        "predictions": records,
    }
    GOLDEN_OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nSaved golden predictions -> {GOLDEN_OUT}")
    print(f"Staged {len(records)} images -> {ASSETS_DIR}")

    assert not mismatches, f"{len(mismatches)} SHA256 mismatches -- refusing to call this a clean golden set"


if __name__ == "__main__":
    main()
