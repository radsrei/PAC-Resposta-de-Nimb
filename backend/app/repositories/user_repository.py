"""Acesso a dados da tabela `users`."""

from typing import Any

from app.db.database import get_connection, now_iso

# Colunas que podem ser alteradas por `update` (lista fixa: nomes de coluna
# nunca vêm do usuário, então a montagem do SQL abaixo é segura)
UPDATABLE = (
    "name", "password_hash", "google_sub", "role", "is_active",
    "must_change_password", "failed_attempts", "locked_until", "last_login_at",
)


def _to_dict(row) -> dict[str, Any] | None:
    if row is None:
        return None
    data = dict(row)
    data["is_active"] = bool(data["is_active"])
    data["must_change_password"] = bool(data["must_change_password"])
    return data


def get(email: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return _to_dict(row)


def get_by_google_sub(google_sub: str) -> dict[str, Any] | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
    return _to_dict(row)


def list_all() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    return [_to_dict(r) for r in rows]


def count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def count_active_admins() -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = 1"
        ).fetchone()[0]


def create(
    email: str,
    name: str,
    password_hash: str | None,
    role: str = "user",
    google_sub: str | None = None,
) -> dict[str, Any]:
    ts = now_iso()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (email, name, password_hash, google_sub, role, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email, name, password_hash, google_sub, role, ts, ts),
        )
    return get(email)


def update(email: str, changes: dict[str, Any]) -> dict[str, Any] | None:
    changes = {k: v for k, v in changes.items() if k in UPDATABLE}
    if changes:
        assignments = ", ".join(f"{column} = ?" for column in changes)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE users SET {assignments}, updated_at = ? WHERE email = ?",
                (*changes.values(), now_iso(), email),
            )
    return get(email)


def delete(email: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM users WHERE email = ?", (email,))
    return cur.rowcount > 0
