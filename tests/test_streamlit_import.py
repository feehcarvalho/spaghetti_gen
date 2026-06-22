import importlib


def test_streamlit_app_imports_without_error():
    module = importlib.import_module("app.ui.streamlit_app")

    assert hasattr(module, "main")
