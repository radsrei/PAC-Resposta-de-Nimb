"""
Entrada no Prompt:
Gere um programa python, para realizar o processo de chunks e embedins, para um RAG.
Dentro desse processo delimite cada uma das funções com explicações e contexto, para ferramentas externas utilize langchain e simule consultas usando 3 canais de LLM's Gemini, GPT e Deepseek.

Dentro do programa, faça um bloco para leitura e gravação em diferentes bancos de dados, voltados para diferentes capítulos e subcapítulos, sempre gravando a página de referencia para busca e demonstração de fonte.
"""

"""
RAG - Pipeline de Chunking, Embeddings, Persistência e Consulta

Objetivo
--------
Este programa demonstra uma arquitetura de RAG organizada para:

1. Ler documentos PDF.
2. Preservar a página de origem.
3. Identificar capítulo e subcapítulo.
4. Dividir o conteúdo em chunks.
5. Gerar embeddings.
6. Armazenar os vetores em bancos separados por capítulo/subcapítulo.
7. Manter um catálogo central dos bancos disponíveis.
8. Recuperar os chunks semanticamente relevantes.
9. Enviar o contexto recuperado para três canais simulados:
       - Gemini
       - GPT
       - DeepSeek
10. Demonstrar as fontes utilizadas na resposta.

A arquitetura utiliza LangChain para os principais componentes
do pipeline de RAG.

IMPORTANTE
----------
Os LLMs Gemini, GPT e DeepSeek deste exemplo são simulados.
Não são realizadas chamadas para as APIs externas.

Isso permite desenvolver e testar o pipeline sem necessidade
de três chaves de API.

Posteriormente, os simuladores podem ser substituídos por:

    ChatGoogleGenerativeAI
    ChatOpenAI
    cliente OpenAI-compatible para DeepSeek
"""

from __future__ import annotations

import os
import re
import json
import sqlite3
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Loader de PDF
from langchain_community.document_loaders import PyPDFLoader

# Embeddings
from langchain_huggingface import HuggingFaceEmbeddings

# Banco vetorial
from langchain_chroma import Chroma


# ============================================================
# CONFIGURAÇÕES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DOCUMENTS_DIR = BASE_DIR / "documentos"
VECTOR_DB_DIR = BASE_DIR / "dados_rag"
CATALOG_DB = VECTOR_DB_DIR / "catalogo.sqlite"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

TOP_K = 5


# ============================================================
# MODELOS DE DADOS
# ============================================================

@dataclass
class SourceReference:
    """
    Representa a origem de um determinado chunk.

    A página é fundamental para um RAG confiável porque permite
    apresentar ao usuário de onde a informação foi retirada.
    """

    document_name: str
    document_path: str
    page: int
    chapter: str
    subchapter: str


# ============================================================
# FUNÇÃO 1 - CRIAÇÃO DOS DIRETÓRIOS
# ============================================================

def create_directories() -> None:
    """
    Cria a estrutura básica de diretórios do projeto.

    O banco vetorial ficará separado em diretórios específicos.

    Exemplo:

        dados_rag/
            capitulo_01/
                subcapitulo_01/
                subcapitulo_02/

    Essa separação permite posteriormente distribuir os dados
    entre diferentes bancos, containers ou serviços cloud.
    """

    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FUNÇÃO 2 - CATÁLOGO CENTRAL
# ============================================================

