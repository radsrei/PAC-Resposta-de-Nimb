"""
Cliente de LLM multi-provedor.

Recebe uma conexão cadastrada (provider, model, base_url, api_key, ...) e uma
conversa no formato [{"role": "user" | "assistant", "content": "..."}] e
devolve o texto gerado.

Provedores suportados:
- openai / deepseek / openai_compatible -> endpoint /chat/completions
- ollama                                 -> endpoint /api/chat (LLM local)
- gemini                                 -> endpoint generateContent
- anthropic                              -> SDK oficial `anthropic`
"""

from dataclasses import dataclass
from time import perf_counter
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import LLMError


@dataclass(frozen=True)
class ProviderInfo:
    id: str
    label: str
    default_model: str
    default_base_url: str
    requires_api_key: bool


PROVIDERS: dict[str, ProviderInfo] = {
    p.id: p
    for p in (
        ProviderInfo("openai", "OpenAI (GPT)", "gpt-4o-mini", "https://api.openai.com/v1", True),
        ProviderInfo("anthropic", "Anthropic (Claude)", "claude-opus-5-5", "https://api.anthropic.com", True),
        ProviderInfo("gemini", "Google Gemini", "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta", True),
        ProviderInfo("deepseek", "DeepSeek", "deepseek-chat", "https://api.deepseek.com", True),
        ProviderInfo("ollama", "Ollama (local)", "llama3.1", "http://localhost:11434", False),
        ProviderInfo("openai_compatible", "Compatível com OpenAI", "", "http://localhost:1234/v1", False),
    )
}


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int


Message = dict[str, str]


def generate(connection: dict[str, Any], system: str, messages: list[Message]) -> LLMResult:
    provider = connection["provider"]
    info = PROVIDERS.get(provider)
    if info is None:
        raise LLMError(f"Provedor de LLM desconhecido: {provider}")

    model = connection.get("model") or info.default_model
    base_url = (connection.get("base_url") or info.default_base_url).rstrip("/")
    api_key = connection.get("api_key")
    if info.requires_api_key and not api_key:
        raise LLMError(f"A conexão '{connection['name']}' não possui API key configurada.")
    if not model:
        raise LLMError(f"A conexão '{connection['name']}' não possui modelo configurado.")

    started = perf_counter()
    if provider == "anthropic":
        text = _call_anthropic(connection, model, base_url, api_key, system, messages)
    elif provider == "gemini":
        text = _call_gemini(connection, model, base_url, api_key, system, messages)
    elif provider == "ollama":
        text = _call_ollama(connection, model, base_url, system, messages)
    else:
        text = _call_openai_compatible(connection, model, base_url, api_key, system, messages)

    if not text.strip():
        raise LLMError("A LLM retornou uma resposta vazia.")

    return LLMResult(
        text=text.strip(),
        provider=provider,
        model=model,
        latency_ms=round((perf_counter() - started) * 1000),
    )


# --------------------------------------------------------------------------
# HTTP helpers
# --------------------------------------------------------------------------
def _post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=settings.llm_timeout)
    except httpx.TimeoutException as exc:
        raise LLMError(f"Tempo esgotado aguardando a LLM ({settings.llm_timeout:.0f}s).") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Não foi possível conectar em {url}: {exc}") from exc

    if response.status_code >= 400:
        raise LLMError(f"A LLM retornou HTTP {response.status_code}: {_error_detail(response)}")
    try:
        return response.json()
    except ValueError as exc:
        raise LLMError("Resposta da LLM não está em JSON válido.") from exc


def _error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text[:300]
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error)[:300]
    if error:
        return str(error)[:300]
    return str(data)[:300]


# --------------------------------------------------------------------------
# Provedores
# --------------------------------------------------------------------------
def _call_openai_compatible(connection, model, base_url, api_key, system, messages) -> str:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    if connection.get("temperature") is not None:
        body["temperature"] = connection["temperature"]
    if connection.get("max_tokens"):
        # A OpenAI usa `max_completion_tokens` nos modelos atuais
        key = "max_completion_tokens" if connection["provider"] == "openai" else "max_tokens"
        body[key] = connection["max_tokens"]

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else None
    data = _post_json(f"{base_url}/chat/completions", body, headers)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Formato de resposta inesperado: {str(data)[:300]}") from exc


def _call_ollama(connection, model, base_url, system, messages) -> str:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": False,
    }
    options = {}
    if connection.get("temperature") is not None:
        options["temperature"] = connection["temperature"]
    if connection.get("max_tokens"):
        options["num_predict"] = connection["max_tokens"]
    if options:
        body["options"] = options

    data = _post_json(f"{base_url}/api/chat", body)
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise LLMError(f"Formato de resposta inesperado: {str(data)[:300]}") from exc


def _call_gemini(connection, model, base_url, api_key, system, messages) -> str:
    body: dict[str, Any] = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
        ],
    }
    generation_config = {}
    if connection.get("temperature") is not None:
        generation_config["temperature"] = connection["temperature"]
    if connection.get("max_tokens"):
        generation_config["maxOutputTokens"] = connection["max_tokens"]
    if generation_config:
        body["generationConfig"] = generation_config

    data = _post_json(
        f"{base_url}/models/{model}:generateContent",
        body,
        headers={"x-goog-api-key": api_key},
    )
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError) as exc:
        reason = (data.get("promptFeedback") or {}).get("blockReason") if isinstance(data, dict) else None
        if reason:
            raise LLMError(f"O Gemini bloqueou a pergunta ({reason}).") from exc
        raise LLMError(f"Formato de resposta inesperado: {str(data)[:300]}") from exc


def _call_anthropic(connection, model, base_url, api_key, system, messages) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise LLMError("Pacote 'anthropic' não instalado. Rode: pip install anthropic") from exc

    client = anthropic.Anthropic(
        api_key=api_key,
        base_url=base_url,
        timeout=settings.llm_timeout,
        max_retries=1,
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": connection.get("max_tokens") or 16000,
        "system": system,
        "messages": messages,
    }
    # Os modelos Claude 5.x não aceitam `temperature`; só envia se configurado.
    if connection.get("temperature") is not None:
        kwargs["temperature"] = connection["temperature"]

    try:
        response = client.messages.create(**kwargs)
    except anthropic.AuthenticationError as exc:
        raise LLMError("API key da Anthropic inválida.") from exc
    except anthropic.NotFoundError as exc:
        raise LLMError(f"Modelo '{model}' não encontrado na Anthropic.") from exc
    except anthropic.RateLimitError as exc:
        raise LLMError("Limite de requisições da Anthropic atingido. Tente novamente em instantes.") from exc
    except anthropic.APIStatusError as exc:
        raise LLMError(f"A Anthropic retornou HTTP {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise LLMError(f"Não foi possível conectar à Anthropic: {exc}") from exc

    if response.stop_reason == "refusal":
        raise LLMError("O modelo recusou responder a esta pergunta.")
    return "".join(block.text for block in response.content if block.type == "text")
