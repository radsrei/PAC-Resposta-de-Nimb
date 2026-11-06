# Respostas de Nimb

Assistente de regras de **Tormenta20** baseado em RAG (*Retrieval-Augmented Generation*). O jogador faz uma pergunta em linguagem natural e o Nimb responde com base nos livros oficiais, citando **livro e página** de onde veio a informação.

Projeto de portfólio do curso de Engenharia de Software — Católica SC. Proposta completa, requisitos e fluxos em [RFC-PAC-Respostas_De_Nimb.md](RFC-PAC-Respostas_De_Nimb.md).

![Nimb](docs/Icon%20-%20Nimb.png)

## Funcionalidades

- **Login com Google**, com lista de e-mails autorizados e papel de administrador.
- **Chat com histórico** de conversas ("Perguntas Anteriores").
- **Validação do livro por PDF:** o usuário prova que tem o livro enviando o PDF; o arquivo é comparado com a impressão digital do catálogo, lido em memória e descartado. Só livros validados entram na busca.
- **Busca híbrida nos livros:** embeddings `bge-m3` (ChromaDB) + palavras-chave (BM25), combinados por RRF.
- **Respostas pelo DeepSeek**, com as fontes (livro, página, trecho).
- **Medidor de Caos:** Nimb é o deus do caos; conforme o nível (Baixo, Médio, Alto, Louco), a resposta pode "alucinar" de propósito, sendo feito sistema de Harness para melhor acertividade.
- **Tabelas do livro em SQLite** e **sorteio de tesouro** por ND e criatura.
- **Rolador de dados** e tela de agradecimentos.

## Arquitetura

```text
                       ┌─────────────── servidor (Docker) ───────────────┐
Navegador ──HTTPS──► Cloudflare Tunnel ──► Caddy ──┬── /      → front (React compilado)
   (local: Vite :3000, proxy /api)                 └── /api/* → FastAPI :8000
                                                                 │
                                   ┌─────────────┬───────────────┼───────────────┐
                                   ▼             ▼               ▼               ▼
                              SQLite         ChromaDB         Ollama         DeepSeek API
                         (usuários, chat,  (vector_store/,  (embedding da    (LLM que
                          tabelas, tesouro) um banco/livro)   pergunta)       responde)

PDF original ──► backend/vector_builder (roda à parte) ──► vector_store/catalog.json + books/<id>/
```

## Tecnologias

| Camada | Tecnologia | Versão |
|---|---|---|
| Front | React · TypeScript · Vite | 19.3 · 7.0 · 8.3 |
| Front | Tailwind CSS · Motion · Lucide | 4.3 · 12 · 0.546 |
| API | Python · FastAPI · Uvicorn · Pydantic | 3.14 · 0.143 · 0.54 · 2.14 |
| API | httpx · google-auth · cryptography · pypdf | 0.28 · 2.62 · 50.0 · 6.21 |
| Banco | SQLite (dados da aplicação) · ChromaDB (vetores) | — · 1.5.9 |
| Construtor do banco vetorial | PyMuPDF · pypdf · ChromaDB | 2.0 · 6.21 · 1.5.9 |
| Embeddings | `bge-m3` via Ollama (padrão) ou sentence-transformers | Ollama 0.40.10 |
| LLM | DeepSeek (`deepseek-chat` ou `deepseek-reasoner`) | API externa |
| Infra | Docker Compose · Caddy · Cloudflare Tunnel · AWS EC2 | Caddy 2.11 |

Versões exatas: [backend/requirements.txt](backend/requirements.txt) (diretas), [backend/requirements.lock](backend/requirements.lock) (indiretas, usado no Docker) e [package.json](frontend/V2%20-%20front%20Studio/package.json).

## Estrutura do repositório

