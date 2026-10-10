/**
 * Cliente HTTP base para o backend FastAPI.
 *
 * Por padrão as chamadas usam caminho relativo (`/api/...`) e o proxy do Vite
 * (vite.config.ts) encaminha para o backend. Para apontar direto para outra
 * URL, defina VITE_BACKEND_URL no `.env.local`.
 */

export const API_BASE = (import.meta.env.VITE_BACKEND_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

function extractDetail(body: unknown): string | null {
  if (!body || typeof body !== 'object') return null;
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') return detail;
  // Erros de validação do FastAPI: [{ loc, msg, ... }]
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const field = Array.isArray(d?.loc) ? d.loc.slice(1).join('.') : '';
        return field ? `${field}: ${d?.msg}` : d?.msg;
      })
      .filter(Boolean)
      .join('; ');
  }
  return null;
}

export async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      'Não foi possível conectar ao backend. Verifique se a API está rodando em http://localhost:8000.',
      0
    );
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }

  if (!res.ok) {
    // Proxy do Vite sem backend no ar responde 500/502/504 sem JSON
    const fallback =
      res.status >= 500 && !body
        ? 'Backend indisponível. Verifique se a API está rodando em http://localhost:8000.'
        : `Erro HTTP ${res.status}`;
    throw new ApiError(extractDetail(body) || fallback, res.status);
  }
  return body as T;
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: data instanceof FormData ? data : JSON.stringify(data ?? {}),
    }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(data) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: <T = void>(path: string) => request<T>(path, { method: 'DELETE' }),
};
