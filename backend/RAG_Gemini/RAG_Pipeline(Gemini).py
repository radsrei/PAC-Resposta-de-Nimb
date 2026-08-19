import os
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# =====================================================================
# ETAPA 1: SIMULAÇÃO E CARREGAMENTO DE DADOS
# =====================================================================
def get_mock_documents() -> list[Document]:
    """
    Contexto: Em um cenário real, você usaria carregadores (como PyPDFLoader).
    Aqui, criamos documentos simulados que já contêm o texto base e,
    crucialmente, os metadados para rastreabilidade (página, capítulo, etc).
    Isso garante que a IA sempre possa demonstrar a fonte exata da resposta.
    """
    print("-> Carregando documentos base...")
    return [
        Document(
            page_content="A arquitetura de microsserviços permite escalabilidade horizontal. Cada serviço opera de forma independente.",
            metadata={"source": "livro_arquitetura.pdf", "page": 12, "chapter": "1", "subchapter": "1.1"}
        ),
        Document(
            page_content="O padrão Saga é utilizado para manter a consistência de dados em transações distribuídas entre microsserviços.",
            metadata={"source": "livro_arquitetura.pdf", "page": 15, "chapter": "1", "subchapter": "1.2"}
        ),
        Document(
            page_content="Bancos de dados NoSQL, como MongoDB, oferecem esquemas flexíveis ideais para dados não estruturados.",
            metadata={"source": "livro_dados.pdf", "page": 45, "chapter": "2", "subchapter": "2.1"}
        )
    ]

