# Deploy completo na AWS EC2 — Respostas de Nimb online

Guia único para levar o sistema da máquina local até **https://respostas-nimb.com.br**. Compila e atualiza o [execucao_controlada.md](execucao_controlada.md) e o [banco_vetorial_livros.md](banco_vetorial_livros.md) para o estado de 24/10/2026: busca híbrida nos livros, Ollama obrigatório, pergunta só com livro liberado e só sobre o Tormenta20. Revisado em 31/10/2026 para o branch `feat/tabelas_adicionais` (commit `efe22d8`, API 0.4.0): lista de acesso, Medidor de Caos, tabelas do livro e sorteio de tesouro. Comandos validados em 01/11/2026 (commit `1f67aaa`).

Antes de começar, leia os itens **críticos** do [problemas_e_falhas.md](problemas_e_falhas.md):
- C3 (versões) e C4 (administrador) foram resolvidos no código em 25/10/2026.
- Este guia contorna o C1 (perfil do Ollama) e o C2 (branch).
- O C5 (imagens nunca construídas) é verificado no passo 6.

Comandos marcados **(local)** rodam no PowerShell da sua máquina (Windows PowerShell 5.1), na raiz do projeto, com a `nimb.pem` na mesma pasta; **(servidor)**, no SSH da EC2 (Ubuntu). No PowerShell 5.1, `curl` é apelido do `Invoke-WebRequest`: use **`curl.exe`**.

```text
Navegador ──HTTPS──► Cloudflare (DNS, certificado, proteção)
                         │ Tunnel: conexão de saída da EC2, nenhuma porta web aberta
                         ▼
EC2 (Docker Compose) ── cloudflared ──► web (Caddy :80) ──► front compilado
                                              └── /api ──► api (FastAPI)
                                                            ├── SQLite + secret.key (volume nimb_data)
                                                            ├── vector_store/ (catálogo + Chroma + chunks.jsonl)
                                                            ├── ollama (bge-m3: embedding da pergunta)
                                                            └── api.deepseek.com (resposta)
```

## Resumo da sequência

| # | Etapa | Onde | Situação em 24/10/2026 |
|---|---|---|---|
| 0 | Pré-requisitos: código no `main`, banco dos livros, contas | local | ⚠️ `feat/tabelas_adicionais` 37 commits à frente do `main` em 01/11/2026 (C2); o `main` é ancestral, o merge não tem conflito; há arquivos sem commit (tela de dados do tesouro) |
| 1 | Criar a EC2 (t3.medium, 30 GB) e o IP elástico | AWS | a fazer |
| 2 | Preparar o servidor (Docker, swap) | servidor | a fazer |
| 3 | Configurar `backend/.env` e `deploy/.env` | servidor | a fazer |
| 4 | Enviar o `vector_store/` | local → servidor | pronto localmente (construção de 30/10/2026: 2.818 trechos, 65 tabelas, ~30 MB) |
| 5 | Subir os containers e baixar o `bge-m3` | servidor | a fazer |
| 6 | Validar no modo A (túnel SSH, sem domínio) | local | a fazer |
| 7 | Cloudflare Tunnel e domínio | Cloudflare + servidor | ✅ domínio já delegado ao Cloudflare (`dalary`/`pranab.ns.cloudflare.com`) |
| 8 | Google Cloud: origem e publicação | Google | a fazer (D4/D5 decididos em 29/10/2026: uso controlado + lista de acesso) |
| 9 | Fechar portas e teste de aceite online | AWS + navegador | a fazer |
| 10 | Rotina: backup, atualização, livros novos | servidor | a fazer |

---

## Roteiro rápido (só os comandos)

Resumo para quem já leu o guia. Os detalhes e as tabelas de variáveis estão nos passos 0 a 10.

