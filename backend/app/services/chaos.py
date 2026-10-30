"""
Níveis de caos do Nimb: Baixo, Médio, Alto e Louco.

Cada nível define:
- `harness_rounds`: voltas de revisão da resposta contra os trechos dos livros
  (Baixo 0, Médio 1, Alto 2, Louco 3). Cada volta é uma chamada extra à LLM que
  confere regras, números e citações e devolve a resposta corrigida;
- `hallucination_chance`: limite (0 a 1) da regra de alucinação abaixo. Quando ela
  manda alucinar, a resposta já revisada é reescrita com 1 ou 2 detalhes de regra
  trocados por valores plausíveis, mantendo tom e formato.

Há dois modos, escolhidos no front (botão "Regra Nimb"):

1. Regra Nimb ligada: resultado = (A + B / C) % 42, com divisão decimal, onde
     A = palavras da pergunta (cada separação por espaço) x primo sorteado de 2 a 97,
     B = dia + mês + ano + hora + minuto + segundo do registro da rolagem (CHAOS_TIMEZONE),
     C = voltas de harness do nível + DIVISOR_OFFSET.
   Nimb alucina se a parte decimal do resultado for igual ou menor que `hallucination_chance`.
   Ex.: 7 palavras x 3 às 27/10/2026 14:05:09 no nível Alto (C = 3) -> (21 + 2091 / 3) % 42 = 4,0;
   0,0 <= 0,50, então alucina.
   A rolagem é feita antes da pergunta (`POST /api/rag/roll`), para o front já mostrar o
   "pensamento" da alucinação.
2. Regra Nimb desligada: depois da busca nos livros, sorteia com `hallucination_chance`
   como probabilidade (`roll_by_chance`).

No modo 1, o resultado vai num token assinado que o front devolve na pergunta,
sem poder alterá-lo (`create_roll` / `read_roll`).

Chances e voltas são configuráveis no `.env` (CHAOS_HALLUCINATION_CHANCES e
CHAOS_HARNESS_ROUNDS). As voltas de harness param antes do fim se o tempo gasto
passar de CHAOS_TIME_BUDGET, para a requisição não estourar o limite do Cloudflare.
"""

import random
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
from time import perf_counter
from typing import Any, Callable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import settings
from app.core.crypto import seal, unseal
from app.core.exceptions import AppError
from app.services import llm_client
from app.services.llm_client import LLMResult, Message


@dataclass(frozen=True)
class ChaosLevel:
    id: int
    label: str
    tone: str
    harness_rounds: int
    hallucination_chance: Fraction


_TONES = (
    ("Baixo", "responda de forma objetiva, precisa e direta, sem floreios."),
    ("Médio", "responda com clareza, com um leve toque da personalidade excêntrica de Nimb."),
    ("Alto", "responda com bastante personalidade caótica e humor."),
    ("Louco", "responda de forma teatral e imprevisível, como o próprio Deus do Caos."),
)

LEVELS: tuple[ChaosLevel, ...] = tuple(
    ChaosLevel(
        i,
        label,
        tone,
        settings.chaos_harness_rounds[i],
        Fraction(str(settings.chaos_hallucination_chances[i])) / 100,
    )
    for i, (label, tone) in enumerate(_TONES)
)


def get_level(level: int) -> ChaosLevel:
    return LEVELS[max(0, min(level, len(LEVELS) - 1))]


# C = voltas de harness + DIVISOR_OFFSET
DIVISOR_OFFSET = 1
# Multiplicadores de A: primos de 1 a 100
PRIMES = tuple(p for p in range(2, 101) if all(p % d for d in range(2, int(p**0.5) + 1)))


def _divisor(level: ChaosLevel) -> int:
    return level.harness_rounds + DIVISOR_OFFSET


def effective_chance(level: ChaosLevel) -> Fraction:
    """Chance real da regra: como A é inteiro (mesmo multiplicado pelo primo), a parte decimal
    só pode ser 0, 1/C, 2/C, ... (C-1)/C."""
    divisor = _divisor(level)
    return Fraction(sum(Fraction(k, divisor) <= level.hallucination_chance for k in range(divisor)), divisor)


def check_progression() -> list[str]:
    """Avisos para quando a chance real de um nível não for maior que a do nível anterior."""
    chances = [effective_chance(level) for level in LEVELS]
    return [
        f"Caos {cur.label} alucina {float(chances[i]):.0%}, que não é mais que {prev.label} "
        f"({float(chances[i - 1]):.0%}): ajuste CHAOS_HALLUCINATION_CHANCES."
        for i, (prev, cur) in enumerate(zip(LEVELS, LEVELS[1:]), start=1)
        if chances[i] <= chances[i - 1]
    ]


ROLL_TTL = 300  # segundos para usar a rolagem na pergunta


MODULUS = 42


def count_words(prompt: str) -> int:
    return len(prompt.split())


def _now() -> datetime:
    try:
        return datetime.now(ZoneInfo(settings.chaos_timezone))
    except ZoneInfoNotFoundError:
        return datetime.now()  # sem base de fusos no sistema: hora local do servidor


