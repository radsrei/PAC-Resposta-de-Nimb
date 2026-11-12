"""
CI-04 Conexão com o Ollama (embeddings da pergunta, services/embeddings.py).

- Com o HTTP simulado (httpx.MockTransport): modelo presente/ausente, Ollama fora do
  ar, rota antiga /api/embeddings, normalização dos vetores e keep_alive enviado.
- Ao vivo (marcador live_ollama): Ollama real em OLLAMA_URL com um modelo pequeno
  (OLLAMA_TEST_MODEL, padrão all-minilm). No CI roda como service container.
"""

import json
import math
import os

import httpx
import pytest

from app.core.exceptions import EmbeddingError
from app.services import embeddings


def _install_transport(monkeypatch, handler):
    real_client = httpx.Client

    def factory(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr(embeddings.httpx, "Client", factory)


def _tags(*names):
    return httpx.Response(200, json={"models": [{"name": n} for n in names]})


def test_modelo_instalado_gera_embedding_normalizado(monkeypatch):
    seen = []

    def handler(request: httpx.Request):
        seen.append(request.url.path)
        if request.url.path == "/api/tags":
            return _tags("bge-m3:latest")
        body = json.loads(request.content)
        assert body["model"] == "bge-m3"
        assert body["keep_alive"] == -1  # OLLAMA_KEEP_ALIVE=-1 vira inteiro
        return httpx.Response(200, json={"embeddings": [[3.0, 4.0]]})

    _install_transport(monkeypatch, handler)
    embedder = embeddings.create_embedder("ollama", "bge-m3", ollama_url="http://ollama:11434")
    vector = embedder.embed_query("o que é uma bola de fogo?")

    assert seen == ["/api/tags", "/api/embed"]
    assert vector == pytest.approx([0.6, 0.8])
    assert math.isclose(sum(v * v for v in vector), 1.0)


def test_modelo_nao_baixado_da_instrucao_de_pull(monkeypatch):
    _install_transport(monkeypatch, lambda r: _tags("llama3:latest"))
    with pytest.raises(EmbeddingError, match="ollama pull bge-m3"):
        embeddings.create_embedder("ollama", "bge-m3")


def test_ollama_fora_do_ar_vira_503(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused")

    _install_transport(monkeypatch, handler)
    with pytest.raises(EmbeddingError) as exc:
        embeddings.create_embedder("ollama", "bge-m3")
    assert exc.value.status_code == 503
    assert "Ollama indisponível" in exc.value.message


def test_ollama_lento_vira_erro_de_tempo(monkeypatch):
    def handler(request):
        raise httpx.ReadTimeout("lento")

    _install_transport(monkeypatch, handler)
    with pytest.raises(EmbeddingError, match="não respondeu a tempo"):
        embeddings.create_embedder("ollama", "bge-m3")


def test_ollama_antigo_usa_rota_legada(monkeypatch):
    def handler(request: httpx.Request):
        if request.url.path == "/api/tags":
            return _tags("bge-m3:latest")
        if request.url.path == "/api/embed":
            return httpx.Response(404, text="404 page not found")
        return httpx.Response(200, json={"embedding": [1.0, 0.0]})

    _install_transport(monkeypatch, handler)
    embedder = embeddings.create_embedder("ollama", "bge-m3")
    assert embedder.embed_query("teste") == [1.0, 0.0]
    assert embedder._legacy is True


def test_ollama_recusando_requisicao_vira_erro(monkeypatch):
    def handler(request):
        if request.url.path == "/api/tags":
            return _tags("bge-m3:latest")
        return httpx.Response(500, text="out of memory")

    _install_transport(monkeypatch, handler)
    embedder = embeddings.create_embedder("ollama", "bge-m3")
    with pytest.raises(EmbeddingError, match="out of memory"):
        embedder.embed_query("teste")


def test_provedor_de_embeddings_invalido():
    with pytest.raises(EmbeddingError, match="inválido"):
        embeddings.create_embedder("openai", "text-embedding-3")


@pytest.mark.live_ollama
def test_ollama_real_responde_embeddings():
    url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    model = os.environ.get("OLLAMA_TEST_MODEL", "all-minilm")
    try:
        embedder = embeddings.create_embedder("ollama", model, ollama_url=url, timeout=120)
    except EmbeddingError as exc:
        pytest.fail(f"Ollama em {url} indisponível ou sem o modelo {model}: {exc.message}")
    vector = embedder.embed_query("Tormenta20")
    assert len(vector) == embedder.dimension > 0
