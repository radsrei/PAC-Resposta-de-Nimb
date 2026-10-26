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

Provedores e conexão ativa: qualquer usuário logado. Demais rotas: administradores
(as conexões guardam API keys e valem para o sistema todo).
"""

from fastapi import APIRouter, Depends, Response, status

from app.controllers import llm_controller
from app.core.deps import require_admin, require_user
from app.schemas.llm import (
    LlmConnectionCreate,
    LlmConnectionOut,
    LlmConnectionUpdate,
    LlmProviderOut,
    LlmTestResult,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])
admin_only = [Depends(require_admin)]


@router.get("/providers", response_model=list[LlmProviderOut], dependencies=[Depends(require_user)])
def list_providers():
    return llm_controller.list_providers()


@router.get("/connections", response_model=list[LlmConnectionOut], dependencies=admin_only)
def list_connections():
    return llm_controller.list_connections()


@router.post("/connections", response_model=LlmConnectionOut, status_code=status.HTTP_201_CREATED, dependencies=admin_only)
def create_connection(payload: LlmConnectionCreate):
    return llm_controller.create_connection(payload)


@router.get("/connections/active", response_model=LlmConnectionOut | None,
            dependencies=[Depends(require_user)])
def get_active_connection():
    active = llm_controller.get_active_connection()
    return llm_controller.to_public(active) if active else None


@router.get("/connections/{connection_id}", response_model=LlmConnectionOut, dependencies=admin_only)
def get_connection(connection_id: str):
    return llm_controller.to_public(llm_controller.get_connection_or_404(connection_id))


@router.put("/connections/{connection_id}", response_model=LlmConnectionOut, dependencies=admin_only)
def update_connection(connection_id: str, payload: LlmConnectionUpdate):
    return llm_controller.update_connection(connection_id, payload)


@router.delete("/connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin_only)
def delete_connection(connection_id: str):
    llm_controller.delete_connection(connection_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/connections/{connection_id}/activate", response_model=LlmConnectionOut, dependencies=admin_only)
def activate_connection(connection_id: str):
    return llm_controller.activate_connection(connection_id)


@router.post("/connections/{connection_id}/test", response_model=LlmTestResult, dependencies=admin_only)
def test_connection(connection_id: str):
    return llm_controller.test_connection(connection_id)
