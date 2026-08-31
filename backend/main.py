"""
Main_exemplo.py — Exemplo de como plugar `pdf_loader.py` no programa
Main do projeto PAC-Resposta-de-Nimb.

Rode com:
    streamlit run Main_exemplo.py

Ajuste o import abaixo para o caminho real do Main.py do repositório e
substitua o comentário "chamar a cadeia RAG aqui" pela sua lógica
(LangChain + Ollama, conforme o RFC do projeto).
"""

import streamlit as st

from pdf_loader import botao_upload_livro, livro_carregado, obter_texto_livro, nome_livro

st.set_page_config(page_title="Respostas de Nimb", page_icon="📖")
st.title("📖 Respostas de Nimb")

st.caption(
    "O PDF fica apenas em memória durante esta sessão. "
    "Ao recompilar/reiniciar o app, será necessário enviá-lo novamente."
)

# 1) Botão de input do livro — sempre visível no topo
botao_upload_livro()

st.divider()

# 2) Trava: só libera a área de perguntas se houver PDF carregado
if not livro_carregado():
    st.info("🔒 Envie um arquivo PDF acima para liberar o envio de perguntas.")
    st.text_input("Sua pergunta:", disabled=True, placeholder="Aguardando o livro...")
    st.button("Enviar", disabled=True)
else:
    st.success(f"Livro atual: {nome_livro()}")
    pergunta = st.text_input("Sua pergunta:")

    if st.button("Enviar", disabled=(pergunta.strip() == "")):
        contexto = obter_texto_livro()

        # --------------------------------------------------------------
        # AQUI entra a chamada para a cadeia RAG (retrieval + LLM), usando
        # `contexto` (texto do PDF) e `pergunta` como entrada. Exemplo:
        #
        # from minha_cadeia_rag import responder
        # resposta = responder(pergunta=pergunta, contexto=contexto)
        # st.write(resposta)
        # --------------------------------------------------------------

        st.write("Resposta: (integrar aqui a cadeia RAG do projeto)")