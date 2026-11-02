import React, { useEffect, useState } from 'react';
import { Allowlist, AuthUser } from '../../types';
import { adminApiService, authApiService } from '../../services/authApi';
import { AcknowledgmentsModal } from '../modals/AcknowledgmentsModal';

interface AccountScreenProps {
  user: AuthUser;
  onUserChange: (user: AuthUser) => void;
  onLogout: () => void;
  onAccountDeleted: () => void;
  onBack: () => void;
}

const inputClass =
  'w-full bg-[#13131F] border border-[#34344E] focus:border-[#39D98A] rounded-lg px-3 py-2 text-sm text-[#F0EEF8] placeholder-[#8B87A8]/50 outline-none transition-colors font-mono';
const labelClass = 'font-mono text-[10px] uppercase tracking-wider text-[#8B87A8] mb-1 block';
const cardClass = 'p-5 rounded-2xl bg-[#1B1B22] border border-[rgba(162,89,255,0.25)] flex flex-col gap-3';

type Feedback = { type: 'ok' | 'error'; text: string } | null;

const FeedbackLine: React.FC<{ feedback: Feedback }> = ({ feedback }) =>
  feedback ? (
    <p className={`text-xs font-mono ${feedback.type === 'ok' ? 'text-[#39D98A]' : 'text-red-300'}`}>
      {feedback.text}
    </p>
  ) : null;

const formatDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—';