**0. Código no `main`** (local)
Publicar o branch e levar ao `main`, que é o que o servidor clona.
```powershell
git status                                   # tudo o que vai para o servidor precisa estar commitado
git add -A; git commit -m "<mensagem>"; git push
```
No GitHub: **Pull requests → New pull request**, base `main` ← compare `feat/tabelas_adicionais` → **Create** → **Merge**. (O `gh` não está instalado nesta máquina; com ele: `gh pr create --base main --head feat/tabelas_adicionais` e `gh pr merge --merge`.)
Resultado: `git fetch; git log origin/main -1` mostra o commit de merge.

**0b. Banco dos livros** (local, em `backend/`)
Conferir o banco que vai para o servidor.
```powershell
..\.venv\Scripts\python -m vector_builder list
..\.venv\Scripts\python -m vector_builder evaluate
```
Resultado: `t20-basico` pronto, 2.818 trechos; híbrida com r@5 100% e MRR ~0,93.

**1. Máquina** (Console AWS)
Criar a EC2 Ubuntu 24.04, `t3.medium`, 30 GB gp3, key pair `nimb`, security group só com SSH 22 do seu IP; alocar e associar o IP elástico.
No Windows, o `ssh` recusa a chave se outros usuários puderem lê-la ("UNPROTECTED PRIVATE KEY FILE"). Uma vez, na pasta da chave:
```powershell
icacls nimb.pem /inheritance:r; icacls nimb.pem /grant:r "$($env:USERNAME):(R)"
```
Resultado: `ssh -i nimb.pem ubuntu@<IP-ELASTICO>` entra.

**2. Servidor** (servidor)
Instalar Docker, Compose e swap.
```bash
git clone https://github.com/radsrei/PAC-Resposta-de-Nimb.git PAC-Resposta-de-Nimb
cd PAC-Resposta-de-Nimb && bash deploy/server-setup.sh && exit
```
Resultado: depois de entrar de novo, `docker compose version` responde sem `sudo` e `swapon --show` lista o `/swapfile`.

**3. Configuração** (servidor)
Criar os dois `.env` e preencher conforme as tabelas do passo 3 (modo A: `CORS_ORIGINS=http://localhost:8080`, `COOKIE_SECURE=false`, `COMPOSE_PROFILES=rag`).
```bash
cd ~/PAC-Resposta-de-Nimb
cp backend/.env.example backend/.env && cp deploy/.env.example deploy/.env && chmod 600 backend/.env deploy/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"    # APP_SECRET_KEY
nano backend/.env && nano deploy/.env
```
Resultado: `ADMIN_EMAILS`, `GOOGLE_CLIENT_ID`, `APP_SECRET_KEY`, `LLM_DEEPSEEK_API` e `OLLAMA_URL=http://ollama:11434` preenchidos.

**4. Banco dos livros** (local → servidor)
```powershell
scp -i nimb.pem -r vector_store ubuntu@<IP-ELASTICO>:~/PAC-Resposta-de-Nimb/
```
```bash
sudo chown -R 10001:10001 ~/PAC-Resposta-de-Nimb/vector_store
```
Resultado: `vector_store/books/t20-basico` com `chroma-*`, `tables-*.sqlite`, `chunks.jsonl` e `manifest.json`.

**5. Containers** (servidor, em `deploy/`)
```bash
docker compose up -d --build
docker compose exec ollama ollama pull bge-m3
docker compose restart api
docker compose ps
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())"
```
Resultado: `api` healthy, `web` e `ollama` running; health com `"rag_engine": "ativo"`, `"books_ready": 1`, `"llm_connected": true`.

**6. Validação sem domínio** (local)
```powershell
ssh -i nimb.pem -L 8080:localhost:80 ubuntu@<IP-ELASTICO>
```
Cadastrar `http://localhost:8080` no Google Cloud e abrir **`http://localhost:8080`**.
Resultado: os testes do passo 6 passam (login, lista de acesso, pergunta com página, recusa fora do tema, sorteio de tesouro).

