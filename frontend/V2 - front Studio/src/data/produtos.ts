// Conteúdo do pop-up "Produtinhos de Nimb" (botão da loja no Header).
// Nada aqui é salvo em lugar nenhum: a lista é mantida só no código.
// Para incluir um produto, acrescente um item em STORE_PRODUCTS; para trocar a loja, altere STORE_URL.

export interface StoreProduct {
  name: string;
  description: string;
  url: string;
}

// Link da loja usado no botão de redirecionamento no fim do pop-up
export const STORE_URL = 'https://jamboeditora.com.br/';

export const STORE_INTRO = 'A MELHOR DEFESA PELO MENOR PREÇO';

export const STORE_CUPOM = 'CUPOM: Ainda não temos a moral';

export const STORE_PRODUCTS: StoreProduct[] = [
  {
    name: 'Me leve com você',
    description: 'Ou não tanto faz',
    url: 'https://jamboeditora.com.br/produto/medalha-dos-deuses-06-nimb/',
  },
  {
    name: 'Conhecer o Chão',
    description: 'Umas histórias e pessoas diferentes',
    url: 'https://jamboeditora.com.br/produto/colecao-arton/',
  },
  {
    name: 'Conhecer os Planos',
    description: 'Minha casa aparece ali',
    url: 'https://jamboeditora.com.br/produto/tormenta20-deuses-e-herois/',
  },
    {
    name: 'O mínimo que você deveria ter',
    description: 'É sério, precisa pelo menos usar essa coisa estranha',
    url: 'https://jamboeditora.com.br/produto/tormenta20-edicao-jogo-do-ano/',
  },
];

  // {
  //   name: 'Produto de exemplo 3',
  //   description: 'Descrição curta do produto. Substitua pelo texto real.',
  //   url: 'https://exemplo.com/loja/produto-3',
  // },
