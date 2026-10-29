// Conteúdo do pop-up "Agradecimentos" (tela Minha conta).
// Cada seção tem um título, um subtítulo opcional e a lista de nomes.
// Para incluir alguém, basta acrescentar o nome na lista da seção; para um novo grupo, uma nova seção.

export interface AcknowledgmentSection {
  title: string;
  subtitle?: string;
  names: string[];
}

export const ACKNOWLEDGMENTS_INTRO =
  'Nimb agradece a todos que rolaram os dados ao nosso lado na criação deste projeto.';

export const ACKNOWLEDGMENTS: AcknowledgmentSection[] = [
  {
    title: 'Equipe do Desenvolvimento',
    subtitle: 'Desenvolvimento, pesquisa e documentação',
    names: ['Rafael dos Santos Pereira', 'Claude', 'Chat GPT', 'Gemini'],
  },
  {
    title: 'Orientação e Ajuda',
    subtitle: 'Professores, Amigos e Colegas que deram suporte e feedback',
    names: ['Prof. Diogo','Prof. Darú','Prof. Claudinei','Prof. Camargo'],
  },
  {
    title: 'Comunidade',
    subtitle: 'Quem respondeu ao formulário e testou o sistema',
    names: ['Nome da pessoa 1', 'Nome da pessoa 2'],
  },
];
