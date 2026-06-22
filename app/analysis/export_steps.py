"""Normalized microstep rows shared by Excel exports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.analysis.activity_text import get_microstep_activity_text
from app.schemas.analysis import MicroStep, OperationalAnalysis


@dataclass(frozen=True)
class NormalizedExportStep:
    sequence: int
    microstep: MicroStep
    classification: Literal["AV", "NAV", "D"]
    activity: str
    duration_s: float


def build_normalized_export_steps(analysis: OperationalAnalysis) -> list[NormalizedExportStep]:
    """Return non-empty microsteps in original order for all Excel exports."""

    rows: list[NormalizedExportStep] = []
    for step in analysis.microetapas:
        activity = get_microstep_activity_text(step).strip()
        if not activity:
            continue
        rows.append(
            NormalizedExportStep(
                sequence=len(rows) + 1,
                microstep=step,
                classification=step.classificacao,
                activity=activity,
                duration_s=float(step.duracao_s),
            )
        )
    return rows
