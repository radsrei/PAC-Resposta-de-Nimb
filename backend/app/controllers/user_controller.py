"""Administração de usuários e da lista de acesso (somente administradores)."""

import logging
import re
from typing import Any

from app.controllers.auth_controller import is_allowed, public_user
from app.core.config import settings
from app.core.exceptions import AppError, NotFoundError
from app.core.security import normalize_email
from app.repositories import allowlist_repository, auth_repository, user_repository
from app.schemas.auth import AdminUserUpdate

logger = logging.getLogger("nimb.auth")

_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


# ---------------------------------------------------------------------------
# Lista de acesso (ALLOWLIST_ENABLED)
# ---------------------------------------------------------------------------
def list_allowed() -> dict[str, Any]:
    return {"enabled": settings.allowlist_enabled, "emails": allowlist_repository.list_all()}


def add_allowed(admin: dict[str, Any], emails: list[str]) -> dict[str, Any]:
    cleaned = list(dict.fromkeys(normalize_email(e) for e in emails if e.strip()))
    invalid = [e for e in cleaned if len(e) > 254 or not _EMAIL.match(e)]
    if invalid:
        raise AppError(f"E-mail inválido: {', '.join(invalid[:5])}.")
    if not cleaned:
        raise AppError("Informe ao menos um e-mail.")
    added = allowlist_repository.add(cleaned, admin["email"])
    logger.info("Admin %s incluiu %d e-mail(s) na lista de acesso", admin["email"], added)
    return list_allowed()


def remove_allowed(admin: dict[str, Any], email: str) -> None:
    email = normalize_email(email)
    if not allowlist_repository.remove(email):
        raise NotFoundError("E-mail não está na lista de acesso.")
    user = user_repository.get(email)
    if user and not is_allowed(email, user["role"]):
        auth_repository.delete_user_sessions(email)  # sai na hora, sem esperar a sessão expirar
    logger.info("Admin %s removeu %s da lista de acesso", admin["email"], email)
