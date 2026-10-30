"""
Criação da aplicação FastAPI: segurança, CORS, banco, handlers de erro e routers.
"""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import llm_controller
from app.core.config import settings
from app.core.exceptions import AppError, TooManyRequestsError
from app.core.middleware import SecurityMiddleware
from app.db.database import init_db
from app.repositories import auth_repository, llm_repository
from app.routers import admin, auth, health, llm, perguntas, rag, sessions, treasure
from app.services import chaos, retrieval, treasure_store

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")
logger = logging.getLogger("nimb")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    llm_repository.encrypt_legacy_keys()
    auth_repository.purge_expired()
    llm_controller.seed_from_env()
    threading.Thread(target=retrieval.warm_up, name="rag-warm-up", daemon=True).start()
    threading.Thread(target=treasure_store.prepare_all, name="treasure-prepare", daemon=True).start()
    if not settings.google_client_id:
        logger.info("GOOGLE_CLIENT_ID não definido: login com Google desativado.")
    for warning in chaos.check_progression():
        logger.warning(warning)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)

app.add_middleware(SecurityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    headers = {"Retry-After": str(exc.retry_after)} if isinstance(exc, TooManyRequestsError) else None
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message}, headers=headers)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError):
    # O FastAPI devolve o valor recebido em cada erro ("input"). Removemos para
    # que senhas e tokens enviados nunca voltem na resposta nem apareçam em logs.
    errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=422, content={"detail": errors})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    # Detalhes (stack trace, SQL, caminhos) ficam só no log do servidor
    logger.exception("Erro não tratado em %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(admin.allowlist_router)
app.include_router(llm.router)
app.include_router(sessions.router)
app.include_router(rag.router)
app.include_router(treasure.router)
app.include_router(perguntas.router)
