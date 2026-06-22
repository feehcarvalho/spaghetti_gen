"""Build an operational-process script before final export microsteps."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.analysis.activity_text import get_microstep_activity_text
from app.analysis.operational_language_repair import (
    detect_generic_process_phrases,
    repair_activity_text,
    repair_generic_process_phrase,
)
from app.schemas.analysis import MicroStep, OperationalAnalysis


WHEEL_CONTEXT_TERMS = (
    "pneu",
    "roda",
    "porca",
    "prisioneiro",
    "cubo",
    "vr de pneu",
    "talha",
    "green box",
    "caixa verde",
    "8x2",
)
ESSENTIAL_OBJECTIVES = (
    "alinhar",
    "encaixar",
    "colocar",
    "instalar",
    "fixar",
    "apertar",
    "conferir",
    "verificar",
    "retirar",
    "acoplar",
)


class OperationalScriptStep(BaseModel):
    """One instruction in the process script."""

    model_config = ConfigDict(extra="forbid")

    ordem: int
    instrucao: str
    evidencia: str | None = None
    confianca: float = Field(default=0.8, ge=0, le=1)
    requer_validacao_gemba: bool = False
    source_microstep_numbers: list[int] = Field(default_factory=list)


class OperationalScript(BaseModel):
    """Compact route used to keep final microsteps coherent."""

    model_config = ConfigDict(extra="forbid")

    steps: list[OperationalScriptStep] = Field(default_factory=list)
    context_terms: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


def build_operational_script(analysis: OperationalAnalysis, context=None, metadata=None) -> OperationalScript:
    """Create a concise execution script from current microsteps and context."""

    metadata = metadata or analysis.metadata
    context_text = _combined_context(analysis, context, metadata)
    is_wheel_process = _has_wheel_context(context_text, analysis)
    terms = _context_terms(context_text)
    alerts: list[str] = []
    script_steps: list[OperationalScriptStep] = []

    for step in analysis.microetapas:
        activity = get_microstep_activity_text(step)
        activity = repair_activity_text(activity, step, context)
        activity = _apply_process_route_repair(activity, step, context_text, is_wheel_process)
        if detect_generic_process_phrases(activity):
            activity = repair_generic_process_phrase(activity, context, step)
        activity, step_alerts = _remove_unconfirmed_quantity_text(activity, step, context_text)
        alerts.extend(f"Microetapa {step.numero}: {alert}" for alert in step_alerts)
        script_steps.append(
            OperationalScriptStep(
                ordem=len(script_steps) + 1,
                instrucao=activity,
                evidencia=step.evidencia_visual or step.evidencia_observavel,
                confianca=step.confianca,
                requer_validacao_gemba=step.requer_validacao_gemba,
                source_microstep_numbers=[step.numero],
            )
        )

    script_steps = _merge_script_repetitions(script_steps)
    for index, script_step in enumerate(script_steps, start=1):
        script_step.ordem = index

    if is_wheel_process and "green box" in context_text and any("bluebox" in item.instrucao.casefold() for item in script_steps):
        alerts.append("Contexto indica Green Box/caixa verde, mas roteiro citou Bluebox.")

    return OperationalScript(steps=script_steps, context_terms=terms, alerts=alerts)


def script_to_microsteps(
    script: OperationalScript,
    original_microsteps: OperationalAnalysis | list[MicroStep],
    context=None,
) -> OperationalAnalysis:
    """Apply script wording back to the analysis without changing timings."""

    if isinstance(original_microsteps, OperationalAnalysis):
        analysis = original_microsteps
        steps = analysis.microetapas
    else:
        raise TypeError("script_to_microsteps expects an OperationalAnalysis for compatibility with export.")

    script_by_source: dict[int, OperationalScriptStep] = {}
    for item in script.steps:
        for number in item.source_microstep_numbers:
            script_by_source[number] = item

    updated_steps: list[dict[str, Any]] = []
    context_text = _combined_context(analysis, context, analysis.metadata)
    for step in steps:
        data = step.model_dump()
        script_step = script_by_source.get(step.numero)
        activity = script_step.instrucao if script_step else get_microstep_activity_text(step)
        _, original_quantity_alerts = _remove_unconfirmed_quantity_text(get_microstep_activity_text(step), step, context_text)
        activity = _normalize_greenbox_bluebox(activity, context_text, data)
        activity, quantity_alerts = _remove_unconfirmed_quantity_text(activity, step, context_text)
        quantity_alerts.extend(alert for alert in original_quantity_alerts if alert not in quantity_alerts)
        if quantity_alerts:
            data["quantidade_confirmada_por"] = data.get("quantidade_confirmada_por") or "nao_confirmada"
            data["requer_validacao_gemba"] = True
            data["baixa_confianca_motivo"] = _append_reason(
                data.get("baixa_confianca_motivo"),
                "; ".join(quantity_alerts),
            )
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

    alerts = list(dict.fromkeys([*analysis.alertas_validacao, *script.alerts]))
    roteiro = [item.instrucao for item in script.steps]
    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {
            "microetapas": updated_steps,
            "alertas_validacao": alerts,
            "roteiro_operacional": roteiro,
        }
    )


def _apply_process_route_repair(activity: str, step: MicroStep, context_text: str, is_wheel_process: bool) -> str:
    value = _normalize_greenbox_bluebox(activity, context_text, {})
    lowered = value.casefold()
    if not is_wheel_process:
        return value

    if "ponto de abastecimento indicado" in lowered and ("green box" in context_text or "caixa verde" in context_text):
        if "porca" in context_text or "porca" in lowered:
            return "Ir ate a Green Box/caixa verde e pegar as porcas necessarias para o eixo."
    if (
        lowered in {"pegar o pneu.", "movimentar o pneu.", "levar o pneu.", "transportar o pneu."}
        or lowered.startswith("levar o pneu ate ")
        or lowered.startswith("deslocar o pneu ate ")
        or lowered.startswith("transportar o pneu ate ")
    ):
        return "Acoplar o pneu ao VR/talha e deslocar ate o eixo indicado."
    if "posicionar a peca no conjunto" in lowered or "posicionar o componente no conjunto" in lowered:
        component = step.peca_componente or "pneu"
        return f"Encaixar o {component} no eixo indicado, alinhando aos prisioneiros do cubo."
    if "posicionar ferramenta no ponto" in lowered:
        tool = step.ferramenta_observacao or _confirmed_tool(context_text)
        if tool:
            return f"Posicionar {tool} no ponto de trabalho confirmado."
        return "Posicionar a ferramenta confirmada no ponto de trabalho, com validacao no gemba."
    return value


def _merge_script_repetitions(script_steps: list[OperationalScriptStep]) -> list[OperationalScriptStep]:
    if not script_steps:
        return []
    merged: list[OperationalScriptStep] = []
    index = 0
    while index < len(script_steps):
        current = script_steps[index]
        group = [current]
        index += 1
        while index < len(script_steps) and _should_merge_script_steps(group[-1], script_steps[index]):
            group.append(script_steps[index])
            index += 1
        merged.append(_merge_script_group(group) if len(group) > 1 else current)
    return merged


def _should_merge_script_steps(a: OperationalScriptStep, b: OperationalScriptStep) -> bool:
    if _normalize(a.instrucao) == _normalize(b.instrucao):
        return not _mentions_different_reference(a.instrucao, b.instrucao)
    verb_a, object_a = _verb_and_object(a.instrucao)
    verb_b, object_b = _verb_and_object(b.instrucao)
    if verb_a in ESSENTIAL_OBJECTIVES or verb_b in ESSENTIAL_OBJECTIVES:
        return False
    if verb_a not in {"pegar", "movimentar", "levar", "transportar", "deslocar", "rolar"}:
        return False
    if verb_b not in {"pegar", "movimentar", "levar", "transportar", "deslocar", "rolar"}:
        return False
    if object_a and object_b and object_a != object_b:
        return False
    if _mentions_different_reference(a.instrucao, b.instrucao):
        return False
    return True


def _merge_script_group(group: list[OperationalScriptStep]) -> OperationalScriptStep:
    first, last = group[0], group[-1]
    _, object_name = _verb_and_object(first.instrucao)
    object_name = object_name or _object_from_text(last.instrucao) or "componente"
    destination = _destination_from_text(last.instrucao) or "eixo indicado" if object_name == "pneu" else _destination_from_text(last.instrucao) or "ponto indicado"
    if object_name == "pneu":
        instruction = "Acoplar o pneu ao VR/talha e deslocar ate o eixo indicado."
    else:
        instruction = f"Deslocar {_with_article(object_name)} ate {destination}."
    return OperationalScriptStep(
        ordem=first.ordem,
        instrucao=instruction,
        evidencia=" | ".join(filter(None, [item.evidencia for item in group]))[:800] or None,
        confianca=min(item.confianca for item in group),
        requer_validacao_gemba=any(item.requer_validacao_gemba for item in group),
        source_microstep_numbers=[number for item in group for number in item.source_microstep_numbers],
    )


def _normalize_greenbox_bluebox(activity: str, context_text: str, data: dict[str, Any]) -> str:
    if ("green box" in context_text or "caixa verde" in context_text) and "bluebox" in activity.casefold():
        data["baixa_confianca_motivo"] = _append_reason(
            data.get("baixa_confianca_motivo"),
            "Bluebox substituido por Green Box/caixa verde conforme contexto/memoria.",
        )
        data["requer_validacao_gemba"] = True
        return re.sub(r"\bbluebox\b", "Green Box/caixa verde", activity, flags=re.I)
    return activity


def _remove_unconfirmed_quantity_text(activity: str, step: MicroStep, context_text: str) -> tuple[str, list[str]]:
    alerts: list[str] = []
    value = activity
    quantity_sources = " ".join(
        [
            context_text,
            str(step.quantidade or ""),
            str(step.quantidade_confirmada_por or ""),
            str(step.evidencia_visual or ""),
            str(step.evidencia_observavel or ""),
            " ".join(step.memoria_utilizada),
        ]
    ).casefold()
    replacements = (
        (r"\bduas porcas\b", "as porcas necessarias", "Quantidade 'duas porcas' sem confirmacao suficiente."),
        (r"\boito porcas restantes\b", "as porcas restantes conforme padrao da operacao", "Quantidade 'oito porcas restantes' sem confirmacao suficiente."),
        (r"\b8 porcas restantes\b", "as porcas restantes conforme padrao da operacao", "Quantidade '8 porcas restantes' sem confirmacao suficiente."),
        (r"\b10 porcas\b", "as porcas necessarias", "Quantidade '10 porcas' sem confirmacao suficiente."),
    )
    for pattern, replacement, alert in replacements:
        term = re.sub(r"\\b", "", pattern).replace("\\", "").casefold()
        if re.search(pattern, value, flags=re.I) and not _quantity_confirmed(pattern, quantity_sources):
            value = re.sub(pattern, replacement, value, flags=re.I)
            alerts.append(alert)
    return value, alerts


def _quantity_confirmed(pattern: str, source: str) -> bool:
    confirmation_terms = (
        "memoria confirma",
        "memória confirma",
        "usuario informou",
        "usuário informou",
        "video mostra",
        "vídeo mostra",
        "confirmada",
        "confirmado",
    )
    if any(token in source for token in confirmation_terms):
        if re.search(pattern, source, flags=re.I):
            return True
    return False


def _combined_context(analysis: OperationalAnalysis, context, metadata) -> str:
    parts = [
        str(context or ""),
        metadata.processo,
        metadata.departamento,
        metadata.posto,
        metadata.observacoes_gerais or "",
        getattr(metadata, "foco_do_processo", None) or "",
        getattr(metadata, "inicio_esperado_processo", None) or "",
        getattr(metadata, "fim_esperado_processo", None) or "",
    ]
    for step in analysis.microetapas:
        parts.extend(
            [
                step.etapa_detalhada,
                step.instrucao_padrao or "",
                step.evidencia_visual or "",
                step.evidencia_observavel or "",
                step.ferramenta_observacao or "",
                step.peca_componente or "",
                step.dispositivo or "",
                step.eixo or "",
                step.lado or "",
                " ".join(step.memoria_utilizada),
                " ".join(step.nomenclatura_utilizada),
            ]
        )
    return " ".join(part for part in parts if part).casefold()


def _has_wheel_context(context_text: str, analysis: OperationalAnalysis) -> bool:
    if any(term in context_text for term in WHEEL_CONTEXT_TERMS):
        return True
    return any(
        any(term in get_microstep_activity_text(step).casefold() for term in ("pneu", "roda", "porca", "eixo"))
        for step in analysis.microetapas
    )


def _context_terms(context_text: str) -> list[str]:
    known = ("Green Box", "caixa verde", "VR de pneu", "talha", "pneu", "porca", "prisioneiro", "cubo", "LD", "LE", "8x2")
    return [term for term in known if term.casefold() in context_text]


def _confirmed_tool(context_text: str) -> str | None:
    for term in ("parafusadeira pneumatica", "parafusadeira pneumática", "apertadeira", "talha", "VR de pneu"):
        if term.casefold() in context_text:
            return term
    return None


def _verb_and_object(text: str) -> tuple[str, str | None]:
    match = re.match(r"\s*(\w+)\s+(?:o|a|os|as)?\s*([\wÀ-ÿ-]+)?", text.casefold())
    if not match:
        return "", None
    return match.group(1), match.group(2)


def _object_from_text(text: str) -> str | None:
    lowered = text.casefold()
    for item in ("pneu", "roda", "porca", "ferramenta", "componente", "peca"):
        if re.search(rf"\b{re.escape(item)}\b", lowered):
            return item
    return None


def _destination_from_text(text: str) -> str | None:
    match = re.search(r"\bate\s+(.+?)(?:\.|$)", text, flags=re.I)
    return match.group(1).strip() if match else None


def _mentions_different_reference(a: str, b: str) -> bool:
    tokens = ("primeiro", "segundo", "terceiro", "quarto", "interno", "externo", "ld", "le")
    found_a = {token for token in tokens if re.search(rf"\b{re.escape(token)}\b", a, flags=re.I)}
    found_b = {token for token in tokens if re.search(rf"\b{re.escape(token)}\b", b, flags=re.I)}
    return bool(found_a or found_b) and found_a != found_b


def _with_article(value: str) -> str:
    clean = value.strip()
    if clean.casefold().startswith(("o ", "a ", "os ", "as ")):
        return clean
    return f"o {clean}"


def _append_reason(current: str | None, addition: str) -> str:
    if not current:
        return addition
    if addition in current:
        return current
    return f"{current} {addition}"


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
