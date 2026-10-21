# Projeto Respostas de Nimb

## Start do Projeto

Para subir o sistema localmente (backend FastAPI + tela React + conexão com a LLM), siga o [Setup-Front-Tela.md](Setup-Front-Tela.md). O banco vetorial dos livros é construído à parte: ver [backend/vector_builder/README.md](backend/vector_builder/README.md).

### Requisitos

| Ferramenta | Versão | Para quê | Instalação (Windows) |
|---|---|---|---|
| Python | 3.11+ | API e construtor do banco vetorial | `winget install -e --id Python.Python.3.11` |
| Node.js | 20+ | tela (React/Vite) | `winget install -e --id OpenJS.NodeJS.LTS` |
| Ollama | atual | embeddings (`bge-m3`) do banco vetorial | `winget install -e --id Ollama.Ollama` |
| Conta DeepSeek | — | LLM que responde as perguntas (API key) | `platform.deepseek.com` |
| Conta Google Cloud | — | Client ID do login com Google | ver Setup-Front-Tela.md, seção 3.1 |

O Ollama é opcional se os embeddings forem gerados pelo `sentence-transformers` (instala o PyTorch, cerca de 2 GB).

### Setup automático

Na raiz do projeto, o script cria o `.venv`, instala backend, construtor e front, baixa o modelo no Ollama e cria o `backend/.env`:

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1                     # embeddings pelo Ollama (padrão)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -InstalarOllama
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings local   # sentence-transformers
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings nenhum  # só API e front
```

```bash
# Linux / macOS
bash scripts/setup.sh
bash scripts/setup.sh --embeddings local
```

Depois do script, falta preencher o `GOOGLE_CLIENT_ID` e o `LLM_API_KEY` (chave do DeepSeek) em `backend/.env`.

Para subir no servidor (AWS): [deploy_aws.md](deploy_aws.md).

### Ambiente Python (.venv)

O projeto usa um único ambiente virtual, `.venv`, na raiz do repositório (fora do Git).

### Ambiente Python (.venv)

O projeto usa um único ambiente virtual, `.venv`, na raiz do repositório (fora do Git).

Criar e instalar (primeira vez):
```bash
python3.11 -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt   # tudo: API + RAG + Docling
```

Acessar o ambiente:
```bash
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
```

Para subir só a API, `pip install -r backend/requirements.txt` basta (dependências mínimas).

## Git
Gerar uma nova Branch para envio de mudanças e PR
### Boas Pratias
Gerar Branch com prefixo:
 - Feat/
 - Fix/
 - Docs/


```bash
git status
git batch 
```
#### Criar uma novo branch usando o Develop como base e trocar branch de uso

Puxar e atualizar a branch local
```bash
git checkout develop
git pull origin develop
```

Checkout e switch (comandos para mudança) - Switch comando mais recente
```bash
git checkout -b nome-da-sua-branch develop
```

Subir o commit para o Git
```bash
git push -u origin feat/minha-nova-funcionalidade
```

Atualiza e remove as branchs já apagadas
```bash
git fetch -p
```

Remover as Branchs remotas (Automático)
```bash
git checkout develop
git branch -vv | grep ': gone]' | awk '{print $1}' | xargs git branch -D
```

```bash
# git branch -D feat/conectar-sistema feat/login feat/remover_telas feat/tela-simples 
git branch -D nome-da-branch
```

### Setup para Bitwarden
```bash
#Bitwarden - Cofre
winget install -e --id Bitwarden.CLI
#Biblioteca para script
winget install jq
###
```


### Entrar no cofre BW
```bash
bw login                           # e-mail, senha mestra e código 2FA
export BW_SESSION="$(bw unlock --raw)"
bw sync
bw status | jq -r .status          # esperado: unlocked
```

## Versão para Diagrama
[Git Diagram](https://gitdiagram.com/radsrei/pac-resposta-de-nimb)


## Agenda

### Levantamento

- [Formulário publicado no Reddit](https://forms.cloud.microsoft/r/DxYnjK8A9F)

### Revisão de RAG

na mão, simples

- contexto: conteúdo e tamanho

### Indexing

loaders - text, web, pdf, Docling
Embeddings model, multilingual, context size, vector size
chunkning - chars vs tokens, estratégias, text, tokens, semantic
vector db - memory, local, remoto, cloud

### Retrieval

distance
quantidade
query

### Composição - Tecnologia

Python
[Ollama](https://ollama.com/download/windows)

[irm](https://ollama.com/install.ps1) | iex

Langchain

[Stitch](https://stitch.withgoogle.com/projects/4150170280574443902?pli=1)

### Augmentation

prompt template
context lenght

## Proximas etapas do desenvolvimento
Gerar script para separar e fragmentar livro confore sumário, validar se transformar pdf em MD vai servir ou ajudar na separação das informações
A quebra de partes deve ser genérica e de fácil reaplicação por conta dos livros disintos a serem usados
---
Gerar botão para entrada de livro e validação em lista dos títulos "autorizados' mapeados para serem usados dentro do sistema
---

###
Bibliotecas para ajustes
 - pandoc input.md -o output.pdf
    https://quarto.org/docs/computations/python.html
 - https://quarto.org/docs/computations/python.html
 - pip install docling
    https://docling.ai/



### Evaluation

### Versão final completa

Ramires silva Paes > Avaliçao do trabalho
Observações: O trabalho está acima da média em organização e clareza, com uma base muito boa para evolução. Para chegar em um nível ainda mais alto (quase profissional), faltam: evidências mais concretas (dados, prints, pesquisa) maior profundidade técnica na solução

### Sugestão pares

Bruno Luis Pereira - Sugestão
Melhorar a descrição do problema, quem vai afetar/ajudar e definir melhor o objetivo final


