"""Testes de protecao contra analise falsa de video e download."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.excel.template_writer import write_analysis_to_template
from app import main as app_main
from app.main import run_analysis_only
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis
from app.ui import streamlit_app


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = REPO_ROOT / "data" / "outputs" / "sample_analysis_pmgs_p1.json"
TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"


def metadata() -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="Teste",
        posto="POSTO.TESTE",
        processo="Processo de teste",
        responsavel="Teste Local",
        data_analise="2026-05-05",
        takt_time_s=100.0,
    )


def test_mock_does_not_analyze_video():
    video_path = REPO_ROOT / "data" / "videos" / "uploads" / "test_mock_block_video.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.write_bytes(b"conteudo nao importa porque mock deve bloquear antes")

    with pytest.raises(ValueError, match="mock.*analisa"):
        run_analysis_only(
            video_path=str(video_path),
            output_path=str(REPO_ROOT / "data" / "outputs" / "blocked_mock_video.xlsx"),
            metadata=metadata(),
            provider_name="mock",
        )


def test_pipeline_real_requires_api_key(monkeypatch):
    monkeypatch.setattr(app_main, "_refresh_env", lambda: None)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        run_analysis_only(
            video_path=str(REPO_ROOT / "data" / "videos" / "qualquer_video.mp4"),
            output_path=str(REPO_ROOT / "data" / "outputs" / "blocked_openai.xlsx"),
            metadata=metadata(),
            provider_name="openai",
        )


class UploadedFileStub:
    name = "teste upload.mp4"

    def __init__(self, payload: bytes):
        self.payload = payload

    def getbuffer(self):
        return memoryview(self.payload)


def test_uploaded_file_saved():
    saved_path = Path(streamlit_app.save_uploaded_video(UploadedFileStub(b"video-bytes")))

    assert saved_path.exists()
    assert saved_path.parent == streamlit_app.VIDEOS_UPLOAD_DIR
    assert saved_path.suffix == ".mp4"
    assert saved_path.stat().st_size == len(b"video-bytes")


def test_download_file_exists():
    analysis = OperationalAnalysis.model_validate(
        json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    )
    output_path = REPO_ROOT / "data" / "outputs" / "test_download_file_exists.xlsx"

    result = write_analysis_to_template(
        analysis=analysis,
        template_path=str(TEMPLATE),
        output_path=str(output_path),
    )

    assert Path(result).exists()
    assert streamlit_app._file_ready_for_download(Path(result))


def test_excel_download_bytes():
    analysis = OperationalAnalysis.model_validate(
        json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    )
    output_path = REPO_ROOT / "data" / "outputs" / "test_excel_download_bytes.xlsx"

    result = write_analysis_to_template(
        analysis=analysis,
        template_path=str(TEMPLATE),
        output_path=str(output_path),
    )
    excel_bytes = streamlit_app._read_download_bytes(Path(result))

    assert len(excel_bytes) > 0
    assert excel_bytes.startswith(b"PK")


def test_rejects_corrupt_xlsx_download():
    output_path = REPO_ROOT / "data" / "outputs" / "test_corrupt_download.xlsx"
    output_path.write_bytes(b"not-a-zip")

    with pytest.raises(ValueError, match="xlsx valido"):
        streamlit_app._read_download_bytes(output_path)


def test_generated_workbook_matches_template_sheets():
    analysis = OperationalAnalysis.model_validate(
        json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    )
    output_path = REPO_ROOT / "data" / "outputs" / "test_template_match.xlsx"

    result = write_analysis_to_template(
        analysis=analysis,
        template_path=str(TEMPLATE),
        output_path=str(output_path),
        fill_standard=True,
    )

    streamlit_app._validate_output_matches_template(Path(result), TEMPLATE)
