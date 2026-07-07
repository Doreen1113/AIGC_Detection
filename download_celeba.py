"""
下載 CelebA 資料集（real face images）用於補充 real class 訓練資料。
執行：python download_celeba.py

下載來源：HuggingFace flwrlabs/celeba
輸出：C:\\My_Project\\AIGC\\celeba_real\\  (jpg images)
"""

import os
from datasets import load_dataset
from PIL import Image

OUT_DIR  = r"C:\My_Project\AIGC\celeba_real"
MAX_IMGS = 30000   # 取 3 萬張就夠

os.makedirs(OUT_DIR, exist_ok=True)

print("Loading CelebA from HuggingFace (flwrlabs/celeba)...")
print("First run will download ~1.5GB, please wait...\n")

ds = load_dataset("flwrlabs/celeba", split="train", trust_remote_code=True)
total = min(MAX_IMGS, len(ds))
print(f"Total available: {len(ds)} | Saving: {total}\n")

for i in range(total):
    item = ds[i]
    img = item["image"]
    if not isinstance(img, Image.Image):
        img = Image.fromarray(img)
    img.convert("RGB").save(os.path.join(OUT_DIR, f"celeba_{i:06d}.jpg"),
                            quality=95)
    if (i + 1) % 1000 == 0:
        print(f"  Saved {i+1}/{total}")

print(f"\nDone. {total} images saved to {OUT_DIR}")
