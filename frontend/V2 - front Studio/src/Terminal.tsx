import { useCallback, useEffect, useState } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ChatArea } from './components/chat/ChatArea';
import { AccountScreen } from './components/auth/AccountScreen';
import { PdfUploadModal } from './components/modals/PdfUploadModal';
import { LlmConnectionModal } from './components/modals/LlmConnectionModal';
import {
  AuthUser,
  ChatMessage,
  ChatSession,
  HistoryItem,
  IndexedBook,
  LlmConnection,
  OperatorProfile,
  ScreenView,
  SessionMessage,
} from './types';
import { ragApiService } from './services/ragApi';
import { llmApiService } from './services/llmApi';
import { sessionApiService } from './services/sessionApi';
import { ApiError } from './services/http';

const INITIAL_BOOKS: IndexedBook[] = [
  {
    id: 'b1',
    title: 'Tormenta20 - Livro Básico',
    fileName: 'Tormenta20 - Livro Básico.pdf',
    size: '48.2 MB',
    chunks: 4120,
    progress: 100,
    status: 'indexed',
    badgeColor: 'green',
  },
  {
    id: 'b2',
    title: 'Grimório do Caos',
    fileName: 'Grimório do Caos.pdf',
    size: '14.8 MB',
    chunks: 1840,
    progress: 100,
    status: 'indexed',
    badgeColor: 'purple',
  },
  {
    id: 'b3',
    title: 'Manual dos Monstros',
    fileName: 'Manual dos Monstros.pdf',
    size: '36.1 MB',
    chunks: 3200,
    progress: 100,
    status: 'indexed',
    badgeColor: 'green',
  },
];

const formatTime = (date: Date) =>
  date.toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

const getNow = () => formatTime(new Date());

const welcomeMessage = (): ChatMessage => ({
  id: 'msg_welcome_' + Date.now(),
  sender: 'nimb',
  text: 'Saudações, mortal ou viajante planar. O dado foi rolado e o grimório aberto. O que você deseja extrair do tecido da realidade hoje?',
  timestamp: getNow(),
  syntaxTag: '#sintaxe-01',
});

// "Hoje, 14:32" | "Ontem, 21:10" | "18 de fev."
const describeDate = (iso: string) => {
  const date = new Date(iso);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);
  const hour = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  if (date.toDateString() === today.toDateString()) return `Hoje, ${hour}`;
  if (date.toDateString() === yesterday.toDateString()) return `Ontem, ${hour}`;
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' });
};

const sessionToHistory = (session: ChatSession): HistoryItem => ({
  id: session.id,
  title: session.title,
  timestampDesc: describeDate(session.updatedAt),
  refCount: session.messageCount,
});

const toChatMessage = (msg: SessionMessage): ChatMessage => {
  const meta = (msg.metadata || {}) as Record<string, any>;
  return {
    id: msg.id,
    sender: msg.role === 'user' ? 'user' : 'nimb',
    text: msg.content,
    timestamp: formatTime(new Date(msg.createdAt)),
    ragMetadata:
      msg.role === 'assistant'
        ? {
            bookTitle: '',
            similarity: '-',
            chaosApplied: meta.chaosApplied ?? 0,
            provider: meta.provider,
            model: meta.model,
            connectionName: meta.connectionName,
            latencyMs: meta.latencyMs,
          }
        : undefined,
  };
};

// Perfil exibido no Header/Sidebar a partir do usuário autenticado
const toOperator = (user: AuthUser): OperatorProfile => ({
  name: user.name,
  title: user.role === 'admin' ? 'Administrador' : 'Operador',
  email: user.email,
  level: user.role,
  isAuthenticated: true,
  provider: user.googleLinked ? 'google' : 'manual',
});

interface TerminalProps {
  user: AuthUser;
  onUserChange: (user: AuthUser) => void;
  /** Encerra a sessão no backend e volta ao login. */
  onLogout: () => void;
  /** Volta ao login sem chamar o backend (ex.: conta excluída). */
  onSignedOut: () => void;
}

