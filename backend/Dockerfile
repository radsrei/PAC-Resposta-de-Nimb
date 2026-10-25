# API do Respostas de Nimb (FastAPI + uvicorn).
# Build a partir da raiz do projeto: docker compose -f deploy/docker-compose.yml build
# Python 3.14.5: a mesma versão em que o projeto foi testado
FROM python:3.14.5-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Versões diretas no requirements.txt e todas as indiretas travadas no requirements.lock
COPY backend/requirements.txt backend/requirements.lock ./
RUN pip install -r requirements.txt -c requirements.lock

COPY backend/app ./app

# Usuário sem privilégios; /app/data recebe o volume com o SQLite e a secret.key
RUN useradd --uid 10001 --create-home nimb \
    && mkdir -p /app/data /app/vector_store \
    && chown nimb:nimb /app/data
USER nimb

EXPOSE 8000

# 1 worker: o limite de requisições fica em memória e a criação da conexão
# DeepSeek pelo .env roda uma vez só. --proxy-headers: lê o IP real do usuário
# enviado pelo Caddy (a porta 8000 não é publicada fora do Docker).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
