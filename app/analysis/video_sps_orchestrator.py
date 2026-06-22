"""Full SPS video-analysis orchestrator for production-quality runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

from app.ai.analyzer import AnalysisRequest, OpenAIAnalysisProvider
from app.analysis.checkpoint_manager import CheckpointManager, build_analysis_id
from app.analysis.continuous_improvement import generate_continuous_improvement_analysis
from app.analysis.language_normalizer import normalize_analysis_language
from app.analysis.operational_investigator import apply_operational_investigation
from app.analysis.quality_gate import validate_analysis_quality
from app.analysis.sps_classifier import apply_sps_classification_final
from app.analysis.time_auditor import recalculate_microstep_times, validate_timeline_coverage
from app.knowledge.knowledge_orchestrator import SPSContext, build_sps_context_for_analysis
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis
from app.video.adaptive_windowing import create_adaptive_video_windows
from app.video.timeline_index import build_video_timeline_index
from app.video.video_metadata import get_video_metadata


def run_full_sps_video_analysis(
    video_path: str,
    metadata: AnalysisMetadata,
    knowledge_paths: list[str] | None = None,
    layout_image_path: str | None = None,
    layout_json_path: str | None = None,
    quality_mode: str = "maxima",
    resume_from_checkpoint: bool = True,
    progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
) -> OperationalAnalysis:
    """Run the full adaptive, checkpointed SPS video-analysis pipeline."""

    if not video_path:
        raise ValueError("Analise SPS real exige video_path.")
    source = Path(video_path)
    if not source.exists():
        raise FileNotFoundError(f"Video nao encontrado: {source}")

    _notify(progress_callback, "knowledge", {"status": "loading"})
    context = build_sps_context_for_analysis(
        metadata=metadata,
        knowledge_paths=knowledge_paths or [],
        max_chars=_read_int_env("MAX_CONTEXT_CHARS", 18000),
    )

    _notify(progress_callback, "metadata", {"status": "reading"})
    video_metadata = get_video_metadata(str(source))
    analysis_metadata = metadata.model_copy(
        update={
            "ciclo_observado_s": metadata.ciclo_observado_s or video_metadata.duration_s,
            "fonte_video": metadata.fonte_video or str(source),
        }
    )

    analysis_id = build_analysis_id(str(source), analysis_metadata)
    checkpoint = CheckpointManager(analysis_id)
    checkpoint.save_metadata(
        analysis_metadata,
        {
            "video_metadata": video_metadata.model_dump(mode="json"),
            "quality_mode": quality_mode,
            "layout_image_path": layout_image_path,
            "layout_json_path": layout_json_path,
            "knowledge_sources": context.source_documents,
            "unreadable_documents": context.unreadable_documents,
        },
    )

    _notify(progress_callback, "timeline", {"status": "indexing"})
    timeline = build_video_timeline_index(
        str(source),
        base_sample_interval_s=float(os.getenv("VIDEO_FRAME_EXTRACTION_INTERVAL", "1.0")),
        motion_sensitive=True,
    )

    min_window_s, target_window_s, max_window_s = _quality_windows(quality_mode)
    _notify(progress_callback, "windows", {"status": "creating"})
    windows = create_adaptive_video_windows(
        timeline,
        min_window_s=min_window_s,
        target_window_s=target_window_s,
        max_window_s=max_window_s,
    )
    _notify(
        progress_callback,
        "windows",
        {
            "count": len(windows),
            "min_window_s": min_window_s,
            "target_window_s": target_window_s,
            "max_window_s": max_window_s,
            "frames_per_window": [len(window.frames) for window in windows],
        },
    )

    request = AnalysisRequest(
        metadata=analysis_metadata,
        frames=timeline.extracted_frames,
        contexto_sps=context.context_text,
        regras_av_nav_d="\n".join(context.av_nav_d_rules),
        observacoes_usuario=analysis_metadata.observacoes_gerais,
        layout_id=analysis_metadata.bloco or analysis_metadata.linha,
    )

    provider = OpenAIAnalysisProvider(
        image_detail=_quality_detail(quality_mode),
        max_frames=_read_int_env("OPENAI_MAX_FRAMES_PER_WINDOW_REANALYSIS", 18),
    )
    overview_frames = _select_overview_frames(
        timeline.extracted_frames,
        max_frames=_read_int_env("OPENAI_OVERVIEW_MAX_FRAMES", 12),
    )

    analysis = provider.analyze_video_pipeline(
        request,
        video_metadata=video_metadata,
        windows=windows,
        overview_frames=overview_frames,
        reprocess_low_confidence=True,
        progress_callback=progress_callback,
        detail_window=_quality_detail(quality_mode),
        checkpoint_manager=checkpoint,
        resume_from_checkpoint=resume_from_checkpoint,
    )

    analysis = _finalize_analysis(analysis, video_metadata, context)
    checkpoint.save_consolidated_analysis(analysis)
    return analysis


def _finalize_analysis(
    analysis: OperationalAnalysis,
    video_metadata,
    context: SPSContext,
) -> OperationalAnalysis:
    analysis = normalize_analysis_language(analysis, context)
    analysis = apply_operational_investigation(analysis, context)
    analysis = apply_sps_classification_final(analysis)
    analysis = recalculate_microstep_times(analysis)
    analysis = generate_continuous_improvement_analysis(analysis)

    alerts = list(analysis.alertas_validacao)
    for alert in validate_timeline_coverage(analysis, video_metadata):
        if alert not in alerts:
            alerts.append(alert)

    gate = validate_analysis_quality(analysis, video_metadata, context)
    for message in gate.alerts:
        alert = f"Quality gate SPS: {message}"
        if alert not in alerts:
            alerts.append(alert)

    return OperationalAnalysis.model_validate(
        analysis.model_dump() | {"alertas_validacao": alerts}
    )


def _quality_windows(quality_mode: str) -> tuple[float, float, float]:
    normalized = quality_mode.strip().casefold()
    if "rap" in normalized or "diagn" in normalized:
        return 8.0, 18.0, 25.0
    if "equilibr" in normalized:
        return 6.0, 14.0, 22.0
    return (
        float(os.getenv("OPENAI_MIN_WINDOW_SECONDS", "5")),
        float(os.getenv("OPENAI_TARGET_WINDOW_SECONDS", "12")),
        float(os.getenv("OPENAI_MAX_WINDOW_SECONDS", "20")),
    )


def _quality_detail(quality_mode: str) -> str:
    normalized = quality_mode.strip().casefold()
    if "rap" in normalized or "diagn" in normalized:
        return "auto"
    if "equilibr" in normalized:
        return os.getenv("OPENAI_WINDOW_DETAIL", "auto")
    return os.getenv("OPENAI_WINDOW_DETAIL", "auto")


def _select_overview_frames(frames, max_frames: int):
    if not frames or max_frames <= 0:
        return []
    if len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[0]]
    last_index = len(frames) - 1
    indexes = {
        round(position * last_index / (max_frames - 1))
        for position in range(max_frames)
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


def _notify(callback, stage: str, payload: dict[str, Any]) -> None:
    if callback is not None:
        callback(stage, payload)
