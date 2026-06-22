"""CLI para extrair frames JPEG de um video."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.video.frame_extractor import extract_frames


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extrai frames JPEG de um video MP4 para analise por IA."
    )
    parser.add_argument("video_path", type=Path, help="Caminho do arquivo MP4.")
    parser.add_argument("output_dir", type=Path, help="Diretorio onde os frames serao salvos.")
    parser.add_argument("--fps", type=float, default=1.0, help="Taxa de amostragem de frames.")
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Quantidade maxima de frames extraidos.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        frames = extract_frames(
            video_path=str(args.video_path),
            output_dir=str(args.output_dir),
            fps=args.fps,
            max_frames=args.max_frames,
        )
    except ValueError as exc:
        print(f"Erro ao extrair frames: {exc}", file=sys.stderr)
        return 1

    print(f"Frames extraidos: {len(frames)}")
    print(f"Destino: {args.output_dir}")
    if frames:
        print(f"Primeiro frame: {frames[0].timestamp_formatado} -> {frames[0].path}")
        print(f"Ultimo frame: {frames[-1].timestamp_formatado} -> {frames[-1].path}")
        print(f"Resolucao: {frames[0].width}x{frames[0].height}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
