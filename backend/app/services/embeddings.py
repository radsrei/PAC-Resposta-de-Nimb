"""
Modelos de embeddings, usados pelo construtor (trechos) e pela API (pergunta).

- ollama: o modelo roda no servidor do Ollama, sem PyTorch. Padrão: bge-m3.
- sentence-transformers: o modelo roda dentro do Python (PyTorch, ~2 GB). Padrão: BAAI/bge-m3.

Provedor, modelo e prefixos ficam no `manifest.json` de cada livro e a consulta
usa os mesmos. O endereço do Ollama não: vem sempre de `OLLAMA_URL`, porque o
servidor que construiu o banco não é o mesmo que responde as perguntas.
"""

import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import EmbeddingError

PROVIDERS = ("sentence-transformers", "ollama")
DEFAULT_MODELS = {"sentence-transformers": "BAAI/bge-m3", "ollama": "bge-m3"}
BUILD_TIMEOUT = 300.0
QUERY_TIMEOUT = 30.0

_PREFIXES = {
    "e5": ("passage: ", "query: "),
    "nomic-embed": ("search_document: ", "search_query: "),
    "mxbai-embed": ("", "Represent this sentence for searching relevant passages: "),
}


def prefixes_for(model_name: str) -> tuple[str, str]:
    """(prefixo do trecho, prefixo da pergunta) recomendados para o modelo."""
    name = model_name.lower()
    return next((value for key, value in _PREFIXES.items() if key in name), ("", ""))


@dataclass
class EmbeddingInfo:
    provider: str
    model: str
    dimension: int
    passage_prefix: str
    query_prefix: str
    normalize: bool = True


def _keep_alive(value: str) -> str | int:
    return int(value) if value.lstrip("-").isdigit() else value


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class Embedder:
    provider = ""

    def __init__(self, model_name: str, batch_size: int):
        self.model_name = model_name
        self.batch_size = batch_size
        self.passage_prefix, self.query_prefix = prefixes_for(model_name)

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    def _embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    def info(self) -> EmbeddingInfo:
        return EmbeddingInfo(self.provider, self.model_name, self.dimension,
                             self.passage_prefix, self.query_prefix)

    def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return self._embed([self.passage_prefix + t for t in texts])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([self.query_prefix + text])[0]


class SentenceTransformerEmbedder(Embedder):
    provider = "sentence-transformers"

    def __init__(self, model_name: str, batch_size: int = 16, device: str | None = None):
        super().__init__(model_name, batch_size)
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise EmbeddingError(
                "Pacote 'sentence-transformers' não instalado "
                "(pip install -r vector_builder/requirements-local.txt). Ou use o provedor ollama."
            ) from exc
        self.model = SentenceTransformer(model_name, device=device)

    @property
    def dimension(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                    show_progress_bar=len(texts) > 1, convert_to_numpy=True)
        return vectors.tolist()


class OllamaEmbedder(Embedder):
    """`POST /api/embed` em lotes; Ollama antigo, sem essa rota, usa `/api/embeddings` (um texto por vez)."""

    provider = "ollama"

    def __init__(self, model_name: str, batch_size: int = 16, base_url: str | None = None,
                 timeout: float = BUILD_TIMEOUT):
        super().__init__(model_name, batch_size)
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self._legacy = False
        self._dimension: int | None = None
        self.keep_alive = _keep_alive(settings.ollama_keep_alive)
        self._check_model()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.TimeoutException as exc:
            raise EmbeddingError(f"O Ollama em {self.base_url} não respondeu a tempo.") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Ollama indisponível em {self.base_url}. Abra o Ollama ou rode `ollama serve`.") from exc
        if response.status_code >= 400 and not (response.status_code == 404 and path == "/api/embed"):
            raise EmbeddingError(f"O Ollama recusou a requisição ({response.status_code}): {response.text[:300]}")
        return response

    def _check_model(self) -> None:
        names = {m.get("name", "") for m in self._request("GET", "/api/tags").json().get("models", [])}
        wanted = self.model_name if ":" in self.model_name else f"{self.model_name}:latest"
        if wanted not in names and self.model_name not in names:
            raise EmbeddingError(f"Modelo '{self.model_name}' não encontrado no Ollama. Rode: ollama pull {self.model_name}")

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._legacy:
            response = self._request("POST", "/api/embed", json={"model": self.model_name, "input": texts,
                                                                 "truncate": True, "keep_alive": self.keep_alive})
            if response.status_code != 404:
                return response.json()["embeddings"]
            if "model" in response.text.lower():
                raise EmbeddingError(f"Modelo '{self.model_name}' não encontrado no Ollama. Rode: ollama pull {self.model_name}")
            self._legacy = True
        payload = {"model": self.model_name, "keep_alive": self.keep_alive}
        return [self._request("POST", "/api/embeddings", json={**payload, "prompt": t}).json()["embedding"]
                for t in texts]

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._dimension = len(self._embed(["dimensão"])[0])
        return self._dimension

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        total = len(texts)
        for start in range(0, total, self.batch_size):
            vectors.extend(_normalize(v) for v in self._embed_batch(texts[start:start + self.batch_size]))
            if total > 1:
                print(f"\r  embeddings: {len(vectors)}/{total}", end="", file=sys.stderr, flush=True)
        if total > 1:
            print(file=sys.stderr)
        if vectors:
            self._dimension = len(vectors[0])
        return vectors


def create_embedder(
    provider: str | None = None,
    model: str | None = None,
    batch_size: int = 16,
    device: str | None = None,
    ollama_url: str | None = None,
    timeout: float = BUILD_TIMEOUT,
) -> Embedder:
    """Embedder do provedor escolhido (padrões em EMBEDDING_PROVIDER / EMBEDDING_MODEL / OLLAMA_URL)."""
    provider = provider or settings.embedding_provider
    if provider not in PROVIDERS:
        raise EmbeddingError(f"Provedor de embeddings inválido: {provider!r}. Use: {', '.join(PROVIDERS)}")
    model = model or settings.embedding_model or DEFAULT_MODELS[provider]
    if provider == "ollama":
        return OllamaEmbedder(model, batch_size=batch_size, base_url=ollama_url, timeout=timeout)
    return SentenceTransformerEmbedder(model, batch_size=batch_size, device=device)


@lru_cache(maxsize=8)
def _query_embedder(provider: str, model: str, passage_prefix: str, query_prefix: str) -> Embedder:
    embedder = create_embedder(provider, model, timeout=QUERY_TIMEOUT)
    embedder.passage_prefix, embedder.query_prefix = passage_prefix, query_prefix
    return embedder


def query_embedder(info: dict[str, Any]) -> Embedder:
    """Embedder da consulta, recriado a partir do `manifest.json` do livro e reaproveitado entre perguntas."""
    provider = info.get("provider", "sentence-transformers")
    model = info["model"]
    default_passage, default_query = prefixes_for(model)
    return _query_embedder(provider, model, info.get("passage_prefix", default_passage),
                           info.get("query_prefix", default_query))
