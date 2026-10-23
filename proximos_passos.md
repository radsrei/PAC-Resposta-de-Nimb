# Próximos Passos — Respostas de Nimb online

Objetivo final: o serviço rodando num servidor (ex.: AWS), com o usuário **entrando com o Google → enviando o PDF do livro → o livro validado → fazendo perguntas respondidas com base no livro**.

Levantamento feito sobre o estado atual do repositório (branch `feat/tela_sistema`). Atualizado em 22/10/2026: DeepSeek definido, kit de deploy pronto e Cloudflare + `respostas-nimb.com.br` (D10).

---

## 1. Onde o projeto está

| Etapa do fluxo final | Situação | Observação |
|---|---|---|
| Login com Google | ✅ pronto | testado localmente; falta configurar o domínio de produção |
| Upload e validação do livro | ✅ pronto | testado com PDFs gerados; **falta testar com os livros reais** |
| Banco vetorial por livro | ✅ pronto | `vector_builder`, Ollama ou sentence-transformers; nenhum livro real construído ainda |
| Perguntas usando o livro (RAG) | ❌ **falta** | hoje a pergunta vai direto para a LLM, sem consultar o banco vetorial |
| Front de produção | ✅ pronto | `tsc` e `vite build` passando; compilado dentro do Docker no deploy |
| LLM | ✅ definida | só DeepSeek (demais provedores desativados no back e no front) |
| Implantação no servidor | ⚠️ kit pronto | Docker + Caddy em `deploy/`, passo a passo em [deploy_aws.md](deploy_aws.md); falta executar na AWS |

```text
Navegador ──HTTPS──► Proxy (nginx / ALB) ──┬── /       → front (arquivos do vite build)
                                           └── /api/*  → API FastAPI (uvicorn)
                                                          ├── SQLite (backend/data/)
                                                          ├── vector_store/ (catálogo + Chroma)
                                                          ├── Embeddings (Ollama ou sentence-transformers)
                                                          └── LLM do chat (API externa ou Ollama)
```

---

## 2. Decisões pendentes

Precisam ser tomadas antes ou durante a implantação. Estão ordenadas da que mais trava o objetivo final para a que menos trava.

### D1. Onde e como hospedar — ALTA
> ✅ **Decidido:** EC2 única + Docker Compose + Caddy (HTTPS automático). Kit em `deploy/`.

| Opção | Prós | Contras |
|---|---|---|
| **EC2 única + Docker Compose** (recomendado para começar) | simples; SQLite e `vector_store/` no mesmo disco (EBS); barato | escala só vertical; você administra a máquina |
| ECS/Fargate ou App Runner | gerenciado, escala | precisa trocar SQLite por RDS e o disco local por EFS/S3 |
| Lightsail | mais barato e simples | menos flexível para GPU/memória |

Tamanho mínimo da máquina, se os embeddings rodarem nela: **8 GB de RAM** (ex.: `t3.large`), porque o `bge-m3` ocupa cerca de 2,5 GB. Confira os valores na calculadora da AWS.

### D2. LLM que responde as perguntas — ALTA
> ✅ **Decidido:** DeepSeek (`deepseek-chat`). Os demais provedores foram removidos.

| Opção | Prós | Contras |
|---|---|---|
| **API externa** (OpenAI, Anthropic, Gemini, DeepSeek) (recomendado) | qualidade alta; servidor sem GPU | custo por uso; dados enviados ao provedor |
| Ollama no servidor | sem custo por token; dados ficam no servidor | exige instância com GPU (cara) ou fica lento em CPU |

O sistema já suporta todas; é só escolher e cadastrar em **Conectar LLM**.

### D3. Embeddings na hora da pergunta — ALTA
A pergunta precisa ser vetorizada **com o mesmo modelo** usado para construir o banco.
| Opção | Prós | Contras |
|---|---|---|
| **Ollama no próprio servidor** (recomendado) | API leve, sem PyTorch; mesmo `bge-m3` | um serviço a mais rodando (container `ollama`) |
| sentence-transformers dentro da API | um processo só | imagem Docker de cerca de 3 GB; mais memória por worker |
| Embeddings por API (ex.: OpenAI) | sem modelo no servidor | exige reconstruir todos os bancos e adicionar o provedor |

