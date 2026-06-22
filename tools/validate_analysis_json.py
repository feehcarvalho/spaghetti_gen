"""Valida um JSON de analise operacional contra os schemas da aplicacao."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.schemas.analysis import OperationalAnalysis, TimeSummary
from app.utils.time_utils import calculate_time_summary


SUMMARY_FIELDS = (
    "av_s",
    "nav_s",
    "d_s",
    "total_s",
    "av_percent",
    "nav_percent",
    "d_percent",
    "folga_vs_takt_s",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Valida um arquivo JSON de analise operacional SPS."
    )
    parser.add_argument("json_path", type=Path, help="Caminho do arquivo JSON de analise.")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("O JSON raiz deve ser um objeto.")

    return data


def values_differ(left: float | None, right: float | None, tolerance: float = 0.1) -> bool:
    if left is None or right is None:
        return left != right
    return abs(left - right) > tolerance


def find_summary_differences(
    informed: TimeSummary,
    calculated: TimeSummary,
) -> list[tuple[str, float | None, float | None]]:
    differences = []
    for field in SUMMARY_FIELDS:
        informed_value = getattr(informed, field)
        calculated_value = getattr(calculated, field)
        if values_differ(informed_value, calculated_value):
            differences.append((field, informed_value, calculated_value))
    return differences


def count_classifications(analysis: OperationalAnalysis) -> dict[str, int]:
    counts = {"AV": 0, "NAV": 0, "D": 0}
    for step in analysis.microetapas:
        counts[step.classificacao] += 1
    return counts


def format_seconds(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}s"


def format_meters(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}m"


def print_summary(
    path: Path,
    analysis: OperationalAnalysis,
    calculated_summary: TimeSummary,
    differences: Iterable[tuple[str, float | None, float | None]],
) -> None:
    differences = list(differences)
    counts = count_classifications(analysis)
    spaghetti = analysis.spaghetti

    print("JSON validado com sucesso")
    print(f"Arquivo: {path}")
    print()
    print("Contexto")
    print(f"- Empresa/departamento: {analysis.metadata.empresa} / {analysis.metadata.departamento}")
    print(f"- Posto: {analysis.metadata.posto}")
    print(f"- Processo: {analysis.metadata.processo}")
    print(f"- Data da analise: {analysis.metadata.data_analise}")
    print(f"- Takt: {format_seconds(analysis.metadata.takt_time_s)}")
    print()
    print("Microetapas")
    print(f"- Total: {len(analysis.microetapas)}")
    print(f"- AV/NAV/D: {counts['AV']} / {counts['NAV']} / {counts['D']}")
    print()
    print("Resumo de tempos recalculado")
    print(
        "- AV: "
        f"{calculated_summary.av_s:.1f}s ({calculated_summary.av_percent:.1f}%) | "
        f"NAV: {calculated_summary.nav_s:.1f}s ({calculated_summary.nav_percent:.1f}%) | "
        f"D: {calculated_summary.d_s:.1f}s ({calculated_summary.d_percent:.1f}%)"
    )
    print(f"- Total: {calculated_summary.total_s:.1f}s")
    print(f"- Folga vs takt: {format_seconds(calculated_summary.folga_vs_takt_s)}")
    print()

    if differences:
        print("AVISO: resumo_tempos do JSON diverge do calculo")
        for field, informed_value, calculated_value in differences:
            print(f"- {field}: JSON={informed_value} | calculado={calculated_value}")
        print()
    else:
        print("Resumo do JSON confere com o calculo.")
        print()

    if spaghetti is not None:
        print("Spaghetti")
        print(f"- Pontos: {len(spaghetti.pontos)}")
        print(f"- Movimentos: {len(spaghetti.movimentos)}")
        print(f"- Passos estimados: {spaghetti.total_passos_estimados}")
        print(f"- Distancia total: {format_meters(spaghetti.distancia_total_m)}")
        print()

    print("Melhorias")
    print(f"- Sugestoes: {len(analysis.melhorias)}")
    for item in analysis.melhorias:
        etapa = item.microetapa_numero if item.microetapa_numero is not None else "n/a"
        print(f"- Etapa {etapa}: {item.prioridade} | {item.tipo_desperdicio}")

    if analysis.alertas_validacao:
        print()
        print("Alertas")
        for alert in analysis.alertas_validacao:
            print(f"- {alert}")


def main() -> int:
    args = parse_args()
    path = args.json_path

    try:
        data = load_json(path)
        analysis = OperationalAnalysis.model_validate(normalize_analysis_payload_for_current_schema(data))
        calculated_summary = calculate_time_summary(
            analysis.microetapas,
            analysis.metadata.takt_time_s,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError, ValidationError) as exc:
        print(f"Erro ao validar JSON: {exc}", file=sys.stderr)
        return 1

    differences = find_summary_differences(analysis.resumo_tempos, calculated_summary)
    print_summary(path, analysis, calculated_summary, differences)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
