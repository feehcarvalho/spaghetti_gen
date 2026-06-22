from pathlib import Path
from uuid import uuid4

from app.analysis.correction_flow import save_feedback_memory
from app.schemas.analysis import AnalysisMetadata


def _runtime_dir() -> Path:
    path = Path("data/outputs/test_feedback_runtime") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_feedback_memory_saved_as_pending_validation(monkeypatch):
    output_dir = _runtime_dir()
    metadata = AnalysisMetadata(
        departamento="Engenharia",
        posto="5.2.6",
        processo="Montagem 8x2",
        responsavel="Teste",
        data_analise="2026-05-21",
    )

    path = save_feedback_memory(
        "Neste processo, usar VR de pneu.",
        metadata=metadata,
        analysis_path="analise_v1.json",
        login="admin",
        output_dir=output_dir,
    )

    text = path.read_text(encoding="utf-8")
    assert path.parent == output_dir
    assert "status: pendente de validação" in text
    assert "usuario_login: admin" in text
    assert "VR de pneu" in text


def test_feedback_memory_redacts_openai_api_key(monkeypatch):
    output_dir = _runtime_dir()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-feedback-secret")

    path = save_feedback_memory(
        "Nao salvar sk-feedback-secret no arquivo.",
        login="admin",
        output_dir=output_dir,
    )

    text = path.read_text(encoding="utf-8")
    assert "sk-feedback-secret" not in text
    assert "[redacted]" in text


def test_feedback_memory_does_not_overwrite_previous_files():
    output_dir = _runtime_dir()

    first = save_feedback_memory("Primeira observacao.", login="admin", output_dir=output_dir)
    second = save_feedback_memory("Segunda observacao.", login="admin", output_dir=output_dir)

    assert first != second
    assert first.exists()
    assert second.exists()
