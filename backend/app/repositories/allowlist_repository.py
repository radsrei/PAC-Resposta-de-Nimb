"""Acesso a dados de `allowed_emails` (lista de acesso mantida pelos administradores)."""

from typing import Any

from app.db.database import get_connection, now_iso


def list_all() -> list[dict[str, Any]]:
    """E-mails da lista, com a indicação de quem já criou a conta."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT a.email, a.added_by, a.created_at, u.email IS NOT NULL AS has_account "
            "FROM allowed_emails a LEFT JOIN users u ON u.email = a.email "
            "ORDER BY a.email"
        ).fetchall()
    return [{**dict(r), "has_account": bool(r["has_account"])} for r in rows]


def contains(email: str) -> bool:
    with get_connection() as conn:
        row = conn.execute("SELECT 1 FROM allowed_emails WHERE email = ?", (email,)).fetchone()
    return row is not None


def add(emails: list[str], added_by: str) -> int:
    """Inclui os e-mails que ainda não estão na lista. Devolve quantos entraram."""
    with get_connection() as conn:
        cur = conn.executemany(
            "INSERT OR IGNORE INTO allowed_emails (email, added_by, created_at) VALUES (?, ?, ?)",
            [(email, added_by, now_iso()) for email in emails],
        )
    return cur.rowcount


def remove(email: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM allowed_emails WHERE email = ?", (email,))
    return cur.rowcount > 0
