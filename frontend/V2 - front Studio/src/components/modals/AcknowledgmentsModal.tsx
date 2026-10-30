import React, { useEffect } from 'react';
import { ACKNOWLEDGMENTS, ACKNOWLEDGMENTS_INTRO } from '../../data/agradecimentos';

interface AcknowledgmentsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const AcknowledgmentsModal: React.FC<AcknowledgmentsModalProps> = ({ isOpen, onClose }) => {
  // Fecha com Esc
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-[#0A0A10]/80 backdrop-blur-md z-50 flex items-center justify-center p-4 md:p-6 animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="acknowledgments-title"
        className="relative w-full max-w-3xl max-h-[90vh] bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Glow ambient effects */}
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#A259FF]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-32 -left-32 w-80 h-80 bg-[#39D98A]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Cabeçalho fixo */}
        <div className="flex items-center justify-between gap-3 p-6 md:px-8 border-b border-[#34344E]/70 relative z-10">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-[#1F1F26] border border-[#39D98A]/30 flex items-center justify-center shadow-md flex-shrink-0">
              <span className="material-symbols-outlined text-[#39D98A] text-2xl">favorite</span>
            </div>
            <div className="flex flex-col min-w-0">
              <h2
                id="acknowledgments-title"
                className="text-lg md:text-xl font-bold text-[#F0EEF8] tracking-tight uppercase"
              >
                Agradecimentos
              </h2>
              <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                {ACKNOWLEDGMENTS_INTRO}
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] transition-colors cursor-pointer flex-shrink-0"
            title="Fechar"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {/* Conteúdo com rolagem */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:px-8 flex flex-col gap-6 relative z-10">
          {ACKNOWLEDGMENTS.map((section) => (
            <section key={section.title} className="flex flex-col gap-3">
              <div className="pb-2 border-b border-[#34344E]/60">
                <h3 className="font-bold text-[#d8b9ff] text-base">{section.title}</h3>
                {section.subtitle && (
                  <p className="font-mono text-[10px] uppercase tracking-wider text-[#8B87A8] mt-0.5">
                    {section.subtitle}
                  </p>
                )}
              </div>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
                {section.names.map((name) => (
                  <li key={name} className="flex items-center gap-2 text-sm text-[#F0EEF8]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#39D98A] flex-shrink-0"></span>
                    <span className="break-words min-w-0">{name}</span>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
};
