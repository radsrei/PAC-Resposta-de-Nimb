/**
 * api.js
 * Camada de comunicação com o Backend. Toda chamada de rede da tela passa por aqui.
 * app.js nunca deve chamar fetch() diretamente — sempre usar o objeto NimbAPI.
 */

const NimbAPI = (() => {

  // Respostas simuladas, usadas apenas quando APP_CONFIG.USE_MOCK === true
  const MOCK_RESPONSES = [
    "Olá! Estou aqui para ajudar. Pode me contar mais detalhes sobre o que você precisa? Vou fazer o meu melhor para oferecer uma resposta completa e precisa.",
    "Ótima pergunta! Com base nas informações fornecidas, existem diversas abordagens para esse problema. A mais eficiente costuma ser começar com uma análise detalhada do contexto.",
    "Entendido! Vou processar sua solicitação. Parece que você está buscando uma solução prática e escalável — excelente combinação para projetos modernos.",
    "Interessante! Isso me leva a pensar em algumas possibilidades. Primeiro, é importante considerar o escopo do que foi pedido e quais recursos estão disponíveis.",
    "Claro, posso ajudar com isso! O ponto central da questão gira em torno da eficiência e da clareza. Recomendo estruturar o problema em etapas menores."
  ];
  let mockIndex = 0;

  /**
   * Faz um fetch com timeout e tratamento de erro padronizado.
   */
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), APP_CONFIG.REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(`${APP_CONFIG.API_BASE_URL}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        signal: controller.signal,
        ...options
      });

      if (!response.ok) {
        throw new Error(`Erro HTTP ${response.status} ao chamar ${path}`);
      }
      return await response.json();
    } finally {
      clearTimeout(timeout);
    }
  }

  /**
   * Envia a mensagem do usuário e retorna a resposta da IA.
   * Contrato esperado do backend:
   *   POST /chat
   *   body: { message: string, conversation_id: string | null }
   *   resposta: { reply: string, conversation_id: string, chaos_level?: number }
   */
  async function sendMessage(message, conversationId = null) {
    if (APP_CONFIG.USE_MOCK) {
      await new Promise(r => setTimeout(r, 1200 + Math.random() * 800));
      const reply = MOCK_RESPONSES[mockIndex % MOCK_RESPONSES.length];
      mockIndex++;
      return { reply, conversation_id: conversationId || "mock-conversation", chaos_level: null };
    }

    return request(APP_CONFIG.ENDPOINTS.CHAT, {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId })
    });
  }

  /**
   * Busca o histórico de conversas do usuário para a sidebar.
   * Contrato esperado do backend:
   *   GET /conversations
   *   resposta: { recent: [{id, title}], previous: [{id, title}] }
   */
  async function getConversations() {
    if (APP_CONFIG.USE_MOCK) {
      return {
        recent: [
          { id: "1", title: "Nova conversa" },
          { id: "2", title: "Análise de dados" },
          { id: "3", title: "Resumo de texto" }
        ],
        previous: [
          { id: "4", title: "Brainstorm ideias" },
          { id: "5", title: "FAQ do produto" }
        ]
      };
    }
    return request(APP_CONFIG.ENDPOINTS.CONVERSATIONS, { method: "GET" });
  }

  /**
   * Busca os dados do usuário logado para exibir na sidebar.
   * Contrato esperado do backend:
   *   GET /user/me
   *   resposta: { name: string, role?: string }
   */
  async function getUser() {
    if (APP_CONFIG.USE_MOCK) {
      return { name: "Usuário Convidado", role: "Sessão local" };
    }
    return request(APP_CONFIG.ENDPOINTS.USER, { method: "GET" });
  }

  /**
   * (v2) Busca os livros carregados na base RAG.
   * Contrato esperado do backend:
   *   GET /books
   *   resposta: { books: [{id, title}] }
   */
  async function getBooks() {
    if (APP_CONFIG.USE_MOCK) {
      return { books: [] }; // v2 ainda não implementada
    }
    return request(APP_CONFIG.ENDPOINTS.BOOKS, { method: "GET" });
  }

  return { sendMessage, getConversations, getUser, getBooks };
})();
