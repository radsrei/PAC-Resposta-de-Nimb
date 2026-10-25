"""Avaliação da busca: recall@k e MRR por página impressa, busca vetorial x híbrida, e calibração do mínimo."""

import json
import re
from pathlib import Path

from app.services import book_catalog, retrieval

EVAL_DIR = Path(__file__).parent / "eval"
THRESHOLDS = [0.30, 0.35, 0.40, 0.42, 0.45, 0.48, 0.50, 0.55]
MODES = {"vetorial": False, "hibrida": True}


def _hit(passage, item: dict, strict: bool) -> bool:
    if passage.page not in item["pages"]:
        return False
    return not strict or not item.get("title") or re.search(item["title"], passage.title) is not None


def _rank(passages, item: dict, strict: bool) -> int | None:
    return next((i for i, p in enumerate(passages, start=1) if _hit(p, item, strict)), None)


def _validate(book_id: str, questions: list[dict]) -> list[str]:
    chunks = [json.loads(l) for l in (book_catalog.book_dir(book_id) / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
    return [
        item["q"] for item in questions
        if not any(c["printed_start"] in item["pages"] and re.search(item.get("title") or "", c["title"]) for c in chunks)
    ]


def _metrics(results: list[tuple[dict, list]], k: int, threshold: float, strict: bool) -> dict:
    ranks = [_rank([p for p in passages if p.similarity >= threshold][:k], item, strict) for item, passages in results]
    total = len(ranks)
    return {
        "r1": sum(1 for r in ranks if r == 1) / total,
        "r3": sum(1 for r in ranks if r and r <= 3) / total,
        "r5": sum(1 for r in ranks if r and r <= 5) / total,
        "mrr": sum(1 / r for r in ranks if r) / total,
        "answered": sum(1 for _, ps in results if any(p.similarity >= threshold for p in ps)) / total,
    }


def run(dataset: Path, k: int = 5) -> int:
    data = json.loads(dataset.read_text(encoding="utf-8"))
    book_id, questions, off_topic = data["book_id"], data["questions"], data.get("off_topic", [])
    invalid = _validate(book_id, questions)
    if invalid:
        print("Gabarito sem trecho correspondente no banco (corrija o arquivo):", *invalid, sep="\n  ")
        return 2

    print(f"{len(questions)} perguntas do livro, {len(off_topic)} fora do tema | k={k}\n")
    found = {}
    for mode, hybrid in MODES.items():
        on = [(item, retrieval.search([book_id], item["q"], k=40, hybrid=hybrid, min_similarity=-1)) for item in questions]
        off = [retrieval.search([book_id], q, k=40, hybrid=hybrid, min_similarity=-1) for q in off_topic]
        found[mode] = (on, off)

    print("Recall por página impressa (estrito = página e título), sem mínimo de similaridade:")
    print(f"  {'busca':<10} {'r@1':>6} {'r@3':>6} {'r@5':>6} {'MRR':>6} | estrito {'r@1':>6} {'r@5':>6} {'MRR':>6}")
    for mode, (on, _) in found.items():
        m, s = _metrics(on, k, -1, False), _metrics(on, k, -1, True)
        print(f"  {mode:<10} {m['r1']:>6.0%} {m['r3']:>6.0%} {m['r5']:>6.0%} {m['mrr']:>6.2f} |         "
              f"{s['r1']:>6.0%} {s['r5']:>6.0%} {s['mrr']:>6.2f}")

    for mode, (on, off) in found.items():
        best_on = sorted(max((p.similarity for p in ps), default=0) for _, ps in on)
        best_off = sorted(max((p.similarity for p in ps), default=0) for ps in off)
        print(f"\nCalibração do mínimo ({mode}) | melhor similaridade: livro {best_on[0]:.2f}–{best_on[-1]:.2f}, "
              f"fora do tema {best_off[0]:.2f}–{best_off[-1]:.2f}")
        print(f"  {'mínimo':>7} {'respondidas':>12} {'r@5':>6} {'MRR':>6} {'fora bloqueadas':>16}")
        for t in THRESHOLDS:
            m = _metrics(on, k, t, False)
            blocked = sum(1 for ps in off if not any(p.similarity >= t for p in ps)) / max(len(off), 1)
            print(f"  {t:>7.2f} {m['answered']:>12.0%} {m['r5']:>6.0%} {m['mrr']:>6.2f} {blocked:>16.0%}")

    print("\nErros da busca híbrida (página esperada fora dos 5 primeiros, sem mínimo):")
    for item, passages in found["hibrida"][0]:
        if not _rank(passages[:k], item, False):
            top = ", ".join(f"{p.title[:28]} p.{p.page}" for p in passages[:3])
            print(f"  - {item['q']} (esperado p.{'/'.join(item['pages'])}) -> {top}")
    return 0
