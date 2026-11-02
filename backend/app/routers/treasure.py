"""
Sorteio de tesouro pelas tabelas do livro (Tormenta20, Capítulo 8).

POST /api/tesouro/sortear    -> sorteia pela criatura ou pelo ND e grava no histórico
POST /api/tesouro/sortear-grupo -> sorteia várias criaturas (com quantidade) e grava no histórico
POST /api/tesouro/consultar  -> resultados rolados na mesa: devolve o próximo dado a rolar ou o tesouro pronto
GET  /api/tesouro/criaturas  -> criaturas do livro com ND e tipo de tesouro (busca por nome)
GET  /api/tesouro/nds        -> NDs que existem na tabela de tesouro
GET  /api/tesouro/historico  -> últimos sorteios do usuário
"""

from fastapi import APIRouter, Depends, Query

from app.controllers import treasure_controller
from app.core.deps import CurrentUser, require_user
from app.schemas.treasure import (
    CreatureOut, TreasureGroupOut, TreasureGroupPayload, TreasureLookupOut, TreasureLookupPayload, TreasureRollOut,
    TreasureRollPayload,
)

router = APIRouter(prefix="/api/tesouro", tags=["tesouro"])


@router.post("/sortear", response_model=TreasureRollOut)
def roll(payload: TreasureRollPayload, user: CurrentUser = Depends(require_user)):
    return treasure_controller.roll(user["email"], payload.book_id, payload.creature, payload.nd, payload.treasure_type)


@router.post("/sortear-grupo", response_model=TreasureGroupOut)
def roll_group(payload: TreasureGroupPayload, user: CurrentUser = Depends(require_user)):
    items = [item.model_dump() for item in payload.creatures]
    return treasure_controller.roll_group(user["email"], payload.book_id, items)


@router.post("/consultar", response_model=TreasureLookupOut)
def lookup(payload: TreasureLookupPayload, user: CurrentUser = Depends(require_user)):
    return treasure_controller.lookup(user["email"], payload.book_id, payload.creature, payload.treasure_type,
                                      payload.values)


@router.get("/criaturas", response_model=list[CreatureOut])
def creatures(q: str = Query("", max_length=120), book_id: str | None = Query(None, alias="bookId", max_length=64),
              limit: int = Query(20, ge=1, le=200), user: CurrentUser = Depends(require_user)):
    return treasure_controller.creatures(user["email"], book_id, q, limit)


@router.get("/nds", response_model=list[str])
def levels(book_id: str | None = Query(None, alias="bookId", max_length=64), user: CurrentUser = Depends(require_user)):
    return treasure_controller.levels(user["email"], book_id)


@router.get("/historico", response_model=list[TreasureRollOut])
def history(limit: int = Query(20, ge=1, le=100), user: CurrentUser = Depends(require_user)):
    return treasure_controller.history(user["email"], limit)
