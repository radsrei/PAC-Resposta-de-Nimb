#!/usr/bin/env bash
# Deploy de uma versão já publicada no Amazon ECR. Roda NA EC2, chamado pelo CD
# (.github/workflows/cd.yml via AWS Systems Manager) ou à mão, como usuário ubuntu:
#
#   bash deploy/deploy.sh <registro-ecr> <tag> [commit]
#   ex.: bash deploy/deploy.sh 123456789012.dkr.ecr.sa-east-1.amazonaws.com 3f2a9c1 3f2a9c1e...
#
# 1. Atualiza o repositório até o commit (docker-compose.yml, scripts);
# 2. Login no ECR (perfil IAM da instância), grava API_IMAGE/WEB_IMAGE no deploy/.env;
# 3. docker compose pull + up -d --no-build;
# 4. Espera o /api/health pelo Caddy. Falhou: volta para as imagens anteriores e sai com erro.
set -euo pipefail

REGISTRY="${1:?informe o registro ECR}"
TAG="${2:?informe a tag da imagem}"
COMMIT="${3:-}"
REGION="${AWS_REGION:-$(echo "$REGISTRY" | cut -d. -f4)}"
HEALTH_URL="${HEALTH_URL:-http://localhost/api/health}"

cd "$(dirname "$0")"
ENV_FILE=".env"
[ -f "$ENV_FILE" ] || { echo "deploy/.env não existe (ver deploy/.env.example)"; exit 1; }
[ -f ../backend/.env ] || { echo "backend/.env não existe (ver backend/.env.example)"; exit 1; }

set_env() {  # set_env CHAVE valor: troca ou acrescenta a linha no deploy/.env
  if grep -q "^$1=" "$ENV_FILE"; then sed -i "s|^$1=.*|$1=$2|" "$ENV_FILE"; else echo "$1=$2" >> "$ENV_FILE"; fi
}
current() { grep "^$1=" "$ENV_FILE" | cut -d= -f2- || true; }

wait_healthy() {
  for _ in $(seq 1 30); do
    if curl -fsS --max-time 5 "$HEALTH_URL" | grep -q '"status":"ok"'; then return 0; fi
    sleep 4
  done
  return 1
}

echo "==> Código"
if [ -n "$COMMIT" ]; then
  git fetch --quiet origin
  git merge --ff-only "$COMMIT"   # falha (sem mexer em nada) se o servidor tiver commits locais
fi

echo "==> Login no ECR ($REGION)"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$REGISTRY"

PREV_API="$(current API_IMAGE)"
PREV_WEB="$(current WEB_IMAGE)"
set_env API_IMAGE "$REGISTRY/nimb-api:$TAG"
set_env WEB_IMAGE "$REGISTRY/nimb-web:$TAG"

echo "==> Subindo $TAG"
docker compose pull api web
docker compose up -d --no-build --remove-orphans

echo "==> Verificando $HEALTH_URL"
if wait_healthy; then
  curl -fsS "$HEALTH_URL"; echo
  docker image prune -f >/dev/null
  echo "Deploy de $TAG concluído."
  exit 0
fi

echo "!! Health check falhou. Logs da API:"
docker compose logs --tail 80 api || true
if [ -n "$PREV_API" ] && [ -n "$PREV_WEB" ]; then
  echo "==> Rollback para $PREV_API"
  set_env API_IMAGE "$PREV_API"
  set_env WEB_IMAGE "$PREV_WEB"
  docker compose up -d --no-build --remove-orphans
  wait_healthy && echo "Rollback concluído (versão anterior no ar)." || echo "!! Rollback também não ficou saudável."
fi
exit 1
