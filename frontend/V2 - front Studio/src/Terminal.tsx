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
import { ragApiService, toIndexedBook } from './services/ragApi';
import { llmApiService } from './services/llmApi';
import { sessionApiService } from './services/sessionApi';
import { DEFAULT_CHAOS_LEVEL } from './chaosLevels';
import { ConfettiBurst } from './components/chat/ConfettiBurst';
import { playChaosSound, preloadChaosSounds } from './services/chaosSound';
import { ApiError } from './services/http';

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
            bookTitle: meta.bookTitle ?? '',
            page: meta.page ?? null,
            similarity: meta.similarity ?? '-',
            chaosApplied: meta.chaosApplied ?? 0,
            harnessRounds: meta.harnessRounds,
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

const CHAOS_RULE_STORAGE_KEY = 'nimb:chaos-rule';

// Duração do giro da tela ao revelar uma alucinação (igual à animação .chaos-spiral)
const SPIRAL_MS = 700;

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
  const [chaosLevel, setChaosLevel] = useState<number>(DEFAULT_CHAOS_LEVEL);
  // Regra Nimb: ligada decide a alucinação pela regra antes da pergunta; desligada, o backend
  // sorteia com a chance do .env depois da busca. Preferência lembrada só neste navegador.
  const [useChaosRule, setUseChaosRule] = useState<boolean>(() => {
    try {
      return localStorage.getItem(CHAOS_RULE_STORAGE_KEY) !== 'off';
    } catch {
      return true;
    }
  });
  const handleToggleChaosRule = () => {
    setUseChaosRule((on) => {
      try {
        localStorage.setItem(CHAOS_RULE_STORAGE_KEY, on ? 'off' : 'on');
      } catch {
        // sem armazenamento (aba anônima): vale só nesta sessão
      }
      return !on;
    });
  };
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [isLlmModalOpen, setIsLlmModalOpen] = useState<boolean>(false);
  const operator = toOperator(user);
  const isAdmin = user.role === 'admin';
  const [books, setBooks] = useState<IndexedBook[]>([]);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>(() => [welcomeMessage()]);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  // Alucinação de Nimb: "pensamento" laranja, giro da tela e confetes na resposta
  const [isHallucinating, setIsHallucinating] = useState<boolean>(false);
  const [isSpinning, setIsSpinning] = useState<boolean>(false);
  const [confettiKey, setConfettiKey] = useState<number>(0);
  const [backendOnline, setBackendOnline] = useState<boolean>(true);
  const [llmConnection, setLlmConnection] = useState<LlmConnection | null>(null);

  // Total de trechos nos bancos vetoriais dos livros liberados
  const totalChunks = books.reduce((acc, b) => acc + b.chunks, 0);
  // Perguntas só com ao menos um livro liberado e com banco vetorial pronto
  const readyBooks = books.filter((b) => b.status === 'indexed');
  const canAsk = readyBooks.length > 0;

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
    if (apiErr?.status === 428) setIsUploadModalOpen(true);
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

  // Livros liberados para o usuário (validados por upload do PDF)
  const loadBooks = useCallback(async () => {
    try {
      const catalog = await ragApiService.listBooks();
      setBooks(catalog.filter((b) => b.unlocked).map(toIndexedBook));
    } catch (err) {
      console.warn('Não foi possível carregar os livros:', err);
    }
  }, []);

  useEffect(() => {
    preloadChaosSounds();
  }, []);

  // Giro rápido (SPIRAL_MS) e, ao terminar, confetes; nada disso segura a resposta na tela
  const revealHallucination = () => {
    playChaosSound('hallucinationReveal');
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    setIsSpinning(true);
    window.setTimeout(() => {
      setIsSpinning(false);
      setConfettiKey((k) => k + 1);
    }, SPIRAL_MS);
  };

  useEffect(() => {
    loadStatus();
    loadSessions();
    loadBooks();
  }, [loadStatus, loadSessions, loadBooks]);

  // Handle Query Submission
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputValue).trim();
    if (!query || isLoading) return;
    if (!canAsk) {
      setIsUploadModalOpen(true);
      return;
    }

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
      // Só com a Regra Nimb a alucinação é conhecida antes da resposta ("pensamento" laranja)
      const roll = useChaosRule ? await ragApiService.rollChaos(query, chaosLevel) : null;
      if (roll?.hallucinated) {
        setIsHallucinating(true);
        playChaosSound('hallucinationThinking');
      }

      const response = await ragApiService.queryRag({
        prompt: query,
        chaosLevel,
        useChaosRule,
        rollToken: roll?.rollToken ?? null,
        bookIds: readyBooks.map((b) => b.id),
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
          harnessRounds: response.harnessRounds,
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
      if (response.hallucinated ?? roll?.hallucinated) revealHallucination();

      if (response.sessionId) {
        setActiveSessionId(response.sessionId);
        loadSessions();
      }
    } catch (err) {
      pushNimbError(handleApiError(err, 'Error querying RAG:'));
    } finally {
      setIsLoading(false);
      setIsHallucinating(false);
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
    <>
    <div
      className={`h-screen w-screen flex flex-col cyber-bg overflow-hidden relative select-none ${
        isSpinning ? 'chaos-spiral' : ''
      }`}
    >
      {/* Background Graphic Watermark */}
      <div className="nimb-watermark pointer-events-none opacity-[0.03]"></div>

      {/* TOPBAR / HEAD */}
      <Header
        chaosLevel={chaosLevel}
        onChaosChange={setChaosLevel}
        useChaosRule={useChaosRule}
        onToggleChaosRule={handleToggleChaosRule}
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
            isHallucinating={isHallucinating}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSendMessage={() => handleSendMessage()}
            onSelectSuggestion={(text) => handleSendMessage(text)}
            onRerollMessage={handleRerollMessage}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
            llmLabel={llmConnection ? `${llmConnection.name} (${llmConnection.model})` : null}
            indexedBooksCount={books.length}
            totalChunks={totalChunks}
            canAsk={canAsk}
          />
        </div>
      ) : (
        /* SCREEN 2: MINHA CONTA (perfil, sessões, admin) */
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
        onBookUnlocked={(book) =>
          setBooks((prev) => [toIndexedBook(book), ...prev.filter((b) => b.id !== book.id)])
        }
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
    <ConfettiBurst burstKey={confettiKey} />
    </>
  );
}
