import React, { useRef, useEffect } from 'react';

interface ChatInputProps {
  value: string;
  onChange: (val: string) => void;
  onSend: () => void;
  onOpenUploadModal: () => void;
  isLoading: boolean;
  indexedBooksCount: number;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  value,
  onChange,
  onSend,
  onOpenUploadModal,
  isLoading,
  indexedBooksCount,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto expand textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 130)}px`;
    }
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading && value.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className="relative bg-[#1A1A2E] rounded-2xl border border-[rgba(162,89,255,0.25)] focus-within:border-[#39D98A] focus-within:shadow-[0_0_20px_rgba(57,217,138,0.15)] transition-all">
      <div className="flex items-end gap-2 p-2.5">
        {/* Attachment / PDF upload trigger */}
        <button
          type="button"
          onClick={onOpenUploadModal}
          className="p-2 text-[#8B87A8] hover:text-[#39D98A] hover:bg-[#181827] rounded-xl transition-colors flex-shrink-0 cursor-pointer"
          title="Anexar documento ou carregar novo Grimório PDF"
        >
          <span className="material-symbols-outlined text-[20px] block">attach_file</span>
        </button>

        {/* Textarea Input */}
        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={isLoading}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Pergunte a Nimb sobre regras, monstros ou role o dado..."
          className="w-full bg-transparent border-0 focus:ring-0 text-[#F0EEF8] placeholder-[#8B87A8]/60 text-sm py-2 resize-none max-h-32 custom-scrollbar font-sans outline-none leading-relaxed"
        />

        {/* Send Action Button */}
        <button
          type="button"
          onClick={onSend}
          disabled={isLoading || !value.trim()}
          title="Disparar Consulta RAG (Enter)"
          className="w-10 h-10 rounded-xl bg-gradient-to-r from-[#A259FF] to-[#39D98A] text-black font-bold flex items-center justify-center flex-shrink-0 hover:scale-105 active:scale-95 transition-all shadow-[0_0_12px_rgba(57,217,138,0.3)] disabled:opacity-40 disabled:hover:scale-100 cursor-pointer"
        >
          {isLoading ? (
            <span className="material-symbols-outlined text-[20px] animate-spin">refresh</span>
          ) : (
            <span className="material-symbols-outlined text-[20px]">send</span>
          )}
        </button>
      </div>

      {/* Micro Status Bar inside Input */}
      <div className="px-3 pb-2 flex items-center justify-between text-[10px] font-mono text-[#8B87A8] border-t border-[#34344E]/30 pt-1.5 select-none">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onOpenUploadModal}
            className="flex items-center gap-1 hover:text-[#39D98A] cursor-pointer transition-colors"
          >
            <span className="material-symbols-outlined text-[13px]">dataset</span>
            <span>RAG: {indexedBooksCount} bases selecionadas</span>
          </button>
          <span className="hidden sm:inline">•</span>
          <span className="hidden sm:inline">Shift + Enter para quebrar linha</span>
        </div>

        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[#39D98A]"></span>
          <span>Modo Neural T20</span>
        </div>
      </div>
    </div>
  );
};
