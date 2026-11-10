import { useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";

/**
 * Conta as vezes que a tela voltou ao foco (sem contar a primeira). O `Stack` mantém a tela anterior montada, então
 * depois de salvar um check-in o treino, a lista e a evolução usam este número para buscar os dados de novo.
 */
export function useContadorDeFoco(): number {
  const [n, setN] = useState(0);
  const primeira = useRef(true);
  useFocusEffect(
    useCallback(() => {
      if (primeira.current) {
        primeira.current = false;
        return;
      }
      setN((x) => x + 1);
    }, []),
  );
  return n;
}
