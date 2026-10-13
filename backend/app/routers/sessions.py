"""
Rotas das conversas do usuário logado ("Perguntas Anteriores" na barra lateral).

GET    /api/sessions                 -> lista sessões
POST   /api/sessions                 -> cria sessão vazia
DELETE /api/sessions                 -> apaga todas as sessões
GET    /api/sessions/{id}            -> sessão com mensagens
PATCH  /api/sessions/{id}            -> renomeia
DELETE /api/sessions/{id}            -> apaga a sessão
GET    /api/sessions/{id}/messages   -> mensagens da sessão
"""

from fastapi import APIRouter, Depends, Response, status

from app.controllers import session_controller
from app.core.deps import CurrentUser, require_user
from app.schemas.sessions import (
    MessageOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
    SessionUpdate,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionOut])
def list_sessions(user: CurrentUser = Depends(require_user)):
    return session_controller.list_sessions(user["email"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(payload: SessionCreate, user: CurrentUser = Depends(require_user)):
    return session_controller.create_session(user["email"], payload.title)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_sessions(user: CurrentUser = Depends(require_user)):
    session_controller.delete_all_sessions(user["email"])
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: str, user: CurrentUser = Depends(require_user)):
    return session_controller.get_session_detail(user["email"], session_id)


@router.patch("/{session_id}", response_model=SessionOut)
def rename_session(session_id: str, payload: SessionUpdate, user: CurrentUser = Depends(require_user)):
    return session_controller.rename_session(user["email"], session_id, payload.title)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, user: CurrentUser = Depends(require_user)):
    session_controller.delete_session(user["email"], session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: str, user: CurrentUser = Depends(require_user)):
    return session_controller.list_messages(user["email"], session_id)
