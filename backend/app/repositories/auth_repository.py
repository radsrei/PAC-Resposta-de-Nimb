"""Acesso a dados de `auth_sessions` e `password_reset_tokens`."""

from typing import Any

from app.db.database import get_connection, now_iso


# ---------------------------------------------------------------------------
# Sessões de login
# ---------------------------------------------------------------------------
def create_session(
    token_hash: str, email: str, expires_at: str, ip: str | None, user_agent: str | None
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO auth_sessions (token_hash, user_email, created_at, expires_at, ip, user_agent) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (token_hash, email, now_iso(), expires_at, ip, (user_agent or "")[:300]),
        )


def get_valid_session(token_hash: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM auth_sessions WHERE token_hash = ? AND expires_at > ?",
            (token_hash, now_iso()),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token_hash: str) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (token_hash,))


def delete_user_sessions(email: str, except_token_hash: str | None = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM auth_sessions WHERE user_email = ? AND token_hash != ?",
            (email, except_token_hash or ""),
        )
    return cur.rowcount


def purge_expired() -> None:
    ts = now_iso()
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (ts,))
        conn.execute(
            "DELETE FROM password_reset_tokens WHERE expires_at <= ? OR used_at IS NOT NULL", (ts,)
        )


# ---------------------------------------------------------------------------
# Tokens de recuperação de senha
# ---------------------------------------------------------------------------
def create_reset_token(token_hash: str, email: str, expires_at: str) -> None:
    with get_connection() as conn:
        # Só um token válido por usuário: pedidos novos invalidam os anteriores
        conn.execute("DELETE FROM password_reset_tokens WHERE user_email = ?", (email,))
        conn.execute(
            "INSERT INTO password_reset_tokens (token_hash, user_email, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (token_hash, email, now_iso(), expires_at),
        )


def consume_reset_token(token_hash: str) -> str | None:
    """Marca o token como usado e devolve o e-mail do dono, se válido."""
    ts = now_iso()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user_email FROM password_reset_tokens "
            "WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
            (token_hash, ts),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ?", (ts, token_hash)
        )
    return row["user_email"]
