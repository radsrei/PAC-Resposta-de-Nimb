"""Contrato ORIGINAL do protótipo estático (frontend/Claude, docs/nimb_prototipo)."""

from uuid import UUID

from pydantic import BaseModel, Field


class PerguntaRequest(BaseModel):
    pergunta: str = Field(..., min_length=10, max_length=500)
    categoria: str | None = None
    sessao_id: UUID | None = None


class FonteResponse(BaseModel):
    titulo: str
    pagina: int | None = None
    secao: str | None = None
    trecho: str | None = None


class RespostaResponse(BaseModel):
    pergunta: str
    resposta: str
    fontes: list[FonteResponse]
    status: str
    tempo_resposta_ms: int
