from fastapi import APIRouter

from app.controllers import llm_controller
from app.services import book_catalog

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    # Rota pública: não expõe nomes, modelos nem dados de usuários
    ready = sum(1 for b in book_catalog.load_catalog() if book_catalog.vector_manifest(b["id"]))
    return {
        "status": "ok",
        "service": "respostas-de-nimb",
        "rag_engine": "ativo" if ready else "sem livros indexados",
        "books_ready": ready,
        "llm_connected": llm_controller.get_active_connection() is not None,
    }
