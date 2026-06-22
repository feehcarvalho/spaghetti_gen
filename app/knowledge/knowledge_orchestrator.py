"""Build compact SPS context for real video analysis."""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Iterable
import xml.etree.ElementTree as ET

from openpyxl import load_workbook
from pydantic import BaseModel, ConfigDict, Field

from app.config import REPO_ROOT
from app.knowledge.feedback_memory import feedback_memories_to_context, load_feedback_memories
from app.knowledge.xlsx_memory_reader import read_xlsx_memory
from app.schemas.analysis import AnalysisMetadata


KNOWLEDGE_ROOT = REPO_ROOT / "data" / "knowledge_raw"
FORBIDDEN_GENERIC_LANGUAGE = [
    "operador pega a peca",
    "a pessoa vai",
    "ele mexe",
    "parece que",
    "realiza alguma coisa",
    "faz o processo",
    "movimenta peca",
    "operador realiza operacao",
]
STANDARD_LANGUAGE_EXAMPLES = [
    "Ir ate o ponto de abastecimento indicado.",
    "Pegar o componente conforme variante indicada no WPO.",
    "Selecionar o componente conforme necessidade da operacao.",
    "Posicionar a peca no conjunto conforme ponto de montagem.",
    "Fixar o componente no conjunto conforme sequencia padrao.",
    "Apontar a operacao no sistema.",
    "Aguardar liberacao da maquina/sistema para continuidade da operacao.",
]
KNOWN_INTERNAL_TERMS = [
    "Bluebox",
    "VR",
    "WPO",
    "IHM",
    "ROP",
    "LD",
    "LE",
    "HOPE",
    "KD",
    "WO",
    "chicote",
    "talha",
    "apertadeira",
    "T-bone",
    "costelas",
    "ribs",
    "pneu",
    "VR de pneu",
    "conjunto 8x2",
    "parafusadeira pneumática",
    "parafusadeira pneumatica",
    "porca",
    "porcas",
    "caixa verde",
    "elemento de fixação",
    "elementos de fixação",
    "prisioneiro",
    "prisioneiros",
]
TOOL_TERMS = {"talha", "apertadeira", "parafusadeira pneumática", "parafusadeira pneumatica", "IHM", "ROP", "WPO", "WO"}
LOCATION_TERMS = {"Bluebox", "VR", "VR de pneu", "HOPE", "LD", "LE", "KD"}
PART_TERMS = {
    "chicote",
    "T-bone",
    "costelas",
    "ribs",
    "pneu",
    "conjunto 8x2",
    "porca",
    "porcas",
    "elemento de fixação",
    "elementos de fixação",
    "prisioneiro",
    "prisioneiros",
}


class SPSContext(BaseModel):
    """Compact, auditable context injected into SPS prompts."""

    model_config = ConfigDict(extra="forbid")

    context_text: str
    glossary_terms: list[str] = Field(default_factory=list)
    process_rules: list[str] = Field(default_factory=list)
    av_nav_d_rules: list[str] = Field(default_factory=list)
    known_locations: list[str] = Field(default_factory=list)
    known_tools: list[str] = Field(default_factory=list)
    known_parts: list[str] = Field(default_factory=list)
    standard_language_examples: list[str] = Field(default_factory=lambda: list(STANDARD_LANGUAGE_EXAMPLES))
    forbidden_generic_language: list[str] = Field(default_factory=lambda: list(FORBIDDEN_GENERIC_LANGUAGE))
    source_documents: list[str] = Field(default_factory=list)
    unreadable_documents: list[str] = Field(default_factory=list)
    alerts: list[str] = Field(default_factory=list)


