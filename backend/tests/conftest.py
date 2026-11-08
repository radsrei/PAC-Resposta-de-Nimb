"""
Configuração compartilhada da suíte de testes da API.

As configurações (`app/core/config.py`) são lidas UMA vez, na importação do app.
Por isso o ambiente de teste é montado aqui, antes de qualquer `import app...`:
banco SQLite, vector_store e pasta do tesouro vão para uma pasta temporária, e
nenhuma chave real (Google, DeepSeek) é usada. O `backend/.env` local não
interfere: o `load_dotenv` não sobrescreve variáveis que já existem.

Marcadores (ver pytest.ini):
  live_deepseek  chama a API real do DeepSeek (exige DEEPSEEK_API_KEY)
  live_ollama    chama um Ollama real em OLLAMA_URL (CI: service container)
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest

TMP_ROOT = Path(tempfile.mkdtemp(prefix="nimb-tests-"))
VECTOR_STORE = TMP_ROOT / "vector_store"
VECTOR_STORE.mkdir()

ADMIN_EMAIL = "admin@nimb.test"
ALLOWED_ORIGIN = "http://localhost:3000"

TEST_ENV = {
    "ENABLE_DOCS": "false",
    "DATABASE_PATH": str(TMP_ROOT / "nimb.db"),
    "VECTOR_STORE_DIR": str(VECTOR_STORE),
    "TREASURE_DIR": str(TMP_ROOT / "tesouro"),
    "CORS_ORIGINS": f"{ALLOWED_ORIGIN},http://127.0.0.1:3000",
    "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
    "REGISTRATION_ENABLED": "true",
    "ADMIN_EMAILS": ADMIN_EMAIL,
    "FIRST_USER_IS_ADMIN": "false",
    "ALLOWLIST_ENABLED": "true",
    "APP_SECRET_KEY": "chave-de-teste-nao-usar-em-producao-0123456789",
    "COOKIE_SECURE": "false",
    "AUTH_RATE_LIMIT_PER_MINUTE": "20",
    "BOOK_UPLOAD_MAX_MB": "95",
    "BOOK_UPLOAD_RATE_PER_MINUTE": "5",
    "EMBEDDING_PROVIDER": "ollama",
    "OLLAMA_URL": os.environ.get("OLLAMA_URL", "http://localhost:11434"),
    "LLM_PROVIDER": "deepseek",
    "LLM_DEEPSEEK_API": "",  # vazio: nenhuma conexão criada na subida
    "ANSWER_TIME_BUDGET": "85",
}
os.environ.update(TEST_ENV)

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402

from app.controllers import auth_controller  # noqa: E402
from app.core import rate_limit  # noqa: E402
from app.core.exceptions import UnauthorizedError  # noqa: E402
from app.main import app  # noqa: E402
from app.services.google_auth import GoogleIdentity  # noqa: E402

VALID_PREFIX = "google-ok:"


def google_credential(email: str) -> str:
    """Credencial falsa que o login simulado aceita como token válido do Google."""
    return f"{VALID_PREFIX}{email}"


def _fake_verify(credential: str) -> GoogleIdentity:
    if not credential.startswith(VALID_PREFIX):
        raise UnauthorizedError("Token do Google inválido ou expirado.")
    email = credential[len(VALID_PREFIX):].strip().lower()
    return GoogleIdentity(sub=f"sub-{email}", email=email, name=email.split("@")[0])


def _wipe_database() -> None:
    db = Path(TEST_ENV["DATABASE_PATH"])
    if not db.exists():
        return
    conn = sqlite3.connect(db)
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )]
        for table in tables:
            conn.execute(f'DELETE FROM "{table}"')
        conn.commit()
    finally:
        conn.close()


def _wipe_vector_store() -> None:
    from app.services import book_catalog

    for child in VECTOR_STORE.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    book_catalog._cache["mtime"] = None


@pytest.fixture(autouse=True)
def _isolated_state(monkeypatch):
    """Cada teste começa com banco vazio, sem livros e com os limites de requisição zerados."""
    _wipe_database()
    _wipe_vector_store()
    rate_limit.auth_limiter.reset()
    rate_limit.book_upload_limiter.reset()
    monkeypatch.setattr(auth_controller, "verify_google_credential", _fake_verify)
    yield
    _wipe_vector_store()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str, remember: bool = False):
    return client.post("/api/auth/google", json={"credential": google_credential(email), "remember": remember})


@pytest.fixture
def admin_client(client):
    response = login(client, ADMIN_EMAIL)
    assert response.status_code == 200, response.text
    return client


def allow_email(email: str) -> None:
    """Coloca o e-mail na lista de acesso direto no banco (sem passar pela rota de admin)."""
    from app.repositories import allowlist_repository

    allowlist_repository.add([email], ADMIN_EMAIL)


@pytest.fixture
def user_client(client):
    """Cliente logado como usuário comum (e-mail já liberado na lista de acesso)."""
    email = "jogador@nimb.test"
    allow_email(email)
    response = login(client, email)
    assert response.status_code == 200, response.text
    return client


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TMP_ROOT, ignore_errors=True)
