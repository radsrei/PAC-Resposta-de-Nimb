import React, { useState, useRef } from 'react';
import { BookValidationResult, CatalogBook, IndexedBook } from '../../types';
import { ragApiService } from '../../services/ragApi';

// Igual a BOOK_UPLOAD_MAX_MB do backend. O plano grátis do Cloudflare recusa
// requisições acima de 100 MB.
const MAX_UPLOAD_MB = 95;

interface PdfUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  books: IndexedBook[];
  onBookUnlocked: (book: CatalogBook) => void;
}

/**
 * Upload de livro: o PDF é comparado com o catálogo de livros permitidos
 * (tamanho, páginas, metadados e frases de controle). Se for reconhecido, o
 * banco vetorial do livro é liberado para o usuário. O arquivo é descartado.
 */
export const PdfUploadModal: React.FC<PdfUploadModalProps> = ({
  isOpen,
  onClose,
  books,
  onBookUnlocked,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadFeedback, setUploadFeedback] = useState<string | null>(null);
  const [result, setResult] = useState<BookValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    if (fileInputRef.current) fileInputRef.current.value = '';

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Selecione um arquivo no formato PDF (.pdf).');
      return;
    }
    // Mesmo limite do backend (BOOK_UPLOAD_MAX_MB): acima dele o proxy corta a
    // conexão e o navegador mostraria só um erro de rede
    if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`Arquivo maior que o limite de ${MAX_UPLOAD_MB} MB.`);
      return;
    }

    setIsProcessing(true);
    setResult(null);
    setError(null);
    setUploadFeedback(`Validando "${file.name}"...`);
    try {
      const validation = await ragApiService.validateBook(file);
      setResult(validation);
      if (validation.accepted && validation.book) onBookUnlocked(validation.book);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsProcessing(false);
      setUploadFeedback(null);
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
                  CARREGAR GRIMÓRIO // VALIDAÇÃO DE LIVRO
                </h2>
                <span className="font-mono text-[11px] text-[#8B87A8] tracking-wider">
                  ENVIE O PDF DO SEU LIVRO PARA LIBERAR O BANCO VETORIAL DELE
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
              Tamanho máximo: {MAX_UPLOAD_MB} MB • O arquivo é analisado e descartado, não fica guardado
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
          <div className="px-4 py-2 rounded-xl bg-[#A259FF]/15 border border-[#A259FF]/40 font-mono text-xs text-[#d8b9ff] flex items-center gap-2 animate-fadeIn">
            <span className="material-symbols-outlined text-[16px] animate-spin">
              autorenew
            </span>
            <span>{uploadFeedback}</span>
          </div>
        )}

        {error && (
          <div role="alert" className="px-4 py-2.5 rounded-xl bg-red-500/10 border border-red-500/40 text-red-300 text-xs flex items-start gap-2">
            <span className="material-symbols-outlined text-[16px]">error</span>
            <span>{error}</span>
          </div>
        )}

        {/* Resultado da validação */}
        {result && (
          <div
            className={`p-4 rounded-xl border flex flex-col gap-3 animate-fadeIn ${
              result.accepted
                ? 'bg-[#39D98A]/10 border-[#39D98A]/40'
                : 'bg-red-500/10 border-red-500/40'
            }`}
          >
            <div className="flex items-center justify-between gap-3">
              <span
                className={`flex items-center gap-2 text-sm font-bold ${
                  result.accepted ? 'text-[#39D98A]' : 'text-red-300'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">
                  {result.accepted ? 'verified' : 'block'}
                </span>
                {result.message}
              </span>
              <span className="font-mono text-[11px] text-[#cec2d7] tabular-nums">
                pontuação {Math.round(result.score * 100)}%
              </span>
            </div>
            {result.checks.length > 0 && (
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 font-mono text-[11px]">
                {result.checks.map((check) => (
                  <li key={check.name} className="flex items-center gap-1.5 text-[#cec2d7]">
                    <span
                      className={`material-symbols-outlined text-[14px] ${
                        check.passed ? 'text-[#39D98A]' : 'text-red-300'
                      }`}
                    >
                      {check.passed ? 'check_circle' : 'cancel'}
                    </span>
                    {check.label}
                  </li>
                ))}
              </ul>
            )}
            {result.accepted && result.book && !result.book.vectorReady && (
              <p className="font-mono text-[11px] text-amber-300">
                O banco vetorial deste livro ainda está em construção. As consultas usarão o livro assim que ele ficar pronto.
              </p>
            )}
          </div>
        )}

        {/* Livros liberados para o usuário */}
        <div className="flex flex-col gap-3 relative z-10">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs uppercase text-[#8B87A8] tracking-wider flex items-center gap-2 font-semibold">
              <span className="material-symbols-outlined text-base text-[#39D98A]">
                memory
              </span>
              LIVROS LIBERADOS // SEU ACERVO
            </span>
            <span className="font-mono text-xs text-[#d8b9ff]">
              {books.length} {books.length === 1 ? 'LIVRO' : 'LIVROS'}
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
                          {b.status === 'indexed'
                            ? `${b.chunks.toLocaleString()} trechos no banco vetorial`
                            : 'banco vetorial em construção'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="px-2.5 py-1 bg-[#222236] text-[#39D98A] font-mono text-[10px] rounded border border-[#39D98A]/30 flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-[13px]">
                        check_circle
                      </span>
                      {b.status === 'indexed' ? 'liberado' : 'aguardando banco'}
                    </span>
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

        {/* Modal Actions Footer */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t border-[#34344E]/40">
          <div className="flex items-center gap-2 text-[#8B87A8] font-mono text-[11px]">
            <span className="material-symbols-outlined text-base text-[#39D98A]">
              security
            </span>
            <span>VALIDAÇÃO POR IMPRESSÃO DIGITAL • ARQUIVO DESCARTADO APÓS A ANÁLISE</span>
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
              <span>Validar livro (.PDF)</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
