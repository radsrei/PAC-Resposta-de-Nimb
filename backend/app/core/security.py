"""
Funções de segurança: hash de senha, tokens e validações.

- Senhas: scrypt (biblioteca padrão) com salt aleatório por usuário. Nunca são
  gravadas nem registradas em log em texto puro.
- Tokens (sessão e recuperação de senha): aleatórios de 256 bits. O banco guarda
  apenas o SHA-256 do token, então um vazamento do banco não expõe sessões.
"""

import base64
import hashlib
import hmac
import re
import secrets

from app.core.exceptions import AppError

# Parâmetros do scrypt (recomendação OWASP: N=2^17 é o ideal; 2^15 mantém o
# login rápido em máquinas de desenvolvimento com memória suficiente)
_SCRYPT_N = 2**15
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 128 * 1024 * 1024

PASSWORD_MIN_LENGTH = 5
PASSWORD_MAX_LENGTH = 30

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, maxmem=_SCRYPT_MAXMEM, dklen=32,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored_hash: str | None) -> bool:
    if not stored_hash:
        return False
    try:
        algorithm, n, r, p, salt, digest = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        candidate = hashlib.scrypt(
            password.encode("utf-8"), salt=_unb64(salt),
            n=int(n), r=int(r), p=int(p), maxmem=_SCRYPT_MAXMEM, dklen=32,
        )
    except (ValueError, TypeError):
        return False
    # Comparação em tempo constante (evita ataque de temporização)
    return hmac.compare_digest(candidate, _unb64(digest))


# Hash calculado uma vez para equalizar o tempo de resposta quando o e-mail não
# existe (evita descobrir contas cadastradas pelo tempo do login).
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def validate_email(email: str) -> str:
    email = normalize_email(email)
    if len(email) > 254 or not _EMAIL_RE.match(email):
        raise AppError("E-mail inválido.")
    return email


def validate_password_strength(password: str) -> None:
    if len(password) < PASSWORD_MIN_LENGTH:
        raise AppError(f"A senha deve ter pelo menos {PASSWORD_MIN_LENGTH} caracteres.")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise AppError(f"A senha deve ter no máximo {PASSWORD_MAX_LENGTH} caracteres.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AppError("A senha deve conter letras e números.")
