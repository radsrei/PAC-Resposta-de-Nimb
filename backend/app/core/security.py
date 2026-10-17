"""
Funções de segurança: tokens de sessão e normalização de e-mail.

- Tokens de sessão: aleatórios de 256 bits. O banco guarda apenas o SHA-256 do
  token, então um vazamento do banco não expõe sessões.
- Não há senhas: o login é feito exclusivamente pelo Google.
"""

import hashlib
import secrets


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()
