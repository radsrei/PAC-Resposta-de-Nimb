"""Busca por palavras (BM25) nos trechos de um livro: acha nomes próprios, tabelas e termos exatos."""

import json
import math
import re
import unicodedata
from collections import Counter
from functools import lru_cache
from pathlib import Path

K1, B = 1.5, 0.75
STOPWORDS = frozenset(
    "a o e de da do das dos em no na nos nas um uma uns umas para pra por com sem que se como qual quais "
    "quanto quantos quanta quantas ou ao aos as os sao ser seu sua seus suas meu minha eu voce ele ela "
    "isso esse essa este esta mais menos muito pode posso faz fazer tem ter sobre entre quando onde "
    "me te lhe nao sim ja la ha foi era sera vai the".split()
)


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    words = (w[:-1] if len(w) > 3 and w.endswith("s") else w for w in re.findall(r"[a-z0-9]+", text))
    return [w for w in words if len(w) > 1 and w not in STOPWORDS]


class Bm25:
    def __init__(self, docs: dict[str, list[str]]):
        self.ids = list(docs)
        self.freqs = [Counter(words) for words in docs.values()]
        self.lengths = [len(words) for words in docs.values()]
        self.average = sum(self.lengths) / max(len(self.lengths), 1)
        df = Counter(word for freq in self.freqs for word in freq)
        total = len(self.ids)
        self.idf = {word: math.log(1 + (total - n + 0.5) / (n + 0.5)) for word, n in df.items()}

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        terms = [t for t in set(tokens(query)) if t in self.idf]
        if not terms:
            return []
        scores = []
        for doc_id, freq, length in zip(self.ids, self.freqs, self.lengths):
            norm = K1 * (1 - B + B * length / self.average)
            score = sum(self.idf[t] * freq[t] * (K1 + 1) / (freq[t] + norm) for t in terms if t in freq)
            if score > 0:
                scores.append((doc_id, score))
        return sorted(scores, key=lambda item: item[1], reverse=True)[:k]


@lru_cache(maxsize=16)
def book_index(book_id: str, chunks_path: str, built_at: str) -> Bm25:
    """Índice do livro, refeito só quando o banco é reconstruído (`built_at` muda)."""
    docs = {}
    for line in Path(chunks_path).read_text(encoding="utf-8").splitlines():
        chunk = json.loads(line)
        docs[f"{book_id}:{chunk['index']:06d}"] = tokens(f"{chunk['title']} {chunk['title']} {chunk['path']} {chunk['text']}")
    return Bm25(docs)
