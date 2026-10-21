"""Acesso a dados de `book_access` e `book_validation_log`."""

from typing import Any

from app.db.database import get_connection, new_id, now_iso


def grant_access(user_email: str, book_id: str, file_sha256: str, score: float) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO book_access (user_email, book_id, granted_at, file_sha256, score) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (user_email, book_id) DO UPDATE SET "
            "granted_at = excluded.granted_at, file_sha256 = excluded.file_sha256, "
            "score = excluded.score",
            (user_email, book_id, now_iso(), file_sha256, score),
        )


def list_access(user_email: str) -> dict[str, dict[str, Any]]:
    """Livros liberados para o usuário, indexados pelo id do livro."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT book_id, granted_at, score FROM book_access WHERE user_email = ?",
            (user_email,),
        ).fetchall()
    return {r["book_id"]: dict(r) for r in rows}


def has_access(user_email: str, book_id: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM book_access WHERE user_email = ? AND book_id = ?",
            (user_email, book_id),
        ).fetchone()
    return row is not None


def log_attempt(
    user_email: str,
    book_id: str | None,
    accepted: bool,
    score: float,
    file_name: str | None,
    file_sha256: str | None,
    size_bytes: int | None,
    page_count: int | None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO book_validation_log (id, user_email, book_id, accepted, score, file_name, "
            "file_sha256, size_bytes, page_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id("val"), user_email, book_id, int(accepted), score,
             (file_name or "")[:255], file_sha256, size_bytes, page_count, now_iso()),
        )
