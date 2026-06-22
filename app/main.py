"""Pipeline principal da aplicação IA SPS Scania."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from app.ai.analyzer import (
    AnalysisProvider,
    AnalysisRequest,
    DEFAULT_SAMPLE_ANALYSIS,
    MOCK_VIDEO_ERROR,
    MockAnalysisProvider,
    OpenAIAnalysisProvider,
)
from app.analysis.sps_validator import assert_analysis_can_generate_excel, validate_sps_analysis
from app.analysis.export_preparer import prepare_analysis_for_export
from app.analysis.video_sps_orchestrator import run_full_sps_video_analysis
from app.excel.template_writer import write_analysis_to_template
from app.knowledge.local_retriever import retrieve_context
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis
from app.utils.time_utils import apply_cumulative_times, calculate_time_summary
from app.video.frame_extractor import ExtractedFrame, extract_representative_frames
from app.video.segmentation import split_video_into_windows
from app.video.video_metadata import VideoMetadata, get_video_metadata


logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[1]
OPENAI_API_KEY_ERROR = "OPENAI_API_KEY não configurada. Configure a chave para análise real de vídeo."
OPENAI_VIDEO_REQUIRED_ERROR = "Análise real de vídeo exige vídeo anexado."
DEMO_SAMPLE_FOR_REAL_VIDEO_ERROR = (
    "A análise retornou dados de demonstração para um vídeo real. Verifique o provider."
)

ZERO_DURATION_ANALYSIS_ALERT = (
    "A analise retornou tempo total zero. Revise os tempos das microetapas antes de gerar "
    "a planilha final; se o video nao mostra o ciclo completo, refaca a coleta ou informe "
    "observacoes complementares."
)
DEFAULT_WINDOW_SECONDS = 15
DEFAULT_MAX_FRAMES_PER_WINDOW = 10
DEFAULT_OVERVIEW_MAX_FRAMES = 12


def _normalize_provider_name(provider_name: str) -> str:
    return provider_name.strip().casefold()


def _refresh_env() -> None:
    load_dotenv(REPO_ROOT / ".env", override=True)


def _has_openai_api_key() -> bool:
    _refresh_env()
    api_key = os.getenv("OPENAI_API_KEY")
    return bool(api_key and api_key.strip())


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _select_provider(provider_name: str) -> AnalysisProvider:
    normalized = _normalize_provider_name(provider_name)
    if normalized == "mock":
        return MockAnalysisProvider()
    if normalized == "openai":
        return OpenAIAnalysisProvider()
    raise ValueError(f"Provider desconhecido: {provider_name}")


def _validate_provider_video_policy(provider_name: str, video_path: str | None) -> str:
    normalized = _normalize_provider_name(provider_name)
    if normalized == "mock" and video_path:
        raise ValueError(MOCK_VIDEO_ERROR)
    if normalized == "openai":
        if not _has_openai_api_key():
            raise ValueError(OPENAI_API_KEY_ERROR)
        if not video_path:
            raise ValueError(OPENAI_VIDEO_REQUIRED_ERROR)
    if normalized not in {"mock", "openai"}:
        raise ValueError(f"Provider desconhecido: {provider_name}")
    return normalized


def _json_output_path(output_path: str) -> Path:
    return Path(output_path).with_suffix(".json")


def _frames_output_dir(video_path: str, output_path: str) -> Path:
    output_parent = Path(output_path).parent
    return output_parent / "frames" / Path(video_path).stem


def _read_rules_av_nav_d(knowledge_root: str) -> str:
    rules_path = Path(knowledge_root) / "corporativo" / "regras_av_nav_d.md"
    if not rules_path.exists():
        return ""
    return rules_path.read_text(encoding="utf-8")


def _limit_context(text: str) -> str:
    max_chars = _read_int_env("MAX_CONTEXT_CHARS", 12000)
    if max_chars <= 0:
        return text
    return text[:max_chars]


def _select_overview_frames(
    frames: list[ExtractedFrame],
    max_frames: int = DEFAULT_OVERVIEW_MAX_FRAMES,
) -> list[ExtractedFrame]:
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


def _notify_progress(progress_callback, stage: str, payload: dict) -> None:
    if progress_callback is not None:
        progress_callback(stage, payload)


def _default_layout_path(metadata: AnalysisMetadata) -> Path:
    return Path("data") / "layouts" / f"{metadata.posto}.json"


def _resolve_layout_path(
    layout_path: str | None,
    metadata: AnalysisMetadata,
    insert_spaghetti: bool,
) -> str | None:
    if layout_path:
        return layout_path
    if not insert_spaghetti:
        return None

    candidate = _default_layout_path(metadata)
    if candidate.exists():
        return str(candidate)

    logger.warning("Layout JSON nao encontrado para posto %s em %s", metadata.posto, candidate)
    return None


def _analysis_query(metadata: AnalysisMetadata) -> str:
    parts = [
        "análise operacional SPS",
        metadata.departamento,
        metadata.linha or "",
        metadata.bloco or "",
        metadata.posto,
        metadata.processo,
    ]
    return " ".join(part for part in parts if part)


def _normalize_analysis_metadata(
    analysis: OperationalAnalysis,
    metadata: AnalysisMetadata,
    video_path: str | None,
) -> OperationalAnalysis:
    updated_metadata = metadata.model_copy(
        update={
            "ciclo_observado_s": metadata.ciclo_observado_s or analysis.resumo_tempos.total_s,
            "fonte_video": metadata.fonte_video or video_path,
        }
    )
    return analysis.model_copy(update={"metadata": updated_metadata})


def _recalculate_summary(analysis: OperationalAnalysis) -> OperationalAnalysis:
    microsteps = apply_cumulative_times(analysis.microetapas)
    summary = calculate_time_summary(
        microsteps,
        analysis.metadata.takt_time_s,
    )
    alerts = list(analysis.alertas_validacao)
    if summary.total_s == 0 and ZERO_DURATION_ANALYSIS_ALERT not in alerts:
        alerts.append(ZERO_DURATION_ANALYSIS_ALERT)
    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {
            "microetapas": [step.model_dump() for step in microsteps],
            "resumo_tempos": summary.model_dump(),
            "alertas_validacao": alerts,
        }
    )


def _save_analysis_json(analysis: OperationalAnalysis, output_path: str) -> Path:
    analysis = prepare_analysis_for_export(analysis)
    json_path = _json_output_path(output_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return json_path


def _matches_demo_sample(analysis: OperationalAnalysis) -> bool:
    if not DEFAULT_SAMPLE_ANALYSIS.exists():
        return False

    try:
        sample_data = json.loads(DEFAULT_SAMPLE_ANALYSIS.read_text(encoding="utf-8"))
        sample = OperationalAnalysis.model_validate(sample_data)
    except Exception:
        return False

    analysis_steps = [step.etapa_detalhada for step in analysis.microetapas]
    sample_steps = [step.etapa_detalhada for step in sample.microetapas]
    analysis_improvements = [item.descricao_desperdicio for item in analysis.melhorias]
    sample_improvements = [item.descricao_desperdicio for item in sample.melhorias]
    return analysis_steps == sample_steps and analysis_improvements == sample_improvements


def run_analysis_pipeline(
    video_path: str | None,
    template_path: str,
    output_path: str,
    metadata: AnalysisMetadata,
    knowledge_root: str = "data/knowledge_raw",
    provider_name: str = "mock",
    fill_standard: bool = False,
    standard_export_mode: str = "standard_legacy",
    insert_charts: bool = False,
    insert_spaghetti: bool = False,
    layout_path: str | None = None,
    layout_image_path: str | None = None,
    fps: float = 1.0,
    max_frames: int | None = None,
    window_seconds: int | None = None,
    max_frames_per_window: int | None = None,
    reprocess_low_confidence: bool = True,
    detail_window: str | None = None,
    quality_mode: str = "maxima",
) -> str:
    """Executa análise completa e gera Excel/JSON de saída."""

    _validate_provider_video_policy(provider_name, video_path)

    template = Path(template_path)
    if not template.exists():
        raise FileNotFoundError(f"Template nao encontrado: {template}")

    analysis = run_analysis_only(
        video_path=video_path,
        output_path=output_path,
        metadata=metadata,
        knowledge_root=knowledge_root,
        provider_name=provider_name,
        fps=fps,
        max_frames=max_frames,
        window_seconds=window_seconds,
        max_frames_per_window=max_frames_per_window,
        reprocess_low_confidence=reprocess_low_confidence,
        detail_window=detail_window,
        quality_mode=quality_mode,
    )
    resolved_layout_path = _resolve_layout_path(layout_path, metadata, insert_spaghetti)
    analysis = prepare_analysis_for_export(analysis)
    assert_analysis_can_generate_excel(analysis)

    generated_path = write_analysis_to_template(
        analysis=analysis,
        template_path=template_path,
        output_path=output_path,
        fill_standard=fill_standard,
        standard_export_mode=standard_export_mode,
        insert_charts=insert_charts,
        insert_spaghetti=insert_spaghetti,
        layout_path=resolved_layout_path,
        layout_image_path=layout_image_path,
    )
    _save_analysis_json(analysis, output_path)

    return generated_path


def run_analysis_only(
    video_path: str | None,
    output_path: str,
    metadata: AnalysisMetadata,
    knowledge_root: str = "data/knowledge_raw",
    knowledge_paths: list[str] | None = None,
    provider_name: str = "mock",
    fps: float = 1.0,
    max_frames: int | None = None,
    window_seconds: int | None = None,
    max_frames_per_window: int | None = None,
    reprocess_low_confidence: bool = True,
    detail_window: str | None = None,
    quality_mode: str = "maxima",
    resume_from_checkpoint: bool = True,
    progress_callback=None,
) -> OperationalAnalysis:
    """Executa provider e retorna OperationalAnalysis validado sem gerar Excel."""

    normalized_provider = _validate_provider_video_policy(provider_name, video_path)

    if normalized_provider == "openai" and video_path:
        if window_seconds is not None:
            os.environ["OPENAI_TARGET_WINDOW_SECONDS"] = str(window_seconds)
        if max_frames_per_window is not None:
            os.environ["OPENAI_MAX_FRAMES_PER_WINDOW_BASE"] = str(max_frames_per_window)
        if detail_window:
            os.environ["OPENAI_WINDOW_DETAIL"] = detail_window
        analysis = run_full_sps_video_analysis(
            video_path=video_path,
            metadata=metadata,
            knowledge_paths=[knowledge_root] + list(knowledge_paths or []),
            quality_mode=quality_mode,
            resume_from_checkpoint=resume_from_checkpoint,
            progress_callback=progress_callback,
        )
        if _matches_demo_sample(analysis):
            raise ValueError(DEMO_SAMPLE_FOR_REAL_VIDEO_ERROR)
        return analysis

    frames: list[ExtractedFrame] = []
    video_metadata: VideoMetadata | None = None
    analysis_metadata = metadata
    if video_path:
        video = Path(video_path)
        if not video.exists():
            raise FileNotFoundError(f"Video nao encontrado: {video}")
        video_metadata = get_video_metadata(str(video))
        _notify_progress(progress_callback, "metadata", video_metadata.model_dump())
        analysis_metadata = metadata.model_copy(
            update={
                "ciclo_observado_s": metadata.ciclo_observado_s or video_metadata.duration_s,
                "fonte_video": metadata.fonte_video or str(video),
            }
        )
        frame_dir = _frames_output_dir(video_path, output_path)
        logger.info("Extraindo frames de %s para %s", video, frame_dir)
        sample_interval_s = 1.0 / fps if fps > 0 else 1.0
        frames = extract_representative_frames(
            video_path=str(video),
            output_dir=str(frame_dir),
            sample_interval_s=sample_interval_s,
        )
        if not frames:
            raise ValueError("Nenhum frame foi extraido do video.")
        _notify_progress(progress_callback, "frames", {"count": len(frames), "output_dir": str(frame_dir)})

    context = retrieve_context(
        query=_analysis_query(analysis_metadata),
        root_dir=knowledge_root,
        position_id=analysis_metadata.posto,
        top_k=12,
    )
    context = _limit_context(context)
    rules = _read_rules_av_nav_d(knowledge_root)

    request = AnalysisRequest(
        metadata=analysis_metadata,
        frames=frames,
        contexto_sps=context,
        regras_av_nav_d=rules,
        observacoes_usuario=analysis_metadata.observacoes_gerais,
        layout_id=analysis_metadata.bloco or analysis_metadata.linha,
    )

    provider = _select_provider(provider_name)
    if normalized_provider == "openai" and video_metadata is not None:
        if not isinstance(provider, OpenAIAnalysisProvider):
            raise ValueError("Provider openai invalido para analise real de video.")
        selected_window_seconds = window_seconds or _read_int_env("OPENAI_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS)
        selected_max_frames = max_frames_per_window or _read_int_env(
            "OPENAI_MAX_FRAMES_PER_WINDOW",
            DEFAULT_MAX_FRAMES_PER_WINDOW,
        )
        windows = split_video_into_windows(
            frames,
            duration_s=video_metadata.duration_s,
            target_window_seconds=selected_window_seconds,
            max_frames_per_window=selected_max_frames,
            include_scene_changes=True,
        )
        _notify_progress(
            progress_callback,
            "windows",
            {
                "count": len(windows),
                "window_seconds": selected_window_seconds,
                "max_frames_per_window": selected_max_frames,
                "frames_per_window": [len(window.frames) for window in windows],
            },
        )
        overview_frames = _select_overview_frames(
            frames,
            max_frames=_read_int_env("OPENAI_OVERVIEW_MAX_FRAMES", DEFAULT_OVERVIEW_MAX_FRAMES),
        )
        analysis = provider.analyze_video_pipeline(
            request,
            video_metadata=video_metadata,
            windows=windows,
            overview_frames=overview_frames,
            reprocess_low_confidence=reprocess_low_confidence,
            progress_callback=progress_callback,
            detail_window=detail_window,
        )
    else:
        analysis = provider.analyze(request)
    if video_path and normalized_provider != "mock" and _matches_demo_sample(analysis):
        raise ValueError(DEMO_SAMPLE_FOR_REAL_VIDEO_ERROR)
    analysis = _normalize_analysis_metadata(analysis, analysis_metadata, video_path)
    analysis = _recalculate_summary(analysis)
    if normalized_provider == "openai":
        analysis = validate_sps_analysis(analysis)
    return analysis
