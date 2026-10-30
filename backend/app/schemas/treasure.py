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


D100 = Annotated[int, Field(ge=1, le=100)]
TreasureType = Literal["padrao", "metade", "dobro", "nenhum"]


class TableRolls(CamelModel):
    """d% da Tabela 8-1 rolados pelo jogador para uma criatura (vazio = rolagem automática)."""
    money: list[D100 | None] = Field(default_factory=list, max_length=2)
    items: list[D100 | None] = Field(default_factory=list, max_length=2)


class TreasureGroupItem(CamelModel):
    creature: str = Field(..., min_length=1, max_length=120)
    quantity: int = Field(1, ge=1, le=20)
    treasure_type: TreasureType | None = None
    # Uma entrada por unidade da criatura, na ordem
    rolls: list[TableRolls] = Field(default_factory=list, max_length=20)


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
    manual: bool = False


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


class TreasureGroupOut(CamelModel):
    groups: list[TreasureGroupEntryOut]
    total_value: float
