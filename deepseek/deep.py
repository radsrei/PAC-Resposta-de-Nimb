import os
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class RAGDeepseek:
    def __init__(self, api_key, base_url="https://api.deepseek.com"):
        """
        Inicializa o cliente Deepseek e prepara a estrutura RAG
        """
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.document_chunks = []  # Lista para armazenar os pedaços de texto
        self.chunk_embeddings = []  # Lista para armazenar embeddings dos chunks
        
    def chunk_document(self, text, chunk_size=500, overlap=50):
        """
        Divide um documento longo em pedaços menores para indexação
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        return chunks
    
    def create_embedding(self, text):
        """
        Cria um embedding para um texto usando a API do Deepseek
        Nota: Deepseek não possui endpoint próprio de embedding,
        você precisaria usar outro modelo (ex: da OpenAI ou locais)
        """
        # Placeholder - você precisará implementar com outro serviço
        # ou usar uma biblioteca local como sentence-transformers
        pass
    
    def index_documents(self, documents):
        """
        Indexa múltiplos documentos no banco vetorial
        """
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)
        
        self.document_chunks = all_chunks
        # Aqui você adicionaria a criação dos embeddings
        print(f"Indexados {len(all_chunks)} chunks de documentos")
        
    def retrieve_relevant_chunks(self, query, top_k=3):
        """
        Recupera os chunks mais relevantes para a query
        """
        # Placeholder - implementar busca por similaridade
        # Retorna os primeiros chunks como exemplo
        return self.document_chunks[:top_k]
    
    def query(self, user_question, system_prompt=None):
        """
        Executa o pipeline completo de RAG: recupera chunks relevantes
        e gera resposta usando o Deepseek
        """
        # 1. Recuperar chunks relevantes
        relevant_chunks = self.retrieve_relevant_chunks(user_question)
        
        # 2. Construir contexto a partir dos chunks recuperados
        context = "\n\n".join(relevant_chunks)
        
        # 3. Construir prompt com contexto
        if system_prompt is None:
            system_prompt = """Você é um assistente útil que responde perguntas baseado 
            exclusivamente no contexto fornecido. Se a informação não estiver no contexto, 
            diga que não possui informação suficiente."""
        
        # 4. Chamar API do Deepseek (como no seu exemplo)
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Contexto:\n{context}\n\nPergunta: {user_question}"}
            ],
            stream=False
        )
        
        return response.choices[0].message.content

# Exemplo de uso
if __name__ == "__main__":
    # Inicializar RAG com Deepseek
    rag = RAGDeepseek(
        api_key=os.environ.get('DEEPSEEK_API_KEY'),
        base_url="https://api.deepseek.com"
    )
    
    # Indexar alguns documentos de exemplo
    documentos = [
        "Deepseek é uma empresa de IA focada em modelos de linguagem eficientes.",
        "A API da Deepseek permite integração com sistemas RAG para busca contextual.",
        "RAG combina recuperação de informação com geração de texto por LLMs."
    ]
    
    rag.index_documents(documentos)
    
    # Fazer uma pergunta
    resposta = rag.query("O que é Deepseek e como usar com RAG?")
    print(resposta)