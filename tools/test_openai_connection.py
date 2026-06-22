"""Teste simples de conexão com a OpenAI API.

Uso no Windows, a partir da raiz do projeto:
    python tools\test_openai_connection.py

Uso em Linux/Mac:
    python tools/test_openai_connection.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv
from openai import OpenAI


def _is_blocked_loopback_proxy(value: str | None) -> bool:
    if not value:
        return False
    proxy_url = value if "://" in value else f"http://{value}"
    parsed = urlparse(proxy_url)
    return parsed.hostname in {"127.0.0.1", "localhost", "::1"} and parsed.port == 9


def _should_ignore_proxy_env() -> bool:
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
        value = os.getenv(name) or os.getenv(name.lower())
        if _is_blocked_loopback_proxy(value):
            return True
    return False


def main() -> int:
    load_dotenv(REPO_ROOT / ".env")

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    if not api_key:
        print(
            "OPENAI_API_KEY não configurada. Crie um arquivo .env na raiz do projeto "
            "com OPENAI_API_KEY=sua_chave.",
            file=sys.stderr,
        )
        return 1

    try:
        client_kwargs = {"api_key": api_key}
        if _should_ignore_proxy_env():
            import httpx

            client_kwargs["http_client"] = httpx.Client(trust_env=False)
        client = OpenAI(**client_kwargs)
        response = client.responses.create(
            model=model,
            input="Responda apenas com: Conexão com OpenAI OK.",
        )
    except Exception as exc:
        print(f"Erro ao conectar na OpenAI: {exc}", file=sys.stderr)
        return 1

    print(response.output_text or "Conexão com OpenAI OK.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
