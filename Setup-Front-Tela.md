# Subindo o sistema localmente (Front V2 + Backend + LLM)

Fluxo: **tela (React/Vite, porta 3000) → proxy `/api` → backend FastAPI (porta 8000) → LLM configurada pela tela**.

> Nesta etapa ainda não há RAG: as perguntas vão direto para a LLM, sem consultar livros nem banco vetorial.

## 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python main.py                  # http://localhost:8000  (Swagger em /docs)
```

- Configuração opcional: copie `backend/.env.example` para `backend/.env`.
- O banco local (SQLite) é criado sozinho em `backend/data/nimb.db`. Ele guarda as conexões LLM (inclusive as API keys) e o histórico das conversas, e fica fora do Git.
- No Windows, se o `pip install` falhar com um erro de caminho longo (`No such file or directory ... anthropic\types\beta\...`), crie o venv num caminho mais curto ou ative o suporte a caminhos longos do Windows.

## 2. Frontend (`frontend/V2 - front Studio`)

Pré-requisito: Node.js 20+.

```bash
cd "frontend/V2 - front Studio"
npm install
npm run dev                     # http://localhost:3000
```

Nenhum `.env` é necessário: o Vite encaminha `/api/*` para `http://localhost:8000`.
Opções em `.env.example` (copie para `.env.local`):

| Variável | Uso |
|---|---|
| `BACKEND_PROXY_TARGET` | muda o destino do proxy (padrão `http://localhost:8000`) |
| `VITE_BACKEND_URL` | chama o backend direto, sem proxy (depende do CORS) |
| `VITE_USE_MOCK=true` | roda sem backend, com respostas simuladas |

## 3. Conectar uma LLM e perguntar

1. Abra http://localhost:3000.
2. Clique no botão **Conectar LLM** no topo (ícone `hub`).
3. Escolha o provedor, informe a API key e, se quiser, o modelo, e clique em **Conectar LLM**. Use **Testar** para validar a conexão.
4. Faça uma pergunta no chat. A resposta aparece na tela com o modelo usado e o tempo de resposta, e a conversa é salva em **Perguntas Anteriores**.

| Provedor | API key | Modelo padrão | Observação |
|---|---|---|---|
| OpenAI | sim | `gpt-4o-mini` | |
| Anthropic (Claude) | sim | `claude-opus-5-5` | deixe a temperatura em branco |
| Google Gemini | sim | `gemini-2.5-flash` | |
| DeepSeek | sim | `deepseek-chat` | |
| Ollama (local) | não | `llama3.1` | precisa do Ollama rodando (`ollama pull llama3.1`) |
| Compatível com OpenAI | opcional | — | LM Studio, vLLM etc. Informe a Base URL |

O modelo é editável. Os padrões são só sugestões.

Também é possível criar a conexão sem passar pela tela, pelo `backend/.env` (`LLM_PROVIDER`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_BASE_URL`). Ela é criada quando a API sobe com o banco vazio.

## 4. Rotas da API

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/health` | status da API e LLM ativa |
| GET | `/api/llm/providers` | provedores suportados |
| GET / POST | `/api/llm/connections` | lista / cria conexão |
| GET | `/api/llm/connections/active` | conexão ativa |
| GET / PUT / DELETE | `/api/llm/connections/{id}` | detalhe / atualiza / remove |
| POST | `/api/llm/connections/{id}/activate` | torna a conexão ativa |
| POST | `/api/llm/connections/{id}/test` | envia uma mensagem de teste |
| GET / POST / DELETE | `/api/sessions` | lista / cria / apaga todas as conversas |
| GET / PATCH / DELETE | `/api/sessions/{id}` | conversa com mensagens / renomeia / apaga |
| GET | `/api/sessions/{id}/messages` | mensagens da conversa |
| POST | `/api/rag/query` | **pergunta → LLM → resposta** (`{prompt, chaosLevel, sessionId?, connectionId?}`) |
| POST | `/api/rag/upload` | stub de upload de livro (etapa de RAG) |
| POST | `/api/perguntas` | contrato legado do protótipo estático |

Erros voltam como `{"detail": "..."}`: `409` quando não há LLM ativa, `502` quando o provedor falha (chave inválida, modelo inexistente, timeout) e `404` para um recurso inexistente.

## 5. Estrutura do backend

```text
backend/
├── main.py               ponto de entrada (python main.py)
└── app/
    ├── main.py           FastAPI, CORS, handlers de erro, routers
    ├── core/             config (.env) e exceções
    ├── db/               SQLite
    ├── schemas/          contratos Pydantic (JSON em camelCase)
    ├── repositories/     acesso a dados
    ├── services/         cliente multi-provedor de LLM + prompt do Nimb
    ├── controllers/      regras de negócio
    └── routers/          rotas HTTP
```

O ponto de extensão para o RAG está em `app/controllers/query_controller.py`: os trechos recuperados do banco vetorial entram no prompt antes da chamada à LLM.
