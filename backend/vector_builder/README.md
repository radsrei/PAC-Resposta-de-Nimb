# Construtor do banco vetorial (`vector_builder`)

O banco vetorial de cada livro é construído **uma vez, à parte da API**, a partir do PDF original. O usuário não gera embeddings: ao subir o PDF na tela, ele só prova que tem o livro. Se o arquivo for reconhecido, o banco daquele livro é liberado para ele.

```text
PDF original ──► vector_builder ──► vector_store/catalog.json      (impressão digital)
                                    vector_store/books/<id>/       (banco Chroma)

PDF do usuário ──► POST /api/rag/upload ──► compara com o catálogo ──► libera o acesso
                   (lido em memória e descartado)
```

## 1. Escolha do provedor de embeddings

Os embeddings (texto → vetor) podem ser gerados de dois jeitos. A escolha é feita na execução (`--provider`) ou no `backend/.env` (`EMBEDDING_PROVIDER`):

| Provedor | Onde o modelo roda | Instalação | Modelo padrão | Quando usar |
|---|---|---|---|---|
| `ollama` | servidor local do Ollama | leve (sem PyTorch) | `bge-m3` | quer evitar o PyTorch; o mesmo Ollama atende o construtor e, na etapa do RAG, o servidor |
| `sentence-transformers` | dentro do Python | PyTorch, cerca de 2 GB | `BAAI/bge-m3` | sem Ollama, ou com GPU NVIDIA (`--device cuda`) |

Os dois rodam o mesmo `bge-m3`, então a qualidade é equivalente; muda só quem executa o modelo.

> **Embeddings não são a LLM do chat.** A LLM que responde é o DeepSeek (API externa). O Ollama aqui só gera vetores, com um modelo próprio de embeddings (`bge-m3`, `nomic-embed-text`, `mxbai-embed-large`, `snowflake-arctic-embed2`). Modelos de chat (`llama3.1`, `qwen2.5`) até geram vetores, mas a busca fica muito pior.

Regras importantes:

- **Construção e consulta usam o mesmo modelo.** Provedor, modelo, dimensão, prefixos e endereço do Ollama ficam gravados no `manifest.json` de cada livro, e a consulta usa exatamente esses valores.
- **Trocar de modelo ou de provedor exige reconstruir** o banco do livro (`build` de novo). Vetores de modelos diferentes não se comparam.
- **Prefixos aplicados automaticamente:** alguns modelos exigem um prefixo no texto (`e5`: `passage:`/`query:`; `nomic-embed-text`: `search_document:`/`search_query:`; `mxbai-embed-large`: prefixo na pergunta). O construtor aplica e grava esses prefixos sozinho.

## 2. Instalação

### Setup automático

O script da raiz instala tudo: `.venv`, backend, construtor, Ollama e modelo, `.env` e front.

```powershell
# Windows (na raiz do projeto)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1                                # Ollama (padrão)
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings ollama -InstalarOllama
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 -Embeddings local              # sentence-transformers
```

```bash
# Linux / macOS
bash scripts/setup.sh                          # Ollama (padrão)
bash scripts/setup.sh --embeddings local       # sentence-transformers
```

| Opção (`setup.ps1` / `setup.sh`) | Uso |
|---|---|
| `-Embeddings` / `--embeddings` | `ollama` (padrão), `local` (sentence-transformers) ou `nenhum` |
| `-ModeloEmbeddings` / `--modelo-embeddings` | modelo de embeddings a baixar no Ollama (padrão `bge-m3`) |
| `-InstalarOllama` | instala o Ollama pelo winget, se faltar (só Windows) |
| `-SemFrontend` / `--sem-frontend` | não roda o `npm ci` |

O script pode ser executado de novo: só instala o que falta e nunca sobrescreve um `backend/.env` existente.

### Setup manual, com Ollama

```powershell
winget install -e --id Ollama.Ollama        # Linux: curl -fsSL https://ollama.com/install.sh | sh   macOS: brew install ollama
ollama pull bge-m3                          # modelo de embeddings (~1,2 GB)
ollama list                                 # confere se o modelo está disponível
.venv\Scripts\activate
pip install -r backend/vector_builder/requirements.txt
```

No `backend/.env`:

