# Front (React/Vite) compilado + Caddy (HTTPS automático e proxy para a API).
# Build a partir da raiz do projeto: docker compose -f deploy/docker-compose.yml build

FROM node:22-alpine AS build
WORKDIR /src
COPY ["frontend/V2 - front Studio/package.json", "frontend/V2 - front Studio/package-lock.json", "./"]
RUN npm ci --no-audit --no-fund
COPY ["frontend/V2 - front Studio/", "./"]
# lint = checagem de tipos (tsc): erro de TypeScript interrompe o deploy
RUN npm run lint && npm run build

FROM caddy:2-alpine
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
