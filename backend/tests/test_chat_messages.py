"""
CI-06 Envio de mensagem no chat/terminal (POST /api/rag/query) e histórico de conversas.

A busca nos livros (Chroma + Ollama) e a LLM (DeepSeek) são simuladas: aqui se valida
o fluxo da API — regras de acesso, validação do prompt, Regra Nimb (rolagem do caos),
gravação da pergunta e da resposta na sessão e isolamento entre usuários.
"""

import json

import pytest

from app.repositories import book_repository, llm_repository
from app.services import chaos, retrieval
from app.services.llm_client import LLMResult
from conftest import VECTOR_STORE, allow_email, login

BOOK_ID = "t20-teste"
PASSAGE = retrieval.Passage(
    book_id=BOOK_ID, book_title="Tormenta20 - Livro de Teste", title="Bola de Fogo",
    path="Magias > Arcanas", chapter="Magia", kind="text", page="190",
    text="Bola de Fogo: uma explosão de chamas causa 6d6 pontos de dano de fogo.", similarity=0.82,
)


@pytest.fixture
def ready(user_client, monkeypatch):
    """Usuário com livro liberado, banco "pronto" e uma conexão DeepSeek ativa."""
    book_dir = VECTOR_STORE / "books" / BOOK_ID
    book_dir.mkdir(parents=True)
    (book_dir / "manifest.json").write_text(json.dumps({"chroma_dir": "chroma-teste", "chunks": 1}))
    book_repository.grant_access("jogador@nimb.test", BOOK_ID, "sha", 1.0)
    llm_repository.create({
        "name": "DeepSeek (teste)", "provider": "deepseek", "model": "deepseek-chat", "base_url": None,
        "api_key": "sk-teste", "temperature": None, "max_tokens": None, "is_active": True,
    })

    calls = {"search": [], "answer": []}

    def fake_search(book_ids, question, *args, **kwargs):
        calls["search"].append((book_ids, question))
        return [PASSAGE]

    def fake_answer(connection, system, messages, level, hallucinate, is_refusal, question_started):
        calls["answer"].append({"system": system, "messages": messages, "hallucinate": hallucinate})
        llm = LLMResult("Bola de Fogo causa 6d6 de dano de fogo (p. 190).", "deepseek", "deepseek-chat", 42)
        return chaos.ChaosResult(llm=llm, level=level, harness_rounds=0, hallucinated=hallucinate)

    monkeypatch.setattr(retrieval, "search", fake_search)
    monkeypatch.setattr(chaos, "answer", fake_answer)
    return user_client, calls


def ask(client, prompt="Quanto de dano causa Bola de Fogo?", **extra):
    payload = {"prompt": prompt, "chaosLevel": 0, "useChaosRule": False, **extra}
    return client.post("/api/rag/query", json=payload)


# ---------------------------------------------------------------------------
# Envio da pergunta
# ---------------------------------------------------------------------------
def test_pergunta_sem_login_e_recusada(client):
    assert ask(client).status_code == 401


def test_pergunta_sem_livro_liberado_responde_428(user_client):
    response = ask(user_client)
    assert response.status_code == 428


def test_pergunta_sem_conexao_llm_responde_409(user_client):
    book_dir = VECTOR_STORE / "books" / BOOK_ID
    book_dir.mkdir(parents=True)
    (book_dir / "manifest.json").write_text('{"chroma_dir": "x"}')
    book_repository.grant_access("jogador@nimb.test", BOOK_ID, "sha", 1.0)
    assert ask(user_client).status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {"prompt": "", "chaosLevel": 0, "useChaosRule": False},
        {"prompt": "x" * 4001, "chaosLevel": 0, "useChaosRule": False},
        {"prompt": "oi", "chaosLevel": 4, "useChaosRule": False},
        {"prompt": "oi", "chaosLevel": 0},
    ],
)
def test_payload_invalido_responde_422(ready, payload):
    client, calls = ready
    assert client.post("/api/rag/query", json=payload).status_code == 422
    assert calls["answer"] == []


