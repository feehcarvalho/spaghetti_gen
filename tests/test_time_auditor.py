from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.analysis.time_auditor import (
    calculate_accumulated_times,
    calculate_av_nav_d_totals,
    calculate_element_time,
    recalculate_microstep_times,
    validate_time_consistency,
)
from app.schemas.analysis import OperationalAnalysis


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = REPO_ROOT / "data" / "outputs" / "sample_analysis_pmgs_p1.json"


def load_sample_analysis() -> OperationalAnalysis:
    return OperationalAnalysis.model_validate(json.loads(SAMPLE_JSON.read_text(encoding="utf-8")))


def test_element_time_is_end_minus_start():
    assert calculate_element_time(10.2, 14.8) == 4.6


def test_accumulated_time_sums_progressively():
    analysis = load_sample_analysis()
    steps = calculate_accumulated_times(analysis.microetapas[:3])

    assert steps[0].duracao_s == pytest.approx(steps[0].fim_s - steps[0].inicio_s)
    assert steps[1].tempo_acumulado_s == pytest.approx(steps[0].duracao_s + steps[1].duracao_s)
    assert steps[2].tempo_acumulado_s == pytest.approx(sum(step.duracao_s for step in steps[:3]))


def test_av_nav_d_totals_sum_to_total():
    analysis = recalculate_microstep_times(load_sample_analysis())
    summary = calculate_av_nav_d_totals(analysis.microetapas)

    assert summary.total_s == pytest.approx(summary.av_s + summary.nav_s + summary.d_s)
    assert summary.total_s == pytest.approx(sum(step.duracao_s for step in analysis.microetapas))


def test_negative_or_inverted_time_blocks():
    with pytest.raises(ValueError):
        calculate_element_time(5.0, 4.0)

    with pytest.raises(ValueError):
        calculate_element_time(-1.0, 4.0)


def test_incoherent_duration_is_detected_and_recalculated():
    analysis = load_sample_analysis()
    bad_step = analysis.microetapas[0].model_copy(update={"duracao_s": 99.0})
    bad_analysis = analysis.model_copy(update={"microetapas": [bad_step, *analysis.microetapas[1:]]})

    alerts = validate_time_consistency(bad_analysis)
    corrected = recalculate_microstep_times(bad_analysis)

    assert any("duracao_s" in alert for alert in alerts)
    assert corrected.microetapas[0].duracao_s == pytest.approx(
        corrected.microetapas[0].fim_s - corrected.microetapas[0].inicio_s
    )


def test_final_accumulated_matches_total():
    analysis = recalculate_microstep_times(load_sample_analysis())

    assert analysis.microetapas[-1].tempo_acumulado_s == pytest.approx(analysis.resumo_tempos.total_s)
    assert not [
        alert for alert in validate_time_consistency(analysis) if "incoerente" in alert.casefold()
    ]
