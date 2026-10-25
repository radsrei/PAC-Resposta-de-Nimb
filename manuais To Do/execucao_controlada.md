# Execução Controlada — Respostas de Nimb

Sequência para subir o sistema do zero: ambiente, configuração, API, tela e banco vetorial dos livros.
Comandos no PowerShell, a partir da raiz do projeto. Linux/Mac nos comentários.

## 0. Requisitos
```bash
winget install -e --id Python.Python.3.11       # Python 3.11+
winget install -e --id OpenJS.NodeJS.LTS        # Node.js 20+ (tela)
winget install -e --id Ollama.Ollama            # embeddings (bge-m3) do banco vetorial
```

## 1. Setup automático
Cria o `.venv`, instala backend, construtor e front, baixa o modelo no Ollama e gera o `backend/.env`.
```bash
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1                        # embeddings pelo Ollama
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings local      # sentence-transformers (PyTorch ~2 GB)
# Linux/Mac: bash scripts/setup.sh  |  bash scripts/setup.sh --embeddings local
```
Feito o script, pule para o passo 3.

## 2. Setup manual
```bash
python -m venv .venv
.venv\Scripts\activate                                   # Linux/Mac: source .venv/bin/activate
pip install -U pip
pip install -r backend/requirements.txt                  # API
pip install -r backend/vector_builder/requirements.txt   # construtor do banco (Ollama)
# pip install -r backend/vector_builder/requirements-local.txt   # ou sentence-transformers
ollama pull bge-m3                                       # modelo de embeddings
copy backend\.env.example backend\.env                   # Linux/Mac: cp backend/.env.example backend/.env
cd "frontend/V2 - front Studio" && npm ci && cd ../..
```

## 3. Configuração (`backend/.env`)
```ini
GOOGLE_CLIENT_ID=xxxx.apps.googleusercontent.com   # obrigatório: único login do sistema
LLM_DEEPSEEK_API=sk-...                                 # chave do DeepSeek (cria a conexão sozinho)
LLM_MODEL=deepseek-chat                            # ou deepseek-reasoner
EMBEDDING_PROVIDER=ollama                          # ou sentence-transformers
EMBEDDING_MODEL=bge-m3
OLLAMA_URL=http://localhost:11434
```
Client ID: Google Cloud → APIs e serviços → Credenciais → ID do cliente OAuth (Web), origem `http://localhost:3000`.

## 4. Subir a API
```bash
.venv\Scripts\activate
cd backend && python main.py          # porta 8000
CTRL + C                              # Sair
```
### http://localhost:8000/docs

## 5. Subir a tela
Em outro terminal:
```bash
cd "frontend/V2 - front Studio" && npm run dev      # porta 3000
q + ENTER                                            # Sair
```
### http://localhost:3000
Entre com o Google. A primeira conta vira administradora.

## 6. Conectar o DeepSeek
Com `LLM_DEEPSEEK_API` no `.env`, a conexão "DeepSeek (.env)" já nasce ativa.
Pela tela: **Conectar LLM** → API key → modelo (`deepseek-chat` ou `deepseek-reasoner`) → **Conectar LLM** → **Testar**.

## 7. Construir o banco vetorial de um livro
Dentro de `backend/`, com o `.venv` ativo. Feito uma vez por livro, pelo administrador.
```bash
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro" --dry-run   # 1. revisa os trechos
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --title "Meu Livro"             # 2. cadastra + vetoriza
python -m vector_builder check "C:\Downloads\copia.pdf"                                            # 3. testa uma cópia
python -m vector_builder list                                                                      # 4. confere o catálogo
```
Trocar o provedor na execução:
```bash
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --provider ollama --model bge-m3
python -m vector_builder build "C:\Livros\livro.pdf" --id meu-livro --provider sentence-transformers
```
Saída em `vector_store/` (fora do Git). Trocar de modelo exige rodar o `build` de novo.

## 8. Liberar o livro para o usuário
Na tela: **Subir PDF** → escolher o PDF do livro.
O arquivo é comparado com o catálogo e descartado. Se reconhecido, o livro aparece em **Livros Liberados**.

## 9. Encerrar
```bash
CTRL + C                 # API
q + ENTER                # tela
deactivate               # sai do .venv
```

## Problemas rápidos
```bash
Get-NetTCPConnection -LocalPort 8000          # porta 8000 presa: pega o PID
Stop-Process -Id <PID>                        # encerra o backend antigo
ollama serve                                  # "Ollama não respondeu"
ollama pull bge-m3                            # "Modelo não encontrado no Ollama"
```
Caminho longo no Windows (`pip` falhando), PowerShell como administrador:
```bash
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

Servidor (AWS): [deploy_aws.md](deploy_aws.md) · Domínio: [cloudflare_dominio.md](cloudflare_dominio.md) · Detalhes: [Setup-Front-Tela.md](Setup-Front-Tela.md) · [backend/vector_builder/README.md](backend/vector_builder/README.md)
