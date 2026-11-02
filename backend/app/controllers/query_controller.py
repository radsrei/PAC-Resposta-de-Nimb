"""
Fluxo de pergunta -> busca nos livros -> LLM -> resposta.

1. Exige ao menos um livro liberado (`book_access`) com banco pronto: sem livro, não há pergunta;
2. Resolve a conexão LLM (a informada ou a ativa) e o histórico recente da sessão;
3. Busca os trechos mais próximos; sem nenhum trecho relevante, a pergunta é recusada sem chamar a LLM;
4. Monta o prompt de sistema (persona Nimb + escopo Tormenta20 + nível de caos + trechos) e chama a LLM;
   o nível define as voltas de revisão (harness) e a chance de Nimb alucinar (services/chaos.py);
5. Persiste pergunta, resposta e fontes na sessão e devolve o resultado.
"""

from time import perf_counter
from typing import Any

from app.core.config import settings
from app.core.exceptions import AppError, BookRequiredError, NoActiveConnectionError, OutOfScopeError
from app.repositories import book_repository, llm_repository, session_repository
from app.services import book_catalog, chaos, retrieval
from app.services.prompts import BOOK_REQUIRED, OUT_OF_SCOPE, build_system_prompt
from app.controllers.session_controller import get_session_or_404

QUOTE_CHARS = 280


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


def _searchable_books(user_email: str, requested: list[str] | None) -> list[str]:
    """Livros liberados e com banco pronto; o pedido do front só pode restringir, nunca ampliar."""
    granted = [b for b in book_repository.list_access(user_email) if book_catalog.vector_manifest(b)]
    books = [b for b in granted if b in requested] if requested else granted
    if not books:
        raise BookRequiredError(BOOK_REQUIRED)
    return books


def _search_text(prompt: str, history: list[dict[str, str]]) -> str:
    """A pergunta anterior entra na busca para resolver continuações ("e se eu gastar mais PM nela?")."""
    previous = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    return f"{previous}\n{prompt}" if previous else prompt


def _is_refusal(answer: str) -> bool:
    """A LLM recusou por estar fora do escopo (devolveu a frase de OUT_OF_SCOPE)."""
    return " ".join(answer.split()).strip("\"“” ").startswith(OUT_OF_SCOPE[:60])


def _quote(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= QUOTE_CHARS else text[:QUOTE_CHARS].rsplit(" ", 1)[0] + "..."


def _source(passage: retrieval.Passage) -> dict[str, Any]:
    return {
        "book_id": passage.book_id,
        "book_title": passage.book_title,
        "title": passage.title,
        "path": passage.path,
        "kind": passage.kind,
        "page": passage.page,
        "similarity": passage.similarity,
    }


def ask(
    user_email: str,
    prompt: str,
    chaos_level: int,
    use_chaos_rule: bool,
    roll_token: str | None = None,
    session_id: str | None = None,
    connection_id: str | None = None,
    book_ids: list[str] | None = None,
) -> dict[str, Any]:
    question_started = perf_counter()
    prompt = prompt.strip()
    level = chaos.get_level(chaos_level)
    if use_chaos_rule and not roll_token:
        raise AppError("Regra Nimb ligada: role o caos (POST /api/rag/roll) antes de perguntar.")
    roll = chaos.read_roll(roll_token, user_email, prompt, level) if use_chaos_rule else None
    books = _searchable_books(user_email, book_ids)
    connection = _resolve_connection(connection_id)

    history: list[dict[str, str]] = []
    if session_id:
        get_session_or_404(user_email, session_id)
        history = [
            {"role": m["role"], "content": m["content"]}
            for m in session_repository.list_messages(session_id, limit=settings.history_limit)
        ]
        # A conversa enviada à LLM precisa começar com uma mensagem do usuário
        while history and history[0]["role"] != "user":
            history.pop(0)

    passages = retrieval.search(books, _search_text(prompt, history))
    if not passages:
        raise OutOfScopeError(OUT_OF_SCOPE)
    if roll is None:
        roll = chaos.roll_by_chance(level)  # Regra Nimb desligada: decide só depois da busca

    outcome = chaos.answer(
        connection,
        system=build_system_prompt(level, passages),
        messages=[*history, {"role": "user", "content": prompt}],
        level=level,
        hallucinate=roll["hallucinated"],
        is_refusal=_is_refusal,
        question_started=question_started,
    )
    result = outcome.llm
    if _is_refusal(result.text):
        raise OutOfScopeError(OUT_OF_SCOPE)

    # A sessão só é criada/gravada quando a LLM respondeu com sucesso
    if not session_id:
        session_id = session_repository.create_session(user_email, _session_title(prompt))["id"]

    best = passages[0]
    source = {
        "book_title": best.book_title,
        "page": best.page,
        "similarity": f"{best.similarity:.1%}",
        "quote": _quote(best.text),
    }
    sources = [_source(p) for p in passages]
    metadata = {
        "provider": result.provider,
        "model": result.model,
        "connectionName": connection["name"],
        "latencyMs": result.latency_ms,
        "chaosApplied": level.id,
        "chaosLabel": level.label,
        "harnessRounds": outcome.harness_rounds,
        "hallucinated": outcome.hallucinated,
        "chaosRoll": roll,
        "bookTitle": source["book_title"],
        "page": source["page"],
        "similarity": source["similarity"],
        "sources": sources,
    }
    session_repository.add_message(session_id, "user", prompt, {"chaosLevel": level.id})
    assistant_message = session_repository.add_message(session_id, "assistant", result.text, metadata)

    return {
        "answer": result.text,
        "session_id": session_id,
        "message_id": assistant_message["id"],
        "provider": result.provider,
        "model": result.model,
        "connection_name": connection["name"],
        "latency_ms": result.latency_ms,
        "chaos_applied": level.id,
        "chaos_label": level.label,
        "harness_rounds": outcome.harness_rounds,
        "hallucinated": outcome.hallucinated,
        **source,
        "sources": sources,
    }
