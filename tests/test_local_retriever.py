"""Testes para a base de conhecimento local."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.knowledge.bootstrap_docs import bootstrap_docs
from app.knowledge.local_retriever import load_text_documents, retrieve_context


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_ROOT = REPO_ROOT / "data" / "outputs"


def reset_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def test_load_text_documents_handles_empty_folder():
    empty_test_root = OUTPUTS_ROOT / f"test_knowledge_empty_{uuid4().hex}"
    reset_dir(empty_test_root)

    documents = load_text_documents(str(empty_test_root))
    context = retrieve_context("PMGS.P1 farol", str(empty_test_root), position_id="PMGS.P1")

    assert documents == []
    assert "Nenhum documento" in context


def test_retrieve_context_prioritizes_position_documents_and_rules():
    knowledge_test_root = OUTPUTS_ROOT / f"test_knowledge_raw_{uuid4().hex}"
    reset_dir(knowledge_test_root)
    bootstrap_docs(knowledge_test_root)

    context = retrieve_context(
        "analisar PMGS.P1 VR farol LD LE apontamento",
        root_dir=str(knowledge_test_root),
        position_id="PMGS.P1",
        top_k=5,
    )

    assert "## Padrao da Posicao PMGS.P1" in context
    assert "## Regras AV NAV D" in context
    assert "PMGS.P1" in context
    assert "farol LD" in context or "Farol LD" in context
    assert "AV" in context
    assert "NAV" in context
    assert "D" in context
    assert "Fonte:" in context


def test_retrieve_context_returns_useful_string_without_position():
    knowledge_test_root = OUTPUTS_ROOT / f"test_knowledge_raw_{uuid4().hex}"
    reset_dir(knowledge_test_root)
    bootstrap_docs(knowledge_test_root)

    context = retrieve_context(
        "VR talha HOPE Bluebox costelas ribs T-bone chicote",
        root_dir=str(knowledge_test_root),
        top_k=4,
    )

    assert isinstance(context, str)
    assert len(context) > 100
    assert "##" in context
    assert "VR" in context
    assert "HOPE/Bluebox" in context or "HOPE" in context
