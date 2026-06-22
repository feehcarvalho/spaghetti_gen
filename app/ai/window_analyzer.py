"""Window-level SPS analysis phase."""

from __future__ import annotations

import json
import os
from statistics import mean

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.ai.openai_call_manager import call_openai_with_retry_and_split
from app.ai.openai_structured import OpenAIStructuredRunner, OpenAITimeoutError
from app.ai.video_overview import VideoOverview
from app.schemas.analysis import AnalysisMetadata
from app.video.frame_extractor import ExtractedFrame
from app.video.segmentation import VideoWindow


class WindowMicroStep(BaseModel):
    """Microstep observed inside one temporal window."""

    model_config = ConfigDict(extra="forbid")

    numero_local: int = Field(..., ge=1)
    inicio_s: float = Field(..., ge=0)
    fim_s: float = Field(..., ge=0)
    duracao_s: float = Field(..., ge=0)
    descricao_tecnica_detalhada: str
    instrucao_padrao: str | None = None
    evidencia_observavel: str | None = None
    interpretacao_de_processo: str | None = None
    classificacao: str = Field(pattern="^(AV|NAV|D)$")
    justificativa_tecnica: str
    evidencia_visual: str
    tipo_movimento: str | None = None
    tipo_desperdicio: str | None = None
    local_inicio: str | None = None
    local_fim: str | None = None
    ferramenta_observacao: str | None = None
    memoria_utilizada: list[str] = Field(default_factory=list)
    confianca: float = Field(..., ge=0, le=1)
    baixa_confianca_motivo: str | None = None
    requer_validacao_gemba: bool = False

    @model_validator(mode="after")
    def validate_window_step(self) -> "WindowMicroStep":
        if self.fim_s < self.inicio_s:
            raise ValueError("fim_s nao pode ser menor que inicio_s")
        expected_duration = self.fim_s - self.inicio_s
        if abs(self.duracao_s - expected_duration) > 0.2:
            raise ValueError("duracao_s deve ser coerente com fim_s - inicio_s")
        if self.confianca < 0.7:
            self.requer_validacao_gemba = True
            if not self.baixa_confianca_motivo:
                self.baixa_confianca_motivo = (
                    "Aviso: confiança abaixo do limite recomendado. Validar esta etapa no gemba antes de decisão definitiva."
                )
        return self


class WindowAnalysis(BaseModel):
    """Structured result for one analyzed video window."""

    model_config = ConfigDict(extra="forbid")

    window_index: int = Field(..., ge=1)
    start_s: float = Field(..., ge=0)
    end_s: float = Field(..., ge=0)
    microetapas: list[WindowMicroStep] = Field(default_factory=list)
    explicacao_sem_microetapas: str | None = None
    confianca_media: float = Field(..., ge=0, le=1)
    alertas: list[str] = Field(default_factory=list)
    falhou: bool = False
    erro: str | None = None

    @model_validator(mode="after")
    def validate_empty_window_explanation(self) -> "WindowAnalysis":
        if not self.microetapas and not self.explicacao_sem_microetapas and not self.falhou:
            raise ValueError("janela sem microetapas deve explicar o motivo")
        if self.end_s < self.start_s:
            raise ValueError("end_s nao pode ser menor que start_s")
        return self


def analyze_window_sps(
    window: VideoWindow,
    overview: VideoOverview,
    context: str,
    rules_av_nav_d: str,
    metadata: AnalysisMetadata,
    *,
    runner: OpenAIStructuredRunner | None = None,
    image_detail: str | None = None,
    timeout_s: int | None = None,
) -> WindowAnalysis:
    """Analyze one temporal window and return only observed microsteps."""

    runner = runner or OpenAIStructuredRunner()
    detail = image_detail or os.getenv("OPENAI_IMAGE_DETAIL_WINDOW", "auto")
    prompt = build_window_analysis_prompt(window, overview, context, rules_av_nav_d, metadata)
    analysis = runner.request_model(
        prompt=prompt,
        frames=window.frames,
        response_model=WindowAnalysis,
        schema_name="window_analysis",
        image_detail=detail,
        timeout_s=timeout_s,
    )
    return analysis.model_copy(
        update={
            "window_index": window.index,
            "start_s": window.start_s,
            "end_s": window.end_s,
        }
    )