### D4. Direitos dos livros — ALTA (se o sistema for público)
O `catalog.json` guarda frases dos livros, e o banco vetorial guarda o texto completo em trechos. As respostas citam o conteúdo.
- Decidir: uso restrito (turma, grupo fechado) ou público.
- Se público: obter autorização da editora (Jambô) ou limitar a aberto/SRD.
- Relacionado: quem pode entrar (D5).

### D5. Quem pode acessar — ALTA
Hoje qualquer conta Google cria conta no primeiro login (`REGISTRATION_ENABLED=true`).
- Aberto para qualquer conta Google;
- Restrito: `REGISTRATION_ENABLED=false` e os usuários cadastrados antes. Falta tela ou comando para o admin cadastrar e-mails.
- Lista de domínios permitidos (ex.: só `@empresa.com.br`): **não implementado**.

A tela de consentimento OAuth do Google também precisa sair do modo **Teste** para **Em produção**. No modo Teste, só os e-mails de teste conseguem entrar.

### D6. Pergunta sem livro liberado — MÉDIA
O que o chat faz quando o usuário não liberou nenhum livro:
- bloqueia e pede o upload;
- ou responde só com a LLM, avisando que não há fonte. É o comportamento atual.

### D7. Domínio e HTTPS — MÉDIA
> ✅ **Decidido:** `respostas-nimb.com.br` (Registro.br, em processamento), com HTTPS pelo Cloudflare (D10). Até o domínio ficar ativo, o modo túnel SSH do [deploy_aws.md](deploy_aws.md) permite testar o login Google sem domínio.

- Domínio próprio (Route 53 ou outro registrador). O Google exige HTTPS na origem.
- Certificado: ACM + ALB, ou nginx + Let's Encrypt (`certbot`) na própria EC2.

### D8. Segredos de produção — MÉDIA
`APP_SECRET_KEY`, `GOOGLE_CLIENT_ID` e as API keys das LLMs.
- Bitwarden: já usado pelo time (README), com injeção no `.env` na implantação;
- ou AWS SSM Parameter Store / Secrets Manager.

### D9. Banco de dados — BAIXA (por enquanto)
SQLite atende uma instância única. Migrar para PostgreSQL (RDS) só se houver mais de uma instância (D1).

### D10. Cloudflare na frente da AWS — ALTA
> ✅ **Decidido em 22/10/2026:** Cloudflare (DNS + Tunnel) como complemento da EC2, no domínio **`respostas-nimb.com.br`** (Registro.br). Passo a passo em [cloudflare_dominio.md](cloudflare_dominio.md).

**Contexto.** Para abrir o sistema aos usuários é preciso um domínio com HTTPS (login Google). O Cloudflare grátis oferece DNS, proxy com proteção contra DDoS, firewall, HTTPS na borda e o Tunnel, que liga a EC2 ao Cloudflare por uma conexão de saída, sem portas abertas no servidor.

**Decisão.**
- O domínio fica registrado no **Registro.br**, com os servidores DNS apontados para o Cloudflare (o Cloudflare não registra `.br`).
- O tráfego entra pelo **Cloudflare Tunnel** (container `cloudflared`, perfil `cloudflare` no compose). O Caddy segue em HTTP dentro do servidor, e o HTTPS fica no Cloudflare.
- A EC2 fecha as portas 80 e 443 no security group. A porta 22 continua só para o IP do administrador.
- A API, o banco e o RAG continuam na EC2. O Cloudflare não substitui nenhuma parte do backend.

**Consequências (aplicadas no código):**

