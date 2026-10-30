# Tabelas do livro em SQL e sorteio de tesouro

Este documento descreve como as tabelas do livro passaram a ser guardadas em estrutura (SQLite), como a busca do chat usa essas tabelas e como funciona o sorteio de tesouro. Ao final está a lista do que falta revisar.

## 1. Visão geral

Antes, cada tabela do livro virava um trecho de texto com as células separadas por `|`. A busca achava a tabela, mas a LLM recebia um pedaço sem cabeçalho nem grupo, às vezes cortado no meio.

Agora o construtor (`python -m vector_builder build`) gera, junto com o banco vetorial:

| O quê | Onde | Para quê |
|---|---|---|
| Trecho da tabela (como antes) | Chroma + `chunks.jsonl` | a busca achar a tabela pelo assunto |
| **Um trecho por linha da tabela** (`kind = linha_tabela`) | Chroma + `chunks.jsonl` | a busca achar o item exato ("adaga", "anel do sustento") |
| **Tabelas em estrutura** | `vector_store/books/<livro>/tables-<data>.sqlite` | entregar à LLM a tabela organizada, com cabeçalho, grupo e página |

A API cria, a partir desse SQLite, o **espaço do tesouro**: `backend/data/tesouro/<livro>.sqlite`. É uma cópia só com as tabelas do sorteio e as criaturas, refeita sozinha quando o livro é reconstruído.

```
PDF ──► extract.py ──► chunking.py ──► trechos de texto ─┐
                    └► tables.py ───► tabelas ──┬────────┼► Chroma (embeddings) + chunks.jsonl
                                                ├► trechos por linha
                                                └► tables-<data>.sqlite
                                                        │
API: busca ──► trecho de tabela ou de linha ──► tabela organizada no prompt
API: tesouro ──► data/tesouro/<livro>.sqlite ──► sorteio ──► histórico (nimb.db)
```

## 2. Correções na extração das tabelas

| Problema | Causa | Correção |
|---|---|---|
| Tabelas 8-7 a 8-15 (itens mágicos), 3-8 e 6-7 não existiam no banco | o cabeçalho (`d% Encanto Efeito`) usa a fonte do texto corrido e encerrava a tabela | a tabela só termina com texto corrido que não seja linha de tabela (`chunking.py`) |
| Tabelas pequenas sumiam dentro do trecho anterior (3-4 Munições, 4-1) | regra das entradas pequenas | tabelas nunca são juntadas a outros trechos |
| Colunas coladas (`CríticoAlcance`, `01-05 Ameaçadora`, `MaiorValor`) | o espaço largo (tab) entre colunas era descartado; colunas estreitas ficam a menos de 12 pt | o tab separa células; na fonte de tabela o limite é 5 pt; distância medida do último caractere visível |
| Cabeçalho da 8-1 colado no título | a regra que junta "ND X" ao nome das criaturas | só junta quando a linha tem uma célula |
| Palavras coladas no texto corrido (`CorpoAdaga`, `Símbolodo`, `Tormenta20é`) | o espaço entre duas partes de texto era descartado | o espaço é mantido |
| Partes de uma linha fora de ordem (nota antes de `91-100` na 8-5) | ordem do PDF | as partes de cada linha são ordenadas da esquerda para a direita |

Para conferir que o texto corrido não piorou, os trechos foram comparados com os da construção anterior: nenhuma palavra nova partida; as diferenças são linhas de tabela que mudaram de lugar e colagens corrigidas.

## 3. Montagem das tabelas (`vector_builder/tables.py`)

Cada célula guarda o início e o fim da sua posição na página. A partir das linhas de cada tabela:

