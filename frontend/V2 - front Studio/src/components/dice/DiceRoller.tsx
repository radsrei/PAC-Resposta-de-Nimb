import React, { useEffect, useState } from 'react';
import { motion, useReducedMotion } from 'motion/react';
import { TreasureGroupResult } from '../../types';

/** Quantos dados aparecem no máximo; o resto vira "+N". */
const MAX_DICE = 8;

/** Tempo mínimo da animação ao sortear, para não piscar quando a API responde rápido. */
export const MIN_ROLL_MS = 900;

/**
 * Som da rolagem, servido de `public/sounds/`. O caminho é fixo (e não uma variável VITE_)
 * para funcionar também na imagem Docker. Sem o arquivo, a rolagem fica em silêncio.
 */
const DICE_SOUND = '/sounds/dice-roll.mp3';
const DICE_VOLUME = 0.6;
let diceAudio: HTMLAudioElement | null = null;

const loadDiceSound = () => {
  if (!diceAudio) {
    diceAudio = new Audio(DICE_SOUND);
    diceAudio.preload = 'auto';
    diceAudio.volume = DICE_VOLUME;
  }
  return diceAudio;
};

/** Toca do início; falhas (arquivo ausente, autoplay bloqueado) são ignoradas. */
const playDiceSound = () => {
  const audio = loadDiceSound();
  audio.currentTime = 0;
  audio.play().catch(() => undefined);
};

export interface DiceFace {
  sides: number;
  value: number;
  label?: string;
}

/** Contorno de cada dado em um viewBox 100x100; d10 e d% usam a mesma pipa. */
const SHAPES: Record<number, string> = {
  4: '50,8 94,88 6,88',
  6: '12,12 88,12 88,88 12,88',
  8: '50,4 94,50 50,96 6,50',
  10: '50,4 94,42 50,96 6,42',
  12: '50,4 95,37 78,92 22,92 5,37',
  20: '50,4 92,27 92,73 50,96 8,73 8,27',
};

const shapeFor = (sides: number) => SHAPES[sides === 100 ? 10 : sides] ?? SHAPES[20];

const randomFace = (sides: number) => 1 + Math.floor(Math.random() * sides);

const Die: React.FC<{ face: DiceFace; rolling: boolean; index: number }> = ({ face, rolling, index }) => {
  const reduceMotion = useReducedMotion();
  const animate = rolling && !reduceMotion;
  const [shown, setShown] = useState(face.value || randomFace(face.sides));

  // Embaralha os números enquanto rola; ao parar mostra o valor sorteado
  useEffect(() => {
    if (!animate) {
      setShown(face.value);
      return;
    }
    const id = window.setInterval(() => setShown(randomFace(face.sides)), 70);
    return () => window.clearInterval(id);
  }, [animate, face.sides, face.value]);

  return (
    <div className="flex flex-col items-center gap-1 w-16">
      <motion.div
        className="w-14 h-14"
        animate={animate ? { rotate: [0, 120, 240, 360], y: [0, -10, 0, -6, 0] } : { rotate: 0, y: 0, scale: [1.25, 1] }}
        transition={
          animate
            ? { duration: 0.6, repeat: Infinity, ease: 'linear', delay: index * 0.05 }
            : { duration: 0.45, ease: 'backOut', delay: index * 0.08 }
        }
      >
        <svg viewBox="0 0 100 100" className="w-full h-full" aria-hidden="true">
          <polygon
            points={shapeFor(face.sides)}
            fill="#181827"
            stroke={rolling ? '#A259FF' : '#39D98A'}
            strokeWidth="5"
            strokeLinejoin="round"
          />
          <text
            x="50"
            y="56"
            textAnchor="middle"
            dominantBaseline="middle"
            fill="#F0EEF8"
            fontFamily="monospace"
            fontWeight="bold"
            fontSize={String(shown).length > 2 ? 24 : 32}
          >
            {shown}
          </text>
        </svg>
      </motion.div>
      <span className="font-mono text-[9px] text-[#8B87A8]">{face.sides === 100 ? 'd%' : `d${face.sides}`}</span>
      {face.label && (
        <span className="font-mono text-[9px] text-[#8B87A8]/80 text-center leading-tight w-full truncate" title={face.label}>
          {face.label}
        </span>
      )}
    </div>
  );
};

interface DiceRollerProps {
  dice: DiceFace[];
  /** Enquanto true os dados giram e os números embaralham; ao virar false param no `value` de cada um */
  rolling: boolean;
}

/** Dados animados que param nos valores sorteados pelo backend. */
export const DiceRoller: React.FC<DiceRollerProps> = ({ dice, rolling }) => {
  // Pré-carrega ao montar e toca a cada rolagem que começa
  useEffect(() => {
    loadDiceSound();
  }, []);
  useEffect(() => {
    if (rolling) playDiceSound();
  }, [rolling]);

  const visible = dice.slice(0, MAX_DICE);
  const hidden = dice.length - visible.length;

  return (
    <div
      className="flex flex-wrap items-start justify-center gap-3 p-3 rounded-xl bg-[#13131F]/70 border border-[#34344E]"
      role="status"
      aria-live="polite"
      aria-label={rolling ? 'Rolando os dados' : `Resultado: ${dice.map((d) => d.value).join(', ')}`}
    >
      {visible.map((face, i) => (
        <Die key={i} face={face} rolling={rolling} index={i} />
      ))}
      {hidden > 0 && (
        <span className="self-center font-mono text-xs text-[#8B87A8]">+{hidden}</span>
      )}
    </div>
  );
};

/** Um d% por coluna rolada no sorteio automático, na ordem do resultado. */
export const treasureDice = (result: TreasureGroupResult): DiceFace[] =>
  result.groups.flatMap((group) =>
    group.results.flatMap((res, unit) =>
      res.rolls.map((roll) => ({
        sides: 100,
        value: roll.roll,
        label: `${group.creature.name} #${unit + 1} · ${roll.column}`,
      }))
    )
  );

/** Dados de espera enquanto o backend sorteia: a quantidade aproximada de d% que vão sair. */
export const placeholderDice = (expected: number): DiceFace[] =>
  Array.from({ length: Math.max(1, Math.min(MAX_DICE, expected)) }, () => ({ sides: 100, value: 0 }));
