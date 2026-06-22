"""Providers de analise operacional por IA."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.parse import urlparse

from pydantic import BaseModel, Field, ValidationError

from app.config import settings
from app.ai.openai_structured import (
    DEFAULT_OPENAI_MAX_RETRIES,
    OPENAI_TIMEOUT_FRIENDLY_MESSAGE,
    OpenAIRequestError,
    OpenAIStructuredRunner,
    OpenAITimeoutError,
)
from app.ai.prompt_builder import build_analysis_prompt
from app.ai.video_overview import VideoOverview, analyze_video_overview
from app.ai.window_analyzer import (
    WindowAnalysis,
    analyze_window_with_timeout_recovery,
    reanalyze_low_confidence_windows,
)
from app.analysis.consolidator import consolidate_window_analyses
from app.analysis.sps_validator import validate_sps_analysis
from app.schemas.analysis import AnalysisMetadata, OperationalAnalysis
from app.video.segmentation import VideoWindow, split_video_into_windows
from app.video.frame_extractor import ExtractedFrame
from app.video.video_metadata import VideoMetadata, get_video_metadata


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_ANALYSIS = REPO_ROOT / "data" / "outputs" / "sample_analysis_pmgs_p1.json"
DEFAULT_PROMPT_PATH = REPO_ROOT / "docs" / "PROMPT_MESTRE_ANALISE_SPS.md"
DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_OPENAI_MAX_FRAMES = 24
DEFAULT_OPENAI_IMAGE_DETAIL = "auto"
DEFAULT_OPENAI_TIMEOUT_S = 300
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 12000
DEFAULT_OPENAI_DEBUG_DIR = REPO_ROOT / "data" / "outputs" / "debug"
MOCK_DEMO_ALERT = "Análise gerada em modo mock/demonstração. Não representa vídeo real."
MOCK_VIDEO_ERROR = "Modo mock não analisa vídeo real. Use provider openai para analisar o vídeo."


class AnalysisRequest(BaseModel):
    metadata: AnalysisMetadata
    frames: list[ExtractedFrame] = Field(default_factory=list)
    contexto_sps: str
    regras_av_nav_d: str
    observacoes_usuario: str | None = None
    layout_id: str | None = None


class AnalysisProvider(Protocol):
    def analyze(self, request: AnalysisRequest) -> OperationalAnalysis:
        ...


class AnalysisProviderError(RuntimeError):
    """Erro controlado de provider de analise."""


class MockAnalysisProvider:
    """Provider offline baseado no JSON de exemplo do projeto."""

    def __init__(self, sample_path: str | Path = DEFAULT_SAMPLE_ANALYSIS):
        self.sample_path = Path(sample_path)

    def analyze(self, request: AnalysisRequest) -> OperationalAnalysis:
        if request.frames:
            raise AnalysisProviderError(MOCK_VIDEO_ERROR)

        if not self.sample_path.exists():
            raise AnalysisProviderError(f"Arquivo sample nao encontrado: {self.sample_path}")

        with self.sample_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        analysis = OperationalAnalysis.model_validate(data)
        alerts = list(analysis.alertas_validacao)
        if MOCK_DEMO_ALERT not in alerts:
            alerts.append(MOCK_DEMO_ALERT)
        return OperationalAnalysis.model_validate(
            analysis.model_dump() | {"alertas_validacao": alerts}
        )


class OpenAIAnalysisProvider:
    """Provider real via OpenAI API, com Structured Outputs quando disponivel."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        prompt_path: str | Path = DEFAULT_PROMPT_PATH,
        include_images: bool = True,
        max_frames: int | None = None,
        image_detail: str | None = None,
        debug_dir: str | Path | None = None,
        timeout_s: int | None = None,
        max_output_tokens: int | None = None,
    ):
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or settings.OPENAI_MODEL or DEFAULT_OPENAI_MODEL
        self.prompt_path = Path(prompt_path)
        self.include_images = include_images
        self.max_frames = (
            max_frames
            if max_frames is not None
            else self._read_int_env("OPENAI_MAX_FRAMES", settings.OPENAI_MAX_FRAMES)
        )
        self.image_detail = image_detail or os.getenv("OPENAI_IMAGE_DETAIL") or settings.OPENAI_IMAGE_DETAIL or DEFAULT_OPENAI_IMAGE_DETAIL
        self.debug_dir = Path(debug_dir or os.getenv("OPENAI_DEBUG_DIR") or settings.OPENAI_DEBUG_DIR or DEFAULT_OPENAI_DEBUG_DIR)
        self.timeout_s = timeout_s or self._read_int_env(
            "OPENAI_TIMEOUT_SECONDS",
            self._read_int_env("OPENAI_TIMEOUT_S", DEFAULT_OPENAI_TIMEOUT_S),
        )
        self.max_retries = self._read_int_env("OPENAI_MAX_RETRIES", DEFAULT_OPENAI_MAX_RETRIES)
        self.max_output_tokens = max_output_tokens or self._read_int_env(
            "OPENAI_MAX_OUTPUT_TOKENS",
            settings.OPENAI_MAX_OUTPUT_TOKENS,
        )

    def analyze(self, request: AnalysisRequest) -> OperationalAnalysis:
        if not self.api_key:
            raise AnalysisProviderError(
                "OPENAI_API_KEY nao configurada. Configure a variavel de ambiente "
                "ou use provider_name='mock' para desenvolvimento offline."
            )

        if request.frames:
            return self._analyze_frames_by_windows(request)

        try:
            from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
        except ImportError as exc:
            raise AnalysisProviderError(
                "Pacote openai nao instalado no ambiente. Instale as dependencias "
                "com `pip install -r requirements.txt`."
            ) from exc

        selected_frames = self._select_frames(request.frames)
        prompt_request = request.model_copy(update={"frames": selected_frames})
        prompt = self._build_full_prompt(prompt_request)
        input_payload = self._build_input_payload(prompt, selected_frames)

        http_client = None
        try:
            if self._should_ignore_proxy_env():
                import httpx

                http_client = httpx.Client(timeout=self.timeout_s, trust_env=False)
            client = OpenAI(
                api_key=self.api_key,
                timeout=self.timeout_s,
                max_retries=self.max_retries,
                http_client=http_client,
            )
            analysis, _ = self._request_validated_analysis(client, input_payload)
            return analysis
        except ValidationError as first_error:
            raw_text = getattr(first_error, "raw_response_text", "")
            return self._repair_invalid_response(client, raw_text, first_error)
        except AnalysisProviderError:
            raise
        except APITimeoutError as exc:
            raise AnalysisProviderError(OPENAI_TIMEOUT_FRIENDLY_MESSAGE) from exc
        except APIConnectionError as exc:
            raise AnalysisProviderError(f"Falha de conexao com OpenAI: {exc}") from exc
        except RateLimitError as exc:
            raise AnalysisProviderError(f"Limite de uso da OpenAI atingido: {exc}") from exc
        except Exception as exc:
            raise AnalysisProviderError(f"Erro na chamada OpenAI: {exc}") from exc
        finally:
            if http_client is not None:
                http_client.close()

    def analyze_video_pipeline(
        self,
        request: AnalysisRequest,
        *,
        video_metadata: VideoMetadata,
        windows: list[VideoWindow],
        overview_frames: list[ExtractedFrame],
        reprocess_low_confidence: bool = True,
        progress_callback: Callable[[str, dict[str, Any]], None] | None = None,
        detail_window: str | None = None,
        checkpoint_manager: Any | None = None,
        resume_from_checkpoint: bool = True,
    ) -> OperationalAnalysis:
        """Run the mandatory multi-phase SPS video analysis pipeline."""

        if not self.api_key:
            raise AnalysisProviderError(
                "OPENAI_API_KEY nao configurada. Configure a variavel de ambiente "
                "ou use provider_name='mock' para desenvolvimento offline."
            )

        runner = OpenAIStructuredRunner(
            api_key=self.api_key,
            model=self.model,
            timeout_s=self.timeout_s,
            max_retries=self.max_retries,
            debug_dir=self.debug_dir,
            max_output_tokens=self.max_output_tokens,
        )
        window_detail = detail_window or os.getenv("OPENAI_IMAGE_DETAIL_WINDOW") or "auto"

        try:
            overview = None
            if checkpoint_manager is not None and resume_from_checkpoint:
                saved_overview = checkpoint_manager.load_video_overview()
                if saved_overview:
                    overview = VideoOverview.model_validate(saved_overview)
            if overview is None:
                _notify(progress_callback, "overview", {"frames": len(overview_frames)})
                overview = analyze_video_overview(
                    video_metadata,
                    overview_frames,
                    request.metadata,
                    request.contexto_sps,
                    runner=runner,
                    image_detail=os.getenv("OPENAI_IMAGE_DETAIL_OVERVIEW", "low"),
                )
                if checkpoint_manager is not None:
                    checkpoint_manager.save_video_overview(overview)

            window_analyses: list[WindowAnalysis] = []
            restored_window_indexes: set[int] = set()
            for position, window in enumerate(windows, start=1):
                _notify(
                    progress_callback,
                    "window",
                    {
                        "current": position,
                        "total": len(windows),
                        "window_index": window.index,
                        "frames": len(window.frames),
                    },
                )
                if checkpoint_manager is not None and resume_from_checkpoint and checkpoint_manager.is_window_completed(window):
                    saved_response = checkpoint_manager.load_window_response(window)
                    restored = _restore_window_analyses(saved_response)
                    window_analyses.extend(restored)
                    restored_window_indexes.update(item.window_index for item in restored)
                    _notify(progress_callback, "window_checkpoint", {"window_index": window.index, "restored": len(restored)})
                    continue

                if checkpoint_manager is not None:
                    checkpoint_manager.save_window_request(
                        window,
                        {
                            "model": self.model,
                            "image_detail": window_detail,
                            "timeout_s": self.timeout_s,
                            "max_retries": self.max_retries,
                        },
                    )
                    checkpoint_manager.save_window_status(window, "running")

                try:
                    analyzed_windows = analyze_window_with_timeout_recovery(
                        window,
                        overview,
                        request.contexto_sps,
                        request.regras_av_nav_d,
                        request.metadata,
                        runner=runner,
                        image_detail=window_detail,
                        timeout_s=self.timeout_s,
                    )
                    window_analyses.extend(analyzed_windows)
                    if checkpoint_manager is not None:
                        checkpoint_manager.save_window_response(window, analyzed_windows)
                        checkpoint_manager.save_window_status(window, "completed")
                except Exception as exc:
                    failed = WindowAnalysis(
                        window_index=window.index,
                        start_s=window.start_s,
                        end_s=window.end_s,
                        microetapas=[],
                        explicacao_sem_microetapas="Janela nao analisada por falha de provider.",
                        confianca_media=0.0,
                        alertas=[f"Janela {window.index} nao analisada: {exc}"],
                        falhou=True,
                        erro=str(exc),
                    )
                    window_analyses.append(failed)
                    if checkpoint_manager is not None:
                        checkpoint_manager.save_window_response(window, [failed])
                        checkpoint_manager.save_window_status(window, "failed", str(exc))

            if reprocess_low_confidence:
                _notify(progress_callback, "reanalyze", {"windows": len(window_analyses)})
                retained = [item for item in window_analyses if item.window_index in restored_window_indexes]
                candidates_for_reanalysis = [
                    item for item in window_analyses if item.window_index not in restored_window_indexes
                ]
                candidate_windows = [
                    item for item in windows if item.index not in restored_window_indexes
                ]
                reanalyzed = reanalyze_low_confidence_windows(
                    candidates_for_reanalysis,
                    candidate_windows,
                    overview,
                    request.contexto_sps,
                    request.regras_av_nav_d,
                    request.metadata,
                    runner=runner,
                    all_frames=request.frames,
                    max_frames_per_window=max(16, self.max_frames),
                )
                window_analyses = sorted(
                    retained + reanalyzed,
                    key=lambda item: (item.start_s, item.end_s, item.window_index),
                )

            _notify(progress_callback, "consolidate", {"window_analyses": len(window_analyses)})
            analysis = consolidate_window_analyses(window_analyses, request.metadata)
            analysis = validate_sps_analysis(analysis)
            if checkpoint_manager is not None:
                checkpoint_manager.save_consolidated_analysis(analysis)
            return analysis
        except (OpenAIRequestError, OpenAITimeoutError) as exc:
            raise AnalysisProviderError(str(exc)) from exc

    def _analyze_frames_by_windows(self, request: AnalysisRequest) -> OperationalAnalysis:
        duration_s = request.metadata.ciclo_observado_s
        video_metadata: VideoMetadata | None = None
        if request.metadata.fonte_video:
            try:
                video_metadata = get_video_metadata(request.metadata.fonte_video)
                duration_s = duration_s or video_metadata.duration_s
            except Exception:
                video_metadata = None

        if duration_s is None:
            duration_s = max((frame.timestamp_s for frame in request.frames), default=0.0)
        video_metadata = video_metadata or VideoMetadata(
            video_path=request.metadata.fonte_video or "",
            duration_s=round(duration_s, 3),
            fps=0.0,
            width=max((frame.width for frame in request.frames), default=0),
            height=max((frame.height for frame in request.frames), default=0),
            frame_count=0,
            file_size_mb=0.0,
        )
        windows = split_video_into_windows(
            request.frames,
            duration_s=video_metadata.duration_s,
            target_window_seconds=self._read_int_env("OPENAI_WINDOW_SECONDS", 15),
            max_frames_per_window=self._read_int_env("OPENAI_MAX_FRAMES_PER_WINDOW", 10),
            include_scene_changes=True,
        )
        overview_frames = self._select_frames(
            request.frames,
            max_frames=self._read_int_env("OPENAI_OVERVIEW_MAX_FRAMES", 12),
        )
        return self.analyze_video_pipeline(
            request,
            video_metadata=video_metadata,
            windows=windows,
            overview_frames=overview_frames,
            reprocess_low_confidence=True,
            detail_window=os.getenv("OPENAI_IMAGE_DETAIL_WINDOW", "auto"),
        )

    def _build_full_prompt(self, request: AnalysisRequest) -> str:
        prompt_parts = []
        if self.prompt_path.exists():
            prompt_parts.append(self.prompt_path.read_text(encoding="utf-8"))
        prompt_parts.append(build_analysis_prompt(request))
        return "\n\n".join(prompt_parts)

    def _build_input_payload(self, prompt: str, frames: list[ExtractedFrame]) -> list[dict]:
        content = [{"type": "input_text", "text": prompt}]

        if self.include_images:
            for frame in frames:
                image_url = self._frame_to_data_url(frame)
                if image_url is not None:
                    content.append(
                        {
                            "type": "input_image",
                            "image_url": image_url,
                            "detail": self.image_detail,
                        }
                    )

        return [{"role": "user", "content": content}]

    def _request_validated_analysis(self, client: Any, input_payload: list[dict]) -> tuple[OperationalAnalysis, str]:
        if not hasattr(client, "responses") or not hasattr(client.responses, "create"):
            raise AnalysisProviderError(
                "SDK OpenAI sem suporte a Responses API. Atualize o pacote `openai`."
            )

        response = client.responses.create(
            model=self.model,
            input=input_payload,
            text={"format": self._response_format()},
            max_output_tokens=self.max_output_tokens,
        )
        raw_text = self._collect_response_text(response)
        if not raw_text:
            raise AnalysisProviderError("Resposta OpenAI sem texto JSON")

        try:
            return OperationalAnalysis.model_validate_json(raw_text), raw_text
        except ValidationError as exc:
            setattr(exc, "raw_response_text", raw_text)
            raise

    def _repair_invalid_response(
        self,
        client: Any,
        raw_text: str,
        first_error: ValidationError,
    ) -> OperationalAnalysis:
        correction_prompt = self._build_correction_prompt(raw_text, first_error)
        correction_payload = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": correction_prompt}],
            }
        ]

        try:
            analysis, _ = self._request_validated_analysis(client, correction_payload)
            return analysis
        except ValidationError as second_error:
            corrected_raw = getattr(second_error, "raw_response_text", "")
            debug_path = self._save_debug_response(
                raw_text=corrected_raw or raw_text,
                first_error=first_error,
                final_error=second_error,
            )
            raise AnalysisProviderError(
                "Resposta OpenAI invalida apos tentativa automatica de correcao. "
                f"Resposta bruta salva em: {debug_path}"
            ) from second_error

    def _frame_to_data_url(self, frame: ExtractedFrame) -> str | None:
        frame_path = Path(frame.path)
        if not frame_path.exists():
            return None

        data = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{data}"

    def _response_format(self) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": "operational_analysis",
            "strict": True,
            "schema": self._json_schema_for_openai(),
        }

    def _json_schema_for_openai(self) -> dict[str, Any]:
        try:
            from openai.lib._pydantic import to_strict_json_schema

            return to_strict_json_schema(OperationalAnalysis)
        except Exception:
            return OperationalAnalysis.model_json_schema()

    def _collect_response_text(self, response: Any) -> str:
        output_text = getattr(response, "output_text", None)
        if output_text:
            return output_text

        if isinstance(response, dict):
            return self._collect_response_text_from_mapping(response)

        chunks: list[str] = []
        for output in getattr(response, "output", []) or []:
            for content in getattr(output, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    chunks.append(text)
                if isinstance(content, dict):
                    text = content.get("text")
                    if text:
                        chunks.append(text)
        return "".join(chunks)

    def _collect_response_text_from_mapping(self, response: dict[str, Any]) -> str:
        chunks: list[str] = []
        for output in response.get("output", []) or []:
            for content in output.get("content", []) or []:
                text = content.get("text")
                if text:
                    chunks.append(text)
        return "".join(chunks)

    def _select_frames(self, frames: list[ExtractedFrame], max_frames: int | None = None) -> list[ExtractedFrame]:
        frame_limit = self.max_frames if max_frames is None else max_frames
        if not frames or frame_limit <= 0:
            return []
        if len(frames) <= frame_limit:
            return [frame for frame in frames if Path(frame.path).exists()]

        if frame_limit == 1:
            selected = [frames[0]]
        else:
            last_index = len(frames) - 1
            indexes = {
                round(position * last_index / (frame_limit - 1))
                for position in range(frame_limit)
            }
            selected = [frames[index] for index in sorted(indexes)]

        return [frame for frame in selected if Path(frame.path).exists()]

    def _should_ignore_proxy_env(self) -> bool:
        for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
            value = os.getenv(name) or os.getenv(name.lower())
            if self._is_blocked_loopback_proxy(value):
                return True
        return False

    def _is_blocked_loopback_proxy(self, value: str | None) -> bool:
        if not value:
            return False
        proxy_url = value if "://" in value else f"http://{value}"
        parsed = urlparse(proxy_url)
        return parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == 9

    def _build_correction_prompt(self, raw_text: str, error: ValidationError) -> str:
        schema_json = json.dumps(
            OperationalAnalysis.model_json_schema(),
            ensure_ascii=False,
            indent=2,
        )
        return f"""
Corrija a resposta abaixo para um JSON valido e aderente ao schema OperationalAnalysis.

Regras:
- Retorne somente JSON, sem markdown e sem texto livre.
- Nao adicione informacoes novas.
- Preserve os metadados, microetapas, classificacoes AV/NAV/D e justificativas ja fornecidas quando coerentes.
- Ajuste apenas estrutura, tipos, campos obrigatorios, enums e consistencia necessaria para validacao.

Erro de validacao Pydantic:
{error}

Schema obrigatorio:
{schema_json}

Resposta bruta a corrigir:
{raw_text or "[sem texto extraido da resposta]"}
""".strip()

    def _save_debug_response(
        self,
        raw_text: str,
        first_error: ValidationError,
        final_error: ValidationError,
    ) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_path = self.debug_dir / f"openai_response_{timestamp}.txt"
        debug_path.write_text(
            "\n".join(
                [
                    "OpenAI raw response debug",
                    f"model={self.model}",
                    "",
                    "First validation error:",
                    str(first_error),
                    "",
                    "Final validation error:",
                    str(final_error),
                    "",
                    "Raw response:",
                    raw_text or "[sem texto extraido da resposta]",
                ]
            ),
            encoding="utf-8",
        )
        return debug_path

    def _read_int_env(self, name: str, default: int) -> int:
        value = os.getenv(name)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default


def _notify(
    callback: Callable[[str, dict[str, Any]], None] | None,
    stage: str,
    payload: dict[str, Any],
) -> None:
    if callback is not None:
        callback(stage, payload)


def _restore_window_analyses(saved_response: Any) -> list[WindowAnalysis]:
    if saved_response is None:
        return []
    if isinstance(saved_response, list):
        return [WindowAnalysis.model_validate(item) for item in saved_response]
    return [WindowAnalysis.model_validate(saved_response)]
