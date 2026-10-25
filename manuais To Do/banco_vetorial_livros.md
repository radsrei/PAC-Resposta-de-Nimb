# Banco vetorial dos livros — como foi construído e o que revisar

Escrito em 23/10/2026, junto com a versão 2.0 do construtor (`backend/vector_builder`). Este documento explica a arquitetura, as regras de extração e de divisão em trechos, os resultados medidos no Tormenta20 e, na seção 8, a lista do que ainda precisa ser revisado ou ajustado.

---

## 1. Visão geral

O banco é construído **uma vez por livro, fora da API**, a partir do PDF original. A API só lê o resultado.

```text
PDF do livro
   │
   ├─► register ──────────────► catalog.json            (impressão digital: validação do upload)
   │
   └─► perfil tipográfico ─► extração ─► entradas ─► trechos ─► embeddings (Ollama bge-m3) ─► Chroma
       profiles/<id>.json     extract.py   chunking.py      app/services/embeddings.py         store.py
```

| Etapa | Arquivo | O que faz |
|---|---|---|
| Perfil | `vector_builder/profile.py` + `profiles/t20-basico.json` | Diz o papel de cada fonte: título (e nível), número da página, rodapé, marca d'água, capitular. Sem perfil, deduz um automático pelas fontes. |
| Extração | `vector_builder/extract.py` | Lê o PDF linha a linha com a fonte de cada pedaço, remove margens, monta títulos, parágrafos e linhas de tabela. |
| Trechos | `vector_builder/chunking.py` | Agrupa o texto por **entrada** (cada magia, ameaça, raça, poder, quadro, tabela) e divide as entradas grandes. |
| Embeddings | `app/services/embeddings.py` | `bge-m3` pelo Ollama (padrão) ou sentence-transformers. Compartilhado pelo construtor e pela API (consulta). |
| Gravação | `vector_builder/store.py` | Grava a coleção Chroma, o `chunks.jsonl` e o `manifest.json`. |

---

## 2. Arquitetura do banco

```text
vector_store/                         (fora do Git; VECTOR_STORE_DIR)
├── catalog.json                      livros permitidos + impressão digital (validação do upload)
├── preview/<id>.chunks.jsonl         saída do --dry-run, para revisão
└── books/<id>/
    ├── manifest.json                 versão ativa, modelo de embeddings, perfil, totais por tipo
    ├── chunks.jsonl                  os mesmos trechos do Chroma, em texto, para revisão
    └── chroma-<data>/                coleção "chunks" (uma pasta por construção)
```

**Um banco por livro.** A liberação de acesso é por livro (`book_access`), então a consulta abre só os bancos dos livros liberados para o usuário. Cada construção grava uma pasta `chroma-<data>` nova e só no fim troca o `manifest.json`, então uma construção interrompida não estraga a versão em uso.

**Coleção `chunks` (Chroma, distância cosseno):**

| Campo | Exemplo | Uso previsto na consulta |
|---|---|---|
| `id` | `t20-basico:000641` | identificador estável dentro da versão |
| `document` | texto do trecho | vai para o prompt e para a citação |
| `embedding` | 1024 números (`bge-m3`) | busca por semelhança |
| `title` | `Erupção Glacial` | nome da entrada, exibido na fonte |
| `path` | `Descrição das magias > Erupção Glacial` | contexto e exibição |
| `chapter` | `Capítulo 4: Magia` | filtro e exibição |
| `kind` | `magia` | filtro (ex.: só `ameaca` quando a pergunta é sobre monstros) |
| `page_start` / `page_end` | `198` | página do arquivo PDF |
| `printed_start` / `printed_end` | `192` | **página impressa**, a que o usuário procura no livro |
| `book_id`, `chunk_index` | `t20-basico`, `641` | rastreio |

**Texto que gera o embedding** (o `document` não leva esse cabeçalho):

```text
Tormenta20 - Livro Básico > Capítulo 4: Magia > Descrição das magias > Erupção Glacial

Arcana 3 (Evocação)
Execução: padrão; Alcance: médio; ...
```

O cabeçalho ajuda a busca a achar trechos que sozinhos não dizem do que falam (ex.: a ficha de um monstro sem o nome no texto).

**Tipos (`kind`) do Tormenta20:** `magia`, `ameaca`, `raca`, `classe`, `personagem`, `pericia_poder`, `equipamento`, `regra`, `mestre`, `recompensa`, `cenario`, `quadro`, `tabela`, `geral` (Prefácio e Introdução).

---

## 3. O perfil tipográfico do Tormenta20

