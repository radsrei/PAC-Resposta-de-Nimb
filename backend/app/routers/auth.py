"""
Rotas de autenticação. O único método de login é o Google.

GET    /api/auth/config            -> configuração pública (Client ID do Google)
POST   /api/auth/google            -> login com Google (ID token)
POST   /api/auth/logout            -> encerra a sessão atual
POST   /api/auth/logout-all        -> encerra as outras sessões do usuário
GET    /api/auth/me                -> usuário logado
PATCH  /api/auth/me                -> altera o nome
DELETE /api/auth/me                -> exclui a própria conta

A sessão fica num cookie HttpOnly (inacessível a JavaScript, protege contra
roubo via XSS), SameSite=Strict (protege contra CSRF) e restrito a /api.
"""

from fastapi import APIRouter, Depends, Request, Response

from app.controllers import auth_controller
from app.controllers.auth_controller import LoginResult
from app.core.config import settings
from app.core.deps import CurrentUser, get_current_user
from app.core.rate_limit import client_ip, limit_auth
from app.core.security import hash_token
from app.schemas.auth import (
    AuthConfigOut,
    GoogleLoginPayload,
    MessageOut,
    UpdateProfilePayload,
    UserOut,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

COOKIE_PATH = "/api"


def _set_session_cookie(response: Response, result: LoginResult) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=result.token,
        max_age=result.max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=COOKIE_PATH,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


@router.get("/config", response_model=AuthConfigOut)
def get_config():
    return auth_controller.auth_config()


@router.post("/google", response_model=UserOut, dependencies=[Depends(limit_auth)])
def login_google(payload: GoogleLoginPayload, request: Request, response: Response):
    result = auth_controller.login_google(
        payload.credential, payload.remember,
        client_ip(request), request.headers.get("user-agent"),
    )
    _set_session_cookie(response, result)
    return result.user


@router.post("/logout", response_model=MessageOut)
def logout(request: Request, response: Response):
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        auth_controller.logout(hash_token(token))
    _clear_session_cookie(response)
    return {"message": "Sessão encerrada."}


@router.post("/logout-all", response_model=MessageOut)
def logout_all(user: CurrentUser = Depends(get_current_user)):
    count = auth_controller.logout_other_sessions(user)
    return {"message": f"{count} outra(s) sessão(ões) encerrada(s)."}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)):
    return auth_controller.public_user(user)


@router.patch("/me", response_model=UserOut)
def update_me(payload: UpdateProfilePayload, user: CurrentUser = Depends(get_current_user)):
    return auth_controller.update_profile(user, payload.name)


@router.delete("/me", response_model=MessageOut)
def delete_me(response: Response, user: CurrentUser = Depends(get_current_user)):
    auth_controller.delete_account(user)
    _clear_session_cookie(response)
    return {"message": "Conta excluída."}
