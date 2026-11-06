import React, { useEffect } from 'react';
import { STORE_INTRO, STORE_PRODUCTS, STORE_CUPOM, STORE_URL } from '../../data/produtos';

interface StoreModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const StoreModal: React.FC<StoreModalProps> = ({ isOpen, onClose }) => {
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
        aria-labelledby="store-title"
        className="relative w-full max-w-3xl max-h-[90vh] bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl shadow-2xl overflow-hidden flex flex-col"
      >
        {/* Glow ambient effects */}
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#A259FF]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-32 -left-32 w-80 h-80 bg-[#39D98A]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Cabeçalho fixo */}
        <div className="flex items-center justify-between gap-3 p-6 md:px-8 border-b border-[#34344E]/70 relative z-10">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-[#1F1F26] border border-[#39D98A]/30 flex items-center justify-center shadow-md flex-shrink-0">
              <span className="material-symbols-outlined text-[#39D98A] text-2xl">store</span>
            </div>
            <div className="flex flex-col min-w-0">
              <h2
                id="store-title"
                className="text-lg md:text-xl font-bold text-[#F0EEF8] tracking-tight uppercase"
              >
                Ado Escudos
              </h2>
              <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                {STORE_INTRO}       
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-5 h-5 rounded-xl bg-[#1F1F26] border border-[#39D98A]/30 flex items-center justify-center shadow-md flex-shrink-0">
              <span className="material-symbols-outlined text-[#39D98A] text-2xl">percent_discount</span>
            </div>
            <div className="flex flex-col min-w-0">
                <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                  {STORE_CUPOM}
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

        {/* Lista de produtos com rolagem */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 md:px-8 relative z-10">
          {STORE_PRODUCTS.length === 0 ? (
            <p className="font-mono text-xs text-[#8B87A8] text-center py-8">
              Nimb ainda não decidiu o que vender.
            </p>
          ) : (
            <ul className="flex flex-col gap-3">
              {STORE_PRODUCTS.map((product) => (
                <li
                  key={product.url}
                  className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl bg-[#13131F] border border-[#34344E]/70 hover:border-[#A259FF]/40 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <h3 className="font-bold text-[#d8b9ff] text-base break-words">
                      {product.name}
                    </h3>
                    <p className="text-sm text-[#F0EEF8]/80 mt-1 break-words">
                      {product.description}
                    </p>
                  </div>
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="self-start sm:self-center flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#39D98A]/30 text-xs font-mono text-[#39D98A] transition-colors flex-shrink-0"
                    title={`Ver ${product.name} na loja`}
                  >
                    <span>Ver na loja</span>
                    <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Rodapé fixo: redirecionamento para a loja */}
        <div className="p-6 md:px-8 border-t border-[#34344E]/70 relative z-10 flex justify-center">
          <a
            href={STORE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full sm:w-auto px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#A259FF] to-[#39D98A] text-[#0D0D14] font-bold text-sm uppercase tracking-wide shadow-[0_0_16px_rgba(162,89,255,0.35)] hover:scale-102 active:scale-98 transition-transform"
          >
            <span className="material-symbols-outlined text-[18px]">storefront</span>
            Visitar a loja <s>de Nimb</s> da Jambô
          </a>
        </div>
      </div>
    </div>
  );
};
