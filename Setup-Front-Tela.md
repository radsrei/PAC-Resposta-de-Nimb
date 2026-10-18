# Subindo o sistema localmente (Front V2 + Backend + LLM + Login)

Fluxo: **tela (React/Vite, porta 3000) → proxy `/api` → backend FastAPI (porta 8000) → LLM configurada pela tela**.

> Nesta etapa a busca no banco vetorial ainda não está ligada ao chat: as perguntas vão direto para a LLM. A validação de livros e a construção do banco vetorial já funcionam (seção 4.1).

## 0. Setup automático (opcional)

O script da raiz faz os passos 1 e 2 e prepara o construtor do banco vetorial (seção 4.1):

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1      # Windows
bash scripts/setup.sh                                             # Linux / macOS
```

Opções e detalhes no [README](README.md#setup-automático). Para fazer à mão, siga as seções abaixo.

## 1. Backend

Use o ambiente `.venv` da raiz do projeto (ver [README](README.md#ambiente-python-venv)). Se ele ainda não existir:

```bash
python -m venv .venv            # na raiz do projeto
.venv\Scripts\activate          # Linux/Mac: source .venv/bin/activate
pip install -r backend/requirements.txt
```

Com o `.venv` ativo:

```bash
cd backend
python main.py                  # http://localhost:8000  (Swagger em /docs)
```

- Configuração: copie `backend/.env.example` para `backend/.env`. O `GOOGLE_CLIENT_ID` é obrigatório para entrar no sistema.
- O banco local (SQLite) é criado sozinho em `backend/data/nimb.db`, junto com a chave de criptografia `backend/data/secret.key`. A pasta `data/` fica fora do Git. Se a `secret.key` for apagada, as API keys das LLMs precisam ser cadastradas de novo.
- No Windows, se o `pip install` falhar com um erro de caminho longo (`No such file or directory ... anthropic\types\beta\...`), mova o projeto para um caminho mais curto ou ative o suporte a caminhos longos do Windows.
- Se a tela mostrar erros 404 em `/api/auth/...`, um backend antigo pode estar preso na porta 8000. Feche os terminais antigos ou encerre o processo: `Get-NetTCPConnection -LocalPort 8000` mostra o PID e `Stop-Process -Id <PID>` encerra.

## 2. Frontend (`frontend/V2 - front Studio`)

Pré-requisito: Node.js 20+.

```bash
cd "frontend/V2 - front Studio"
npm ci                          # instala exatamente as versões do package-lock.json
npm run dev                     # http://localhost:3000
```

Nenhum `.env` é necessário: o Vite encaminha `/api/*` para `http://localhost:8000`.
Opções em `.env.example` (copie para `.env.local`):

| Variável | Uso |
|---|---|
| `BACKEND_PROXY_TARGET` | muda o destino do proxy (padrão `http://localhost:8000`) |
| `VITE_BACKEND_URL` | chama o backend direto, sem proxy (depende do CORS) |
| `VITE_USE_MOCK=true` | roda sem backend, com respostas simuladas |

## 3. Login e contas

Ao abrir http://localhost:3000, aparece a tela de login. Nada do sistema fica acessível sem uma sessão válida.

**O único método de acesso é o login com Google** (configuração na seção 3.1). Não há cadastro com e-mail e senha, troca de senha nem recuperação de senha.

**Primeiro acesso:** clique em **Fazer login com o Google**. A conta no Nimb é criada automaticamente no primeiro login. A primeira conta criada vira **administradora** (`FIRST_USER_IS_ADMIN`). Também é possível definir administradores fixos em `ADMIN_EMAILS`. Com `REGISTRATION_ENABLED=false`, só entram usuários que já existem no banco.

| Funcionalidade | Onde fica |
|---|---|
| Entrar com Google, com opção "Manter conectado" (7 dias) | tela de login |
| Editar nome, encerrar outras sessões, excluir conta | botão com seu nome no topo → **Minha conta** |
| Listar usuários, promover a admin, desativar, excluir | **Minha conta** → painel *Usuários do sistema* (só admins) |

Contas antigas, criadas com e-mail e senha antes desta versão, continuam no banco: no primeiro login com Google usando o mesmo e-mail, a conta é vinculada ao Google e mantém conversas e permissões.

**Conexões LLM:** somente administradores cadastram, editam e testam conexões, porque elas guardam API keys e valem para o sistema todo. Usuários comuns veem apenas qual LLM está ativa.

### 3.1 Login com Google

O botão do Google fica desativado até existir um Client ID:

1. Acesse https://console.cloud.google.com → **APIs e serviços** → **Credenciais**.
2. Se for solicitado, configure a **Tela de consentimento OAuth** (tipo *Externo*, com os escopos padrão `email`, `profile` e `openid`).
3. **Criar credenciais** → **ID do cliente OAuth** → tipo **Aplicativo da Web**.
4. Em **Origens JavaScript autorizadas**, adicione `http://localhost:3000`. Não é preciso URI de redirecionamento.
5. Copie o Client ID para `backend/.env`: `GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com`, e reinicie o backend.

O front busca o Client ID em `/api/auth/config`, então ele não é configurado no front. O backend valida o token do Google (assinatura, emissor, expiração e Client ID) e só aceita e-mails verificados. Se já existir uma conta com o mesmo e-mail, o Google é vinculado a ela.

> Sem `GOOGLE_CLIENT_ID`, ninguém consegue entrar no sistema.

### 3.2 Proteções de segurança

| Ameaça | Proteção |
|---|---|
| SQL injection | todas as consultas usam parâmetros (`?`); nomes de coluna vêm de listas fixas no código |
| Senhas | o sistema não guarda senhas: a identidade é confirmada pelo Google (ID token validado no backend) |
| Vazamento do banco | tokens de sessão guardados só como SHA-256; API keys das LLMs criptografadas (Fernet/AES) |
| Roubo de sessão via XSS | sessão em cookie **HttpOnly** (o JavaScript não consegue ler); nada em `localStorage` |
| CSRF | cookie **SameSite=Strict**, mais bloqueio de requisições que alteram dados vindas de origem fora de `CORS_ORIGINS` |
| Abuso do login | limite de 20 requisições por minuto por IP na rota de login |
| Acesso a dados de outro usuário (IDOR) | conversas filtradas pelo usuário logado em todas as consultas |
| Escalada de privilégio | rotas de admin exigem papel `admin`; um admin não pode remover o próprio acesso; sempre resta ao menos um admin |
| Sessões antigas | "Encerrar outras sessões" em **Minha conta**; desativar um usuário encerra todas as sessões dele |
| Vazamento em erros | erros internos devolvem só "Erro interno do servidor" (detalhes ficam no log); erros de validação não ecoam o valor enviado |
| Clickjacking, sniffing e cache | cabeçalhos `X-Frame-Options`, `X-Content-Type-Options`, `Cache-Control: no-store` e CSP na API |

**Para produção:** use HTTPS com `COOKIE_SECURE=true`, defina um `APP_SECRET_KEY` longo e aleatório, desative o Swagger com `ENABLE_DOCS=false` e ajuste `CORS_ORIGINS` para o domínio real. O limite por IP é guardado em memória, então vale por processo da API.

## 4. Conectar uma LLM e perguntar

1. Entre com uma conta de administrador.
2. Clique no botão **Conectar LLM** no topo (ícone `hub`).
3. Escolha o provedor, informe a API key e, se quiser, o modelo, e clique em **Conectar LLM**. Use **Testar** para validar a conexão.
4. Faça uma pergunta no chat. A resposta aparece na tela com o modelo usado e o tempo de resposta, e a conversa é salva em **Perguntas Anteriores**. Cada usuário vê apenas as próprias conversas.

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

### 4.1 Livros e banco vetorial

O banco vetorial de cada livro é construído à parte, a partir do PDF original, com `python -m vector_builder` (ver [backend/vector_builder/README.md](backend/vector_builder/README.md)). O resultado fica em `vector_store/`, fora do Git.

Preparar e construir (com o `.venv` ativo):

```powershell
# Embeddings pelo Ollama (sem PyTorch)
ollama pull bge-m3
pip install -r backend/vector_builder/requirements.txt

# ou pelo sentence-transformers (PyTorch, ~2 GB)
pip install -r backend/vector_builder/requirements-local.txt

cd backend
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro" --dry-run    # revisa os trechos
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro" --provider ollama
python -m vector_builder list
```

O provedor padrão vem de `EMBEDDING_PROVIDER` no `backend/.env` (`ollama` ou `sentence-transformers`). Os embeddings não usam a LLM do chat: são um modelo próprio (`bge-m3`), mesmo quando rodam no mesmo Ollama.

Na tela, o botão **Subir PDF** valida o livro do usuário: o arquivo é comparado com o catálogo de livros permitidos (frases em páginas definidas, número de páginas, tamanho, metadados e formato da página). Se for reconhecido, o banco daquele livro é liberado **para aquele usuário**. O PDF é lido em memória e descartado; fica registrado só o resultado (tabela `book_validation_log`).

## 5. Rotas da API

Acesso: 🌐 público · 🔑 usuário logado · 🛡️ administrador.

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/health` | 🌐 | status da API |
| GET | `/api/auth/config` | 🌐 | Client ID do Google |
| POST | `/api/auth/google` | 🌐 | login com o ID token do Google (`remember` opcional); cria a conta no primeiro acesso |
| POST | `/api/auth/logout` | 🌐 | encerra a sessão atual |
| GET / PATCH / DELETE | `/api/auth/me` | 🔑 | dados do usuário / altera o nome / exclui a conta |
| POST | `/api/auth/logout-all` | 🔑 | encerra as outras sessões |
| GET | `/api/admin/users` | 🛡️ | lista usuários |
| PATCH / DELETE | `/api/admin/users/{email}` | 🛡️ | altera papel ou status / exclui |
| GET | `/api/llm/providers` | 🔑 | provedores suportados |
| GET | `/api/llm/connections/active` | 🔑 | conexão ativa (sem API key) |
| GET / POST | `/api/llm/connections` | 🛡️ | lista / cria conexão |
| GET / PUT / DELETE | `/api/llm/connections/{id}` | 🛡️ | detalhe / atualiza / remove |
| POST | `/api/llm/connections/{id}/activate` | 🛡️ | torna a conexão ativa |
| POST | `/api/llm/connections/{id}/test` | 🛡️ | envia uma mensagem de teste |
| GET / POST / DELETE | `/api/sessions` | 🔑 | lista / cria / apaga todas as suas conversas |
| GET / PATCH / DELETE | `/api/sessions/{id}` | 🔑 | conversa com mensagens / renomeia / apaga |
| GET | `/api/sessions/{id}/messages` | 🔑 | mensagens da conversa |
| POST | `/api/rag/query` | 🔑 | **pergunta → LLM → resposta** (`{prompt, chaosLevel, sessionId?, connectionId?}`) |
| GET | `/api/rag/books` | 🔑 | livros do catálogo e quais o usuário já liberou |
| POST | `/api/rag/upload` | 🔑 | valida o PDF de um livro e libera o banco vetorial dele (multipart, campo `file`) |
| POST | `/api/perguntas` | 🔑 | contrato legado do protótipo estático |

Erros voltam como `{"detail": "..."}`:

| Código | Quando |
|---|---|
| `401` | sem sessão ou sessão expirada |
| `403` | sem permissão, origem bloqueada, conta desativada ou cadastro de novas contas desativado |
| `404` | recurso inexistente ou de outro usuário |
| `409` | nenhuma LLM ativa |
| `400` | PDF inválido, protegido por senha, acima do limite ou catálogo vazio |
| `429` | muitas tentativas (cabeçalho `Retry-After`) |
| `502` | falha no provedor de LLM |

## 6. Estrutura do backend

```text
backend/
├── main.py               ponto de entrada (python main.py)
├── app/
│   ├── main.py           FastAPI, middlewares, handlers de erro, routers
│   ├── core/             config (.env), exceções, segurança (tokens),
│   │                     criptografia, rate limit, middleware HTTP, dependências de auth
│   ├── db/               SQLite (schema + migração)
│   ├── schemas/          contratos Pydantic (JSON em camelCase)
│   ├── repositories/     acesso a dados (consultas parametrizadas)
│   ├── services/         cliente multi-provedor de LLM, prompt do Nimb, validação Google,
│   │                     impressão digital de PDF, catálogo e validação de livros
│   ├── controllers/      regras de negócio (auth, usuários, LLM, conversas, consulta, livros)
│   └── routers/          rotas HTTP
└── vector_builder/       construtor do banco vetorial e do catálogo (roda à parte)
```

O ponto de extensão para o RAG está em `app/controllers/query_controller.py`: os trechos recuperados do banco vetorial entram no prompt antes da chamada à LLM.
