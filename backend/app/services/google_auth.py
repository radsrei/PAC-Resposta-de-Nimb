"""
Validação do login com Google (Google Identity Services).

O front recebe do Google um ID token (JWT assinado) e o envia ao backend. Aqui
o token é validado com a biblioteca oficial `google-auth`: assinatura com as
chaves públicas do Google, emissor, expiração e o público (`aud`), que precisa
ser o GOOGLE_CLIENT_ID deste sistema. Só e-mails verificados pelo Google são aceitos.
"""

from dataclasses import dataclass

from app.core.config import settings
from app.core.exceptions import AppError, UnauthorizedError


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str
    email: str
    name: str


def verify_google_credential(credential: str) -> GoogleIdentity:
    if not settings.google_client_id:
        raise AppError("Login com Google não está configurado neste servidor.")

    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError as exc:
        raise AppError("Pacote 'google-auth' não instalado. Rode: pip install google-auth requests") from exc

    try:
        claims = id_token.verify_oauth2_token(
            credential, google_requests.Request(), settings.google_client_id
        )
    except ValueError as exc:
        raise UnauthorizedError("Token do Google inválido ou expirado.") from exc

    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        raise UnauthorizedError("Token do Google com emissor inválido.")
    if not claims.get("email") or not claims.get("email_verified"):
        raise UnauthorizedError("A conta Google precisa ter um e-mail verificado.")

    email = claims["email"].strip().lower()
    return GoogleIdentity(
        sub=str(claims["sub"]),
        email=email,
        name=(claims.get("name") or email.split("@")[0])[:80],
    )
