prompt_rag = f"""
Baseado ESTRITAMENTE no seguinte contexto, responda à pergunta do usuário.
Se a resposta não puder ser encontrada no contexto, diga que não há informação suficiente.

Contexto:
{contexto_recuperado}

Pergunta: {pergunta_usuario}

Resposta (baseada apenas no contexto):
"""