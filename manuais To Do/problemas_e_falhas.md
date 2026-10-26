# Problemas e falhas existentes — Respostas de Nimb

Levantamento de 24/10/2026, feito na validação para o deploy na AWS EC2 (branch `feat/deepseek_docker`, commit `db17346`). Cada item traz a evidência, o impacto e a correção sugerida. O passo a passo do deploy está em [deploy_ec2_compilado.md](deploy_ec2_compilado.md).

| Gravidade | Quantidade | Significado |
|---|---|---|
| 🔴 Crítico | 5 | impede o sistema de funcionar online ou expõe o sistema |
| 🟠 Alto | 8 | segurança, dados ou operação; resolver antes de abrir ao público |
| 🟡 Médio | 9 | qualidade das respostas e robustez; resolver logo após subir |
| ⚪ Documentação | 4 | guias desatualizados |

---

## O que foi validado e passou

| Verificação | Resultado |
|---|---|
| Dependências da API para Linux + Python 3.12 (imagem `python:3.12-slim`) | ✅ 95 pacotes com pacote binário disponível (`chromadb` 1.5.9, `onnxruntime` 1.31.0), ~104 MB |
| Compilação do código Python (`app/` e `vector_builder/`) | ✅ sem erros |
| Front (`tsc` + `vite build`) | ✅ |
| API em modo produção (uvicorn real, `ENABLE_DOCS=false`, `COOKIE_SECURE=true`) | ✅ `/docs` e `/openapi.json` 404; sem login 401; outra origem 403; cabeçalhos CSP, HSTS, X-Frame-Options e COOP presentes; aquecimento da busca em 3,8 s |
| Busca (`python -m vector_builder evaluate`, 48 perguntas) | ✅ híbrida: 88% em 1º lugar, 100% no top-5, MRR 0,93 |
| Fluxo completo com o DeepSeek real | ✅ 12/12 (respostas com página; fora do tema 422; sem livro 428) |
| Segredos versionados no Git | ✅ nenhum. O alerta em 4 notebooks da antiga `estrutura-Exemplo/` era falso positivo (imagem em base64); a pasta foi removida |
| `.env`, banco, `secret.key`, `vector_store`, PDFs fora do Git | ✅ |
| Domínio `respostas-nimb.com.br` | ✅ registrado e delegado ao Cloudflare |
| Saldo do DeepSeek | ✅ US$ 5,00 |

**Não foi possível validar nesta máquina:** o build das imagens Docker (não há Docker instalado) e o desempenho do Ollama em CPU (localmente ele roda em GPU).

---

## 🔴 Críticos

### C1. Ollama está num perfil opcional, mas a pergunta depende dele
- **Evidência:** em `deploy/docker-compose.yml`, o serviço `ollama` tem `profiles: ["rag"]` e o `api` não tem `depends_on` nem healthcheck para ele. O `cloudflare_dominio.md` (passo 5) manda usar `COMPOSE_PROFILES=cloudflare`, sem `rag`.
- **Impacto:** desde a decisão D6, toda pergunta passa pela busca nos livros. Sem o Ollama, **todas as perguntas respondem 503**.
- **Correção:** tirar o `profiles` do `ollama`; adicionar healthcheck (`ollama list`) e `depends_on: ollama: condition: service_healthy` no `api`. Opcional: um serviço de inicialização que rode `ollama pull bge-m3`.
- **Contorno já no guia:** `COMPOSE_PROFILES=rag` (modo A) e `cloudflare,rag` (online).

### C2. O código do deploy não está no `main`
- **Evidência:** `git rev-list origin/main..HEAD` = **38 commits**; `origin/develop..HEAD` = 13. O `deploy_aws.md` manda clonar o repositório, o que traz o `main`.
- **Impacto:** o servidor subiria uma versão antiga, sem RAG, DeepSeek, bloqueios nem busca híbrida, e possivelmente sem o kit de deploy.
- **Correção:** PR `feat/deepseek_docker` → `develop` → `main`. Contorno: `git clone -b feat/deepseek_docker`.

### C3. Versões das dependências e das imagens não estão fixas — ✅ resolvido em 25/10/2026

As versões testadas foram fixadas em todos os pontos:

