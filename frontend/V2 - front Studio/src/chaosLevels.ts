// Níveis do Medidor de Caos. Espelha backend/app/services/chaos.py:
// cada nível acima de Baixo faz uma volta a mais de revisão (harness) e
// aumenta a chance de Nimb alucinar de propósito.
export interface ChaosLevelInfo {
  id: number;
  label: string;
  //harnessRounds: number;
  className: string;
}

export const CHAOS_LEVELS: ChaosLevelInfo[] = [
  { id: 0, label: 'Baixo', //harnessRounds: 0,
    className: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
  { id: 1, label: 'Médio', //harnessRounds: 1,
    className: 'bg-purple-500/15 text-[#d8b9ff] border-purple-500/30' },
  { id: 2, label: 'Alto', //harnessRounds: 2,
    className: 'bg-[#39d98a]/15 text-[#39d98a] border-[#39d98a]/30' },
  {
    id: 3,
    label: 'Louco',
    //harnessRounds: 3,
    className: 'bg-red-500/20 text-red-400 border-red-500/50 animate-pulse',
  },
];

export const DEFAULT_CHAOS_LEVEL = 1;

/** Nível (0-3) de um valor salvo; mensagens antigas guardavam porcentagem (0-100). */
export const getChaosLevel = (value: number | undefined | null): ChaosLevelInfo => {
  const v = value ?? DEFAULT_CHAOS_LEVEL;
  if (v <= 3) return CHAOS_LEVELS[Math.max(0, Math.round(v))];
  if (v < 30) return CHAOS_LEVELS[0];
  if (v < 70) return CHAOS_LEVELS[1];
  if (v < 90) return CHAOS_LEVELS[2];
  return CHAOS_LEVELS[3];
};
