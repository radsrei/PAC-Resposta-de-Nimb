"""
Extração do texto do livro para indexação (PyMuPDF).

Cuidados para a qualidade dos trechos:
- lê por blocos, na ordem do conteúdo do PDF (respeita colunas, ao contrário
  de ordenar por posição, que mistura as colunas de livros de RPG);
- remove cabeçalhos e rodapés repetidos (título do livro, número da página);
- junta palavras hifenizadas no fim da linha e quebras de linha dentro do parágrafo;
- usa o sumário (bookmarks) do PDF para saber o capítulo e a seção de cada página.
"""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

MARGIN_RATIO = 0.08          # faixa do topo e do rodapé onde ficam cabeçalhos
REPEATED_MIN_PAGES = 3
REPEATED_RATIO = 0.2         # bloco de margem presente em 20% das páginas = repetido


@dataclass
class Page:
    number: int              # página física do arquivo, começando em 1
    text: str
    chapter: str
    section: str


def _margin_key(text: str) -> str:
    # Números variam de página para página ("Capítulo 3 • 127"): viram '#'
    return re.sub(r"\d+", "#", " ".join(text.lower().split()))


def _clean_block(text: str) -> str:
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)   # hifenização no fim da linha
    text = re.sub(r"[ \t]*\n[ \t]*", " ", text)     # quebras dentro do parágrafo
    return " ".join(text.split())


def _is_page_number(text: str) -> bool:
    return bool(re.fullmatch(r"[\divxlcdm\s.\-–|•]+", text.lower()))


def _sections_by_page(toc: list, page_count: int) -> dict[int, tuple[str, str]]:
    """Capítulo (nível 1) e seção (nível mais profundo até 3) vigentes em cada página."""
    result: dict[int, tuple[str, str]] = {}
    entries = sorted(((p, lvl, title.strip()) for lvl, title, p in toc if p >= 1), key=lambda e: (e[0], e[1]))
    chapter, path = "", {}
    idx = 0
    for page in range(1, page_count + 1):
        while idx < len(entries) and entries[idx][0] <= page:
            _, lvl, title = entries[idx]
            if lvl == 1:
                chapter, path = title, {}
            elif lvl <= 3:
                path = {k: v for k, v in path.items() if k < lvl}
                path[lvl] = title
            idx += 1
        section = path[max(path)] if path else ""
        result[page] = (chapter, section)
    return result


def extract_pages(pdf_path: Path) -> list[Page]:
    import pymupdf

    with pymupdf.open(pdf_path) as doc:
        raw: list[list[tuple[str, bool]]] = []   # por página: (texto, está na margem)
        for page in doc:
            height = page.rect.height
            blocks = []
            for x0, y0, x1, y1, text, _no, block_type in page.get_text("blocks"):
                if block_type != 0 or not text.strip():
                    continue
                in_margin = y1 <= height * MARGIN_RATIO or y0 >= height * (1 - MARGIN_RATIO)
                blocks.append((text, in_margin))
            raw.append(blocks)
        toc = doc.get_toc(simple=True)

    page_count = len(raw)
    margin_counts = Counter(
        key for blocks in raw for key in {_margin_key(t) for t, m in blocks if m}
    )
    threshold = max(REPEATED_MIN_PAGES, page_count * REPEATED_RATIO)
    sections = _sections_by_page(toc, page_count)

    pages = []
    for number, blocks in enumerate(raw, start=1):
        paragraphs = []
        for text, in_margin in blocks:
            cleaned = _clean_block(text)
            if in_margin and (margin_counts[_margin_key(text)] >= threshold or _is_page_number(cleaned)):
                continue
            if cleaned:
                paragraphs.append(cleaned)
        chapter, section = sections.get(number, ("", ""))
        pages.append(Page(number, "\n\n".join(paragraphs), chapter, section))
    return pages
