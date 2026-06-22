"""Consolidate repetitive consecutive microsteps without hiding real process changes."""

from __future__ import annotations

import re

from app.analysis.activity_text import get_microstep_activity_text
from app.schemas.analysis import MicroStep, OperationalAnalysis
from app.analysis.time_auditor import recalculate_microstep_times


MERGE_INTENT_VERBS = {"pegar", "movimentar", "levar", "transportar", "deslocar", "rolar"}
STOP_INTENT_VERBS = {"alinhar", "encaixar", "instalar", "fixar", "apertar", "conferir", "verificar", "retirar"}


def detect_redundant_microsteps(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    for previous, current in zip(analysis.microetapas, analysis.microetapas[1:]):
        if should_merge_microsteps(previous, current):
            alerts.append(f"Microetapas {previous.numero} e {current.numero} parecem repetir a mesma intenção operacional.")
    return alerts


def consolidate_redundant_microsteps(analysis: OperationalAnalysis) -> OperationalAnalysis:
    if not analysis.microetapas:
        return analysis
    merged: list[MicroStep] = []
    index = 0
    steps = list(analysis.microetapas)
    while index < len(steps):
        current = steps[index]
        group = [current]
        index += 1
        while index < len(steps) and should_merge_microsteps(group[-1], steps[index]):
            group.append(steps[index])
            index += 1
        merged.append(_merge_group(group) if len(group) > 1 else current)

    renumbered = [
        MicroStep.model_validate(step.model_dump() | {"numero": number})
        for number, step in enumerate(merged, start=1)
    ]
    updated = OperationalAnalysis.model_validate(
        analysis.model_dump() | {"microetapas": [step.model_dump() for step in renumbered]}
    )
    return recalculate_microstep_times(updated)


def should_merge_microsteps(step_a: MicroStep, step_b: MicroStep) -> bool:
    if step_a.classificacao != step_b.classificacao:
        return False
    if any(_field_changed(step_a, step_b, field) for field in ("ferramenta_observacao", "peca_componente", "lado", "eixo", "dispositivo")):
        return False
    text_a = get_microstep_activity_text(step_a)
    text_b = get_microstep_activity_text(step_b)
    if _normalize(text_a) == _normalize(text_b) and not _mentions_different_cycle(text_a, text_b):
        return step_b.inicio_s - step_a.fim_s <= 2.0
    verb_a, object_a = _verb_and_object(text_a)
    verb_b, object_b = _verb_and_object(text_b)
    if verb_a in STOP_INTENT_VERBS or verb_b in STOP_INTENT_VERBS:
        return False
    if verb_a not in MERGE_INTENT_VERBS or verb_b not in MERGE_INTENT_VERBS:
        return False
    if object_a and object_b and object_a != object_b:
        return False
    if _mentions_different_cycle(text_a, text_b):
        return False
    return step_b.inicio_s - step_a.fim_s <= 2.0


def _merge_group(group: list[MicroStep]) -> MicroStep:
    first, last = group[0], group[-1]
    object_name = _first_object(group) or "componente"
    destination = last.local_fim or _destination_from_text(get_microstep_activity_text(last)) or "ponto indicado"
    activity = f"Deslocar {_with_article(object_name)} até {destination}."
    evidence = " | ".join(filter(None, [step.evidencia_visual or step.evidencia_observavel for step in group]))
    memories = sorted({item for step in group for item in step.memoria_utilizada})
    data = first.model_dump()
    data.update(
        {
            "fim_s": last.fim_s,
            "duracao_s": round(last.fim_s - first.inicio_s, 3),
            "fim_formatado": last.fim_formatado,
            "duracao_formatada": last.duracao_formatada,
            "instrucao_operacional": activity,
            "instrucao_padrao": activity,
            "etapa_detalhada": activity,
            "descricao_tecnica_detalhada": activity,
            "evidencia_visual": evidence[:800] or first.evidencia_visual,
            "evidencia_observavel": evidence[:800] or first.evidencia_observavel,
            "memoria_utilizada": memories,
            "confianca": min(step.confianca for step in group),
        }
    )
    return MicroStep.model_validate(data)


def _verb_and_object(text: str) -> tuple[str, str | None]:
    normalized = text.casefold()
    match = re.match(r"\s*(\w+)\s+(?:o|a|os|as)?\s*([\wÀ-ÿ-]+)?", normalized)
    if not match:
        return "", None
    return match.group(1), match.group(2)


def _first_object(group: list[MicroStep]) -> str | None:
    for step in group:
        if step.peca_componente:
            return step.peca_componente
        _, obj = _verb_and_object(get_microstep_activity_text(step))
        if obj and obj not in {"ate", "até"}:
            return obj
    return None


def _destination_from_text(text: str) -> str | None:
    match = re.search(r"\bat[eé]\s+(.+?)(?:\.|$)", text, flags=re.I)
    return match.group(1).strip() if match else None


def _field_changed(step_a: MicroStep, step_b: MicroStep, field: str) -> bool:
    a = (getattr(step_a, field) or "").strip().casefold()
    b = (getattr(step_b, field) or "").strip().casefold()
    return bool(a and b and a != b)


def _mentions_different_cycle(text_a: str, text_b: str) -> bool:
    tokens = ("primeiro", "segundo", "terceiro", "quarto", "ld", "le")
    found_a = {token for token in tokens if re.search(rf"\b{re.escape(token)}\b", text_a, flags=re.I)}
    found_b = {token for token in tokens if re.search(rf"\b{re.escape(token)}\b", text_b, flags=re.I)}
    return found_a != found_b and bool(found_a or found_b)


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())


def _with_article(object_name: str) -> str:
    clean = object_name.strip()
    if clean.casefold().startswith(("o ", "a ", "os ", "as ")):
        return clean
    return f"o {clean}"