| # | Limite do Cloudflare grátis | Ajuste feito | Onde |
|---|---|---|---|
| 1 | Requisições de no máximo 100 MB (erro 413) | upload de livros reduzido de 150 para **95 MB**; o Caddy barra acima de 100 MB; o front avisa antes de enviar | `BOOK_UPLOAD_MAX_MB=95`, `MAX_UPLOAD_MB` em `PdfUploadModal.tsx`, `request_body` no `Caddyfile` |
| 2 | Resposta em até ~100 s (erro 524) | tempo máximo da LLM reduzido de 120 para **90 s** | `LLM_TIMEOUT=90` (`config.py`, `.env.example`) |
| 3 | O IP que chega ao servidor é do Cloudflare; o `X-Forwarded-For` pode ser forjado pelo cliente | o Caddy lê o IP real do `CF-Connecting-IP`, mas só de proxies da rede privada (o `cloudflared`); requisições diretas ignoram o cabeçalho | `servers { trusted_proxies / client_ip_headers }` + `header_up X-Forwarded-For {client_ip}` no `Caddyfile` |

**Alternativas descartadas.**

| Alternativa | Motivo |
|---|---|
| API no Cloudflare (Workers/D1/Vectorize) | memória e tempo de CPU insuficientes para ler PDFs com o pypdf; reescrita total do backend |
| Front no Cloudflare Pages | ganho pequeno (~300 KB); front e API em origens diferentes complicam o cookie e o CORS |
| Quick Tunnel (`trycloudflare.com`) | o endereço muda a cada execução, e a origem do Google teria de ser recadastrada sempre |
| Vectorize como banco vetorial | a cota grátis comporta cerca de 4.900 trechos (1 a 2 livros) |
| Proxy do Cloudflare apontando para portas abertas na EC2 | funciona, mas expõe o servidor; o Tunnel dispensa portas abertas |

**Em aberto.**
- Livros acima de 95 MB: comprimir o PDF, upload em partes (mudança de código) ou plano Business (200 MB).
- `deepseek-reasoner` com respostas longas pode passar de 90 s. A saída definitiva é enviar a resposta aos poucos (streaming).
- Cloudflare Access (até 50 usuários grátis) para restringir quem entra (D5), se o sistema não for público.
- Workers AI (`@cf/baai/bge-m3`) para os embeddings da pergunta (D3), a reavaliar no P0.1.

---

## 3. Demandas por prioridade

### P0 — Bloqueiam o objetivo final (sem isso o sistema não funciona online)

**P0.1 Ligar o RAG às perguntas** — `backend/app/controllers/query_controller.py`
- Pegar os livros liberados do usuário em `book_access`. **Não confiar** no `bookIds` enviado pelo front.
- Vetorizar a pergunta com `create_embedder_from_info(manifest["embedding"]).embed_query(...)`.
- Buscar os trechos mais próximos em `book_catalog.chroma_path(id)` de cada livro e montar o contexto no prompt (`services/prompts.py`).
- Devolver `bookTitle`, `page`, `similarity` e `quote` reais. Hoje voltam vazios em `routers/rag.py`.
- Mover `embeddings.py` (ou a parte de consulta) para `app/services/`, porque a API não deve depender do pacote do construtor.
- Adicionar `chromadb` em `backend/requirements.txt`.
- Atualizar `/api/health`, que hoje retorna `"rag_engine": "desativado"`.
- Depende de: D3, D6.

**P0.2 Compilar e testar o front** — ✅ `tsc` e `vite build` passando; falta só o teste manual no navegador
- As mudanças de login, upload e livros foram feitas sem Node.js na máquina: **nunca passaram pelo `tsc`**.
```bash
cd "frontend/V2 - front Studio"
npm ci && npm run lint && npm run build      # gera dist/
```
- Testar no navegador: login → Subir PDF → Livros Liberados → pergunta.

