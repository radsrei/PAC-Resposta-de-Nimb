import React, { useEffect, useState } from 'react';
import {
  LlmConnection,
  LlmConnectionInput,
  LlmProvider,
  LlmProviderId,
  LlmTestResult,
} from '../../types';
import { llmApiService } from '../../services/llmApi';

interface LlmConnectionModalProps {
  /** Só administradores gerenciam conexões (elas guardam API keys). */
  isAdmin: boolean;
  isOpen: boolean;
  onClose: () => void;
  /** Chamado sempre que a lista muda, com a conexão ativa atual (ou null). */
  onChanged: (active: LlmConnection | null) => void;
}

interface FormState {
  name: string;
  provider: LlmProviderId;
  model: string;
  baseUrl: string;
  apiKey: string;
  temperature: string;
  maxTokens: string;
}

const EMPTY_FORM: FormState = {
  name: '',
  provider: 'openai',
  model: '',
  baseUrl: '',
  apiKey: '',
  temperature: '',
  maxTokens: '',
};

const inputClass =
  'w-full bg-[#13131F] border border-[#34344E] focus:border-[#39D98A] rounded-lg px-3 py-2 text-sm text-[#F0EEF8] placeholder-[#8B87A8]/50 outline-none transition-colors font-mono';

const labelClass = 'font-mono text-[10px] uppercase tracking-wider text-[#8B87A8] mb-1 block';

