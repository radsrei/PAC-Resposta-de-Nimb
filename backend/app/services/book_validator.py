"""
Validação de livro: compara a impressão digital de um PDF com o catálogo.

Pontuação (0 a 1) contra cada livro do catálogo:

    frases de controle   0.55 x (frases encontradas / total)
    número de páginas    0.15 (dentro da tolerância)
    tamanho do arquivo   0.10 (dentro da tolerância)
    metadados do PDF     0.10 x (campos iguais / campos no catálogo)
    tamanho da página    0.10 (diferença de até 2 pt)

Um arquivo idêntico ao original (SHA-256 no catálogo) é aceito direto. Nos
demais casos são exigidas as duas condições: pontuação >= `min_score` e pelo
menos `min_probes` frases encontradas. As frases provam que o conteúdo do livro
está no arquivo; metadados e tamanho, sozinhos, são fáceis de falsificar.
"""

import math
from dataclasses import dataclass, field
from typing import Any

from app.services.book_fingerprint import PdfFingerprint, normalize_text, text_similarity

WEIGHTS = {"probes": 0.55, "page_count": 0.15, "size": 0.10, "metadata": 0.10, "page_size": 0.10}
PROBE_MIN_SIMILARITY = 0.85
PAGE_SIZE_TOLERANCE_PT = 2.0


@dataclass
class Check:
    name: str
    passed: bool
    score: float  # contribuição na pontuação final
    detail: str   # só para log / ferramenta de linha de comando


@dataclass
class BookMatch:
    book: dict[str, Any]
    score: float
    accepted: bool
    exact: bool
    probes_found: int
    probes_required: int
    checks: list[Check] = field(default_factory=list)


def _probes_required(book: dict[str, Any]) -> int:
    total = len(book["probes"])
    if book["min_probes"] is not None:
        return min(int(book["min_probes"]), total)
    return math.ceil(total * 0.6)


def _find_probe(fp: PdfFingerprint, probe: dict[str, Any], window: int) -> tuple[float, int | None]:
    """Melhor semelhança da frase nas páginas próximas à esperada."""
    needle = normalize_text(probe["text"])
    expected = int(probe["page"])
    best, best_page = 0.0, None
    # Página esperada primeiro, depois as vizinhas (1, -1, 2, -2...)
    offsets = [0] + [d for k in range(1, window + 1) for d in (k, -k)]
    for offset in offsets:
        page = expected + offset
        similarity = text_similarity(needle, fp.page_text(page))
        if similarity > best:
            best, best_page = similarity, page
        if best >= 0.99:
            break
    return best, best_page


def match_book(fp: PdfFingerprint, book: dict[str, Any]) -> BookMatch:
    required = _probes_required(book)
    if fp.sha256 in book["sha256"]:
        return BookMatch(book, 1.0, True, True, len(book["probes"]), required,
                         [Check("sha256", True, 1.0, "arquivo idêntico ao original")])

    checks: list[Check] = []

    # Frases de controle
    found = 0
    misses = []
    for probe in book["probes"]:
        similarity, page = _find_probe(fp, probe, int(book["probe_page_window"]))
        if similarity >= PROBE_MIN_SIMILARITY:
            found += 1
        else:
            misses.append(f"p.{probe['page']} ({similarity:.0%})")
    total = len(book["probes"])
    ratio = found / total if total else 0.0
    checks.append(Check(
        "probes", total > 0 and found >= required, WEIGHTS["probes"] * ratio,
        f"{found}/{total} frases (mínimo {required})" + (f"; faltaram: {', '.join(misses)}" if misses else ""),
    ))

    # Número de páginas
    if book.get("page_count"):
        diff = abs(fp.page_count - int(book["page_count"]))
        ok = diff <= int(book["page_count_tolerance"])
        checks.append(Check("page_count", ok, WEIGHTS["page_count"] if ok else 0.0,
                            f"{fp.page_count} páginas (catálogo: {book['page_count']})"))

    # Tamanho do arquivo
    if book.get("size_bytes"):
        expected = int(book["size_bytes"])
        diff_pct = abs(fp.size_bytes - expected) / expected * 100
        ok = diff_pct <= float(book["size_tolerance_pct"])
        checks.append(Check("size", ok, WEIGHTS["size"] if ok else 0.0,
                            f"{fp.size_bytes} bytes ({diff_pct:.1f}% de diferença)"))

    # Metadados
    expected_meta = {k: v for k, v in book["metadata"].items() if v}
    if expected_meta:
        equal = sum(
            1 for k, v in expected_meta.items()
            if normalize_text(fp.metadata.get(k, "")) == normalize_text(str(v))
        )
        meta_ratio = equal / len(expected_meta)
        checks.append(Check("metadata", meta_ratio == 1.0, WEIGHTS["metadata"] * meta_ratio,
                            f"{equal}/{len(expected_meta)} campos iguais"))

    # Tamanho da página
    if book.get("page_size") and fp.page_size:
        w, h = book["page_size"]
        ok = (abs(fp.page_size[0] - w) <= PAGE_SIZE_TOLERANCE_PT
              and abs(fp.page_size[1] - h) <= PAGE_SIZE_TOLERANCE_PT)
        checks.append(Check("page_size", ok, WEIGHTS["page_size"] if ok else 0.0,
                            f"{fp.page_size[0]}x{fp.page_size[1]} pt (catálogo: {w}x{h})"))

    score = round(sum(c.score for c in checks), 4)
    accepted = total > 0 and found >= required and score >= float(book["min_score"])
    return BookMatch(book, score, accepted, False, found, required, checks)


def find_best_match(fp: PdfFingerprint, books: list[dict[str, Any]]) -> BookMatch | None:
    """Livro do catálogo mais parecido com o PDF. Aceitos têm prioridade."""
    matches = [match_book(fp, book) for book in books]
    if not matches:
        return None
    return max(matches, key=lambda m: (m.accepted, m.score))
