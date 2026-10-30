import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  TreasureCreature,
  TreasureDiceRequest,
  TreasureGroupResult,
  TreasureLookup,
  TreasureReward,
} from '../../types';
import { treasureApiService } from '../../services/treasureApi';

// Mesmos limites do backend (TreasureGroupPayload)
const MAX_CREATURES = 10;
const MAX_QUANTITY = 20;

const TYPE_STYLE: Record<string, string> = {
  Nenhum: 'bg-[#34344E]/40 text-[#8B87A8] border-[#34344E]',
  Padrão: 'bg-[#39D98A]/10 text-[#39D98A] border-[#39D98A]/30',
  Metade: 'bg-amber-400/10 text-amber-300 border-amber-400/30',
  Dobro: 'bg-[#A259FF]/15 text-[#d8b9ff] border-[#A259FF]/40',
};

interface Selected {
  creature: TreasureCreature;
  quantity: number;
}

/** Uma unidade de uma criatura (ex.: o 2º goblin), consultada separadamente no modo informado. */
interface Unit {
  key: string;
  creature: TreasureCreature;
  unit: number;
}

interface TreasureModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const normalize = (text: string) =>
  text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();

const formatValue = (value: number) =>
  `T$ ${value.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}`;

/** d% da Tabela 8-1 por coluna: 1 (Padrão/Metade), 2 (Dobro) ou nenhum (sem tesouro na tabela). */
const rollsPerColumn = (creature: TreasureCreature) =>
  creature.treasure === 'Nenhum' ? 0 : creature.treasure === 'Dobro' ? 2 : 1;

/** Soma dos dados pedidos; no d% "00" vale 100. undefined = fora do intervalo possível. */
const parseRoll = (raw: string, request: TreasureDiceRequest): number | undefined => {
  const text = raw.trim();
  if (!/^\d{1,4}$/.test(text)) return undefined;
  const value = request.sides === 100 && request.count === 1 && text === '00' ? 100 : Number(text);
  return value >= request.count && value <= request.count * request.sides ? value : undefined;
};

const rollHint = (request: TreasureDiceRequest) =>
  request.count > 1 ? `Role ${request.dice} e informe a soma` : `Role ${request.dice}`;

const RewardItem: React.FC<{ reward: TreasureReward }> = ({ reward }) => (
  <li className="flex flex-col gap-1">
    <div className="flex items-start justify-between gap-3">
      <span className="text-sm text-[#F0EEF8] break-words min-w-0">{reward.name}</span>
      {reward.value != null && reward.value > 0 && (
        <span className="font-mono text-[11px] text-[#39D98A] flex-shrink-0">{formatValue(reward.value)}</span>
      )}
    </div>
    {reward.details.length > 0 && (
      <span className="font-mono text-[10px] text-[#8B87A8] break-words">{reward.details.join(' · ')}</span>
    )}
    {reward.sources.length > 0 && (
      <span className="font-mono text-[10px] text-[#8B87A8]/70 break-words">{reward.sources.join(' · ')}</span>
    )}
    {reward.options.length > 0 && (
      <ul className="mt-1 ml-3 pl-3 border-l border-[#A259FF]/30 flex flex-col gap-2">
        {reward.options.map((option, i) => (
          <RewardItem key={i} reward={option} />
        ))}
      </ul>
    )}
  </li>
);

/**
 * Sorteio de tesouro: escolhe as criaturas (lista com busca) e quantas são de cada, e
 * rola automaticamente ou informa os dados rolados na mesa. No modo informado o sistema
 * pede um dado por vez (quantidade, tipo e para quê) e consulta o resultado nas tabelas.
 * Sair (Esc ou X) pede confirmação; os sorteios feitos ficam no histórico do backend.
 */
