"""
Qwen2-VL Image Forensics Control Group Pipeline
================================================
Usage:
    # 執行整個測試資料夾
    python run_qwen_control.py --folder ./path/to/images
"""

import argparse
import json
import os
import csv
from pathlib import Path
import torch
from tqdm import tqdm
from PIL import Image
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor

# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
IMG_EXTS = {".jpg", ".jpeg", ".png", ".jfif", ".bmp", ".webp"}

SYSTEM_PROMPT = (
    "You are an expert in image forensics and facial manipulation detection.\n"
    "Analyze the provided facial image carefully and determine if it has been manipulated.\n\n"
    "You MUST respond strictly in the following format (do not include markdown block ticks):\n"
    "PREDICTION: [real / fake / filter]\n"
    "ARTIFACTS: [Select from: eye_enlarging, face_reshaping, over_smoothing, whitening, or none]\n"
    "REGIONS: [Select from: forehead, left_eye, right_eye, nose, left_cheek, right_cheek, mouth, jaw, or none]\n"
    "EXPLANATION: [A brief, professional one-sentence forensic explanation in English]\n"
)

def parse_qwen_output(text):
    prediction = "filter"
    artifact_types = []
    suspicious_region = []
    explanation = text.strip()
    
    lines = text.split("\n")
    for line in lines:
        line_clean = line.strip()
        if line_clean.upper().startswith("PREDICTION:"):
            pred_val = line_clean.split(":", 1)[1].strip().lower()
            if "real" in pred_val: prediction = "real"
            elif "fake" in pred_val: prediction = "fake"
            elif "filter" in pred_val: prediction = "filter"
            
        elif line_clean.upper().startswith("ARTIFACTS:"):
            art_val = line_clean.split(":", 1)[1].strip().lower()
            if "none" not in art_val:
                # 支援逗號或直槓分割
                artifact_types = [a.strip() for a in art_val.replace("|", ",").split(",") if a.strip()]
                
        elif line_clean.upper().startswith("REGIONS:"):
            reg_val = line_clean.split(":", 1)[1].strip().lower()
            if "none" not in reg_val:
                suspicious_region = [r.strip() for r in reg_val.replace("|", ",").split(",") if r.strip()]
                
        elif line_clean.upper().startswith("EXPLANATION:"):
            explanation = line_clean.split(":", 1)[1].strip()
            
    return prediction, artifact_types, suspicious_region, explanation

# ──────────────────────────────────────────────
# Main 
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Qwen2-VL Baseline Pipeline")
    parser.add_argument("--folder", required=True, help="Path to the test images folder")
    parser.add_argument("--output_dir", default=None, help="Output directory")
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device detected for Qwen2-VL: {device}")
    
    folder = args.folder
    out_dir = args.output_dir or os.path.join(folder, "qwen_control_output")
    os.makedirs(out_dir, exist_ok=True)

    image_files = sorted([
        p for p in Path(folder).iterdir()
        if p.suffix.lower() in IMG_EXTS
    ])[:20]  # 取前 20 張做定性分析表格
    
    print(f"Found {len(image_files)} images for control group evaluation.")
    print("Loading Qwen2-VL-7B-Instruct (this may take a while on Doreen's GPU)...")

    # 載入大模型
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-7B-Instruct", 
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
    if device == "cpu":
        model.to(device)

    results = []

    for i, img_path in enumerate(image_files, 1):
        print(f"[{i:3d}/{len(image_files)}] Processing {img_path.name}...")
        try:
            image = Image.open(img_path).convert("RGB")
            
            conversation = [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image},
                        {"type": "text", "text": SYSTEM_PROMPT},
                    ],
                }
            ]
            
            text = processor.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
            inputs = processor(images=image, texts=[text], padding=True, return_tensors="pt").to(device)

            with torch.no_grad():
                generated_ids = model.generate(**inputs, max_new_tokens=150)
                generated_ids_trimmed = [out_ids[len(in_ids):] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)]
                output_text = processor.batch_decode(
                    generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
                )[0]

            pred, artifacts, regions, exp = parse_qwen_output(output_text)
            
            r = {
                "image": img_path.name,
                "prediction": pred,
                "confidence": 1.0,  # VLM 預設給予 1.0 或留空
                "artifact_type": artifacts,
                "suspicious_region": regions,
                "explanation": exp,
                "qwen_raw_response": output_text
            }
            results.append(r)
            
        except Exception as e:
            print(f"Error processing {img_path.name}: {e}")
            results.append({
                "image": img_path.name,
                "prediction": "error",
                "confidence": 0.0,
                "artifact_type": [],
                "suspicious_region": [],
                "explanation": f"Inference failed: {str(e)}"
            })

    # Save summary CSV
    csv_path = os.path.join(out_dir, "qwen_summary.csv")
    csv_fields = ["image", "prediction", "confidence", "artifact_type", "suspicious_region", "explanation"]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            row = dict(r)
            row["artifact_type"] = "|".join(r.get("artifact_type", []))
            row["suspicious_region"] = "|".join(r.get("suspicious_region", []))
            writer.writerow(row)

    # Save all JSONs
    json_path = os.path.join(out_dir, "qwen_all_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}\nQwen2-VL Control Group Evaluation Complete!")
    print(f"CSV  → {csv_path}")
    print(f"JSON → {json_path}")

if __name__ == "__main__":
    main()