import React, { useState } from 'react';
import { OperatorProfile } from '../../types';
import { authApiService } from '../../services/authApi';

interface LoginScreenProps {
  onSuccess: (profile: OperatorProfile) => void;
  onBackToTerminal: () => void;
  currentOperator: OperatorProfile;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({
  onSuccess,
  onBackToTerminal,
  currentOperator,
}) => {
  const [email, setEmail] = useState(currentOperator.email || 'operador@cluster-nimb.network');
  const [token, setToken] = useState('0x9F4A87C3120E8B90');
  const [showPassword, setShowPassword] = useState(false);
  const [keepActive, setKeepActive] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [googleOauthSuccess, setGoogleOauthSuccess] = useState(
    currentOperator.provider === 'google'
  );

  const handleGoogleAuth = async () => {
    setIsSyncing(true);
    setSyncStatus('Conectando ao Google Workspace OAuth 2.0...');

    try {
      const profile = await authApiService.loginWithGoogle();
      setGoogleOauthSuccess(true);
      setSyncStatus('OAUTH 2.0 VERIFICADO // ESCOPO RAG ATIVO');
      setTimeout(() => {
        setIsSyncing(false);
        onSuccess(profile);
      }, 1000);
    } catch {
      setIsSyncing(false);
      setSyncStatus('Falha ao autenticar com Google');
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;

    setIsSyncing(true);
    setSyncStatus('SINCRONIZANDO VETORES RAG...');

    try {
      const profile = await authApiService.loginWithToken(email, token);
      setTimeout(() => {
        setSyncStatus('NEURAL LINK ESTABELECIDO');
        setTimeout(() => {
          setIsSyncing(false);
          onSuccess(profile);
        }, 600);
      }, 1200);
    } catch {
      setIsSyncing(false);
      setSyncStatus('Erro na sincronização neural');
    }
  };

  return (
    <div className="relative w-full min-h-[calc(100vh-4rem)] flex items-center justify-center p-4 md:p-8 overflow-y-auto">
      {/* Background Dot Grid */}
      <div className="fixed inset-0 pointer-events-none opacity-20 bg-[radial-gradient(#ae71ff_1px,transparent_1px)] [background-size:24px_24px]"></div>

      <div className="flex flex-col w-full max-w-[1240px] mx-auto z-10 my-4">
        {/* Top Back bar */}
        <div className="flex items-center justify-between mb-4 px-2">
          <button
            onClick={onBackToTerminal}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] text-xs font-mono text-[#d8b9ff] transition-all hover:scale-102 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            <span>Retornar ao Terminal NIMB_OS</span>
          </button>

          <span className="font-mono text-xs text-[#8B87A8] hidden sm:inline">
            Status: {currentOperator.isAuthenticated ? 'Sessão Ativa' : 'Desconectado'}
          </span>
        </div>

        {/* Main Double Card Container */}
        <div className="relative w-full rounded-2xl bg-[#1B1B22] border border-[rgba(162,89,255,0.25)] shadow-2xl overflow-hidden">
          {/* Ambient Corner Glows */}
          <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#ae71ff]/15 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-[#43e090]/10 rounded-full blur-3xl pointer-events-none"></div>

          <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[680px]">
            {/* LEFT COLUMN: Entity Showcase & Cluster Status */}
            <div className="lg:col-span-6 relative flex flex-col justify-between p-6 md:p-10 bg-[#0E0E15] overflow-hidden border-b lg:border-b-0 lg:border-r border-[#34344E]/60">
              <div className="absolute inset-0 bg-gradient-to-b from-[#d8b9ff]/5 via-transparent to-[#43e090]/5 pointer-events-none"></div>
              <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#d8b9ff] via-[#43e090] to-transparent opacity-75"></div>

              {/* Status Header */}
              <div className="relative z-10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="inline-flex w-3 h-3 rounded-full bg-[#43e090] animate-pulse shadow-[0_0_8px_rgba(67,224,144,0.6)]"></span>
                  <span className="font-mono text-xs text-[#43e090] tracking-widest uppercase">
                    SYS.ONLINE // PORT 8443
                  </span>
                </div>
                <div className="flex items-center gap-2 px-3 py-1 rounded bg-[#1F1F26] font-mono text-xs text-[#cec2d7]">
                  <span className="material-symbols-outlined text-[14px] text-[#d8b9ff]">terminal</span>
                  <span>KERNEL V2.4 // RAG NEURAL LINK</span>
                </div>
              </div>

              {/* Central Character & Branding */}
              <div className="relative z-10 my-6 flex flex-col items-center justify-center text-center">
                <div className="relative w-full max-w-[340px] md:max-w-[380px] aspect-square flex items-center justify-center">
                  <div className="absolute -inset-4 rounded-2xl bg-gradient-to-tr from-[#ae71ff]/20 to-[#43e090]/20 blur-xl opacity-60"></div>
                  <img
                    alt="Entidade Nimb - Senhor do Caos e Entropia Digital"
                    referrerPolicy="no-referrer"
                    className="relative z-10 w-full h-full object-contain filter drop-shadow-[0_0_24px_rgba(174,113,255,0.35)] transition-transform duration-700 hover:scale-105"
                    src="https://lh3.googleusercontent.com/aida/AEtjO1VeZBenvo1EbBBHx1FCf1uEDMzj2vDFk-dsyMejBABVcZInwDymH5IfVK8E8VvWse6MmYhip_RjWrR87W_Dka3BxvnTXRfnIoXv16FZpPwGRfcY9UfwbIlgMTKEwOwZp2-4qtEM7vqAzLb_sexGZbohFocz7yo6EyFICdgMUXbnIJV4Nagsih0WZUnDeK60xI03S0lSg68d1qhmwWt2u5kUvh_fWVobKAkLJxhS1zN4-3p5ruEYIDpebZgRiHQC6ShBUloIEoz58w"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                  <div className="absolute -bottom-2 left-6 right-6 h-1 bg-gradient-to-r from-[#d8b9ff] via-transparent to-[#43e090] opacity-80"></div>
                </div>

                <div className="w-full mt-4">
                  <div className="inline-block px-3 py-1 mb-2 rounded bg-[#1F1F26] font-mono text-[10px] text-[#66feaa] tracking-widest uppercase border border-[#43e090]/30">
                    // INSTABILIDADE CONTROLADA
                  </div>
                  <h1 className="text-2xl md:text-3xl font-bold text-[#F0EEF8] tracking-tight uppercase">
                    NIMB_OS <span className="text-[#d8b9ff]">//</span> TERMINAL DO CAOS
                  </h1>
                  <p className="text-xs md:text-sm text-[#cec2d7] mt-2 max-w-md mx-auto leading-relaxed">
                    Interface quântica de indexação RAG, orquestração de agentes e síntese neural multivariada sob entropia dirigida.
                  </p>
                </div>
              </div>

              {/* Entropy Bar footer */}
              <div className="relative z-10 pt-4 border-t border-[#34344E]/40">
                <div className="flex items-center justify-between text-[#cec2d7] font-mono text-xs mb-2">
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-[#43e090]">memory</span>
                    FLUXO ENTROPICO DO CLUSTER
                  </span>
                  <span className="text-[#43e090] font-bold">78% ENTROPIA CRÍTICA</span>
                </div>
                <div className="w-full h-1.5 bg-[#1F1F26] rounded-full overflow-hidden flex">
                  <div className="h-full bg-gradient-to-r from-[#d8b9ff] to-[#43e090] w-[78%] rounded-full shadow-[0_0_10px_rgba(67,224,144,0.5)]"></div>
                </div>
                <div className="flex justify-between items-center mt-2.5 text-[#cec2d7] font-mono text-[11px] opacity-80">
                  <span>HASH: 0x9B...C41F</span>
                  <span>NODES ATIVOS: 14/16</span>
                </div>
              </div>
            </div>

            {/* RIGHT COLUMN: Operator Authentication Form */}
            <div className="lg:col-span-6 flex flex-col justify-between p-6 md:p-10 bg-[#1F1F26]">
              <div className="w-full max-w-md mx-auto">
                <div className="flex items-center justify-between mb-6 pb-3 border-b border-[#34344E]/50">
                  <div>
                    <span className="font-mono text-[11px] text-[#d8b9ff] tracking-widest uppercase block mb-1">
                      PROTOCOLO DE ACESSO SINÁPTICO
                    </span>
                    <h2 className="text-xl md:text-2xl font-bold text-[#F0EEF8] tracking-tight">
                      AUTENTICAÇÃO DE OPERADOR
                    </h2>
                  </div>
                  <div className="h-10 w-10 rounded-xl bg-[#2A2931] border border-[#43e090]/40 flex items-center justify-center text-[#43e090] shadow-[0_0_12px_rgba(67,224,144,0.2)]">
                    <span className="material-symbols-outlined text-[22px]">fingerprint</span>
                  </div>
                </div>

                <div className="flex flex-col gap-4">
                  {/* Google Workspace API OAuth Button */}
                  <button
                    type="button"
                    disabled={isSyncing}
                    onClick={handleGoogleAuth}
                    className={`group relative w-full flex items-center justify-center gap-3 px-5 py-3.5 rounded-xl bg-[#34343C] hover:bg-[#393840] text-[#E4E1EC] font-medium transition-all duration-300 shadow-[0_0_20px_rgba(174,113,255,0.15)] hover:shadow-[0_0_25px_rgba(67,224,144,0.3)] hover:-translate-y-0.5 active:translate-y-0 border border-transparent hover:border-[#43e090]/50 cursor-pointer ${
                      googleOauthSuccess ? 'ring-2 ring-[#43e090]' : ''
                    }`}
                  >
                    <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-[#d8b9ff]/10 via-[#43e090]/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"></div>
                    <svg className="w-5 h-5 flex-shrink-0" viewBox="0 0 24 24">
                      <path
                        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                        fill="#4285F4"
                      />
                      <path
                        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                        fill="#34A853"
                      />
                      <path
                        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                        fill="#FBBC05"
                      />
                      <path
                        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                        fill="#EA4335"
                      />
                    </svg>
                    <span className="font-medium tracking-tight text-sm">
                      Conectar com Google Workspace API
                    </span>
                    <span className="material-symbols-outlined text-[18px] text-[#43e090] ml-auto group-hover:translate-x-1 transition-transform">
                      bolt
                    </span>
                  </button>

                  {/* Google OAuth Feedback Bar */}
                  {googleOauthSuccess && (
                    <div className="px-4 py-2.5 rounded-lg bg-[#2A2931] border border-[#43e090]/40 font-mono text-xs text-[#43e090] flex items-center gap-2 animate-fadeIn">
                      <span className="material-symbols-outlined text-[16px] text-[#43e090]">
                        verified_user
                      </span>
                      <span>OAUTH 2.0 VERIFICADO // ESCOPO RAG ATIVO</span>
                    </div>
                  )}

                  {/* Separator */}
                  <div className="relative flex items-center justify-center my-2">
                    <div className="w-full h-px bg-[#34343C]"></div>
                    <span className="absolute px-3 bg-[#1F1F26] font-mono text-[10px] text-[#cec2d7] uppercase tracking-wider">
                      OU ACESSO MANUAL / CREDENCIAIS SINÁPTICAS
                    </span>
                  </div>

                  {/* Form */}
                  <form onSubmit={handleManualSubmit} className="space-y-4">
                    <div>
                      <label
                        className="font-mono text-xs text-[#cec2d7] uppercase tracking-wider mb-1.5 flex items-center justify-between"
                        htmlFor="op-email"
                      >
                        <span>EMAIL DE OPERADOR // IDENT</span>
                        <span className="text-[#d8b9ff] text-[10px]">OBRIGATÓRIO</span>
                      </label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-[#8B87A8] text-[18px]">
                          alternate_email
                        </span>
                        <input
                          id="op-email"
                          type="email"
                          required
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          placeholder="operador@cluster-nimb.network"
                          className="w-full bg-[#1A1A2E] text-[#E4E1EC] placeholder:text-[#4b4454] font-mono text-xs pl-11 pr-4 py-3 rounded-lg border border-[#34344E] focus:outline-none focus:border-[#43e090] focus:bg-[#2A2931] transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label
                        className="font-mono text-xs text-[#cec2d7] uppercase tracking-wider mb-1.5 flex items-center justify-between"
                        htmlFor="op-token"
                      >
                        <span>TOKEN DE ACESSO // CHAVE DE API</span>
                        <button
                          type="button"
                          onClick={() =>
                            setToken(
                              '0x' +
                                Array.from({ length: 16 }, () =>
                                  Math.floor(Math.random() * 16).toString(16)
                                )
                                  .join('')
                                  .toUpperCase()
                            )
                          }
                          className="text-[#43e090] hover:underline text-[10px] uppercase font-mono cursor-pointer"
                        >
                          Regenerar Token
                        </button>
                      </label>
                      <div className="relative">
                        <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-[#8B87A8] text-[18px]">
                          vpn_key
                        </span>
                        <input
                          id="op-token"
                          type={showPassword ? 'text' : 'password'}
                          required
                          value={token}
                          onChange={(e) => setToken(e.target.value)}
                          placeholder="••••••••••••••••••••••••••••••••"
                          className="w-full bg-[#1A1A2E] text-[#E4E1EC] placeholder:text-[#4b4454] font-mono text-xs pl-11 pr-11 py-3 rounded-lg border border-[#34344E] focus:outline-none focus:border-[#43e090] focus:bg-[#2A2931] transition-all"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8B87A8] hover:text-[#E4E1EC] focus:outline-none cursor-pointer"
                        >
                          <span className="material-symbols-outlined text-[18px]">
                            {showPassword ? 'visibility_off' : 'visibility'}
                          </span>
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-1 text-xs">
                      <label className="flex items-center gap-2 cursor-pointer select-none">
                        <input
                          type="checkbox"
                          checked={keepActive}
                          onChange={(e) => setKeepActive(e.target.checked)}
                          className="w-4 h-4 rounded bg-[#1A1A2E] accent-[#43e090] cursor-pointer"
                        />
                        <span className="text-[#cec2d7] hover:text-[#E4E1EC] transition-colors">
                          Manter Sessão Ativa no Nexus
                        </span>
                      </label>
                      <button
                        type="button"
                        onClick={() => alert('Chave enviada para o canal neural de emergência.')}
                        className="font-mono text-xs text-[#d8b9ff] hover:underline cursor-pointer"
                      >
                        Recuperar Chave?
                      </button>
                    </div>

                    {/* Sincronizar Button */}
                    <button
                      type="submit"
                      disabled={isSyncing}
                      className="relative w-full mt-4 py-3.5 px-6 rounded-xl font-bold text-sm text-[#0D0D14] bg-gradient-to-r from-[#ae71ff] via-[#d8b9ff] to-[#43e090] shadow-[0_0_20px_rgba(174,113,255,0.4)] hover:shadow-[0_0_30px_rgba(67,224,144,0.5)] hover:scale-[1.01] active:scale-[0.99] transition-all duration-200 flex items-center justify-center gap-2 overflow-hidden cursor-pointer"
                    >
                      <span className="tracking-wide uppercase">
                        {syncStatus || 'Sincronizar Neural Link'}
                      </span>
                      <span
                        className={`material-symbols-outlined text-[20px] ${
                          isSyncing ? 'animate-spin' : ''
                        }`}
                      >
                        {isSyncing ? 'sync' : 'bolt'}
                      </span>
                    </button>
                  </form>
                </div>
              </div>

              {/* Security Bottom Note */}
              <div className="w-full max-w-md mx-auto pt-6 mt-4 border-t border-[#34344E]/40">
                <div className="flex flex-wrap items-center justify-between gap-2 text-[#cec2d7] font-mono text-[11px]">
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-[#43e090]">lock</span>
                    PROTOCOLO SEGURO AES-256
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="material-symbols-outlined text-[14px] text-[#d8b9ff]">hub</span>
                    CLUSTER DE CAOS: 78% ENTROPIA
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
