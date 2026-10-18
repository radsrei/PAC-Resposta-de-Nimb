import { AuthConfig, AuthUser } from '../types';
import { http } from './http';

/**
 * Autenticação (backend: /api/auth). O único método de login é o Google.
 *
 * A sessão fica num cookie HttpOnly definido pelo backend: o front nunca lê
 * nem armazena o token (nada em localStorage), o que protege contra roubo
 * de sessão via XSS.
 */
export const authApiService = {
  getConfig: () => http.get<AuthConfig>('/api/auth/config'),

  me: () => http.get<AuthUser>('/api/auth/me'),

  loginWithGoogle: (credential: string, remember: boolean) =>
    http.post<AuthUser>('/api/auth/google', { credential, remember }),

  logout: () => http.post<{ message: string }>('/api/auth/logout'),

  logoutOtherSessions: () => http.post<{ message: string }>('/api/auth/logout-all'),

  updateProfile: (name: string) => http.patch<AuthUser>('/api/auth/me', { name }),

  deleteAccount: () => http.delete<{ message: string }>('/api/auth/me'),
};

/**
 * Administração de usuários (backend: /api/admin/users) — somente admins.
 */
export const adminApiService = {
  listUsers: () => http.get<AuthUser[]>('/api/admin/users'),

  updateUser: (email: string, data: { role?: 'user' | 'admin'; isActive?: boolean }) =>
    http.patch<AuthUser>(`/api/admin/users/${encodeURIComponent(email)}`, data),

  deleteUser: (email: string) =>
    http.delete<{ message: string }>(`/api/admin/users/${encodeURIComponent(email)}`),
};
