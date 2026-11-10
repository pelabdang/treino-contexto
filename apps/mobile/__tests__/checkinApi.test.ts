import { apagarCheckin, buscarCheckinsPendentes, motivo422, registrarCheckin } from "../src/checkin/api";
import { checkinExemplo, pendentes } from "../__fixtures__/checkin";

const resposta = (status: number, corpo?: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo?: unknown) =>
  jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;

const envio = { pse: 5, sensacao: 4, nada_a_relatar: true, atalhos: [], texto: null };

describe("cliente do check-in", () => {
  it("PUT envia o corpo em JSON para a rota da atividade", async () => {
    const f = fetchCom(200, checkinExemplo);
    const r = await registrarCheckin(1, 101, envio, { baseUrl: "http://api.teste/", fetch: f });
    expect(r).toEqual({ ok: true, dados: checkinExemplo });
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://api.teste/atletas/1/atividades/101/checkin");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body)).toEqual(envio);
  });

  it("DELETE aceita 204 sem corpo", async () => {
    const f = fetchCom(204);
    const r = await apagarCheckin(1, 101, { baseUrl: "http://api.teste", fetch: f });
    expect(r).toEqual({ ok: true, dados: null });
    expect(f.mock.calls[0][1].method).toBe("DELETE");
  });

  it("pendentes: com e sem o parâmetro dias", async () => {
    const f = fetchCom(200, pendentes);
    await buscarCheckinsPendentes(1, undefined, { baseUrl: "http://api.teste", fetch: f });
    await buscarCheckinsPendentes(1, 3, { baseUrl: "http://api.teste", fetch: f });
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/checkins/pendentes");
    expect(f.mock.calls[1][0]).toBe("http://api.teste/atletas/1/checkins/pendentes?dias=3");
  });

  it("devolve erro tipado para rede, 404, 422 e 500, sem lançar", async () => {
    const rede = jest.fn().mockRejectedValue(new Error("x")) as unknown as typeof fetch;
    expect((await registrarCheckin(1, 1, envio, { fetch: rede })).ok).toBe(false);
    const r404 = await registrarCheckin(1, 1, envio, { fetch: fetchCom(404, { detail: "atividade não encontrada" }) });
    expect(!r404.ok && r404.erro.tipo).toBe("nao_encontrado");
    const r422 = await registrarCheckin(1, 1, envio, { fetch: fetchCom(422, { detail: [{ loc: [], msg: "m", type: "fora_do_prazo" }] }) });
    expect(!r422.ok && motivo422(r422.erro)).toBe("fora_do_prazo");
    const r500 = await registrarCheckin(1, 1, envio, { fetch: fetchCom(500, {}) });
    expect(!r500.ok && r500.erro).toEqual({ tipo: "http", status: 500 });
  });

  it("motivo422 reconhece os dois códigos de domínio e trata o resto como outro", () => {
    const erro = (type: string) => ({ tipo: "validacao" as const, status: 422 as const, detalhe: { detail: [{ loc: [], msg: "m", type }] } });
    expect(motivo422(erro("atividade_sem_checkin"))).toBe("atividade_sem_checkin");
    expect(motivo422(erro("string_too_long"))).toBe("outro");
    expect(motivo422({ tipo: "rede", mensagem: "x" })).toBe("outro");
  });
});
