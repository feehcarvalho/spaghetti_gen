from __future__ import annotations

from app.analysis.schema_compat import LOW_CONFIDENCE_DEFAULT_REASON, normalize_analysis_payload_for_current_schema
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _analysis_payload() -> dict:
    return {
        "metadata": AnalysisMetadata(
            departamento="CHASSI",
            posto="5.2.6",
            processo="Oitao XT",
            responsavel="SPS",
            data_analise="2026-06-01",
        ).model_dump(),
        "microetapas": [
            {
                "numero": 86,
                "inicio_s": 1.0,
                "fim_s": 2.0,
                "duracao_s": 1.0,
                "inicio_formatado": "00:01",
                "fim_formatado": "00:02",
                "duracao_formatada": "00:01",
                "tempo_acumulado_s": 1.0,
                "etapa_detalhada": "Conferir o posicionamento do pneu no eixo indicado.",
                "classificacao": "NAV",
                "justificativa_tecnica": "Etapa necessaria para controle do metodo observado.",
                "confianca": 0.6,
                "requer_validacao_gemba": False,
            }
        ],
        "resumo_tempos": TimeSummary(
            av_s=0,
            nav_s=1,
            d_s=0,
            total_s=1,
            av_percent=0,
            nav_percent=100,
            d_percent=0,
        ).model_dump(),
    }


def test_low_confidence_without_reason_is_repaired_before_validation():
    payload = normalize_analysis_payload_for_current_schema(_analysis_payload())
    analysis = OperationalAnalysis.model_validate(payload)
    step = analysis.microetapas[0]
    assert step.numero == 86
    assert step.baixa_confianca_motivo == LOW_CONFIDENCE_DEFAULT_REASON
    assert step.requer_validacao_gemba is True


def test_missing_operational_instruction_is_backfilled_from_detailed_step():
    payload = normalize_analysis_payload_for_current_schema(_analysis_payload())
    step = MicroStep.model_validate(payload["microetapas"][0])
    assert step.instrucao_operacional == "Conferir o posicionamento do pneu no eixo indicado."
