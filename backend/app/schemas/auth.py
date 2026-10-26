from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel

# Limites de tamanho em todos os campos: evitam payloads gigantes (DoS) e
# entradas inesperadas. O conteúdo é validado nos controllers.


class AuthConfigOut(CamelModel):
    google_client_id: str | None


class GoogleLoginPayload(CamelModel):
    credential: str = Field(..., min_length=10, max_length=4096)
    remember: bool = False


class UpdateProfilePayload(CamelModel):
    name: str = Field(..., min_length=1, max_length=80)


class UserOut(CamelModel):
    email: str
    name: str
    role: Literal["user", "admin"]
    is_active: bool
    google_linked: bool
    created_at: str
    last_login_at: str | None


class MessageOut(CamelModel):
    message: str


class AdminUserUpdate(CamelModel):
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None
