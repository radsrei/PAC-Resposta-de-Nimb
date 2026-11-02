"""Acesso a dados de `treasure_rolls` (histórico de sorteios de tesouro de cada usuário)."""

import json
from typing import Any

from app.db.database import get_connection, new_id, now_iso


def add(user_email: str, result: dict[str, Any]) -> dict[str, Any]:
    creature = (result.get("creature") or {}).get("name")
    record = {"id": new_id("tes"), "created_at": now_iso()}
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO treasure_rolls (id, user_email, book_id, creature, nd, treasure_type, total_value, result, "
            "created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record["id"], user_email, result["book_id"], creature, result["nd"], result["treasure_type"],
             result["total_value"], json.dumps(result, ensure_ascii=False), record["created_at"]),
        )
    return record


def list_recent(user_email: str, limit: int) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, result, created_at FROM treasure_rolls WHERE user_email = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_email, limit),
        ).fetchall()
    return [{**json.loads(r["result"]), "id": r["id"], "created_at": r["created_at"]} for r in rows]
