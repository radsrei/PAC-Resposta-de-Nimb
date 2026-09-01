# from markitdown import MarkItDown

# # Inicializa a ferramenta
# md = MarkItDown()

# # Caminhos dos arquivos
# arquivo_pdf = "Tormenta20_base.pdf"
# arquivo_md = "saida.md"

# # Realiza a conversão
# resultado = md.convert(arquivo_pdf)

# # Exporta e salva o conteúdo em um arquivo .md
# with open(arquivo_md, "w", encoding="utf-8") as f:
#     f.write(resultado.text_content)

# print(f"Arquivo exportado com sucesso para: {arquivo_md}")


###-------###

from markitdown import MarkItDown
from langchain_text_splitters import MarkdownHeaderTextSplitter

# 1. Inicializa o MarkItDown e converte o PDF
md_tool = MarkItDown()
arquivo_pdf = "Tormenta20_base.pdf"

print("Convertendo PDF para Markdown...")
resultado = md_tool.convert(arquivo_pdf)
texto_markdown = resultado.text_content

# 2. Definir a hierarquia de cabeçalhos para o fatiamento (Chunking)
# Isso ensinará o código a ler as seções e subseções do Markdown
headers_to_split_on = [
    ("#", "Capitulo"),
    ("##", "Secao"),
    ("###", "Subsecao"),
]

# Inicializa o divisor de texto
markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on,
    strip_headers=False # Mantém o cabeçalho no texto do chunk
)

# 3. Fatiar o texto com base nas seções
chunks_estruturados = markdown_splitter.split_text(texto_markdown)

# 4. Tratar trechos específicos baseados na caracterização do capítulo
documentos_prontos_para_vetor = []

for chunk in chunks_estruturados:
    # Captura em qual capítulo/seção esse trecho está
    capitulo = chunk.metadata.get("Capitulo", "Geral")
    secao = chunk.metadata.get("Secao", "Geral")
    
    # --- LÓGICA DE CARACTERIZAÇÃO ESPECÍFICA ---
    
    if "Raças" in capitulo or "Classes" in capitulo:
        # Adiciona metadados ou tags para facilitar a busca do RAG depois
        chunk.metadata["categoria"] = "Criacao_de_Personagem"
        chunk.metadata["prioridade_busca"] = "Alta"
        
    elif "Equipamento" in capitulo:
        chunk.metadata["categoria"] = "Itens_e_Economia"
        # Pode-se aplicar uma limpeza extra no texto se as tabelas de armas estiverem complexas
        
    elif "Magias" in capitulo:
        chunk.metadata["categoria"] = "Grimorio"
        # Exemplo: Adicionar um prefixo ao texto do chunk para dar mais contexto ao LLM
        chunk.page_content = f"[Contexto: Regras de Magia Tormenta20]\n{chunk.page_content}"
        
    elif "Ameaças" in capitulo or "Monstros" in capitulo:
        chunk.metadata["categoria"] = "Bestiario"
        
    # Adiciona o chunk tratado à lista final
    documentos_prontos_para_vetor.append(chunk)

# (Opcional) Salvar para conferência visual
arquivo_md = "saida_estruturada.md"
with open(arquivo_md, "w", encoding="utf-8") as f:
    for doc in documentos_prontos_para_vetor:
        f.write(f"--- METADADOS: {doc.metadata} ---\n")
        f.write(f"{doc.page_content}\n\n")

print(f"Processamento concluído. {len(documentos_prontos_para_vetor)} chunks gerados e classificados.")