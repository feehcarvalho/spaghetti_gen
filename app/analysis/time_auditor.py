"""Python-side time audit for SPS OperationalAnalysis."""

from __future__ import annotations

from app.schemas.analysis import MicroStep, OperationalAnalysis, TimeSummary
from app.utils.time_utils import calculate_time_summary, seconds_to_mmss
from app.video.video_metadata import VideoMetadata


GAP_THRESHOLD_S = 2.0
OVERLAP_THRESHOLD_S = 0.5


def calculate_element_time(inicio_s, fim_s) -> float:
    """Calculate the individual element time from observable timestamps."""

    start_s = round(float(inicio_s), 3)
    end_s = round(float(fim_s), 3)
    if start_s < 0 or end_s < 0:
        raise ValueError("Inicio/fim da microetapa nao podem ser negativos.")
    if end_s < start_s:
        raise ValueError("fim_s nao pode ser menor que inicio_s.")
    return round(end_s - start_s, 3)


def calculate_accumulated_times(microsteps: list[MicroStep]) -> list[MicroStep]:
    """Recalculate duration and accumulated time in sequence."""

    if not microsteps:
        raise ValueError("Lista de microetapas nao pode estar vazia.")

    accumulated = 0.0
    recalculated: list[MicroStep] = []
    for step in microsteps:
        start_s = round(float(step.inicio_s), 3)
        end_s = round(float(step.fim_s), 3)
        duration_s = calculate_element_time(start_s, end_s)
        accumulated = round(accumulated + duration_s, 3)
        recalculated.append(
            MicroStep.model_validate(
                step.model_dump()
                | {
                    "inicio_s": start_s,
                    "fim_s": end_s,
                    "duracao_s": duration_s,
                    "tempo_acumulado_s": accumulated,
                    "inicio_formatado": seconds_to_mmss(start_s),
                    "fim_formatado": seconds_to_mmss(end_s),
                    "duracao_formatada": seconds_to_mmss(duration_s),
                    "tempo_acumulado_formatado": seconds_to_mmss(accumulated),
                }
            )
        )
    return recalculated


def calculate_av_nav_d_totals(microsteps: list[MicroStep]) -> TimeSummary:
    """Calculate AV/NAV/D totals from audited element times."""

    return calculate_time_summary(microsteps)


