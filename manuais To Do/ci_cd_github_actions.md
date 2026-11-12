# CI/CD com GitHub Actions — Respostas de Nimb

Como funciona o pipeline e como configurar do zero o deploy automático: **merge no `main` → testes → imagens Docker no Amazon ECR → atualização da EC2**. Complementa o [deploy_ec2_compilado.md](deploy_ec2_compilado.md), que continua valendo para criar a máquina e o primeiro `.env`.

```text
PR (feat/* → develop → main)                 push no main (merge do PR)
        │                                              │
        ▼                                              ▼
┌──────────────── CI (.github/workflows/ci.yml) ────────────────┐
│ backend-tests     pytest: CI-01 … CI-08 (Google, DeepSeek e    │
│                   Ollama simulados)                            │
│ live-integrations Ollama real (service container) + DeepSeek   │
│                   real (só com o secret)                       │
│ frontend          npm ci · tsc · vite build · npm audit        │
│ docker-smoke      build das 2 imagens, compose up, portas      │
│ secret-scan       gitleaks no histórico                        │
└────────────────────────────────────────────────────────────────┘
                                                       │ tudo verde
                                                       ▼
┌──────────────── CD (.github/workflows/cd.yml) ─────────────────┐
│ build-push  OIDC → role AWS → push nimb-api e nimb-web no ECR  │
│             (tag = 12 primeiros caracteres do commit + latest) │
│ deploy      SSM → EC2: deploy/deploy.sh <registro> <tag> <sha> │
│             pull · up -d · health · rollback se falhar          │
│             health público · security group · varredura portas │
└────────────────────────────────────────────────────────────────┘
```

**Decisões:**
- **OIDC, sem chave da AWS no GitHub:** o GitHub recebe credenciais temporárias de uma role que só aceita este repositório no ambiente `production`.
- **SSM no lugar de SSH:** o deploy não abre a porta 22 para os IPs do GitHub. O security group pode ficar sem nenhuma regra de entrada.
- **Imagem pronta no ECR:** a EC2 não compila mais (o build do front em `t3.medium` demora e consome memória). O `docker compose up -d --build` local continua funcionando: sem `API_IMAGE`/`WEB_IMAGE` no `deploy/.env`, o compose usa o build.
- **O que não muda no deploy:** `backend/.env`, `deploy/.env` (menos as duas linhas de imagem), o volume `nimb_data` (SQLite + `secret.key`) e o `vector_store/` ficam no servidor.

---

## 1. CI — testes automatizados

Ficam em `backend/tests/`. Rodam sem internet e sem chaves reais: o login do Google, o DeepSeek e o Ollama são simulados. Os testes marcados `live_*` chamam os serviços de verdade e só rodam quando pedidos.

