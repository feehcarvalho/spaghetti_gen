import importlib
from pathlib import Path
from uuid import uuid4


def test_streamlit_auth_imports_without_error():
    module = importlib.import_module("app.ui.auth")

    assert hasattr(module, "render_login_page")


def test_login_background_fallback_works_without_image():
    module = importlib.import_module("app.ui.auth")
    assets_dir = Path("data/outputs/test_auth_runtime") / uuid4().hex / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    style = module.build_login_background_style(assets_dir)

    assert "#061B33" in style
    assert "background" in style
