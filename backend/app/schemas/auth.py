from typing import Literal

from pydantic import Field

from app.core.security import PASSWORD_MAX_LENGTH
from app.schemas.base import CamelModel

# Limites de tamanho em todos os campos: evitam payloads gigantes (DoS) e
# entradas inesperadas. O conteúdo é validado nos controllers.
EmailField = Field(..., min_length=3, max_length=254)
PasswordField = Field(..., min_length=1, max_length=PASSWORD_MAX_LENGTH)


class AuthConfigOut(CamelModel):
    google_client_id: str | None
    registration_enabled: bool
    password_min_length: int


class RegisterPayload(CamelModel):
    name: str = Field(..., min_length=1, max_length=80)
    email: str = EmailField
    password: str = PasswordField


class LoginPayload(CamelModel):
    email: str = EmailField
    password: str = PasswordField
    remember: bool = False


class GoogleLoginPayload(CamelModel):
    credential: str = Field(..., min_length=10, max_length=4096)
    remember: bool = False


class ChangePasswordPayload(CamelModel):
    # Opcional apenas para contas Google que ainda não têm senha
    current_password: str | None = Field(default=None, max_length=PASSWORD_MAX_LENGTH)
    new_password: str = PasswordField


class ForgotPasswordPayload(CamelModel):
    email: str = EmailField


class ResetPasswordPayload(CamelModel):
    token: str = Field(..., min_length=10, max_length=200)


class UpdateProfilePayload(CamelModel):
    name: str = Field(..., min_length=1, max_length=80)


class DeleteAccountPayload(CamelModel):
    password: str | None = Field(default=None, max_length=PASSWORD_MAX_LENGTH)


class UserOut(CamelModel):
    email: str
    name: str
    role: Literal["user", "admin"]
    is_active: bool
    must_change_password: bool
    has_password: bool
    google_linked: bool
    created_at: str
    last_login_at: str | None


class MessageOut(CamelModel):
    message: str


class PasswordResetOut(CamelModel):
    message: str
    temporary_password: str


class AdminUserUpdate(CamelModel):
    role: Literal["user", "admin"] | None = None
    is_active: bool | None = None
