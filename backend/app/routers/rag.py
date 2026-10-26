"""
Rotas consumidas pelo front React (`src/services/ragApi.ts`).

POST /api/rag/query   -> busca nos livros liberados, envia a pergunta à LLM e devolve resposta e fontes
GET  /api/rag/books   -> livros do catálogo e quais o usuário já liberou
POST /api/rag/upload  -> valida o PDF de um livro e libera o banco vetorial dele
"""

from fastapi import APIRouter, Depends, File, UploadFile

from app.controllers import book_controller, query_controller
from app.core.config import settings
from app.core.deps import CurrentUser, require_user
from app.core.exceptions import AppError
from app.core.rate_limit import limit_book_upload
from app.schemas.rag import BookOut, BookValidationOut, QueryRagPayload, QueryRagResponse

router = APIRouter(prefix="/api/rag", tags=["rag"])

_READ_CHUNK = 1024 * 1024


@router.post("/query", response_model=QueryRagResponse)
def query_rag(payload: QueryRagPayload, user: CurrentUser = Depends(require_user)):
    result = query_controller.ask(
        user_email=user["email"],
        prompt=payload.prompt,
        chaos_level=payload.chaos_level,
        session_id=payload.session_id,
        connection_id=payload.connection_id,
        book_ids=payload.book_ids,
    )
    return QueryRagResponse(**result)


@router.get("/books", response_model=list[BookOut])
def list_books(user: CurrentUser = Depends(require_user)):
    return book_controller.list_books(user["email"])


@router.post("/upload", response_model=BookValidationOut, dependencies=[Depends(limit_book_upload)])
def upload_book(file: UploadFile = File(...), user: CurrentUser = Depends(require_user)):
    # Lê em blocos para recusar arquivos grandes sem carregá-los inteiros
    limit = settings.book_upload_max_mb * 1024 * 1024
    data = bytearray()
    while chunk := file.file.read(_READ_CHUNK):
        data.extend(chunk)
        if len(data) > limit:
            raise AppError(f"Arquivo maior que o limite de {settings.book_upload_max_mb} MB.")
    return book_controller.validate_upload(user["email"], file.filename, bytes(data))
