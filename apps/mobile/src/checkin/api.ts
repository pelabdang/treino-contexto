// Chamadas do check-in pós-treino (ADR 0012, item 7). Os tipos vêm do cliente gerado (@treino/api-client); as funções
// moram aqui porque o pacote só exporta os tipos, como na semana-padrão. Nunca lançam: devolvem `Resultado`.
// Privacidade (ADR 0012, item 5): nada do corpo enviado ou recebido vai para log, console ou mensagem de erro.
import type {
  Checkin,
  CheckinEnvio,
  CheckinsPendentes,
  ErroApi,
  ErroNaoEncontrado,
  ErroValidacao,
  OpcoesCliente,
  Resultado,
} from "@treino/api-client";

const BASE_PADRAO = "http://localhost:8000";

async function chamar<T>(
  caminho: string,
  init: RequestInit,
  opcoes: OpcoesCliente,
  semCorpo = false,
): Promise<Resultado<T>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(`${base}${caminho}`, init);
  } catch (e) {
    return { ok: false, erro: { tipo: "rede", mensagem: e instanceof Error ? e.message : "falha de rede" } };
  }
  if (resposta.ok) {
    if (semCorpo) return { ok: true, dados: null as T };
    try {
      return { ok: true, dados: (await resposta.json()) as T };
    } catch {
      return { ok: false, erro: { tipo: "http", status: resposta.status } };
    }
  }
  if (resposta.status === 404 || resposta.status === 422) {
    try {
      const detalhe = await resposta.json();
      const erro: ErroApi =
        resposta.status === 404
          ? { tipo: "nao_encontrado", status: 404, detalhe: detalhe as ErroNaoEncontrado }
          : { tipo: "validacao", status: 422, detalhe: detalhe as ErroValidacao };
      return { ok: false, erro };
    } catch {
      // corpo que não é JSON: cai no erro HTTP genérico
    }
  }
  return { ok: false, erro: { tipo: "http", status: resposta.status } };
}

const rotaCheckin = (atletaId: number, atividadeId: number) =>
  `/atletas/${encodeURIComponent(String(atletaId))}/atividades/${encodeURIComponent(String(atividadeId))}/checkin`;

/** `PUT .../checkin`: cria ou substitui o check-in (200 nos dois casos). */
export function registrarCheckin(
  atletaId: number,
  atividadeId: number,
  envio: CheckinEnvio,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<Checkin>> {
  return chamar<Checkin>(
    rotaCheckin(atletaId, atividadeId),
    {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(envio),
    },
    opcoes,
  );
}

/** `DELETE .../checkin`: 204, sem corpo. Idempotente. */
export function apagarCheckin(atletaId: number, atividadeId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<null>> {
  return chamar<null>(rotaCheckin(atletaId, atividadeId), { method: "DELETE", headers: { Accept: "application/json" } }, opcoes, true);
}

/** `GET /atletas/{id}/checkins/pendentes[?dias=]`: só o treino (nada do check-in). */
export function buscarCheckinsPendentes(
  atletaId: number,
  dias?: number,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<CheckinsPendentes>> {
  return chamar<CheckinsPendentes>(
    `/atletas/${encodeURIComponent(String(atletaId))}/checkins/pendentes${dias ? `?dias=${encodeURIComponent(String(dias))}` : ""}`,
    { headers: { Accept: "application/json" } },
    opcoes,
  );
}

export type Motivo422 = "fora_do_prazo" | "atividade_sem_checkin" | "outro";

/** O código do `422` de domínio vem em `detail[0].type` (ADR 0012, item 5). Nunca olha `msg` nem `input`. */
export function motivo422(erro: ErroApi): Motivo422 {
  if (erro.tipo !== "validacao") return "outro";
  const tipo = (erro.detalhe.detail as { type?: unknown }[] | undefined)?.[0]?.type;
  return tipo === "fora_do_prazo" || tipo === "atividade_sem_checkin" ? tipo : "outro";
}
