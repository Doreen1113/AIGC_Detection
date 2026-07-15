"""
3-class + FFT + MAM attention branch.

This script keeps the current Real/Fake/Filter objective and adds a weak
localization objective for MAM. Filter images with a matching FFHQ original get
a pseudo mask from absolute image difference; all unpaired/real/fake samples use
an all-zero mask.

python AIGuard/train_3class_mam.py
"""
import os
import random
import time
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.transforms import functional as TF

from models_mam import DualBranchMAMModel


BASE = r"C:\My_Project\AIGC"
REAL_DIR = os.path.join(BASE, "AIGuard", "real")
FAKE_DIR = os.path.join(BASE, "AIGuard", "fake")
FILTER_DIR = os.path.join(BASE, "filter_data")
FFHQ_DIR = os.path.join(
    BASE, "FFHQ_four_process", "Whitening_Smoothing_FaceLifting_EyeEnlarging"
)
MEGVII_DIR = os.path.join(
    BASE, "FFHQ_megvii_four_process", "Whitening_Smoothing_FaceLifting_EyeEnlarging"
)
ALI_DIR = os.path.join(BASE, "FFHQ_ali_process")

# Put FFHQ.zip contents here, or change this list to the extracted original dir.
ORIGINAL_DIR_CANDIDATES = [
    os.path.join(BASE, "FFHQ"),
    os.path.join(BASE, "ffhq"),
    os.path.join(BASE, "ffhq_original"),
    os.path.join(BASE, "FFHQ_original"),
]

WEIGHTS_PATH = os.path.join(BASE, "shufflenet_v2_3class_mam.pth")
RESULTS_CSV = os.path.join(BASE, "results", "3class_mam_val_results.csv")

CLASSES = ["real", "fake", "filter"]
N_PER_SUB = 6000
EPOCHS = 15
BATCH_SIZE = 48
LR = 1e-3
VAL_RATIO = 0.1
MAM_LOSS_WEIGHT = 0.2
MASK_DIFF_THRESHOLD = 18
IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".jfif"}


class JointTransform:
    def __init__(self, train=True):
        self.train = train
        self.jitter = transforms.ColorJitter(
            brightness=0.2, contrast=0.2, saturation=0.2
        )
        self.normalize = transforms.Normalize([0.5] * 3, [0.5] * 3)

    def __call__(self, image, mask):
        image = image.resize((224, 224), Image.BILINEAR)
        mask = mask.resize((224, 224), Image.BILINEAR)

        if self.train and random.random() < 0.5:
            image = TF.hflip(image)
            mask = TF.hflip(mask)
        if self.train:
            image = self.jitter(image)
            if random.random() < 0.05:
                image = TF.to_grayscale(image, num_output_channels=3)

        image_tensor = self.normalize(TF.to_tensor(image))
        mask_tensor = TF.to_tensor(mask.convert("L"))
        mask_tensor = (mask_tensor > 0.15).float()
        return image_tensor, mask_tensor


class MAMFaceDataset(Dataset):
    def __init__(self, paths, labels, original_index, transform=None):
        self.paths = paths
        self.labels = labels
        self.original_index = original_index
        self.transform = transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, idx):
        path = self.paths[idx]
        label = self.labels[idx]
        image = Image.open(path).convert("RGB")
        mask = self._build_mask(path, image, label)

        if self.transform:
            image, mask = self.transform(image, mask)
        return image, label, mask

    def _build_mask(self, path, image, label):
        if label != 2:
            return Image.new("L", image.size, 0)

        original_path = find_original_path(path, self.original_index)
        if original_path is None:
            return Image.new("L", image.size, 0)

        original = Image.open(original_path).convert("RGB").resize(image.size)
        current = np.asarray(image, dtype=np.int16)
        source = np.asarray(original, dtype=np.int16)
        diff = np.abs(current - source).mean(axis=2).astype(np.uint8)
        mask = (diff > MASK_DIFF_THRESHOLD).astype(np.uint8) * 255
        return Image.fromarray(mask, mode="L")