# =====================================================================
# ETAPA 2: PROCESSAMENTO DE CHUNKS (FRAGMENTAÇÃO)
# =====================================================================
def process_chunks(documents: list[Document]) -> list[Document]:
    """
    Contexto: Modelos de linguagem possuem um limite de contexto (tokens). 
    Além disso, buscar em textos muito longos dilui a relevância do embedding.
    O 'RecursiveCharacterTextSplitter' tenta dividir o texto de forma inteligente 
    (parágrafos, depois frases, depois palavras), mantendo a coesão semântica.
    O 'chunk_overlap' garante que o contexto na borda de um chunk não seja perdido.
    """
    print("-> Iniciando o processo de Chunking...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,     # Tamanho máximo de caracteres por fragmento
        chunk_overlap=50,   # Sobreposição para não perder o contexto entre cortes
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    # O split_documents divide o texto e propaga os metadados originais (página/capítulo) para todos os pedaços.
    chunks = text_splitter.split_documents(documents)
    print(f"-> {len(documents)} documentos originais foram divididos em {len(chunks)} chunks.")
    return chunks

# =====================================================================
# ETAPA 3: EMBEDDINGS E ROTEAMENTO PARA MÚLTIPLOS BANCOS DE DADOS
# =====================================================================
def store_in_databases(chunks: list[Document], base_db_path: str = "./vector_stores"):
    """
    Contexto: Transforma os chunks de texto em vetores numéricos (embeddings).
    Nesta função, roteamos os chunks para bancos de dados *diferentes* baseados 
    no metadado 'chapter'. Isso é extremamente útil para segmentação de conhecimento 
    e otimização de busca (ex: buscar apenas no banco de dados do Capítulo 1).
    """
    print("-> Gerando Embeddings e gravando nos bancos de dados...")
    
    # Usando um modelo open-source leve para gerar os vetores localmente
    embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # Dicionário para organizar chunks por capítulo
    chunks_by_chapter = {}
    for chunk in chunks:
        chapter = chunk.metadata.get("chapter", "geral")
        if chapter not in chunks_by_chapter:
            chunks_by_chapter[chapter] = []
        chunks_by_chapter[chapter].append(chunk)

    # Cria/Atualiza um banco de dados (Chroma) para cada capítulo
    vector_stores = {}
    for chapter, chapter_chunks in chunks_by_chapter.items():
        db_path = os.path.join(base_db_path, f"capitulo_{chapter}")
        
        # Cria e persiste o banco de dados
        vector_store = Chroma.from_documents(
            documents=chapter_chunks,
            embedding=embeddings_model,
            persist_directory=db_path
        )
        vector_stores[chapter] = vector_store
        print(f"   - Gravado(s) {len(chapter_chunks)} chunk(s) no banco: {db_path}")
        
    return vector_stores

# =====================================================================
# ETAPA 4: CONSULTA E SIMULAÇÃO MULTI-LLM (GEMINI, GPT, DEEPSEEK)
# =====================================================================
def simulate_multi_llm_query(query: str, context_docs: list[Document]):
    """
    Contexto: Esta etapa pega o contexto recuperado do banco de dados e envia
    para diferentes LLMs, forçando a demonstração da fonte (página e capítulo).
    O DeepSeek é invocado aqui usando a interface compatível com OpenAI da LangChain, 
    apontando para a API oficial do DeepSeek.
    """
    print(f"\n[Consulta do Usuário]: {query}")
    
    # Montagem do contexto com citações de fonte explícitas
    context_text = ""
    for i, doc in enumerate(context_docs):
        page = doc.metadata.get('page', 'N/A')
        cap = doc.metadata.get('chapter', 'N/A')
        sub = doc.metadata.get('subchapter', 'N/A')
        context_text += f"\n[Fonte {i+1} | Cap: {cap}.{sub} | Pág: {page}]: {doc.page_content}"

    prompt = f"""Use o contexto abaixo para responder à pergunta. 
    Sempre cite a fonte informando o Capítulo, Subcapítulo e a Página de onde tirou a informação.
    Se não souber, diga que não sabe.
    
    Contexto: {context_text}
    
    Pergunta: {query}
    """

    print("\n" + "="*50)
    print("CONTEXTO MONTADO PARA O PROMPT:")
    print(context_text)
    print("="*50)

    # 1. Configuração do Gemini (Google)
    try:
        # Requer variável de ambiente GOOGLE_API_KEY
        llm_gemini = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest", temperature=0)
        print("\n🤖 Resposta GEMINI:")
        print(llm_gemini.invoke(prompt).content)
    except Exception as e:
        print(f"\n🤖 [Gemini não configurado (Falta API Key) - Simulando comportamento] -> {e}")

    # 2. Configuração do GPT (OpenAI)
    try:
        # Requer variável de ambiente OPENAI_API_KEY
        llm_gpt = ChatOpenAI(model="gpt-4o", temperature=0)
        print("\n🤖 Resposta GPT-4o:")
        print(llm_gpt.invoke(prompt).content)
    except Exception as e:
        print(f"\n🤖 [GPT não configurado (Falta API Key) - Simulando comportamento] -> {e}")

    # 3. Configuração do DeepSeek
    try:
        # Requer variável de ambiente DEEPSEEK_API_KEY
        llm_deepseek = ChatOpenAI(
            model_name="deepseek-chat", 
            api_key=os.environ.get("DEEPSEEK_API_KEY", "dummy_key"), 
            base_url="https://api.deepseek.com",
            temperature=0
        )
        print("\n🤖 Resposta DEEPSEEK:")
        print(llm_deepseek.invoke(prompt).content)
    except Exception as e:
        print(f"\n🤖 [DeepSeek não configurado (Falta API Key) - Simulando comportamento] -> {e}")

# =====================================================================
# EXECUÇÃO PRINCIPAL
# =====================================================================
if __name__ == "__main__":
    # 1. Carrega os dados simulados
    raw_docs = get_mock_documents()
    
    # 2. Faz o chunking
    chunked_docs = process_chunks(raw_docs)
    
    # 3. Salva em bancos separados por capítulo
    databases = store_in_databases(chunked_docs)
    
    # 4. Simulação de busca: Usuário pergunta sobre microsserviços (pertence ao cap 1)
    # Na prática, você utilizaria a query para gerar um embedding e faria a busca de similaridade no Chroma
    print("\n-> Simulando busca no banco do Capítulo 1...")
    retriever = databases["1"].as_retriever(search_kwargs={"k": 2})
    user_query = "Como lidar com a consistência de dados em microsserviços?"
    
    # Recupera os documentos mais relevantes do banco vetorial do Capítulo 1
    retrieved_docs = retriever.invoke(user_query)
    
    # 5. Gera as respostas usando os 3 LLMs
    simulate_multi_llm_query(user_query, retrieved_docs)

"""
---------
--------
--------------
--------------
"""

# Adicione estes imports no topo do arquivo
import os
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain_cohere import CohereRerank

# ... (etapas 1, 2 e 3 iguais ao script anterior) ...

# =====================================================================
# NOVA ETAPA 4: BUSCA COM RE-RANKING (COHERE)
# =====================================================================
print("\n-> Configurando retriever base (ChromaDB)...")
# ATENÇÃO: Agora buscamos mais documentos inicialmente (ex: k=10)
# A busca vetorial é rápida, então podemos ser mais "fominhas" nesta etapa.
base_retriever = databases["1"].as_retriever(search_kwargs={"k": 10})

print("-> Configurando o compressor (Cohere Rerank)...")
# Utilizamos o modelo multilingual pois nossa base está em português
# top_n=3 significa que, dos 10 documentos, apenas os 3 melhores irão para o LLM.
cohere_compressor = CohereRerank(
    cohere_api_key=os.environ.get("COHERE_API_KEY"),
    model="rerank-multilingual-v3.0",
    top_n=3 
)

# O ContextualCompressionRetriever une os dois mundos
compression_retriever = ContextualCompressionRetriever(
    base_compressor=cohere_compressor,
    base_retriever=base_retriever
)

user_query = "Como lidar com a consistência de dados em microsserviços?"
print(f"\n[Consulta do Usuário]: {user_query}")

# Ao invocar este retriever, ele internamente busca 10 no Chroma, 
# envia para a API da Cohere, que os reordena e devolve apenas os 3 melhores.
retrieved_docs = compression_retriever.invoke(user_query)

print("\n-> Documentos após o Re-ranking:")
for i, doc in enumerate(retrieved_docs):
    # O modelo da Cohere também injeta o score de relevância nos metadados!
    relevance_score = doc.metadata.get('relevance_score', 'N/A')
    print(f"[{i+1}] Score: {relevance_score} | Cap: {doc.metadata.get('chapter')} - {doc.page_content[:50]}...")

# 5. Gera as respostas usando os 3 LLMs (função original)
simulate_multi_llm_query(user_query, retrieved_docs)