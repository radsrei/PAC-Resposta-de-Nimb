"""
Respostas de Nimb — API (FastAPI)

Ponto de entrada do backend. A aplicação fica em `app/`, organizada em camadas:

    app/
    ├── core/          configurações (.env) e exceções de domínio
    ├── db/            SQLite local (conexões LLM, sessões e mensagens)
    ├── schemas/       modelos Pydantic (contratos de entrada/saída)
    ├── repositories/  acesso a dados
    ├── services/      cliente multi-provedor de LLM e prompts
    ├── controllers/   regras de negócio
    └── routers/       rotas HTTP

Rode com (dentro da pasta `backend/`):
    python main.py
ou
    uvicorn main:app --reload

API:      http://localhost:8000
Swagger:  http://localhost:8000/docs
"""

from app.core.config import settings
from app.main import app  # noqa: F401  (usado pelo uvicorn: "main:app")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        reload_dirs=["app"],
    )
