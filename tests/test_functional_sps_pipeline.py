from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.ai.openai_structured import OpenAITimeoutError
from app.ai.openai_call_manager import call_openai_with_retry_and_split
from app.ai.prompt_builder import build_analysis_prompt
from app.ai.analyzer import AnalysisRequest
from app.ai.video_overview import VideoOverview
from app.ai.window_analyzer import WindowAnalysis, WindowMicroStep, reanalyze_low_confidence_windows
from app.analysis.checkpoint_manager import CheckpointManager
from app.analysis.improvements import generate_improvements_from_waste
from app.analysis.language_normalizer import contains_generic_video_language, normalize_microstep_language
from app.analysis.quality_gate import validate_analysis_quality
from app.analysis.time_auditor import recalculate_microstep_times
from app.excel.template_writer import write_analysis_to_template
from app.knowledge.knowledge_orchestrator import build_sps_context_for_analysis
from app.schemas.analysis import AnalysisMetadata, ImprovementSuggestion, MicroStep, OperationalAnalysis, TimeSummary
from app.video.frame_extractor import ExtractedFrame
from app.video.segmentation import VideoWindow


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
RUNTIME_ROOT = REPO_ROOT / "data" / "outputs" / "test_functional_sps_pipeline_runtime"


def metadata(process: str = "Processo teste") -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="Teste",
        posto="POSTO.TESTE",
        processo=process,
        responsavel="Teste Local",
        data_analise="2026-05-20",
    )


def microstep(number: int, text: str, classification: str = "NAV", start: float | None = None, end: float | None = None) -> MicroStep:
    start_s = float(number - 1) if start is None else start
    end_s = float(number) if end is None else end
    return MicroStep(
        numero=number,
        inicio_s=start_s,
        fim_s=end_s,
        duracao_s=end_s - start_s,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada=text,
        classificacao=classification,  # type: ignore[arg-type]
        justificativa_tecnica="Acao necessaria ao metodo atual, sem transformacao direta do produto.",
        evidencia_visual="Evidencia visual especifica.",
        confianca=0.9,
    )


def analysis_from_steps(steps: list[MicroStep], md: AnalysisMetadata | None = None) -> OperationalAnalysis:
    total = sum(step.duracao_s for step in steps)
    av = sum(step.duracao_s for step in steps if step.classificacao == "AV")
    nav = sum(step.duracao_s for step in steps if step.classificacao == "NAV")
    d = sum(step.duracao_s for step in steps if step.classificacao == "D")
    improvements = [
        ImprovementSuggestion(
            microetapa_numero=step.numero,
            descricao_desperdicio=f"Perda na etapa {step.numero}",
            tipo_desperdicio=step.tipo_desperdicio or "espera",
            sugestao_pratica="Validar causa no gemba e reduzir desperdicio observado.",
            prioridade="Baixa",
        )
        for step in steps
        if step.classificacao == "D"
    ]
    return OperationalAnalysis(
        metadata=md or metadata(),
        microetapas=steps,
        resumo_tempos=TimeSummary(
            av_s=av,
            nav_s=nav,
            d_s=d,
            total_s=total,
            av_percent=(av / total * 100) if total else 0,
            nav_percent=(nav / total * 100) if total else 0,
            d_percent=(d / total * 100) if total else 0,
        ),
        melhorias=improvements,
    )


def test_no_fixed_microstep_count():
    short = analysis_from_steps([microstep(i, f"Verificar item tecnico {i}") for i in range(1, 5)])
    long = analysis_from_steps([microstep(i, f"Verificar item tecnico {i}") for i in range(1, 38)])

    assert len(short.microetapas) == 4
    assert len(long.microetapas) == 37


def test_no_pmgs_leakage():
    analysis = analysis_from_steps([microstep(1, "Posicionar componente PMGS no dispositivo")])
    result = validate_analysis_quality(analysis, None, "")

    assert not result.passed
    assert any("PMGS" in error for error in result.critical_errors)


def test_imperative_language():
    normalized = normalize_microstep_language(microstep(1, "O operador pega a peca na bancada."))

    assert normalized.instrucao_padrao.startswith("Pegar")


def test_generic_video_language_blocked():
    assert contains_generic_video_language("O operador pega a peça")
    analysis = analysis_from_steps([microstep(1, "O operador pega a peca")])
    result = validate_analysis_quality(analysis, None, "")

    assert result.warnings or result.critical_errors


