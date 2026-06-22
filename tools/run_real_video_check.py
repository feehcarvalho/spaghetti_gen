"""Run a real OpenAI SPS analysis for one video and persist audit artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.analysis.quality_gate import validate_analysis_quality
from app.excel.template_writer import write_analysis_to_template
from app.main import run_analysis_only
from app.schemas.analysis import AnalysisMetadata
from app.video.video_metadata import get_video_metadata


DEFAULT_TEMPLATE = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description="Executa teste real de video com OpenAI e salva artefatos.")
    parser.add_argument("video_path")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "data" / "outputs" / "real_video_checks"))
    parser.add_argument("--posto", default="PMGS.P1")
    parser.add_argument("--processo", default="Analise operacional PMGS")
    parser.add_argument("--departamento", default="PMGS")
    parser.add_argument("--responsavel", default="Teste OpenAI")
    parser.add_argument("--data-analise", default=date.today().isoformat())
    parser.add_argument("--takt", type=float, default=None)
    parser.add_argument("--skip-excel", action="store_true")
    args = parser.parse_args()

    video_path = Path(args.video_path)
    if not video_path.exists():
        raise SystemExit(f"Video nao encontrado: {video_path}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"analise_real_{args.posto.replace('.', '_')}_{date.today().isoformat()}"
    json_path = output_dir / f"{stem}.json"
    excel_path = output_dir / f"{stem}.xlsx"

    metadata = AnalysisMetadata(
        departamento=args.departamento,
        posto=args.posto,
        processo=args.processo,
        responsavel=args.responsavel,
        data_analise=args.data_analise,
        takt_time_s=args.takt,
        fonte_video=str(video_path),
    )

    progress_events: list[dict] = []

    def progress(stage: str, payload: dict) -> None:
        event = {"stage": stage, "payload": payload}
        progress_events.append(event)
        if stage == "window":
            print(f"janela {payload.get('current')}/{payload.get('total')} frames={payload.get('frames')}", flush=True)
        elif stage in {"knowledge", "metadata", "timeline", "windows", "overview", "reanalyze", "consolidate"}:
            print(f"{stage}: {payload}", flush=True)

    analysis = run_analysis_only(
        video_path=str(video_path),
        output_path=str(excel_path),
        metadata=metadata,
        knowledge_root=str(REPO_ROOT / "data" / "knowledge_raw"),
        provider_name="openai",
        quality_mode="maxima",
        progress_callback=progress,
    )

    json_path.write_text(
        json.dumps(analysis.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    video_metadata = get_video_metadata(str(video_path))
    gate = validate_analysis_quality(analysis, video_metadata, None)
    gate_path = output_dir / f"{stem}_quality_gate.json"
    gate_path.write_text(
        json.dumps(gate.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    progress_path = output_dir / f"{stem}_progress.json"
    progress_path.write_text(
        json.dumps(progress_events, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"JSON: {json_path}", flush=True)
    print(f"QUALITY_GATE: {gate_path}", flush=True)
    print(f"PROGRESS: {progress_path}", flush=True)
    print(f"MICROETAPAS: {len(analysis.microetapas)}", flush=True)
    print(
        f"TEMPOS: AV={analysis.resumo_tempos.av_s}s NAV={analysis.resumo_tempos.nav_s}s D={analysis.resumo_tempos.d_s}s TOTAL={analysis.resumo_tempos.total_s}s",
        flush=True,
    )
    print(f"QUALITY_GATE_PASSOU: {gate.passed}", flush=True)
    if gate.critical_errors:
        print("ERROS_CRITICOS: " + " | ".join(gate.critical_errors), flush=True)
    if gate.warnings:
        print("ALERTAS: " + " | ".join(gate.warnings[:10]), flush=True)

    if not args.skip_excel and gate.can_export:
        generated = write_analysis_to_template(
            analysis=analysis,
            template_path=str(DEFAULT_TEMPLATE),
            output_path=str(excel_path),
            fill_standard=True,
        )
        print(f"EXCEL: {generated}", flush=True)
    elif not gate.can_export:
        print("EXCEL: bloqueado por erro tecnico fatal", flush=True)

    return 0 if gate.can_export else 2


if __name__ == "__main__":
    raise SystemExit(main())
