# Deploy completo na AWS EC2 — Respostas de Nimb online

Guia único para levar o sistema da máquina local até **https://respostas-nimb.com.br**. Compila e atualiza o [deploy_aws.md](deploy_aws.md), o [cloudflare_dominio.md](cloudflare_dominio.md), o [execucao_controlada.md](execucao_controlada.md) e o [banco_vetorial_livros.md](banco_vetorial_livros.md) para o estado de 24/10/2026: busca híbrida nos livros, Ollama obrigatório, pergunta só com livro liberado e só sobre o Tormenta20.

Antes de começar, leia os itens **críticos** do [problemas_e_falhas.md](problemas_e_falhas.md):
- C3 (versões) e C4 (administrador) foram resolvidos no código em 25/10/2026.
- Este guia contorna o C1 (perfil do Ollama) e o C2 (branch).
- O C5 (imagens nunca construídas) é verificado no passo 6.

Comandos marcados **(local)** rodam no PowerShell da sua máquina; **(servidor)**, no SSH da EC2 (Ubuntu).

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
| 0 | Pré-requisitos: código no `main`, banco dos livros, contas | local | ⚠️ código fora do `main` (C2) |
| 1 | Criar a EC2 (t3.medium, 30 GB) e o IP elástico | AWS | a fazer |
| 2 | Preparar o servidor (Docker, swap) | servidor | a fazer |
| 3 | Configurar `backend/.env` e `deploy/.env` | servidor | a fazer |
| 4 | Enviar o `vector_store/` | local → servidor | pronto localmente (1.313 trechos, 22 MB) |
| 5 | Subir os containers e baixar o `bge-m3` | servidor | a fazer |
| 6 | Validar no modo A (túnel SSH, sem domínio) | local | a fazer |
| 7 | Cloudflare Tunnel e domínio | Cloudflare + servidor | ✅ domínio já delegado ao Cloudflare (`dalary`/`pranab.ns.cloudflare.com`) |
| 8 | Google Cloud: origem e publicação | Google | a fazer (depende de D4/D5) |
| 9 | Fechar portas e teste de aceite online | AWS + navegador | a fazer |
| 10 | Rotina: backup, atualização, livros novos | servidor | a fazer |

---

## 0. Pré-requisitos (local)

### 0.1 Código no branch que o servidor clona
O servidor clona o branch padrão (`main`), mas tudo o que foi feito está em `feat/deepseek_docker`, 38 commits à frente do `main` (item C2). Escolha um caminho:
- **Recomendado:** abrir um PR `feat/deepseek_docker` → `develop` → `main` no GitHub e fazer o merge.
- **Alternativa:** clonar o branch direto no passo 2 (`git clone -b feat/deepseek_docker ...`).

```powershell
git status                 # (local) nada pendente
git push                   # o servidor só enxerga o que está no GitHub
```

### 0.2 Banco dos livros pronto e medido
```powershell
cd backend
..\.venv\Scripts\python -m vector_builder list        # t20-basico: banco pronto, 1313 trechos, ollama/bge-m3
..\.venv\Scripts\python -m vector_builder evaluate    # esperado: híbrida r@5 100%, MRR ~0,93
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
# alternativa do passo 0.1:  git clone -b feat/deepseek_docker https://github.com/radsrei/PAC-Resposta-de-Nimb.git PAC-Resposta-de-Nimb
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
| `ENABLE_DOCS` | `false` | `false` | o padrão do código é `true` |
| `CORS_ORIGINS` | `http://localhost:8080` | `https://respostas-nimb.com.br` | diferente disso, todo POST é bloqueado |
| `COOKIE_SECURE` | `false` | `true` | `true` sem HTTPS faz o login voltar à tela inicial |
| `APP_SECRET_KEY` | valor gerado | o mesmo | |
| `GOOGLE_CLIENT_ID` | seu Client ID | o mesmo | |
| **`ADMIN_EMAILS`** | **e-mail Google do administrador** | o mesmo | obrigatório: é o único jeito de ter administrador. Fica só no `.env` (repositório público). Vira admin na criação da conta e a cada login |
| `FIRST_USER_IS_ADMIN` | `false` | `false` | já é o padrão desde 25/10/2026 (item C4) |
| `REGISTRATION_ENABLED` | `true` | decisão D5 | `false`: só entram usuários já cadastrados |
| `LLM_DEEPSEEK_API` | chave do DeepSeek | a mesma | cria a conexão "DeepSeek (.env)" na 1ª subida |
| `LLM_MODEL` | `deepseek-chat` | `deepseek-chat` | |
| `LLM_TIMEOUT` | `90` | `90` | abaixo dos ~100 s do Cloudflare (erro 524) |
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
ls ~/PAC-Resposta-de-Nimb/vector_store/books/t20-basico      # chroma-<data>/  chunks.jsonl  manifest.json
```
O `chunks.jsonl` é obrigatório: é o índice da busca por palavras. A pasta `preview/` pode ir junto ou ser apagada.

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
| 2 | **Conectar LLM** → "DeepSeek (.env)" → **Testar** | ativa e respondendo |
| 3 | Sem livro: campo de pergunta | travado, com o aviso "Adicione o livro…" e o botão **Subir PDF** |
| 4 | **Subir PDF** do Tormenta20 (89 MB) | "Livro reconhecido… Acesso liberado." |
| 5 | "Quanto de dano causa a Bola de Fogo?" | 6d6, fonte Tormenta20, p. 182 |
| 6 | "Quanto dinheiro inicial um personagem de 5º nível recebe?" | T$ 2.000, p. 140 |
| 7 | "Qual é a capital da França?" | mensagem "Nimb só responde sobre o sistema Tormenta20…" |
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
- **Publicar app:** tira do modo *Teste* e libera qualquer conta Google. **Só depois das decisões D4 (direitos dos livros) e D5 (quem pode entrar).** Até lá, mantenha em *Teste* com os e-mails do grupo.

---

## 9. Fechar portas e teste de aceite online

**EC2 → Security groups**: só SSH 22 do seu IP; sem 80 nem 443.
```bash
curl -m 5 http://<IP-ELASTICO>        # (local) deve falhar: o site só existe pelo Cloudflare
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
| Erro **1033** | `cloudflared` parado ou token errado: `docker compose logs cloudflared` |
| **502 Bad Gateway** no domínio | hostname do tunnel diferente de `web:80`, ou `web` fora do ar |
| **ERR_TOO_MANY_REDIRECTS** | `SITE_ADDRESS` com o domínio em vez de `:80` |
| **524** | resposta passou de ~100 s: `LLM_TIMEOUT=90` e `deepseek-chat` |
| Build da API falha no `pip install` | conflito com o `requirements.lock`: confira se o `requirements.txt` e o lock são do mesmo commit; para mudar uma versão, gere o lock de novo (C3) |
| Ninguém é administrador | `ADMIN_EMAILS` vazio ou diferente do e-mail da conta Google; corrija o `.env`, `docker compose restart api` e entre de novo |
| Sem memória no build ou no upload | instância menor que `t3.medium`, ou swap não criado (`swapon --show`) |
| Logs | `docker compose logs -f api` · `web` · `ollama` · `cloudflared` |

Arquivos do deploy: [deploy/docker-compose.yml](../deploy/docker-compose.yml) · [deploy/Caddyfile](../deploy/Caddyfile) · [backend/Dockerfile](../backend/Dockerfile) · [deploy/web.Dockerfile](../deploy/web.Dockerfile) · [deploy/server-setup.sh](../deploy/server-setup.sh) · [deploy/backup.sh](../deploy/backup.sh)
