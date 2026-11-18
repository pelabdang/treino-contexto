// Chamadas de identidade da ADR 0016 (item 4): POST/GET/DELETE /sessao e PUT /conta/senha. Os tipos vêm do cliente gerado.
// Nunca lançam. Privacidade: e-mail, senha, token e corpo recebido NUNCA vão para log, console, mensagem de erro nem URL.
import type { components, OpcoesCliente } from "@treino/api-client";

export type Entrou = components["schemas"]["EntrarOut"];
export type QuemSou = components["schemas"]["QuemSouOut"];
export type NovoAcesso = components["schemas"]["AcessoOut"];

const BASE_PADRAO = "http://localhost:8000";

/** Por que a chamada falhou, em palavras que a tela entende (sem repetir nada do que foi enviado). */
export type Falha =
  | { motivo: "nao_autorizado" } // 401
  | { motivo: "espere"; espereS: number } // 429
  | { motivo: "invalido"; tipo: string | null } // 422 (`type` do primeiro item de `detail`)
  | { motivo: "rede" }
  | { motivo: "servidor"; status: number };

export type ResultadoSessao<T> = { ok: true; dados: T } | { ok: false; falha: Falha };

type Opcoes = OpcoesCliente & { token?: string };

async function chamar<T>(metodo: string, caminho: string, corpo: unknown, opcoes: Opcoes, semCorpo = false): Promise<ResultadoSessao<T>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const headers: Record<string, string> = { Accept: "application/json" };
  if (corpo !== undefined) headers["Content-Type"] = "application/json";
  if (opcoes.token) headers.Authorization = `Bearer ${opcoes.token}`;
  let r: Response;
  try {
    r = await (opcoes.fetch ?? fetch)(`${base}${caminho}`, { method: metodo, headers, body: corpo === undefined ? undefined : JSON.stringify(corpo) });
  } catch {
    return { ok: false, falha: { motivo: "rede" } };
  }
  if (r.ok) {
    if (semCorpo) return { ok: true, dados: null as T };
    try {
      return { ok: true, dados: (await r.json()) as T };
    } catch {
      return { ok: false, falha: { motivo: "servidor", status: r.status } };
    }
  }
  if (r.status === 401) return { ok: false, falha: { motivo: "nao_autorizado" } };
  if (r.status === 429) {
    let espereS = 0;
    try {
      const n = Number(((await r.json()) as { espere_s?: unknown }).espere_s);
      if (Number.isFinite(n) && n > 0) espereS = Math.ceil(n);
    } catch {
      // sem corpo: tenta o cabeçalho
    }
    if (espereS === 0) {
      // `Retry-After` repete o valor (ADR 0016): lido antes de a tela assumir um tempo próprio.
      const n = Number(r.headers?.get?.("retry-after"));
      if (Number.isFinite(n) && n > 0) espereS = Math.ceil(n);
    }
    return { ok: false, falha: { motivo: "espere", espereS } };
  }
  if (r.status === 422) {
    let tipo: string | null = null;
    try {
      const detail = ((await r.json()) as { detail?: unknown }).detail;
      const primeiro = Array.isArray(detail) ? (detail[0] as { type?: unknown } | undefined) : undefined;
      if (typeof primeiro?.type === "string") tipo = primeiro.type;
    } catch {
      // corpo que não é JSON
    }
    return { ok: false, falha: { motivo: "invalido", tipo } };
  }
  return { ok: false, falha: { motivo: "servidor", status: r.status } };
}

/** `POST /sessao`: 401 uniforme (e-mail inexistente, senha errada e conta desativada); 429 com `espere_s`. */
export const entrar = (email: string, senha: string, opcoes: Opcoes) => chamar<Entrou>("POST", "/sessao", { email, senha }, opcoes);

/** `GET /sessao`: quem sou (papel, ids, nome, `troca_de_senha_obrigatoria`). */
export const quemSou = (opcoes: Opcoes) => chamar<QuemSou>("GET", "/sessao", undefined, opcoes);

/** `DELETE /sessao`: revoga a sessão atual (204). */
export const sair = (opcoes: Opcoes) => chamar<null>("DELETE", "/sessao", undefined, opcoes, true);

/** `PUT /conta/senha`: revoga todas as sessões e devolve o acesso novo. 422 `senha_atual_incorreta` ou `senha_nova_invalida`. */
export const trocarSenha = (senhaAtual: string, senhaNova: string, opcoes: Opcoes) =>
  chamar<NovoAcesso>("PUT", "/conta/senha", { senha_atual: senhaAtual, senha_nova: senhaNova }, opcoes);
