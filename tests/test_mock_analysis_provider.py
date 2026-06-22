"""Testes do provider mock de analise."""

from __future__ import annotations

from app.ai.analyzer import AnalysisRequest, MockAnalysisProvider
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis


def test_mock_analysis_provider_returns_valid_sample_analysis():
    request = AnalysisRequest(
        metadata=AnalysisMetadata(
            departamento="PMGS",
            posto="PMGS.P1",
            processo="Pré montagem da grade superior",
            responsavel="Engenharia de Processos",
            data_analise="2026-05-05",
        ),
        frames=[],
        contexto_sps="Contexto SPS de teste",
        regras_av_nav_d="Regras AV/NAV/D de teste",
    )
    provider = MockAnalysisProvider()

    analysis = provider.analyze(request)

    assert isinstance(analysis, OperationalAnalysis)
    assert analysis.metadata.posto == "PMGS.P1"
    assert len(analysis.microetapas) >= 8
    assert {step.classificacao for step in analysis.microetapas} == {"AV", "NAV", "D"}
    assert analysis.resumo_tempos.total_s == 84.0
    assert analysis.melhorias
