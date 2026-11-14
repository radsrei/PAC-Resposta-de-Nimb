#!/usr/bin/env bash
# CI-08 (em execução): com os containers de pé (docker compose up -d em deploy/),
# confere que só o Caddy responde no host e que API/Ollama ficam na rede interna.
#
#   bash deploy/ci/check-exposed-ports.sh
set -euo pipefail
cd "$(dirname "$0")/.."

fail=0
ok()   { echo "  ok    $*"; }
bad()  { echo "  FALHA $*"; fail=1; }

echo "==> Aguardando o /api/health pelo Caddy (porta 80)"
for _ in $(seq 1 40); do
  curl -fsS --max-time 3 http://localhost/api/health >/dev/null 2>&1 && break
  sleep 3
done
curl -fsS --max-time 5 http://localhost/api/health | grep -q '"status":"ok"' \
  && ok "health respondeu pelo Caddy" || bad "health não respondeu pelo Caddy"

echo "==> Portas publicadas no host (esperado: só web 80 e 443)"
published="$(docker compose ps --format json \
  | jq -s -r 'if (.[0]|type)=="array" then .[0] else . end
              | .[] | .Service as $s | (.Publishers // [])[]
              | select(.PublishedPort > 0) | "\($s):\(.PublishedPort)"' \
  | sort -u | tr '\n' ' ')"
echo "  publicadas: ${published:-nenhuma}"
[ "$published" = "web:443 web:80 " ] && ok "somente web:80 e web:443" || bad "portas inesperadas: $published"

echo "==> Portas internas não podem responder no host"
for port in 8000 11434; do
  if curl -s -o /dev/null --max-time 3 "http://localhost:$port/"; then
    bad "porta $port acessível pelo host"
  else
    ok "porta $port fechada no host"
  fi
done

echo "==> Proteções do Caddy"
headers="$(curl -sS -D - -o /dev/null http://localhost/)"
echo "$headers" | grep -qi '^x-content-type-options: nosniff' && ok "nosniff" || bad "sem X-Content-Type-Options"
echo "$headers" | grep -qi '^server:' && bad "cabeçalho Server exposto" || ok "sem cabeçalho Server"

code="$(head -c 200000 /dev/zero | tr '\0' ' ' \
  | curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
         --data-binary @- http://localhost/api/auth/google)"
[ "$code" = "413" ] && ok "corpo > 128 KB recusado (413)" || bad "corpo grande respondeu $code (esperado 413)"

code="$(curl -s -o /dev/null -w '%{http_code}' http://localhost/api/auth/me)"
[ "$code" = "401" ] && ok "/api/auth/me sem login = 401" || bad "/api/auth/me sem login respondeu $code"

exit $fail
