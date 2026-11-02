"""
Sorteio de tesouro: só para quem já liberou um livro que tem as tabelas de tesouro.

1. Escolhe o livro (o informado, se liberado; senão o primeiro liberado com tesouro);
2. Sorteia pela criatura (ND e tipo de tesouro da ficha) ou pelo ND informado; no sorteio em grupo,
   uma rolagem por unidade de cada criatura;
3. Na consulta, usa os resultados rolados na mesa e devolve a próxima rolagem que falta ou o tesouro pronto;
4. Grava cada resultado no histórico do usuário e devolve o sorteio com as fontes.
"""

from dataclasses import asdict
from typing import Any

from app.core.exceptions import AppError, BookRequiredError, NotFoundError
from app.repositories import book_repository, treasure_repository
from app.services import treasure, treasure_store

NO_BOOK = "Para sortear tesouro, envie antes o PDF de um livro com as tabelas de tesouro (Tormenta20 - Livro Básico)."


def _book(user_email: str, book_id: str | None) -> str:
    granted = [b for b in book_repository.list_access(user_email) if treasure_store.supported(b)]
    if book_id:
        if book_id not in granted:
            raise BookRequiredError(NO_BOOK)
        return book_id
    if not granted:
        raise BookRequiredError(NO_BOOK)
    return granted[0]


def roll(user_email: str, book_id: str | None, creature: str | None, nd: str | None,
         treasure_type: str | None) -> dict[str, Any]:
    book = _book(user_email, book_id)
    try:
        result = treasure.roll_treasure(book, creature=creature, nd=nd, treasure_type=treasure_type).to_dict()
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    return {**result, **treasure_repository.add(user_email, result)}


def roll_group(user_email: str, book_id: str | None, items: list[dict[str, Any]]) -> dict[str, Any]:
    book = _book(user_email, book_id)
    groups = []
    for item in items:
        results = []
        for _ in range(item["quantity"]):
            try:
                result = treasure.roll_treasure(
                    book, creature=item["creature"], treasure_type=item.get("treasure_type"),
                ).to_dict()
            except LookupError as exc:
                raise NotFoundError(str(exc)) from exc
            except ValueError as exc:
                raise AppError(str(exc)) from exc
            results.append({**result, **treasure_repository.add(user_email, result)})
        total = round(sum(r["total_value"] for r in results), 1)
        groups.append({"creature": results[0]["creature"], "quantity": item["quantity"],
                       "total_value": total, "results": results})
    return {"groups": groups, "total_value": round(sum(g["total_value"] for g in groups), 1)}


def lookup(user_email: str, book_id: str | None, creature: str, treasure_type: str | None,
           values: list[int]) -> dict[str, Any]:
    book = _book(user_email, book_id)
    dice = treasure.TypedDice(values)
    try:
        result = treasure.roll_treasure(book, creature=creature, treasure_type=treasure_type, dice=dice).to_dict()
    except treasure.RollNeeded as need:
        return {"done": False, "steps": dice.log, "next": asdict(need.request), "result": None}
    except LookupError as exc:
        raise NotFoundError(str(exc)) from exc
    except ValueError as exc:
        raise AppError(str(exc)) from exc
    result = {**result, **treasure_repository.add(user_email, result)}
    return {"done": True, "steps": dice.log, "next": None, "result": result}


def creatures(user_email: str, book_id: str | None, query: str, limit: int) -> list[dict[str, Any]]:
    return treasure.search_creatures(_book(user_email, book_id), query, limit)


def levels(user_email: str, book_id: str | None) -> list[str]:
    return treasure.nd_levels(_book(user_email, book_id))


def history(user_email: str, limit: int) -> list[dict[str, Any]]:
    return treasure_repository.list_recent(user_email, limit)
