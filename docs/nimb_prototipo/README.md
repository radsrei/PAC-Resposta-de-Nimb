# Integração Frontend -> Backend — Respostas de Nimb

Esta etapa conecta a tela Stitch fornecida ao backend FastAPI.

## Estrutura

- `frontend/nimb_terminal.html`: tela Stitch com o JavaScript de integração.
- `backend/main.py`: API FastAPI preparada para receber perguntas.
- `backend/requirements.txt`: dependências mínimas.

## Executar

### Backend

```bash
cd backend
python -m venv .venv
# Linux/macOS
#source .venv/bin/activate
# Windows
.venv\Scripts\activate

pip install -r requirements.txt
python main.py
```

API: `http://localhost:8000`

Swagger: `http://localhost:8000/docs`

### Frontend

Em outro terminal:

```bash
cd frontend
python -m http.server 5500
```

Abrir:

`http://localhost:5500/nimb_terminal.html`

## Contrato atual

### POST `/api/perguntas`

```json
{
  "pergunta": "Qual é o status do kernel?",
  "categoria": null,
  "sessao_id": "uuid-da-sessao"
}
```

### Resposta

```json
{
  "pergunta": "Qual é o status do kernel?",
  "resposta": "Backend conectado...",
  "fontes": [],
  "status": "aguardando_implementacao",
  "tempo_resposta_ms": 0
}
```

O `main.py` não implementa o RAG ainda. O ponto de extensão está marcado dentro da função `perguntar()`.
