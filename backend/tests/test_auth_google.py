"""
CI-01 Login com Google.

Duas camadas:
- `verify_google_credential` (services/google_auth.py) com a biblioteca do Google
  simulada: assinatura inválida, emissor errado, e-mail não verificado, sem Client ID;
- rota POST /api/auth/google com o login simulado (conftest): cookie de sessão,
  /me, logout, "manter conectado" e limite de tentativas.
"""

import pytest
from google.oauth2 import id_token

from app.core.config import settings
from app.core.exceptions import AppError, UnauthorizedError
from app.services import google_auth
from conftest import ADMIN_EMAIL, login

VALID_CLAIMS = {
    "iss": "https://accounts.google.com",
    "sub": "1234567890",
    "email": "Jogador@Nimb.Test",
    "email_verified": True,
    "name": "Jogador",
}


def _patch_google(monkeypatch, claims=None, error=None):
    def fake(credential, request, audience):
        assert audience == settings.google_client_id  # o público do token é o Client ID deste sistema
        if error:
            raise error
        return dict(claims)

    monkeypatch.setattr(id_token, "verify_oauth2_token", fake)


# ---------------------------------------------------------------------------
# Validação do ID token
# ---------------------------------------------------------------------------
def test_token_valido_devolve_identidade_com_email_normalizado(monkeypatch):
    _patch_google(monkeypatch, VALID_CLAIMS)
    identity = google_auth.verify_google_credential("token")
    assert identity.email == "jogador@nimb.test"
    assert identity.sub == "1234567890"
    assert identity.name == "Jogador"


def test_token_com_assinatura_invalida_ou_expirado_e_recusado(monkeypatch):
    _patch_google(monkeypatch, error=ValueError("Token expired"))
    with pytest.raises(UnauthorizedError):
        google_auth.verify_google_credential("token")


@pytest.mark.parametrize("iss", ["https://evil.example.com", "", None])
def test_token_de_outro_emissor_e_recusado(monkeypatch, iss):
    _patch_google(monkeypatch, {**VALID_CLAIMS, "iss": iss})
    with pytest.raises(UnauthorizedError):
        google_auth.verify_google_credential("token")


@pytest.mark.parametrize("changes", [{"email_verified": False}, {"email": ""}, {"email": None}])
def test_conta_google_sem_email_verificado_e_recusada(monkeypatch, changes):
    _patch_google(monkeypatch, {**VALID_CLAIMS, **changes})
    with pytest.raises(UnauthorizedError):
        google_auth.verify_google_credential("token")


def test_sem_google_client_id_o_login_fica_desativado(monkeypatch):
    monkeypatch.setattr(google_auth, "settings", type("S", (), {"google_client_id": None})())
    with pytest.raises(AppError, match="não está configurado"):
        google_auth.verify_google_credential("token")


# ---------------------------------------------------------------------------
# Rota de login
# ---------------------------------------------------------------------------
def test_config_publica_expoe_so_o_client_id(client):
    response = client.get("/api/auth/config")
    assert response.status_code == 200
    assert response.json() == {"googleClientId": settings.google_client_id}


def test_login_cria_sessao_em_cookie_httponly_strict(client):
    response = login(client, ADMIN_EMAIL)
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == ADMIN_EMAIL
    assert body["role"] == "admin"
    assert body["googleLinked"] is True

    cookie = response.headers["set-cookie"].lower()
    assert f"{settings.session_cookie_name}=" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api" in cookie
    assert "max-age" not in cookie  # sem "manter conectado": cookie de sessão do navegador


def test_manter_conectado_define_validade_do_cookie(client):
    response = login(client, ADMIN_EMAIL, remember=True)
    assert response.status_code == 200
    assert f"max-age={settings.remember_me_days * 86400}" in response.headers["set-cookie"].lower()


def test_me_exige_sessao_e_devolve_usuario_logado(client):
    assert client.get("/api/auth/me").status_code == 401
    login(client, ADMIN_EMAIL)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == ADMIN_EMAIL


def test_credencial_invalida_responde_401_sem_criar_sessao(client):
    response = client.post("/api/auth/google", json={"credential": "token-forjado-123"})
    assert response.status_code == 401
    assert "set-cookie" not in response.headers


def test_payload_de_login_invalido_responde_422_sem_ecoar_o_token(client):
    response = client.post("/api/auth/google", json={"credential": "curto"})
    assert response.status_code == 422
    assert "curto" not in response.text  # o handler remove o valor recebido dos erros


def test_logout_encerra_a_sessao(client):
    login(client, ADMIN_EMAIL)
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_de_sessao_forjado_e_recusado(client):
    client.cookies.set(settings.session_cookie_name, "x" * 43, path="/api")
    assert client.get("/api/auth/me").status_code == 401


def test_limite_de_tentativas_de_login_por_ip(client):
    for _ in range(settings.auth_rate_limit_per_minute):
        client.post("/api/auth/google", json={"credential": "token-forjado-123"})
    response = client.post("/api/auth/google", json={"credential": "token-forjado-123"})
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
