"""Normalize microstep text to Scania process-instruction language."""

from __future__ import annotations

import re

from app.knowledge.knowledge_orchestrator import SPSContext
from app.schemas.analysis import MicroStep


IMPERATIVE_STARTERS = (
    "Ir",
    "Pegar",
    "Levar",
    "Rolar",
    "Encaixar",
    "Comprar",
    "Selecionar",
    "Posicionar",
    "Fixar",
    "Apertar",
    "Conectar",
    "Verificar",
    "Inspecionar",
    "Apontar",
    "Aguardar",
    "Descartar",
    "Separar",
    "Abastecer",
    "Confirmar",
    "Retornar",
    "Remover",
    "Soltar",
    "Travar",
    "Destravar",
    "Procurar",
    "Buscar",
    "Transportar",
    "Deslocar",
    "Aplicar",
    "Liberar",
    "Conferir",
    "Preparar",
    "Estabilizar",
    "Controlar",
    "Iniciar",
    "Aproximar",
    "Assentar",
    "Reposicionar",
    "Conter",
    "Acoplar",
    "Desacoplar",
    "Retirar",
    "Movimentar",
    "Alinhar",
    "Afastar-se",
    "Ajustar",
    "Encostar",
    "Segurar",
    "Apoiar",
    "Acionar",
    "Recompor",
    "Manter",
    "Orientar",
    "Executar",
)
NARRATIVE_PREFIX_RE = re.compile(
    r"^\s*(?:o\s+)?(?:operador|colaborador|funcionario|pessoa|ele|ela)\s+",
    re.IGNORECASE,
)
GENERIC_VIDEO_PATTERNS = (
    re.compile(r"\boperador\s+pega\s+a?\s*peca\b", re.IGNORECASE),
    re.compile(r"\ba\s+pessoa\s+vai\b", re.IGNORECASE),
    re.compile(r"\bele\s+mexe\b", re.IGNORECASE),
    re.compile(r"\bparece\s+que\b", re.IGNORECASE),
    re.compile(r"\brealiza\s+alguma\s+coisa\b", re.IGNORECASE),
    re.compile(r"\bfaz\s+o\s+processo\b", re.IGNORECASE),
    re.compile(r"\bmovimenta\s+peca\b", re.IGNORECASE),
)
VERB_REPLACEMENTS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?:pega|pegar|coleta|retira)\b", re.IGNORECASE), "Pegar"),
    (re.compile(r"^(?:anda|vai|caminha|desloca(?:-se)?)\b", re.IGNORECASE), "Ir"),
    (re.compile(r"^(?:compra|comprar)\b", re.IGNORECASE), "Comprar"),
    (re.compile(r"^(?:seleciona|selecionar|separa|separar)\b", re.IGNORECASE), "Selecionar"),
    (re.compile(r"^(?:coloca|posiciona|posicionar)\b", re.IGNORECASE), "Posicionar"),
    (re.compile(r"^(?:fixa|fixar|aplica\s+fixacao)\b", re.IGNORECASE), "Fixar"),
    (re.compile(r"^(?:aperta|apertar|torqueia|torquear)\b", re.IGNORECASE), "Apertar"),
    (re.compile(r"^(?:conecta|conectar|encaixa|encaixar)\b", re.IGNORECASE), "Conectar"),
    (re.compile(r"^(?:verifica|verificar|confere|conferir)\b", re.IGNORECASE), "Verificar"),
    (re.compile(r"^(?:inspeciona|inspecionar)\b", re.IGNORECASE), "Inspecionar"),
    (re.compile(r"^(?:aponta|apontar|registra|registrar)\b", re.IGNORECASE), "Apontar"),
    (re.compile(r"^(?:espera|esperar|aguarda|aguardar)\b", re.IGNORECASE), "Aguardar"),
    (re.compile(r"^(?:retorna|retornar)\b", re.IGNORECASE), "Retornar"),
    (re.compile(r"^(?:procura|procurar|busca|buscar)\b", re.IGNORECASE), "Procurar"),
    (re.compile(r"^(?:abastece|abastecer)\b", re.IGNORECASE), "Abastecer"),
    (re.compile(r"^(?:confirma|confirmar)\b", re.IGNORECASE), "Confirmar"),
    (re.compile(r"^(?:libera|liberar)\b", re.IGNORECASE), "Liberar"),
    (re.compile(r"^(?:aplica|aplicar)\b", re.IGNORECASE), "Aplicar"),
    (re.compile(r"^(?:retira|retirar)\b", re.IGNORECASE), "Retirar"),
    (re.compile(r"^(?:movimenta|movimentar)\b", re.IGNORECASE), "Movimentar"),
    (re.compile(r"^(?:alinha|alinhar)\b", re.IGNORECASE), "Alinhar"),
    (re.compile(r"^(?:afasta(?:-se)?|afastar(?:-se)?)\b", re.IGNORECASE), "Afastar-se"),
    (re.compile(r"^(?:ajusta|ajustar)\b", re.IGNORECASE), "Ajustar"),
    (re.compile(r"^(?:aciona|acionar)\b", re.IGNORECASE), "Acionar"),
    (re.compile(r"^(?:recompoe|recompor)\b", re.IGNORECASE), "Recompor"),
    (re.compile(r"^(?:orienta|orientar)\b", re.IGNORECASE), "Orientar"),
    (re.compile(r"^(?:mantem|manter)\b", re.IGNORECASE), "Manter"),
)


