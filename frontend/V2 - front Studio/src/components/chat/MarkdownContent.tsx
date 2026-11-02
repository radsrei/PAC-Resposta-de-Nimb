import React, { useState } from 'react';

// Renderizador Markdown leve (sem dependências) para as respostas do Nimb.
// Suporta: blocos de código ```lang, código inline, **negrito**, *itálico*,
// ~~tachado~~, links, títulos (#), listas (-, *, 1.), citações (>) e separadores.
// Todo texto passa pelo React como string, então não há risco de injeção de HTML.

type Block =
  | { type: 'code'; lang: string; content: string }
  | { type: 'heading'; level: number; content: string }
  | { type: 'ul'; items: string[] }
  | { type: 'ol'; start: number; items: string[] }
  | { type: 'quote'; content: string }
  | { type: 'hr' }
  | { type: 'p'; content: string };

const FENCE = /^\s*(```|~~~)\s*([\w+#.-]*)\s*$/;
const HEADING = /^\s*(#{1,6})\s+(.*)$/;
const UL_ITEM = /^\s*[-*+]\s+(.*)$/;
const OL_ITEM = /^\s*(\d+)[.)]\s+(.*)$/;
const QUOTE = /^\s*>\s?(.*)$/;
const HR = /^\s*([-*_])(\s*\1){2,}\s*$/;

function parseBlocks(text: string): Block[] {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const blocks: Block[] = [];
  let i = 0;

  const isBlockStart = (line: string) =>
    FENCE.test(line) || HEADING.test(line) || UL_ITEM.test(line) ||
    OL_ITEM.test(line) || QUOTE.test(line) || HR.test(line);

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i++;
      continue;
    }

    const fence = line.match(FENCE);
    if (fence) {
      const marker = fence[1];
      const body: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(marker)) {
        body.push(lines[i]);
        i++;
      }
      i++; // fecha o bloco (ou fim do texto, caso a resposta venha truncada)
      blocks.push({ type: 'code', lang: fence[2] || '', content: body.join('\n') });
      continue;
    }

    if (HR.test(line)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) {
      blocks.push({ type: 'heading', level: heading[1].length, content: heading[2] });
      i++;
      continue;
    }

    if (UL_ITEM.test(line)) {
      const items: string[] = [];
      while (i < lines.length && UL_ITEM.test(lines[i])) {
        items.push(lines[i].match(UL_ITEM)![1]);
        i++;
      }
      blocks.push({ type: 'ul', items });
      continue;
    }

    const ol = line.match(OL_ITEM);
    if (ol) {
      const items: string[] = [];
      while (i < lines.length && OL_ITEM.test(lines[i])) {
        items.push(lines[i].match(OL_ITEM)![2]);
        i++;
      }
      blocks.push({ type: 'ol', start: Number(ol[1]), items });
      continue;
    }

    if (QUOTE.test(line)) {
      const body: string[] = [];
      while (i < lines.length && QUOTE.test(lines[i])) {
        body.push(lines[i].match(QUOTE)![1]);
        i++;
      }
      blocks.push({ type: 'quote', content: body.join('\n') });
      continue;
    }

    const body: string[] = [];
    while (i < lines.length && lines[i].trim() && !isBlockStart(lines[i])) {
      body.push(lines[i]);
      i++;
    }
    blocks.push({ type: 'p', content: body.join('\n') });
  }

  return blocks;
}

// Ordem importa: código inline primeiro para não formatar o que está dentro dele.
const INLINE =
  /(`+)([\s\S]+?)\1|\*\*([\s\S]+?)\*\*|__([\s\S]+?)__|~~([\s\S]+?)~~|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])|(?<![\w_])_(?!\s)([^_\n]+?)_(?![\w_])/g;