def audit_and_recalculate_times(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Authoritative timing pass used before UI/JSON/Excel export."""

    return recalculate_microstep_times(analysis)


def validate_time_consistency(analysis: OperationalAnalysis) -> list[str]:
    """Return technical timing alerts after comparing AI values to Python calculations."""

    alerts: list[str] = []
    if not analysis.microetapas:
        return ["Analise sem microetapas para auditoria de tempo."]

    accumulated = 0.0
    for step in analysis.microetapas:
        try:
            expected_duration = calculate_element_time(step.inicio_s, step.fim_s)
        except ValueError as exc:
            alerts.append(f"Microetapa {step.numero}: {exc}")
            continue

        accumulated = round(accumulated + expected_duration, 3)
        if abs(step.duracao_s - expected_duration) > 0.1:
            alerts.append(
                f"Microetapa {step.numero}: duracao_s={step.duracao_s:.3f}s difere de fim-inicio "
                f"({expected_duration:.3f}s); usar calculo Python."
            )
        if step.tempo_acumulado_s is not None and abs(step.tempo_acumulado_s - accumulated) > 0.2:
            alerts.append(
                f"Microetapa {step.numero}: tempo acumulado incoerente "
                f"({step.tempo_acumulado_s:.3f}s vs {accumulated:.3f}s)."
            )

    try:
        audited_steps = calculate_accumulated_times(list(analysis.microetapas))
        summary = calculate_time_summary(audited_steps, analysis.metadata.takt_time_s)
        if abs(summary.total_s - analysis.resumo_tempos.total_s) > 0.2:
            alerts.append(
                f"Resumo total incoerente ({analysis.resumo_tempos.total_s:.3f}s vs "
                f"{summary.total_s:.3f}s auditado)."
            )
        for label, current, audited in (
            ("AV", analysis.resumo_tempos.av_s, summary.av_s),
            ("NAV", analysis.resumo_tempos.nav_s, summary.nav_s),
            ("D", analysis.resumo_tempos.d_s, summary.d_s),
        ):
            if abs(current - audited) > 0.2:
                alerts.append(
                    f"Total {label} incoerente ({current:.3f}s vs {audited:.3f}s auditado)."
                )
    except ValueError as exc:
        alerts.append(f"Auditoria de resumo de tempo falhou: {exc}")

    alerts.extend(detect_time_gaps(analysis))
    alerts.extend(detect_time_overlaps(analysis))
    return alerts


def recalculate_microstep_times(analysis: OperationalAnalysis) -> OperationalAnalysis:
    """Recalculate duration and formatted timestamps from start/end seconds."""

    ordered_steps = sorted(analysis.microetapas, key=lambda item: (item.inicio_s, item.fim_s, item.numero))
    recalculated = calculate_accumulated_times(ordered_steps)
    summary = calculate_av_nav_d_summary_from_steps(recalculated, analysis.metadata.takt_time_s)
    return OperationalAnalysis.model_validate(
        analysis.model_dump()
        | {
            "microetapas": [step.model_dump() for step in recalculated],
            "resumo_tempos": summary.model_dump(),
        }
    )


def validate_time_columns_for_export(analysis: OperationalAnalysis) -> list[str]:
    """Validate exported time semantics: G=element, H=progressive accumulated."""

    alerts: list[str] = []
    accumulated = 0.0
    for step in sorted(analysis.microetapas, key=lambda item: (item.numero, item.inicio_s)):
        try:
            element = calculate_element_time(step.inicio_s, step.fim_s)
        except ValueError as exc:
            alerts.append(f"Microetapa {step.numero}: {exc}")
            continue
        accumulated = round(accumulated + element, 3)
        if abs(step.duracao_s - element) > 0.01:
            alerts.append(f"Microetapa {step.numero}: tempo do elemento nao auditado.")
        if step.tempo_acumulado_s is None or abs(step.tempo_acumulado_s - accumulated) > 0.01:
            alerts.append(f"Microetapa {step.numero}: tempo acumulado nao e soma progressiva.")
        if abs(accumulated - step.fim_s) <= 0.01 and step.inicio_s > 0:
            alerts.append(f"Microetapa {step.numero}: acumulado parece timestamp fim_s.")

    summary = calculate_time_summary(analysis.microetapas, analysis.metadata.takt_time_s)
    if abs(summary.total_s - (summary.av_s + summary.nav_s + summary.d_s)) > 0.01:
        alerts.append("Resumo AV/NAV/D nao fecha com total.")
    return alerts


def validate_timeline_coverage(
    analysis: OperationalAnalysis,
    video_metadata: VideoMetadata,
) -> list[str]:
    """Return alerts for incomplete or incoherent coverage."""

    alerts: list[str] = []
    alerts.extend(detect_time_gaps(analysis))
    alerts.extend(detect_time_overlaps(analysis))

    if not analysis.microetapas:
        alerts.append("Analise sem microetapas; cobertura temporal inexistente.")
        return alerts

    first_start = min(step.inicio_s for step in analysis.microetapas)
    last_end = max(step.fim_s for step in analysis.microetapas)
    duration_s = video_metadata.duration_s
    if duration_s > 0:
        if first_start > GAP_THRESHOLD_S:
            alerts.append(f"Inicio util da analise comeca em {first_start:.2f}s; validar trecho inicial do video.")
        tail_gap = duration_s - last_end
        if tail_gap > GAP_THRESHOLD_S:
            alerts.append(f"Trecho final de {tail_gap:.2f}s sem microetapa consolidada; validar cobertura.")
        covered_s = sum(step.duracao_s for step in analysis.microetapas)
        if covered_s < duration_s * 0.70:
            alerts.append(
                f"Soma de microetapas ({covered_s:.2f}s) muito abaixo da duracao do video ({duration_s:.2f}s)."
            )

    return alerts


def detect_time_gaps(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    steps = sorted(analysis.microetapas, key=lambda item: (item.inicio_s, item.fim_s))
    for previous, current in zip(steps, steps[1:]):
        gap_s = current.inicio_s - previous.fim_s
        if gap_s > GAP_THRESHOLD_S:
            alerts.append(
                f"Buraco temporal de {gap_s:.2f}s entre microetapas {previous.numero} e {current.numero}."
            )
    return alerts


def detect_time_overlaps(analysis: OperationalAnalysis) -> list[str]:
    alerts: list[str] = []
    steps = sorted(analysis.microetapas, key=lambda item: (item.inicio_s, item.fim_s))
    for previous, current in zip(steps, steps[1:]):
        overlap_s = previous.fim_s - current.inicio_s
        if overlap_s > OVERLAP_THRESHOLD_S:
            alerts.append(
                f"Sobreposicao temporal de {overlap_s:.2f}s entre microetapas {previous.numero} e {current.numero}."
            )
    return alerts


def calculate_accumulated_time(analysis_or_steps):
    """Calculate accumulated time for an analysis or for a list of MicroStep."""

    if isinstance(analysis_or_steps, OperationalAnalysis):
        microsteps = calculate_accumulated_times(list(analysis_or_steps.microetapas))
        return OperationalAnalysis.model_validate(
            analysis_or_steps.model_dump() | {"microetapas": [step.model_dump() for step in microsteps]}
        )
    return calculate_accumulated_times(list(analysis_or_steps))


def calculate_av_nav_d_summary(analysis_or_steps):
    if isinstance(analysis_or_steps, OperationalAnalysis):
        summary = calculate_time_summary(analysis_or_steps.microetapas, analysis_or_steps.metadata.takt_time_s)
        return OperationalAnalysis.model_validate(
            analysis_or_steps.model_dump() | {"resumo_tempos": summary.model_dump()}
        )
    return calculate_time_summary(list(analysis_or_steps))


def calculate_av_nav_d_summary_from_steps(
    microsteps: list[MicroStep],
    takt_time_s: float | None = None,
) -> TimeSummary:
    return calculate_time_summary(microsteps, takt_time_s)
