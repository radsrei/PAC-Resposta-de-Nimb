# Integração — Front-end React (NIMB_OS) + Backend

> Repositório do projeto: https://github.com/radsrei/PAC-Resposta-de-Nimb

Este guia documenta como o front-end React `nimb-os-react` (telas Terminal / Login /
Upload de PDF, gerado a partir dos mockups em `frontend/Proposta de Tela (Stitich)/`)
se conecta ao backend FastAPI do projeto, e como publicar essa mudança respeitando
o histórico de branches já existente.

## 1. Contexto: branches e onde este trabalho se encaixa

```text
main
 └── develop
      └── feat/tela-simples          (mockups Stitch + frontend/Claude em HTML/JS)
           └── feat/frontend-react   (nimb-os-react — este guia)
```

- `feat/tela-simples` é a branch mais avançada em termos de UI: contém os mockups
  originais (`frontend/Proposta de Tela (Stitich)/`) e uma primeira implementação em
  HTML/CSS/JS puro (`frontend/Claude/`).
- O front-end React enviado (`nimb-os-react`) é a evolução dessas mesmas 3 telas
  (Terminal/Chat, Login, Upload de PDF), então deve ser criado **a partir de
  `feat/tela-simples`**, não de `main` nem `develop`.
- O backend de referência para o contrato de API é
  `docs/nimb_prototipo/backend/main.py`.

## 2. Mapeamento mockup → componente React

| Mockup (Stitch) | Componente React |
|---|---|
| `nimb_os_login_neural_sync` | `src/components/auth/LoginScreen.tsx` |
| `nimb_rag_neural_terminal` | `src/components/chat/ChatArea.tsx` + `Sidebar.tsx` + `Header.tsx` |
| `initialize_new_flux_kernel_config` | `src/components/modals/PdfUploadModal.tsx` |

## 3. Passo a passo em Git

### 3.1 Clonar e posicionar na branch base

```bash
git clone https://github.com/radsrei/PAC-Resposta-de-Nimb.git
cd PAC-Resposta-de-Nimb

git fetch --all
git checkout -b feat/tela-simples origin/feat/tela-simples
```

### 3.2 Criar a branch do front React

```bash
git checkout -b feat/frontend-react feat/tela-simples
```

### 3.3 Adicionar os arquivos do projeto React

```bash
mkdir -p frontend/nimb-os-react
```

Copie o conteúdo do pacote `nimb_os---neural-chaos-rag-terminal.zip` para dentro de
`frontend/nimb-os-react/`, preservando a estrutura:

```text
frontend/nimb-os-react/
├── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
├── .env.example
└── src/
    ├── App.tsx
    ├── main.tsx
    ├── index.css
    ├── types/index.ts
    ├── services/
    │   ├── ragApi.ts
    │   └── authApi.ts
    └── components/
        ├── layout/   (Header.tsx, Sidebar.tsx)
        ├── chat/     (ChatArea.tsx, ChatInput.tsx, ChatMessageItem.tsx, SuggestionChips.tsx)
        ├── auth/     (LoginScreen.tsx)
        └── modals/   (PdfUploadModal.tsx)
```

### 3.4 Atualizar o backend

Substitua `docs/nimb_prototipo/backend/main.py` pela versão mesclada
(`main.py` anexo a este pacote — ver seção 5). Ele mantém o contrato antigo
(`/api/perguntas`, usado por `frontend/Claude`) e adiciona o contrato novo
(`/api/rag/query` e `/api/rag/upload`, usado por `nimb-os-react`).

```bash
cp /caminho/para/main.py docs/nimb_prototipo/backend/main.py
```

### 3.5 Commit e push

```bash
git add frontend/nimb-os-react docs/nimb_prototipo/backend/main.py
git status   # conferir o que vai entrar
git commit -m "feat(frontend+backend): integra front React (NIMB_OS) e unifica contrato de API do backend"
git push -u origin feat/frontend-react
```

### 3.6 Pull Request

Abra o PR em `https://github.com/radsrei/PAC-Resposta-de-Nimb/pulls`,
com **base = `feat/tela-simples`** (é dela que a branch derivou).

## 4. Rodando localmente

**Backend:**

```bash
cd docs/nimb_prototipo/backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py                 # http://localhost:8000  (Swagger em /docs)
```

**Front-end React:**

```bash
cd frontend/nimb-os-react
cp .env.example .env.local
```

No `.env.local`:

```env
VITE_BACKEND_URL=http://localhost:8000
```

```bash
npm install
npm run dev                    # http://localhost:3000
```

Com `VITE_BACKEND_URL` vazio, o app funciona sozinho com respostas simuladas
(`ragApiService`). Ao preencher a variável, ele passa a consumir o backend real,
sem alterações de código.

## 5. Contrato de API unificado (`main.py` mesclado)

| Rota | Método | Usado por | Body | Resposta |
|---|---|---|---|---|
| `/api/health` | GET | monitoramento | — | `{status, service, rag_engine}` |
| `/api/perguntas` | POST | `frontend/Claude`, `docs/nimb_prototipo/frontend` | `{pergunta, categoria?, sessao_id?}` | `{pergunta, resposta, fontes[], status, tempo_resposta_ms}` |
| `/api/rag/query` | POST | `frontend/nimb-os-react` (`ragApi.ts`) | `{prompt, chaosLevel, bookIds?}` | `{answer, bookTitle, page, similarity, chaosApplied, quote?, rollTable?}` |
| `/api/rag/upload` | POST (multipart) | `frontend/nimb-os-react` (`ragApi.ts`) | `file, chunkSize, model, entropy` | `{id, title, fileName, size, chunks, progress, status, badgeColor?}` |

Os `TODO`s marcados no arquivo indicam onde plugar o pipeline RAG real
(retrieval no vector DB + chamada ao LLM), reaproveitando o que já existe em
`Convert_file/` e `backend/RAG_Claude|RAG_GPT|RAG_Gemini/`.

CORS liberado para:
- `http://localhost:5500` / `http://127.0.0.1:5500` (protótipo estático)
- `http://localhost:3000` / `http://127.0.0.1:3000` (Vite / React)

## 6. Checklist antes de abrir o PR

- [ ] `npm run lint` (`tsc --noEmit`) sem erros em `frontend/nimb-os-react`
- [ ] `python -m py_compile main.py` sem erros no backend
- [ ] Testar os 3 fluxos manualmente: terminal/chat, login, upload de PDF
- [ ] Confirmar que `frontend/Claude` continua funcionando com `/api/perguntas`
      (contrato antigo preservado)
- [ ] Confirmar que `nimb-os-react` funciona com `/api/rag/query` e
      `/api/rag/upload` (contrato novo)
- [ ] Alinhar na equipe se `frontend/Claude` será descontinuado em favor do
      React, para não manter duas fontes de verdade
- [ ] PR aberto com base `feat/tela-simples`