def test_time_audit():
    step = microstep(1, "Verificar etiqueta do componente", start=0, end=3)
    bad = MicroStep.model_validate(step.model_dump() | {"duracao_s": 3.0})
    analysis = analysis_from_steps([bad])
    audited = recalculate_microstep_times(analysis)

    assert audited.microetapas[0].duracao_s == 3.0
    assert audited.microetapas[0].tempo_acumulado_s == 3.0
    assert audited.resumo_tempos.total_s == 3.0


def runtime_dir() -> Path:
    path = RUNTIME_ROOT / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_window_checkpoint():
    checkpoint = CheckpointManager("unit", root_dir=runtime_dir())
    window = VideoWindow(index=1, start_s=0, end_s=5)
    response = WindowAnalysis(
        window_index=1,
        start_s=0,
        end_s=5,
        microetapas=[],
        explicacao_sem_microetapas="Sem acao observavel.",
        confianca_media=0,
    )

    checkpoint.save_window_response(window, [response])
    checkpoint.save_window_status(window, "completed")

    assert checkpoint.is_window_completed(window)
    assert checkpoint.load_window_response(window)[0]["window_index"] == 1


def test_timeout_subdivides_window():
    calls = {"count": 0}

    def failing_call(window, timeout_seconds):
        calls["count"] += 1
        raise OpenAITimeoutError("timeout")

    window = VideoWindow(index=1, start_s=0, end_s=8)
    results = call_openai_with_retry_and_split(failing_call, window, timeout_seconds=1, max_retries=0)

    assert calls["count"] > 1
    assert all(item.get("falhou") for item in results if isinstance(item, dict))


def test_low_confidence_reanalysis():
    class FakeRunner:
        timeout_s = 10

        def request_model(self, **kwargs):
            return WindowAnalysis(
                window_index=1,
                start_s=0,
                end_s=5,
                microetapas=[
                    WindowMicroStep(
                        numero_local=1,
                        inicio_s=0,
                        fim_s=1,
                        duracao_s=1,
                        descricao_tecnica_detalhada="Verificar componente especifico",
                        classificacao="NAV",
                        justificativa_tecnica="Necessario ao metodo atual.",
                        evidencia_visual="Frame mostra verificacao.",
                        confianca=0.95,
                    )
                ],
                confianca_media=0.95,
            )

    low = WindowAnalysis(
        window_index=1,
        start_s=0,
        end_s=5,
        microetapas=[],
        explicacao_sem_microetapas="nao conclusivo",
        confianca_media=0.2,
    )
    window = VideoWindow(index=1, start_s=0, end_s=5)
    overview = VideoOverview(
        processo_aparente="Processo teste",
        ciclo_completo_aparente=True,
        confianca_geral=0.8,
    )
    result = reanalyze_low_confidence_windows(
        [low],
        [window],
        overview,
        "contexto",
        "AV NAV D",
        metadata(),
        runner=FakeRunner(),  # type: ignore[arg-type]
    )

    assert result[0].confianca_media == 0.95


def test_d_generates_improvement():
    step = microstep(1, "Aguardar liberacao do sistema", "D")
    analysis = analysis_from_steps([step])

    assert generate_improvements_from_waste(analysis)


def test_quality_gate_blocks_bad_analysis():
    steps = [microstep(i, "Operador realiza operacao no processo observado") for i in range(1, 11)]
    analysis = analysis_from_steps(steps)
    result = validate_analysis_quality(analysis, None, "")

    assert not result.passed


def test_excel_only_after_valid_analysis():
    if not TEMPLATE.exists():
        pytest.skip("Template padrao nao encontrado")
    steps = [microstep(i, "Operador realiza operacao no processo observado") for i in range(1, 11)]
    analysis = analysis_from_steps(steps)
    output_path = runtime_dir() / "blocked.xlsx"

    write_analysis_to_template(analysis, str(TEMPLATE), str(output_path))

    assert output_path.exists()


def test_knowledge_context_used():
    memory = runtime_dir() / "memoria.md"
    memory.write_text("WPO deve ser usado para confirmar variante. AV NAV D seguem regras SPS.", encoding="utf-8")
    md = metadata()
    context = build_sps_context_for_analysis(md, [str(memory)], max_chars=4000)
    request = AnalysisRequest(
        metadata=md,
        frames=[],
        contexto_sps=context.context_text,
        regras_av_nav_d="\n".join(context.av_nav_d_rules),
    )
    prompt = build_analysis_prompt(request)

    assert "WPO" in prompt
    assert "CONTEXTO SPS OBRIGATORIO" in prompt
