"""Overview phase for real SPS video analysis."""

from __future__ import annotations

import json
import os

from pydantic import BaseModel, ConfigDict, Field

from app.ai.openai_structured import OpenAIStructuredRunner
from app.schemas.analysis import AnalysisMetadata
from app.video.frame_extractor import ExtractedFrame
from app.video.video_metadata import VideoMetadata


class VideoOverview(BaseModel):
    """High-level visual orientation for the subsequent window analysis."""

    model_config = ConfigDict(extra="forbid")

    processo_aparente: str
    elementos_visiveis: list[str] = Field(default_factory=list)
    ferramentas_visiveis: list[str] = Field(default_factory=list)
    produto_ou_conjunto_visivel: str | None = None
    inicio_ciclo_estimado_s: float | None = Field(default=None, ge=0)
    fim_ciclo_estimado_s: float | None = Field(default=None, ge=0)
    ciclo_completo_aparente: bool
    limitacoes_visuais: list[str] = Field(default_factory=list)
    confianca_geral: float = Field(..., ge=0, le=1)
    alertas: list[str] = Field(default_factory=list)


def analyze_video_overview(
    metadata: VideoMetadata,
    overview_frames: list[ExtractedFrame],
    user_metadata: AnalysisMetadata,
    context: str,
    *,
    runner: OpenAIStructuredRunner | None = None,
    image_detail: str | None = None,
) -> VideoOverview:
    """Ask OpenAI for video-level context without generating final microsteps."""

    runner = runner or OpenAIStructuredRunner()
    detail = image_detail or os.getenv("OPENAI_OVERVIEW_DETAIL") or os.getenv("OPENAI_IMAGE_DETAIL_OVERVIEW", "low")
    prompt = build_video_overview_prompt(metadata, overview_frames, user_metadata, context)
    return runner.request_model(
        prompt=prompt,
        frames=overview_frames,
        response_model=VideoOverview,
        schema_name="video_overview",
        image_detail=detail,
    )


def build_video_overview_prompt(
    metadata: VideoMetadata,
    overview_frames: list[ExtractedFrame],
    user_metadata: AnalysisMetadata,
    context: str,
) -> str:
    frames_text = "\n".join(
        f"- frame_index={frame.index}; timestamp_s={frame.timestamp_s:.3f}; "
        f"path={frame.path}; resolucao={frame.width}x{frame.height}"
        for frame in overview_frames
    ) or "- Nenhum frame de overview fornecido."

    return f"""
Voce e uma IA corporativa de apoio a engenharia de processos SPS/Lean Manufacturing.
Esta fase orienta a analise real do video inteiro sem gerar microetapas finais.

Tarefa desta fase:
- Analisar visualmente apenas os frames de overview.
- Identificar o processo aparente, objetos, ferramentas, produto/conjunto, operador/posto visiveis.
- Estimar inicio e fim provaveis do ciclo quando houver evidencia.
- Registrar limitacoes de camera, oclusoes, baixa resolucao e riscos da analise.
- Indicar se o video aparenta conter ciclo completo ou parcial.

Regras inegociaveis:
- Esta fase NAO gera microetapas finais.
- Nao assuma PMGS, Bluebox, VR ou qualquer processo como resposta padrao. Nao copie exemplos anteriores.
- Se algo nao estiver claro, escreva "nao conclusivo pelo video; requer validacao no gemba".
- Use "aparente" ou "provavel" quando depender de inferencia visual.
- Nao invente ferramenta, produto, padrao, etapa ou intencao sem evidencia.
- Retorne somente JSON aderente ao schema VideoOverview.

Metadados tecnicos do video:
{metadata.model_dump_json(indent=2)}

Metadados informados pelo usuario:
{user_metadata.model_dump_json(indent=2)}

Contexto SPS disponivel:
{context}

Frames de overview:
{frames_text}

Schema esperado:
{json.dumps(VideoOverview.model_json_schema(), ensure_ascii=False, indent=2)}
""".strip()
