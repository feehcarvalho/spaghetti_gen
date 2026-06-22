from app.analysis.language_normalizer import normalize_microstep_language
from app.knowledge.knowledge_orchestrator import SPSContext
from app.schemas.analysis import MicroStep


def test_526_context_replaces_generic_part_with_pneu():
    context = SPSContext(
        context_text="Posto 5.2.6 / 8x2. Quando o item manipulado for pneu, escrever pneu.",
        glossary_terms=["pneu", "VR de pneu"],
        known_parts=["pneu"],
        known_locations=["VR de pneu"],
    )
    step = MicroStep(
        numero=1,
        inicio_s=0.0,
        fim_s=1.0,
        duracao_s=1.0,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada="operador pega a peca no abastecimento",
        classificacao="NAV",
        justificativa_tecnica="Necessario pelo metodo atual.",
        evidencia_visual="Pneu visivel no ponto de abastecimento.",
        confianca=0.9,
    )

    normalized = normalize_microstep_language(step, context)

    assert normalized.etapa_detalhada.startswith("Pegar o pneu")
    assert "peca" not in normalized.etapa_detalhada.casefold()


def test_526_context_keeps_porca_when_fastener_is_observed():
    context = SPSContext(
        context_text="Posto 5.2.6 / 8x2. Usar pneu para pneu e porca para caixa verde de elementos de fixação.",
        glossary_terms=["pneu", "porca", "caixa verde"],
        known_parts=["pneu", "porca"],
    )
    step = MicroStep(
        numero=1,
        inicio_s=0.0,
        fim_s=1.0,
        duracao_s=1.0,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada="Selecionar o componente conforme necessidade da operacao.",
        classificacao="NAV",
        justificativa_tecnica="Necessario pelo metodo atual.",
        evidencia_visual="Frame mostra caixa verde com porcas e mão do operador dentro da caixa.",
        confianca=0.9,
    )

    normalized = normalize_microstep_language(step, context)

    assert normalized.etapa_detalhada == "Selecionar a porca na caixa verde de elementos de fixação."


def test_526_context_keeps_pneu_when_tire_positioning_mentions_prisioneiro():
    context = SPSContext(
        context_text="Posto 5.2.6 / 8x2. Usar pneu para pneu e porca para caixa verde.",
        glossary_terms=["pneu", "porca", "VR de pneu"],
        known_parts=["pneu", "porca"],
        known_locations=["VR de pneu"],
    )
    step = MicroStep(
        numero=1,
        inicio_s=0.0,
        fim_s=1.0,
        duracao_s=1.0,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada="Posicionar o pneu no ponto de montagem do conjunto 8x2.",
        classificacao="AV",
        justificativa_tecnica="Posicionamento do pneu altera o estado do conjunto.",
        evidencia_visual="VR de pneu sustenta o pneu diante do cubo/prisioneiros.",
        ferramenta_observacao="VR de pneu",
        confianca=0.9,
    )

    normalized = normalize_microstep_language(step, context)

    assert normalized.etapa_detalhada.startswith("Posicionar o pneu")