def normalize_microstep_language(
    microstep: MicroStep,
    context: SPSContext | None = None,
) -> MicroStep:
    """Convert narrative text into process instruction text without inventing terms."""

    source = (
        getattr(microstep, "instrucao_operacional", None)
        or getattr(microstep, "instrucao_padrao", None)
        or getattr(microstep, "descricao_tecnica_detalhada", None)
        or getattr(microstep, "etapa_detalhada", None)
    )
    normalized = _normalize_spacing(source) if _is_good_shopfloor_instruction(source) else _normalize_text(source)
    normalized = _apply_known_nomenclature(normalized, context)
    normalized = _replace_generic_part_with_context_part(normalized, context, microstep)
    normalized = _correct_fastener_terms(normalized, microstep, context)

    data = microstep.model_dump()
    data.update(
        {
            "etapa_detalhada": normalized,
            "descricao_tecnica_detalhada": normalized,
            "instrucao_operacional": normalized,
            "instrucao_padrao": normalized,
            "interpretacao_de_processo": microstep.interpretacao_de_processo or normalized,
        }
    )

    if context is not None:
        memories = [term for term in context.glossary_terms if term.casefold() in normalized.casefold()]
        data["memoria_utilizada"] = sorted(set(microstep.memoria_utilizada + memories))
        data["nomenclatura_utilizada"] = sorted(set(getattr(microstep, "nomenclatura_utilizada", []) + memories))

    if contains_generic_video_language(source) and not microstep.baixa_confianca_motivo:
        data["baixa_confianca_motivo"] = (
            "Descricao narrativa/generica normalizada; requer validacao no gemba/SPS."
        )
        data["requer_validacao_gemba"] = True

    return MicroStep.model_validate(data)


def normalize_analysis_language(analysis, context: SPSContext | None = None):
    """Normalize all microsteps in an OperationalAnalysis-like object."""

    from app.schemas.analysis import OperationalAnalysis

    microsteps = [
        normalize_microstep_language(step, context)
        for step in analysis.microetapas
    ]
    return OperationalAnalysis.model_validate(
        analysis.model_dump() | {"microetapas": [step.model_dump() for step in microsteps]}
    )


def contains_generic_video_language(text: str) -> bool:
    normalized = _strip_accents_for_match(text)
    return any(pattern.search(normalized) for pattern in GENERIC_VIDEO_PATTERNS)


def is_imperative_language(text: str) -> bool:
    stripped = text.strip()
    return any(stripped.startswith(starter) for starter in IMPERATIVE_STARTERS)


def _normalize_spacing(text: str) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    return value.rstrip(".") + "." if value else value


def _is_good_shopfloor_instruction(text: str | None) -> bool:
    if not text:
        return False
    value = _normalize_spacing(text)
    lowered = value.casefold()
    bureaucratic = (
        "realizar a movimentacao",
        "realizar a movimentação",
        "proceder com",
        "efetuar a atividade",
        "interface de montagem",
        "elemento de uniao",
        "elemento de união",
    )
    return is_imperative_language(value) and not any(item in lowered for item in bureaucratic)


def _normalize_text(text: str) -> str:
    value = re.sub(r"\s+", " ", text or "").strip()
    value = NARRATIVE_PREFIX_RE.sub("", value)
    value = re.sub(r"^(?:realiza|executa|faz)\s+", "", value, flags=re.IGNORECASE)
    value = re.sub(
        r"^fixar\s+(recompor|ajustar|acionar|manter|orientar)\b",
        lambda match: match.group(1).capitalize(),
        value,
        flags=re.IGNORECASE,
    )
    value = _strip_redundant_execute_prefix(value)
    value = re.sub(r"\b(?:a\s+)?peca\b", "a peca", value, flags=re.IGNORECASE)
    for pattern, replacement in VERB_REPLACEMENTS:
        if pattern.search(value):
            value = pattern.sub(replacement, value, count=1)
            break
    if not is_imperative_language(value):
        value = _fallback_to_instruction(value)
    value = value[0].upper() + value[1:] if value else value
    return value.rstrip(".") + "."


