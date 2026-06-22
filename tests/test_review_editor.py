"""Testes do editor de revisao humana."""

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.analysis import OperationalAnalysis
from app.ui.review_editor import analysis_to_dataframe, dataframe_to_analysis


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_JSON = REPO_ROOT / "data" / "outputs" / "sample_analysis_pmgs_p1.json"


def load_sample_analysis() -> OperationalAnalysis:
    data = json.loads(SAMPLE_JSON.read_text(encoding="utf-8"))
    return OperationalAnalysis.model_validate(data)


def as_records(df) -> list[dict]:
    if hasattr(df, "to_dict"):
        return df.to_dict(orient="records")
    return [dict(row) for row in df]


def test_changing_classification_recalculates_summary():
    analysis = load_sample_analysis()
    rows = as_records(analysis_to_dataframe(analysis))
    first_duration = rows[0]["duracao_s"]
    rows[0]["classificacao"] = "AV"

    reviewed = dataframe_to_analysis(rows, analysis)

    assert reviewed.resumo_tempos.av_s == analysis.resumo_tempos.av_s + first_duration
    assert reviewed.resumo_tempos.nav_s == analysis.resumo_tempos.nav_s - first_duration
    assert any("classificacao da microetapa 1" in alert for alert in reviewed.alertas_validacao)
    OperationalAnalysis.model_validate(reviewed.model_dump())


def test_changing_duration_recalculates_summary_and_keeps_valid_json():
    analysis = load_sample_analysis()
    rows = as_records(analysis_to_dataframe(analysis))
    rows[0]["duracao_s"] = rows[0]["duracao_s"] + 2.0

    reviewed = dataframe_to_analysis(rows, analysis)

    assert reviewed.microetapas[0].duracao_s == analysis.microetapas[0].duracao_s + 2.0
    assert reviewed.microetapas[0].fim_s == reviewed.microetapas[0].inicio_s + reviewed.microetapas[0].duracao_s
    assert reviewed.resumo_tempos.total_s == analysis.resumo_tempos.total_s + 2.0
    assert any("duracao da microetapa 1" in alert for alert in reviewed.alertas_validacao)
    assert any("diverge do ciclo observado" in alert for alert in reviewed.alertas_validacao)
    OperationalAnalysis.model_validate(reviewed.model_dump())


def test_d_step_without_improvement_adds_alert():
    analysis = load_sample_analysis().model_copy(update={"melhorias": []})
    rows = as_records(analysis_to_dataframe(analysis))

    reviewed = dataframe_to_analysis(rows, analysis)

    assert any("classificada como D sem sugestao de melhoria" in alert for alert in reviewed.alertas_validacao)
    OperationalAnalysis.model_validate(reviewed.model_dump())
