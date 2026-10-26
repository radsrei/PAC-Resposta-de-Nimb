"""
Cliente da LLM do projeto: DeepSeek (API compatível com a OpenAI).

Recebe uma conexão cadastrada (model, base_url, api_key, ...) e uma conversa no
formato [{"role": "user" | "assistant", "content": "..."}] e devolve o texto gerado.

Modelos: `deepseek-chat` (resposta direta, padrão) e `deepseek-reasoner`
(raciocínio antes de responder; mais lento, ignora temperatura).

Outros provedores (OpenAI, Anthropic, Gemini, Ollama) foram desativados: o
projeto usa só o DeepSeek. Conexões antigas desses provedores continuam no
banco, mas não respondem; cadastre uma conexão DeepSeek no lugar.
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


DEEPSEEK = ProviderInfo("deepseek", "DeepSeek", "deepseek-chat", "https://api.deepseek.com", True)
PROVIDERS: dict[str, ProviderInfo] = {DEEPSEEK.id: DEEPSEEK}


@dataclass(frozen=True)
class LLMResult:
    text: str
    provider: str
    model: str
    latency_ms: int


Message = dict[str, str]


def generate(connection: dict[str, Any], system: str, messages: list[Message]) -> LLMResult:
    provider = connection["provider"]
    if provider not in PROVIDERS:
        raise LLMError(
            f"O provedor '{provider}' foi desativado: o sistema usa só o DeepSeek. "
            "Cadastre uma conexão DeepSeek em Conectar LLM."
        )

    model = connection.get("model") or DEEPSEEK.default_model
    base_url = (connection.get("base_url") or DEEPSEEK.default_base_url).rstrip("/")
    api_key = connection.get("api_key")
    if not api_key:
        raise LLMError(f"A conexão '{connection['name']}' não possui API key configurada.")

    started = perf_counter()
    text = _call_deepseek(connection, model, base_url, api_key, system, messages)
    if not text.strip():
        raise LLMError("A LLM retornou uma resposta vazia.")

    return LLMResult(
        text=text.strip(),
        provider=provider,
        model=model,
        latency_ms=round((perf_counter() - started) * 1000),
    )


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
def _post_json(url: str, body: dict, headers: dict | None = None) -> dict:
    try:
        response = httpx.post(url, json=body, headers=headers, timeout=settings.llm_timeout)
    except httpx.TimeoutException as exc:
        raise LLMError(f"Tempo esgotado aguardando a LLM ({settings.llm_timeout:.0f}s).") from exc
    except httpx.HTTPError as exc:
        raise LLMError(f"Não foi possível conectar em {url}: {exc}") from exc

    if response.status_code == 401:
        raise LLMError("API key do DeepSeek inválida.")
    if response.status_code == 402:
        raise LLMError("Conta do DeepSeek sem saldo. Recarregue os créditos na plataforma do DeepSeek.")
    if response.status_code == 429:
        raise LLMError("Limite de requisições do DeepSeek atingido. Tente novamente em instantes.")
    if response.status_code >= 400:
        raise LLMError(f"O DeepSeek retornou HTTP {response.status_code}: {_error_detail(response)}")
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


def _call_deepseek(connection, model, base_url, api_key, system, messages) -> str:
    body: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "system", "content": system}, *messages],
    }
    if connection.get("temperature") is not None:
        body["temperature"] = connection["temperature"]
    if connection.get("max_tokens"):
        body["max_tokens"] = connection["max_tokens"]

    data = _post_json(f"{base_url}/chat/completions", body, {"Authorization": f"Bearer {api_key}"})
    try:
        # deepseek-reasoner também devolve `reasoning_content`: só a resposta final é usada
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Formato de resposta inesperado: {str(data)[:300]}") from exc
