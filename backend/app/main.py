"""
Criação da aplicação FastAPI: CORS, banco, handlers de erro e routers.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import llm_controller
from app.core.config import settings
from app.core.exceptions import AppError
from app.db.database import init_db
from app.routers import health, llm, perguntas, rag, sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    llm_controller.seed_from_env()
    yield


app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


app.include_router(health.router)
app.include_router(llm.router)
app.include_router(sessions.router)
app.include_router(rag.router)
app.include_router(perguntas.router)