def _fallback_to_instruction(text: str) -> str:
    lowered = text.casefold()
    if any(word in lowered for word in ("espera", "aguard", "liberacao")):
        return f"Aguardar {text}"
    if any(word in lowered for word in ("verif", "confer", "inspec")):
        return f"Verificar {text}"
    if re.search(r"\b(fixar|fixa|apertar|aperta|montar|monta|aplicar|aplica)\b", lowered):
        return f"Fixar {text}"
    if any(word in lowered for word in ("posicion", "coloc", "encaix")):
        return f"Posicionar {text}"
    if any(word in lowered for word in ("busc", "procur")):
        return f"Procurar {text}"
    return f"Executar {text}"


def _strip_redundant_execute_prefix(text: str) -> str:
    value = re.sub(r"^(?:executar\s+)+", "", text, flags=re.IGNORECASE).strip()
    if value and is_imperative_language(value[0].upper() + value[1:]):
        return value
    return text


def _apply_known_nomenclature(text: str, context: SPSContext | None) -> str:
    if context is None:
        return text
    result = text
    for term in sorted(context.glossary_terms, key=len, reverse=True):
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        result = pattern.sub(term, result)
    return result.replace("bluebox", "Bluebox").replace("BlueBox", "Bluebox")


def _replace_generic_part_with_context_part(text: str, context: SPSContext | None, microstep: MicroStep) -> str:
    if context is None:
        return text
    context_text = f"{' '.join(context.glossary_terms)} {context.context_text}".casefold()
    if "pneu" not in context_text:
        return text
    evidence_text = _microstep_evidence_text(microstep)
    if _has_fastener_evidence(evidence_text) and not _has_tire_handling_evidence(evidence_text):
        return text
    result = text
    replacements = (
        (r"\ba\s+peca\b", "o pneu"),
        (r"\bpeca\b", "pneu"),
        (r"\bo\s+componente\b", "o pneu"),
        (r"\bcomponente\b", "pneu"),
        (r"\bo\s+item\b", "o pneu"),
        (r"\bitem\b", "pneu"),
    )
    for pattern, replacement in replacements:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    return result


def _correct_fastener_terms(text: str, microstep: MicroStep, context: SPSContext | None) -> str:
    if context is None:
        return text
    evidence_text = _microstep_evidence_text(microstep)
    if not _has_fastener_evidence(evidence_text):
        return text
    result = text
    if re.match(r"^\s*(Selecionar|Pegar)\s+(?:o\s+pneu|o\s+componente|a\s+peca|o\s+item)\b", result, flags=re.IGNORECASE):
        verb = re.match(r"^\s*(Selecionar|Pegar)", result, flags=re.IGNORECASE).group(1).capitalize()
        return f"{verb} a porca na caixa verde de elementos de fixação."
    if (
        re.match(r"^\s*(Transportar|Movimentar)\s+o\s+pneu\b", result, flags=re.IGNORECASE)
        and not _has_tire_handling_evidence(evidence_text)
    ):
        verb = re.match(r"^\s*(Transportar|Movimentar)", result, flags=re.IGNORECASE).group(1).capitalize()
        return f"{verb} a porca até o ponto de montagem do pneu."
    if (
        re.match(r"^\s*Posicionar\s+o\s+pneu\b", result, flags=re.IGNORECASE)
        and not _has_tire_handling_evidence(evidence_text)
    ):
        return "Posicionar a porca no prisioneiro do conjunto."
    return result


def _microstep_evidence_text(microstep: MicroStep) -> str:
    parts = [
        microstep.etapa_detalhada,
        microstep.descricao_tecnica_detalhada or "",
        microstep.instrucao_padrao or "",
        microstep.evidencia_observavel or "",
        microstep.evidencia_visual or "",
        microstep.interpretacao_de_processo or "",
        microstep.ferramenta_observacao or "",
        microstep.local_inicio or "",
        microstep.local_fim or "",
    ]
    return " ".join(parts).casefold()


def _has_fastener_evidence(evidence_text: str) -> bool:
    return any(
        term in evidence_text
        for term in ("porca", "porcas", "caixa verde", "elemento de fix", "prisioneiro", "prisioneiros")
    )


def _has_tire_handling_evidence(evidence_text: str) -> bool:
    return any(
        term in evidence_text
        for term in (
            "pneu suspenso",
            "vr de pneu",
            "ponto de abastecimento de pneus",
            "conjunto de pneus",
            "pneus inclinados",
        )
    )


def _strip_accents_for_match(text: str) -> str:
    replacements = str.maketrans(
        {
            "ç": "c",
            "Ç": "c",
            "ã": "a",
            "Ã": "a",
            "á": "a",
            "Á": "a",
            "à": "a",
            "À": "a",
            "â": "a",
            "Â": "a",
            "é": "e",
            "É": "e",
            "ê": "e",
            "Ê": "e",
            "í": "i",
            "Í": "i",
            "ó": "o",
            "Ó": "o",
            "ô": "o",
            "Ô": "o",
            "õ": "o",
            "Õ": "o",
            "ú": "u",
            "Ú": "u",
        }
    )
    return text.translate(replacements).casefold()