// ---------------------------------------------------------------------------
// Painel de administração de usuários
// ---------------------------------------------------------------------------
const AdminUsersPanel: React.FC<{ currentEmail: string }> = ({ currentEmail }) => {
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [busyEmail, setBusyEmail] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<Feedback>(null);

  const load = () =>
    adminApiService
      .listUsers()
      .then(setUsers)
      .catch((err) => setFeedback({ type: 'error', text: err.message }));

  useEffect(() => {
    load();
  }, []);

  const run = async (email: string, action: () => Promise<string | void>) => {
    setBusyEmail(email);
    setFeedback(null);
    try {
      const message = await action();
      if (message) setFeedback({ type: 'ok', text: message });
      await load();
    } catch (err) {
      setFeedback({ type: 'error', text: (err as Error).message });
    } finally {
      setBusyEmail(null);
    }
  };

  return (
    <section className={`${cardClass} lg:col-span-2`}>
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[#d8b9ff]">admin_panel_settings</span>
        <h3 className="font-bold text-[#F0EEF8]">Usuários do sistema</h3>
        <span className="font-mono text-[10px] text-[#8B87A8]">({users.length})</span>
      </div>
      <FeedbackLine feedback={feedback} />

      <div className="overflow-x-auto custom-scrollbar">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left font-mono text-[10px] uppercase text-[#8B87A8] border-b border-[#34344E]">
              <th className="py-2 pr-3">Usuário</th>
              <th className="py-2 pr-3">Acesso</th>
              <th className="py-2 pr-3">Login</th>
              <th className="py-2 pr-3">Último acesso</th>
              <th className="py-2 text-right">Ações</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => {
              const isSelf = u.email === currentEmail;
              const busy = busyEmail === u.email;
              return (
                <tr key={u.email} className="border-b border-[#34344E]/50 align-middle">
                  <td className="py-2.5 pr-3">
                    <div className="text-[#F0EEF8] font-medium">{u.name}</div>
                    <div className="font-mono text-[10px] text-[#8B87A8]">{u.email}</div>
                  </td>
                  <td className="py-2.5 pr-3">
                    <select
                      value={u.role}
                      disabled={busy || isSelf}
                      onChange={(e) =>
                        run(u.email, () =>
                          adminApiService
                            .updateUser(u.email, { role: e.target.value as AuthUser['role'] })
                            .then(() => `Perfil de ${u.email} atualizado.`)
                        )
                      }
                      className="bg-[#13131F] border border-[#34344E] rounded px-2 py-1 font-mono text-[11px] text-[#F0EEF8] disabled:opacity-50"
                    >
                      <option value="user">Usuário</option>
                      <option value="admin">Admin</option>
                    </select>
                    {!u.isActive && (
                      <span className="ml-2 text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-red-500/15 text-red-300 border border-red-500/30">
                        Inativo
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[10px] text-[#8B87A8]">
                    {u.googleLinked ? 'google' : 'pendente (1º login)'}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[10px] text-[#8B87A8]">
                    {formatDate(u.lastLoginAt)}
                  </td>
                  <td className="py-2.5">
                    <div className="flex justify-end gap-1.5 font-mono text-[10px]">
                      {!isSelf && (
                        <>
                          <button
                            disabled={busy}
                            onClick={() =>
                              run(u.email, () =>
                                adminApiService
                                  .updateUser(u.email, { isActive: !u.isActive })
                                  .then(() => `${u.email} ${u.isActive ? 'desativado' : 'reativado'}.`)
                              )
                            }
                            className="px-2 py-1 rounded border border-[#34344E] text-[#8B87A8] hover:text-[#F0EEF8] cursor-pointer disabled:opacity-40"
                          >
                            {u.isActive ? 'Desativar' : 'Reativar'}
                          </button>
                          <button
                            disabled={busy}
                            onClick={() =>
                              window.confirm(`Excluir a conta ${u.email} e todas as conversas dela?`) &&
                              run(u.email, () =>
                                adminApiService.deleteUser(u.email).then(() => `${u.email} excluído.`)
                              )
                            }
                            className="px-2 py-1 rounded border border-red-500/30 text-red-300 hover:bg-red-500/10 cursor-pointer disabled:opacity-40"
                          >
                            Excluir
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

// ---------------------------------------------------------------------------
// Lista de acesso: e-mails que podem entrar (só administradores editam)
// ---------------------------------------------------------------------------
const AllowlistPanel: React.FC = () => {
  const [allowlist, setAllowlist] = useState<Allowlist>({ enabled: true, emails: [] });
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);

  useEffect(() => {
    adminApiService
      .listAllowed()
      .then(setAllowlist)
      .catch((err) => setFeedback({ type: 'error', text: err.message }));
  }, []);

  const run = async (action: () => Promise<string>) => {
    setBusy(true);
    setFeedback(null);
    try {
      setFeedback({ type: 'ok', text: await action() });
    } catch (err) {
      setFeedback({ type: 'error', text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    // Aceita vários e-mails separados por vírgula, ponto e vírgula, espaço ou linha
    const emails = input.split(/[\s,;]+/).filter(Boolean);
    if (emails.length === 0) return;
    run(async () => {
      const before = allowlist.emails.length;
      const updated = await adminApiService.addAllowed(emails);
      setAllowlist(updated);
      setInput('');
      const added = updated.emails.length - before;
      return added === 1 ? '1 e-mail incluído.' : `${added} e-mails incluídos.`;
    });
  };

  const handleRemove = (email: string) => {
    if (!window.confirm(`Remover ${email} da lista? As sessões abertas dele serão encerradas.`)) return;
    run(async () => {
      await adminApiService.removeAllowed(email);
      setAllowlist(await adminApiService.listAllowed());
      return `${email} removido da lista.`;
    });
  };

  return (
    <section className={`${cardClass} lg:col-span-2`}>
      <div className="flex items-center gap-2">
        <span className="material-symbols-outlined text-[#d8b9ff]">how_to_reg</span>
        <h3 className="font-bold text-[#F0EEF8]">E-mails com acesso</h3>
        <span className="font-mono text-[10px] text-[#8B87A8]">({allowlist.emails.length})</span>
      </div>
      <p className="text-xs text-[#8B87A8]">
        Só as contas Google destes e-mails conseguem entrar no sistema. Administradores entram sempre.
        {!allowlist.enabled && (
          <span className="text-amber-300"> A lista está desligada no servidor (ALLOWLIST_ENABLED=false): hoje qualquer conta entra.</span>
        )}
      </p>

      <form onSubmit={handleAdd} className="flex flex-col sm:flex-row gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="email@gmail.com, outro@gmail.com"
          className={inputClass}
        />
        <button
          disabled={busy || !input.trim()}
          className="shrink-0 px-4 py-2 rounded-lg bg-[#39D98A]/15 border border-[#39D98A]/40 text-[#39D98A] text-xs font-semibold cursor-pointer disabled:opacity-40"
        >
          Incluir
        </button>
      </form>
      <FeedbackLine feedback={feedback} />

      {allowlist.emails.length > 0 && (
        <div className="overflow-x-auto custom-scrollbar">
          <table className="w-full text-xs">
            <thead>
              <tr className="text-left font-mono text-[10px] uppercase text-[#8B87A8] border-b border-[#34344E]">
                <th className="py-2 pr-3">E-mail</th>
                <th className="py-2 pr-3">Conta</th>
                <th className="py-2 pr-3">Incluído por</th>
                <th className="py-2 text-right">Ações</th>
              </tr>
            </thead>
            <tbody>
              {allowlist.emails.map((a) => (
                <tr key={a.email} className="border-b border-[#34344E]/50 align-middle">
                  <td className="py-2.5 pr-3 font-mono text-[11px] text-[#F0EEF8]">{a.email}</td>
                  <td className="py-2.5 pr-3 font-mono text-[10px] text-[#8B87A8]">
                    {a.hasAccount ? 'já entrou' : 'aguardando 1º login'}
                  </td>
                  <td className="py-2.5 pr-3 font-mono text-[10px] text-[#8B87A8]">
                    {a.addedBy} • {formatDate(a.createdAt)}
                  </td>
                  <td className="py-2.5">
                    <div className="flex justify-end font-mono text-[10px]">
                      <button
                        disabled={busy}
                        onClick={() => handleRemove(a.email)}
                        className="px-2 py-1 rounded border border-red-500/30 text-red-300 hover:bg-red-500/10 cursor-pointer disabled:opacity-40"
                      >
                        Remover
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
};

// ---------------------------------------------------------------------------
// Minha conta
// ---------------------------------------------------------------------------
export const AccountScreen: React.FC<AccountScreenProps> = ({
  user,
  onUserChange,
  onLogout,
  onAccountDeleted,
  onBack,
}) => {
  const [name, setName] = useState(user.name);
  const [profileFeedback, setProfileFeedback] = useState<Feedback>(null);

  const [sessionFeedback, setSessionFeedback] = useState<Feedback>(null);
  const [deleteFeedback, setDeleteFeedback] = useState<Feedback>(null);
  const [busy, setBusy] = useState(false);
  const [showAcknowledgments, setShowAcknowledgments] = useState(false);

  const run = async (setFeedback: (f: Feedback) => void, action: () => Promise<string>) => {
    setBusy(true);
    setFeedback(null);
    try {
      setFeedback({ type: 'ok', text: await action() });
    } catch (err) {
      setFeedback({ type: 'error', text: (err as Error).message });
    } finally {
      setBusy(false);
    }
  };

  const handleProfile = (e: React.FormEvent) => {
    e.preventDefault();
    run(setProfileFeedback, async () => {
      onUserChange(await authApiService.updateProfile(name));
      return 'Nome atualizado.';
    });
  };

  const handleDelete = (e: React.FormEvent) => {
    e.preventDefault();
    if (!window.confirm('Excluir sua conta e todas as suas conversas? Esta ação não pode ser desfeita.')) return;
    run(setDeleteFeedback, async () => {
      await authApiService.deleteAccount();
      onAccountDeleted();
      return 'Conta excluída.';
    });
  };

  return (
    <div className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-8 select-text">
      <div className="max-w-5xl mx-auto flex flex-col gap-5">
        <div className="flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] text-xs font-mono text-[#d8b9ff] cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">arrow_back</span>
            Voltar ao terminal
          </button>
          <button
            onClick={onLogout}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#181827] hover:bg-red-500/10 border border-red-500/30 text-xs font-mono text-red-300 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[16px]">logout</span>
            Sair
          </button>
        </div>

        <div>
          <h2 className="text-2xl font-bold text-[#F0EEF8]">Minha conta</h2>
          <p className="font-mono text-xs text-[#8B87A8]">
            {user.email} • {user.role === 'admin' ? 'Administrador' : 'Usuário'} • criada em{' '}
            {formatDate(user.createdAt)}
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Perfil */}
          <form onSubmit={handleProfile} className={cardClass}>
            <h3 className="font-bold text-[#F0EEF8] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#39D98A]">badge</span> Perfil
            </h3>
            <div>
              <label className={labelClass}>Nome</label>
              <input value={name} maxLength={80} required onChange={(e) => setName(e.target.value)} className={inputClass} />
            </div>
            <div>
              <label className={labelClass}>E-mail (identificador da conta)</label>
              <input value={user.email} disabled className={`${inputClass} opacity-60`} />
            </div>
            <div className="font-mono text-[10px] text-[#8B87A8]">
              Método de login: Google
            </div>
            <FeedbackLine feedback={profileFeedback} />
            <button disabled={busy || name.trim() === user.name} className="self-start px-4 py-2 rounded-lg bg-[#39D98A]/15 border border-[#39D98A]/40 text-[#39D98A] text-xs font-semibold cursor-pointer disabled:opacity-40">
              Salvar nome
            </button>
          </form>

          {/* Sessões */}
          <section className={cardClass}>
            <h3 className="font-bold text-[#F0EEF8] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#39D98A]">devices</span> Sessões
            </h3>
            <p className="text-xs text-[#8B87A8]">
              Último acesso: {formatDate(user.lastLoginAt)}. Encerre as sessões abertas em outros
              navegadores ou dispositivos.
            </p>
            <FeedbackLine feedback={sessionFeedback} />
            <button
              disabled={busy}
              onClick={() => run(setSessionFeedback, async () => (await authApiService.logoutOtherSessions()).message)}
              className="self-start px-4 py-2 rounded-lg bg-[#181827] border border-[#34344E] text-[#F0EEF8] text-xs font-semibold cursor-pointer disabled:opacity-40"
            >
              Encerrar outras sessões
            </button>
          </section>

          {/* Exclusão */}
          <form onSubmit={handleDelete} className={`${cardClass} border-red-500/30`}>
            <h3 className="font-bold text-red-300 flex items-center gap-2">
              <span className="material-symbols-outlined">warning</span> Excluir conta
            </h3>
            <p className="text-xs text-[#8B87A8]">Remove sua conta e todas as suas conversas.</p>
            <FeedbackLine feedback={deleteFeedback} />
            <button disabled={busy} className="self-start px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-xs font-semibold cursor-pointer disabled:opacity-40">
              Excluir minha conta
            </button>
          </form>

          {/* Agradecimentos */}
          <section className={cardClass}>
            <h3 className="font-bold text-[#F0EEF8] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#39D98A]">favorite</span> Agradecimentos
            </h3>
            <p className="text-xs text-[#8B87A8]">
              Conheça as pessoas que ajudaram a construir o Respostas de Nimb.
            </p>
            <button
              type="button"
              onClick={() => setShowAcknowledgments(true)}
              className="self-start px-4 py-2 rounded-lg bg-[#39D98A]/15 border border-[#39D98A]/40 text-[#39D98A] text-xs font-semibold cursor-pointer"
            >
              Ver agradecimentos
            </button>
          </section>

          {user.role === 'admin' && <AllowlistPanel />}
          {user.role === 'admin' && <AdminUsersPanel currentEmail={user.email} />}
        </div>
      </div>

      <AcknowledgmentsModal
        isOpen={showAcknowledgments}
        onClose={() => setShowAcknowledgments(false)}
      />
    </div>
  );
};
