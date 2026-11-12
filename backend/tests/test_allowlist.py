"""
CI-02 Validade do e-mail na lista de acesso (ALLOWLIST_ENABLED=true).

Regras (controllers/auth_controller.py e core/deps.py):
- e-mail fora da lista não cria conta nem sessão (403);
- e-mails de ADMIN_EMAILS entram sempre e viram administradores;
- a lista é aplicada a cada requisição: remover o e-mail derruba a sessão aberta;
- só administradores mantêm a lista; e-mails são normalizados e validados.
"""

import pytest

from app.controllers import auth_controller
from app.repositories import user_repository
from conftest import ADMIN_EMAIL, allow_email, login


def test_email_fora_da_lista_e_recusado_e_nao_cria_conta(client):
    response = login(client, "intruso@gmail.com")
    assert response.status_code == 403
    assert response.json()["detail"] == auth_controller.NOT_ALLOWED
    assert "set-cookie" not in response.headers
    assert user_repository.get("intruso@gmail.com") is None


def test_admin_de_admin_emails_entra_sem_estar_na_lista(client):
    response = login(client, ADMIN_EMAIL)
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


def test_email_liberado_entra_como_usuario_comum(client):
    allow_email("jogador@nimb.test")
    response = login(client, "jogador@nimb.test")
    assert response.status_code == 200
    assert response.json()["role"] == "user"


def test_email_com_maiusculas_casa_com_a_lista(client):
    allow_email("jogador@nimb.test")
    assert login(client, "  Jogador@NIMB.test ").status_code == 200


def test_admin_inclui_email_pela_rota_e_ele_passa_a_entrar(admin_client):
    response = admin_client.post("/api/admin/allowed-emails", json={"emails": ["Novo@Nimb.Test", "novo@nimb.test"]})
    assert response.status_code == 200
    emails = [e["email"] for e in response.json()["emails"]]
    assert emails == ["novo@nimb.test"]  # normalizado e sem duplicata

    admin_client.post("/api/auth/logout")
    assert login(admin_client, "novo@nimb.test").status_code == 200


@pytest.mark.parametrize("bad", ["sem-arroba", "a@b", "x@" + "a" * 260 + ".com", "duas@@nimb.test"])
def test_email_invalido_na_lista_e_recusado(admin_client, bad):
    response = admin_client.post("/api/admin/allowed-emails", json={"emails": [bad]})
    assert response.status_code == 400


def test_remover_da_lista_derruba_a_sessao_aberta(client):
    allow_email("jogador@nimb.test")
    login(client, "jogador@nimb.test")
    assert client.get("/api/auth/me").status_code == 200

    from app.repositories import allowlist_repository

    allowlist_repository.remove("jogador@nimb.test")  # um admin removeu o e-mail
    assert client.get("/api/auth/me").status_code == 401


def test_admin_remove_email_pela_rota(admin_client):
    allow_email("jogador@nimb.test")
    response = admin_client.delete("/api/admin/allowed-emails/jogador@nimb.test")
    assert response.status_code == 200
    assert admin_client.delete("/api/admin/allowed-emails/jogador@nimb.test").status_code == 404


def test_usuario_comum_nao_acessa_a_lista_nem_os_usuarios(user_client):
    assert user_client.get("/api/admin/allowed-emails").status_code == 403
    assert user_client.post("/api/admin/allowed-emails", json={"emails": ["x@nimb.test"]}).status_code == 403
    assert user_client.get("/api/admin/users").status_code == 403


def test_conta_desativada_nao_entra(client):
    allow_email("jogador@nimb.test")
    login(client, "jogador@nimb.test")
    client.post("/api/auth/logout")
    user_repository.update("jogador@nimb.test", {"is_active": 0})
    assert login(client, "jogador@nimb.test").status_code == 403


def test_cadastro_desligado_recusa_conta_nova(client, monkeypatch):
    monkeypatch.setattr(auth_controller, "settings", _settings_with(registration_enabled=False))
    allow_email("jogador@nimb.test")
    assert login(client, "jogador@nimb.test").status_code == 403


def _settings_with(**changes):
    from dataclasses import replace

    from app.core.config import settings

    return replace(settings, **changes)