def image_files(root):
    if not os.path.exists(root):
        return []
    paths = []
    for dirpath, _, filenames in os.walk(root):
        for name in filenames:
            if Path(name).suffix.lower() in IMG_EXTS:
                paths.append(os.path.join(dirpath, name))
    return paths


def build_original_index(roots):
    index = {}
    for root in roots:
        for path in image_files(root):
            stem = Path(path).stem
            name = Path(path).name
            index.setdefault(stem, path)
            index.setdefault(name, path)
    return index


def find_original_path(path, original_index):
    p = Path(path)
    candidates = [p.name, p.stem]
    stem_parts = p.stem.split("_")
    if stem_parts:
        candidates.append(stem_parts[0])
    for key in candidates:
        if key in original_index:
            return original_index[key]
    return None


def collect_subfolders(root, label, max_per_sub=None):
    paths, labels = [], []
    if not os.path.exists(root):
        return paths, labels
    for sub in sorted(os.listdir(root)):
        sp = os.path.join(root, sub)
        if not os.path.isdir(sp):
            continue
        files = [f for f in os.listdir(sp) if Path(f).suffix.lower() in IMG_EXTS]
        random.seed(42)
        random.shuffle(files)
        for f in (files[:max_per_sub] if max_per_sub else files):
            paths.append(os.path.join(sp, f))
            labels.append(label)
    return paths, labels


def collect_flat_types(root, label):
    paths, labels = [], []
    if not os.path.exists(root):
        return paths, labels
    for sub in os.listdir(root):
        sp = os.path.join(root, sub)
        if os.path.isdir(sp):
            for path in image_files(sp):
                paths.append(path)
                labels.append(label)
    return paths, labels


def collect_ali(root, label):
    paths, labels = [], []
    if not os.path.exists(root):
        return paths, labels
    for type_level in os.listdir(root):
        tl_path = os.path.join(root, type_level)
        if not os.path.isdir(tl_path):
            continue
        for sub in os.listdir(tl_path):
            sp = os.path.join(tl_path, sub)
            if os.path.isdir(sp):
                for path in image_files(sp):
                    paths.append(path)
                    labels.append(label)
    return paths, labels


def evaluate(model, loader, device):
    model.eval()
    preds, trues = [], []
    with torch.no_grad():
        for imgs, labels, _ in loader:
            logits = model(imgs.to(device))
            preds.extend(logits.argmax(1).cpu().tolist())
            trues.extend(labels.tolist())
    acc = accuracy_score(trues, preds)
    f1_macro = f1_score(trues, preds, average="macro")
    f1_per_class = f1_score(trues, preds, average=None, labels=[0, 1, 2])
    return acc, f1_macro, f1_per_class[2], preds, trues