**7. Domínio** (Cloudflare + servidor)
Criar o tunnel `nimb-aws` com os hostnames raiz e `www` → `HTTP web:80`; trocar para o modo online.
```bash
nano deploy/.env     # COMPOSE_PROFILES=cloudflare,rag   TUNNEL_TOKEN=eyJ...
nano backend/.env    # CORS_ORIGINS=https://respostas-nimb.com.br   COOKIE_SECURE=true
cd deploy && docker compose up -d
docker compose logs cloudflared | grep -c "Registered tunnel connection"
```
Resultado: `4` e o tunnel **Healthy** no painel.

**8. Google Cloud**
Origem `https://respostas-nimb.com.br`, remover `http://localhost:8080`, domínio autorizado e publicar o app.
Resultado: o botão do Google funciona no domínio.

**9. Fechar e aceitar** (AWS + local)
Security group só com SSH 22.
```powershell
curl.exe -m 5 http://<IP-ELASTICO>
```
Resultado: o `curl` falha e o checklist do passo 9 passa em `https://respostas-nimb.com.br`.

**10. Rotina** (servidor)
```bash
crontab -e     # 0 3 * * * bash $HOME/PAC-Resposta-de-Nimb/deploy/backup.sh
cd ~/PAC-Resposta-de-Nimb && git pull && cd deploy && docker compose up -d --build    # a cada atualização
```
Resultado: um `~/backups/nimb-AAAAMMDD-HHMM.tar.gz` por dia.

---

## 0. Pré-requisitos (local)

### 0.1 Código no branch que o servidor clona
O servidor clona o branch padrão (`main`), mas tudo o que foi feito está em `feat/tabelas_adicionais`, 37 commits à frente do `main` em 01/11/2026 (item C2). O `main` é ancestral do branch, então o merge não tem conflito. O `develop` não traz nada que falte no branch. Escolha um caminho:
- **Recomendado:** abrir um PR `feat/tabelas_adicionais` → `main` no GitHub e fazer o merge (ver o roteiro rápido).
- **Alternativa:** clonar o branch direto no passo 2 (`git clone -b feat/tabelas_adicionais ...`).

O `.gitignore` que tira o `relatorio_pentest.md` do Git já está commitado (o repositório é público). Antes do merge, faça o commit do que estiver pendente: em 01/11/2026, a animação dos dados do tesouro (`src/components/dice/`, `TreasureModal.tsx`) e o `public/sounds/LEIAME.md`. Faça o commit dos dois juntos: o `TreasureModal.tsx` novo importa o `DiceRoller`, e sem o `dice/` no Git o build do front no servidor falha. Os dois itens Altos do relatório estão tratados (31/10/2026): a chave do LangSmith (V-01) foi revogada, e o corpo das requisições (V-02) passou a ser limitado no `deploy/Caddyfile` (128 KB, ou 100 MB só no upload) e na API (`BodyLimitMiddleware`, que também exige sessão antes de receber o PDF). No passo 6, confira o upload do PDF real (teste 4): é ele que valida o limite do Caddy.

```powershell
git status                 # (local) nada pendente
git push                   # o servidor só enxerga o que está no GitHub
```

### 0.2 Banco dos livros pronto e medido
```powershell
cd backend
..\.venv\Scripts\python -m vector_builder list        # t20-basico: banco pronto, 2818 trechos (1.322 de texto + 1.496 linhas de tabela), ollama/bge-m3
..\.venv\Scripts\python -m vector_builder evaluate    # esperado (63 perguntas): híbrida r@5 100%, MRR ~0,93
cd ..
```
Se o livro mudar, reconstrua com `build` (ver [banco_vetorial_livros.md](banco_vetorial_livros.md), seção 7) antes de enviar.

### 0.3 Contas e segredos (guarde tudo no Bitwarden)
| Item | Onde | Observação |
|---|---|---|
| Chave do DeepSeek | `platform.deepseek.com` | conta com saldo (US$ 5,00 em 24/10/2026) |
| Google Client ID | Google Cloud → Credenciais → ID do cliente OAuth (Web) | o mesmo do ambiente local |
| `APP_SECRET_KEY` | gerada no passo 3 | sem ela, a chave do DeepSeek gravada no banco não abre mais |
| Token do Tunnel | Cloudflare Zero Trust (passo 7) | começa com `eyJ` |
| Chave SSH `nimb.pem` | AWS (passo 1) | nunca no Git |
| Alarme de gastos | AWS → Billing → Budgets | ex.: US$ 40/mês com alerta por e-mail |

