"""Local audit logging for access to the Streamlit app."""

from __future__ import annotations

import csv
import getpass
import os
import uuid
from datetime import datetime
from pathlib import Path


AUDIT_LOG_PATH = Path("data/audit/login_events.csv")
AUDIT_FIELDNAMES = [
    "timestamp",
    "login",
    "status",
    "message",
    "user_name",
    "user_area",
    "user_profile",
    "app_env",
    "machine_user",
    "session_id",
]
ALLOWED_STATUSES = {"authorized", "denied", "accepted_responsibility", "logout"}
_SESSION_ID = uuid.uuid4().hex


def _safe_text(value: object) -> str:
    text = str(value or "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key and api_key in text:
        text = text.replace(api_key, "[redacted]")
    return text


def log_login_event(
    login: str,
    status: str,
    message: str,
    user_data: dict | None = None,
) -> None:
    """Append a local access event without storing sensitive analysis content."""

    normalized_status = status if status in ALLOWED_STATUSES else "denied"
    user_data = user_data or {}
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    write_header = not AUDIT_LOG_PATH.exists() or AUDIT_LOG_PATH.stat().st_size == 0

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "login": _safe_text(login).strip().lower(),
        "status": normalized_status,
        "message": _safe_text(message),
        "user_name": _safe_text(user_data.get("nome") or user_data.get("name")),
        "user_area": _safe_text(user_data.get("area")),
        "user_profile": _safe_text(user_data.get("perfil") or user_data.get("profile")),
        "app_env": _safe_text(os.getenv("APP_ENV", "local")),
        "machine_user": _safe_text(getpass.getuser()),
        "session_id": _SESSION_ID,
    }

    with AUDIT_LOG_PATH.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=AUDIT_FIELDNAMES)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
