import { useColorScheme, useWindowDimensions } from "react-native";

import { cores, espaco, type Cores } from "./tokens";

export * from "./tokens";

export type Tema = { escuro: boolean; cor: Cores };

const temaClaro: Tema = { escuro: false, cor: cores.claro };
const temaEscuro: Tema = { escuro: true, cor: cores.escuro };

/** Tema do sistema (claro quando o sistema não informa). */
export function useTema(): Tema {
  return useColorScheme() === "dark" ? temaEscuro : temaClaro;
}

/** A partir desta largura (px) a margem da tela passa de 16 para 24 (guia visual). */
export const larguraMargemGrande = 600;

/** Margem da tela: 16 no celular, 24 a partir de 600 de largura (web e tablet). */
export function margemDaTela(largura: number): number {
  return largura >= larguraMargemGrande ? espaco[5] : espaco[4];
}

export function useMargemTela(): number {
  return margemDaTela(useWindowDimensions().width);
}
