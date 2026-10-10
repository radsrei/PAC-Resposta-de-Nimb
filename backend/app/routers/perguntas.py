"""
Contrato ORIGINAL do protótipo estático (frontend/Claude, docs/nimb_prototipo).
Mantido por compatibilidade; usa o mesmo fluxo de consulta à LLM.
"""

from fastapi import APIRouter, Depends

from app.controllers import query_controller
from app.core.deps import CurrentUser, require_user
from app.schemas.perguntas import PerguntaRequest, RespostaResponse

router = APIRouter(prefix="/api", tags=["perguntas (legado)"])


@router.post("/perguntas", response_model=RespostaResponse)
def perguntar(payload: PerguntaRequest, user: CurrentUser = Depends(require_user)):
    result = query_controller.ask(user_email=user["email"], prompt=payload.pergunta)
    return RespostaResponse(
        pergunta=payload.pergunta,
        resposta=result["answer"],
        fontes=[],
        status="ok",
        tempo_resposta_ms=result["latency_ms"],
    )
