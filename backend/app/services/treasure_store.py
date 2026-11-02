"""
Espaço próprio do sorteio de tesouro: `TREASURE_DIR/<livro>.sqlite` (padrão `backend/data/tesouro/`).

É uma cópia das tabelas de tesouro do livro (Tabelas 8-1 a 8-15 no Tormenta20) e das
criaturas com ND e tipo de tesouro, já no formato do sorteio (faixas de d% numéricas).
É montada a partir do banco do livro (`tables-<data>.sqlite` e `chunks.jsonl`) e refeita
quando o banco é reconstruído (`built_at` do manifesto muda).
"""

import json
import logging
import os
import re
import sqlite3
import threading
from contextlib import closing
from pathlib import Path

from app.core.config import settings
from app.services import book_catalog, lexical

# Tabelas do sorteio em cada livro: papel -> (chave da tabela, coluna/grupo usado)
SOURCES: dict[str, dict[str, str]] = {
    "t20-basico": {
        "nd": "8-1", "riqueza": "8-2", "diverso": "8-3", "equipamento": "8-4", "superior": "8-5",
        "encanto_arma": "8-8", "arma_especifica": "8-9", "encanto_armadura": "8-10",
        "armadura_especifica": "8-11", "pocao": "8-12",
        "acessorio_menor": "8-13", "acessorio_medio": "8-14", "acessorio_maior": "8-15",
    },
}
CATEGORIES = {"Menor": "menor", "Média": "media", "Maior": "maior"}
EQUIPMENT_COLUMNS = {"Arma": "arma", "Armadura": "armadura", "Esotérico": "esoterico"}
SUPERIOR_COLUMNS = {"Armas": "arma", "Armaduras/Escudos": "armadura", "Esotéricos": "esoterico"}
CREATURE = re.compile(r"^(.*?)\s+ND\s+(\d+(?:/\d+)?)\b")
TREASURE = re.compile(r"Tesouro\s+([^\n]+)")
TYPES = re.compile(r"^(Nenhum|Padrão|Metade|Dobro)\b\s*(.*)$")
RANGE = re.compile(r"^(\d+)(?:-(\d+))?$")

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE treasure_nd (
    nd TEXT, nd_value REAL, kind TEXT, roll_min INTEGER, roll_max INTEGER, result TEXT, page TEXT
);
CREATE TABLE roll_tables (
    role TEXT, category TEXT, roll_min INTEGER, roll_max INTEGER, result TEXT, detail TEXT,
    price TEXT, notes TEXT, label TEXT, page TEXT
);
CREATE TABLE creatures (
    name TEXT, search TEXT, nd TEXT, nd_value REAL, treasure TEXT, treasure_note TEXT, page TEXT
);
CREATE INDEX idx_treasure_nd ON treasure_nd (nd, kind);
CREATE INDEX idx_roll_tables ON roll_tables (role, category);
"""

_lock = threading.Lock()
logger = logging.getLogger("nimb.tesouro")


def nd_value(nd: str) -> float:
    if "/" in nd:
        top, bottom = nd.split("/", 1)
        return int(top) / int(bottom)
    return float(nd)


def normalize(text: str) -> str:
    return " ".join(lexical.tokens(text)) or text.lower().strip()


def store_path(book_id: str) -> Path:
    return settings.treasure_dir / f"{book_id}.sqlite"


def supported(book_id: str) -> bool:
    return book_id in SOURCES and book_catalog.tables_path(book_id) is not None


def _range(value: str) -> tuple[int, int] | None:
    match = RANGE.match(value.strip())
    if not match:
        return None
    low, high = int(match.group(1)), int(match.group(2) or match.group(1))
    return low, 100 if high == 0 else high


def _table(conn: sqlite3.Connection, key: str) -> tuple[str, str, list[dict]]:
    head = conn.execute("SELECT label, printed_start FROM book_tables WHERE key = ?", (key,)).fetchone()
    if head is None:
        raise LookupError(f"Tabela {key} não encontrada no banco do livro.")
    rows = conn.execute(
        "SELECT cells, notes, printed FROM table_rows WHERE table_key = ? ORDER BY position", (key,)
    ).fetchall()
    return head[0], head[1], [
        {"cells": json.loads(c), "notes": json.loads(n), "page": p or head[1]} for c, n, p in rows
    ]


def _nd_rows(conn, key: str) -> list[tuple]:
    _, _, rows = _table(conn, key)
    result = []
    for row in rows:
        cells, nd = row["cells"], row["cells"].get("ND", "")
        for kind, roll_col, result_col in (("dinheiro", "d% (Dinheiro)", "Dinheiro"), ("itens", "d% (Itens)", "Itens")):
            span = _range(cells.get(roll_col, ""))
            if nd and span:
                result.append((nd, nd_value(nd), kind, *span, cells.get(result_col, "—") or "—", row["page"]))
    return result


def _roll_rows(conn, role: str, key: str) -> list[tuple]:
    label, _, rows = _table(conn, key)
    result = []
    for row in rows:
        cells = row["cells"]
        if role == "riqueza":
            for column, category in CATEGORIES.items():
                span = _range(cells.get(column, ""))
                if span:
                    result.append((role, category, *span, cells.get("Valor (T$)", ""), cells.get("Exemplos", ""),
                                   "", "[]", label, row["page"]))
            continue
        columns = EQUIPMENT_COLUMNS if role == "equipamento" else SUPERIOR_COLUMNS if role == "superior" else {}
        names = [k for k in cells if k != "d%"]
        category = next((columns[k] for k in names if k in columns), "")
        span = _range(cells.get("d%", ""))
        if not span or not names:
            continue
        name = cells[names[0]]
        detail = cells.get("Efeito", "")
        price = cells.get("Preço", "")
        result.append((role, category, *span, name, detail, price, json.dumps(row["notes"], ensure_ascii=False),
                       label, row["page"]))
    return result


def _creatures(book_id: str) -> list[tuple]:
    path = book_catalog.book_dir(book_id) / "chunks.jsonl"
    found: dict[str, list] = {}
    entry = None
    for line in path.read_text(encoding="utf-8").splitlines():
        chunk = json.loads(line)
        if chunk.get("kind") != "ameaca":
            continue
        match = CREATURE.match(chunk["title"])
        if match:
            name, nd = match.group(1).strip(), match.group(2)
            entry = found.setdefault(name, [name, normalize(name), nd, nd_value(nd), "", "", chunk["printed_start"]])
        if entry is None:
            continue
        treasure = TREASURE.search(chunk["text"])
        if treasure and not entry[4]:
            kind = TYPES.match(treasure.group(1).strip())
            entry[4] = kind.group(1) if kind else "Nenhum"
            entry[5] = (kind.group(2) if kind else f"especial: {treasure.group(1)}").strip(" .;")
    missing = "tipo de tesouro não encontrado na ficha; usado Padrão"
    return [tuple(e[:4]) + (e[4] or "Padrão", e[5] if e[4] else missing, e[6]) for e in found.values()]


def _build(book_id: str, built_at: str) -> None:
    roles = SOURCES[book_id]
    target = store_path(book_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.unlink(missing_ok=True)
    tables = book_catalog.tables_path(book_id)
    with closing(sqlite3.connect(f"{tables.as_uri()}?mode=ro", uri=True)) as source, closing(sqlite3.connect(tmp)) as out:
        out.executescript(SCHEMA)
        out.executemany("INSERT INTO treasure_nd VALUES (?,?,?,?,?,?,?)", _nd_rows(source, roles["nd"]))
        for role, key in roles.items():
            if role != "nd":
                out.executemany("INSERT INTO roll_tables VALUES (?,?,?,?,?,?,?,?,?,?)", _roll_rows(source, role, key))
        out.executemany("INSERT INTO creatures VALUES (?,?,?,?,?,?,?)", _creatures(book_id))
        labels = {r: source.execute("SELECT label, printed_start FROM book_tables WHERE key = ?", (k,)).fetchone()
                  for r, k in roles.items()}
        out.executemany("INSERT INTO meta VALUES (?,?)", [
            ("book_id", book_id), ("source_built_at", built_at),
            ("sources", json.dumps({r: list(v) for r, v in labels.items() if v}, ensure_ascii=False)),
        ])
        out.commit()
    os.replace(tmp, target)


def _current(book_id: str, built_at: str) -> bool:
    path = store_path(book_id)
    if not path.is_file():
        return False
    try:
        with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'source_built_at'").fetchone()
    except sqlite3.Error:
        return False
    return row is not None and row[0] == built_at


def ensure(book_id: str) -> Path:
    """Caminho do banco de tesouro do livro, criado ou refeito se o banco do livro mudou."""
    manifest = book_catalog.vector_manifest(book_id)
    if manifest is None or not supported(book_id):
        raise LookupError(f"O livro '{book_id}' não tem tabelas de tesouro disponíveis.")
    built_at = manifest["built_at"]
    with _lock:
        if not _current(book_id, built_at):
            _build(book_id, built_at)
    return store_path(book_id)


def prepare_all() -> None:
    """Cria ou atualiza o banco de tesouro de cada livro que tem as tabelas (roda na subida da API)."""
    for book_id in SOURCES:
        if not supported(book_id):
            continue
        try:
            ensure(book_id)
        except (LookupError, OSError, sqlite3.Error) as exc:
            logger.warning("Banco de tesouro de %s não foi preparado: %s", book_id, exc)


def sources(conn: sqlite3.Connection) -> dict[str, list[str]]:
    """Rótulo e página de cada tabela usada no sorteio, para citar a fonte."""
    return json.loads(conn.execute("SELECT value FROM meta WHERE key = 'sources'").fetchone()[0])


def connect(book_id: str) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{ensure(book_id).as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn
