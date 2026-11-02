"""
Construtor do banco vetorial dos livros (roda à parte, fora da API).

Gera, a partir do PDF original de cada livro permitido:
- a entrada do livro no catálogo (impressão digital usada na validação);
- o banco vetorial do livro (Chroma), com página, capítulo e seção de cada trecho;
- as tabelas do livro em SQLite (colunas, grupos e linhas), ligadas aos trechos.

Uso (dentro de `backend/`, com o `.venv` ativo):

    python -m vector_builder --help

Detalhes em `vector_builder/README.md`.
"""

BUILDER_VERSION = "2.1"
