"""
Limite de requisições em memória (janela deslizante) por IP.

Usado nas rotas de autenticação para dificultar força bruta e abuso da
recuperação de senha. Por ser em memória, vale por processo da API.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Request

from app.core.config import settings
from app.core.exceptions import TooManyRequestsError


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= now - self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                retry_after = int(self.window - (now - hits[0])) + 1
                raise TooManyRequestsError(
                    "Muitas tentativas em pouco tempo. Aguarde e tente novamente.",
                    retry_after=retry_after,
                )
            hits.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


auth_limiter = RateLimiter(settings.auth_rate_limit_per_minute)


def client_ip(request: Request) -> str:
    # X-Forwarded-For não é considerado: pode ser forjado pelo cliente.
    return request.client.host if request.client else "unknown"


def limit_auth(request: Request) -> None:
    """Dependência FastAPI: aplica o limite por IP e por rota."""
    auth_limiter.check(f"{client_ip(request)}:{request.url.path}")
