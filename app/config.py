"""
Configurações e variáveis de ambiente para a aplicação ia_sps_scania.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
# Force load .env file with override=True to ensure variables are loaded
load_dotenv(REPO_ROOT / ".env", override=True)
try:
    from pydantic_settings import BaseSettings
except ImportError:  # pragma: no cover - fallback para ambientes de teste parciais.
    from pydantic import BaseModel as BaseSettings
from typing import Optional


DEFAULT_OPENAI_MODEL = "gpt-4.1"
DEFAULT_OPENAI_MAX_FRAMES = 24
DEFAULT_OPENAI_TIMEOUT_S = 300
DEFAULT_OPENAI_MAX_OUTPUT_TOKENS = 12000


class Settings(BaseSettings):
    """Configurações da aplicação."""
    
    # Environment
    APP_ENV: str = os.getenv("APP_ENV", "local")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
    OPENAI_MAX_FRAMES: int = int(os.getenv("OPENAI_MAX_FRAMES", str(DEFAULT_OPENAI_MAX_FRAMES)))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", "2"))
    OPENAI_WINDOW_SECONDS: int = int(os.getenv("OPENAI_WINDOW_SECONDS", "15"))
    OPENAI_MAX_FRAMES_PER_WINDOW: int = int(os.getenv("OPENAI_MAX_FRAMES_PER_WINDOW", "10"))
    OPENAI_OVERVIEW_MAX_FRAMES: int = int(os.getenv("OPENAI_OVERVIEW_MAX_FRAMES", "12"))
    OPENAI_IMAGE_DETAIL: str = os.getenv("OPENAI_IMAGE_DETAIL", "auto")
    OPENAI_IMAGE_DETAIL_OVERVIEW: str = os.getenv("OPENAI_IMAGE_DETAIL_OVERVIEW", "low")
    OPENAI_IMAGE_DETAIL_WINDOW: str = os.getenv("OPENAI_IMAGE_DETAIL_WINDOW", "auto")
    OPENAI_OVERVIEW_DETAIL: str = os.getenv("OPENAI_OVERVIEW_DETAIL", OPENAI_IMAGE_DETAIL_OVERVIEW)
    OPENAI_WINDOW_DETAIL: str = os.getenv("OPENAI_WINDOW_DETAIL", OPENAI_IMAGE_DETAIL_WINDOW)
    OPENAI_REANALYSIS_DETAIL: str = os.getenv("OPENAI_REANALYSIS_DETAIL", "high")
    OPENAI_TARGET_WINDOW_SECONDS: float = float(os.getenv("OPENAI_TARGET_WINDOW_SECONDS", "12"))
    OPENAI_MIN_WINDOW_SECONDS: float = float(os.getenv("OPENAI_MIN_WINDOW_SECONDS", "5"))
    OPENAI_MAX_WINDOW_SECONDS: float = float(os.getenv("OPENAI_MAX_WINDOW_SECONDS", "20"))
    OPENAI_MAX_FRAMES_PER_WINDOW_BASE: int = int(os.getenv("OPENAI_MAX_FRAMES_PER_WINDOW_BASE", "10"))
    OPENAI_MAX_FRAMES_PER_WINDOW_REANALYSIS: int = int(os.getenv("OPENAI_MAX_FRAMES_PER_WINDOW_REANALYSIS", "18"))
    OPENAI_TIMEOUT_SECONDS: int = int(os.getenv("OPENAI_TIMEOUT_SECONDS", os.getenv("OPENAI_TIMEOUT_S", str(DEFAULT_OPENAI_TIMEOUT_S))))
    OPENAI_TIMEOUT_S: int = OPENAI_TIMEOUT_SECONDS
    OPENAI_FRAME_MAX_WIDTH: int = int(os.getenv("OPENAI_FRAME_MAX_WIDTH", "1024"))
    OPENAI_JPEG_QUALITY: int = int(os.getenv("OPENAI_JPEG_QUALITY", "75"))
    MAX_CONTEXT_CHARS: int = int(os.getenv("MAX_CONTEXT_CHARS", "12000"))
    OPENAI_MAX_OUTPUT_TOKENS: int = int(
        os.getenv("OPENAI_MAX_OUTPUT_TOKENS", str(DEFAULT_OPENAI_MAX_OUTPUT_TOKENS))
    )
    OPENAI_DEBUG_DIR: str = os.getenv("OPENAI_DEBUG_DIR", "data/outputs/debug")
    
    # Database
    DB_URL: str = os.getenv("DB_URL", "sqlite:///./data/sps_analysis.db")
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    TEMPLATES_DIR: Path = DATA_DIR / "templates"
    VIDEOS_DIR: Path = DATA_DIR / "videos"
    FRAMES_DIR: Path = DATA_DIR / "frames"
    KNOWLEDGE_DIR: Path = DATA_DIR / "knowledge_index"
    OUTPUTS_DIR: Path = DATA_DIR / "outputs"
    LAYOUTS_DIR: Path = DATA_DIR / "layouts"
    
    # Excel Template
    EXCEL_TEMPLATE_PATH: str = os.getenv(
        "EXCEL_TEMPLATE_PATH",
        "data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
    )
    OUTPUT_EXCEL_PATH: str = os.getenv("OUTPUT_EXCEL_PATH", "data/outputs/")
    
    # Video Processing
    VIDEO_FRAME_EXTRACTION_INTERVAL: float = float(
        os.getenv("VIDEO_FRAME_EXTRACTION_INTERVAL", "1.0")
    )
    VIDEO_RESOLUTION_TARGET: str = os.getenv("VIDEO_RESOLUTION_TARGET", "1920x1080")
    
    # Knowledge Base
    KNOWLEDGE_EMBEDDING_MODEL: str = os.getenv(
        "KNOWLEDGE_EMBEDDING_MODEL",
        "text-embedding-3-small"
    )
    KNOWLEDGE_INDEX_PATH: str = os.getenv("KNOWLEDGE_INDEX_PATH", "data/knowledge_index/")
    
    # Thresholds
    MIN_CONFIDENCE_CLASSIFICATION: float = float(
        os.getenv("MIN_CONFIDENCE_CLASSIFICATION", "0.85")
    )
    LOW_CONFIDENCE_FLAG_THRESHOLD: float = float(
        os.getenv("LOW_CONFIDENCE_FLAG_THRESHOLD", "0.7")
    )
    
    # API Configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Streamlit UI
    STREAMLIT_THEME: str = os.getenv("STREAMLIT_THEME", "dark")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Função para criar uma nova instância de configurações com valores do ambiente atualizados
def get_settings():
    """Retorna uma nova instância de Settings com valores do ambiente atualizados."""
    load_dotenv(REPO_ROOT / ".env", override=True)
    return Settings()


def get_default_template_path() -> Path | None:
    """Retorna o caminho do template Excel padrão Scania, se existir."""
    template_env = os.getenv(
        "EXCEL_TEMPLATE_PATH",
        "data/templates/PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx",
    )
    candidate = Path(template_env)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    if candidate.exists():
        return candidate

    fallback = REPO_ROOT / "data" / "templates" / "PMGS_P1_Analise_SPS_CORRIGIDA_2026-03-18.xlsx"
    if fallback.exists():
        return fallback
    return None


# Instância global de configurações (será substituída por get_settings() no Streamlit)
settings = Settings()

# Criar diretórios se não existirem
for dir_path in [
    settings.DATA_DIR,
    settings.TEMPLATES_DIR,
    settings.VIDEOS_DIR,
    settings.FRAMES_DIR,
    settings.KNOWLEDGE_DIR,
    settings.OUTPUTS_DIR,
    settings.LAYOUTS_DIR,
]:
    dir_path.mkdir(parents=True, exist_ok=True)
