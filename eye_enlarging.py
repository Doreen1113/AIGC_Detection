"""產生 Eye Enlarging before/after 圖與量化報告。

安裝：
    pip install opencv-python mediapipe==0.10.21 numpy

執行：
    python eye_enlarging.py input.jpg --scale 1.18 --output-dir eye_output
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np


# MediaPipe Face Mesh landmark indices.
LEFT_EYE = (33, 133, 159, 145)
RIGHT_EYE = (362, 263, 386, 374)
FACE_WIDTH = (234, 454)


def detect_landmarks(image: np.ndarray) -> np.ndarray:
    """偵測單一人臉，回傳像素座標 shape=(468, 2)。"""
    if not hasattr(mp, "solutions"):
        raise RuntimeError(
            "目前的 MediaPipe 版本已移除 mp.solutions。請執行："
            "python -m pip install --force-reinstall mediapipe==0.10.21"
        )
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    with mp.solutions.face_mesh.FaceMesh(
        static_image_mode=True,
        max_num_faces=1,
        refine_landmarks=False,
        min_detection_confidence=0.5,
    ) as face_mesh:
        result = face_mesh.process(rgb)

    if not result.multi_face_landmarks:
        raise RuntimeError("找不到人臉，請使用正面、清楚且眼睛未被遮住的照片。")

    height, width = image.shape[:2]
    points = np.array(
        [(lm.x * width, lm.y * height) for lm in result.multi_face_landmarks[0].landmark],
        dtype=np.float32,
    )
    return points


def distance(points: np.ndarray, first: int, second: int) -> float:
    return float(np.linalg.norm(points[first] - points[second]))


def eye_geometry(points: np.ndarray) -> dict[str, float]:
    left_width = distance(points, LEFT_EYE[0], LEFT_EYE[1])
    right_width = distance(points, RIGHT_EYE[0], RIGHT_EYE[1])
    face_width = distance(points, FACE_WIDTH[0], FACE_WIDTH[1])
    average_eye_width = (left_width + right_width) / 2.0
    return {
        "left_eye_width": left_width,
        "right_eye_width": right_width,
        "average_eye_width": average_eye_width,
        "face_width": face_width,
        "eye_face_ratio": average_eye_width / face_width if face_width else 0.0,
    }


def eye_center_and_radius(
    points: np.ndarray,
    indices: tuple[int, int, int, int],
    radius_factor: float,
) -> tuple[tuple[float, float], float]:
    eye_points = points[list(indices)]
    center = tuple(np.mean(eye_points, axis=0))
    eye_width = float(np.linalg.norm(points[indices[0]] - points[indices[1]]))
    return center, max(eye_width * radius_factor, 8.0)


def local_eye_magnify(
    image: np.ndarray,
    center: tuple[float, float],
    radius: float,
    scale: float,
) -> np.ndarray:
    """使用平滑反向映射放大局部眼睛，邊界縮放逐漸回到 1。"""
    height, width = image.shape[:2]
    center_x, center_y = center

    x0 = max(0, int(np.floor(center_x - radius)))
    x1 = min(width, int(np.ceil(center_x + radius + 1)))
    y0 = max(0, int(np.floor(center_y - radius)))
    y1 = min(height, int(np.ceil(center_y + radius + 1)))

    grid_x, grid_y = np.meshgrid(
        np.arange(x0, x1, dtype=np.float32),
        np.arange(y0, y1, dtype=np.float32),
    )
    delta_x = grid_x - center_x
    delta_y = grid_y - center_y
    radial_distance = np.sqrt(delta_x**2 + delta_y**2)
    normalized = np.clip(radial_distance / radius, 0.0, 1.0)

    # The center uses the requested scale; the circular boundary remains fixed.
    local_scale = 1.0 + (scale - 1.0) * (1.0 - normalized) ** 2
    map_x = center_x + delta_x / local_scale
    map_y = center_y + delta_y / local_scale

    roi = cv2.remap(
        image,
        map_x,
        map_y,
        interpolation=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REFLECT_101,
    )

    # Feather the circular edge so the warp does not leave a hard seam.
    alpha = np.clip((1.0 - normalized) / 0.18, 0.0, 1.0)
    alpha[normalized >= 1.0] = 0.0
    alpha = alpha[:, :, None]

    result = image.copy()
    original_roi = image[y0:y1, x0:x1].astype(np.float32)
    blended = original_roi * (1.0 - alpha) + roi.astype(np.float32) * alpha
    result[y0:y1, x0:x1] = np.clip(blended, 0, 255).astype(np.uint8)
    return result


def apply_eye_enlarging(
    image: np.ndarray,
    landmarks: np.ndarray,
    scale: float,
    radius_factor: float,
) -> np.ndarray:
    result = image.copy()
    for eye_indices in (LEFT_EYE, RIGHT_EYE):
        center, radius = eye_center_and_radius(landmarks, eye_indices, radius_factor)
        result = local_eye_magnify(result, center, radius, scale)
    return result


def make_comparison(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    left = before.copy()
    right = after.copy()
    cv2.rectangle(left, (0, 0), (190, 48), (0, 0, 0), -1)
    cv2.rectangle(right, (0, 0), (190, 48), (0, 0, 0), -1)
    cv2.putText(left, "BEFORE", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    cv2.putText(right, "AFTER", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    return np.hstack([left, right])


def change_text(before: float, after: float, unit: str = "") -> str:
    difference = after - before
    percentage = difference / before * 100.0 if before else 0.0
    return f"{before:.3f}{unit} -> {after:.3f}{unit} ({difference:+.3f}{unit}, {percentage:+.2f}%)"


def build_report(
    scale: float,
    radius_factor: float,
    before: dict[str, float],
    after: dict[str, float],
) -> str:
    return f"""
