"""Helpers for post-analysis correction and local feedback memory."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from app.knowledge.feedback_memory import save_feedback_memory as _save_structured_feedback_memory
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis


FEEDBACK_MEMORY_DIR = Path("data/knowledge_raw/feedback_aprendizado")
SESSION_CORRECTION_DIR = Path("data/outputs/corrections/session_context")
CORRECTION_REVIEW_PROMPT = (
    "Você deve revisar a análise SPS anterior considerando a observação do usuário. "
    "Preserve o que estiver correto. Corrija apenas o que a observação justificar. "
    "Não invente novas etapas sem evidência visual ou memória. Não altere tempos sem necessidade. "
    "Não altere classificação AV/NAV/D sem justificativa. Reescreva microetapas para linguagem "
    "operacional Scania, no modo imperativo. Use memórias internas, nomenclatura disponível e "
    "observação do usuário como contexto."
)


def build_correction_context(
    previous_analysis: OperationalAnalysis,
    user_observation: str,
) -> str:
    """Build a local RAG note for a correction rerun."""

    observation = _redact_sensitive(user_observation).strip()
    previous_payload = previous_analysis.model_dump(mode="json")
    compact_previous = {
        "metadata": previous_payload.get("metadata", {}),
        "resumo_tempos": previous_payload.get("resumo_tempos", {}),
        "microetapas": previous_payload.get("microetapas", []),
        "melhorias": previous_payload.get("melhorias", []),
        "alertas_validacao": previous_payload.get("alertas_validacao", []),
    }
    return (
        "# Revisao contextual pos-analise SPS\n\n"
        "## CORRECAO DO USUARIO — PRIORIDADE ALTA\n\n"
        f"{observation}\n\n"
        f"{CORRECTION_REVIEW_PROMPT}\n\n"
        "## Observacao do usuario\n\n"
        f"{observation}\n\n"
        "## Análise SPS anterior\n\n"
        "```json\n"
        f"{json.dumps(compact_previous, ensure_ascii=False, indent=2)}\n"
        "```\n"
    )


def save_correction_context_note(
    previous_analysis: OperationalAnalysis,
    user_observation: str,
    login: str | None = None,
    output_dir: str | Path = SESSION_CORRECTION_DIR,
) -> Path:
    """Persist the correction context used only by the rerun."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = _timestamp()
    safe_login = _safe_slug(login or "usuario")
    path = directory / f"correction_context_{timestamp}_{safe_login}.md"
    path.write_text(
        build_correction_context(previous_analysis, user_observation),
        encoding="utf-8",
    )
    return path


def save_feedback_memory(
    observation: str,
    metadata: AnalysisMetadata | None = None,
    analysis_path: str | Path | None = None,
    login: str | None = None,
    output_dir: str | Path = FEEDBACK_MEMORY_DIR,
) -> Path:
    """Save user feedback as pending local memory for future RAG review."""

    metadata = metadata or _empty_metadata()
    return Path(
        _save_structured_feedback_memory(
            feedback_text=observation,
            metadata=metadata,
            user_login=login,
            analysis_id=str(analysis_path or ""),
            scope="process_specific",
            status="pending_validation",
            output_dir=output_dir,
        )
    )


def build_reanalysis_prompt_with_feedback(
    original_analysis: OperationalAnalysis,
    feedback_text: str,
    metadata: AnalysisMetadata,
    sps_context,
) -> str:
    """Build a high-priority correction prompt block for reruns."""

    context_text = getattr(sps_context, "context_text", str(sps_context or ""))
    compact_steps = [
        {
            "numero": step.numero,
            "atividade": (
                getattr(step, "instrucao_operacional", None)
                or getattr(step, "instrucao_padrao", None)
                or getattr(step, "etapa_detalhada", "")
            ),
            "classificacao": step.classificacao,
            "inicio_s": step.inicio_s,
            "fim_s": step.fim_s,
        }
        for step in original_analysis.microetapas[:80]
    ]
    return (
        "# CORRECAO DO USUARIO — PRIORIDADE ALTA\n\n"
        "Esta correcao do usuario tem prioridade alta. Reanalise o video considerando essa correcao. "
        "Nao faca apenas uma reescrita superficial. Corrija a sequencia operacional, a nomenclatura, "
        "a granularidade e os tempos quando necessario.\n\n"
        "## Correcao completa do usuario\n\n"
        f"{_redact_sensitive(feedback_text).strip()}\n\n"
        "## Metadados\n\n"
        f"posto: {metadata.posto}\n"
        f"processo: {metadata.processo}\n"
        f"video: {metadata.fonte_video or ''}\n\n"
        "## Analise anterior resumida\n\n"
        "```json\n"
        f"{json.dumps(compact_steps, ensure_ascii=False, indent=2)}\n"
        "```\n\n"
        "## Memorias relevantes\n\n"
        f"{context_text}\n\n"
        "## Regra de uso\n\n"
        "Use a correcao como orientacao de alta prioridade, desde que nao contradiga evidencia visual critica. "
        "Se a correcao estiver pendente de validacao, marque requer_validacao_gemba quando aplicar informacao especifica de processo."
    )


def next_corrected_excel_path(
    previous_excel_path: str | Path,
    history_count: int = 0,
    base_stem: str | None = None,
) -> Path:
    """Return a non-overwriting corrected Excel output path."""

    previous = Path(previous_excel_path)
    version = max(2, int(history_count) + 2)
    stem = _safe_slug(base_stem or _base_stem(previous.stem))
    candidate = previous.with_name(f"{stem}_v{version}_corrigida_{_timestamp()}.xlsx")
    while candidate.exists():
        version += 1
        candidate = previous.with_name(f"{stem}_v{version}_corrigida_{_timestamp()}.xlsx")
    return candidate


def append_correction_history(
    history: list[dict[str, Any]] | None,
    *,
    observation: str,
    previous_excel_path: str | Path,
    previous_json_path: str | Path,
    new_excel_path: str | Path,
    new_json_path: str | Path,
    feedback_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Return a new correction history preserving previous versions."""

    updated = list(history or [])
    updated.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "observation": _redact_sensitive(observation).strip(),
            "previous_excel_path": str(previous_excel_path),
            "previous_json_path": str(previous_json_path),
            "new_excel_path": str(new_excel_path),
            "new_json_path": str(new_json_path),
            "feedback_path": str(feedback_path) if feedback_path else None,
        }
    )
    return updated


def prepare_correction_rerun(
    previous_excel_path: str | Path,
    observation: str,
    history: list[dict[str, Any]] | None = None,
    login: str | None = None,
    base_stem: str | None = None,
) -> dict[str, Any]:
    """Prepare versioning metadata for a correction rerun."""

    output_path = next_corrected_excel_path(
        previous_excel_path,
        history_count=len(history or []),
        base_stem=base_stem,
    )
    return {
        "observation": _redact_sensitive(observation).strip(),
        "login": _redact_sensitive(login or ""),
        "output_path": str(output_path),
        "json_path": str(output_path.with_suffix(".json")),
        "version": len(history or []) + 2,
    }


def _empty_metadata() -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="",
        posto="",
        processo="",
        responsavel="",
        data_analise=datetime.now().date().isoformat(),
    )


def _base_stem(stem: str) -> str:
    return re.sub(r"_v\d+_corrigida.*$", "", stem)


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    return slug or "analise"


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _redact_sensitive(value: str) -> str:
    text = str(value or "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key in text:
        text = text.replace(api_key, "[redacted]")
    return text
