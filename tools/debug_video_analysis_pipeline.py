"""Diagnose video metadata, frame extraction and window planning."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.video.frame_extractor import extract_representative_frames
from app.video.segmentation import split_video_into_windows
from app.video.video_metadata import get_video_metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnostico do pipeline de video SPS.")
    parser.add_argument("video_path", type=Path, help="Caminho do video a diagnosticar.")
    parser.add_argument("--window-seconds", type=int, default=15)
    parser.add_argument("--max-frames-per-window", type=int, default=10)
    parser.add_argument("--sample-interval", type=float, default=1.0)
    args = parser.parse_args()

    metadata = get_video_metadata(str(args.video_path))
    frame_dir = Path("data/outputs/debug/frames") / args.video_path.stem
    frames = extract_representative_frames(
        video_path=str(args.video_path),
        output_dir=str(frame_dir),
        sample_interval_s=args.sample_interval,
    )
    windows = split_video_into_windows(
        frames,
        duration_s=metadata.duration_s,
        target_window_seconds=args.window_seconds,
        max_frames_per_window=args.max_frames_per_window,
        include_scene_changes=True,
    )

    estimated_calls = 1 + len(windows)
    timeout_risk = (
        "alto"
        if metadata.duration_s > 180 or len(windows) > 16 or metadata.file_size_mb > 500
        else "baixo/moderado"
    )

    print(f"Video: {metadata.video_path}")
    print(f"Duracao: {metadata.duration_s:.2f}s")
    print(f"FPS: {metadata.fps:.2f}")
    print(f"Resolucao: {metadata.width}x{metadata.height}")
    print(f"Frame count: {metadata.frame_count}")
    print(f"Tamanho: {metadata.file_size_mb:.2f} MB")
    print(f"Frames extraidos: {len(frames)}")
    print(f"Janelas: {len(windows)}")
    print(f"Frames por janela: {[len(window.frames) for window in windows]}")
    print(f"Estimativa de chamadas OpenAI: {estimated_calls}")
    print(f"Risco de timeout: {timeout_risk}")


if __name__ == "__main__":
    main()
