"""Acesso a dados de `auth_sessions` (sessões de login)."""

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
    with get_connection() as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now_iso(),))

