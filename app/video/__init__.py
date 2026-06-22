"""Utilitarios de video da aplicacao."""

from app.video.frame_extractor import ExtractedFrame, extract_frames, extract_representative_frames
from app.video.segmentation import (
    SceneMarker,
    VideoWindow,
    detect_motion_or_scene_changes,
    split_video_into_windows,
)
from app.video.video_metadata import VideoMetadata, get_video_metadata

__all__ = [
    "ExtractedFrame",
    "SceneMarker",
    "VideoMetadata",
    "VideoWindow",
    "detect_motion_or_scene_changes",
    "extract_frames",
    "extract_representative_frames",
    "get_video_metadata",
    "split_video_into_windows",
]
