"""
Divisão do livro em trechos (chunks) para o banco vetorial.

- Respeita parágrafos e frases: só corta no meio de uma frase se ela sozinha
  passar do tamanho máximo.
- Um trecho nunca mistura capítulos ou seções diferentes.
- Pode atravessar páginas da mesma seção; guarda a página inicial e a final.
- Sobreposição (overlap) com o fim do trecho anterior, para não perder o
  contexto de uma explicação que começa num trecho e termina no outro.
"""

import re
from dataclasses import dataclass

from vector_builder.extract import Page

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Unit:
    text: str
    page: int
    chapter: str
    section: str


@dataclass
class Chunk:
    index: int
    text: str
    page_start: int
    page_end: int
    chapter: str
    section: str


def _split_long(text: str, limit: int) -> list[str]:
    """Quebra um parágrafo grande em frases e, se preciso, em palavras."""
    parts, current = [], ""
    for sentence in _SENTENCE_SPLIT.split(text):
        while len(sentence) > limit:  # frase gigante (tabela, lista sem pontuação)
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def _units(pages: list[Page], chunk_size: int) -> list[Unit]:
    units = []
    for page in pages:
        for paragraph in page.text.split("\n\n"):
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            pieces = [paragraph] if len(paragraph) <= chunk_size else _split_long(paragraph, chunk_size)
            units.extend(Unit(p, page.number, page.chapter, page.section) for p in pieces)
    return units


def chunk_pages(pages: list[Page], chunk_size: int = 1200, overlap: int = 200, min_chars: int = 80) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[Unit] = []

    def length(units: list[Unit]) -> int:
        return sum(len(u.text) for u in units) + max(len(units) - 1, 0) * 2

    def flush(keep_overlap: bool) -> list[Unit]:
        if not current:
            return []
        text = "\n\n".join(u.text for u in current)
        if len(text) >= min_chars or not chunks:
            chunks.append(Chunk(len(chunks), text, current[0].page, current[-1].page,
                                current[0].chapter, current[0].section))
        if not keep_overlap:
            return []
        tail: list[Unit] = []
        for unit in reversed(current):
            if length([unit, *tail]) > overlap:
                break
            tail.insert(0, unit)
        # Se o último parágrafo sozinho já passa do overlap, não há sobreposição
        return tail if len(tail) < len(current) else []

    for unit in _units(pages, chunk_size):
        same_section = current and (unit.chapter, unit.section) == (current[0].chapter, current[0].section)
        if current and not same_section:
            flush(keep_overlap=False)
            current = []
        elif current and length([*current, unit]) > chunk_size:
            current = flush(keep_overlap=True)
        current.append(unit)
    flush(keep_overlap=False)
    return chunks


def embedding_text(book_title: str, chunk: Chunk) -> str:
    """
    Texto usado para gerar o embedding: o trecho com um cabeçalho de contexto
    (livro > capítulo > seção). Ajuda a busca a achar o trecho certo quando o
    parágrafo, sozinho, não diz de que assunto está falando.
    """
    header = " > ".join(part for part in (book_title, chunk.chapter, chunk.section) if part)
    return f"{header}\n\n{chunk.text}"
