"""Continuous-improvement analysis derived from D-classified steps."""

from __future__ import annotations

from app.analysis.improvements import generate_improvements_from_waste
from app.schemas.analysis import OperationalAnalysis


GENERAL_RECOMMENDATIONS = [
    "Validar balanceamento entre etapas e postos antes de alterar tempo padrao.",
    "Avaliar layout e pontos de uso para reduzir deslocamentos e transporte sem transformacao.",
    "Revisar abastecimento, sequenciamento e disponibilidade de materiais no gemba.",
    "Confirmar padronizacao do metodo observado com lideranca/SPS antes de aprovar mudanca.",
    "Avaliar ergonomia, alcances e uso de dispositivos com seguranca e engenharia.",
    "Verificar estabilidade de sistema/apontamento quando houver esperas ou interrupcoes.",
    "Aplicar 5S e gestao visual quando houver procura, separacao incerta ou baixa rastreabilidade.",
]


def generate_continuous_improvement_analysis(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Generate D-step improvements and conservative SPS recommendations."""

    improvements = generate_improvements_from_waste(analysis)
    recommendations = list(analysis.recomendacoes_gerais)
    for recommendation in GENERAL_RECOMMENDATIONS:
        if recommendation not in recommendations:
            recommendations.append(recommendation)

    alerts = list(analysis.alertas_validacao)
    for item in improvements:
        if item.causa_observavel.casefold().startswith("causa nao conclusiva") or "nao conclusiva" in item.causa_observavel.casefold():
            message = (
                f"Melhoria da microetapa {item.microetapa_numero} depende de validacao no gemba/SPS; "
                "causa nao conclusiva pelo video."
            )
            if message not in alerts:
                alerts.append(message)

    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {
            "melhorias": [item.model_dump() for item in improvements],
            "recomendacoes_gerais": recommendations,
            "alertas_validacao": alerts,
        }
    )
