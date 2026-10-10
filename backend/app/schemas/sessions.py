from typing import Any, Literal

from pydantic import Field

from app.schemas.base import CamelModel


class SessionCreate(CamelModel):
    title: str | None = Field(default=None, max_length=120)


class SessionUpdate(CamelModel):
    title: str = Field(..., min_length=1, max_length=120)


class MessageOut(CamelModel):
    id: str
    session_id: str
    role: Literal["user", "assistant"]
    content: str
    metadata: dict[str, Any] | None = None
    created_at: str


class SessionOut(CamelModel):
    id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str


class SessionDetail(SessionOut):
    messages: list[MessageOut]
