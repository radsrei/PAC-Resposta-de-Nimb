"""Acesso a dados da tabela `llm_connections`."""

from typing import Any

from app.db.database import get_connection, new_id, now_iso

COLUMNS = (
    "name", "provider", "model", "base_url", "api_key",
    "temperature", "max_tokens", "is_active",
)


def _to_dict(row) -> dict[str, Any]:
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    return data


def list_all() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM llm_connections ORDER BY is_active DESC, created_at DESC"
        ).fetchall()
    return [_to_dict(r) for r in rows]


def get(connection_id: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM llm_connections WHERE id = ?", (connection_id,)
        ).fetchone()
    return _to_dict(row) if row else None


def get_active() -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM llm_connections WHERE is_active = 1 LIMIT 1"
        ).fetchone()
    return _to_dict(row) if row else None


def count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM llm_connections").fetchone()[0]


def create(data: dict[str, Any]) -> dict[str, Any]:
    connection_id = new_id("llm")
    ts = now_iso()
    with get_connection() as conn:
        # Apenas uma conexão pode estar ativa por vez
        if data.get("is_active"):
            conn.execute("UPDATE llm_connections SET is_active = 0")
        conn.execute(
            f"INSERT INTO llm_connections (id, {', '.join(COLUMNS)}, created_at, updated_at) "
            f"VALUES (?, {', '.join('?' for _ in COLUMNS)}, ?, ?)",
            (connection_id, *(data.get(c) for c in COLUMNS), ts, ts),
        )
    return get(connection_id)


def update(connection_id: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    changes = {k: v for k, v in changes.items() if k in COLUMNS}
    with get_connection() as conn:
        if changes.get("is_active"):
            conn.execute("UPDATE llm_connections SET is_active = 0")
        if changes:
            assignments = ", ".join(f"{k} = ?" for k in changes)
            conn.execute(
                f"UPDATE llm_connections SET {assignments}, updated_at = ? WHERE id = ?",
                (*changes.values(), now_iso(), connection_id),
            )
    return get(connection_id)


def delete(connection_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM llm_connections WHERE id = ?", (connection_id,))
    return cur.rowcount > 0