Arquivo: `backend/vector_builder/profiles/t20-basico.json`. Levantado medindo as fontes de todas as páginas do PDF.

| Fonte | Tamanho | Posição | Papel |
|---|---|---|---|
| `Helvetica` | 10 | rodapé | **marca d'água do comprador (nome + e-mail)** → descartada |
| `IowanOldStyle-Bold` | 10 | rodapé | nome do capítulo no rodapé → descartado |
| `Tormenta20-Regular` | 11 | rodapé | **número impresso da página** → guardado |
| `Tormenta20-*` | ≥ 28 | — | títulos decorativos de abertura; letra única = capitular (vai para o início do parágrafo) |
| `Tormenta20-Regular` | 26–27 | corpo | título nível 1 (`Anão`, `Atributos básicos`) |
| `Tormenta20-Regular` | 21 | corpo | título nível 2 (`Golem`, `Habilidades de Classe`, `Orcs`) |
| `Tormenta20-Regular` | 16 | corpo | título nível 3 = entrada (cada magia, `Orc Chefe`, `Atributos Mínimos`) |
| `SourceSansPro-Bold` | 13 | corpo | título de **quadro lateral** (`Familiares Arcanos`) |
| `IowanOldStyle-Bold` | 11–12 | corpo | legenda de **tabela** (`Tabela 1-1: Atributos`) |
| `IowanOldStyle-*` | 9,5 | corpo | texto principal (`body`) |

Outras regras do perfil:

- `skip_sections`: capítulos do sumário do PDF que não entram no banco (Sobrecapa, Capa, Créditos, Sumário, Playtesters, Índice Remissivo, Ficha de Personagem, 4ª Capa...). O **Apêndice: Lista de Condições** entra.
- `title_suffix: "^ND\s"`: o "ND 1/4" ao lado do nome do monstro é juntado ao título (`Glop ND 1/4`).
- `kinds`: regras, na ordem, para definir o tipo do trecho (título com `ND` → `ameaca`; texto começando com `Arcana 3` → `magia`; depois, pelo capítulo).

**Para outro livro da Jambô:** copie o perfil do T20 para `profiles/<id-do-livro>.json` e confira com `--dry-run`. A diagramação da editora tende a repetir as fontes. Para um livro sem perfil, o construtor avisa e usa o perfil automático (títulos = os 3 maiores tamanhos de fonte frequentes).

---

## 4. Regras da extração (`extract.py`)

1. **Linha e célula.** Linhas de um bloco na mesma altura formam uma linha da página. Se estão separadas por mais de 12 pt, são células de tabela e viram `a | b | c`.
2. **Duplicatas.** Texto desenhado duas vezes no mesmo lugar (efeito de contorno em quadros) é ignorado.
3. **Papel de cada pedaço de texto**, pela regra do perfil: título, número da página, descartado, capitular ou texto. Qualquer e-mail é apagado do texto, mesmo sem regra.
4. **Título.** Uma linha é título quando a primeira célula é toda em fonte de título e o resto é título ou o sufixo `ND`. Títulos seguidos do mesmo nível e bloco se juntam (`Definindo` + `seus atributos`).
5. **Parágrafo.** Uma linha continua o parágrafo anterior quando:
   - a frase anterior não terminou (não acaba em `. ! ? : ;`), mesmo mudando de bloco, coluna ou página; ou
   - está no mesmo bloco e sem recuo.

   Recuo com a frase anterior terminada abre parágrafo novo.
6. **Hifenização.** `ex-` + `posta` vira `exposta` quando a palavra continua em minúscula, inclusive entre colunas e páginas.
7. **Capítulo** de cada página pelo sumário (nível 1) do PDF. **Página impressa** pelo número do rodapé. Páginas sem número (aberturas de capítulo) recebem o valor deduzido da página vizinha (no T20, impressa = arquivo − 6).

## 5. Regras dos trechos (`chunking.py`)

1. **Entrada.** Cada título abre uma entrada. O caminho é a pilha de títulos (nível 1 > 2 > 3), zerada a cada capítulo.
2. **Desvios: tabela e quadro.** O título de tabela ou quadro abre uma entrada sem alterar a pilha do texto principal.
   - A **tabela** termina quando volta o texto principal (fonte do corpo).
   - O **quadro** termina na troca de página ou no próximo título.

   Depois do desvio, o texto principal continua numa entrada com o caminho anterior.
