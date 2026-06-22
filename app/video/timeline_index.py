"""Temporal index builder for full-video SPS analysis."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.config import REPO_ROOT
from app.video.frame_extractor import ExtractedFrame
from app.video.segmentation import SceneMarker
from app.video.video_metadata import VideoMetadata, get_video_metadata


@dataclass(frozen=True)
class TimelineSample:
    timestamp_s: float
    frame_index: int
    frame_path: str
    width: int
    height: int
    motion_score: float
    is_key_frame: bool
    is_scene_change: bool
    is_static: bool
    is_action: bool


@dataclass(frozen=True)
class VideoTimelineIndex:
    video_path: str
    metadata: VideoMetadata
    samples: list[TimelineSample] = field(default_factory=list)
    key_frames: list[TimelineSample] = field(default_factory=list)
    scene_change_markers: list[SceneMarker] = field(default_factory=list)
    motion_scores: list[float] = field(default_factory=list)

    @property
    def sampled_timestamps(self) -> list[float]:
        return [sample.timestamp_s for sample in self.samples]

    @property
    def extracted_frames(self) -> list[ExtractedFrame]:
        return [
            ExtractedFrame(
                index=sample.frame_index,
                timestamp_s=sample.timestamp_s,
                timestamp_formatado=_format_timestamp(sample.timestamp_s),
                path=sample.frame_path,
                width=sample.width,
                height=sample.height,
            )
            for sample in self.samples
        ]


def build_video_timeline_index(
    video_path: str,
    base_sample_interval_s: float = 1.0,
    motion_sensitive: bool = True,
) -> VideoTimelineIndex:
    """Create a complete temporal index without decoding the whole video into memory."""

    if base_sample_interval_s <= 0:
        raise ValueError("base_sample_interval_s deve ser maior que zero")

    source = Path(video_path)
    metadata = get_video_metadata(str(source))
    output_dir = _timeline_frames_dir(source)
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Nao foi possivel abrir o video: {source}")

    max_width = _read_int_env("OPENAI_FRAME_MAX_WIDTH", 1280)
    jpeg_quality = _read_int_env("OPENAI_JPEG_QUALITY", 82)
    previous_gray = None
    raw_samples: list[tuple[ExtractedFrame, float]] = []
    frame_number = 0
    next_timestamp_s = 0.0

    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break

            capture_msec = float(capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
            timestamp_s = _frame_timestamp(frame_number, metadata.fps, capture_msec)
            is_last_frame = (
                metadata.frame_count > 0
                and frame_number >= max(metadata.frame_count - 1, 0)
            )

            if timestamp_s + 1e-9 >= next_timestamp_s or is_last_frame:
                resized = _resize_to_max_width(frame, max_width=max_width)
                height, width = resized.shape[:2]
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
                motion_score = 0.0
                if previous_gray is not None:
                    motion_score = float(np.mean(cv2.absdiff(previous_gray, gray))) / 255.0
                previous_gray = gray

                frame_index = len(raw_samples) + 1
                frame_path = output_dir / f"frame_{frame_index:06d}_{_format_timestamp_for_filename(timestamp_s)}.jpg"
                _write_jpeg(frame_path, resized, jpeg_quality=jpeg_quality)
                raw_samples.append(
                    (
                        ExtractedFrame(
                            index=frame_index,
                            timestamp_s=round(timestamp_s, 3),
                            timestamp_formatado=_format_timestamp(timestamp_s),
                            path=str(frame_path),
                            width=int(width),
                            height=int(height),
                        ),
                        round(motion_score, 5),
                    )
                )
                next_timestamp_s += base_sample_interval_s

            frame_number += 1
    finally:
        capture.release()

    if not raw_samples:
        raise ValueError(f"Nenhum frame foi indexado no video: {source}")

    scores = [score for _, score in raw_samples]
    mean_score = float(np.mean(scores)) if scores else 0.0
    std_score = float(np.std(scores)) if scores else 0.0
    scene_threshold = max(0.08, mean_score + std_score) if motion_sensitive else float("inf")
    action_threshold = max(0.015, mean_score * 0.60)
    static_threshold = min(0.01, max(0.004, mean_score * 0.25))

    samples: list[TimelineSample] = []
    markers: list[SceneMarker] = []
    for position, (frame, score) in enumerate(raw_samples):
        is_first_or_last = position == 0 or position == len(raw_samples) - 1
        is_scene_change = motion_sensitive and position > 0 and score >= scene_threshold
        is_key_frame = is_first_or_last or is_scene_change
        is_static = score <= static_threshold
        is_action = score >= action_threshold
        sample = TimelineSample(
            timestamp_s=frame.timestamp_s,
            frame_index=frame.index,
            frame_path=frame.path,
            width=frame.width,
            height=frame.height,
            motion_score=score,
            is_key_frame=is_key_frame,
            is_scene_change=is_scene_change,
            is_static=is_static,
            is_action=is_action,
        )
        samples.append(sample)
        if is_scene_change:
            markers.append(
                SceneMarker(
                    timestamp_s=sample.timestamp_s,
                    frame_index=sample.frame_index,
                    score=sample.motion_score,
                )
            )

    return VideoTimelineIndex(
        video_path=str(source),
        metadata=metadata,
        samples=samples,
        key_frames=[sample for sample in samples if sample.is_key_frame],
        scene_change_markers=markers,
        motion_scores=scores,
    )


def _timeline_frames_dir(source: Path) -> Path:
    digest = hashlib.sha1(str(source.resolve(strict=False)).encode("utf-8", errors="ignore")).hexdigest()[:10]
    safe_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in source.stem)
    return REPO_ROOT / "data" / "outputs" / "timeline_frames" / f"{safe_name}_{digest}"


def _frame_timestamp(frame_number: int, source_fps: float, capture_msec: float) -> float:
    if source_fps > 0:
        return frame_number / source_fps
    if capture_msec > 0:
        return capture_msec / 1000
    return 0.0


def _format_timestamp(seconds: float) -> str:
    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60
    return f"{minutes:02d}:{remaining_seconds:02d}"


def _format_timestamp_for_filename(seconds: float) -> str:
    return f"{seconds:06.2f}s"


def _resize_to_max_width(frame, max_width: int):
    if max_width <= 0:
        return frame
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    scale = max_width / width
    return cv2.resize(frame, (max_width, int(height * scale)), interpolation=cv2.INTER_AREA)


def _write_jpeg(frame_path: Path, frame, jpeg_quality: int) -> None:
    quality = max(1, min(100, int(jpeg_quality)))
    ok, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise ValueError(f"Nao foi possivel salvar frame em: {frame_path}")
    encoded.tofile(str(frame_path))


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
