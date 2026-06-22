"""Operational specificity layer for SPS microsteps."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.analysis import MicroStep, OperationalAnalysis


LOW_CONFIDENCE_DETAIL_MESSAGE = (
    "Detalhe operacional especifico nao confirmado nas memorias/frames; requer validacao no gemba/SPS."
)


@dataclass(frozen=True)
class OperationalContextDetails:
    variant: str | None = None
    axis: str | None = None
    side: str | None = None
    nomenclature_note: str | None = None
    terms: tuple[str, ...] = ()


def apply_operational_investigation(analysis: OperationalAnalysis, context: Any) -> OperationalAnalysis:
    """Use available memories/context to increase operational specificity without inventing data."""

    details = extract_operational_context_details(context)
    microsteps = [_investigate_step(step, details) for step in analysis.microetapas]
    return OperationalAnalysis.model_validate(
        analysis.model_dump() | {"microetapas": [step.model_dump() for step in microsteps]}
    )


def extract_operational_context_details(context: Any) -> OperationalContextDetails:
    text = _context_text(context)
    terms = tuple(_context_terms(context, text))
    return OperationalContextDetails(
        variant=_extract_detail(text, ("configuracao/variante do veiculo", "configuração/variante do veículo", "variante")),
        axis=_extract_detail(text, ("eixo envolvido", "eixo")),
        side=_extract_side(text),
        nomenclature_note=_extract_detail(text, ("observacoes de nomenclatura", "observações de nomenclatura", "nomenclatura")),
        terms=terms,
    )


def _investigate_step(step: MicroStep, details: OperationalContextDetails) -> MicroStep:
    data = step.model_dump()
    original_text = _step_text(step)
    updated_text = _apply_known_nomenclature(original_text, step, details)
    if _is_vehicle_mount_step(updated_text):
        updated_text = _append_vehicle_details(updated_text, details)
        data = _mark_missing_vehicle_details(data, updated_text, details)

    if updated_text != original_text:
        for key in ("instrucao_padrao", "descricao_tecnica_detalhada", "etapa_detalhada"):
            if data.get(key):
                data[key] = _apply_known_nomenclature(str(data[key]), step, details)
                if _is_vehicle_mount_step(str(data[key])):
                    data[key] = _append_vehicle_details(str(data[key]), details)
        data["interpretacao_de_processo"] = data.get("instrucao_padrao") or updated_text

    memory = list(data.get("memoria_utilizada") or [])
    for item in _memory_refs(details):
        if item not in memory:
            memory.append(item)
    data["memoria_utilizada"] = memory
    return MicroStep.model_validate(data)


def _apply_known_nomenclature(text: str, step: MicroStep, details: OperationalContextDetails) -> str:
    result = text
    evidence = _evidence_text(step)
    terms = {term.casefold(): term for term in details.terms}

    if "vr de pneu" in terms and _mentions_tire_or_vr(result, evidence):
        result = re.sub(r"\b(equipamento|dispositivo)\b", terms["vr de pneu"], result, flags=re.IGNORECASE)

    tool_term = _first_matching_term(terms, ("parafusadeira pneumática", "parafusadeira pneumatica"))
    if tool_term and _mentions_tool_context(result, evidence):
        result = re.sub(r"\bferramenta\b", tool_term, result, flags=re.IGNORECASE)

    return _normalize_sentence_spacing(result)


def _append_vehicle_details(text: str, details: OperationalContextDetails) -> str:
    result = text.strip()
    suffixes: list[str] = []
    lowered = result.casefold()

    if details.variant and details.variant.casefold() not in lowered:
        suffixes.append(f"no conjunto {details.variant}")
    if details.axis and details.axis.casefold() not in lowered:
        suffixes.append(f"do {details.axis}")
    if details.side and details.side.casefold() not in lowered:
        suffixes.append(f"lado {details.side}")

    if not suffixes:
        return result
    result = result.rstrip(".")
    return f"{result} {' , '.join(suffixes)}."


def _mark_missing_vehicle_details(
    data: dict,
    text: str,
    details: OperationalContextDetails,
) -> dict:
    lowered = text.casefold()
    missing = []
    if details.variant is None and not re.search(r"\b[468]x[24]\b", lowered):
        missing.append("variante")
    if details.axis is None and "eixo" not in lowered:
        missing.append("eixo")
    if details.side is None and not re.search(r"\b(ld|le|lado direito|lado esquerdo)\b", lowered):
        missing.append("lado")

    if not missing:
        return data
    reason = f"{LOW_CONFIDENCE_DETAIL_MESSAGE} Detalhe(s): {', '.join(missing)}."
    current_reason = str(data.get("baixa_confianca_motivo") or "").strip()
    if reason not in current_reason:
        data["baixa_confianca_motivo"] = f"{current_reason} {reason}".strip()
    data["requer_validacao_gemba"] = True
    data["confianca"] = min(float(data.get("confianca") or 1.0), 0.69)
    return data


def _extract_detail(text: str, labels: tuple[str, ...]) -> str | None:
    for label in labels:
        pattern = re.compile(rf"{re.escape(label)}\s*:\s*([^\n\r.;]+)", flags=re.IGNORECASE)
        match = pattern.search(text)
        if match:
            value = match.group(1).strip(" -")
            return value or None
    return None


def _extract_side(text: str) -> str | None:
    explicit = _extract_detail(text, ("lado envolvido", "lado"))
    if explicit:
        match = re.search(r"\b(LD|LE|lado direito|lado esquerdo)\b", explicit, flags=re.IGNORECASE)
        if match:
            value = match.group(1)
            if value.casefold() == "lado direito":
                return "LD"
            if value.casefold() == "lado esquerdo":
                return "LE"
            return value.upper()
    match = re.search(r"\b(LD|LE)\b", text, flags=re.IGNORECASE)
    return match.group(1).upper() if match else None


def _context_text(context: Any) -> str:
    if context is None:
        return ""
    if isinstance(context, str):
        return context
    if hasattr(context, "context_text"):
        return str(context.context_text)
    return str(context)


def _context_terms(context: Any, text: str) -> list[str]:
    terms: list[str] = []
    for attr in ("glossary_terms", "known_locations", "known_tools", "known_parts"):
        for item in getattr(context, attr, []) or []:
            if item and str(item) not in terms:
                terms.append(str(item))
    for item in ("VR de pneu", "parafusadeira pneumática", "parafusadeira pneumatica"):
        if item.casefold() in text.casefold() and item not in terms:
            terms.append(item)
    return terms


def _step_text(step: MicroStep) -> str:
    return step.instrucao_padrao or step.descricao_tecnica_detalhada or step.etapa_detalhada


def _evidence_text(step: MicroStep) -> str:
    return " ".join(
        part
        for part in (
            step.evidencia_observavel or "",
            step.evidencia_visual or "",
            step.ferramenta_observacao or "",
            " ".join(step.memoria_utilizada),
        )
        if part
    )


def _is_vehicle_mount_step(text: str) -> bool:
    lowered = text.casefold()
    return any(term in lowered for term in ("pneu", "roda", "cubo", "prisioneiro", "caminhao", "caminhão", "eixo"))


def _mentions_tire_or_vr(text: str, evidence: str) -> bool:
    lowered = f"{text} {evidence}".casefold()
    return any(term in lowered for term in ("pneu", "vr", "roda", "equipamento", "dispositivo"))


def _mentions_tool_context(text: str, evidence: str) -> bool:
    lowered = f"{text} {evidence}".casefold()
    return any(term in lowered for term in ("parafus", "apert", "ferramenta"))


def _first_matching_term(terms: dict[str, str], options: tuple[str, ...]) -> str | None:
    for option in options:
        if option.casefold() in terms:
            return terms[option.casefold()]
    return None


def _memory_refs(details: OperationalContextDetails) -> list[str]:
    refs = []
    if details.variant:
        refs.append(f"Contexto operacional: variante={details.variant}")
    if details.axis:
        refs.append(f"Contexto operacional: eixo={details.axis}")
    if details.side:
        refs.append(f"Contexto operacional: lado={details.side}")
    if details.nomenclature_note:
        refs.append("Contexto operacional: observacao de nomenclatura")
    return refs


def _normalize_sentence_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", text).replace(" ,", ",").strip()