def analyze_window_with_timeout_recovery(
    window: VideoWindow,
    overview: VideoOverview,
    context: str,
    rules_av_nav_d: str,
    metadata: AnalysisMetadata,
    *,
    runner: OpenAIStructuredRunner,
    image_detail: str,
    timeout_s: int | None = None,
) -> list[WindowAnalysis]:
    """Retry a timed-out window by splitting it into two smaller windows."""

    base_timeout = int(timeout_s or getattr(runner, "timeout_s", 300))
    max_retries = int(getattr(runner, "max_retries", 1))

    def _call(target_window: VideoWindow, current_timeout: int) -> WindowAnalysis:
        target_context = context if target_window.index == window.index else _focused_timeout_context(context)
        return analyze_window_sps(
            target_window,
            overview,
            target_context,
            rules_av_nav_d,
            metadata,
            runner=runner,
            image_detail=image_detail,
            timeout_s=current_timeout,
        )

    results = call_openai_with_retry_and_split(
        _call,
        window=window,
        timeout_seconds=base_timeout,
        max_retries=max_retries,
    )
    analyses: list[WindowAnalysis] = []
    for result in results:
        if isinstance(result, WindowAnalysis):
            analyses.append(result)
        elif isinstance(result, dict) and result.get("falhou"):
            failed_window = VideoWindow(
                index=int(result.get("window_index", window.index)),
                start_s=float(result.get("start_s", window.start_s)),
                end_s=float(result.get("end_s", window.end_s)),
                frames=[],
            )
            analyses.append(_failed_window_analysis(failed_window, str(result.get("erro") or "timeout")))
    return analyses or [_failed_window_analysis(window, "timeout sem resposta valida")]


def reanalyze_low_confidence_windows(
    window_analyses: list[WindowAnalysis],
    windows: list[VideoWindow],
    overview: VideoOverview,
    context: str,
    rules_av_nav_d: str,
    metadata: AnalysisMetadata,
    *,
    runner: OpenAIStructuredRunner | None = None,
    all_frames: list[ExtractedFrame] | None = None,
    max_frames_per_window: int = 16,
) -> list[WindowAnalysis]:
    """Reprocess low-confidence windows using high image detail and focused context."""

    runner = runner or OpenAIStructuredRunner()
    by_index = {window.index: window for window in windows}
    updated: list[WindowAnalysis] = []

    for analysis in window_analyses:
        if not _needs_reanalysis(analysis):
            updated.append(analysis)
            continue

        source_window = by_index.get(analysis.window_index)
        if source_window is None:
            updated.append(analysis)
            continue

        window = source_window
        if all_frames:
            detailed_frames = [
                frame
                for frame in all_frames
                if source_window.start_s - 1e-9 <= frame.timestamp_s <= source_window.end_s + 1e-9
            ]
            window = source_window.__class__(
                index=source_window.index,
                start_s=source_window.start_s,
                end_s=source_window.end_s,
                frames=_select_evenly_frames(detailed_frames, max_frames_per_window) or source_window.frames,
                scene_markers=source_window.scene_markers,
            )

        try:
            updated.append(
                analyze_window_sps(
                    window,
                    overview,
                    _focused_timeout_context(context),
                    rules_av_nav_d,
                    metadata,
                    runner=runner,
                    image_detail=os.getenv("OPENAI_REANALYSIS_DETAIL", "high"),
                    timeout_s=runner.timeout_s * 2,
                )
            )
        except Exception as exc:
            alerts = list(analysis.alertas)
            message = f"Reanalise de baixa confianca falhou: {exc}"
            if message not in alerts:
                alerts.append(message)
            updated.append(analysis.model_copy(update={"alertas": alerts}))

    return updated


