import { AuthConfig, AuthUser, PasswordResetResult } from '../types';
import { http } from './http';

/**
 * Autenticação (backend: /api/auth).
 *
 * A sessão fica num cookie HttpOnly definido pelo backend: o front nunca lê
 * nem armazena o token (nada em localStorage), o que protege contra roubo
 * de sessão via XSS.
 */
export const authApiService = {
  getConfig: () => http.get<AuthConfig>('/api/auth/config'),

  me: () => http.get<AuthUser>('/api/auth/me'),

  register: (name: string, email: string, password: string) =>
    http.post<AuthUser>('/api/auth/register', { name, email, password }),

  login: (email: string, password: string, remember: boolean) =>
    http.post<AuthUser>('/api/auth/login', { email, password, remember }),

  loginWithGoogle: (credential: string, remember: boolean) =>
    http.post<AuthUser>('/api/auth/google', { credential, remember }),

  logout: () => http.post<{ message: string }>('/api/auth/logout'),

  logoutOtherSessions: () => http.post<{ message: string }>('/api/auth/logout-all'),

  updateProfile: (name: string) => http.patch<AuthUser>('/api/auth/me', { name }),

  changePassword: (currentPassword: string | null, newPassword: string) =>
    http.post<AuthUser>('/api/auth/change-password', { currentPassword, newPassword }),

  forgotPassword: (email: string) =>
    http.post<{ message: string }>('/api/auth/forgot-password', { email }),

  resetPassword: (token: string) =>
    http.post<PasswordResetResult>('/api/auth/reset-password', { token }),

  deleteAccount: (password: string | null) =>
    http.request<{ message: string }>('/api/auth/me', {
      method: 'DELETE',
      body: JSON.stringify({ password }),
    }),
};

/**
 * Administração de usuários (backend: /api/admin/users) — somente admins.
 */
export const adminApiService = {
  listUsers: () => http.get<AuthUser[]>('/api/admin/users'),

  updateUser: (email: string, data: { role?: 'user' | 'admin'; isActive?: boolean }) =>
    http.patch<AuthUser>(`/api/admin/users/${encodeURIComponent(email)}`, data),

  resetPassword: (email: string) =>
    http.post<PasswordResetResult>(`/api/admin/users/${encodeURIComponent(email)}/reset-password`),

  deleteUser: (email: string) =>
    http.delete<{ message: string }>(`/api/admin/users/${encodeURIComponent(email)}`),
};