export const LlmConnectionModal: React.FC<LlmConnectionModalProps> = ({
  isAdmin,
  isOpen,
  onClose,
  onChanged,
}) => {
  const [providers, setProviders] = useState<LlmProvider[]>([]);
  const [connections, setConnections] = useState<LlmConnection[]>([]);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [testResults, setTestResults] = useState<Record<string, LlmTestResult>>({});
  const [error, setError] = useState<string | null>(null);

  const [activeInfo, setActiveInfo] = useState<LlmConnection | null>(null);

  const refresh = async () => {
    const list = await llmApiService.listConnections();
    setConnections(list);
    onChanged(list.find((c) => c.isActive) || null);
    return list;
  };

  useEffect(() => {
    if (!isOpen) return;
    setError(null);
    if (!isAdmin) {
      llmApiService
        .getActive()
        .then((active) => {
          setActiveInfo(active);
          onChanged(active);
        })
        .catch((err) => setError(err.message));
      return;
    }
    Promise.all([llmApiService.listProviders(), refresh()])
      .then(([provs]) => setProviders(provs))
      .catch((err) => setError(err.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, isAdmin]);

  if (!isOpen) return null;

  if (!isAdmin) {
    return (
      <div
        className="fixed inset-0 bg-[#0A0A10]/80 backdrop-blur-md z-50 flex items-center justify-center p-4 animate-fadeIn"
        onClick={(e) => e.target === e.currentTarget && onClose()}
      >
        <div className="w-full max-w-md bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2 className="font-bold text-[#F0EEF8] flex items-center gap-2">
              <span className="material-symbols-outlined text-[#d8b9ff]">hub</span> Conexão LLM
            </h2>
            <button onClick={onClose} className="text-[#8B87A8] hover:text-[#F0EEF8] cursor-pointer" title="Fechar">
              <span className="material-symbols-outlined">close</span>
            </button>
          </div>
          {error && <p className="text-xs font-mono text-red-300">{error}</p>}
          {activeInfo ? (
            <p className="text-sm text-[#F0EEF8]">
              LLM ativa: <strong>{activeInfo.name}</strong>
              <span className="block font-mono text-xs text-[#8B87A8]">{activeInfo.model}</span>
            </p>
          ) : (
            <p className="text-sm text-amber-300">Nenhuma LLM conectada no momento.</p>
          )}
          <p className="text-xs text-[#8B87A8]">
            Somente administradores podem cadastrar ou alterar conexões com LLMs.
          </p>
        </div>
      </div>
    );
  }

  const provider = providers.find((p) => p.id === form.provider);
  const editing = connections.find((c) => c.id === editingId) || null;

  const setField = (field: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const resetForm = () => {
    setForm(EMPTY_FORM);
    setEditingId(null);
  };

  const startEdit = (conn: LlmConnection) => {
    setEditingId(conn.id);
    setError(null);
    setForm({
      name: conn.name,
      provider: conn.provider,
      model: conn.model,
      baseUrl: conn.baseUrl || '',
      apiKey: '',
      temperature: conn.temperature?.toString() ?? '',
      maxTokens: conn.maxTokens?.toString() ?? '',
    });
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSaving(true);

    const payload: LlmConnectionInput = {
      name: form.name.trim() || provider?.label || form.provider,
      provider: form.provider,
      model: form.model.trim() || null,
      baseUrl: form.baseUrl.trim() || null,
      temperature: form.temperature === '' ? null : Number(form.temperature),
      maxTokens: form.maxTokens === '' ? null : Number(form.maxTokens),
    };
    // Na edição, API key em branco mantém a chave já salva
    if (form.apiKey.trim() || !editingId) {
      payload.apiKey = form.apiKey.trim() || null;
    }

    try {
      if (editingId) {
        await llmApiService.update(editingId, payload);
      } else {
        await llmApiService.create({ ...payload, isActive: true });
      }
      await refresh();
      resetForm();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const runAction = async (id: string, action: () => Promise<unknown>) => {
    setBusyId(id);
    setError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  };

  const handleTest = (conn: LlmConnection) =>
    runAction(conn.id, async () => {
      const result = await llmApiService.test(conn.id);
      setTestResults((prev) => ({ ...prev, [conn.id]: result }));
    });

  const handleDelete = (conn: LlmConnection) => {
    if (!window.confirm(`Remover a conexão "${conn.name}"?`)) return;
    if (editingId === conn.id) resetForm();
    runAction(conn.id, () => llmApiService.remove(conn.id));
  };

  const providerLabel = (id: string) => providers.find((p) => p.id === id)?.label || id;

  return (
    <div
      className="fixed inset-0 bg-[#0A0A10]/80 backdrop-blur-md z-50 flex items-center justify-center p-4 md:p-6 overflow-y-auto animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isSaving) onClose();
      }}
    >
      <div className="relative w-full max-w-5xl bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl shadow-2xl flex flex-col gap-5 p-6 md:p-8 my-auto max-h-[90vh] overflow-y-auto custom-scrollbar">
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#A259FF]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Header */}
        <div className="flex items-center justify-between relative z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1F1F26] border border-[#A259FF]/40 flex items-center justify-center">
              <span className="material-symbols-outlined text-[#d8b9ff] text-2xl">hub</span>
            </div>
            <div>
              <h2 className="text-lg md:text-xl font-bold text-[#F0EEF8] tracking-tight uppercase">
                Conexão LLM // Núcleo de Linguagem
              </h2>
              <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                CONFIGURE A API DO MODELO QUE RESPONDE ÀS CONSULTAS
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] transition-colors cursor-pointer"
            title="Fechar"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>

        {error && (
          <div className="relative z-10 px-4 py-2.5 rounded-lg bg-red-500/10 border border-red-500/40 text-red-300 text-xs font-mono flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px]">error</span>
            <span>{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative z-10">
          {/* Lista de conexões */}
          <div className="flex flex-col gap-3">
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold">
              Conexões cadastradas ({connections.length})
            </span>

            {connections.length === 0 && (
              <div className="p-4 rounded-xl border border-dashed border-[#34344E] text-xs text-[#8B87A8] font-mono text-center">
                Nenhuma conexão cadastrada. Preencha o formulário ao lado para conectar uma LLM.
              </div>
            )}

            {connections.map((conn) => {
              const test = testResults[conn.id];
              const busy = busyId === conn.id;
              return (
                <div
                  key={conn.id}
                  className={`p-3 rounded-xl border bg-[#181827] transition-all ${
                    conn.isActive ? 'border-[#39D98A]/60' : 'border-[#34344E]'
                  } ${editingId === conn.id ? 'ring-1 ring-[#A259FF]' : ''}`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-[#F0EEF8] truncate">
                          {conn.name}
                        </span>
                        {conn.isActive && (
                          <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-[#39D98A]/15 text-[#39D98A] border border-[#39D98A]/30">
                            Ativa
                          </span>
                        )}
                      </div>
                      <div className="font-mono text-[10px] text-[#8B87A8] truncate">
                        {providerLabel(conn.provider)} • {conn.model}
                        {conn.apiKeyPreview ? ` • key ${conn.apiKeyPreview}` : ''}
                      </div>
                    </div>
                    {busy && (
                      <span className="material-symbols-outlined text-[18px] text-[#d8b9ff] animate-spin">
                        refresh
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-1.5 mt-2.5 font-mono text-[10px]">
                    {!conn.isActive && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => runAction(conn.id, () => llmApiService.activate(conn.id))}
                        className="px-2 py-1 rounded border border-[#39D98A]/40 text-[#39D98A] hover:bg-[#39D98A]/10 cursor-pointer disabled:opacity-40"
                      >
                        Ativar
                      </button>
                    )}
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleTest(conn)}
                      className="px-2 py-1 rounded border border-[#A259FF]/40 text-[#d8b9ff] hover:bg-[#A259FF]/10 cursor-pointer disabled:opacity-40"
                    >
                      Testar
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => startEdit(conn)}
                      className="px-2 py-1 rounded border border-[#34344E] text-[#8B87A8] hover:text-[#F0EEF8] cursor-pointer disabled:opacity-40"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => handleDelete(conn)}
                      className="px-2 py-1 rounded border border-red-500/30 text-red-300 hover:bg-red-500/10 cursor-pointer disabled:opacity-40"
                    >
                      Excluir
                    </button>
                  </div>

                  {test && (
                    <div
                      className={`mt-2 px-2.5 py-1.5 rounded text-[10px] font-mono ${
                        test.ok
                          ? 'bg-[#39D98A]/10 text-[#39D98A] border border-[#39D98A]/25'
                          : 'bg-red-500/10 text-red-300 border border-red-500/30'
                      }`}
                    >
                      {test.ok
                        ? `OK em ${test.latencyMs} ms — "${test.sample}"`
                        : `Falha: ${test.error}`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Formulário */}
          <form
            onSubmit={handleSave}
            className="flex flex-col gap-3 p-4 rounded-xl bg-[#181827]/70 border border-[#34344E]"
          >
            <span className="font-mono text-[11px] uppercase tracking-wider text-[#d8b9ff] font-semibold">
              {editing ? `Editando: ${editing.name}` : 'Nova conexão'}
            </span>

            <div>
              <label className={labelClass}>Provedor</label>
              <select
                value={form.provider}
                onChange={(e) => setField('provider', e.target.value)}
                className={inputClass}
              >
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Nome da conexão</label>
              <input
                value={form.name}
                onChange={(e) => setField('name', e.target.value)}
                placeholder={provider?.label || 'Minha LLM'}
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>Modelo</label>
              <input
                value={form.model}
                onChange={(e) => setField('model', e.target.value)}
                placeholder={provider?.defaultModel || 'nome-do-modelo'}
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>
                API key {provider?.requiresApiKey ? '(obrigatória)' : '(opcional)'}
              </label>
              <input
                type="password"
                autoComplete="off"
                value={form.apiKey}
                onChange={(e) => setField('apiKey', e.target.value)}
                placeholder={
                  editing?.hasApiKey
                    ? `Em branco mantém a atual (${editing.apiKeyPreview})`
                    : provider?.requiresApiKey
                      ? 'Cole aqui a chave da API'
                      : 'Não necessária para este provedor'
                }
                className={inputClass}
              />
            </div>

            <div>
              <label className={labelClass}>Base URL (opcional)</label>
              <input
                value={form.baseUrl}
                onChange={(e) => setField('baseUrl', e.target.value)}
                placeholder={provider?.defaultBaseUrl || 'https://...'}
                className={inputClass}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className={labelClass}>Temperatura (opcional)</label>
                <input
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={form.temperature}
                  onChange={(e) => setField('temperature', e.target.value)}
                  placeholder="padrão"
                  className={inputClass}
                />
              </div>
              <div>
                <label className={labelClass}>Máx. tokens (opcional)</label>
                <input
                  type="number"
                  min={1}
                  value={form.maxTokens}
                  onChange={(e) => setField('maxTokens', e.target.value)}
                  placeholder="padrão"
                  className={inputClass}
                />
              </div>
            </div>
            {form.provider === 'anthropic' && (
              <p className="font-mono text-[10px] text-[#8B87A8]">
                Os modelos Claude 5.x não aceitam temperatura — deixe em branco.
              </p>
            )}

            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                disabled={isSaving}
                className="flex-1 py-2.5 rounded-xl bg-gradient-to-r from-[#A259FF] to-[#39D98A] text-black text-sm font-bold hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-40"
              >
                {isSaving ? 'Salvando...' : editing ? 'Salvar alterações' : 'Conectar LLM'}
              </button>
              {editing && (
                <button
                  type="button"
                  onClick={resetForm}
                  className="px-4 py-2.5 rounded-xl border border-[#34344E] text-[#8B87A8] hover:text-[#F0EEF8] text-sm cursor-pointer"
                >
                  Cancelar
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
