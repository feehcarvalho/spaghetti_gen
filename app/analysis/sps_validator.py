"""Final SPS validation and generic-content blocking."""

from __future__ import annotations

import os
import re
from collections import Counter
from difflib import SequenceMatcher

from app.analysis.improvements import generate_improvements_from_waste
from app.schemas.analysis import OperationalAnalysis


GENERIC_ANALYSIS_ERROR = (
    "A análise retornou conteúdo genérico ou repetido. Reprocessar com mais frames/contexto."
)
FORCE_EXCEL_EXPORT_WITH_ALERTS = True
GENERIC_PHRASES = (
    "realiza operacao",
    "realiza operação",
    "executa atividade",
    "faz processo",
    "trabalha no produto",
    "operador realiza",
    "atividade operacional",
    "processo observado",
    "deslocar o realiza",
)


def validate_sps_analysis(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Validate SPS completeness and block generic/template-like analyses."""

    if not analysis.microetapas:
        raise ValueError(GENERIC_ANALYSIS_ERROR)

    alerts = list(analysis.alertas_validacao)
    if detect_generic_or_repeated_analysis(analysis):
        _append_alert(alerts, GENERIC_ANALYSIS_ERROR)

    for step in analysis.microetapas:
        if not step.etapa_detalhada.strip():
            _append_alert(alerts, f"Microetapa {step.numero} sem descricao tecnica detalhada.")
        if not step.justificativa_tecnica.strip():
            _append_alert(alerts, f"Microetapa {step.numero} sem justificativa tecnica.")
        if step.fim_s < step.inicio_s or abs(step.duracao_s - (step.fim_s - step.inicio_s)) > 0.1:
            _append_alert(alerts, f"Microetapa {step.numero} com timestamps incoerentes.")
        if step.confianca < 0.60:
            _append_alert(
                alerts,
                f"Microetapa {step.numero} com confianca < 0.60; requer validacao no gemba/SPS.",
            )
        if step.baixa_confianca_motivo:
            _append_alert(
                alerts,
                f"Microetapa {step.numero} possui classificacao/observacao incerta; requer validacao no gemba/SPS.",
            )
        if _is_generic_description(step.etapa_detalhada):
            _append_alert(
                alerts,
                f"Microetapa {step.numero} possui descricao generica demais; revisar com mais frames/contexto.",
            )
        if step.classificacao == "D":
            _append_alert(
                alerts,
                f"Microetapa {step.numero} classificada como D deve ser tratada em melhorias e validada no gemba/SPS.",
            )

    if analysis.metadata.ciclo_observado_s is not None:
        diff = abs(analysis.resumo_tempos.total_s - analysis.metadata.ciclo_observado_s)
        tolerance = max(3.0, analysis.metadata.ciclo_observado_s * 0.20)
        if diff > tolerance:
            _append_alert(
                alerts,
                (
                    f"Tempo total ({analysis.resumo_tempos.total_s:.2f}s) incoerente com ciclo observado "
                    f"({analysis.metadata.ciclo_observado_s:.2f}s); revisar cobertura do video."
                ),
            )

    improvements = generate_improvements_from_waste(analysis)
    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {
            "melhorias": [item.model_dump() for item in improvements],
            "alertas_validacao": alerts,
        }
    )


def detect_generic_or_repeated_analysis(analysis: OperationalAnalysis) -> bool:
    """Detect template-like, PMGS-default or repeated analyses."""

    steps = analysis.microetapas
    if not steps:
        return True

    metadata_text = " ".join(
        [
            analysis.metadata.departamento,
            analysis.metadata.posto,
            analysis.metadata.processo,
            analysis.metadata.observacoes_gerais or "",
        ]
    ).casefold()
    combined = " ".join(
        [step.etapa_detalhada for step in steps]
        + [step.justificativa_tecnica for step in steps]
    ).casefold()

    if "pmgs" in combined and "pmgs" not in metadata_text:
        return True

    descriptions = [_normalize(step.etapa_detalhada) for step in steps]
    if any(not description for description in descriptions):
        return True

    if len(steps) == 10 and len(set(descriptions)) <= 4:
        return True

    counts = Counter(descriptions)
    most_common_count = counts.most_common(1)[0][1]
    if len(steps) >= 5 and most_common_count / len(steps) >= 0.45:
        return True

    if len(steps) >= 4:
        pair_count = 0
        similar_pairs = 0
        for i, first in enumerate(descriptions):
            for second in descriptions[i + 1 :]:
                pair_count += 1
                if SequenceMatcher(None, first, second).ratio() >= 0.92:
                    similar_pairs += 1
        if pair_count and similar_pairs / pair_count >= 0.55:
            return True

    generic_count = sum(1 for step in steps if _is_generic_description(step.etapa_detalhada))
    if len(steps) == 1 and generic_count == 1:
        return True
    if generic_count >= max(2, len(steps) // 3):
        return True

    for step in steps:
        if step.fim_s < step.inicio_s:
            return True
        if abs(step.duracao_s - (step.fim_s - step.inicio_s)) > 0.2:
            return True

    starts = [step.inicio_s for step in steps]
    if starts != sorted(starts):
        return True

    return False


def assert_analysis_can_generate_excel(
    analysis: OperationalAnalysis | None,
    *,
    block_on_quality: bool = False,
) -> None:
    """Guard Excel export, blocking only technical fatal errors by default."""

    if analysis is None:
        raise ValueError("Excel nao pode ser gerado sem analise valida.")
    if not analysis.microetapas:
        raise ValueError("Excel nao pode ser gerado sem microetapas validas.")
    force_export = _env_flag("FORCE_EXCEL_EXPORT_WITH_ALERTS", FORCE_EXCEL_EXPORT_WITH_ALERTS)
    effective_block_on_quality = block_on_quality and not force_export
    if effective_block_on_quality and detect_generic_or_repeated_analysis(analysis):
        raise ValueError(f"Excel bloqueado: {GENERIC_ANALYSIS_ERROR}")
    from app.analysis.quality_gate import assert_quality_gate_passed

    assert_quality_gate_passed(analysis, block_on_quality=effective_block_on_quality)


def _is_generic_description(description: str) -> bool:
    normalized = _normalize(description)
    if len(normalized) < 12:
        return True
    return any(phrase in normalized for phrase in GENERIC_PHRASES)


def _normalize(value: str) -> str:
    text = re.sub(r"\s+", " ", value.casefold()).strip()
    return re.sub(r"[^a-z0-9à-ÿ ]+", "", text)


def _append_alert(alerts: list[str], message: str) -> None:
    if message not in alerts:
        alerts.append(message)


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().casefold() in {"1", "true", "yes", "sim", "on"}
