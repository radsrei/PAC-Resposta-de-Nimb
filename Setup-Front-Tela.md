# Subindo o sistema localmente (Front V2 + Backend + LLM + Login)

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
- O banco local (SQLite) é criado sozinho em `backend/data/nimb.db`, junto com a chave de criptografia `backend/data/secret.key`. A pasta `data/` fica fora do Git. Se a `secret.key` for apagada, as API keys das LLMs precisam ser cadastradas de novo.
- No Windows, se o `pip install` falhar com um erro de caminho longo (`No such file or directory ... anthropic\types\beta\...`), crie o venv num caminho mais curto ou ative o suporte a caminhos longos do Windows.
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

**Primeiro acesso:** clique em **Criar conta**. A primeira conta criada vira **administradora** (`FIRST_USER_IS_ADMIN`). Também é possível definir administradores fixos em `ADMIN_EMAILS`.

| Funcionalidade | Onde fica |
|---|---|
| Criar conta (o e-mail é a chave primária, sem diferenciar maiúsculas) | tela de login → **Criar conta** |
| Entrar com e-mail e senha, com opção "Manter conectado" (7 dias) | tela de login |
| Entrar com Google | tela de login (ver seção 3.1) |
| Esqueci a senha → código de recuperação → senha padrão | tela de login → **Esqueci minha senha** |
| Troca obrigatória após reset | automática no login seguinte |
| Editar nome, trocar senha, encerrar outras sessões, excluir conta | botão com seu nome no topo → **Minha conta** |
| Listar usuários, promover a admin, desativar, resetar senha, excluir | **Minha conta** → painel *Usuários do sistema* (só admins) |

**Recuperação de senha (senha básica e fixa):**

1. Em **Esqueci minha senha**, informe o e-mail. A resposta é sempre a mesma, exista a conta ou não, para não revelar quem está cadastrado.
2. O código de recuperação (uso único, válido por 30 minutos) é **impresso no terminal do backend**, porque ainda não há servidor de e-mail. Procure o bloco `RECUPERAÇÃO DE SENHA`.
3. Em **Usar código de recuperação**, cole o código. A senha passa a ser a senha padrão `DEFAULT_RESET_PASSWORD` (padrão `Nimb@12345`).
4. Entre com a senha padrão. O sistema exige uma nova senha antes de liberar qualquer funcionalidade.

Um administrador também pode resetar a senha de qualquer usuário pelo painel. O efeito é o mesmo: senha padrão com troca obrigatória.

> Por que o reset exige um código: se bastasse informar um e-mail para a senha virar uma senha conhecida, qualquer pessoa poderia invadir qualquer conta. Para enviar o código por e-mail de verdade, implemente o envio em `_deliver_reset_token` (`backend/app/controllers/auth_controller.py`).

**Conexões LLM:** somente administradores cadastram, editam e testam conexões, porque elas guardam API keys e valem para o sistema todo. Usuários comuns veem apenas qual LLM está ativa.

### 3.1 Login com Google

O botão do Google fica desativado até existir um Client ID:

1. Acesse https://console.cloud.google.com → **APIs e serviços** → **Credenciais**.
2. Se for solicitado, configure a **Tela de consentimento OAuth** (tipo *Externo*, com os escopos padrão `email`, `profile` e `openid`).
3. **Criar credenciais** → **ID do cliente OAuth** → tipo **Aplicativo da Web**.
4. Em **Origens JavaScript autorizadas**, adicione `http://localhost:3000`. Não é preciso URI de redirecionamento.
5. Copie o Client ID para `backend/.env`: `GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com`, e reinicie o backend.

O front busca o Client ID em `/api/auth/config`, então ele não é configurado no front. O backend valida o token do Google (assinatura, emissor, expiração e Client ID) e só aceita e-mails verificados. Se já existir uma conta local com o mesmo e-mail, o Google é vinculado a ela. Uma conta criada pelo Google pode definir uma senha em **Minha conta** para também entrar com e-mail e senha.

### 3.2 Proteções de segurança

