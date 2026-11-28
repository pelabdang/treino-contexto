// Perguntas prontas do chat (adendo da spec do chat, #629): a API escolhe conforme os treinos; as 6 fixas (`PERGUNTAS_PRONTAS`) são o plano B.
// Uma lista só por sessão, em memória: o Início mostra as 3 primeiras, o chat mostra todas e `?pronta=<índice>` aponta para a MESMA lista.
// Plano B depois de 4 s, em qualquer erro ou com lista vazia, sem aviso. Se a lista da API chegar depois do plano B, não troca.
import type { OpcoesCliente } from "@treino/api-client";
import { useEffect, useState } from "react";

import { buscarPerguntasProntas } from "./api";
import { PERGUNTAS_PRONTAS } from "./textos";

export const TEMPO_PERGUNTAS_PRONTAS_MS = 4000;

const prontas = new Map<string, readonly string[]>();
const buscando = new Map<string, Promise<readonly string[]>>();
const chaveDe = (apiUrl: string, atletaId: number) => `${apiUrl}|${atletaId}`;

/** Zera o cache (testes e troca de conta). */
export function limparPerguntasProntas(): void {
  prontas.clear();
  buscando.clear();
}

function obter(apiUrl: string, atletaId: number, opcoes: OpcoesCliente): Promise<readonly string[]> {
  const chave = chaveDe(apiUrl, atletaId);
  const feita = prontas.get(chave);
  if (feita) return Promise.resolve(feita);
  const andando = buscando.get(chave);
  if (andando) return andando;
  const promessa = new Promise<readonly string[]>((resolver) => {
    let decidida = false;
    const decidir = (lista: readonly string[]) => {
      if (decidida) return; // a resposta tardia da API não troca a lista
      decidida = true;
      clearTimeout(relogio);
      prontas.set(chave, lista);
      buscando.delete(chave);
      resolver(lista);
    };
    const relogio = setTimeout(() => decidir(PERGUNTAS_PRONTAS), TEMPO_PERGUNTAS_PRONTAS_MS);
    (relogio as { unref?: () => void }).unref?.();
    buscarPerguntasProntas(atletaId, opcoes).then((r) => decidir(r.ok && r.dados.length > 0 ? r.dados : PERGUNTAS_PRONTAS));
  });
  buscando.set(chave, promessa);
  return promessa;
}

/** `ativo` falso (conversa que já existe) não busca nada. `perguntas` é `null` enquanto carrega (a tela mostra esqueletos); depois é sempre uma lista (da API ou o plano B), de até 6. */
export function usePerguntasProntas(apiUrl: string, atletaId: number, fetchFn?: typeof fetch, ativo = true): { perguntas: readonly string[] | null } {
  const chave = chaveDe(apiUrl, atletaId);
  const [resolvida, setResolvida] = useState<{ chave: string; lista: readonly string[] } | null>(null);
  useEffect(() => {
    if (!ativo) return;
    let vivo = true;
    obter(apiUrl, atletaId, { baseUrl: apiUrl, fetch: fetchFn }).then((lista) => vivo && setResolvida({ chave, lista }));
    return () => {
      vivo = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chave, ativo]);
  const doCache = prontas.get(chave);
  return { perguntas: doCache ?? (resolvida?.chave === chave ? resolvida.lista : null) };
}
