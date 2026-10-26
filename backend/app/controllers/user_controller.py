"""Administração de usuários (somente administradores)."""

import logging
from typing import Any

from app.controllers.auth_controller import public_user
from app.core.exceptions import AppError, NotFoundError
from app.core.security import normalize_email
from app.repositories import auth_repository, user_repository
from app.schemas.auth import AdminUserUpdate

logger = logging.getLogger("nimb.auth")


def _get_or_404(email: str) -> dict[str, Any]:
    user = user_repository.get(normalize_email(email))
    if user is None:
        raise NotFoundError("Usuário não encontrado.")
    return user


def _loses_admin(target: dict[str, Any], changes: dict[str, Any]) -> bool:
    return target["role"] == "admin" and target["is_active"] and (
        changes.get("role") == "user" or changes.get("is_active") is False
    )


def list_users() -> list[dict[str, Any]]:
    return [public_user(u) for u in user_repository.list_all()]


def update_user(admin: dict[str, Any], email: str, payload: AdminUserUpdate) -> dict[str, Any]:
    target = _get_or_404(email)
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)

    if target["email"] == admin["email"] and _loses_admin(target, changes):
        raise AppError("Você não pode remover o seu próprio acesso de administrador.")
    if _loses_admin(target, changes) and user_repository.count_active_admins() <= 1:
        raise AppError("O sistema precisa de pelo menos um administrador ativo.")

    updated = user_repository.update(target["email"], changes)
    if changes.get("is_active") is False:
        auth_repository.delete_user_sessions(target["email"])
    logger.info("Admin %s alterou %s: %s", admin["email"], target["email"], changes)
    return public_user(updated)


def delete_user(admin: dict[str, Any], email: str) -> None:
    target = _get_or_404(email)
    if target["email"] == admin["email"]:
        raise AppError("Para excluir a sua própria conta, use a opção na tela Minha Conta.")
    if _loses_admin(target, {"is_active": False}) and user_repository.count_active_admins() <= 1:
        raise AppError("O sistema precisa de pelo menos um administrador ativo.")
    user_repository.delete(target["email"])
    logger.info("Admin %s excluiu a conta %s", admin["email"], target["email"])