### 0.4 Versões (item C3, resolvido em 25/10/2026)
O servidor instala exatamente o que foi testado:
- Python **3.14.5** e as dependências do `backend/requirements.txt`, travadas pelo `backend/requirements.lock`;
- imagens `node:24.20.0-alpine`, `caddy:2.11.6-alpine`, `ollama/ollama:0.40.10` e `cloudflare/cloudflared:2026.10.0`.

Localmente, use as mesmas: Python 3.14, Node 24.20, Ollama 0.40.10. O banco dos livros precisa ser construído com o `chromadb==1.5.9`, a mesma versão da API.

---

## 1. Criar a máquina (Console AWS → EC2 → Launch instance)

| Campo | Valor | Por quê |
|---|---|---|
| Região | `us-east-1` (mais barata) ou `sa-east-1` (menor latência no Brasil) | |
| Imagem | Ubuntu Server 24.04 LTS | |
| Tipo | **`t3.medium` (2 vCPU, 4 GB)**, no mínimo | Ollama (bge-m3 ~1,2 GB) + API com Chroma + build do front. O `t3.small` do guia antigo não comporta |
| Key pair | `nimb` (.pem) | |
| Disco | **30 GB gp3** | imagens do Ollama, da API e do Node, mais modelo, swap e backups |
| Security group | **SSH 22 só do seu IP**. Nada mais | o site entra pelo Cloudflare Tunnel, sem portas web |

Depois: **EC2 → Elastic IPs → Allocate → Associate** à instância.

Custo aproximado: um `t3.medium` ligado 24 h custa cerca de US$ 30/mês em `us-east-1`, mais o disco. Confira na calculadora da AWS. Parar a instância quando não estiver em uso reduz o custo.

---

## 2. Preparar o servidor (servidor)

```bash
ssh -i nimb.pem ubuntu@<IP-ELASTICO>
git clone https://github.com/radsrei/PAC-Resposta-de-Nimb.git PAC-Resposta-de-Nimb
# alternativa do passo 0.1:  git clone -b feat/tabelas_adicionais https://github.com/radsrei/PAC-Resposta-de-Nimb.git PAC-Resposta-de-Nimb
cd PAC-Resposta-de-Nimb
bash deploy/server-setup.sh          # Docker + Compose, swap de 2 GB, updates de segurança
exit                                 # saia e entre de novo para usar o docker sem sudo
```

---

## 3. Configurar (servidor), antes de qualquer `docker compose`

O compose exige o `backend/.env` existente, então configure antes de subir qualquer serviço.

```bash
ssh -i nimb.pem ubuntu@<IP-ELASTICO>
cd ~/PAC-Resposta-de-Nimb
cp backend/.env.example backend/.env && chmod 600 backend/.env
cp deploy/.env.example deploy/.env && chmod 600 deploy/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"     # APP_SECRET_KEY: copie e guarde no cofre
nano backend/.env
```