def build_window_analysis_prompt(
    window: VideoWindow,
    overview: VideoOverview,
    context: str,
    rules_av_nav_d: str,
    metadata: AnalysisMetadata,
) -> str:
    frames_text = "\n".join(
        f"- frame_index={frame.index}; timestamp_s={frame.timestamp_s:.3f}; "
        f"path={frame.path}; resolucao={frame.width}x{frame.height}"
        for frame in window.frames
    ) or "- Nenhum frame disponivel nesta janela."

    scene_text = "\n".join(
        f"- timestamp_s={marker.timestamp_s:.3f}; frame_index={marker.frame_index}; score={marker.score}"
        for marker in window.scene_markers
    ) or "- Nenhuma mudanca visual relevante detectada por heuristica."

    return f"""
Voce e uma IA corporativa de apoio a engenharia de processos SPS/Lean Manufacturing.
Sua tarefa e analisar o processo observado no video, nao apenas descrever imagens.
Voce deve transformar evidencias visuais em microetapas de processo, usando nomenclatura,
memorias e regras SPS fornecidas.

Nao copie exemplos anteriores. Nao assuma PMGS, Bluebox, VR ou qualquer processo como resposta padrao.
Nao gere numero fixo de etapas.
Gere quantas microetapas forem necessarias para representar apenas as acoes observaveis
no intervalo de tempo analisado.

Intervalo da janela:
- window_index={window.index}
- inicio_s={window.start_s:.3f}
- fim_s={window.end_s:.3f}

Regras de observacao:
- A IA deve analisar acoes observaveis, nao inventar etapas.
- Escreva microetapas em linguagem tecnica, direta, no modo imperativo/instrucional.
- Evite frases narrativas como "o operador pega a peca". Prefira "Pegar a peca no ponto de abastecimento indicado".
- Use termos internos somente quando existirem nas memorias ou estiverem visual/contextualmente confirmados.
- Se uma acao nao estiver clara, marcar baixa confianca.
- Se nao houver evidencia visual, escrever "nao conclusivo pelo video; requer validacao no gemba".
- Se uma acao comecar antes da janela ou terminar depois, marque isso na evidencia e estime apenas a parte observavel.
- Se a acao nao estiver visivel, nao invente.
- Se em uma janela houver 0 microetapas observaveis, retorne lista vazia e explique.
- Nao repita texto de outra janela.

Separar acoes operacionalmente distintas:
- deslocar
- pegar
- selecionar
- posicionar
- montar
- fixar
- apertar
- inspecionar
- apontar
- aguardar
- procurar
- retornar
- ajustar
- retrabalhar
- comprar

Nao agrupar "pegar peca, levar e montar" em uma unica etapa.

Classificacao SPS:
AV = transforma diretamente o produto ou adiciona/fixa/conecta componente ao produto conforme requisito.
NAV = necessario pelo metodo atual, qualidade, seguranca, sistema ou abastecimento, mas sem transformacao direta do produto.
D = perda observavel ou atividade eliminavel/reduzivel, como espera, procura, retrabalho, movimentacao excessiva ou repeticao.

Regras de classificacao:
- Nao classificar como AV so porque o operador esta trabalhando.
- Usar NAV para acoes necessarias mas sem transformacao direta.
- Usar D para espera, procura, retrabalho, repeticao evitavel, deslocamento desnecessario ou perda observavel.
- Quando a classificacao depender de contexto nao visivel, marcar baixa confianca.
- Para cada microetapa, fornecer justificativa tecnica.
- Quando houver duvida, marcar baixa confianca e requer validacao no gemba.

Overview do video:
{overview.model_dump_json(indent=2)}

Metadados do usuario:
{metadata.model_dump_json(indent=2)}

Contexto SPS:
{context}

Regras AV/NAV/D:
{rules_av_nav_d}

Frames da janela:
{frames_text}

Mudancas visuais detectadas:
{scene_text}

Schema esperado:
{json.dumps(WindowAnalysis.model_json_schema(), ensure_ascii=False, indent=2)}

Retorne somente JSON valido.
""".strip()


def _needs_reanalysis(analysis: WindowAnalysis) -> bool:
    if analysis.falhou:
        return False
    if analysis.confianca_media < 0.60:
        return True
    if analysis.microetapas:
        avg = mean(step.confianca for step in analysis.microetapas)
        if avg < 0.60:
            return True
    alert_text = " ".join(analysis.alertas).casefold()
    return (
        "nao observavel" in alert_text
        or "nao conclusivo" in alert_text
        or "confus" in alert_text
    )


def _split_window_in_half(window: VideoWindow) -> list[VideoWindow]:
    midpoint = round((window.start_s + window.end_s) / 2, 3)
    first_frames = [frame for frame in window.frames if frame.timestamp_s <= midpoint]
    second_frames = [frame for frame in window.frames if frame.timestamp_s >= midpoint]
    return [
        VideoWindow(
            index=window.index * 100 + 1,
            start_s=window.start_s,
            end_s=midpoint,
            frames=first_frames or window.frames[: max(1, len(window.frames) // 2)],
            scene_markers=[m for m in window.scene_markers if m.timestamp_s <= midpoint],
        ),
        VideoWindow(
            index=window.index * 100 + 2,
            start_s=midpoint,
            end_s=window.end_s,
            frames=second_frames or window.frames[max(1, len(window.frames) // 2) :],
            scene_markers=[m for m in window.scene_markers if m.timestamp_s >= midpoint],
        ),
    ]


def _select_evenly_frames(frames: list[ExtractedFrame], max_count: int) -> list[ExtractedFrame]:
    if max_count <= 0 or not frames:
        return []
    frames = sorted(frames, key=lambda frame: frame.timestamp_s)
    if len(frames) <= max_count:
        return frames
    if max_count == 1:
        return [frames[len(frames) // 2]]
    last_index = len(frames) - 1
    indexes = {
        round(position * last_index / (max_count - 1))
        for position in range(max_count)
    }
    return [frames[index] for index in sorted(indexes)]


def _failed_window_analysis(window: VideoWindow, error: str) -> WindowAnalysis:
    return WindowAnalysis(
        window_index=window.index,
        start_s=window.start_s,
        end_s=window.end_s,
        microetapas=[],
        explicacao_sem_microetapas="Janela nao analisada por falha de provider.",
        confianca_media=0.0,
        alertas=[f"Janela {window.index} nao analisada: {error}"],
        falhou=True,
        erro=error,
    )


def _focused_timeout_context(context: str) -> str:
    max_chars = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
    focused_limit = max(1500, min(max_chars, 4000))
    return context[:focused_limit]
