"""
Rotas de configuração das conexões com LLM.

GET    /api/llm/providers                  -> provedores suportados
GET    /api/llm/connections                -> lista conexões
POST   /api/llm/connections                -> cria conexão
GET    /api/llm/connections/active         -> conexão ativa (ou null)
GET    /api/llm/connections/{id}           -> detalhe
PUT    /api/llm/connections/{id}           -> atualiza (parcial)
DELETE /api/llm/connections/{id}           -> remove
POST   /api/llm/connections/{id}/activate  -> define como ativa
POST   /api/llm/connections/{id}/test      -> envia mensagem de teste à LLM
"""

from fastapi import APIRouter, Response, status

from app.controllers import llm_controller
from app.schemas.llm import (
    LlmConnectionCreate,
    LlmConnectionOut,
    LlmConnectionUpdate,
    LlmProviderOut,
    LlmTestResult,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/providers", response_model=list[LlmProviderOut])
def list_providers():
    return llm_controller.list_providers()


@router.get("/connections", response_model=list[LlmConnectionOut])
def list_connections():
    return llm_controller.list_connections()


@router.post("/connections", response_model=LlmConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(payload: LlmConnectionCreate):
    return llm_controller.create_connection(payload)


@router.get("/connections/active", response_model=LlmConnectionOut | None)
def get_active_connection():
    active = llm_controller.get_active_connection()
    return llm_controller.to_public(active) if active else None


@router.get("/connections/{connection_id}", response_model=LlmConnectionOut)
def get_connection(connection_id: str):
    return llm_controller.to_public(llm_controller.get_connection_or_404(connection_id))


@router.put("/connections/{connection_id}", response_model=LlmConnectionOut)
def update_connection(connection_id: str, payload: LlmConnectionUpdate):
    return llm_controller.update_connection(connection_id, payload)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(connection_id: str):
    llm_controller.delete_connection(connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/connections/{connection_id}/activate", response_model=LlmConnectionOut)
def activate_connection(connection_id: str):
    return llm_controller.activate_connection(connection_id)


@router.post("/connections/{connection_id}/test", response_model=LlmTestResult)
def test_connection(connection_id: str):
    return llm_controller.test_connection(connection_id)