**P0.3 Empacotar para o servidor** — ✅ `backend/Dockerfile`, `deploy/web.Dockerfile` e `deploy/docker-compose.yml`. **Pendente:** fixar as versões das dependências
- `backend/Dockerfile`: Python 3.11/3.12, `pip install -r requirements.txt`, rodando:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips="*"
```
- **Não usar `python main.py` em produção.** Ele sobe com `reload=True` (`backend/main.py`).
- `docker-compose.yml` com `api`, `ollama` (se D3 = Ollama) e `nginx`, e volumes para `backend/data/` e `vector_store/`.
- Fixar as versões das dependências (`pip freeze` → `requirements.lock`). Hoje nada tem versão fixa, e o servidor pode instalar versões diferentes das testadas.

**P0.4 Proxy, HTTPS e mesmo domínio** — ✅ Caddy (`deploy/Caddyfile`): front e `/api` no mesmo endereço, limite de 100 MB (D10), HTTPS pelo Cloudflare ou pelo próprio Caddy
- O front chama `/api/...` por caminho relativo: front e API precisam estar **no mesmo domínio**.
- nginx (ou ALB) servindo `dist/` em `/` e encaminhando `/api/` para o uvicorn.
- `client_max_body_size 160m;` no nginx. **O padrão de 1 MB bloqueia o upload dos livros.**
- Tempo de resposta: `LLM_TIMEOUT=90`, abaixo dos ~100 s do Cloudflare (D10).

**P0.5 Corrigir o IP real atrás do proxy** — ✅ uvicorn com `--proxy-headers` + Caddy lendo o `CF-Connecting-IP` só da rede privada (D10); testado: IP forjado no `X-Forwarded-For` é descartado
- `core/rate_limit.py` usa `request.client.host`. Atrás do nginx/ALB, **todos os usuários aparecem com o mesmo IP**: o limite de 20 logins/min e 5 uploads/min passaria a valer para o sistema inteiro.
- Resolve com `--proxy-headers --forwarded-allow-ips` no uvicorn (P0.3), aceitando o cabeçalho só do proxy.

**P0.6 Configuração de produção** — `backend/.env` no servidor — ✅ valores por modo no [deploy_aws.md](deploy_aws.md), passo 4
```ini
COOKIE_SECURE=true
ENABLE_DOCS=false
CORS_ORIGINS=https://respostas-nimb.com.br
APP_SECRET_KEY=<valor longo e aleatório, guardado no cofre>
GOOGLE_CLIENT_ID=<client id>
EMBEDDING_PROVIDER=ollama
OLLAMA_URL=http://ollama:11434
```
- Sem o domínio em `CORS_ORIGINS`, o middleware bloqueia **todo POST** (login inclusive) com "Origem não permitida".
- No Google Cloud: adicionar `https://respostas-nimb.com.br` nas origens JavaScript autorizadas e publicar a tela de consentimento (D5).

**P0.7 Livros reais: construir e calibrar**
- Rodar `build --dry-run` em cada livro e revisar o `chunks.jsonl` (qualidade dos trechos, colunas, tabelas).
- Rodar `build` e depois `check` com **uma cópia diferente do original** (outra tiragem ou outro download) para calibrar `min_score`, `probe_page_window` e `page_count_tolerance`.
- Conferir se os PDFs têm camada de texto. Se não tiverem, aplicar OCR antes.
- Enviar `vector_store/` para o servidor (`scp`, `rsync` ou `aws s3 sync`). Ele está fora do Git.

**P0.8 Persistência e backup** — ✅ volume `nimb_data` + `deploy/backup.sh`; falta agendar no servidor (cron + snapshot do EBS)
- `backend/data/` (usuários, sessões, conversas, API keys criptografadas, `secret.key`) e `vector_store/` em volume persistente (EBS).
- Snapshot automático do EBS (AWS Data Lifecycle Manager), ou cópia diária para o S3.
- **Se a `secret.key` ou a `APP_SECRET_KEY` se perder, as API keys cadastradas deixam de abrir.**

### P1 — Importantes logo após subir (segurança e operação)

| # | Demanda | Onde |
|---|---|---|
| P1.1 | Testes automatizados no repositório (hoje só existiram em pasta temporária) + CI no GitHub Actions rodando `pytest` e `npm run lint/build` | `backend/tests/`, `.github/workflows/` |
| P1.2 | SQLite em modo WAL (`PRAGMA journal_mode=WAL`) para vários workers gravando juntos | `app/db/database.py` |
| P1.3 | Limite de tempo e memória na leitura do PDF (um PDF malicioso pode prender um worker) | `services/book_fingerprint.py` |
| P1.4 | Ferramentas de admin: ver o histórico de validações, revogar o acesso a um livro, cadastrar e-mails permitidos (D5) | `routers/admin.py` + tela Minha Conta |
| P1.5 | Logs centralizados (CloudWatch) e alarme no `/api/health` | infra |
| P1.6 | `Cross-Origin-Opener-Policy: same-origin` no middleware. Se um dia a API servir o HTML do front, o popup do Google quebra; usar `same-origin-allow-popups` | `core/middleware.py` |
| P1.7 | Rate limit em memória vale por processo; com vários workers, o limite real multiplica. Avaliar Redis se o abuso virar problema | `core/rate_limit.py` |
| P1.8 | Script de implantação: atualizar código, reconstruir os containers, rodar a migração do banco | `scripts/deploy.sh` |

