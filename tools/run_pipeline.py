"""CLI do pipeline principal de análise SPS."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.main import run_analysis_pipeline
from app.schemas.analysis import AnalysisMetadata


DEFAULT_TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
FALLBACK_TEMPLATE = REPO_ROOT / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Executa o pipeline IA SPS Scania.")
    parser.add_argument("--video", default=None, help="Caminho opcional do video MP4.")
    parser.add_argument("--template", required=True, type=Path, help="Caminho do template Excel.")
    parser.add_argument("--output", required=True, help="Caminho do Excel gerado.")
    parser.add_argument("--posto", required=True)
    parser.add_argument("--processo", required=True)
    parser.add_argument("--departamento", required=True)
    parser.add_argument("--responsavel", required=True)
    parser.add_argument("--data-analise", default=date.today().isoformat())
    parser.add_argument("--linha", default=None)
    parser.add_argument("--bloco", default=None)
    parser.add_argument("--takt", type=float, default=None)
    parser.add_argument("--ciclo-observado", type=float, default=None)
    parser.add_argument("--knowledge-root", default="data/knowledge_raw")
    parser.add_argument("--provider", choices=["mock", "openai"], default="mock")
    parser.add_argument("--fill-standard", action="store_true")
    parser.add_argument("--insert-charts", action="store_true")
    parser.add_argument("--insert-spaghetti", action="store_true")
    parser.add_argument("--layout", default=None, help="Caminho opcional do layout JSON do posto.")
    parser.add_argument("--fps", type=float, default=1.0)
    parser.add_argument("--max-frames", type=int, default=120)
    parser.add_argument("--window-seconds", type=int, default=None)
    parser.add_argument("--max-frames-per-window", type=int, default=None)
    parser.add_argument("--detail-window", choices=["low", "auto", "high"], default=None)
    parser.add_argument("--no-reprocess-low-confidence", action="store_true")
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


def main() -> int:
    args = parse_args()

    try:
        template_path, warning = resolve_template_path(args.template)
        metadata = AnalysisMetadata(
            departamento=args.departamento,
            linha=args.linha,
            bloco=args.bloco,
            posto=args.posto,
            processo=args.processo,
            responsavel=args.responsavel,
            data_analise=args.data_analise,
            takt_time_s=args.takt,
            ciclo_observado_s=args.ciclo_observado,
            fonte_video=args.video,
        )
        output_path = run_analysis_pipeline(
            video_path=args.video,
            template_path=str(template_path),
            output_path=args.output,
            metadata=metadata,
            knowledge_root=args.knowledge_root,
            provider_name=args.provider,
            fill_standard=args.fill_standard,
            insert_charts=args.insert_charts,
            insert_spaghetti=args.insert_spaghetti,
            layout_path=args.layout,
            fps=args.fps,
            max_frames=args.max_frames,
            window_seconds=args.window_seconds,
            max_frames_per_window=args.max_frames_per_window,
            reprocess_low_confidence=not args.no_reprocess_low_confidence,
            detail_window=args.detail_window,
        )
    except Exception as exc:
        print(f"Erro no pipeline: {exc}", file=sys.stderr)
        return 1

    if warning:
        print(f"Aviso: {warning}")
    print(f"Excel gerado: {output_path}")
    print(f"JSON gerado: {Path(output_path).with_suffix('.json')}")
    print(f"Provider: {args.provider}")
    print(f"Standard preenchido: {'sim' if args.fill_standard else 'nao'}")
    print(f"Grafico inserido: {'sim' if args.insert_charts else 'nao'}")
    print(f"Spaghetti inserido: {'sim' if args.insert_spaghetti else 'nao'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
