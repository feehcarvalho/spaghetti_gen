"""Quality gate for SPS video analyses before Excel generation."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import mean
import re

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.activity_text import get_microstep_activity_text, is_specific_activity_text
from app.analysis.language_normalizer import contains_generic_video_language, is_imperative_language
from app.analysis.operational_language_repair import detect_generic_process_phrases, validate_operational_text
from app.analysis.time_auditor import validate_time_consistency
from app.schemas.analysis import OperationalAnalysis
from app.video.video_metadata import VideoMetadata


DEBUG_DIR = Path("data/outputs/debug")
INTERNAL_TERMS = ("PMGS", "Bluebox", "VR", "WPO", "IHM", "ROP", "HOPE", "KD", "WO")


class QualityGateResult(BaseModel):
    """Result of pre-Excel SPS quality validation."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    can_export: bool = True
    blocking_errors: list[str] = Field(default_factory=list)
    critical_errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)


def validate_analysis_quality(analysis: OperationalAnalysis | None, video_metadata, context) -> QualityGateResult:
    """Validate content, language, timing and SPS logic before Excel export."""

    blocking: list[str] = []
    critical: list[str] = []
    warnings: list[str] = []
    if analysis is None:
        blocking.append("Analise inexistente.")
        return QualityGateResult(
            passed=False,
            can_export=False,
            blocking_errors=blocking,
            critical_errors=blocking,
            alerts=blocking,
            metrics={"microetapas": 0},
        )

    steps = analysis.microetapas
    metadata_text = _analysis_metadata_text(analysis)
    context_text = _context_text(context)
    combined_context = f"{metadata_text} {context_text}".casefold()

    if not steps:
        blocking.append("Analise sem microetapas validas.")

    if analysis.metadata.fonte_video and _mentions_mock_demo(analysis):
        critical.append("Provider mock/demonstracao usado em analise com video real.")

    _check_process_leakage(analysis, combined_context, critical, warnings)
    _check_microstep_count_pattern(steps, critical, warnings)
    _check_descriptions(steps, critical, warnings)
    critical.extend(detect_action_hidden_in_justification(analysis))
    warnings.extend(validate_operational_tone(analysis))
    warnings.extend(detect_generic_operational_phrases(analysis))
    warnings.extend(detect_unsupported_tool_or_method_claims(analysis, context))
    _check_timestamps(steps, critical, warnings)
    _check_time_audit(analysis, critical, warnings)
    _check_classification_logic(analysis, critical, warnings)
    _check_window_alerts(analysis, critical, warnings)
    _check_coverage(analysis, video_metadata, critical, warnings)

    alerts = _unique_messages([*blocking, *critical, *warnings])
    result = QualityGateResult(
        passed=not critical and not blocking,
        can_export=not blocking,
        blocking_errors=blocking,
        critical_errors=_unique_messages([*blocking, *critical]),
        warnings=_unique_messages(warnings),
        alerts=alerts,
        metrics={
            "microetapas": len(steps),
            "av_s": analysis.resumo_tempos.av_s,
            "nav_s": analysis.resumo_tempos.nav_s,
            "d_s": analysis.resumo_tempos.d_s,
            "total_s": analysis.resumo_tempos.total_s,
        },
    )
    if not result.passed:
        _save_quality_gate_debug(analysis, result)
    return result


def assert_quality_gate_passed(
    analysis: OperationalAnalysis | None,
    video_metadata: VideoMetadata | None = None,
    context=None,
    *,
    block_on_quality: bool = False,
) -> None:
    """Raise only for fatal technical export blockers.

    `block_on_quality` is kept for backwards-compatible call sites, but SPS
    quality findings are now warning-only and must not block Excel generation.
    """

    metadata = video_metadata or (_metadata_from_analysis(analysis) if analysis is not None else None)
    result = validate_analysis_quality(analysis, metadata, context)
    if not result.can_export:
        raise ValueError(
            "Excel bloqueado por erro tecnico fatal: "
            + " | ".join(result.blocking_errors)
        )


