"""Persistent feedback memories created from manual correction notes."""

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.config import REPO_ROOT
from app.schemas.analysis import AnalysisMetadata


FEEDBACK_MEMORY_DIR = REPO_ROOT / "data" / "knowledge_raw" / "feedback_aprendizado"


class FeedbackMemory(BaseModel):
    """Structured representation of a manual feedback memory."""

    model_config = ConfigDict(extra="forbid")

    path: str
    created_at: str
    user_login: str | None = None
    posto: str
    processo: str
    video: str | None = None
    analysis_id: str | None = None
    scope: str = "process_specific"
    status: str = "pending_validation"
    feedback_text: str
    general_rules: list[str] = Field(default_factory=list)

    def to_context_block(self) -> str:
        rules = "\n".join(f"- {rule}" for rule in self.general_rules) or "- Nenhuma regra geral extraida."
        return (
            f"FONTE_FEEDBACK: {self.path}\n"
            f"status: {self.status}\n"
            f"escopo: {self.scope}\n"
            f"posto: {self.posto}\n"
            f"processo: {self.processo}\n"
            f"usuario_login: {self.user_login or ''}\n"
            f"video: {self.video or ''}\n\n"
            "Correcao do usuario:\n"
            f"{self.feedback_text}\n\n"
            "Regras gerais extraidas:\n"
            f"{rules}\n"
            "Observacao: Memoria criada a partir de feedback manual. Requer validacao SPS/gemba antes de virar padrao oficial."
        )


def save_feedback_memory(
    feedback_text: str,
    metadata: AnalysisMetadata,
    user_login: str | None,
    analysis_id: str | None,
    scope: str = "process_specific",
    status: str = "pending_validation",
    output_dir: str | Path = FEEDBACK_MEMORY_DIR,
) -> str:
    """Save manual correction feedback as a pending operational memory."""

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_post = _safe_slug(metadata.posto)
    safe_process = _safe_slug(metadata.processo)
    safe_user = _safe_slug(user_login or "usuario")
    path = directory / f"feedback_{timestamp}_{safe_post}_{safe_process}_{safe_user}.md"
    clean_feedback = _redact_sensitive(feedback_text).strip()
    rules = _extract_general_language_rules(clean_feedback)
    content = (
        "# Memoria de feedback manual pendente de validacao\n\n"
        f"- data_hora: {datetime.now().isoformat(timespec='seconds')}\n"
        f"- usuario_login: {_redact_sensitive(user_login or '')}\n"
        f"- posto: {_redact_sensitive(metadata.posto)}\n"
        f"- processo: {_redact_sensitive(metadata.processo)}\n"
        f"- video: {_redact_sensitive(metadata.fonte_video or '')}\n"
        f"- analysis_id: {_redact_sensitive(analysis_id or '')}\n"
        f"- analise_relacionada: {_redact_sensitive(analysis_id or '')}\n"
        f"- status: {status}\n"
        "- status: pendente de validação\n"
        "- status_legado: pendente de validacao\n"
        f"- escopo: {scope}\n"
        "- origem: feedback manual pos-analise\n\n"
        "## Texto da correcao\n\n"
        f"{clean_feedback}\n\n"
        "## Regras gerais extraidas\n\n"
        f"{_format_rules(rules)}\n\n"
        "## Observacao\n\n"
        "Memoria criada a partir de feedback manual. Requer validacao SPS/gemba antes de virar padrao oficial.\n"
    )
    path.write_text(content, encoding="utf-8")
    return str(path)


def load_feedback_memories(
    metadata: AnalysisMetadata,
    include_pending: bool = True,
    memory_dir: str | Path = FEEDBACK_MEMORY_DIR,
) -> list[FeedbackMemory]:
    """Load related process feedback and general language feedback."""

    directory = Path(memory_dir)
    if not directory.exists():
        return []

    loaded: list[FeedbackMemory] = []
    for path in sorted(directory.glob("feedback_*.md")):
        memory = _parse_feedback_file(path)
        if memory is None:
            continue
        if memory.status != "validated" and not include_pending:
            continue
        if _memory_applies_to_metadata(memory, metadata):
            loaded.append(memory)
    return loaded


