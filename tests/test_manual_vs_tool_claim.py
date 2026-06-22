from __future__ import annotations

from app.analysis.activity_text import get_microstep_activity_text
from app.analysis.export_preparer import prepare_analysis_for_export
from app.analysis.quality_gate import detect_unsupported_tool_or_method_claims
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _analysis(text: str) -> OperationalAnalysis:
    step = MicroStep(
        numero=1,
        inicio_s=0,
        fim_s=2,
        duracao_s=2,
        inicio_formatado="00:00",
        fim_formatado="00:02",
        duracao_formatada="00:02",
        etapa_detalhada=text,
        instrucao_operacional=text,
        classificacao="AV",
        justificativa_tecnica="Etapa classificada como AV porque altera a condicao de montagem do produto.",
        peca_componente="porcas",
        confianca=0.9,
    )
    return OperationalAnalysis(
        metadata=AnalysisMetadata(departamento="Funcao 5", posto="5.2.6", processo="Pneu", responsavel="SPS", data_analise="2026-05-28"),
        microetapas=[step],
        resumo_tempos=TimeSummary(av_s=2, nav_s=0, d_s=0, total_s=2, av_percent=100, nav_percent=0, d_percent=0),
    )


def test_manual_context_removes_pneumatic_claim():
    prepared = prepare_analysis_for_export(_analysis("Fixar as porcas com a parafusadeira pneumatica."), "instalacao manual observada")
    assert "parafusadeira pneum" not in get_microstep_activity_text(prepared.microetapas[0]).casefold()
    assert "manual" in get_microstep_activity_text(prepared.microetapas[0]).casefold()


def test_unconfirmed_tool_marks_alert():
    analysis = _analysis("Fixar as porcas com a parafusadeira pneumatica.")
    assert detect_unsupported_tool_or_method_claims(analysis, "")


def test_memory_confirmed_tool_is_allowed():
    analysis = _analysis("Fixar as porcas com a parafusadeira pneumatica.")
    assert not detect_unsupported_tool_or_method_claims(analysis, "Memoria confirma parafusadeira pneumatica nesta etapa.")