def _check_process_leakage(
    analysis: OperationalAnalysis,
    combined_context: str,
    critical: list[str],
    warnings: list[str],
) -> None:
    combined_steps = " ".join(
        [
            step.instrucao_padrao or step.etapa_detalhada
            for step in analysis.microetapas
        ]
        + [step.justificativa_tecnica for step in analysis.microetapas]
    )
    combined_evidence = " ".join(
        [
            step.evidencia_observavel or step.evidencia_visual or ""
            for step in analysis.microetapas
        ]
        + [str(step.memoria_utilizada) for step in analysis.microetapas]
    ).casefold()
    lowered_steps = combined_steps.casefold()
    if "pmgs" in lowered_steps and "pmgs" not in combined_context:
        critical.append("Vazamento critico de PMGS em analise sem contexto/metadados PMGS.")

    for term in INTERNAL_TERMS:
        term_lower = term.casefold()
        if term_lower not in lowered_steps:
            continue
        if term_lower in combined_context or term_lower in combined_evidence:
            continue
        warnings.append(f"Nomenclatura interna '{term}' usada sem evidencia/contexto suficiente.")


def _check_microstep_count_pattern(steps, critical: list[str], warnings: list[str]) -> None:
    if not steps:
        return
    descriptions = [_normalize(step.instrucao_padrao or step.etapa_detalhada) for step in steps]
    counts = Counter(descriptions)
    repeated_ratio = counts.most_common(1)[0][1] / len(steps)
    durations = [round(step.duracao_s, 1) for step in steps]
    uniform_duration_ratio = Counter(durations).most_common(1)[0][1] / len(steps)
    if len(steps) in {8, 10} and (repeated_ratio >= 0.35 or uniform_duration_ratio >= 0.80):
        critical.append("Quantidade de microetapas aparenta padrao fixo/artificial.")
    elif len(steps) in {8, 10}:
        warnings.append("Quantidade de microetapas e 8/10; confirmar que nao e segmentacao padrao.")


