"""
Administração de usuários e da lista de acesso (somente administradores).

GET    /api/admin/users                          -> lista usuários
PATCH  /api/admin/users/{email}                  -> altera papel / ativa / desativa
DELETE /api/admin/users/{email}                  -> exclui a conta
GET    /api/admin/allowed-emails                 -> lista de acesso
POST   /api/admin/allowed-emails                 -> inclui e-mails na lista
DELETE /api/admin/allowed-emails/{email}         -> remove um e-mail (encerra as sessões dele)
"""

from fastapi import APIRouter, Depends

from app.controllers import user_controller
from app.core.deps import CurrentUser, require_admin
from app.schemas.auth import AdminUserUpdate, AllowlistAddPayload, AllowlistOut, MessageOut, UserOut

router = APIRouter(prefix="/api/admin/users", tags=["admin"])
allowlist_router = APIRouter(prefix="/api/admin/allowed-emails", tags=["admin"])


@router.get("", response_model=list[UserOut])
def list_users(_: CurrentUser = Depends(require_admin)):
    return user_controller.list_users()


@router.patch("/{email}", response_model=UserOut)
def update_user(email: str, payload: AdminUserUpdate, admin: CurrentUser = Depends(require_admin)):
    return user_controller.update_user(admin, email, payload)


@router.delete("/{email}", response_model=MessageOut)
def delete_user(email: str, admin: CurrentUser = Depends(require_admin)):
    user_controller.delete_user(admin, email)
    return {"message": "Usuário excluído."}


@allowlist_router.get("", response_model=AllowlistOut)
def list_allowed(_: CurrentUser = Depends(require_admin)):
    return user_controller.list_allowed()


@allowlist_router.post("", response_model=AllowlistOut)
def add_allowed(payload: AllowlistAddPayload, admin: CurrentUser = Depends(require_admin)):
    return user_controller.add_allowed(admin, payload.emails)


@allowlist_router.delete("/{email}", response_model=MessageOut)
def remove_allowed(email: str, admin: CurrentUser = Depends(require_admin)):
    user_controller.remove_allowed(admin, email)
    return {"message": "E-mail removido da lista de acesso."}
