// Estilo de Pressable com hover e anel de foco (`borda.foco` em `cor.foco`, guia visual). Só a web manda `hovered` e `focused`.
import type { PressableStateCallbackType } from "react-native";

export const comFoco = (base: object, foco: object, hover?: object) => (e: PressableStateCallbackType) => {
  const { hovered, focused } = e as { hovered?: boolean; focused?: boolean };
  return [base, hovered && hover, focused && foco];
};
