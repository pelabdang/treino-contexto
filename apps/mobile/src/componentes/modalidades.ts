export type ModalidadeInfo = {
  nome: string;
  icone: "directions-run" | "directions-bike" | "pool";
  cor: "corrida" | "ciclismo" | "natacao";
};

/** Nome, ícone e cor da modalidade (guia visual). Modalidade desconhecida: sem chip. */
export const MODALIDADES: Record<string, ModalidadeInfo> = {
  corrida: { nome: "Corrida", icone: "directions-run", cor: "corrida" },
  ciclismo: { nome: "Ciclismo", icone: "directions-bike", cor: "ciclismo" },
  natacao: { nome: "Natação", icone: "pool", cor: "natacao" },
};
