


# pip install --upgrade pinecone
# pip install pinecone
# pip install -qU langchain langchain-openai langchain-community pypdf
# pip install -U langchain-community langchain-huggingface replicate langchain_milvus docling
# pip install langchain langchain-classic langchain-deepseek faiss-cpu unstructured chromadb 
# 


import pinecone
from langchain_huggingface import HuggingFaceEmbeddings
from dotenv import load_dotenv
load_dotenv()

from pinecone import Pinecone
pc = Pinecone(api_key="API_PINECONE")

assistant = pc.assistant.create_assistant(
    assistant_name="example-assistant", 
    instructions="Answer in polite, short sentences. Use American English spelling and vocabulary.", 
    timeout=30 # Wait 30 seconds for assistant operation to complete.
)