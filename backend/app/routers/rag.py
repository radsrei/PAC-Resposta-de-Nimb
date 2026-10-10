"""
Rotas consumidas pelo front React (`src/services/ragApi.ts`).

POST /api/rag/query   -> envia a pergunta para a LLM ativa e devolve a resposta
POST /api/rag/upload  -> (stub) indexação de livros — fora do escopo desta etapa
"""

from fastapi import APIRouter, File, Form, UploadFile

from app.controllers import query_controller
from app.schemas.rag import IndexedBookResponse, QueryRagPayload, QueryRagResponse

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=QueryRagResponse)
def query_rag(payload: QueryRagPayload):
    result = query_controller.ask(
        prompt=payload.prompt,
        chaos_level=payload.chaos_level,
        session_id=payload.session_id,
        connection_id=payload.connection_id,
    )
    # Campos de fonte ficam vazios até a etapa de RAG (livros/vector DB)
    return QueryRagResponse(
        **result,
        book_title="",
        page=None,
        similarity="-",
        quote=None,
        roll_table=None,
    )


@router.post("/upload", response_model=IndexedBookResponse)
async def upload_grimorio(
    file: UploadFile = File(...),
    chunkSize: int = Form(...),
    model: str = Form(...),
    entropy: float = Form(...),
):
    """
    TODO (etapa de RAG): salvar o PDF, aplicar chunking (`chunkSize`), gerar
    embeddings (`model`) e persistir no vector DB. Por ora apenas devolve um
    retorno coerente com o contrato esperado pelo front.
    """
    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    return IndexedBookResponse(
        id=f"book_{file.filename}",
        title=file.filename.rsplit(".", 1)[0] if file.filename else "documento",
        file_name=file.filename or "documento.pdf",
        size=f"{size_mb:.1f} MB",
        chunks=0,
        progress=100,
        status="indexed",
        badge_color="purple",
    )
