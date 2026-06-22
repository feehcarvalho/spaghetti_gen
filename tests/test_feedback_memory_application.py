from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from app.analysis.correction_flow import build_reanalysis_prompt_with_feedback
from app.analysis.quality_gate import validate_feedback_was_applied
from app.knowledge.feedback_memory import (
    feedback_memories_to_context,
    load_feedback_memories,
    save_feedback_memory,
)
from app.knowledge.knowledge_orchestrator import build_sps_context_for_analysis
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _runtime_dir() -> Path:
    path = Path("data/outputs/test_feedback_application") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _metadata(posto: str = "5.2.6", processo: str = "Oitao XT-8X2") -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="Funcao 5",
        posto=posto,
        processo=processo,
        responsavel="Rafael",
        data_analise="2026-05-28",
        fonte_video="oitao.mp4",
    )


def _analysis(texts: list[str], metadata: AnalysisMetadata | None = None) -> OperationalAnalysis:
    steps = [
        MicroStep(
            numero=index,
            inicio_s=index - 1,
            fim_s=index,
            duracao_s=1,
            inicio_formatado="00:00",
            fim_formatado="00:01",
            duracao_formatada="00:01",
            etapa_detalhada=text,
            instrucao_operacional=text,
            classificacao="NAV",
            justificativa_tecnica="Etapa necessaria ao metodo observado.",
            confianca=0.9,
        )
        for index, text in enumerate(texts, start=1)
    ]
    total = float(len(steps))
    return OperationalAnalysis(
        metadata=metadata or _metadata(),
        microetapas=steps,
        resumo_tempos=TimeSummary(av_s=0, nav_s=total, d_s=0, total_s=total, av_percent=0, nav_percent=100, d_percent=0),
    )


def test_feedback_is_saved_with_pending_status_and_process_metadata():
    output_dir = _runtime_dir()
    path = Path(
        save_feedback_memory(
            "Nesse processo, pegar porcas na Green Box/caixa verde.",
            metadata=_metadata(),
            user_login="rafael",
            analysis_id="analise_123",
            output_dir=output_dir,
        )
    )
    text = path.read_text(encoding="utf-8")
    assert path.parent == output_dir
    assert "status: pending_validation" in text
    assert "escopo: process_specific" in text
    assert "posto: 5.2.6" in text
    assert "processo: Oitao XT-8X2" in text
    assert "Green Box/caixa verde" in text


def test_feedback_loads_for_same_post_process_and_enters_context():
    output_dir = _runtime_dir()
    save_feedback_memory(
        "Nesse processo, usar Green Box/caixa verde antes de montar o pneu.",
        metadata=_metadata(),
        user_login="rafael",
        analysis_id="a1",
        output_dir=output_dir,
    )
    memories = load_feedback_memories(_metadata(), memory_dir=output_dir)
    context = feedback_memories_to_context(memories)
    assert len(memories) == 1
    assert "MEMORIAS DE FEEDBACK MANUAL PENDENTES DE VALIDACAO" in context
    assert "Green Box/caixa verde" in context


def test_process_specific_feedback_does_not_apply_to_unrelated_process():
    output_dir = _runtime_dir()
    save_feedback_memory(
        "Nesse processo, usar Green Box/caixa verde.",
        metadata=_metadata(posto="5.2.6", processo="Oitao XT-8X2"),
        user_login="rafael",
        analysis_id="a1",
        output_dir=output_dir,
    )
    unrelated = _metadata(posto="PMGS.P1", processo="Montagem da grade superior")
    assert load_feedback_memories(unrelated, memory_dir=output_dir) == []


def test_general_language_feedback_can_apply_to_other_processes():
    output_dir = _runtime_dir()
    save_feedback_memory(
        "Nao repetir varias linhas para pegar e movimentar o mesmo pneu; consolidar quando for a mesma intencao operacional.",
        metadata=_metadata(),
        user_login="rafael",
        analysis_id="a1",
        output_dir=output_dir,
    )
    unrelated = _metadata(posto="PMGS.P1", processo="Montagem da grade superior")
    memories = load_feedback_memories(unrelated, memory_dir=output_dir)
    assert memories
    assert memories[0].general_rules


def test_reanalysis_prompt_contains_high_priority_feedback():
    analysis = _analysis(["Ir ate o Bluebox e pegar porcas."])
    prompt = build_reanalysis_prompt_with_feedback(
        analysis,
        "Corrigir para Green Box/caixa verde.",
        analysis.metadata,
        "Memorias SPS relevantes",
    )
    assert "CORRECAO DO USUARIO" in prompt
    assert "prioridade alta" in prompt.casefold()
    assert "Nao faca apenas uma reescrita superficial" in prompt
    assert "Green Box/caixa verde" in prompt


def test_feedback_blocks_export_when_greenbox_correction_not_applied():
    analysis = _analysis(["Ir ate o Bluebox e pegar porcas."])
    alerts = validate_feedback_was_applied(analysis, "Usar Green Box/caixa verde, nao Bluebox.")
    assert any("Reprocessar antes de gerar Excel" in alert for alert in alerts)


def test_feedback_blocks_manual_becoming_pneumatic():
    analysis = _analysis(["Fixar as porcas com a parafusadeira pneumatica."])
    alerts = validate_feedback_was_applied(analysis, "A instalacao das porcas e manual.")
    assert alerts


def test_feedback_repetition_check_detects_redundant_microsteps():
    analysis = _analysis(["Pegar o pneu.", "Pegar o pneu.", "Pegar o pneu."])
    alerts = validate_feedback_was_applied(analysis, "Nao repetir varias linhas com a mesma intencao operacional.")
    assert alerts


def test_feedback_context_is_added_to_sps_context(monkeypatch):
    output_dir = _runtime_dir()
    save_feedback_memory(
        "Nesse processo, usar Green Box/caixa verde.",
        metadata=_metadata(),
        user_login="rafael",
        analysis_id="a1",
        output_dir=output_dir,
    )
    monkeypatch.setattr("app.knowledge.knowledge_orchestrator.load_feedback_memories", lambda metadata, include_pending=True: load_feedback_memories(metadata, memory_dir=output_dir))
    context = build_sps_context_for_analysis(_metadata(), [], max_chars=4000)
    assert "Memoria criada a partir de feedback manual" in context.context_text
    assert "Green Box/caixa verde" in context.context_text
