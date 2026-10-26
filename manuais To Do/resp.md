A integração está pronta. O sistema sobe localmente: você abre a tela, cadastra a API de uma LLM, faz uma pergunta e a resposta aparece no chat. Não fiz commit; as mudanças estão na branch `feat/remover_telas`.

**Para subir:**
```bash
cd backend && pip install -r requirements.txt && python main.py         # porta 8000
CTRL + C #Sair
```
### http://localhost:8000 
```bash
winget install -e --id OpenJS.NodeJS.LTS
cd "frontend/V2 - front Studio" && npm install && npm run dev            # porta 3000
q + ENTER       #Sair
```
### http://localhost:3000
Depois clique em **Conectar LLM** no topo da tela, escolha o provedor, cole a API key e pergunte. O passo a passo completo e a lista de rotas estão em [Setup-Front-Tela.md](Setup-Front-Tela.md).

**Backend** ([backend/app/](backend/app/))
- Organizei o código em camadas: `routers` → `controllers` → `repositories` → `services`, com `schemas` em Pydantic e um banco SQLite local criado sozinho em `backend/data/`.
- **CRUD das conexões LLM** (`/api/llm/connections`): criar, listar, editar, excluir, ativar e testar. A API key nunca volta nas respostas, só uma prévia mascarada.
- **CRUD das conversas** (`/api/sessions`): é o histórico da barra lateral "Perguntas Anteriores".
- **`POST /api/rag/query`**: recebe a pergunta, monta o prompt da persona Nimb (o Medidor de Caos muda o tom), inclui as últimas mensagens da conversa e chama a LLM ativa. A conversa só é gravada se a LLM responder.
- **Provedores:** OpenAI, Anthropic (pelo SDK oficial), Gemini, DeepSeek, Ollama local e qualquer API compatível com a OpenAI.
- **Erros:** voltam como mensagem legível: 409 quando não há LLM ativa, 502 quando o provedor falha, 404 quando o recurso não existe.
- O `python main.py` continua funcionando como antes, e o contrato antigo `/api/perguntas` foi mantido.

**Front V2**
- **Nova caixa de conexão:** [LlmConnectionModal.tsx](frontend/V2%20-%20front%20Studio/src/components/modals/LlmConnectionModal.tsx). O botão no Header mostra o estado: verde com o modelo ativo, amarelo sem LLM, vermelho com o backend fora do ar.
- **Dados reais:** o chat consome o backend de verdade, e as respostas mostram qual modelo respondeu e quanto tempo levou. Erros aparecem no próprio chat; se não houver LLM, a caixa de conexão abre sozinha. O histórico vem do banco, e dá para excluir uma conversa ou limpar todas.
- **Proxy no Vite:** as chamadas `/api` são encaminhadas para o backend, então não precisa de `.env` nem de ajuste de CORS. A simulação antiga só roda se você definir `VITE_USE_MOCK=true`.
- **Dependências:** removi as que não eram usadas (`@google/genai`, `express`, `dotenv`).

**Testes que rodei**
- **Backend:** um script de teste passou em todas as rotas, nos formatos dos provedores (com as LLMs simuladas) e nos casos de erro.
- **Ponta a ponta:** subi o backend, o Vite e uma LLM falsa local. Pelo proxy na porta 3000, a pergunta foi respondida e a segunda pergunta na mesma conversa levou o histórico junto.
- **Front:** o `tsc --noEmit` e o `vite build` passaram, usando um Node temporário que já apaguei.
- **Não testei com chave real** de nenhum provedor nem abri a tela num navegador. A primeira pergunta com sua chave será o teste final.

**Pontos de atenção**
- **API keys:** ficam em texto puro no SQLite local, fora do Git. Serve para desenvolvimento local, não para produção.
- **Windows:** o pacote `anthropic` tem caminhos de arquivo muito longos. Num venv em pasta muito profunda, o `pip install` pode falhar. Anotei no guia; o venv `nimb` na raiz do projeto não deve ter esse problema.
- **Livros e RAG:** não mexi. O upload de livros continua como stub e a lista de livros na tela continua fixa. O ponto onde o RAG vai entrar está marcado em [query_controller.py](backend/app/controllers/query_controller.py).
- **Modelos padrão:** os nomes sugeridos (ex.: `gpt-4o-mini`) são editáveis na própria tela.

