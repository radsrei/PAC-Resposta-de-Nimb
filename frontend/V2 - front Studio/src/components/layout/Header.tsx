import React from 'react';
import { LlmConnection, OperatorProfile, ScreenView } from '../../types';
import { CHAOS_LEVELS, getChaosLevel } from '../../chaosLevels';
import { ToggleSwitch } from './ToggleSwitch';

interface HeaderProps {
  chaosLevel: number;
  onChaosChange: (val: number) => void;
  useChaosRule: boolean;
  onToggleChaosRule: () => void;
  onToggleSidebar: () => void;
  onOpenStoreModal: () => void;
  onOpenUploadModal: () => void;
  onNavigateLogin: () => void;
  onOpenLlmModal: () => void;
  llmConnection: LlmConnection | null;
  backendOnline: boolean;
  operator: OperatorProfile;
  currentScreen: ScreenView;
}

export const Header: React.FC<HeaderProps> = ({
  chaosLevel,
  onChaosChange,
  useChaosRule,
  onToggleChaosRule,
  onToggleSidebar,
  onOpenStoreModal,
  onOpenUploadModal,
  onNavigateLogin,
  onOpenLlmModal,
  llmConnection,
  backendOnline,
  operator,
  currentScreen,
}) => {
  const badge = getChaosLevel(chaosLevel);

  return (
    <header className="chaos-glow-target h-16flex-shrink-0 border-b border-[rgba(162,89,255,0.25)] bg-[#0D0D14]/90 backdrop-blur-xl px-4 md:px-6 flex items-center justify-between z-30 relative select-none">
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
            className="w-full h-full object-contain rounded-lg group-hover:scale-110 transition-transform duration-300"
            src="/favicon.png"
            onError={(e) => {
              // Graceful SVG fallback
              (e.target as HTMLElement).style.display = 'none';
            }}
          />
        </div>

        <div>
          <div className="flex items-center gap-2">
            <span className="font-bold text-lg md:text-xl tracking-tight bg-gradient-to-r from-[#d8b9ff] via-[#A259FF] to-[#39D98A] bg-clip-text text-transparent">
              Respostas de Nimb
            </span>
            <span className="font-mono text-[10px] uppercase px-1.5 py-0.5 rounded bg-[#A259FF]/20 text-[#d8b9ff] border border-[#A259FF]/30">
              Versão X.Y
            </span>
          </div>
          <p className="font-mono text-[10px] text-[#8B87A8] leading-none hidden sm:block">
            Caótico, Formiável, Impreciso e Batata. <br></br><span className="text-[#39D98A]">Nimb</span> é um Deus que responde perguntas com base na vontade dele e talvez baseado em livros.
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
            max={CHAOS_LEVELS.length - 1}
            step="1"
            list="chaos-levels"
            value={chaosLevel}
            onChange={(e) => onChaosChange(Number(e.target.value))}
            className="chaos-slider w-16 sm:w-24 md:w-28 h-1.5 bg-[#222236] rounded-lg appearance-none cursor-pointer"
            title={`Nível de Caos: ${badge.label}`}
          />
          <datalist id="chaos-levels">
            {CHAOS_LEVELS.map((level) => (
              <option key={level.id} value={level.id} label={level.label} />
            ))}
          </datalist>
          <div className="font-mono text-xs font-bold text-[#39D98A] w-11 uppercase">
            {badge.label}
          </div>
        </div>

        <ToggleSwitch
          checked={useChaosRule}
          onToggle={onToggleChaosRule}
          label="Regra"
          labelClassName="hidden sm:inline"
          title={
            useChaosRule
              ? 'Regra Nimb ligada: a alucinação é decidida pela regra (palavras x primo + data) antes da pergunta'
              : 'Regra Nimb desligada: a alucinação é sorteada com a chance do nível depois da busca nos livros'
          }
        />
      </div>

      {/* Right: Actions, Upload Trigger, Link Status & Auth Button */}
      <div className="flex items-center gap-2.5">
        {/* Loja (Produtinhos de Nimb) Modal button */}
        <button
          onClick={onOpenStoreModal}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#39D98A]/30 text-xs font-mono text-[#39D98A] transition-all hover:scale-102 active:scale-98 shadow-sm"
          title="Loja de Produtos de Nimb"
        >
          <span className="material-symbols-outlined text-[16px]">store</span>
          <span className="hidden md:inline">Ado Escudos</span>
        </button>

        {/* Upload PDF Modal button */}
        <button
          onClick={onOpenUploadModal}
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#39D98A]/30 text-xs font-mono text-[#39D98A] transition-all hover:scale-102 active:scale-98 shadow-sm"
          title="Carregar Livro em PDF"
        >
          <span className="material-symbols-outlined text-[16px]">upload_file</span>
          <span className="hidden md:inline">Subir PDF</span>
        </button>

        {/* Conexão LLM: status + abre a caixa de configuração da API */}
        <button
          onClick={onOpenLlmModal}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#181827] border transition-all cursor-pointer hover:bg-[#222236] ${
            !backendOnline
              ? 'border-red-500/40'
              : llmConnection
                ? 'border-[#39D98A]/30'
                : 'border-amber-400/40'
          }`}
          title={
            !backendOnline
              ? 'Backend offline — clique para configurar a LLM'
              : llmConnection
                ? `LLM ativa: ${llmConnection.name} (${llmConnection.model})`
                : 'Nenhuma LLM conectada — clique para configurar'
          }
        >
          <span
            className={`w-2 h-2 rounded-full ${
              !backendOnline
                ? 'bg-red-400'
                : llmConnection
                  ? 'bg-[#39D98A] pulse-status'
                  : 'bg-amber-400 animate-pulse'
            }`}
          ></span>
          <span className="material-symbols-outlined text-[16px] text-[#d8b9ff]">hub</span>
          <span
            className={`font-mono text-xs font-medium hidden lg:inline truncate max-w-[160px] ${
              !backendOnline ? 'text-red-300' : llmConnection ? 'text-[#39D98A]' : 'text-amber-300'
            }`}
          >
            {!backendOnline
              ? 'Backend Offline'
              : llmConnection
                ? llmConnection.model
                : 'Conectar LLM'}
          </span>
        </button>

        {/* Login / Operator Navigation toggle */}
        <button
          onClick={onNavigateLogin}
          className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
            currentScreen === 'account'
              ? 'bg-[#A259FF]/20 border-[#A259FF] text-white shadow-[0_0_12px_rgba(162,89,255,0.3)]'
              : 'bg-[#13131F] border-[rgba(162,89,255,0.25)] text-[#8B87A8] hover:text-[#F0EEF8] hover:border-[#A259FF]/50'
          }`}
          title="Minha conta"
        >
          <span className="material-symbols-outlined text-[17px] text-[#A259FF]">
            account_circle
          </span>
          <span className="hidden sm:inline font-mono text-[11px] truncate max-w-[90px]">
            {operator.name.split(' ')[0]}
          </span>
        </button>
      </div>
    </header>
  );
};