| ID | Tema | Arquivo | O que valida |
|---|---|---|---|
| CI-01 | Login com Google | `test_auth_google.py` | Token com assinatura inválida/expirada → 401; emissor diferente de `accounts.google.com` → 401; e-mail não verificado → 401; sem `GOOGLE_CLIENT_ID` o login fica desativado; o `aud` conferido é o Client ID do sistema. Cookie `HttpOnly`, `SameSite=Strict`, `Path=/api`; "manter conectado" define `Max-Age`; `/me`, logout, cookie forjado; payload inválido não ecoa o token; limite de tentativas por IP (429 com `Retry-After`) |
| CI-02 | E-mail na lista de acesso | `test_allowlist.py` | Fora da lista → 403, sem conta e sem cookie; `ADMIN_EMAILS` entra sempre como admin; liberado entra como `user`; maiúsculas e espaços normalizados; admin inclui/remove pela rota; e-mail inválido → 400; **remover da lista derruba a sessão aberta**; usuário comum não acessa `/api/admin/*`; conta desativada e cadastro desligado → 403 |
| CI-03 | Conexão com o DeepSeek | `test_llm_deepseek.py` | URL `/chat/completions`, `Authorization: Bearer`, mensagem de sistema, `temperature`/`max_tokens`; 401/402/429/5xx viram mensagens claras; timeout e falha de rede; resposta vazia ou fora do formato; sem API key não chama o provedor; provedor desativado. Rotas: só admin gerencia conexões, chave volta mascarada e fica criptografada no banco, "Testar conexão" devolve `ok:false` sem 500, `/api/health` mostra `llm_connected`. **Ao vivo:** `-m live_deepseek` com `DEEPSEEK_API_KEY` |
| CI-04 | Conexão com o Ollama | `test_ollama_embeddings.py` | Modelo instalado → embedding normalizado e `keep_alive` enviado; modelo não baixado → instrução `ollama pull`; Ollama fora do ar → 503; lento → erro de tempo; Ollama antigo usa `/api/embeddings`; erro 500 do Ollama; provedor inválido. **Ao vivo:** `-m live_ollama` (CI: service container com `all-minilm`) |
| CI-05 | Envio e validação de arquivo | `test_book_upload.py` | Upload sem login → 401 **antes de ler o arquivo**; acima do limite → 413; 6ª validação no minuto → 429; sem catálogo → 400; texto, PNG e PDF corrompido → 400 e tentativa registrada; PDF idêntico (SHA-256) libera o livro; outro PDF é recusado e não libera; resposta não vaza hashes nem frases do catálogo; metadados iguais sem as frases de controle não bastam |
| CI-06 | Mensagem no chat/terminal | `test_chat_messages.py` | Sem login → 401; sem livro → 428; sem conexão LLM → 409; prompt vazio, acima de 4000 caracteres ou nível de caos inválido → 422; resposta com livro, página, similaridade e fontes; trecho do livro entra no prompt; pergunta e resposta gravadas na sessão; continuação envia o histórico; fora do tema → 422 sem chamar a LLM e sem gravar; falha da LLM → 502 sem gravar; Regra Nimb exige rolagem válida da mesma pergunta; CRUD de sessões; um usuário não vê a conversa de outro |
| CI-07 | Conexão com a API | `test_api_security.py` | `/api/health` sem dados sensíveis; `/docs`, `/redoc`, `/openapi.json` desligados; **varredura de todas as rotas `/api`: qualquer rota fora da lista pública sem login → 401** (rota nova sem `require_user` quebra o CI); cabeçalhos de segurança; CSRF por `Origin`; CORS só para origens configuradas; corpo > 128 KB → 413; `Content-Length` inválido → 400; erro 500 sem detalhes internos |
| CI-08 | Portas expostas | `test_exposed_ports.py` + `deploy/ci/*.sh` | **Estático (pytest):** só o `web` publica portas, e só 80/443; `api`, `ollama`, `cloudflared` sem porta no host; nada `privileged`/`network_mode: host`; Caddy só encaminha para `api:8000`; API com `EXPOSE 8000` e usuário sem root; `.env.example` com Swagger desligado; `.env`, `.pem`, banco e `vector_store` fora da imagem e do Git. **Em execução (`check-exposed-ports.sh`, job `docker-smoke`):** containers reais, só `web:80`/`web:443` publicadas, 8000 e 11434 fechadas no host, sem cabeçalho `Server`, 413 no Caddy, 401 sem login. **Produção (`check-aws-exposure.sh`, CD):** nenhuma regra `0.0.0.0/0` no security group fora de `EXPECTED_OPEN_PORTS` e varredura de 22/80/443/3000/8000/11434 no IP público |

### Rodar na sua máquina

```powershell
# na raiz, com o .venv
.venv\Scripts\pip install -r backend\requirements-dev.txt
cd backend
..\.venv\Scripts\python -m pytest                       # suíte padrão (~6 s)
..\.venv\Scripts\python -m pytest tests\test_allowlist.py -v
$env:OLLAMA_TEST_MODEL="bge-m3"; ..\.venv\Scripts\python -m pytest -m live_ollama
# DeepSeek real: usa DEEPSEEK_API_KEY, ou o LLM_DEEPSEEK_API do backend\.env (lido pelo python-dotenv)
..\.venv\Scripts\python -m pytest -m live_deepseek
```

No teste ao vivo do DeepSeek: **401** = chave inválida ou revogada; **402** = conta sem saldo. Em caso de falha o teste mostra só a mensagem, sem traceback (que exporia a chave). No secret `DEEPSEEK_API_KEY` do GitHub, cole a chave **sem aspas**.