| Ameaça | Proteção |
|---|---|
| SQL injection | todas as consultas usam parâmetros (`?`); nomes de coluna vêm de listas fixas no código |
| Vazamento de senhas | hash **scrypt** com salt único por usuário; senhas nunca voltam na API nem vão para os logs |
| Vazamento do banco | tokens de sessão e de recuperação guardados só como SHA-256; API keys das LLMs criptografadas (Fernet/AES) |
| Roubo de sessão via XSS | sessão em cookie **HttpOnly** (o JavaScript não consegue ler); nada em `localStorage` |
| CSRF | cookie **SameSite=Strict**, mais bloqueio de requisições que alteram dados vindas de origem fora de `CORS_ORIGINS` |
| Força bruta | conta bloqueada por 15 min após 5 senhas erradas; limite de 20 requisições por minuto por IP nas rotas de login |
| Descobrir e-mails cadastrados | mesma mensagem para e-mail inexistente e senha errada; tempo de resposta igualado; "esqueci a senha" sempre responde igual |
| Acesso a dados de outro usuário (IDOR) | conversas filtradas pelo usuário logado em todas as consultas |
| Escalada de privilégio | rotas de admin exigem papel `admin`; um admin não pode remover o próprio acesso; sempre resta ao menos um admin |
| Sessões antigas | trocar a senha encerra as outras sessões; reset e desativação encerram todas |
| Vazamento em erros | erros internos devolvem só "Erro interno do servidor" (detalhes ficam no log); erros de validação não ecoam o valor enviado |
| Clickjacking, sniffing e cache | cabeçalhos `X-Frame-Options`, `X-Content-Type-Options`, `Cache-Control: no-store` e CSP na API |

**Para produção:** use HTTPS com `COOKIE_SECURE=true`, defina um `APP_SECRET_KEY` longo e aleatório, desative o Swagger com `ENABLE_DOCS=false`, troque `DEFAULT_RESET_PASSWORD` e ajuste `CORS_ORIGINS` para o domínio real. O limite por IP é guardado em memória, então vale por processo da API.

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

## 5. Rotas da API

Acesso: 🌐 público · 🔑 usuário logado · 🛡️ administrador.

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| GET | `/api/health` | 🌐 | status da API |
| GET | `/api/auth/config` | 🌐 | Client ID do Google, cadastro habilitado, regra de senha |
| POST | `/api/auth/register` | 🌐 | cria conta e já entra |
| POST | `/api/auth/login` | 🌐 | login com e-mail e senha (`remember` opcional) |
| POST | `/api/auth/google` | 🌐 | login com o ID token do Google |
| POST | `/api/auth/forgot-password` | 🌐 | gera o código de recuperação |
| POST | `/api/auth/reset-password` | 🌐 | usa o código e aplica a senha padrão |
| POST | `/api/auth/logout` | 🌐 | encerra a sessão atual |
| GET / PATCH / DELETE | `/api/auth/me` | 🔑 | dados do usuário / altera o nome / exclui a conta |
| POST | `/api/auth/change-password` | 🔑 | troca (ou define) a senha |
| POST | `/api/auth/logout-all` | 🔑 | encerra as outras sessões |
| GET | `/api/admin/users` | 🛡️ | lista usuários |
| PATCH / DELETE | `/api/admin/users/{email}` | 🛡️ | altera papel ou status / exclui |
| POST | `/api/admin/users/{email}/reset-password` | 🛡️ | aplica a senha padrão |
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
| POST | `/api/rag/upload` | 🛡️ | stub de upload de livro (etapa de RAG) |
| POST | `/api/perguntas` | 🔑 | contrato legado do protótipo estático |

Erros voltam como `{"detail": "..."}`:

| Código | Quando |
|---|---|
| `401` | sem sessão ou sessão expirada |
| `403` | sem permissão, origem bloqueada ou troca de senha pendente |
| `404` | recurso inexistente ou de outro usuário |
| `409` | e-mail já cadastrado ou nenhuma LLM ativa |
| `429` | muitas tentativas (cabeçalho `Retry-After`) |
| `502` | falha no provedor de LLM |

## 6. Estrutura do backend

```text
backend/
├── main.py               ponto de entrada (python main.py)
└── app/
    ├── main.py           FastAPI, middlewares, handlers de erro, routers
    ├── core/             config (.env), exceções, segurança (hash, tokens),
    │                     criptografia, rate limit, middleware HTTP, dependências de auth
    ├── db/               SQLite (schema + migração)
    ├── schemas/          contratos Pydantic (JSON em camelCase)
    ├── repositories/     acesso a dados (consultas parametrizadas)
    ├── services/         cliente multi-provedor de LLM, prompt do Nimb, validação Google
    ├── controllers/      regras de negócio (auth, usuários, LLM, conversas, consulta)
    └── routers/          rotas HTTP
```

O ponto de extensão para o RAG está em `app/controllers/query_controller.py`: os trechos recuperados do banco vetorial entram no prompt antes da chamada à LLM.
