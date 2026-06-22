"""Conversao e revalidacao da revisao humana de microetapas."""

from __future__ import annotations

import logging
from math import isclose
from typing import Any

from app.schemas.analysis import MicroStep, OperationalAnalysis
from app.utils.time_utils import apply_cumulative_times, calculate_time_summary, seconds_to_mmss


logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.7
TIME_TOLERANCE_S = 0.1

REVIEW_COLUMNS = [
    "numero",
    "inicio_s",
    "fim_s",
    "duracao_s",
    "tempo_acumulado_s",
    "tempo_acumulado_formatado",
    "classificacao",
    "etapa_detalhada",
    "justificativa_tecnica",
    "ferramenta_observacao",
    "confianca",
]


def analysis_to_dataframe(analysis: OperationalAnalysis):
    """Converte microetapas para DataFrame editavel, ou lista de dicts se pandas ausente."""

    rows = [
        {
            "numero": step.numero,
            "inicio_s": step.inicio_s,
            "fim_s": step.fim_s,
            "duracao_s": step.duracao_s,
            "tempo_acumulado_s": step.tempo_acumulado_s,
            "tempo_acumulado_formatado": step.tempo_acumulado_formatado or "",
            "classificacao": step.classificacao,
            "etapa_detalhada": step.etapa_detalhada,
            "justificativa_tecnica": step.justificativa_tecnica,
            "ferramenta_observacao": step.ferramenta_observacao or "",
            "confianca": step.confianca,
        }
        for step in analysis.microetapas
    ]

    try:
        import pandas as pd
    except ImportError:
        return rows

    return pd.DataFrame(rows, columns=REVIEW_COLUMNS)


