from __future__ import annotations

from app.analysis.export_preparer import prepare_analysis_for_export
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _step(number: int, start: float, end: float, text: str, **kwargs) -> MicroStep:
    return MicroStep(
        numero=number,
        inicio_s=start,
        fim_s=end,
        duracao_s=end - start,
        inicio_formatado="00:00",
        fim_formatado="00:00",
        duracao_formatada="00:00",
        etapa_detalhada=text,
        instrucao_operacional=text,
        classificacao=kwargs.pop("classificacao", "NAV"),
        justificativa_tecnica="Etapa necessaria ao metodo observado.",
        confianca=0.9,
        **kwargs,
    )


def _analysis(steps: list[MicroStep]) -> OperationalAnalysis:
    total = sum(step.duracao_s for step in steps)
    return OperationalAnalysis(
        metadata=AnalysisMetadata(
            departamento="Funcao 5",
            posto="5.2.6",
            processo="Roda/pneu",
            responsavel="SPS",
            data_analise="2026-05-28",
        ),
        microetapas=steps,
        resumo_tempos=TimeSummary(av_s=0, nav_s=total, d_s=0, total_s=total, av_percent=0, nav_percent=100, d_percent=0),
    )


def test_pick_move_take_tire_becomes_one_step():
    prepared = prepare_analysis_for_export(
        _analysis(
            [
                _step(1, 0, 1, "Pegar o pneu.", peca_componente="pneu"),
                _step(2, 1, 2, "Movimentar o pneu.", peca_componente="pneu"),
                _step(3, 2, 4, "Levar o pneu ate o eixo indicado.", peca_componente="pneu"),
            ]
        ),
        "VR de pneu confirmado",
    )
    assert len(prepared.microetapas) == 1
    assert prepared.resumo_tempos.total_s == 4


def test_align_fit_and_nuts_are_not_merged():
    prepared = prepare_analysis_for_export(
        _analysis(
            [
                _step(1, 0, 1, "Alinhar o pneu aos prisioneiros do cubo.", peca_componente="pneu"),
                _step(2, 1, 2, "Encaixar o pneu no eixo indicado.", peca_componente="pneu"),
                _step(3, 2, 3, "Colocar as porcas necessarias para travamento inicial.", peca_componente="porcas"),
            ]
        ),
        "Processo de pneu",
    )
    assert len(prepared.microetapas) == 3


def test_different_tires_or_axes_are_not_grouped():
    prepared = prepare_analysis_for_export(
        _analysis(
            [
                _step(1, 0, 1, "Pegar o pneu do primeiro eixo.", peca_componente="pneu", eixo="primeiro eixo"),
                _step(2, 1, 2, "Pegar o pneu do segundo eixo.", peca_componente="pneu", eixo="segundo eixo"),
            ]
        ),
        "primeiro eixo e segundo eixo confirmados",
    )
    assert len(prepared.microetapas) == 2
