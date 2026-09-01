# Projeto Respostas de Nimb

## Start do Projeto

### Acessar o ambiente

```
Acessar o ambiente venv
nimb

```

## Setup

```
python3.11 -m venv env
source env/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## Agenda

### Levantamento

- [Formulário publicado no Reddit](https://forms.cloud.microsoft/r/DxYnjK8A9F)

### Revisão de RAG

na mão, simples

- contexto: conteúdo e tamanho

### Indexing

loaders - text, web, pdf, Docling
Embeddings model, multilingual, context size, vector size
chunkning - chars vs tokens, estratégias, text, tokens, semantic
vector db - memory, local, remoto, cloud

### Retrieval

distance
quantidade
query

### Composição - Tecnologia

Python
[Ollama](https://ollama.com/download/windows)

[irm](https://ollama.com/install.ps1) | iex

Langchain


[Stitch](https://stitch.withgoogle.com/projects/4150170280574443902?pli=1)
### Augmentation

prompt template
context lenght

## Proximas etapas do desenvolvimento
Gerar script para separar e fragmentar livro confore sumário, validar se transformar pdf em MD vai servir ou ajudar na separação das informações
A quebra de partes deve ser genérica e de fácil reaplicação por conta dos livros disintos a serem usados
---
Gerar botão para entrada de livro e validação em lista dos títulos "autorizados' mapeados para serem usados dentro do sistema
---


### Evaluation

### Versão final completa

Ramires silva Paes > Avaliçao do trabalho
Observações: O trabalho está acima da média em organização e clareza, com uma base muito boa para evolução. Para chegar em um nível ainda mais alto (quase profissional), faltam: evidências mais concretas (dados, prints, pesquisa) maior profundidade técnica na solução

### Sugestão pares

Bruno Luis Pereira - Sugestão
Melhorar a descrição do problema, quem vai afetar/ajudar e definir melhor o objetivo final
