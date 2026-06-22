"""Adaptive temporal windows for SPS video analysis."""

from __future__ import annotations

import os
from statistics import mean

from app.video.frame_extractor import ExtractedFrame
from app.video.segmentation import VideoWindow
from app.video.timeline_index import TimelineSample, VideoTimelineIndex


def create_adaptive_video_windows(
    timeline: VideoTimelineIndex,
    min_window_s: float = 5.0,
    target_window_s: float = 12.0,
    max_window_s: float = 20.0,
) -> list[VideoWindow]:
    """Create windows that cover the whole useful timeline with local adaptation."""

    if min_window_s <= 0 or target_window_s <= 0 or max_window_s <= 0:
        raise ValueError("duracoes de janela devem ser maiores que zero")
    if min_window_s > target_window_s or target_window_s > max_window_s:
        raise ValueError("esperado min_window_s <= target_window_s <= max_window_s")

    duration_s = float(timeline.metadata.duration_s)
    if duration_s <= 0:
        duration_s = max((sample.timestamp_s for sample in timeline.samples), default=0.0)
    duration_s = max(duration_s, min_window_s if not timeline.samples else duration_s)

    frames = timeline.extracted_frames
    if not frames:
        raise ValueError("indice temporal sem frames amostrados")

    global_motion = mean(timeline.motion_scores) if timeline.motion_scores else 0.0
    high_motion = max(0.035, global_motion * 1.35)
    low_motion = max(0.006, global_motion * 0.60)
    overlap_s = min(1.0, max(0.25, min_window_s * 0.12))
    max_frames_base = _read_int_env("OPENAI_MAX_FRAMES_PER_WINDOW_BASE", 10)

    windows: list[VideoWindow] = []
    start_s = 0.0
    window_index = 1
    while start_s < duration_s - 1e-9:
        lookahead_end = min(duration_s, start_s + target_window_s)
        local_samples = _samples_in_range(timeline.samples, start_s, lookahead_end)
        local_motion = mean([sample.motion_score for sample in local_samples]) if local_samples else global_motion

        if local_motion >= high_motion:
            window_size = min_window_s
        elif local_motion <= low_motion:
            window_size = max_window_s
        else:
            window_size = target_window_s

        scene_near = _next_scene_change(timeline, start_s, min(duration_s, start_s + window_size))
        if scene_near is not None and scene_near - start_s >= min_window_s:
            end_s = min(duration_s, scene_near + overlap_s)
        else:
            end_s = min(duration_s, start_s + window_size)

        if end_s <= start_s:
            end_s = min(duration_s, start_s + min_window_s)

        window_samples = _samples_in_range(timeline.samples, start_s, end_s)
        selected_frames = _select_window_frames(frames, window_samples, start_s, end_s, max_frames_base)
        scene_markers = [
            marker
            for marker in timeline.scene_change_markers
            if start_s - 1e-9 <= marker.timestamp_s <= end_s + 1e-9
        ]
        motion_score = mean([sample.motion_score for sample in window_samples]) if window_samples else 0.0

        windows.append(
            VideoWindow(
                index=window_index,
                start_s=round(start_s, 3),
                end_s=round(end_s, 3),
                frames=selected_frames,
                scene_markers=scene_markers,
                motion_score=round(motion_score, 5),
                status="pending",
            )
        )

        if end_s >= duration_s - 1e-9:
            break
        start_s = max(start_s + 0.001, end_s - overlap_s)
        window_index += 1

    return windows


def _samples_in_range(samples: list[TimelineSample], start_s: float, end_s: float) -> list[TimelineSample]:
    return [sample for sample in samples if start_s - 1e-9 <= sample.timestamp_s <= end_s + 1e-9]


def _next_scene_change(timeline: VideoTimelineIndex, start_s: float, end_s: float) -> float | None:
    markers = [
        marker.timestamp_s
        for marker in timeline.scene_change_markers
        if start_s < marker.timestamp_s <= end_s
    ]
    return min(markers) if markers else None


def _select_window_frames(
    all_frames: list[ExtractedFrame],
    samples: list[TimelineSample],
    start_s: float,
    end_s: float,
    max_count: int,
) -> list[ExtractedFrame]:
    frames_by_index = {frame.index: frame for frame in all_frames}
    selected: list[ExtractedFrame] = []

    for timestamp in (start_s, end_s):
        nearest = _nearest_frame(all_frames, timestamp)
        if nearest is not None:
            selected.append(nearest)

    for sample in samples:
        if sample.is_key_frame or sample.is_scene_change or sample.is_action:
            frame = frames_by_index.get(sample.frame_index)
            if frame is not None:
                selected.append(frame)

    remaining = max(0, max_count - len(_unique_sorted(selected)))
    if remaining:
        in_window = [
            frame
            for frame in all_frames
            if start_s - 1e-9 <= frame.timestamp_s <= end_s + 1e-9
        ]
        selected.extend(_select_evenly(in_window, remaining))

    selected = _unique_sorted(selected)
    if len(selected) > max_count:
        selected = _select_evenly(selected, max_count)
    return selected


def _nearest_frame(frames: list[ExtractedFrame], timestamp_s: float) -> ExtractedFrame | None:
    if not frames:
        return None
    return min(frames, key=lambda frame: abs(frame.timestamp_s - timestamp_s))


def _unique_sorted(frames: list[ExtractedFrame]) -> list[ExtractedFrame]:
    by_path: dict[str, ExtractedFrame] = {}
    for frame in frames:
        by_path[frame.path] = frame
    return sorted(by_path.values(), key=lambda frame: frame.timestamp_s)


def _select_evenly(frames: list[ExtractedFrame], max_count: int) -> list[ExtractedFrame]:
    if max_count <= 0 or not frames:
        return []
    frames = sorted(frames, key=lambda frame: frame.timestamp_s)
    if len(frames) <= max_count:
        return frames
    if max_count == 1:
        return [frames[len(frames) // 2]]
    last_index = len(frames) - 1
    indexes = {
        round(position * last_index / (max_count - 1))
        for position in range(max_count)
    }
    return [frames[index] for index in sorted(indexes)]


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
