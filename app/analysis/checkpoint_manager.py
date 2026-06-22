"""Checkpoint persistence for long SPS video analyses."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis
from app.video.segmentation import VideoWindow


CHECKPOINT_ROOT = Path("data/outputs/checkpoints")


class CheckpointManager:
    """Persist window-level progress without storing secrets."""

    def __init__(self, analysis_id: str, root_dir: str | Path = CHECKPOINT_ROOT) -> None:
        self.analysis_id = analysis_id
        self.root_dir = Path(root_dir) / analysis_id
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_metadata(self, metadata: AnalysisMetadata, extra: dict[str, Any] | None = None) -> Path:
        payload = {
            "analysis_id": self.analysis_id,
            "saved_at": datetime.now().isoformat(timespec="seconds"),
            "metadata": metadata.model_dump(mode="json"),
            "extra": extra or {},
        }
        return self._write_json("metadata.json", payload)

    def save_video_overview(self, overview: Any) -> Path:
        return self._write_json("video_overview.json", _to_jsonable(overview))

    def load_video_overview(self) -> dict[str, Any] | None:
        return self._read_json("video_overview.json")

    def save_window_request(self, window: VideoWindow, payload: dict[str, Any] | None = None) -> Path:
        safe_payload = _sanitize_payload(payload or {})
        safe_payload.update(_window_payload(window))
        return self._write_json(f"{window.window_id}_request.json", safe_payload)

    def save_window_response(self, window: VideoWindow, response: Any) -> Path:
        return self._write_json(f"{window.window_id}_response.json", _to_jsonable(response))

    def save_window_status(self, window: VideoWindow, status: str, error: str | None = None) -> Path:
        return self._write_json(
            f"{window.window_id}_status.json",
            {
                "window_id": window.window_id,
                "window_index": window.index,
                "status": status,
                "error": error,
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

    def is_window_completed(self, window: VideoWindow) -> bool:
        status = self._read_json(f"{window.window_id}_status.json")
        response = self._read_json(f"{window.window_id}_response.json")
        return bool(status and status.get("status") == "completed" and response)

    def load_window_response(self, window: VideoWindow) -> Any | None:
        return self._read_json(f"{window.window_id}_response.json")

    def save_consolidated_analysis(self, analysis: OperationalAnalysis) -> Path:
        return self._write_json(
            "consolidated_analysis.json",
            analysis.model_dump(mode="json"),
        )

    def load_consolidated_analysis(self) -> OperationalAnalysis | None:
        data = self._read_json("consolidated_analysis.json")
        if not data:
            return None
        return OperationalAnalysis.model_validate(data)

    def checkpoint_exists(self) -> bool:
        return self.root_dir.exists() and any(self.root_dir.glob("*_status.json"))

    def _write_json(self, name: str, payload: Any) -> Path:
        path = self.root_dir / name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _read_json(self, name: str) -> Any | None:
        path = self.root_dir / name
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


def build_analysis_id(video_path: str, metadata: AnalysisMetadata) -> str:
    raw = "|".join(
        [
            str(Path(video_path).resolve(strict=False)),
            metadata.departamento,
            metadata.posto,
            metadata.processo,
            metadata.data_analise,
        ]
    )
    digest = hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
    safe_post = "".join(char if char.isalnum() else "_" for char in metadata.posto).strip("_") or "posto"
    return f"{safe_post}_{digest}"


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    return value


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = str(key).casefold()
        if "api" in lowered and "key" in lowered:
            safe[key] = "[redacted]"
        elif key in {"image_url", "input", "frames"}:
            safe[key] = f"[{key} omitted]"
        else:
            safe[key] = _to_jsonable(value)
    return safe


def _window_payload(window: VideoWindow) -> dict[str, Any]:
    return {
        "window_id": window.window_id,
        "window_index": window.index,
        "start_s": window.start_s,
        "end_s": window.end_s,
        "duration_s": window.duration_s,
        "frame_count": len(window.frames),
        "frame_paths": window.frame_paths,
        "frame_timestamps_s": window.frame_timestamps_s,
        "motion_score": window.motion_score,
        "scene_change_markers": [
            {
                "timestamp_s": marker.timestamp_s,
                "frame_index": marker.frame_index,
                "score": marker.score,
                "reason": marker.reason,
            }
            for marker in window.scene_markers
        ],
    }
