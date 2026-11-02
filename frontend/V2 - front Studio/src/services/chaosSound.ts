/**
 * Avisos sonoros da alucinação de Nimb (preparado para receber os áudios depois).
 *
 * Para ativar um som, coloque o arquivo em `public/sounds/` e informe o caminho
 * abaixo, ou defina a variável no `.env.local` (ex.: VITE_SOUND_HALLUCINATION_THINKING=/sounds/risada.mp3).
 * Sem caminho configurado, o evento fica em silêncio.
 */

export type ChaosSoundEvent =
  | 'hallucinationThinking' // o dado caiu: começa o "pensamento" laranja
  | 'hallucinationReveal'; // a resposta alucinada aparece (giro + confetes)

const SOUND_SOURCES: Record<ChaosSoundEvent, string | undefined> = {
  hallucinationThinking: import.meta.env.VITE_SOUND_HALLUCINATION_THINKING || undefined,
  hallucinationReveal: import.meta.env.VITE_SOUND_HALLUCINATION_REVEAL || undefined,
};

const VOLUME = 0.6;
const cache = new Map<string, HTMLAudioElement>();

/** Pré-carrega os sons configurados para tocarem sem atraso. */
export const preloadChaosSounds = () => {
  Object.values(SOUND_SOURCES).forEach((src) => {
    if (!src || cache.has(src)) return;
    const audio = new Audio(src);
    audio.preload = 'auto';
    audio.volume = VOLUME;
    cache.set(src, audio);
  });
};

/** Toca o som do evento, se houver; falhas (arquivo ausente, autoplay bloqueado) são ignoradas. */
export const playChaosSound = (event: ChaosSoundEvent) => {
  const src = SOUND_SOURCES[event];
  if (!src) return;
  const audio = cache.get(src) ?? new Audio(src);
  audio.volume = VOLUME;
  audio.currentTime = 0;
  audio.play().catch(() => undefined);
};
