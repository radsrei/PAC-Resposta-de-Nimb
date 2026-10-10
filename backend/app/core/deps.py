"""
Dependências FastAPI de autenticação/autorização.

- get_current_user: exige um cookie de sessão válido (401 se ausente/expirado).
- require_user:     idem, e bloqueia quem precisa trocar a senha (403).
- require_admin:    idem, e exige papel de administrador (403).
"""

from typing import Any

from fastapi import Depends, Request

from app.core.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import hash_token
from app.repositories import auth_repository, user_repository

CurrentUser = dict[str, Any]


def get_current_user(request: Request) -> CurrentUser:
    token = request.cookies.get(settings.session_cookie_name)
    if not token or len(token) > 200:
        raise UnauthorizedError("Faça login para continuar.")

    token_hash = hash_token(token)
    session = auth_repository.get_valid_session(token_hash)
    if session is None:
        raise UnauthorizedError("Sessão expirada. Faça login novamente.")

    user = user_repository.get(session["user_email"])
    if user is None or not user["is_active"]:
        auth_repository.delete_session(token_hash)
        raise UnauthorizedError("Sessão inválida. Faça login novamente.")

    user["token_hash"] = token_hash
    return user


def require_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if user["must_change_password"]:
        raise ForbiddenError("Troca de senha obrigatória antes de continuar.")
    return user


def require_admin(user: CurrentUser = Depends(require_user)) -> CurrentUser:
    if user["role"] != "admin":
        raise ForbiddenError("Acesso restrito a administradores.")
    return user
