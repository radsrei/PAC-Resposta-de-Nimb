# Domínio e Cloudflare — respostas-nimb.com.br

> ⚠️ **Atualização de 24/10/2026:** os passos 1 e 2 já foram feitos (domínio delegado ao Cloudflare). No passo 5, use **`COMPOSE_PROFILES=cloudflare,rag`**: sem o `rag`, o Ollama não sobe e toda pergunta falha. Sequência completa em [deploy_ec2_compilado.md](deploy_ec2_compilado.md).

Sequência para colocar o sistema da EC2 no domínio **`respostas-nimb.com.br`** usando o Cloudflare (DNS + Tunnel), conforme a decisão **D10** do [proximos_passos.md](proximos_passos.md).
Pré-requisito: o sistema já rodando na EC2 pelo [deploy_aws.md](deploy_aws.md) (modo A, túnel SSH).

```text
Navegador ──HTTPS──► Cloudflare (DNS, certificado, proteção)
                          │  Tunnel: conexão de SAÍDA da EC2, nenhuma porta aberta
                          ▼
                     EC2: cloudflared → web (Caddy :80) → front + /api → api → DeepSeek
```

## O que mudou no projeto (D10)
| Ponto | Antes | Agora | Por quê |
|---|---|---|---|
| Upload de livro | 150 MB | **95 MB** (`BOOK_UPLOAD_MAX_MB`, front e Caddy) | o Cloudflare grátis recusa acima de 100 MB |
| Tempo da LLM | 120 s | **90 s** (`LLM_TIMEOUT`) | o Cloudflare encerra em ~100 s (erro 524) |
| IP do usuário | `X-Forwarded-For` | **`CF-Connecting-IP`**, aceito só da rede privada | o IP que chega é do Cloudflare; o `X-Forwarded-For` pode ser forjado |
| Entrada no servidor | portas 80/443 abertas (modo B) | **container `cloudflared`** (`COMPOSE_PROFILES=cloudflare`) | EC2 sem portas web abertas |

Arquivos: [deploy/Caddyfile](deploy/Caddyfile) · [deploy/docker-compose.yml](deploy/docker-compose.yml) · [deploy/.env.example](deploy/.env.example) · `backend/.env.example` · `PdfUploadModal.tsx`

## 0. Enquanto o Registro.br processa
O domínio só aceita troca de DNS depois de aprovado (status *Publicado* no Registro.br).
Até lá, siga no **modo A** (túnel SSH) e já faça os passos 1 e 4, que não dependem do domínio ativo.
```bash
nslookup -type=NS respostas-nimb.com.br        # mostra os servidores DNS atuais
```

## 1. Adicionar o domínio no Cloudflare
1. Crie a conta em `dash.cloudflare.com`.
2. **Add a domain** → `respostas-nimb.com.br` → plano **Free**.
3. A importação de registros DNS vem vazia; tudo bem, porque o Tunnel cria o registro sozinho.
4. Anote os **2 nameservers** que o Cloudflare mostrar (ex.: `xxxx.ns.cloudflare.com` e `yyyy.ns.cloudflare.com`).

## 2. Apontar o Registro.br para o Cloudflare
`registro.br` → **Acessar conta** → `respostas-nimb.com.br` → **DNS** → **Alterar servidores DNS**:
```text
Servidor 1:  xxxx.ns.cloudflare.com
Servidor 2:  yyyy.ns.cloudflare.com
```
O Registro.br publica as alterações a cada ~30 min. O Cloudflare avisa por e-mail quando o domínio fica **Active**.
```bash
nslookup -type=NS respostas-nimb.com.br        # deve listar os ns.cloudflare.com
```

## 3. Ajustes no painel do Cloudflare
| Onde | Ajuste |
|---|---|
| SSL/TLS → Edge Certificates | **Always Use HTTPS**: ligado · **Minimum TLS**: 1.2 |
| Speed → Optimization | **Rocket Loader**: desligado (quebra apps React) |
| Security → Bots | **Bot Fight Mode**: desligado no início; ligar só depois de testar login e upload |
| Rules → Redirect Rules | modelo **Redirect from WWW to root** (`www` → `respostas-nimb.com.br`) |
| DNS → Settings (opcional) | **DNSSEC**: habilitar e copiar o registro DS para o Registro.br (*DNSSEC* no painel do domínio) |

## 4. Criar o Tunnel
**Zero Trust** → **Networks** → **Tunnels** → **Create a tunnel** → **Cloudflared** → nome `nimb-aws`.
Na primeira vez, o Zero Trust pede para escolher um nome de equipe e o plano **Free**.

1. Na tela de instalação, copie **só o token** (o texto longo depois de `--token`, começa com `eyJ`). Ele é segredo: guarde no Bitwarden.
2. **Public hostnames** → **Add a public hostname**:

