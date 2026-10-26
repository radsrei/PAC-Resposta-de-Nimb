"""Regras de negócio das conversas do usuário logado e suas mensagens."""

from typing import Any

from app.core.exceptions import NotFoundError
from app.repositories import session_repository


def list_sessions(user_email: str) -> list[dict[str, Any]]:
    return session_repository.list_sessions(user_email)


def get_session_or_404(user_email: str, session_id: str) -> dict[str, Any]:
    session = session_repository.get_session(user_email, session_id)
    if session is None:
        # Mesma resposta para "não existe" e "é de outro usuário"
        raise NotFoundError(f"Sessão '{session_id}' não encontrada.")
    return session


def get_session_detail(user_email: str, session_id: str) -> dict[str, Any]:
    session = get_session_or_404(user_email, session_id)
    return {**session, "messages": session_repository.list_messages(session_id)}


def list_messages(user_email: str, session_id: str) -> list[dict[str, Any]]:
    get_session_or_404(user_email, session_id)
    return session_repository.list_messages(session_id)


def create_session(user_email: str, title: str | None) -> dict[str, Any]:
    return session_repository.create_session(user_email, (title or "").strip() or "Nova sinapse")


def rename_session(user_email: str, session_id: str, title: str) -> dict[str, Any]:
    get_session_or_404(user_email, session_id)
    return session_repository.update_session(user_email, session_id, title.strip())


def delete_session(user_email: str, session_id: str) -> None:
    get_session_or_404(user_email, session_id)
    session_repository.delete_session(user_email, session_id)


def delete_all_sessions(user_email: str) -> int:
    return session_repository.delete_all_sessions(user_email)
