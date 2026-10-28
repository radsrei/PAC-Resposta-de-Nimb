"""
Criptografia simétrica (Fernet/AES) para dados sensíveis gravados no banco,
como as API keys das LLMs.

A chave vem de APP_SECRET_KEY ou, se não definida, de `data/secret.key`, que é
gerado na primeira execução. Se essa chave for perdida, as API keys salvas
precisam ser cadastradas de novo.
"""

import base64
import hashlib
import json
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)

_FERNET_PREFIX = "gAAAAA"


@lru_cache
def _fernet() -> Fernet:
    if settings.app_secret_key:
        key = base64.urlsafe_b64encode(hashlib.sha256(settings.app_secret_key.encode()).digest())
        return Fernet(key)

    key_file = settings.database_path.parent / "secret.key"
    if not key_file.exists():
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(Fernet.generate_key())
    return Fernet(key_file.read_bytes().strip())


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(_FERNET_PREFIX)


def encrypt(value: str | None) -> str | None:
    if not value:
        return None
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt(value: str | None) -> str | None:
    if not value:
        return None
    if not is_encrypted(value):
        return value  # valor legado gravado antes da criptografia
    try:
        return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken:
        logger.warning("Não foi possível descriptografar um valor (chave secreta diferente?)")
        return None


def seal(data: dict) -> str:
    """Token criptografado (e com data) para o front devolver depois sem poder alterar."""
    return _fernet().encrypt(json.dumps(data).encode("utf-8")).decode("ascii")


def unseal(token: str, ttl: int) -> dict | None:
    """Conteúdo de um token de `seal`, ou None se for inválido ou tiver mais de `ttl` segundos."""
    try:
        return json.loads(_fernet().decrypt(token.encode("ascii"), ttl=ttl))
    except (InvalidToken, ValueError):
        return None
