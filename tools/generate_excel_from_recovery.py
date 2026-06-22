"""Generate a Scania Excel workbook from a preserved recovery JSON."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analysis.export_preparer import prepare_analysis_for_export  # noqa: E402
from app.analysis.quality_gate import validate_analysis_quality  # noqa: E402
from app.analysis.schema_compat import normalize_analysis_payload_for_current_schema  # noqa: E402
from app.excel.template_writer import export_analysis_with_warnings  # noqa: E402
from app.schemas.analysis import OperationalAnalysis  # noqa: E402


DEFAULT_TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
FALLBACK_TEMPLATE = REPO_ROOT / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
OUTPUT_DIR = REPO_ROOT / "data" / "outputs" / "recovery_excel"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera Excel a partir de data/outputs/recovery/analise_preservada_*.json."
    )
    parser.add_argument("recovery_json", type=Path, help="JSON preservado pela UI.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Template .xlsx Scania.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Diretorio de saida.")
    return parser.parse_args()


def resolve_template(path: Path) -> Path:
    requested = path if path.is_absolute() else REPO_ROOT / path
    if requested.exists():
        return requested
    if requested == DEFAULT_TEMPLATE and FALLBACK_TEMPLATE.exists():
        return FALLBACK_TEMPLATE
    raise FileNotFoundError(f"Template nao encontrado: {path}")


def load_recovery_analysis(path: Path) -> OperationalAnalysis:
    payload = json.loads(path.read_text(encoding="utf-8"))
    analysis_payload = payload.get("analysis", payload) if isinstance(payload, dict) else payload
    return OperationalAnalysis.model_validate(
        normalize_analysis_payload_for_current_schema(analysis_payload)
    )


def main() -> int:
    args = parse_args()
    try:
        recovery_path = args.recovery_json if args.recovery_json.is_absolute() else REPO_ROOT / args.recovery_json
        template_path = resolve_template(args.template)
        analysis = load_recovery_analysis(recovery_path)
        gate = validate_analysis_quality(analysis, None, None)
        prepared = prepare_analysis_for_export(analysis)

        args.output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = args.output_dir / f"{recovery_path.stem}_{stamp}.xlsx"
        json_path = output_path.with_suffix(".json")

        excel_path = export_analysis_with_warnings(
            analysis=prepared,
            template_path=str(template_path),
            output_path=str(output_path),
            quality_alerts=gate.alerts,
            force_export=True,
            fill_standard=True,
            standard_export_mode="standard_consolidado",
        )
        prepared = prepare_analysis_for_export(prepared)
        json_path.write_text(
            json.dumps(prepared.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except (FileNotFoundError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"Erro ao gerar Excel de recovery: {exc}", file=sys.stderr)
        return 1

    print(f"Excel gerado: {excel_path}")
    print(f"JSON gerado: {json_path}")
    print(f"Alertas preservados: {len(gate.alerts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
