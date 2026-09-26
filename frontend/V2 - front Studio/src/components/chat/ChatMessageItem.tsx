import React, { useState } from 'react';
import { ChatMessage } from '../../types';

interface ChatMessageItemProps {
  message: ChatMessage;
  onReroll?: (query: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  onReroll,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.sender === 'user';

  const handleCopy = () => {
    const textToCopy = `${message.text}\n${message.quote ? `"${message.quote}"\n` : ''}${
      message.rollTable ? `${message.rollTable.title}: ${message.rollTable.description}` : ''
    }`;
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  if (isUser) {
    return (
      <div className="flex items-start gap-3.5 max-w-[92%] md:max-w-[80%] self-end flex-row-reverse animate-fadeIn">
        {/* User Avatar */}
        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-[#39D98A] to-green-600 flex items-center justify-center flex-shrink-0 font-mono font-bold text-xs text-black shadow-[0_0_10px_rgba(57,217,138,0.3)]">
          EU
        </div>

        <div className="space-y-1">
          <div className="bg-[#222236]/90 border border-[rgba(57,217,138,0.45)] rounded-2xl rounded-tr-sm p-4 text-sm leading-relaxed text-[#F0EEF8] shadow-lg">
            <div className="flex items-center justify-end gap-2 mb-1.5 pb-1 border-b border-[rgba(57,217,138,0.2)] font-mono text-[11px]">
              <span className="text-[#39D98A] font-semibold">OPERADOR</span>
              <span className="text-[#8B87A8]">CONSULTA RAG</span>
            </div>
            <p className="whitespace-pre-wrap">{message.text}</p>
          </div>
          <div className="font-mono text-[10px] text-[#8B87A8] pr-1 text-right">
            VOCÊ // {message.timestamp}
          </div>
        </div>
      </div>
    );
  }

  // Nimb AI Message
  return (
    <div className="flex items-start gap-3.5 max-w-[95%] md:max-w-[85%] animate-fadeIn">
      {/* Nimb Avatar */}
      <div className="w-9 h-9 rounded-xl bg-[#13131F] border border-[#A259FF]/50 flex items-center justify-center flex-shrink-0 shadow-[0_0_10px_rgba(162,89,255,0.25)] overflow-hidden">
        <img
          alt="Nimb Avatar"
          referrerPolicy="no-referrer"
          className="w-full h-full object-cover"
          src="https://lh3.googleusercontent.com/aida/AEtjO1VeZBenvo1EbBBHx1FCf1uEDMzj2vDFk-dsyMejBABVcZInwDymH5IfVK8E8VvWse6MmYhip_RjWrR87W_Dka3BxvnTXRfnIoXv16FZpPwGRfcY9UfwbIlgMTKEwOwZp2-4qtEM7vqAzLb_sexGZbohFocz7yo6EyFICdgMUXbnIJV4Nagsih0WZUnDeK60xI03S0lSg68d1qhmwWt2u5kUvh_fWVobKAkLJxhS1zN4-3p5ruEYIDpebZgRiHQC6ShBUloIEoz58w"
          onError={(e) => {
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
      </div>

      <div className="space-y-2 flex-1">
        <div className="bg-[#181827]/95 border border-[rgba(162,89,255,0.25)] rounded-2xl rounded-tl-sm p-4 text-sm leading-relaxed text-[#F0EEF8] shadow-xl space-y-3">
          {/* Header syntax or RAG citation tag bar */}
          {message.ragMetadata ? (
            <div className="flex flex-wrap items-center gap-2 pb-2 border-b border-[#34344E]/60 font-mono text-[10px]">
              <span className="px-2 py-0.5 rounded bg-[#39D98A]/10 border border-[#39D98A]/30 text-[#39D98A] flex items-center gap-1 font-semibold">
                <span className="material-symbols-outlined text-[12px]">verified</span>
                Fonte RAG: {message.ragMetadata.bookTitle}
                {message.ragMetadata.page ? ` pág. ${message.ragMetadata.page}` : ''}
              </span>
              <span className="text-[#8B87A8]">
                Similaridade: {message.ragMetadata.similarity}
              </span>
              <span className="text-[#d8b9ff] font-mono ml-auto">
                Caos Atual: {message.ragMetadata.chaosApplied}%
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 mb-2 pb-1.5 border-b border-[#34344E]/50 font-mono text-[11px]">
              <span className="text-[#d8b9ff] font-semibold">NIMB [CONSCIÊNCIA ARTIFICIAL]</span>
              <span className="text-[#8B87A8]">{message.syntaxTag || '#sintaxe-01'}</span>
            </div>
          )}

          <p className="whitespace-pre-wrap leading-relaxed">{message.text}</p>

          {/* Roll table / stylized quote block */}
          {message.rollTable && (
            <div className="p-3.5 rounded-xl bg-[#A259FF]/10 border-2 border-[#39D98A]/70 relative">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-mono text-xs uppercase font-bold text-[#39D98A] flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-sm">casino</span>
                  {message.rollTable.title}
                </span>
                <span className="font-mono text-[10px] text-[#8B87A8]">
                  {message.rollTable.diceRoll}
                </span>
              </div>
              <p className="text-xs text-[#F0EEF8] leading-relaxed">
                {message.rollTable.description}
              </p>
            </div>
          )}

          {/* Action buttons (Copiar, Gerar outra variante) */}
          {message.ragMetadata && (
            <div className="flex items-center gap-2 text-[11px] font-mono text-[#8B87A8] pt-1">
              <button
                onClick={handleCopy}
                className="hover:text-[#39D98A] flex items-center gap-1 transition-colors cursor-pointer"
              >
                <span className="material-symbols-outlined text-[14px]">
                  {copied ? 'check' : 'content_copy'}
                </span>
                <span>{copied ? 'Copiado!' : 'Copiar'}</span>
              </button>
              <span>•</span>
              {onReroll && (
                <button
                  onClick={() => onReroll(message.text)}
                  className="hover:text-[#d8b9ff] flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <span className="material-symbols-outlined text-[14px]">refresh</span>
                  <span>Gerar Outra Variante</span>
                </button>
              )}
            </div>
          )}
        </div>

        <div className="font-mono text-[10px] text-[#8B87A8] pl-1">
          NIMB // {message.timestamp}
        </div>
      </div>
    </div>
  );
};
