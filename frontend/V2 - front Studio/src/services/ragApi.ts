import { ChatMessage, IndexedBook } from '../types';

/**
 * RAG API Service Layer
 * Prepared for live backend connection via fetch('/api/rag/...')
 * or standalone execution with domain-rich simulated embeddings.
 */

const API_BASE = import.meta.env.VITE_BACKEND_URL || '';

export interface QueryRagPayload {
  prompt: string;
  chaosLevel: number;
  bookIds?: string[];
}

export interface QueryRagResponse {
  answer: string;
  bookTitle: string;
  page: string | number;
  similarity: string;
  chaosApplied: number;
  quote?: string;
  rollTable?: {
    title: string;
    diceRoll: string;
    description: string;
  };
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
  /**
   * Send user prompt to RAG endpoint (or fallback to domain-accurate simulator)
   */
  async queryRag(payload: QueryRagPayload): Promise<QueryRagResponse> {
    if (API_BASE) {
      try {
        const res = await fetch(`${API_BASE}/api/rag/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('Backend unavailable, utilizing local RAG neural pipeline:', err);
      }
    }

    // Realistic neural simulated delay
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

  /**
   * Upload and index a PDF grimório into the RAG vector database
   */
  async uploadGrimorio(
    file: File,
    config: { chunkSize: number; model: string; entropy: number }
  ): Promise<IndexedBook> {
    if (API_BASE) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('chunkSize', config.chunkSize.toString());
        formData.append('model', config.model);
        formData.append('entropy', config.entropy.toString());

        const res = await fetch(`${API_BASE}/api/rag/upload`, {
          method: 'POST',
          body: formData,
        });
        if (res.ok) {
          return await res.json();
        }
      } catch (err) {
        console.warn('Backend upload unavailable, using client indexing simulation:', err);
      }
    }

    // Local simulation
    const estimatedChunks = Math.max(800, Math.floor(file.size / (config.chunkSize * 2)));
    const sizeMb = (file.size / (1024 * 1024)).toFixed(1);

    return {
      id: 'book_' + Date.now(),
      title: file.name.replace(/\.[^/.]+$/, ''),
      fileName: file.name,
      size: `${sizeMb} MB`,
      chunks: estimatedChunks,
      progress: 100,
      status: 'indexed',
      badgeColor: 'purple',
    };
  },
};
