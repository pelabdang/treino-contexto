// Foco e rolagem entre plataformas. Na web o nó é um elemento do DOM (`focus`, `scrollIntoView`); no celular, o foco do leitor de tela
// e a posição vêm de `findNodeHandle` e `measureLayout`. Nunca lança: sem leitor de tela ou sem nó, não faz nada.
import { AccessibilityInfo, findNodeHandle, Platform } from "react-native";

type NoWeb = { focus?: (o?: object) => void; scrollIntoView?: (o?: object) => void };

/** Leva o foco ao nó (o nó precisa aceitar foco: botão, ou texto com `tabIndex={-1}` na web). */
export function focar(no: unknown): void {
  if (!no) return;
  try {
    if (Platform.OS === "web") {
      (no as NoWeb).focus?.({ preventScroll: true });
      return;
    }
    const alvo = findNodeHandle(no as never);
    if (alvo) AccessibilityInfo.setAccessibilityFocus?.(alvo);
  } catch {
    // sem nó nativo
  }
}

/** Rola a `ScrollView` até o nó. */
export function rolarAte(rolagem: unknown, no: unknown): void {
  if (!no) return;
  try {
    if (Platform.OS === "web") {
      (no as NoWeb).scrollIntoView?.({ block: "center" });
      return;
    }
    const sv = rolagem as { getInnerViewRef?: () => unknown; scrollTo?: (o: object) => void };
    (no as { measureLayout?: (rel: unknown, ok: (x: number, y: number) => void) => void }).measureLayout?.(sv.getInnerViewRef?.(), (_x, y) =>
      sv.scrollTo?.({ y: Math.max(0, y - 16), animated: false }),
    );
  } catch {
    // sem medida
  }
}

/** Título que recebe foco por código (não entra na ordem do Tab). Só a web usa; o tabIndex não está nos tipos do React Native. */
export const FOCAVEL = { tabIndex: -1 } as object;
