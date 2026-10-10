export type SenderType = 'user' | 'nimb';

export interface RagMetadata {
  bookTitle: string;
  page?: number | string | null;
  similarity: string;
  chaosApplied: number;
  // Dados da LLM que gerou a resposta
  provider?: string;
  model?: string;
  connectionName?: string;
  latencyMs?: number;
}

export interface RollTableCard {
  title: string;
  diceRoll: string;
  description: string;
}

export interface ChatMessage {
  id: string;
  sender: SenderType;
  text: string;
  timestamp: string;
  syntaxTag?: string;
  ragMetadata?: RagMetadata;
  quote?: string;
  rollTable?: RollTableCard;
  isError?: boolean;
}

export interface IndexedBook {
  id: string;
  title: string;
  fileName: string;
  size: string;
  chunks: number;
  progress: number;
  status: 'indexed' | 'indexing' | 'queued';
  badgeColor?: 'green' | 'purple' | 'amber';
}

export interface HistoryItem {
  id: string;
  title: string;
  timestampDesc: string;
  refCount: number;
  conversation?: ChatMessage[];
}

export interface OperatorProfile {
  name: string;
  title: string;
  email: string;
  level: string;
  isAuthenticated: boolean;
  provider?: 'google' | 'manual';
  avatarUrl?: string;
}

export type ScreenView = 'terminal' | 'login';

// ---------------------------------------------------------------------------
// Conexões LLM (backend: /api/llm)
// ---------------------------------------------------------------------------
export type LlmProviderId =
  | 'openai'
  | 'anthropic'
  | 'gemini'
  | 'deepseek'
  | 'ollama'
  | 'openai_compatible';

export interface LlmProvider {
  id: LlmProviderId;
  label: string;
  defaultModel: string;
  defaultBaseUrl: string;
  requiresApiKey: boolean;
}

export interface LlmConnection {
  id: string;
  name: string;
  provider: LlmProviderId;
  model: string;
  baseUrl: string | null;
  temperature: number | null;
  maxTokens: number | null;
  isActive: boolean;
  hasApiKey: boolean;
  apiKeyPreview: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface LlmConnectionInput {
  name: string;
  provider: LlmProviderId;
  model?: string | null;
  baseUrl?: string | null;
  apiKey?: string | null;
  temperature?: number | null;
  maxTokens?: number | null;
  isActive?: boolean;
}

export interface LlmTestResult {
  ok: boolean;
  provider: string;
  model: string;
  latencyMs?: number | null;
  sample?: string | null;
  error?: string | null;
}

// ---------------------------------------------------------------------------
// Sessões de conversa (backend: /api/sessions)
// ---------------------------------------------------------------------------
export interface ChatSession {
  id: string;
  title: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface SessionMessage {
  id: string;
  sessionId: string;
  role: 'user' | 'assistant';
  content: string;
  metadata?: Record<string, unknown> | null;
  createdAt: string;
}

export interface ChatSessionDetail extends ChatSession {
  messages: SessionMessage[];
}
