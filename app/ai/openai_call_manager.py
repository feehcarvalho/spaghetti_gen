"""Retry, split and debug handling for OpenAI window calls."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from app.ai.openai_structured import OpenAITimeoutError
from app.video.segmentation import VideoWindow


DEBUG_DIR = Path("data/outputs/debug")
MAX_SPLIT_DEPTH = 3


def call_openai_with_retry_and_split(
    request_payload,
    window: VideoWindow,
    timeout_seconds: int,
    max_retries: int,
):
    """Call OpenAI for one window, retry timeouts, then split the window."""

    return _call_with_retry_and_split(
        request_payload=request_payload,
        window=window,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        depth=0,
    )


def _call_with_retry_and_split(
    *,
    request_payload,
    window: VideoWindow,
    timeout_seconds: int,
    max_retries: int,
    depth: int,
):
    last_error: Exception | None = None
    attempts = max(1, max_retries + 1)
    for attempt in range(1, attempts + 1):
        try:
            return [_execute_payload(request_payload, window, timeout_seconds)]
        except (OpenAITimeoutError, TimeoutError) as exc:
            last_error = exc
            _save_window_debug(
                window=window,
                error=exc,
                attempt=attempt,
                timeout_seconds=timeout_seconds,
                request_payload=request_payload,
            )

    if depth >= MAX_SPLIT_DEPTH or window.duration_s <= 1.0:
        return [_failed_payload(window, last_error or RuntimeError("timeout"))]

    results: list[Any] = []
    for sub_window in _split_window(window):
        sub_results = _call_with_retry_and_split(
            request_payload=request_payload,
            window=sub_window,
            timeout_seconds=max(timeout_seconds, int(timeout_seconds * 1.25)),
            max_retries=max_retries,
            depth=depth + 1,
        )
        results.extend(sub_results)
    return results


def _execute_payload(request_payload, window: VideoWindow, timeout_seconds: int):
    if callable(request_payload):
        return request_payload(window, timeout_seconds)

    if isinstance(request_payload, dict):
        call = request_payload.get("call")
        if callable(call):
            return call(window=window, timeout_seconds=timeout_seconds)

        runner = request_payload.get("runner")
        if runner is not None and hasattr(runner, "request_model"):
            kwargs = dict(request_payload)
            kwargs.pop("runner", None)
            kwargs.pop("call", None)
            kwargs["frames"] = window.frames
            kwargs["timeout_s"] = timeout_seconds
            return runner.request_model(**kwargs)

    raise TypeError("request_payload deve ser callable ou dict com call/runner")


def _split_window(window: VideoWindow) -> list[VideoWindow]:
    midpoint = round((window.start_s + window.end_s) / 2, 3)
    first_frames = [frame for frame in window.frames if frame.timestamp_s <= midpoint]
    second_frames = [frame for frame in window.frames if frame.timestamp_s >= midpoint]
    return [
        VideoWindow(
            index=window.index * 100 + 1,
            start_s=window.start_s,
            end_s=midpoint,
            frames=first_frames or window.frames[: max(1, len(window.frames) // 2)],
            scene_markers=[marker for marker in window.scene_markers if marker.timestamp_s <= midpoint],
            motion_score=window.motion_score,
            status="pending",
        ),
        VideoWindow(
            index=window.index * 100 + 2,
            start_s=midpoint,
            end_s=window.end_s,
            frames=second_frames or window.frames[max(1, len(window.frames) // 2) :],
            scene_markers=[marker for marker in window.scene_markers if marker.timestamp_s >= midpoint],
            motion_score=window.motion_score,
            status="pending",
        ),
    ]


def _failed_payload(window: VideoWindow, error: Exception) -> dict[str, Any]:
    return {
        "falhou": True,
        "window_id": window.window_id,
        "window_index": window.index,
        "start_s": window.start_s,
        "end_s": window.end_s,
        "erro": str(error),
    }


def _save_window_debug(
    *,
    window: VideoWindow,
    error: Exception,
    attempt: int,
    timeout_seconds: int,
    request_payload,
) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = DEBUG_DIR / f"openai_window_timeout_{window.window_id}_{timestamp}.json"
    safe_payload = _safe_payload_summary(request_payload)
    debug = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": safe_payload.get("model"),
        "window_id": window.window_id,
        "window_index": window.index,
        "start_s": window.start_s,
        "end_s": window.end_s,
        "frame_count": len(window.frames),
        "payload_size_bytes_aprox": len(json.dumps(safe_payload, default=str, ensure_ascii=False)),
        "error": str(error),
        "attempt": attempt,
        "timeout_seconds": timeout_seconds,
        "api_key": "[redacted]",
    }
    path.write_text(json.dumps(debug, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _safe_payload_summary(request_payload) -> dict[str, Any]:
    if callable(request_payload):
        return {"type": "callable", "model": getattr(request_payload, "model", None)}
    if not isinstance(request_payload, dict):
        return {"type": type(request_payload).__name__}
    summary: dict[str, Any] = {}
    for key, value in request_payload.items():
        lowered = str(key).casefold()
        if "api" in lowered and "key" in lowered:
            summary[key] = "[redacted]"
        elif key in {"frames", "image_url", "input"}:
            summary[key] = f"[{key} omitted]"
        elif callable(value):
            summary[key] = "[callable]"
        else:
            summary[key] = value
    return summary
