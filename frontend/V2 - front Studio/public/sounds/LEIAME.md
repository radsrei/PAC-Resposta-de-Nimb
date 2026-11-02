# Sons da alucinação de Nimb

Coloque aqui os áudios (mp3, ogg ou wav) e aponte para eles no `.env.local`:

- `VITE_SOUND_HALLUCINATION_THINKING`: toca quando o dado do caos cai (início do "pensamento" laranja).
- `VITE_SOUND_HALLUCINATION_REVEAL`: toca quando a resposta alucinada aparece (giro + confetes).

Exemplo: `VITE_SOUND_HALLUCINATION_REVEAL=/sounds/risada-nimb.mp3`. Sem variável, o evento fica em silêncio.
A lógica fica em `src/services/chaosSound.ts`.

## Som da rolagem de dados (tela de tesouro)

- `dice-roll.mp3`: toca quando os dados começam a rolar no sorteio automático. O caminho é fixo no código
  (`src/components/dice/DiceRoller.tsx`), sem variável de ambiente, e funciona também na imagem Docker.
  Ideal: MP3 mono de ~1 s, sem silêncio no início. Sem o arquivo, a rolagem fica em silêncio.

Para remover só o som e manter a animação: apague no DiceRoller.tsx o bloco de DICE_SOUND até playDiceSound e os dois useEffect no início do componente DiceRoller.
