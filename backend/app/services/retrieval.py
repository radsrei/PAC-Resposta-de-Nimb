"""Busca dos trechos mais próximos da pergunta nos bancos vetoriais dos livros liberados."""

import logging
import time
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import RetrievalError
from app.services import book_catalog
from app.services.embeddings import query_embedder

logger = logging.getLogger("nimb.rag")


@dataclass(frozen=True)
class Passage:
    book_id: str
    book_title: str
    title: str
    path: str
    chapter: str
    kind: str
    page: str
    text: str
    similarity: float

    @property
    def label(self) -> str:
        where = " > ".join(p for p in (self.chapter, self.path) if p)
        return f"{self.book_title} > {where}, p. {self.page}" if self.page else f"{self.book_title} > {where}"


@lru_cache(maxsize=16)
def _collection(chroma_dir: str, name: str):
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:
        raise RetrievalError("Pacote 'chromadb' não instalado na API: busca nos livros indisponível.") from exc
    client = chromadb.PersistentClient(path=chroma_dir, settings=Settings(anonymized_telemetry=False))
    return client.get_collection(name)


def _search_book(book_id: str, question: str, k: int, vectors: dict) -> list[Passage]:
    manifest = book_catalog.vector_manifest(book_id)
    if manifest is None:
        return []
    info = manifest["embedding"]
    key = (info.get("provider"), info["model"], info.get("query_prefix", ""))
    if key not in vectors:
        vectors[key] = query_embedder(info).embed_query(question)
    try:
        collection = _collection(str(book_catalog.chroma_path(book_id)), manifest["collection"])
        result = collection.query(query_embeddings=[vectors[key]], n_results=k,
                                  include=["documents", "metadatas", "distances"])
    except RetrievalError:
        raise
    except Exception as exc:
        logger.exception("Falha ao consultar o banco vetorial do livro %s", book_id)
        raise RetrievalError(f"Não foi possível consultar o banco do livro '{manifest['title']}'.") from exc

    return [
        Passage(
            book_id=book_id,
            book_title=manifest["title"],
            title=meta.get("title", ""),
            path=meta.get("path", ""),
            chapter=meta.get("chapter", ""),
            kind=meta.get("kind", ""),
            page=str(meta.get("printed_start") or meta.get("page_start") or ""),
            text=document,
            similarity=round(1 - distance, 4),
        )
        for document, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
    ]


def warm_up() -> None:
    """Carrega o modelo de embeddings e abre o banco de cada livro, para a 1ª pergunta não esperar."""
    started = time.monotonic()
    for book in book_catalog.load_catalog():
        manifest = book_catalog.vector_manifest(book["id"])
        if manifest is None:
            continue
        try:
            query_embedder(manifest["embedding"]).embed_query("aquecimento")
            _collection(str(book_catalog.chroma_path(book["id"])), manifest["collection"])
        except Exception as exc:
            logger.warning("Aquecimento da busca falhou para %s: %s", book["id"], getattr(exc, "message", exc))
            return
    logger.info("Busca nos livros pronta (%.1fs).", time.monotonic() - started)


def search(book_ids: list[str], question: str, k: int | None = None) -> list[Passage]:
    """Os `k` trechos mais próximos entre todos os livros, acima da similaridade mínima."""
    k = k or settings.rag_top_k
    vectors: dict = {}
    passages = [p for book_id in book_ids for p in _search_book(book_id, question, k, vectors)]
    relevant = [p for p in passages if p.similarity >= settings.rag_min_similarity]
    return sorted(relevant, key=lambda p: p.similarity, reverse=True)[:k]