```ini
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=bge-m3
OLLAMA_URL=http://localhost:11434
```

O Ollama precisa estar aberto: o aplicativo do Windows sobe o servidor sozinho; no Linux/macOS, rode `ollama serve`. Se ele estiver em outra máquina, aponte `OLLAMA_URL` (ou `--ollama-url`) para ela.

### Setup manual, com sentence-transformers

```powershell
.venv\Scripts\activate
pip install -r backend/vector_builder/requirements-local.txt   # inclui o PyTorch (~2 GB)
```

No `backend/.env`: `EMBEDDING_PROVIDER=sentence-transformers`, com `EMBEDDING_MODEL` vazio para usar `BAAI/bge-m3`. O modelo (cerca de 2,3 GB) é baixado na primeira construção. No Windows, se o `pip` falhar com erro de caminho longo, ative os caminhos longos (PowerShell como administrador):

```powershell
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1 -PropertyType DWORD -Force
```

## 3. Comandos

Rode dentro de `backend/`, com o `.venv` ativo:

```bash
cd backend

# Revisar a extração e os trechos antes de gerar embeddings (rápido, não usa o provedor)
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --title "Tormenta20 - Livro Básico" --dry-run

# Cadastrar no catálogo e construir o banco (provedor do .env)
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --title "Tormenta20 - Livro Básico"

# Escolhendo o provedor na execução
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --provider ollama --model bge-m3
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --provider sentence-transformers --device cuda

# Reconstruir só o banco (ex.: trocar de modelo), sem mexer no catálogo
python -m vector_builder build "C:\Livros\T20 Basico.pdf" --id t20-basico --skip-register --provider ollama --model nomic-embed-text

# Só cadastrar/atualizar a impressão digital (sem embeddings)
python -m vector_builder register "C:\Livros\T20 Basico.pdf" --id t20-basico --title "Tormenta20 - Livro Básico"

# Testar se um PDF seria aceito, com o detalhe de cada verificação
python -m vector_builder check "C:\Downloads\copia.pdf"

# Ver o catálogo e o estado dos bancos (provedor e modelo de cada um)
python -m vector_builder list
```

| Opção (`build`) | Padrão | Uso |
|---|---|---|
| `--provider` | `EMBEDDING_PROVIDER` | `ollama` ou `sentence-transformers` |
| `--model` | `EMBEDDING_MODEL`, ou o padrão do provedor | modelo de embeddings |
| `--ollama-url` | `OLLAMA_URL` (`http://localhost:11434`) | servidor do Ollama |
| `--device` | automático | só sentence-transformers: `cpu` ou `cuda` |
| `--batch-size` | 16 | trechos por lote enviados ao modelo |
| `--chunk-size` | 1200 | tamanho máximo do trecho, em caracteres |
| `--overlap` | 200 | sobreposição entre trechos vizinhos |
| `--probes` | 8 | quantidade de frases de controle automáticas |
| `--probe PAGINA:TEXTO` | — | frase escolhida à mão (repita a opção); substitui as automáticas |
| `--skip-register` | — | reconstrói o banco sem mexer na entrada do catálogo |
| `--dry-run` | — | grava só os trechos em `vector_store/preview/<id>.chunks.jsonl` |

A pasta de saída é `VECTOR_STORE_DIR` (padrão `vector_store/` na raiz do projeto, fora do Git). Ela pode ficar em outro disco ou servidor: basta apontar a variável no `backend/.env`.

### Problemas comuns

| Mensagem | Solução |
|---|---|
| `Ollama não respondeu em http://localhost:11434` | abra o aplicativo do Ollama ou rode `ollama serve` |
| `Modelo 'bge-m3' não encontrado no Ollama` | `ollama pull bge-m3` |
| `Pacote 'sentence-transformers' não instalado` | `pip install -r backend/vector_builder/requirements-local.txt`, ou use `--provider ollama` |
| `N de M páginas sem texto` | o PDF é digitalizado: rode um OCR antes (ex.: `ocrmypdf entrada.pdf saida.pdf`) |
| `pip` falha com caminho longo no Windows | ative os caminhos longos (comando acima) |

## 4. Parte 1: validação do livro

A impressão digital de cada livro fica no `catalog.json`. A pontuação do PDF enviado é:

