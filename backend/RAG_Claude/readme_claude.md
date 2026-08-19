Vou criar um programa Python completo, comentado em português, cobrindo todo o pipeline de RAG (chunking, embeddings, bancos vetoriais por capítulo/subcapítulo com página de referência) e a simulação das 3 consultas (Gemini, GPT, Deepseek) via LangChain.**Estrutura do pipeline** (`rag_pipeline.py`):

1. **Leitura** — `carregar_documento()`: usa `PyPDFLoader` do LangChain, preservando a página de cada trecho.
2. **Tagueamento** — `taguear_capitulos()`: associa cada página a um capítulo/subcapítulo via `CHAPTER_MAP` (intervalos de página configuráveis).
3. **Chunking** — `dividir_em_chunks()`: `RecursiveCharacterTextSplitter`, propagando página/capítulo/subcapítulo para cada chunk.
4. **Embeddings** — `EmbeddingsLocalSimulado`: implementa a interface `Embeddings` do LangChain (determinística, sem exigir API key); comentários mostram como trocar por `OpenAIEmbeddings` ou `GoogleGenerativeAIEmbeddings` reais.
5. **Gravação por capítulo** — `gravar_por_capitulo()`: cria **um banco Chroma persistido por capítulo** (pastas separadas em `./vector_db/`), sempre guardando a página no metadata.
6. **Leitura do banco** — `carregar_banco_capitulo()`: reabre o banco vetorial de um capítulo específico a partir do disco.
7. **Retrieval** — `recuperar_contexto()` + `formatar_fontes()`: busca por similaridade e formata a citação "Capítulo > Subcapítulo, página X".
8. **Multi-LLM** — `consultar_gemini()`, `consultar_gpt()`, `consultar_deepseek()`: simulam as 3 chamadas (cada uma comenta exatamente o código real do LangChain para plugar `ChatGoogleGenerativeAI`, `ChatOpenAI` e o endpoint compatível da Deepseek); `consultar_multi_llm()` orquestra tudo e retorna as 3 respostas + fontes.
9. `executar_pipeline()` amarra tudo, do PDF bruto à resposta final.

Para rodar de verdade: `pip install langchain langchain-community langchain-openai langchain-google-genai chromadb pypdf`, coloque um PDF em `documento_exemplo.pdf` (ou ajuste o caminho) e execute `python rag_pipeline.py`. Para produção, é só descomentar as chamadas reais nas 3 funções de LLM e trocar `EmbeddingsLocalSimulado` por um provedor real.