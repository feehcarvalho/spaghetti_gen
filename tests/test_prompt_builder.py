"""Testes do prompt de analise SPS."""

from __future__ import annotations

from app.ai.analyzer import AnalysisRequest
from app.ai.prompt_builder import build_analysis_prompt
from app.schemas.analysis import AnalysisMetadata
from app.video.frame_extractor import ExtractedFrame


def test_build_analysis_prompt_contains_core_rules_and_frames():
    request = AnalysisRequest(
        metadata=AnalysisMetadata(
            departamento="PMGS",
            posto="PMGS.P1",
            processo="Pré montagem da grade superior",
            responsavel="Engenharia de Processos",
            data_analise="2026-05-05",
            takt_time_s=120.0,
            ciclo_observado_s=84.0,
        ),
        frames=[
            ExtractedFrame(
                index=1,
                timestamp_s=0.0,
                timestamp_formatado="00:00.00",
                path="data/frames/exemplo/frame_000001_000.00s.jpg",
                width=1280,
                height=720,
            )
        ],
        contexto_sps="Contexto SPS de teste",
        regras_av_nav_d="AV transforma produto; NAV necessário; D desperdício.",
        observacoes_usuario="Focar no apontamento do farol.",
        layout_id="PMGS_P1",
    )

    prompt = build_analysis_prompt(request)

    assert "analista de engenharia de processos SPS/Lean" in prompt
    assert "nomenclatura" in prompt
    assert "Não invente informação" in prompt
    assert "baixa_confianca_motivo" in prompt
    assert "sem agrupar ações distintas" in prompt
    assert "AV, NAV ou D" in prompt
    assert "gemba" in prompt
    assert "Não culpe o operador" in prompt
    assert "somente JSON" in prompt
    assert "OperationalAnalysis" in prompt
    assert "MODULO SPS DE ANALISE DE VIDEO INDUSTRIAL" in prompt
    assert "nao analisar por intervalo fixo" in prompt
    assert "microetapa do processo, nao bloco de tempo" in prompt
    assert "AV + NAV + D seja calculado por soma de segundos" in prompt
    assert "Preservar nomes de abas, formulas, graficos, imagens, mesclagens" in prompt
    assert "necessita validacao no gemba/SPS" in prompt
    assert "PMGS.P1" in prompt
    assert "frame_index=1" in prompt
    assert "timestamp=00:00.00" in prompt
    assert "Contexto SPS de teste" in prompt
    assert "Focar no apontamento do farol." in prompt
