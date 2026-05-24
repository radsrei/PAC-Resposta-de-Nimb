# RFC: Request for Comments — Projeto de Portfólio

**Engenharia de Software – Católica SC**

---

# Identificação

![Nimb](/Front/Icon%20-%20Nimb.png)

- **Título do Projeto:**  
  Respostas de Nimb.

  ![Nimb-](/Front/Nimb%20-%20Imagem.jpeg)


- **Linha de Projeto (Direction):**  
  RAG usando IA e Processamento de Linguagem Natural para fornecer respostas rápidas e precisas sobre regras, cenários e mecânicas do jogo de RPG Tormenta20.

- **Autor:**  
  Rafael dos Santos Pereira

- **Data da Proposta:**  
  19/02/2026

- **Versão:**  
  1.0

---

# 1. Visão do Produto e Impacto (O Problema)

O objetivo desta seção é responder uma pergunta fundamental:

**Este projeto resolve um problema real ou é apenas um exercício técnico?**

---

Esse projeto em primeiro momento é um exercício técnico, mas tem potencial para atender um problema real, considerando a necessidade de respostas e discussões que acontecem dentro do universo de RPG (Tormenta20).
Com essa situação em mente, o projeto tem potencial para ser utilizado por jogadores e mestres, que buscam respostas rápidas e precisas para suas dúvidas sobre regras, cenários e mecânicas do jogo.

## 1.1 Contexto e Problema

Descreva claramente o problema que motivou o projeto.

Explique:

- Quem sofre com esse problema
  -- Jogadores e Mestres que jogam Tormenta20
- Em que contexto ele ocorre
  -- Durante sessões de RPG, onde por conta da narrativa e contexto, surgem dúvidas sobre regras, cenários e mecânicas do jogo.
- Como esse problema é resolvido atualmente
  -- Entre os jogadores presencialmente e em alguns casos atravessa para o cenário online através de fóruns, grupos de discussão e debates em comunidades online, onde os jogadores buscam respostas para suas dúvidas.
- Quais são as limitações das soluções atuais
  -- O processo hoje se dá de forma manual, onde os jogadores conversam e discutem as regras entre si, trazendo um viés de cada um dos envolvidos, o que pode levar a interpretações divergentes e discussões prolongadas

Sempre que possível apresente:

- exemplos reais
- prints de processos atuais
- descrições de fluxos existentes

---

## 1.2 Origem da Demanda e Evidências

É necessário demonstrar que existe **interesse real pela solução**.

Apresente pelo menos **uma evidência concreta**.

### Demanda Externa

Projeto solicitado por:

- grupo de usuários de RPG do Aluno

Inclua:

- Campeões de Svallas (grupo de RPG do aluno)
- Dúvidas e discussões sobre as regras do jogo

---

### Pesquisa com Usuários

Pode incluir:

