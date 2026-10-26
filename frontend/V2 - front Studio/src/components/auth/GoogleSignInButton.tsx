import React, { useEffect, useRef, useState } from 'react';

/**
 * Botão oficial "Fazer login com o Google" (Google Identity Services).
 *
 * O Google devolve um ID token (JWT) em `onCredential`; esse token é enviado ao
 * backend, que valida assinatura, emissor, expiração e o Client ID antes de
 * criar a sessão. O front nunca confia no conteúdo do token por conta própria.
 */

const GSI_SRC = 'https://accounts.google.com/gsi/client';

declare global {
  interface Window {
    google?: any;
  }
}

let gsiPromise: Promise<void> | null = null;

function loadGsi(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  if (!gsiPromise) {
    gsiPromise = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = GSI_SRC;
      script.async = true;
      script.defer = true;
      script.onload = () => resolve();
      script.onerror = () => {
        gsiPromise = null;
        reject(new Error('Não foi possível carregar o login do Google.'));
      };
      document.head.appendChild(script);
    });
  }
  return gsiPromise;
}

interface GoogleSignInButtonProps {
  clientId: string | null;
  onCredential: (credential: string) => void;
  disabled?: boolean;
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  clientId,
  onCredential,
  disabled,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onCredential);
  const [loadError, setLoadError] = useState<string | null>(null);

  callbackRef.current = onCredential;

  useEffect(() => {
    if (!clientId) return;
    let cancelled = false;

    loadGsi()
      .then(() => {
        if (cancelled || !containerRef.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response: { credential?: string }) => {
            if (response.credential) callbackRef.current(response.credential);
          },
          ux_mode: 'popup',
          cancel_on_tap_outside: true,
        });
        containerRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(containerRef.current, {
          type: 'standard',
          theme: 'filled_black',
          size: 'large',
          text: 'signin_with',
          shape: 'pill',
          locale: 'pt-BR',
          width: Math.min(containerRef.current.offsetWidth || 360, 400),
        });
      })
      .catch((err: Error) => !cancelled && setLoadError(err.message));

    return () => {
      cancelled = true;
    };
  }, [clientId]);

  if (!clientId) {
    return (
      <div
        className="w-full flex items-center justify-center gap-3 px-5 py-3 rounded-xl bg-[#2A2931] text-[#8B87A8] text-sm border border-[#34344E] cursor-not-allowed"
        title="Defina GOOGLE_CLIENT_ID no backend/.env para habilitar"
      >
        <span className="material-symbols-outlined text-[18px]">block</span>
        Login com Google não configurado
      </div>
    );
  }

  return (
    <div className={disabled ? 'pointer-events-none opacity-50' : ''}>
      <div ref={containerRef} className="w-full flex justify-center min-h-[44px]" />
      {loadError && (
        <p className="mt-2 text-center font-mono text-[10px] text-red-300">{loadError}</p>
      )}
    </div>
  );
};
