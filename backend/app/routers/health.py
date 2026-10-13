from fastapi import APIRouter

from app.controllers import llm_controller

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    # Rota pública: não expõe nomes, modelos nem dados de usuários
    return {
        "status": "ok",
        "service": "respostas-de-nimb",
        "rag_engine": "desativado",
        "llm_connected": llm_controller.get_active_connection() is not None,
    }