def test_pergunta_valida_devolve_resposta_com_livro_e_pagina(ready):
    client, calls = ready
    response = ask(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["answer"].startswith("Bola de Fogo")
    assert body["bookTitle"] == "Tormenta20 - Livro de Teste"
    assert body["page"] == "190"
    assert body["similarity"] == "82.0%"
    assert body["sources"][0]["title"] == "Bola de Fogo"
    assert body["provider"] == "deepseek"
    assert "Bola de Fogo: uma explosão" in calls["answer"][0]["system"]  # trecho entrou no prompt


def test_mensagens_ficam_gravadas_na_sessao(ready):
    client, _ = ready
    body = ask(client).json()
    session_id = body["sessionId"]

    sessions = client.get("/api/sessions").json()
    assert [s["id"] for s in sessions] == [session_id]
    assert sessions[0]["title"] == "Quanto de dano causa Bola de Fogo?"

    messages = client.get(f"/api/sessions/{session_id}/messages").json()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[1]["metadata"]["page"] == "190"


def test_continuacao_envia_historico_para_a_llm(ready):
    client, calls = ready
    session_id = ask(client).json()["sessionId"]
    response = ask(client, prompt="E se eu gastar mais PM?", sessionId=session_id)
    assert response.status_code == 200
    roles = [m["role"] for m in calls["answer"][1]["messages"]]
    assert roles == ["user", "assistant", "user"]
    assert "Bola de Fogo" in calls["search"][1][1]  # a pergunta anterior entra na busca


def test_pergunta_fora_do_tema_e_recusada_sem_chamar_a_llm(ready, monkeypatch):
    client, calls = ready
    monkeypatch.setattr(retrieval, "search", lambda *a, **k: [])
    response = ask(client, prompt="Qual a capital da França?")
    assert response.status_code == 422
    assert calls["answer"] == []
    assert client.get("/api/sessions").json() == []  # nada gravado


def test_falha_da_llm_nao_grava_mensagem(ready, monkeypatch):
    client, _ = ready
    from app.core.exceptions import LLMError

    def broken(*args, **kwargs):
        raise LLMError("Conta do DeepSeek sem saldo.")

    monkeypatch.setattr(chaos, "answer", broken)
    response = ask(client)
    assert response.status_code == 502
    assert client.get("/api/sessions").json() == []


# ---------------------------------------------------------------------------
# Regra Nimb (rolagem do caos)
# ---------------------------------------------------------------------------
def test_regra_nimb_exige_rolagem(ready):
    client, _ = ready
    assert ask(client, useChaosRule=True).status_code == 400


def test_regra_nimb_com_rolagem_valida(ready):
    client, calls = ready
    prompt = "Quanto de dano causa Bola de Fogo?"
    roll = client.post("/api/rag/roll", json={"prompt": prompt, "chaosLevel": 1}).json()
    response = ask(client, prompt=prompt, chaosLevel=1, useChaosRule=True, rollToken=roll["rollToken"])
    assert response.status_code == 200
    assert calls["answer"][0]["hallucinate"] is roll["hallucinated"]


def test_rolagem_de_outra_pergunta_e_recusada(ready):
    client, _ = ready
    roll = client.post("/api/rag/roll", json={"prompt": "uma pergunta", "chaosLevel": 1}).json()
    response = ask(client, prompt="outra pergunta bem diferente", chaosLevel=1,
                   useChaosRule=True, rollToken=roll["rollToken"])
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Conversas
# ---------------------------------------------------------------------------
def test_crud_de_sessoes(user_client):
    created = user_client.post("/api/sessions", json={"title": "Mesa de sábado"})
    assert created.status_code == 201
    session_id = created.json()["id"]

    renamed = user_client.patch(f"/api/sessions/{session_id}", json={"title": "Mesa de domingo"})
    assert renamed.json()["title"] == "Mesa de domingo"

    assert user_client.delete(f"/api/sessions/{session_id}").status_code == 204
    assert user_client.get(f"/api/sessions/{session_id}").status_code == 404


def test_usuario_nao_ve_conversa_de_outro(ready):
    client, _ = ready
    session_id = ask(client).json()["sessionId"]
    client.post("/api/auth/logout")

    allow_email("outro@nimb.test")
    login(client, "outro@nimb.test")
    assert client.get(f"/api/sessions/{session_id}").status_code == 404
    assert client.get(f"/api/sessions/{session_id}/messages").status_code == 404
    assert client.delete(f"/api/sessions/{session_id}").status_code == 404
    assert ask(client, sessionId=session_id).status_code in (404, 428)
