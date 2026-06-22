"""Local authorization helpers for the Streamlit entry screen."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


AUTHORIZED_LOGINS_PATH = Path("data/security/authorized_logins.csv")
FIELDNAMES = ["login", "nome", "area", "perfil", "ativo"]


def normalize_login(login: str) -> str:
    """Normalize a corporate login for local authorization checks."""

    normalized = str(login or "").strip().lower()
    if "@" in normalized:
        normalized = normalized.split("@", 1)[0].strip()
    if not normalized:
        raise ValueError("login vazio nao e permitido")
    return normalized


def _is_active(value: Any) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "sim", "yes", "y"}


def _write_example_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerow(
            {
                "login": "m123456",
                "nome": "Nome Sobrenome",
                "area": "Engenharia de Processos",
                "perfil": "user",
                "ativo": "false",
            }
        )
        writer.writerow(
            {
                "login": "admin",
                "nome": "Administrador Local",
                "area": "Engenharia",
                "perfil": "admin",
                "ativo": "false",
            }
        )


def load_authorized_logins(path: str = "data/security/authorized_logins.csv") -> dict[str, dict[str, str]]:
    """Load active logins from the local CSV file.

    If the file is missing, an inactive example is created and access remains
    blocked until the CSV is configured.
    """

    csv_path = Path(path)
    if path == "data/security/authorized_logins.csv":
        csv_path = AUTHORIZED_LOGINS_PATH
    if not csv_path.exists():
        _write_example_file(csv_path)
        return {}

    authorized: dict[str, dict[str, str]] = {}
    with csv_path.open("r", newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            try:
                normalized = normalize_login(row.get("login", ""))
            except ValueError:
                continue
            if not _is_active(row.get("ativo")):
                continue
            authorized[normalized] = {
                "login": normalized,
                "nome": str(row.get("nome") or "").strip(),
                "area": str(row.get("area") or "").strip(),
                "perfil": str(row.get("perfil") or "user").strip() or "user",
                "ativo": "true",
            }
    return authorized


def is_login_authorized(login: str) -> tuple[bool, dict[str, str] | None]:
    """Return whether a normalized login is authorized and its local profile."""

    try:
        normalized = normalize_login(login)
    except ValueError:
        return False, None

    user_data = load_authorized_logins().get(normalized)
    if user_data is None:
        return False, None
    return True, user_data
