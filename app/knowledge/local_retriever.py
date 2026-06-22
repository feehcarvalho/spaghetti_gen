"""Busca local simples em documentos Markdown de conhecimento SPS."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


ESSENTIAL_CORPORATE_FILES = {
    "regras_av_nav_d.md",
    "nomenclatura_sps.md",
    "scania_way.md",
    "scania_house.md",
}
TOKEN_RE = re.compile(r"[\wÀ-ÿ./-]+", re.IGNORECASE)


@dataclass(frozen=True)
class KnowledgeDocument:
    path: str
    title: str
    text: str
    category: str
    position_id: str | None = None


def _normalize_token(token: str) -> str:
    return token.casefold().strip(".,;:()[]{}")


def _tokenize(text: str) -> set[str]:
    return {
        normalized
        for normalized in (_normalize_token(token) for token in TOKEN_RE.findall(text))
        if len(normalized) >= 2
    }


def _title_from_path(path: Path) -> str:
    first_line = ""
    try:
        first_line = path.read_text(encoding="utf-8").splitlines()[0]
    except (IndexError, UnicodeDecodeError):
        pass

    if first_line.startswith("#"):
        return first_line.lstrip("#").strip()
    return path.stem.replace("_", " ").title()


def _category_and_position(path: Path, root: Path) -> tuple[str, str | None]:
    relative_parts = path.relative_to(root).parts
    if not relative_parts:
        return "outros", None

    if relative_parts[0] == "corporativo":
        return "corporativo", None

    if relative_parts[0] == "posicoes" and len(relative_parts) >= 2:
        return "posicao", relative_parts[1]

    return relative_parts[0], None


def load_text_documents(root_dir: str) -> list[KnowledgeDocument]:
    """Carrega documentos Markdown/texto de uma raiz local."""

    root = Path(root_dir)
    if not root.exists():
        return []

    documents: list[KnowledgeDocument] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="latin-1")

        category, position = _category_and_position(path, root)
        documents.append(
            KnowledgeDocument(
                path=str(path),
                title=_title_from_path(path),
                text=text,
                category=category,
                position_id=position,
            )
        )

    return documents


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if paragraphs:
        return paragraphs
    return [line.strip() for line in text.splitlines() if line.strip()]


def _relevant_excerpt(document: KnowledgeDocument, query_tokens: set[str], max_chars: int = 900) -> str:
    paragraphs = _split_paragraphs(document.text)
    scored: list[tuple[int, int, str]] = []

    for index, paragraph in enumerate(paragraphs):
        if paragraph.lstrip().startswith("#"):
            continue
        paragraph_tokens = _tokenize(paragraph)
        score = len(query_tokens & paragraph_tokens)
        if score:
            scored.append((score, -index, paragraph))

    if not scored:
        excerpt = next(
            (paragraph for paragraph in paragraphs if not paragraph.lstrip().startswith("#")),
            paragraphs[0] if paragraphs else "",
        )
        return excerpt[:max_chars].strip()

    scored.sort(reverse=True)
    selected: list[str] = []
    total_chars = 0
    for paragraph in paragraphs:
        if paragraph.lstrip().startswith("#"):
            continue
        selected.append(paragraph)
        total_chars += len(paragraph)
        break

    for _, _, paragraph in scored[:3]:
        if paragraph in selected:
            continue
        if total_chars + len(paragraph) > max_chars and selected:
            break
        selected.append(paragraph)
        total_chars += len(paragraph)

    return "\n\n".join(selected)[:max_chars].strip()


def _document_score(
    document: KnowledgeDocument,
    query_tokens: set[str],
    position_id: str | None,
) -> int:
    document_tokens = _tokenize(f"{document.title}\n{document.text}")
    score = len(query_tokens & document_tokens)

    if position_id and document.position_id and document.position_id.casefold() == position_id.casefold():
        score += 12

    filename = Path(document.path).name
    if document.category == "corporativo" and filename in ESSENTIAL_CORPORATE_FILES:
        score += 6

    if filename == "regras_av_nav_d.md":
        score += 8

    if position_id and position_id.casefold() in _tokenize(f"{document.path} {document.title}"):
        score += 4

    return score


def retrieve_context(
    query: str,
    root_dir: str,
    position_id: str | None = None,
    top_k: int = 8,
) -> str:
    """Recupera contexto local concatenado para compor prompt de analise."""

    if top_k <= 0:
        return "Nenhum contexto recuperado: top_k deve ser maior que zero."

    documents = load_text_documents(root_dir)
    if not documents:
        return "Nenhum documento de conhecimento local encontrado."

    query_tokens = _tokenize(f"{query} {position_id or ''}")
    scored = [
        (_document_score(document, query_tokens, position_id), document)
        for document in documents
    ]
    scored.sort(key=lambda item: (item[0], item[1].title), reverse=True)
    selected = [document for score, document in scored if score > 0][:top_k]

    if not selected:
        return "Nenhum trecho relevante encontrado na base de conhecimento local."

    context_blocks = []
    for document in selected:
        relative_path = Path(document.path)
        excerpt = _relevant_excerpt(document, query_tokens)
        context_blocks.append(
            "\n".join(
                [
                    f"## {document.title}",
                    f"Fonte: {relative_path}",
                    f"Categoria: {document.category}"
                    + (f" | Posição: {document.position_id}" if document.position_id else ""),
                    "",
                    excerpt,
                ]
            )
        )

    return "\n\n---\n\n".join(context_blocks)
