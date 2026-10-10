"""
Configurações da aplicação, lidas do arquivo `backend/.env` (ver `.env.example`).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_DIR / ".env")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Respostas de Nimb API"
    version: str = "0.3.0"

    host: str = os.getenv("API_HOST", "0.0.0.0")
    port: int = int(os.getenv("API_PORT", "8000"))

    # Banco local (SQLite) para conexões LLM e histórico de sessões
    database_path: Path = Path(
        os.getenv("DATABASE_PATH", str(BACKEND_DIR / "data" / "nimb.db"))
    )

    # 5500 -> protótipo estático | 3000 -> front React/Vite (frontend/V2 - front Studio)
    cors_origins: list[str] = field(
        default_factory=lambda: _csv(
            os.getenv(
                "CORS_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,"
                "http://localhost:5500,http://127.0.0.1:5500",
            )
        )
    )

    # Tempo máximo (segundos) de espera pela resposta da LLM
    llm_timeout: float = float(os.getenv("LLM_TIMEOUT", "120"))
    # Quantidade de mensagens anteriores da sessão enviadas como contexto
    history_limit: int = int(os.getenv("HISTORY_LIMIT", "10"))

    # Conexão LLM padrão (opcional). Se o banco estiver vazio na subida da API,
    # uma conexão é criada a partir destas variáveis.
    default_llm_provider: str | None = os.getenv("LLM_PROVIDER") or None
    default_llm_model: str | None = os.getenv("LLM_MODEL") or None
    default_llm_api_key: str | None = os.getenv("LLM_API_KEY") or None
    default_llm_base_url: str | None = os.getenv("LLM_BASE_URL") or None


settings = Settings()
