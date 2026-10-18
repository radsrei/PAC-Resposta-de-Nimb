"""
Impressão digital de um PDF: os sinais usados para reconhecer um livro.

Usado nos dois lados, com o mesmo código, para que os valores sejam comparáveis:
- `vector_builder` extrai a impressão digital do PDF original e grava no catálogo;
- a API extrai a do PDF enviado pelo usuário e compara com o catálogo.

Sinais: SHA-256 do arquivo, tamanho, número de páginas, metadados do PDF,
tamanho da página e o texto de páginas específicas (frases de controle).
Só as páginas necessárias são lidas, sob demanda.
"""

import hashlib
import io
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.core.exceptions import AppError

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError:  # pragma: no cover - dependência obrigatória
    PdfReader = None
    PdfReadError = Exception

# Metadados do PDF considerados na comparação (chave do catálogo -> chave do PDF)
METADATA_KEYS = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "creator": "/Creator",
    "producer": "/Producer",
}


def normalize_text(text: str) -> str:
    """Texto comparável: sem acentos, hifenização, pontuação ou espaços extras."""
    text = re.sub(r"-\s*\n\s*", "", text)  # junta palavras quebradas no fim da linha
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return " ".join(text.split())


def text_similarity(needle: str, haystack: str) -> float:
    """
    Semelhança (0 a 1) entre uma frase e o melhor trecho de mesmo tamanho de uma
    página, ambos já normalizados. 1.0 quando a frase aparece exatamente.
    Tolera pequenas diferenças de extração (ligaduras, espaços, OCR).
    """
    if not needle or not haystack:
        return 0.0
    if needle in haystack:
        return 1.0
    needle_words = needle.split()
    words = haystack.split()
    size = len(needle_words)
    if len(words) < size:
        return SequenceMatcher(None, needle, haystack).ratio()

    best = 0.0
    matcher = SequenceMatcher(autojunk=False)
    matcher.set_seq2(needle)
    for start in range(0, len(words) - size + 1):
        matcher.set_seq1(" ".join(words[start:start + size]))
        if matcher.real_quick_ratio() <= best or matcher.quick_ratio() <= best:
            continue
        best = max(best, matcher.ratio())
        if best >= 0.99:
            break
    return best


@dataclass
class PdfFingerprint:
    sha256: str
    size_bytes: int
    page_count: int
    metadata: dict[str, str]
    page_size: tuple[float, float] | None
    _reader: "PdfReader" = field(repr=False)
    _page_cache: dict[int, str] = field(default_factory=dict, repr=False)

    def raw_page_text(self, page: int) -> str:
        """Texto da página como extraído do PDF (1 = primeira página do arquivo)."""
        if page < 1 or page > self.page_count:
            return ""
        try:
            return self._reader.pages[page - 1].extract_text() or ""
        except Exception:  # página corrompida não derruba a validação
            return ""

    def page_text(self, page: int) -> str:
        """Texto normalizado da página `page` (1 = primeira página do arquivo)."""
        if page not in self._page_cache:
            self._page_cache[page] = normalize_text(self.raw_page_text(page))
        return self._page_cache[page]


def _read_metadata(reader: "PdfReader") -> dict[str, str]:
    try:
        info = reader.metadata or {}
    except Exception:
        return {}
    data = {}
    for key, pdf_key in METADATA_KEYS.items():
        value = info.get(pdf_key)
        if value:
            data[key] = str(value).strip()[:300]
    return data


def _read_page_size(reader: "PdfReader") -> tuple[float, float] | None:
    try:
        box = reader.pages[0].mediabox
        return (round(float(box.width), 1), round(float(box.height), 1))
    except Exception:
        return None


def fingerprint_pdf(data: bytes) -> PdfFingerprint:
    """Lê o PDF em memória e devolve sua impressão digital. Nada é gravado em disco."""
    if PdfReader is None:
        raise AppError("Pacote 'pypdf' não instalado. Rode: pip install pypdf")
    if not data.startswith(b"%PDF-"):
        raise AppError("O arquivo enviado não é um PDF válido.")

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise AppError("PDF protegido por senha. Envie o arquivo sem senha.")
        page_count = len(reader.pages)
    except AppError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError) as exc:
        raise AppError("Não foi possível ler o PDF. O arquivo pode estar corrompido.") from exc
    if page_count == 0:
        raise AppError("O PDF não tem páginas.")

    return PdfFingerprint(
        sha256=hashlib.sha256(data).hexdigest(),
        size_bytes=len(data),
        page_count=page_count,
        metadata=_read_metadata(reader),
        page_size=_read_page_size(reader),
        _reader=reader,
    )
