"""Temporal segmentation for video-window SPS analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.video.frame_extractor import ExtractedFrame


@dataclass(frozen=True)
class SceneMarker:
    timestamp_s: float
    frame_index: int
    score: float
    reason: str = "mudanca visual relevante"


@dataclass(frozen=True)
class VideoWindow:
    index: int
    start_s: float
    end_s: float
    frames: list[ExtractedFrame] = field(default_factory=list)
    scene_markers: list[SceneMarker] = field(default_factory=list)
    motion_score: float = 0.0
    status: str = "pending"

    @property
    def duration_s(self) -> float:
        return round(max(0.0, self.end_s - self.start_s), 3)

    @property
    def window_id(self) -> str:
        return f"window_{self.index:03d}"

    @property
    def frame_paths(self) -> list[str]:
        return [frame.path for frame in self.frames]

    @property
    def frame_timestamps_s(self) -> list[float]:
        return [frame.timestamp_s for frame in self.frames]


def _load_gray(path: str, size: tuple[int, int] = (160, 90)):
    frame = cv2.imread(str(Path(path)))
    if frame is None:
        return None
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, size, interpolation=cv2.INTER_AREA)


def detect_motion_or_scene_changes(frames: list[ExtractedFrame]) -> list[SceneMarker]:
    """Identify visual changes between extracted frames using a lightweight diff."""

    markers: list[SceneMarker] = []
    if len(frames) < 2:
        return markers

    previous_gray = _load_gray(frames[0].path)
    if previous_gray is None:
        return markers

    scores: list[tuple[ExtractedFrame, float]] = []
    for frame in frames[1:]:
        gray = _load_gray(frame.path)
        if gray is None:
            continue
        diff = cv2.absdiff(previous_gray, gray)
        score = float(np.mean(diff)) / 255.0
        scores.append((frame, score))
        previous_gray = gray

    if not scores:
        return markers

    score_values = [score for _, score in scores]
    mean_score = float(np.mean(score_values))
    std_score = float(np.std(score_values))
    threshold = max(0.08, mean_score + std_score)

    for frame, score in scores:
        if score >= threshold:
            markers.append(
                SceneMarker(
                    timestamp_s=frame.timestamp_s,
                    frame_index=frame.index,
                    score=round(score, 4),
                )
            )

    return markers


def _nearest_frame(frames: list[ExtractedFrame], timestamp_s: float) -> ExtractedFrame | None:
    if not frames:
        return None
    return min(frames, key=lambda frame: abs(frame.timestamp_s - timestamp_s))


def _select_evenly(frames: list[ExtractedFrame], max_count: int) -> list[ExtractedFrame]:
    if max_count <= 0 or not frames:
        return []
    if len(frames) <= max_count:
        return list(frames)
    if max_count == 1:
        return [frames[len(frames) // 2]]
    last_index = len(frames) - 1
    indexes = {
        round(position * last_index / (max_count - 1))
        for position in range(max_count)
    }
    return [frames[index] for index in sorted(indexes)]


def _unique_sorted(frames: list[ExtractedFrame]) -> list[ExtractedFrame]:
    by_index: dict[int, ExtractedFrame] = {}
    for frame in frames:
        by_index[frame.index] = frame
    return sorted(by_index.values(), key=lambda frame: frame.timestamp_s)


def split_video_into_windows(
    frames: list[ExtractedFrame],
    duration_s: float,
    target_window_seconds: int = 15,
    max_frames_per_window: int = 10,
    include_scene_changes: bool = True,
) -> list[VideoWindow]:
    """Split a full video timeline into frame-covered analysis windows."""

    if target_window_seconds <= 0:
        raise ValueError("target_window_seconds deve ser maior que zero")
    if max_frames_per_window <= 0:
        raise ValueError("max_frames_per_window deve ser maior que zero")

    sorted_frames = sorted(frames, key=lambda item: item.timestamp_s)
    if duration_s <= 0 and sorted_frames:
        duration_s = sorted_frames[-1].timestamp_s
    duration_s = max(0.0, float(duration_s))
    if duration_s == 0:
        duration_s = max(0.001, float(target_window_seconds))

    markers = detect_motion_or_scene_changes(sorted_frames) if include_scene_changes else []
    windows: list[VideoWindow] = []
    start_s = 0.0
    window_index = 1

    while start_s < duration_s - 1e-9:
        end_s = min(duration_s, start_s + target_window_seconds)
        in_window = [
            frame
            for frame in sorted_frames
            if start_s - 1e-9 <= frame.timestamp_s <= end_s + 1e-9
        ]
        marker_subset = [
            marker
            for marker in markers
            if start_s - 1e-9 <= marker.timestamp_s <= end_s + 1e-9
        ]

        selected: list[ExtractedFrame] = []
        start_frame = _nearest_frame(sorted_frames, start_s)
        end_frame = _nearest_frame(sorted_frames, end_s)
        selected.extend(frame for frame in (start_frame, end_frame) if frame is not None)

        for marker in marker_subset:
            marker_frame = next((frame for frame in sorted_frames if frame.index == marker.frame_index), None)
            if marker_frame is not None:
                selected.append(marker_frame)

        remaining_slots = max_frames_per_window - len(_unique_sorted(selected))
        if remaining_slots > 0:
            selected.extend(_select_evenly(in_window, remaining_slots))

        selected = _unique_sorted(selected)
        if len(selected) > max_frames_per_window:
            selected = _select_evenly(selected, max_frames_per_window)

        windows.append(
            VideoWindow(
                index=window_index,
                start_s=round(start_s, 3),
                end_s=round(end_s, 3),
                frames=selected,
                scene_markers=marker_subset,
            )
        )
        start_s = end_s
        window_index += 1

    return windows
