"""Prepare OperationalAnalysis for UI/JSON/Excel export."""

from __future__ import annotations

from app.analysis.microstep_consolidator import consolidate_redundant_microsteps
from app.analysis.operational_investigator import apply_operational_investigation
from app.analysis.operational_language_repair import repair_microstep_activity_and_justification
from app.analysis.operational_script_builder import build_operational_script, script_to_microsteps
from app.analysis.quality_alerts import build_quality_alert_rows
from app.analysis.activity_text import get_microstep_activity_text
from app.analysis.schema_compat import (
    build_validation_warnings_for_analysis,
    normalize_analysis_payload_for_current_schema,
    normalize_rows_before_excel_export,
)
from app.schemas.analysis import OperationalAnalysis


def prepare_analysis_for_export(analysis: OperationalAnalysis, context=None) -> OperationalAnalysis:
    """Normalize, repair, consolidate and audit an analysis before any export."""

    normalized = OperationalAnalysis.model_validate(
        normalize_analysis_payload_for_current_schema(analysis)
    )
    normalized_rows, row_warnings, warnings_count, affected_rows = normalize_rows_before_excel_export(
        [step.model_dump() for step in normalized.microetapas]
    )
    if warnings_count and row_warnings:
        message = "Existem avisos de baixa confiança; consulte a aba Avisos_Validacao."
        if message not in normalized.alertas_validacao:
            normalized.alertas_validacao.append(message)
    normalized = OperationalAnalysis.model_validate(
        normalized.model_dump() | {"microetapas": normalized_rows}
    )
    pre_repair_alerts = _quality_gate_alerts(normalized, context)
    repaired_steps = [
        repair_microstep_activity_and_justification(step, context)
        for step in normalized.microetapas
    ]
    prepared = OperationalAnalysis.model_validate(
        normalized.model_dump() | {"microetapas": [step.model_dump() for step in repaired_steps]}
    )
    if context is not None:
        prepared = apply_operational_investigation(prepared, context)
    script = build_operational_script(prepared, context, prepared.metadata)
    prepared = script_to_microsteps(script, prepared, context)
    prepared = consolidate_redundant_microsteps(prepared)
    prepared = _recalculate_times(prepared)
    prepared = _disambiguate_repeated_generic_activities(prepared)

    alerts = list(prepared.alertas_validacao)
    for alert in (
        pre_repair_alerts
        + _quality_gate_alerts(prepared, context)
        + _low_confidence_alerts(prepared)
        + _validate_time_columns_for_export(prepared)
    ):
        if alert not in alerts:
            alerts.append(alert)

    prepared = OperationalAnalysis.model_validate(prepared.model_dump() | {"alertas_validacao": alerts})
    return OperationalAnalysis.model_validate(
        prepared.model_dump() | {"alertas_validacao_sps": build_quality_alert_rows(prepared)}
    )


def _disambiguate_repeated_generic_activities(analysis: OperationalAnalysis) -> OperationalAnalysis:
    counts: dict[str, int] = {}
    for step in analysis.microetapas:
        try:
            key = " ".join(get_microstep_activity_text(step).casefold().split())
        except ValueError:
            continue
        counts[key] = counts.get(key, 0) + 1

    seen: dict[str, int] = {}
    updated_steps = []
    for step in analysis.microetapas:
        data = step.model_dump()
        try:
            activity = get_microstep_activity_text(step)
        except ValueError:
            updated_steps.append(data)
            continue
        key = " ".join(activity.casefold().split())
        seen[key] = seen.get(key, 0) + 1
        if counts.get(key, 0) >= 3:
            suffix = _repetition_context_suffix(step, seen[key])
            if suffix and suffix.casefold() not in activity.casefold():
                activity = activity.rstrip(".") + f" {suffix}."
                data.update(
                    {
                        "instrucao_operacional": activity,
                        "instrucao_padrao": activity,
                        "etapa_detalhada": activity,
                        "descricao_tecnica_detalhada": activity,
                        "interpretacao_de_processo": activity,
                    }
                )
        updated_steps.append(data)

    return OperationalAnalysis.model_validate(analysis.model_dump() | {"microetapas": updated_steps})


def _repetition_context_suffix(step, occurrence: int) -> str:
    references = []
    for value in (
        getattr(step, "eixo", None),
        getattr(step, "lado", None),
        getattr(step, "local_inicio", None),
        getattr(step, "local_fim", None),
        getattr(step, "peca_componente", None),
        getattr(step, "dispositivo", None),
    ):
        if value and str(value).strip():
            references.append(str(value).strip())
    if references:
        return "no contexto " + " / ".join(dict.fromkeys(references[:3]))
    return f"no trecho observado {step.inicio_formatado}-{step.fim_formatado}"


def _recalculate_times(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Import time auditor lazily so Streamlit startup is resilient to reload/cache state."""

    from app.analysis import time_auditor

    return time_auditor.recalculate_microstep_times(analysis)


def _quality_gate_alerts(analysis: OperationalAnalysis, context=None) -> list[str]:
    """Run optional quality-gate helpers without making Streamlit import fragile."""

    try:
        from app.analysis import quality_gate
    except Exception as exc:
        return [f"Quality gate operacional nao carregado durante preparo de exportacao: {exc}"]

    validator = getattr(quality_gate, "validate_analysis_quality", None)
    if validator is not None:
        result = validator(analysis, None, context)
        return list(result.alerts)

    alerts: list[str] = []
    helper_calls = (
        ("detect_action_hidden_in_justification", (analysis,)),
        ("detect_unsupported_tool_or_method_claims", (analysis, context)),
        ("validate_operational_tone", (analysis,)),
    )
    for helper_name, args in helper_calls:
        helper = getattr(quality_gate, helper_name, None)
        if helper is None:
            continue
        alerts.extend(helper(*args))
    return alerts


def _low_confidence_alerts(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    for step in analysis.microetapas:
        if step.confianca < 0.7:
            alerts.append(
                f"Microetapa {step.numero}: Confianca abaixo de 0.70; requer validacao no gemba/SPS."
            )
        elif step.confianca < 0.9:
            alerts.append(
                f"Microetapa {step.numero}: Confianca entre 0.70 e 0.90; revisar antes de oficializar."
            )
        if step.baixa_confianca_motivo:
            alerts.append(f"Microetapa {step.numero}: {step.baixa_confianca_motivo}")
    return alerts


def _validate_time_columns_for_export(analysis: OperationalAnalysis) -> list[str]:
    try:
        from app.analysis import time_auditor
    except Exception as exc:
        return [f"Auditoria de tempo nao carregada durante preparo de exportacao: {exc}"]

    helper = getattr(time_auditor, "validate_time_columns_for_export", None)
    if helper is not None:
        return helper(analysis)

    alerts: list[str] = []
    accumulated = 0.0
    for step in analysis.microetapas:
        duration = round(float(step.fim_s) - float(step.inicio_s), 3)
        accumulated = round(accumulated + duration, 3)
        if abs(step.duracao_s - duration) > 0.01:
            alerts.append(f"Microetapa {step.numero}: tempo do elemento nao auditado.")
        if step.tempo_acumulado_s is None or abs(step.tempo_acumulado_s - accumulated) > 0.01:
            alerts.append(f"Microetapa {step.numero}: tempo acumulado nao e soma progressiva.")
    return alerts
