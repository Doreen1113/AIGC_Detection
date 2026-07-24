"""
Structured explanation pipeline — single image inference.
Schema v2.0.0 output (thin wrapper around pipeline.py).

Usage (base env):
    python explainability/explain.py --image path/to/face.jpg
    python explainability/explain.py --image path/to/face.jpg --save_heatmap
"""

import argparse
import json
import os
import sys
import torch

BASE = r"C:\My_Project\AIGC"
sys.path.insert(0, BASE)

from pipeline import (
    DualBranchModel,
    GradCAMPlusPlus,
    build_artifact_model,
    RegionHead,
    WEIGHTS_PATH,
    ARTIFACT_WEIGHTS_PATH,
    REGION_HEAD_PATH,
    run_single,
)


def main():
    parser = argparse.ArgumentParser(
        description="Single-image AIGC/filter detection with schema v2.0.0 output."
    )
    parser.add_argument("--image", required=True, help="Path to input face image")
    parser.add_argument("--save_heatmap", action="store_true",
                        help="Save Grad-CAM overlay to explanation_output/")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = DualBranchModel(num_classes=3).to(device)
    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    model.eval()

    gradcam = GradCAMPlusPlus(model, model.spatial_branch.conv5)

    artifact_model = None
    if os.path.exists(ARTIFACT_WEIGHTS_PATH):
        artifact_model = build_artifact_model().to(device)
        artifact_model.load_state_dict(
            torch.load(ARTIFACT_WEIGHTS_PATH, map_location=device))
        artifact_model.eval()

    region_head = None
    if os.path.exists(REGION_HEAD_PATH):
        region_head = RegionHead().to(device)
        region_head.load_state_dict(
            torch.load(REGION_HEAD_PATH, map_location=device))
        region_head.eval()

    out_dir = os.path.join(BASE, "explanation_output")
    os.makedirs(out_dir, exist_ok=True)

    result = run_single(
        args.image, model, gradcam, artifact_model, region_head, device,
        save_heatmap=args.save_heatmap,
        output_dir=out_dir,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