def initialize_catalog() -> None:
    """
    Cria o banco SQLite responsável por catalogar os bancos vetoriais.

    O SQLite não armazena os embeddings.

    Ele funciona como um catálogo administrativo:

        capítulo
        subcapítulo
        caminho do banco vetorial
        quantidade de chunks

    Em uma arquitetura cloud, esse catálogo poderia posteriormente
    ser substituído por PostgreSQL, MySQL, DynamoDB etc.
    """

    connection = sqlite3.connect(CATALOG_DB)

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_databases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chapter TEXT NOT NULL,
            subchapter TEXT NOT NULL,
            database_path TEXT NOT NULL,
            chunks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(chapter, subchapter)
        )
        """
    )

    connection.commit()
    connection.close()


# ============================================================
# FUNÇÃO 3 - NORMALIZAÇÃO DE NOMES
# ============================================================

def normalize_name(value: str) -> str:
    """
    Converte nomes de capítulos/subcapítulos em nomes seguros
    para diretórios.

    Exemplo:

        "1. Introdução Geral"

    torna-se:

        "1_introducao_geral"
    """

    value = value.lower()

    value = re.sub(
        r"[^a-zA-Z0-9À-ÿ\s_-]",
        "",
        value
    )

    value = value.strip()

    value = re.sub(r"\s+", "_", value)

    return value


# ============================================================
# FUNÇÃO 4 - EXTRAÇÃO DE CAPÍTULO
# ============================================================

def detect_chapter(text: str) -> Tuple[str, str]:
    """
    Tenta identificar capítulo e subcapítulo no texto.

    Exemplos reconhecidos:

        CAPÍTULO 1
        CAPÍTULO 01 - INTRODUÇÃO

        1. INTRODUÇÃO
        1.1 OBJETIVOS
        1.2 METODOLOGIA

    Essa função é propositalmente simples.

    Em um projeto real, a identificação pode ser melhorada
    utilizando regras específicas do documento ou um LLM.
    """

    chapter = "sem_capitulo"
    subchapter = "sem_subcapitulo"

    lines = text.splitlines()

    for line in lines:

        line_clean = line.strip()

        # CAPÍTULO 1
        chapter_match = re.match(
            r"^(?:CAP[IÍ]TULO)\s+(\d+)(?:\s*[-:]?\s*(.*))?$",
            line_clean,
            re.IGNORECASE
        )

        if chapter_match:

            number = chapter_match.group(1)
            title = chapter_match.group(2) or ""

            chapter = f"capitulo_{number}"

            if title:
                chapter += f"_{normalize_name(title)}"

            continue

        # 1.1 Título
        subchapter_match = re.match(
            r"^(\d+\.\d+)\s+(.+)$",
            line_clean
        )

        if subchapter_match:

            number = subchapter_match.group(1)
            title = subchapter_match.group(2)

            subchapter = (
                f"subcapitulo_{number.replace('.', '_')}_"
                f"{normalize_name(title)}"
            )

            break

    return chapter, subchapter


# ============================================================
# FUNÇÃO 5 - LEITURA DO PDF
# ============================================================

def load_pdf(pdf_path: Path) -> List[Document]:
    """
    Lê um PDF utilizando PyPDFLoader.

    Cada página é convertida em um objeto Document do LangChain.

    Isso é importante porque o metadata do Document mantém
    a informação de página.

    O objetivo é nunca perder a referência da fonte durante
    o processamento.
    """

    loader = PyPDFLoader(str(pdf_path))

    documents = loader.load()

    for document in documents:

        # PyPDFLoader normalmente utiliza página iniciando em 0.
        original_page = document.metadata.get("page", 0)

        document.metadata["page"] = int(original_page) + 1

        document.metadata["document_name"] = pdf_path.name
        document.metadata["document_path"] = str(pdf_path)

    return documents


# ============================================================
# FUNÇÃO 6 - IDENTIFICAÇÃO DE CAPÍTULO/SUBCAPÍTULO
# ============================================================

def enrich_metadata(documents: List[Document]) -> List[Document]:
    """
    Adiciona informações de capítulo e subcapítulo aos Documents.

    Quando o documento possuir estrutura consistente, podemos
    identificar esses elementos diretamente.

    O estado do capítulo é mantido entre páginas.
    """

    current_chapter = "sem_capitulo"
    current_subchapter = "sem_subcapitulo"

    enriched_documents = []

    for document in documents:

        text = document.page_content

        detected_chapter, detected_subchapter = detect_chapter(text)

        if detected_chapter != "sem_capitulo":
            current_chapter = detected_chapter

        if detected_subchapter != "sem_subcapitulo":
            current_subchapter = detected_subchapter

        document.metadata["chapter"] = current_chapter
        document.metadata["subchapter"] = current_subchapter

        enriched_documents.append(document)

    return enriched_documents


# ============================================================
# FUNÇÃO 7 - CHUNKING
# ============================================================

def split_documents(
    documents: List[Document]
) -> List[Document]:
    """
    Divide os documentos em chunks.

    Parâmetros principais:

        CHUNK_SIZE
            Quantidade aproximada de caracteres.

        CHUNK_OVERLAP
            Quantidade de caracteres repetidos entre chunks.

    O overlap reduz a possibilidade de perder contexto
    entre duas divisões.

    O metadata da página é preservado pelo LangChain.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = splitter.split_documents(documents)

    for index, chunk in enumerate(chunks):

        chunk.metadata["chunk_id"] = (
            f"chunk_{index:06d}"
        )

    return chunks


