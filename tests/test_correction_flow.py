from pathlib import Path
from uuid import uuid4

from app.analysis.correction_flow import (
    append_correction_history,
    prepare_correction_rerun,
    save_correction_context_note,
)
from app.schemas.analysis import AnalysisMetadata, MicroStep, OperationalAnalysis, TimeSummary


def _runtime_dir() -> Path:
    path = Path("data/outputs/test_correction_runtime") / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sample_analysis() -> OperationalAnalysis:
    metadata = AnalysisMetadata(
        departamento="Engenharia",
        posto="5.2.6",
        processo="Montagem 8x2",
        responsavel="Teste",
        data_analise="2026-05-21",
    )
    step = MicroStep(
        numero=1,
        inicio_s=0.0,
        fim_s=1.0,
        duracao_s=1.0,
        inicio_formatado="00:00",
        fim_formatado="00:01",
        duracao_formatada="00:01",
        etapa_detalhada="Posicionar componente no conjunto.",
        classificacao="NAV",
        justificativa_tecnica="Necessario pelo metodo atual sem transformacao direta observavel.",
        evidencia_visual="Componente posicionado no conjunto.",
        confianca=0.9,
    )
    summary = TimeSummary(
        av_s=0.0,
        nav_s=1.0,
        d_s=0.0,
        total_s=1.0,
        av_percent=0.0,
        nav_percent=100.0,
        d_percent=0.0,
    )
    return OperationalAnalysis(metadata=metadata, microetapas=[step], resumo_tempos=summary)


def test_prepare_correction_rerun_versions_new_paths():
    previous = _runtime_dir() / "analise_x_v1.xlsx"
    previous.write_bytes(b"old")

    plan = prepare_correction_rerun(previous, "usar termo VR de pneu", history=[], login="admin", base_stem="analise_x")

    assert plan["output_path"].endswith(".xlsx")
    assert "_v2_corrigida_" in plan["output_path"]
    assert plan["json_path"].endswith(".json")
    assert str(previous) != plan["output_path"]


def test_append_correction_history_preserves_previous_version():
    previous_history = [{"new_json_path": "v1.json"}]

    updated = append_correction_history(
        previous_history,
        observation="corrigir nomenclatura",
        previous_excel_path="v1.xlsx",
        previous_json_path="v1.json",
        new_excel_path="v2.xlsx",
        new_json_path="v2.json",
    )

    assert len(previous_history) == 1
    assert len(updated) == 2
    assert updated[-1]["new_excel_path"] == "v2.xlsx"


def test_save_correction_context_note_contains_prompt_and_observation():
    output_dir = _runtime_dir()
    path = save_correction_context_note(
        _sample_analysis(),
        "Reescrever como padrão Scania.",
        login="admin",
        output_dir=output_dir,
    )

    text = path.read_text(encoding="utf-8")
    assert path.exists()
    assert "Você deve revisar a análise SPS anterior" in text
    assert "Reescrever como padrão Scania." in text
    assert "Análise SPS anterior" in text
