// Correção do rótulo de transição pelo atleta (ADR 0009, #467). Só as rotas que já existem; nunca lançam.
// Privacidade: nada do corpo vai para log, console ou mensagem de erro.
import type { OpcoesCliente, Resultado, TransicaoAtividade } from "@treino/api-client";

import { chamar } from "../checkin/api";

const rota = (atletaId: number, atividadeId: number) =>
  `/atletas/${encodeURIComponent(String(atletaId))}/atividades/${encodeURIComponent(String(atividadeId))}/transicao`;

/** `PUT .../transicao` com `{ transicao }`: a correção do atleta vence a sugestão (`origem = atleta`). */
export function corrigirTransicao(
  atletaId: number,
  atividadeId: number,
  transicao: boolean,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<TransicaoAtividade>> {
  return chamar<TransicaoAtividade>(
    rota(atletaId, atividadeId),
    { method: "PUT", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify({ transicao }) },
    opcoes,
  );
}

/** `DELETE .../transicao`: apaga a correção e devolve o estado real (a sugestão da regra, se houver). */
export function desfazerCorrecaoDeTransicao(
  atletaId: number,
  atividadeId: number,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<TransicaoAtividade>> {
  return chamar<TransicaoAtividade>(rota(atletaId, atividadeId), { method: "DELETE", headers: { Accept: "application/json" } }, opcoes);
}
