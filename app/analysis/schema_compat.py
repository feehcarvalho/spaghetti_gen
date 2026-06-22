"""Compatibility helpers for analyses created before schema hardening."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


LOW_CONFIDENCE_DEFAULT_REASON = (
    "Aviso: confiança abaixo do limite recomendado. Validar esta etapa no gemba antes de decisão definitiva."
)


def normalize_analysis_payload_for_current_schema(analysis: Any) -> dict[str, Any]:
    """Return an OperationalAnalysis payload compatible with the current schema."""

    if hasattr(analysis, "model_dump"):
        payload = analysis.model_dump()
    elif isinstance(analysis, dict):
        payload = deepcopy(analysis)
    else:
        raise TypeError("Analise invalida para normalizacao de schema.")

    if "analysis" in payload and isinstance(payload["analysis"], dict) and "microetapas" not in payload:
        payload = deepcopy(payload["analysis"])

    microsteps = payload.get("microetapas") or []
    normalized_steps = []
    for step in microsteps:
        data = dict(step)
        _normalize_microstep_payload(data)
        normalized_steps.append(data)
    payload["microetapas"] = normalized_steps
    payload.setdefault("roteiro_operacional", [])
    payload.setdefault("alertas_validacao", [])
    payload.setdefault("alertas_validacao_sps", [])
    payload.setdefault("recomendacoes_gerais", [])
    payload.setdefault("melhorias", [])
    return payload


def normalize_rows_before_excel_export(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Normalize row payloads before Excel export and collect non-blocking warnings."""

    normalized_rows: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    affected_lines: set[int] = set()

    for row in rows:
        data = dict(row)
        if "validacao_gemba" in data:
            data["requer_validacao_gemba"] = bool(data.pop("validacao_gemba"))
        data.setdefault("requer_validacao_gemba", False)

        confidence = data.get("confianca")
        if confidence == "" or confidence is None:
            data["confianca"] = 0.0
        else:
            try:
                data["confianca"] = float(confidence)
            except (TypeError, ValueError):
                data["confianca"] = 0.0

        if data["confianca"] < 0.7:
            if not data.get("baixa_confianca_motivo"):
                data["baixa_confianca_motivo"] = LOW_CONFIDENCE_DEFAULT_REASON
            data["requer_validacao_gemba"] = True

        if data["confianca"] < 0.9:
            severity = (
                "Baixa - validar no gemba"
                if data["confianca"] < 0.7
                else "Média"
            )
            message = (
                "Confiança abaixo de 0.7. A etapa deve ser validada no gemba."
                if data["confianca"] < 0.7
                else "Confiança entre 0.7 e 0.9. Revisar antes de decisão definitiva."
            )
            warnings.append(
                {
                    "numero": data.get("numero"),
                    "campo": "confianca",
                    "severidade": severity,
                    "mensagem": message,
                    "acao_recomendada": "Validar classificação, tempo e justificativa com a liderança antes de usar para decisão.",
                    "confianca": data["confianca"],
                    "validacao_gemba": "Sim" if data["requer_validacao_gemba"] else "Não",
                }
            )
            if data.get("numero") is not None:
                affected_lines.add(int(data["numero"]))

        normalized_rows.append(data)

    return normalized_rows, warnings, len(warnings), len(affected_lines)


def build_validation_warnings_for_analysis(analysis: Any) -> list[dict[str, Any]]:
    """Build non-blocking validation warnings for Excel export."""

    from math import isclose

    warnings: list[dict[str, Any]] = []

    for step in analysis.microetapas:
        if step.confianca < 0.7:
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "confianca",
                    "severidade": "Baixa - validar no gemba",
                    "mensagem": "Confiança abaixo de 0.7. A etapa deve ser validada no gemba.",
                    "acao_recomendada": "Validar classificação, tempo e justificativa com a liderança antes de usar para decisão.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )
        elif step.confianca < 0.9:
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "confianca",
                    "severidade": "Média",
                    "mensagem": "Confiança entre 0.7 e 0.9. Revisar antes de decisão definitiva.",
                    "acao_recomendada": "Revisar classificação, tempo e justificativa antes de decisão final.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )

        if step.fim_s < step.inicio_s or not isclose(step.duracao_s, step.fim_s - step.inicio_s, abs_tol=0.2):
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "tempo",
                    "severidade": "Baixa - validar no gemba",
                    "mensagem": "Inconsistência identificada entre início, fim e duração.",
                    "acao_recomendada": "Revisar tempos e recalcular a duração antes de exportar.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )

        if not step.evidencia_observavel and not step.evidencia_visual and not step.ferramenta_observacao:
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "evidencia_observavel",
                    "severidade": "Média",
                    "mensagem": "Dados de evidência ou observação ausentes.",
                    "acao_recomendada": "Registrar observação visual ou ferramenta utilizada antes da decisão final.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )

        if len(str(step.justificativa_tecnica).strip()) < 20:
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "justificativa_tecnica",
                    "severidade": "Média",
                    "mensagem": "Justificativa técnica curta ou incompleta.",
                    "acao_recomendada": "Informar motivo técnico mais detalhado para esta etapa.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )

        if step.classificacao == "NAV":
            warnings.append(
                {
                    "numero": step.numero,
                    "etapa": get_step_activity_label(step),
                    "campo": "classificacao",
                    "severidade": "Média",
                    "mensagem": "Classificação NAV pode indicar incerteza operacional.",
                    "acao_recomendada": "Revisar classificação antes de usar esta análise para decisões.",
                    "confianca": step.confianca,
                    "validacao_gemba": "Sim" if step.requer_validacao_gemba else "Não",
                }
            )

    return warnings


def get_step_activity_label(step: Any) -> str:
    return (
        step.etapa_detalhada
        or getattr(step, "instrucao_operacional", None)
        or getattr(step, "descricao_tecnica_detalhada", "")
    )


def _normalize_microstep_payload(data: dict[str, Any]) -> None:
    instruction = (
        data.get("instrucao_operacional")
        or data.get("instrucao_padrao")
        or data.get("descricao_tecnica_detalhada")
        or data.get("etapa_detalhada")
        or data.get("interpretacao_de_processo")
    )
    if instruction:
        data.setdefault("instrucao_operacional", instruction)
        data.setdefault("instrucao_padrao", instruction)
        data.setdefault("descricao_tecnica_detalhada", instruction)
        data.setdefault("interpretacao_de_processo", instruction)
    if not data.get("observacao_visual_bruta"):
        data["observacao_visual_bruta"] = data.get("evidencia_visual") or data.get("evidencia_observavel")
    if not data.get("evidencia_observavel") and data.get("evidencia_visual"):
        data["evidencia_observavel"] = data.get("evidencia_visual")
    data.setdefault("memoria_utilizada", [])
    data.setdefault("nomenclatura_utilizada", [])

    if "validacao_gemba" in data:
        data["requer_validacao_gemba"] = bool(data.pop("validacao_gemba"))
    data.setdefault("requer_validacao_gemba", False)

    try:
        confidence = float(data.get("confianca", 1.0))
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0.7 and not data.get("baixa_confianca_motivo"):
        data["baixa_confianca_motivo"] = LOW_CONFIDENCE_DEFAULT_REASON
        data["requer_validacao_gemba"] = True
