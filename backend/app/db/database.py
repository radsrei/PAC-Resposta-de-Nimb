"""
Persistência local em SQLite (biblioteca padrão, sem dependências extras).

Tabelas:
- users:                 contas de usuário (e-mail é a chave primária)
- auth_sessions:         sessões de login (apenas o hash do token é salvo)
- llm_connections:       conexões/credenciais de LLM (API key criptografada)
- chat_sessions:         conversas de cada usuário ("Perguntas Anteriores")
- chat_messages:         mensagens de cada conversa
- book_access:           livros liberados para cada usuário (após validar o PDF)
- book_validation_log:   histórico de tentativas de validação de livro
- allowed_emails:        lista de acesso (e-mails que podem entrar), mantida pelos admins
- treasure_rolls:        sorteios de tesouro de cada usuário (entrada e resultado)

Segurança: todas as consultas usam parâmetros (`?`). Nenhum valor vindo do
usuário é concatenado em SQL, o que impede SQL injection.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    email                TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    google_sub           TEXT UNIQUE,
    role                 TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_active            INTEGER NOT NULL DEFAULT 1,
    last_login_at        TEXT,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash  TEXT PRIMARY KEY,
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
    created_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    ip          TEXT,
    user_agent  TEXT
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions (user_email);

CREATE TABLE IF NOT EXISTS llm_connections (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    provider    TEXT NOT NULL,
    model       TEXT NOT NULL,
    base_url    TEXT,
    api_key     TEXT,
    temperature REAL,
    max_tokens  INTEGER,
    is_active   INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_sessions (
    id         TEXT PRIMARY KEY,
    user_email TEXT REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
    title      TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id         TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT NOT NULL,
    metadata   TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_session
    ON chat_messages (session_id, created_at);

CREATE TABLE IF NOT EXISTS book_access (
    user_email  TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
    book_id     TEXT NOT NULL,
    granted_at  TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    score       REAL NOT NULL,
    PRIMARY KEY (user_email, book_id)
);

CREATE TABLE IF NOT EXISTS book_validation_log (
    id          TEXT PRIMARY KEY,
    user_email  TEXT REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
    book_id     TEXT,
    accepted    INTEGER NOT NULL,
    score       REAL NOT NULL,
    file_name   TEXT,
    file_sha256 TEXT,
    size_bytes  INTEGER,
    page_count  INTEGER,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_book_validation_user
    ON book_validation_log (user_email, created_at);

CREATE TABLE IF NOT EXISTS allowed_emails (
    email       TEXT PRIMARY KEY,
    added_by    TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS treasure_rolls (
    id             TEXT PRIMARY KEY,
    user_email     TEXT NOT NULL REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE,
    book_id        TEXT NOT NULL,
    creature       TEXT,
    nd             TEXT NOT NULL,
    treasure_type  TEXT NOT NULL,
    total_value    REAL NOT NULL,
    result         TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_treasure_rolls_user
    ON treasure_rolls (user_email, created_at);
"""


def now() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now().isoformat()


def iso_in(**delta) -> str:
    return (now() + timedelta(**delta)).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Ajusta bancos criados por versões anteriores."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(chat_sessions)")}
    if "user_email" not in columns:
        # Conversas antigas ficam sem dono (não aparecem para nenhum usuário)
        conn.execute(
            "ALTER TABLE chat_sessions ADD COLUMN user_email TEXT "
            "REFERENCES users(email) ON DELETE CASCADE ON UPDATE CASCADE"
        )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_chat_sessions_user ON chat_sessions (user_email, updated_at)"
    )
    # Login com e-mail e senha foi removido (só Google): os tokens de
    # recuperação de senha não têm mais uso. Colunas antigas de `users`
    # (password_hash etc.) permanecem em bancos existentes, sem uso.
    conn.execute("DROP TABLE IF EXISTS password_reset_tokens")


def init_db() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
