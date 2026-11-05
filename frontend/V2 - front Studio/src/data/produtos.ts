// Conteúdo do pop-up "Produtinhos de Nimb" (botão da loja no Header).
// Nada aqui é salvo em lugar nenhum: a lista é mantida só no código.
// Para incluir um produto, acrescente um item em STORE_PRODUCTS; para trocar a loja, altere STORE_URL.

export interface StoreProduct {
  name: string;
  description: string;
  url: string;
}

// Link da loja usado no botão de redirecionamento no fim do pop-up
export const STORE_URL = 'https://exemplo.com/loja';

export const STORE_INTRO = 'Itens abençoados (ou amaldiçoados) por Nimb. A sorte decide.';

export const STORE_PRODUCTS: StoreProduct[] = [
  {
    name: 'Produto de exemplo 1',
    description: 'Descrição curta do produto. Substitua pelo texto real.',
    url: 'https://exemplo.com/loja/produto-1',
  },
  {
    name: 'Produto de exemplo 2',
    description: 'Descrição curta do produto. Substitua pelo texto real.',
    url: 'https://exemplo.com/loja/produto-2',
  },
  {
    name: 'Produto de exemplo 3',
    description: 'Descrição curta do produto. Substitua pelo texto real.',
    url: 'https://exemplo.com/loja/produto-3',
  },
];
