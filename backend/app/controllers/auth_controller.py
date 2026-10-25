"""
Regras de negócio da autenticação.

O único método de login é o Google: não há cadastro com e-mail e senha. A conta
é criada no primeiro login com Google (se REGISTRATION_ENABLED=true). Fluxos:
login com Google, logout, edição de perfil e exclusão de conta.
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError, ForbiddenError, UnauthorizedError
from app.core.security import generate_token, hash_token
from app.db.database import now, now_iso
from app.repositories import auth_repository, user_repository
from app.services.google_auth import verify_google_credential

logger = logging.getLogger("nimb.auth")


@dataclass(frozen=True)
class LoginResult:
    user: dict[str, Any]
    token: str
    # None = cookie de sessão do navegador (some ao fechar)
    max_age: int | None


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Dados seguros para devolver ao front."""
    return {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "google_linked": bool(user["google_sub"]),
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
    }


def auth_config() -> dict[str, Any]:
    return {"google_client_id": settings.google_client_id}


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------
def _role_for_new_user(email: str) -> str:
    if email in settings.admin_emails:
        return "admin"
    if settings.first_user_is_admin and user_repository.count() == 0:
        return "admin"
    return "user"


def _start_session(user: dict[str, Any], remember: bool, ip: str, user_agent: str | None) -> LoginResult:
    token = generate_token()
    ttl = timedelta(days=settings.remember_me_days) if remember else timedelta(hours=settings.session_ttl_hours)
    auth_repository.create_session(
        hash_token(token), user["email"], (now() + ttl).isoformat(), ip, user_agent
    )
    user = user_repository.update(user["email"], {"last_login_at": now_iso()})
    return LoginResult(
        user=public_user(user),
        token=token,
        max_age=int(ttl.total_seconds()) if remember else None,
    )


# ---------------------------------------------------------------------------
# Fluxos
# ---------------------------------------------------------------------------
def login_google(credential: str, remember: bool, ip: str, user_agent: str | None) -> LoginResult:
    auth_repository.purge_expired()
    identity = verify_google_credential(credential)
    user = user_repository.get_by_google_sub(identity.sub) or user_repository.get(identity.email)

    if user is None:
        if not settings.registration_enabled:
            raise ForbiddenError("O cadastro de novas contas está desativado.")
        user = user_repository.create(
            identity.email, identity.name, _role_for_new_user(identity.email), google_sub=identity.sub,
        )
        logger.info("Conta criada via Google: %s (%s)", identity.email, user["role"])
    else:
        if user["google_sub"] and user["google_sub"] != identity.sub:
            raise UnauthorizedError("Este e-mail está vinculado a outra conta Google.")
        if not user["is_active"]:
            raise ForbiddenError("Conta desativada. Procure um administrador.")
        if not user["google_sub"]:
            # Conta antiga (criada com e-mail e senha): o Google confirmou a
            # posse do e-mail, então ela é vinculada a esta conta Google
            user = user_repository.update(user["email"], {"google_sub": identity.sub})
        if user["role"] != "admin" and user["email"] in settings.admin_emails:
            user = user_repository.update(user["email"], {"role": "admin"})
            logger.info("Conta promovida a administradora (ADMIN_EMAILS): %s", user["email"])
    return _start_session(user, remember, ip, user_agent)


def logout(token_hash: str) -> None:
    auth_repository.delete_session(token_hash)


def logout_other_sessions(user: dict[str, Any]) -> int:
    return auth_repository.delete_user_sessions(user["email"], except_token_hash=user["token_hash"])


def update_profile(user: dict[str, Any], name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise AppError("Informe seu nome.")
    return public_user(user_repository.update(user["email"], {"name": name}))


def delete_account(user: dict[str, Any]) -> None:
    if user["role"] == "admin" and user_repository.count_active_admins() <= 1:
        raise AppError("Você é o único administrador. Promova outro usuário antes de excluir sua conta.")
    user_repository.delete(user["email"])  # sessões e conversas apagadas em cascata
    logger.info("Conta excluída pelo próprio usuário: %s", user["email"])
