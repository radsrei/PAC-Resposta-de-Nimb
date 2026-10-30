"""
Sorteio de tesouro pelas regras do Tormenta20 (Capítulo 8, "Tesouro em Combate"):

- a criatura indica o tipo de tesouro: Nenhum, Padrão, Metade (dinheiro pela metade) ou Dobro (duas rolagens por coluna);
- na Tabela 8-1, na linha do ND, rola-se d% na coluna Dinheiro e outro na coluna Itens;
- cada resultado leva à tabela seguinte: riquezas (8-2), diverso (8-3), equipamento (1d6 para o tipo e 8-4),
  superior (8-5 por melhoria), poções (8-12) e mágico (1d6 para o tipo e 8-8 a 8-15);
- "+%" soma 20 ao d% de riqueza ou poção; "2D" rola 2d6 para o tipo e o jogador escolhe uma das opções.
"""

import json
import re
import secrets
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass, field
from random import Random

from app.services import treasure_store

COINS = re.compile(r"^(\d+d\d+(?:\+\d+)?(?:x[\d.]+)?)\s*(TC|T\$|TO)$")
DICE = re.compile(r"^(\d+)d(\d+)(?:\+(\d+))?(?:x([\d.]+))?$")
RICHES = re.compile(r"^(\S+)\s+riquezas?\s+(menor|média|maior)\w*(\+%)?$")
POTIONS = re.compile(r"^(\S+)\s+poç(?:ão|ões)(\+%)?$")
SUPERIOR = re.compile(r"^Superior \((\d+) melhorias?\)\s*(2D)?$")
MAGIC = re.compile(r"^Mágico \((menor|médio|maior)\)\s*(2D)?$")
EQUIPMENT = re.compile(r"^Equipamento\s*(2D)?$")
MATERIALS = re.compile(r"(\d)\)\s*([^,.]+)")
PRICE = re.compile(r"T\$\s*([\d.]+)")
COIN_VALUE = {"TC": 0.1, "T$": 1.0, "TO": 10.0}
COIN_NAMES = {"TC": "tibares de cobre", "T$": "tibares de prata", "TO": "tibares de ouro"}
TREASURE_TYPES = {"nenhum": "Nenhum", "padrao": "Padrão", "metade": "Metade", "dobro": "Dobro"}
CATEGORY = {"menor": "menor", "média": "media", "médio": "media", "maior": "maior"}
ENCHANTMENTS = {"menor": 1, "media": 2, "maior": 3}
ACCESSORIES = {"menor": "acessorio_menor", "media": "acessorio_medio", "maior": "acessorio_maior"}
LABELS = {"menor": "menor", "media": "médio", "maior": "maior"}
MAX_REROLLS = 50


@dataclass
class Reward:
    kind: str
    name: str
    details: list[str] = field(default_factory=list)
    value: float | None = None
    options: list["Reward"] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)


@dataclass
class ColumnRoll:
    column: str
    roll: int
    result: str
    rewards: list[Reward]
    source: str
    manual: bool = False


@dataclass
class TreasureResult:
    book_id: str
    nd: str
    treasure_type: str
    creature: dict | None
    rolls: list[ColumnRoll]
    total_value: float
    notes: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


class Dice:
    def __init__(self, rng: Random | None = None):
        self.rng = rng or secrets.SystemRandom()

    def d(self, sides: int) -> int:
        return self.rng.randint(1, sides)

    def d100(self, bonus: int = 0) -> int:
        return min(100, self.d(100) + bonus)

    def roll(self, expression: str) -> tuple[int, str]:
        if expression.isdigit():
            return int(expression), expression
        match = DICE.match(expression)
        if not match:
            raise ValueError(f"Expressão de dados inválida: {expression}")
        count, sides, plus, times = match.groups()
        faces = [self.d(int(sides)) for _ in range(int(count))]
        total = sum(faces) + int(plus or 0)
        multiplier = int(times.replace(".", "")) if times else 1
        shown = "+".join(map(str, faces)) + (f"+{plus}" if plus else "")
        detail = f"{expression}: ({shown})" + (f" x {multiplier}" if times else "") + f" = {total * multiplier}"
        return total * multiplier, detail