Resultado esperado em 07/11/2026: `153 passed, 2 deselected`; `live_ollama` passou contra o Ollama local com `bge-m3`.

O `conftest.py` cria banco, `vector_store` e pasta do tesouro numa pasta temporária. O seu `backend/.env` e o `backend/data/nimb.db` não são tocados.

---

## 2. CD — passo a passo da configuração

Substitua nos comandos: `<CONTA>` (ID da conta AWS, 12 dígitos), `<REGIAO>` (ex.: `sa-east-1`), `<INSTANCIA>` (ex.: `i-0abc...`). Comandos com `aws` rodam na sua máquina com um usuário administrador (`aws configure`) ou no **CloudShell** do console.

### Passo 1 — Repositórios no Amazon ECR

```bash
aws ecr create-repository --repository-name nimb-api --region <REGIAO> --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name nimb-web --region <REGIAO> --image-scanning-configuration scanOnPush=true

# guarda só as 15 imagens mais novas de cada repositório (custo)
for repo in nimb-api nimb-web; do
  aws ecr put-lifecycle-policy --repository-name $repo --region <REGIAO> --lifecycle-policy-text \
    '{"rules":[{"rulePriority":1,"description":"ultimas 15","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":15},"action":{"type":"expire"}}]}'
done
```
**Validar:** `aws ecr describe-repositories --region <REGIAO> --query 'repositories[].repositoryUri'` lista os dois.

### Passo 2 — Provedor OIDC do GitHub no IAM (uma vez por conta)

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com
```
**Validar:** `aws iam list-open-id-connect-providers` mostra `token.actions.githubusercontent.com`.

### Passo 3 — Role que o GitHub assume

`trust.json`: só o repositório `radsrei/PAC-Resposta-de-Nimb`, só jobs do ambiente `production`.
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::<CONTA>:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
        "token.actions.githubusercontent.com:sub": "repo:radsrei/PAC-Resposta-de-Nimb:environment:production"
      }
    }
  }]
}
```

`permissions.json`: push nos dois repositórios, comando SSM só na instância do Nimb e leitura para a checagem de portas.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    { "Sid": "EcrLogin", "Effect": "Allow", "Action": "ecr:GetAuthorizationToken", "Resource": "*" },
    { "Sid": "EcrPush", "Effect": "Allow",
      "Action": ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
                 "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"],
      "Resource": ["arn:aws:ecr:<REGIAO>:<CONTA>:repository/nimb-api", "arn:aws:ecr:<REGIAO>:<CONTA>:repository/nimb-web"] },
    { "Sid": "SsmDeploy", "Effect": "Allow", "Action": "ssm:SendCommand",
      "Resource": ["arn:aws:ec2:<REGIAO>:<CONTA>:instance/<INSTANCIA>", "arn:aws:ssm:<REGIAO>::document/AWS-RunShellScript"] },
    { "Sid": "SsmResult", "Effect": "Allow", "Action": "ssm:GetCommandInvocation", "Resource": "*" },
    { "Sid": "PortCheck", "Effect": "Allow", "Action": ["ec2:DescribeInstances", "ec2:DescribeSecurityGroups"], "Resource": "*" }
  ]
}
```

```bash
aws iam create-role --role-name nimb-github-deploy --assume-role-policy-document file://trust.json
aws iam put-role-policy --role-name nimb-github-deploy --policy-name nimb-deploy --policy-document file://permissions.json
aws iam get-role --role-name nimb-github-deploy --query Role.Arn --output text    # anote: AWS_DEPLOY_ROLE_ARN
```

### Passo 4 — Perfil IAM da EC2 (SSM + leitura do ECR)

A instância precisa receber comandos do SSM e baixar as imagens.
```bash
aws iam create-role --role-name nimb-ec2 --assume-role-policy-document \
  '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
