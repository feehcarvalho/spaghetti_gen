"""Diagnose full-video SPS analysis cost and timeout risk."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analysis.checkpoint_manager import CHECKPOINT_ROOT
from app.schemas.analysis import AnalysisMetadata
from app.video.adaptive_windowing import create_adaptive_video_windows
from app.video.timeline_index import build_video_timeline_index


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostico do pipeline completo de video SPS.")
    parser.add_argument("video_path", help="Caminho do video operacional")
    args = parser.parse_args()

    video_path = Path(args.video_path)
    if not video_path.exists():
        raise SystemExit(f"Video nao encontrado: {video_path}")

    metadata = AnalysisMetadata(
        departamento="Diagnostico",
        posto="DIAGNOSTICO",
        processo="Diagnostico de video",
        responsavel="Codex",
        data_analise="2026-05-20",
        fonte_video=str(video_path),
    )
    timeline = build_video_timeline_index(str(video_path))
    windows = create_adaptive_video_windows(timeline)
    checkpoints = list(CHECKPOINT_ROOT.glob("*")) if CHECKPOINT_ROOT.exists() else []

    frame_counts = [len(window.frames) for window in windows]
    estimated_calls = 1 + len(windows)
    high_risk_windows = [
        window.window_id
        for window in windows
        if len(window.frames) >= 14 or window.duration_s >= 20
    ]

    print("Diagnostico de video SPS")
    print(f"video: {video_path}")
    print(f"duracao_s: {timeline.metadata.duration_s}")
    print(f"fps: {timeline.metadata.fps}")
    print(f"resolucao: {timeline.metadata.width}x{timeline.metadata.height}")
    print(f"frames_total: {timeline.metadata.frame_count}")
    print(f"tamanho_mb: {timeline.metadata.file_size_mb}")
    print(f"codec: {timeline.metadata.codec or 'nao identificado'}")
    print(f"timestamps_indexados: {len(timeline.samples)}")
    print(f"mudancas_visuais: {len(timeline.scene_change_markers)}")
    print(f"janelas_estimadas: {len(windows)}")
    print(f"frames_por_janela: {frame_counts}")
    print(f"risco_timeout: {'alto' if high_risk_windows else 'normal'}")
    print(f"janelas_risco_timeout: {high_risk_windows}")
    print(f"chamadas_openai_estimadas_minimas: {estimated_calls}")
    print(f"checkpoints_existentes: {len(checkpoints)}")
    print("memorias_carregadas: data/knowledge_raw sera consultado no pipeline real")
    print(f"metadata_exemplo: {metadata.posto} / {metadata.processo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