### P2 — Podem ser corrigidas depois, sem prejuízo ao projeto

| # | Demanda | Onde |
|---|---|---|
| P2.1 | Textos fixos na tela: selo "RAG v2.4", "NEURAL CHAOS RETRIEVAL ENGINE", sugestões fixas do chat | `Header.tsx`, `SuggestionChips.tsx` |
| P2.2 | Botão **Subir PDF** escondido no celular (`hidden sm:flex`); no celular só abre pela barra lateral | `Header.tsx` |
| P2.3 | Limpeza do repositório: pipelines antigos `backend/RAG_*`, `Convert_file/` (splitter duplicado em `backend/RAG_Claude/Conversao_Docling/`), `deepseek/`, `estrutura-Exemplo/`, `docs/nimb_prototipo/`, `backend/Estrutura_base.py`, `final.ipynb` | raiz e `backend/` |
| P2.4 | Rota legada `/api/perguntas` e a docstring desatualizada de `backend/main.py` (cita `frontend/nimb-os-react` e `frontend/Claude`, que não existem mais) | `routers/perguntas.py`, `backend/main.py` |
| P2.5 | `requirements.txt` da raiz instala tudo (Docling, LangChain), mas o servidor só precisa de `backend/requirements.txt` | raiz |
| P2.6 | Docs antigas: `resp.md` (cita o venv `nimb` e o "upload como stub"), tutoriais do Docling usando `env` | `resp.md`, `*/TUTORIAL_GIT_E_DOCLING.md` |
| P2.7 | Imagens com nomes de pessoas em `PAC-7+8/` (presença, PRs) num repositório público: avaliar se devem continuar versionadas | `PAC-7+8/` |
| P2.8 | Licença AGPL-3.0: num serviço online, o código-fonte precisa ficar disponível aos usuários (link no rodapé para o GitHub) | `LICENSE`, tela |
| P2.9 | Comando para cadastrar outra edição do mesmo livro sem refazer as frases (`add-edition`) e uma etapa de OCR automática (`ocrmypdf`) | `vector_builder/` |
| P2.10 | PostgreSQL (RDS) e armazenamento compartilhado só quando houver mais de uma instância (D9) | infra |

---

## 4. Sequência sugerida

```text
Semana 1 — Decidir e fechar o fluxo local
  D1, D2, D3, D5, D6 decididas
  P0.1  RAG ligado às perguntas
  P0.2  front compilado e testado no navegador
  P0.7  livros reais construídos e calibrados

Semana 2 — Empacotar e subir
  P0.3  Dockerfile + compose + versões fixas
  D7    domínio e certificado
  P0.4  nginx/ALB com HTTPS, limite de upload e timeout
  P0.5  IP real (proxy headers)
  P0.6  .env de produção + Google com o domínio
  P0.8  volumes e backup
  → teste ponta a ponta no servidor: login → upload → pergunta com fonte

Depois de online
  P1 (testes/CI, WAL, admin, logs) → P2 (limpeza e ajustes de tela)
```

## 5. Checklist de aceite (sistema online)

- [ ] `https://respostas-nimb.com.br` abre a tela de login com certificado válido
- [ ] Login com Google funciona com uma conta fora da lista de teste
- [ ] Upload de um livro real (até 95 MB) é aceito; um PDF diferente é recusado
- [ ] O livro aparece em **Livros Liberados** só para quem enviou
- [ ] A pergunta volta com resposta, nome do livro e página da fonte
- [ ] Reiniciar o servidor não perde usuários, conversas, livros liberados nem a conexão LLM
- [ ] Dois usuários diferentes conseguem logar ao mesmo tempo sem bater no limite de requisições
