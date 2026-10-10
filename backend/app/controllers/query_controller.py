"""
Fluxo de pergunta -> LLM -> resposta.

1. Resolve a conexão LLM (a informada ou a ativa);
2. Recupera o histórico recente da sessão (se houver);
3. Monta o prompt de sistema (persona Nimb + nível de caos);
4. Chama a LLM;
5. Persiste pergunta e resposta na sessão e devolve o resultado.

Ponto de extensão do RAG (próxima etapa): entre os passos 2 e 3, recuperar os
trechos dos livros no vector DB e incluí-los no prompt.
"""

from typing import Any

from app.core.config import settings
from app.core.exceptions import NoActiveConnectionError
from app.repositories import llm_repository, session_repository
from app.services import llm_client
from app.services.prompts import build_system_prompt
from app.controllers.session_controller import get_session_or_404


def _resolve_connection(connection_id: str | None) -> dict[str, Any]:
    if connection_id:
        connection = llm_repository.get(connection_id)
        if connection is None:
            raise NoActiveConnectionError(f"Conexão LLM '{connection_id}' não encontrada.")
        return connection
    connection = llm_repository.get_active()
    if connection is None:
        raise NoActiveConnectionError()
    return connection


def _session_title(prompt: str) -> str:
    title = " ".join(prompt.split())
    return title if len(title) <= 60 else title[:57] + "..."


def ask(
    prompt: str,
    chaos_level: int = 50,
    session_id: str | None = None,
    connection_id: str | None = None,
) -> dict[str, Any]:
    prompt = prompt.strip()
    connection = _resolve_connection(connection_id)

    history: list[dict[str, str]] = []
    if session_id:
        get_session_or_404(session_id)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in session_repository.list_messages(session_id, limit=settings.history_limit)
        ]
        # A conversa enviada à LLM precisa começar com uma mensagem do usuário
        while history and history[0]["role"] != "user":
            history.pop(0)

    result = llm_client.generate(
        connection,
        system=build_system_prompt(chaos_level),
        messages=[*history, {"role": "user", "content": prompt}],
    )

    # A sessão só é criada/gravada quando a LLM respondeu com sucesso
    if not session_id:
        session_id = session_repository.create_session(_session_title(prompt))["id"]

    metadata = {
        "provider": result.provider,
        "model": result.model,
        "connectionName": connection["name"],
        "latencyMs": result.latency_ms,
        "chaosApplied": chaos_level,
    }
    session_repository.add_message(session_id, "user", prompt, {"chaosLevel": chaos_level})
    assistant_message = session_repository.add_message(
        session_id, "assistant", result.text, metadata
    )

    return {
        "answer": result.text,
        "session_id": session_id,
        "message_id": assistant_message["id"],
        "provider": result.provider,
        "model": result.model,
        "connection_name": connection["name"],
        "latency_ms": result.latency_ms,
        "chaos_applied": chaos_level,
    }
