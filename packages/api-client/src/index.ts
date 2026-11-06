// Cliente da API treino-contexto. Os tipos vêm de `schema.d.ts`, gerado do OpenAPI (docs/modulos/api-client.md).
// Não formata pace nem escolhe escala: tudo vem pronto da API (ADR 0004).
import type { components, operations } from "./schema";

export type { components, operations } from "./schema";

export type EvolucaoTiros1km = components["schemas"]["EvolucaoTiros1km"];
export type SessaoTiros = components["schemas"]["SessaoOut"];
export type TiroSessao = components["schemas"]["TiroOut"];
export type RespostaUploadFit = components["schemas"]["UploadFitOut"];
export type Atividade = components["schemas"]["AtividadeOut"];
/** Clima da atividade: `estado` e, só em `ok`, `temperatura_c`, `sensacao_c`, `umidade_pct` e `vento_kmh` (ADR 0007). */
export type ClimaAtividade = components["schemas"]["ClimaOut"];
export type EstadoClima = ClimaAtividade["estado"];
export type Eixos = components["schemas"]["Eixos"];
export type ErroNaoEncontrado = components["schemas"]["Erro"];
export type ErroValidacao = components["schemas"]["HTTPValidationError"];

export type FiltroPeriodo = {
  /** AAAA-MM-DD, data local, inclusiva. */
  inicio?: string;
  /** AAAA-MM-DD, data local, inclusiva. */
  fim?: string;
};

export type OpcoesCliente = {
  /** Padrão `http://localhost:8000`. */
  baseUrl?: string;
  /** Padrão: o `fetch` global. Troque nos testes. */
  fetch?: typeof fetch;
};

export type ErroApi =
  | { tipo: "nao_encontrado"; status: 404; detalhe: ErroNaoEncontrado }
  | { tipo: "validacao"; status: 422; detalhe: ErroValidacao }
  | { tipo: "http"; status: number; /** `detail` da API (400, 413...), quando vier no corpo. */ detail?: string }
  | { tipo: "rede"; mensagem: string };

export type Resultado<T> = { ok: true; dados: T } | { ok: false; erro: ErroApi };

export const BASE_URL_PADRAO = "http://localhost:8000";

/** `GET /atletas/{atletaId}/evolucao/tiros-1km`. Nunca lança: devolve o JSON tipado ou um erro tipado. */
export async function buscarEvolucaoTiros1km(
  atletaId: number,
  filtro: FiltroPeriodo = {},
  opcoes: OpcoesCliente = {},
): Promise<Resultado<EvolucaoTiros1km>> {
  const base = (opcoes.baseUrl ?? BASE_URL_PADRAO).replace(/\/+$/, "");
  const consulta = new URLSearchParams();
  if (filtro.inicio) consulta.set("inicio", filtro.inicio);
  if (filtro.fim) consulta.set("fim", filtro.fim);
  const texto = consulta.toString();
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/evolucao/tiros-1km${texto ? `?${texto}` : ""}`;

  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, { headers: { Accept: "application/json" } });
  } catch (e) {
    return { ok: false, erro: { tipo: "rede", mensagem: e instanceof Error ? e.message : String(e) } };
  }

  if (resposta.ok) {
    try {
      return { ok: true, dados: (await resposta.json()) as EvolucaoTiros1km };
    } catch {
      return { ok: false, erro: { tipo: "http", status: resposta.status } };
    }
  }
  if (resposta.status === 404 || resposta.status === 422) {
    try {
      const detalhe = await resposta.json();
      return resposta.status === 404
        ? { ok: false, erro: { tipo: "nao_encontrado", status: 404, detalhe: detalhe as ErroNaoEncontrado } }
        : { ok: false, erro: { tipo: "validacao", status: 422, detalhe: detalhe as ErroValidacao } };
    } catch {
      // corpo que não é JSON: cai no erro HTTP genérico
    }
  }
  return { ok: false, erro: { tipo: "http", status: resposta.status } };
}

/** `GET /atletas/{atletaId}/atividades/{atividadeId}`: a atividade com campos prontos e o `clima`. Nunca lança. */
export async function buscarAtividade(
  atletaId: number,
  atividadeId: number,
  opcoes: OpcoesCliente = {},
): Promise<Resultado<Atividade>> {
  const base = (opcoes.baseUrl ?? BASE_URL_PADRAO).replace(/\/+$/, "");
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/atividades/${encodeURIComponent(String(atividadeId))}`;

  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, { headers: { Accept: "application/json" } });
  } catch (e) {
    return { ok: false, erro: { tipo: "rede", mensagem: e instanceof Error ? e.message : String(e) } };
  }
  if (resposta.ok) {
    try {
      return { ok: true, dados: (await resposta.json()) as Atividade };
    } catch {
      return { ok: false, erro: { tipo: "http", status: resposta.status } };
    }
  }
  if (resposta.status === 404 || resposta.status === 422) {
    try {
      const detalhe = await resposta.json();
      return resposta.status === 404
        ? { ok: false, erro: { tipo: "nao_encontrado", status: 404, detalhe: detalhe as ErroNaoEncontrado } }
        : { ok: false, erro: { tipo: "validacao", status: 422, detalhe: detalhe as ErroValidacao } };
    } catch {
      // corpo que não é JSON: cai no erro HTTP genérico
    }
  }
  return { ok: false, erro: { tipo: "http", status: resposta.status } };
}

