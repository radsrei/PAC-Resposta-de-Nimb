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


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class Settings:
    app_name: str = "Respostas de Nimb API"
    version: str = "0.4.0"
    # Swagger em /docs (desligue em produção)
    enable_docs: bool = _bool("ENABLE_DOCS", True)

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

    # ------------------------------------------------------------------
    # Autenticação
    # ------------------------------------------------------------------
    # Chave usada para criptografar as API keys das LLMs no banco. Se vazia,
    # uma chave é gerada e salva em data/secret.key (fora do Git).
    app_secret_key: str | None = os.getenv("APP_SECRET_KEY") or None

    # Cookie de sessão (HttpOnly). Em produção com HTTPS use COOKIE_SECURE=true.
    session_cookie_name: str = os.getenv("SESSION_COOKIE_NAME", "nimb_session")
    cookie_secure: bool = _bool("COOKIE_SECURE", False)
    session_ttl_hours: int = int(os.getenv("SESSION_TTL_HOURS", "8"))
    remember_me_days: int = int(os.getenv("REMEMBER_ME_DAYS", "7"))

    # Login com Google (Google Identity Services). Vazio = botão desativado.
    google_client_id: str | None = os.getenv("GOOGLE_CLIENT_ID") or None

    # Contas são criadas no primeiro login com Google. Com false, só entram
    # usuários que já existem no banco.
    registration_enabled: bool = _bool("REGISTRATION_ENABLED", True)
    # E-mails que viram administradores ao criar conta
    admin_emails: list[str] = field(
        default_factory=lambda: [e.lower() for e in _csv(os.getenv("ADMIN_EMAILS", ""))]
    )
    # A primeira conta criada no sistema vira administradora
    first_user_is_admin: bool = _bool("FIRST_USER_IS_ADMIN", True)

    # Limite de requisições por minuto, por IP, na rota de login
    auth_rate_limit_per_minute: int = int(os.getenv("AUTH_RATE_LIMIT_PER_MINUTE", "20"))


settings = Settings()
