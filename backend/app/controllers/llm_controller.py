"""Regras de negócio das conexões de LLM (CRUD, ativação e teste)."""

from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError, LLMError, NotFoundError
from app.repositories import llm_repository
from app.schemas.llm import LlmConnectionCreate, LlmConnectionUpdate
from app.services import llm_client


def _mask_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 8:
        return "••••"
    return f"{api_key[:4]}••••{api_key[-4:]}"


def to_public(connection: dict[str, Any]) -> dict[str, Any]:
    """Remove a API key do retorno, expondo só se existe e uma prévia mascarada."""
    data = {k: v for k, v in connection.items() if k != "api_key"}
    data["has_api_key"] = bool(connection.get("api_key"))
    data["api_key_preview"] = _mask_key(connection.get("api_key"))
    return data


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def list_providers() -> list[dict[str, Any]]:
    return [vars(p) for p in llm_client.PROVIDERS.values()]


def list_connections() -> list[dict[str, Any]]:
    return [to_public(c) for c in llm_repository.list_all()]


def get_connection_or_404(connection_id: str) -> dict[str, Any]:
    connection = llm_repository.get(connection_id)
    if connection is None:
        raise NotFoundError(f"Conexão LLM '{connection_id}' não encontrada.")
    return connection


def get_active_connection() -> dict[str, Any] | None:
    return llm_repository.get_active()


def create_connection(payload: LlmConnectionCreate) -> dict[str, Any]:
    info = llm_client.PROVIDERS[payload.provider]
    data = payload.model_dump()
    data["name"] = data["name"].strip()
    data["model"] = _clean(data["model"]) or info.default_model
    data["base_url"] = _clean(data["base_url"])
    data["api_key"] = _clean(data["api_key"])
    if not data["model"]:
        raise AppError("Informe o modelo da LLM.")
    if info.requires_api_key and not data["api_key"]:
        raise AppError(f"O provedor {info.label} exige uma API key.")
    # A primeira conexão cadastrada já nasce ativa
    if llm_repository.count() == 0:
        data["is_active"] = True
    return to_public(llm_repository.create(data))


def update_connection(connection_id: str, payload: LlmConnectionUpdate) -> dict[str, Any]:
    current = get_connection_or_404(connection_id)
    changes = payload.model_dump(exclude_unset=True)
    for key in ("model", "base_url", "api_key"):
        if key in changes:
            changes[key] = _clean(changes[key])
    if "name" in changes and changes["name"]:
        changes["name"] = changes["name"].strip()
    if changes.get("is_active") is False:
        changes.pop("is_active")  # desativar = ativar outra conexão

    provider = changes.get("provider") or current["provider"]
    info = llm_client.PROVIDERS.get(provider)
    if info is None:
        raise AppError("Esta conexão usa um provedor desativado. Cadastre uma conexão DeepSeek.")
    if "model" in changes and not changes["model"]:
        changes["model"] = info.default_model
    final_key = changes["api_key"] if "api_key" in changes else current["api_key"]
    if info.requires_api_key and not final_key:
        raise AppError(f"O provedor {info.label} exige uma API key.")

    return to_public(llm_repository.update(connection_id, changes))


def activate_connection(connection_id: str) -> dict[str, Any]:
    connection = get_connection_or_404(connection_id)
    if connection["provider"] not in llm_client.PROVIDERS:
        raise AppError("Esta conexão usa um provedor desativado. Cadastre uma conexão DeepSeek.")
    return to_public(llm_repository.update(connection_id, {"is_active": True}))


def delete_connection(connection_id: str) -> None:
    connection = get_connection_or_404(connection_id)
    llm_repository.delete(connection_id)
    # Se a conexão ativa foi removida, ativa a mais recente restante
    if connection["is_active"]:
        remaining = llm_repository.list_all()
        if remaining:
            llm_repository.update(remaining[0]["id"], {"is_active": True})


def test_connection(connection_id: str) -> dict[str, Any]:
    connection = get_connection_or_404(connection_id)
    model = connection["model"]
    try:
        result = llm_client.generate(
            connection,
            system="Você é um verificador de conexão. Responda de forma curtíssima.",
            messages=[{"role": "user", "content": "Responda apenas: Conexão estabelecida."}],
        )
    except LLMError as exc:
        return {"ok": False, "provider": connection["provider"], "model": model, "error": exc.message}
    return {
        "ok": True,
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "sample": result.text[:200],
    }


def seed_from_env() -> None:
    """Cria uma conexão a partir do `.env` se nenhuma estiver cadastrada."""
    provider = settings.default_llm_provider
    if not provider or provider not in llm_client.PROVIDERS or llm_repository.count() > 0:
        return
    info = llm_client.PROVIDERS[provider]
    if info.requires_api_key and not settings.default_llm_api_key:
        return
    llm_repository.create({
        "name": f"{info.label} (.env)",
        "provider": provider,
        "model": settings.default_llm_model or info.default_model,
        "base_url": settings.default_llm_base_url,
        "api_key": settings.default_llm_api_key,
        "temperature": None,
        "max_tokens": None,
        "is_active": True,
    })