function renderInline(text: string, keyPrefix = 'i'): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let n = 0;

  for (const m of text.matchAll(INLINE)) {
    const idx = m.index ?? 0;
    if (idx > last) nodes.push(text.slice(last, idx));
    const key = `${keyPrefix}-${n++}`;

    if (m[2] !== undefined) {
      nodes.push(
        <code
          key={key}
          className="px-1.5 py-0.5 rounded-md bg-[#0A0A10] border border-[#34344E] text-[#39D98A] text-[0.85em] font-mono break-words"
        >
          {m[2].trim()}
        </code>
      );
    } else if (m[3] !== undefined || m[4] !== undefined) {
      nodes.push(
        <strong key={key} className="font-semibold text-white">
          {renderInline(m[3] ?? m[4], key)}
        </strong>
      );
    } else if (m[5] !== undefined) {
      nodes.push(
        <del key={key} className="text-[#8B87A8]">
          {renderInline(m[5], key)}
        </del>
      );
    } else if (m[6] !== undefined) {
      nodes.push(
        <a
          key={key}
          href={m[7]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-[#d8b9ff] underline underline-offset-2 hover:text-[#39D98A] transition-colors"
        >
          {renderInline(m[6], key)}
        </a>
      );
    } else if (m[8] !== undefined || m[9] !== undefined) {
      nodes.push(
        <em key={key} className="italic text-[#E4DCF7]">
          {renderInline(m[8] ?? m[9], key)}
        </em>
      );
    }
    last = idx + m[0].length;
  }

  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

// Quebras de linha simples dentro de um parágrafo viram <br />.
function renderLines(text: string, keyPrefix: string): React.ReactNode[] {
  return text.split('\n').flatMap((line, idx, arr) => {
    const parts = renderInline(line, `${keyPrefix}-${idx}`);
    return idx < arr.length - 1 ? [...parts, <br key={`${keyPrefix}-br-${idx}`} />] : parts;
  });
}

const CodeBlock: React.FC<{ lang: string; content: string }> = ({ lang, content }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="rounded-xl border border-[#34344E] bg-[#0A0A10] overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-[#34344E]/70 bg-[#13131F] font-mono text-[10px] uppercase tracking-wider">
        <span className="text-[#8B87A8]">{lang || 'código'}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-[#8B87A8] hover:text-[#39D98A] transition-colors cursor-pointer"
        >
          <span className="material-symbols-outlined text-[13px]">
            {copied ? 'check' : 'content_copy'}
          </span>
          <span>{copied ? 'Copiado!' : 'Copiar'}</span>
        </button>
      </div>
      <pre className="custom-scrollbar overflow-x-auto p-3 text-[12.5px] leading-relaxed text-[#E4DCF7] font-mono">
        <code>{content}</code>
      </pre>
    </div>
  );
};

const HEADING_CLASSES: Record<number, string> = {
  1: 'text-lg',
  2: 'text-base',
  3: 'text-[15px]',
};

export const MarkdownContent: React.FC<{ text: string }> = ({ text }) => {
  const blocks = parseBlocks(text);

  return (
    <div className="space-y-3 leading-relaxed break-words min-w-0">
      {blocks.map((block, b) => {
        const key = `b-${b}`;
        switch (block.type) {
          case 'code':
            return <CodeBlock key={key} lang={block.lang} content={block.content} />;
          case 'heading':
            return (
              <div
                key={key}
                role="heading"
                aria-level={block.level}
                className={`font-semibold text-[#d8b9ff] ${HEADING_CLASSES[block.level] ?? 'text-sm'}`}
              >
                {renderInline(block.content, key)}
              </div>
            );
          case 'ul':
            return (
              <ul key={key} className="list-disc pl-5 space-y-1 marker:text-[#A259FF]">
                {block.items.map((item, idx) => (
                  <li key={idx}>{renderInline(item, `${key}-${idx}`)}</li>
                ))}
              </ul>
            );
          case 'ol':
            return (
              <ol
                key={key}
                start={block.start}
                className="list-decimal pl-5 space-y-1 marker:text-[#A259FF] marker:font-mono"
              >
                {block.items.map((item, idx) => (
                  <li key={idx}>{renderInline(item, `${key}-${idx}`)}</li>
                ))}
              </ol>
            );
          case 'quote':
            return (
              <blockquote
                key={key}
                className="border-l-2 border-[#A259FF]/60 pl-3 italic text-[#C9C3E0]"
              >
                {renderLines(block.content, key)}
              </blockquote>
            );
          case 'hr':
            return <hr key={key} className="border-[#34344E]/70" />;
          default:
            return <p key={key}>{renderLines(block.content, key)}</p>;
        }
      })}
    </div>
  );
};