- entrevistas
  >[Reddit](https://www.reddit.com/r/Tormenta/comments/1skhv02/projeto_de_tcc_respostas_de_nimb/)

- questionários
  >[Formulário](https://forms.cloud.microsoft/r/DxYnjK8A9F)


- observação de processos

Inclua:

- número de pessoas entrevistadas
>26 respostas Obtidas até a data de 23/05/26
- principais dores identificadas
>![Resposta4](/Front/Formulario%20Reddit/Resposta%204%20-%20Forms.png)



- padrões observados
>As respostas em sua maioria foram de aprovação ao projeto/ideia, onde foi demonstrado com as respostas coletadas que parte dos usuários utilizaria e mesmo pagaria para utilizar/usufruir de um sistema de IA para tirar dúvidas.

>![Resposta5](/Front/Formulario%20Reddit/Resposta%205%20-%20Forms%20Reddit.png)

>![Resposta8](/Front/Formulario%20Reddit/Resposta%208%20-%20Forms%20Reddit.png)

Adicione **tabelas, gráficos ou prints**.

---

### Evidência de Interesse

Podem ser incluídos:

- cartas de intenção
- feedback de usuários
- comentários de comunidades
- resultados de formulários


![Reddit](/Front/Formulario%20Reddit/Post%20Reddit.png)
---

## 1.3 Análise de Soluções Existentes (Benchmark)

Investigue **3 a 5 soluções existentes** que tentam resolver o mesmo problema.

Para cada solução apresente:

- nome do produto
- link
- público-alvo
- funcionalidades principais
- limitações

Inclua **prints da interface ou diagramas simplificados**.

---

### Comparação

| Solução | Pontos Fortes | Limitações |
| ------- | ------------- | ---------- |

---

### Diferencial do Projeto

Explique claramente:

- A ideia de fóruns e debates em comunidade para as regras já existentes é uma pratica comum dentro do contexto do RPG. A ideia é trazer uma ferramenta que ao ser alimentda e trabalhada consiga trazer um entendimento mais objetivo e direto da regra.
- As lacunas existentes hoje estão a nível comparativo a discussões juridicas na interpretação de leis, o que acaba ocorrendo é o vies de cada um dos envolvidos no debate, a ideia da IA é remover justamente o vies existente.
- O nicho atendido em primeira instancia é o do grupo de RPG que o aluno participa

---

## 1.4 Público-Alvo

Defina quem usará o sistema.

Exemplos:

- jogadores novatos
- jogadores veteranos
- mestres de RPG

Descreva:

### Jogadores e Mestres de Tormenta20

- Perfil do usuário: Jogadores e mestres de RPG que utilizam o sistema de regras de Tormenta20.
- Contexto de uso: Durante sessões de RPG, onde surgem dúvidas sobre regras, cenários e mecânicas do jogo.
- Nível de conhecimento técnico esperado: Qualquer nível de conhecimento no tema, e sem alto nível para uso o sistema, o objetivo é justamente trazer uma solução acessível para todos os níveis de jogadores e mestres.

---

## 1.5 Objetivos do Projeto

### Objetivo Geral

Qual transformação o projeto pretende gerar.

O projeto tem como objetivo criar um sistema de perguntas e respostas para o universo de Tormenta20 (RPG), utilizando técnicas de IA e Processamento de Linguagem Natural para fornecer respostas rápidas e precisas sobre regras, cenários e mecânicas do jogo, atendendo às necessidades de jogadores e mestres.

---

### Objetivos Específicos

Liste **3 a 5 objetivos técnicos ou de produto**.

Exemplo:

- Agilizar busca por regras e informações do jogo
- Permitir gerar contexto de aplicação das regras
- Fornecer respostas precisas e contextualizadas
- Criar uma base de conhecimento estruturada sobre o universo de Tormenta20

---

## 1.6 Métricas de Sucesso (KPIs)

Como saberemos que o projeto foi bem sucedido?

- acurácia da IA superior a 85%
- Respostas geradas com menos de 1 segundo de latência
- Respostas com nível de satisfação do usuário superior a 4 em uma escala de 1 a 5

---

# 2. Engenharia de Requisitos

Esta seção define **o que o sistema fará**.

Evite descrições vagas.

---

## 2.1 Personas

Crie **1 a 3 personas principais**.

Inclua:

- Nome fictício
- Contexto
- Objetivos
- Principais dificuldades

Adicionar **imagens ou ilustrações** pode ajudar na compreensão.

### Persona - Mestre
>- Nome: Cleber "Alface"
>- Contexto: Cleber é um mestre de Tormenta 20, com anos de experiencia, conhecimento dos livros e das regras. Sabe como balancear conflitos e conhece das regras com grande maestria
>- Objetivos: Tem como objetivo base pesquisar 
>- Principais dificuldades: Lembrar de valores especificos de magias/itens, caracteristicas de condições e caracteristicas de habilidades pontuais.


### Persona - Jogador Veterano
>- Nome: Vanderler
>- Contexto: Vanderler é um jogador veterano de Tormenta 20, com anos de experiencia, conhece as regras e tem uma boa compreensão do jogo. Ele gosta de explorar as mecânicas e criar estratégias complexas durante as sessões.
>- Objetivos: Vanderler tem como objetivo base pesquisar regras e mecânicas específicas para otimizar suas jogadas e criar estratégias mais eficazes durante as sessões de RPG.
>- Principais dificuldades: Lembrar de detalhes específicos de regras, como interações entre habilidades, efeitos de magias e condições, o que pode impactar suas decisões durante o jogo.

### Persona - Jogador Novato
>- Nome: Robson
>- Contexto: Robson é um jogador novato de Tormenta 20, com pouco conhecimento das regras e mecânicas do jogo. Ele está começando a aprender sobre o universo de RPG e tem dificuldades para entender as regras complexas.
>- Objetivos: Robson tem como objetivo base aprender as regras e mecânicas do jogo de forma rápida e fácil, para poder participar das sessões de RPG sem se sentir perdido ou confuso.
>- Principais dificuldades: Entender as regras complexas, lembrar de detalhes específicos e encontrar informações relevantes durante as sessões de RPG, o que pode levar a frustração e desmotivação para jogar.
---

## 2.2 Casos de Uso Principais

Liste os principais fluxos do sistema.

Exemplo:

- Gerar respostas para perguntas sobre regras


Sempre que possível inclua **diagramas de caso de uso**.

---

## 2.3 Requisitos Funcionais (RF)

Use a estrutura:

> O sistema deve permitir que **[ator] realize [ação]**.


**RF01** — O sistema deve permitir que o usuário acesse uma interface de perguntas e respostas.

**RF02** — O sistema deve permitir que o usuário envie perguntas sobre regras do jogo.

**RF03** — O sistema deve permitir que o usuário visualize respostas geradas.

**RF04** - O sistema deve permitir que o usuário acesse uma interface de perguntas e respostas sem necessidade de instalação local, via navegador web.

**RF05** — O sistema deve permitir que o usuário envie perguntas em linguagem natural sobre regras, mecânicas e cenários do Tormenta20. 

**RF06** — O sistema deve permitir que o usuário visualize a resposta gerada pela IA com indicação da(s) fonte(s) do livro de regras consultada(s).

**RF07** — O sistema deve permitir que o usuário visualize o histórico de perguntas realizadas durante a sessão atual.

**RF08** — O sistema deve exibir uma mensagem clara quando não houver informação suficiente na base de conhecimento para responder à pergunta.

---

## 2.4 Requisitos Não Funcionais (RNF)

Inclua requisitos relacionados a:

- Desempenho
- Latência
- Segurança
- Escalabilidade
- Usabilidade
- Acurácia 

Exemplo:

**RNF01** — O tempo de resposta do sistema para perguntas deve ser inferior a 3 segundos em condições normais de uso 

**RNF02** — O tempo total entre o envio da pergunta e a exibição da resposta, incluindo busca vetorial e geração do modelo, deve ser inferior a 5 segundos.   

**RNF03** — O sistema deve ter campos de fácil entendimento, e legibilidade de leitura nas respostas.

**RNF04** — O modelo deve atingir acurácia de respostas avaliadas como corretas em ao menos 85% dos casos em testes com questões validadas por especialistas em Tormenta20.

**RNF05** - A arquitetura deve suportar aumento de carga sem refatoração, permitindo escalonamento horizontal dos serviços de backend.

---

## 2.5 Regras de Negócio

Exemplos:

- apenas usuários autenticados podem acessar determinados recursos
- determinadas operações exigem validação adicional

**RN01** — Somente conteúdo oficial de Tormenta20 

O sistema deve responder exclusivamente com base em materiais oficiais de Tormenta20 (livros, suplementos e erratas publicados pela Jambô Editora). Conteúdos de fanmade, regras-casa ou outros sistemas de RPG não devem ser indexados na base de conhecimento. 

**RN02** — Obrigatoriedade de citação de fonte 

Toda resposta gerada deve referenciar ao menos um trecho da base de conhecimento indexada. Respostas sem respaldo documental identificável não devem ser exibidas ao usuário. 

**RN03** — Limite de tokens por pergunta 

Perguntas enviadas pelo usuário devem ter no mínimo 10 caracteres e no máximo 500 caracteres, evitando consultas excessivamente vagas ou abusivas ao modelo de linguagem. 

Exemplo de rejeição: a pergunta "oi" é rejeitada com a mensagem "Por favor, elabore sua dúvida sobre as regras de Tormenta20." 

**RN04** — Não substituição de consulta ao mestre 

O sistema deve exibir um aviso padrão indicando que as respostas são baseadas na interpretação dos textos oficiais e que o mestre da sessão tem autoridade final sobre a aplicação das regras na mesa. 
---

## 2.6 Fora do Escopo

Liste explicitamente **o que o sistema não fará**.

Isso ajuda a evitar crescimento descontrolado do projeto.

Os itens abaixo estão explicitamente excluídos do escopo deste projeto para garantir foco e evitar crescimento descontrolado (scope creep): 

- Suporte a outros sistemas de RPG (D&D 5e, Pathfinder, Vampiro: A Máscara, etc.). 

- Geração de fichas de personagem ou calculadora de atributos. 

- Funcionalidade de chat em tempo real entre jogadores. 

- Criação de aventuras ou encontros de forma automatizada. 

- Suporte a áudio ou imagem como entrada de pergunta. 

- Aplicativo mobile nativo (iOS/Android) — o sistema será acessível via navegador responsivo. 

- Integração com plataformas de VTT (Virtual Tabletop) como Foundry VTT ou Roll20. 

- Funcionalidade de rolagem de dados. 

---

# 3. Fluxos e Comportamento do Sistema

Esta seção demonstra **como o sistema funciona**.

Use diagramas sempre que possível.

---

## 3.1 Fluxo Principal do Usuário

Apresente o fluxo principal do sistema.

Utilize:

- fluxogramas
- diagramas de atividades
- diagramas de sequência

Inclua **imagens dos diagramas**.

---

## 3.2 Fluxos Alternativos

Descreva cenários como:

- erros
- cancelamentos
- exceções

---

# 4. Mockups e Experiência do Usuário (UX)

Esta seção apresenta **a visualização inicial do produto antes da implementação**.

Mockups ajudam a validar:

- fluxo de navegação
- organização da interface
- interações do usuário
- clareza da experiência

Ferramentas sugeridas:

- Figma
- Excalidraw
- Balsamiq
- Whimsical
- protótipos desenhados à mão

---

## 4.1 Fluxo de Navegação

Apresente um diagrama mostrando como o usuário navega entre telas.

Exemplo:

Login → Dashboard → Cadastro → Relatório

Inclua **imagem do fluxo de navegação**.

---

## 4.2 Wireframes ou Mockups das Telas

Apresente os principais mockups do sistema.

Inclua pelo menos:

- tela inicial
- fluxo principal
- tela de entrada de dados
- tela de resultado ou visualização

Para cada tela inclua:

- imagem
- breve descrição da funcionalidade
- ações principais do usuário

Sempre que possível:

- inclua **links para protótipo navegável**
- inclua **prints das telas**

---

## 4.3 Fluxo de Interação do Usuário

Demonstre passo a passo um fluxo importante.

Exemplo:

1. usuário acessa o sistema
2. cria conta
3. registra dados
4. visualiza resultados

Inclua **sequência de telas ou fluxo visual**.

---

## 4.4 Feedback Inicial de Usuários (Opcional)

Se possível, inclua:

- comentários de usuários
- sugestões de melhoria
- validação inicial do mockup

---

# 5. Arquitetura do Sistema

Esta seção demonstra **como o sistema será construído**.

---

## 5.1 Diagrama C4

Apresente três níveis.

## 1. Nível 1: Diagrama de Contexto

É a **visão macro** do sistema. O foco aqui não é a tecnologia, mas sim como o software se encaixa no ecossistema e no mundo real.

- **Objetivo:** Mostrar o sistema como uma "caixa preta" e suas interações básicas com o ambiente externo.
- **O que incluir:**
  - **Atores:** Diferentes perfis de usuários (Ex: Cliente, Administrador, Operador).
  - **Sistemas Externos:** Softwares legados, serviços de terceiros ou provedores de identidade.
  - **Fluxo de Valor:** Como a informação entra, circula e sai do sistema principal.

---

## 2. Nível 2: Diagrama de Containers

Neste estágio, damos o primeiro **"zoom"**. Decompomos o sistema em suas unidades de execução independentes (containers).

- **Objetivo:** Apresentar a arquitetura de alto nível e as decisões tecnológicas fundamentais.
- **O que incluir:**
  - **Aplicações Web/Mobile:** Interfaces de usuário (Ex: SPA em React, App Android/iOS).
  - **Serviços de Backend:** Unidades lógicas de processamento (Ex: API Gateway, Microserviços em Node.js ou Go).
  - **Armazenamento:** Persistência de dados (Ex: PostgreSQL, MongoDB, Redis).
  - **Protocolos:** Como os containers se comunicam (Ex: JSON/HTTPS, gRPC, RabbitMQ).

---

## 3. Nível 3: Diagrama de Componentes

O foco agora é o que acontece **dentro de um único container** (como uma API específica ou um serviço de backend).

- **Objetivo:** Identificar as responsabilidades internas, padrões de código e a organização lógica.
- **O que incluir:**
  - **Estrutura Interna:** Organização das camadas (Ex: Controladores, Serviços, Repositórios e Clientes de API).
  - **Lógica de Negócio:** Componentes que encapsulam as regras específicas do domínio.
  - **Interações:** Como os componentes internos se orquestram para processar e responder a uma requisição.

---

## 5.2 Modelo de Dados

Apresente:

- DER (diagrama entidade relacionamento)
- esquema relacional
- modelo de documentos (NoSQL)

Inclua **diagramas do modelo de dados**.

---

## 5.3 Principais Componentes

Descreva os principais módulos do sistema.

Exemplo:

- API
- sistema de autenticação
- módulo de processamento
- camada de persistência

---

## 5.4 Stack Tecnológica

Liste as tecnologias utilizadas.

Para cada tecnologia explique **por que ela foi escolhida**.

Exemplo:

**Python**: Escolhido pela facilidade de uso e ampla biblioteca de IA.

**Langchain**: Utilizado para facilitar a construção de aplicações de IA.



---

# 6. Segurança e Privacidade

Inclua preocupações básicas de segurança.

Exemplos:

- proteção contra OWASP Top 10
- autenticação e autorização
- criptografia de dados sensíveis

---

## 6.1 Privacidade e LGPD

Explique:

- quais dados serão coletados
- como serão armazenados
- como o usuário poderá solicitar remoção de dados

---

# 7. Planejamento do Projeto

Defina os principais marcos de desenvolvimento.

| Marco | Descrição                             | Prazo    |
| ----- | ------------------------------------- | -------- |
| M1    | Setup do ambiente e prova de conceito | Semana X |
| M2    | MVP funcional                         | Semana Y |
| M3    | Testes e melhorias                    | Semana Z |

---

# 8. Referências

Inclua:

- artigos
- documentação técnica
- ferramentas utilizadas
- repositórios

---

# 9. Apêndices

Podem incluir:

- mockups adicionais
- resultados de pesquisa
- entrevistas com usuários
- diagramas complementares
- links para protótipos ou repositórios

Sempre que possível inclua **imagens, protótipos ou referências visuais**.

---

# 10. Parecer do Comitê de Avaliação

(A ser preenchido pelos professores)

**Avaliador 1:** \***\*\*\*\*\*\*\***\_\_\***\*\*\*\*\*\*\***  
**Status:** [ ] Aprovado [ ] Ajustar

Observações:

---

**Avaliador 2:** \***\*\*\*\*\*\*\***\_\_\***\*\*\*\*\*\*\***  
**Status:** [ ] Aprovado [ ] Ajustar

Observações:

---

**Avaliador 3:** \***\*\*\*\*\*\*\***\_\_\***\*\*\*\*\*\*\***  
**Status:** [ ] Aprovado [ ] Ajustar

Observações:
