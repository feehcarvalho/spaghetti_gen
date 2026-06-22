"""Tests for the real video SPS analysis pipeline."""

from __future__ import annotations

import inspect
from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
import pytest

from app.ai.analyzer import AnalysisProviderError, OpenAIAnalysisProvider
from app.ai.openai_structured import OpenAITimeoutError
from app.ai.video_overview import VideoOverview
from app.ai.window_analyzer import (
    WindowAnalysis,
    WindowMicroStep,
    analyze_window_with_timeout_recovery,
)
from app.analysis.consolidator import consolidate_window_analyses
from app.analysis.improvements import generate_improvements_from_waste
from app.analysis.sps_validator import detect_generic_or_repeated_analysis, validate_sps_analysis
from app.main import run_analysis_pipeline, run_analysis_only
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary
from app.video.frame_extractor import ExtractedFrame
from app.video.segmentation import VideoWindow, split_video_into_windows


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
RUNTIME_ROOT = REPO_ROOT / "data" / "outputs" / "test_real_video_pipeline_runtime"


def _metadata(process: str = "Montagem teste") -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="Teste",
        posto="POSTO.TESTE",
        processo=process,
        responsavel="Teste Local",
        data_analise="2026-05-15",
        takt_time_s=120.0,
    )


def _frame(index: int, timestamp_s: float, path: str = "dummy.jpg") -> ExtractedFrame:
    return ExtractedFrame(
        index=index,
        timestamp_s=timestamp_s,
        timestamp_formatado="00:00",
        path=path,
        width=64,
        height=48,
    )


def _window_step(number: int, start: float, end: float, classification: str = "NAV") -> WindowMicroStep:
    return WindowMicroStep(
        numero_local=number,
        inicio_s=start,
        fim_s=end,
        duracao_s=end - start,
        descricao_tecnica_detalhada=f"Selecionar componente especifico numero {number}",
        classificacao=classification,
        justificativa_tecnica="Acao observada e necessaria ao metodo atual sem transformacao direta.",
        evidencia_visual=f"Frame mostra componente especifico numero {number}.",
        tipo_movimento="selecionar",
        confianca=0.85,
    )


def _analysis_with_steps(steps: list[MicroStep], metadata: AnalysisMetadata | None = None) -> OperationalAnalysis:
    av_s = sum(step.duracao_s for step in steps if step.classificacao == "AV")
    nav_s = sum(step.duracao_s for step in steps if step.classificacao == "NAV")
    d_s = sum(step.duracao_s for step in steps if step.classificacao == "D")
    total = av_s + nav_s + d_s
    summary = TimeSummary(
        av_s=av_s,
        nav_s=nav_s,
        d_s=d_s,
        total_s=total,
        av_percent=(av_s / total) * 100 if total else 0,
        nav_percent=(nav_s / total) * 100 if total else 0,
        d_percent=(d_s / total) * 100 if total else 0,
    )
    return OperationalAnalysis(
        metadata=metadata or _metadata(),
        microetapas=steps,
        resumo_tempos=summary,
    )


def _microstep(number: int, description: str, classification: str = "NAV", confidence: float = 0.9) -> MicroStep:
    return MicroStep(
        numero=number,
        inicio_s=float(number - 1),
        fim_s=float(number),
        duracao_s=1.0,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada=description,
        classificacao=classification,  # type: ignore[arg-type]
        justificativa_tecnica="Justificativa tecnica especifica baseada na evidencia visual observada.",
        evidencia_visual="Evidencia visual especifica no frame.",
        confianca=confidence,
        baixa_confianca_motivo="Imagem parcialmente ocluida; requer validacao no gemba/SPS."
        if confidence < 0.7
        else None,
    )


def test_no_pmgs_hardcoded_in_openai_provider():
    source = inspect.getsource(OpenAIAnalysisProvider)

    assert "sample_analysis_pmgs_p1" not in source
    assert "DEFAULT_SAMPLE_ANALYSIS" not in source


def test_mock_blocked_with_video():
    video_path = REPO_ROOT / "data" / "videos" / "uploads" / "mock_block_real_video.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"video real deve bloquear mock antes de analisar")

    with pytest.raises(ValueError, match="mock.*analisa"):
        run_analysis_only(
            video_path=str(video_path),
            output_path=str(REPO_ROOT / "data" / "outputs" / "mock_block_real_video.xlsx"),
            metadata=_metadata(),
            provider_name="mock",
        )


def test_dynamic_microstep_count():
    window_analysis = WindowAnalysis(
        window_index=1,
        start_s=0,
        end_s=12,
        microetapas=[_window_step(number, number - 1, number) for number in range(1, 13)],
        confianca_media=0.85,
    )

    analysis = consolidate_window_analyses([window_analysis], _metadata())

    assert len(analysis.microetapas) == 12
    assert [step.numero for step in analysis.microetapas] == list(range(1, 13))


