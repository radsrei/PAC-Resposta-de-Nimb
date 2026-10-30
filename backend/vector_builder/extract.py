"""Extração do livro guiada pelo perfil tipográfico: títulos, parágrafos e linhas de tabela, já sem margens."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from vector_builder.profile import FontRule, Profile

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
SENTENCE_END = re.compile(r"[.!?:;)”\"»]$")
CELL_GAP = 12.0
TABLE_GAP = 5.0
TAB = 0.5
INDENT = 8.0
BOLD = re.compile(r"Bold|Black")
MARKER = re.compile(r"^([•●▪◦·]|\d{1,2}\))$")


@dataclass
class Element:
    kind: str
    text: str
    chapter: str
    page_start: int
    page_end: int
    level: int = 0
    heading_kind: str = ""
    detour: str = ""
    body: bool = True
    row: bool = False
    bold: bool = False
    cells: list[tuple[float, float, str]] = field(default_factory=list)


@dataclass
class Extraction:
    elements: list[Element]
    printed: dict[int, str]
    page_count: int
    skipped: list[int] = field(default_factory=list)
    empty: list[int] = field(default_factory=list)


@dataclass
class _Line:
    text: str
    rule: FontRule | None
    body: bool
    indent: bool
    cells: list[tuple[float, float, str]]
    block: int
    bold: bool


def _zone(bbox, height: float, margin: float) -> str:
    if bbox[3] <= height * margin:
        return "top"
    if bbox[1] >= height * (1 - margin):
        return "bottom"
    return "body"


def _chapters(toc: list, page_count: int) -> dict[int, str]:
    starts = sorted((page, title.strip()) for level, title, page in toc if level == 1 and page >= 1)
    result, current = {}, ""
    for page in range(1, page_count + 1):
        while starts and starts[0][0] <= page:
            current = starts.pop(0)[1]
        result[page] = current
    return result


def _fill_printed(found: dict[int, str], page_count: int) -> dict[int, str]:
    offsets = {p: p - int(v) for p, v in found.items() if v.isdigit()}
    if not offsets:
        return found
    result = dict(found)
    for page in range(1, page_count + 1):
        if page not in result:
            nearest = min(offsets, key=lambda p: abs(p - page))
            number = page - offsets[nearest]
            result[page] = str(number) if number >= 1 else ""
    return result


def _join(left: str, right: str) -> str:
    if re.search(r"\w-$", left) and right[:1].islower():
        return left[:-1] + right
    return f"{left} {right}"


def _line_text(line: dict) -> str:
    return "".join(s["text"] for s in line["spans"])


def _rows(lines: list[dict]) -> list[list[dict]]:
    rows: list[list[dict]] = []
    for line in lines:
        same_row = rows and abs(rows[-1][0]["bbox"][3] - line["bbox"][3]) <= 2
        if same_row and any(abs(o["bbox"][0] - line["bbox"][0]) < 1 and _line_text(o) == _line_text(line)
                            for o in rows[-1]):
            continue
        if same_row:
            rows[-1].append(line)
        else:
            rows.append([line])
    return rows


def _is_tab(span: dict) -> bool:
    return not span["text"].strip() and span["bbox"][2] - span["bbox"][0] > TAB * span["size"]


def _glue(parts: list[str]) -> str:
    text = ""
    for part in parts:
        if text and re.search(r"[:;,.!?)]$", text) and part[:1].isalnum():
            text += " "
        text += part
    return " ".join(text.split())


class _PageReader:
    def __init__(self, page, profile: Profile, printed: dict[int, str]):
        self.page, self.profile, self.printed = page, profile, printed
        self.dropcap = ""

    def _keep(self, span: dict) -> tuple[str, FontRule | None] | None:
        text = EMAIL.sub("", span["text"])
        if not text.strip():
            return None
        zone = _zone(span["bbox"], self.page.rect.height, self.profile.margin)
        rule = self.profile.rule_for(span["font"], span["size"], zone)
        role = rule.role if rule else None
        if role == "page_number" or (role is None and zone != "body" and text.strip().isdigit()):
            self.printed[self.page.number + 1] = text.strip()
            return None
        if role == "drop" or (role is None and zone != "body" and self.profile.drop_unmatched_margin):
            return None
        if role == "decor":
            letter = text.strip()
            self.dropcap = letter if len(letter) == 1 and letter.isalpha() else self.dropcap
            return None
        return text, rule if role == "heading" else None

    def _heading(self, cells: list) -> FontRule | None:
        suffix = self.profile.title_suffix
        first, rest = cells[0], cells[1:]
        if not all(first[3]):
            return None
        if not all(all(rules) or (suffix and re.search(suffix, text)) for _, _, text, rules in rest):
            return None
        return min((r for cell in cells for r in cell[3] if r), key=lambda r: r.level)

    def _segments(self, line: dict):
        split, space = False, False
        for span in line["spans"]:
            if _is_tab(span):
                split = True
                continue
            if not span["text"].strip():
                space = True
                continue
            for n, text in enumerate(span["text"].split("\t")):
                kept = self._keep({**span, "text": text})
                if kept:
                    yield span, (" " if space else "") + kept[0], kept[1], split or n > 0
                    split, space = False, False
            split = split or span["text"].endswith("\t")

    def _row(self, row: list[dict], block: int, left: float) -> _Line | None:
        cells, spans, previous = [], [], None
        for line in sorted(row, key=lambda l: l["bbox"][0]):
            body = all(self.profile.is_body(s["font"], s["size"]) for s in line["spans"] if s["text"].strip())
            gap = CELL_GAP if body and (previous is None or previous[1]) else TABLE_GAP
            new_line = True
            for span, text, rule, split in self._segments(line):
                apart = previous is not None and new_line and line["bbox"][0] - previous[0] > gap
                if not cells or split or apart:
                    cells.append([span["bbox"][0], span["bbox"][2], [[text]], []])
                elif new_line:
                    cells[-1][2].append([text])
                else:
                    cells[-1][2][-1].append(text)
                cells[-1][1] = max(cells[-1][1], span["bbox"][2])
                cells[-1][3].append(rule)
                spans.append(span)
                new_line = False
            if not new_line:
                previous = (max(s["bbox"][2] for s in line["spans"] if s["text"].strip()), body)
        if not cells:
            return None
        texts = [" ".join(_glue(parts) for parts in lines) for _, _, lines, _ in cells]
        while len(texts) > 1 and MARKER.match(texts[0]):
            texts[:2] = [f"{texts[0]} {texts[1]}"]
            cells[:2] = [[cells[0][0], cells[1][1], [], cells[0][3] + cells[1][3]]]
        rule = self._heading([(x0, x1, text, rules) for (x0, x1, _, rules), text in zip(cells, texts)])
        if self.dropcap and rule is None:
            texts[0], self.dropcap = self.dropcap + texts[0], ""
        return _Line(
            text=" ".join(texts) if rule else " | ".join(texts),
            rule=rule,
            body=self.profile.is_body(spans[0]["font"], spans[0]["size"]),
            indent=row[0]["bbox"][0] > left + INDENT,
            cells=[(round(x0, 1), round(x1, 1), text) for (x0, x1, _, _), text in zip(cells, texts)],
            block=block,
            bold=all(BOLD.search(span["font"]) for span in spans),
        )

    def lines(self) -> list[_Line]:
        result = []
        for index, block in enumerate(self.page.get_text("dict")["blocks"]):
            if block.get("type") != 0 or not block.get("lines"):
                continue
            left = min(l["bbox"][0] for l in block["lines"])
            result.extend(line for row in _rows(block["lines"]) if (line := self._row(row, index, left)))
        return result


def _add(elements: list[Element], line: _Line, page: int, chapter: str, previous: _Line | None,
         suffix: re.Pattern | None) -> None:
    last = elements[-1] if elements else None
    same_chapter = last is not None and last.chapter == chapter
    after_heading = same_chapter and last.kind == "heading" and previous is not None and previous.rule is not None

    if suffix and after_heading and len(line.cells) == 1 and suffix.search(line.text):
        last.text = f"{last.text} {line.text}"
        return
    if line.rule:
        if after_heading and previous.rule == line.rule and previous.block == line.block:
            last.text = f"{last.text} {line.text}"
            return
        elements.append(Element("heading", line.text, chapter, page, page, line.rule.level,
                                line.rule.kind, line.rule.detour))
        return

    row = len(line.cells) > 1
    same_paragraph = (not line.indent and previous is not None
                      and previous.block == line.block and previous.rule is None)
    wraps = (same_chapter and last.kind == "text" and last.row and not row and last.page_end == page
             and abs(last.cells[-1][0] - line.cells[0][0]) <= INDENT)
    if wraps:
        x0, x1, cell = last.cells[-1]
        last.cells[-1] = (x0, max(x1, line.cells[0][1]), _join(cell, line.text))
        last.text = " | ".join(text for _, _, text in last.cells)
        return
    same_column = line.body or not last or not last.cells or abs(last.cells[0][0] - line.cells[0][0]) <= INDENT
    continues = (
        same_chapter and last.kind == "text" and not last.row and not row and last.body == line.body
        and ((same_paragraph and same_column) or not SENTENCE_END.search(last.text))
    )
    if continues:
        last.text = _join(last.text, line.text)
        last.page_end = page
        if last.bold and line.bold:
            last.cells = last.cells + line.cells
    else:
        elements.append(Element("text", line.text, chapter, page, page, body=line.body, row=row,
                                bold=line.bold, cells=line.cells))


def extract(pdf_path: Path, profile: Profile) -> Extraction:
    import pymupdf

    suffix = re.compile(profile.title_suffix) if profile.title_suffix else None
    with pymupdf.open(pdf_path) as doc:
        page_count = doc.page_count
        chapters = _chapters(doc.get_toc(simple=True), page_count)
        skip = set(profile.skip_sections)
        result = Extraction([], {}, page_count)
        for page in doc:
            number = page.number + 1
            chapter = chapters.get(number, "")
            if chapter in skip:
                result.skipped.append(number)
                continue
            lines = _PageReader(page, profile, result.printed).lines()
            if not lines:
                result.empty.append(number)
            previous = None
            for line in lines:
                _add(result.elements, line, number, chapter, previous, suffix)
                previous = line
    result.printed = _fill_printed(result.printed, page_count)
    return result