def build_sps_context_for_analysis(
    metadata: AnalysisMetadata,
    knowledge_paths: list[str] | None,
    max_chars: int,
) -> SPSContext:
    """Retrieve relevant memories and compress them into structured SPS context."""

    if max_chars <= 0:
        max_chars = 18000

    candidates = list(_ordered_candidate_paths(metadata, knowledge_paths or []))
    loaded: list[tuple[Path, str]] = []
    unreadable: list[str] = []
    alerts: list[str] = []

    for path in candidates:
        if not path.exists():
            alerts.append(f"Memoria nao encontrada: {path}")
            unreadable.append(str(path))
            continue
        if path.is_dir():
            continue
        text, error = _read_supported_document(path)
        if error:
            alerts.append(error)
            unreadable.append(str(path))
            continue
        if text.strip():
            loaded.append((path, text.strip()))

    if not loaded:
        alerts.append("Nenhuma memoria textual foi carregada; analise exige validacao no gemba/SPS.")

    query = _metadata_query(metadata)
    selected = _select_relevant_excerpts(loaded, query, max_chars=max_chars)
    feedback_memories = load_feedback_memories(metadata, include_pending=True)
    feedback_context = feedback_memories_to_context(feedback_memories, max_chars=max(1200, max_chars // 4))
    combined_text = _compose_context_text(
        metadata,
        selected,
        alerts,
        max_chars=max_chars,
        feedback_context=feedback_context,
    )
    glossary_terms = _extract_terms(" ".join(text for _, text in selected))

    return SPSContext(
        context_text=combined_text,
        glossary_terms=glossary_terms,
        process_rules=_extract_rule_lines(selected, ("sps", "padrao", "regra", "standard", "metodo")),
        av_nav_d_rules=_extract_rule_lines(selected, ("av", "nav", "desperdicio", "agrega valor")),
        known_locations=sorted(term for term in glossary_terms if term in LOCATION_TERMS),
        known_tools=sorted(term for term in glossary_terms if term in TOOL_TERMS),
        known_parts=sorted(term for term in glossary_terms if term in PART_TERMS),
        source_documents=[str(path) for path, _ in selected] + [memory.path for memory in feedback_memories],
        unreadable_documents=unreadable,
        alerts=alerts,
    )


def _ordered_candidate_paths(metadata: AnalysisMetadata, knowledge_paths: list[str]) -> Iterable[Path]:
    seen: set[str] = set()
    current_position = metadata.posto.strip().casefold()

    def _yield(path: Path):
        key = str(path.resolve(strict=False)).casefold()
        if key in seen:
            return
        seen.add(key)
        if path.is_dir():
            for child in sorted(path.rglob("*")):
                if child.is_file():
                    if _is_other_position_file(child, current_position):
                        continue
                    child_key = str(child.resolve(strict=False)).casefold()
                    if child_key not in seen:
                        seen.add(child_key)
                        yield child
        else:
            if _is_other_position_file(path, current_position):
                return
            yield path

    for raw_path in knowledge_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = REPO_ROOT / path
        yield from _yield(path)

    position_path = KNOWLEDGE_ROOT / "posicoes" / metadata.posto
    yield from _yield(position_path)

    corporate_path = KNOWLEDGE_ROOT / "corporativo"
    yield from _yield(corporate_path)

    uploads_path = KNOWLEDGE_ROOT / "uploads"
    yield from _yield(uploads_path)


def _is_other_position_file(path: Path, current_position: str) -> bool:
    try:
        relative = path.resolve(strict=False).relative_to((KNOWLEDGE_ROOT / "posicoes").resolve(strict=False))
    except ValueError:
        return False
    parts = relative.parts
    if not parts:
        return False
    return parts[0].casefold() != current_position


def _read_supported_document(path: Path) -> tuple[str, str | None]:
    suffix = path.suffix.lower()
    try:
        if suffix in {".md", ".txt"}:
            return path.read_text(encoding="utf-8", errors="replace"), None
        if suffix == ".csv":
            return _read_csv(path), None
        if suffix == ".docx":
            return _read_docx(path), None
        if suffix == ".xlsx":
            return _read_xlsx(path), None
        if suffix == ".pdf":
            return _read_pdf_if_available(path)
    except Exception as exc:
        return "", f"Nao foi possivel ler memoria {path}: {exc}"

    return "", f"Formato de memoria nao suportado para leitura textual: {path}"


def _read_csv(path: Path) -> str:
    lines: list[str] = []
    with path.open("r", encoding="utf-8", errors="replace", newline="") as csv_file:
        reader = csv.reader(csv_file)
        for row in reader:
            if row:
                lines.append(" | ".join(str(cell) for cell in row))
    return "\n".join(lines)


def _read_docx(path: Path) -> str:
    paragraphs: list[str] = []
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    with zipfile.ZipFile(path, "r") as archive:
        with archive.open("word/document.xml") as document:
            root = ET.parse(document).getroot()
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        text = "".join(texts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _read_xlsx(path: Path) -> str:
    return read_xlsx_memory(str(path)).to_context_text()


def _read_pdf_if_available(path: Path) -> tuple[str, str | None]:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return "", f"PDF salvo, mas biblioteca de leitura nao disponivel; conteudo nao usado: {path}"

    reader = PdfReader(str(path))
    pages = [(page.extract_text() or "") for page in reader.pages]
    return "\n".join(pages), None


def _metadata_query(metadata: AnalysisMetadata) -> str:
    return " ".join(
        part
        for part in (
            metadata.departamento,
            metadata.linha or "",
            metadata.bloco or "",
            metadata.posto,
            metadata.processo,
            metadata.observacoes_gerais or "",
        )
        if part
    ).casefold()


def _select_relevant_excerpts(
    loaded: list[tuple[Path, str]],
    query: str,
    max_chars: int,
) -> list[tuple[Path, str]]:
    query_tokens = _tokens(query)
    scored: list[tuple[int, int, Path, str]] = []
    for order, (path, text) in enumerate(loaded):
        source_text = f"{path.name} {text}".casefold()
        score = len(query_tokens & _tokens(source_text))
        lowered_name = path.name.casefold()
        if any(name in lowered_name for name in ("regra", "av_nav", "nomenclatura", "scania", "padrao")):
            score += 8
        if "uploads" in str(path).casefold():
            score += 10
        scored.append((score, -order, path, _excerpt(text, query_tokens)))

    scored.sort(reverse=True)
    selected: list[tuple[Path, str]] = []
    total = 0
    for _, _, path, excerpt in scored:
        if not excerpt:
            continue
        if total + len(excerpt) > max_chars and selected:
            continue
        selected.append((path, excerpt))
        total += len(excerpt)
        if total >= max_chars:
            break
    return selected


def _excerpt(text: str, query_tokens: set[str], max_chars: int = 1600) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if not paragraphs:
        paragraphs = [line.strip() for line in text.splitlines() if line.strip()]
    scored: list[tuple[int, int, str]] = []
    for index, paragraph in enumerate(paragraphs):
        score = len(query_tokens & _tokens(paragraph.casefold()))
        if score:
            scored.append((score, -index, paragraph))
    if not scored:
        return "\n".join(paragraphs[:4])[:max_chars]
    scored.sort(reverse=True)
    chosen: list[str] = []
    for _, _, paragraph in scored[:4]:
        if paragraph not in chosen:
            chosen.append(paragraph)
    return "\n\n".join(chosen)[:max_chars]


def _compose_context_text(
    metadata: AnalysisMetadata,
    selected: list[tuple[Path, str]],
    alerts: list[str],
    max_chars: int,
    feedback_context: str = "",
) -> str:
    blocks = [
        "CONTEXTO SPS OBRIGATORIO",
        "Use memorias e nomenclaturas apenas quando houver evidencia visual ou contexto suficiente.",
        "Nao invente nomenclatura interna. Em duvida, use termo tecnico generico e marque baixa confianca.",
        f"Posto informado: {metadata.posto}",
        f"Processo informado: {metadata.processo}",
        "",
        "LINGUAGEM PADRAO",
        "\n".join(f"- {item}" for item in STANDARD_LANGUAGE_EXAMPLES),
        "",
        "LINGUAGEM GENERICA PROIBIDA",
        "\n".join(f"- {item}" for item in FORBIDDEN_GENERIC_LANGUAGE),
    ]
    if alerts:
        blocks.extend(["", "ALERTAS DE MEMORIA", "\n".join(f"- {alert}" for alert in alerts)])
    if feedback_context:
        blocks.extend(["", feedback_context])
    for path, excerpt in selected:
        blocks.extend(["", f"FONTE: {path}", excerpt])
    return "\n".join(blocks)[:max_chars]


def _extract_terms(text: str) -> list[str]:
    found: list[str] = []
    lowered = text.casefold()
    for term in KNOWN_INTERNAL_TERMS:
        if term.casefold() in lowered and term not in found:
            found.append(term)
    return sorted(found)


def _extract_rule_lines(selected: list[tuple[Path, str]], keywords: tuple[str, ...]) -> list[str]:
    lines: list[str] = []
    for _, text in selected:
        for line in text.splitlines():
            clean = line.strip(" -\t")
            if len(clean) < 8:
                continue
            lowered = clean.casefold()
            if any(keyword in lowered for keyword in keywords) and clean not in lines:
                lines.append(clean[:280])
            if len(lines) >= 20:
                return lines
    return lines


def _tokens(text: str) -> set[str]:
    return {token.casefold() for token in re.findall(r"[\w./-]+", text) if len(token) >= 2}
