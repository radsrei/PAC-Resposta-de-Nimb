"""
Gravação do banco vetorial de um livro (Chroma), separado por livro:

    vector_store/books/<book_id>/
    ├── chroma-<data>/   coleção "chunks", distância cosseno, metadados de entrada e página (uma pasta por construção)
    ├── tables-<data>.sqlite  tabelas do livro em estrutura (colunas, grupos, linhas) e índice das entradas
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
import sqlite3
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import book_catalog
from vector_builder import BUILDER_VERSION
from vector_builder.chunking import ROW_KIND, Chunk
from vector_builder.tables import Table
from app.services.embeddings import EmbeddingInfo

COLLECTION = "chunks"
_BATCH = 1000

TABLES_SCHEMA = """
CREATE TABLE book_tables (
    key TEXT PRIMARY KEY, number TEXT, title TEXT, label TEXT, chapter TEXT,
    page_start INTEGER, page_end INTEGER, printed_start TEXT, printed_end TEXT,
    columns TEXT, notes TEXT, chunks TEXT
);
CREATE TABLE table_rows (
    id INTEGER PRIMARY KEY, table_key TEXT NOT NULL REFERENCES book_tables(key), position INTEGER,
    grp TEXT, name TEXT, cells TEXT, notes TEXT, page INTEGER, printed TEXT, chunk_index INTEGER, text TEXT
);
CREATE INDEX idx_table_rows ON table_rows (table_key, position);
CREATE VIRTUAL TABLE table_rows_fts USING fts5(
    name, text, content='table_rows', content_rowid='id', tokenize='unicode61 remove_diacritics 2'
);
CREATE TABLE entries (
    chunk_index INTEGER PRIMARY KEY, title TEXT, path TEXT, chapter TEXT, kind TEXT,
    printed_start TEXT, table_key TEXT
);
"""


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_chunks_jsonl(path: Path, chunks: list[Chunk]) -> None:
    _atomic_write(path, "".join(json.dumps(asdict(c), ensure_ascii=False) + "\n" for c in chunks))


def write_tables(path: Path, tables: list[Table], chunks: list[Chunk]) -> None:
    rows = {(c.table, c.row): c for c in chunks if c.kind == ROW_KIND}
    path.unlink(missing_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(TABLES_SCHEMA)
        for t in tables:
            conn.execute(
                "INSERT INTO book_tables VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (t.key, t.number, t.title, t.label, t.chapter, t.page_start, t.page_end, t.printed_start,
                 t.printed_end, json.dumps(t.columns, ensure_ascii=False), json.dumps(t.notes, ensure_ascii=False),
                 json.dumps([c.index for c in chunks if c.table == t.key and c.kind != ROW_KIND])),
            )
            for position, row in enumerate(t.rows, start=1):
                chunk = rows.get((t.key, position))
                conn.execute(
                    "INSERT INTO table_rows (table_key, position, grp, name, cells, notes, page, printed, chunk_index, text) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (t.key, position, row.group, row.name, json.dumps(row.cells, ensure_ascii=False),
                     json.dumps(row.notes, ensure_ascii=False), row.page,
                     chunk.printed_start if chunk else t.printed_start, chunk.index if chunk else None, t.row_text(row)),
                )
        conn.execute("INSERT INTO table_rows_fts (table_rows_fts) VALUES ('rebuild')")
        conn.executemany(
            "INSERT INTO entries VALUES (?,?,?,?,?,?,?)",
            [(c.index, c.title, c.path, c.chapter, c.kind, c.printed_start, c.table or None)
             for c in chunks if c.kind != ROW_KIND],
        )
        conn.commit()
    finally:
        conn.close()


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
                "table": c.table,
                "row": c.row,
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
    tables: list[Table],
) -> Path:
    root = book_catalog.book_dir(book["id"])
    root.mkdir(parents=True, exist_ok=True)
    built_at = datetime.now(timezone.utc)
    chroma_dir = f"chroma-{built_at:%Y%m%dT%H%M%S%f}"
    tables_db = f"tables-{built_at:%Y%m%dT%H%M%S%f}.sqlite"

    _write_chroma(root / chroma_dir, book["id"], chunks, vectors)
    write_tables(root / tables_db, tables, chunks)
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
        "tables_db": tables_db,
        "tables": len(tables),
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
        elif old.is_file() and old.name != tables_db and old.name.startswith("tables-"):
            try:
                old.unlink()
            except OSError:
                pass
    return root / chroma_dir