if __name__ == "__main__":
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    original_index = build_original_index(ORIGINAL_DIR_CANDIDATES)
    print(f"Original index: {len(original_index)} lookup keys")
    if not original_index:
        print("[WARN] No FFHQ original images found. MAM masks will be zero.")
        print("       Update ORIGINAL_DIR_CANDIDATES after extracting FFHQ.zip.")

    rp, rl = collect_subfolders(REAL_DIR, 0, N_PER_SUB)
    fp, fl = collect_subfolders(FAKE_DIR, 1, N_PER_SUB)
    flt_p, flt_l = collect_flat_types(FILTER_DIR, 2)
    ffhq_p, ffhq_l = collect_subfolders(FFHQ_DIR, 2)
    mgv_p, mgv_l = collect_subfolders(MEGVII_DIR, 2)
    ali_p, ali_l = collect_ali(ALI_DIR, 2)

    filter_paths = flt_p + ffhq_p + mgv_p + ali_p
    filter_labels = flt_l + ffhq_l + mgv_l + ali_l
    paired = sum(1 for p in filter_paths if find_original_path(p, original_index))

    print(f"Real:   {len(rp)}")
    print(f"Fake:   {len(fp)}")
    print(
        f"Filter: {len(filter_paths)} "
        f"(self={len(flt_p)}, ffhq={len(ffhq_p)}, megvii={len(mgv_p)}, ali={len(ali_p)})"
    )
    print(f"Paired filter images for MAM masks: {paired}/{len(filter_paths)}")

    all_paths = rp + fp + filter_paths
    all_labels = rl + fl + filter_labels
    print("Class counts:", dict(Counter(all_labels)))

    tr_p, va_p, tr_l, va_l = train_test_split(
        all_paths,
        all_labels,
        test_size=VAL_RATIO,
        random_state=42,
        stratify=all_labels,
    )

    train_ds = MAMFaceDataset(tr_p, tr_l, original_index, JointTransform(train=True))
    val_ds = MAMFaceDataset(va_p, va_l, original_index, JointTransform(train=False))
    train_loader = DataLoader(
        train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=4, pin_memory=True
    )
    val_loader = DataLoader(
        val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=4, pin_memory=True
    )
    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}")

    model = DualBranchMAMModel(num_classes=3, pretrained=True).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    ce_loss = nn.CrossEntropyLoss()

    best_f1 = 0.0
    rows = []

    for epoch in range(1, EPOCHS + 1):
        model.train()
        t0 = time.time()
        total_cls, total_mam, total_loss, seen = 0.0, 0.0, 0.0, 0

        for imgs, labels, masks in train_loader:
            imgs = imgs.to(device)
            labels = labels.to(device)
            masks = masks.to(device)

            optimizer.zero_grad()
            logits, attn = model.forward_with_attention(imgs)
            cls_loss = ce_loss(logits, labels)
            attn_up = F.interpolate(
                attn, size=masks.shape[-2:], mode="bilinear", align_corners=False
            )
            mam_loss = F.binary_cross_entropy(attn_up, masks)
            loss = cls_loss + MAM_LOSS_WEIGHT * mam_loss
            loss.backward()
            optimizer.step()

            batch = imgs.size(0)
            seen += batch
            total_cls += cls_loss.item() * batch
            total_mam += mam_loss.item() * batch
            total_loss += loss.item() * batch

        scheduler.step()
        acc, f1_macro, f1_filter, _, _ = evaluate(model, val_loader, device)
        elapsed = time.time() - t0
        avg_loss = total_loss / seen
        avg_cls = total_cls / seen
        avg_mam = total_mam / seen

        print(
            f"[{epoch:02d}/{EPOCHS}] loss={avg_loss:.4f} "
            f"cls={avg_cls:.4f} mam={avg_mam:.4f} "
            f"Acc={acc:.4f} F1_macro={f1_macro:.4f} "
            f"F1_filter={f1_filter:.4f} ({elapsed:.1f}s)"
        )
        rows.append(
            [
                epoch,
                f"{avg_loss:.4f}",
                f"{avg_cls:.4f}",
                f"{avg_mam:.4f}",
                f"{acc:.4f}",
                f"{f1_macro:.4f}",
                f"{f1_filter:.4f}",
            ]
        )

        if f1_filter > best_f1:
            best_f1 = f1_filter
            torch.save(model.state_dict(), WEIGHTS_PATH)
            print(f"  Saved MAM model (filter F1={best_f1:.4f})")

    print(f"\nBest filter F1={best_f1:.4f}  Weights: {WEIGHTS_PATH}")

    model.load_state_dict(torch.load(WEIGHTS_PATH, map_location=device))
    _, _, _, preds, trues = evaluate(model, val_loader, device)
    print("\n--- Classification Report (val) ---")
    print(classification_report(trues, preds, target_names=CLASSES, digits=4))
    print("Confusion matrix:\n", confusion_matrix(trues, preds))

    os.makedirs(os.path.dirname(RESULTS_CSV), exist_ok=True)
    pd.DataFrame(
        rows,
        columns=[
            "epoch",
            "loss",
            "cls_loss",
            "mam_loss",
            "acc",
            "f1_macro",
            "f1_filter",
        ],
    ).to_csv(RESULTS_CSV, index=False)
    print(f"\nResults saved to {RESULTS_CSV}")