| Onde | Versão |
|---|---|
| Python (`backend/Dockerfile`, `.python-version`, scripts de setup) | **3.14.5** no container (a testada; antes era 3.12). Mínimo local 3.12 |
| `backend/requirements.txt` | 11 dependências diretas com `==` (`fastapi==0.143.3`, `chromadb==1.5.9`…) |
| `backend/requirements.lock` (novo) | 96 pacotes, diretos e indiretos, resolvidos para Linux + Python 3.14. O Dockerfile instala com `-c requirements.lock` |
| `backend/vector_builder/requirements*.txt` | `pymupdf==2.0`, `chromadb==1.5.9` (o mesmo da API), `sentence-transformers==6.1.0` (não testado) |
| Imagens | `python:3.14.5-slim`, `node:24.20.0-alpine`, `caddy:2.11.6-alpine`, `ollama/ollama:0.40.10`, `cloudflare/cloudflared:2026.10.0` (tags conferidas no Docker Hub) |
| Front | `engines.node` `>=24.20.0 <25` no `package.json`; dependências já travadas pelo `package-lock.json` |

**Validação:**
- O ambiente local já atende a todas as versões (`pip install --dry-run`: nada a trocar).
- O lock resolve sem conflito para Linux + Python 3.14 (95 pacotes).
- `tsc` e `vite build` passam, e a API sobe em modo produção.

**Pendente:** o `uvloop` 0.23.0 (só existe no Linux) entra no container sem ter sido testado localmente. O build real das imagens continua no C5.

**Para atualizar uma versão:** mudar no `requirements.txt`, testar localmente e gerar o lock de novo com `pip download -r requirements.txt -c <freeze testado> --platform manylinux_2_28_x86_64 --python-version 3.14 --only-binary=:all:`, acrescentando o `uvloop`.

<details><summary>Descrição original do problema</summary>

- **Evidência:**
  - `backend/requirements.txt` não tem versões. Resolvendo hoje para o servidor, 9 pacotes ficam diferentes dos testados: `fastapi` 0.143.3 → **0.162.0**, `starlette` 1.8.0 → 1.10.0, `httpx2` 2.13.1 → 2.16.0, `huggingface_hub` 2.2.0 → 2.3.0, `multidict`, `websockets`, `certifi`, `pycparser`, `httpcore2`.
  - As imagens `ollama/ollama:latest` e `cloudflare/cloudflared:latest` também não têm versão fixa.
- **Impacto:** o servidor roda versões nunca testadas. O `chromadb` grava o banco num formato que pode mudar entre versões: um `chromadb` mais novo no servidor pode não abrir, ou migrar, o banco construído localmente com a 1.5.9.
- **Correção:**
  - Gerar `backend/requirements.lock` a partir do ambiente testado, com o `chromadb==1.5.9` fixo, e usar no `Dockerfile`.
  - Fixar as tags das imagens.
  - O mesmo lock vale para `vector_builder/requirements.txt`, já que o banco é construído localmente.

</details>

### C4. O primeiro login vira administrador — ✅ resolvido em 25/10/2026
- **Feito:**
  - O padrão do código passou a ser `FIRST_USER_IS_ADMIN=false` (`config.py` e `.env.example`).
  - O administrador é definido **só** por `ADMIN_EMAILS` no `.env`, fora do Git, porque o repositório é público.
  - O `backend/.env` local tem o e-mail do administrador definido em 25/10/2026; no servidor, repita no `.env` de lá.
  - Novidade: o e-mail de `ADMIN_EMAILS` vira administrador também no login de uma conta que já existe, e não só na criação.
- **Teste (login do Google simulado, banco temporário):** desconhecido entrando primeiro → `user`; e-mail administrador → `admin`; a mesma conta rebaixada → volta a `admin` no próximo login.

<details><summary>Descrição original do problema</summary>

- **Evidência:** `auth_controller._role_for_new_user` dá papel de admin quando `FIRST_USER_IS_ADMIN=true` (padrão) e o banco não tem usuários. Com `REGISTRATION_ENABLED=true`, qualquer conta Google cria usuário.
- **Impacto:** com o domínio público, quem entrar primeiro no servidor novo (antes de você) vira administrador e passa a gerenciar a conexão LLM e os usuários.
- **Correção:** `FIRST_USER_IS_ADMIN=false` + `ADMIN_EMAILS` no servidor (já no guia). Melhor ainda: mudar o padrão do código para `false`.