### `backend/.env`
| Variável | Modo A (validação, túnel SSH) | Online (Cloudflare) | Observação |
|---|---|---|---|
| `ENABLE_DOCS` | `false` | `false` | padrão `false` desde 29/10/2026 (M7); `true` só na sua máquina |
| `CORS_ORIGINS` | `http://localhost:8080` | `https://respostas-nimb.com.br` | diferente disso, todo POST é bloqueado |
| `COOKIE_SECURE` | `false` | `true` | `true` sem HTTPS faz o login voltar à tela inicial |
| `APP_SECRET_KEY` | valor gerado | o mesmo | |
| `GOOGLE_CLIENT_ID` | seu Client ID | o mesmo | |
| **`ADMIN_EMAILS`** | **e-mail Google do administrador** | o mesmo | obrigatório: é o único jeito de ter administrador. Fica só no `.env` (repositório público). Vira admin na criação da conta e a cada login |
| `FIRST_USER_IS_ADMIN` | `false` | `false` | já é o padrão desde 25/10/2026 (item C4) |
| `REGISTRATION_ENABLED` | `true` | `true` | quem entra é decidido pela lista de acesso abaixo; `false` só deixa entrar quem já tem conta |
| **`ALLOWLIST_ENABLED`** | `true` | `true` | só entram os e-mails da lista de acesso, que o administrador preenche em **Minha conta → E-mails com acesso**. Os de `ADMIN_EMAILS` entram sempre (A4) |
| `LLM_DEEPSEEK_API` | chave do DeepSeek | a mesma | cria a conexão "DeepSeek (.env)" na 1ª subida |
| `LLM_MODEL` | `deepseek-chat` | `deepseek-chat` | |
| `LLM_TIMEOUT` | `90` | `90` | limite de uma chamada à LLM |
| `ANSWER_TIME_BUDGET` | `85` | `85` | tempo total da pergunta (busca + resposta + revisões e alucinação do Medidor de Caos); cada chamada recebe só o que resta, abaixo dos ~100 s do Cloudflare (erro 524). Substitui o antigo `CHAOS_TIME_BUDGET` |
| `CHAOS_HALLUCINATION_CHANCES`, `CHAOS_HARNESS_ROUNDS`, `CHAOS_TIMEZONE` | padrão do `.env.example` | o mesmo | níveis do Medidor de Caos |
| `EMBEDDING_PROVIDER` | `ollama` | `ollama` | |
| **`OLLAMA_URL`** | **`http://ollama:11434`** | **`http://ollama:11434`** | nome do container, não `localhost` |
| `OLLAMA_KEEP_ALIVE` | `-1` | `-1` | modelo sempre carregado |
| `RAG_MIN_SIMILARITY`, `RAG_HYBRID`, `RAG_LEXICAL_WEIGHT`, `RAG_CANDIDATES`, `RAG_TOP_K` | padrão do `.env.example` | o mesmo | calibrados com `evaluate` (0,45 / true / 0,5 / 20 / 5) |
| `BOOK_UPLOAD_MAX_MB` | `95` | `95` | limite do Cloudflare grátis |

O `DATABASE_PATH` e o `VECTOR_STORE_DIR` são definidos pelo `docker-compose.yml`; não precisam estar no `.env`.

### `deploy/.env`
| Variável | Modo A | Online (Cloudflare) |
|---|---|---|
| `SITE_ADDRESS` | `:80` | `:80` (o HTTPS fica no Cloudflare; com o domínio aqui, o site entra em loop de redirecionamento) |
| **`COMPOSE_PROFILES`** | **`rag`** | **`cloudflare,rag`** |
| `TUNNEL_TOKEN` | vazio | token do passo 7 |

O perfil `rag` sobe o Ollama, e **sem ele toda pergunta responde 503** (item C1). Nunca use `COMPOSE_PROFILES=cloudflare` sozinho, como dizia o guia antigo.

---

## 4. Enviar os bancos dos livros

```powershell
# (local, na raiz do projeto)
scp -i nimb.pem -r vector_store ubuntu@<IP-ELASTICO>:~/PAC-Resposta-de-Nimb/
```
```bash
# (servidor) o Chroma precisa gravar na pasta: ela passa a ser do usuário da API no container (uid 10001)
sudo chown -R 10001:10001 ~/PAC-Resposta-de-Nimb/vector_store
ls ~/PAC-Resposta-de-Nimb/vector_store/books/t20-basico      # chroma-<data>/  chunks.jsonl  manifest.json  tables-<data>.sqlite
```
O `chunks.jsonl` é obrigatório: é o índice da busca por palavras. O `tables-<data>.sqlite` também: a API monta a partir dele o espaço do sorteio de tesouro (`/app/data/tesouro`, no volume `nimb_data`), na subida ou no primeiro sorteio. A pasta `preview/` pode ir junto ou ser apagada.

