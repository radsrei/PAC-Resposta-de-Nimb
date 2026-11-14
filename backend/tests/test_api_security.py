"""
CI-07 Conexão com a API: saúde, contratos públicos e proteções HTTP.

- /api/health responde e não expõe dados sensíveis;
- Swagger/OpenAPI desligados (ENABLE_DOCS=false, padrão de produção);
- TODA rota /api fora da lista pública exige login (varredura automática das rotas:
  uma rota nova sem `Depends(require_user)` quebra o CI);
- cabeçalhos de segurança, CSRF por Origin, CORS, limite de corpo (pentest V-02),
  erro 500 sem detalhes internos.
"""

import importlib
import pkgutil
import re

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import app
from conftest import ALLOWED_ORIGIN

PUBLIC_ROUTES = {
    ("GET", "/api/health"),
    ("GET", "/api/auth/config"),
    ("POST", "/api/auth/google"),
    ("POST", "/api/auth/logout"),
}


def _api_routes():
    """Todas as rotas de todos os APIRouter do pacote app.routers (módulos novos entram sozinhos)."""
    import app.routers as routers_pkg

    seen = set()
    for info in pkgutil.iter_modules(routers_pkg.__path__):
        module = importlib.import_module(f"app.routers.{info.name}")
        for router in vars(module).values():
            if not isinstance(router, APIRouter):
                continue
            for route in router.routes:
                if isinstance(route, APIRoute) and route.path.startswith("/api"):
                    for method in sorted(route.methods):
                        if (method, route.path) not in seen:
                            seen.add((method, route.path))
                            yield method, route.path


def test_health_responde_ok_sem_dados_sensiveis(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body) == {"status", "service", "rag_engine", "books_ready", "llm_connected"}


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_documentacao_da_api_desligada(client, path):
    assert client.get(path).status_code == 404


def test_lista_de_rotas_publicas_esta_atualizada():
    """Se uma rota pública sumir ou mudar de nome, a lista acima precisa ser revista."""
    routes = set(_api_routes())
    assert len(routes) > 30
    assert PUBLIC_ROUTES <= routes


@pytest.mark.parametrize("method, path", [r for r in _api_routes() if r not in PUBLIC_ROUTES])
def test_rotas_protegidas_exigem_login(client, method, path):
    url = re.sub(r"\{[^}]+\}", "teste", path)
    response = client.request(method, url)
    assert response.status_code == 401, f"{method} {path} respondeu {response.status_code} sem login"


def test_cabecalhos_de_seguranca(client):
    headers = client.get("/api/health").headers
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert headers["cache-control"] == "no-store"
    assert "default-src 'none'" in headers["content-security-policy"]


def test_csrf_origem_desconhecida_e_bloqueada(client):
    response = client.post("/api/auth/logout", headers={"Origin": "https://site-malicioso.example"})
    assert response.status_code == 403


def test_csrf_origem_permitida_passa(client):
    response = client.post("/api/auth/logout", headers={"Origin": ALLOWED_ORIGIN})
    assert response.status_code == 200


def test_cors_libera_so_origens_configuradas(client):
    preflight = {"Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"}
    ok = client.options("/api/auth/google", headers={"Origin": ALLOWED_ORIGIN, **preflight})
    assert ok.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert ok.headers.get("access-control-allow-credentials") == "true"

    evil = client.options("/api/auth/google", headers={"Origin": "https://evil.example", **preflight})
    assert "access-control-allow-origin" not in evil.headers


def test_corpo_acima_de_128kb_fora_do_upload_responde_413(client):
    response = client.post("/api/auth/google", content=b"{" + b" " * (129 * 1024) + b"}",
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 413


def test_content_length_invalido_responde_400(client):
    response = client.post("/api/auth/google", content=b"{}",
                           headers={"Content-Type": "application/json", "Content-Length": "abc"})
    assert response.status_code == 400


def test_erro_interno_nao_vaza_detalhes(monkeypatch):
    from app.routers import health

    def boom():
        raise RuntimeError("segredo: /app/data/secret.key")

    with TestClient(app, raise_server_exceptions=False) as c:
        monkeypatch.setattr(health.book_catalog, "load_catalog", boom)  # depois da subida (aquecimento)
        response = c.get("/api/health")
    assert response.status_code == 500
    assert response.json() == {"detail": "Erro interno do servidor."}
    assert "segredo" not in response.text
