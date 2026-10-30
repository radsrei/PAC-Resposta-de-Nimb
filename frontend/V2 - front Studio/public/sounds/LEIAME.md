# Sons da alucinação de Nimb

Coloque aqui os áudios (mp3, ogg ou wav) e aponte para eles no `.env.local`:

- `VITE_SOUND_HALLUCINATION_THINKING`: toca quando o dado do caos cai (início do "pensamento" laranja).
- `VITE_SOUND_HALLUCINATION_REVEAL`: toca quando a resposta alucinada aparece (giro + confetes).

Exemplo: `VITE_SOUND_HALLUCINATION_REVEAL=/sounds/risada-nimb.mp3`. Sem variável, o evento fica em silêncio.
A lógica fica em `src/services/chaosSound.ts`.
