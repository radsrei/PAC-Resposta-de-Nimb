"""Perfil tipográfico do livro: o papel de cada fonte na página (título, rodapé, marca d'água...)."""

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROFILES_DIR = Path(__file__).parent / "profiles"
ROLES = ("heading", "page_number", "drop", "decor")
ZONES = ("any", "top", "bottom", "body")
DETOURS = ("", "body", "page")


@dataclass(frozen=True)
class FontRule:
    role: str
    font: str = ".*"
    size: tuple[float, float] = (0.0, 999.0)
    zone: str = "any"
    level: int = 0
    kind: str = ""
    detour: str = ""

    def matches(self, font: str, size: float, zone: str) -> bool:
        return (self.size[0] <= size <= self.size[1]
                and self.zone in ("any", zone)
                and re.search(self.font, font) is not None)


@dataclass(frozen=True)
class KindRule:
    kind: str
    title: str | None = None
    text: str | None = None
    chapter: str | None = None

    def matches(self, title: str, text: str, chapter: str) -> bool:
        checks = ((self.title, title), (self.text, text), (self.chapter, chapter))
        return all(re.search(pattern, value) for pattern, value in checks if pattern)


@dataclass
class Profile:
    name: str
    body_font: str
    body_size: tuple[float, float]
    rules: list[FontRule]
    margin: float = 0.08
    drop_unmatched_margin: bool = False
    skip_sections: list[str] = field(default_factory=list)
    title_suffix: str | None = None
    kinds: list[KindRule] = field(default_factory=list)
    source: str = "auto"

    def rule_for(self, font: str, size: float, zone: str) -> FontRule | None:
        return next((r for r in self.rules if r.matches(font, size, zone)), None)

    def is_body(self, font: str, size: float) -> bool:
        return self.body_size[0] <= size <= self.body_size[1] and re.search(self.body_font, font) is not None

    def kind_of(self, title: str, text: str, chapter: str) -> str:
        return next((k.kind for k in self.kinds if k.matches(title, text, chapter)), "geral")

    def describe(self) -> dict[str, Any]:
        return {"name": self.name, "source": self.source}


def _rule(raw: dict[str, Any]) -> FontRule:
    rule = FontRule(**{**raw, "size": tuple(raw.get("size", (0.0, 999.0)))})
    if rule.role not in ROLES or rule.zone not in ZONES or rule.detour not in DETOURS:
        raise ValueError(f"Regra de fonte inválida no perfil: {raw}")
    return rule


def load_profile(path: Path) -> Profile:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return Profile(
        name=raw["name"],
        body_font=raw["body"]["font"],
        body_size=tuple(raw["body"]["size"]),
        rules=[_rule(r) for r in raw["rules"]],
        margin=raw.get("margin", 0.08),
        drop_unmatched_margin=raw.get("drop_unmatched_margin", False),
        skip_sections=raw.get("skip_sections", []),
        title_suffix=raw.get("title_suffix"),
        kinds=[KindRule(**k) for k in raw.get("kinds", [])],
        source=str(path.name),
    )


def find_profile(book_id: str, explicit: Path | None = None) -> Path | None:
    if explicit:
        return explicit
    candidate = PROFILES_DIR / f"{book_id}.json"
    return candidate if candidate.is_file() else None


def auto_profile(doc) -> Profile:
    usage: Counter = Counter()
    pages_with: dict[tuple[str, float], set[int]] = {}
    for page in doc:
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if span["text"].strip():
                        key = (span["font"], round(span["size"] * 2) / 2)
                        usage[key] += len(span["text"])
                        pages_with.setdefault(key, set()).add(page.number)
    (body_font, body_size), _ = usage.most_common(1)[0]
    sizes = sorted({size for (_, size), pages in pages_with.items()
                    if size >= body_size * 1.4 and len(pages) >= 3}, reverse=True)[:3]
    rules = [FontRule("heading", size=(s - 0.25, s + 0.25), zone="body", level=i + 1, kind="secao")
             for i, s in enumerate(sizes)]
    return Profile(
        name="automático",
        body_font=re.escape(body_font),
        body_size=(body_size - 0.5, body_size + 0.5),
        rules=rules,
        drop_unmatched_margin=True,
    )
