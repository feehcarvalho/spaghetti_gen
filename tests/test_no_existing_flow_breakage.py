import importlib
from pathlib import Path


def test_ui_import_and_download_helpers_still_exist():
    module = importlib.import_module("app.ui.streamlit_app")

    assert hasattr(module, "main")
    assert hasattr(module, "_render_downloads")
    assert hasattr(module, "_generate_excel_from_review_state")


def test_pipeline_current_entrypoint_still_accessible():
    app_main = importlib.import_module("app.main")

    assert hasattr(app_main, "run_analysis_only")
    assert hasattr(app_main, "run_analysis_pipeline")


def test_excel_conversion_and_standard_exports_are_accessible():
    conversion = importlib.import_module("app.excel.conversion_sheet_writer")
    standard = importlib.import_module("app.excel.standard_writer")

    assert hasattr(conversion, "ensure_conversion_sheets")
    assert hasattr(conversion, "validate_conversion_sheet_contract")
    assert hasattr(standard, "write_standard_consolidado_sheet")


def test_standard_template_constant_is_preserved():
    module = importlib.import_module("app.ui.streamlit_app")

    assert module.TEMPLATE_FILENAME == "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
    assert Path(module.DEFAULT_TEMPLATE_PATH).exists()
