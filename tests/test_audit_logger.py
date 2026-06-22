import csv
from pathlib import Path
from uuid import uuid4

from app.security import audit_logger


def _runtime_log_path() -> Path:
    root = Path("data/outputs/test_auth_runtime") / uuid4().hex
    return root / "login_events.csv"


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_log_login_event_saves_authorized_event(monkeypatch):
    log_path = _runtime_log_path()
    monkeypatch.setattr(audit_logger, "AUDIT_LOG_PATH", log_path)

    audit_logger.log_login_event(
        "admin",
        "authorized",
        "Login autorizado.",
        {"nome": "Administrador Local", "area": "Engenharia", "perfil": "admin"},
    )

    rows = _read_rows(log_path)
    assert len(rows) == 1
    assert rows[0]["login"] == "admin"
    assert rows[0]["status"] == "authorized"
    assert rows[0]["user_name"] == "Administrador Local"


def test_log_login_event_saves_denied_event_and_creates_folder(monkeypatch):
    log_path = _runtime_log_path()
    monkeypatch.setattr(audit_logger, "AUDIT_LOG_PATH", log_path)

    audit_logger.log_login_event("desconhecido", "denied", "Login nao autorizado.")

    rows = _read_rows(log_path)
    assert log_path.parent.exists()
    assert rows[0]["status"] == "denied"
    assert rows[0]["login"] == "desconhecido"


def test_log_login_event_redacts_openai_api_key(monkeypatch):
    log_path = _runtime_log_path()
    monkeypatch.setattr(audit_logger, "AUDIT_LOG_PATH", log_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-sensitive-test-key")

    audit_logger.log_login_event("admin", "authorized", "chave sk-sensitive-test-key nao deve aparecer")

    contents = log_path.read_text(encoding="utf-8")
    assert "sk-sensitive-test-key" not in contents
    assert "[redacted]" in contents
