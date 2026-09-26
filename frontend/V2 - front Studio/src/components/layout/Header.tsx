import React from 'react';
import { OperatorProfile } from '../../types';

interface HeaderProps {
  chaosLevel: number;
  onChaosChange: (val: number) => void;
  onToggleSidebar: () => void;
  onOpenUploadModal: () => void;
  onNavigateLogin: () => void;
  operator: OperatorProfile;
  currentScreen: 'terminal' | 'login';
}

export const Header: React.FC<HeaderProps> = ({
  chaosLevel,
  onChaosChange,
  onToggleSidebar,
  onOpenUploadModal,
  onNavigateLogin,
  operator,
  currentScreen,
}) => {
  // Determine dynamic chaos badge label and color
  const getChaosBadge = () => {
    if (chaosLevel < 30) {
      return {
        label: 'Ordem',
        className: 'bg-blue-500/10 text-blue-400 border-blue-500/30',
      };
    } else if (chaosLevel < 70) {
      return {
        label: 'Equilibrado',
        className: 'bg-purple-500/15 text-[#d8b9ff] border-purple-500/30',
      };
    } else if (chaosLevel < 90) {
      return {
        label: 'Instável',
        className: 'bg-[#39d98a]/15 text-[#39d98a] border-[#39d98a]/30',
      };
    } else {
      return {
        label: 'CAOS TOTAL!',
        className: 'bg-red-500/20 text-red-400 border-red-500/50 animate-pulse',
      };
    }
  };

  const badge = getChaosBadge();

  return (
    <header className="h-16 flex-shrink-0 border-b border-[rgba(162,89,255,0.25)] bg-[#0D0D14]/90 backdrop-blur-xl px-4 md:px-6 flex items-center justify-between z-30 relative select-none">
      {/* Left: Logo & Project Name */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleSidebar}
          className="md:hidden p-2 rounded-lg bg-[#13131F] border border-[rgba(162,89,255,0.25)] text-[#8B87A8] hover:text-[#F0EEF8] transition-colors"
          title="Abrir Menu Lateral"
        >
          <span className="material-symbols-outlined text-[20px] block">menu</span>
        </button>

        <div
          className="relative w-10 h-10 rounded-xl overflow-hidden border border-[rgba(162,89,255,0.3)] flex items-center justify-center p-0.5 bg-[#13131F] shadow-[0_0_12px_rgba(162,89,255,0.25)] group cursor-pointer"
          title="Nimb Core Avatar"
          onClick={() => onNavigateLogin()}
        >
          <img
            alt="Nimb Mascot"
            referrerPolicy="no-referrer"
            className="w-full h-full object-cover rounded-lg group-hover:scale-110 transition-transform duration-300"
            src="https://lh3.googleusercontent.com/aida/AEtjO1VeZBenvo1EbBBHx1FCf1uEDMzj2vDFk-dsyMejBABVcZInwDymH5IfVK8E8VvWse6MmYhip_RjWrR87W_Dka3BxvnTXRfnIoXv16FZpPwGRfcY9UfwbIlgMTKEwOwZp2-4qtEM7vqAzLb_sexGZbohFocz7yo6EyFICdgMUXbnIJV4Nagsih0WZUnDeK60xI03S0lSg68d1qhmwWt2u5kUvh_fWVobKAkLJxhS1zN4-3p5ruEYIDpebZgRiHQC6ShBUloIEoz58w"
            onError={(e) => {
              // Graceful SVG fallback
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg md:text-xl tracking-tight bg-gradient-to-r from-[#d8b9ff] via-[#A259FF] to-[#39D98A] bg-clip-text text-transparent">
              NIMB_OS
            </span>
            <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-[#A259FF]/20 text-[#d8b9ff] border border-[#A259FF]/30">
              RAG v2.4
            </span>
          </div>
          <p className="font-mono text-[10px] text-[#8B87A8] leading-none hidden sm:block">
            NEURAL CHAOS RETRIEVAL ENGINE
          </p>
        </div>
      </div>

      {/* Center: Medidor de Caos (Chaos Meter Interactive) */}
      <div className="flex items-center gap-2 sm:gap-3 bg-[#13131F]/90 px-3 sm:px-4 py-1.5 rounded-full border border-[rgba(162,89,255,0.25)] shadow-inner">
        <div className="flex items-center gap-1.5">
          <span
            className="material-symbols-outlined text-[#39D98A] text-[18px] animate-spin"
            style={{ animationDuration: '8s' }}
          >
            casino
          </span>
          <span className="font-mono text-xs uppercase font-semibold tracking-wider text-[#8B87A8] hidden md:inline">
            Medidor de Caos:
          </span>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="range"
            min="0"
            max="100"
            value={chaosLevel}
            onChange={(e) => onChaosChange(Number(e.target.value))}
            className="chaos-slider w-20 sm:w-28 md:w-36 h-1.5 bg-[#222236] rounded-lg appearance-none cursor-pointer"
            title={`Nível de Caos: ${chaosLevel}%`}
          />
          <div className="flex items-baseline font-mono text-xs font-bold text-[#39D98A] w-9 text-right tabular-nums">
            <span>{chaosLevel}</span>%
          </div>
        </div>

        <span
          className={`hidden lg:inline text-[10px] font-mono uppercase px-2 py-0.5 rounded-full border transition-all ${badge.className}`}
        >
          {badge.label}
        </span>
      </div>

      {/* Right: Actions, Upload Trigger, Link Status & Auth Button */}
      <div className="flex items-center gap-2.5">
        {/* Upload PDF Modal button */}
        <button
          onClick={onOpenUploadModal}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#39D98A]/30 text-xs font-mono text-[#39D98A] transition-all hover:scale-102 active:scale-98 shadow-sm"
          title="Carregar Grimório em PDF"
        >
          <span className="material-symbols-outlined text-[16px]">upload_file</span>
          <span className="hidden md:inline">Subir PDF</span>
        </button>

        {/* Neural Link Status */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#181827] border border-[#39D98A]/25">
          <span className="w-2 h-2 rounded-full bg-[#39D98A] pulse-status"></span>
          <span className="font-mono text-xs text-[#39D98A] font-medium hidden lg:inline">
            Neural Link Ativo
          </span>
        </div>

        {/* Login / Operator Navigation toggle */}
        <button
          onClick={onNavigateLogin}
          className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
            currentScreen === 'login'
              ? 'bg-[#A259FF]/20 border-[#A259FF] text-white shadow-[0_0_12px_rgba(162,89,255,0.3)]'
              : 'bg-[#13131F] border-[rgba(162,89,255,0.25)] text-[#8B87A8] hover:text-[#F0EEF8] hover:border-[#A259FF]/50'
          }`}
          title="Tela de Autenticação / Google Workspace"
        >
          <span className="material-symbols-outlined text-[17px] text-[#A259FF]">
            account_circle
          </span>
          <span className="hidden sm:inline font-mono text-[11px] truncate max-w-[90px]">
            {operator.isAuthenticated ? 'Nexus' : 'Login'}
          </span>
        </button>
      </div>
    </header>
  );
};