- **Cabeçalho**: as linhas em negrito antes do primeiro dado. Partes empilhadas na mesma coluna são juntadas ("Nível de" + "personagem"). Um cabeçalho colado que cobre duas colunas de dados é separado (`d% Arma`).
- **Alinhamento**: cada célula vai para a coluna mais próxima pelo início, pelo centro ou pelo fim (as colunas do livro são centralizadas, à esquerda ou à direita).
- **Subtabelas lado a lado**: quando o primeiro nome do cabeçalho se repete (`d% | Arma | d% | Arma`), cada metade vira uma subtabela. Se os nomes diferem (`Armas`, `Armaduras/Escudos`, `Esotéricos` na 8-5), cada uma vira um grupo.
- **Grupos**: linha em negrito com uma célula (`Corpo a Corpo — Leves`), ou uma por subtabela (`Equipamento de Aventura | Vestuário`). Cabeçalhos que mudam só a primeira coluna (`Armas Simples`, `Armas Marciais`) também viram grupo, e a coluna passa a se chamar `Nome`.
- **Células em várias linhas**: a continuação alinhada a uma coluna é somada à célula da linha anterior (`Juncos (Sobrevivência)`, preços das poções).
- **Primeira coluna em branco** herda o valor de cima (o ND na Tabela 8-1).
- **Notas**: linhas longas ou com marcador colado (`1Conta como duas melhorias`, `+%Na rolagem...`) viram notas da tabela; o marcador do item (`Atroz1`) é retirado e a nota fica ligada à linha.
- **Continuação**: as partes "(Continuação)" entram na mesma tabela.

### Estrutura do SQLite (`tables-<data>.sqlite`)

```sql
book_tables (key PK, number, title, label, chapter, page_start, page_end,
             printed_start, printed_end, columns JSON, notes JSON, chunks JSON)
table_rows  (id PK, table_key → book_tables, position, grp, name, cells JSON,
             notes JSON, page, printed, chunk_index, text)
table_rows_fts  -- busca por texto (FTS5, sem acentos) em name + text
entries     (chunk_index PK, title, path, chapter, kind, printed_start, table_key)
```

- `key` é o número da tabela (`8-1`) ou o título sem acento, para as tabelas sem número (`poderes-concedidos`).
- `cells` é um objeto `{coluna: valor}`; em tabelas com subtabelas, cada linha tem as colunas da sua subtabela.
- `chunk_index` liga a linha ao trecho dela no Chroma; `book_tables.chunks` liga a tabela aos trechos de tabela.
- `entries` é o índice de todas as entradas do livro (magias, ameaças, poderes…) com o trecho de cada uma, para ligar uma linha de tabela à descrição completa.
- O arquivo é versionado como a pasta do Chroma (`tables_db` no `manifest.json`), com troca atômica.

## 4. A tabela na resposta do chat (etapa A)

Em `app/services/retrieval.py`:

1. A busca híbrida devolve trechos de texto, de tabela e de linha.
2. Trechos da mesma tabela viram **uma passagem só**: as linhas encontradas se somam; se veio o trecho da tabela inteira, vale a tabela toda.
3. O texto da passagem é trocado pela tabela organizada do SQLite (`app/services/book_tables.py`): título, página, grupos, cabeçalho e as notas.
   - Linhas encontradas → só essas linhas, com o cabeçalho (`Tabela 3-3: Armas (p. 144-145) — 2 de 47 linhas`).
   - Tabela inteira → a tabela toda, se couber em 6.000 caracteres; senão fica o trecho original.

A LLM continua sem escrever SQL: recebe as linhas certas e completas. A página citada é a da linha.

## 5. Sorteio de tesouro

### Espaço próprio

`backend/data/tesouro/<livro>.sqlite` (pasta configurável em `TREASURE_DIR`), fora do Git, como o `nimb.db`. No Docker fica no volume `nimb_data`.

| Tabela | Conteúdo |
|---|---|
| `treasure_nd` | Tabela 8-1: ND, coluna (dinheiro/itens), faixa de d% e resultado |
| `roll_tables` | 8-2 a 8-15 por papel: riqueza (menor/média/maior), diverso, equipamento (arma/armadura/esotérico), superior, encantos, específicos, poções, acessórios (menor/médio/maior); com efeito, preço e notas |
| `creatures` | criaturas do Capítulo 7: nome, ND e tipo de tesouro da ficha (Nenhum/Padrão/Metade/Dobro + extras) |
| `meta` | livro, `built_at` do banco de origem e fonte (tabela e página) de cada papel |

É montado pela API a partir do banco do livro, na subida (`treasure_store.prepare_all`) ou no primeiro sorteio, e refeito quando o `built_at` do livro muda. O mapa "papel → tabela" de cada livro fica em `SOURCES` (`app/services/treasure_store.py`).

### Regras aplicadas (`app/services/treasure.py`, Capítulo 8 do livro)

