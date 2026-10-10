# NIMB_OS — Front V2

Tela final do projeto Respostas de Nimb (React + Vite + Tailwind).

```bash
npm install
npm run dev     # http://localhost:3000 (com o backend rodando em http://localhost:8000)
```

O guia completo, que cobre backend, conexão com a LLM e rotas, está em [`Setup-Front-Tela.md`](../../Setup-Front-Tela.md).

## Estrutura

```text
src/
├── App.tsx                     estado da tela e orquestração das chamadas
├── services/
│   ├── http.ts                 cliente HTTP base (erros, proxy /api)
│   ├── ragApi.ts               POST /api/rag/query (pergunta → LLM)
│   ├── llmApi.ts               CRUD das conexões LLM
│   ├── sessionApi.ts           CRUD das conversas (Perguntas Anteriores)
│   └── authApi.ts              login (simulado)
└── components/
    ├── layout/                 Header (status da LLM), Sidebar (histórico)
    ├── chat/                   área de chat e mensagens
    ├── modals/LlmConnectionModal.tsx   caixa de conexão com a LLM
    ├── modals/PdfUploadModal.tsx       upload de livros (etapa de RAG)
    └── auth/                   tela de login
```
