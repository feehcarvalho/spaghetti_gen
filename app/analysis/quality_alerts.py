"""Helpers for preserving SPS quality alerts as exportable review rows."""

from __future__ import annotations

import re
from typing import Any, Iterable

from app.schemas.analysis import OperationalAnalysis


ALERTS_SHEET_NAME = "ALERTAS_VALIDACAO_SPS"
ALERT_HEADERS = [
    "Nº",
    "Severidade",
    "Tipo",
    "Microetapa",
    "Descrição do alerta",
    "Ação recomendada",
    "Requer validação no gemba",
    "Status",
]


def build_quality_alert_rows(
    analysis: OperationalAnalysis,
    extra_alerts: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Return normalized, deduplicated SPS alert rows for JSON/Excel review."""

    raw_alerts: list[str] = []
    raw_alerts.extend(str(alert).strip() for alert in analysis.alertas_validacao if str(alert).strip())
    raw_alerts.extend(str(alert).strip() for alert in (extra_alerts or []) if str(alert).strip())
    raw_alerts.extend(_low_confidence_alerts(analysis))

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for alert in raw_alerts:
        key = " ".join(alert.casefold().split())
        if not key or key in seen:
            continue
        seen.add(key)
        rows.append(_classify_alert(alert, len(rows) + 1))
    return rows


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


def _classify_alert(message: str, number: int) -> dict[str, Any]:
    lowered = _strip_accents(message.casefold())
    microstep = _microstep_number(message)

    severity = "Media"
    alert_type = "Alerta SPS"
    action = "Revisar manualmente a analise e validar no gemba antes de usar como padrao oficial."
    requires_gemba = "Sim"

    if "acao operacional parece estar na justificativa" in lowered:
        severity = "Alta"
        alert_type = "Ação na justificativa"
        action = (
            "Revisar a microetapa e mover a ação operacional para o campo de atividade/instrução."
        )
    elif "sem melhoria" in lowered or "sem melhoria/alerta" in lowered or "classificada como d" in lowered:
        severity = "Alta"
        alert_type = "Etapa D sem melhoria"
        action = "Revisar a etapa D e adicionar melhoria ou justificar manutenção da etapa."
    elif "ferramenta" in lowered and any(token in lowered for token in ("conflitante", "metodo manual", "manual observado")):
        severity = "Alta"
        alert_type = "Ferramenta conflitante"
        action = "Revisar se a etapa foi manual ou com ferramenta. Corrigir a atividade se necessário."
    elif "confianca" in lowered:
        severity = "Alta" if any(token in lowered for token in ("< 0.60", "abaixo de 0.70", "abaixo de 0.7")) else "Media"
        alert_type = "Baixa confiança"
        action = "Validar no gemba e ajustar classificação, tempo, nomenclatura ou evidência se necessário."
    elif any(token in lowered for token in ("eixo", "lado", "ferramenta", "quantidade", "nomenclatura", "termo")):
        alert_type = "Nomenclatura ou evidência incerta"
        action = "Validar no gemba e corrigir a nomenclatura, lado, eixo, quantidade ou ferramenta se necessário."
    elif any(token in lowered for token in ("generica", "generico", "narrativa", "burocratica", "imperativo", "instrucional")):
        alert_type = "Linguagem genérica"
        action = "Reescrever a microetapa com linguagem operacional específica."
    elif "gemba" in lowered:
        alert_type = "Validação gemba"
        action = "Validar presencialmente no gemba antes de utilizar como padrao oficial."
    elif any(token in lowered for token in ("tempo", "timestamp", "cobertura", "janela")):
        alert_type = "Tempo ou cobertura"
        action = "Conferir tempos, cobertura do video e segmentacao antes de oficializar."

    return {
        "numero": number,
        "severidade": severity,
        "tipo": alert_type,
        "microetapa": microstep if microstep is not None else "",
        "descricao": message,
        "acao_recomendada": action,
        "requer_validacao_gemba": requires_gemba,
        "status": "Pendente",
    }


def _microstep_number(message: str) -> int | None:
    match = re.search(r"\bMicroetapa(?:\s+D)?\s+(\d+)\b", message, flags=re.I)
    if not match:
        match = re.search(r"\bEtapa\s+(\d+)\b", message, flags=re.I)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _strip_accents(text: str) -> str:
    mapping = str.maketrans(
        "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
        "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
    )
    return text.translate(mapping)