aws iam attach-role-policy --role-name nimb-ec2 --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam attach-role-policy --role-name nimb-ec2 --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam create-instance-profile --instance-profile-name nimb-ec2
aws iam add-role-to-instance-profile --instance-profile-name nimb-ec2 --role-name nimb-ec2
aws ec2 associate-iam-instance-profile --instance-id <INSTANCIA> --iam-instance-profile Name=nimb-ec2
```
Se a instância já tiver um perfil, use **EC2 → Actions → Security → Modify IAM role**.

**Validar** (pode levar alguns minutos depois de associar o perfil):
```bash
aws ssm describe-instance-information --region <REGIAO> \
  --query 'InstanceInformationList[].[InstanceId,PingStatus]' --output text     # <INSTANCIA>  Online
```

### Passo 5 — Preparar o servidor (SSH, uma última vez)

```bash
cd ~/PAC-Resposta-de-Nimb
git checkout main && git pull                      # o servidor passa a seguir o main
bash deploy/server-setup.sh                        # agora instala também AWS CLI e SSM Agent
aws sts get-caller-identity                        # deve mostrar a role nimb-ec2 (perfil da instância)
ls backend/.env deploy/.env                        # precisam existir (passo 3 do deploy_ec2_compilado.md)
```

Teste manual do script de deploy com uma imagem já publicada. Antes do primeiro CD, publique uma vez da sua máquina, ou deixe o Passo 8 fazer isso:
```bash
bash deploy/deploy.sh <CONTA>.dkr.ecr.<REGIAO>.amazonaws.com <tag>
grep _IMAGE deploy/.env                            # API_IMAGE=...nimb-api:<tag>  WEB_IMAGE=...nimb-web:<tag>
```
**Validar:** o script termina com `Deploy de <tag> concluído.` e `docker compose ps` mostra `api` healthy.

> O `deploy.sh` usa `git merge --ff-only` para atualizar o código. Se alguém fez commit direto no servidor, o deploy para sem mexer em nada. Resolva com `git status` e `git log`.

### Passo 6 — GitHub: ambiente, secrets e variáveis

**Settings → Environments → New environment → `production`:**
- *Deployment branches and tags:* **Selected branches** → `main`.
- *Required reviewers* (opcional): você mesmo. O deploy espera sua aprovação no Actions.

**Settings → Secrets and variables → Actions:**

| Tipo | Nome | Valor |
|---|---|---|
| Secret (environment `production`) | `AWS_DEPLOY_ROLE_ARN` | ARN do Passo 3 |
| Secret (repositório) | `DEEPSEEK_API_KEY` | opcional: habilita o teste real do DeepSeek no CI (consome poucos tokens) |
| Variable | `AWS_REGION` | ex.: `sa-east-1` |
| Variable | `EC2_INSTANCE_ID` | `<INSTANCIA>` |
| Variable | `PUBLIC_URL` | `https://respostas-nimb.com.br` |
| Variable | `EXPECTED_OPEN_PORTS` | vazio no modo Cloudflare Tunnel; `80 443` no modo B (HTTPS pelo Caddy) |
| Variable | `EC2_APP_DIR` | opcional; padrão `/home/ubuntu/PAC-Resposta-de-Nimb` |

**Settings → Actions → General → Workflow permissions:** *Read repository contents* (o padrão) é suficiente.

### Passo 7 — Proteção dos branches

**Settings → Branches → Add rule** (ou *Rulesets*) para `main` e `develop`:
- [x] Require a pull request before merging
- [x] Require status checks to pass: `API · testes (pytest)`, `Front · tipos e build`, `Docker · build e portas expostas`, `Segurança · segredos no histórico` (e `Integrações · Ollama e DeepSeek reais` se quiser bloquear por ela)
- [x] Require branches to be up to date before merging
- [x] Do not allow bypassing the above settings

Os nomes aparecem na lista depois que o CI rodar pela primeira vez num PR.

### Passo 8 — Primeiro deploy e checklist de validação

1. Abra um PR `develop → main` com estes arquivos. O CI roda no PR e precisa ficar verde.
2. Faça o merge. Em **Actions → CD** aparecem os jobs `ci`, `build-push` e `deploy`.
3. Se configurou revisores, aprove o deploy em *Review deployments*.

