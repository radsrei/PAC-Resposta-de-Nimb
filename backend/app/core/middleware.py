"""
Middlewares de segurança HTTP.

- Cabeçalhos de segurança em todas as respostas (anti-clickjacking, anti-sniffing,
  sem cache de dados da API).
- Proteção CSRF: requisições que alteram dados (POST/PUT/PATCH/DELETE) vindas de
  navegador só são aceitas se a origem (`Origin`) estiver na lista permitida.
  Somado ao cookie SameSite=Strict, impede que outro site use a sessão do usuário.
- Limite do corpo da requisição (pentest V-02): o FastAPI lê e interpreta o corpo
  antes de checar login e limite de requisições. Aqui o corpo é recusado antes:
  pelo Content-Length, ou cortado no meio do envio quando passa do limite. O upload
  do livro também exige uma sessão válida antes de qualquer byte ser lido.
  O Caddy aplica os mesmos limites na frente (deploy/Caddyfile).
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import settings
from app.core.security import hash_token
from app.repositories import auth_repository

UPLOAD_PATH = "/api/rag/upload"
# Maior corpo legítimo fora do upload: prompt de 4000 caracteres com escapes \uXXXX (~48 KB)
BODY_MAX_BYTES = 128 * 1024
# PDF de até BOOK_UPLOAD_MAX_MB + margem do multipart
UPLOAD_MAX_BYTES = (settings.book_upload_max_mb + 1) * 1024 * 1024

_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method not in _SAFE_METHODS and path.startswith("/api/"):
            origin = request.headers.get("origin")
            if origin and origin not in settings.cors_origins:
                return JSONResponse(
                    status_code=403,
                    content={"detail": "Origem da requisição não permitida."},
                )

        response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        if path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            # A API só devolve JSON: bloqueia execução de qualquer conteúdo
            response.headers.setdefault(
                "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
            )
        if settings.cookie_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


class BodyLimitMiddleware:
    """Recusa corpos acima do limite da rota (413) sem lê-los inteiros."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        is_upload = scope["path"] == UPLOAD_PATH
        limit = UPLOAD_MAX_BYTES if is_upload else BODY_MAX_BYTES

        content_length = request.headers.get("content-length")
        if content_length is not None:
            if not content_length.isdigit():
                await _reject(scope, receive, send, 400, "Content-Length inválido.")
                return
            if int(content_length) > limit:
                await _reject(scope, receive, send, 413, _too_large(is_upload))
                return

        if is_upload and request.method == "POST" and not await _has_valid_session(request):
            await _reject(scope, receive, send, 401, "Faça login para continuar.")
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Corpo sem Content-Length (chunked) ou com valor falso: corta a leitura.
                    # O FastAPI repassa a HTTPException como resposta 413.
                    raise HTTPException(status_code=413, detail=_too_large(is_upload))
            return message

        await self.app(scope, limited_receive, send)


async def _has_valid_session(request: Request) -> bool:
    token = request.cookies.get(settings.session_cookie_name)
    if not token or len(token) > 200:
        return False
    return await run_in_threadpool(auth_repository.get_valid_session, hash_token(token)) is not None


def _too_large(is_upload: bool) -> str:
    if is_upload:
        return f"Arquivo maior que o limite de {settings.book_upload_max_mb} MB."
    return "Requisição grande demais."


async def _reject(scope: Scope, receive: Receive, send: Send, status: int, detail: str):
    response = JSONResponse(status_code=status, content={"detail": detail}, headers={"Connection": "close"})
    await response(scope, receive, send)
