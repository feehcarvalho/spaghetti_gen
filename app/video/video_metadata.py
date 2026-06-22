"""Video metadata helpers used by the SPS analysis pipeline."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
from pydantic import BaseModel, ConfigDict, Field


class VideoMetadata(BaseModel):
    """Technical metadata read from the video file."""

    model_config = ConfigDict(extra="forbid")

    video_path: str
    duration_s: float = Field(..., ge=0)
    fps: float = Field(..., ge=0)
    width: int = Field(..., ge=0)
    height: int = Field(..., ge=0)
    frame_count: int = Field(..., ge=0)
    file_size_mb: float = Field(..., ge=0)
    codec: str | None = None
    created_at: str | None = None
    processado_em: str = Field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


def get_video_metadata(video_path: str) -> VideoMetadata:
    """Read metadata from a video without decoding the whole file."""

    source = Path(video_path)
    if not source.exists():
        raise FileNotFoundError(f"Video nao encontrado: {source}")
    if source.stat().st_size <= 0:
        raise ValueError(f"Video vazio ou invalido: {source}")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Nao foi possivel abrir o video: {source}")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fourcc = int(capture.get(cv2.CAP_PROP_FOURCC) or 0)
    finally:
        capture.release()

    duration_s = frame_count / fps if fps > 0 and frame_count > 0 else 0.0
    file_size_mb = source.stat().st_size / (1024 * 1024)
    created_at = datetime.fromtimestamp(source.stat().st_ctime).isoformat(timespec="seconds")

    return VideoMetadata(
        video_path=str(source),
        duration_s=round(duration_s, 3),
        fps=round(fps, 3),
        width=width,
        height=height,
        frame_count=frame_count,
        file_size_mb=round(file_size_mb, 3),
        codec=_decode_fourcc(fourcc),
        created_at=created_at,
    )


def _decode_fourcc(value: int) -> str | None:
    if not value:
        return None
    chars = [chr((value >> 8 * index) & 0xFF) for index in range(4)]
    codec = "".join(char for char in chars if char.isprintable()).strip()
    return codec or None
