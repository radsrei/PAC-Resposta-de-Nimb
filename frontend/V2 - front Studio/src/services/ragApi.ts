import { BookValidationResult, CatalogBook, IndexedBook } from '../types';
import { http } from './http';

/**
 * RAG API Service Layer
 * Envia as perguntas para o backend (POST /api/rag/query), que repassa para a
 * LLM ativa. Com VITE_USE_MOCK=true o app roda sozinho com respostas simuladas.
 */

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

export interface ChaosRoll {
  rollToken: string;
  hallucinated: boolean;
  chaosLevel: number;
  chaosLabel: string;
}

export interface QueryRagPayload {
  prompt: string;
  chaosLevel: number;
  /** Regra Nimb ligada: exige o rollToken de rollChaos. Desligada: o backend sorteia após a busca. */
  useChaosRule: boolean;
  rollToken?: string | null;
  bookIds?: string[];
  sessionId?: string | null;
  connectionId?: string | null;
}

export interface RagSource {
  bookId: string;
  bookTitle: string;
  title: string;
  path: string;
  kind: string;
  page: string;
  similarity: number;
}

export interface QueryRagResponse {
  answer: string;
  bookTitle: string;
  page?: string | number | null;
  similarity: string;
  chaosApplied: number;
  chaosLabel?: string;
  harnessRounds?: number;
  hallucinated?: boolean;
  quote?: string | null;
  rollTable?: {
    title: string;
    diceRoll: string;
    description: string;
  } | null;
  sources?: RagSource[];
  // Dados da execução na LLM (backend real)
  sessionId?: string;
  messageId?: string;
  provider?: string;
  model?: string;
  connectionName?: string;
  latencyMs?: number;
}

const KNOWLEDGE_RESPONSES = [
  {
    bookTitle: 'Grimório do Caos.pdf',
    page: 77,
    similarity: '94.2%',
    text: 'O status do Kernel Nimb permanece em estabilidade caótica (98.4% de sincronização com o banco vetorial). Consultando o Grimório do Caos e os registros de Tormenta20, quando você conjura uma magia sob a égide do Caos Primordial:',
    quote: 'O Caos não é a ausência de ordem, mas a sobreposição de infinitas ordens em choque contínuo.',
    rollTable: {
      title: 'EFEITO DE RETORNO // TABELA DE ROLO ALEATÓRIO',
      diceRoll: 'd20: Resultado 18',
      description: '“O conjurador distorce os limites da física planar. O alvo sofre dano de essência aleatória e deve rolar Fortitude ou trocar de lugar no espaço com o objeto sólido mais próximo em até 9m.”',
    },
  },
  {
    bookTitle: 'Tormenta20 - Livro Básico.pdf',
    page: 243,
    similarity: '96.8%',
    text: 'De acordo com as diretrizes do capítulo de Magia e Poderes Concedidos a devotos de Nimb, o devoto pode gastar 1 PM para substituir qualquer rolagem de teste por 1d20 com resultado imprevisível. Se o número for par, soma +5; se ímpar, sofre uma transmutação caótica menor.',
    quote: 'A sorte é uma deusa caprichosa, mas Nimb é o próprio dado que rola sobre a mesa do destino.',
    rollTable: {
      title: 'PODER CONCEDIDO // SORTE DOS LOUCOS',
      diceRoll: 'd6: Resultado 5',
      description: '“Você recebe camuflagem ilusória por 1 rodada enquanto risadas ecoam do éter planar.”',
    },
  },
  {
    bookTitle: 'Manual dos Monstros.pdf',
    page: 112,
    similarity: '91.5%',
    text: 'As entidades e aberrações vinculadas à Loucura de Nimb possuem resistência ampliada contra dano psíquico e transmutação. Qualquer tentativa de leitura mental contra tais criaturas exige um teste de Vontade contra CD 22 para não sofrer confusão mental.',
    quote: 'Não tente decifrar a mente da quimera do abismo; ela já recalculou sua existência dez vezes antes de você piscar.',
    rollTable: {
      title: 'REAÇÃO INSTINTIVA // TABELA ANORMAL',
      diceRoll: 'd10: Resultado 7',
      description: '“A criatura se divide temporariamente em duas sombras que desferem ataques de flanco.”',
    },
  },
  {
    bookTitle: 'Ameaças de Arton.pdf',
    page: 319,
    similarity: '93.1%',
    text: 'No coração das tempestades rubras e áreas de alta entropia cósmica, conjurar magias arcanas de 3º círculo ou superior aciona flutuações no tecido da realidade.',
    quote: 'Quando as leis da física se calam, apenas a intuição sobrevive.',
    rollTable: {
      title: 'DISRUPÇÃO PLANAR // TABELA DE RETORNO',
      diceRoll: 'd20: Resultado 12',
      description: '“Uma chuva de moedas antigas cai num raio de 6m, obscurecendo a visão e concedendo camuflagem leve.”',
    },
  },
];

