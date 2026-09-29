/**
 * config.js
 * Configuração central de conexão com o Backend do "Respostas de Nimb".
 * Ajuste apenas este arquivo ao trocar de ambiente (local, homologação, produção).
 */

const APP_CONFIG = {
  // URL base da API do backend. Troque para a URL real quando o backend estiver disponível.
  API_BASE_URL: "http://localhost:8000/api",

  // Endpoints esperados no backend (ver contrato descrito no README/tutorial)
  ENDPOINTS: {
    CHAT: "/chat",                 // POST -> envia pergunta, recebe resposta da IA
    CONVERSATIONS: "/conversations", // GET  -> histórico de perguntas anteriores
    USER: "/user/me",              // GET  -> dados do usuário logado
    BOOKS: "/books",               // GET  -> (v2) livros carregados na base RAG
    CHAOS: "/chaos-level"          // GET  -> (v2) nível de "caos" da resposta atual
  },

  // Enquanto o backend não estiver no ar, USE_MOCK=true faz a tela funcionar
  // com respostas simuladas (mesmo comportamento do protótipo original).
  // Assim que o backend estiver pronto, basta trocar para false.
  USE_MOCK: true,

  // Tempo máximo de espera por uma resposta do backend, em milissegundos
  REQUEST_TIMEOUT_MS: 20000
};
