"""
Sorteio de tesouro pelas regras do Tormenta20 (Capítulo 8, "Tesouro em Combate"):

- a criatura indica o tipo de tesouro: Nenhum, Padrão, Metade (dinheiro pela metade) ou Dobro (duas rolagens por coluna);
- na Tabela 8-1, na linha do ND, rola-se d% na coluna Dinheiro e outro na coluna Itens;
- cada resultado leva à tabela seguinte: riquezas (8-2), diverso (8-3), equipamento (1d6 para o tipo e 8-4),
  superior (8-5 por melhoria), poções (8-12) e mágico (1d6 para o tipo e 8-8 a 8-15);
- "+%" soma 20 ao d% de riqueza ou poção; "2D" rola 2d6 para o tipo e o jogador escolhe uma das opções.

Os dados vêm de `Dice` (sorteio do sistema) ou de `TypedDice` (resultados rolados na mesa): com `TypedDice`
o sorteio é refeito com os valores já informados e para na primeira rolagem que falta (`RollNeeded`),
dizendo quais dados rolar e para quê.
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
CATEGORY_NAMES = {"menor": "menor", "media": "média", "maior": "maior", "arma": "arma",
                  "armadura": "armadura ou escudo", "esoterico": "esotérico", "acessorio": "acessório"}
EQUIPMENT_FACES = {range(1, 4): "arma", range(4, 6): "armadura", range(6, 7): "esoterico"}
MAGIC_FACES = {range(1, 3): "arma", range(3, 4): "armadura", range(4, 7): "acessorio"}
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


@dataclass
class DiceRequest:
    """Rolagem pedida ao jogador: `count`d`sides` (ele informa a soma) e para que serve."""
    dice: str
    count: int
    sides: int
    purpose: str


class RollNeeded(Exception):
    def __init__(self, request: DiceRequest):
        super().__init__(request.purpose)
        self.request = request


class Dice:
    def __init__(self, rng: Random | None = None):
        self.rng = rng or secrets.SystemRandom()

    def faces(self, count: int, sides: int, purpose: str) -> list[int]:
        return [self.rng.randint(1, sides) for _ in range(count)]

    def note(self, outcome: str) -> None:
        """O que a última rolagem encontrou na tabela (só registrado nos dados rolados na mesa)."""

    def d(self, sides: int, purpose: str = "") -> int:
        return self.faces(1, sides, purpose)[0]

    def d100(self, bonus: int = 0, purpose: str = "") -> int:
        return min(100, self.d(100, purpose) + bonus)

    def roll(self, expression: str, purpose: str = "") -> tuple[int, str]:
        if expression.isdigit():
            return int(expression), expression
        match = DICE.match(expression)
        if not match:
            raise ValueError(f"Expressão de dados inválida: {expression}")
        count, sides, plus, times = match.groups()
        faces = self.faces(int(count), int(sides), f"{purpose} ({expression})" if purpose else expression)
        total = sum(faces) + int(plus or 0)
        multiplier = int(times.replace(".", "")) if times else 1
        self.note(f"{expression} = {total * multiplier}")
        shown = "+".join(map(str, faces)) + (f"+{plus}" if plus else "")
        detail = f"{expression}: ({shown})" + (f" x {multiplier}" if times else "") + f" = {total * multiplier}"
        return total * multiplier, detail


class TypedDice(Dice):
    """Resultados rolados na mesa: cada valor responde, na ordem, à próxima rolagem pedida."""

    def __init__(self, values: list[int]):
        super().__init__()
        self.values = list(values)
        self.log: list[dict] = []

    def faces(self, count: int, sides: int, purpose: str) -> list[int]:
        request = DiceRequest(f"{count}d{sides}", count, sides, purpose)
        if not self.values:
            raise RollNeeded(request)
        value = self.values.pop(0)
        if not count <= value <= count * sides:
            raise ValueError(f"O resultado de {request.dice} deve estar entre {count} e {count * sides} ({purpose}).")
        self.log.append({**asdict(request), "value": value, "outcome": ""})
        return [value]

    def note(self, outcome: str) -> None:
        if self.log:
            self.log[-1]["outcome"] = outcome


def _span(row: sqlite3.Row) -> str:
    low, high = row["roll_min"], row["roll_max"]
    return f"{low:02d}" if low == high else f"{low:02d}-{high:02d}"


def _slot_purpose(what: str, slots: int, total: int, chosen: list[str], reason: str) -> str:
    """Pedido de melhoria/encanto: espaços restantes, o que já saiu e por que rolar de novo."""
    text = f"{what} ({slots} de {total} restante(s))"
    if chosen:
        text += f"; já escolhidos: {', '.join(chosen)}"
    return text + (f". Role de novo: {reason}" if reason else "")


def _notes(raw: str) -> str:
    return " ".join(json.loads(raw or "[]"))


def _price(text: str) -> float | None:
    match = PRICE.search(text or "")
    return float(match.group(1).replace(".", "")) if match else None


class _Roller:
    def __init__(self, conn: sqlite3.Connection, dice: Dice, half: bool):
        self.conn, self.dice, self.half = conn, dice, half
        self.labels = {role: value[0] for role, value in treasure_store.sources(conn).items()}

    def _row(self, role: str, category: str, roll: int) -> sqlite3.Row:
        row = self.conn.execute(
            "SELECT * FROM roll_tables WHERE role = ? AND category = ? AND ? BETWEEN roll_min AND roll_max",
            (role, category, roll),
        ).fetchone()
        if row is None:
            raise LookupError(f"Sem resultado para d% {roll} na tabela '{role}' ({category or 'geral'}).")
        return row

    def pick(self, role: str, category: str = "", bonus: int = 0, purpose: str = "") -> tuple[sqlite3.Row, int, str]:
        text = self.labels.get(role, role) + (f", coluna {CATEGORY_NAMES[category]}" if category else "")
        text += (f": {purpose}" if purpose else "") + (f" (o sistema soma +{bonus})" if bonus else "")
        roll = self.dice.d100(bonus, text)
        row = self._row(role, category, roll)
        self.dice.note(f"{row['result']} (d% {_span(row)})")
        return row, roll, f"{row['label']}, p. {row['page']}"

    def _type(self, choose: bool, faces: dict[range, str], purpose: str) -> list[str]:
        legend = ", ".join(f"{s.start}-{s.stop - 1}: {CATEGORY_NAMES[k]}" if len(s) > 1 else f"{s.start}: {CATEGORY_NAMES[k]}"
                           for s, k in faces.items())
        kinds = []
        for n in range(2 if choose else 1):
            roll = self.dice.d(6, f"{purpose} ({legend})" + (f", dado {n + 1} de 2 (2D: o jogador escolhe)" if choose else ""))
            kinds.append(next(kind for span, kind in faces.items() if roll in span))
            self.dice.note(CATEGORY_NAMES[kinds[-1]])
        return kinds

    def coins(self, expression: str, coin: str) -> Reward:
        amount, detail = self.dice.roll(expression, f"moedas em {coin}")
        details = [detail]
        if self.half:
            amount //= 2
            details.append(f"tesouro Metade: {amount}")
        return Reward("moedas", f"{amount} {coin} ({COIN_NAMES[coin]})", details,
                      amount * COIN_VALUE[coin], sources=[])

    def riches(self, count: str, category: str, bonus: bool) -> list[Reward]:
        total, detail = self.dice.roll(count, f"quantidade de riquezas ({category})")
        rewards = []
        for n in range(total):
            row, roll, source = self.pick("riqueza", CATEGORY[category], 20 if bonus else 0, f"riqueza {n + 1} de {total}")
            expression = row["result"].split("(")[0].strip()
            value, value_detail = self.dice.roll(expression, f"valor em T$ da riqueza {n + 1} de {total}")
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
        row, roll, source = self.pick("diverso", purpose="item diverso")
        return Reward("diverso", row["result"], [f"d% {roll}"], sources=[source])

    def base_item(self, kind: str) -> Reward:
        row, roll, source = self.pick("equipamento", kind, purpose="item base")
        label = {"arma": "arma", "armadura": "armadura ou escudo", "esoterico": "esotérico"}[kind]
        return Reward("equipamento", row["result"], [f"tipo: {label}", f"d% {roll}"], sources=[source])

    def _options(self, kinds: list[str], build) -> Reward:
        items = [build(kind) for kind in kinds]
        if len(items) == 1:
            return items[0]
        return Reward(items[0].kind, "Escolha uma das opções (2D)", ["2d6 para o tipo: o jogador escolhe uma"],
                      options=items, sources=sorted({s for i in items for s in i.sources}))

    def equipment(self, choose: bool) -> Reward:
        return self._options(self._type(choose, EQUIPMENT_FACES, "tipo do equipamento"), self.base_item)

    def superior(self, upgrades: int, choose: bool) -> Reward:
        def build(kind: str) -> Reward:
            item = self.base_item(kind)
            chosen, slots, tries, reason = [], upgrades, 0, ""
            while slots > 0 and tries < MAX_REROLLS:
                tries += 1
                row, roll, source = self.pick("superior", kind, purpose=_slot_purpose(
                    "melhoria", slots, upgrades, [c.split(" (")[0] for c in chosen], reason))
                name, notes = row["result"], _notes(row["notes"])
                cost = 2 if "Conta como duas" in notes else 1
                if name in [c.split(" (")[0] for c in chosen]:
                    reason = f"{name} (d% {_span(row)}) já foi escolhida"
                elif cost > slots:
                    reason = f"{name} (d% {_span(row)}) conta como duas melhorias e só resta 1"
                else:
                    reason = ""
                if reason:
                    self.dice.note(f"{reason}: role de novo")
                    continue
                if "material" in notes:
                    materials = dict(MATERIALS.findall(notes))
                    legend = ", ".join(f"{k}: {v.strip()}" for k, v in materials.items())
                    face = self.dice.d(6, f"material especial ({legend})")
                    self.dice.note(materials.get(str(face), "?").strip())
                    name = f"{name} ({materials.get(str(face), '?')}, 1d6 = {face})"
                chosen.append(name)
                slots -= cost
                item.sources.append(source)
            item.kind = "superior"
            item.name = f"{item.name} superior"
            item.details.append("melhorias: " + ", ".join(chosen))
            item.sources = sorted(set(item.sources))
            return item

        return self._options(self._type(choose, EQUIPMENT_FACES, "tipo do item superior"), build)

    def potions(self, count: str, bonus: bool) -> list[Reward]:
        total, detail = self.dice.roll(count, "quantidade de poções")
        rewards = []
        for n in range(total):
            row, roll, source = self.pick("pocao", bonus=20 if bonus else 0, purpose=f"poção {n + 1} de {total}")
            details = [f"d% {roll}" + (" (+20%)" if bonus else ""), f"preço {row['price']}"]
            if n == 0 and count != "1":
                details.insert(0, f"quantidade {detail}")
            rewards.append(Reward("pocao", row["result"], details, _price(row["price"]), sources=[source]))
        return rewards

    def _enchanted(self, kind: str, category: str) -> Reward:
        role, specific = ("encanto_arma", "arma_especifica") if kind == "arma" else ("encanto_armadura", "armadura_especifica")
        base = self.base_item(kind)
        chosen, slots, tries, sources, reason = [], ENCHANTMENTS[category], 0, list(base.sources), ""
        while slots > 0 and tries < MAX_REROLLS:
            tries += 1
            row, roll, source = self.pick(role, purpose=_slot_purpose(
                "encanto", slots, ENCHANTMENTS[category], chosen, reason))
            name, notes = row["result"], _notes(row["notes"])
            if "específic" in name.lower():
                special, special_roll, special_source = self.pick(specific, purpose="item específico")
                return Reward("magico", special["result"],
                              [f"d% {roll}: item específico", f"d% {special_roll}", f"preço {special['price']}"],
                              _price(special["price"]), sources=sorted({source, special_source}))
            double = name.endswith("*") or "Conta como dois" in notes
            name = name.rstrip("*")
            if name in chosen:
                reason = f"{name} (d% {_span(row)}) já foi escolhido"
            elif double and category == "menor":
                reason = f"{name} (d% {_span(row)}) conta como dois encantos e não vale em item menor"
            elif double and slots < 2:
                reason = f"{name} (d% {_span(row)}) conta como dois encantos e só resta 1"
            elif "Apenas escudos" in notes and "escudo" not in base.name.lower():
                reason = f"{name} (d% {_span(row)}) é apenas para escudos"
            else:
                reason = ""
            if reason:
                self.dice.note(f"{reason}: role de novo")
                continue
            chosen.append(name)
            slots -= 2 if double else 1
            sources.append(source)
        label = LABELS[category]
        return Reward("magico", f"{base.name} mágica ({label})" if kind == "arma" else f"{base.name} mágico ({label})",
                      base.details + ["encantos: " + ", ".join(chosen)], sources=sorted(set(sources)))

    def magic(self, category: str, choose: bool) -> Reward:
        def build(kind: str) -> Reward:
            if kind == "acessorio":
                row, roll, source = self.pick(ACCESSORIES[category], purpose="acessório")
                return Reward("magico", row["result"], [f"acessório, d% {roll}", f"preço {row['price']}"],
                              _price(row["price"]), sources=[source])
            return self._enchanted(kind, category)

        return self._options(self._type(choose, MAGIC_FACES, "tipo do item mágico"), build)

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
                  treasure_type: str | None = None, dice: Dice | None = None) -> TreasureResult:
    """
    Sorteia o tesouro de uma criatura (pelo nome) ou de um ND, com o tipo da ficha ou o informado.
    Com `TypedDice`, levanta `RollNeeded` na primeira rolagem que ainda não foi informada.
    """
    dice = dice or Dice()
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
            times = 2 if kind == "Dobro" else 1
            for n in range(times):
                purpose = f"{table}, ND {nd}, coluna {'Dinheiro' if column == 'dinheiro' else 'Itens'}"
                roll = dice.d100(0, purpose + (f" ({n + 1}ª de 2, tesouro Dobro)" if times > 1 else ""))
                row = conn.execute(
                    "SELECT result, page FROM treasure_nd WHERE nd = ? AND kind = ? AND ? BETWEEN roll_min AND roll_max",
                    (nd, column, roll),
                ).fetchone()
                dice.note(row["result"])
                rolls.append(ColumnRoll(column, roll, row["result"], resolve(row["result"]), f"{table}, p. {row['page']}"))
    total = sum(_value(r) for c in rolls for r in c.rewards)
    return TreasureResult(book_id, nd, kind, found, rolls, round(total, 1), notes)
