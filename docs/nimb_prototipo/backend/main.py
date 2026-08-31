from time import perf_counter
from uuid import UUID
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Respostas de Nimb API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "respostas-de-nimb",
        "rag_engine": "aguardando_implementacao",
    }


@app.post("/api/perguntas", response_model=RespostaResponse)
def perguntar(payload: PerguntaRequest):
    started = perf_counter()

    # Ponto de extensão do RAG:
    # 1. recuperar chunks no ChromaDB;
    # 2. montar contexto;
    # 3. chamar o LLM;
    # 4. retornar fontes e páginas.
    resposta = (
        "Backend conectado. O pipeline RAG ainda não foi preenchido. "
        "A pergunta foi recebida corretamente e está pronta para ser "
        "encaminhada ao serviço RAG."
    )

    return RespostaResponse(
        pergunta=payload.pergunta,
        resposta=resposta,
        fontes=[],
        status="aguardando_implementacao",
        tempo_resposta_ms=round((perf_counter() - started) * 1000),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
