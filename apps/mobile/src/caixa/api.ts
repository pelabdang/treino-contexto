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

const BASE_PADRAO = "http://localhost:8000";

/** `GET /professores/{professorId}/caixa-do-dia`: calculada a cada leitura. 404 `professor_inexistente` é uniforme. */
export async function buscarCaixaDoDia(professorId: number, opcoes: OpcoesCliente = {}): Promise<Resultado<CaixaDoDia>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const url = `${base}/professores/${encodeURIComponent(String(professorId))}/caixa-do-dia`;
  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, { headers: { Accept: "application/json" } });
  } catch {
    return { ok: false, erro: { tipo: "rede", mensagem: "falha de rede" } };
  }
  if (resposta.ok) {
    try {
      return { ok: true, dados: (await resposta.json()) as CaixaDoDia };
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