def _notes(raw: str) -> str:
    return " ".join(json.loads(raw or "[]"))


def _price(text: str) -> float | None:
    match = PRICE.search(text or "")
    return float(match.group(1).replace(".", "")) if match else None


class _Roller:
    def __init__(self, conn: sqlite3.Connection, dice: Dice, half: bool):
        self.conn, self.dice, self.half = conn, dice, half

    def _row(self, role: str, category: str, roll: int) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM roll_tables WHERE role = ? AND category = ? AND ? BETWEEN roll_min AND roll_max",
            (role, category, roll),
        ).fetchone()
        if row is None:
            raise LookupError(f"Sem resultado para d% {roll} na tabela '{role}' ({category or 'geral'}).")
        return row

    def pick(self, role: str, category: str = "", bonus: int = 0) -> tuple[sqlite3.Row, int, str]:
        roll = self.dice.d100(bonus)
        row = self._row(role, category, roll)
        return row, roll, f"{row['label']}, p. {row['page']}"

    def _type(self, choose: bool, faces: dict[range, str]) -> list[str]:
        rolls = [self.dice.d(6) for _ in range(2 if choose else 1)]
        return [next(kind for span, kind in faces.items() if r in span) for r in rolls]

    def coins(self, expression: str, coin: str) -> Reward:
        amount, detail = self.dice.roll(expression)
        details = [detail]
        if self.half:
            amount //= 2
            details.append(f"tesouro Metade: {amount}")
        return Reward("moedas", f"{amount} {coin} ({COIN_NAMES[coin]})", details,
                      amount * COIN_VALUE[coin], sources=[])

    def riches(self, count: str, category: str, bonus: bool) -> list[Reward]:
        total, detail = self.dice.roll(count)
        rewards = []
        for n in range(total):
            row, roll, source = self.pick("riqueza", CATEGORY[category], 20 if bonus else 0)
            expression = row["result"].split("(")[0].strip()
            value, value_detail = self.dice.roll(expression)
            details = [f"d% {roll}" + (" (+20%)" if bonus else ""), f"valor {value_detail}"]
            if self.half:
                value //= 2
                details.append(f"tesouro Metade: T$ {value}")
            details.append(f"exemplos: {row['detail']}")
            if n == 0 and count != "1":
                details.insert(0, f"quantidade {detail}")
            rewards.append(Reward("riqueza", f"Riqueza {category} (T$ {value})", details, float(value), sources=[source]))
        return rewards

    def misc(self) -> Reward:
        row, roll, source = self.pick("diverso")
        return Reward("diverso", row["result"], [f"d% {roll}"], sources=[source])

    def base_item(self, kind: str) -> Reward:
        row, roll, source = self.pick("equipamento", kind)
        label = {"arma": "arma", "armadura": "armadura ou escudo", "esoterico": "esotérico"}[kind]
        return Reward("equipamento", row["result"], [f"tipo: {label}", f"d% {roll}"], sources=[source])

    def _options(self, kinds: list[str], build) -> Reward:
        items = [build(kind) for kind in kinds]
        if len(items) == 1:
            return items[0]
        return Reward(items[0].kind, "Escolha uma das opções (2D)", ["2d6 para o tipo: o jogador escolhe uma"],
                      options=items, sources=sorted({s for i in items for s in i.sources}))

    def equipment(self, choose: bool) -> Reward:
        faces = {range(1, 4): "arma", range(4, 6): "armadura", range(6, 7): "esoterico"}
        return self._options(self._type(choose, faces), self.base_item)

    def superior(self, upgrades: int, choose: bool) -> Reward:
        faces = {range(1, 4): "arma", range(4, 6): "armadura", range(6, 7): "esoterico"}

        def build(kind: str) -> Reward:
            item = self.base_item(kind)
            chosen, slots, tries = [], upgrades, 0
            while slots > 0 and tries < MAX_REROLLS:
                tries += 1
                row, roll, source = self.pick("superior", kind)
                name, notes = row["result"], _notes(row["notes"])
                cost = 2 if "Conta como duas" in notes else 1
                if name in [c.split(" (")[0] for c in chosen] or cost > slots:
                    continue
                if "material" in notes:
                    materials = dict(MATERIALS.findall(notes))
                    face = self.dice.d(6)
                    name = f"{name} ({materials.get(str(face), '?')}, 1d6 = {face})"
                chosen.append(name)
                slots -= cost
                item.sources.append(source)
            item.kind = "superior"
            item.name = f"{item.name} superior"
            item.details.append("melhorias: " + ", ".join(chosen))
            item.sources = sorted(set(item.sources))
            return item

        return self._options(self._type(choose, faces), build)

    def potions(self, count: str, bonus: bool) -> list[Reward]:
        total, detail = self.dice.roll(count)
        rewards = []
        for n in range(total):
            row, roll, source = self.pick("pocao", bonus=20 if bonus else 0)
            details = [f"d% {roll}" + (" (+20%)" if bonus else ""), f"preço {row['price']}"]
            if n == 0 and count != "1":
                details.insert(0, f"quantidade {detail}")
            rewards.append(Reward("pocao", row["result"], details, _price(row["price"]), sources=[source]))
        return rewards

    def _enchanted(self, kind: str, category: str) -> Reward:
        role, specific = ("encanto_arma", "arma_especifica") if kind == "arma" else ("encanto_armadura", "armadura_especifica")
        base = self.base_item(kind)
        chosen, slots, tries, sources = [], ENCHANTMENTS[category], 0, list(base.sources)
        while slots > 0 and tries < MAX_REROLLS:
            tries += 1
            row, roll, source = self.pick(role)
            name, notes = row["result"], _notes(row["notes"])
            if "específic" in name.lower():
                special, special_roll, special_source = self.pick(specific)
                return Reward("magico", special["result"],
                              [f"d% {roll}: item específico", f"d% {special_roll}", f"preço {special['price']}"],
                              _price(special["price"]), sources=sorted({source, special_source}))
            double = name.endswith("*") or "Conta como dois" in notes
            name = name.rstrip("*")
            if name in chosen or (double and (category == "menor" or slots < 2)):
                continue
            if "Apenas escudos" in notes and "escudo" not in base.name.lower():
                continue
            chosen.append(name)
            slots -= 2 if double else 1
            sources.append(source)
        label = LABELS[category]
        return Reward("magico", f"{base.name} mágica ({label})" if kind == "arma" else f"{base.name} mágico ({label})",
                      base.details + ["encantos: " + ", ".join(chosen)], sources=sorted(set(sources)))

    def magic(self, category: str, choose: bool) -> Reward:
        faces = {range(1, 3): "arma", range(3, 4): "armadura", range(4, 7): "acessorio"}

        def build(kind: str) -> Reward:
            if kind == "acessorio":
                row, roll, source = self.pick(ACCESSORIES[category])
                return Reward("magico", row["result"], [f"acessório, d% {roll}", f"preço {row['price']}"],
                              _price(row["price"]), sources=[source])
            return self._enchanted(kind, category)

        return self._options(self._type(choose, faces), build)

    def money(self, result: str) -> list[Reward]:
        text = result.strip()
        if text in ("—", ""):
            return []
        if match := COINS.match(text):
            return [self.coins(*match.groups())]
        if match := RICHES.match(text):
            return self.riches(match.group(1), match.group(2), bool(match.group(3)))
        return [Reward("outro", text, ["resultado sem regra automática: resolva com o mestre"])]

    def items(self, result: str) -> list[Reward]:
        text = result.strip()
        if text in ("—", ""):
            return []
        if text == "Diverso":
            return [self.misc()]
        if match := EQUIPMENT.match(text):
            return [self.equipment(bool(match.group(1)))]
        if match := POTIONS.match(text):
            return self.potions(match.group(1), bool(match.group(2)))
        if match := SUPERIOR.match(text):
            return [self.superior(int(match.group(1)), bool(match.group(2)))]
        if match := MAGIC.match(text):
            return [self.magic(CATEGORY[match.group(1)], bool(match.group(2)))]
        return [Reward("outro", text, ["resultado sem regra automática: resolva com o mestre"])]


