"""Consolidate window analyses into a final OperationalAnalysis."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.ai.window_analyzer import WindowAnalysis, WindowMicroStep
from app.analysis.improvements import generate_improvements_from_waste
from app.analysis.language_normalizer import normalize_microstep_language
from app.analysis.sps_classifier import classify_microstep_sps
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, SpaghettiData
from app.utils.time_utils import apply_cumulative_times, calculate_time_summary, seconds_to_mmss


NOT_CONCLUSIVE_VIDEO = "não conclusivo pelo vídeo; requer validação no gemba"
LIGHT_OVERLAP_TOLERANCE_S = 0.5
GAP_ALERT_THRESHOLD_S = 2.0


@dataclass(frozen=True)
class _StepCandidate:
    source_window_index: int
    step: WindowMicroStep


def consolidate_window_analyses(
    window_analyses: list[WindowAnalysis],
    metadata: AnalysisMetadata,
) -> OperationalAnalysis:
    """Join window analyses, preserve distinct actions, and recalculate all times."""

    alerts: list[str] = []
    candidates: list[_StepCandidate] = []

    for window_analysis in window_analyses:
        if window_analysis.falhou:
            _append_alert(
                alerts,
                f"Janela {window_analysis.window_index} nao analisada: {window_analysis.erro or 'falha desconhecida'}",
            )
            continue

        if not window_analysis.microetapas:
            reason = window_analysis.explicacao_sem_microetapas or NOT_CONCLUSIVE_VIDEO
            _append_alert(alerts, f"Janela {window_analysis.window_index} sem microetapas observaveis: {reason}")
            continue

        for step in window_analysis.microetapas:
            candidates.append(_StepCandidate(window_analysis.window_index, step))
            if step.confianca < 0.60:
                _append_alert(
                    alerts,
                    f"Microetapa candidata da janela {window_analysis.window_index} com baixa confianca ({step.confianca:.2f}); requer validacao no gemba/SPS.",
                )

    if not candidates:
        raise ValueError("Nenhuma microetapa observavel foi consolidada; analise real nao concluida.")

    candidates.sort(key=lambda item: (item.step.inicio_s, item.step.fim_s, item.source_window_index))
    deduplicated = _remove_obvious_duplicates(candidates, alerts)
    microsteps = _to_microsteps(deduplicated, alerts)
    microsteps = [classify_microstep_sps(normalize_microstep_language(step)) for step in microsteps]
    microsteps = apply_cumulative_times(microsteps)
    summary = calculate_time_summary(microsteps, metadata.takt_time_s)

    normalized_metadata = metadata.model_copy(
        update={
            "ciclo_observado_s": metadata.ciclo_observado_s or summary.total_s,
        }
    )

    analysis = OperationalAnalysis.model_validate(
        {
            "metadata": normalized_metadata.model_dump(),
            "microetapas": [step.model_dump() for step in microsteps],
            "resumo_tempos": summary.model_dump(),
            "spaghetti": SpaghettiData().model_dump(),
            "melhorias": [],
            "recomendacoes_gerais": _build_recommendations(alerts),
            "alertas_validacao": alerts,
        }
    )
    improvements = generate_improvements_from_waste(analysis)
    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {"melhorias": [item.model_dump() for item in improvements]}
    )


def _remove_obvious_duplicates(
    candidates: list[_StepCandidate],
    alerts: list[str],
) -> list[_StepCandidate]:
    kept: list[_StepCandidate] = []
    for candidate in candidates:
        duplicate = next(
            (
                item
                for item in kept
                if _is_obvious_duplicate(item.step, candidate.step)
            ),
            None,
        )
        if duplicate is not None:
            _append_alert(
                alerts,
                (
                    "Duplicidade obvia removida entre janelas "
                    f"{duplicate.source_window_index} e {candidate.source_window_index}."
                ),
            )
            continue
        kept.append(candidate)
    return kept


def _to_microsteps(candidates: list[_StepCandidate], alerts: list[str]) -> list[MicroStep]:
    microsteps: list[MicroStep] = []
    previous_end: float | None = None

    for index, candidate in enumerate(candidates, start=1):
        step = candidate.step
        start_s = round(max(0.0, step.inicio_s), 3)
        end_s = round(max(start_s, step.fim_s), 3)

        if previous_end is not None:
            gap_s = start_s - previous_end
            if gap_s > GAP_ALERT_THRESHOLD_S:
                _append_alert(
                    alerts,
                    f"Buraco temporal de {gap_s:.2f}s antes da microetapa {index}; validar cobertura do video.",
                )
            if start_s < previous_end:
                overlap_s = previous_end - start_s
                if overlap_s <= LIGHT_OVERLAP_TOLERANCE_S and end_s > previous_end:
                    _append_alert(
                        alerts,
                        f"Sobreposicao leve corrigida antes da microetapa {index} ({overlap_s:.2f}s).",
                    )
                    start_s = previous_end
                else:
                    _append_alert(
                        alerts,
                        f"Sobreposicao temporal relevante na microetapa {index}; requer validacao no gemba/SPS.",
                    )

        duration_s = round(max(0.0, end_s - start_s), 3)
        if duration_s == 0:
            _append_alert(
                alerts,
                f"Microetapa {index} com duracao zero; tempo nao conclusivo pelo video.",
            )

        evidence = (step.evidencia_visual or "").strip() or NOT_CONCLUSIVE_VIDEO
        evidence_observable = (step.evidencia_observavel or evidence).strip() or evidence
        if evidence.casefold() in {"nao conclusivo", "não conclusivo"}:
            evidence = NOT_CONCLUSIVE_VIDEO
            evidence_observable = NOT_CONCLUSIVE_VIDEO

        description = (step.instrucao_padrao or step.descricao_tecnica_detalhada).strip()

        microsteps.append(
            MicroStep(
                numero=index,
                inicio_s=start_s,
                fim_s=end_s,
                duracao_s=duration_s,
                inicio_formatado=seconds_to_mmss(start_s),
                fim_formatado=seconds_to_mmss(end_s),
                duracao_formatada=seconds_to_mmss(duration_s),
                etapa_detalhada=description,
                descricao_tecnica_detalhada=step.descricao_tecnica_detalhada.strip(),
                instrucao_padrao=description,
                evidencia_observavel=evidence_observable,
                interpretacao_de_processo=step.interpretacao_de_processo or description,
                classificacao=step.classificacao,  # type: ignore[arg-type]
                justificativa_tecnica=step.justificativa_tecnica.strip(),
                ferramenta_observacao=step.ferramenta_observacao,
                tipo_movimento=step.tipo_movimento,
                tipo_desperdicio=step.tipo_desperdicio,
                local_inicio=step.local_inicio,
                local_fim=step.local_fim,
                evidencia_visual=evidence,
                memoria_utilizada=step.memoria_utilizada,
                confianca=step.confianca,
                baixa_confianca_motivo=step.baixa_confianca_motivo,
                requer_validacao_gemba=step.requer_validacao_gemba,
            )
        )
        previous_end = max(previous_end or 0.0, end_s)

    return microsteps


def _is_obvious_duplicate(first: WindowMicroStep, second: WindowMicroStep) -> bool:
    first_desc = _normalize_description(first.descricao_tecnica_detalhada)
    second_desc = _normalize_description(second.descricao_tecnica_detalhada)
    if not first_desc or first_desc != second_desc:
        return False
    close_start = abs(first.inicio_s - second.inicio_s) <= 0.5
    close_end = abs(first.fim_s - second.fim_s) <= 0.5
    return (close_start and close_end) or _overlap_ratio(first, second) >= 0.85


def _overlap_ratio(first: WindowMicroStep, second: WindowMicroStep) -> float:
    overlap = max(0.0, min(first.fim_s, second.fim_s) - max(first.inicio_s, second.inicio_s))
    shortest = max(0.001, min(first.duracao_s, second.duracao_s))
    return overlap / shortest


def _normalize_description(value: str) -> str:
    text = re.sub(r"\s+", " ", value.casefold()).strip()
    return re.sub(r"[^a-z0-9à-ÿ ]+", "", text)


def _build_recommendations(alerts: list[str]) -> list[str]:
    recommendations = [
        "Validar a analise no gemba/SPS antes de usar como padrao oficial.",
        "Usar mais de uma amostra para definir tempo padrao ou alterar metodo.",
    ]
    if alerts:
        recommendations.append("Revisar alertas de baixa confianca, buracos temporais ou sobreposicoes antes do Excel final.")
    return recommendations


def _append_alert(alerts: list[str], message: str) -> None:
    if message not in alerts:
        alerts.append(message)
