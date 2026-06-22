from __future__ import annotations

from app.analysis.operational_investigator import apply_operational_investigation
from app.knowledge.knowledge_orchestrator import SPSContext
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _analysis_with_step(step: MicroStep) -> OperationalAnalysis:
    return OperationalAnalysis(
        metadata=AnalysisMetadata(
            departamento="FA5",
            posto="5.2.6",
            processo="Montagem 8x2",
            responsavel="Teste",
            data_analise="2026-05-26",
            takt_time_s=300,
        ),
        microetapas=[step],
        resumo_tempos=TimeSummary(
            av_s=step.duracao_s if step.classificacao == "AV" else 0,
            nav_s=step.duracao_s if step.classificacao == "NAV" else 0,
            d_s=step.duracao_s if step.classificacao == "D" else 0,
            total_s=step.duracao_s,
            av_percent=100 if step.classificacao == "AV" else 0,
            nav_percent=100 if step.classificacao == "NAV" else 0,
            d_percent=100 if step.classificacao == "D" else 0,
            folga_vs_takt_s=300 - step.duracao_s,
        ),
    )


def _step(text: str, evidence: str = "") -> MicroStep:
    return MicroStep(
        numero=1,
        inicio_s=0,
        fim_s=5,
        duracao_s=5,
        inicio_formatado="00:00",
        fim_formatado="00:05",
        duracao_formatada="00:05",
        tempo_acumulado_s=5,
        tempo_acumulado_formatado="00:05",
        etapa_detalhada=text,
        instrucao_padrao=text,
        classificacao="AV",
        justificativa_tecnica="Etapa agrega valor por posicionar componente no conjunto.",
        evidencia_observavel=evidence,
        confianca=0.9,
    )


def _context(text: str, terms: list[str] | None = None) -> SPSContext:
    return SPSContext(
        context_text=text,
        glossary_terms=terms or [],
        known_locations=[term for term in terms or [] if "VR" in term],
        known_tools=[term for term in terms or [] if "parafusadeira" in term.casefold()],
        known_parts=["pneu"] if "pneu" in (terms or []) else [],
    )


def test_context_axis_side_variant_are_used_when_available():
    context = _context(
        "\n".join(
            [
                "Configuracao/variante do veiculo: 8x2",
                "Eixo envolvido: segundo eixo",
                "Lado envolvido: LD",
            ]
        )
    )
    analysis = apply_operational_investigation(
        _analysis_with_step(_step("Alinhar o pneu aos prisioneiros do cubo.")),
        context,
    )
    text = analysis.microetapas[0].instrucao_padrao

    assert "8x2" in text
    assert "segundo eixo" in text
    assert "LD" in text


def test_missing_vehicle_detail_marks_low_confidence_without_inventing():
    analysis = apply_operational_investigation(
        _analysis_with_step(_step("Alinhar o pneu aos prisioneiros do cubo.")),
        _context("Sem eixo, lado ou variante confirmados."),
    )
    step = analysis.microetapas[0]

    assert "segundo eixo" not in step.instrucao_padrao
    assert step.requer_validacao_gemba is True
    assert step.baixa_confianca_motivo


def test_memory_term_vr_de_pneu_replaces_generic_equipment():
    analysis = apply_operational_investigation(
        _analysis_with_step(_step("Deslocar o equipamento ate o ponto de montagem.", "pneu visivel no VR")),
        _context("Nomenclatura: VR de pneu", ["VR de pneu", "pneu"]),
    )

    assert "VR de pneu" in analysis.microetapas[0].instrucao_padrao
    assert "equipamento" not in analysis.microetapas[0].instrucao_padrao.casefold()


def test_memory_tool_term_replaces_generic_tool():
    analysis = apply_operational_investigation(
        _analysis_with_step(_step("Pegar a ferramenta para apertar as porcas.", "parafusadeira em uso")),
        _context("Nomenclatura: parafusadeira pneumática", ["parafusadeira pneumática"]),
    )

    assert "parafusadeira pneumática" in analysis.microetapas[0].instrucao_padrao
    assert "ferramenta" not in analysis.microetapas[0].instrucao_padrao.casefold()


def test_quantity_is_not_invented_without_memory_or_visual_evidence():
    analysis = apply_operational_investigation(
        _analysis_with_step(_step("Selecionar as porcas na caixa verde.", "caixa verde")),
        _context("Sem quantidade confirmada."),
    )

    assert "10 porcas" not in analysis.microetapas[0].instrucao_padrao
