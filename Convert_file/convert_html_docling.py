
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("Convert_file\Tormenta20_base.pdf")

# Exporta diretamente o HTML estruturado com reconhecimento de layout e colunas
html_content = result.document.export_to_html()

with open("saida_docling.html", "w", encoding="utf-8") as f:
    f.write(html_content)