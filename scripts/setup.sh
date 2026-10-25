#!/usr/bin/env bash
# Setup completo do Respostas de Nimb (Linux / macOS): ambiente Python (.venv),
# backend, construtor do banco vetorial (Ollama ou sentence-transformers) e front.
# Pode ser executado de novo: só instala o que estiver faltando.
#
#   bash scripts/setup.sh                       # embeddings pelo Ollama (padrão)
#   bash scripts/setup.sh --embeddings local    # sentence-transformers (PyTorch, ~2 GB)
#   bash scripts/setup.sh --embeddings nenhum --sem-frontend
set -euo pipefail

EMBEDDINGS="ollama"
MODELO_EMBEDDINGS="bge-m3"
SEM_FRONTEND=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --embeddings) EMBEDDINGS="$2"; shift 2 ;;
    --modelo-embeddings) MODELO_EMBEDDINGS="$2"; shift 2 ;;
    --sem-frontend) SEM_FRONTEND=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "Opção desconhecida: $1"; exit 1 ;;
  esac
done
case "$EMBEDDINGS" in ollama|local|nenhum) ;; *) echo "--embeddings deve ser ollama, local ou nenhum"; exit 1 ;; esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
step() { printf '\n\033[36m==> %s\033[0m\n' "$1"; }
ok()   { printf '    \033[32m%s\033[0m\n' "$1"; }
warn() { printf '    \033[33mAVISO: %s\033[0m\n' "$1"; }
fail() { printf '    \033[31mERRO: %s\033[0m\n' "$1"; exit 1; }

step "Python"
PY="$(command -v python3.14 || command -v python3 || true)"
[[ -n "$PY" ]] || fail "Python 3.12+ não encontrado (testado: 3.14)."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' || fail "é preciso Python 3.12 ou mais novo (testado: 3.14)."
ok "$("$PY" --version)"

step "Ambiente virtual (.venv)"
[[ -x .venv/bin/python ]] || { "$PY" -m venv .venv; ok "criado em .venv"; }
VPY=".venv/bin/python"
"$VPY" -m pip install -q -U pip

step "Dependências do backend"
"$VPY" -m pip install -q -r backend/requirements.txt
ok "backend/requirements.txt"

if [[ "$EMBEDDINGS" == "local" ]]; then
  step "Construtor do banco vetorial (sentence-transformers)"
  "$VPY" -m pip install -q -r backend/vector_builder/requirements-local.txt
  ok "sentence-transformers instalado (o modelo baixa na primeira construção)"
elif [[ "$EMBEDDINGS" == "ollama" ]]; then
  step "Construtor do banco vetorial (ollama)"
  "$VPY" -m pip install -q -r backend/vector_builder/requirements.txt
  ok "dependências do construtor instaladas"
fi

# A LLM do chat é o DeepSeek (API externa): o Ollama só gera os embeddings
if [[ "$EMBEDDINGS" == "ollama" ]]; then
  step "Ollama"
  command -v ollama >/dev/null || fail "Ollama não instalado. Linux: curl -fsSL https://ollama.com/install.sh | sh  |  macOS: brew install ollama"
  if ! curl -fs http://localhost:11434/api/tags >/dev/null; then
    ok "iniciando o servidor do Ollama..."
    (ollama serve >/dev/null 2>&1 &)
    for _ in $(seq 20); do curl -fs http://localhost:11434/api/tags >/dev/null && break; sleep 1; done
    curl -fs http://localhost:11434/api/tags >/dev/null || fail "o servidor do Ollama não respondeu em http://localhost:11434"
  fi
  ok "servidor no ar"
  ollama pull "$MODELO_EMBEDDINGS"; ok "modelo de embeddings: $MODELO_EMBEDDINGS"
fi

step "Configuração (backend/.env)"
if [[ ! -f backend/.env ]]; then
  PROVIDER="ollama"; MODEL="$MODELO_EMBEDDINGS"
  [[ "$EMBEDDINGS" == "local" ]] && { PROVIDER="sentence-transformers"; MODEL=""; }
  [[ "$EMBEDDINGS" == "nenhum" ]] && MODEL=""
  sed -e "s/^EMBEDDING_PROVIDER=.*/EMBEDDING_PROVIDER=$PROVIDER/" -e "s/^EMBEDDING_MODEL=.*/EMBEDDING_MODEL=$MODEL/" \
    backend/.env.example > backend/.env
  ok "backend/.env criado a partir do .env.example (EMBEDDING_PROVIDER=$PROVIDER)"
else
  ok "backend/.env já existe (não foi alterado). Confira EMBEDDING_PROVIDER e EMBEDDING_MODEL."
fi
grep -Eq '^GOOGLE_CLIENT_ID=\S' backend/.env || warn "GOOGLE_CLIENT_ID vazio em backend/.env: sem ele ninguém entra no sistema."

if [[ "$SEM_FRONTEND" == 0 ]]; then
  step "Frontend (frontend/V2 - front Studio)"
  if command -v npm >/dev/null; then
    (cd "frontend/V2 - front Studio" && npm ci --no-audit --no-fund)
    ok "npm ci concluído"
  else
    warn "Node.js não encontrado: instale o Node 20+ e rode o script de novo."
  fi
fi

step "Pronto. Próximos passos"
cat <<'EOF'
    1. Ative o ambiente:      source .venv/bin/activate
    2. Suba a API:            cd backend && python main.py
    3. Suba a tela (outro terminal):
                              cd "frontend/V2 - front Studio" && npm run dev
    4. Construa o banco de um livro (dentro de backend/):
                              python -m vector_builder build ~/Livros/livro.pdf --id meu-livro --title "Meu Livro" --dry-run
                              python -m vector_builder build ~/Livros/livro.pdf --id meu-livro --title "Meu Livro"
EOF
