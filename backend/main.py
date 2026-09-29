"""
Respostas de Nimb — API (FastAPI)

Este arquivo é a evolução de `docs/nimb_prototipo/backend/main.py`.
Mantém o contrato original (`/api/perguntas`, usado pelo protótipo em
`frontend/Claude` e `docs/nimb_prototipo/frontend/nimb_terminal.html`)
e ADICIONA o contrato exigido pelo front-end React `frontend/nimb-os-react`
(serviço `src/services/ragApi.ts`), para que os dois front-ends existentes
no repositório consigam falar com o mesmo backend sem retrabalho.

Rode com:
    python main.py
ou
    uvicorn main:app --reload

API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
"""

from time import perf_counter
from uuid import UUID

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="Respostas de Nimb API",
    version="0.2.0",
)

# --------------------------------------------------------------------------
# CORS
# --------------------------------------------------------------------------
# 5500 -> protótipo estático (frontend/Claude, docs/nimb_prototipo/frontend)
# 3000 -> front-end React/Vite (frontend/nimb-os-react -> npm run dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================================================
# Health check
# ==========================================================================
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "respostas-de-nimb",
        "rag_engine": "aguardando_implementacao",
    }


# ==========================================================================
# Contrato ORIGINAL — protótipo estático (frontend/Claude e docs/nimb_prototipo)
# POST /api/perguntas
# ==========================================================================
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


# ==========================================================================
# Contrato NOVO — front-end React (frontend/nimb-os-react/src/services/ragApi.ts)
# POST /api/rag/query
# POST /api/rag/upload
# ==========================================================================
class RollTable(BaseModel):
    title: str
    diceRoll: str
    description: str


class QueryRagPayload(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)
    chaosLevel: int = Field(default=50, ge=0, le=100)
    bookIds: list[str] | None = None


class QueryRagResponse(BaseModel):
    answer: str
    bookTitle: str
    page: str | int
    similarity: str
    chaosApplied: int
    quote: str | None = None
    rollTable: RollTable | None = None


@app.post("/api/rag/query", response_model=QueryRagResponse)
def query_rag(payload: QueryRagPayload):
    """
    Espelha o `/api/perguntas`, mas no formato que `ragApiService.queryRag()`
    (frontend/nimb-os-react/src/services/ragApi.ts) já espera receber.

    Ponto de extensão do RAG (o mesmo de `/api/perguntas`):
    1. recuperar chunks relevantes no vector DB, filtrando por `payload.bookIds`
       quando informado;
    2. montar o contexto (respeitando `payload.chaosLevel` na composição do
       prompt, se esse parâmetro for usado para calibrar o "tom" da resposta);
    3. chamar o LLM;
    4. devolver `bookTitle`/`page`/`similarity` da fonte usada.
    """

    # TODO: substituir pelo pipeline real (LangChain + Ollama/LLM, conforme RFC)
    return QueryRagResponse(
        answer=(
            "Backend conectado. O pipeline RAG ainda não foi preenchido. "
            "A pergunta foi recebida corretamente e está pronta para ser "
            "encaminhada ao serviço RAG."
        ),
        bookTitle="N/A",
        page="-",
        similarity="0%",
        chaosApplied=payload.chaosLevel,
        quote=None,
        rollTable=None,
    )


class IndexedBookResponse(BaseModel):
    id: str
    title: str
    fileName: str
    size: str
    chunks: int
    progress: int
    status: str
    badgeColor: str | None = None


@app.post("/api/rag/upload", response_model=IndexedBookResponse)
async def upload_grimorio(
    file: UploadFile = File(...),
    chunkSize: int = Form(...),
    model: str = Form(...),
    entropy: float = Form(...),
):
    """
    Recebe o PDF ("Grimório") enviado pelo modal de upload do front-end React
    e deve indexá-lo no vector DB.

    Ponto de extensão do RAG:
    1. salvar/ler o arquivo (`file`);
    2. aplicar chunking (`chunkSize`) — reaproveitar `Convert_file/` e
       `backend/RAG_Claude|RAG_GPT|RAG_Gemini` já existentes no repositório;
    3. gerar embeddings com o `model` informado;
    4. persistir no vector DB e retornar a contagem real de chunks.
    """

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)

    # TODO: indexação real. Abaixo, apenas um retorno coerente com o contrato
    # esperado por `ragApiService.uploadGrimorio()` no front-end.
    return IndexedBookResponse(
        id=f"book_{file.filename}",
        title=file.filename.rsplit(".", 1)[0] if file.filename else "documento",
        fileName=file.filename or "documento.pdf",
        size=f"{size_mb:.1f} MB",
        chunks=0,
        progress=100,
        status="indexed",
        badgeColor="purple",
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
