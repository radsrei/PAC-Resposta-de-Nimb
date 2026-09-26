import React, { useState, useRef } from 'react';
import { IndexedBook } from '../../types';
import { ragApiService } from '../../services/ragApi';

interface PdfUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  books: IndexedBook[];
  onAddBook: (book: IndexedBook) => void;
  onRemoveBook: (id: string) => void;
}

export const PdfUploadModal: React.FC<PdfUploadModalProps> = ({
  isOpen,
  onClose,
  books,
  onAddBook,
  onRemoveBook,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [chunkSize, setChunkSize] = useState<number>(1024);
  const [model, setModel] = useState('Nimb-Vector-Embedding-v3');
  const [entropy, setEntropy] = useState<number>(0.75);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      alert('Por favor, selecione um arquivo no formato PDF (.pdf).');
      return;
    }

    setIsProcessing(true);
    setUploadFeedback(`Vetorizando "${file.name}"...`);

    try {
      const newBook = await ragApiService.uploadGrimorio(file, {
        chunkSize,
        model,
        entropy,
      });
      onAddBook(newBook);
      setUploadFeedback(`Grimório "${file.name}" indexado com sucesso no cluster RAG!`);
      setTimeout(() => {
        setIsProcessing(false);
        setUploadFeedback(null);
      }, 1500);
    } catch {
      setIsProcessing(false);
      setUploadFeedback('Erro ao vetorizar arquivo.');
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  return (
    <div
      className="fixed inset-0 bg-[#0A0A10]/80 backdrop-blur-md z-50 flex items-center justify-center p-4 md:p-6 overflow-y-auto animate-fadeIn"
      onClick={(e) => {
        if (e.target === e.currentTarget && !isProcessing) {
          onClose();
        }
      }}
    >
      <div className="relative w-full max-w-4xl bg-[#1B1B22] border border-[rgba(162,89,255,0.3)] rounded-2xl shadow-2xl overflow-hidden flex flex-col gap-6 p-6 md:p-8 my-auto max-h-[90vh] overflow-y-auto custom-scrollbar">
        {/* Glow ambient effects */}
        <div className="absolute -top-32 -right-32 w-80 h-80 bg-[#A259FF]/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute -bottom-32 -left-32 w-80 h-80 bg-[#39D98A]/10 rounded-full blur-3xl pointer-events-none"></div>

        {/* Modal Header */}
        <div className="flex flex-col gap-2 relative z-10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#1F1F26] border border-[#39D98A]/30 flex items-center justify-center shadow-md">
                <span className="material-symbols-outlined text-[#39D98A] text-2xl">
                  auto_stories
                </span>
              </div>
              <div className="flex flex-col">
                <h2 className="text-lg md:text-xl font-bold text-[#F0EEF8] tracking-tight uppercase">
                  CARREGAR GRIMÓRIO // INGESTÃO RAG VETORIAL
                </h2>
                <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                  MÓDULO DE PIPELINE SEMÂNTICO V2.4 // TORMENTA20 & D20 REPOSITORIES
                </span>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <span className="hidden sm:flex px-3 py-1 bg-[#222236] rounded-full font-mono text-[10px] uppercase text-[#39D98A] tracking-wider items-center gap-1.5 border border-[#39D98A]/25">
                <span className="w-1.5 h-1.5 rounded-full bg-[#39D98A] animate-ping"></span>
                Upload de Livros (.PDF)
              </span>

              <button
                type="button"
                onClick={onClose}
                disabled={isProcessing}
                className="w-8 h-8 rounded-lg bg-[#181827] hover:bg-[#222236] border border-[#34344E] flex items-center justify-center text-[#8B87A8] hover:text-[#F0EEF8] transition-colors cursor-pointer"
                title="Fechar"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            </div>
          </div>

          <div className="w-full flex items-center gap-1 mt-1">
            <div className="h-0.5 w-16 bg-[#A259FF]"></div>
            <div className="h-0.5 w-8 bg-[#39D98A]"></div>
            <div className="h-0.5 flex-1 bg-[#34343C]"></div>
          </div>
        </div>

        {/* Drag and Drop Box */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`relative group cursor-pointer rounded-2xl bg-[#181827] p-6 md:p-8 flex flex-col items-center justify-center gap-3 border-2 border-dashed transition-all duration-300 shadow-md ${
            isDragging
              ? 'border-[#39D98A] bg-[#222236]/90 scale-[1.01]'
              : 'border-[#34344E] hover:border-[#A259FF]/60 hover:bg-[#1F1F26]'
          }`}
        >
          <div className="w-16 h-16 rounded-2xl bg-[#222236] border border-[#34344E] flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
            <span className="material-symbols-outlined text-[#39D98A] text-4xl group-hover:text-[#d8b9ff] transition-colors">
              cloud_upload
            </span>
          </div>

          <div className="flex flex-col items-center text-center gap-1">
            <p className="text-base md:text-lg font-bold text-[#F0EEF8]">
              Arraste tomos, manuais ou suplementos em PDF
            </p>
            <span className="font-mono text-xs text-[#8B87A8]">
              Tamanho máximo suportado: 150MB por grimório • Text layer nativo ou OCR acelerado
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-3 mt-2">
            <button
              type="button"
              className="px-5 py-2.5 rounded-xl bg-[#2A2931] hover:bg-[#34343C] text-[#F0EEF8] font-mono text-xs uppercase tracking-wider transition-all flex items-center gap-2 shadow-sm border border-[#34344E]"
            >
              <span className="material-symbols-outlined text-base text-[#d8b9ff]">
                folder_open
              </span>
              <span>Selecionar Arquivos do Disco</span>
            </button>
            <span className="font-mono text-[11px] text-[#8B87A8] uppercase">
              // SUPORTA .PDF NATIVO
            </span>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {/* Feedback message if any */}
        {uploadFeedback && (
          <div className="px-4 py-2 rounded-xl bg-[#39D98A]/15 border border-[#39D98A]/40 font-mono text-xs text-[#39D98A] flex items-center gap-2 animate-fadeIn">
            <span className="material-symbols-outlined text-[16px] animate-spin">
              autorenew
            </span>
            <span>{uploadFeedback}</span>
          </div>
        )}

        {/* Queue / Current Repository Section */}
        <div className="flex flex-col gap-3 relative z-10">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase text-[#8B87A8] tracking-wider flex items-center gap-2 font-semibold">
              <span className="material-symbols-outlined text-base text-[#39D98A]">
                memory
              </span>
              FILA DE INDEXAÇÃO // REPOSITÓRIO ATUAL
            </span>
            <span className="font-mono text-xs text-[#d8b9ff]">
              {books.length} TOMOS CARREGADOS
            </span>
          </div>

          <div className="flex flex-col gap-2.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
            {books.map((b) => (
              <div
                key={b.id}
                className="bg-[#181827] p-3.5 rounded-xl flex flex-col gap-2.5 border border-[#34344E] hover:border-[#39D98A]/30 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-[#222236] border border-[#34344E] flex items-center justify-center text-[#39D98A]">
                      <span className="material-symbols-outlined text-xl">picture_as_pdf</span>
                    </div>
                    <div>
                      <span className="text-xs md:text-sm text-[#F0EEF8] font-bold leading-none block truncate max-w-[280px] sm:max-w-md">
                        {b.fileName}
                      </span>
                      <div className="flex items-center gap-2 mt-1 font-mono text-[10px] text-[#8B87A8]">
                        <span>{b.size}</span>
                        <span>•</span>
                        <span className="text-[#39D98A] font-bold tabular-nums">
                          {b.chunks.toLocaleString()} Chunks Vetorizados
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 bg-[#222236] text-[#39D98A] font-mono text-[10px] rounded border border-[#39D98A]/30 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[13px]">
                        check_circle
                      </span>
                      {b.progress}%
                    </span>

                    <button
                      type="button"
                      onClick={() => onRemoveBook(b.id)}
                      className="text-[#8B87A8] hover:text-red-400 transition-colors cursor-pointer"
                      title="Remover Tomo"
                    >
                      <span className="material-symbols-outlined text-lg">delete</span>
                    </button>
                  </div>
                </div>

                <div className="w-full h-1.5 bg-[#222236] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#A259FF] to-[#39D98A] rounded-full"
                    style={{ width: `${b.progress}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chunking & Entropy Parameters */}
        <div className="bg-[#181827] p-5 rounded-2xl border border-[#34344E] flex flex-col gap-4 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase text-[#8B87A8] tracking-wider flex items-center gap-2 font-semibold">
              <span className="material-symbols-outlined text-base text-[#d8b9ff]">
                tune
              </span>
              PARÂMETROS DE CHUNKING & ENTROPIA RAG
            </span>
            <span className="font-mono text-[10px] text-[#8B87A8] uppercase">
              // INGESTION_CONFIG_V3
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Chunk size */}
            <div className="flex flex-col gap-2">
              <label className="font-mono text-[11px] uppercase text-[#cec2d7]">
                TAMANHO DO CHUNK (TOKENS)
              </label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setChunkSize(512)}
                  className={`flex-1 py-2 rounded-lg font-mono text-xs transition-colors cursor-pointer ${
                    chunkSize === 512
                      ? 'bg-[#2A2931] border border-[#39D98A] text-[#39D98A] font-bold shadow-sm'
                      : 'bg-[#222236] text-[#F0EEF8] hover:bg-[#2A2931]'
                  }`}
                >
                  512 tk
                </button>
                <button
                  type="button"
                  onClick={() => setChunkSize(1024)}
                  className={`flex-1 py-2 rounded-lg font-mono text-xs transition-colors cursor-pointer ${
                    chunkSize === 1024
                      ? 'bg-[#2A2931] border border-[#39D98A] text-[#39D98A] font-bold shadow-sm'
                      : 'bg-[#222236] text-[#F0EEF8] hover:bg-[#2A2931]'
                  }`}
                >
                  1024 tk
                </button>
              </div>
            </div>

            {/* Embedding model */}
            <div className="flex flex-col gap-2">
              <label className="font-mono text-[11px] uppercase text-[#cec2d7]">
                MODELO DE EMBEDDINGS
              </label>
              <div className="relative">
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full py-2 px-3 rounded-lg bg-[#222236] text-[#F0EEF8] font-mono text-xs appearance-none cursor-pointer focus:outline-none focus:border-[#39D98A] border border-[#34344E]"
                >
                  <option value="Nimb-Vector-Embedding-v3">Nimb-Vector-Embedding-v3</option>
                  <option value="Arton-Neural-Ada-002">Arton-Neural-Ada-002</option>
                  <option value="Cohere-Multilingual-v3">Cohere-Multilingual-v3</option>
                </select>
                <span className="material-symbols-outlined absolute right-2.5 top-2.5 text-[#8B87A8] pointer-events-none text-base">
                  expand_more
                </span>
              </div>
            </div>

            {/* Chaos Level / Entropy */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <label className="font-mono text-[11px] uppercase text-[#cec2d7]">
                  NÍVEL DE ENTROPIA / CAOS
                </label>
                <span className="font-mono text-xs text-[#ffb95d] font-bold">
                  {entropy.toFixed(2)} ({entropy > 0.6 ? 'NIMB' : 'ORDEM'})
                </span>
              </div>
              <div className="flex items-center gap-3 pt-1">
                <span className="font-mono text-[10px] text-[#8B87A8]">ORDEM</span>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={entropy}
                  onChange={(e) => setEntropy(parseFloat(e.target.value))}
                  className="chaos-slider w-full accent-[#39D98A] h-1.5 bg-[#222236] rounded-lg cursor-pointer"
                />
                <span className="font-mono text-[10px] text-[#ffb95d]">CAOS</span>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Actions Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-[#34344E]/40">
          <div className="flex items-center gap-2 text-[#8B87A8] font-mono text-[11px]">
            <span className="material-symbols-outlined text-base text-[#39D98A]">
              security
            </span>
            <span>PARIDADE SEMÂNTICA VERIFICADA • SHA-256 AUTOMÁTICO</span>
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              type="button"
              onClick={onClose}
              disabled={isProcessing}
              className="flex-1 sm:flex-initial px-5 py-2.5 rounded-xl bg-[#181827] hover:bg-[#222236] border border-[#34344E] text-[#cec2d7] hover:text-[#F0EEF8] font-mono text-xs uppercase tracking-wider transition-colors cursor-pointer"
            >
              Concluir
            </button>

            <button
              type="button"
              disabled={isProcessing}
              onClick={() => {
                fileInputRef.current?.click();
              }}
              className="flex-1 sm:flex-initial px-6 py-2.5 rounded-xl bg-gradient-to-r from-[#A259FF] to-[#39D98A] text-[#0D0D14] font-bold text-xs uppercase tracking-wider hover:scale-[1.02] shadow-[0_0_15px_rgba(57,217,138,0.3)] hover:shadow-[0_0_20px_rgba(57,217,138,0.5)] transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <span className="material-symbols-outlined text-lg">bolt</span>
              <span>Subir Novo Livro (.PDF)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
