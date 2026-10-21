from pydantic import Field

from app.schemas.base import CamelModel


class RollTable(CamelModel):
    title: str
    dice_roll: str
    description: str


class QueryRagPayload(CamelModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    chaos_level: int = Field(default=50, ge=0, le=100)
    book_ids: list[str] | None = None  # reservado para a busca no banco vetorial
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


class BookOut(CamelModel):
    id: str
    title: str
    unlocked: bool            # o usuário já validou o PDF deste livro
    unlocked_at: str | None
    vector_ready: bool        # banco vetorial do livro já foi construído
    chunks: int
    page_count: int | None = None


class BookCheckOut(CamelModel):
    name: str
    label: str
    passed: bool


class BookValidationOut(CamelModel):
    accepted: bool
    message: str
    score: float
    checks: list[BookCheckOut]
    book: BookOut | None = None
