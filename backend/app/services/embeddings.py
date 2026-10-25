"""
Modelos de embeddings: dois provedores, escolhidos na execução.

- sentence-transformers: o modelo roda dentro do próprio Python (instala o
  PyTorch, ~2 GB). Padrão: BAAI/bge-m3.
- ollama: o modelo roda no servidor local do Ollama (o mesmo que pode servir a
  LLM do chat). Não precisa do PyTorch. Padrão: bge-m3 (`ollama pull bge-m3`).

O mesmo provedor, modelo e prefixos precisam ser usados na consulta: por isso
tudo fica gravado no `manifest.json` de cada livro (ver `EmbeddingInfo`).
Trocar de modelo exige reconstruir o banco do livro.
"""

import math
import sys
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

PROVIDERS = ("sentence-transformers", "ollama")
DEFAULT_MODELS = {"sentence-transformers": "BAAI/bge-m3", "ollama": "bge-m3"}

# Prefixos (trecho, pergunta) exigidos por algumas famílias de modelos
_PREFIXES = {
    "e5": ("passage: ", "query: "),
    "nomic-embed": ("search_document: ", "search_query: "),
    "mxbai-embed": ("", "Represent this sentence for searching relevant passages: "),
}


def prefixes_for(model_name: str) -> tuple[str, str]:
    """(prefixo do trecho, prefixo da pergunta) recomendados para o modelo."""
    name = model_name.lower()
    for key, value in _PREFIXES.items():
        if key in name:
            return value
    return ("", "")


@dataclass
class EmbeddingInfo:
    provider: str
    model: str
    dimension: int
    passage_prefix: str
    query_prefix: str
    normalize: bool = True
    base_url: str | None = None  # servidor do Ollama


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


class Embedder:
    """Interface comum aos provedores."""

    provider = ""

    def __init__(self, model_name: str, batch_size: int):
        self.model_name = model_name
        self.batch_size = batch_size
        self.passage_prefix, self.query_prefix = prefixes_for(model_name)

    @property
    def dimension(self) -> int:
        raise NotImplementedError

    @property
    def base_url(self) -> str | None:
        return None

    def _embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @property
    def info(self) -> EmbeddingInfo:
        return EmbeddingInfo(
            provider=self.provider,
            model=self.model_name,
            dimension=self.dimension,
            passage_prefix=self.passage_prefix,
            query_prefix=self.query_prefix,
            base_url=self.base_url,
        )

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
            raise SystemExit(
                "Pacote 'sentence-transformers' não instalado. Rode:\n"
                "  pip install -r vector_builder/requirements-local.txt\n"
                "ou use o Ollama: --provider ollama"
            ) from exc
        self.model = SentenceTransformer(model_name, device=device)

    @property
    def dimension(self) -> int:
        return int(self.model.get_sentence_embedding_dimension())

    def _embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 1,
            convert_to_numpy=True,
        )
        return vectors.tolist()


class OllamaEmbedder(Embedder):
    """
    Embeddings pelo servidor do Ollama (`POST /api/embed`, em lotes). Versões
    antigas do Ollama, sem `/api/embed`, usam `/api/embeddings` (um texto por vez).
    """

    provider = "ollama"

    def __init__(self, model_name: str, batch_size: int = 16, base_url: str | None = None,
                 timeout: float = 300.0):
        super().__init__(model_name, batch_size)
        import httpx

        self._base_url = (base_url or settings.ollama_url).rstrip("/")
        self._client = httpx.Client(base_url=self._base_url, timeout=timeout)
        self._legacy = False
        self._dimension: int | None = None
        self._check_model()

    @property
    def base_url(self) -> str | None:
        return self._base_url

    def _check_model(self) -> None:
        import httpx

        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SystemExit(
                f"Ollama não respondeu em {self._base_url}. Abra o Ollama (ou rode `ollama serve`) "
                "e tente de novo."
            ) from exc
        names = {m.get("name", "") for m in response.json().get("models", [])}
        wanted = self.model_name if ":" in self.model_name else f"{self.model_name}:latest"
        if wanted not in names and self.model_name not in names:
            raise SystemExit(f"Modelo '{self.model_name}' não encontrado no Ollama. Rode: ollama pull {self.model_name}")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._client.post(path, json=payload)
        if response.status_code >= 400:
            detail = response.text[:300]
            raise SystemExit(f"Ollama recusou a requisição ({response.status_code}): {detail}")
        return response.json()

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._legacy:
            response = self._client.post("/api/embed", json={"model": self.model_name, "input": texts, "truncate": True})
            if response.status_code == 404 and "model" not in response.text.lower():
                self._legacy = True  # Ollama antigo: rota inexistente
            elif response.status_code >= 400:
                raise SystemExit(f"Ollama recusou a requisição ({response.status_code}): {response.text[:300]}")
            else:
                return response.json()["embeddings"]
        return [self._post("/api/embeddings", {"model": self.model_name, "prompt": t})["embedding"] for t in texts]

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
) -> Embedder:
    """Cria o embedder do provedor escolhido (padrões em EMBEDDING_PROVIDER / EMBEDDING_MODEL)."""
    provider = provider or settings.embedding_provider
    if provider not in PROVIDERS:
        raise SystemExit(f"Provedor de embeddings inválido: {provider!r}. Use: {', '.join(PROVIDERS)}")
    model = model or settings.embedding_model or DEFAULT_MODELS[provider]
    if provider == "ollama":
        return OllamaEmbedder(model, batch_size=batch_size, base_url=ollama_url)
    return SentenceTransformerEmbedder(model, batch_size=batch_size, device=device)


def create_embedder_from_info(info: dict[str, Any]) -> Embedder:
    """Recria o embedder gravado no manifest.json de um livro (usado na consulta)."""
    embedder = create_embedder(
        provider=info.get("provider", "sentence-transformers"),
        model=info["model"],
        ollama_url=info.get("base_url"),
    )
    embedder.passage_prefix = info.get("passage_prefix", embedder.passage_prefix)
    embedder.query_prefix = info.get("query_prefix", embedder.query_prefix)
    return embedder
