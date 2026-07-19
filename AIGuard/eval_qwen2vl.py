"""
Qwen2-VL control group inference.

對 FakeClue test + AIGuard unseen + WildDeepfake test 各取樣 20 張圖，
讓 Qwen2-VL-7B-Instruct 判斷 real / fake / filter，
輸出 JSON 供 paper qualitative comparison。

Usage:
    python AIGuard/eval_qwen2vl.py
    python AIGuard/eval_qwen2vl.py --n 20 --out results/qwen2vl_results.json
"""
import argparse, json, csv, random
from pathlib import Path
import torch

BASE = Path(r"C:\My_Project\AIGC")

PROMPT = (
    "You are an expert in image forensics and facial manipulation detection.\n"
    "Analyze the provided facial image carefully and determine if it has been manipulated.\n\n"
    "Classify it as one of:\n"
    "- real: an authentic, unmodified photograph of a real person\n"
    "- fake: a deepfake or AI-generated/synthesized face (identity replaced or fully generated)\n"
    "- filter: a real person's face processed with beauty filters "
    "(e.g. skin smoothing, eye enlarging, face whitening, face reshaping) — identity preserved\n\n"
    "Reply in this exact JSON format:\n"
    "{\"verdict\": \"real\" | \"fake\" | \"filter\", "
    "\"confidence\": 0.0-1.0, "
    "\"reason\": \"one sentence explanation\"}"
)


def load_model():
    from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
    print("Loading Qwen2-VL-7B-Instruct...")
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        "Qwen/Qwen2-VL-7B-Instruct",
        torch_dtype=torch.float16,
        device_map="auto",
    )
    processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-7B-Instruct")
    print("Model loaded.")
    return model, processor


def infer_one(model, processor, image_path: str) -> dict:
    from qwen_vl_utils import process_vision_info
    messages = [{"role": "user", "content": [
        {"type": "image", "image": image_path},
        {"type": "text",  "text": PROMPT},
    ]}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, _ = process_vision_info(messages)
    inputs = processor(text=[text], images=image_inputs, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=128, do_sample=False)
    generated = out[0][inputs.input_ids.shape[1]:]
    response = processor.decode(generated, skip_special_tokens=True).strip()
    try:
        start = response.find("{")
        end   = response.rfind("}") + 1
        return json.loads(response[start:end])
    except Exception:
        return {"verdict": "unknown", "confidence": 0.0, "reason": response[:200]}


def sample_fakeclue(n):
    rows = list(csv.DictReader(open(BASE / "FakeClue/test_clean/labels.csv", encoding="utf-8")))
    real_rows = [r for r in rows if r["label"] == "1"]
    fake_rows = [r for r in rows if r["label"] == "0"]
    sampled = random.sample(real_rows, min(n//2, len(real_rows))) + \
              random.sample(fake_rows, min(n//2, len(fake_rows)))
    return [{"path": r["path"], "gt": "real" if r["label"]=="1" else "fake",
             "source": "FakeClue"} for r in sampled]


def sample_unseen(n):
    lines = (BASE / "AIGuard/unseen/clean_output/clean_paths.txt").read_text().splitlines()
    real = [p for p in lines if Path(p).name.lower().startswith("real")]
    fake = [p for p in lines if Path(p).name.lower().startswith("fake")]
    items = random.sample(real, min(n//2, len(real))) + random.sample(fake, min(n//2, len(fake)))
    return [{"path": p, "gt": "real" if Path(p).name.lower().startswith("real") else "fake",
             "source": "AIGuard_unseen"} for p in items]


def sample_wilddeepfake(n):
    lines = (BASE / "WildDeepfake_subset/images/clean_output/clean_paths.txt").read_text().splitlines()
    real = [p for p in lines if Path(p).name.startswith("test_") and "/real/" in p.replace("\\","/")]
    fake = [p for p in lines if Path(p).name.startswith("test_") and "/fake/" in p.replace("\\","/")]
    items = random.sample(real, min(n//2, len(real))) + random.sample(fake, min(n//2, len(fake)))
    return [{"path": p, "gt": "real" if "/real/" in p.replace("\\","/") else "fake",
             "source": "WildDeepfake"} for p in items]


def sample_filter(n):
    lines = (BASE / "filter_data/clean_output/clean_paths.txt").read_text().splitlines()
    items = random.sample(lines, min(n, len(lines)))
    return [{"path": p, "gt": "filter", "source": "filter_data"} for p in items]


def sample_truetest(n_each):
    real_paths  = (BASE / "splits/truetest_real.txt").read_text().splitlines()
    fake_paths  = (BASE / "splits/truetest_fake.txt").read_text().splitlines()
    filter_paths = list((BASE / "test_set_true/filter").glob("*.*"))
    filter_paths = [str(p) for p in filter_paths if p.suffix.lower() in {".jpg",".jpeg",".png"}]

    items = (
        [{"path": p, "gt": "real",   "source": "truetest_real"}   for p in random.sample(real_paths,   min(n_each, len(real_paths)))]
      + [{"path": p, "gt": "fake",   "source": "truetest_fake"}   for p in random.sample(fake_paths,   min(n_each, len(fake_paths)))]
      + [{"path": p, "gt": "filter", "source": "truetest_filter"} for p in random.sample(filter_paths, min(n_each, len(filter_paths)))]
    )
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=20, help="Images per dataset")
    parser.add_argument("--out", default="results/qwen2vl_results.json")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--truetest", action="store_true", help="Run on True test set instead")
    args = parser.parse_args()

    random.seed(args.seed)

    if args.truetest:
        samples = sample_truetest(n_each=args.n)
    else:
        samples = (
            sample_fakeclue(args.n) +
            sample_unseen(args.n) +
            sample_wilddeepfake(args.n) +
            sample_filter(args.n)
        )
    print(f"Total samples: {len(samples)}")

    model, processor = load_model()

    results = []
    for i, item in enumerate(samples):
        print(f"[{i+1}/{len(samples)}] {item['source']} gt={item['gt']} {Path(item['path']).name}")
        pred = infer_one(model, processor, item["path"])
        row = {**item, **pred}
        results.append(row)
        print(f"  → verdict={pred.get('verdict')}  conf={pred.get('confidence')}  reason={pred.get('reason','')[:80]}")

    out_path = BASE / args.out
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved {len(results)} results → {out_path}")

    # Accuracy summary: per-source and per-class
    from collections import defaultdict
    correct_src = defaultdict(int)
    total_src   = defaultdict(int)
    correct_cls = defaultdict(int)
    total_cls   = defaultdict(int)
    for r in results:
        src, gt = r["source"], r["gt"]
        verdict = r.get("verdict")
        total_src[src] += 1
        total_cls[gt]  += 1
        if verdict == gt:
            correct_src[src] += 1
            correct_cls[gt]  += 1
    print("\n=== Qwen2-VL Accuracy by Source ===")
    for src in total_src:
        print(f"  {src}: {correct_src[src]}/{total_src[src]} = {correct_src[src]/total_src[src]:.2%}")
    print("\n=== Qwen2-VL Accuracy by Class ===")
    for cls in ("real", "fake", "filter"):
        if total_cls[cls]:
            print(f"  {cls}: {correct_cls[cls]}/{total_cls[cls]} = {correct_cls[cls]/total_cls[cls]:.2%}")
    total_all   = sum(total_cls.values())
    correct_all = sum(correct_cls.values())
    print(f"\n  Overall: {correct_all}/{total_all} = {correct_all/total_all:.2%}")


if __name__ == "__main__":
    main()
