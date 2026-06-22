"""Validate OpenAI vision with one image before running a large video."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.ai.openai_structured import OpenAIStructuredRunner
from app.video.frame_extractor import ExtractedFrame


class SmallVisionCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    descricao_imagem: str
    objetos_visiveis: list[str] = Field(default_factory=list)
    confianca: float = Field(..., ge=0, le=1)
    limitacoes: list[str] = Field(default_factory=list)


def main() -> None:
    parser = argparse.ArgumentParser(description="Teste pequeno de visao OpenAI com 1 imagem.")
    parser.add_argument("image_path", type=Path, help="Caminho da imagem JPEG/PNG.")
    parser.add_argument("--detail", default="low", choices=["low", "auto", "high"])
    args = parser.parse_args()

    if not args.image_path.exists():
        raise FileNotFoundError(args.image_path)

    frame = ExtractedFrame(
        index=1,
        timestamp_s=0.0,
        timestamp_formatado="00:00",
        path=str(args.image_path),
        width=0,
        height=0,
    )
    runner = OpenAIStructuredRunner()
    result = runner.request_model(
        prompt=(
            "Descreva objetivamente a imagem industrial recebida. "
            "Nao invente objetos nao visiveis. Retorne JSON."
        ),
        frames=[frame],
        response_model=SmallVisionCheck,
        schema_name="small_vision_check",
        image_detail=args.detail,
    )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
