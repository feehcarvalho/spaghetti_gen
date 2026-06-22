"""Repair activity/justification split while preserving shopfloor language."""

from __future__ import annotations

import re

from app.analysis.activity_text import is_specific_activity_text
from app.analysis.language_normalizer import is_imperative_language
from app.schemas.analysis import MicroStep


BUREAUCRATIC_REWRITES = (
    (
        re.compile(r"^realizar a movimenta[cç][aã]o do componente at[eé] o ponto de aplica[cç][aã]o\.?$", re.I),
        "Rolar {componente} até {local}.",
    ),
)
GENERIC_PROCESS_PHRASES = (
    "ponto necessario para continuidade da operacao",
    "ponto de abastecimento indicado",
    "componente conforme necessidade",
    "recurso de apoio",
    "ferramenta indicada",
    "peca no conjunto",
    "atividade conforme operacao",
    "manter area segura",
    "conforme necessidade da operacao",
    "ponto de trabalho indicado",
)
NOUN_TO_VERB_PREFIXES = (
    (re.compile(r"^estabiliza[cç][aã]o\b", re.I), "Estabilizar"),
    (re.compile(r"^prepara[cç][aã]o\b", re.I), "Preparar"),
    (re.compile(r"^controle\b", re.I), "Controlar"),
    (re.compile(r"^posicionamento\b", re.I), "Posicionar"),
    (re.compile(r"^in[ií]cio\b", re.I), "Iniciar"),
    (re.compile(r"^movimenta[cç][aã]o\b", re.I), "Movimentar"),
    (re.compile(r"^ajuste\b", re.I), "Ajustar"),
    (re.compile(r"^aproxima[cç][aã]o\b", re.I), "Aproximar"),
    (re.compile(r"^alinhamento\b", re.I), "Alinhar"),
    (re.compile(r"^transporte\b", re.I), "Transportar"),
    (re.compile(r"^assentamento\b", re.I), "Assentar"),
    (re.compile(r"^reposicionamento\b", re.I), "Reposicionar"),
    (re.compile(r"^conten[cç][aã]o\b", re.I), "Conter"),
    (re.compile(r"^poss[ií]vel posicionamento\b", re.I), "Posicionar"),
)


def repair_microstep_activity_and_justification(microstep: MicroStep, context=None) -> MicroStep:
    data = microstep.model_dump()
    activity = (
        getattr(microstep, "instrucao_operacional", None)
        or getattr(microstep, "instrucao_padrao", None)
        or getattr(microstep, "descricao_tecnica_detalhada", None)
        or getattr(microstep, "etapa_detalhada", None)
    )
    interpretation = getattr(microstep, "interpretacao_de_processo", None)
    if interpretation and not is_specific_activity_text(activity):
        activity = interpretation
    repaired = repair_activity_text(activity, microstep, context)

    if _activity_hidden_in_justification(repaired, microstep.justificativa_tecnica):
        candidate = _extract_activity_from_justification(microstep.justificativa_tecnica)
        if candidate:
            repaired = candidate
            data["justificativa_tecnica"] = _clean_sps_justification(microstep.classificacao)

    repaired = _remove_unsupported_manual_conflict(repaired, context, data)
    data.update(
        {
            "instrucao_operacional": repaired,
            "instrucao_padrao": repaired,
            "etapa_detalhada": repaired,
            "descricao_tecnica_detalhada": repaired,
            "interpretacao_de_processo": repaired,
        }
    )
    return MicroStep.model_validate(data)


def repair_activity_text(text: str, microstep: MicroStep | None = None, context=None) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    if detect_generic_process_phrases(value):
        value = repair_generic_process_phrase(value, context, microstep)
    for pattern, template in BUREAUCRATIC_REWRITES:
        if pattern.search(value):
            component = _context_value(context, "componente") or getattr(microstep, "peca_componente", None) or "o componente"
            local = _location_with_article(_context_value(context, "local") or getattr(microstep, "local_fim", None) or "o ponto indicado")
            return template.format(componente=_with_article(component), local=local).rstrip(".") + "."
    if value.casefold().startswith("bota "):
        value = re.sub(r"^bota\s+", "Colocar ", value, flags=re.I)
        value = re.sub(r"\s+l[aá]\s+no\s+eixo", " no eixo indicado", value, flags=re.I)
        value = re.sub(r"\bl[aá]\b", "no eixo indicado", value, flags=re.I)
    value = _convert_noun_phrase_to_instruction(value)
    return value[0].upper() + value[1:] if value else value


def _activity_hidden_in_justification(activity: str, justification: str) -> bool:
    return (not is_specific_activity_text(activity)) and _contains_operational_claim(justification)


def detect_generic_process_phrases(text: str) -> list[str]:
    lowered = _strip_accents(text.casefold())
    alerts: list[str] = []
    for phrase in GENERIC_PROCESS_PHRASES:
        if _strip_accents(phrase.casefold()) in lowered:
            alerts.append(f"Frase generica bloqueada: {phrase}.")
    return alerts


