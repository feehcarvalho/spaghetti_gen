from pathlib import Path
from uuid import uuid4

from app.security import authorized_users


def _runtime_path(filename: str) -> Path:
    root = Path("data/outputs/test_auth_runtime") / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root / filename


def test_normalize_login_trims_case_and_email():
    assert authorized_users.normalize_login("  M123456@scania.com  ") == "m123456"


def test_load_authorized_logins_only_active_rows():
    csv_path = _runtime_path("authorized_logins.csv")
    csv_path.write_text(
        "login,nome,area,perfil,ativo\n"
        "M123456,Nome Ativo,Engenharia,user,true\n"
        "M999999,Nome Inativo,Engenharia,user,false\n",
        encoding="utf-8",
    )

    users = authorized_users.load_authorized_logins(str(csv_path))

    assert "m123456" in users
    assert "m999999" not in users
    assert users["m123456"]["nome"] == "Nome Ativo"


def test_is_login_authorized_blocks_inactive_and_missing(monkeypatch):
    csv_path = _runtime_path("authorized_logins.csv")
    csv_path.write_text(
        "login,nome,area,perfil,ativo\n"
        "ADMIN,Administrador Local,Engenharia,admin,true\n"
        "BLOQUEADO,Usuario Bloqueado,Engenharia,user,false\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(authorized_users, "AUTHORIZED_LOGINS_PATH", csv_path)

    authorized, user_data = authorized_users.is_login_authorized(" admin ")
    inactive, inactive_data = authorized_users.is_login_authorized("bloqueado")
    missing, missing_data = authorized_users.is_login_authorized("naoexiste")

    assert authorized is True
    assert user_data["login"] == "admin"
    assert inactive is False
    assert inactive_data is None
    assert missing is False
    assert missing_data is None


def test_missing_authorized_file_creates_example_and_blocks(monkeypatch):
    csv_path = _runtime_path("authorized_logins.csv")
    monkeypatch.setattr(authorized_users, "AUTHORIZED_LOGINS_PATH", csv_path)

    users = authorized_users.load_authorized_logins()

    assert users == {}
    assert csv_path.exists()
    assert "login,nome,area,perfil,ativo" in csv_path.read_text(encoding="utf-8")
