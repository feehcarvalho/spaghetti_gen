from __future__ import annotations

from app.analysis.operational_script_builder import build_operational_script, script_to_microsteps
from app.analysis.quality_gate import detect_unsupported_tool_or_method_claims
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _metadata(processo: str = "Oitao XT-8X2") -> AnalysisMetadata:
    return AnalysisMetadata(
        departamento="Funcao 5",
        posto="5.2.6",
        processo=processo,
        responsavel="Rafael",
        data_analise="2026-05-28",
    )


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
        instrucao_operacional=kwargs.pop("instrucao_operacional", text),
        classificacao=kwargs.pop("classificacao", "NAV"),
        justificativa_tecnica=kwargs.pop("justificativa_tecnica", "Etapa necessaria ao metodo observado."),
        confianca=kwargs.pop("confianca", 0.9),
        baixa_confianca_motivo=kwargs.pop("baixa_confianca_motivo", None),
        **kwargs,
    )


def _analysis(steps: list[MicroStep]) -> OperationalAnalysis:
    total = sum(step.duracao_s for step in steps)
    return OperationalAnalysis(
        metadata=_metadata(),
        microetapas=steps,
        resumo_tempos=TimeSummary(av_s=0, nav_s=total, d_s=0, total_s=total, av_percent=0, nav_percent=100, d_percent=0),
    )


def test_build_operational_script_avoids_repeating_same_tire_pickup():
    analysis = _analysis(
        [
            _step(1, 0, 1, "Pegar o pneu.", peca_componente="pneu"),
            _step(2, 1, 2, "Movimentar o pneu.", peca_componente="pneu"),
            _step(3, 2, 4, "Levar o pneu ate o eixo indicado.", peca_componente="pneu"),
        ]
    )
    script = build_operational_script(analysis, "Processo de pneu com VR de pneu.")
    instructions = [step.instrucao for step in script.steps]
    assert len(instructions) == 1
    assert instructions[0] == "Acoplar o pneu ao VR/talha e deslocar ate o eixo indicado."


def test_build_operational_script_separates_align_fit_and_nuts():
    analysis = _analysis(
        [
            _step(1, 0, 1, "Alinhar o pneu aos prisioneiros do cubo.", peca_componente="pneu"),
            _step(2, 1, 2, "Encaixar o pneu no eixo indicado.", peca_componente="pneu"),
            _step(3, 2, 3, "Colocar as porcas necessarias para travamento inicial.", peca_componente="porcas"),
        ]
    )
    script = build_operational_script(analysis, "Processo de pneu e porcas.")
    assert [step.instrucao for step in script.steps] == [
        "Alinhar o pneu aos prisioneiros do cubo.",
        "Encaixar o pneu no eixo indicado.",
        "Colocar as porcas necessarias para travamento inicial.",
    ]


def test_script_preserves_greenbox_and_does_not_use_bluebox():
    analysis = _analysis(
        [
            _step(1, 0, 2, "Ir ate o ponto de abastecimento indicado.", peca_componente="porcas"),
            _step(2, 2, 4, "Ir ate o Bluebox e pegar porcas.", peca_componente="porcas"),
        ]
    )
    context = "Memoria da posicao: Green Box / caixa verde de porcas."
    script = build_operational_script(analysis, context)
    prepared = script_to_microsteps(script, analysis, context)
    text = " ".join(prepared.roteiro_operacional + [step.instrucao_operacional or "" for step in prepared.microetapas])
    assert "Green Box/caixa verde" in text
    assert "Bluebox" not in text


def test_script_does_not_invent_axis_when_not_confirmed():
    analysis = _analysis([_step(1, 0, 2, "Encaixar o pneu no eixo indicado.", peca_componente="pneu")])
    script = build_operational_script(analysis, "Processo de pneu sem eixo confirmado.")
    assert "segundo eixo" not in script.steps[0].instrucao.casefold()
    assert "eixo indicado" in script.steps[0].instrucao.casefold()


def test_unconfirmed_tool_claim_is_detected_by_gate():
    analysis = _analysis([_step(1, 0, 2, "Fixar as porcas com a parafusadeira pneumatica.", peca_componente="porcas")])
    assert detect_unsupported_tool_or_method_claims(analysis, "")
