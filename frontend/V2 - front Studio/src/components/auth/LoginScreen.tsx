import React, { useEffect, useState } from 'react';
import { AuthConfig, AuthUser } from '../../types';
import { authApiService } from '../../services/authApi';
import { GoogleSignInButton } from './GoogleSignInButton';

type AuthMode = 'login' | 'register' | 'forgot' | 'reset' | 'change';

interface LoginScreenProps {
  config: AuthConfig | null;
  /** Usuário logado que precisa trocar a senha (senha padrão após reset). */
  pendingUser: AuthUser | null;
  onAuthenticated: (user: AuthUser) => void;
  onLogout: () => void;
}

const inputClass =
  'w-full bg-[#1A1A2E] text-[#E4E1EC] placeholder:text-[#4b4454] font-mono text-xs pl-11 pr-4 py-3 rounded-lg border border-[#34344E] focus:outline-none focus:border-[#43e090] focus:bg-[#2A2931] transition-all';

const Field: React.FC<{
  id: string;
  label: string;
  icon: string;
  children: React.ReactNode;
  hint?: string;
}> = ({ id, label, icon, children, hint }) => (
  <div>
    <label
      htmlFor={id}
      className="font-mono text-xs text-[#cec2d7] uppercase tracking-wider mb-1.5 flex items-center justify-between"
    >
      <span>{label}</span>
      {hint && <span className="text-[#8B87A8] text-[10px] normal-case">{hint}</span>}
    </label>
    <div className="relative">
      <span className="absolute left-3.5 top-1/2 -translate-y-1/2 material-symbols-outlined text-[#8B87A8] text-[18px] pointer-events-none">
        {icon}
      </span>
      {children}
    </div>
  </div>
);

const PasswordInput: React.FC<{
  id: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete: string;
  placeholder?: string;
}> = ({ id, value, onChange, autoComplete, placeholder }) => {
  const [visible, setVisible] = useState(false);
  return (
    <>
      <input
        id={id}
        type={visible ? 'text' : 'password'}
        required
        maxLength={128}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder || '••••••••'}
        className={`${inputClass} pr-11`}
      />
      <button
        type="button"
        onClick={() => setVisible(!visible)}
        className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8B87A8] hover:text-[#E4E1EC] cursor-pointer"
        title={visible ? 'Ocultar senha' : 'Mostrar senha'}
      >
        <span className="material-symbols-outlined text-[18px]">
          {visible ? 'visibility_off' : 'visibility'}
        </span>
      </button>
    </>
  );
};

const TITLES: Record<AuthMode, [string, string]> = {
  login: ['PROTOCOLO DE ACESSO', 'ENTRAR NO NIMB_OS'],
  register: ['NOVO OPERADOR', 'CRIAR CONTA'],
  forgot: ['RECUPERAÇÃO', 'ESQUECI MINHA SENHA'],
  reset: ['RECUPERAÇÃO', 'USAR CÓDIGO DE RECUPERAÇÃO'],
  change: ['SEGURANÇA', 'DEFINA UMA NOVA SENHA'],
};

