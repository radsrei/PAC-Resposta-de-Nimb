## Inicio

python -m venv .venv

## PowerShell

.venv\Scripts\activate

## Bash

pip install -r req_gpt.txt

python app.py

## Pipe

                         DOCUMENTO PDF
                              |
                              v
                     +----------------+
                     |  PyPDFLoader   |
                     +----------------+
                              |
                              v
                     Documento / Página
                              |
                              v
                  +-----------------------+
                  | Metadata              |
                  |                       |
                  | documento             |
                  | página                |
                  | capítulo              |
                  | subcapítulo           |
                  +-----------------------+
                              |
                              v
                  RecursiveCharacter
                     TextSplitter
                              |
                              v
                         CHUNKS
                              |
                              v
                    Embedding Model
                              |
                              v
                    Vetores semânticos
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
     Capítulo 1          Capítulo 2          Capítulo 3
          |                   |                   |
     +----+----+         +----+----+         +----+----+
     |         |         |         |         |         |
    1.1       1.2       2.1       2.2       3.1       3.2
     |         |         |         |         |         |
     v         v         v         v         v         v
  Chroma    Chroma    Chroma    Chroma    Chroma    Chroma


## Expectativa do banco

dados_rag/
│
├── catalogo.sqlite
│
├── capitulo_1/
│   ├── subcapitulo_1_1/
│   └── subcapitulo_1_2/
│
├── capitulo_2/
│   ├── subcapitulo_2_1/
│   └── subcapitulo_2_2/
│
└── capitulo_3/
    ├── subcapitulo_3_1/
    └── subcapitulo_3_2/

### Gravação
{
    "document_name": "manual.pdf",
    "document_path": "/documentos/manual.pdf",
    "page": 37,
    "chapter": "capitulo_3",
    "subchapter": "subcapitulo_3_2",
    "chunk_id": "chunk_000123",
    "chunk_hash": "..."
}

### Apresentação

Resposta:
...

Fontes:

manual.pdf
Página: 37
Capítulo: 3
Subcapítulo: 3.2