def _value(reward: Reward) -> float:
    if reward.options:
        return 0.0
    return reward.value or 0.0


def find_creature(book_id: str, name: str) -> dict:
    query = treasure_store.normalize(name)
    with closing(treasure_store.connect(book_id)) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM creatures")]
    exact = [r for r in rows if r["search"] == query]
    partial = [r for r in rows if query in r["search"]]
    found = exact or sorted(partial, key=lambda r: len(r["search"]))
    if not found:
        raise LookupError(f"Criatura '{name}' não encontrada no livro.")
    return found[0]


def search_creatures(book_id: str, text: str, limit: int = 20) -> list[dict]:
    query = treasure_store.normalize(text) if text.strip() else ""
    with closing(treasure_store.connect(book_id)) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM creatures ORDER BY nd_value, name")]
    return [r for r in rows if query in r["search"]][:limit]


def nd_levels(book_id: str) -> list[str]:
    with closing(treasure_store.connect(book_id)) as conn:
        return [r[0] for r in conn.execute("SELECT DISTINCT nd FROM treasure_nd ORDER BY nd_value")]


def roll_treasure(book_id: str, creature: str | None = None, nd: str | None = None,
                  treasure_type: str | None = None, dice: Dice | None = None,
                  table_rolls: dict[str, list[int | None]] | None = None) -> TreasureResult:
    """
    Sorteia o tesouro de uma criatura (pelo nome) ou de um ND, com o tipo da ficha ou o informado.

    `table_rolls` traz os d% da Tabela 8-1 rolados pelo jogador ({"dinheiro": [..], "itens": [..]},
    dois valores por coluna no tipo Dobro); valor vazio é rolado aqui. As rolagens seguintes são automáticas.
    """
    dice = dice or Dice()
    given = {column: list(values) for column, values in (table_rolls or {}).items()}
    found = find_creature(book_id, creature) if creature else None
    nd = (nd or (found["nd"] if found else "")).strip()
    if not nd:
        raise ValueError("Informe a criatura ou o ND.")
    kind = TREASURE_TYPES.get((treasure_type or "").strip().lower().replace("ã", "a"))
    kind = kind or (found["treasure"] if found else "Padrão")
    notes = []
    special = bool(found and found["treasure_note"].startswith("especial:"))
    if special:
        notes.append(f"Tesouro especial de {found['name']} (sem rolagem na tabela): {found['treasure_note'][10:]}")
    elif found and found["treasure_note"]:
        notes.append(f"Ficha de {found['name']}: {found['treasure']} {found['treasure_note']}".strip())
    with closing(treasure_store.connect(book_id)) as conn:
        levels = [r[0] for r in conn.execute("SELECT DISTINCT nd FROM treasure_nd ORDER BY nd_value")]
        if nd not in levels:
            value = treasure_store.nd_value(nd)
            if value > treasure_store.nd_value(levels[-1]):
                notes.append(f"ND {nd} acima da tabela: usada a linha do ND {levels[-1]}.")
                nd = levels[-1]
            else:
                raise ValueError(f"ND '{nd}' não existe na tabela de tesouro.")
        if kind == "Nenhum":
            if not special:
                notes.append("Tesouro Nenhum: a criatura não traz tesouro.")
            return TreasureResult(book_id, nd, kind, found, [], 0.0, notes)
        roller = _Roller(conn, dice, half=kind == "Metade")
        table = treasure_store.sources(conn)["nd"][0]
        rolls = []
        for column, resolve in (("dinheiro", roller.money), ("itens", roller.items)):
            for _ in range(2 if kind == "Dobro" else 1):
                typed = given.get(column, []).pop(0) if given.get(column) else None
                roll = typed or dice.d100()
                row = conn.execute(
                    "SELECT result, page FROM treasure_nd WHERE nd = ? AND kind = ? AND ? BETWEEN roll_min AND roll_max",
                    (nd, column, roll),
                ).fetchone()
                rolls.append(ColumnRoll(column, roll, row["result"], resolve(row["result"]), f"{table}, p. {row['page']}",
                                        typed is not None))
    total = sum(_value(r) for c in rolls for r in c.rewards)
    return TreasureResult(book_id, nd, kind, found, rolls, round(total, 1), notes)