def _check_descriptions(steps, critical: list[str], warnings: list[str]) -> None:
    generic_count = 0
    non_imperative_count = 0
    for step in steps:
        try:
            text = get_microstep_activity_text(step)
        except ValueError:
            text = step.instrucao_padrao or step.etapa_detalhada
            critical.append(f"Microetapa {step.numero} sem activity operacional especifica.")
        if contains_generic_video_language(text) or _is_too_generic(text):
            generic_count += 1
            warnings.append(f"Microetapa {step.numero} com linguagem generica/narrativa.")
        if not is_imperative_language(text):
            non_imperative_count += 1
            warnings.append(f"Microetapa {step.numero} fora do modo imperativo/instrucional.")
        if not step.justificativa_tecnica.strip():
            critical.append(f"Microetapa {step.numero} sem justificativa tecnica.")
    if steps and generic_count >= max(2, len(steps) // 3):
        critical.append("Analise generica demais para liberar Excel.")
    if steps and non_imperative_count > len(steps) * 0.50:
        critical.append("Maioria das microetapas nao esta em modo imperativo/instrucional.")


def _check_timestamps(steps, critical: list[str], warnings: list[str]) -> None:
    previous_start = -1.0
    for step in steps:
        if step.fim_s < step.inicio_s:
            critical.append(f"Microetapa {step.numero} com fim anterior ao inicio.")
        if abs(step.duracao_s - (step.fim_s - step.inicio_s)) > 0.2:
            critical.append(f"Microetapa {step.numero} com duracao incoerente.")
        if step.inicio_s < previous_start:
            critical.append("Microetapas fora de ordem cronologica.")
        previous_start = step.inicio_s
        if step.duracao_s == 0:
            warnings.append(f"Microetapa {step.numero} com duracao zero.")


def _check_time_audit(
    analysis: OperationalAnalysis,
    critical: list[str],
    warnings: list[str],
) -> None:
    for alert in validate_time_consistency(analysis):
        lowered = alert.casefold()
        if "fim_s nao pode ser menor" in lowered or "negativos" in lowered:
            critical.append(alert)
        elif "difer" in lowered or "incoerente" in lowered:
            warnings.append(alert)


def _check_classification_logic(
    analysis: OperationalAnalysis,
    critical: list[str],
    warnings: list[str],
) -> None:
    improved_steps = {
        item.microetapa_numero
        for item in analysis.melhorias
        if item.microetapa_numero is not None
    }
    for step in analysis.microetapas:
        text = f"{step.instrucao_padrao or step.etapa_detalhada} {step.justificativa_tecnica}".casefold()
        if step.classificacao == "D" and step.numero not in improved_steps:
            critical.append(f"Microetapa D {step.numero} sem melhoria/alerta vinculado.")
        if step.classificacao == "AV" and not any(
            term in text for term in ("transform", "fix", "mont", "conect", "apert", "produto", "conjunto")
        ):
            warnings.append(f"Microetapa AV {step.numero} sem transformacao clara na justificativa.")
        if step.classificacao in {"NAV", "D"} and not step.justificativa_tecnica.strip():
            critical.append(f"Microetapa {step.numero} sem logica SPS para classificacao {step.classificacao}.")


def _check_window_alerts(
    analysis: OperationalAnalysis,
    critical: list[str],
    warnings: list[str],
) -> None:
    alert_text = " ".join(analysis.alertas_validacao).casefold()
    if "janela" in alert_text and ("nao analisada" in alert_text or "falha" in alert_text):
        warnings.append("Ha janelas nao analisadas ou com falha parcial; validar no gemba/SPS.")
    if "timeout" in alert_text:
        warnings.append("Ha timeout parcial registrado; verificar checkpoints/debug antes do Excel.")


def _check_coverage(
    analysis: OperationalAnalysis,
    video_metadata,
    critical: list[str],
    warnings: list[str],
) -> None:
    duration_s = float(getattr(video_metadata, "duration_s", 0.0) or 0.0)
    if duration_s <= 0 or not analysis.microetapas:
        return
    first_start = min(step.inicio_s for step in analysis.microetapas)
    last_end = max(step.fim_s for step in analysis.microetapas)
    if first_start > 3.0:
        warnings.append(f"Cobertura inicia em {first_start:.2f}s; validar trecho inicial.")
    if duration_s - last_end > 3.0:
        warnings.append(f"Cobertura termina {duration_s - last_end:.2f}s antes do final do video.")
    total_steps = sum(step.duracao_s for step in analysis.microetapas)
    if total_steps < duration_s * 0.60:
        warnings.append("Baixa cobertura temporal consolidada em relacao ao video.")


def _metadata_from_analysis(analysis: OperationalAnalysis) -> VideoMetadata:
    duration_s = analysis.metadata.ciclo_observado_s or analysis.resumo_tempos.total_s
    return VideoMetadata(
        video_path=analysis.metadata.fonte_video or "",
        duration_s=duration_s,
        fps=0.0,
        width=0,
        height=0,
        frame_count=0,
        file_size_mb=0.0,
    )


def detect_action_hidden_in_justification(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    for step in analysis.microetapas:
        activity = getattr(step, "instrucao_operacional", None) or step.instrucao_padrao or step.etapa_detalhada
        justification = step.justificativa_tecnica or ""
        if is_specific_activity_text(activity):
            continue
        lowered = justification.casefold()
        has_action = any(verb in lowered for verb in ("fixar", "instalar", "encaixar", "apertar", "posicionar"))
        has_specific = any(term in lowered for term in ("porca", "eixo", "pneu", "parafusadeira", "ferramenta"))
        if has_action and has_specific:
            alerts.append(
                f"Microetapa {step.numero}: A ação operacional parece estar na justificativa, não na microetapa."
            )
    return alerts


def detect_unsupported_tool_or_method_claims(analysis: OperationalAnalysis, context) -> list[str]:
    alerts: list[str] = []
    context_text = _context_text(context).casefold()
    metadata_text = _analysis_metadata_text(analysis).casefold()
    known_text = f"{context_text} {metadata_text}"
    watched = (
        "parafusadeira pneumática",
        "parafusadeira pneumatica",
        "apertadeira",
        "vr",
        "bluebox",
        "green box",
        "caixa verde",
        "wpo",
        "segundo eixo",
        "terceiro eixo",
        "ld",
        "le",
        "8x2",
        "10 porcas",
        "duas porcas",
        "oito porcas",
        "8 porcas",
        "valvula",
        "válvula",
        "bico de ar",
    )
    for step in analysis.microetapas:
        activity = f"{getattr(step, 'instrucao_operacional', '') or ''} {step.instrucao_padrao or ''} {step.etapa_detalhada}".casefold()
        evidence = " ".join(
            [
                step.evidencia_visual or "",
                step.evidencia_observavel or "",
                step.ferramenta_observacao or "",
                " ".join(step.memoria_utilizada),
                " ".join(getattr(step, "nomenclatura_utilizada", [])),
            ]
        ).casefold()
        allowed_text = f"{known_text} {evidence}"
        if "manual" in allowed_text and "parafusadeira pneum" in activity:
            alerts.append(f"Microetapa {step.numero}: ferramenta pneumática conflitante com método manual observado/contextual.")
        for term in watched:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, activity, flags=re.IGNORECASE) and not re.search(pattern, allowed_text, flags=re.IGNORECASE):
                alerts.append(f"Microetapa {step.numero}: termo '{term}' usado sem evidencia/memoria/contexto suficiente.")
    return alerts


def validate_operational_tone(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    for step in analysis.microetapas:
        try:
            text = get_microstep_activity_text(step)
        except ValueError as exc:
            alerts.append(f"Microetapa {step.numero}: {exc}")
            continue
        for alert in validate_operational_text(text):
            alerts.append(f"Microetapa {step.numero}: {alert}")
    return alerts


def validate_feedback_was_applied(analysis: OperationalAnalysis, feedback_text: str) -> list[str]:
    """Check whether a rerun incorporated the user's correction."""

    feedback = (feedback_text or "").casefold()
    if not feedback.strip():
        return []
    activity_text = " ".join(
        [
            get_microstep_activity_text(step)
            for step in analysis.microetapas
            if get_microstep_activity_text(step)
        ]
    ).casefold()
    alerts: list[str] = []

    if ("green box" in feedback or "caixa verde" in feedback) and "bluebox" in activity_text:
        alerts.append("A análise não incorporou a correção do usuário: Green Box/caixa verde ainda foi trocado por Bluebox.")
    if "manual" in feedback and "parafusadeira pneum" in activity_text:
        alerts.append("A análise não incorporou a correção do usuário: método manual ainda virou pneumática.")
    if any(token in feedback for token in ("nao repetir", "não repetir", "repetir varias", "mesma intencao", "mesma intenção")):
        repeated = Counter(" ".join(get_microstep_activity_text(step).casefold().split()) for step in analysis.microetapas)
        if any(count >= 3 for count in repeated.values()):
            alerts.append("A análise não incorporou a correção do usuário: repetição excessiva de microetapas permanece.")
    if "nao invent" in feedback or "não invent" in feedback:
        unsupported = detect_unsupported_tool_or_method_claims(analysis, feedback_text)
        if unsupported:
            alerts.append("A análise não incorporou a correção do usuário: ainda há ferramenta/método/detalhe sem evidência.")
    if alerts:
        alerts.append("A análise não incorporou a correção do usuário. Reprocessar antes de gerar Excel.")
    return alerts


def detect_generic_operational_phrases(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    for step in analysis.microetapas:
        try:
            text = get_microstep_activity_text(step)
        except ValueError:
            continue
        for alert in detect_generic_process_phrases(text):
            alerts.append(f"Microetapa {step.numero}: {alert}")
    return alerts


def _mentions_mock_demo(analysis: OperationalAnalysis) -> bool:
    text = " ".join(analysis.alertas_validacao + analysis.recomendacoes_gerais).casefold()
    return "mock" in text or "demonstr" in text


def _analysis_metadata_text(analysis: OperationalAnalysis) -> str:
    metadata = analysis.metadata
    return " ".join(
        part
        for part in (
            metadata.departamento,
            metadata.linha or "",
            metadata.bloco or "",
            metadata.posto,
            metadata.processo,
            metadata.observacoes_gerais or "",
        )
        if part
    )


def _context_text(context) -> str:
    if context is None:
        return ""
    if isinstance(context, str):
        return context
    if hasattr(context, "context_text"):
        return str(context.context_text)
    return str(context)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _unique_messages(messages: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for message in messages:
        key = " ".join(str(message).casefold().split())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(message)
    return unique


def _is_too_generic(text: str) -> bool:
    normalized = _normalize(text)
    if len(normalized) < 12:
        return True
    return any(
        phrase in normalized
        for phrase in (
            "atividade operacional",
            "realizar processo",
            "executar tarefa",
            "operacao no processo",
            "trabalhar no produto",
        )
    )


def _save_quality_gate_debug(analysis: OperationalAnalysis, result: QualityGateResult) -> Path:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "result": result.model_dump(mode="json"),
        "metadata": analysis.metadata.model_dump(mode="json"),
        "microstep_count": len(analysis.microetapas),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
