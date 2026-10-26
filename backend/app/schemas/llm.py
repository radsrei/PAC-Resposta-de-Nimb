from typing import Literal

from pydantic import Field

from app.schemas.base import CamelModel

# Único provedor ativo do projeto
ProviderName = Literal["deepseek"]


class LlmProviderOut(CamelModel):
    id: ProviderName
    label: str
    default_model: str
    default_base_url: str
    requires_api_key: bool


class LlmConnectionCreate(CamelModel):
    name: str = Field(..., min_length=1, max_length=80)
    provider: ProviderName
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=500)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    is_active: bool = True


class LlmConnectionUpdate(CamelModel):
    """Atualização parcial. `apiKey` omitido mantém a chave atual; `""` remove."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    provider: ProviderName | None = None
    model: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=300)
    api_key: str | None = Field(default=None, max_length=500)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=128000)
    is_active: bool | None = None


class LlmConnectionOut(CamelModel):
    id: str
    name: str
    provider: str  # str: conexões antigas de outros provedores ainda aparecem na lista
    model: str
    base_url: str | None
    temperature: float | None
    max_tokens: int | None
    is_active: bool
    has_api_key: bool
    api_key_preview: str | None
    created_at: str
    updated_at: str


class LlmTestResult(CamelModel):
    ok: bool
    provider: str
    model: str
    latency_ms: int | None = None
    sample: str | None = None
    error: str | None = None
