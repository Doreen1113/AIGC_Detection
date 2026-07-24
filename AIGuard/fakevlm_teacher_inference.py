"""
Phase 2 — FakeVLM teacher inference on FakeClue train fake images.

Model  : lingcco/fakeVLM (LLaVA-1.5-7B fine-tuned on FakeClue, BF16)
         Run with: fakevlm conda env (transformers==4.45.2)
Target : FakeClue train fake images (label=0), ~5,000 sampled
Output : results/fakevlm_teacher_outputs.jsonl  (one JSON per line)

Supports resume: skips images already written to the output file.

Usage:
    C:\\miniconda3\\envs\\fakevlm\\python.exe AIGuard/fakevlm_teacher_inference.py
    ... --n 5000 --seed 42
    ... --n 0        # all 19872
"""

import argparse, csv, json, random, time
from pathlib import Path
from collections import Counter, defaultdict
import torch
from PIL import Image
from transformers import LlavaForConditionalGeneration, AutoProcessor

BASE       = Path(r"C:\My_Project\AIGC")
MODEL_PATH = BASE / "FakeVLM_weights"
OUT_DIR    = BASE / "results"
OUT_DIR.mkdir(exist_ok=True)

# FakeVLM generates natural language explanations — no JSON forcing
PROMPT = (
    "Is this facial image real or fake? "
    "If fake, describe the specific artifacts or manipulations you can observe."
)


def load_model():
    print(f"Loading FakeVLM from {MODEL_PATH} ...")
    t0 = time.time()
    model = LlavaForConditionalGeneration.from_pretrained(
        str(MODEL_PATH),
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
        attn_implementation="eager",   # no flash-attn on Windows
    ).eval().cuda()
    processor = AutoProcessor.from_pretrained(str(MODEL_PATH))
    print(f"Loaded in {time.time()-t0:.1f}s")
    return model, processor


def infer_one(model, processor, image_path: str) -> dict:
    image = Image.open(image_path).convert("RGB")
    conversation = [{"role": "user", "content": [
        {"type": "image"},
        {"type": "text", "text": PROMPT},
    ]}]
    text = processor.apply_chat_template(conversation, add_generation_prompt=True)
    inputs = processor(text=text, images=image, return_tensors="pt").to(
        model.device, torch.bfloat16
    )
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=256, do_sample=False)
    generated = out[0][inputs["input_ids"].shape[1]:]
    response = processor.decode(generated, skip_special_tokens=True).strip()

    # Extract verdict from natural language
    low = response.lower()
    if "fake" in low and "real" not in low[:20]:
        verdict = "fake"
    elif "real" in low and "fake" not in low[:20]:
        verdict = "real"
    elif "fake" in low:
        verdict = "fake"
    else:
        verdict = "unknown"

    return {"verdict": verdict, "explanation": response}


def load_sample(n_target: int, seed: int) -> list:
    csv_path = BASE / "FakeClue" / "train_clean" / "labels.csv"
    rows = [r for r in csv.DictReader(open(csv_path, encoding="utf-8"))
            if r["label"] == "0"]
    rows = [r for r in rows if Path(r["path"]).exists()]
    print(f"Available fake images: {len(rows)}")

    if n_target == 0 or n_target >= len(rows):
        print(f"Using all {len(rows)}")
        return rows

    by_sub = defaultdict(list)
    for r in rows:
        by_sub[Path(r["path"]).parent.parent.name].append(r)

    rng = random.Random(seed)
    selected = []
    for sub, items in sorted(by_sub.items()):
        k = max(1, round(n_target * len(items) / len(rows)))
        selected.extend(rng.sample(items, min(k, len(items))))
    rng.shuffle(selected)
    selected = selected[:n_target]

    print(f"Sampled {len(selected)} (stratified):")
    for s, c in sorted(Counter(Path(r["path"]).parent.parent.name for r in selected).items()):
        print(f"  {s}: {c}")
    return selected


def load_done(out_path: Path) -> set:
    done = set()
    if out_path.exists():
        for line in out_path.read_text(encoding="utf-8").splitlines():
            try:
                done.add(json.loads(line)["path"])
            except Exception:
                pass
    return done


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n",    type=int, default=5000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out",  default="results/fakevlm_teacher_outputs.jsonl")
    args = parser.parse_args()

    out_path = BASE / args.out

    if not MODEL_PATH.exists():
        print(f"ERROR: FakeVLM weights not found at {MODEL_PATH}")
        return

    rows = load_sample(args.n, args.seed)
    done = load_done(out_path)
    if done:
        print(f"\nResuming: {len(done)} already done")
    todo = [r for r in rows if r["path"] not in done]
    print(f"Remaining: {len(todo)}\n")

    if not todo:
        print("All done.")
        return

    model, processor = load_model()

    fout = open(out_path, "a", encoding="utf-8", buffering=1)
    t_start = time.time()
    counts  = Counter()

    for i, row in enumerate(todo, 1):
        path = row["path"]
        t0   = time.time()
        pred = infer_one(model, processor, path)
        elapsed = time.time() - t0

        record = {
            "path":   path,
            "gt":     "fake",
            "subdir": Path(path).parent.parent.name,
            **pred,
        }
        fout.write(json.dumps(record, ensure_ascii=False) + "\n")

        v = pred["verdict"]
        counts[v] += 1

        done_total = i + len(done)
        avg = (time.time() - t_start) / i
        rem = (len(todo) - i) * avg
        h, s = divmod(int(rem), 3600); m = s // 60
        exp_short = pred["explanation"][:60].replace("\n", " ")
        print(
            f"[{done_total}/{len(rows)}] {Path(path).name[:24]:24s}  "
            f"{v:7s}  {elapsed:.1f}s  ETA {h}h{m:02d}m  | {exp_short}"
        )

    fout.close()
    total = time.time() - t_start
    print(f"\n{'='*55}")
    print(f"FakeVLM teacher inference complete")
    print(f"Processed: {len(todo)} in {total/60:.1f} min ({total/len(todo):.1f}s/img)")
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    print(f"Output: {out_path}")

    (OUT_DIR / "fakevlm_teacher_summary.txt").write_text(
        f"FakeVLM Teacher Inference\n"
        f"Date   : 2026-07-22\n"
        f"Model  : lingcco/fakeVLM\n"
        f"N      : {len(todo)}\n"
        f"Time   : {total/60:.1f} min ({total/len(todo):.1f}s/img)\n"
        f"Counts : {dict(counts)}\n",
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