# ============================================================
# FUNÇÃO 8 - EMBEDDINGS
# ============================================================

def create_embedding_model():
    """
    Cria o modelo de embeddings.

    Neste exemplo utilizamos um modelo Hugging Face local:

        all-MiniLM-L6-v2

    Isso evita depender de uma API paga durante o desenvolvimento.

    O LangChain fornece a interface padronizada para o embedding.

    Posteriormente poderia ser substituído por:

        Google Generative AI Embeddings
        OpenAI Embeddings
        outro modelo hospedado
    """

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={
            "device": "cpu"
        },
        encode_kwargs={
            "normalize_embeddings": True
        }
    )

    return embeddings


# ============================================================
# FUNÇÃO 9 - CRIAÇÃO DO BANCO VETORIAL
# ============================================================

def get_vector_database(
    chapter: str,
    subchapter: str,
    embeddings
) -> Chroma:
    """
    Retorna um banco Chroma específico para determinado
    capítulo/subcapítulo.

    Exemplo:

        dados_rag/
            capitulo_01/
                subcapitulo_01/

    Cada combinação capítulo/subcapítulo possui seu próprio
    armazenamento vetorial.

    Isso permite:

        - isolamento dos dados;
        - recuperação seletiva;
        - manutenção independente;
        - futura distribuição em cloud.
    """

    chapter_safe = normalize_name(chapter)
    subchapter_safe = normalize_name(subchapter)

    database_path = (
        VECTOR_DB_DIR /
        chapter_safe /
        subchapter_safe
    )

    database_path.mkdir(
        parents=True,
        exist_ok=True
    )

    collection_name = (
        f"{chapter_safe}_{subchapter_safe}"
    )

    collection_name = re.sub(
        r"[^a-zA-Z0-9_-]",
        "_",
        collection_name
    )

    collection_name = collection_name[:63]

    vector_db = Chroma(
        collection_name=collection_name,
        persist_directory=str(database_path),
        embedding_function=embeddings
    )

    return vector_db


# ============================================================
# FUNÇÃO 10 - REGISTRO DO BANCO NO CATÁLOGO
# ============================================================

