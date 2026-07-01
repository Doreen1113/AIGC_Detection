"""Generate a facial skin-whitening example and a quantitative report.

Usage:
    python whitening.py input.jpg --level 30 --output-dir output

Dependencies:
    pip install opencv-python numpy
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


# RetouchingFFHQ uses API levels 0/30/60/90. Because the proprietary APIs do
# not disclose their algorithms, these are conservative strengths for this
# paper-inspired OpenCV approximation, not an exact reproduction of any API.
PAPER_LEVEL_TO_STRENGTH = {0: 0.0, 30: 0.15, 60: 0.30, 90: 0.45}
PAPER_LEVEL_TO_CLASS = {0: 0, 30: 1, 60: 2, 90: 3}


def detect_largest_face(image: np.ndarray) -> tuple[int, int, int, int]:
    """Return the largest detected face as (x, y, width, height)."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    faces = detector.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )
    if len(faces) == 0:
        raise RuntimeError("找不到正面人臉，請改用光線清楚、臉部完整的照片。")
    return tuple(max(faces, key=lambda box: box[2] * box[3]))


def build_skin_mask(image: np.ndarray, face: tuple[int, int, int, int]) -> np.ndarray:
    """Build a soft mask from a face ellipse and common YCrCb skin ranges."""
    x, y, w, h = face

    # The ellipse prevents similarly colored background pixels from being changed.
    face_mask = np.zeros(image.shape[:2], dtype=np.uint8)
    center = (x + w // 2, y + int(h * 0.52))
    axes = (int(w * 0.44), int(h * 0.48))
    cv2.ellipse(face_mask, center, axes, 0, 0, 360, 255, -1)

    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    lower = np.array([0, 133, 77], dtype=np.uint8)
    upper = np.array([255, 173, 127], dtype=np.uint8)
    skin_color_mask = cv2.inRange(ycrcb, lower, upper)

    mask = cv2.bitwise_and(face_mask, skin_color_mask)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.GaussianBlur(mask, (21, 21), 0)

    if np.count_nonzero(mask > 32) < 500:
        raise RuntimeError("偵測到人臉，但無法取得足夠的皮膚區域。請更換照片。")
    return mask


def apply_whitening(
    image: np.ndarray,
    mask: np.ndarray,
    strength: float,
) -> np.ndarray:
    """Raise facial-skin luminance in LAB while slightly reducing saturation."""
    mask_alpha = mask.astype(np.float32) / 255.0

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB).astype(np.float32)
    lightness = lab[:, :, 0]
    # Move L toward white instead of adding a fixed value; this avoids clipping.
    lab[:, :, 0] = lightness + strength * (255.0 - lightness)
    brightened = cv2.cvtColor(np.clip(lab, 0, 255).astype(np.uint8), cv2.COLOR_LAB2BGR)

    # Beauty whitening commonly makes skin color slightly less saturated.
    hsv = cv2.cvtColor(brightened, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= 1.0 - 0.18 * strength
    whitened = cv2.cvtColor(np.clip(hsv, 0, 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    blend = mask_alpha[:, :, None]
    result = image.astype(np.float32) * (1.0 - blend) + whitened.astype(np.float32) * blend
    return np.clip(result, 0, 255).astype(np.uint8)


def calculate_metrics(image: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    """Measure the masked skin area's luminance, saturation, and high-frequency energy."""
    valid = mask > 64

    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)

    return {
        "brightness": float(np.mean(lab[:, :, 0][valid])),
        "saturation": float(np.mean(hsv[:, :, 1][valid])),
        "high_frequency": float(np.mean(np.square(laplacian[valid]))),
    }


def make_comparison(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    """Create one side-by-side image with English labels for font portability."""
    left = before.copy()
    right = after.copy()
    cv2.rectangle(left, (0, 0), (190, 48), (0, 0, 0), -1)
    cv2.rectangle(right, (0, 0), (190, 48), (0, 0, 0), -1)
    cv2.putText(left, "BEFORE", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    cv2.putText(right, "AFTER", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    return np.hstack([left, right])


def change_text(before: float, after: float) -> str:
    difference = after - before
    percentage = difference / before * 100.0 if before else 0.0
    return f"{before:.2f} -> {after:.2f} ({difference:+.2f}, {percentage:+.2f}%)"


def build_report(
    paper_level: int,
    strength: float,
    before: dict[str, float],
    after: dict[str, float],
    psnr: float,
) -> str:
    label_class = PAPER_LEVEL_TO_CLASS[paper_level]
    return f"""
濾鏡類型：Face Whitening（臉部美白）
論文依據：RetouchingFFHQ (Ying et al., 2023, arXiv:2307.10642v1)
論文標籤：{{Smooth: 0, EyeEnlarge: 0, FaceLift: 0, Whiten: {label_class}}}
RetouchingFFHQ 等級：{paper_level}（0=off、30=slight、60=medium、90=heavy）
方法：YCrCb 膚色遮罩 + LAB L 通道亮度映射；OpenCV 實作強度 = {strength:.2f}
對臉做了什麼：偵測臉部皮膚區域，將 LAB 色彩空間的 L 通道往較高亮度移動，並輕微降低飽和度；背景與非皮膚區域盡量保持不變。

量化結果（僅計算臉部皮膚遮罩內的像素）：
- 平均亮度（LAB L，0-255）：{change_text(before['brightness'], after['brightness'])}
- 平均飽和度（HSV S，0-255）：{change_text(before['saturation'], after['saturation'])}
- 高頻能量（Laplacian squared mean）：{change_text(before['high_frequency'], after['high_frequency'])}
- 原圖與處理圖 PSNR：{psnr:.2f} dB

可能的偵測特徵：臉部皮膚亮度相對背景異常升高、膚色飽和度降低、臉部與頸部色差增加，以及皮膚區域的亮度分布出現不自然偏移。

方法限制：原論文使用 Megvii、Tencent 與 Alibaba 的商業 API，未公開各 API 的 Whitening 演算法。本程式沿用論文的類型與等級標註，但美白處理是可重現的 OpenCV 近似實作，不等同於原商業 API。
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生臉部 Whitening before/after 圖與量化報告")
    parser.add_argument("input", type=Path, help="輸入照片路徑")
    parser.add_argument(
        "--level",
        type=int,
        choices=(0, 30, 60, 90),
        default=30,
        help="RetouchingFFHQ 等級：0=off、30=slight、60=medium、90=heavy",
    )
    parser.add_argument(
        "--strength",
        type=float,
        default=None,
        help="覆寫 OpenCV 實作強度（0-1）；通常不需要設定",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("whitening_output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strength = PAPER_LEVEL_TO_STRENGTH[args.level] if args.strength is None else args.strength
    if not 0.0 <= strength <= 1.0:
        raise ValueError("--strength 必須介於 0 和 1 之間。")

    image = cv2.imread(str(args.input))
    if image is None:
        raise FileNotFoundError(f"無法讀取圖片：{args.input}")

    face = detect_largest_face(image)
    mask = build_skin_mask(image, face)
    after = apply_whitening(image, mask, strength)
    before_metrics = calculate_metrics(image, mask)
    after_metrics = calculate_metrics(after, mask)
    comparison = make_comparison(image, after)
    psnr = float(cv2.PSNR(image, after))
    report = build_report(args.level, strength, before_metrics, after_metrics, psnr)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output_dir / "whitening_after.jpg"), after)
    cv2.imwrite(str(args.output_dir / "whitening_before_after.jpg"), comparison)
    cv2.imwrite(str(args.output_dir / "whitening_skin_mask.png"), mask)
    (args.output_dir / "whitening_report.txt").write_text(report, encoding="utf-8")

    print(report)
    print(f"\n輸出位置：{args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