| # | Verificação | Onde / como | Esperado |
|---|---|---|---|
| 1 | CI completo antes do deploy | Actions → CD → `ci / …` | todos verdes; o `build-push` só começa depois |
| 2 | OIDC funcionando | log de `configure-aws-credentials` | sem `Not authorized to perform sts:AssumeRoleWithWebIdentity` |
| 3 | Imagens no ECR | `aws ecr list-images --repository-name nimb-api` | tag com os 12 primeiros caracteres do commit + `latest` |
| 4 | Comando SSM | log de "Executar deploy/deploy.sh" | `Status final: Success` e o JSON do health |
| 5 | Imagem certa no servidor | `docker compose ps --format '{{.Service}} {{.Image}}'` (servidor) | `api` e `web` com a tag do commit |
| 6 | Health público | log do "Teste de fumaça" | `"status":"ok"`, `"books_ready": 1`, `"llm_connected": true` |
| 7 | Portas | log do "CI-08 Exposição da EC2" | nenhuma `FALHA`; no modo Tunnel, todas as portas fechadas |
| 8 | Dados preservados | entrar no site | mesmas conversas, livros liberados e lista de acesso de antes |
| 9 | Rollback automático | PR de teste que quebre o `/api/health` (ex.: `raise` no `health()`) num branch, deploy por *Run workflow* | CI barra antes. Se forçado, o `deploy.sh` volta para a tag anterior e o job falha |
| 10 | Sem deploy fora do `main` | *Run workflow* do CD em outro branch | o ambiente `production` recusa (Passo 6) |

### Passo 9 — Rollback manual

Qualquer versão anterior ainda no ECR (as 15 últimas):
```bash
aws ecr describe-images --repository-name nimb-api --query 'sort_by(imageDetails,&imagePushedAt)[-5:].imageTags'   # local
bash deploy/deploy.sh <CONTA>.dkr.ecr.<REGIAO>.amazonaws.com <tag-anterior>                                         # servidor
```
Ou sem SSH: **Actions → CD → Re-run all jobs** num run antigo. Ele refaz o deploy daquele commit. O `merge --ff-only` não volta o código do servidor, só as imagens, e isso basta, porque os arquivos que importam estão dentro delas.

---

## 3. Problemas comuns

| Sintoma | Causa / solução |
|---|---|
| `Not authorized to perform sts:AssumeRoleWithWebIdentity` | o `sub` da trust policy não bate: o job precisa estar no environment `production` e o repositório escrito igual (`radsrei/PAC-Resposta-de-Nimb`) |
| `InvalidInstanceId` no `send-command` | SSM Agent parado ou instância sem o perfil `nimb-ec2` (Passo 4); confira `describe-instance-information` |
| SSM `Failed` com `no basic auth credentials` | perfil da EC2 sem `AmazonEC2ContainerRegistryReadOnly`, ou região do registro diferente da instância |
| `fatal: Not possible to fast-forward` | commit local no servidor; `git log origin/main..HEAD` mostra qual |
| `deploy/.env não existe` | o servidor nunca foi configurado: passo 3 do [deploy_ec2_compilado.md](deploy_ec2_compilado.md) |
| `docker-smoke` falha em "portas inesperadas" | alguém adicionou `ports:` em um serviço; é exatamente o que o teste barra |
| `secret-scan` acusa um segredo antigo | o segredo está no histórico: **revogue a chave** (DeepSeek, Google) e depois limpe o histórico ou registre a exceção em `.gitleaksignore` |
| `live-integrations` lento | o service do Ollama baixa a imagem (~1 GB) a cada run; normal (~2 min) |
| Teste `test_rotas_protegidas_exigem_login` falha numa rota nova | a rota não tem `Depends(require_user)`; se for pública de propósito, inclua em `PUBLIC_ROUTES` no teste |

## 4. Próximos passos sugeridos

- **Testes do front:** Vitest + Testing Library para `ChatInput`, `PdfUploadModal` (limite de 95 MB, só `.pdf`) e `LoginScreen`; Playwright E2E com `VITE_USE_MOCK=true` para o fluxo login → upload → pergunta.
- **Fixar as actions por SHA** (`actions/checkout@<sha>`) e ativar o Dependabot para `github-actions`, `pip` e `npm`.
- **`pip-audit`** no job `backend-tests`, como o `npm audit` do front.
- **Backup antes do deploy:** chamar `deploy/backup.sh` no início do `deploy.sh`.
