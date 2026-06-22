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
        classificacao="NAV",
        justificativa_tecnica="Etapa necessaria ao metodo atual.",
        peca_componente="porcas",
        confianca=0.9,
    )
    return OperationalAnalysis(
        metadata=AnalysisMetadata(departamento="Funcao 5", posto="5.2.6", processo="Pneu", responsavel="SPS", data_analise="2026-05-28"),
        microetapas=[step],
        resumo_tempos=TimeSummary(av_s=0, nav_s=2, d_s=0, total_s=2, av_percent=0, nav_percent=100, d_percent=0),
    )


def test_greenbox_is_preserved_from_context():
    prepared = prepare_analysis_for_export(_analysis("Ir ate o ponto de abastecimento indicado."), "Green Box / caixa verde de porcas")
    assert "Green Box/caixa verde" in get_microstep_activity_text(prepared.microetapas[0])


def test_bluebox_is_not_kept_when_context_says_greenbox():
    prepared = prepare_analysis_for_export(_analysis("Ir ate o Bluebox e pegar porcas."), "Green Box / caixa verde de porcas")
    assert "Bluebox" not in get_microstep_activity_text(prepared.microetapas[0])


def test_unconfirmed_greenbox_generates_alert():
    analysis = _analysis("Ir ate a Green Box/caixa verde e pegar porcas.")
    assert detect_unsupported_tool_or_method_claims(analysis, "")
