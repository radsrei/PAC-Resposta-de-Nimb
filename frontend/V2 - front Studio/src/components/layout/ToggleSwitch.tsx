import React from 'react';

// Chave liga/desliga no estilo do Medidor de Caos (pílula laranja quando ligada).
// Usada no botão "Regra" do topo e nos efeitos sonoros da tela Minha conta.

interface ToggleSwitchProps {
  checked: boolean;
  onToggle: () => void;
  label: string;
  title?: string;
  /** Classes do texto; o topo esconde o texto em telas pequenas ('hidden sm:inline'). */
  labelClassName?: string;
}

export const ToggleSwitch: React.FC<ToggleSwitchProps> = ({
  checked,
  onToggle,
  label,
  title,
  labelClassName = '',
}) => (
  <button
    type="button"
    role="switch"
    aria-checked={checked}
    aria-label={label}
    onClick={onToggle}
    title={title}
    className={`flex items-center gap-1.5 text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border transition-colors cursor-pointer ${
      checked
        ? 'bg-[#FF8A00]/15 text-[#FFB547] border-[#FF8A00]/50'
        : 'bg-[#222236] text-[#8B87A8] border-[#34344E] hover:text-[#F0EEF8]'
    }`}
  >
    <span
      className={`relative w-6 h-3 rounded-full transition-colors ${checked ? 'bg-[#FF8A00]' : 'bg-[#34344E]'}`}
    >
      <span
        className={`absolute top-0.5 w-2 h-2 rounded-full bg-[#F0EEF8] transition-all ${
          checked ? 'left-3.5' : 'left-0.5'
        }`}
      />
    </span>
    <span className={labelClassName}>{label}</span>
  </button>
);
