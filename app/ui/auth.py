"""Streamlit login and SPS responsibility gate."""

from __future__ import annotations

import base64
import mimetypes
from datetime import datetime
from pathlib import Path

try:
    import streamlit as st
except ImportError:  # pragma: no cover - allows importing tests without Streamlit.
    st = None

from app.security.audit_logger import log_login_event
from app.security.authorized_users import is_login_authorized, normalize_login


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
BACKGROUND_FILENAMES = [
    "login_background.png",
    "login_background.jpg",
    "login_background.jpeg",
]
LOGO_FILENAME = "logo.png"
RESPONSIBILITY_TEXT = [
    "Esta ferramenta utiliza Inteligência Artificial para apoiar a análise de processos, "
    "decomposição de microetapas, classificação AV/NAV/D, identificação de desperdícios, "
    "sugestões de melhoria e preenchimento da planilha padrão Scania.",
    "Esta ferramenta não aprova padrão automaticamente.",
    "A análise gerada pela IA deve ser revisada no gemba e validada tecnicamente conforme "
    "a governança SPS, liderança responsável e critérios de segurança, qualidade, entrega e custo.",
    "O usuário que utiliza, revisa ou autoriza o padrão assume responsabilidade pela verificação "
    "técnica das informações registradas. A assinatura/login será registrada no padrão gerado.",
    "Qualquer padrão gerado sem revisão adequada pode comprometer segurança, qualidade, ergonomia, "
    "estabilidade do método e cultura SPS.",
    "O foco da ferramenta é apoiar a melhoria contínua, preservando a cultura Scania, o trabalho "
    "padronizado e a responsabilidade técnica sobre o processo.",
    "Não utilize esta ferramenta para aprovar alteração de método sem validação no gemba, "
    "envolvimento da liderança e revisão SPS.",
]
RESPONSIBILITY_CHECKBOX = (
    "Li, compreendi e assumo a responsabilidade de revisar tecnicamente a análise antes "
    "de utilizar ou autorizar o padrão."
)


def _asset_data_url(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _find_login_asset(assets_dir: Path = ASSETS_DIR) -> Path | None:
    for filename in BACKGROUND_FILENAMES:
        candidate = assets_dir / filename
        if candidate.exists():
            return candidate
    return None


def build_login_background_style(assets_dir: Path = ASSETS_DIR) -> str:
    """Build the login-only background CSS value with a safe fallback."""

    background_asset = _find_login_asset(assets_dir)
    if background_asset is None:
        return "background: linear-gradient(135deg, #061B33 0%, #082B49 100%);"

    data_url = _asset_data_url(background_asset)
    if data_url is None:
        return "background: linear-gradient(135deg, #061B33 0%, #082B49 100%);"
    return (
        "background-image: linear-gradient(rgba(6, 27, 51, 0.82), rgba(6, 27, 51, 0.88)), "
        f"url('{data_url}'); background-size: cover; background-position: center;"
    )


def _render_login_css() -> None:
    if st is None:
        return
    background_style = build_login_background_style()
    st.markdown(
        f"""
        <style>
        .stApp {{
            {background_style}
            color: #F8FAFC;
        }}
        .block-container {{
            max-width: 780px;
            padding-top: 7vh;
            padding-bottom: 7vh;
        }}
        .auth-card {{
            background: rgba(8, 43, 73, 0.92);
            border: 1px solid #7DB7E8;
            border-radius: 8px;
            padding: 28px 30px;
            box-shadow: 0 22px 60px rgba(0, 0, 0, 0.34);
        }}
        .auth-title {{
            color: #F8FAFC;
            font-size: 2.1rem;
            font-weight: 760;
            margin: 0 0 4px 0;
            letter-spacing: 0;
        }}
        .auth-subtitle {{
            color: #D8E4F2;
            font-size: 1rem;
            margin: 0 0 22px 0;
        }}
        .auth-warning {{
            border-left: 3px solid #FDE68A;
            color: #F8FAFC;
            background: rgba(253, 230, 138, 0.08);
            padding: 12px 14px;
            margin: 14px 0 18px 0;
            font-size: 0.95rem;
            line-height: 1.45;
        }}
        .auth-warning p {{
            margin: 0 0 10px 0;
        }}
        .auth-warning p:last-child {{
            margin-bottom: 0;
        }}
        div.stButton > button:first-child {{
            background: #2F80ED;
            color: #F8FAFC;
            border: 1px solid #2F80ED;
        }}
        div.stButton > button:first-child:hover {{
            background: #1C64C7;
            color: #F8FAFC;
            border: 1px solid #1C64C7;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_logo() -> None:
    if st is None:
        return
    logo_data_url = _asset_data_url(ASSETS_DIR / LOGO_FILENAME)
    if logo_data_url:
        st.markdown(
            f'<img src="{logo_data_url}" alt="Scania" style="max-width: 160px; margin-bottom: 18px;" />',
            unsafe_allow_html=True,
        )


def _store_auth_session(user_data: dict[str, str], accepted_at: str) -> None:
    if st is None:
        return
    st.session_state["auth_authenticated"] = True
    st.session_state["auth_user_login"] = user_data.get("login", "")
    st.session_state["auth_user_name"] = user_data.get("nome", "")
    st.session_state["auth_user_area"] = user_data.get("area", "")
    st.session_state["auth_user_profile"] = user_data.get("perfil", "")
    st.session_state["auth_accepted_responsibility_at"] = accepted_at


def render_login_page() -> dict | None:
    """Render the mandatory local login and SPS responsibility page."""

    if st is None:
        return None

    _render_login_css()
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    _render_logo()
    st.markdown(
        """
        <h1 class="auth-title">SPS Process Analysis AI</h1>
        <p class="auth-subtitle">Ferramenta de apoio à criação, revisão e melhoria de padrões operacionais.</p>
        """,
        unsafe_allow_html=True,
    )
    responsibility_html = "".join(f"<p>{paragraph}</p>" for paragraph in RESPONSIBILITY_TEXT)
    st.markdown(f'<div class="auth-warning">{responsibility_html}</div>', unsafe_allow_html=True)

    login = st.text_input("Login corporativo", value="", key="auth_login_input")
    accepted = st.checkbox(RESPONSIBILITY_CHECKBOX, key="auth_responsibility_accept")
    submitted = st.button("Acessar ferramenta", type="primary", key="auth_submit")

    user_data: dict | None = None
    if submitted:
        try:
            normalized_login = normalize_login(login)
        except ValueError:
            normalized_login = ""

        if not accepted:
            st.warning("É necessário ler e aceitar a responsabilidade antes de acessar a ferramenta.")
            st.markdown("</div>", unsafe_allow_html=True)
            return None

        authorized, user_data = is_login_authorized(normalized_login)
        if not authorized or user_data is None:
            log_login_event(normalized_login or login, "denied", "Login não autorizado para uso desta ferramenta.")
            st.error("Login não autorizado para uso desta ferramenta.")
            st.markdown("</div>", unsafe_allow_html=True)
            return None

        accepted_at = datetime.now().isoformat(timespec="seconds")
        _store_auth_session(user_data, accepted_at)
        log_login_event(user_data["login"], "authorized", "Login autorizado.", user_data)
        log_login_event(
            user_data["login"],
            "accepted_responsibility",
            "Responsabilidade SPS aceita antes do acesso.",
            user_data,
        )
        st.success("Acesso autorizado.")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    return user_data
