"""
Regras de negócio dos livros.

Fluxo do upload: o PDF é lido em memória, a impressão digital é comparada com o
catálogo de livros permitidos e, se aceito, o usuário ganha acesso ao banco
vetorial daquele livro. O arquivo é descartado: só o resultado é registrado.
"""

import logging
from typing import Any

from app.core.exceptions import AppError
from app.repositories import book_repository
from app.services import book_catalog
from app.services.book_fingerprint import fingerprint_pdf
from app.services.book_validator import find_best_match

logger = logging.getLogger("nimb.books")

# Nomes exibidos ao usuário para cada verificação
CHECK_LABELS = {
    "sha256": "Arquivo idêntico ao original",
    "probes": "Frases de controle nas páginas",
    "page_count": "Número de páginas",
    "size": "Tamanho do arquivo",
    "metadata": "Metadados do PDF",
    "page_size": "Formato da página",
}


def _book_out(book: dict[str, Any], access: dict[str, Any] | None) -> dict[str, Any]:
    manifest = book_catalog.vector_manifest(book["id"])
    return {
        "id": book["id"],
        "title": book["title"],
        "unlocked": access is not None,
        "unlocked_at": access["granted_at"] if access else None,
        "vector_ready": manifest is not None,
        "chunks": int(manifest.get("chunks", 0)) if manifest else 0,
        "page_count": book.get("page_count"),
    }


def list_books(user_email: str) -> list[dict[str, Any]]:
    access = book_repository.list_access(user_email)
    return [_book_out(b, access.get(b["id"])) for b in book_catalog.load_catalog()]


def validate_upload(user_email: str, file_name: str | None, data: bytes) -> dict[str, Any]:
    books = book_catalog.load_catalog()
    if not books:
        raise AppError("Nenhum livro permitido foi cadastrado no catálogo ainda.")

    try:
        fp = fingerprint_pdf(data)
    except AppError:
        # Arquivo ilegível também fica no histórico (auditoria de abuso)
        book_repository.log_attempt(user_email, None, False, 0.0, file_name, None, len(data), None)
        raise
    match = find_best_match(fp, books)
    accepted = bool(match and match.accepted)
    book_id = match.book["id"] if accepted else None

    book_repository.log_attempt(
        user_email, book_id, accepted, match.score if match else 0.0,
        file_name, fp.sha256, fp.size_bytes, fp.page_count,
    )
    if match:
        logger.info(
            "Validação de livro: usuário=%s arquivo=%r melhor=%s score=%.2f aceito=%s | %s",
            user_email, file_name, match.book["id"], match.score, accepted,
            "; ".join(f"{c.name}: {c.detail}" for c in match.checks),
        )

    book = None
    if accepted:
        book_repository.grant_access(user_email, book_id, fp.sha256, match.score)
        book = _book_out(match.book, book_repository.list_access(user_email).get(book_id))
        message = f"Livro reconhecido: {match.book['title']}. Acesso liberado."
    else:
        message = "O arquivo não corresponde a nenhum livro permitido."

    return {
        "accepted": accepted,
        "message": message,
        "score": round(match.score, 2) if match else 0.0,
        # Só o nome e o resultado de cada verificação: os valores esperados do
        # catálogo (frases, hashes, tamanhos) nunca voltam para o cliente
        "checks": [
            {"name": c.name, "label": CHECK_LABELS.get(c.name, c.name), "passed": c.passed}
            for c in (match.checks if match else [])
        ],
        "book": book,
    }
