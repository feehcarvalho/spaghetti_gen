from pathlib import Path


STREAMLIT_SOURCE = Path("app/ui/streamlit_app.py").read_text(encoding="utf-8")


def test_memory_not_numbered_main_step():
    assert 'st.subheader("2. Memórias da IA")' not in STREAMLIT_SOURCE
    assert "Memória da IA / adicionar conhecimento" in STREAMLIT_SOURCE
    assert "def _render_memory_sidebar" in STREAMLIT_SOURCE


def test_main_flow_sections_are_operational():
    expected_sections = [
        'st.subheader("1. Vídeo da operação")',
        'st.subheader("2. Layout do posto para mapa de espaguete")',
        'st.subheader("3. Opções da análise")',
        'st.subheader("4. Metadados")',
        'st.subheader("5. Processamento")',
        'st.subheader("6. Resultado da análise")',
    ]

    for section in expected_sections:
        assert section in STREAMLIT_SOURCE


def test_technical_options_are_dev_only():
    assert 'os.getenv("APP_ENV", "local").strip().lower() == "dev"' in STREAMLIT_SOURCE
    assert "Configurações técnicas avançadas" in STREAMLIT_SOURCE
    assert "A análise será executada em qualidade máxima / produção." in STREAMLIT_SOURCE


def test_memory_is_auxiliary_and_optional():
    assert "Adicionar à memória desta análise" in STREAMLIT_SOURCE
    assert "Incluir arquivos de memória anexados nesta análise, se houver" in STREAMLIT_SOURCE
    assert "memory_payload = _render_memory_sidebar()" in STREAMLIT_SOURCE