def test_video_split_windows():
    frames = [_frame(index + 1, float(index)) for index in range(91)]

    windows = split_video_into_windows(
        frames,
        duration_s=90,
        target_window_seconds=15,
        max_frames_per_window=10,
        include_scene_changes=False,
    )

    assert len(windows) == 6
    assert [(window.start_s, window.end_s) for window in windows] == [
        (0.0, 15.0),
        (15.0, 30.0),
        (30.0, 45.0),
        (45.0, 60.0),
        (60.0, 75.0),
        (75.0, 90.0),
    ]


def test_window_analysis_empty_allowed():
    analysis = WindowAnalysis(
        window_index=1,
        start_s=0,
        end_s=15,
        microetapas=[],
        explicacao_sem_microetapas="Sem acao observavel nesta janela.",
        confianca_media=0.0,
    )

    assert analysis.microetapas == []


def test_consolidation_recalculates_accumulated_time():
    window_analysis = WindowAnalysis(
        window_index=1,
        start_s=0,
        end_s=3,
        microetapas=[
            _window_step(1, 0, 1),
            _window_step(2, 1, 3),
        ],
        confianca_media=0.85,
    )

    analysis = consolidate_window_analyses([window_analysis], _metadata())

    assert [step.tempo_acumulado_s for step in analysis.microetapas] == [1.0, 3.0]
    assert analysis.resumo_tempos.total_s == 3.0


def test_detect_generic_repeated_analysis():
    steps = [
        _microstep(number, "Operador realiza operacao no processo observado")
        for number in range(1, 11)
    ]
    analysis = _analysis_with_steps(steps)

    assert detect_generic_or_repeated_analysis(analysis) is True


def test_timeout_splits_window_or_retries():
    class FakeRunner:
        timeout_s = 10

        def __init__(self):
            self.calls = 0

        def request_model(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise OpenAITimeoutError("timeout")
            return WindowAnalysis(
                window_index=1,
                start_s=0,
                end_s=5,
                microetapas=[_window_step(1, 0, 1)],
                confianca_media=0.8,
            )

    runtime_dir = RUNTIME_ROOT / uuid4().hex
    runtime_dir.mkdir(parents=True, exist_ok=True)
    image = runtime_dir / "frame.jpg"
    cv2.imwrite(str(image), np.zeros((10, 10, 3), dtype=np.uint8))
    window = VideoWindow(
        index=1,
        start_s=0,
        end_s=10,
        frames=[_frame(1, 0, str(image)), _frame(2, 10, str(image))],
    )
    overview = VideoOverview(
        processo_aparente="Processo teste",
        ciclo_completo_aparente=True,
        confianca_geral=0.8,
    )
    runner = FakeRunner()

    analyses = analyze_window_with_timeout_recovery(
        window,
        overview,
        context="contexto",
        rules_av_nav_d="AV NAV D",
        metadata=_metadata(),
        runner=runner,  # type: ignore[arg-type]
        image_detail="auto",
    )

    assert runner.calls >= 2
    assert analyses
    assert any(not item.falhou for item in analyses)


def test_no_excel_on_failed_real_analysis(monkeypatch):
    runtime_dir = RUNTIME_ROOT / uuid4().hex
    runtime_dir.mkdir(parents=True, exist_ok=True)
    video_path = runtime_dir / "failed_real_video.mp4"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        5.0,
        (32, 24),
    )
    if not writer.isOpened():
        pytest.skip("OpenCV nao conseguiu inicializar VideoWriter MP4 neste ambiente")
    try:
        for _ in range(5):
            writer.write(np.zeros((24, 32, 3), dtype=np.uint8))
    finally:
        writer.release()

    output_path = runtime_dir / "failed_real.xlsx"
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-placeholder")
    monkeypatch.setattr("app.main._refresh_env", lambda: None)

    def _fail(self, *args, **kwargs):
        raise AnalysisProviderError("falha real OpenAI")

    monkeypatch.setattr(OpenAIAnalysisProvider, "analyze_video_pipeline", _fail)

    with pytest.raises(AnalysisProviderError):
        run_analysis_pipeline(
            video_path=str(video_path),
            template_path=str(TEMPLATE),
            output_path=str(output_path),
            metadata=_metadata(),
            provider_name="openai",
        )

    assert not output_path.exists()


def test_d_steps_generate_improvements():
    analysis = _analysis_with_steps(
        [_microstep(1, "Operador procura componente no abastecimento lateral", "D")]
    )

    improvements = generate_improvements_from_waste(analysis)

    assert len(improvements) == 1
    assert improvements[0].microetapa_numero == 1
    assert improvements[0].requer_validacao_gemba is True


def test_low_confidence_alerts():
    analysis = _analysis_with_steps(
        [_microstep(1, "Inspecionar etiqueta parcialmente ocluida no produto", "NAV", confidence=0.55)]
    )

    validated = validate_sps_analysis(analysis)

    assert any("confianca < 0.60" in alert for alert in validated.alertas_validacao)
    assert any("validacao no gemba" in alert for alert in validated.alertas_validacao)
