// Chamadas da semana-padrão (ADR 0011, itens 9 e 10). Os tipos vêm do cliente gerado (@treino/api-client);
// as funções moram aqui porque o pacote ainda só exporta os tipos (#264). Nunca lançam: devolvem `Resultado`.
import type {
  ErroApi,
  ErroNaoEncontrado,
  ErroValidacao,
  OpcoesCliente,
  Resultado,
  SemanaPadrao,
  SemanaPadraoEnvio,
  SemanaPadraoGravada,
} from "@treino/api-client";

const BASE_PADRAO = "http://localhost:8000";

async function chamar<T>(
  atletaId: number,
  consulta: string,
  init: RequestInit,
  opcoes: OpcoesCliente,
): Promise<Resultado<T>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/semana-padrao${consulta}`;
  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, init);
  } catch (e) {
    return { ok: false, erro: { tipo: "rede", mensagem: e instanceof Error ? e.message : String(e) } };
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

/** `GET /atletas/{id}/semana-padrao[?em=AAAA-MM-DD]`: a semana vigente (hoje, sem `em`) e o histórico. */
export function buscarSemanaPadrao(
  atletaId: number,
  em?: string,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<SemanaPadrao>> {
  return chamar<SemanaPadrao>(
    atletaId,
    em ? `?em=${encodeURIComponent(em)}` : "",
    { headers: { Accept: "application/json" } },
    opcoes,
  );
}

/** `PUT /atletas/{id}/semana-padrao`: cria ou substitui a vigência `vigente_desde`. */
export function gravarSemanaPadrao(
  atletaId: number,
  envio: SemanaPadraoEnvio,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<SemanaPadraoGravada>> {
  return chamar<SemanaPadraoGravada>(
    atletaId,
    "",
    {
      method: "PUT",
      headers: { Accept: "application/json", "Content-Type": "application/json" },
      body: JSON.stringify(envio),
    },
    opcoes,
  );
}
