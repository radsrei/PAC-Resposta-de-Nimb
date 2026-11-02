"""Tabelas do livro em estrutura (colunas, grupos, linhas e notas), montadas a partir das linhas de tabela extraídas."""

import re
import unicodedata
from dataclasses import dataclass, field

from vector_builder.extract import Element

NUMBERED = re.compile(r"^Tabela (\d+-\d+):?\s*(.*?)\s*(\(Continuação\))?$")
CONTINUED = re.compile(r"\s*\(Continuação\)$")
FOOTNOTE = re.compile(r"^(\D*[^\W\d]{2})([1-9])$")
NOTE = re.compile(r"^\S{1,3}[A-ZÀ-Ú][a-zà-ú]")
RANGE = re.compile(r"^(\d+)(?:-(\d+))?$")
EMPTY = ("", "—", "-")


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", "".join(c for c in text if not unicodedata.combining(c))).strip("-")


def table_key(title: str) -> str:
    match = NUMBERED.match(title)
    return match.group(1) if match else slug(CONTINUED.sub("", title))


def parse_range(value: str) -> tuple[int, int] | None:
    match = RANGE.match(value.strip())
    if not match:
        return None
    low = int(match.group(1))
    high = int(match.group(2) or low)
    return (low, 100 if high == 0 else high)


@dataclass
class Row:
    group: str
    cells: dict[str, str]
    notes: list[str] = field(default_factory=list)
    top: str = ""
    page: int = 0

    @property
    def name(self) -> str:
        values = [v for v in self.cells.values() if v not in EMPTY]
        return next((v for v in values if not parse_range(v)), values[0] if values else "")


@dataclass
class Table:
    key: str
    number: str
    title: str
    chapter: str
    page_start: int
    page_end: int
    columns: list[str] = field(default_factory=list)
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    chunks: list[int] = field(default_factory=list)
    printed_start: str = ""
    printed_end: str = ""

    @property
    def label(self) -> str:
        return f"Tabela {self.number}: {self.title}" if self.number else self.title

    def row_text(self, row: Row) -> str:
        values = "; ".join(f"{k}: {v}" for k, v in row.cells.items() if v not in EMPTY)
        where = " > ".join(p for p in (self.label, row.group) if p)
        notes = f" ({'; '.join(row.notes)})" if row.notes else ""
        return f"{where} — {values}{notes}"


@dataclass
class _Column:
    name: str
    x0: float
    x1: float

    def distance(self, x0: float, x1: float) -> float:
        return min(abs(x0 - self.x0), abs((x0 + x1) / 2 - (self.x0 + self.x1) / 2), abs(x1 - self.x1))


def _unique(names: list[str]) -> list[str]:
    result = []
    for i, name in enumerate(names):
        if names.count(name) > 1:
            following = next((n for n in names[i + 1:] if n != name), "")
            name = f"{name} ({following})" if following else f"{name} {names[:i].count(name) + 1}"
        result.append(name)
    return result


