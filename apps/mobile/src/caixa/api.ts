// Chamada da caixa do dia do professor (#426, ADR 0015). O tipo vem do cliente gerado (@treino/api-client); a função mora aqui
// porque o pacote só exporta os tipos, como na semana-padrão e no check-in. Nunca lança: devolve `Resultado`.
// Privacidade (ADR 0015, item 7): nada do corpo recebido vai para log, console, mensagem de erro, URL ou armazenamento.
import type { components, ErroApi, ErroNaoEncontrado, ErroValidacao, OpcoesCliente, Resultado } from "@treino/api-client";

export type CaixaDoDia = components["schemas"]["CaixaDoDiaOut"];
export type AlunoCaixa = components["schemas"]["AlunoOut"];
export type TreinoComMotivo = components["schemas"]["TreinoComMotivoOut"];
export type TreinoNovo = components["schemas"]["NovoOut"];
export type DetalheTreino = components["schemas"]["DetalheOut"];
export type MotivoCaixa = components["schemas"]["MotivoOut"];
export type TiposConfirmados = components["schemas"]["TiposConfirmadosOut"];
export type TipoTreino = NonNullable<components["schemas"]["TipoItemIn"]["tipo_treino"]>;
export type ItemTipo = { atividade_id: number; tipo_treino: TipoTreino };

/** Os cinco tipos, na ordem da folha "Tipo do treino" (ADR 0015). */
export const TIPOS: { valor: TipoTreino; texto: string }[] = [
  { valor: "leve", texto: "Leve" },
  { valor: "moderado", texto: "Moderado" },
  { valor: "longo", texto: "Longo" },
  { valor: "intervalado", texto: "Intervalado" },
  { valor: "fartlek", texto: "Fartlek" },
];

/** `type` do primeiro item de `detail` (404 e 422 da API: `atividade_nao_encontrada`, `atividade_sem_tipo`, `professor_inexistente`). */
export function codigoDoErro(erro: ErroApi): string | null {
  if (erro.tipo !== "nao_encontrado" && erro.tipo !== "validacao") return null;
  const detail = (erro.detalhe as { detail?: unknown }).detail;
  const primeiro = Array.isArray(detail) ? (detail[0] as { type?: unknown } | undefined) : undefined;
  return typeof primeiro?.type === "string" ? primeiro.type : null;
}

const BASE_PADRAO = "http://localhost:8000";

/** `GET /professores/{professorId}/caixa-do-dia`: calculada a cada leitura. 404 `professor_inexistente` é uniforme. */
export function buscarCaixaDoDia(professorId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<CaixaDoDia>> {
  return chamar<CaixaDoDia>(professorId, "caixa-do-dia", { headers: { Accept: "application/json" } }, opcoes);
}

/**
 * `PUT /professores/{professorId}/tipos-de-treino`: confirma (tipo igual ao sugerido) ou corrige (tipo diferente) em lote, tudo ou nada
 * (#425, no máximo 200). Só `atividade_id` e `tipo_treino` saem do app. Nunca lança.
 */
export function confirmarTiposDeTreino(professorId: number, itens: ItemTipo[], opcoes: OpcoesCliente = {}): Promise<Resultado<TiposConfirmados>> {
  return chamar<TiposConfirmados>(
    professorId,
    "tipos-de-treino",
    { method: "PUT", headers: { Accept: "application/json", "Content-Type": "application/json" }, body: JSON.stringify(itens) },
    opcoes,
  );
}

async function chamar<T>(professorId: number, caminho: string, init: RequestInit, opcoes: OpcoesCliente): Promise<Resultado<T>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const url = `${base}/professores/${encodeURIComponent(String(professorId))}/${caminho}`;
  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, init);
  } catch {
    return { ok: false, erro: { tipo: "rede", mensagem: "falha de rede" } };
  }
  if (resposta.ok) {
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