def feedback_memories_to_context(memories: list[FeedbackMemory], max_chars: int = 5000) -> str:
    """Render feedback memories as an SPS context section."""

    if not memories:
        return ""
    blocks = [
        "MEMORIAS DE FEEDBACK MANUAL PENDENTES DE VALIDACAO",
        "Use como orientacao de alta prioridade quando o posto/processo for relacionado. Marque validacao no gemba quando a informacao ainda estiver pendente.",
    ]
    blocks.extend(memory.to_context_block() for memory in memories)
    return "\n\n".join(blocks)[:max_chars]


def _parse_feedback_file(path: Path) -> FeedbackMemory | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    data = _parse_front_matter_bullets(text)
    feedback = _section(text, "Texto da correcao") or _section(text, "Observação do usuário") or ""
    rules_section = _section(text, "Regras gerais extraidas")
    rules = [
        line.strip(" -\t")
        for line in rules_section.splitlines()
        if line.strip(" -\t") and "nenhuma" not in line.casefold()
    ]
    if not feedback.strip():
        return None
    return FeedbackMemory(
        path=str(path),
        created_at=data.get("data_hora", ""),
        user_login=data.get("usuario_login") or None,
        posto=data.get("posto", ""),
        processo=data.get("processo", ""),
        video=data.get("video") or None,
        analysis_id=data.get("analysis_id") or data.get("analise_relacionada") or None,
        status=_normalize_status(data.get("status", "pending_validation")),
        scope=data.get("escopo") or data.get("scope") or "process_specific",
        feedback_text=feedback.strip(),
        general_rules=rules or _extract_general_language_rules(feedback),
    )


def _memory_applies_to_metadata(memory: FeedbackMemory, metadata: AnalysisMetadata) -> bool:
    if memory.scope == "general_language_rule" or memory.general_rules:
        return True
    if _same_text(memory.posto, metadata.posto):
        return True
    if _same_text(memory.processo, metadata.processo):
        return True
    metadata_text = f"{metadata.posto} {metadata.processo} {metadata.observacoes_gerais or ''}".casefold()
    return bool(memory.processo and memory.processo.casefold() in metadata_text)


def _extract_general_language_rules(feedback_text: str) -> list[str]:
    lowered = feedback_text.casefold()
    rules: list[str] = []
    checks = (
        (("nao repetir", "não repetir", "repetir varias", "repetição"), "Nao repetir microetapas com a mesma intencao operacional; consolidar movimentos continuos quando objeto e objetivo forem os mesmos."),
        (("consolidar", "granularidade", "mesma intencao"), "Consolidar pegar, movimentar e levar quando forem parte do mesmo deslocamento continuo."),
        (("linguagem", "modo imperativo", "mandamento", "roteiro"), "Escrever microetapas como instrucao operacional direta, em modo imperativo."),
        (("generica", "genérica", "ponto necessario", "recurso de apoio"), "Evitar frases genericas sem especificar peca, ferramenta, dispositivo, local ou objetivo."),
        (("nao inventar", "não inventar", "sem evidencia", "sem evidência"), "Nao inventar ferramenta, metodo, eixo, lado, variante ou quantidade sem evidencia/contexto."),
    )
    for tokens, rule in checks:
        if any(token in lowered for token in tokens) and rule not in rules:
            rules.append(rule)
    return rules


def _parse_front_matter_bullets(text: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^-\s*([^:]+):\s*(.*)$", line.strip())
        if match:
            data[match.group(1).strip()] = match.group(2).strip()
    return data


def _section(text: str, title: str) -> str:
    pattern = rf"##\s+{re.escape(title)}\s*\n(.*?)(?=\n##\s+|\Z)"
    match = re.search(pattern, text, flags=re.I | re.S)
    return match.group(1).strip() if match else ""


def _format_rules(rules: list[str]) -> str:
    if not rules:
        return "- Nenhuma regra geral extraida automaticamente."
    return "\n".join(f"- {rule}" for rule in rules)


def _normalize_status(value: str) -> str:
    lowered = value.strip().casefold()
    if "pendente" in lowered:
        return "pending_validation"
    if "valid" in lowered:
        return "validated"
    if "rejeit" in lowered or "reject" in lowered:
        return "rejected"
    return lowered or "pending_validation"


def _same_text(a: str, b: str) -> bool:
    return _safe_slug(a) == _safe_slug(b) and bool(_safe_slug(a))


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(value or "").strip()).strip("_").lower()
    return slug or "analise"


def _redact_sensitive(value: str) -> str:
    text = str(value or "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key in text:
        text = text.replace(api_key, "[redacted]")
    return text
