import React from 'react';

interface SuggestionChipsProps {
  onSelectSuggestion: (text: string) => void;
  disabled?: boolean;
}

const DEFAULT_SUGGESTIONS = [
  { text: 'Qual o efeito da magia do Caos?', iconColor: 'text-[#39D98A]' },
  { text: 'Resumir atributos de Nimb', iconColor: 'text-[#d8b9ff]' },
  { text: 'Consultar tabela de perícias', iconColor: 'text-[#39D98A]' },
  { text: 'Regras de combate aleatório', iconColor: 'text-[#d8b9ff]' },
];

export const SuggestionChips: React.FC<SuggestionChipsProps> = ({
  onSelectSuggestion,
  disabled = false,
}) => {
  return (
    <div className="flex items-center gap-2 overflow-x-auto custom-scrollbar pb-1 text-xs whitespace-nowrap">
      {DEFAULT_SUGGESTIONS.map((s, idx) => (
        <button
          key={idx}
          disabled={disabled}
          onClick={() => onSelectSuggestion(s.text)}
          className="px-3 py-1.5 rounded-full bg-[#181827] hover:bg-[#222236] border border-[rgba(162,89,255,0.25)] hover:border-[#39D98A]/50 text-[#8B87A8] hover:text-[#F0EEF8] transition-all font-mono text-[11px] flex items-center gap-1 active:scale-95 disabled:opacity-50 cursor-pointer shadow-sm"
        >
          <span className={s.iconColor}>✦</span>
          <span>{s.text}</span>
        </button>
      ))}
    </div>
  );
};
