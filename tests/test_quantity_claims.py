from __future__ import annotations

from app.analysis.activity_text import get_microstep_activity_text
from app.analysis.export_preparer import prepare_analysis_for_export
from app.analysis.quality_gate import detect_unsupported_tool_or_method_claims
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _analysis(text: str, confirmed_by: str | None = None) -> OperationalAnalysis:
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
        justificativa_tecnica="Etapa classificada como AV porque altera a montagem do produto.",
        peca_componente="porcas",
        quantidade_confirmada_por=confirmed_by,
        confianca=0.9,
    )
    return OperationalAnalysis(
        metadata=AnalysisMetadata(departamento="Funcao 5", posto="5.2.6", processo="Pneu", responsavel="SPS", data_analise="2026-05-28"),
        microetapas=[step],
        resumo_tempos=TimeSummary(av_s=2, nav_s=0, d_s=0, total_s=2, av_percent=100, nav_percent=0, d_percent=0),
    )


def test_two_nuts_requires_confirmation():
    analysis = _analysis("Colocar duas porcas manualmente para travamento inicial.")
    assert detect_unsupported_tool_or_method_claims(analysis, "")
    prepared = prepare_analysis_for_export(analysis, "")
    assert "duas porcas" not in get_microstep_activity_text(prepared.microetapas[0]).casefold()
    assert prepared.microetapas[0].quantidade_confirmada_por == "nao_confirmada"


def test_eight_remaining_nuts_requires_confirmation():
    prepared = prepare_analysis_for_export(_analysis("Instalar oito porcas restantes conforme padrao."), "")
    assert "oito porcas" not in get_microstep_activity_text(prepared.microetapas[0]).casefold()


def test_confirmed_quantity_is_kept():
    prepared = prepare_analysis_for_export(
        _analysis("Colocar duas porcas manualmente para travamento inicial.", confirmed_by="memoria"),
        "Memoria confirma duas porcas para travamento inicial.",
    )
    assert "duas porcas" in get_microstep_activity_text(prepared.microetapas[0]).casefold()
