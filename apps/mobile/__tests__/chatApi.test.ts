import { apagarConversa, buscarConversa, criarConversa, enviarMensagem, listarConversas } from "../src/chat/api";
import { conversa, mensagem } from "../__fixtures__/chat";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo?: unknown) => jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;
const base = { baseUrl: "http://api.teste/" };

describe("chamadas do chat", () => {
  it("cada chamada vai ao endereço e ao método do contrato", async () => {
    const f = fetchCom(200, { atleta_id: 1, conversas: [] });
    await listarConversas(1, { ...base, fetch: f });
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/conversas");
    const g = fetchCom(201, conversa());
    await criarConversa(1, "Oi", { ...base, fetch: g });
    expect(g.mock.calls[0][0]).toBe("http://api.teste/atletas/1/conversas");
    expect(g.mock.calls[0][1]).toMatchObject({ method: "POST", body: JSON.stringify({ pergunta: "Oi" }) });
    const h = fetchCom(200, mensagem());
    await enviarMensagem(1, 7, "Oi", { ...base, fetch: h });
    expect(h.mock.calls[0][0]).toBe("http://api.teste/atletas/1/conversas/7/mensagens");
    const i = fetchCom(200, conversa());
    await buscarConversa(1, 7, { ...base, fetch: i });
    expect(i.mock.calls[0][0]).toBe("http://api.teste/atletas/1/conversas/7");
    const j = fetchCom(204);
    expect(await apagarConversa(1, 7, { ...base, fetch: j })).toEqual({ ok: true, dados: undefined });
    expect(j.mock.calls[0][1]).toMatchObject({ method: "DELETE" });
  });

  it("a lista devolve só as conversas", async () => {
    const r = await listarConversas(1, { ...base, fetch: fetchCom(200, { atleta_id: 1, conversas: [{ id: 3, titulo: "x", criada_em: "a", atualizada_em: "b" }] }) });
    expect(r).toEqual({ ok: true, dados: [{ id: 3, titulo: "x", criada_em: "a", atualizada_em: "b" }] });
  });

  it("429 traz o detail e o espere_texto como vieram; sem espere_texto, só o detail", async () => {
    const com = await criarConversa(1, "Oi", { ...base, fetch: fetchCom(429, { detail: "Você fez 20 perguntas na última hora.", espere_texto: "Você pode perguntar de novo em 12 min.", espere_s: 720 }) });
    expect(com).toEqual({ ok: false, erro: { tipo: "limite", limite: { detail: "Você fez 20 perguntas na última hora.", espere_texto: "Você pode perguntar de novo em 12 min.", espere_s: 720 } } });
    const sem = await criarConversa(1, "Oi", { ...base, fetch: fetchCom(429, { detail: "Você fez 20 perguntas na última hora.", espere_s: 720 }) });
    expect(sem).toEqual({ ok: false, erro: { tipo: "limite", limite: { detail: "Você fez 20 perguntas na última hora.", espere_s: 720 } } });
  });

  it("404, 500 e queda de rede viram erros tipados", async () => {
    expect(await buscarConversa(1, 9, { ...base, fetch: fetchCom(404, { detail: "x" }) })).toEqual({ ok: false, erro: { tipo: "nao_encontrada" } });
    expect(await buscarConversa(1, 9, { ...base, fetch: fetchCom(500, { detail: "x" }) })).toEqual({ ok: false, erro: { tipo: "http", status: 500 } });
    const cai = jest.fn().mockRejectedValue(new Error("x")) as unknown as typeof fetch;
    expect(await buscarConversa(1, 9, { ...base, fetch: cai })).toEqual({ ok: false, erro: { tipo: "rede" } });
  });

  it("desiste do pedido depois do tempo do cliente", async () => {
    const preso = ((_u: unknown, init?: RequestInit) =>
      new Promise((_ok, falha) => init?.signal?.addEventListener("abort", () => falha(new Error("abortado"))))) as unknown as typeof fetch;
    expect(await criarConversa(1, "Oi", { ...base, fetch: preso, tempoMs: 5 })).toEqual({ ok: false, erro: { tipo: "tempo" } });
  });
});
