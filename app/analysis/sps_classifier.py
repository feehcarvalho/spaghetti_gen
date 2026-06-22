"""Deterministic SPS AV/NAV/D classification support."""

from __future__ import annotations

from app.schemas.analysis import MicroStep, OperationalAnalysis


AV_TERMS = (
    "fixar",
    "apertar",
    "conectar",
    "montar",
    "encaixar",
    "aplicar",
    "posicionar a peca no conjunto",
    "liberar conjunto montado",
)
NAV_TERMS = (
    "verificar",
    "conferir",
    "inspecionar",
    "apontar",
    "confirmar",
    "selecionar",
    "separar",
    "preparar",
    "abastecer",
    "acoplar talha",
    "ler",
    "ajustar",
    "acionar",
    "recompor",
    "manter",
    "orientar",
)
D_TERMS = (
    "aguardar",
    "espera",
    "procurar",
    "buscar",
    "retrabalho",
    "refazer",
    "corrigir",
    "ajustar novamente",
    "deslocamento excessivo",
    "movimentacao excessiva",
    "retornar por",
)


def classify_microstep_sps(microstep: MicroStep) -> MicroStep:
    """Ensure classification and justification follow SPS logic."""

    text = f"{microstep.instrucao_padrao or microstep.etapa_detalhada} {microstep.justificativa_tecnica}".casefold()
    classification = microstep.classificacao
    waste_type = microstep.tipo_desperdicio
    justification = microstep.justificativa_tecnica.strip()
    confidence_reason = microstep.baixa_confianca_motivo
    requires_gemba = microstep.requer_validacao_gemba

    necessary_without_waste = _states_necessary_without_waste(text)
    if any(term in text for term in D_TERMS) and not necessary_without_waste:
        classification = "D"
        waste_type = waste_type or _waste_type_from_text(text)
        if not _mentions_sps_logic(justification, "D"):
            justification = (
                f"{justification} Perda observavel/reduzivel no metodo atual; nao transforma o produto "
                "e requer avaliacao de fluxo, layout, abastecimento ou sistema."
            ).strip()
    elif any(term in text for term in AV_TERMS):
        classification = "AV"
        if not _mentions_sps_logic(justification, "AV"):
            justification = (
                f"{justification} Acao altera diretamente a condicao do produto/conjunto por montagem, "
                "fixacao, conexao ou aplicacao conforme requisito."
            ).strip()
    elif any(term in text for term in NAV_TERMS) or necessary_without_waste:
        classification = "NAV"
        waste_type = None
        if not _mentions_sps_logic(justification, "NAV"):
            justification = (
                f"{justification} Acao necessaria ao metodo atual, qualidade, seguranca, sistema, "
                "abastecimento ou rastreabilidade, sem transformacao direta do produto."
            ).strip()
    elif not confidence_reason:
        confidence_reason = (
            "Classificacao depende de contexto nao conclusivo pelo video; requer validacao no gemba/SPS."
        )
        requires_gemba = True

    return MicroStep.model_validate(
        microstep.model_dump()
        | {
            "classificacao": classification,
            "justificativa_tecnica": justification,
            "tipo_desperdicio": waste_type,
            "baixa_confianca_motivo": confidence_reason,
            "requer_validacao_gemba": requires_gemba,
        }
    )


def apply_sps_classification_final(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Apply deterministic SPS classification pass to all microsteps."""

    microsteps = [classify_microstep_sps(step) for step in analysis.microetapas]
    return OperationalAnalysis.model_validate(
        analysis.model_dump() | {"microetapas": [step.model_dump() for step in microsteps]}
    )


def _mentions_sps_logic(justification: str, classification: str) -> bool:
    text = justification.casefold()
    if classification == "AV":
        return any(term in text for term in ("transform", "altera", "fixa", "monta", "conecta", "produto"))
    if classification == "NAV":
        return any(term in text for term in ("necess", "qualidade", "seguranca", "sistema", "rastreabilidade"))
    return any(term in text for term in ("perda", "desperd", "espera", "procura", "retrabalho", "excess"))


def _waste_type_from_text(text: str) -> str:
    if any(term in text for term in ("aguardar", "espera", "liberacao")):
        return "espera"
    if any(term in text for term in ("procurar", "buscar", "localizar")):
        return "procura"
    if any(term in text for term in ("retrabalho", "refazer", "corrigir")):
        return "retrabalho"
    if any(term in text for term in ("desloc", "movimentacao", "andar", "caminhar")):
        return "movimentacao excessiva"
    return "desperdicio nao conclusivo"


def _states_necessary_without_waste(text: str) -> bool:
    return any(
        phrase in text
        for phrase in (
            "necessario pelo metodo",
            "necessaria pelo metodo",
            "necessario ao metodo",
            "necessaria ao metodo",
            "necessario pelo método",
            "necessária pelo método",
            "aparenta ser necessario",
            "aparenta ser necessária",
            "aparenta ser necessario pelo metodo",
            "nao ha evidencia suficiente para classifica-lo como desperdicio",
            "não há evidência suficiente para classificá-lo como desperdício",
            "sem evidência suficiente para classificar como desperdício",
        )
    )
