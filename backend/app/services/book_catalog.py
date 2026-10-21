"""
Catálogo de livros permitidos e localização dos bancos vetoriais.

Estrutura da pasta `VECTOR_STORE_DIR` (fora do Git, gerada por `vector_builder`):

    vector_store/
    ├── catalog.json            livros permitidos + impressão digital de cada um
    └── books/<book_id>/
        ├── chroma-<data>/      banco vetorial (Chroma) do livro, uma pasta por construção
        ├── chunks.jsonl        trechos indexados, para revisão de qualidade
        └── manifest.json       versão ativa (`chroma_dir`), modelo de embeddings e totais

Formato de cada livro no `catalog.json` (editável à mão):

    {
      "id": "t20-basico",                  identificador (pasta do banco)
      "title": "Tormenta20 - Livro Básico",
      "sha256": ["..."],                   hashes de arquivos idênticos ao original
      "size_bytes": 50331648, "size_tolerance_pct": 5,
      "page_count": 400, "page_count_tolerance": 0,
      "page_size": [595.3, 841.9],
      "metadata": {"title": "...", "author": "..."},
      "probes": [{"page": 12, "text": "frase que existe na página 12"}],
      "probe_page_window": 1,              aceita a frase até N páginas antes/depois
      "min_probes": 5,                     frases que precisam ser encontradas
      "min_score": 0.65                    pontuação mínima para aceitar
    }
"""

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import settings

CATALOG_VERSION = 1
BOOK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")

DEFAULTS: dict[str, Any] = {
    "sha256": [],
    "size_tolerance_pct": 5.0,
    "page_count_tolerance": 0,
    "page_size": None,
    "metadata": {},
    "probes": [],
    "probe_page_window": 1,
    "min_probes": None,  # None = 60% das frases
    "min_score": 0.65,
}

_cache: dict[str, Any] = {"mtime": None, "books": []}


def catalog_path() -> Path:
    return settings.vector_store_dir / "catalog.json"


def book_dir(book_id: str) -> Path:
    if not BOOK_ID_RE.match(book_id):
        raise ValueError(f"Identificador de livro inválido: {book_id!r}")
    return settings.vector_store_dir / "books" / book_id


def _with_defaults(entry: dict[str, Any]) -> dict[str, Any]:
    book = {**DEFAULTS, **entry}
    if not BOOK_ID_RE.match(str(book.get("id", ""))) or not book.get("title"):
        raise ValueError(f"Livro inválido no catálogo (id/title): {entry.get('id')!r}")
    return book


def load_catalog() -> list[dict[str, Any]]:
    """Livros do catálogo. Relê o arquivo só quando ele muda."""
    path = catalog_path()
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return []
    if _cache["mtime"] != mtime:
        raw = json.loads(path.read_text(encoding="utf-8"))
        _cache["books"] = [_with_defaults(b) for b in raw.get("books", [])]
        _cache["mtime"] = mtime
    return _cache["books"]


def get_book(book_id: str) -> dict[str, Any] | None:
    return next((b for b in load_catalog() if b["id"] == book_id), None)


def save_catalog(books: list[dict[str, Any]]) -> None:
    """Grava o catálogo de forma atômica (arquivo temporário + rename)."""
    path = catalog_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": CATALOG_VERSION, "books": sorted(books, key=lambda b: b["id"])}
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".catalog-", suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    _cache["mtime"] = None


def upsert_book(entry: dict[str, Any]) -> None:
    _with_defaults(entry)
    path = catalog_path()
    raw = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"books": []}
    books = [b for b in raw.get("books", []) if b.get("id") != entry["id"]]
    save_catalog([*books, entry])


def chroma_path(book_id: str) -> Path | None:
    """Pasta do Chroma da versão ativa do banco do livro."""
    manifest = vector_manifest(book_id)
    return book_dir(book_id) / manifest["chroma_dir"] if manifest else None


def vector_manifest(book_id: str) -> dict[str, Any] | None:
    """Manifesto do banco vetorial do livro, ou None se ainda não foi construído."""
    try:
        path = book_dir(book_id) / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, FileNotFoundError, json.JSONDecodeError):
        return None
