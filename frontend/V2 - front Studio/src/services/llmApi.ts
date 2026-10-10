import { LlmConnection, LlmConnectionInput, LlmProvider, LlmTestResult } from '../types';
import { http } from './http';

/**
 * Configuração das conexões com LLM (backend: /api/llm).
 */
export const llmApiService = {
  listProviders: () => http.get<LlmProvider[]>('/api/llm/providers'),

  listConnections: () => http.get<LlmConnection[]>('/api/llm/connections'),

  getActive: () => http.get<LlmConnection | null>('/api/llm/connections/active'),

  create: (data: LlmConnectionInput) => http.post<LlmConnection>('/api/llm/connections', data),

  update: (id: string, data: Partial<LlmConnectionInput>) =>
    http.put<LlmConnection>(`/api/llm/connections/${id}`, data),

  remove: (id: string) => http.delete(`/api/llm/connections/${id}`),

  activate: (id: string) => http.post<LlmConnection>(`/api/llm/connections/${id}/activate`),

  test: (id: string) => http.post<LlmTestResult>(`/api/llm/connections/${id}/test`),
};
