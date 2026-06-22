"""Utilidades para manipulacao e agregacao de tempos."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.analysis import MicroStep, TimeSummary


def seconds_to_mmss(seconds: float) -> str:
    """Converte segundos para o formato mm:ss."""

    if seconds < 0:
        raise ValueError(f"Segundos não pode ser negativo: {seconds}")

    total_seconds = int(round(seconds))
    minutes = total_seconds // 60
    remaining_seconds = total_seconds % 60

    return f"{minutes:02d}:{remaining_seconds:02d}"


def mmss_to_seconds(value: str) -> float:
    """Converte uma string mm:ss para segundos."""

    if not isinstance(value, str):
        raise ValueError(f"Valor deve ser string, recebido: {type(value)}")

    parts = value.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Formato inválido. Use 'mm:ss', recebido: {value}")

    try:
        minutes = int(parts[0])
        seconds = int(parts[1])
    except ValueError as exc:
        raise ValueError(f"Minutos e segundos devem ser inteiros. Recebido: {value}") from exc

    if minutes < 0 or seconds < 0:
        raise ValueError(f"Minutos e segundos não podem ser negativos: {value}")

    if seconds >= 60:
        raise ValueError(f"Segundos deve ser menor que 60: {value}")

    return float(minutes * 60 + seconds)


def calculate_time_summary(
    microsteps: list[MicroStep],
    takt_time_s: float | None = None,
) -> TimeSummary:
    """Calcula o resumo AV/NAV/D a partir de microetapas validadas."""

    if not microsteps:
        raise ValueError("Lista de microetapas não pode estar vazia")

    av_s = 0.0
    nav_s = 0.0
    d_s = 0.0

    for step in microsteps:
        if not hasattr(step, "duracao_s") or not hasattr(step, "classificacao"):
            raise ValueError(f"Microetapa inválida: {step}")

        if step.duracao_s < 0:
            raise ValueError(f"Duracao de microetapa não pode ser negativa: {step.duracao_s}")

        if step.classificacao == "AV":
            av_s += step.duracao_s
        elif step.classificacao == "NAV":
            nav_s += step.duracao_s
        elif step.classificacao == "D":
            d_s += step.duracao_s
        else:
            raise ValueError(f"Classificação inválida: {step.classificacao}")

    if takt_time_s is not None and takt_time_s < 0:
        raise ValueError(f"Takt time não pode ser negativo: {takt_time_s}")

    total_s = av_s + nav_s + d_s
    if total_s == 0:
        from app.schemas.analysis import TimeSummary

        return TimeSummary(
            av_s=0.0,
            nav_s=0.0,
            d_s=0.0,
            total_s=0.0,
            av_percent=0.0,
            nav_percent=0.0,
            d_percent=0.0,
            folga_vs_takt_s=None,
        )

    folga_vs_takt_s = None if takt_time_s is None else takt_time_s - total_s

    from app.schemas.analysis import TimeSummary

    return TimeSummary(
        av_s=round(av_s, 2),
        nav_s=round(nav_s, 2),
        d_s=round(d_s, 2),
        total_s=round(total_s, 2),
        av_percent=round((av_s / total_s) * 100, 1),
        nav_percent=round((nav_s / total_s) * 100, 1),
        d_percent=round((d_s / total_s) * 100, 1),
        folga_vs_takt_s=round(folga_vs_takt_s, 2) if folga_vs_takt_s is not None else None,
    )


def apply_cumulative_times(microsteps: list[MicroStep]) -> list[MicroStep]:
    """Retorna microetapas com tempo acumulado recalculado em Python."""

    if not microsteps:
        raise ValueError("Lista de microetapas nao pode estar vazia")

    from app.schemas.analysis import MicroStep

    accumulated = 0.0
    updated_steps: list[MicroStep] = []

    for step in microsteps:
        accumulated += step.duracao_s
        data = step.model_dump()
        data.update(
            {
                "tempo_acumulado_s": round(accumulated, 2),
                "tempo_acumulado_formatado": seconds_to_mmss(accumulated),
            }
        )
        updated_steps.append(MicroStep.model_validate(data))

    return updated_steps
