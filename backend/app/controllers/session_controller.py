"""Regras de negócio das sessões de conversa e suas mensagens."""

from typing import Any

from app.core.exceptions import NotFoundError
from app.repositories import session_repository


def list_sessions() -> list[dict[str, Any]]:
    return session_repository.list_sessions()


def get_session_or_404(session_id: str) -> dict[str, Any]:
    session = session_repository.get_session(session_id)
    if session is None:
        raise NotFoundError(f"Sessão '{session_id}' não encontrada.")
    return session


def get_session_detail(session_id: str) -> dict[str, Any]:
    session = get_session_or_404(session_id)
    return {**session, "messages": session_repository.list_messages(session_id)}


def list_messages(session_id: str) -> list[dict[str, Any]]:
    get_session_or_404(session_id)
    return session_repository.list_messages(session_id)


def create_session(title: str | None) -> dict[str, Any]:
    return session_repository.create_session((title or "").strip() or "Nova sinapse")


def rename_session(session_id: str, title: str) -> dict[str, Any]:
    get_session_or_404(session_id)
    return session_repository.update_session(session_id, title.strip())


def delete_session(session_id: str) -> None:
    get_session_or_404(session_id)
    session_repository.delete_session(session_id)


def delete_all_sessions() -> int:
    return session_repository.delete_all_sessions()
