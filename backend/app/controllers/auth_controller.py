"""
Regras de negócio da autenticação.

Fluxos: cadastro, login (senha ou Google), logout, troca de senha, recuperação
de senha (token de uso único -> senha padrão com troca obrigatória), edição de
perfil e exclusão de conta.
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.exceptions import (
    AppError,
    ConflictError,
    ForbiddenError,
    TooManyRequestsError,
    UnauthorizedError,
)
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    PASSWORD_MIN_LENGTH,
    generate_token,
    hash_password,
    hash_token,
    normalize_email,
    validate_email,
    validate_password_strength,
    verify_password,
)
from app.db.database import iso_in, now, now_iso
from app.repositories import auth_repository, user_repository
from app.services.google_auth import verify_google_credential

logger = logging.getLogger("nimb.auth")

INVALID_CREDENTIALS = "E-mail ou senha inválidos."
FORGOT_PASSWORD_MESSAGE = (
    "Se o e-mail estiver cadastrado, um código de recuperação foi enviado. "
    "Ele vale por {minutes} minutos."
)


@dataclass(frozen=True)
class LoginResult:
    user: dict[str, Any]
    token: str
    # None = cookie de sessão do navegador (some ao fechar)
    max_age: int | None


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Dados seguros para devolver ao front (nunca inclui hash de senha)."""
    return {
        "email": user["email"],
        "name": user["name"],
        "role": user["role"],
        "is_active": user["is_active"],
        "must_change_password": user["must_change_password"],
        "has_password": bool(user["password_hash"]),
        "google_linked": bool(user["google_sub"]),
        "created_at": user["created_at"],
        "last_login_at": user["last_login_at"],
    }


def auth_config() -> dict[str, Any]:
    return {
        "google_client_id": settings.google_client_id,
        "registration_enabled": settings.registration_enabled,
        "password_min_length": PASSWORD_MIN_LENGTH,
    }


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
    user = user_repository.update(
        user["email"], {"last_login_at": now_iso(), "failed_attempts": 0, "locked_until": None}
    )
    return LoginResult(
        user=public_user(user),
        token=token,
        max_age=int(ttl.total_seconds()) if remember else None,
    )