| Subdomain | Domain | Type | URL |
|---|---|---|---|
| *(vazio)* | `respostas-nimb.com.br` | HTTP | `web:80` |
| `www` | `respostas-nimb.com.br` | HTTP | `web:80` |

O `web` é o nome do container do Caddy no `docker-compose.yml`; o `cloudflared` o encontra pela rede do Docker.

## 5. Configurar o servidor
```bash
ssh -i nimb.pem ubuntu@<IP-ELASTICO>
cd ~/PAC-Resposta-de-Nimb && git pull
nano deploy/.env && chmod 600 deploy/.env
```
```ini
# deploy/.env
SITE_ADDRESS=:80
COMPOSE_PROFILES=cloudflare
TUNNEL_TOKEN=eyJ...
```
```bash
nano backend/.env
```
```ini
# backend/.env (só estas mudam)
CORS_ORIGINS=https://respostas-nimb.com.br
COOKIE_SECURE=true
BOOK_UPLOAD_MAX_MB=95
LLM_TIMEOUT=90
```
`SITE_ADDRESS` continua `:80`. O HTTPS é do Cloudflare: se o Caddy também tentar HTTPS, o site entra em loop de redirecionamento.

## 6. Subir
```bash
cd ~/PAC-Resposta-de-Nimb/deploy
docker compose up -d --build
docker compose ps                         # api: healthy | web, cloudflared: running
docker compose logs cloudflared           # esperado: "Registered tunnel connection" (4 vezes)
```
No painel: **Tunnels** → `nimb-aws` com status **Healthy**.

## 7. Google Cloud
- **Credenciais** → ID do cliente OAuth → **Origens JavaScript autorizadas**: `https://respostas-nimb.com.br`
- **Tela de consentimento** → **Domínios autorizados**: `respostas-nimb.com.br`. Se pedir verificação, adicione o TXT do Search Console no **DNS do Cloudflare**.
- **Publicar app**: sai do modo *Teste* e libera para qualquer conta Google.

## 8. Fechar as portas da EC2
**EC2** → **Security groups** → regras de entrada:
```text
SSH 22    → Meu IP        (mantém)
HTTP 80   → remover
HTTPS 443 → remover
```
```bash
curl -m 5 http://<IP-ELASTICO>            # deve falhar: o site só existe pelo Cloudflare
```

## 9. Teste de aceite
### https://respostas-nimb.com.br
1. Cadeado válido no navegador; `https://www.respostas-nimb.com.br` redireciona para o domínio raiz.
2. Login com Google.
3. **Conectar LLM** → DeepSeek ativo → **Testar**.
4. **Subir PDF** de até 95 MB → "Livro reconhecido". Acima disso, o front avisa antes de enviar.
5. Pergunta no chat.
6. IP real gravado (deve ser o seu IP público, não um `172.x` do Docker):
```bash
docker compose exec api python -c "import sqlite3; print(sqlite3.connect('/app/data/nimb.db').execute('select user_email, ip from auth_sessions order by created_at desc limit 3').fetchall())"
```

## 10. Voltar ao modo A (se algo der errado)
```bash
nano deploy/.env                          # COMPOSE_PROFILES=   (vazio)
nano backend/.env                         # CORS_ORIGINS=http://localhost:8080  e  COOKIE_SECURE=false
docker compose up -d --remove-orphans     # derruba o cloudflared
ssh -i nimb.pem -L 8080:localhost:80 ubuntu@<IP-ELASTICO>   # http://localhost:8080
```

## Problemas rápidos
| Sintoma | Causa / solução |
|---|---|
| Erro **1033** (Argo Tunnel error) | `cloudflared` parado ou token errado: `docker compose logs cloudflared` |
| **502 Bad Gateway** | URL do hostname público diferente de `web:80`, ou `web` fora do ar |
| **ERR_TOO_MANY_REDIRECTS** | `SITE_ADDRESS` com o domínio em vez de `:80` |
| "Origem da requisição não permitida" | acessou pelo `www` sem o redirecionamento do passo 3, ou `CORS_ORIGINS` diferente |
| **413** no upload | PDF acima de 100 MB passou pelo front antigo: atualizar (`git pull` + `--build`) e comprimir o PDF |
| **524** na pergunta | resposta passou de ~100 s: manter `LLM_TIMEOUT=90` e usar `deepseek-chat` |
| Todos os usuários com o mesmo IP no limite de login | o `Caddyfile` não é o da D10: `git pull` e `docker compose up -d --build` |
| Domínio não fica *Active* | nameservers ainda não publicados no Registro.br: aguarde e confira com `nslookup` |

Relacionados: [deploy_aws.md](deploy_aws.md) · [proximos_passos.md](proximos_passos.md) (D7, D10) · [execucao_controlada.md](execucao_controlada.md)
