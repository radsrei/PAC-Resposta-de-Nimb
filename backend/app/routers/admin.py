"""
Administração de usuários (somente administradores).

GET    /api/admin/users                          -> lista usuários
PATCH  /api/admin/users/{email}                  -> altera papel / ativa / desativa
DELETE /api/admin/users/{email}                  -> exclui a conta
"""

from fastapi import APIRouter, Depends

from app.controllers import user_controller
from app.core.deps import CurrentUser, require_admin
from app.schemas.auth import AdminUserUpdate, MessageOut, UserOut

router = APIRouter(prefix="/api/admin/users", tags=["admin"])


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
