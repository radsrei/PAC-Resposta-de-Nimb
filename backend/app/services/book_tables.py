"""
Tabelas dos livros, lidas do SQLite que o construtor grava junto do banco vetorial
(`tables-<data>.sqlite`). A busca acha a tabela ou a linha pelo trecho; daqui sai a
tabela organizada, com cabeçalho, grupo e página, para entrar no prompt.
"""

import json
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services import book_catalog

MAX_TABLE_CHARS = 6000


@dataclass(frozen=True)
class TableRow:
    position: int
    group: str
    name: str
    cells: dict[str, str]
    notes: tuple[str, ...]
    printed: str


@dataclass(frozen=True)
class BookTable:
    key: str
    label: str
    printed_start: str
    printed_end: str
    columns: tuple[str, ...]
    notes: tuple[str, ...]
    rows: tuple[TableRow, ...]

    @property
    def pages(self) -> str:
        return self.printed_start if self.printed_end in ("", self.printed_start) else f"{self.printed_start}-{self.printed_end}"

    def select(self, positions: set[int] | None = None) -> list[TableRow]:
        return [r for r in self.rows if positions is None or r.position in positions]

    def render(self, positions: set[int] | None = None) -> str:
        rows = self.select(positions)
        partial = len(rows) < len(self.rows)
        lines = [f"{self.label} (p. {self.pages})" + (f" — {len(rows)} de {len(self.rows)} linhas" if partial else "")]
        group, columns = None, None
        for row in rows:
            keys = list(row.cells)
            if row.group != group or keys != columns:
                group, columns = row.group, keys
                lines += ["", f"{group}:"] if group else [""]
                lines += ["| " + " | ".join(keys) + " |", "|" + "---|" * len(keys)]
            lines.append("| " + " | ".join(row.cells[k] or "—" for k in keys) + " |")
        notes = [n for r in rows for n in r.notes] if partial else list(self.notes)
        lines += [f"Nota: {n}" for n in dict.fromkeys(notes)]
        return "\n".join(lines)


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=256)
def _load(path: str, key: str) -> BookTable | None:
    with closing(_connect(Path(path))) as conn:
        head = conn.execute("SELECT * FROM book_tables WHERE key = ?", (key,)).fetchone()
        if head is None:
            return None
        rows = conn.execute(
            "SELECT position, grp, name, cells, notes, printed FROM table_rows WHERE table_key = ? ORDER BY position",
            (key,),
        ).fetchall()
    return BookTable(
        key=key,
        label=head["label"],
        printed_start=head["printed_start"] or str(head["page_start"]),
        printed_end=head["printed_end"] or str(head["page_end"]),
        columns=tuple(json.loads(head["columns"])),
        notes=tuple(json.loads(head["notes"])),
        rows=tuple(
            TableRow(r["position"], r["grp"], r["name"], json.loads(r["cells"]), tuple(json.loads(r["notes"])), r["printed"])
            for r in rows
        ),
    )


def get_table(book_id: str, key: str) -> BookTable | None:
    path = book_catalog.tables_path(book_id)
    if path is None or not path.is_file():
        return None
    return _load(str(path), key)


def table_text(book_id: str, key: str, positions: set[int] | None = None) -> tuple[str, str] | None:
    """Texto da tabela (inteira ou só as linhas pedidas) e a página da primeira linha mostrada."""
    table = get_table(book_id, key)
    if table is None:
        return None
    text = table.render(positions)
    if positions is None and len(text) > MAX_TABLE_CHARS:
        return None
    rows = table.select(positions)
    return text, (rows[0].printed if rows else table.printed_start)
