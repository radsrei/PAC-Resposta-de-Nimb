from fastapi import APIRouter

from app.controllers import llm_controller

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    active = llm_controller.get_active_connection()
    return {
        "status": "ok",
        "service": "respostas-de-nimb",
        "rag_engine": "desativado",
        "llm": {
            "connected": active is not None,
            "connectionId": active["id"] if active else None,
            "name": active["name"] if active else None,
            "provider": active["provider"] if active else None,
            "model": active["model"] if active else None,
        },
    }
