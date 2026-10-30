from typing import Annotated, Literal

from pydantic import Field, model_validator

from app.schemas.base import CamelModel


class TreasureRollPayload(CamelModel):
    book_id: str | None = Field(None, max_length=64)
    creature: str | None = Field(None, max_length=120)
    nd: str | None = Field(None, pattern=r"^\d{1,2}(/\d)?$")
    # Vazio = o tipo da ficha da criatura (ou Padrão, quando só o ND é informado)
    treasure_type: Literal["padrao", "metade", "dobro", "nenhum"] | None = None

    @model_validator(mode="after")
    def creature_or_nd(self):
        if not (self.creature and self.creature.strip()) and not self.nd:
            raise ValueError("Informe a criatura ou o ND.")
        return self


TreasureType = Literal["padrao", "metade", "dobro", "nenhum"]


class TreasureGroupItem(CamelModel):
    creature: str = Field(..., min_length=1, max_length=120)
    quantity: int = Field(1, ge=1, le=20)
    treasure_type: TreasureType | None = None


class TreasureLookupPayload(CamelModel):
    """Resultados rolados na mesa para uma criatura, na ordem em que o sistema pediu."""
    book_id: str | None = Field(None, max_length=64)
    creature: str = Field(..., min_length=1, max_length=120)
    treasure_type: TreasureType | None = None
    values: list[Annotated[int, Field(ge=1, le=10000)]] = Field(default_factory=list, max_length=300)


class TreasureGroupPayload(CamelModel):
    book_id: str | None = Field(None, max_length=64)
    creatures: list[TreasureGroupItem] = Field(..., min_length=1, max_length=10)


class RewardOut(CamelModel):
    kind: str
    name: str
    details: list[str]
    value: float | None = None
    options: list["RewardOut"] = []
    sources: list[str]


class ColumnRollOut(CamelModel):
    column: str
    roll: int
    result: str
    rewards: list[RewardOut]
    source: str


class CreatureOut(CamelModel):
    name: str
    nd: str
    treasure: str
    treasure_note: str = ""
    page: str = ""


class TreasureRollOut(CamelModel):
    id: str
    created_at: str
    book_id: str
    nd: str
    treasure_type: str
    creature: CreatureOut | None = None
    rolls: list[ColumnRollOut]
    total_value: float
    notes: list[str]


class TreasureGroupEntryOut(CamelModel):
    creature: CreatureOut
    quantity: int
    total_value: float
    results: list[TreasureRollOut]


class DiceRequestOut(CamelModel):
    dice: str
    count: int
    sides: int
    purpose: str


class DiceStepOut(DiceRequestOut):
    value: int
    # O que o valor encontrou na tabela, ou por que foi descartado
    outcome: str = ""


class TreasureLookupOut(CamelModel):
    """`done` false: falta a rolagem `next`. `done` true: `result` é o tesouro (já gravado no histórico)."""
    done: bool
    steps: list[DiceStepOut]
    next: DiceRequestOut | None = None
    result: TreasureRollOut | None = None


class TreasureGroupOut(CamelModel):
    groups: list[TreasureGroupEntryOut]
    total_value: float
