from pathlib import Path


STREAMLIT_SOURCE = Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")


def test_operational_context_is_optional_expander():
    assert "Contexto operacional adicional" in STREAMLIT_SOURCE
    assert "Configuração/variante do veículo" in STREAMLIT_SOURCE
    assert "Eixo envolvido" in STREAMLIT_SOURCE
    assert "Lado envolvido" in STREAMLIT_SOURCE
    assert "Observações de nomenclatura" in STREAMLIT_SOURCE