def _stack(cells: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Junta as partes de um cabeçalho em várias linhas que ocupam a mesma coluna."""
    columns: list[list] = []
    for x0, x1, text in cells:
        same = next((c for c in columns if min(c[1], x1) - max(c[0], x0) > 0), None)
        if same:
            joined = f"{same[2]}{text}" if same[2].endswith("-") else f"{same[2]} {text}"
            same[0], same[1], same[2] = min(same[0], x0), max(same[1], x1), joined
        else:
            columns.append([x0, x1, text])
    return [tuple(c) for c in sorted(columns)]


def _split(header: list[tuple[float, float, str]], data: list[tuple[float, float, str]]) -> list[tuple[float, float, str]]:
    """Separa um cabeçalho colado ("d% Arma") que cobre duas colunas de dados."""
    result = []
    for x0, x1, text in header:
        below = [c for c in data if c[0] >= x0 - 6 and c[1] <= x1 + 6]
        words = text.split(" ", len(below) - 1) if len(below) > 1 else [text]
        if len(below) > 1 and len(words) == len(below):
            result += [(c[0], c[1], w) for c, w in zip(below, words)]
        else:
            result.append((x0, x1, text))
    return result


def _assign(cells: list[tuple[float, float, str]], columns: list[_Column]) -> dict[int, str]:
    placed: dict[int, str] = {}
    last = -1
    for n, (x0, x1, text) in enumerate(cells):
        remaining = len(cells) - n - 1
        options = range(last + 1, max(len(columns) - remaining, last + 2))
        best = min(min(options, key=lambda i: columns[min(i, len(columns) - 1)].distance(x0, x1)), len(columns) - 1)
        placed[best] = f"{placed[best]} {text}" if best in placed else text
        last = best
    return placed


def _segment_starts(names: list[str]) -> list[int]:
    return [i for i, n in enumerate(names) if n == names[0]] if len(names) > 2 else [0]


class _Builder:
    def __init__(self, table: Table):
        self.table = table
        self.columns: list[_Column] = []
        self.segments: list[range] = []
        self.header: list[str] = []
        self.pending: list[tuple[float, float, str]] = []
        self.complete = False
        self.tops: list[str] = []
        self.top = ""
        self.subgroups: dict[int, str] = {}
        self.open: dict[int, Row] = {}
        self.buffer: dict[int, list[Row]] = {}
        self.page = 0

    def _release(self) -> None:
        for s in sorted(self.buffer):
            self.table.rows += self.buffer[s]
        self.buffer = {}

    def _set_header(self, cells: list[tuple[float, float, str]]) -> None:
        self._release()
        names =[FOOTNOTE.sub(r"\1", text) for _, _, text in cells]
        starts = _segment_starts(names)
        self.segments = [range(a, b) for a, b in zip(starts, starts[1:] + [len(names)])]
        unique = [n for seg in self.segments for n in _unique(names[seg.start:seg.stop])]
        self.columns = [_Column(n, x0, x1) for n, (x0, x1, _) in zip(unique, cells)]
        self.table.columns = list(dict.fromkeys(self.table.columns + unique))
        self.header, self.top, self.subgroups, self.open = names, names[0], {}, {}
        self.tops.append(names[0])

    def _flush(self, data: list[tuple[float, float, str]] | None = None) -> None:
        stacked = _stack(self.pending)
        self.pending, self.complete = [], False
        if len(stacked) > 1:
            self._set_header(_split(stacked, data) if data and len(data) > len(stacked) else stacked)
        elif stacked and not self.columns:
            self.table.notes.append(stacked[0][2])

    def _segment_of(self, x0: float, x1: float) -> int:
        index = min(range(len(self.columns)), key=lambda i: self.columns[i].distance(x0, x1))
        return next(n for n, seg in enumerate(self.segments) if index in seg)

    def _labels(self, cells: list) -> bool:
        names = [t for _, _, t in _stack(self.pending)] if self.pending else self.header
        segments = len(_segment_starts(names)) if names else 0
        fresh = all(t not in names for _, _, t in cells)
        return segments > 1 and fresh and len(cells) == segments and len(cells) < len(names)

    def _group(self, s: int) -> str:
        segment = self.segments[s]
        names = {tuple(self.header[seg.start + 1:seg.stop]) for seg in self.segments}
        own = self.header[segment.start + 1] if len(names) > 1 and len(segment) > 1 else ""
        return " > ".join(p for p in (own, self.subgroups.get(s, "")) if p)

    def _add_row(self, placed: dict[int, str]) -> None:
        for s, segment in enumerate(self.segments):
            values = {self.columns[i].name: placed.get(i, "") for i in segment}
            if not any(values.values()):
                continue
            first = self.columns[segment.start].name
            previous = self.open.get(s)
            if not values[first] and previous and previous.group == self._group(s):
                values[first] = previous.cells[first]
            row = Row(self._group(s), values, top=self.top, page=self.page)
            self.buffer.setdefault(s, []).append(row)
            self.open[s] = row

    def _continue(self, x0: float, x1: float, text: str) -> bool:
        index = min(range(len(self.columns)), key=lambda i: self.columns[i].distance(x0, x1))
        s = self._segment_of(x0, x1)
        row = self.open.get(s)
        if row is None:
            return False
        name = self.columns[index].name
        if index == self.segments[s].start and not text[:1].islower() and row.cells.get(name):
            return False
        current = row.cells.get(name, "")
        row.cells[name] = f"{current[:-1]}{text}" if re.search(r"\w-$", current) else f"{current} {text}".strip()
        return True

    def _cells(self, el: Element) -> list[tuple[float, float, str]]:
        texts = [text for _, _, text in sorted(el.cells)]
        if len(texts) == 2 and len(texts[0]) <= 3 and len(texts[1]) > 60 and not el.bold:
            self.table.notes.append(f"{texts[0]} {texts[1]}")
            return []
        cells = []
        for x0, x1, text in sorted(el.cells or [(0.0, 0.0, el.text)]):
            dashes = text.split()
            if len(dashes) > 1 and set(dashes) <= {"—"}:
                width = (x1 - x0) / len(dashes)
                cells += [(x0 + i * width, x0 + (i + 1) * width, "—") for i in range(len(dashes))]
            elif len(el.cells) > 1 and not el.bold and NOTE.match(text):
                self.table.notes.append(text)
            elif len(el.cells) > 1 and re.match(r"^\d\) ", text) and self.table.notes:
                self.table.notes[-1] += f" {text}"
            else:
                cells.append((x0, x1, text))
        return cells

    def feed(self, el: Element) -> None:
        self.page = el.page_start
        cells = self._cells(el)
        if not cells:
            return
        text = cells[0][2]
        if len(cells) == 1 and not el.bold and (len(text) > 70 or NOTE.match(text)):
            self.table.notes.append(text)
            return
        if el.bold and len(cells) > 1 and (self.complete or self.columns) and self._labels(cells):
            if self.pending:
                self._flush()
            for x0, x1, label in cells:
                self.subgroups[self._segment_of(x0, x1)] = label
            self.open = {}
            return
        if el.bold and (len(cells) > 1 or (not self.columns and not self.complete)):
            self.pending += cells
            self.complete = self.complete or len(cells) > 1
            return
        if self.pending:
            self._flush(cells)
        if not self.columns:
            self._set_header([(x0, x1, f"Coluna {n}") for n, (x0, x1, _) in enumerate(cells, 1)])
        if len(cells) == 1:
            if el.bold:
                self.subgroups[self._segment_of(*cells[0][:2])] = text
                self.open = {}
                return
            if self._continue(*cells[0]):
                return
        self._add_row(_assign(cells, self.columns))

    def finish(self) -> Table:
        self._release()
        categories = len(set(self.tops)) > 1
        for row in self.table.rows:
            if categories and row.top in row.cells:
                row.cells = {("Nome" if k == row.top else k): v for k, v in row.cells.items()}
                row.group = " > ".join(p for p in (row.top, row.group) if p)
            for key, value in row.cells.items():
                match = FOOTNOTE.match(value)
                if match:
                    row.cells[key] = match.group(1)
                    row.notes += [n for n in self.table.notes if n.startswith(match.group(2))]
        if categories:
            self.table.columns = ["Nome"] + [c for c in self.table.columns if c not in self.tops]
        return self.table


def build_tables(entries, printed: dict[int, str]) -> list[Table]:
    """Uma tabela por chave: as partes "(Continuação)" entram na mesma tabela."""
    tables: dict[str, tuple[Table, _Builder]] = {}
    for entry in entries:
        if entry.heading_kind != "tabela":
            continue
        key = table_key(entry.title)
        if key not in tables:
            match = NUMBERED.match(entry.title)
            title = match.group(2) if match else CONTINUED.sub("", entry.title)
            table = Table(key, match.group(1) if match else "", title, entry.chapter,
                          entry.paragraphs[0].page_start, entry.paragraphs[-1].page_end)
            tables[key] = (table, _Builder(table))
        table, builder = tables[key]
        table.page_end = max(table.page_end, entry.paragraphs[-1].page_end)
        for element in entry.paragraphs:
            builder.feed(element)
    result = []
    for table, builder in tables.values():
        builder.finish()
        table.printed_start = printed.get(table.page_start, "")
        table.printed_end = printed.get(table.page_end, "")
        result.append(table)
    return result
