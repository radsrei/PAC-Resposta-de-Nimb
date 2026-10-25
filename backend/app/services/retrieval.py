"""
Busca dos trechos mais próximos da pergunta nos livros liberados.

Híbrida: os candidatos da busca vetorial (sentido) e da busca por palavras (BM25:
nomes, tabelas, termos exatos) são combinados por RRF. Todo trecho passa pelo
mesmo filtro de similaridade vetorial mínima, que barra perguntas fora do livro.
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import settings
from app.core.exceptions import RetrievalError
from app.services import book_catalog, lexical
from app.services.embeddings import query_embedder

logger = logging.getLogger("nimb.rag")
RRF_K = 60


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
    score: float = 0.0

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


def _ranked(book_id: str, manifest: dict, collection, question: str, vector: list[float],
            hybrid: bool, candidates: int) -> dict[str, float]:
    scores: dict[str, float] = defaultdict(float)
    dense = collection.query(query_embeddings=[vector], n_results=candidates, include=[])["ids"][0]
    for rank, doc_id in enumerate(dense, start=1):
        scores[doc_id] += 1 / (RRF_K + rank)
    if hybrid:
        index = lexical.book_index(book_id, str(book_catalog.book_dir(book_id) / "chunks.jsonl"), manifest["built_at"])
        for rank, (doc_id, _) in enumerate(index.search(question, candidates), start=1):
            scores[doc_id] += settings.rag_lexical_weight / (RRF_K + rank)
    return scores


def _search_book(book_id: str, question: str, vectors: dict, hybrid: bool, candidates: int) -> list[Passage]:
    manifest = book_catalog.vector_manifest(book_id)
    if manifest is None:
        return []
    info = manifest["embedding"]
    key = (info.get("provider"), info["model"], info.get("query_prefix", ""))
    if key not in vectors:
        vectors[key] = query_embedder(info).embed_query(question)
    vector = vectors[key]
    try:
        collection = _collection(str(book_catalog.chroma_path(book_id)), manifest["collection"])
        scores = _ranked(book_id, manifest, collection, question, vector, hybrid, candidates)
        found = collection.get(ids=list(scores), include=["documents", "metadatas", "embeddings"])
    except RetrievalError:
        raise
    except Exception as exc:
        logger.exception("Falha ao consultar o banco do livro %s", book_id)
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
            similarity=round(sum(a * b for a, b in zip(vector, embedding)), 4),
            score=scores[doc_id],
        )
        for doc_id, document, meta, embedding in zip(found["ids"], found["documents"], found["metadatas"], found["embeddings"])
    ]


def warm_up() -> None:
    """Carrega o modelo de embeddings, o banco e o índice de palavras de cada livro, para a 1ª pergunta não esperar."""
    started = time.monotonic()
    for book in book_catalog.load_catalog():
        if book_catalog.vector_manifest(book["id"]) is None:
            continue
        try:
            search([book["id"]], "aquecimento", k=1, min_similarity=-1)
        except Exception as exc:
            logger.warning("Aquecimento da busca falhou para %s: %s", book["id"], getattr(exc, "message", exc))
            return
    logger.info("Busca nos livros pronta (%.1fs).", time.monotonic() - started)


def search(book_ids: list[str], question: str, k: int | None = None, hybrid: bool | None = None,
           min_similarity: float | None = None, candidates: int | None = None) -> list[Passage]:
    """Os `k` trechos mais bem colocados entre todos os livros, acima da similaridade mínima."""
    k = k or settings.rag_top_k
    hybrid = settings.rag_hybrid if hybrid is None else hybrid
    floor = settings.rag_min_similarity if min_similarity is None else min_similarity
    candidates = candidates or settings.rag_candidates
    vectors: dict = {}
    passages = [p for book_id in book_ids for p in _search_book(book_id, question, vectors, hybrid, candidates)]
    relevant = [p for p in passages if p.similarity >= floor]
    return sorted(relevant, key=lambda p: p.score, reverse=True)[:k]
