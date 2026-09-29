import React, { useRef, useEffect } from 'react';
import { ChatMessage } from '../../types';
import { ChatMessageItem } from './ChatMessageItem';
import { SuggestionChips } from './SuggestionChips';
import { ChatInput } from './ChatInput';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  inputValue: string;
  onInputChange: (val: string) => void;
  onSendMessage: () => void;
  onSelectSuggestion: (text: string) => void;
  onOpenUploadModal: () => void;
  indexedBooksCount: number;
  totalChunks: number;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  inputValue,
  onInputChange,
  onSendMessage,
  onSelectSuggestion,
  onOpenUploadModal,
  indexedBooksCount,
  totalChunks,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when messages update
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  return (
    <main className="flex-1 flex flex-col overflow-hidden relative z-10">
      {/* Scrollable Conversation Container */}
      <section
        ref={scrollRef}
        className="flex-1 overflow-y-auto custom-scrollbar p-4 md:p-6 lg:p-8 flex flex-col gap-6 scroll-smooth"
      >
        {/* Bento Hologram Welcome Banner */}
        <div className="w-full max-w-4xl mx-auto rounded-2xl holo-card p-5 border border-[rgba(162,89,255,0.2)] overflow-hidden relative">
          <div className="absolute -top-12 -right-12 w-40 h-40 bg-[#A259FF]/15 rounded-full blur-3xl pointer-events-none"></div>
          <div className="absolute -bottom-12 -left-12 w-40 h-40 bg-[#39D98A]/15 rounded-full blur-3xl pointer-events-none"></div>

          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 relative z-10">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-[#A259FF]/20 border border-[#A259FF]/30 text-[#d8b9ff] font-mono text-[11px] font-semibold">
                  PROTOCOLO DE RECUPERAÇÃO RAG
                </span>
                <span className="font-mono text-[10px] text-[#39D98A]">
                  VECTOR DB CONECTADO
                </span>
              </div>
              <h2 className="text-xl font-bold text-[#F0EEF8] tracking-tight">
                Bem-vindo ao Núcleo de Consulta NIMB
              </h2>
              <p className="text-sm text-[#8B87A8] max-w-2xl leading-relaxed">
                Todas as respostas são sintetizadas cruzando seus tomos indexados com o grau de instabilidade do Medidor de Caos. Faça perguntas sobre magias, regras ou consulte a sorte dos dados.
              </p>
            </div>

            {/* Mini stats box */}
            <div className="flex md:flex-col gap-3 font-mono text-xs border-t md:border-t-0 md:border-l border-[#34344E] pt-3 md:pt-0 md:pl-5 flex-shrink-0">
              <div>
                <span className="text-[#8B87A8] text-[10px] uppercase block">
                  Índice Semântico
                </span>
                <span className="text-[#39D98A] font-semibold tabular-nums">
                  {totalChunks.toLocaleString()} fragmentos
                </span>
              </div>
              <div>
                <span className="text-[#8B87A8] text-[10px] uppercase block">
                  Modo Ativo
                </span>
                <span className="text-[#d8b9ff] font-semibold">
                  Raciocínio Probabilístico
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Message Stream */}
        <div className="w-full max-w-4xl mx-auto flex flex-col gap-5">
          {messages.map((msg) => (
            <ChatMessageItem
              key={msg.id}
              message={msg}
              onReroll={msg.sender === 'nimb' ? () => onSendMessage() : undefined}
            />
          ))}

          {/* Dynamic AI Typing Indicator */}
          {isLoading && (
            <div className="flex items-start gap-3.5 max-w-[80%] animate-fadeIn">
              <div className="w-9 h-9 rounded-xl bg-[#13131F] border border-[#A259FF]/50 flex items-center justify-center flex-shrink-0">
                <span className="material-symbols-outlined text-[#d8b9ff] text-[18px]">
                  terminal
                </span>
              </div>
              <div className="bg-[#181827]/90 border border-[rgba(162,89,255,0.25)] rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                <span className="font-mono text-xs text-[#d8b9ff] font-medium">
                  Nimb está consultando os grimórios vetoriais
                </span>
                <div className="flex gap-1 items-center ml-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#A259FF] typing-dot"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#39D98A] typing-dot"></span>
                  <span className="w-1.5 h-1.5 rounded-full bg-[#d8b9ff] typing-dot"></span>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Input Zone & Quick Suggestions */}
      <footer className="p-3 md:p-5 border-t border-[rgba(162,89,255,0.25)] bg-[#0D0D14]/90 backdrop-blur-xl flex flex-col gap-2.5 max-w-4xl w-full mx-auto relative z-20">
        <SuggestionChips
          onSelectSuggestion={onSelectSuggestion}
          disabled={isLoading}
        />
        <ChatInput
          value={inputValue}
          onChange={onInputChange}
          onSend={onSendMessage}
          onOpenUploadModal={onOpenUploadModal}
          isLoading={isLoading}
          indexedBooksCount={indexedBooksCount}
        />
      </footer>
    </main>
  );
};
