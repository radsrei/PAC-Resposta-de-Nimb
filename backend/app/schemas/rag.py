from pydantic import Field

from app.schemas.base import CamelModel


class RollTable(CamelModel):
    title: str
    dice_roll: str
    description: str


class QueryRagPayload(CamelModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    chaos_level: int = Field(default=50, ge=0, le=100)
    book_ids: list[str] | None = None  # reservado para a etapa de RAG
    session_id: str | None = None
    connection_id: str | None = None


class QueryRagResponse(CamelModel):
    answer: str
    book_title: str
    page: str | int | None = None
    similarity: str
    chaos_applied: int
    quote: str | None = None
    roll_table: RollTable | None = None
    # Dados da execução na LLM
    session_id: str
    message_id: str
    provider: str
    model: str
    connection_name: str
    latency_ms: int


class IndexedBookResponse(CamelModel):
    id: str
    title: str
    file_name: str
    size: str
    chunks: int
    progress: int
    status: str
    badge_color: str | None = None