export default function Terminal({ user, onUserChange, onLogout, onSignedOut }: TerminalProps) {
  const [currentScreen, setCurrentScreen] = useState<ScreenView>('terminal');
  const [chaosLevel, setChaosLevel] = useState<number>(50);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isLlmModalOpen, setIsLlmModalOpen] = useState<boolean>(false);
  const operator = toOperator(user);
  const isAdmin = user.role === 'admin';
  const [books, setBooks] = useState<IndexedBook[]>(INITIAL_BOOKS);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [welcomeMessage()]);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [llmConnection, setLlmConnection] = useState<LlmConnection | null>(null);

  // Total Chunks calculation
  const totalChunks = books.reduce((acc, b) => acc + b.chunks, 25680);

  const pushNimbError = (text: string) =>
    setMessages((prev) => [
      ...prev,
      {
        id: 'msg_err_' + Date.now(),
        sender: 'nimb',
        text,
        timestamp: getNow(),
        isError: true,
      },
    ]);

  const handleApiError = (err: unknown, context: string) => {
    console.error(context, err);
    const apiErr = err instanceof ApiError ? err : null;
    if (apiErr && (apiErr.status === 0 || apiErr.status >= 500)) {
      // 502 com detalhe vem do provedor de LLM; sem detalhe, é o backend fora do ar
      if (apiErr.status !== 502 || apiErr.message.startsWith('Backend')) setBackendOnline(false);
    }
    if (apiErr?.status === 409) setIsLlmModalOpen(true);
    return apiErr?.message || 'Erro inesperado ao consultar o backend.';
  };

  const loadSessions = useCallback(async () => {
    try {
      const sessions = await sessionApiService.list();
      setHistory(sessions.map(sessionToHistory));
    } catch (err) {
      console.warn('Não foi possível carregar o histórico:', err);
    }
  }, []);

  const loadStatus = useCallback(async () => {
    try {
      const active = await llmApiService.getActive();
      setLlmConnection(active);
      setBackendOnline(true);
    } catch {
      setBackendOnline(false);
    }
  }, []);

  useEffect(() => {
    loadStatus();
    loadSessions();
  }, [loadStatus, loadSessions]);

  // Handle Query Submission
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;

    const userMsg: ChatMessage = {
      id: 'msg_' + Date.now(),
      sender: 'user',
      text: query,
      timestamp: getNow(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue('');
    setIsLoading(true);

    try {
      const response = await ragApiService.queryRag({
        prompt: query,
        chaosLevel,
        bookIds: books.map((b) => b.id),
        sessionId: activeSessionId,
      });

      const nimbMsg: ChatMessage = {
        id: response.messageId || 'msg_res_' + Date.now(),
        sender: 'nimb',
        text: response.answer,
        timestamp: getNow(),
        ragMetadata: {
          bookTitle: response.bookTitle,
          page: response.page,
          similarity: response.similarity,
          chaosApplied: response.chaosApplied,
          provider: response.provider,
          model: response.model,
          connectionName: response.connectionName,
          latencyMs: response.latencyMs,
        },
        quote: response.quote || undefined,
        rollTable: response.rollTable || undefined,
      };

      setMessages((prev) => [...prev, nimbMsg]);
      setBackendOnline(true);

      if (response.sessionId) {
        setActiveSessionId(response.sessionId);
        loadSessions();
      }
    } catch (err) {
      pushNimbError(handleApiError(err, 'Error querying RAG:'));
    } finally {
      setIsLoading(false);
    }
  };

  // Reenvia a pergunta do usuário que originou a resposta selecionada
  const handleRerollMessage = (messageId: string) => {
    const index = messages.findIndex((m) => m.id === messageId);
    const previousUser = messages
      .slice(0, index)
      .reverse()
      .find((m) => m.sender === 'user');
    if (previousUser) handleSendMessage(previousUser.text);
  };

  // Start new clean session
  const handleNewSession = () => {
    setActiveSessionId(null);
    setMessages([
      {
        id: 'msg_fresh_' + Date.now(),
        sender: 'nimb',
        text: 'Nova sinapse ativada. O tecido temporal foi reiniciado. Consulte os grimórios à vontade.',
        timestamp: getNow(),
        syntaxTag: '#fluxo-novo',
      },
    ]);
  };

  // Select historical question
  const handleSelectHistory = async (item: HistoryItem) => {
    try {
      const session = await sessionApiService.get(item.id);
      setActiveSessionId(session.id);
      setMessages(
        session.messages.length > 0 ? session.messages.map(toChatMessage) : [welcomeMessage()]
      );
    } catch (err) {
      pushNimbError(handleApiError(err, 'Error loading session:'));
    }
  };

  const handleDeleteHistory = async (item: HistoryItem) => {
    try {
      await sessionApiService.remove(item.id);
      if (item.id === activeSessionId) handleNewSession();
      await loadSessions();
    } catch (err) {
      pushNimbError(handleApiError(err, 'Error deleting session:'));
    }
  };

  const handleClearHistory = async () => {
    if (history.length === 0) return;
    if (!window.confirm('Apagar todas as conversas salvas?')) return;
    try {
      await sessionApiService.removeAll();
      setHistory([]);
      handleNewSession();
    } catch (err) {
      pushNimbError(handleApiError(err, 'Error clearing history:'));
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col cyber-bg overflow-hidden relative select-none">
      {/* Background Graphic Watermark */}
      <div className="nimb-watermark pointer-events-none opacity-[0.03]"></div>

      {/* TOPBAR / HEAD */}
      <Header
        chaosLevel={chaosLevel}
        onChaosChange={setChaosLevel}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        onOpenUploadModal={() => setIsUploadModalOpen(true)}
        onOpenLlmModal={() => setIsLlmModalOpen(true)}
        llmConnection={llmConnection}
        backendOnline={backendOnline}
        onNavigateLogin={() =>
          setCurrentScreen(currentScreen === 'account' ? 'terminal' : 'account')
        }
        operator={operator}
        currentScreen={currentScreen}
      />

      {/* MAIN VIEWPORT (Either Terminal or Login Screen) */}
      {currentScreen === 'terminal' ? (
        <div className="flex-1 flex overflow-hidden relative">
          {/* SIDEBAR */}
          <Sidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            operator={operator}
            history={history}
            activeHistoryId={activeSessionId}
            onSelectHistory={handleSelectHistory}
            onClearHistory={handleClearHistory}
            onDeleteHistory={handleDeleteHistory}
            backendOnline={backendOnline}
            books={books}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
            onNewSession={handleNewSession}
            onNavigateLogin={() => setCurrentScreen('account')}
          />

          {/* CHAT BODY */}
          <ChatArea
            messages={messages}
            isLoading={isLoading}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSendMessage={() => handleSendMessage()}
            onSelectSuggestion={(text) => handleSendMessage(text)}
            onRerollMessage={handleRerollMessage}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
            llmLabel={llmConnection ? `${llmConnection.name} (${llmConnection.model})` : null}
            indexedBooksCount={books.length}
            totalChunks={totalChunks}
          />
        </div>
      ) : (
        /* SCREEN 2: MINHA CONTA (perfil, senha, sessões, admin) */
        <AccountScreen
          user={user}
          onUserChange={onUserChange}
          onLogout={onLogout}
          onAccountDeleted={onSignedOut}
          onBack={() => setCurrentScreen('terminal')}
        />
      )}

      {/* SCREEN 3: POP-UP TO UPLOAD PDF BOOKS (Grimórios) */}
      <PdfUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        books={books}
        onAddBook={(newBook) => setBooks((prev) => [newBook, ...prev])}
        onRemoveBook={(id) => setBooks((prev) => prev.filter((b) => b.id !== id))}
      />

      {/* SCREEN 4: CAIXA DE CONEXÃO COM A LLM (API) */}
      <LlmConnectionModal
        isAdmin={isAdmin}
        isOpen={isLlmModalOpen}
        onClose={() => setIsLlmModalOpen(false)}
        onChanged={(active) => {
          setLlmConnection(active);
          setBackendOnline(true);
        }}
      />
    </div>
  );
}