---

## 5. Subir os containers e o modelo (servidor)

```bash
cd ~/PAC-Resposta-de-Nimb/deploy
docker compose up -d --build                       # 1ª vez: 5–15 min (compila o front e instala o chromadb)
docker compose exec ollama ollama pull bge-m3      # 1,2 GB, só na primeira vez (fica no volume ollama_models)
docker compose restart api                         # refaz o aquecimento da busca já com o modelo baixado
docker compose ps                                  # api: healthy | web: running | ollama: running
docker compose logs api | grep -E "Busca nos livros pronta|Aquecimento"   # esperado: "Busca nos livros pronta (x s)"
```
Conferência rápida:
```bash
docker compose exec api python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').read().decode())"
# esperado: "rag_engine": "ativo", "books_ready": 1, "llm_connected": true
docker compose exec ollama ollama ps               # bge-m3 carregado, UNTIL "Forever"
free -h                                            # memória: sobra > 500 MB
```

---

## 6. Validar no modo A (túnel SSH, sem domínio)

```powershell
# (local) deixe aberto enquanto testa
ssh -i nimb.pem -L 8080:localhost:80 ubuntu@<IP-ELASTICO>
```
No Google Cloud, adicione temporariamente a origem `http://localhost:8080` (passo 8). Abra **http://localhost:8080**.

| # | Teste | Esperado |
|---|---|---|
| 1 | Entrar com o Google (e-mail de `ADMIN_EMAILS`) | entra como administrador |
| 1b | Outra conta Google, fora da lista | recusada: "Seu e-mail ainda não tem acesso…". Incluí-la em **Minha conta → E-mails com acesso** e entrar de novo: entra como usuário |
| 2 | **Conectar LLM** → "DeepSeek (.env)" → **Testar** | ativa e respondendo |
| 3 | Sem livro: campo de pergunta | travado, com o aviso "Adicione o livro…" e o botão **Subir PDF** |
| 4 | **Subir PDF** do Tormenta20 (89 MB) | "Livro reconhecido… Acesso liberado." |
| 5 | "Quanto de dano causa a Bola de Fogo?" | 6d6, fonte Tormenta20, p. 182 |
| 6 | "Quanto dinheiro inicial um personagem de 5º nível recebe?" | T$ 2.000, p. 140 |
| 7 | "Qual é a capital da França?" | mensagem "Nimb só responde sobre o sistema Tormenta20…" |
| 7b | **Sorteio de tesouro** por criatura (Necromante) e por ND (7) | rolagens, recompensas e total em T$; o sorteio aparece no histórico |
| 8 | Tempo da 1ª e da 2ª pergunta | anote: no servidor o embedding roda em CPU (localmente era GPU) |
| 9 | `docker compose restart` e entrar de novo | usuário, conversa, livro liberado e LLM continuam |

Se o build do passo 5 ou algum teste falhar, veja a tabela de problemas no fim e o [problemas_e_falhas.md](problemas_e_falhas.md).

---

## 7. Cloudflare Tunnel e domínio

O domínio já está delegado ao Cloudflare. Falta:

1. **Ajustes no painel** (`dash.cloudflare.com` → `respostas-nimb.com.br`):
   - SSL/TLS → Edge Certificates: **Always Use HTTPS** ligado, **Minimum TLS 1.2**.
   - Speed → Optimization: **Rocket Loader desligado** (quebra apps React).
   - Security → Bots: **Bot Fight Mode desligado** até testar o login e o upload.
   - Rules → Redirect Rules: modelo **Redirect from WWW to root**.
2. **Criar o Tunnel:** Zero Trust → Networks → Tunnels → **Create a tunnel** → Cloudflared → `nimb-aws`. Copie **só o token** (`eyJ...`) para o Bitwarden.
3. **Public hostnames** do tunnel:

   | Subdomain | Domain | Type | URL |
   |---|---|---|---|
   | *(vazio)* | `respostas-nimb.com.br` | HTTP | `web:80` |
   | `www` | `respostas-nimb.com.br` | HTTP | `web:80` |
