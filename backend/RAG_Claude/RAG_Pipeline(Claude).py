"""
Entrada no Prompt:
Gere um programa python, para realizar o processo de chunks e embedins, para um RAG.
Dentro desse processo delimite cada uma das funções com explicações e contexto, para ferramentas externas utilize langchain e simule consultas usando 3 canais de LLM's Gemini, GPT e Deepseek.

Dentro do programa, faça um bloco para leitura e gravação em diferentes bancos de dados, voltados para diferentes capítulos e subcapítulos, sempre gravando a página de referencia para busca e demonstração de fonte.
"""


"""
================================================================================
PIPELINE RAG: CHUNKING, EMBEDDINGS, ARMAZENAMENTO VETORIAL POR CAPÍTULO
E SIMULAÇÃO DE CONSULTA MULTI-LLM (GEMINI, GPT E DEEPSEEK)
================================================================================

Este programa demonstra, de ponta a ponta, um pipeline de RAG
(Retrieval-Augmented Generation) construído sobre o LangChain.

Etapas do pipeline:

    1. LEITURA  -> carrega um PDF preservando o número da página de cada
                   trecho de texto (metadado nativo do LangChain).
    2. TAGUEAMENTO -> associa cada página a um Capítulo/Subcapítulo, com
                   base em um mapa de intervalos de página definido pelo
                   usuário (CHAPTER_MAP).
    3. CHUNKING -> divide os documentos em pedaços menores (chunks),
                   preservando todos os metadados (capítulo, subcapítulo,
                   página) em cada chunk gerado.
    4. EMBEDDINGS -> gera vetores numéricos para cada chunk.
    5. GRAVAÇÃO -> persiste os chunks + embeddings em bancos vetoriais
                   (Chroma) SEPARADOS por capítulo/subcapítulo — cada
                   capítulo vira uma "coleção"/banco próprio em disco.
    6. LEITURA (retrieval) -> dada uma pergunta, busca nos bancos vetoriais
                   os trechos mais relevantes, sempre trazendo a página de
                   origem para poder citar a fonte.
    7. CONSULTA MULTI-LLM -> o mesmo contexto recuperado é enviado, em
                   paralelo (simulado), para 3 canais de LLM diferentes:
                   Gemini, GPT e Deepseek. Cada um responde citando a
                   página de referência usada.

--------------------------------------------------------------------------------
DEPENDÊNCIAS (pip install):

    pip install langchain langchain-community langchain-openai \
                langchain-google-genai chromadb pypdf tiktoken

--------------------------------------------------------------------------------
SOBRE A "SIMULAÇÃO" DOS LLMS:

Para que este script rode de ponta a ponta SEM exigir chaves de API reais,
as funções `consultar_gemini`, `consultar_gpt` e `consultar_deepseek`
retornam respostas simuladas (mock). Os pontos exatos onde as chamadas
reais do LangChain entrariam estão comentados dentro de cada função,
prontos para serem descomentados assim que houver uma API key configurada.
================================================================================
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma


# ==============================================================================
# 1. CONFIGURAÇÃO GERAL
# ==============================================================================

# Diretório raiz onde cada capítulo terá seu próprio banco vetorial (Chroma).
DIRETORIO_BASE_VETORES = "./vector_db"

# Mapa de capítulos/subcapítulos por intervalo de páginas.
# Ajuste esse mapa de acordo com o sumário real do documento que será
# processado. Páginas são 1-indexadas (página impressa do documento).
CHAPTER_MAP: List[Dict] = [
    {"capitulo": "Capitulo_1_Introducao", "subcapitulo": "1.1_Contexto", "page_start": 1, "page_end": 5},
    {"capitulo": "Capitulo_1_Introducao", "subcapitulo": "1.2_Objetivos", "page_start": 6, "page_end": 10},
    {"capitulo": "Capitulo_2_Metodologia", "subcapitulo": "2.1_Dados", "page_start": 11, "page_end": 18},
    {"capitulo": "Capitulo_2_Metodologia", "subcapitulo": "2.2_Modelo", "page_start": 19, "page_end": 25},
    {"capitulo": "Capitulo_3_Resultados", "subcapitulo": "3.1_Analise", "page_start": 26, "page_end": 40},
]

TAMANHO_CHUNK = 800        # caracteres por chunk
SOBREPOSICAO_CHUNK = 120   # overlap entre chunks vizinhos, para não perder contexto
TOP_K_RECUPERACAO = 4      # quantos chunks recuperar por pergunta


# ==============================================================================
# 2. LEITURA DO DOCUMENTO (mantendo a página de origem)
# ==============================================================================

def carregar_documento(caminho_pdf: str) -> List[Document]:
    """
    Carrega um arquivo PDF usando o PyPDFLoader do LangChain.

    Contexto:
        O PyPDFLoader retorna UM `Document` por página do PDF, e já inclui
        automaticamente o metadado `page` (0-indexado) em cada um. Isso é
        essencial para o RAG, pois permitirá citar a página exata de onde
        cada resposta foi extraída.

    Parâmetros:
        caminho_pdf (str): caminho local do arquivo .pdf a ser processado.

    Retorno:
        List[Document]: lista de documentos, um por página, cada um com
        `page_content` (texto da página) e `metadata["page"]`.
    """
    loader = PyPDFLoader(caminho_pdf)
    documentos = loader.load()

    # Normaliza a página para 1-indexada (mais amigável para citação humana)
    for doc in documentos:
        doc.metadata["page"] = doc.metadata.get("page", 0) + 1

    return documentos


# ==============================================================================
# 3. TAGUEAMENTO DE CAPÍTULO / SUBCAPÍTULO
# ==============================================================================

def taguear_capitulos(documentos: List[Document], mapa_capitulos: List[Dict]) -> List[Document]:
    """
    Enriquece cada documento (página) com os metadados de capítulo e
    subcapítulo, de acordo com o intervalo de páginas em que ela se encaixa.

    Contexto:
        PDFs não trazem estrutura de capítulos nativamente. Por isso,
        usamos um mapa de intervalos de página (CHAPTER_MAP) definido
        manualmente (ou que poderia vir de um sumário extraído via
        regex/índice do próprio PDF) para associar cada página ao seu
        capítulo/subcapítulo correspondente.

    Parâmetros:
        documentos (List[Document]): documentos por página (saída de
            `carregar_documento`).
        mapa_capitulos (List[Dict]): lista de dicionários com
            capitulo, subcapitulo, page_start, page_end.

    Retorno:
        List[Document]: os mesmos documentos, agora com metadata["capitulo"]
        e metadata["subcapitulo"] preenchidos.
    """
    for doc in documentos:
        pagina = doc.metadata["page"]
        capitulo_encontrado = "Sem_Capitulo"
        subcapitulo_encontrado = "Sem_Subcapitulo"

        for faixa in mapa_capitulos:
            if faixa["page_start"] <= pagina <= faixa["page_end"]:
                capitulo_encontrado = faixa["capitulo"]
                subcapitulo_encontrado = faixa["subcapitulo"]
                break

        doc.metadata["capitulo"] = capitulo_encontrado
        doc.metadata["subcapitulo"] = subcapitulo_encontrado

    return documentos


# ==============================================================================
# 4. CHUNKING
# ==============================================================================

def dividir_em_chunks(
    documentos: List[Document],
    tamanho_chunk: int = TAMANHO_CHUNK,
    sobreposicao: int = SOBREPOSICAO_CHUNK,
) -> List[Document]:
    """
    Divide cada documento (página) em pedaços menores (chunks) de texto.

    Contexto:
        Chunks menores melhoram a precisão da busca semântica (embeddings
        de trechos muito longos "diluem" o significado). O
        RecursiveCharacterTextSplitter tenta cortar em quebras naturais
        (parágrafos, frases, palavras), nessa ordem de prioridade.
        Importante: o splitter propaga automaticamente os metadados
        originais (page, capitulo, subcapitulo) para cada novo chunk.

    Parâmetros:
        documentos (List[Document]): documentos já tagueados por capítulo.
        tamanho_chunk (int): tamanho alvo de cada chunk, em caracteres.
        sobreposicao (int): quantos caracteres de overlap entre chunks
            vizinhos, para preservar contexto na fronteira dos cortes.

    Retorno:
        List[Document]: lista de chunks, cada um herdando os metadados
        (page, capitulo, subcapitulo) do documento de origem.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=tamanho_chunk,
        chunk_overlap=sobreposicao,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documentos)

    # Adiciona um id determinístico ao chunk (útil para upsert/dedup no banco)
    for i, chunk in enumerate(chunks):
        base = f"{chunk.metadata.get('capitulo')}-{chunk.metadata.get('page')}-{i}"
        chunk.metadata["chunk_id"] = hashlib.md5(base.encode("utf-8")).hexdigest()[:12]

    return chunks


