"""Single source for the operational activity text used in UI and exports."""

from __future__ import annotations

import re

from app.schemas.analysis import MicroStep


GENERIC_ACTIVITY_ERROR = "Microetapa sem instrucao operacional especifica para exportacao."

GENERIC_PATTERNS = (
    r"^posicionar\s+(?:a\s+)?ferramenta\s+no\s+ponto\s+indicado\.?$",
    r"^posicionar\s+(?:a\s+)?peca\s+no\s+conjunto\s+conforme\s+ponto\s+de\s+montagem\.?$",
    r"^colocar\s+(?:o\s+)?componente\s+no\s+conjunto\.?$",
    r"^realizar\s+(?:a\s+)?(?:atividade|operacao|movimentacao).*$",
    r"^executar\s+(?:a\s+)?(?:atividade|operacao|tarefa).*$",
    r"^movimentar\s+(?:peca|componente)\.?$",
)


def get_microstep_activity_text(microstep: MicroStep) -> str:
    """Return the best operational instruction for a microstep.

    The justification is intentionally never considered an activity source.
    """

    for value in (
        getattr(microstep, "instrucao_operacional", None),
        getattr(microstep, "descricao_tecnica_detalhada", None),
        getattr(microstep, "etapa_detalhada", None),
        getattr(microstep, "interpretacao_de_processo", None),
    ):
        text = _clean(value)
        if text and _is_specific_activity(text):
            return text

    text = _clean(getattr(microstep, "observacao_visual_bruta", None))
    if text:
        raise ValueError(f"{GENERIC_ACTIVITY_ERROR} Observacao visual nao pode virar activity.")
    raise ValueError(GENERIC_ACTIVITY_ERROR)


def is_specific_activity_text(text: str | None) -> bool:
    return bool(_clean(text) and _is_specific_activity(_clean(text)))


def _is_specific_activity(text: str) -> bool:
    normalized = _normalize(text)
    if len(normalized) < 12:
        return False
    return not any(re.search(pattern, normalized, flags=re.IGNORECASE) for pattern in GENERIC_PATTERNS)


def _clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize(value: str) -> str:
    return _clean(value).casefold().replace("peça", "peca").replace("operação", "operacao")