4. **Servidor:**
   ```bash
   cd ~/PAC-Resposta-de-Nimb
   nano deploy/.env        # COMPOSE_PROFILES=cloudflare,rag   TUNNEL_TOKEN=eyJ...
   nano backend/.env       # CORS_ORIGINS=https://respostas-nimb.com.br   COOKIE_SECURE=true
   cd deploy && docker compose up -d
   docker compose logs cloudflared | grep -c "Registered tunnel connection"     # esperado: 4
   ```
   No painel, o tunnel `nimb-aws` deve aparecer como **Healthy**.

---

## 8. Google Cloud (Credenciais → ID do cliente OAuth)

- **Origens JavaScript autorizadas:** `https://respostas-nimb.com.br`. Remova o `http://localhost:8080` depois da validação.
- **Tela de consentimento → Domínios autorizados:** `respostas-nimb.com.br`. Se pedir verificação, adicione o TXT do Search Console no DNS do Cloudflare.
- **Publicar app:** tira do modo *Teste*. Pode ser feito: quem entra no sistema é controlado pela lista de acesso (`ALLOWLIST_ENABLED=true`), e não pelo Google. Decisão de 29/10/2026: uso em ambiente controlado, por poucos usuários. Alternativa: manter em *Teste* com os mesmos e-mails como usuários de teste (limite de 100).

---

## 9. Fechar portas e teste de aceite online

**EC2 → Security groups**: só SSH 22 do seu IP; sem 80 nem 443.
```bash
curl.exe -m 5 http://<IP-ELASTICO>    # (local, PowerShell) deve falhar: o site só existe pelo Cloudflare
```

### Checklist em https://respostas-nimb.com.br
- [ ] Cadeado válido; `www.` redireciona para o domínio raiz
- [ ] Login com Google (conta fora da lista de teste só depois de publicar o app)
- [ ] Administrador é o e-mail de `ADMIN_EMAILS`; uma segunda conta entra como usuário comum
- [ ] Conta sem livro não consegue perguntar
- [ ] Upload do livro (até 95 MB) aceito; um PDF qualquer é recusado
- [ ] Pergunta do livro volta com resposta, livro e página impressa
- [ ] Pergunta fora do tema é recusada
- [ ] Reiniciar (`docker compose restart`) não perde nada
- [ ] Dois usuários logados ao mesmo tempo sem bater no limite de requisições
- [ ] IP real gravado (seu IP público, não `172.x`):
  ```bash
  docker compose exec api python -c "import sqlite3; print(sqlite3.connect('/app/data/nimb.db').execute('select user_email, ip from auth_sessions order by created_at desc limit 3').fetchall())"
  ```

---

## 10. Rotina de operação (servidor)

```bash
# Atualizar o sistema
cd ~/PAC-Resposta-de-Nimb && git pull && cd deploy && docker compose up -d --build

# Backup diário do banco + secret.key (agendar uma vez)
crontab -e      # 0 3 * * * bash $HOME/PAC-Resposta-de-Nimb/deploy/backup.sh
```

**Livro novo ou banco reconstruído:** o `scp` não sobrescreve uma pasta que pertence ao uid 10001 e não apaga as versões antigas `chroma-*`. Faça a troca inteira:
```bash
sudo rm -rf ~/PAC-Resposta-de-Nimb/vector_store                                   # (servidor)
```
```powershell
scp -i nimb.pem -r vector_store ubuntu@<IP-ELASTICO>:~/PAC-Resposta-de-Nimb/     # (local)
```
```bash
sudo chown -R 10001:10001 ~/PAC-Resposta-de-Nimb/vector_store && cd ~/PAC-Resposta-de-Nimb/deploy && docker compose restart api   # (servidor)
```

