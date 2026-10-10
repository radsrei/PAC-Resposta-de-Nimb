import { ChatSession, ChatSessionDetail, SessionMessage } from '../types';
import { http } from './http';

/**
 * Sessões de conversa / "Perguntas Anteriores" (backend: /api/sessions).
 */
export const sessionApiService = {
  list: () => http.get<ChatSession[]>('/api/sessions'),

  get: (id: string) => http.get<ChatSessionDetail>(`/api/sessions/${id}`),

  create: (title?: string) => http.post<ChatSession>('/api/sessions', { title }),

  rename: (id: string, title: string) => http.patch<ChatSession>(`/api/sessions/${id}`, { title }),

  remove: (id: string) => http.delete(`/api/sessions/${id}`),

  removeAll: () => http.delete('/api/sessions'),

  listMessages: (id: string) => http.get<SessionMessage[]>(`/api/sessions/${id}/messages`),
};