let queryCounter = 0;

export const ragApiService = {
  /** Rola o dado do caos antes da pergunta: diz se Nimb vai alucinar nesta resposta. */
  async rollChaos(prompt: string, chaosLevel: number): Promise<ChaosRoll> {
    if (!USE_MOCK) {
      return http.post<ChaosRoll>('/api/rag/roll', { prompt, chaosLevel });
    }
    // Mesma regra do backend (app/services/chaos.py): (A x primo + B / C) % 42, parte decimal <= limite
    const limits = [0.15, 0.5, 0.5, 0.75];
    const primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97];
    const prime = primes[Math.floor(Math.random() * primes.length)];
    const now = new Date();
    const words = prompt.trim().split(/\s+/).length * prime;
    const dateSum =
      now.getDate() + now.getMonth() + 1 + now.getFullYear() +
      now.getHours() + now.getMinutes() + now.getSeconds();
    const result = (words + dateSum / (chaosLevel + 1)) % 42;
    return {
      rollToken: 'mock',
      hallucinated: result - Math.floor(result) <= limits[chaosLevel],
      chaosLevel,
      chaosLabel: '',
    };
  },

  /**
   * Envia a pergunta ao backend. Erros (backend fora do ar, sem conexão LLM,
   * falha no provedor) são propagados como ApiError para a tela exibir.
   */
  async queryRag(payload: QueryRagPayload): Promise<QueryRagResponse> {
    if (!USE_MOCK) {
      return http.post<QueryRagResponse>('/api/rag/query', payload);
    }

    // Modo simulado (VITE_USE_MOCK=true)
    await new Promise((r) => setTimeout(r, 900 + Math.random() * 400));

    const selected = KNOWLEDGE_RESPONSES[queryCounter % KNOWLEDGE_RESPONSES.length];
    queryCounter++;

    return {
      answer: selected.text,
      bookTitle: selected.bookTitle,
      page: selected.page,
      similarity: selected.similarity,
      chaosApplied: payload.chaosLevel,
      quote: selected.quote,
      rollTable: selected.rollTable,
    };
  },

  /** Livros do catálogo, com os que o usuário já liberou. */
  async listBooks(): Promise<CatalogBook[]> {
    if (USE_MOCK) return [];
    return http.get<CatalogBook[]>('/api/rag/books');
  },

  /**
   * Envia o PDF para validação. Se ele corresponder a um livro permitido, o
   * backend libera o banco vetorial desse livro para o usuário. O arquivo é
   * descartado depois da análise.
   */
  async validateBook(file: File): Promise<BookValidationResult> {
    if (USE_MOCK) {
      await new Promise((r) => setTimeout(r, 800));
      return {
        accepted: false,
        message: 'Modo simulado: a validação de livros precisa do backend.',
        score: 0,
        checks: [],
        book: null,
      };
    }
    const formData = new FormData();
    formData.append('file', file);
    return http.post<BookValidationResult>('/api/rag/upload', formData);
  },
};

/** Livro liberado -> formato usado pela barra lateral e pelo modal. */
export function toIndexedBook(book: CatalogBook): IndexedBook {
  return {
    id: book.id,
    title: book.title,
    fileName: book.title,
    size: book.pageCount ? `${book.pageCount} páginas` : '',
    chunks: book.chunks,
    progress: book.vectorReady ? 100 : 0,
    status: book.vectorReady ? 'indexed' : 'queued',
    badgeColor: book.vectorReady ? 'green' : 'amber',
  };
}