```text
.
├── backend/
│   ├── app/                    API FastAPI
│   │   ├── main.py             criação da aplicação (ponto de entrada: app.main:app)
│   │   ├── core/               configuração (.env), segurança, middleware, rate limit
│   │   ├── db/                 SQLite
│   │   ├── routers/            rotas HTTP (/api/...)
│   │   ├── controllers/        regras de negócio
│   │   ├── services/           busca (retrieval, lexical), embeddings, LLM, caos, tesouro
│   │   ├── repositories/       acesso a dados
│   │   └── schemas/            contratos Pydantic
│   ├── vector_builder/         construtor do banco vetorial dos livros (CLI)
│   ├── requirements.txt / requirements.lock
│   ├── Dockerfile
│   └── .env.example
├── frontend/V2 - front Studio/ tela (React + Vite + Tailwind)
├── deploy/                     docker-compose, Caddyfile, setup do servidor e backup
├── scripts/                    setup.ps1 (Windows) e setup.sh (Linux/macOS)
├── manuais To Do/              guias de execução, deploy, banco vetorial e problemas conhecidos
├── docs/                       protótipos, Figma, pesquisa do Reddit, imagens
├── RFC_arquivos/               diagramas de fluxo do RFC
└── RFC-PAC-Respostas_De_Nimb.md
```

Pastas geradas e fora do Git: `.venv/`, `backend/data/` (SQLite e `secret.key`), `vector_store/` (catálogo e bancos dos livros), `node_modules/`.

## Requisitos