- **Tipo de tesouro**: o da ficha da criatura, ou o informado. Nenhum = sem sorteio; Metade = dinheiro pela metade; Dobro = duas rolagens em cada coluna.
- **Tabela 8-1**: d% na linha do ND, uma vez na coluna Dinheiro e outra na coluna Itens. ND acima da tabela usa a última linha (com aviso).
- **Moedas**: `2d6+1x100 T$` → (2d6+1) × 100. TC = 0,1 T$, TO = 10 T$.
- **Riquezas**: quantidade, d% na coluna da categoria da 8-2, valor pelos dados da tabela e exemplos.
- **Diverso**: 8-3.
- **Equipamento**: 1d6 para o tipo (1–3 arma, 4–5 armadura/escudo, 6 esotérico) e 8-4.
- **Superior (N melhorias)**: item da 8-4 e uma rolagem na 8-5 por melhoria, sem repetir; "conta como duas" ocupa duas; material especial rola 1d6 para o material.
- **Poções**: quantidade e d% na 8-12.
- **Mágico (menor/médio/maior)**: 1d6 para o tipo (1–2 arma, 3 armadura/escudo, 4–6 acessório). Arma e armadura: item da 8-4 e 1, 2 ou 3 encantos (8-8 / 8-10); "conta como dois" vale dois e é rolado de novo em item menor; "apenas escudos" é rolado de novo em armadura; "item específico" troca tudo por um da 8-9 / 8-11. Acessório: 8-13, 8-14 ou 8-15.
- **`+%`**: +20 no d% de riqueza ou poção (máximo 100). **`2D`**: rola 2d6 para o tipo e devolve as duas opções para o jogador escolher.
- Cada resultado traz a rolagem, os detalhes e a fonte (tabela e página). Os dados usam `secrets.SystemRandom`.

### API (login obrigatório; o usuário precisa ter liberado o livro)

| Rota | Uso |
|---|---|
| `POST /api/tesouro/sortear` | `{"creature": "necromante"}` ou `{"nd": "7", "treasureType": "dobro"}` (`bookId` opcional). Devolve as rolagens, as recompensas, o total em T$ e as fontes, e grava no histórico |
| `POST /api/tesouro/sortear-grupo` | `{"creatures": [{"creature": "Necromante", "quantity": 2, "rolls": [{"money": [100], "items": [null]}]}]}`: uma rolagem por unidade (até 10 criaturas e 20 de cada). `rolls` traz, por unidade, os d% da Tabela 8-1 rolados na mesa (dois por coluna no tipo Dobro; `null` = automático). Devolve os resultados por criatura, o total e marca cada d% como `manual` ou não |
| `GET /api/tesouro/criaturas?q=dragao` | criaturas com ND e tipo de tesouro (para autocompletar) |
| `GET /api/tesouro/nds` | NDs da Tabela 8-1 |
| `GET /api/tesouro/historico?limit=20` | últimos sorteios do usuário (tabela `treasure_rolls` do `nimb.db`) |

