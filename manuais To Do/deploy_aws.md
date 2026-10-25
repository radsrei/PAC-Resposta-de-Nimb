# Deploy AWS — Respostas de Nimb

> ⚠️ **Desatualizado em 24/10/2026.** Use o [deploy_ec2_compilado.md](deploy_ec2_compilado.md), que corrige a instância (`t3.medium`), o Ollama obrigatório (`COMPOSE_PROFILES=rag`), o `FIRST_USER_IS_ADMIN=false` e a ordem dos passos. Problemas em [problemas_e_falhas.md](problemas_e_falhas.md).

Sequência para colocar o sistema numa EC2 da AWS: login com Google → upload do livro → perguntas respondidas pelo DeepSeek.
Comandos do servidor no terminal SSH (Ubuntu); comandos da sua máquina no PowerShell.

```text
Navegador ──► EC2 (Docker)
               ├── web : Caddy → front compilado + HTTPS automático + /api → api
               └── api : FastAPI (SQLite em volume, catálogo dos livros em vector_store/)
                           └──► api.deepseek.com
```

**Nenhum trecho de código muda para apontar o servidor.** O front chama `/api` por caminho relativo. O que muda entre local e servidor fica em dois arquivos: `backend/.env` e `deploy/.env`.

> Ainda falta: as perguntas são respondidas pelo DeepSeek, mas **ainda sem consultar o texto do livro** (próximo passo P0.1 em [proximos_passos.md](proximos_passos.md)).

## Domínio: agora ou depois?

O login do Google **exige HTTPS e não aceita IP** como origem; só o `localhost` é exceção.

| Modo | Domínio | Quem acessa | Para quê |
|---|---|---|---|
| **A. Túnel SSH** | não precisa | só quem tem a chave SSH (você) | subir, testar e validar tudo agora |
| **Cloudflare** (escolhido, D10) | `respostas-nimb.com.br` | qualquer pessoa | sistema aberto, sem portas abertas na EC2 |
| B. Domínio direto | `respostas-nimb.com.br` | qualquer pessoa | alternativa sem Cloudflare (Caddy emite o HTTPS) |

Comece no **modo A**. Quando o Registro.br liberar o domínio, siga o [cloudflare_dominio.md](cloudflare_dominio.md) (passo 9).

## 0. Antes de começar (sua máquina)
```bash
# 1. Código no GitHub (o servidor clona de lá)
git push

# 2. Catálogo dos livros pronto (dentro de backend/, com o .venv ativo)
python -m vector_builder register "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro"
python -m vector_builder list
```
- **Conta AWS:** contas novas têm créditos do Free Tier. O AWS Educate não dá mais créditos desde 2023. Confira o saldo em *Billing → Credits*.
- **Alarme de gastos:** *Billing → Budgets → Create budget* → valor mensal (ex.: US$ 10) com alerta por e-mail.
- **Chave do DeepSeek:** pegue em `platform.deepseek.com` (conta com saldo).

## 1. Criar a máquina (Console AWS → EC2 → Launch instance)
| Campo | Valor |
|---|---|
| Região | `us-east-1` (mais barata) ou `sa-east-1` São Paulo (menor latência) |
| Imagem | Ubuntu Server 24.04 LTS |
| Tipo | `t3.small` (2 GB). Para o Ollama na etapa do RAG: 4 GB+ (`t3.medium`). Prefira os marcados *Free tier eligible* |
| Key pair | criar `nimb` (.pem) e guardar |
| Disco | 20 GB gp3 |
| Security group | SSH 22 **só Meu IP**. Modos A e Cloudflare: nada mais. Só o modo B abre HTTP 80 e HTTPS 443 |

Depois: *EC2 → Elastic IPs → Allocate → Associate* à instância. O IP fixo é usado no SSH e no DNS.

## 2. Preparar o servidor
```bash
ssh -i nimb.pem ubuntu@<IP-ELASTICO>
git clone https://github.com/<usuario>/pac-resposta-de-nimb.git PAC-Resposta-de-Nimb
cd PAC-Resposta-de-Nimb
bash deploy/server-setup.sh          # Docker, swap de 2 GB, updates de segurança
exit                                 # entre de novo para usar o docker sem sudo
```
Repositório privado: use `gh auth login` ou uma *deploy key* no GitHub.

## 3. Enviar o catálogo e os bancos dos livros (sua máquina)
```bash
scp -i nimb.pem -r vector_store ubuntu@<IP-ELASTICO>:~/PAC-Resposta-de-Nimb/
ssh -i nimb.pem ubuntu@<IP-ELASTICO> "sudo chown -R 10001:10001 ~/PAC-Resposta-de-Nimb/vector_store"
```
O Chroma (banco vetorial) usa SQLite e não abre uma pasta somente leitura: o `chown` dá a pasta ao usuário da API no container (uid 10001).

Embeddings da pergunta: suba o Ollama do compose e baixe o modelo uma vez (instância com 4 GB+ de RAM):
```bash
cd ~/PAC-Resposta-de-Nimb/deploy && docker compose --profile rag up -d ollama && docker compose exec ollama ollama pull bge-m3
```
e no `backend/.env`: `OLLAMA_URL=http://ollama:11434`. Se o Ollama não estiver de pé, a pergunta responde 503 com a mensagem do problema.

