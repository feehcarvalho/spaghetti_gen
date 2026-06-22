"""Testes para extracao de frames de video."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest

from app.video.frame_extractor import extract_frames


REPO_ROOT = Path(__file__).resolve().parents[1]
VIDEO_ROOT = REPO_ROOT / "data" / "videos"
FRAMES_ROOT = REPO_ROOT / "data" / "frames"


def create_synthetic_video(path: Path, fps: float = 10.0, frame_count: int = 20) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width = 64
    height = 48
    writer = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    if not writer.isOpened():
        pytest.skip("OpenCV nao conseguiu inicializar VideoWriter MP4 neste ambiente")

    try:
        for frame_number in range(frame_count):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:, :] = (
                frame_number * 7 % 255,
                frame_number * 13 % 255,
                frame_number * 19 % 255,
            )
            cv2.putText(
                frame,
                str(frame_number),
                (8, 28),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            writer.write(frame)
    finally:
        writer.release()


def test_extract_frames_from_synthetic_video():
    run_id = uuid4().hex
    video_path = VIDEO_ROOT / f"test_frame_extractor_{run_id}.mp4"
    frames_dir = FRAMES_ROOT / f"test_frame_extractor_{run_id}"
    create_synthetic_video(video_path)
    frames_dir.mkdir(parents=True, exist_ok=True)

    frames = extract_frames(
        video_path=str(video_path),
        output_dir=str(frames_dir),
        fps=2.0,
        max_frames=3,
    )

    assert len(frames) == 3
    assert [frame.index for frame in frames] == [1, 2, 3]
    assert [frame.timestamp_s for frame in frames] == sorted(
        frame.timestamp_s for frame in frames
    )
    assert frames[0].timestamp_s == 0.0
    assert frames[1].timestamp_s == 0.5
    assert frames[2].timestamp_s == 1.0

    for frame in frames:
        assert Path(frame.path).exists()
        assert Path(frame.path).suffix.lower() == ".jpg"
        assert frame.width == 64
        assert frame.height == 48
        assert frame.timestamp_formatado
