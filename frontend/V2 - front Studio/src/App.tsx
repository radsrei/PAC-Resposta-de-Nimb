import { useState } from 'react';
import { Header } from './components/layout/Header';
import { Sidebar } from './components/layout/Sidebar';
import { ChatArea } from './components/chat/ChatArea';
import { LoginScreen } from './components/auth/LoginScreen';
import { PdfUploadModal } from './components/modals/PdfUploadModal';
import {
  ChatMessage,
  HistoryItem,
  IndexedBook,
  OperatorProfile,
  ScreenView,
} from './types';
import { ragApiService } from './services/ragApi';
import { authApiService } from './services/authApi';

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

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 'msg_01',
    sender: 'nimb',
    text: 'Saudações, mortal ou viajante planar. O dado foi rolado e o grimório aberto. Os tomos de Tormenta20 estão mapeados na memória neural. O que você deseja extrair do tecido da realidade hoje?',
    timestamp: '14:30:12',
    syntaxTag: '#sintaxe-01',
  },
  {
    id: 'msg_02',
    sender: 'user',
    text: 'Diga, meu pequeno ser perdido... Qual é o status do kernel e o efeito primordial da magia do Caos de acordo com o Grimório?',
    timestamp: '14:31:05',
  },
  {
    id: 'msg_03',
    sender: 'nimb',
    text: 'O status do Kernel Nimb permanece em estabilidade caótica (98.4% de sincronização com o banco vetorial).\n\nConsultando o Grimório do Caos.pdf e os registros de Tormenta20, quando você conjura uma magia sob a égide do Caos Primordial:',
    timestamp: '14:31:40',
    ragMetadata: {
      bookTitle: 'Grimório do Caos.pdf',
      page: 77,
      similarity: '94.2%',
      chaosApplied: 78,
    },
    rollTable: {
      title: 'EFEITO DE RETORNO // TABELA DE ROLO ALEATÓRIO',
      diceRoll: 'd20: Resultado 18',
      description: '“O conjurador distorce os limites da física planar. O alvo sofre dano de essência aleatória e deve rolar Fortitude ou trocar de lugar no espaço com o objeto sólido mais próximo em até 9m.”',
    },
  },
];

const INITIAL_HISTORY: HistoryItem[] = [
  {
    id: 'hist_1',
    title: 'Efeitos da loucura de Nimb',
    timestampDesc: 'Hoje, 14:32',
    refCount: 4,
    conversation: INITIAL_MESSAGES,
  },
  {
    id: 'hist_2',
    title: 'Tabela de magias aleatórias',
    timestampDesc: 'Ontem, 21:10',
    refCount: 2,
  },
  {
    id: 'hist_3',
    title: 'Atributos do Clérigo Caótico',
    timestampDesc: '18 Fev',
    refCount: 6,
  },
];

export default function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenView>('terminal');
  const [chaosLevel, setChaosLevel] = useState<number>(78);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState<boolean>(false);
  const [operator, setOperator] = useState<OperatorProfile>(authApiService.getStoredSession());
  const [books, setBooks] = useState<IndexedBook[]>(INITIAL_BOOKS);
  const [history, setHistory] = useState<HistoryItem[]>(INITIAL_HISTORY);
  const [activeHistoryId, setActiveHistoryId] = useState<string | null>('hist_1');
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);

  // Total Chunks calculation
  const totalChunks = books.reduce((acc, b) => acc + b.chunks, 25680);

  // Formatted timestamp
  const getNow = () =>
    new Date().toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

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
      });

      const nimbMsg: ChatMessage = {
        id: 'msg_res_' + Date.now(),
        sender: 'nimb',
        text: response.answer,
        timestamp: getNow(),
        ragMetadata: {
          bookTitle: response.bookTitle,
          page: response.page,
          similarity: response.similarity,
          chaosApplied: response.chaosApplied,
        },
        quote: response.quote,
        rollTable: response.rollTable,
      };

      setMessages((prev) => [...prev, nimbMsg]);

      // Update or prepend history
      setHistory((prev) => {
        const titleSnippet = query.length > 32 ? query.slice(0, 32) + '...' : query;
        const exists = prev.some((h) => h.title === titleSnippet);
        if (exists) return prev;
        return [
          {
            id: 'hist_' + Date.now(),
            title: titleSnippet,
            timestampDesc: 'Agora mesmo',
            refCount: 3,
          },
          ...prev,
        ];
      });
    } catch (err) {
      console.error('Error querying RAG:', err);
    } finally {
      setIsLoading(false);
    }
  };

  // Start new clean session
  const handleNewSession = () => {
    setActiveHistoryId(null);
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
  const handleSelectHistory = (item: HistoryItem) => {
    setActiveHistoryId(item.id);
    if (item.conversation && item.conversation.length > 0) {
      setMessages(item.conversation);
    } else {
      // Simulate historical prompt
      handleSendMessage(item.title);
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
        onNavigateLogin={() =>
          setCurrentScreen(currentScreen === 'login' ? 'terminal' : 'login')
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
            activeHistoryId={activeHistoryId}
            onSelectHistory={handleSelectHistory}
            onClearHistory={() => setHistory([])}
            books={books}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
            onNewSession={handleNewSession}
            onNavigateLogin={() => setCurrentScreen('login')}
          />

          {/* CHAT BODY */}
          <ChatArea
            messages={messages}
            isLoading={isLoading}
            inputValue={inputValue}
            onInputChange={setInputValue}
            onSendMessage={() => handleSendMessage()}
            onSelectSuggestion={(text) => handleSendMessage(text)}
            onOpenUploadModal={() => setIsUploadModalOpen(true)}
            indexedBooksCount={books.length}
            totalChunks={totalChunks}
          />
        </div>
      ) : (
        /* SCREEN 2: LOGIN & OPERATOR AUTHENTICATION */
        <LoginScreen
          currentOperator={operator}
          onBackToTerminal={() => setCurrentScreen('terminal')}
          onSuccess={(newProfile) => {
            setOperator(newProfile);
            setCurrentScreen('terminal');
          }}
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
    </div>
  );
}