</details>

### C5. As imagens Docker nunca foram construídas nem testadas
- **Evidência:** não há Docker nesta máquina. O build do `api` (agora com `chromadb`/`onnxruntime`) e do `web`, o funcionamento do RAG dentro dos containers e o Ollama em CPU nunca rodaram.
- **Impacto:** podem aparecer falhas que só existem no Linux, como falta de biblioteca de sistema, memória ou permissão no volume.
- **Correção:** fazer o primeiro deploy no **modo A** (túnel SSH) e passar pelo checklist do passo 6 do guia antes de abrir o domínio. Melhor ainda: CI no GitHub Actions construindo as imagens a cada PR (ver A5).

---

## 🟠 Altos

### A1. Atualizar o `vector_store` no servidor falha ou acumula lixo
- **Evidência:** depois do `chown 10001`, o usuário `ubuntu` não sobrescreve a pasta com `scp`, o que dá *permission denied*. Além disso, o `scp` não apaga as versões antigas `chroma-<data>`, que se acumulam no disco.
- **Correção:** o procedimento "apagar → enviar → chown → restart" já está no guia (passo 10). Melhor: um script `deploy/update_books.sh` ou o envio por `rsync --delete` a partir do WSL.

### A2. A instância indicada no guia antigo não comporta o sistema
- **Evidência:** o `deploy_aws.md` sugere `t3.small` (2 GB). Agora o servidor precisa de Ollama (bge-m3 ~1,2 GB), da API com Chroma e do build do front.
- **Impacto:** falta de memória (*OOM*) no build ou no upload de PDF de 89 MB.
- **Correção:** `t3.medium` (4 GB) e disco de 30 GB (já no guia). Os créditos de CPU do `t3` são limitados: medir o embedding em CPU no passo 6 e, se a pergunta ficar lenta, avaliar uma instância `c`/`m` ou o modo *unlimited*.

### A3. Dados pessoais num repositório público — ✅ resolvido na versão atual em 25/10/2026 (resta o histórico)
- **Regra definida:** o repositório **continua público**.
- **Feito:**
  - O `convert_xml.py` não era usado pelo sistema. Foi renomeado para `convert_xml_OLD.py`, com o e-mail trocado por uma regra genérica, e depois removido junto com a pasta `Convert_file_OLD/`.
  - As 6 imagens de `PAC-7+8/` foram apagadas.
  - Nenhum arquivo versionado contém mais o e-mail.
- **Restante:**
  - O e-mail e as imagens continuam no **histórico do Git**, visível num repositório público. Removê-los exige reescrever o histórico (`git filter-repo`) e forçar o push em todos os branches, o que afeta os clones do grupo. A decisão é do grupo.
  - Ficou na pasta o `PAC-7+8/Presença em Aula/Encontro 2-- 21-09-26.txt` (13 linhas, lista de presença). Avaliar se pode ser apagado.

<details><summary>Descrição original do problema</summary>

