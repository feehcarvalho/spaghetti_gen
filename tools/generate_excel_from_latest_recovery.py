"""Generate a Scania Excel workbook from the newest preserved recovery JSON."""

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
from app.excel.template_writer import export_analysis_with_warnings  # noqa: E402
from tools.generate_excel_from_recovery import (  # noqa: E402
    DEFAULT_TEMPLATE,
    OUTPUT_DIR,
    load_recovery_analysis,
    resolve_template,
)

RECOVERY_DIR = REPO_ROOT / "data" / "outputs" / "recovery"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera Excel a partir do JSON mais recente em data/outputs/recovery/."
    )
    parser.add_argument("--recovery-dir", type=Path, default=RECOVERY_DIR, help="Diretorio com JSONs preservados.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE, help="Template .xlsx Scania.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Diretorio de saida.")
    return parser.parse_args()


def find_latest_recovery_json(recovery_dir: Path) -> Path:
    directory = recovery_dir if recovery_dir.is_absolute() else REPO_ROOT / recovery_dir
    candidates = [path for path in directory.glob("*.json") if path.is_file()]
    if not candidates:
        raise FileNotFoundError(f"Nenhum JSON preservado encontrado em: {directory}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def main() -> int:
    args = parse_args()
    try:
        recovery_path = find_latest_recovery_json(args.recovery_dir)
        template_path = resolve_template(args.template)
        analysis = load_recovery_analysis(recovery_path)
        gate = validate_analysis_quality(analysis, None, None)
        prepared = prepare_analysis_for_export(analysis)

        output_dir = args.output_dir if args.output_dir.is_absolute() else REPO_ROOT / args.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{recovery_path.stem}_{stamp}.xlsx"
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
        print(f"Erro ao gerar Excel do ultimo recovery: {exc}", file=sys.stderr)
        return 1

    print(f"Recovery JSON: {recovery_path}")
    print(f"Excel gerado: {excel_path}")
    print(f"JSON gerado: {json_path}")
    print(f"Alertas preservados: {len(gate.alerts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