# ==============================================================================
# 5. EMBEDDINGS
# ==============================================================================

class EmbeddingsLocalSimulado(Embeddings):
    """
    Implementação simples e determinística da interface `Embeddings` do
    LangChain, usada apenas para permitir a execução completa deste
    exemplo SEM exigir uma chave de API de embeddings.

    Contexto:
        Em produção, troque esta classe por um provedor real, por exemplo:

            from langchain_openai import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

        ou

            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

        A interface (embed_documents / embed_query) é a mesma, então o
        restante do pipeline (Chroma, retrieval) não muda.
    """

    def __init__(self, dimensao: int = 384):
        self.dimensao = dimensao

    def _vetorizar(self, texto: str) -> List[float]:
        """Gera um vetor pseudo-aleatório, porém determinístico, a partir
        de um hash do texto — apenas para fins de demonstração local."""
        semente = int(hashlib.sha256(texto.encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(semente)
        vetor = rng.normal(size=self.dimensao)
        vetor = vetor / np.linalg.norm(vetor)  # normaliza (cosine-friendly)
        return vetor.tolist()

    def embed_documents(self, textos: List[str]) -> List[List[float]]:
        """Gera embeddings para uma lista de chunks (indexação em lote)."""
        return [self._vetorizar(t) for t in textos]

    def embed_query(self, texto: str) -> List[float]:
        """Gera o embedding de uma pergunta/consulta do usuário."""
        return self._vetorizar(texto)


def obter_modelo_embeddings() -> Embeddings:
    """
    Fábrica do modelo de embeddings usado em todo o pipeline.

    Contexto:
        Centralizar essa escolha aqui facilita trocar de provedor
        (OpenAI, Google, HuggingFace local, etc.) em um único lugar.

    Retorno:
        Embeddings: instância pronta para uso pelo Chroma.
    """
    return EmbeddingsLocalSimulado(dimensao=384)


# ==============================================================================
# 6. GRAVAÇÃO EM BANCOS VETORIAIS SEPARADOS POR CAPÍTULO
# ==============================================================================

def _slug(texto: str) -> str:
    """Normaliza uma string para uso seguro como nome de pasta/coleção."""
    return re.sub(r"[^a-zA-Z0-9_]+", "_", texto).strip("_").lower()


def gravar_por_capitulo(
    chunks: List[Document],
    modelo_embeddings: Embeddings,
    diretorio_base: str = DIRETORIO_BASE_VETORES,
) -> Dict[str, Chroma]:
    """
    Agrupa os chunks por capítulo e grava cada grupo em seu PRÓPRIO banco
    vetorial Chroma, persistido em disco.

    Contexto:
        Ter um banco por capítulo (em vez de um único banco monolítico)
        permite:
          - buscas mais rápidas e focadas quando já se sabe o capítulo
            de interesse;
          - governança/atualização independente por capítulo (ex.:
            reprocessar só o Capítulo 2 sem tocar nos demais);
          - isolamento físico dos dados por assunto.
        A página de origem (`page`) permanece nos metadados de cada
        chunk gravado, garantindo a citação de fonte na recuperação.

    Parâmetros:
        chunks (List[Document]): chunks já com metadados de capítulo/página.
        modelo_embeddings (Embeddings): modelo usado para vetorizar o texto.
        diretorio_base (str): pasta raiz onde cada capítulo terá sua
            subpasta de persistência.

    Retorno:
        Dict[str, Chroma]: mapa {nome_do_capitulo: vectorstore} para reuso
        imediato (ex.: consultas logo em seguida, sem precisar reabrir do
        disco).
    """
    chunks_por_capitulo: Dict[str, List[Document]] = {}
    for chunk in chunks:
        capitulo = chunk.metadata.get("capitulo", "Sem_Capitulo")
        chunks_por_capitulo.setdefault(capitulo, []).append(chunk)

    bancos: Dict[str, Chroma] = {}
    os.makedirs(diretorio_base, exist_ok=True)

    for capitulo, chunks_do_capitulo in chunks_por_capitulo.items():
        pasta_capitulo = os.path.join(diretorio_base, _slug(capitulo))

        vectorstore = Chroma.from_documents(
            documents=chunks_do_capitulo,
            embedding=modelo_embeddings,
            collection_name=_slug(capitulo),
            persist_directory=pasta_capitulo,
        )
        vectorstore.persist()  # garante a escrita em disco

        bancos[capitulo] = vectorstore
        print(f"[GRAVAÇÃO] Capítulo '{capitulo}': {len(chunks_do_capitulo)} chunks "
              f"gravados em '{pasta_capitulo}'.")

    return bancos


def carregar_banco_capitulo(
    capitulo: str,
    modelo_embeddings: Embeddings,
    diretorio_base: str = DIRETORIO_BASE_VETORES,
) -> Optional[Chroma]:
    """
    Reabre, a partir do disco, o banco vetorial de UM capítulo específico.

    Contexto:
        Usado em execuções futuras (ex.: um servidor de perguntas e
        respostas) para não precisar reprocessar o PDF inteiro toda vez
        — basta carregar o banco vetorial já persistido do capítulo de
        interesse.

    Parâmetros:
        capitulo (str): nome do capítulo (chave usada em CHAPTER_MAP).
        modelo_embeddings (Embeddings): mesmo modelo usado na gravação
            (precisa ser compatível/dimensionalmente igual).
        diretorio_base (str): pasta raiz dos bancos vetoriais.

    Retorno:
        Optional[Chroma]: vectorstore carregado, ou None se a pasta do
        capítulo não existir.
    """
    pasta_capitulo = os.path.join(diretorio_base, _slug(capitulo))
    if not os.path.isdir(pasta_capitulo):
        print(f"[AVISO] Banco do capítulo '{capitulo}' não encontrado em {pasta_capitulo}.")
        return None

    return Chroma(
        collection_name=_slug(capitulo),
        embedding_function=modelo_embeddings,
        persist_directory=pasta_capitulo,
    )


# ==============================================================================
# 7. RECUPERAÇÃO (RETRIEVAL) COM CITAÇÃO DE PÁGINA
# ==============================================================================

def recuperar_contexto(
    pergunta: str,
    vectorstore: Chroma,
    k: int = TOP_K_RECUPERACAO,
) -> List[Document]:
    """
    Busca, dentro de um banco vetorial (de um capítulo), os `k` chunks
    mais relevantes semanticamente para a pergunta do usuário.

    Contexto:
        Esta é a etapa de "Retrieval" do RAG: convertemos a pergunta em
        embedding e comparamos por similaridade (cosine) com os
        embeddings já gravados, retornando os trechos mais próximos.

    Parâmetros:
        pergunta (str): pergunta em linguagem natural feita pelo usuário.
        vectorstore (Chroma): banco vetorial do capítulo a ser consultado.
        k (int): quantidade de chunks mais relevantes a retornar.

    Retorno:
        List[Document]: chunks recuperados, cada um com metadata["page"],
        metadata["capitulo"] e metadata["subcapitulo"] para citação.
    """
    return vectorstore.similarity_search(pergunta, k=k)


def formatar_fontes(chunks_recuperados: List[Document]) -> str:
    """
    Formata, de forma legível, as fontes (capítulo, subcapítulo e página)
    dos chunks recuperados, para exibição junto com a resposta final.

    Parâmetros:
        chunks_recuperados (List[Document]): saída de `recuperar_contexto`.

    Retorno:
        str: texto multi-linha, uma fonte por linha, no formato:
             "- Capítulo X > Subcapítulo Y, página Z"
    """
    linhas = []
    for chunk in chunks_recuperados:
        meta = chunk.metadata
        linhas.append(
            f"- {meta.get('capitulo')} > {meta.get('subcapitulo')}, "
            f"página {meta.get('page')}"
        )
    return "\n".join(dict.fromkeys(linhas))  # remove duplicadas preservando ordem


# ==============================================================================
# 8. SIMULAÇÃO DE CONSULTA A 3 CANAIS DE LLM (GEMINI, GPT, DEEPSEEK)
# ==============================================================================

def _montar_prompt(pergunta: str, chunks_contexto: List[Document]) -> str:
    """
    Monta o prompt padrão (contexto + pergunta) enviado a qualquer um dos
    3 LLMs, garantindo que todos recebam exatamente a mesma base para que
    as respostas sejam comparáveis.

    Parâmetros:
        pergunta (str): pergunta do usuário.
        chunks_contexto (List[Document]): chunks recuperados do vectorstore.

    Retorno:
        str: prompt final, com instrução explícita para citar a página.
    """
    contexto = "\n---\n".join(
        f"(Página {c.metadata.get('page')}) {c.page_content}" for c in chunks_contexto
    )
    return (
        "Responda a pergunta usando APENAS o contexto abaixo. "
        "Sempre cite a página de onde tirou a informação.\n\n"
        f"CONTEXTO:\n{contexto}\n\n"
        f"PERGUNTA: {pergunta}"
    )


def consultar_gemini(pergunta: str, chunks_contexto: List[Document]) -> str:
    """
    Simula uma consulta ao canal Gemini (Google).

    Contexto:
        Para uso real, substitua o corpo simulado por:

            from langchain_google_genai import ChatGoogleGenerativeAI
            llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", api_key=...)
            resposta = llm.invoke(_montar_prompt(pergunta, chunks_contexto))
            return resposta.content

    Retorno:
        str: resposta simulada do modelo Gemini.
    """
    prompt = _montar_prompt(pergunta, chunks_contexto)  # noqa: F841 (mantido p/ paridade com uso real)
    paginas = sorted({c.metadata.get("page") for c in chunks_contexto})
    return (
        f"[Gemini] Com base nos trechos recuperados (páginas {paginas}), "
        f"a resposta para '{pergunta}' foi sintetizada a partir do contexto fornecido."
    )


def consultar_gpt(pergunta: str, chunks_contexto: List[Document]) -> str:
    """
    Simula uma consulta ao canal GPT (OpenAI).

    Contexto:
        Para uso real, substitua o corpo simulado por:

            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(model="gpt-4o", api_key=...)
            resposta = llm.invoke(_montar_prompt(pergunta, chunks_contexto))
            return resposta.content

    Retorno:
        str: resposta simulada do modelo GPT.
    """
    prompt = _montar_prompt(pergunta, chunks_contexto)  # noqa: F841
    paginas = sorted({c.metadata.get("page") for c in chunks_contexto})
    return (
        f"[GPT] Analisando o contexto recuperado (páginas {paginas}), "
        f"segue uma resposta objetiva para '{pergunta}'."
    )


def consultar_deepseek(pergunta: str, chunks_contexto: List[Document]) -> str:
    """
    Simula uma consulta ao canal Deepseek.

    Contexto:
        A Deepseek expõe uma API compatível com o padrão OpenAI, então em
        produção basta apontar o `base_url`:

            from langchain_openai import ChatOpenAI
            llm = ChatOpenAI(
                model="deepseek-chat",
                api_key=...,
                base_url="https://api.deepseek.com",
            )
            resposta = llm.invoke(_montar_prompt(pergunta, chunks_contexto))
            return resposta.content

    Retorno:
        str: resposta simulada do modelo Deepseek.
    """
    prompt = _montar_prompt(pergunta, chunks_contexto)  # noqa: F841
    paginas = sorted({c.metadata.get("page") for c in chunks_contexto})
    return (
        f"[Deepseek] Considerando o material recuperado (páginas {paginas}), "
        f"segue a resposta gerada para '{pergunta}'."
    )


def consultar_multi_llm(pergunta: str, vectorstore: Chroma) -> Dict[str, str]:
    """
    Orquestra o fluxo completo de pergunta-e-resposta: recupera o contexto
    relevante e consulta os 3 canais de LLM em sequência (simulando um
    disparo paralelo), retornando as 3 respostas junto das fontes citadas.

    Parâmetros:
        pergunta (str): pergunta em linguagem natural.
        vectorstore (Chroma): banco vetorial do capítulo relevante.

    Retorno:
        Dict[str, str]: {"gemini": ..., "gpt": ..., "deepseek": ...,
        "fontes": ...} com as respostas e a citação de páginas.
    """
    chunks_contexto = recuperar_contexto(pergunta, vectorstore)
    fontes = formatar_fontes(chunks_contexto)

    return {
        "gemini": consultar_gemini(pergunta, chunks_contexto),
        "gpt": consultar_gpt(pergunta, chunks_contexto),
        "deepseek": consultar_deepseek(pergunta, chunks_contexto),
        "fontes": fontes,
    }


# ==============================================================================
# 9. ORQUESTRAÇÃO PRINCIPAL (DEMONSTRAÇÃO END-TO-END)
# ==============================================================================

def executar_pipeline(caminho_pdf: str, pergunta_teste: str) -> None:
    """
    Executa o pipeline completo, do PDF bruto à resposta multi-LLM.

    Etapas executadas, em ordem:
        1. carregar_documento     -> leitura do PDF com página de origem
        2. taguear_capitulos      -> associação capítulo/subcapítulo
        3. dividir_em_chunks      -> chunking com metadados preservados
        4. obter_modelo_embeddings + gravar_por_capitulo
                                   -> geração de embeddings e gravação em
                                      bancos vetoriais separados por capítulo
        5. carregar_banco_capitulo -> simula reabertura do banco em uma
                                      sessão futura (ex.: um servidor de API)
        6. consultar_multi_llm    -> retrieval + consulta aos 3 canais de LLM

    Parâmetros:
        caminho_pdf (str): caminho do PDF de entrada.
        pergunta_teste (str): pergunta de exemplo usada na demonstração.
    """
    print("=" * 80)
    print("ETAPA 1-3: LEITURA, TAGUEAMENTO E CHUNKING")
    print("=" * 80)
    documentos = carregar_documento(caminho_pdf)
    documentos = taguear_capitulos(documentos, CHAPTER_MAP)
    chunks = dividir_em_chunks(documentos)
    print(f"Total de páginas lidas: {len(documentos)} | Total de chunks gerados: {len(chunks)}")

    print("\n" + "=" * 80)
    print("ETAPA 4: EMBEDDINGS + GRAVAÇÃO POR CAPÍTULO")
    print("=" * 80)
    modelo_embeddings = obter_modelo_embeddings()
    bancos_por_capitulo = gravar_por_capitulo(chunks, modelo_embeddings)

    print("\n" + "=" * 80)
    print("ETAPA 5: RECARREGANDO UM BANCO ESPECÍFICO DO DISCO")
    print("=" * 80)
    capitulo_alvo = chunks[0].metadata["capitulo"] if chunks else None
    if capitulo_alvo is None:
        print("Nenhum chunk gerado — verifique o PDF de entrada.")
        return

    vectorstore_alvo = carregar_banco_capitulo(capitulo_alvo, modelo_embeddings) \
        or bancos_por_capitulo[capitulo_alvo]

    print("\n" + "=" * 80)
    print(f"ETAPA 6: CONSULTA MULTI-LLM — Capítulo '{capitulo_alvo}'")
    print("=" * 80)
    print(f"Pergunta: {pergunta_teste}\n")

    resultado = consultar_multi_llm(pergunta_teste, vectorstore_alvo)

    print(resultado["gemini"])
    print(resultado["gpt"])
    print(resultado["deepseek"])
    print("\nFontes utilizadas:")
    print(resultado["fontes"])


if __name__ == "__main__":
    # Ajuste o caminho abaixo para um PDF real antes de executar.
    CAMINHO_PDF_EXEMPLO = "documento_exemplo.pdf"
    PERGUNTA_EXEMPLO = "Qual é o objetivo principal descrito no documento?"

    if os.path.exists(CAMINHO_PDF_EXEMPLO):
        executar_pipeline(CAMINHO_PDF_EXEMPLO, PERGUNTA_EXEMPLO)
    else:
        print(
            f"Arquivo '{CAMINHO_PDF_EXEMPLO}' não encontrado.\n"
            "Coloque um PDF nesse caminho (ou ajuste CAMINHO_PDF_EXEMPLO) "
            "e rode novamente: python rag_pipeline.py"
        )