/** Arquivo para o upload: `File`/`Blob` (web) ou `{uri, name, type}` (React Native). */
export type ArquivoFit = Blob | { uri: string; name: string; type?: string };

export type SucessoUploadFit = {
  /** `true` no `201` (atividade nova); `false` no `200` (já existia). */
  criada: boolean;
  resposta: RespostaUploadFit;
};

/** `POST /atletas/{atletaId}/atividades/fit` (multipart, campo `arquivo`). Nunca lança. */
export async function enviarAtividadeFit(
  atletaId: number,
  arquivo: ArquivoFit,
  opcoes: OpcoesCliente & { nome?: string } = {},
): Promise<Resultado<SucessoUploadFit>> {
  const base = (opcoes.baseUrl ?? BASE_URL_PADRAO).replace(/\/+$/, "");
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/atividades/fit`;
  const form = new FormData();
  if (typeof Blob !== "undefined" && arquivo instanceof Blob) {
    form.append("arquivo", arquivo, opcoes.nome ?? (arquivo as File).name ?? "atividade.fit");
  } else {
    // React Native aceita {uri, name, type} no FormData.
    form.append("arquivo", arquivo as unknown as Blob);
  }

  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, { method: "POST", body: form, headers: { Accept: "application/json" } });
  } catch (e) {
    return { ok: false, erro: { tipo: "rede", mensagem: e instanceof Error ? e.message : String(e) } };
  }

  let corpo: unknown;
  try {
    corpo = await resposta.json();
  } catch {
    corpo = undefined;
  }
  if (resposta.status === 200 || resposta.status === 201) {
    if (corpo === undefined) return { ok: false, erro: { tipo: "http", status: resposta.status } };
    return { ok: true, dados: { criada: resposta.status === 201, resposta: corpo as RespostaUploadFit } };
  }
  if (resposta.status === 422 && corpo !== undefined) {
    return { ok: false, erro: { tipo: "validacao", status: 422, detalhe: corpo as ErroValidacao } };
  }
  if (resposta.status === 404 && corpo !== undefined) {
    return { ok: false, erro: { tipo: "nao_encontrado", status: 404, detalhe: corpo as ErroNaoEncontrado } };
  }
  const detail = (corpo as { detail?: unknown } | undefined)?.detail;
  return {
    ok: false,
    erro: typeof detail === "string" ? { tipo: "http", status: resposta.status, detail } : { tipo: "http", status: resposta.status },
  };
}
