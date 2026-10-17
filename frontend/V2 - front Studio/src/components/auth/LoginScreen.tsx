import React, { useState } from 'react';
import { AuthConfig, AuthUser } from '../../types';
import { authApiService } from '../../services/authApi';
import { GoogleSignInButton } from './GoogleSignInButton';

interface LoginScreenProps {
  config: AuthConfig | null;
  onAuthenticated: (user: AuthUser) => void;
}

/** Tela de acesso: o único método de login é o Google. */
export const LoginScreen: React.FC<LoginScreenProps> = ({ config, onAuthenticated }) => {
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGoogle = async (credential: string) => {
    setBusy(true);
    setError(null);
    try {
      onAuthenticated(await authApiService.loginWithGoogle(credential, remember));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative w-full min-h-screen flex items-center justify-center p-4 md:p-8 overflow-y-auto select-text">
      <div className="fixed inset-0 pointer-events-none opacity-20 bg-[radial-gradient(#ae71ff_1px,transparent_1px)] [background-size:24px_24px]"></div>

      <div className="relative w-full max-w-[1100px] mx-auto z-10 my-4 rounded-2xl bg-[#1B1B22] border border-[rgba(162,89,255,0.25)] shadow-2xl overflow-hidden">
        <div className="absolute -top-32 -left-32 w-96 h-96 bg-[#ae71ff]/15 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-[#43e090]/10 rounded-full blur-3xl pointer-events-none"></div>

        <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[620px]">
          {/* Coluna esquerda: identidade visual */}
          <div className="hidden lg:flex lg:col-span-5 relative flex-col justify-between p-10 bg-[#0E0E15] border-r border-[#34344E]/60">
            <div className="absolute top-0 left-0 w-full h-[2px] bg-gradient-to-r from-[#d8b9ff] via-[#43e090] to-transparent opacity-75"></div>
            <div className="flex items-center gap-3 relative z-10">
              <span className="inline-flex w-3 h-3 rounded-full bg-[#43e090] animate-pulse"></span>
              <span className="font-mono text-xs text-[#43e090] tracking-widest uppercase">
                NIMB_OS // ACESSO SEGURO
              </span>
            </div>

            <div className="relative z-10 flex flex-col items-center text-center">
              <div className="relative w-full max-w-[300px] aspect-square flex items-center justify-center">
                <div className="absolute -inset-4 rounded-2xl bg-gradient-to-tr from-[#ae71ff]/20 to-[#43e090]/20 blur-xl opacity-60"></div>
                <img
                  alt="Nimb"
                  referrerPolicy="no-referrer"
                  className="relative z-10 w-full h-full object-contain drop-shadow-[0_0_24px_rgba(174,113,255,0.35)]"
                  src="https://lh3.googleusercontent.com/aida/AEtjO1VeZBenvo1EbBBHx1FCf1uEDMzj2vDFk-dsyMejBABVcZInwDymH5IfVK8E8VvWse6MmYhip_RjWrR87W_Dka3BxvnTXRfnIoXv16FZpPwGRfcY9UfwbIlgMTKEwOwZp2-4qtEM7vqAzLb_sexGZbohFocz7yo6EyFICdgMUXbnIJV4Nagsih0WZUnDeK60xI03S0lSg68d1qhmwWt2u5kUvh_fWVobKAkLJxhS1zN4-3p5ruEYIDpebZgRiHQC6ShBUloIEoz58w"
                  onError={(e) => ((e.target as HTMLElement).style.display = 'none')}
                />
              </div>
              <h1 className="mt-6 text-2xl font-bold text-[#F0EEF8] tracking-tight uppercase">
                NIMB_OS <span className="text-[#d8b9ff]">//</span> TERMINAL DO CAOS
              </h1>
              <p className="text-sm text-[#cec2d7] mt-2 max-w-sm leading-relaxed">
                Consulte regras, magias e monstros de Tormenta20 com a ajuda do deus do caos.
              </p>
            </div>

            <div className="relative z-10 pt-4 border-t border-[#34344E]/40 flex flex-wrap gap-x-4 gap-y-1 font-mono text-[11px] text-[#cec2d7]">
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-[#43e090]">lock</span>
                Sessão em cookie HttpOnly
              </span>
              <span className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-[#d8b9ff]">shield</span>
                Login exclusivo via Google
              </span>
            </div>
          </div>

          {/* Coluna direita: acesso */}
          <div className="lg:col-span-7 flex flex-col justify-center p-6 md:p-10 bg-[#1F1F26]">
            <div className="w-full max-w-md mx-auto">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-[#34344E]/50">
                <div>
                  <span className="font-mono text-[11px] text-[#d8b9ff] tracking-widest uppercase block mb-1">
                    PROTOCOLO DE ACESSO
                  </span>
                  <h2 className="text-xl md:text-2xl font-bold text-[#F0EEF8] tracking-tight">ENTRAR NO NIMB_OS</h2>
                </div>
                <div className="h-10 w-10 rounded-xl bg-[#2A2931] border border-[#43e090]/40 flex items-center justify-center text-[#43e090]">
                  <span className="material-symbols-outlined text-[22px]">fingerprint</span>
                </div>
              </div>

              {error && (
                <div role="alert" className="mb-4 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-xs flex items-start gap-2">
                  <span className="material-symbols-outlined text-[16px]">error</span>
                  <span>{error}</span>
                </div>
              )}

              <p className="mb-5 text-xs text-[#cec2d7] leading-relaxed">
                Use sua conta Google para entrar. No primeiro acesso, sua conta no Nimb é criada
                automaticamente.
              </p>

              <GoogleSignInButton
                clientId={config?.googleClientId ?? null}
                onCredential={handleGoogle}
                disabled={busy}
              />

              <label className="mt-5 flex items-center justify-center gap-2 text-xs cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="w-4 h-4 rounded bg-[#1A1A2E] accent-[#43e090] cursor-pointer"
                />
                <span className="text-[#cec2d7]">Manter conectado</span>
              </label>

              {busy && (
                <p className="mt-4 flex items-center justify-center gap-2 font-mono text-[11px] text-[#d8b9ff]">
                  <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
                  Validando acesso...
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
