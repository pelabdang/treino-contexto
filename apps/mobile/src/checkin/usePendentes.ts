// Quantos treinos esperam check-in (selo da aba Treinos). Uma chamada ao abrir e a cada `atualizar`; falha vira 0.
import { useEffect, useMemo, useState } from "react";

import { buscarCheckinsPendentes } from "./api";

export function usePendentes(ativo: boolean, apiUrl: string, atletaId: number, fetchFn?: typeof fetch, atualizar: unknown = 0): number {
  const [n, setN] = useState(0);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);
  useEffect(() => {
    if (!ativo) return;
    let vivo = true;
    buscarCheckinsPendentes(atletaId, undefined, opcoes).then((r) => {
      if (vivo) setN(r.ok && typeof r.dados.total === "number" ? r.dados.total : 0);
    });
    return () => {
      vivo = false;
    };
  }, [ativo, atletaId, opcoes, atualizar]);
  return ativo ? n : 0;
}
