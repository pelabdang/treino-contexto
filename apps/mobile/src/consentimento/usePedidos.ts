// Pedidos de professor aguardando resposta do atleta (selo da aba Conta). Uma chamada ao abrir e a cada `atualizar`; falha vira 0.
import { useEffect, useMemo, useState } from "react";

import { buscarProfessores, totalAguardando } from "./api";

export function usePedidos(ativo: boolean, apiUrl: string, atletaId: number, fetchFn?: typeof fetch, atualizar: unknown = 0): number {
  const [n, setN] = useState(0);
  const opcoes = useMemo(() => ({ baseUrl: apiUrl, fetch: fetchFn }), [apiUrl, fetchFn]);
  useEffect(() => {
    if (!ativo) return;
    let vivo = true;
    buscarProfessores(atletaId, opcoes).then((r) => {
      if (vivo) setN(r.ok && Array.isArray(r.dados.professores) ? totalAguardando(r.dados.professores) : 0);
    });
    return () => {
      vivo = false;
    };
  }, [ativo, atletaId, opcoes, atualizar]);
  return ativo ? n : 0;
}
