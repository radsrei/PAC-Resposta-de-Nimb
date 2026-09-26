# Front — Respostas de Nimb

Este diretório contém a tela de chat do projeto **Respostas de Nimb**, reestruturada a partir do protótipo único (`Prototipo-IA.html`) em arquivos separados de HTML, CSS e JS, já preparada para se conectar ao Backend.

> Repositório do projeto: https://github.com/radsrei/PAC-Resposta-de-Nimb

## Estrutura de pastas

```
Front/
├── index.html          # Estrutura semântica da tela (Head / Sidebar / Body)
├── css/
│   └── style.css        # Todo o visual da tela — nenhum estilo inline
├── js/
│   ├── config.js         # Configuração de conexão com o backend
│   ├── api.js             # Camada de comunicação (fetch) com o backend
│   └── app.js              # DOM, eventos e estado da tela
├── assets/
│   └── img/               # Logo e demais imagens estáticas
└── README.md            # Este arquivo
```

**Fluxo de dados:** `index.html` (Tela) → `app.js` → `api.js` (usa `config.js`) → **Backend**.
`app.js` nunca chama `fetch()` diretamente — toda chamada de rede passa por `NimbAPI` em `api.js`.

## Estrutura da tela

| Região | Conteúdo |
|---|---|
| **Head** (topbar) | Logo do projeto, nome do projeto, medidor de "Chance de Caos" (badge `v2`, inativo até o backend enviar `chaos_level`) |
| **Sidebar** | Perguntas anteriores (carregadas via `NimbAPI.getConversations()`), Livros carregados (badge `v2`, desabilitado — RAG ainda não conectado), nome do usuário logado (via `NimbAPI.getUser()`) |
| **Body** | Entrada e saída do chat (`response-area`), caixa de entrada com auto-resize, sugestões de perguntas (chips) |

Funcionalidades marcadas **v2** já estão na interface (para manter o layout final estável), porém desabilitadas/inertes até o backend expor os dados correspondentes.

## Preparação para o Backend

Toda a comunicação está isolada em `js/api.js`, configurada por `js/config.js`:

```js
// js/config.js
const APP_CONFIG = {
  API_BASE_URL: "http://localhost:8000/api", // trocar por ambiente
  USE_MOCK: true // true = respostas simuladas | false = chama o backend real
};
```

Enquanto `USE_MOCK` estiver `true`, a tela funciona sozinha, com respostas e listas simuladas (igual ao protótipo original). Basta trocar para `false` quando o backend estiver disponível — nenhuma outra alteração de código é necessária.

### Contrato de API esperado

| Rota | Método | Body / Resposta |
|---|---|---|
| `/chat` | `POST` | body: `{ message, conversation_id }` → resposta: `{ reply, conversation_id, chaos_level? }` |
| `/conversations` | `GET` | resposta: `{ recent: [{id, title}], previous: [{id, title}] }` |
| `/user/me` | `GET` | resposta: `{ name, role }` |
| `/books` (v2) | `GET` | resposta: `{ books: [{id, title}] }` |
| `/chaos-level` (v2) | `GET` | usado indiretamente via `chaos_level` na resposta do `/chat` |

Ajuste as rotas em `APP_CONFIG.ENDPOINTS` (`js/config.js`) caso o backend use caminhos diferentes.

## Como rodar localmente

Como o `index.html` referencia arquivos locais via `<script src="js/...">`, abra-o através de um servidor estático (não em `file://`) para evitar bloqueios de CORS do navegador:

```bash
cd Front
python3 -m http.server 5500
# depois acesse http://localhost:5500
```

## Como publicar esta atualização no repositório

```bash
# 1. Clonar o repositório (se ainda não tiver)
git clone https://github.com/radsrei/PAC-Resposta-de-Nimb.git
cd PAC-Resposta-de-Nimb

# 2. Criar uma branch dedicada
git checkout -b refactor/front-separado-css-js

# 3. Copiar os arquivos deste pacote para dentro de Front/, mantendo a subestrutura
#    (css/, js/, assets/img/)

# 4. Conferir o que mudou
git status
git diff

# 5. Adicionar e commitar
git add Front/
git commit -m "refactor(front): separa HTML, CSS e JS e prepara conexao com backend"

# 6. Enviar a branch e abrir Pull Request
git push -u origin refactor/front-separado-css-js
# depois abrir PR em https://github.com/radsrei/PAC-Resposta-de-Nimb/pulls
```

## Referências

- Repositório do projeto: https://github.com/radsrei/PAC-Resposta-de-Nimb
- Configurar o Git: https://docs.github.com/en/get-started/git-basics/set-up-git
- Fluxo branch → commit → pull request: https://docs.github.com/en/get-started/using-github/github-flow

## Próximos passos (v2)

- [ ] Conectar `/chaos-level` (ou o campo `chaos_level` no `/chat`) e ativar `updateChaosMeter()` em `app.js`
- [ ] Implementar upload/listagem de livros e conectar `NimbAPI.getBooks()`
- [ ] Autenticação real de usuário em `/user/me`
