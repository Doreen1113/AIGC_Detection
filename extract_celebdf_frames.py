"""
Extract face crops from Celeb-DF-v2 videos.
- Excludes official test videos (List_of_testing_videos.txt)
- Real:  Celeb-real/ + YouTube-real/ (non-test)  → FRAMES_PER_REAL frames each
- Fake:  Celeb-synthesis/ (non-test)              → FRAMES_PER_FAKE frames each
- Saves face crops to Celeb-DF-v2/frames/real/ and .../fake/
- Outputs clean_paths_real.txt and clean_paths_fake.txt

python extract_celebdf_frames.py
"""
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict

BASE        = Path(r"C:\My_Project\AIGC")
CELEBDF     = BASE / "Celeb-DF-v2"
OUT_REAL    = CELEBDF / "frames" / "real"
OUT_FAKE    = CELEBDF / "frames" / "fake"
YUNET       = str(BASE / "face_detection_yunet.onnx")
TEST_LIST   = CELEBDF / "List_of_testing_videos.txt"

FRAMES_PER_REAL = 10   # frames per real video
FRAMES_PER_FAKE = 2    # frames per fake video
MIN_FACE_PX     = 80   # min face short-side after crop
FACE_PADDING    = 0.2  # padding ratio around detected face box
SCORE_THRESH    = 0.7

OUT_REAL.mkdir(parents=True, exist_ok=True)
OUT_FAKE.mkdir(parents=True, exist_ok=True)


def load_test_set():
    test_videos = set()
    for line in TEST_LIST.read_text().splitlines():
        parts = line.strip().split()
        if len(parts) == 2:
            test_videos.add(Path(parts[1]).name)
    return test_videos


def collect_videos(test_videos):
    real_vids, fake_vids = [], []
    for mp4 in sorted((CELEBDF / "Celeb-real").glob("*.mp4")):
        if mp4.name not in test_videos:
            real_vids.append(mp4)
    for mp4 in sorted((CELEBDF / "YouTube-real").glob("*.mp4")):
        if mp4.name not in test_videos:
            real_vids.append(mp4)
    for mp4 in sorted((CELEBDF / "Celeb-synthesis").glob("*.mp4")):
        if mp4.name not in test_videos:
            fake_vids.append(mp4)
    return real_vids, fake_vids


def get_face_crop(frame, detector):
    h, w = frame.shape[:2]
    detector.setInputSize((w, h))
    _, faces = detector.detect(frame)
    if faces is None or len(faces) == 0:
        return None
    # pick highest-score face
    best = max(faces, key=lambda f: f[14])
    if best[14] < SCORE_THRESH:
        return None
    x, y, fw, fh = int(best[0]), int(best[1]), int(best[2]), int(best[3])
    pad_x = int(fw * FACE_PADDING)
    pad_y = int(fh * FACE_PADDING)
    x1 = max(0, x - pad_x)
    y1 = max(0, y - pad_y)
    x2 = min(w, x + fw + pad_x)
    y2 = min(h, y + fh + pad_y)
    crop = frame[y1:y2, x1:x2]
    if crop.shape[0] < MIN_FACE_PX or crop.shape[1] < MIN_FACE_PX:
        return None
    return crop


def sample_frame_indices(total_frames, n):
    if total_frames <= 0 or n <= 0:
        return []
    # skip first and last 10% to avoid intros/outros
    start = max(0, int(total_frames * 0.10))
    end   = max(start + 1, int(total_frames * 0.90))
    if end - start <= n:
        return list(range(start, end))
    step = (end - start) / n
    return [int(start + step * i) for i in range(n)]


def extract_from_video(mp4_path, out_dir, n_frames, detector, video_idx):
    cap = cv2.VideoCapture(str(mp4_path))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    indices = sample_frame_indices(total, n_frames)

    saved = []
    for fi in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
        ret, frame = cap.read()
        if not ret:
            continue
        crop = get_face_crop(frame, detector)
        if crop is None:
            continue
        fname = f"{mp4_path.stem}_f{fi:05d}.jpg"
        out_path = out_dir / fname
        cv2.imwrite(str(out_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 95])
        saved.append(str(out_path))
    cap.release()
    return saved


if __name__ == "__main__":
    detector = cv2.FaceDetectorYN.create(YUNET, "", (320, 320), score_threshold=SCORE_THRESH)

    test_videos = load_test_set()
    print(f"Test set exclusion: {len(test_videos)} videos")

    real_vids, fake_vids = collect_videos(test_videos)
    print(f"Train real videos : {len(real_vids)}  ({FRAMES_PER_REAL} frames each → target {len(real_vids)*FRAMES_PER_REAL})")
    print(f"Train fake videos : {len(fake_vids)}  ({FRAMES_PER_FAKE} frames each → target {len(fake_vids)*FRAMES_PER_FAKE})")

    # --- Extract real ---
    print(f"\n[Real] Extracting...")
    real_paths = []
    for i, mp4 in enumerate(real_vids):
        paths = extract_from_video(mp4, OUT_REAL, FRAMES_PER_REAL, detector, i)
        real_paths.extend(paths)
        if (i + 1) % 50 == 0 or i + 1 == len(real_vids):
            print(f"  [{i+1}/{len(real_vids)}]  saved={len(real_paths)}")

    # --- Extract fake ---
    print(f"\n[Fake] Extracting...")
    fake_paths = []
    for i, mp4 in enumerate(fake_vids):
        paths = extract_from_video(mp4, OUT_FAKE, FRAMES_PER_FAKE, detector, i)
        fake_paths.extend(paths)
        if (i + 1) % 200 == 0 or i + 1 == len(fake_vids):
            print(f"  [{i+1}/{len(fake_vids)}]  saved={len(fake_paths)}")

    # --- Write output lists ---
    real_txt = CELEBDF / "clean_paths_real.txt"
    fake_txt = CELEBDF / "clean_paths_fake.txt"
    real_txt.write_text("\n".join(real_paths), encoding="utf-8")
    fake_txt.write_text("\n".join(fake_paths), encoding="utf-8")

    print(f"\n=== Done ===")
    print(f"Real frames saved : {len(real_paths)}  → {real_txt}")
    print(f"Fake frames saved : {len(fake_paths)}  → {fake_txt}")
