"""Trechos por entrada do livro (magia, ameaça, raça, poder...): um título, seu caminho e seu texto."""

import re
from dataclasses import dataclass, replace

from vector_builder.extract import Element, Extraction
from vector_builder.profile import Profile
from vector_builder.tables import Table, table_key

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
DETOUR_KINDS = ("quadro", "tabela")
ROW_KIND = "linha_tabela"


@dataclass
class Chunk:
    index: int
    title: str
    path: str
    chapter: str
    kind: str
    text: str
    page_start: int
    page_end: int
    printed_start: str
    printed_end: str
    table: str = ""
    row: int = 0


@dataclass
class _Entry:
    path: list[str]
    chapter: str
    heading_kind: str
    paragraphs: list[Element]

    @property
    def title(self) -> str:
        return self.path[-1] if self.path else self.chapter

    @property
    def size(self) -> int:
        return sum(len(p.text) for p in self.paragraphs)


def _entries(elements: list[Element]) -> list[_Entry]:
    entries: list[_Entry] = []
    stack: dict[int, str] = {}
    chapter, detour, detour_page = None, "", 0

    def open_entry(path: list[str], kind: str) -> _Entry:
        entries.append(_Entry(path, chapter, kind, []))
        return entries[-1]

    current = None
    for el in elements:
        if el.chapter != chapter:
            chapter, stack, detour, current = el.chapter, {}, "", None
        path = [stack[k] for k in sorted(stack)]
        if el.kind == "heading":
            detour, detour_page = el.detour, el.page_start
            if not el.detour:
                stack = {k: v for k, v in stack.items() if k < el.level} | {el.level: el.text}
                path = [stack[k] for k in sorted(stack)]
            current = open_entry(path + [el.text] if el.detour else path, el.heading_kind)
            continue
        if detour and (el.page_start != detour_page or (detour == "body" and el.body and not el.row)):
            detour, current = "", open_entry(path, "")
        if current is None:
            current = open_entry(path, "")
        current.paragraphs.append(el)
    return [e for e in entries if e.paragraphs]


def _merge_small(entries: list[_Entry], min_chars: int) -> list[_Entry]:
    merged: list[_Entry] = []
    for entry in entries:
        previous = merged[-1] if merged else None
        tables = DETOUR_KINDS[1] in (entry.heading_kind, previous.heading_kind if previous else "")
        if entry.size < min_chars and previous and previous.chapter == entry.chapter and not tables:
            first = entry.paragraphs[0]
            label = replace(first, text=f"{entry.title}: {first.text}") if entry.title != previous.title else first
            previous.paragraphs.extend([label, *entry.paragraphs[1:]])
        else:
            merged.append(entry)
    return merged


def _split_long(el: Element, limit: int) -> list[Element]:
    parts, current = [], ""
    for sentence in _SENTENCE_SPLIT.split(el.text):
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            parts.extend([current] if current else [])
            parts.append(sentence[:cut].strip())
            current, sentence = "", sentence[cut:].strip()
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    parts.extend([current] if current else [])
    return [replace(el, text=p) for p in parts]


def _pack(paragraphs: list[Element], max_chars: int, overlap: int) -> list[list[Element]]:
    pieces = [p for el in paragraphs for p in (_split_long(el, max_chars) if len(el.text) > max_chars else [el])]
    groups: list[list[Element]] = [[]]
    for piece in pieces:
        group = groups[-1]
        if group and sum(len(p.text) + 2 for p in group) + len(piece.text) > max_chars:
            tail = group[-1:] if len(group) > 1 and len(group[-1].text) <= overlap else []
            groups.append([*tail, piece])
        else:
            group.append(piece)
    return groups


def book_entries(extraction: Extraction, min_chars: int = 120) -> list[_Entry]:
    return _merge_small(_entries(extraction.elements), min_chars)


def chunk_book(extraction: Extraction, profile: Profile, max_chars: int = 2400,
               overlap: int = 300, min_chars: int = 120) -> list[Chunk]:
    chunks: list[Chunk] = []
    printed = extraction.printed
    for entry in book_entries(extraction, min_chars):
        full_text = "\n\n".join(p.text for p in entry.paragraphs)
        kind = (entry.heading_kind if entry.heading_kind in DETOUR_KINDS
                else profile.kind_of(entry.title, full_text, entry.chapter))
        for group in _pack(entry.paragraphs, max_chars, overlap):
            start, end = group[0].page_start, max(p.page_end for p in group)
            chunks.append(Chunk(
                index=len(chunks),
                title=entry.title,
                path=" > ".join(entry.path),
                chapter=entry.chapter,
                kind=kind,
                text="\n\n".join(p.text for p in group),
                page_start=start,
                page_end=end,
                printed_start=printed.get(start, ""),
                printed_end=printed.get(end, ""),
                table=table_key(entry.title) if kind == DETOUR_KINDS[1] else "",
            ))
    return chunks


def row_chunks(tables: list[Table], printed: dict[int, str], start: int) -> list[Chunk]:
    """Um trecho curto por linha de tabela, com o nome da tabela e do grupo, para a busca achar o item exato."""
    chunks = []
    for table in tables:
        for position, row in enumerate(table.rows, start=1):
            page = row.page or table.page_start
            chunks.append(Chunk(
                index=start + len(chunks),
                title=table.label,
                path=" > ".join(p for p in (table.label, row.group) if p),
                chapter=table.chapter,
                kind=ROW_KIND,
                text=table.row_text(row),
                page_start=page,
                page_end=page,
                printed_start=printed.get(page, ""),
                printed_end=printed.get(page, ""),
                table=table.key,
                row=position,
            ))
    return chunks


def embedding_text(book_title: str, chunk: Chunk) -> str:
    header = " > ".join(part for part in (book_title, chunk.chapter, chunk.path) if part)
    return f"{header}\n\n{chunk.text}"