## 4. Configurar (servidor)
```bash
cd ~/PAC-Resposta-de-Nimb
cp backend/.env.example backend/.env && chmod 600 backend/.env
cp deploy/.env.example deploy/.env
python3 -c "import secrets; print(secrets.token_urlsafe(48))"     # valor do APP_SECRET_KEY
nano backend/.env
```
| Variável (`backend/.env`) | Modo A (túnel) | Cloudflare ou modo B |
|---|---|---|
| `CORS_ORIGINS` | `http://localhost:8080` | `https://respostas-nimb.com.br` |
| `COOKIE_SECURE` | `false` | `true` |
| `ENABLE_DOCS` | `false` | `false` |
| `APP_SECRET_KEY` | valor gerado acima | o mesmo |
| `GOOGLE_CLIENT_ID` | seu Client ID | o mesmo |
| `ADMIN_EMAILS` | seu e-mail Google | o mesmo |
| `LLM_DEEPSEEK_API` | chave do DeepSeek | a mesma |
| `LLM_MODEL` | `deepseek-chat` | `deepseek-chat` |

`deploy/.env`: modo A `SITE_ADDRESS=:80` · Cloudflare: ver [cloudflare_dominio.md](cloudflare_dominio.md) · modo B `SITE_ADDRESS=respostas-nimb.com.br`

Guarde o `APP_SECRET_KEY` no cofre (Bitwarden). Sem ele, a chave do DeepSeek salva no banco não abre mais.

## 5. Google Cloud (Credenciais → seu ID do cliente OAuth)
- **Origens JavaScript autorizadas:** modo A `http://localhost:8080` · Cloudflare/modo B `https://respostas-nimb.com.br`
- **Tela de consentimento:** em *Teste*, só os usuários de teste entram. Para abrir a todos: *Publicar app* (modo B).

## 6. Subir
```bash
cd ~/PAC-Resposta-de-Nimb/deploy
docker compose up -d --build         # 1ª vez: alguns minutos (compila o front)
docker compose ps                    # api: healthy | web: running
docker compose logs -f api           # CTRL + C para sair dos logs
```

## 7. Acessar
Modo A (túnel), sua máquina:
```bash
ssh -i nimb.pem -L 8080:localhost:80 ubuntu@<IP-ELASTICO>       # deixe aberto
```
### http://localhost:8080

Cloudflare ou modo B:
### https://respostas-nimb.com.br

## 8. Teste de aceite
1. Entrar com o Google. O e-mail de `ADMIN_EMAILS` vira administrador.
2. **Conectar LLM** → a conexão "DeepSeek (.env)" aparece ativa → **Testar**.
3. **Subir PDF** → livro do catálogo → "Livro reconhecido. Acesso liberado."
4. Fazer uma pergunta no chat.

## 9. Colocar no domínio (quando o Registro.br liberar)
Caminho escolhido (Cloudflare Tunnel): **[cloudflare_dominio.md](cloudflare_dominio.md)**.

Alternativa sem Cloudflare (modo B):
```bash
# DNS no Registro.br: registro A  respostas-nimb.com.br → <IP-ELASTICO>
# Security group: liberar 80 e 443
nano deploy/.env        # SITE_ADDRESS=respostas-nimb.com.br
nano backend/.env       # CORS_ORIGINS=https://respostas-nimb.com.br  e  COOKIE_SECURE=true
cd deploy && docker compose up -d     # o Caddy emite o certificado HTTPS sozinho
```
No Google Cloud: adicionar a origem `https://respostas-nimb.com.br` e publicar o app.

## 10. Rotina
```bash
cd ~/PAC-Resposta-de-Nimb && git pull && cd deploy && docker compose up -d --build   # atualizar versão
bash deploy/backup.sh                                                                # backup do banco + secret.key
crontab -e        # 0 3 * * * bash $HOME/PAC-Resposta-de-Nimb/deploy/backup.sh        (todo dia às 3h)
scp -i nimb.pem -r vector_store ubuntu@<IP-ELASTICO>:~/PAC-Resposta-de-Nimb/        # livro novo (sua máquina)
sudo chown -R 10001:10001 ~/PAC-Resposta-de-Nimb/vector_store                        # depois de cada envio (servidor)
```
- **Snapshot do disco:** *EC2 → Lifecycle Manager → política diária de snapshot do volume*.
- **Economizar créditos:** pare a instância quando não estiver usando (*Instance state → Stop*). O IP elástico continua cobrando um valor pequeno.

## Problemas rápidos
| Sintoma | Causa / solução |
|---|---|
| "Origem da requisição não permitida" | `CORS_ORIGINS` diferente do endereço aberto no navegador |
| Botão do Google não aparece ou dá erro de origem | falta a origem no Google Cloud ou o endereço não é `https`/`localhost` |
| Login entra e volta para a tela de login | `COOKIE_SECURE=true` sem HTTPS (modo A precisa de `false`) |
| "Conta do DeepSeek sem saldo" | recarregar créditos no DeepSeek |
| Upload termina com "Nenhum livro permitido" | `vector_store/catalog.json` não foi enviado ao servidor (passo 3) |
| "Arquivo maior que o limite de 95 MB" | limite do Cloudflare grátis (D10): comprimir o PDF |
| HTTPS não emite certificado | DNS ainda não aponta para o IP, ou portas 80/443 fechadas |
| Logs | `docker compose logs api` · `docker compose logs web` |

Arquivos do deploy: [deploy/docker-compose.yml](deploy/docker-compose.yml) · [deploy/Caddyfile](deploy/Caddyfile) · [backend/Dockerfile](backend/Dockerfile) · [deploy/web.Dockerfile](deploy/web.Dockerfile)