def compute_roll(prompt: str, level: ChaosLevel, moment: datetime, multiplier: int) -> dict[str, Any]:
    """Aplica a regra de alucinação (ver docstring do módulo) e devolve o cálculo completo."""
    words = count_words(prompt)
    date_sum = moment.day + moment.month + moment.year + moment.hour + moment.minute + moment.second
    divisor = _divisor(level)
    result = (words * multiplier + Fraction(date_sum, divisor)) % MODULUS  # Fraction: sem arredondamento
    decimal = result - (result.numerator // result.denominator)
    return {
        "mode": "rule",
        "words": words,
        "multiplier": multiplier,
        "dateSum": date_sum,
        "divisor": divisor,
        "result": round(float(result), 6),
        "decimal": round(float(decimal), 6),
        "threshold": float(level.hallucination_chance),
        "recordedAt": moment.isoformat(timespec="seconds"),
        "hallucinated": decimal <= level.hallucination_chance,
    }


def create_roll(user_email: str, prompt: str, level: ChaosLevel) -> tuple[str, dict[str, Any]]:
    roll = compute_roll(prompt, level, _now(), random.choice(PRIMES))
    token = seal({"email": user_email, "level": level.id, "roll": roll})
    return token, roll


def read_roll(token: str, user_email: str, prompt: str, level: ChaosLevel) -> dict[str, Any]:
    """Cálculo guardado no token; recusa token vencido, de outro usuário, nível ou pergunta."""
    data = unseal(token, ROLL_TTL)
    if (
        not data
        or data.get("email") != user_email
        or data.get("level") != level.id
        or data.get("roll", {}).get("words") != count_words(prompt)
    ):
        raise AppError("Rolagem do caos inválida ou expirada. Envie a pergunta novamente.")
    return data["roll"]


def roll_by_chance(level: ChaosLevel) -> dict[str, Any]:
    """Modo sem a regra: sorteio simples com a chance do nível no `.env`."""
    draw = random.random()
    return {
        "mode": "chance",
        "draw": round(draw, 6),
        "threshold": float(level.hallucination_chance),
        "hallucinated": draw < level.hallucination_chance,
    }


# O prompt da resposta proíbe inventar regras; a alucinação usa um prompt próprio, sem os trechos
HALLUCINATION_SYSTEM = (
    "Você é Nimb, o Deus do Caos e da Sorte de Tormenta20, e às vezes engana os mortais por diversão. "
    "Responda sempre em português do Brasil."
)


def _harness_round(
    connection: dict[str, Any], system: str, question: str, draft: str, round_no: int, total: int
) -> str:
    instruction = (
        f"REVISÃO {round_no}/{total}. Abaixo está a pergunta do usuário e o rascunho da sua resposta.\n"
        "Confira o rascunho, frase a frase, contra os TRECHOS DOS LIVROS do prompt de sistema:\n"
        "- corrija qualquer regra, número, condição ou página que não bata com os trechos;\n"
        "- remova o que não estiver nos trechos e complete o que for importante e estiver faltando;\n"
        "- garanta a citação (Livro, p. N) em cada regra ou número;\n"
        "- mantenha o tom do nível de caos e a formatação Markdown.\n"
        "Devolva SOMENTE a resposta final revisada, sem comentar a revisão.\n\n"
        f"PERGUNTA:\n{question}\n\nRASCUNHO:\n{draft}"
    )
    return llm_client.generate(connection, system=system, messages=[{"role": "user", "content": instruction}]).text


def _hallucinate(connection: dict[str, Any], question: str, answer: str) -> str:
    instruction = (
        "Nimb decidiu pregar uma peça. Reescreva a resposta abaixo mantendo o mesmo tom, tamanho, "
        "estrutura, formatação e citações, mas troque 1 ou 2 detalhes de regra (um número, uma "
        "duração, um alcance, um bônus ou uma condição) por valores diferentes e plausíveis, que "
        "pareçam corretos. Não avise que algo foi alterado.\n"
        "Devolva SOMENTE a resposta reescrita.\n\n"
        f"PERGUNTA:\n{question}\n\nRESPOSTA:\n{answer}"
    )
    messages = [{"role": "user", "content": instruction}]
    return llm_client.generate(connection, system=HALLUCINATION_SYSTEM, messages=messages).text


@dataclass(frozen=True)
class ChaosResult:
    llm: LLMResult
    level: ChaosLevel
    harness_rounds: int  # voltas de revisão de fato executadas
    hallucinated: bool


def answer(
    connection: dict[str, Any],
    system: str,
    messages: list[Message],
    level: ChaosLevel,
    hallucinate: bool,
    is_refusal: Callable[[str], bool],
) -> ChaosResult:
    """Gera a resposta, revisa conforme o nível e, se o dado mandou, alucina no fim."""
    started = perf_counter()
    question = messages[-1]["content"]

    first = llm_client.generate(connection, system=system, messages=messages)
    text = first.text
    rounds = 0

    # Recusa de escopo volta direto: não há o que revisar nem alucinar
    if not is_refusal(text):
        for round_no in range(1, level.harness_rounds + 1):
            if perf_counter() - started > settings.chaos_time_budget:
                break
            revised = _harness_round(connection, system, question, text, round_no, level.harness_rounds)
            rounds += 1
            if not is_refusal(revised):
                text = revised

    # O front já mostrou a alucinação durante o pensamento: ela acontece mesmo após o orçamento de tempo
    hallucinated = hallucinate and not is_refusal(text)
    if hallucinated:
        text = _hallucinate(connection, question, text)

    return ChaosResult(
        llm=LLMResult(
            text=text,
            provider=first.provider,
            model=first.model,
            latency_ms=round((perf_counter() - started) * 1000),
        ),
        level=level,
        harness_rounds=rounds,
        hallucinated=hallucinated,
    )
