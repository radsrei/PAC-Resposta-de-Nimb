/**
 * Avisos sonoros da alucinação de Nimb.
 *
 * Cada evento tem uma lista de sons; a cada vez, um deles é sorteado (sem repetir
 * o último que tocou, quando há mais de um). Para incluir sons, coloque os arquivos
 * em `public/sounds/` e acrescente os caminhos na lista do evento abaixo, ou defina
 * a variável no `.env.local` com os caminhos separados por vírgula
 * (ex.: VITE_SOUND_HALLUCINATION_REVEAL=/sounds/risada-1.mp3,/sounds/risada-2.mp3).
 * A variável, quando preenchida, substitui a lista do código. Lista vazia = silêncio.
 *
 * Um som nunca se sobrepõe a outro: antes de tocar, os que estiverem tocando são
 * encerrados com fade-out (FADE_MS). Com `loop`, o som repete até `stopChaosSound`.
 */

export type ChaosSoundEvent =
  | 'hallucinationThinking' // o dado caiu: começa o "pensamento" laranja
  | 'hallucinationReveal'; // a resposta alucinada aparece (giro + confetes)

// Sons de cada evento (caminhos a partir de `public/`, começando por /sounds/)
const DEFAULT_SOUNDS: Record<ChaosSoundEvent, string[]> = {
  hallucinationThinking: [
     '/sounds/Space cat.mp3',
     '/sounds/dexter-meme.mp3',
     '/sounds/indian-song.mp3',
  ],
  hallucinationReveal: [
    '/sounds/xaropinho-rapaz.mp3',
    '/sounds/cosmo-ou-sera.mp3',
    '/sounds/tomar cafe.mp3',
    '/sounds/procure saber.mp3',
    '/sounds/deu-errado.mp3',
    '/sounds/desculpe.mp3',
    '/sounds/lata-bebida.mp3',
  ],
};

const fromEnv = (value: string | undefined): string[] =>
  (value || '')
    .split(',')
    .map((src) => src.trim())
    .filter(Boolean);

const envOrDefault = (value: string | undefined, fallback: string[]): string[] => {
  const list = fromEnv(value);
  return list.length > 0 ? list : fallback;
};

const SOUND_SOURCES: Record<ChaosSoundEvent, string[]> = {
  hallucinationThinking: envOrDefault(
    import.meta.env.VITE_SOUND_HALLUCINATION_THINKING,
    DEFAULT_SOUNDS.hallucinationThinking
  ),
  hallucinationReveal: envOrDefault(
    import.meta.env.VITE_SOUND_HALLUCINATION_REVEAL,
    DEFAULT_SOUNDS.hallucinationReveal
  ),
};

const VOLUME = 0.6;
const FADE_MS = 300;
const FADE_STEP_MS = 30;
const cache = new Map<string, HTMLAudioElement>();
const lastPlayed = new Map<ChaosSoundEvent, string>();
// Som tocando agora em cada evento, e o fade-out em andamento
const active = new Map<ChaosSoundEvent, HTMLAudioElement>();
const stopping = new Map<ChaosSoundEvent, Promise<void>>();
// Muda a cada stop: um play que ainda esperava outro som parar não começa mais
const generation = new Map<ChaosSoundEvent, number>();

/** Sorteia um som do evento, evitando repetir o último quando há outra opção. */
const pickSound = (event: ChaosSoundEvent): string | undefined => {
  const sources = SOUND_SOURCES[event];
  if (sources.length === 0) return undefined;
  const last = lastPlayed.get(event);
  const options = sources.length > 1 ? sources.filter((src) => src !== last) : sources;
  const src = options[Math.floor(Math.random() * options.length)];
  lastPlayed.set(event, src);
  return src;
};

// Preferência do usuário (tela Minha conta), lembrada neste navegador. Padrão: desligado.
const ENABLED_STORAGE_KEY = 'nimb:chaos-sound';

const readEnabled = (): boolean => {
  try {
    return localStorage.getItem(ENABLED_STORAGE_KEY) === 'on';
  } catch {
    return false;
  }
};

let enabled = readEnabled();

export const isChaosSoundEnabled = () => enabled;

/** Liga ou desliga os efeitos sonoros; ao desligar, encerra o que estiver tocando. */
export const setChaosSoundEnabled = (on: boolean) => {
  enabled = on;
  try {
    localStorage.setItem(ENABLED_STORAGE_KEY, on ? 'on' : 'off');
  } catch {
    // sem armazenamento (aba anônima): vale só até recarregar a página
  }
  if (on) preloadChaosSounds();
  else (Object.keys(SOUND_SOURCES) as ChaosSoundEvent[]).forEach((event) => void stopChaosSound(event));
};

/** Pré-carrega todos os sons configurados para tocarem sem atraso (só com o som ligado). */
export const preloadChaosSounds = () => {
  if (!enabled) return;
  Object.values(SOUND_SOURCES)
    .flat()
    .forEach((src) => {
      if (cache.has(src)) return;
      const audio = new Audio(src);
      audio.preload = 'auto';
      audio.volume = VOLUME;
      cache.set(src, audio);
    });
};

/** Encerra o som do evento com fade-out; resolve quando ele parou (ou se não havia som). */
export const stopChaosSound = (event: ChaosSoundEvent): Promise<void> => {
  generation.set(event, (generation.get(event) ?? 0) + 1);
  const pending = stopping.get(event);
  if (pending) return pending;
  const audio = active.get(event);
  if (!audio) return Promise.resolve();
  active.delete(event);

  const promise = new Promise<void>((resolve) => {
    const startVolume = audio.volume;
    const started = performance.now();
    const timer = window.setInterval(() => {
      const progress = Math.min((performance.now() - started) / FADE_MS, 1);
      audio.volume = startVolume * (1 - progress);
      if (progress < 1) return;
      window.clearInterval(timer);
      audio.pause();
      audio.loop = false;
      audio.currentTime = 0;
      audio.volume = VOLUME;
      stopping.delete(event);
      resolve();
    }, FADE_STEP_MS);
  });
  stopping.set(event, promise);
  return promise;
};

interface PlayOptions {
  /** Repete o som até `stopChaosSound` (ex.: enquanto Nimb "pensa"). */
  loop?: boolean;
}

/**
 * Toca um som sorteado do evento, se houver, depois de encerrar os que estiverem tocando.
 * Falhas (arquivo ausente, autoplay bloqueado) são ignoradas.
 */
export const playChaosSound = async (event: ChaosSoundEvent, { loop = false }: PlayOptions = {}) => {
  if (!enabled) return;
  const src = pickSound(event);
  if (!src) return;
  // Sem sobreposição: encerra tudo que estiver tocando, inclusive um som anterior deste evento
  const stops = (Object.keys(SOUND_SOURCES) as ChaosSoundEvent[]).map(stopChaosSound);
  const ticket = generation.get(event) ?? 0;
  await Promise.all(stops);
  if ((generation.get(event) ?? 0) !== ticket || !enabled) return; // parado ou desligado enquanto esperava

  const audio = cache.get(src) ?? new Audio(src);
  cache.set(src, audio);
  audio.loop = loop;
  audio.volume = VOLUME;
  audio.currentTime = 0;
  active.set(event, audio);
  audio.addEventListener('ended', () => active.get(event) === audio && active.delete(event), { once: true });
  audio.play().catch(() => active.get(event) === audio && active.delete(event));
};
