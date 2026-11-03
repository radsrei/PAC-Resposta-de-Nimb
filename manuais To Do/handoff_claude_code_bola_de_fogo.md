# Handoff: corrigir números errados nas respostas do Nimb (Bola de Fogo 8d6 → 6d6)

Contexto para o Claude Code no VS Code, no repositório `PAC-Resposta-de-Nimb` (branch `main`). Gerado em 02/11/2026, depois do deploy em produção.

## Seu papel

- Investigue e corrija o bug descrito abaixo **no código do repositório**. Depois, prepare a atualização do servidor.
- Antes de mudar alguma coisa, leia o código para localizar os arquivos certos. Os nomes de arquivo citados aqui são palpites.
- **Não altere** a configuração de deploy (`deploy/.env`, `SITE_ADDRESS=:80`, `COMPOSE_PROFILES=cloudflare,rag`, `CORS_ORIGINS`, `COOKIE_SECURE`), nem os timeouts (`ANSWER_TIME_BUDGET=85`, `LLM_TIMEOUT=90`), nem o modelo (`deepseek-chat`).
- Nunca escreva segredos em arquivos versionados.
- Faça commits pequenos e explique cada mudança.

## O bug

Pergunta: **"Quanto de dano causa a Bola de Fogo?"**

| | Valor |
|---|---|
| Esperado (Tormenta20, Livro Básico, p. 182) | **6d6** de dano de fogo |
| O Nimb responde | **8d6** de dano de fogo |
| Fonte citada pelo Nimb | Tormenta20, Livro Básico, p. 182 (correta) |

O erro se repete com o **Medidor de Caos em "Médio" e em "Baixo"**, com o modo **REGRA** ligado. Então não é só a temperatura.

O resto da resposta veio certo: aprimoramento de +2 PM que soma +2d6, esfera de 6 m e Reflexos que reduz à metade. 8d6 é o valor da *Fireball* do D&D 5e. A hipótese mais forte é que o LLM está substituindo o número do trecho pelo número que ele "conhece" de outro sistema, ou que o trecho recuperado não traz o "6d6".

## Etapa 1: diagnóstico (não corrija nada antes disto)

1. **Ver o texto indexado.** Descubra como o `vector_store` é lido no backend e escreva um script de diagnóstico que:
   - busque nos chunks indexados os textos que contêm `Bola de Fogo`;
   - mostre o texto completo desses chunks, a página e o tamanho de cada um;
   - responda: o `6d6` aparece no chunk? A extração do PDF quebrou o número (por exemplo `6 d6`, `6d 6`, hifenização, coluna trocada)? A descrição da magia ficou dividida entre dois chunks?
2. **Ver o que vai para o LLM.** Para a mesma pergunta, registre o que o retriever devolve: os chunks em ordem, os scores e o prompt final montado (system + contexto + pergunta). Confirme se o chunk com `6d6` está entre os recuperados e se ele sobrevive ao corte de contexto ou de tokens.
3. **Ver o prompt e os parâmetros.** Localize o prompt do sistema e como o Medidor de Caos e o modo REGRA mudam a `temperature`, o `top_p` e o texto do prompt.

Conclua com um diagnóstico curto: em qual destes casos estamos?

- **A)** O número não chega ao LLM: problema de extração, de chunking ou de recuperação.
- **B)** O número chega, mas o LLM troca: problema de prompt ou de geração.
- **C)** Os dois.

## Etapa 2: correções (conforme o diagnóstico)

### Se for A (extração, chunking ou recuperação)
- Corrigir a normalização do texto extraído do PDF: juntar números quebrados, hifenização e espaços dentro de `NdM`.
- Ajustar o chunking para não separar o cabeçalho da magia da descrição. Por exemplo, aumentar o tamanho ou a sobreposição dos chunks, ou dividir por entrada de magia.
- Se o chunking mudar, **reindexar** o livro e gerar um novo `vector_store`. Documente o comando e lembre do `chown 10001` ao enviar o resultado para o servidor.

### Se for B (prompt ou geração)
- Acrescentar ao prompt do sistema uma regra que vale **em qualquer nível de Caos**:
  > Números de regras (dados de dano, PM, CD, alcance, duração, preços) devem ser copiados exatamente do trecho recuperado. Nunca use valores de outros sistemas de RPG (como D&D). Se o número não estiver no trecho, diga que não encontrou.
- Fazer o Medidor de Caos afetar **só o estilo do texto**. A parte factual deve usar temperatura baixa, por exemplo ≤ 0,3 no modo REGRA.

### Em qualquer caso: validação de números (recomendado)
Implemente um pós-processamento barato antes de devolver a resposta:
- extrair da resposta todos os padrões de dado (`\b\d+d\d+\b`) e de custo (`T\$ ?[\d.]+`);
- conferir se cada um aparece no contexto recuperado, considerando a normalização;
- se algum não aparecer, refazer a geração uma vez, com um aviso explícito ao modelo (por exemplo: "o valor 8d6 não está no trecho; use somente os valores do trecho"), ou marcar a resposta com um aviso;
- registrar em log, em nível INFO, quando isso acontecer.

## Etapa 3: testes de regressão

Crie testes automatizados (pytest) com perguntas "douradas". Use um mock do LLM quando o teste for de pipeline e um teste marcado como `integration` quando chamar o DeepSeek de verdade:

| Pergunta | Deve conter | Não deve conter |
|---|---|---|
| Quanto de dano causa a Bola de Fogo? | `6d6`, `p. 182` | `8d6` |
| (adicione 3 ou 4 magias ou itens com números conhecidos do livro) | | |

Teste também a validação de números isoladamente: uma resposta com um `NdM` que não está no contexto deve ser detectada.

## Etapa 4: atualizar o servidor

Depois do merge na `main`, documente para o usuário rodar **no servidor** (`ubuntu@ip-172-31-35-232`):

```bash
cd ~/PAC-Resposta-de-Nimb && git pull
cd deploy && docker compose up -d --build
docker compose logs --tail 50 api
```

Se houver reindexação, inclua os passos de envio do novo `vector_store` com `chown 10001`. Antes de qualquer mudança no servidor, lembre o usuário de fazer um backup com `bash ~/PAC-Resposta-de-Nimb/deploy/backup.sh`.

Aceite final em **https://respostas-nimb.com.br**: "Quanto de dano causa a Bola de Fogo?" responde **6d6, Tormenta20, p. 182**, com o Caos em Baixo, Médio e Louco, sem erro 524.

## Estado atual do deploy (referência, não mexer)

- EC2 `c7i-flex.large` (us-east-2), IP elástico 77.112.180.130. Só a porta SSH 22 está aberta, para o IP do usuário.
- Cloudflare Tunnel `nimb-aws`: `respostas-nimb.com.br` e `www` apontam para `http://web:80`. Há um redirecionamento do www para a raiz. Always Use HTTPS, TLS ≥ 1.2 e Bot Fight Mode estão ligados.
- Google OAuth em modo Teste. As origens autorizadas são `https://respostas-nimb.com.br` e `http://localhost:3000`.
- Backup diário pelo cron às 3h (`deploy/backup.sh`), com destino em `/home/ubuntu/backups/`.
- O health atual responde `rag_engine: ativo`, `books_ready: 1` e `llm_connected: true`.