Sem livro liberado a resposta é **428**, como nas perguntas; criatura ou ND inexistente, **404**/**400**.

### Tela (`frontend/V2 - front Studio/src/components/modals/TreasureModal.tsx`)

- Aberta pelo botão **Sorteio de Tesouro** na barra lateral esquerda (abaixo de "Nova Sinapse Neural").
- **Criaturas**: campo de busca com lista suspensa (nome, ND e tipo de tesouro; setas e Enter funcionam). Escolher a mesma criatura de novo soma 1 na quantidade; a quantidade também muda pelos botões − / + ou digitando (1 a 20).
- **Rolagem**: *automática* ou *informar resultados*. No modo informado aparece, para cada unidade, o d% de Dinheiro e de Itens da Tabela 8-1 (dois de cada no tipo Dobro; 00 = 100; vazio = automático). Criaturas com tesouro Nenhum ou especial não têm campos. As rolagens seguintes (riquezas, itens, encantos) continuam automáticas.
- **Resultado**: total geral e por criatura, e para cada unidade o d% (informado ou automático), o resultado da tabela, as recompensas com detalhes, as opções 2D e as fontes.
- **Saída**: Esc ou X abrem a confirmação "Sair do sorteio?" (Esc de novo volta ao sorteio). Clicar fora não fecha. Os sorteios feitos já estão gravados no histórico.

## 6. Como rodar

```bash
cd backend
python -m vector_builder build ../Livros/T20_teste.pdf --id t20-basico --skip-register --dry-run   # revisar: preview/t20-basico.tables.sqlite
python -m vector_builder build ../Livros/T20_teste.pdf --id t20-basico --skip-register             # construir
python -m vector_builder evaluate                                                                  # medir a busca
```

Depois de reconstruir, reinicie a API: ela refaz o espaço do tesouro sozinha. No servidor, basta enviar a pasta `vector_store` como antes.

## 7. Resultado no Tormenta20

Construção de 30/10/2026 (`Livros/T20_teste.pdf`, 407 páginas, 265 s com Ollama/bge-m3):

| Item | Antes | Agora |
|---|---|---|
| Tabelas no banco | 56 trechos, sem estrutura; 8-7 a 8-15, 3-4, 3-8, 4-1 e 6-7 ausentes ou escondidas | **65 tabelas, 1.496 linhas**, todas com cabeçalho reconhecido |
| Trechos | 1.313 | 1.322 de texto + 1.496 de linha de tabela |
| Faixas de d% das tabelas de tesouro (8-1 a 8-15) | — | todas cobrem de 01 a 100, sem buraco |

**Busca** (`python -m vector_builder evaluate`, 63 perguntas: as 48 anteriores + 15 sobre tabelas):

| Busca híbrida | r@1 | r@5 | MRR |
|---|---|---|---|
| estrito (página e título) | 87% | 100% | 0,93 |
| só as 15 de tabela | 13/15 | 15/15 | — |

O mínimo de similaridade 0,45 continua respondendo 100% das perguntas do livro. No gabarito, a pergunta do custo em PM passou a aceitar a `Tabela 4-1`, que antes ficava escondida no trecho "Lançando Magias".

**Sorteio de tesouro**:

- Espaço do tesouro: 180 faixas da Tabela 8-1 (22 NDs × dinheiro/itens), 366 faixas das tabelas 8-2 a 8-15, 82 entradas com ND (78 criaturas e 4 perigos).
- Tipo de tesouro de todas as criaturas lido da ficha: Padrão 32, Nenhum 29 (11 delas com tesouro especial, como venenos e couro), Metade 12, Dobro 9. Os 4 perigos (Avalanche, Jornada pelos ermos, Sala Esmagadora, Tempestade em Alto Mar) não têm ficha de tesouro e usam Padrão.
- 9.900 sorteios automáticos (todos os NDs, Padrão/Metade/Dobro): nenhum erro e nenhum resultado sem regra.
- Rotas testadas com uma cópia do `nimb.db`: sorteio por criatura (Necromante, ND 7, Dobro) e por ND; 400 para ND inválido, 422 sem criatura nem ND, 404 para criatura inexistente, 428 para usuário sem o livro; histórico gravado.

## 8. To Do — revisar e ajustar

- [x] **Interface do sorteio**: pop-up com criaturas, quantidade, d% informados ou automáticos e resultado (ver seção 5, "Tela").
- [ ] **Tela do sorteio, próximos passos**: mostrar o histórico (`GET /api/tesouro/historico`), sorteio só pelo ND e troca do tipo de tesouro; informar também as rolagens seguintes (riquezas, itens).
- [ ] **Etapa B (comparações)**: dar à LLM uma ferramenta `consultar_tabela(tabela, filtros, ordenar_por)` com SQL parametrizado e somente leitura, para perguntas como "a arma de duas mãos mais barata com dano 1d10". As tabelas e o índice FTS já estão prontos para isso.
- [ ] **Tabelas com estrutura mais simples**: 6-1 (rótulo abaixo dos valores) e 5-2/8-7 (cabeçalho em duas linhas) saem certas no texto, mas conferir a coluna de cada valor.
- [ ] **Ligar linha de tabela à entrada completa**: usar `entries` para trazer, junto da linha da Tabela 1-5 ("Caminho do arcanista"), a descrição da habilidade.
- [ ] **Extras do tesouro da ficha** ("Padrão mais adaga da Tormenta", "1d4 doses de veneno…") aparecem como nota no sorteio, sem rolagem automática.
- [ ] **Pré-requisitos de encantos** (Magnífica exige Formidável) não são verificados no sorteio.
- [ ] **Outro livro**: o mapa de tabelas do tesouro (`SOURCES`) só existe para o `t20-basico`.