export const LoginScreen: React.FC<LoginScreenProps> = ({
  config,
  pendingUser,
  onAuthenticated,
  onLogout,
}) => {
  const initialToken = new URLSearchParams(window.location.search).get('reset') || '';
  const [mode, setMode] = useState<AuthMode>(
    pendingUser ? 'change' : initialToken ? 'reset' : 'login'
  );
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [resetToken, setResetToken] = useState(initialToken);
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);

  useEffect(() => {
    if (pendingUser) setMode('change');
  }, [pendingUser]);

  const minLength = config?.passwordMinLength ?? 8;

  const switchMode = (next: AuthMode) => {
    setMode(next);
    setError(null);
    setInfo(null);
    setPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const checkNewPassword = (value: string) => {
    if (value.length < minLength) return `A senha deve ter pelo menos ${minLength} caracteres.`;
    if (!/[A-Za-z]/.test(value) || !/\d/.test(value)) return 'A senha deve conter letras e números.';
    if (value !== confirmPassword) return 'A confirmação da senha não confere.';
    return null;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (mode === 'login') {
      run(async () => onAuthenticated(await authApiService.login(email, password, remember)));
    } else if (mode === 'register') {
      const problem = checkNewPassword(newPassword);
      if (problem) return setError(problem);
      run(async () => onAuthenticated(await authApiService.register(name, email, newPassword)));
    } else if (mode === 'forgot') {
      run(async () => {
        const res = await authApiService.forgotPassword(email);
        setMode('reset');
        setInfo(res.message);
      });
    } else if (mode === 'reset') {
      run(async () => {
        const res = await authApiService.resetPassword(resetToken);
        window.history.replaceState(null, '', window.location.pathname);
        switchMode('login');
        setPassword(res.temporaryPassword);
        setInfo(`${res.message} Senha padrão: ${res.temporaryPassword}`);
      });
    } else if (mode === 'change') {
      const problem = checkNewPassword(newPassword);
      if (problem) return setError(problem);
      run(async () => onAuthenticated(await authApiService.changePassword(password, newPassword)));
    }
  };

  const handleGoogle = (credential: string) =>
    run(async () => onAuthenticated(await authApiService.loginWithGoogle(credential, remember)));

  const [kicker, title] = TITLES[mode];
  const submitLabel: Record<AuthMode, string> = {
    login: 'Entrar',
    register: 'Criar conta',
    forgot: 'Gerar código de recuperação',
    reset: 'Redefinir senha',
    change: 'Salvar nova senha',
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
                Senhas com hash scrypt
              </span>
            </div>
          </div>

          {/* Coluna direita: formulário */}
          <div className="lg:col-span-7 flex flex-col justify-center p-6 md:p-10 bg-[#1F1F26]">
            <div className="w-full max-w-md mx-auto">
              <div className="flex items-center justify-between mb-6 pb-3 border-b border-[#34344E]/50">
                <div>
                  <span className="font-mono text-[11px] text-[#d8b9ff] tracking-widest uppercase block mb-1">
                    {kicker}
                  </span>
                  <h2 className="text-xl md:text-2xl font-bold text-[#F0EEF8] tracking-tight">{title}</h2>
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
              {info && (
                <div className="mb-4 px-4 py-2.5 rounded-lg bg-[#43e090]/10 border border-[#43e090]/40 text-[#43e090] text-xs flex items-start gap-2">
                  <span className="material-symbols-outlined text-[16px]">info</span>
                  <span>{info}</span>
                </div>
              )}

              {mode === 'change' && (
                <p className="mb-4 text-xs text-[#cec2d7] leading-relaxed">
                  Olá, <strong className="text-[#F0EEF8]">{pendingUser?.name}</strong>. Sua senha foi
                  redefinida para a senha padrão. Por segurança, defina uma senha pessoal para continuar.
                </p>
              )}
              {mode === 'reset' && (
                <p className="mb-4 text-xs text-[#cec2d7] leading-relaxed">
                  Informe o código de recuperação. A senha será redefinida para a senha padrão do
                  sistema e você precisará trocá-la no próximo acesso.
                </p>
              )}

              {(mode === 'login' || mode === 'register') && (
                <>
                  <GoogleSignInButton
                    clientId={config?.googleClientId ?? null}
                    onCredential={handleGoogle}
                    disabled={busy}
                  />
                  <div className="relative flex items-center justify-center my-5">
                    <div className="w-full h-px bg-[#34343C]"></div>
                    <span className="absolute px-3 bg-[#1F1F26] font-mono text-[10px] text-[#cec2d7] uppercase tracking-wider">
                      ou com e-mail e senha
                    </span>
                  </div>
                </>
              )}

              <form onSubmit={handleSubmit} className="space-y-4">
                {mode === 'register' && (
                  <Field id="auth-name" label="Nome" icon="badge">
                    <input
                      id="auth-name"
                      required
                      maxLength={80}
                      autoComplete="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Seu nome"
                      className={inputClass}
                    />
                  </Field>
                )}

                {(mode === 'login' || mode === 'register' || mode === 'forgot') && (
                  <Field id="auth-email" label="E-mail" icon="alternate_email">
                    <input
                      id="auth-email"
                      type="email"
                      required
                      maxLength={254}
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="voce@exemplo.com"
                      className={inputClass}
                    />
                  </Field>
                )}

                {mode === 'reset' && (
                  <Field id="auth-token" label="Código de recuperação" icon="key">
                    <input
                      id="auth-token"
                      required
                      maxLength={200}
                      autoComplete="one-time-code"
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value.trim())}
                      placeholder="Cole aqui o código recebido"
                      className={inputClass}
                    />
                  </Field>
                )}

                {(mode === 'login' || mode === 'change') && (
                  <Field
                    id="auth-password"
                    label={mode === 'change' ? 'Senha atual (padrão)' : 'Senha'}
                    icon="vpn_key"
                  >
                    <PasswordInput
                      id="auth-password"
                      value={password}
                      onChange={setPassword}
                      autoComplete="current-password"
                    />
                  </Field>
                )}

                {(mode === 'register' || mode === 'change') && (
                  <>
                    <Field
                      id="auth-new-password"
                      label={mode === 'change' ? 'Nova senha' : 'Senha'}
                      icon="lock"
                      hint={`mín. ${minLength}, letras e números`}
                    >
                      <PasswordInput
                        id="auth-new-password"
                        value={newPassword}
                        onChange={setNewPassword}
                        autoComplete="new-password"
                      />
                    </Field>
                    <Field id="auth-confirm" label="Confirmar senha" icon="lock_reset">
                      <PasswordInput
                        id="auth-confirm"
                        value={confirmPassword}
                        onChange={setConfirmPassword}
                        autoComplete="new-password"
                      />
                    </Field>
                  </>
                )}

                {mode === 'login' && (
                  <div className="flex items-center justify-between pt-1 text-xs">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={remember}
                        onChange={(e) => setRemember(e.target.checked)}
                        className="w-4 h-4 rounded bg-[#1A1A2E] accent-[#43e090] cursor-pointer"
                      />
                      <span className="text-[#cec2d7]">Manter conectado</span>
                    </label>
                    <button
                      type="button"
                      onClick={() => switchMode('forgot')}
                      className="font-mono text-xs text-[#d8b9ff] hover:underline cursor-pointer"
                    >
                      Esqueci minha senha
                    </button>
                  </div>
                )}

                <button
                  type="submit"
                  disabled={busy}
                  className="w-full mt-2 py-3.5 px-6 rounded-xl font-bold text-sm text-[#0D0D14] bg-gradient-to-r from-[#ae71ff] via-[#d8b9ff] to-[#43e090] shadow-[0_0_20px_rgba(174,113,255,0.4)] hover:scale-[1.01] active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60"
                >
                  <span className="uppercase tracking-wide">{busy ? 'Aguarde...' : submitLabel[mode]}</span>
                  <span className={`material-symbols-outlined text-[20px] ${busy ? 'animate-spin' : ''}`}>
                    {busy ? 'sync' : 'arrow_forward'}
                  </span>
                </button>
              </form>

              {/* Navegação entre modos */}
              <div className="mt-6 flex flex-col items-center gap-2 text-xs text-[#cec2d7]">
                {mode === 'login' && config?.registrationEnabled !== false && (
                  <span>
                    Não tem conta?{' '}
                    <button type="button" onClick={() => switchMode('register')} className="text-[#43e090] hover:underline cursor-pointer">
                      Criar conta
                    </button>
                  </span>
                )}
                {mode === 'login' && (
                  <button type="button" onClick={() => switchMode('reset')} className="text-[#8B87A8] hover:text-[#d8b9ff] cursor-pointer">
                    Já tenho um código de recuperação
                  </button>
                )}
                {(mode === 'register' || mode === 'forgot' || mode === 'reset') && (
                  <button type="button" onClick={() => switchMode('login')} className="text-[#d8b9ff] hover:underline cursor-pointer">
                    Voltar para o login
                  </button>
                )}
                {mode === 'change' && (
                  <button type="button" onClick={onLogout} className="text-[#8B87A8] hover:text-red-300 cursor-pointer">
                    Sair
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