3. **Entradas pequenas** (< `--min-chars`, 120) são unidas à entrada anterior do mesmo capítulo, com o título no início (`Título: texto`).
4. **Entradas grandes** (> `--chunk-size`, 2400 caracteres) são divididas por parágrafo. Um parágrafo maior que o limite é dividido por frase. Todos os pedaços mantêm o mesmo título e caminho. O último parágrafo de até `--overlap` (300) caracteres se repete no pedaço seguinte.
5. **Tipo** pelo perfil (`kinds`). Tabela e quadro mantêm o próprio tipo.

Por que 2400 caracteres: o `bge-m3` aceita até 8.192 tokens, então o limite vem da busca e do prompt, não do modelo. Cerca de 600 tokens por trecho cabem em uma magia ou ficha inteira e permitem enviar 5 trechos à LLM com folga.

---

## 6. Resultado no Tormenta20 (`Livros/T20_teste.pdf`, 407 páginas)

| Medida | Antes (v1, por página e tamanho) | Agora (v2, por entrada) |
|---|---|---|
| Trechos | 1.568 | 1.313 |
| Trechos com o **e-mail do comprador** | 26 | **0** (a construção é interrompida se aparecer) |
| Trechos do Índice Remissivo | 59 | 0 (17 páginas ignoradas) |
| Seção certa por trecho | não: "Golem" continha Hynne; 205 magias numa só seção | sim: 1 entrada = 1 magia, monstro, raça... |
| Título colado no texto anterior | sim (`…círculo. Erupção Glacial Arcana 3`) | não |
| Cabeçalho "Capítulo Um" dentro do texto | sim | 0 ocorrências |
| Palavra quebrada entre blocos (`ex-` / `posta`) | sim | 0 ocorrências |
| Tabelas | números soltos sem cabeçalho | linhas `Atributo \| Custo \| Rolagem` |
| Página citada | só a do arquivo | arquivo **e impressa** (todos os trechos) |
| Tipo do trecho | — | 13 tipos |

Exemplos do resultado (arquivo `vector_store/books/t20-basico/chunks.jsonl`):

- `[magia] Descrição das magias > Bola de Fogo`, p. impressa 182: "Arcana 2 (Evocação) / Execução: padrão; Alcance: médio; Área: esfera com 6m de raio…"
- `[ameaca] Criaturas > Orcs > Orc Chefe ND 2`, p. 286: a ficha completa num trecho só.
- `[quadro] Arcanista > Habilidades de Classe > Familiares Arcanos`, p. 38.
- `[tabela] … > Tabela 1-1: Atributos`, p. 17: `–2 | — | 7 ou menos`.

**Construção completa:** 1.313 trechos e embeddings `bge-m3` (Ollama, CPU) em **104 s**. Totais por tipo: magia 226, personagem 225, ameaça 150, perícia/poder 131, mestre 126, cenário 86, regra 71, quadro 69, tabela 60, equipamento 55, recompensa 54, classe 28, raça 18, geral 14.

**Teste rápido de busca** (só vetores, 3 primeiros resultados, sem LLM):

| Pergunta | 1º resultado | Avaliação |
|---|---|---|
| Quanto de dano causa a Bola de Fogo? | `[magia] Bola de Fogo`, p. 182 (0,63) | ✅ |
| Quais são os atributos de um glop? | `[ameaca] Glop ND 1/4`, p. 286 (0,50) | ✅ |
| Como funciona o familiar do arcanista? | `[quadro] Familiares Arcanos`, p. 38 (0,63) | ✅ |
| Quanto dinheiro inicial um personagem de 5º nível recebe? | `Frutos do Trabalho`, p. 86 | ❌ a `Tabela 3-1: Dinheiro Inicial` (p. 140) não aparece nos 3 primeiros |
| Quais os ajustes de atributo do anão? | `[tabela] Tabela 1-2: Raças`, p. 18; `Anão > Habilidades de Raça`, p. 20 em 3º | ✅ |
| O que acontece quando um personagem fica fatigado? | `[regra] Lista de Condições`, p. 395 (0,64) | ✅ |

A falha está em tabela, que é número e pouco texto. É o caso que a busca híbrida (palavras + vetores) deve resolver.

---

## 7. Como rodar

```powershell
# raiz do projeto, uma vez
.venv\Scripts\python -m pip install -r backend\requirements.txt -r backend\vector_builder\requirements.txt
ollama pull bge-m3

cd backend
# revisar os trechos antes (rápido, sem embeddings)
..\.venv\Scripts\python -m vector_builder build ..\Livros\T20_teste.pdf --id t20-basico --title "Tormenta20 - Livro Básico" --dry-run
# construir (provedor padrão: ollama)
..\.venv\Scripts\python -m vector_builder build ..\Livros\T20_teste.pdf --id t20-basico --skip-register
..\.venv\Scripts\python -m vector_builder list
```

