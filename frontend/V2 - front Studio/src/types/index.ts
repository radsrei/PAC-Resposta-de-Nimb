export type SenderType = 'user' | 'nimb';

export interface RagMetadata {
  bookTitle: string;
  page?: number | string | null;
  similarity: string;
  chaosApplied: number;
  harnessRounds?: number;
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

/** Livro do catálogo (backend: GET /api/rag/books). */
export interface CatalogBook {
  id: string;
  title: string;
  unlocked: boolean;
  unlockedAt: string | null;
  vectorReady: boolean;
  chunks: number;
  pageCount?: number | null;
}

/** Resultado da validação de um PDF (backend: POST /api/rag/upload). */
export interface BookValidationResult {
  accepted: boolean;
  message: string;
  score: number;
  checks: { name: string; label: string; passed: boolean }[];
  book: CatalogBook | null;
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

export type ScreenView = 'terminal' | 'account';

// ---------------------------------------------------------------------------
// Autenticação (backend: /api/auth e /api/admin)
// ---------------------------------------------------------------------------
export interface AuthUser {
  email: string;
  name: string;
  role: 'user' | 'admin';
  isActive: boolean;
  googleLinked: boolean;
  createdAt: string;
  lastLoginAt: string | null;
}

/** E-mail da lista de acesso (backend: /api/admin/allowed-emails). */
export interface AllowedEmail {
  email: string;
  addedBy: string;
  createdAt: string;
  hasAccount: boolean;
}

export interface Allowlist {
  enabled: boolean;
  emails: AllowedEmail[];
}

export interface AuthConfig {
  googleClientId: string | null;
}

// ---------------------------------------------------------------------------
// Conexões LLM (backend: /api/llm)
// ---------------------------------------------------------------------------
/** Único provedor de LLM do projeto. */
export type LlmProviderId = 'deepseek';

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
  /** string: conexões antigas de provedores desativados ainda podem aparecer. */
  provider: string;
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

// ---------------------------------------------------------------------------
// Sorteio de tesouro (backend: /api/tesouro)
// ---------------------------------------------------------------------------
export type TreasureType = 'Nenhum' | 'Padrão' | 'Metade' | 'Dobro';

export interface TreasureCreature {
  name: string;
  nd: string;
  treasure: TreasureType;
  treasureNote: string;
  page: string;
}

export interface TreasureReward {
  kind: string;
  name: string;
  details: string[];
  value?: number | null;
  options: TreasureReward[];
  sources: string[];
}

export interface TreasureColumnRoll {
  column: 'dinheiro' | 'itens';
  roll: number;
  result: string;
  rewards: TreasureReward[];
  source: string;
  /** d% informado pelo jogador (false = rolado pelo sistema) */
  manual: boolean;
}

export interface TreasureRollResult {
  id: string;
  createdAt: string;
  bookId: string;
  nd: string;
  treasureType: TreasureType;
  creature: TreasureCreature | null;
  rolls: TreasureColumnRoll[];
  totalValue: number;
  notes: string[];
}

/** d% da Tabela 8-1 de uma unidade da criatura (null = rolagem automática). */
export interface TreasureTableRolls {
  money: (number | null)[];
  items: (number | null)[];
}

export interface TreasureGroupItem {
  creature: string;
  quantity: number;
  rolls?: TreasureTableRolls[];
}

export interface TreasureGroupResult {
  groups: {
    creature: TreasureCreature;
    quantity: number;
    totalValue: number;
    results: TreasureRollResult[];
  }[];
  totalValue: number;
}
