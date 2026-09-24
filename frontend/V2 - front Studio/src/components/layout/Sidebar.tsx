import React from 'react';
import { HistoryItem, IndexedBook, OperatorProfile } from '../../types';

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  operator: OperatorProfile;
  history: HistoryItem[];
  activeHistoryId: string | null;
  onSelectHistory: (item: HistoryItem) => void;
  onClearHistory: () => void;
  books: IndexedBook[];
  onOpenUploadModal: () => void;
  onNewSession: () => void;
  onNavigateLogin: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  onClose,
  operator,
  history,
  activeHistoryId,
  onSelectHistory,
  onClearHistory,
  books,
  onOpenUploadModal,
  onNewSession,
  onNavigateLogin,
}) => {
  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={`w-72 md:w-80 flex-shrink-0 bg-[#0A0A10]/95 md:bg-[#13131F]/80 border-r border-[rgba(162,89,255,0.25)] flex flex-col justify-between backdrop-blur-xl z-40 transition-all duration-300 fixed md:static inset-y-0 ${
          isOpen ? 'left-0' : '-left-full md:left-0'
        }`}
      >
        {/* Top: User Profile & New Synapse Action */}
        <div className="p-4 border-b border-[#34344E]/60 space-y-3">
          {/* User Profile Card */}
          <div
            onClick={onNavigateLogin}
            className="flex items-center justify-between bg-[#181827]/70 hover:bg-[#181827] p-2.5 rounded-xl border border-[rgba(162,89,255,0.25)] hover:border-[#39D98A]/50 transition-all cursor-pointer group"
            title="Acessar Tela de Login / Credenciais"
          >
            <div className="flex items-center gap-2.5">
              <div className="relative w-9 h-9 rounded-lg bg-gradient-to-tr from-[#A259FF] to-[#39D98A] p-0.5">
                <div className="w-full h-full bg-[#13131F] rounded-[7px] flex items-center justify-center font-bold text-xs text-[#39D98A] font-mono">
                  {operator.name.slice(0, 2).toUpperCase()}
                </div>
                <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-[#39D98A] border-2 border-[#13131F]"></span>
              </div>
              <div className="overflow-hidden">
                <div className="text-xs font-semibold text-[#F0EEF8] group-hover:text-[#39D98A] transition-colors truncate">
                  {operator.name}
                </div>
                <div className="font-mono text-[10px] text-[#8B87A8] truncate">
                  {operator.title}
                </div>
              </div>
            </div>
            <span className="material-symbols-outlined text-[#8B87A8] text-[18px] group-hover:text-[#d8b9ff] transition-colors">
              badge
            </span>
          </div>

          {/* Nova Sinapse Neural Button */}
          <button
            onClick={onNewSession}
            className="w-full py-2.5 px-3 rounded-xl bg-gradient-to-r from-[#A259FF]/20 via-[#A259FF]/30 to-[#39D98A]/20 hover:from-[#A259FF]/30 hover:to-[#39D98A]/30 border border-[#A259FF]/40 text-[#F0EEF8] text-xs font-semibold flex items-center justify-center gap-2 transition-all shadow-[0_0_15px_rgba(162,89,255,0.15)] active:scale-98 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px] text-[#39D98A]">
              add_circle
            </span>
            <span>Nova Sinapse Neural</span>
          </button>
        </div>

        {/* Middle: Scrollable RAG Bases (v2) & Previous Questions */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-5">
          {/* SECTION 1: Bases RAG Carregadas (v2) */}
          <div>
            <div className="flex items-center justify-between px-2 mb-2">
              <span className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px] text-[#39D98A]">
                  folder_special
                </span>
                Bases RAG (v2)
              </span>
              <button
                onClick={onOpenUploadModal}
                className="font-mono text-[10px] text-[#39D98A] bg-[#39D98A]/10 hover:bg-[#39D98A]/20 px-2 py-0.5 rounded border border-[#39D98A]/30 transition-all flex items-center gap-1 cursor-pointer"
                title="Subir novo arquivo PDF"
              >
                <span>+</span>
                <span>{books.length} Livros</span>
              </button>
            </div>

            <div className="space-y-1.5 font-mono text-xs">
              {books.map((book) => (
                <div
                  key={book.id}
                  onClick={onOpenUploadModal}
                  className="p-2 rounded-lg bg-[#181827]/60 hover:bg-[#181827] border border-[#34344E] hover:border-[#39D98A]/40 transition-all flex items-center justify-between group cursor-pointer"
                  title={`${book.fileName} (${book.size}) - Clique para gerenciar`}
                >
                  <div className="flex items-center gap-2 truncate">
                    <span className="material-symbols-outlined text-[#39D98A] text-[16px] flex-shrink-0">
                      menu_book
                    </span>
                    <span className="truncate text-[#F0EEF8] text-[11px] group-hover:text-[#39D98A] transition-colors">
                      {book.fileName}
                    </span>
                  </div>
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#39D98A]/15 text-[#39D98A] border border-[#39D98A]/25 flex-shrink-0">
                    {book.progress}%
                  </span>
                </div>
              ))}

              {/* Quick upload card trigger */}
              <button
                onClick={onOpenUploadModal}
                className="w-full py-1.5 px-2 rounded-lg border border-dashed border-[#34344E] hover:border-[#A259FF]/50 text-[#8B87A8] hover:text-[#d8b9ff] text-[10px] flex items-center justify-center gap-1.5 transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[14px]">cloud_upload</span>
                <span>Subir Livro PDF (.pdf)</span>
              </button>
            </div>
          </div>

          {/* SECTION 2: Perguntas Anteriores / Histórico */}
          <div>
            <div className="px-2 mb-2 flex items-center justify-between">
              <span className="font-mono text-[11px] uppercase tracking-wider text-[#8B87A8] font-semibold flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[15px] text-[#d8b9ff]">
                  history
                </span>
                Perguntas Anteriores
              </span>
              <button
                onClick={onClearHistory}
                className="text-[10px] text-[#8B87A8] hover:text-[#F0EEF8] transition-colors cursor-pointer"
              >
                Limpar
              </button>
            </div>

            <div className="space-y-1">
              {history.map((item) => {
                const isActive = activeHistoryId === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      onSelectHistory(item);
                      if (window.innerWidth < 768) {
                        onClose();
                      }
                    }}
                    className={`w-full text-left p-2.5 rounded-lg flex items-start gap-2 group transition-all cursor-pointer border ${
                      isActive
                        ? 'bg-[#A259FF]/15 border-l-2 border-l-[#A259FF] border-transparent text-[#d8b9ff]'
                        : 'hover:bg-[#181827]/70 text-[#8B87A8] border-transparent hover:border-[#34344E]'
                    }`}
                  >
                    <span
                      className={`material-symbols-outlined text-[16px] mt-0.5 flex-shrink-0 ${
                        isActive ? 'text-[#d8b9ff]' : 'text-[#8B87A8] group-hover:text-[#39D98A]'
                      }`}
                    >
                      chat_bubble
                    </span>
                    <div className="flex-1 truncate">
                      <div
                        className={`text-xs truncate ${
                          isActive
                            ? 'font-medium text-[#F0EEF8]'
                            : 'font-normal text-[#8B87A8] group-hover:text-[#F0EEF8]'
                        }`}
                      >
                        {item.title}
                      </div>
                      <div className="font-mono text-[9px] text-[#8B87A8]/80">
                        {item.timestampDesc} // {item.refCount} refs
                      </div>
                    </div>
                  </button>
                );
              })}

              {history.length === 0 && (
                <div className="p-3 text-center text-xs text-[#8B87A8] font-mono">
                  Nenhuma consulta gravada ainda.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Bottom Status Footer */}
        <div className="p-3 border-t border-[#34344E]/60 bg-[#0A0A10]/60 flex items-center justify-between font-mono text-[10px] text-[#8B87A8]">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-[#39D98A] animate-pulse"></span>
            Cluster RAG: Online
          </span>
          <span className="tabular-nums">Latência: 24ms</span>
        </div>
      </aside>
    </>
  );
};