Ambiente verificado em 23/10/2026: `.venv` com Python 3.14.5, `pymupdf` e `chromadb 1.5.9` instalados sem erro, e Ollama com `bge-m3`. O provedor padrão passou a ser `ollama` (`config.py` e `.env.example`).

---

## 8. To Do — revisar e ajustar

### Qualidade dos trechos

- [ ] **Revisar o `chunks.jsonl` por amostragem**, 10 trechos de cada tipo, procurando texto fora de ordem, título errado ou quadro misturado com o texto principal.
- [ ] **Tabelas com cabeçalho em fonte de corpo ou estreito:** o cabeçalho às vezes não se separa em células (`Nível Dinheiro Inicial (T$)`). Avaliar o Docling (`Convert_file/`) só nas ~60 páginas de tabela, ou ajustar à mão as tabelas mais consultadas (armas, armaduras, itens, tesouro).
- [ ] **Tabela seguida de entrada pequena:** a `Tabela 3-1` absorveu o texto curto "Usando & Carregando" (regra das entradas pequenas). Avaliar não unir entradas pequenas a tabelas.
- [ ] **Quadro que passa de página** termina na troca de página. Conferir se algum quadro grande foi cortado.
- [ ] **Fichas de monstro** saem com as linhas do bloco de estatísticas num parágrafo só (`Monstro Pequeno Iniciativa +0, …`). Funciona para a busca. Avaliar quebrar por campo (`Defesa`, `Pontos de Vida`…) para a exibição.
- [ ] **Lista de raças e classes no perfil** (`kinds`) está escrita à mão. Conferir se falta alguma.
- [ ] **Perfil automático** não foi testado com outro livro. Testar antes de indexar um livro sem perfil.

### Validação do livro (catálogo)

- [ ] **Escolher as frases de controle à mão** (`--probe PAGINA:TEXTO`). Três das automáticas são frágeis: `"Capítulo Um Golpe Pessoal…"` (cabeçalho colado), `"peculiari dades"` (palavra partida) e `"2D Na rolagem…"`.
- [ ] **Calibrar com a cópia de outro comprador.** O SHA-256 nunca coincide, porque a marca d'água muda por comprador. Rodar `check` e ajustar `min_score` e `probe_page_window`.

### Consulta (P0.1, ligada em 24/10/2026)

- [x] **E1** (24/10/2026): a consulta usa `settings.ollama_url`; o `manifest.json` não grava mais o endereço do Ollama (o `base_url` de manifests antigos é ignorado). `query_embedder()` em `app/services/embeddings.py`.
- [x] **E2** (24/10/2026): `embeddings.py` movido para `app/services/`; `SystemExit` trocado por `EmbeddingError` (HTTP 503), incluindo falha de rede e tempo esgotado no meio da consulta (30 s).
- [x] **Busca híbrida** (24/10/2026):
  - BM25 em memória sobre o `chunks.jsonl` (`app/services/lexical.py`): ignora acentos e plurais simples, o título conta em dobro, e o índice é refeito só quando o banco muda.
  - Combinada com a busca vetorial por RRF, com peso 0,5 para as palavras (`RAG_LEXICAL_WEIGHT`) e 20 candidatos de cada busca (`RAG_CANDIDATES`).
  - Todo trecho, inclusive os achados só por palavra, passa pelo mesmo filtro de similaridade vetorial.
  - Desliga com `RAG_HYBRID=false`.
- [ ] **Citação:** exibir os dois últimos níveis do `path` + `printed_start` ("Anão > Habilidades de Raça, p. 20"). O `title` sozinho às vezes é genérico (`Habilidades de Raça`, `Habilidades de Classe`). Usar `kind` para filtrar quando a pergunta indicar o tipo.
- [ ] **Tabelas na busca:** com a híbrida, a `Tabela 3-1` passou a aparecer em 3º lugar e a resposta ficou certa (T$ 2.000 no 5º nível). Ainda vale dar às tabelas um texto de embedding com a legenda e o assunto, para subirem ao 1º lugar.
- [ ] **Perguntas que dependem de dois trechos:** "dano **e custo** da Bola de Fogo" traz a magia (Arcana 2), mas não a regra de custo por círculo (p. 170), então a LLM diz que o custo não está no trecho. Perguntando só o custo, a resposta vem certa (3 PM). Possível melhoria: buscar também pelo termo da regra (círculo → custo) ou aumentar o `RAG_TOP_K`.
- [x] **Busca ligada ao chat** (24/10/2026), em `app/services/retrieval.py`:
  - busca só nos livros de `book_access` (o `bookIds` do front só restringe);
  - junta a pergunta anterior da sessão à busca, para resolver continuações;
  - descarta trechos abaixo de `RAG_MIN_SIMILARITY` (0,45, calibrado) e envia até `RAG_TOP_K` (5) trechos ao prompt;
  - o prompt manda responder só com os trechos e citar (Livro, p. N);
  - a resposta e o histórico trazem `bookTitle`, `page` impressa, `similarity`, `quote` e `sources`.