def dataframe_to_analysis(df, original_analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Reconstrói e valida OperationalAnalysis a partir da tabela revisada."""

    records = _records_from_dataframe(df)
    original_by_number = {step.numero: step for step in original_analysis.microetapas}
    alerts = list(original_analysis.alertas_validacao)
    reviewed_steps: list[MicroStep] = []

    for row in records:
        number = _coerce_int(row.get("numero"), "numero")
        original_step = original_by_number.get(number)
        if original_step is None:
            raise ValueError(f"Microetapa revisada sem correspondencia original: {number}")

        reviewed_step = _row_to_microstep(row, original_step)
        _log_human_changes(original_step, reviewed_step, alerts)
        reviewed_steps.append(reviewed_step)

    reviewed_data = original_analysis.model_dump()
    reviewed_data.update(
        {
            "microetapas": [step.model_dump() for step in reviewed_steps],
            "alertas_validacao": alerts,
        }
    )
    reviewed = OperationalAnalysis.model_validate(reviewed_data)
    return recalculate_after_review(reviewed)


def recalculate_after_review(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Recalcula resumo, sincroniza melhorias e adiciona alertas de revisao."""

    alerts = list(analysis.alertas_validacao)
    microsteps = apply_cumulative_times(analysis.microetapas)
    analysis = analysis.model_copy(update={"microetapas": microsteps})
    summary = calculate_time_summary(microsteps, analysis.metadata.takt_time_s)
    updated_improvements = _sync_improvements_with_steps(analysis)
    d_steps_with_improvement = {
        item.microetapa_numero
        for item in updated_improvements
        if item.microetapa_numero is not None
    }

    for step in analysis.microetapas:
        if step.confianca < LOW_CONFIDENCE_THRESHOLD or step.baixa_confianca_motivo:
            _append_alert(
                alerts,
                f"Microetapa {step.numero} marcada para validacao: baixa confianca ({step.confianca:.2f}).",
            )
        if step.classificacao == "D" and step.numero not in d_steps_with_improvement:
            _append_alert(
                alerts,
                f"Microetapa {step.numero} classificada como D sem sugestao de melhoria vinculada.",
            )

    cycle_seconds = analysis.metadata.ciclo_observado_s
    if cycle_seconds is not None and not isclose(summary.total_s, cycle_seconds, abs_tol=TIME_TOLERANCE_S):
        _append_alert(
            alerts,
            (
                f"Tempo total revisado ({summary.total_s:.2f}s) diverge do ciclo observado "
                f"({cycle_seconds:.2f}s)."
            ),
        )

    reviewed_data = analysis.model_dump()
    reviewed_data.update(
        {
            "resumo_tempos": summary.model_dump(),
            "microetapas": [step.model_dump() for step in microsteps],
            "melhorias": [item.model_dump() for item in updated_improvements],
            "alertas_validacao": alerts,
        }
    )
    return OperationalAnalysis.model_validate(reviewed_data)


def _records_from_dataframe(df) -> list[dict[str, Any]]:
    if hasattr(df, "to_dict"):
        return [dict(row) for row in df.to_dict(orient="records")]
    if isinstance(df, list):
        return [dict(row) for row in df]
    if isinstance(df, tuple):
        return [dict(row) for row in df]
    raise TypeError(f"Tipo de dataframe nao suportado: {type(df)}")


def _row_to_microstep(row: dict[str, Any], original_step: MicroStep) -> MicroStep:
    inicio_s = _coerce_float(row.get("inicio_s"), "inicio_s")
    fim_s = _coerce_float(row.get("fim_s"), "fim_s")
    duracao_s = _coerce_float(row.get("duracao_s"), "duracao_s")

    inicio_changed = not isclose(inicio_s, original_step.inicio_s, abs_tol=TIME_TOLERANCE_S)
    fim_changed = not isclose(fim_s, original_step.fim_s, abs_tol=TIME_TOLERANCE_S)
    duration_changed = not isclose(duracao_s, original_step.duracao_s, abs_tol=TIME_TOLERANCE_S)

    if duration_changed and not fim_changed:
        fim_s = inicio_s + duracao_s
    elif (inicio_changed or fim_changed) and not duration_changed:
        duracao_s = fim_s - inicio_s

    update = {
        "inicio_s": round(inicio_s, 3),
        "fim_s": round(fim_s, 3),
        "duracao_s": round(duracao_s, 3),
        "inicio_formatado": seconds_to_mmss(inicio_s),
        "fim_formatado": seconds_to_mmss(fim_s),
        "duracao_formatada": seconds_to_mmss(duracao_s),
        "etapa_detalhada": _coerce_text(row.get("etapa_detalhada"), "etapa_detalhada"),
        "classificacao": _coerce_text(row.get("classificacao"), "classificacao").upper(),
        "justificativa_tecnica": _coerce_text(row.get("justificativa_tecnica"), "justificativa_tecnica"),
        "ferramenta_observacao": _coerce_optional_text(row.get("ferramenta_observacao")),
    }
    data = original_step.model_dump()
    data.update(update)
    return MicroStep.model_validate(data)


def _sync_improvements_with_steps(analysis: OperationalAnalysis):
    step_by_number = {step.numero: step for step in analysis.microetapas}
    updated = []
    for suggestion in analysis.melhorias:
        step = step_by_number.get(suggestion.microetapa_numero)
        if step is None:
            updated.append(suggestion)
            continue
        updated.append(
            suggestion.model_copy(
                update={
                    "inicio_formatado": step.inicio_formatado,
                    "fim_formatado": step.fim_formatado,
                    "duracao_s": step.duracao_s,
                }
            )
        )
    return updated


def _log_human_changes(original: MicroStep, reviewed: MicroStep, alerts: list[str]) -> None:
    fields = {
        "etapa_detalhada": (original.etapa_detalhada, reviewed.etapa_detalhada),
        "inicio_s": (original.inicio_s, reviewed.inicio_s),
        "fim_s": (original.fim_s, reviewed.fim_s),
        "duracao_s": (original.duracao_s, reviewed.duracao_s),
        "classificacao": (original.classificacao, reviewed.classificacao),
        "justificativa_tecnica": (original.justificativa_tecnica, reviewed.justificativa_tecnica),
        "ferramenta_observacao": (original.ferramenta_observacao or "", reviewed.ferramenta_observacao or ""),
    }

    for field_name, (before, after) in fields.items():
        if _values_equal(before, after):
            continue
        logger.info(
            "Revisao humana alterou microetapa %s campo %s: %r -> %r",
            original.numero,
            field_name,
            before,
            after,
        )
        if field_name == "duracao_s":
            _append_alert(
                alerts,
                (
                    f"Revisao humana alterou duracao da microetapa {original.numero}: "
                    f"{float(before):.2f}s -> {float(after):.2f}s."
                ),
            )
        elif field_name == "classificacao":
            _append_alert(
                alerts,
                (
                    f"Revisao humana alterou classificacao da microetapa {original.numero}: "
                    f"{before} -> {after}."
                ),
            )


def _values_equal(before: Any, after: Any) -> bool:
    if isinstance(before, (int, float)) and isinstance(after, (int, float)):
        return isclose(float(before), float(after), abs_tol=TIME_TOLERANCE_S)
    return before == after


def _append_alert(alerts: list[str], message: str) -> None:
    if message not in alerts:
        alerts.append(message)


def _coerce_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo {field_name} deve ser inteiro") from exc


def _coerce_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Campo {field_name} deve ser numerico") from exc


def _coerce_text(value: Any, field_name: str) -> str:
    if value is None:
        raise ValueError(f"Campo {field_name} nao pode ser vazio")
    text = str(value).strip()
    if not text:
        raise ValueError(f"Campo {field_name} nao pode ser vazio")
    return text


def _coerce_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