| Ferramenta | Versão | Para quê | Instalação (Windows) |
|---|---|---|---|
| Python | 3.14 (mínimo 3.12) | API e construtor do banco vetorial | `winget install -e --id Python.Python.3.14` |
| Node.js | 24 (`>=24.20 <25`) | tela (React/Vite) | `winget install -e --id OpenJS.NodeJS.LTS` |
| Ollama | 0.40.10 | embeddings `bge-m3` (construção e pergunta) | `winget install -e --id Ollama.Ollama` |
| Conta DeepSeek | — | API key da LLM | [platform.deepseek.com](https://platform.deepseek.com) |
| Google Cloud | — | Client ID do login com Google | [Setup-Front-Tela.md, seção 3.1](manuais%20To%20Do/Setup-Front-Tela.md) |
| Docker | — | só para o deploy | — |

> **Ollama local × servidor:** na sua máquina, o `sentence-transformers` (PyTorch, ~2 GB) pode substituir o Ollama, porque construtor e API usam o mesmo `.venv`. No servidor o Ollama é obrigatório: a imagem da API não inclui o PyTorch.

## Instalação

### Setup automático (recomendado)

Na raiz do projeto. Cria o `.venv`, instala backend, construtor e front, baixa o modelo no Ollama e cria o `backend/.env`. Pode ser executado de novo: só instala o que falta.

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1                     # Ollama (padrão)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -InstalarOllama     # instala o Ollama pelo winget
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings local   # sentence-transformers
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings nenhum  # só API e front
```

```bash
# Linux / macOS
bash scripts/setup.sh
bash scripts/setup.sh --embeddings local
```

Depois, preencha em `backend/.env`: `GOOGLE_CLIENT_ID`, `LLM_DEEPSEEK_API` e `ADMIN_EMAILS`.

### Setup manual

```bash
python -m venv .venv                                        # na raiz
.venv\Scripts\activate                                      # Linux/macOS: source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt                     # API
pip install -r backend/vector_builder/requirements.txt      # construtor (Ollama)
# ou: pip install -r backend/vector_builder/requirements-local.txt   (sentence-transformers)

ollama pull bge-m3

cd "frontend/V2 - front Studio" && npm ci
```

Copie `backend/.env.example` para `backend/.env` e preencha as chaves.

## Executando localmente

Terminal 1 — API (porta 8000):

```bash
.venv\Scripts\activate
cd backend
uvicorn app.main:app --reload --port 8000
```

Terminal 2 — tela (porta 3000):

```bash
cd "frontend/V2 - front Studio"
npm run dev
```

Acesse **http://localhost:3000**. O Vite encaminha `/api/*` para `http://localhost:8000`. O Swagger fica em `http://localhost:8000/docs` só com `ENABLE_DOCS=true` no `.env`.

O SQLite (`backend/data/nimb.db`) e a chave de criptografia (`backend/data/secret.key`) são criados na primeira subida. Se a `secret.key` for apagada, a API key do DeepSeek precisa ser cadastrada de novo.

## Banco vetorial dos livros

Cada livro é processado **uma vez, à parte da API**, a partir do PDF original. Dentro de `backend/`, com o `.venv` ativo:

```bash
# revisar a extração dos trechos (rápido, não gera embeddings)
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --title "Tormenta20 - Livro Básico" --dry-run

# cadastrar no catálogo e construir o banco
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --title "Tormenta20 - Livro Básico"

python -m vector_builder list                     # catálogo e estado dos bancos
python -m vector_builder check "C:\copia.pdf"     # testar se um PDF seria aceito
python -m vector_builder evaluate --id t20-basico # medir a busca e calibrar RAG_MIN_SIMILARITY
```

Guia completo (provedores, opções, validação do PDF, formato do banco): [backend/vector_builder/README.md](backend/vector_builder/README.md).

## Configuração (`backend/.env`)

Lista completa e comentada em [backend/.env.example](backend/.env.example). As principais:

| Variável | Para quê |
|---|---|
| `GOOGLE_CLIENT_ID` | **obrigatória** — login com Google (único método de acesso) |
| `LLM_DEEPSEEK_API` | API key do DeepSeek; cria a conexão na primeira subida (também dá para cadastrar pela tela) |
| `ADMIN_EMAILS` | e-mails administradores (obrigatório no servidor) |
| `ALLOWLIST_ENABLED` | `true`: só entram os e-mails liberados em *Minha conta → E-mails com acesso* |
| `APP_SECRET_KEY` | criptografia das API keys no banco; use um valor longo em produção |
| `COOKIE_SECURE` / `ENABLE_DOCS` | `true` / `false` em produção |
| `EMBEDDING_PROVIDER` / `EMBEDDING_MODEL` / `OLLAMA_URL` | quem gera os embeddings e onde está o Ollama |
| `RAG_TOP_K` / `RAG_MIN_SIMILARITY` / `RAG_HYBRID` | ajuste da busca nos livros |
| `CHAOS_HALLUCINATION_CHANCES` / `CHAOS_HARNESS_ROUNDS` | comportamento do Medidor de Caos |
| `LLM_TIMEOUT` / `ANSWER_TIME_BUDGET` | limites de tempo (abaixo dos ~100 s do Cloudflare) |

A tela não exige variáveis; opções em [frontend/V2 - front Studio/.env.example](frontend/V2%20-%20front%20Studio/.env.example) (ex.: `VITE_USE_MOCK=true` para revisar a tela sem backend).

## Principais rotas da API

| Prefixo | Uso |
|---|---|
| `GET /api/health` | verificação de saúde (usada pelo Docker) |
| `/api/auth` | login Google, sessão, minha conta |
| `/api/admin/users`, `/api/admin/allowed-emails` | usuários e lista de acesso (admin) |
| `/api/llm` | conexões com a LLM (admin) |
| `/api/sessions` | conversas e mensagens |
| `/api/rag` | `query` (pergunta), `upload` (validar PDF), `books`, `roll` (caos) |
| `/api/tesouro` | sorteio de tesouro, criaturas, NDs, histórico |

Detalhes de cada rota e das regras de segurança: [Setup-Front-Tela.md](manuais%20To%20Do/Setup-Front-Tela.md).

## Deploy

Produção em AWS EC2 com Docker Compose (API + Caddy servindo o front), Cloudflare Tunnel para o domínio e Ollama no perfil `rag`.

```bash
bash deploy/server-setup.sh          # uma vez, no servidor novo (Docker, swap, updates)
cd deploy && docker compose up -d --build
bash deploy/backup.sh                # backup do SQLite e da secret.key
```

Passo a passo completo: [manuais To Do/deploy_ec2_compilado.md](manuais%20To%20Do/deploy_ec2_compilado.md).

## Documentação

| Documento | Conteúdo |
|---|---|
| [RFC-PAC-Respostas_De_Nimb.md](RFC-PAC-Respostas_De_Nimb.md) | problema, requisitos, arquitetura e fluxos |
| [manuais To Do/Setup-Front-Tela.md](manuais%20To%20Do/Setup-Front-Tela.md) | subir o sistema localmente, login Google, rotas |
| [manuais To Do/execucao_controlada.md](manuais%20To%20Do/execucao_controlada.md) | sequência de subida do zero |
| [manuais To Do/banco_vetorial_livros.md](manuais%20To%20Do/banco_vetorial_livros.md) | como o banco vetorial foi construído e o que revisar |
| [manuais To Do/tabelas_e_tesouro.md](manuais%20To%20Do/tabelas_e_tesouro.md) | tabelas do livro em SQL e sorteio de tesouro |
| [manuais To Do/deploy_ec2_compilado.md](manuais%20To%20Do/deploy_ec2_compilado.md) | deploy na AWS EC2 com Cloudflare |
| [manuais To Do/problemas_e_falhas.md](manuais%20To%20Do/problemas_e_falhas.md) | problemas conhecidos e correções sugeridas |
| [backend/vector_builder/README.md](backend/vector_builder/README.md) | construtor do banco vetorial |
| [Git Diagram](https://gitdiagram.com/radsrei/pac-resposta-de-nimb) | diagrama gerado a partir do repositório |

[![Architecture diagram of radsrei/pac-resposta-de-nimb](https://gitdiagram.com/radsrei/pac-resposta-de-nimb/diagram.png)](https://gitdiagram.com/radsrei/pac-resposta-de-nimb?utm_source=readme&utm_medium=picture)

## Fluxo de Git

<details>
<summary>Comentário Off-Topic</summary>
Usado como cola durante periodo de desenvolvimento<br>
</details>


Branches de trabalho saem do `develop` e voltam por Pull Request. Prefixos: `feat/`, `fix/`, `docs/`.

```bash
git checkout develop
git pull origin develop
git switch -c feat/minha-funcionalidade        # cria a branch a partir do develop
git push -u origin feat/minha-funcionalidade   # publica e abre o PR para develop
```

Limpeza depois do merge:

```bash
git fetch -p                                   # remove referências de branches apagadas no remoto
git branch -D nome-da-branch                   # apaga uma branch local

# apaga todas as branches locais cujo remoto já foi removido (Git Bash / Linux / macOS)
git branch -vv | grep ': gone]' | awk '{print $1}' | xargs git branch -D
```

## Segredos (opcional: Bitwarden)

<details>
<summary>Comentário Off-Topic</summary>
Desenvolvida parcialmente a funcionalidade, mas não está em produção.<br>
</details>

As chaves do `backend/.env` (DeepSeek, Google, `APP_SECRET_KEY`) nunca vão para o Git. Para guardá-las no cofre do Bitwarden:

```bash
winget install -e --id Bitwarden.CLI
winget install jq

bw login                                # e-mail, senha mestra e código 2FA
export BW_SESSION="$(bw unlock --raw)"
bw sync
bw status | jq -r .status               # esperado: unlocked
```

## Limitações conhecidas

- Não há testes automatizados nem CI (`backend/tests/` e `.github/workflows/` não existem).
- Busca validada com o *Tormenta20 — Livro Básico*; outros livros precisam de perfil tipográfico próprio (`backend/vector_builder/profiles/`).
- Outros itens em aberto: [problemas_e_falhas.md](manuais%20To%20Do/problemas_e_falhas.md).

## Licença

[GNU AGPL-3.0](LICENSE). Tormenta20 e seus livros pertencem aos respectivos autores e à editora; o repositório não distribui o conteúdo dos livros.

## Autor

Rafael dos Santos Pereira — Engenharia de Software, Católica SC.

<!-- ======================== FIM DO README PROPOSTO ======================== -->
