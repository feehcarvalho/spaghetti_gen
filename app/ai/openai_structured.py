"""Small OpenAI Structured Outputs client shared by video analysis phases."""

from __future__ import annotations

import base64
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel, ValidationError

from app.config import settings
from app.video.frame_extractor import ExtractedFrame


T = TypeVar("T", bound=BaseModel)

DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_OPENAI_TIMEOUT_SECONDS = 300
DEFAULT_OPENAI_MAX_RETRIES = 2
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 12000
DEFAULT_OPENAI_DEBUG_DIR = Path("data/outputs/debug")
OPENAI_TIMEOUT_FRIENDLY_MESSAGE = (
    "A analise excedeu o tempo limite. O sistema tentara analisar por janelas menores. "
    "Se persistir, reduza o tamanho do video ou diminua documentos anexados."
)


class OpenAIRequestError(RuntimeError):
    """Controlled error raised for OpenAI request failures."""


class OpenAITimeoutError(OpenAIRequestError):
    """Controlled timeout error used by the window retry flow."""


class OpenAIStructuredRunner:
    """Run OpenAI Responses calls and validate them against Pydantic models."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout_s: int | None = None,
        max_retries: int | None = None,
        debug_dir: str | Path | None = None,
        max_output_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL") or getattr(settings, "OPENAI_MODEL", None) or DEFAULT_OPENAI_MODEL
        self.timeout_s = timeout_s or _read_int_env(
            "OPENAI_TIMEOUT_SECONDS",
            _read_int_env("OPENAI_TIMEOUT_S", DEFAULT_OPENAI_TIMEOUT_SECONDS),
        )
        self.max_retries = max_retries if max_retries is not None else _read_int_env(
            "OPENAI_MAX_RETRIES",
            DEFAULT_OPENAI_MAX_RETRIES,
        )
        self.debug_dir = Path(debug_dir or os.getenv("OPENAI_DEBUG_DIR") or DEFAULT_OPENAI_DEBUG_DIR)
        self.max_output_tokens = max_output_tokens or _read_int_env(
            "OPENAI_MAX_OUTPUT_TOKENS",
            DEFAULT_OPENAI_MAX_OUTPUT_TOKENS,
        )

    def request_model(
        self,
        *,
        prompt: str,
        frames: list[ExtractedFrame],
        response_model: type[T],
        schema_name: str,
        image_detail: str = "auto",
        timeout_s: int | None = None,
        max_output_tokens: int | None = None,
    ) -> T:
        """Call OpenAI and return a validated model instance."""

        if not self.api_key:
            raise OpenAIRequestError(
                "OPENAI_API_KEY nao configurada. Configure a variavel de ambiente "
                "ou use provider_name='mock' para desenvolvimento offline."
            )

        try:
            from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
        except ImportError as exc:  # pragma: no cover - depends on environment.
            raise OpenAIRequestError(
                "Pacote openai nao instalado no ambiente. Instale as dependencias "
                "com `pip install -r requirements.txt`."
            ) from exc

        timeout_value = timeout_s or self.timeout_s
        http_client = None
        try:
            if self._should_ignore_proxy_env():
                import httpx

                http_client = httpx.Client(timeout=timeout_value, trust_env=False)

            client = OpenAI(
                api_key=self.api_key,
                timeout=timeout_value,
                max_retries=self.max_retries,
                http_client=http_client,
            )
            payload = self._build_input_payload(prompt, frames, image_detail)
            raw_text = self._create_response(
                client=client,
                input_payload=payload,
                response_model=response_model,
                schema_name=schema_name,
                max_output_tokens=max_output_tokens or self.max_output_tokens,
            )
            return self._validate_response(raw_text, response_model)
        except ValidationError as first_error:
            raw_text = getattr(first_error, "raw_response_text", "")
            return self._repair_invalid_response(
                client=client,
                raw_text=raw_text,
                first_error=first_error,
                response_model=response_model,
                schema_name=schema_name,
            )
        except APITimeoutError as exc:
            self._save_debug("timeout", {"schema_name": schema_name, "error": str(exc)})
            raise OpenAITimeoutError(OPENAI_TIMEOUT_FRIENDLY_MESSAGE) from exc
        except APIConnectionError as exc:
            self._save_debug("connection", {"schema_name": schema_name, "error": str(exc)})
            raise OpenAIRequestError(f"Falha de conexao com OpenAI: {exc}") from exc
        except RateLimitError as exc:
            self._save_debug("rate_limit", {"schema_name": schema_name, "error": str(exc)})
            raise OpenAIRequestError(f"Limite de uso da OpenAI atingido: {exc}") from exc
        except OpenAIRequestError:
            raise
        except Exception as exc:
            self._save_debug("unexpected", {"schema_name": schema_name, "error": str(exc)})
            raise OpenAIRequestError(f"Erro na chamada OpenAI: {exc}") from exc
        finally:
            if http_client is not None:
                http_client.close()

    def _create_response(
        self,
        *,
        client: Any,
        input_payload: list[dict[str, Any]],
        response_model: type[BaseModel],
        schema_name: str,
        max_output_tokens: int,
    ) -> str:
        if not hasattr(client, "responses") or not hasattr(client.responses, "create"):
            raise OpenAIRequestError(
                "SDK OpenAI sem suporte a Responses API. Atualize o pacote `openai`."
            )

        response = client.responses.create(
            model=self.model,
            input=input_payload,
            text={"format": self._response_format(response_model, schema_name)},
            max_output_tokens=max_output_tokens,
        )
        raw_text = self._collect_response_text(response)
        if not raw_text:
            raise OpenAIRequestError("Resposta OpenAI sem texto JSON")
        return raw_text

    def _validate_response(self, raw_text: str, response_model: type[T]) -> T:
        try:
            return response_model.model_validate_json(raw_text)
        except ValidationError as exc:
            setattr(exc, "raw_response_text", raw_text)
            raise

    def _repair_invalid_response(
        self,
        *,
        client: Any,
        raw_text: str,
        first_error: ValidationError,
        response_model: type[T],
        schema_name: str,
    ) -> T:
        correction_prompt = self._build_correction_prompt(raw_text, first_error, response_model)
        correction_payload = [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": correction_prompt}],
            }
        ]
        try:
            corrected_raw = self._create_response(
                client=client,
                input_payload=correction_payload,
                response_model=response_model,
                schema_name=schema_name,
                max_output_tokens=self.max_output_tokens,
            )
            return response_model.model_validate_json(corrected_raw)
        except ValidationError as second_error:
            corrected_raw = getattr(second_error, "raw_response_text", "")
            debug_path = self._save_debug(
                "validation",
                {
                    "schema_name": schema_name,
                    "first_error": str(first_error),
                    "final_error": str(second_error),
                    "raw_response": corrected_raw or raw_text,
                },
            )
            raise OpenAIRequestError(
                "Resposta OpenAI invalida apos tentativa automatica de correcao. "
                f"Resposta bruta salva em: {debug_path}"
            ) from second_error

    def _build_input_payload(
        self,
        prompt: str,
        frames: list[ExtractedFrame],
        image_detail: str,
    ) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = [{"type": "input_text", "text": prompt}]
        for frame in frames:
            image_url = self._frame_to_data_url(frame)
            if image_url is None:
                continue
            content.append(
                {
                    "type": "input_image",
                    "image_url": image_url,
                    "detail": image_detail,
                }
            )
        return [{"role": "user", "content": content}]

    def _frame_to_data_url(self, frame: ExtractedFrame) -> str | None:
        frame_path = Path(frame.path)
        if not frame_path.exists():
            return None
        data = base64.b64encode(frame_path.read_bytes()).decode("ascii")
        return f"data:image/jpeg;base64,{data}"

    def _response_format(self, response_model: type[BaseModel], schema_name: str) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "name": schema_name,
            "strict": True,
            "schema": self._json_schema_for_openai(response_model),
        }

    def _json_schema_for_openai(self, response_model: type[BaseModel]) -> dict[str, Any]:
        try:
            from openai.lib._pydantic import to_strict_json_schema

            return to_strict_json_schema(response_model)
        except Exception:
            return response_model.model_json_schema()

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
                    dict_text = content.get("text")
                    if dict_text:
                        chunks.append(dict_text)
        return "".join(chunks)

    def _collect_response_text_from_mapping(self, response: dict[str, Any]) -> str:
        chunks: list[str] = []
        for output in response.get("output", []) or []:
            for content in output.get("content", []) or []:
                text = content.get("text")
                if text:
                    chunks.append(text)
        return "".join(chunks)

    def _build_correction_prompt(
        self,
        raw_text: str,
        error: ValidationError,
        response_model: type[BaseModel],
    ) -> str:
        schema_json = json.dumps(response_model.model_json_schema(), ensure_ascii=False, indent=2)
        return f"""
Corrija a resposta abaixo para um JSON valido e aderente ao schema informado.

Regras:
- Retorne somente JSON, sem markdown e sem texto livre.
- Nao adicione informacoes novas.
- Preserve tempos, descricoes, classificacoes e justificativas quando coerentes.
- Ajuste apenas estrutura, tipos, campos obrigatorios, enums e consistencia necessaria para validacao.

Erro de validacao Pydantic:
{error}

Schema obrigatorio:
{schema_json}

Resposta bruta a corrigir:
{raw_text or "[sem texto extraido da resposta]"}
""".strip()

    def _save_debug(self, reason: str, payload: dict[str, Any]) -> Path:
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        debug_path = self.debug_dir / f"openai_{reason}_{timestamp}.json"
        safe_payload = {
            "reason": reason,
            "model": self.model,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "payload": payload,
        }
        debug_path.write_text(
            json.dumps(safe_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return debug_path

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


def _read_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default
