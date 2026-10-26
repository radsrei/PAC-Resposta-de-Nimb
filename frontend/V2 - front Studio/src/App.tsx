import { useCallback, useEffect, useState } from 'react';
import Terminal from './Terminal';
import { LoginScreen } from './components/auth/LoginScreen';
import { AuthConfig, AuthUser } from './types';
import { authApiService } from './services/authApi';
import { UNAUTHORIZED_EVENT } from './services/http';

/**
 * Portão de autenticação: só renderiza o terminal com uma sessão válida.
 * Sem sessão mostra a tela de login (somente Google).
 */
export default function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [checking, setChecking] = useState(true);
  const [backendError, setBackendError] = useState<string | null>(null);

  const checkSession = useCallback(async () => {
    setChecking(true);
    setBackendError(null);
    try {
      setConfig(await authApiService.getConfig());
      try {
        setUser(await authApiService.me());
      } catch {
        setUser(null); // sem sessão válida
      }
    } catch (err) {
      setBackendError((err as Error).message);
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    checkSession();
  }, [checkSession]);

  // Sessão expirada em qualquer chamada da API -> volta ao login
  useEffect(() => {
    const handler = () => setUser(null);
    window.addEventListener(UNAUTHORIZED_EVENT, handler);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, handler);
  }, []);

  const handleLogout = async () => {
    try {
      await authApiService.logout();
    } finally {
      setUser(null);
    }
  };

  if (checking) {
    return (
      <div className="h-screen w-screen flex items-center justify-center cyber-bg font-mono text-sm text-[#d8b9ff] gap-2">
        <span className="material-symbols-outlined animate-spin">sync</span>
        Verificando sessão...
      </div>
    );
  }

  if (backendError) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center cyber-bg gap-4 p-6 text-center">
        <span className="material-symbols-outlined text-4xl text-red-400">cloud_off</span>
        <p className="text-sm text-[#F0EEF8] max-w-md">{backendError}</p>
        <button
          onClick={checkSession}
          className="px-4 py-2 rounded-lg bg-[#181827] border border-[#A259FF]/40 text-[#d8b9ff] text-xs font-mono cursor-pointer"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="h-screen w-screen cyber-bg overflow-y-auto">
        <LoginScreen config={config} onAuthenticated={setUser} />
      </div>
    );
  }

  return (
    <Terminal
      key={user.email}
      user={user}
      onUserChange={setUser}
      onLogout={handleLogout}
      onSignedOut={() => setUser(null)}
    />
  );
}