def repair_generic_process_phrase(text: str, context=None, microstep: MicroStep | None = None) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    lowered = _strip_accents(value.casefold())
    context_text = _strip_accents(str(context or "").casefold())
    component = _context_value(context, "componente") or getattr(microstep, "peca_componente", None) or ""
    local = _context_value(context, "local") or getattr(microstep, "local_fim", None) or ""
    tool = _context_value(context, "ferramenta") or getattr(microstep, "ferramenta_observacao", None) or ""
    device = _context_value(context, "dispositivo") or getattr(microstep, "dispositivo", None) or ""

    if "conforme necessidade da operacao" in lowered and len(value.split()) > 4:
        value = re.sub(r"\s+conforme necessidade da opera[cç][aã]o", "", value, flags=re.I).rstrip(".") + "."
        lowered = _strip_accents(value.casefold())
    if "ponto de abastecimento indicado" in lowered and ("green box" in context_text or "caixa verde" in context_text):
        if "porca" in context_text or "porca" in _strip_accents(str(component).casefold()):
            return "Ir ate a Green Box/caixa verde e pegar as porcas necessarias para o eixo."
    if "ponto necessario para continuidade da operacao" in lowered:
        destination = local or "ponto confirmado do processo"
        return f"Ir ate {destination} para continuar a operacao."
    if "recurso de apoio" in lowered:
        if device:
            return f"Preparar {device} para apoiar a operacao."
        return "Preparar o dispositivo de apoio confirmado para a operacao."
    if "ferramenta indicada" in lowered or "ponto de trabalho indicado" in lowered:
        if tool:
            return f"Posicionar {tool} no ponto de trabalho confirmado."
        return "Posicionar a ferramenta confirmada no ponto de trabalho."
    if "peca no conjunto" in lowered or "componente conforme necessidade" in lowered:
        if component and local:
            return f"Posicionar {_with_article(component)} em {local}."
        if component:
            return f"Posicionar {_with_article(component)} no conjunto confirmado."
        return "Posicionar o componente confirmado no conjunto."
    return value


def _contains_operational_claim(text: str) -> bool:
    lowered = text.casefold()
    return any(verb in lowered for verb in ("fixar", "instalar", "encaixar", "apertar", "posicionar")) and any(
        term in lowered for term in ("porca", "eixo", "pneu", "parafusadeira", "ferramenta", "componente")
    )


def _extract_activity_from_justification(justification: str) -> str | None:
    text = re.sub(r"^(etapa classificada.*?porque\s+)", "", justification.strip(), flags=re.I)
    text = re.sub(r"^(a[cç][aã]o de\s+)", "", text, flags=re.I)
    match = re.search(r"\b(fixar|instalar|encaixar|apertar|posicionar|colocar|retirar)\b.*", text, flags=re.I)
    if not match:
        return None
    candidate = match.group(0).split(";")[0].strip()
    candidate = re.sub(r",?\s*(mas|por[eé]m)\s+.*$", "", candidate, flags=re.I)
    return candidate[0].upper() + candidate[1:].rstrip(".") + "."


def _clean_sps_justification(classification: str) -> str:
    if classification == "AV":
        return "Etapa classificada como AV porque altera diretamente a condição de montagem do produto."
    if classification == "NAV":
        return "Etapa classificada como NAV porque é necessária ao método atual, mas não transforma diretamente o produto."
    return "Etapa classificada como D porque representa desperdício ou perda no fluxo observado."


def _remove_unsupported_manual_conflict(activity: str, context, data: dict) -> str:
    context_text = str(context or "").casefold()
    lowered = activity.casefold()
    if "manual" in context_text and "parafusadeira pneum" in lowered:
        data["baixa_confianca_motivo"] = "Ferramenta pneumática removida por conflito com evidência/contexto de instalação manual."
        data["requer_validacao_gemba"] = True
        return re.sub(r"\s+com\s+(?:a\s+)?parafusadeira pneum[aá]tica", " manualmente", activity, flags=re.I)
    return activity


def _context_value(context, key: str) -> str | None:
    if isinstance(context, dict):
        value = context.get(key)
        return str(value) if value else None
    return None


def _with_article(component: str) -> str:
    clean = component.strip()
    if clean.casefold().startswith(("o ", "a ", "os ", "as ")):
        return clean
    return f"o {clean}"


def _location_with_article(local: str) -> str:
    clean = local.strip()
    if clean.casefold().startswith(("o ", "a ", "os ", "as ", "no ", "na ", "nos ", "nas ")):
        return clean
    if clean.casefold().startswith("eixo"):
        return f"o {clean}"
    return clean


def _convert_noun_phrase_to_instruction(text: str) -> str:
    value = text.strip()
    for pattern, verb in NOUN_TO_VERB_PREFIXES:
        if pattern.search(value):
            remainder = pattern.sub("", value, count=1).strip(" .:-")
            if not remainder:
                return verb
            if remainder.casefold().startswith(("de ", "da ", "do ", "das ", "dos ")):
                return f"{verb} {remainder[3:].strip()}"
            return f"{verb} {remainder}"
    return value


def validate_operational_text(text: str) -> list[str]:
    alerts: list[str] = []
    lowered = text.casefold()
    if not is_imperative_language(text):
        alerts.append("Microetapa não está em modo instrucional.")
    if any(term in lowered for term in ("realizar a moviment", "proceder com", "efetuar a atividade")):
        alerts.append("Linguagem excessivamente burocrática.")
    if any(term in lowered for term in ("bota ", "pega aí", "dá uma ajeitada", "fazer o negócio")):
        alerts.append("Linguagem informal inadequada.")
    alerts.extend(detect_generic_process_phrases(text))
    if not is_specific_activity_text(text):
        alerts.append("Linguagem excessivamente genérica.")
    return alerts


def _strip_accents(text: str) -> str:
    mapping = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return text.translate(mapping)
