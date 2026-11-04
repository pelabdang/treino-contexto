import { useColorScheme } from "react-native";

import { cores, type Cores } from "./tokens";

export * from "./tokens";

export type Tema = { escuro: boolean; cor: Cores };

const temaClaro: Tema = { escuro: false, cor: cores.claro };
const temaEscuro: Tema = { escuro: true, cor: cores.escuro };

/** Tema do sistema (claro quando o sistema não informa). */
export function useTema(): Tema {
  return useColorScheme() === "dark" ? temaEscuro : temaClaro;
}