濾鏡類型：Eye Enlarging（眼睛放大）
方法：MediaPipe Face Mesh 偵測眼睛 landmark + 平滑局部 warp；中心放大倍率 = {scale:.2f}，作用半徑 = 眼寬 × {radius_factor:.2f}
對臉做了什麼：分別以左右眼中心為基準，將眼睛附近像素向外放大；放大強度會隨著與眼睛中心的距離增加而逐漸降低，使作用區域邊界維持不變。

量化結果：
- 左眼寬度（landmark 33-133）：{change_text(before['left_eye_width'], after['left_eye_width'], 'px')}
- 右眼寬度（landmark 362-263）：{change_text(before['right_eye_width'], after['right_eye_width'], 'px')}
- 平均眼睛寬度：{change_text(before['average_eye_width'], after['average_eye_width'], 'px')}
- 眼睛／臉寬比例：{change_text(before['eye_face_ratio'], after['eye_face_ratio'])}

可能的偵測特徵：眼睛與臉寬比例異常、左右眼幾何比例改變、眼皮或眼角附近出現局部插值與 warp artifact，以及眼睛周圍紋理產生不自然的拉伸。
""".strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="產生 Eye Enlarging before/after 圖與量化報告")
    parser.add_argument("input", type=Path, help="輸入照片路徑")
    parser.add_argument("--scale", type=float, default=1.18, help="眼睛中心放大倍率，建議 1.10-1.30")
    parser.add_argument("--radius-factor", type=float, default=1.70, help="作用半徑相對於眼寬的倍率")
    parser.add_argument("--output-dir", type=Path, default=Path("eye_enlarging_output"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1.0 <= args.scale <= 1.5:
        raise ValueError("--scale 建議介於 1.0 和 1.5 之間。")
    if not 1.0 <= args.radius_factor <= 3.0:
        raise ValueError("--radius-factor 建議介於 1.0 和 3.0 之間。")

    image = cv2.imread(str(args.input))
    if image is None:
        raise FileNotFoundError(f"無法讀取圖片：{args.input}")

    before_landmarks = detect_landmarks(image)
    after = apply_eye_enlarging(image, before_landmarks, args.scale, args.radius_factor)
    after_landmarks = detect_landmarks(after)
    before_metrics = eye_geometry(before_landmarks)
    after_metrics = eye_geometry(after_landmarks)
    comparison = make_comparison(image, after)
    report = build_report(
        args.scale,
        args.radius_factor,
        before_metrics,
        after_metrics,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(args.output_dir / "eye_enlarging_after.jpg"), after)
    cv2.imwrite(str(args.output_dir / "eye_enlarging_before_after.jpg"), comparison)
    (args.output_dir / "eye_enlarging_report.txt").write_text(report, encoding="utf-8")

    print(report)
    print(f"\n輸出位置：{args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
