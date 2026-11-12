"""
CI-03 Conexão com o DeepSeek.

- Cliente (services/llm_client.py) com o HTTP simulado: corpo enviado, cabeçalho de
  autenticação e tradução de cada erro do provedor (401, 402, 429, 5xx, timeout).
- Rotas /api/llm: só admin gerencia conexões, a API key nunca volta inteira, o botão
  "Testar conexão" devolve ok/erro sem estourar 500.
- Teste ao vivo (marcador live_deepseek): roda só com DEEPSEEK_API_KEY definida.
"""

import os

import httpx
import pytest

from app.core.exceptions import LLMError
from app.services import llm_client

CONNECTION = {
    "name": "DeepSeek teste",
    "provider": "deepseek",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "api_key": "sk-teste-1234567890", # gitleaks:allow
    "temperature": 0.2,
    "max_tokens": 50,
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("sem JSON")
        return self._payload


def _ok(content="Conexão estabelecida."):
    return FakeResponse(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture
def http_post(monkeypatch):
    calls = []
    state = {"response": _ok()}

    def fake_post(url, json=None, headers=None, timeout=None):
        calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if isinstance(state["response"], Exception):
            raise state["response"]
        return state["response"]

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    return state, calls


def test_chamada_monta_requisicao_compativel_com_openai(http_post):
    state, calls = http_post
    result = llm_client.generate(CONNECTION, "sistema", [{"role": "user", "content": "oi"}], timeout=10)

    assert result.text == "Conexão estabelecida."
    assert result.provider == "deepseek"
    call = calls[0]
    assert call["url"] == "https://api.deepseek.com/chat/completions"
    assert call["headers"] == {"Authorization": "Bearer sk-teste-1234567890"}
    assert call["timeout"] == 10
    assert call["json"]["messages"][0] == {"role": "system", "content": "sistema"}
    assert call["json"]["temperature"] == 0.2
    assert call["json"]["max_tokens"] == 50


@pytest.mark.parametrize(
    "status, expected",
    [
        (401, "API key do DeepSeek inválida"),
        (402, "sem saldo"),
        (429, "Limite de requisições"),
        (500, "HTTP 500"),
    ],
)
def test_erros_do_provedor_viram_mensagens_claras(http_post, status, expected):
    state, _ = http_post
    state["response"] = FakeResponse(status, {"error": {"message": "falhou"}})
    with pytest.raises(LLMError, match=expected):
        llm_client.generate(CONNECTION, "s", [{"role": "user", "content": "oi"}])


def test_timeout_vira_llm_timeout_error(http_post):
    state, _ = http_post
    state["response"] = httpx.ReadTimeout("lento")
    with pytest.raises(llm_client.LLMTimeoutError):
        llm_client.generate(CONNECTION, "s", [{"role": "user", "content": "oi"}], timeout=1)


def test_falha_de_rede_vira_llm_error(http_post):
    state, _ = http_post
    state["response"] = httpx.ConnectError("sem rede")
    with pytest.raises(LLMError, match="Não foi possível conectar"):
        llm_client.generate(CONNECTION, "s", [{"role": "user", "content": "oi"}])


@pytest.mark.parametrize("response", [_ok("   "), FakeResponse(200, {"choices": []}), FakeResponse(200, None)])
def test_resposta_vazia_ou_fora_do_formato_e_recusada(http_post, response):
    state, _ = http_post
    state["response"] = response
    with pytest.raises(LLMError):
        llm_client.generate(CONNECTION, "s", [{"role": "user", "content": "oi"}])


def test_conexao_sem_api_key_nao_chama_o_provedor(http_post):
    _, calls = http_post
    with pytest.raises(LLMError, match="não possui API key"):
        llm_client.generate({**CONNECTION, "api_key": None}, "s", [{"role": "user", "content": "oi"}])
    assert calls == []


def test_provedor_desativado_e_recusado(http_post):
    with pytest.raises(LLMError, match="desativado"):
        llm_client.generate({**CONNECTION, "provider": "ollama"}, "s", [{"role": "user", "content": "oi"}])


# ---------------------------------------------------------------------------
# Rotas /api/llm
# ---------------------------------------------------------------------------
NEW_CONNECTION = {"name": "DeepSeek", "provider": "deepseek", "apiKey": "sk-abcdefghijklmnop"}


def test_admin_cria_conexao_e_a_chave_volta_mascarada(admin_client):
    response = admin_client.post("/api/llm/connections", json=NEW_CONNECTION)
    assert response.status_code == 201
    body = response.json()
    assert body["isActive"] is True  # a primeira conexão nasce ativa
    assert body["hasApiKey"] is True
    assert body["apiKeyPreview"] == "sk-a••••mnop"
    assert "sk-abcdefghijklmnop" not in response.text


def test_chave_fica_criptografada_no_banco(admin_client):
    admin_client.post("/api/llm/connections", json=NEW_CONNECTION)
    import sqlite3

    from app.core.config import settings

    stored = sqlite3.connect(settings.database_path).execute("SELECT api_key FROM llm_connections").fetchone()[0]
    assert stored and "sk-abcdefghijklmnop" not in stored


def test_deepseek_sem_api_key_e_recusado(admin_client):
    response = admin_client.post("/api/llm/connections", json={"name": "x", "provider": "deepseek"})
    assert response.status_code == 400


def test_usuario_comum_nao_gerencia_conexoes(user_client):
    assert user_client.get("/api/llm/connections").status_code == 403
    assert user_client.post("/api/llm/connections", json=NEW_CONNECTION).status_code == 403
    assert user_client.get("/api/llm/providers").status_code == 200
    assert user_client.get("/api/llm/connections/active").status_code == 200


def test_testar_conexao_devolve_ok(admin_client, http_post):
    connection_id = admin_client.post("/api/llm/connections", json=NEW_CONNECTION).json()["id"]
    response = admin_client.post(f"/api/llm/connections/{connection_id}/test")
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["sample"] == "Conexão estabelecida."


def test_testar_conexao_com_chave_invalida_devolve_erro_sem_500(admin_client, http_post):
    state, _ = http_post
    state["response"] = FakeResponse(401, {"error": {"message": "invalid key"}})
    connection_id = admin_client.post("/api/llm/connections", json=NEW_CONNECTION).json()["id"]
    response = admin_client.post(f"/api/llm/connections/{connection_id}/test")
    assert response.status_code == 200
    assert response.json() == {
        "ok": False, "provider": "deepseek", "model": "deepseek-chat",
        "latencyMs": None, "sample": None, "error": "API key do DeepSeek inválida.",
    }


def test_health_informa_se_ha_llm_conectada(admin_client):
    assert admin_client.get("/api/health").json()["llm_connected"] is False
    admin_client.post("/api/llm/connections", json=NEW_CONNECTION)
    assert admin_client.get("/api/health").json()["llm_connected"] is True


# ---------------------------------------------------------------------------
# Ao vivo (não roda por padrão)
# ---------------------------------------------------------------------------
def _live_api_key() -> str | None:
    """DEEPSEEK_API_KEY (CI) ou LLM_DEEPSEEK_API do backend/.env, lido como a API lê (sem aspas/espaços)."""
    from dotenv import dotenv_values

    from conftest import BACKEND_DIR

    key = os.environ.get("DEEPSEEK_API_KEY") or dotenv_values(BACKEND_DIR / ".env").get("LLM_DEEPSEEK_API")
    key = (key or "").strip().strip("\"'").strip()
    return key or None


@pytest.mark.live_deepseek
def test_deepseek_real_responde():
    api_key = _live_api_key()
    if not api_key:
        pytest.skip("Sem chave: defina DEEPSEEK_API_KEY ou LLM_DEEPSEEK_API no backend/.env")
    try:
        result = llm_client.generate(
            {**CONNECTION, "api_key": api_key, "temperature": 0, "max_tokens": 20},
            "Responda de forma curtíssima.",
            [{"role": "user", "content": "Responda apenas: ok"}],
            timeout=60,
        )
    except LLMError as exc:
        # pytrace=False: o traceback mostraria a chave nos argumentos das funções
        pytest.fail(f"DeepSeek recusou: {exc.message}", pytrace=False)
    assert result.text
    assert result.latency_ms > 0
