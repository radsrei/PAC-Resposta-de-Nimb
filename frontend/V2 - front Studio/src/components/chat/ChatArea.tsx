import React, { useRef, useEffect } from 'react';
import { ChatMessage } from '../../types';
import { ChatMessageItem } from './ChatMessageItem';
import { SuggestionChips } from './SuggestionChips';
import { ChatInput } from './ChatInput';

interface ChatAreaProps {
  messages: ChatMessage[];
  isLoading: boolean;
  /** O dado do caos caiu: o "pensamento" fica laranja. */
  isHallucinating?: boolean;
  inputValue: string;
  onInputChange: (val: string) => void;
  onSendMessage: () => void;
  onSelectSuggestion: (text: string) => void;
  onRerollMessage: (messageId: string) => void;
  onOpenUploadModal: () => void;
  llmLabel: string | null;
  indexedBooksCount: number;
  totalChunks: number;
  canAsk: boolean;
}

export const ChatArea: React.FC<ChatAreaProps> = ({
  messages,
  isLoading,
  isHallucinating = false,
  inputValue,
  onInputChange,
  onSendMessage,
  onSelectSuggestion,
  onRerollMessage,
  onOpenUploadModal,
  llmLabel,
  indexedBooksCount,
  totalChunks,
  canAsk,
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
                <span
                  className={`font-mono text-[10px] ${llmLabel ? 'text-[#39D98A]' : 'text-amber-300'}`}
                >
                  {llmLabel ? `LLM CONECTADA: ${llmLabel}` : 'NENHUMA LLM CONECTADA'}
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
                  {canAsk ? 'RAG nos livros liberados' : 'Aguardando livro'}
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
              onReroll={
                msg.sender === 'nimb' && !isLoading ? () => onRerollMessage(msg.id) : undefined
              }
            />
          ))}

          {/* Dynamic AI Typing Indicator */}
          {isLoading && (
            <div className="flex items-start gap-3.5 max-w-[80%] animate-fadeIn">
              <div
                className={`w-9 h-9 rounded-xl bg-[#13131F] border flex items-center justify-center flex-shrink-0 transition-colors ${
                  isHallucinating
                    ? 'border-[#FF8A00]/70 shadow-[0_0_12px_rgba(255,138,0,0.45)]'
                    : 'border-[#A259FF]/50'
                }`}
              >
                <span
                  className={`material-symbols-outlined text-[18px] ${
                    isHallucinating ? 'text-[#FFB547]' : 'text-[#d8b9ff]'
                  }`}
                >
                  terminal
                </span>
              </div>
              <div
                className={`bg-[#181827]/90 border rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2 transition-colors ${
                  isHallucinating
                    ? 'border-[#FF8A00]/60 shadow-[0_0_14px_rgba(255,138,0,0.25)]'
                    : 'border-[rgba(162,89,255,0.25)]'
                }`}
              >
                <span
                  className={`font-mono text-xs font-medium ${
                    isHallucinating ? 'text-[#FFB547]' : 'text-[#d8b9ff]'
                  }`}
                >
                  Nimb está consultando os grimórios vetoriais
                </span>
                <div className="flex gap-1 items-center ml-2">
                  {(isHallucinating
                    ? ['bg-[#FF8A00]', 'bg-[#FFB547]', 'bg-[#FF6A00]']
                    : ['bg-[#A259FF]', 'bg-[#39D98A]', 'bg-[#d8b9ff]']
                  ).map((color) => (
                    <span key={color} className={`w-1.5 h-1.5 rounded-full ${color} typing-dot`}></span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Input Zone & Quick Suggestions */}
      <footer className="p-3 md:p-5 border-t border-[rgba(162,89,255,0.25)] bg-[#0D0D14]/90 backdrop-blur-xl flex flex-col gap-2.5 max-w-4xl w-full mx-auto relative z-20">
        {!canAsk && (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 px-3 py-2.5 rounded-xl bg-amber-400/10 border border-amber-400/30 text-xs text-amber-200">
            <span className="flex items-center gap-2">
              <span className="material-symbols-outlined text-[16px]">menu_book</span>
              Adicione o livro do Tormenta20 para liberar as perguntas.
            </span>
            <button
              type="button"
              onClick={onOpenUploadModal}
              className="px-3 py-1 rounded-lg bg-[#39D98A] text-black font-semibold font-mono text-[11px] hover:brightness-110 cursor-pointer self-start sm:self-auto"
            >
              Subir PDF
            </button>
          </div>
        )}
        <SuggestionChips
          onSelectSuggestion={onSelectSuggestion}
          disabled={isLoading || !canAsk}
        />
        <ChatInput
          value={inputValue}
          onChange={onInputChange}
          onSend={onSendMessage}
          onOpenUploadModal={onOpenUploadModal}
          isLoading={isLoading}
          locked={!canAsk}
          indexedBooksCount={indexedBooksCount}
        />
      </footer>
    </main>
  );
};
