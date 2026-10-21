"""
Cadastro do livro no catálogo: extrai a impressão digital do PDF original e
escolhe as frases de controle usadas para reconhecer cópias do livro.
"""

import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services import book_catalog
from app.services.book_fingerprint import PdfFingerprint, fingerprint_pdf, normalize_text, text_similarity
from app.services.book_validator import PROBE_MIN_SIMILARITY

# Campos que o administrador pode ajustar à mão no catálogo: preservados ao
# recadastrar o mesmo livro
_TUNABLE = ("size_tolerance_pct", "page_count_tolerance", "probe_page_window", "min_probes", "min_score")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?;:])\s+|\n{2,}")


def _clean(text: str) -> str:
    text = re.sub(r"-\s*\n\s*", "", text)
    return " ".join(text.split())


def _without_repeated_lines(raw_pages: dict[int, str]) -> dict[int, str]:
    """
    Remove cabeçalhos e rodapés (linhas repetidas em muitas páginas, números de
    página): uma frase de controle não pode depender deles, que mudam entre edições.
    """
    key = lambda line: re.sub(r"\d+", "#", " ".join(line.lower().split()))
    counts = Counter(k for text in raw_pages.values() for k in {key(l) for l in text.splitlines() if l.strip()})
    threshold = max(3, len(raw_pages) * 0.2)
    return {
        page: "\n".join(
            line for line in text.splitlines()
            if line.strip() and counts[key(line)] < threshold and not re.fullmatch(r"[\d\s.\-–|•]+", line)
        )
        for page, text in raw_pages.items()
    }


def _candidate_sentences(raw: str, min_words: int, max_words: int) -> list[str]:
    sentences = []
    for part in _SENTENCE_SPLIT.split(raw):
        sentence = _clean(part)
        words = sentence.split()
        norm = normalize_text(sentence)
        letters = sum(c.isalpha() for c in sentence)
        if (min_words <= len(words) <= max_words and len(norm) >= 40
                and letters / max(len(sentence), 1) >= 0.7):
            sentences.append(sentence)
    # Preferência por frases de tamanho médio (menos genéricas, menos frágeis)
    middle = (min_words + max_words) / 2
    return sorted(sentences, key=lambda s: abs(len(s.split()) - middle))


def select_probes(fp: PdfFingerprint, count: int = 8, min_words: int = 8, max_words: int = 25) -> list[dict[str, Any]]:
    """
    Escolhe `count` frases espalhadas pelo livro (entre 5% e 95% das páginas,
    evitando capa, créditos e índice). Cada frase precisa ser única: aparece só
    na própria página, para não ser reconhecida em outro trecho ou livro.
    """
    n = fp.page_count
    first, last = (1, n) if n < 20 else (max(1, round(n * 0.05)), min(n, round(n * 0.95)))
    if count == 1:
        targets = [(first + last) // 2]
    else:
        targets = [round(first + i * (last - first) / (count - 1)) for i in range(count)]

    all_pages = {p: fp.page_text(p) for p in range(1, n + 1)}
    content = _without_repeated_lines({p: fp.raw_page_text(p) for p in range(1, n + 1)})
    probes, used = [], set()
    for target in targets:
        for offset in (0, 1, -1, 2, -2, 3, -3):
            page = target + offset
            if page in used or not first <= page <= last:
                continue
            choice = next(
                (s for s in _candidate_sentences(content[page], min_words, max_words)
                 if sum(normalize_text(s) in text for text in all_pages.values()) == 1),
                None,
            )
            if choice:
                probes.append({"page": page, "text": choice})
                used.add(page)
                break
    return probes


def parse_manual_probe(value: str) -> dict[str, Any]:
    """'12:texto da frase' -> {"page": 12, "text": "texto da frase"}"""
    page, sep, text = value.partition(":")
    if not sep or not page.strip().isdigit() or not text.strip():
        raise ValueError(f"Frase inválida {value!r}. Use o formato PAGINA:texto")
    return {"page": int(page), "text": text.strip()}


def build_entry(
    pdf_path: Path,
    book_id: str,
    title: str,
    probe_count: int = 8,
    manual_probes: list[dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Monta a entrada do catálogo. Devolve (entrada, avisos)."""
    book_catalog.book_dir(book_id)  # valida o identificador
    fp = fingerprint_pdf(pdf_path.read_bytes())
    warnings: list[str] = []

    if manual_probes:
        probes = manual_probes
        for probe in probes:
            similarity = text_similarity(normalize_text(probe["text"]), fp.page_text(probe["page"]))
            if similarity < PROBE_MIN_SIMILARITY:
                warnings.append(
                    f"A frase da página {probe['page']} não foi encontrada nela ({similarity:.0%}). "
                    "Confira o número da página (página física do arquivo, começando em 1)."
                )
    else:
        probes = select_probes(fp, probe_count)
    if len(probes) < 3:
        warnings.append(
            f"Só {len(probes)} frase(s) de controle. O PDF pode não ter camada de texto "
            "(digitalizado sem OCR): só cópias idênticas (SHA-256) serão aceitas."
        )

    existing = book_catalog.get_book(book_id) or {}
    entry: dict[str, Any] = {
        "id": book_id,
        "title": title,
        "sha256": sorted({*existing.get("sha256", []), fp.sha256}),
        "size_bytes": fp.size_bytes,
        "page_count": fp.page_count,
        "page_size": list(fp.page_size) if fp.page_size else None,
        "metadata": fp.metadata,
        "probes": probes,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    for key in _TUNABLE:
        entry[key] = existing.get(key, book_catalog.DEFAULTS[key])
    return entry, warnings
