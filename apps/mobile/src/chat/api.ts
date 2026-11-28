// Chamadas do chat (ADR 0017, adendo 16 da ADR 0004). Os tipos vêm do cliente gerado (@treino/api-client); as funções moram aqui, como
// na semana-padrão e na caixa, porque o pacote só exporta os tipos. Nunca lançam: devolvem `ResultadoChat`.
// Privacidade: pergunta, resposta e texto de erro não vão a log, console, mensagem de erro nem armazenamento.
import type { components, OpcoesCliente } from "@treino/api-client";

import { TEMPO_LIMITE_PEDIDO_MS } from "./textos";

export type ConversaChat = components["schemas"]["ConversaOut"];
export type ConversaResumo = components["schemas"]["ConversaResumoOut"];
export type MensagemChat = components["schemas"]["MensagemOut"];
export type LinkChat = components["schemas"]["LinkOut"];

/** `429`: `detail` e `espere_texto` prontos (a API formata; o app não converte `espere_s` em minutos). Tolerante: se `espere_texto` faltar, só o `detail` aparece. */
export type LimiteChat = Omit<components["schemas"]["app__rotas__chat__Muitas"], "espere_texto"> & Partial<Pick<components["schemas"]["app__rotas__chat__Muitas"], "espere_texto">>;

export type ErroChat =
  | { tipo: "rede" }
  | { tipo: "tempo" }
  | { tipo: "nao_encontrada" }
  | { tipo: "limite"; limite: LimiteChat }
  | { tipo: "http"; status: number };
export type ResultadoChat<T> = { ok: true; dados: T } | { ok: false; erro: ErroChat };

type Opcoes = OpcoesCliente & { tempoMs?: number };

const BASE_PADRAO = "http://localhost:8000";
const JSON_ACEITO = { Accept: "application/json" };
const JSON_ENVIADO = { ...JSON_ACEITO, "Content-Type": "application/json" };

async function chamar<T>(atletaId: number, caminho: string, init: RequestInit, opcoes: Opcoes): Promise<ResultadoChat<T>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/conversas${caminho}`;
  const controle = new AbortController();
  const relogio = setTimeout(() => controle.abort(), opcoes.tempoMs ?? TEMPO_LIMITE_PEDIDO_MS);
  (relogio as { unref?: () => void }).unref?.(); // no Node (testes) o relógio não segura o processo
  let resposta: Response;
  try {
    resposta = await (opcoes.fetch ?? fetch)(url, { ...init, signal: controle.signal });
  } catch {
    return { ok: false, erro: controle.signal.aborted ? { tipo: "tempo" } : { tipo: "rede" } };
  } finally {
    clearTimeout(relogio);
  }
  if (resposta.status === 204) return { ok: true, dados: undefined as T };
  if (resposta.ok) {
    try {
      return { ok: true, dados: (await resposta.json()) as T };
    } catch {
      return { ok: false, erro: { tipo: "http", status: resposta.status } };
    }
  }
  if (resposta.status === 404) return { ok: false, erro: { tipo: "nao_encontrada" } };
  if (resposta.status === 429) {
    try {
      const corpo = (await resposta.json()) as Partial<LimiteChat>;
      const limite: LimiteChat = { detail: String(corpo.detail ?? ""), espere_s: Number(corpo.espere_s ?? 0) };
      if (typeof corpo.espere_texto === "string" && corpo.espere_texto) limite.espere_texto = corpo.espere_texto;
      return { ok: false, erro: { tipo: "limite", limite } };
    } catch {
      return { ok: false, erro: { tipo: "limite", limite: { detail: "", espere_s: 0 } } };
    }
  }
  return { ok: false, erro: { tipo: "http", status: resposta.status } };
}

/** `GET /atletas/{id}/chat/perguntas-prontas` (#629): as perguntas prontas escolhidas pela API conforme os treinos (até 6; o app ignora o que passar). */
export async function buscarPerguntasProntas(atletaId: number, opcoes: Opcoes = {}): Promise<ResultadoChat<string[]>> {
  const base = (opcoes.baseUrl ?? BASE_PADRAO).replace(/\/+$/, "");
  const url = `${base}/atletas/${encodeURIComponent(String(atletaId))}/chat/perguntas-prontas`;
  try {
    const resposta = await (opcoes.fetch ?? fetch)(url, { headers: JSON_ACEITO });
    if (!resposta.ok) return { ok: false, erro: { tipo: "http", status: resposta.status } };
    const corpo = (await resposta.json()) as { perguntas?: unknown };
    const lista = Array.isArray(corpo.perguntas) ? corpo.perguntas.filter((p): p is string => typeof p === "string" && p.trim() !== "") : [];
    return { ok: true, dados: lista.slice(0, 6) };
  } catch {
    return { ok: false, erro: { tipo: "rede" } };
  }
}

/** `PUT .../conversas/{id}/mensagens/{mid}/avaliacao`: `1` (👍), `-1` (👎) ou `null` (desfaz). Só o valor vai; nada do texto. */
export function avaliarMensagem(atletaId: number, conversaId: number, mensagemId: number, valor: 1 | -1 | null, opcoes: Opcoes = {}): Promise<ResultadoChat<MensagemChat>> {
  return chamar<MensagemChat>(atletaId, `/${conversaId}/mensagens/${mensagemId}/avaliacao`, { method: "PUT", headers: JSON_ENVIADO, body: JSON.stringify({ valor }) }, opcoes);
}

/** `GET /atletas/{id}/conversas`: da mais recente para a mais antiga. */
export async function listarConversas(atletaId: number, opcoes: Opcoes = {}): Promise<ResultadoChat<ConversaResumo[]>> {
  const r = await chamar<{ conversas: ConversaResumo[] }>(atletaId, "", { headers: JSON_ACEITO }, opcoes);
  return r.ok ? { ok: true, dados: r.dados.conversas ?? [] } : r;
}

/** `POST /atletas/{id}/conversas`: abre a conversa e responde a primeira pergunta (síncrono). */
export function criarConversa(atletaId: number, pergunta: string, opcoes: Opcoes = {}): Promise<ResultadoChat<ConversaChat>> {
  return chamar<ConversaChat>(atletaId, "", { method: "POST", headers: JSON_ENVIADO, body: JSON.stringify({ pergunta }) }, opcoes);
}

/** `POST /atletas/{id}/conversas/{conversaId}/mensagens`: continua a conversa (síncrono). */
export function enviarMensagem(atletaId: number, conversaId: number, pergunta: string, opcoes: Opcoes = {}): Promise<ResultadoChat<MensagemChat>> {
  return chamar<MensagemChat>(atletaId, `/${conversaId}/mensagens`, { method: "POST", headers: JSON_ENVIADO, body: JSON.stringify({ pergunta }) }, opcoes);
}

/** `GET /atletas/{id}/conversas/{conversaId}`: a conversa com as mensagens. */
export function buscarConversa(atletaId: number, conversaId: number, opcoes: Opcoes = {}): Promise<ResultadoChat<ConversaChat>> {
  return chamar<ConversaChat>(atletaId, `/${conversaId}`, { headers: JSON_ACEITO }, opcoes);
}

/** `DELETE /atletas/{id}/conversas/{conversaId}`: apaga de verdade (`204`). */
export function apagarConversa(atletaId: number, conversaId: number, opcoes: Opcoes = {}): Promise<ResultadoChat<void>> {
  return chamar<void>(atletaId, `/${conversaId}`, { method: "DELETE", headers: JSON_ACEITO }, opcoes);
}
