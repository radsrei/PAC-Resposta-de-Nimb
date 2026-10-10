"""Acesso a dados das tabelas `chat_sessions` e `chat_messages`."""

import json
from typing import Any

from app.db.database import get_connection, new_id, now_iso

_SESSION_SELECT = """
SELECT s.*,
       (SELECT COUNT(*) FROM chat_messages m WHERE m.session_id = s.id) AS message_count
FROM chat_sessions s
"""


def _message_to_dict(row) -> dict[str, Any]:
    data = dict(row)
    data["metadata"] = json.loads(data["metadata"]) if data["metadata"] else None
    return data


def list_sessions() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(_SESSION_SELECT + " ORDER BY s.updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def get_session(session_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(_SESSION_SELECT + " WHERE s.id = ?", (session_id,)).fetchone()
    return dict(row) if row else None


def create_session(title: str) -> dict[str, Any]:
    session_id = new_id("ses")
    ts = now_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (session_id, title, ts, ts),
        )
    return get_session(session_id)


def update_session(session_id: str, title: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now_iso(), session_id),
        )
    return get_session(session_id)


def delete_session(session_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    return cur.rowcount > 0


def delete_all_sessions() -> int:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM chat_sessions")
    return cur.rowcount


def list_messages(session_id: str, limit: int | None = None) -> list[dict[str, Any]]:
    """Mensagens em ordem cronológica. Com `limit`, retorna apenas as últimas N."""
    with get_connection() as conn:
        if limit:
            rows = conn.execute(
                "SELECT * FROM ("
                "  SELECT rowid AS seq, * FROM chat_messages WHERE session_id = ?"
                "  ORDER BY seq DESC LIMIT ?"
                ") ORDER BY seq",
                (session_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT rowid AS seq, * FROM chat_messages WHERE session_id = ? ORDER BY seq",
                (session_id,),
            ).fetchall()
    messages = [_message_to_dict(r) for r in rows]
    for m in messages:
        m.pop("seq", None)
    return messages


def add_message(
    session_id: str, role: str, content: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    message_id = new_id("msg")
    ts = now_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_messages (id, session_id, role, content, metadata, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                message_id, session_id, role, content,
                json.dumps(metadata, ensure_ascii=False) if metadata else None, ts,
            ),
        )
        conn.execute("UPDATE chat_sessions SET updated_at = ? WHERE id = ?", (ts, session_id))
    return {
        "id": message_id, "session_id": session_id, "role": role,
        "content": content, "metadata": metadata, "created_at": ts,
    }
