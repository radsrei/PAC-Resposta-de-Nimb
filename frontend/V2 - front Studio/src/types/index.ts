export type SenderType = 'user' | 'nimb';

export interface RagMetadata {
  bookTitle: string;
  page?: number | string;
  similarity: string;
  chaosApplied: number;
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
