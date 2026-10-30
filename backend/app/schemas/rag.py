from pydantic import Field

from app.schemas.base import CamelModel


class RollTable(CamelModel):
    title: str
    dice_roll: str
    description: str


class ChaosRollPayload(CamelModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    chaos_level: int = Field(..., ge=0, le=3)  # 0 Baixo, 1 Médio, 2 Alto, 3 Louco


class ChaosRollOut(CamelModel):
    roll_token: str     # devolvido em QueryRagPayload.roll_token
    hallucinated: bool  # o front muda o "pensamento" para laranja
    chaos_level: int
    chaos_label: str
    roll: dict  # cálculo da regra: words, dateSum, divisor, result, decimal, threshold, recordedAt


class QueryRagPayload(CamelModel):
    prompt: str = Field(..., min_length=1, max_length=4000)
    chaos_level: int = Field(..., ge=0, le=3)  # 0 Baixo, 1 Médio, 2 Alto, 3 Louco
    # Regra Nimb ligada: decide pela regra, com o token de POST /api/rag/roll.
    # Desligada: decide depois da busca, pela chance do nível no .env.
    use_chaos_rule: bool
    roll_token: str | None = None
    book_ids: list[str] | None = None  # só restringe a busca aos livros já liberados
    session_id: str | None = None
    connection_id: str | None = None


class SourceOut(CamelModel):
    book_id: str
    book_title: str
    title: str
    path: str
    kind: str
    page: str
    similarity: float


class QueryRagResponse(CamelModel):
    answer: str
    book_title: str
    page: str | int | None = None
    similarity: str
    chaos_applied: int
    chaos_label: str
    harness_rounds: int  # voltas de revisão executadas
    hallucinated: bool   # Nimb alterou a resposta de propósito
    quote: str | None = None
    roll_table: RollTable | None = None
    sources: list[SourceOut] = []
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
