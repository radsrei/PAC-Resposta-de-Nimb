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
