"""Testes de configuracao do provider OpenAI sem chamada real."""

from __future__ import annotations

import pytest

from app.ai.analyzer import AnalysisProviderError, AnalysisRequest, OpenAIAnalysisProvider
from app.ai.prompt_builder import build_analysis_prompt
from app.schemas.analysis import AnalysisMetadata


def build_request() -> AnalysisRequest:
    return AnalysisRequest(
        metadata=AnalysisMetadata(
            departamento="PMGS",
            posto="PMGS.P1",
            processo="Pre montagem da grade superior",
            responsavel="Engenharia de Processos",
            data_analise="2026-05-05",
            takt_time_s=120.0,
        ),
        frames=[],
        contexto_sps="Contexto SPS para teste de provider OpenAI.",
        regras_av_nav_d="AV agrega valor; NAV e necessario; D e desperdicio.",
        observacoes_usuario="Sinalizar baixa confianca quando a evidencia visual for insuficiente.",
        layout_id="PMGS.P1",
    )


def test_openai_provider_friendly_error_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    provider = OpenAIAnalysisProvider(api_key=None)

    with pytest.raises(AnalysisProviderError, match="OPENAI_API_KEY nao configurada"):
        provider.analyze(build_request())


def test_openai_provider_reads_environment_configuration(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-placeholder")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test-model")
    monkeypatch.setenv("OPENAI_MAX_FRAMES", "3")

    provider = OpenAIAnalysisProvider()

    assert provider.api_key == "test-key-placeholder"
    assert provider.model == "gpt-test-model"
    assert provider.max_frames == 3


def test_openai_provider_ignores_blocked_loopback_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")

    provider = OpenAIAnalysisProvider(api_key="test-key-placeholder")

    assert provider._should_ignore_proxy_env() is True


def test_openai_provider_respects_regular_proxy(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example.local:8080")
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    monkeypatch.delenv("ALL_PROXY", raising=False)

    provider = OpenAIAnalysisProvider(api_key="test-key-placeholder")

    assert provider._should_ignore_proxy_env() is False


def test_prompt_contains_av_nav_d_and_low_confidence_rules():
    prompt = build_analysis_prompt(build_request())

    assert "AV/NAV/D" in prompt
    assert "baixa_confianca_motivo" in prompt
    assert "baixa confiança" in prompt
    assert "Não invente informação" in prompt
    assert "nomenclatura" in prompt
    assert "gemba" in prompt
