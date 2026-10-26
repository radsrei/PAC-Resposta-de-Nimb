"""Extração do livro guiada pelo perfil tipográfico: títulos, parágrafos e linhas de tabela, já sem margens."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from vector_builder.profile import FontRule, Profile

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
SENTENCE_END = re.compile(r"[.!?:;)”\"»]$")
CELL_GAP = 12.0
INDENT = 8.0


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
    cells: int
    block: int


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

    def _row(self, row: list[dict], block: int, left: float) -> _Line | None:
        cells, first_span = [], None
        for line in row:
            kept = [(span, *k) for span in line["spans"] if (k := self._keep(span))]
            if kept:
                first_span = first_span or kept[0][0]
                rules = [rule for _, _, rule in kept]
                cells.append((line["bbox"][0], line["bbox"][2], _glue([text for _, text, _ in kept]), rules))
        if not cells:
            return None
        rule = self._heading(cells)
        gaps = [x0 - prev_x1 > CELL_GAP for (_, prev_x1, _, _), (x0, _, _, _) in zip(cells, cells[1:])]
        text = cells[0][2]
        for wide, (_, _, cell, _) in zip(gaps, cells[1:]):
            text += (" | " if wide and rule is None else " ") + cell
        if self.dropcap and rule is None:
            text, self.dropcap = self.dropcap + text, ""
        return _Line(
            text=text,
            rule=rule,
            body=self.profile.is_body(first_span["font"], first_span["size"]),
            indent=row[0]["bbox"][0] > left + INDENT,
            cells=1 if rule else sum(gaps) + 1,
            block=block,
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

    if suffix and after_heading and suffix.search(line.text):
        last.text = f"{last.text} {line.text}"
        return
    if line.rule:
        if after_heading and previous.rule == line.rule and previous.block == line.block:
            last.text = f"{last.text} {line.text}"
            return
        elements.append(Element("heading", line.text, chapter, page, page, line.rule.level,
                                line.rule.kind, line.rule.detour))
        return

    row = line.cells > 1
    same_paragraph = (not line.indent and previous is not None
                      and previous.block == line.block and previous.rule is None)
    continues = (
        same_chapter and last.kind == "text" and not last.row and not row and last.body == line.body
        and (same_paragraph or not SENTENCE_END.search(last.text))
    )
    if continues:
        last.text = _join(last.text, line.text)
        last.page_end = page
    else:
        elements.append(Element("text", line.text, chapter, page, page, body=line.body, row=row))


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