def register_database(
    chapter: str,
    subchapter: str,
    database_path: Path,
    chunks: int
) -> None:
    """
    Registra no catálogo SQLite a existência de um banco vetorial.
    """

    connection = sqlite3.connect(CATALOG_DB)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO vector_databases
        (
            chapter,
            subchapter,
            database_path,
            chunks
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(chapter, subchapter)
        DO UPDATE SET
            database_path = excluded.database_path,
            chunks = excluded.chunks
        """,
        (
            chapter,
            subchapter,
            str(database_path),
            chunks
        )
    )

    connection.commit()
    connection.close()


# ============================================================
# FUNÇÃO 11 - GERAÇÃO DE ID ÚNICO
# ============================================================

def generate_chunk_id(chunk: Document) -> str:
    """
    Gera um identificador determinístico para o chunk.

    Isso ajuda a evitar duplicações quando o mesmo documento
    for processado novamente.
    """

    content = (
        chunk.metadata.get("document_name", "")
        + str(chunk.metadata.get("page", ""))
        + chunk.page_content
    )

    return hashlib.sha256(
        content.encode("utf-8")
    ).hexdigest()


# ============================================================
# FUNÇÃO 12 - GRAVAÇÃO DOS CHUNKS
# ============================================================

def store_chunks(
    chunks: List[Document],
    embeddings
) -> None:
    """
    Distribui os chunks entre os bancos correspondentes.

    Exemplo:

        Capítulo 1 / Subcapítulo 1.1
            -> banco A

        Capítulo 1 / Subcapítulo 1.2
            -> banco B

        Capítulo 2 / Subcapítulo 2.1
            -> banco C

    Cada chunk mantém:

        documento
        página
        capítulo
        subcapítulo
        chunk_id
    """

    grouped_chunks: Dict[
        Tuple[str, str],
        List[Document]
    ] = {}

    for chunk in chunks:

        key = (
            chunk.metadata.get(
                "chapter",
                "sem_capitulo"
            ),
            chunk.metadata.get(
                "subchapter",
                "sem_subcapitulo"
            )
        )

        grouped_chunks.setdefault(
            key,
            []
        ).append(chunk)

    for (
        chapter,
        subchapter
    ), chapter_chunks in grouped_chunks.items():

        vector_db = get_vector_database(
            chapter,
            subchapter,
            embeddings
        )

        ids = []

        for chunk in chapter_chunks:

            chunk_id = generate_chunk_id(chunk)

            chunk.metadata["chunk_hash"] = chunk_id

            ids.append(chunk_id)

        vector_db.add_documents(
            documents=chapter_chunks,
            ids=ids
        )

        database_path = (
            VECTOR_DB_DIR /
            normalize_name(chapter) /
            normalize_name(subchapter)
        )

        register_database(
            chapter=chapter,
            subchapter=subchapter,
            database_path=database_path,
            chunks=len(chapter_chunks)
        )

        print(
            f"[OK] Banco criado/atualizado:"
            f" {chapter} / {subchapter}"
            f" -> {len(chapter_chunks)} chunks"
        )


# ============================================================
# FUNÇÃO 13 - LISTAGEM DOS BANCOS
# ============================================================

def list_vector_databases() -> List[Dict[str, Any]]:
    """
    Retorna todos os bancos vetoriais registrados.

    Essa função representa uma camada simples de descoberta.

    Em uma arquitetura cloud, essa informação poderia vir
    de um serviço de catálogo.
    """

    connection = sqlite3.connect(CATALOG_DB)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            chapter,
            subchapter,
            database_path,
            chunks
        FROM vector_databases
        ORDER BY chapter, subchapter
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        {
            "chapter": row[0],
            "subchapter": row[1],
            "database_path": row[2],
            "chunks": row[3]
        }
        for row in rows
    ]


# ============================================================
# FUNÇÃO 14 - BUSCA SEMÂNTICA
# ============================================================

def semantic_search(
    query: str,
    embeddings,
    top_k: int = TOP_K
) -> List[Document]:
    """
    Executa busca semântica em todos os bancos vetoriais.

    A consulta é transformada em embedding e comparada
    com os embeddings dos chunks armazenados.

    Retornamos os documentos mais relevantes.

    A busca global é propositalmente simples para demonstração.

    Em produção, recomenda-se:

        1. classificador de capítulo;
        2. busca apenas nos bancos relevantes;
        3. reranking;
        4. busca híbrida BM25 + vetor.
    """

    databases = list_vector_databases()

    results = []

    for database in databases:

        vector_db = get_vector_database(
            database["chapter"],
            database["subchapter"],
            embeddings
        )

        docs = vector_db.similarity_search(
            query,
            k=top_k
        )

        for document in docs:

            document.metadata[
                "database_chapter"
            ] = database["chapter"]

            document.metadata[
                "database_subchapter"
            ] = database["subchapter"]

            results.append(document)

    return results[:top_k]


# ============================================================
# FUNÇÃO 15 - FORMATAÇÃO DO CONTEXTO
# ============================================================

def build_context(
    documents: List[Document]
) -> str:
    """
    Constrói o contexto que será enviado ao LLM.

    A fonte é colocada junto ao conteúdo.

    Isso permite que o modelo saiba exatamente de onde
    determinada informação foi recuperada.
    """

    context_parts = []

    for index, document in enumerate(documents, start=1):

        metadata = document.metadata

        source = (
            f"Documento: "
            f"{metadata.get('document_name', 'desconhecido')}\n"
            f"Página: "
            f"{metadata.get('page', 'desconhecida')}\n"
            f"Capítulo: "
            f"{metadata.get('chapter', 'desconhecido')}\n"
            f"Subcapítulo: "
            f"{metadata.get('subchapter', 'desconhecido')}"
        )

        block = (
            f"\n--- CONTEXTO {index} ---\n"
            f"{source}\n\n"
            f"{document.page_content}\n"
        )

        context_parts.append(block)

    return "\n".join(context_parts)


# ============================================================
# FUNÇÃO 16 - PROMPT DO RAG
# ============================================================

def build_rag_prompt(
    query: str,
    context: str
) -> str:
    """
    Cria o prompt final do RAG.

    O modelo recebe:

        pergunta
        contexto
        origem das informações

    A instrução também determina que o modelo não invente
    informações que não estejam presentes no contexto.
    """

    prompt = f"""
Você é um assistente especializado em responder perguntas
utilizando exclusivamente o contexto fornecido.

PERGUNTA:
{query}

CONTEXTO:
{context}

REGRAS:

1. Responda somente utilizando as informações disponíveis.
2. Não invente informações.
3. Se o contexto não for suficiente, informe isso.
4. Sempre informe as páginas utilizadas.
5. Cite capítulo e subcapítulo quando disponíveis.
6. Diferencie claramente informação encontrada de inferência.

Responda de maneira objetiva.
"""

    return prompt.strip()


# ============================================================
# FUNÇÃO 17 - CANAL GEMINI SIMULADO
# ============================================================

class GeminiSimulator:
    """
    Simula uma chamada para Gemini.

    Posteriormente pode ser substituído por:

        ChatGoogleGenerativeAI

    do ecossistema LangChain.
    """

    name = "Gemini"

    def invoke(
        self,
        prompt: str,
        documents: List[Document]
    ) -> str:

        sources = format_sources(documents)

        return (
            "[SIMULAÇÃO GEMINI]\n\n"
            "Resposta baseada no contexto recuperado.\n\n"
            "O Gemini receberia aqui o prompt RAG "
            "e produziria a resposta final.\n\n"
            f"Fontes consideradas:\n{sources}"
        )


# ============================================================
# FUNÇÃO 18 - CANAL GPT SIMULADO
# ============================================================

class GPTSimulator:
    """
    Simula uma chamada para GPT.

    Posteriormente pode ser substituído por:

        ChatOpenAI

    do LangChain.
    """

    name = "GPT"

    def invoke(
        self,
        prompt: str,
        documents: List[Document]
    ) -> str:

        sources = format_sources(documents)

        return (
            "[SIMULAÇÃO GPT]\n\n"
            "Resposta baseada no contexto recuperado.\n\n"
            "O GPT receberia aqui o prompt RAG "
            "e produziria a resposta final.\n\n"
            f"Fontes consideradas:\n{sources}"
        )


# ============================================================
# FUNÇÃO 19 - CANAL DEEPSEEK SIMULADO
# ============================================================

class DeepSeekSimulator:
    """
    Simula uma chamada para DeepSeek.

    O DeepSeek possui APIs compatíveis com padrões utilizados
    por clientes OpenAI-compatible.

    Posteriormente pode ser conectado através de um cliente
    compatível com LangChain.
    """

    name = "DeepSeek"

    def invoke(
        self,
        prompt: str,
        documents: List[Document]
    ) -> str:

        sources = format_sources(documents)

        return (
            "[SIMULAÇÃO DEEPSEEK]\n\n"
            "Resposta baseada no contexto recuperado.\n\n"
            "O DeepSeek receberia aqui o prompt RAG "
            "e produziria a resposta final.\n\n"
            f"Fontes consideradas:\n{sources}"
        )


# ============================================================
# FUNÇÃO 20 - FORMATAÇÃO DAS FONTES
# ============================================================

def format_sources(
    documents: List[Document]
) -> str:
    """
    Formata as fontes para apresentação ao usuário.

    Essa função é importante para a rastreabilidade do RAG.
    """

    sources = []

    for document in documents:

        metadata = document.metadata

        source = (
            f"- {metadata.get('document_name')}"
            f" | página {metadata.get('page')}"
            f" | {metadata.get('chapter')}"
            f" | {metadata.get('subchapter')}"
        )

        sources.append(source)

    return "\n".join(sources)


# ============================================================
# FUNÇÃO 21 - CONSULTA NOS TRÊS LLMs
# ============================================================

def query_three_llms(
    query: str,
    documents: List[Document]
) -> Dict[str, str]:
    """
    Executa a mesma consulta nos três canais simulados.

    O fluxo é:

        pergunta
            |
            v
        busca vetorial
            |
            v
        contexto
            |
            +------> Gemini
            |
            +------> GPT
            |
            +------> DeepSeek

    Essa arquitetura permite posteriormente comparar
    respostas de diferentes modelos.
    """

    context = build_context(documents)

    prompt = build_rag_prompt(
        query=query,
        context=context
    )

    channels = [
        GeminiSimulator(),
        GPTSimulator(),
        DeepSeekSimulator()
    ]

    responses = {}

    for channel in channels:

        responses[channel.name] = channel.invoke(
            prompt,
            documents
        )

    return responses


# ============================================================
# FUNÇÃO 22 - INGESTÃO COMPLETA
# ============================================================

def ingest_document(
    pdf_path: Path
) -> None:
    """
    Executa todo o pipeline de ingestão.

    Fluxo:

        PDF
         |
         v
        Loader
         |
         v
        Document por página
         |
         v
        Metadata
         |
         v
        Chunks
         |
         v
        Embeddings
         |
         v
        Bancos vetoriais
    """

    print(
        f"\nIniciando ingestão: {pdf_path.name}\n"
    )

    print("[1/5] Lendo PDF...")

    documents = load_pdf(pdf_path)

    print(
        f"       {len(documents)} páginas encontradas."
    )

    print("[2/5] Identificando capítulos...")

    documents = enrich_metadata(
        documents
    )

    print("[3/5] Criando chunks...")

    chunks = split_documents(
        documents
    )

    print(
        f"       {len(chunks)} chunks gerados."
    )

    print("[4/5] Carregando modelo de embeddings...")

    embeddings = create_embedding_model()

    print("[5/5] Gravando bancos vetoriais...")

    store_chunks(
        chunks,
        embeddings
    )

    print(
        "\nIngestão concluída."
    )


# ============================================================
# FUNÇÃO 23 - EXECUÇÃO DE UMA CONSULTA
# ============================================================

def execute_query(
    query: str
) -> None:
    """
    Executa uma pergunta sobre os documentos já indexados.
    """

    print(
        "\n========================================"
    )

    print(
        "CONSULTA RAG"
    )

    print(
        "========================================"
    )

    print(
        f"\nPergunta:\n{query}\n"
    )

    print(
        "Carregando embeddings..."
    )

    embeddings = create_embedding_model()

    print(
        "Executando busca semântica..."
    )

    documents = semantic_search(
        query,
        embeddings,
        top_k=TOP_K
    )

    if not documents:

        print(
            "\nNenhum documento relevante encontrado."
        )

        return

    print(
        f"\n{len(documents)} documentos recuperados."
    )

    print(
        "\nFONTES RECUPERADAS:"
    )

    print(
        format_sources(documents)
    )

    print(
        "\nExecutando canais Gemini, GPT e DeepSeek..."
    )

    responses = query_three_llms(
        query,
        documents
    )

    for model_name, response in responses.items():

        print(
            "\n========================================"
        )

        print(
            f"CANAL: {model_name}"
        )

        print(
            "========================================"
        )

        print(
            response
        )


# ============================================================
# FUNÇÃO 24 - EXEMPLO DE INSPEÇÃO DOS BANCOS
# ============================================================

def show_database_catalog() -> None:
    """
    Exibe os bancos vetoriais existentes.

    Isso facilita a demonstração da arquitetura de separação
    por capítulo/subcapítulo.
    """

    databases = list_vector_databases()

    print(
        "\n========================================"
    )

    print(
        "CATÁLOGO DOS BANCOS VETORIAIS"
    )

    print(
        "========================================\n"
    )

    if not databases:

        print(
            "Nenhum banco cadastrado."
        )

        return

    for database in databases:

        print(
            f"Capítulo: "
            f"{database['chapter']}"
        )

        print(
            f"Subcapítulo: "
            f"{database['subchapter']}"
        )

        print(
            f"Banco: "
            f"{database['database_path']}"
        )

        print(
            f"Chunks: "
            f"{database['chunks']}"
        )

        print(
            "-" * 50
        )


# ============================================================
# FUNÇÃO 25 - MAIN
# ============================================================

def main():
    """
    Ponto principal da aplicação.

    Para demonstração:

        1. Inicializa estrutura.
        2. Processa PDFs existentes.
        3. Mostra os bancos.
        4. Executa uma consulta de exemplo.

    Em produção, essa função pode ser substituída por uma API
    FastAPI ou por workers de processamento.
    """

    create_directories()

    initialize_catalog()

    # --------------------------------------------------------
    # INGESTÃO
    # --------------------------------------------------------

    pdf_files = list(
        DOCUMENTS_DIR.glob("*.pdf")
    )

    if pdf_files:

        for pdf_path in pdf_files:

            ingest_document(
                pdf_path
            )

    else:

        print(
            "\nNenhum PDF encontrado."
        )

        print(
            f"Coloque os documentos em:\n"
            f"{DOCUMENTS_DIR}"
        )

    # --------------------------------------------------------
    # MOSTRAR BANCOS
    # --------------------------------------------------------

    show_database_catalog()

    # --------------------------------------------------------
    # CONSULTA DE EXEMPLO
    # --------------------------------------------------------

    databases = list_vector_databases()

    if databases:

        query = input(
            "\nDigite sua pergunta para o RAG "
            "(ENTER para encerrar): "
        )

        if query.strip():

            execute_query(
                query.strip()
            )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()