def _ensure_not_locked(user: dict[str, Any]) -> None:
    locked_until = user.get("locked_until")
    if locked_until and locked_until > now_iso():
        remaining = datetime.fromisoformat(locked_until) - now()
        minutes = max(1, int(remaining.total_seconds() // 60) + 1)
        raise TooManyRequestsError(
            f"Conta bloqueada temporariamente por excesso de tentativas. "
            f"Tente novamente em {minutes} min.",
            retry_after=int(remaining.total_seconds()) + 1,
        )


def _register_failed_attempt(user: dict[str, Any]) -> None:
    attempts = user["failed_attempts"] + 1
    if attempts >= settings.max_failed_logins:
        user_repository.update(
            user["email"],
            {"failed_attempts": 0, "locked_until": iso_in(minutes=settings.lockout_minutes)},
        )
        logger.warning("Conta %s bloqueada por %s min após tentativas inválidas",
                       user["email"], settings.lockout_minutes)
        raise TooManyRequestsError(
            f"Conta bloqueada temporariamente por excesso de tentativas. "
            f"Tente novamente em {settings.lockout_minutes} min.",
            retry_after=settings.lockout_minutes * 60,
        )
    user_repository.update(user["email"], {"failed_attempts": attempts})


def apply_default_password(email: str) -> None:
    """Redefine para a senha padrão, exige troca e encerra todas as sessões."""
    user_repository.update(email, {
        "password_hash": hash_password(settings.default_reset_password),
        "must_change_password": True,
        "failed_attempts": 0,
        "locked_until": None,
    })
    auth_repository.delete_user_sessions(email)


def _deliver_reset_token(email: str, token: str) -> None:
    # Sem servidor de e-mail configurado, o código é exibido no console da API
    # (equivalente ao e-mail em ambiente de desenvolvimento). Ver Setup-Front-Tela.md.
    logger.warning(
        "\n================ RECUPERAÇÃO DE SENHA ================\n"
        "Usuário: %s\nCódigo:  %s\nValidade: %s minutos\n"
        "======================================================",
        email, token, settings.reset_token_ttl_minutes,
    )


# ---------------------------------------------------------------------------
# Fluxos
# ---------------------------------------------------------------------------
def register(name: str, email: str, password: str, ip: str, user_agent: str | None) -> LoginResult:
    if not settings.registration_enabled:
        raise ForbiddenError("O cadastro de novas contas está desativado.")
    email = validate_email(email)
    name = name.strip()
    if not name:
        raise AppError("Informe seu nome.")
    validate_password_strength(password)
    if password == settings.default_reset_password:
        raise AppError("Escolha uma senha diferente da senha padrão do sistema.")
    if user_repository.get(email):
        raise ConflictError("Já existe uma conta com este e-mail.")

    try:
        user = user_repository.create(email, name, hash_password(password), _role_for_new_user(email))
    except sqlite3.IntegrityError as exc:
        raise ConflictError("Já existe uma conta com este e-mail.") from exc
    logger.info("Conta criada: %s (%s)", email, user["role"])
    return _start_session(user, remember=False, ip=ip, user_agent=user_agent)


def login(email: str, password: str, remember: bool, ip: str, user_agent: str | None) -> LoginResult:
    auth_repository.purge_expired()
    user = user_repository.get(normalize_email(email))
    if user is None:
        verify_password(password, DUMMY_PASSWORD_HASH)  # mesmo tempo de resposta
        raise UnauthorizedError(INVALID_CREDENTIALS)

    _ensure_not_locked(user)
    if not verify_password(password, user["password_hash"]):
        _register_failed_attempt(user)
        raise UnauthorizedError(INVALID_CREDENTIALS)
    if not user["is_active"]:
        raise ForbiddenError("Conta desativada. Procure um administrador.")
    return _start_session(user, remember, ip, user_agent)


def login_google(credential: str, remember: bool, ip: str, user_agent: str | None) -> LoginResult:
    identity = verify_google_credential(credential)
    user = user_repository.get_by_google_sub(identity.sub) or user_repository.get(identity.email)

    if user is None:
        if not settings.registration_enabled:
            raise ForbiddenError("O cadastro de novas contas está desativado.")
        user = user_repository.create(
            identity.email, identity.name, None,
            _role_for_new_user(identity.email), google_sub=identity.sub,
        )
        logger.info("Conta criada via Google: %s (%s)", identity.email, user["role"])
    else:
        if user["google_sub"] and user["google_sub"] != identity.sub:
            raise UnauthorizedError("Este e-mail está vinculado a outra conta Google.")
        if not user["is_active"]:
            raise ForbiddenError("Conta desativada. Procure um administrador.")
        if not user["google_sub"]:
            # O Google confirmou a posse do e-mail: vincula à conta existente
            user = user_repository.update(user["email"], {"google_sub": identity.sub})
    return _start_session(user, remember, ip, user_agent)


def logout(token_hash: str) -> None:
    auth_repository.delete_session(token_hash)


def logout_other_sessions(user: dict[str, Any]) -> int:
    return auth_repository.delete_user_sessions(user["email"], except_token_hash=user["token_hash"])


def change_password(user: dict[str, Any], current_password: str | None, new_password: str) -> dict[str, Any]:
    if user["password_hash"]:
        if not current_password or not verify_password(current_password, user["password_hash"]):
            raise AppError("Senha atual incorreta.")
        if verify_password(new_password, user["password_hash"]):
            raise AppError("A nova senha deve ser diferente da atual.")
    validate_password_strength(new_password)
    if new_password == settings.default_reset_password:
        raise AppError("Escolha uma senha diferente da senha padrão do sistema.")

    updated = user_repository.update(user["email"], {
        "password_hash": hash_password(new_password),
        "must_change_password": False,
    })
    # Encerra as outras sessões (ex.: alguém que conhecia a senha antiga)
    auth_repository.delete_user_sessions(user["email"], except_token_hash=user["token_hash"])
    return public_user(updated)


def forgot_password(email: str) -> str:
    """Sempre devolve a mesma mensagem, exista o e-mail ou não (evita enumeração)."""
    user = user_repository.get(normalize_email(email))
    if user and user["is_active"]:
        token = generate_token()
        auth_repository.create_reset_token(
            hash_token(token), user["email"], iso_in(minutes=settings.reset_token_ttl_minutes)
        )
        _deliver_reset_token(user["email"], token)
    return FORGOT_PASSWORD_MESSAGE.format(minutes=settings.reset_token_ttl_minutes)


def reset_password(token: str) -> dict[str, str]:
    email = auth_repository.consume_reset_token(hash_token(token.strip()))
    user = user_repository.get(email) if email else None
    if user is None or not user["is_active"]:
        raise AppError("Código de recuperação inválido ou expirado.")
    apply_default_password(user["email"])
    logger.info("Senha redefinida para a senha padrão via recuperação: %s", user["email"])
    return {
        "message": "Senha redefinida para a senha padrão. Entre com ela e defina uma nova senha.",
        "temporary_password": settings.default_reset_password,
    }


def update_profile(user: dict[str, Any], name: str) -> dict[str, Any]:
    name = name.strip()
    if not name:
        raise AppError("Informe seu nome.")
    return public_user(user_repository.update(user["email"], {"name": name}))


def delete_account(user: dict[str, Any], password: str | None) -> None:
    if user["password_hash"] and (not password or not verify_password(password, user["password_hash"])):
        raise AppError("Senha incorreta.")
    if user["role"] == "admin" and user_repository.count_active_admins() <= 1:
        raise AppError("Você é o único administrador. Promova outro usuário antes de excluir sua conta.")
    user_repository.delete(user["email"])  # sessões e conversas apagadas em cascata
    logger.info("Conta excluída pelo próprio usuário: %s", user["email"])