- **Snapshot do disco:** EC2 → Lifecycle Manager → política diária do volume.
- **Backup do `vector_store`:** o `backup.sh` não o inclui. A cópia de referência fica na sua máquina, e ele pode ser refeito a partir do PDF com o `build`.
- **Economia:** pare a instância quando não estiver em uso. O IP elástico parado tem custo pequeno.

---

## Problemas rápidos

| Sintoma | Causa / solução |
|---|---|
| Toda pergunta responde **503** "Ollama indisponível" | `COMPOSE_PROFILES` sem `rag`, `OLLAMA_URL` diferente de `http://ollama:11434`, ou o modelo não foi baixado (`docker compose exec ollama ollama pull bge-m3`) |
| 503 "Modelo 'bge-m3' não encontrado" | volume `ollama_models` novo: baixe o modelo de novo |
| 1ª pergunta lenta depois de reiniciar | aquecimento rodou antes do Ollama: `docker compose restart api` |
| "Adicione um livro antes de perguntar" (428) | o usuário não liberou o livro, ou o `vector_store` não está no servidor ou sem permissão (`chown 10001`) |
| "Nimb só responde sobre o sistema Tormenta20…" (422) | pergunta fora do livro; esperado |
| 503 "Não foi possível consultar o banco do livro" | `vector_store` sem permissão de escrita para o uid 10001 (o Chroma não abre somente leitura) |
| "Origem da requisição não permitida" | `CORS_ORIGINS` diferente do endereço no navegador, ou acesso pelo `www` sem o redirecionamento |
| Login entra e volta para a tela de login | `COOKIE_SECURE=true` no modo A (HTTP) |
| Botão do Google com erro de origem | origem não cadastrada no Google Cloud |
| "Conta do DeepSeek sem saldo" (502) | recarregar créditos |
| Upload: "Arquivo maior que o limite de 95 MB" / 413 | limite do Cloudflare grátis: comprimir o PDF |
| 413 / "Requisição grande demais" fora do upload | corpo acima de 128 KB (limite do V-02 no Caddy e na API); nenhuma tela legítima chega perto disso |
| Upload responde 401 logado | a sessão expirou: o upload exige sessão válida antes de receber o arquivo; entre de novo |
| Erro **1033** | `cloudflared` parado ou token errado: `docker compose logs cloudflared` |
| **502 Bad Gateway** no domínio | hostname do tunnel diferente de `web:80`, ou `web` fora do ar |
| **ERR_TOO_MANY_REDIRECTS** | `SITE_ADDRESS` com o domínio em vez de `:80` |
| **524** | resposta passou de ~100 s: manter `ANSWER_TIME_BUDGET=85`, `LLM_TIMEOUT=90` e `deepseek-chat` |
| `ssh`: "UNPROTECTED PRIVATE KEY FILE" | permissões da `nimb.pem` no Windows: `icacls` do passo 1 |
| `curl -m 5` dá erro de parâmetro no PowerShell | use `curl.exe` (no 5.1, `curl` é o `Invoke-WebRequest`) |
| Build da API falha no `pip install` | conflito com o `requirements.lock`: confira se o `requirements.txt` e o lock são do mesmo commit; para mudar uma versão, gere o lock de novo (C3) |
| Ninguém é administrador | `ADMIN_EMAILS` vazio ou diferente do e-mail da conta Google; corrija o `.env`, `docker compose restart api` e entre de novo |
| Sem memória no build ou no upload | instância menor que `t3.medium`, ou swap não criado (`swapon --show`) |
| Logs | `docker compose logs -f api` · `web` · `ollama` · `cloudflared` |

Arquivos do deploy: [deploy/docker-compose.yml](../deploy/docker-compose.yml) · [deploy/Caddyfile](../deploy/Caddyfile) · [backend/Dockerfile](../backend/Dockerfile) · [deploy/web.Dockerfile](../deploy/web.Dockerfile) · [deploy/server-setup.sh](../deploy/server-setup.sh) · [deploy/backup.sh](../deploy/backup.sh)
