"""Generate improvement suggestions from observed SPS wastes."""

from __future__ import annotations

from app.schemas.analysis import ImprovementSuggestion, OperationalAnalysis


CAUSE_NOT_CONCLUSIVE = "Causa nao conclusiva pelo video; requer validacao no gemba/SPS."


def generate_improvements_from_waste(analysis: OperationalAnalysis) -> list[ImprovementSuggestion]:
    """Create one improvement suggestion for every D-classified microstep."""

    existing_by_step = {
        item.microetapa_numero: item
        for item in analysis.melhorias
        if item.microetapa_numero is not None
    }
    suggestions: list[ImprovementSuggestion] = []

    for step in analysis.microetapas:
        if step.classificacao != "D":
            continue
        if step.numero in existing_by_step:
            suggestions.append(existing_by_step[step.numero])
            continue

        step_text = step.instrucao_padrao or step.etapa_detalhada
        waste_type = step.tipo_desperdicio or _classify_waste_type(step_text, step.justificativa_tecnica)
        suggestions.append(
            ImprovementSuggestion(
                microetapa_numero=step.numero,
                inicio_formatado=step.inicio_formatado,
                fim_formatado=step.fim_formatado,
                duracao_s=step.duracao_s,
                descricao_desperdicio=(
                    f"Perda observada na microetapa {step.numero}: {step_text}"
                ),
                tipo_desperdicio=waste_type,
                causa_observavel=_cause_from_evidence(step.evidencia_visual),
                sugestao_pratica=_suggest_action(waste_type),
                impacto_esperado="Reduzir tempo D e estabilizar o metodo observado.",
                prioridade=_priority_for_duration(step.duracao_s),
                requer_validacao_gemba=True,
            )
        )

    return suggestions


def _classify_waste_type(description: str, justification: str) -> str:
    text = f"{description} {justification}".casefold()
    if any(word in text for word in ("espera", "aguardar", "parado", "liberacao")):
        return "espera"
    if any(word in text for word in ("procur", "buscar", "localizar", "encontrar")):
        return "procura"
    if any(word in text for word in ("retrabal", "refaz", "corrig", "ajustar novamente")):
        return "retrabalho"
    if any(word in text for word in ("desloc", "caminh", "andar", "movimentacao excessiva")):
        return "movimentação excessiva"
    if any(word in text for word in ("transport", "levar", "carregar")):
        return "transporte desnecessário"
    if any(word in text for word in ("processamento extra", "excesso", "duplicad")):
        return "processamento extra"
    if any(word in text for word in ("abastec", "estoque", "falta de peca", "kit")):
        return "estoque/abastecimento inadequado"
    if any(word in text for word in ("defeit", "erro", "falha")):
        return "defeito/erro"
    if any(word in text for word in ("ergonom", "alcance", "postura")):
        return "ergonomia/alcance"
    if any(word in text for word in ("instavel", "variacao", "hesit")):
        return "instabilidade de método"
    return "não conclusivo"


def _cause_from_evidence(evidence: str | None) -> str:
    if not evidence:
        return CAUSE_NOT_CONCLUSIVE
    text = evidence.strip()
    if not text or "nao conclusivo" in text.casefold() or "não conclusivo" in text.casefold():
        return CAUSE_NOT_CONCLUSIVE
    return text


def _suggest_action(waste_type: str) -> str:
    actions = {
        "espera": "Avaliar sincronismo, liberacoes e disponibilidade de recurso no gemba.",
        "procura": "Revisar organizacao visual, endereco de materiais e ponto de uso.",
        "retrabalho": "Validar causa do retrabalho e reforcar poka-yoke, padrao ou qualidade de entrada.",
        "movimentação excessiva": "Revisar layout, ponto de uso e sequencia para reduzir deslocamento.",
        "transporte desnecessário": "Avaliar abastecimento no ponto de uso e fluxo de materiais.",
        "processamento extra": "Validar necessidade tecnica da acao e eliminar duplicidades do metodo.",
        "estoque/abastecimento inadequado": "Revisar quantidade, sequenciamento e reposicao do abastecimento.",
        "defeito/erro": "Investigar origem do defeito e proteger o processo com controle na fonte.",
        "ergonomia/alcance": "Avaliar altura, alcance, postura e dispositivo com seguranca/SPS.",
        "instabilidade de método": "Padronizar sequencia observada e treinar condicao aprovada.",
        "não conclusivo": "Realizar validacao no gemba para identificar causa antes de alterar o metodo.",
    }
    return actions.get(waste_type, actions["não conclusivo"])


def _priority_for_duration(duration_s: float) -> str:
    if duration_s >= 5:
        return "Alta"
    if duration_s >= 2:
        return "Média"
    return "Baixa"
