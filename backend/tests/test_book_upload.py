"""
CI-05 Envio de arquivo (POST /api/rag/upload) e validação do PDF do livro.

- O upload exige sessão válida ANTES de qualquer byte ser lido (BodyLimitMiddleware);
- limite de tamanho (413) e de validações por minuto (429);
- arquivo que não é PDF, PDF vazio/corrompido: 400 com mensagem clara e tentativa registrada;
- PDF idêntico ao do catálogo (SHA-256) libera o livro; outro PDF é recusado;
- a resposta nunca devolve os valores esperados do catálogo (hashes, frases).
"""

import hashlib
import io
import sqlite3

import pytest
from pypdf import PdfWriter

from app.core import middleware
from app.core.config import settings
from app.services import book_catalog, book_validator
from app.services.book_fingerprint import fingerprint_pdf

BOOK_ID = "t20-teste"


def make_pdf(pages: int = 2, size=(595.3, 841.9)) -> bytes:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=size[0], height=size[1])
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


ORIGINAL_PDF = make_pdf()


def register_book(**overrides):
    entry = {
        "id": BOOK_ID,
        "title": "Tormenta20 - Livro de Teste",
        "sha256": [hashlib.sha256(ORIGINAL_PDF).hexdigest()],
        "page_count": 2,
        "probes": [{"page": 1, "text": "frase de controle que só existe no livro original"}],
        **overrides,
    }
    book_catalog.save_catalog([entry])


def upload(client, data: bytes, name="livro.pdf", content_type="application/pdf"):
    return client.post("/api/rag/upload", files={"file": (name, data, content_type)})


def attempts():
    conn = sqlite3.connect(settings.database_path)
    try:
        return conn.execute("SELECT accepted, file_name FROM book_validation_log").fetchall()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Acesso e limites
# ---------------------------------------------------------------------------
def test_upload_sem_login_e_recusado_antes_de_ler_o_arquivo(client):
    response = upload(client, ORIGINAL_PDF)
    assert response.status_code == 401
    assert attempts() == []


def test_arquivo_acima_do_limite_responde_413(user_client, monkeypatch):
    monkeypatch.setattr(middleware, "UPLOAD_MAX_BYTES", 1024)
    response = upload(user_client, b"%PDF-1.7\n" + b"0" * 4096)
    assert response.status_code == 413


def test_limite_de_validacoes_por_minuto(user_client):
    register_book()
    for _ in range(settings.book_upload_rate_per_minute):
        assert upload(user_client, b"nao sou pdf").status_code == 400
    assert upload(user_client, b"nao sou pdf").status_code == 429


def test_sem_catalogo_avisa_que_nao_ha_livros(user_client):
    response = upload(user_client, ORIGINAL_PDF)
    assert response.status_code == 400
    assert "Nenhum livro permitido" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Validação do conteúdo
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "data, name",
    [
        (b"isto e um texto qualquer", "livro.pdf"),
        (b"\x89PNG\r\n\x1a\n" + b"0" * 100, "imagem.pdf"),
        (b"%PDF-1.7\nlixo corrompido sem xref", "corrompido.pdf"),
    ],
)
def test_arquivo_que_nao_e_pdf_valido_e_recusado_e_registrado(user_client, data, name):
    register_book()
    response = upload(user_client, data, name=name)
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]
    assert attempts() == [(0, name)]  # tentativa fica no histórico (auditoria de abuso)


def test_pdf_identico_ao_original_libera_o_livro(user_client):
    register_book()
    response = upload(user_client, ORIGINAL_PDF)
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is True
    assert body["score"] == 1.0
    assert body["book"]["id"] == BOOK_ID
    assert body["book"]["unlocked"] is True

    books = user_client.get("/api/rag/books").json()
    assert books[0]["id"] == BOOK_ID and books[0]["unlocked"] is True


def test_outro_pdf_e_recusado_e_nao_libera_o_livro(user_client):
    register_book()
    response = upload(user_client, make_pdf(pages=3, size=(612, 792)), name="outro.pdf")
    assert response.status_code == 200
    body = response.json()
    assert body["accepted"] is False
    assert body["book"] is None
    assert {c["name"] for c in body["checks"]} >= {"probes", "page_count"}
    assert user_client.get("/api/rag/books").json()[0]["unlocked"] is False
    assert attempts() == [(0, "outro.pdf")]


def test_resposta_nao_vaza_dados_do_catalogo(user_client):
    register_book()
    response = upload(user_client, make_pdf(pages=3), name="outro.pdf")
    text = response.text
    assert hashlib.sha256(ORIGINAL_PDF).hexdigest() not in text
    assert "frase de controle" not in text
    for check in response.json()["checks"]:
        assert set(check) == {"name", "label", "passed"}


def test_validador_exige_frases_mesmo_com_metadados_iguais():
    """Tamanho, páginas e formato iguais não bastam: sem as frases do livro, recusa."""
    pdf = make_pdf()
    fp = fingerprint_pdf(pdf)
    book = book_catalog._with_defaults({
        "id": BOOK_ID, "title": "x", "sha256": [],
        "page_count": fp.page_count, "size_bytes": fp.size_bytes, "page_size": list(fp.page_size),
        "probes": [{"page": 1, "text": "texto que não está no arquivo"}], "min_score": 0.3,
    })
    match = book_validator.match_book(fp, book)
    assert match.score >= 0.3
    assert match.accepted is False
