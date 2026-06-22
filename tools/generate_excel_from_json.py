"""Gera uma planilha Excel preenchida a partir de um JSON OperationalAnalysis."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analysis.schema_compat import normalize_analysis_payload_for_current_schema
from app.excel.template_writer import write_analysis_to_template
from app.schemas.analysis import OperationalAnalysis


DEFAULT_TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
FALLBACK_TEMPLATE = REPO_ROOT / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preenche uma copia do template Excel SPS a partir de JSON validado."
    )
    parser.add_argument("analysis_json", type=Path, help="Caminho do JSON OperationalAnalysis.")
    parser.add_argument("template_path", type=Path, help="Caminho do template .xlsx.")
    parser.add_argument("output_path", type=Path, help="Caminho do .xlsx gerado.")
    parser.add_argument(
        "--fill-standard",
        action="store_true",
        help="Preenche tambem as abas Standard existentes com as microetapas.",
    )
    parser.add_argument(
        "--standard-consolidado",
        action="store_true",
        help="Gera uma primeira aba STANDARD_CONSOLIDADO com todas as microetapas em sequencia.",
    )
    parser.add_argument(
        "--insert-charts",
        action="store_true",
        help="Gera e insere o grafico de balanceamento AV/NAV/D na copia do template.",
    )
    parser.add_argument(
        "--insert-spaghetti",
        action="store_true",
        help="Gera e insere o mapa de espaguete na copia do template.",
    )
    parser.add_argument(
        "--layout",
        type=Path,
        default=None,
        help="Caminho do layout JSON usado pelo mapa de espaguete.",
    )
    return parser.parse_args()


def resolve_template_path(template_path: Path) -> tuple[Path, str | None]:
    requested = template_path if template_path.is_absolute() else REPO_ROOT / template_path

    if requested.exists():
        return requested, None

    if requested == DEFAULT_TEMPLATE and FALLBACK_TEMPLATE.exists():
        return FALLBACK_TEMPLATE, (
            f"Template {DEFAULT_TEMPLATE.relative_to(REPO_ROOT)} nao encontrado; "
            f"usando fallback {FALLBACK_TEMPLATE.relative_to(REPO_ROOT)}."
        )

    raise FileNotFoundError(f"Template nao encontrado: {template_path}")


def load_analysis(path: Path) -> OperationalAnalysis:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return OperationalAnalysis.model_validate(normalize_analysis_payload_for_current_schema(data))


def main() -> int:
    args = parse_args()

    try:
        template_path, warning = resolve_template_path(args.template_path)
        analysis = load_analysis(args.analysis_json)
        output_path = write_analysis_to_template(
            analysis=analysis,
            template_path=str(template_path),
            output_path=str(args.output_path),
            fill_standard=args.fill_standard,
            standard_export_mode="standard_consolidado" if args.standard_consolidado else "standard_legacy",
            insert_charts=args.insert_charts,
            insert_spaghetti=args.insert_spaghetti,
            layout_path=str(args.layout) if args.layout is not None else None,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"Erro ao gerar Excel: {exc}", file=sys.stderr)
        return 1

    if warning:
        print(f"Aviso: {warning}")
    print(f"Excel gerado: {output_path}")
    print(f"Posto: {analysis.metadata.posto}")
    print(f"Microetapas: {len(analysis.microetapas)}")
    print(f"Melhorias: {len(analysis.melhorias)}")
    print(f"Standard preenchido: {'sim' if args.fill_standard else 'nao'}")
    print(f"Grafico inserido: {'sim' if args.insert_charts else 'nao'}")
    print(f"Spaghetti inserido: {'sim' if args.insert_spaghetti else 'nao'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