export const TreasureModal: React.FC<TreasureModalProps> = ({ isOpen, onClose }) => {
  const [creatures, setCreatures] = useState<TreasureCreature[]>([]);
  const [loadingCreatures, setLoadingCreatures] = useState(false);
  const [query, setQuery] = useState('');
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [highlight, setHighlight] = useState(0);
  const [selected, setSelected] = useState<Selected[]>([]);
  const [manualMode, setManualMode] = useState(false);
  const [lookups, setLookups] = useState<Record<string, TreasureLookup>>({});
  const [typed, setTyped] = useState('');
  const [lookupBusy, setLookupBusy] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [isRolling, setIsRolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TreasureGroupResult | null>(null);
  const [confirmExit, setConfirmExit] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const stayRef = useRef<HTMLButtonElement>(null);
  const rollInputRef = useRef<HTMLInputElement>(null);
  const stepsRef = useRef<HTMLOListElement>(null);

  // Carrega as criaturas ao abrir (uma vez por sessão do modal)
  useEffect(() => {
    if (!isOpen || creatures.length > 0) return;
    setLoadingCreatures(true);
    treasureApiService
      .listCreatures()
      .then(setCreatures)
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoadingCreatures(false));
  }, [isOpen, creatures.length]);

  const filtered = useMemo(() => {
    const term = normalize(query);
    return creatures.filter((c) => normalize(c.name).includes(term));
  }, [creatures, query]);

  // Modo informado: cada unidade é consultada à parte, na ordem da lista
  const units = useMemo<Unit[]>(
    () =>
      selected.flatMap(({ creature, quantity }) =>
        Array.from({ length: quantity }, (_, unit) => ({ key: `${creature.name}|${unit}`, creature, unit }))
      ),
    [selected]
  );
  const active = units.find((u) => !lookups[u.key]?.done);
  const activeLookup = active ? lookups[active.key] : undefined;
  const doneCount = units.filter((u) => lookups[u.key]?.done).length;

  // Resultados do modo informado no mesmo formato do sorteio automático
  const manualResult = useMemo<TreasureGroupResult | null>(() => {
    const groups = selected
      .map(({ creature, quantity }) => {
        const results = Array.from({ length: quantity }, (_, unit) => lookups[`${creature.name}|${unit}`]?.result)
          .filter((r): r is NonNullable<typeof r> => !!r);
        const totalValue = Math.round(results.reduce((sum, r) => sum + r.totalValue, 0) * 10) / 10;
        return { creature, quantity, totalValue, results };
      })
      .filter((g) => g.results.length > 0);
    if (groups.length === 0) return null;
    return { groups, totalValue: Math.round(groups.reduce((sum, g) => sum + g.totalValue, 0) * 10) / 10 };
  }, [selected, lookups]);

  const sendLookup = async (target: Unit, values: number[]) => {
    setLookupBusy(true);
    setLookupError(null);
    try {
      const response = await treasureApiService.lookup(target.creature.name, values);
      setLookups((prev) => ({ ...prev, [target.key]: response }));
      setTyped('');
    } catch (err) {
      setLookupError((err as Error).message);
    } finally {
      setLookupBusy(false);
    }
  };

  // Pede ao backend a primeira rolagem da próxima unidade
  useEffect(() => {
    if (!isOpen || !manualMode || !active || activeLookup || lookupBusy || lookupError) return;
    sendLookup(active, []);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, manualMode, active?.key, activeLookup, lookupBusy, lookupError]);

  // Foco no campo do dado a cada nova rolagem pedida; a lista de passos mostra o mais recente
  useEffect(() => {
    if (manualMode && activeLookup?.next) rollInputRef.current?.focus();
    stepsRef.current?.scrollTo({ top: stepsRef.current.scrollHeight });
  }, [manualMode, activeLookup]);

  const reset = () => {
    setQuery('');
    setDropdownOpen(false);
    setSelected([]);
    setManualMode(false);
    setLookups({});
    setTyped('');
    setLookupError(null);
    setError(null);
    setResult(null);
    setConfirmExit(false);
  };

  const exit = () => {
    reset();
    onClose();
  };

  // Esc: fecha a confirmação, depois a lista; senão pede confirmação para sair
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      e.preventDefault();
      if (confirmExit) setConfirmExit(false);
      else if (dropdownOpen) setDropdownOpen(false);
      else setConfirmExit(true);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, confirmExit, dropdownOpen]);

  useEffect(() => {
    if (confirmExit) stayRef.current?.focus();
  }, [confirmExit]);

  if (!isOpen) return null;

  const shown = manualMode ? manualResult : result;

  const addCreature = (creature: TreasureCreature) => {
    const existing = selected.some((s) => s.creature.name === creature.name);
    if (!existing && selected.length >= MAX_CREATURES) {
      setError(`Limite de ${MAX_CREATURES} criaturas diferentes por sorteio.`);
      return;
    }
    setSelected((prev) =>
      existing
        ? prev.map((s) =>
            s.creature.name === creature.name ? { ...s, quantity: Math.min(MAX_QUANTITY, s.quantity + 1) } : s
          )
        : [...prev, { creature, quantity: 1 }]
    );
    setQuery('');
    setDropdownOpen(false);
    setResult(null);
  };

  const setQuantity = (name: string, quantity: number) => {
    const value = Math.max(1, Math.min(MAX_QUANTITY, Number.isFinite(quantity) ? Math.round(quantity) : 1));
    setSelected((prev) => prev.map((s) => (s.creature.name === name ? { ...s, quantity: value } : s)));
    setResult(null);
  };

  const removeCreature = (name: string) => {
    setSelected((prev) => prev.filter((s) => s.creature.name !== name));
    setResult(null);
  };

  const handleSearchKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setDropdownOpen(true);
      setHighlight((h) => Math.min(h + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlight((h) => Math.max(h - 1, 0));
    } else if (e.key === 'Enter' && dropdownOpen && filtered[highlight]) {
      e.preventDefault();
      addCreature(filtered[highlight]);
    }
  };

  const handleTypedRoll = () => {
    if (!active || !activeLookup?.next || lookupBusy) return;
    const request = activeLookup.next;
    const value = parseRoll(typed, request);
    if (value === undefined) {
      const zero = request.sides === 100 && request.count === 1 ? ' (00 = 100)' : '';
      setLookupError(`O resultado de ${request.dice} deve ser um número de ${request.count} a ${request.count * request.sides}${zero}.`);
      return;
    }
    sendLookup(active, [...activeLookup.steps.map((s) => s.value), value]);
  };

  const undoTypedRoll = () => {
    if (!active || !activeLookup || activeLookup.steps.length === 0 || lookupBusy) return;
    sendLookup(active, activeLookup.steps.slice(0, -1).map((s) => s.value));
  };

  const restartLookups = () => {
    setLookups({});
    setTyped('');
    setLookupError(null);
  };

  const handleRoll = async () => {
    setError(null);
    setIsRolling(true);
    try {
      setResult(await treasureApiService.rollGroup(selected.map((s) => ({ creature: s.creature.name, quantity: s.quantity }))));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsRolling(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-[#0A0A10]/80 backdrop-blur-md z-50 flex items-center justify-center p-4 md:p-6">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="treasure-title"
        className="relative w-[92vw] h-[90vh] max-w-none bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Glow ambient effects */}
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#A259FF]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-32 -left-32 w-80 h-80 bg-[#39D98A]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Cabeçalho fixo */}
        <div className="flex items-center justify-between gap-3 p-6 md:px-8 border-b border-[#34344E]/70 relative z-10">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-[#1F1F26] border border-[#39D98A]/30 flex items-center justify-center shadow-md flex-shrink-0">
              <span className="material-symbols-outlined text-[#39D98A] text-2xl">diamond</span>
            </div>
            <div className="flex flex-col min-w-0">
              <h2 id="treasure-title" className="text-lg md:text-xl font-bold text-[#F0EEF8] tracking-tight uppercase">
                Sorteio de Tesouro
              </h2>
              <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                TABELAS 8-1 A 8-15 // TORMENTA20 - LIVRO BÁSICO
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setConfirmExit(true)}
            className="w-8 h-8 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] transition-colors cursor-pointer flex-shrink-0"
            title="Fechar (Esc)"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {/* Conteúdo com rolagem */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:px-8 flex flex-col gap-6 relative z-10">
          {/* 1. Criaturas */}
          <section className="flex flex-col gap-3">
            <h3 className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold flex items-center gap-1.5">
              <span className="material-symbols-outlined text-[15px] text-[#d8b9ff]">pets</span>
              Criaturas
            </h3>

            <div className="relative">
              <div className="flex items-center gap-2 bg-[#181827] border border-[#34344E] focus-within:border-[#A259FF]/60 rounded-xl px-3 transition-colors">
                <span className="material-symbols-outlined text-[18px] text-[#8B87A8]">search</span>
                <input
                  ref={searchRef}
                  value={query}
                  onChange={(e) => {
                    setQuery(e.target.value);
                    setHighlight(0);
                    setDropdownOpen(true);
                  }}
                  onFocus={() => setDropdownOpen(true)}
                  onBlur={() => setDropdownOpen(false)}
                  onKeyDown={handleSearchKey}
                  placeholder={loadingCreatures ? 'Carregando criaturas...' : 'Buscar criatura pelo nome'}
                  disabled={loadingCreatures}
                  role="combobox"
                  aria-expanded={dropdownOpen}
                  aria-controls="treasure-creature-list"
                  className="flex-1 min-w-0 bg-transparent py-2.5 text-sm text-[#F0EEF8] placeholder-[#8B87A8] outline-none"
                />
                <button
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    setDropdownOpen((open) => !open);
                    searchRef.current?.focus();
                  }}
                  className="text-[#8B87A8] hover:text-[#F0EEF8] cursor-pointer"
                  title="Mostrar lista"
                >
                  <span className="material-symbols-outlined text-[20px] block">
                    {dropdownOpen ? 'expand_less' : 'expand_more'}
                  </span>
                </button>
              </div>

              {dropdownOpen && (
                <ul
                  id="treasure-creature-list"
                  role="listbox"
                  className="absolute left-0 right-0 top-full mt-1 max-h-64 overflow-y-auto custom-scrollbar bg-[#13131F] border border-[#A259FF]/30 rounded-xl shadow-2xl z-20 py-1"
                >
                  {filtered.map((c, i) => (
                    <li
                      key={c.name}
                      role="option"
                      aria-selected={i === highlight}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        addCreature(c);
                      }}
                      onMouseEnter={() => setHighlight(i)}
                      className={`px-3 py-2 flex items-center justify-between gap-3 cursor-pointer text-sm ${
                        i === highlight ? 'bg-[#A259FF]/15 text-[#F0EEF8]' : 'text-[#c9c5de]'
                      }`}
                    >
                      <span className="truncate">{c.name}</span>
                      <span className="flex items-center gap-2 flex-shrink-0 font-mono text-[10px]">
                        <span className="text-[#8B87A8]">ND {c.nd}</span>
                        <span className={`px-1.5 py-0.5 rounded border ${TYPE_STYLE[c.treasure]}`}>{c.treasure}</span>
                      </span>
                    </li>
                  ))}
                  {filtered.length === 0 && (
                    <li className="px-3 py-2 text-xs text-[#8B87A8] font-mono">Nenhuma criatura encontrada.</li>
                  )}
                </ul>
              )}
            </div>

            {selected.length === 0 ? (
              <p className="p-3 text-center text-xs text-[#8B87A8] font-mono border border-dashed border-[#34344E] rounded-xl">
                Escolha uma criatura na lista para adicionar ao sorteio.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {selected.map(({ creature, quantity }) => (
                  <li
                    key={creature.name}
                    className="p-3 rounded-xl bg-[#181827]/70 border border-[#34344E] flex flex-wrap items-center justify-between gap-3"
                  >
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-semibold text-[#F0EEF8] truncate">{creature.name}</span>
                      <span className="flex items-center gap-2 font-mono text-[10px] text-[#8B87A8]">
                        ND {creature.nd} · p. {creature.page}
                        <span className={`px-1.5 py-0.5 rounded border ${TYPE_STYLE[creature.treasure]}`}>
                          {creature.treasure}
                        </span>
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex items-center rounded-lg border border-[#34344E] overflow-hidden">
                        <button
                          type="button"
                          onClick={() => setQuantity(creature.name, quantity - 1)}
                          className="w-8 h-8 flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] hover:bg-[#222236] cursor-pointer"
                          title="Menos uma"
                        >
                          <span className="material-symbols-outlined text-[16px]">remove</span>
                        </button>
                        <input
                          type="number"
                          min={1}
                          max={MAX_QUANTITY}
                          value={quantity}
                          onChange={(e) => setQuantity(creature.name, Number(e.target.value))}
                          aria-label={`Quantidade de ${creature.name}`}
                          className="w-12 h-8 bg-[#13131F] text-center text-sm font-mono text-[#F0EEF8] outline-none [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
                        />
                        <button
                          type="button"
                          onClick={() => setQuantity(creature.name, quantity + 1)}
                          className="w-8 h-8 flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] hover:bg-[#222236] cursor-pointer"
                          title="Mais uma"
                        >
                          <span className="material-symbols-outlined text-[16px]">add</span>
                        </button>
                      </div>
                      <button
                        type="button"
                        onClick={() => removeCreature(creature.name)}
                        className="w-8 h-8 rounded-lg flex items-center justify-center text-[#8B87A8] hover:text-red-300 hover:bg-red-500/10 cursor-pointer"
                        title="Remover criatura"
                      >
                        <span className="material-symbols-outlined text-[18px]">delete</span>
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 2. Rolagem */}
          {selected.length > 0 && (
            <section className="flex flex-col gap-3">
              <h3 className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px] text-[#39D98A]">casino</span>
                Rolagem
              </h3>

              <div className="grid grid-cols-2 gap-2 p-1 rounded-xl bg-[#181827] border border-[#34344E] font-mono text-xs">
                {[
                  { manual: false, label: 'Rolagem automática', icon: 'auto_awesome' },
                  { manual: true, label: 'Informar resultados', icon: 'edit_note' },
                ].map((option) => (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => setManualMode(option.manual)}
                    className={`py-2 rounded-lg flex items-center justify-center gap-1.5 transition-colors cursor-pointer ${
                      manualMode === option.manual
                        ? 'bg-[#A259FF]/25 text-[#F0EEF8] border border-[#A259FF]/50'
                        : 'text-[#8B87A8] hover:text-[#F0EEF8] border border-transparent'
                    }`}
                  >
                    <span className="material-symbols-outlined text-[16px]">{option.icon}</span>
                    {option.label}
                  </button>
                ))}
              </div>

              {manualMode ? (
                <div className="flex flex-col gap-3">
                  {/* Dados a rolar: as primeiras rolagens de cada criatura e o que vem depois */}
                  <div className="p-3 rounded-xl bg-[#181827]/50 border border-[#34344E] flex flex-col gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-[#8B87A8]">Dados a rolar</span>
                    <ul className="flex flex-col gap-1 text-xs text-[#c9c5de]">
                      {selected.map(({ creature, quantity }) => {
                        const per = rollsPerColumn(creature);
                        return (
                          <li key={creature.name} className="flex flex-wrap gap-x-2">
                            <span className="font-semibold text-[#F0EEF8]">
                              {creature.name} x{quantity}:
                            </span>
                            {per === 0 ? (
                              <span className="text-[#8B87A8]">tesouro Nenhum ou especial, sem rolagem</span>
                            ) : (
                              <span>
                                {per * quantity}x <b className="text-[#39D98A]">1d100</b> para Dinheiro e{' '}
                                {per * quantity}x <b className="text-[#39D98A]">1d100</b> para Itens na Tabela 8-1 (ND{' '}
                                {creature.nd}
                                {per === 2 ? ', tesouro Dobro: 2 de cada por criatura' : ''})
                              </span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                    <p className="font-mono text-[10px] text-[#8B87A8]">
                      Depois, cada resultado pede os seus dados: a quantidade de moedas (ex.: 2d8 x100 T$), o tipo do item
                      (1d6) e um 1d100 em cada tabela seguinte (8-2 a 8-15). O sistema pede um por vez, com a tabela e o
                      motivo, e consulta o valor informado.
                    </p>
                  </div>

                  {/* Consulta da unidade atual */}
                  {active ? (
                    <div className="p-4 rounded-xl bg-[#13131F] border border-[#A259FF]/40 flex flex-col gap-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <span className="text-sm font-semibold text-[#F0EEF8]">
                          {active.creature.name} <span className="font-mono text-xs text-[#8B87A8]">#{active.unit + 1}</span>
                        </span>
                        <span className="font-mono text-[10px] text-[#8B87A8]">
                          {doneCount} de {units.length} concluída(s)
                        </span>
                      </div>

                      {activeLookup && activeLookup.steps.length > 0 && (
                        <ol
                          ref={stepsRef}
                          className="max-h-48 overflow-y-auto custom-scrollbar flex flex-col gap-1.5 font-mono text-[10px] text-[#8B87A8] pr-1"
                        >
                          {activeLookup.steps.map((step, i) => {
                            const rejected = step.outcome.endsWith('role de novo');
                            return (
                              <li key={i} className="flex gap-2">
                                <span className="text-[#d8b9ff] flex-shrink-0 w-20">
                                  {step.dice} = {step.value}
                                </span>
                                <span className="flex flex-col min-w-0">
                                  <span className="break-words">{step.purpose.split('. Role de novo:')[0]}</span>
                                  {step.outcome && (
                                    <span className={`break-words ${rejected ? 'text-amber-300' : 'text-[#39D98A]'}`}>
                                      → {step.outcome}
                                    </span>
                                  )}
                                </span>
                              </li>
                            );
                          })}
                        </ol>
                      )}

                      {activeLookup?.next ? (
                        <div className="flex flex-col gap-2">
                          <div className="flex items-start gap-2">
                            <span className="material-symbols-outlined text-[20px] text-[#39D98A]">casino</span>
                            <div className="flex flex-col">
                              <span className="text-sm font-bold text-[#39D98A]">{rollHint(activeLookup.next)}</span>
                              <span className="text-xs text-[#c9c5de] break-words">
                                {activeLookup.next.purpose.split('. Role de novo:')[0]}
                              </span>
                              {activeLookup.next.purpose.includes('. Role de novo:') && (
                                <span className="text-xs text-amber-300 break-words">
                                  Role de novo: {activeLookup.next.purpose.split('. Role de novo:')[1].trim()}
                                </span>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-wrap items-center gap-2">
                            <input
                              ref={rollInputRef}
                              inputMode="numeric"
                              maxLength={4}
                              value={typed}
                              onChange={(e) => setTyped(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                  e.preventDefault();
                                  handleTypedRoll();
                                }
                              }}
                              placeholder={`${activeLookup.next.count}-${activeLookup.next.count * activeLookup.next.sides}`}
                              aria-label={`Resultado de ${activeLookup.next.dice}`}
                              disabled={lookupBusy}
                              className="w-24 h-10 rounded-lg bg-[#181827] border border-[#34344E] focus:border-[#A259FF]/60 text-center text-base font-mono text-[#F0EEF8] placeholder-[#8B87A8]/60 outline-none"
                            />
                            <button
                              type="button"
                              onClick={handleTypedRoll}
                              disabled={lookupBusy || !typed.trim()}
                              className="h-10 px-4 rounded-lg bg-[#A259FF]/25 hover:bg-[#A259FF]/35 border border-[#A259FF]/50 text-xs font-semibold text-[#F0EEF8] flex items-center gap-1.5 disabled:opacity-50 cursor-pointer"
                            >
                              <span className="material-symbols-outlined text-[16px]">
                                {lookupBusy ? 'sync' : 'manage_search'}
                              </span>
                              Consultar tabela
                            </button>
                            <button
                              type="button"
                              onClick={undoTypedRoll}
                              disabled={lookupBusy || activeLookup.steps.length === 0}
                              className="h-10 px-3 rounded-lg border border-[#34344E] text-xs text-[#8B87A8] hover:text-[#F0EEF8] hover:bg-[#222236] flex items-center gap-1 disabled:opacity-40 cursor-pointer"
                              title="Desfazer o último resultado informado"
                            >
                              <span className="material-symbols-outlined text-[16px]">undo</span>
                              Desfazer
                            </button>
                          </div>
                        </div>
                      ) : (
                        !lookupError && (
                          <span className="font-mono text-[10px] text-[#8B87A8] flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-[14px] animate-spin">sync</span>
                            Consultando...
                          </span>
                        )
                      )}

                      {lookupError && (
                        <div className="flex flex-wrap items-center gap-2 text-xs text-red-200">
                          <span className="material-symbols-outlined text-[16px] text-red-300">error</span>
                          <span className="flex-1 min-w-0">{lookupError}</span>
                          {!activeLookup && (
                            <button
                              type="button"
                              onClick={() => setLookupError(null)}
                              className="px-2 py-1 rounded border border-red-400/40 hover:bg-red-500/15 cursor-pointer"
                            >
                              Tentar de novo
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <p className="p-3 rounded-xl bg-[#39D98A]/10 border border-[#39D98A]/30 text-xs text-[#39D98A] flex items-center gap-2">
                      <span className="material-symbols-outlined text-[16px]">check_circle</span>
                      Todas as criaturas foram consultadas. O resultado está abaixo.
                    </p>
                  )}

                  {doneCount > 0 && (
                    <button
                      type="button"
                      onClick={restartLookups}
                      disabled={lookupBusy}
                      className="self-start px-3 py-1.5 rounded-lg border border-[#34344E] text-[11px] text-[#8B87A8] hover:text-[#F0EEF8] hover:bg-[#222236] flex items-center gap-1 cursor-pointer"
                    >
                      <span className="material-symbols-outlined text-[14px]">restart_alt</span>
                      Recomeçar consulta
                    </button>
                  )}
                </div>
              ) : (
                <button
                  type="button"
                  onClick={handleRoll}
                  disabled={isRolling}
                  className="w-full py-3 rounded-xl bg-gradient-to-r from-[#A259FF]/30 to-[#39D98A]/25 hover:from-[#A259FF]/40 hover:to-[#39D98A]/35 border border-[#A259FF]/50 text-[#F0EEF8] text-sm font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-60 cursor-pointer"
                >
                  <span className={`material-symbols-outlined text-[20px] text-[#39D98A] ${isRolling ? 'animate-spin' : ''}`}>
                    {isRolling ? 'sync' : 'casino'}
                  </span>
                  {isRolling ? 'Sorteando...' : result ? 'Sortear novamente' : 'Sortear tesouro'}
                </button>
              )}
            </section>
          )}

          {error && (
            <div className="p-3 rounded-xl bg-red-500/10 border border-red-400/30 text-xs text-red-200 flex items-start gap-2">
              <span className="material-symbols-outlined text-[16px] text-red-300">error</span>
              <span>{error}</span>
            </div>
          )}

          {/* 3. Resultado */}
          {shown && (
            <section className="flex flex-col gap-3">
              <div className="flex items-center justify-between gap-3">
                <h3 className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[15px] text-[#39D98A]">paid</span>
                  Resultado
                </h3>
                <span className="font-mono text-xs text-[#39D98A]" title="Soma de moedas, riquezas e itens com preço (opções 2D não entram)">
                  Total: {formatValue(shown.totalValue)}
                </span>
              </div>

              {shown.groups.map((group) => (
                <div key={group.creature.name} className="rounded-xl border border-[#34344E] bg-[#181827]/60 overflow-hidden">
                  <div className="px-4 py-2.5 border-b border-[#34344E] flex items-center justify-between gap-3">
                    <span className="text-sm font-semibold text-[#F0EEF8] truncate">
                      {group.creature.name}{' '}
                      <span className="text-[#8B87A8] font-mono text-xs">
                        {group.results.length < group.quantity
                          ? `${group.results.length} de ${group.quantity}`
                          : `x${group.quantity}`}
                      </span>
                    </span>
                    <span className="font-mono text-[11px] text-[#39D98A] flex-shrink-0">{formatValue(group.totalValue)}</span>
                  </div>

                  <div className="divide-y divide-[#34344E]/60">
                    {group.results.map((res, unit) => (
                      <div key={res.id} className="px-4 py-3 flex flex-col gap-2">
                        <span className="font-mono text-[10px] text-[#8B87A8]">
                          #{unit + 1} · ND {res.nd} · tesouro {res.treasureType}
                        </span>
                        {res.notes.map((note) => (
                          <p key={note} className="text-xs text-amber-200/90">{note}</p>
                        ))}
                        {res.rolls.map((roll, i) => (
                          <div key={i} className="flex flex-col gap-1.5">
                            <div className="flex flex-wrap items-center gap-2 font-mono text-[10px]">
                              <span className="px-1.5 py-0.5 rounded bg-[#222236] text-[#d8b9ff] uppercase">{roll.column}</span>
                              <span className="text-[#F0EEF8]">d% {roll.roll}</span>
                              <span className={manualMode ? 'text-amber-300' : 'text-[#8B87A8]'}>
                                {manualMode ? 'informado' : 'automático'}
                              </span>
                              <span className="text-[#8B87A8]">→ {roll.result}</span>
                              <span className="text-[#8B87A8]/70">({roll.source})</span>
                            </div>
                            {roll.rewards.length > 0 && (
                              <ul className="ml-3 pl-3 border-l border-[#39D98A]/30 flex flex-col gap-2">
                                {roll.rewards.map((reward, j) => (
                                  <RewardItem key={j} reward={reward} />
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </section>
          )}
        </div>

        {/* Confirmação de saída */}
        {confirmExit && (
          <div className="absolute inset-0 z-30 bg-[#0A0A10]/75 backdrop-blur-sm flex items-center justify-center p-4">
            <div
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="treasure-exit-title"
              className="w-full max-w-sm bg-[#13131F] border border-[#A259FF]/40 rounded-2xl p-6 flex flex-col gap-4 shadow-2xl"
            >
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-amber-300">warning</span>
                <h3 id="treasure-exit-title" className="text-base font-bold text-[#F0EEF8]">Sair do sorteio?</h3>
              </div>
              <p className="text-xs text-[#c9c5de]">
                As criaturas escolhidas e os resultados digitados serão descartados. Os sorteios já feitos ficam salvos no
                seu histórico.
              </p>
              <div className="flex justify-end gap-2">
                <button
                  ref={stayRef}
                  type="button"
                  onClick={() => setConfirmExit(false)}
                  className="px-4 py-2 rounded-lg bg-[#181827] border border-[#34344E] text-xs text-[#F0EEF8] hover:bg-[#222236] cursor-pointer"
                >
                  Continuar
                </button>
                <button
                  type="button"
                  onClick={exit}
                  className="px-4 py-2 rounded-lg bg-red-500/15 border border-red-400/40 text-xs text-red-200 hover:bg-red-500/25 cursor-pointer"
                >
                  Sair
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
