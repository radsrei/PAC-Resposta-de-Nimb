"""
Middlewares de segurança HTTP.

- Cabeçalhos de segurança em todas as respostas (anti-clickjacking, anti-sniffing,
  sem cache de dados da API).
- Proteção CSRF: requisições que alteram dados (POST/PUT/PATCH/DELETE) vindas de
  navegador só são aceitas se a origem (`Origin`) estiver na lista permitida.
  Somado ao cookie SameSite=Strict, impede que outro site use a sessão do usuário.
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

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