- **Evidência:** o repositório `radsrei/PAC-Resposta-de-Nimb` é **público** (API do GitHub respondeu 200).
  - `Convert_file/convert_xml.py`, linha 231, contém o **e-mail do comprador do livro** (filtro de marca d'água).
  - `PAC-7+8/` tem imagens com nomes de colegas e registros de presença.
- **Impacto:** exposição de dados pessoais (LGPD) e rastreio da cópia licenciada do livro.
- **Correção:** trocar o filtro do script pela regra genérica de e-mail (como no `extract.py`), mover `PAC-7+8/` para fora do repositório e avaliar limpar o histórico (`git filter-repo`) ou tornar o repositório privado.

</details>

### A4. Decisões D4 (direitos do livro) e D5 (quem acessa) em aberto
- **Evidência:** o `vector_store/` tem o texto completo do Livro Básico. Hoje, qualquer conta Google pode se cadastrar, e quem tiver uma cópia do PDF libera o acesso.
- **Impacto:** risco legal ao publicar o app no Google (sair do modo *Teste*).
- **Correção:** decidir antes do passo 8 do guia. Se o uso for restrito, `REGISTRATION_ENABLED=false` com cadastro dos e-mails, ou Cloudflare Access (até 50 usuários grátis).

### A5. Não há testes automatizados nem CI
- **Evidência:** não existe `backend/tests/` nem `.github/workflows/`. Todos os testes desta fase (E1/E2, RAG ponta a ponta, DeepSeek, uvicorn em produção) estão em scripts temporários fora do projeto.
- **Impacto:** regressões passam sem aviso, como os bloqueios 428/422, a citação de página e a busca.
- **Correção:** levar os cenários para `pytest`, com LLM simulada e o banco do livro ou um livro de teste pequeno; GitHub Actions rodando `pytest`, `npm run lint && npm run build` e `docker build`.

### A6. Backup incompleto e não agendado
- **Evidência:** o `backup.sh` existe, mas não há cron configurado nem snapshot do EBS. O backup não inclui o `vector_store` (só reconstruível com o PDF, que existe apenas na sua máquina) nem o modelo do Ollama.
- **Correção:** cron diário, política de snapshot e cópia do `vector_store` num local seguro (S3 privado).

### A7. Ollama sem healthcheck e modelo baixado à mão
- **Evidência:** o `pull` do `bge-m3` é manual. O aquecimento da API pode rodar antes do Ollama estar pronto, e aí a 1ª pergunta fica lenta. Se o volume `ollama_models` se perder, todas as perguntas dão 503 até um novo `pull`.
- **Correção:** junto com o C1, healthcheck + `depends_on` + `pull` automático na inicialização.

### A8. Leitura de PDF sem limite de tempo ou memória (P1.3)
- **Evidência:** `book_fingerprint.py` lê o PDF inteiro em memória (até 95 MB) sem tempo limite. A API roda com 1 worker.
- **Impacto:** um PDF malicioso ou muito pesado ocupa CPU e memória da única instância. O rate limit (5 uploads/min por IP) reduz, mas não elimina.
- **Correção:** ler o PDF num processo separado com tempo e memória limitados.

---

## 🟡 Médios

### M1. Metade da recusa "fora do tema" depende da LLM
- **Evidência:** a melhor similaridade das perguntas do livro vai de 0,47 a 0,76, e a das fora do tema de 0,34 a 0,53. As faixas se sobrepõem, então com o mínimo de 0,45 metade das perguntas fora do tema chega à LLM, que recusa pelo prompt.
- **Impacto:** custo de LLM nessas perguntas e risco de a LLM não recusar algum caso novo.
- **Correção:** ampliar o conjunto de avaliação e recalibrar; avaliar um classificador barato de escopo antes da LLM.

### M2. Conjunto de avaliação pequeno e otimista
- **Evidência:** 48 perguntas escritas a partir dos próprios trechos do livro, que repetem as palavras dele. A margem da calibração é pequena (mínimo de 0,45 contra 0,469 da pergunta do grifo).
- **Correção:** incluir perguntas reais de jogadores (formulário do Reddit em `docs/`) e avaliar a **resposta final** com especialistas (RNF04 do RFC: 85%).

### M3. Perguntas que dependem de dois trechos
- **Evidência:** "dano **e custo** da Bola de Fogo" traz a magia, mas não a regra de custo por círculo (p. 170). A LLM diz que o custo não está no trecho.
- **Correção:** buscar também pelos termos de regra relacionados, aumentar o `RAG_TOP_K` para essas perguntas, ou dividir a pergunta em partes.

### M4. Tabelas aparecem em posições baixas na busca
- **Evidência:** a `Tabela 3-1: Dinheiro Inicial` aparece em 3º lugar com a busca híbrida. Antes, não aparecia.
- **Correção:** texto de embedding próprio para as tabelas (legenda + assunto) e reconstrução do banco.

### M5. Validação do livro não foi calibrada com outra cópia (P0.7)
- **Evidência:** 3 das 8 frases de controle são frágeis (`"Capítulo Um Golpe Pessoal…"`, `"peculiari dades"`, `"2D Na rolagem…"`). Cada comprador tem uma marca d'água diferente, então o SHA-256 nunca coincide. Só foi testada uma cópia regravada do mesmo arquivo.
- **Impacto:** o PDF de outro comprador pode ser recusado.
- **Correção:** escolher as frases à mão (`--probe`) e rodar `check` com a cópia de outro comprador.

### M6. O front nunca foi testado num navegador real (P0.2)
- **Evidência:** as mudanças de tela (bloqueio sem livro, avisos 428/422, fonte no histórico) passaram só pelo `tsc` e pelo `vite build`.
- **Correção:** passo 6 do guia, no modo A.

### M7. Configurações com padrão inseguro ou divergente
- **Evidência:**
  - `ENABLE_DOCS` tem padrão `true` no código.
  - `LLM_TIMEOUT` local é 60 e no servidor deve ser 90.
  - O rate limit fica em memória, por processo (P1.7).
  - Não há resposta em streaming: respostas longas se aproximam do limite de 100 s do Cloudflare e ficam longe da meta de 3–5 s do RFC.
- **Correção:** padrões seguros no `config.py` (`ENABLE_DOCS=false`, `FIRST_USER_IS_ADMIN=false`) e streaming da resposta como evolução.

### M8. Limite de upload próximo do tamanho do livro
- **Evidência:** o PDF do Livro Básico tem 89 MB e o limite é 95 MB (Cloudflare grátis: 100 MB).
- **Correção:** para outros livros maiores, comprimir o PDF, enviar em partes ou validar só uma amostra de páginas no navegador.

### M9. Código legado no repositório (P2.3/P2.4)
- **Evidência:** `backend/RAG_*`, `Convert_file/`, `deepseek/`, `estrutura-Exemplo/`, `docs/nimb_prototipo/`, a rota `/api/perguntas` e o `requirements.txt` da raiz (Docling, LangChain).
- **Correção:** limpeza, para reduzir confusão e superfície de ataque.
- **Feito em 25/10/2026:** verificação de uso das pastas `Convert_file`, `estrutura-Exemplo` e `deepseek`.
  - Nenhum arquivo é importado ou executado pelo sistema (API, construtor, front, Docker e scripts). Por isso nada foi integrado.
  - O que esses códigos faziam já existe no sistema atual:
    - conversão do PDF e análise tipográfica → `backend/vector_builder`;
    - cliente DeepSeek e RAG → `app/services/llm_client.py` e `retrieval.py`.
  - Pastas e códigos (`.py`, `.ipynb`) receberam o sufixo `_OLD`.
  - Em seguida as três pastas `_OLD` foram **apagadas** (inclusive o `tormenta20.xml` e o `.venv` locais). As regras delas no `.gitignore` e no `.dockerignore` foram retiradas e as referências nos documentos, atualizadas.
- **Pendente:** `backend/RAG_*`, `docs/nimb_prototipo/`, a rota `/api/perguntas` e o `requirements.txt` da raiz. O conteúdo apagado continua acessível no histórico do Git (ver A3).

---

## ⚪ Documentação desatualizada

| # | Arquivo | Problema |
|---|---|---|
| D1 | `deploy_aws.md` | diz que as perguntas são respondidas "ainda sem consultar o texto do livro"; sugere `t3.small`; manda subir o Ollama (passo 3) antes de criar o `.env` (passo 4); não traz `FIRST_USER_IS_ADMIN=false` nem `OLLAMA_URL` na tabela. **Substituído pelo `deploy_ec2_compilado.md`** |
| D2 | `cloudflare_dominio.md` | `COMPOSE_PROFILES=cloudflare` sem `rag` (causa o C1); passos 1 e 2 já concluídos |
| D3 | `resp.md` | descreve uma versão antiga (vários provedores, chaves em texto puro, upload como *stub*): arquivar ou apagar |
| D4 | `proximos_passos.md` | P0.3 ainda lista "fixar versões" (C3) e P0.8 o agendamento do backup (A6); tabela do item 1 a atualizar depois do deploy |

---

## Ordem sugerida para resolver

Resolvidos em 25/10/2026: **C3**, **C4** e **A3** (versão atual; o histórico fica para decisão do grupo).

```text
Antes do deploy        C2 (merge no main) → C1/A7 (Ollama obrigatório no compose)
No deploy (modo A)     C5 + M6 (build e teste no navegador) → A2 (medir memória e CPU)
Antes de abrir         A3 (dados pessoais no repositório) → A4 (D4/D5) → A6 (backup) → A1 (script de livros)
Logo depois            A5 (testes + CI) → A8 → M1–M5 (qualidade da busca e da validação) → M7–M9
```
