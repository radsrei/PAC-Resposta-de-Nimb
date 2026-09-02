import html
from collections import Counter
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF


class PDFToSemanticHTML:
    """
    Converte arquivos PDF em HTML semântico estruturado por:
    - h1: Capítulos principais
    - h2: Subcapítulos
    - h3: Seções / Subtópicos
    - p:  Parágrafos de texto contínuo
    """

    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.body_font_size = self._detect_body_font_size()

    def _detect_body_font_size(self) -> float:
        """Identifica a moda estatística do tamanho das fontes (corpo de texto padrão)."""
        sizes: List[float] = []
        for page in self.doc:
            blocks = page.get_text("dict").get("blocks", [])
            for b in blocks:
                if b.get("type") == 0:  # Bloco de texto
                    for line in b.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                sizes.append(round(span["size"], 1))
        
        if not sizes:
            return 10.0
        return Counter(sizes).most_common(1)[0][0]

    def _classify_heading(self, size: float, is_bold: bool) -> Optional[str]:
        """Classifica o elemento hierárquico com base nos limiares tipográficos."""
        # Limiares relativos ao tamanho do corpo do texto
        h1_min = self.body_font_size * 1.55  # Capítulos
        h2_min = self.body_font_size * 1.25  # Subcapítulos
        h3_min = self.body_font_size * 1.10  # Seções

        if size >= h1_min:
            return "h1"
        elif size >= h2_min or (size >= h3_min and is_bold):
            return "h2"
        elif size >= h3_min or (is_bold and size >= self.body_font_size):
            return "h3"
        return None

    def convert(self) -> str:
        """Executa a extração do PDF e gera o código HTML estruturado."""
        html_output = [
            '<!DOCTYPE html>',
            '<html lang="pt-BR">',
            '<head>',
            '  <meta charset="utf-8">',
            '  <title>Documento Convertido</title>',
            '</head>',
            '<body>'
        ]

        for page_num in range(len(self.doc)):
            page = self.doc[page_num]
            page_index = page_num + 1
            blocks = page.get_text("dict").get("blocks", [])

            current_p_buffer: List[str] = []

            def flush_p():
                """Descarrega o buffer de parágrafo acumulado."""
                nonlocal current_p_buffer
                if current_p_buffer:
                    paragraph_text = " ".join(current_p_buffer).strip()
                    if paragraph_text:
                        escaped = html.escape(paragraph_text)
                        html_output.append(f'  <p data-page="{page_index}">{escaped}</p>')
                    current_p_buffer = []

            for b in blocks:
                if b.get("type") != 0:  # Ignora imagens ou metadados não-textuais
                    continue

                for line in b.get("lines", []):
                    # Agrupa textos da mesma linha
                    line_text = " ".join(
                        s["text"].strip() for s in line["spans"] if s["text"].strip()
                    ).strip()

                    if not line_text:
                        continue

                    # Analisa o primeiro span significativo da linha
                    first_span = next(s for s in line["spans"] if s["text"].strip())
                    size = round(first_span["size"], 1)
                    font_name = first_span.get("font", "").lower()
                    is_bold = bool(first_span.get("flags", 0) & 2 or "bold" in font_name or "black" in font_name)

                    heading_tag = self._classify_heading(size, is_bold)

                    if heading_tag:
                        # Finaliza qualquer parágrafo aberto antes de abrir um novo título
                        flush_p()
                        escaped_title = html.escape(line_text)
                        html_output.append(f'  <{heading_tag} data-page="{page_index}">{escaped_title}</{heading_tag}>')
                    else:
                        # Concatena texto no parágrafo corrente
                        current_p_buffer.append(line_text)

            # Esvazia o buffer de parágrafos ao mudar de página
            flush_p()

        html_output.extend(['</body>', '</html>'])
        return "\n".join(html_output)

    def save_to_file(self, output_path: str) -> None:
        """Converte e salva o conteúdo diretamente em um arquivo .html."""
        html_content = self.convert()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)


# ==============================================================================
# EXEMPLO DE USO
# ==============================================================================
if __name__ == "__main__":
    caminho_pdf = "livro_regras.pdf"
    caminho_saida = "documento_estruturado.html"

    # Inicializa e processa
    conversor = PDFToSemanticHTML(caminho_pdf)
    conversor.save_to_file(caminho_saida)

    print(f"HTML gerado com sucesso em: {caminho_saida}")