- [x] `chromadb` no `backend/requirements.txt`. No compose, o volume do `vector_store` ficou sem `:ro` (testado: o Chroma não abre pasta somente leitura), com `chown 10001` no deploy.
- [x] **Teste com o DeepSeek real** (24/10/2026): 10/10 casos.
  - As respostas citam as páginas e não inventam regras.
  - As perguntas fora do Tormenta20 (receita, capital da França, piada, D&D 5e e mudança de assunto no meio da conversa) recebem 422.
  - Usuário sem livro recebe 428.
- [x] **Escopo e livro obrigatório (D6):** veja `proximos_passos.md`. Mensagens em `app/services/prompts.py` (`BOOK_REQUIRED`, `OUT_OF_SCOPE`).
- [x] **Primeira pergunta lenta:**
  - A 1ª pergunta tinha ~10 s fixos: verificar o modelo (2,3 s), o Ollama carregá-lo (6,2 s) e abrir o Chroma (1,3 s).
  - Agora a API aquece em segundo plano ao subir (`retrieval.warm_up`) e o Ollama mantém o modelo na memória (`OLLAMA_KEEP_ALIVE=-1`).
  - Resultado: 1ª pergunta em 3–5 s.
- [x] **`RAG_MIN_SIMILARITY` calibrado em 0,45** (24/10/2026, `evaluate`):
  - A melhor similaridade das perguntas do livro ficou entre 0,47 e 0,76; a das fora do tema, entre 0,34 e 0,53. As faixas se sobrepõem.
  - Com 0,45, 100% das perguntas do livro são respondidas e 50% das fora do tema são barradas antes da LLM; o resto a LLM recusa.
  - Com 0,48, cai uma pergunta do livro (grifo, 0,469).
  - Margem pequena: recalibrar quando o conjunto crescer.
- [x] **Teste com o DeepSeek real, com busca híbrida:** 12/12 casos. As perguntas de custo por círculo e de dinheiro inicial passaram a ser respondidas corretamente.
- [ ] **Imagem Docker com `chromadb`:** não foi construída nesta máquina. Conferir o tamanho e a instalação no Python 3.12.

### Avaliação

- [x] **Conjunto de perguntas do T20** (24/10/2026): `vector_builder/eval/t20-basico.json`.
  - 48 perguntas, com página impressa e título esperados, cobrindo magia, ameaça, raça, classe, quadro, origem, deus, poder, tabela, regra, recompensa, cenário e mestre.
  - Mais 14 perguntas fora do tema, incluindo D&D e Pathfinder.
  - O comando valida o gabarito contra o banco antes de medir.
- [x] **`python -m vector_builder evaluate`:** recall@1/3/5 e MRR por página (e no critério estrito, página e título), busca vetorial x híbrida, e uma tabela de calibração do mínimo.
  - Resultado atual (estrito): vetorial 85% em 1º, 98% no top-5, MRR 0,91; **híbrida 88% em 1º, 100% no top-5, MRR 0,93**.
- [ ] **Ampliar o conjunto com perguntas de jogadores reais.** As atuais foram escritas a partir dos trechos e tendem a repetir as palavras do livro, o que deixa o resultado otimista. Fontes possíveis: o formulário do Reddit em `docs/` e o grupo de testes.
- [ ] Medir a **resposta final** (RNF04 do RFC: 85% de acerto avaliado por especialistas). O `evaluate` mede só a busca.

### Dados e direitos

- [ ] O PDF em `Livros/` é uma cópia licenciada com nome e e-mail do comprador. Não versionar (já está no `.gitignore`) e não enviar a outras pessoas.
- [ ] Decidir o uso restrito ou público (D4 do `proximos_passos.md`) antes de levar o `vector_store/` para o servidor.

### Ambiente

- [ ] O `.venv` local usa Python 3.14 e o Docker usa 3.12. Fixar as versões (`requirements.lock`) e testar a construção também no 3.12.
