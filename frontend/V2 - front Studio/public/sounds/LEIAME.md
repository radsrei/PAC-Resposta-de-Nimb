# Sons da alucinação de Nimb

Coloque aqui os áudios (mp3, ogg ou wav). Cada evento pode ter vários sons: a cada vez,
um deles é sorteado, sem repetir o último que tocou.

Eventos:

- `hallucinationThinking`: toca quando o dado do caos cai (início do "pensamento" laranja).
- `hallucinationReveal`: toca quando a resposta alucinada aparece (giro + confetes).

Há duas formas de registrar os sons:

1. Na lista `DEFAULT_SOUNDS` de `src/services/chaosSound.ts`, por exemplo
   `hallucinationReveal: ['/sounds/risada-1.mp3', '/sounds/risada-2.mp3']`.
2. No `.env.local`, com os caminhos separados por vírgula:
   `VITE_SOUND_HALLUCINATION_REVEAL=/sounds/risada-1.mp3,/sounds/risada-2.mp3`.
   Quando preenchida, a variável substitui a lista do código.

Sem nenhum som registrado, o evento fica em silêncio.
