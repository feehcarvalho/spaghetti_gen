"""Testes de seguranca utilitaria da UI Streamlit."""

from __future__ import annotations

import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from app.ui import streamlit_app


@pytest.fixture
def local_work_dir():
    path = Path(tempfile.gettempdir()) / "ia_sps_scania_test_outputs" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def local_lock_dir():
    path = Path(tempfile.gettempdir()) / "ia_sps_scania_test_locks" / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_upload_extension_validation_accepts_expected_suffixes():
    streamlit_app._validate_upload_extension("operacao.PDF.MP4", {".mp4"})
    streamlit_app._validate_upload_extension("template.xlsx", {".xlsx"})
    streamlit_app._validate_upload_extension("layout.JSON", {".json"})


def test_upload_extension_validation_rejects_unexpected_suffixes():
    with pytest.raises(ValueError, match="Extensao de upload invalida"):
        streamlit_app._validate_upload_extension("payload.exe", {".mp4"})


def test_timestamp_has_microsecond_resolution_for_unique_outputs():
    first = streamlit_app._timestamp()
    second = streamlit_app._timestamp()

    assert first != second
    assert len(first) > len("20260505_120000")


def test_generation_lock_ignores_legacy_output_sidecar(local_work_dir, local_lock_dir, monkeypatch):
    monkeypatch.setattr(streamlit_app, "GENERATION_LOCK_DIR", local_lock_dir)
    excel_path = local_work_dir / "analise.xlsx"
    legacy_lock = streamlit_app._legacy_generation_lock_path(excel_path)
    legacy_lock.write_text("12345", encoding="utf-8")

    fd, lock_path = streamlit_app._acquire_generation_lock(excel_path)
    try:
        assert lock_path.parent == local_lock_dir
        assert lock_path.exists()
        assert legacy_lock.exists()
    finally:
        streamlit_app._release_generation_lock(fd, lock_path)

    assert not lock_path.exists()


def test_generation_lock_blocks_duplicate_temp_lock(local_work_dir, local_lock_dir, monkeypatch):
    monkeypatch.setattr(streamlit_app, "GENERATION_LOCK_DIR", local_lock_dir)
    excel_path = local_work_dir / "analise.xlsx"
    fd, lock_path = streamlit_app._acquire_generation_lock(excel_path)

    try:
        with pytest.raises(streamlit_app.GenerationAlreadyRunningError, match="ja esta em andamento"):
            streamlit_app._acquire_generation_lock(excel_path)
    finally:
        streamlit_app._release_generation_lock(fd, lock_path)


def test_generation_lock_active_tracks_temp_lock(local_work_dir, local_lock_dir, monkeypatch):
    monkeypatch.setattr(streamlit_app, "GENERATION_LOCK_DIR", local_lock_dir)
    excel_path = local_work_dir / "analise.xlsx"

    assert not streamlit_app._is_generation_lock_active(excel_path)

    fd, lock_path = streamlit_app._acquire_generation_lock(excel_path)
    try:
        assert streamlit_app._is_generation_lock_active(excel_path)
    finally:
        streamlit_app._release_generation_lock(fd, lock_path)

    assert not streamlit_app._is_generation_lock_active(excel_path)
