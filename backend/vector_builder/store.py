"""
Gravação do banco vetorial de um livro (Chroma), separado por livro:

    vector_store/books/<book_id>/
    ├── chroma-<data>/   coleção "chunks", distância cosseno, metadados de entrada e página (uma pasta por construção)
    ├── chunks.jsonl     trechos indexados (para revisar a qualidade)
    └── manifest.json    aponta para a versão ativa (`chroma_dir`); a presença dele = banco pronto

Cada construção grava uma pasta nova e só no fim troca o `manifest.json`
(gravação atômica). Assim, uma construção interrompida não deixa banco pela
metade, e reconstruir funciona mesmo com a API lendo a versão anterior (no
Windows, uma pasta aberta não pode ser renomeada nem apagada). Versões antigas
são removidas quando estiverem livres, na mesma construção ou na seguinte.
"""

import gc
import json
import os
import shutil
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import book_catalog
from vector_builder import BUILDER_VERSION
from vector_builder.chunking import Chunk
from app.services.embeddings import EmbeddingInfo

COLLECTION = "chunks"
_BATCH = 1000


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_chunks_jsonl(path: Path, chunks: list[Chunk]) -> None:
    _atomic_write(path, "".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in chunks))


def _write_chroma(path: Path, book_id: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(path=str(path), settings=Settings(anonymized_telemetry=False))
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    for start in range(0, len(chunks), _BATCH):
        batch = chunks[start:start + _BATCH]
        collection.add(
            ids=[f"{book_id}:{c.index:06d}" for c in batch],
            embeddings=vectors[start:start + _BATCH],
            documents=[c.text for c in batch],
            metadatas=[{
                "book_id": book_id,
                "chunk_index": c.index,
                "title": c.title,
                "path": c.path,
                "chapter": c.chapter,
                "kind": c.kind,
                "page_start": c.page_start,
                "page_end": c.page_end,
                "printed_start": c.printed_start,
                "printed_end": c.printed_end,
            } for c in batch],
        )
    # Libera os arquivos do SQLite do Chroma (no Windows a pasta não pode ser
    # renomeada enquanto estiver aberta)
    del collection, client
    try:
        from chromadb.api.client import SharedSystemClient
        SharedSystemClient.clear_system_cache()
    except ImportError:
        pass
    gc.collect()


def write_book_store(
    book: dict[str, Any],
    chunks: list[Chunk],
    vectors: list[list[float]],
    embedding: EmbeddingInfo,
    params: dict[str, Any],
    source_sha256: str,
    page_count: int,
    profile: dict[str, Any],
) -> Path:
    root = book_catalog.book_dir(book["id"])
    root.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(timezone.utc)
    chroma_dir = f"chroma-{built_at:%Y%m%dT%H%M%S%f}"

    _write_chroma(root / chroma_dir, book["id"], chunks, vectors)
    write_chunks_jsonl(root / "chunks.jsonl", chunks)
    manifest = {
        "book_id": book["id"],
        "title": book["title"],
        "built_at": built_at.isoformat(),
        "builder_version": BUILDER_VERSION,
        "source_sha256": source_sha256,
        "pages": page_count,
        "chunks": len(chunks),
        "chroma_dir": chroma_dir,
        "collection": COLLECTION,
        "distance": "cosine",
        "chunking": params,
        "profile": profile,
        "kinds": dict(Counter(c.kind for c in chunks)),
        "embedding": asdict(embedding),
    }
    # A troca de versão acontece aqui: até este ponto, quem lê usa a anterior
    _atomic_write(root / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

    for old in root.iterdir():
        if old.is_dir() and old.name != chroma_dir and old.name.startswith("chroma"):
            shutil.rmtree(old, ignore_errors=True)  # em uso: fica para a próxima construção
    return root / chroma_dir
