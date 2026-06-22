from __future__ import annotations

from app.analysis.operational_language_repair import (
    detect_generic_process_phrases,
    repair_activity_text,
    repair_generic_process_phrase,
)
from app.analysis.quality_gate import detect_generic_operational_phrases
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
        confianca=0.9,
    )
    return OperationalAnalysis(
        metadata=AnalysisMetadata(departamento="Funcao 5", posto="5.2.6", processo="Teste", responsavel="SPS", data_analise="2026-05-28"),
        microetapas=[step],
        resumo_tempos=TimeSummary(av_s=0, nav_s=2, d_s=0, total_s=2, av_percent=0, nav_percent=100, d_percent=0),
    )


def test_generic_phrases_generate_alerts():
    for text in (
        "Ir ate o ponto necessario para continuidade da operacao.",
        "Preparar recurso de apoio conforme necessidade da operacao.",
        "Posicionar componente conforme necessidade da operacao.",
    ):
        assert detect_generic_process_phrases(text)
        assert detect_generic_operational_phrases(_analysis(text))


def test_generic_supply_point_rewrites_to_greenbox_when_context_confirms():
    repaired = repair_generic_process_phrase(
        "Ir ate o ponto de abastecimento indicado.",
        "Memoria: Green Box / caixa verde de porcas.",
    )
    assert repaired == "Ir ate a Green Box/caixa verde e pegar as porcas necessarias para o eixo."


def test_specific_detail_passes_generic_blocker():
    assert detect_generic_process_phrases("Ir ate a Green Box/caixa verde e pegar as porcas necessarias para o eixo.") == []


def test_repair_activity_text_removes_generic_resource_phrase():
    repaired = repair_activity_text("Preparar recurso de apoio conforme necessidade da operacao.", context={"dispositivo": "VR de pneu"})
    assert repaired == "Preparar VR de pneu para apoiar a operacao."