| Verificação | Peso | Regra |
|---|---|---|
| Frases de controle | 0,55 | proporção de frases encontradas na página indicada (± `probe_page_window`) |
| Número de páginas | 0,15 | diferença até `page_count_tolerance` |
| Tamanho do arquivo | 0,10 | diferença até `size_tolerance_pct` % |
| Metadados do PDF | 0,10 | título, autor, assunto, criador e produtor iguais |
| Tamanho da página | 0,10 | diferença até 2 pt |

- Um arquivo idêntico ao original (SHA-256 no catálogo) é aceito direto.
- Nos outros casos, o livro só é aceito com **pontuação ≥ `min_score`** (padrão 0,65) **e** pelo menos **`min_probes`** frases encontradas (padrão 60% delas). As frases provam que o conteúdo está no arquivo; metadados e tamanho, sozinhos, são fáceis de falsificar.
- A comparação de texto ignora acentos, pontuação, maiúsculas e hifenização, e tolera pequenas diferenças de extração (85% de semelhança).
- As frases automáticas ficam entre 5% e 95% do livro (evitam capa, créditos e índice) e precisam ser únicas no livro.
- "Página" é sempre a página física do arquivo, começando em 1, e não o número impresso.

O `catalog.json` pode ser editado à mão para ajustar tolerâncias (`size_tolerance_pct`, `page_count_tolerance`, `probe_page_window`, `min_probes`, `min_score`). Esses ajustes são mantidos quando o livro é recadastrado. Para aceitar outra edição do mesmo livro (outra tiragem, outro PDF), aumente `probe_page_window` e `page_count_tolerance`, e confira com `check`.

O usuário vê só o resultado de cada verificação. Os valores esperados (frases, hashes, tamanhos) nunca saem do servidor. O detalhe completo vai para o log da API.

## 5. Parte 2: o banco vetorial

Escolhas feitas para melhorar a qualidade em relação aos pipelines anteriores (`RAG_*`):

- **Extração por blocos (PyMuPDF)**, na ordem do conteúdo do PDF, o que respeita as colunas dos livros de RPG.
- **Cabeçalhos e rodapés repetidos removidos** (título do livro, número da página).
- **Hifenização e quebras de linha** dentro do parágrafo corrigidas.
- **Capítulo e seção** de cada trecho tirados do sumário (bookmarks) do PDF.
- **Trechos que respeitam parágrafos e frases**, sem misturar seções, com sobreposição entre vizinhos.
- **Cabeçalho de contexto no embedding** (`livro > capítulo > seção`), para a busca achar trechos que sozinhos não dizem do que falam.
- **Embeddings locais multilíngues** (`bge-m3`, pelo Ollama ou pelo sentence-transformers), normalizados, com distância cosseno.
- **Um banco por livro, versionado**: cada construção grava uma pasta `chroma-<data>` nova e só no fim troca o `manifest.json`. Uma construção interrompida não deixa banco pela metade, e dá para reconstruir com a API lendo a versão anterior.

Cada `books/<id>/` tem:

- `chroma-<data>/`: a coleção `chunks` da versão ativa (indicada em `manifest.json` → `chroma_dir`). Metadados de cada trecho: `book_id`, `chunk_index`, `page_start`, `page_end`, `chapter`, `section`.
- `chunks.jsonl`: os trechos em texto, para revisar a qualidade.
- `manifest.json`: a versão ativa, o provedor, o modelo, a dimensão e os prefixos de embeddings, os parâmetros e os totais. A consulta precisa usar o **mesmo provedor e modelo** registrados aqui.

Se o PDF não tiver camada de texto (digitalizado sem OCR), o construtor avisa. Rode um OCR antes (ex.: `ocrmypdf`).

## 6. Próxima etapa

Ligar a busca ao chat em `app/controllers/query_controller.py`:

1. pegar os livros liberados do usuário (`book_access`);
2. gerar o embedding da pergunta com o provedor e o modelo do `manifest.json`: `create_embedder_from_info(manifest["embedding"]).embed_query(pergunta)`, em `vector_builder/embeddings.py` (já aplica o `query_prefix`);
3. buscar os trechos mais próximos na versão ativa de cada livro (`book_catalog.chroma_path(id)`);
4. incluir os trechos no prompt e devolver livro, página e trecho na resposta.
