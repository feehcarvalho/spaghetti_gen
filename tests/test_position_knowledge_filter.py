from app.knowledge.knowledge_orchestrator import build_sps_context_for_analysis
from app.schemas.analysis import AnalysisMetadata


def test_position_knowledge_does_not_leak_pmgs_for_526():
    metadata = AnalysisMetadata(
        departamento="FA5",
        posto="5.2.6",
        processo="Montagem 8x2 pneu",
        responsavel="Teste",
        data_analise="2026-05-22",
    )

    context = build_sps_context_for_analysis(metadata, ["data/knowledge_raw"], max_chars=18000)

    assert any("posicoes\\5.2.6" in source or "posicoes/5.2.6" in source for source in context.source_documents)
    assert not any("posicoes\\PMGS.P1" in source or "posicoes/PMGS.P1" in source for source in context.source_documents)
    assert "Pegar o pneu" in context.context_text
