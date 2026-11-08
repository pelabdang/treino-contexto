import { buscarCarga, buscarEvolucaoTiros1km, enviarAtividadeFit, type EvolucaoTiros1km } from "@treino/api-client";

// Exemplo gerado pelo TestClient com as fixtures sintéticas (services/api/scripts/exportar_openapi.py).
import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";

import exemploCarga from "../../../packages/api-client/exemplos/carga.json";

function respostaJson(corpo: unknown, status = 200): Response {
  return new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } });
}

describe("buscarEvolucaoTiros1km", () => {
  it("200: devolve o JSON tipado e monta a URL com o período", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson(exemplo));
    const r = await buscarEvolucaoTiros1km(1, { inicio: "2025-03-01", fim: "2025-03-31" }, {
      baseUrl: "http://api.local:8000/",
      fetch: falso,
    });
    expect(falso.mock.calls[0][0]).toBe(
      "http://api.local:8000/atletas/1/evolucao/tiros-1km?inicio=2025-03-01&fim=2025-03-31",
    );
    expect(r.ok).toBe(true);
    if (r.ok) {
      const dados: EvolucaoTiros1km = r.dados;
      expect(dados.metrica).toBe("tiros_1km");
      expect(dados.sessoes[0].pace_medio).toBe("4:11");
      expect(dados.sessoes[0].tiros[0].pace).toBe("4:15");
      expect(dados.eixos?.pace?.invertido).toBe(true);
    }
  });

  it("sem filtro nem opções: URL sem query, no padrão local", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson(exemplo));
    const original = globalThis.fetch;
    globalThis.fetch = falso;
    try {
      await buscarEvolucaoTiros1km(7);
    } finally {
      globalThis.fetch = original;
    }
    expect(falso.mock.calls[0][0]).toBe("http://localhost:8000/atletas/7/evolucao/tiros-1km");
  });

  it("404: erro tipado com o detail da API", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson({ detail: "atleta não encontrado" }, 404));
    const r = await buscarEvolucaoTiros1km(9999, {}, { fetch: falso });
    expect(r).toEqual({
      ok: false,
      erro: { tipo: "nao_encontrado", status: 404, detalhe: { detail: "atleta não encontrado" } },
    });
  });

  it("422: erro tipado com a lista de problemas", async () => {
    const detalhe = { detail: [{ type: "value_error", loc: ["query", "fim"], msg: "fim antes de inicio" }] };
    const falso = jest.fn().mockResolvedValue(respostaJson(detalhe, 422));
    const r = await buscarEvolucaoTiros1km(1, { inicio: "2025-03-11", fim: "2025-03-04" }, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "validacao", status: 422, detalhe } });
  });

  it("erro de rede: não lança, devolve tipo rede", async () => {
    const falso = jest.fn().mockRejectedValue(new TypeError("Network request failed"));
    const r = await buscarEvolucaoTiros1km(1, {}, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "rede", mensagem: "Network request failed" } });
  });

  it("outro status ou corpo que não é JSON: erro http", async () => {
    const f500 = jest.fn().mockResolvedValue(new Response("boom", { status: 500 }));
    expect(await buscarEvolucaoTiros1km(1, {}, { fetch: f500 })).toEqual({ ok: false, erro: { tipo: "http", status: 500 } });
    const f404 = jest.fn().mockResolvedValue(new Response("<html>", { status: 404 }));
    expect(await buscarEvolucaoTiros1km(1, {}, { fetch: f404 })).toEqual({ ok: false, erro: { tipo: "http", status: 404 } });
  });
});

describe("enviarAtividadeFit", () => {
  const arquivo = { uri: "file:///tmp/a.fit", name: "a.fit", type: "application/octet-stream" };
  const ok = { resultado: "inserida", atividade_id: 7, avisos: [] };

  it("201: criada, URL e campo `arquivo` no multipart", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson(ok, 201));
    const r = await enviarAtividadeFit(3, arquivo, { baseUrl: "http://api.local:8000/", fetch: falso });
    expect(falso.mock.calls[0][0]).toBe("http://api.local:8000/atletas/3/atividades/fit");
    const init = falso.mock.calls[0][1];
    expect(init.method).toBe("POST");
    expect(init.body).toBeInstanceOf(FormData);
    expect(init.body.has("arquivo")).toBe(true);
    expect(r).toEqual({ ok: true, dados: { criada: true, resposta: ok } });
  });

  it("201 com Blob (web): usa o nome informado", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson(ok, 201));
    const r = await enviarAtividadeFit(1, new Blob([new Uint8Array([1, 2])]), { fetch: falso, nome: "treino.fit" });
    expect(r.ok).toBe(true);
    expect(falso.mock.calls[0][1].body.get("arquivo").name).toBe("treino.fit");
  });

  it("200: atividade que já existia", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson({ ...ok, resultado: "ignorada" }, 200));
    const r = await enviarAtividadeFit(1, arquivo, { fetch: falso });
    expect(r.ok && r.dados.criada).toBe(false);
  });

  it.each([
    [400, "FIT inválido"],
    [413, "Arquivo grande demais"],
  ])("%i: erro http com o detail da API", async (status, detail) => {
    const falso = jest.fn().mockResolvedValue(respostaJson({ detail }, status));
    const r = await enviarAtividadeFit(1, arquivo, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "http", status, detail } });
  });

  it("404: atleta não encontrado", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson({ detail: "Atleta não encontrado" }, 404));
    const r = await enviarAtividadeFit(99, arquivo, { fetch: falso });
    expect(r).toEqual({
      ok: false,
      erro: { tipo: "nao_encontrado", status: 404, detalhe: { detail: "Atleta não encontrado" } },
    });
  });

  it("422: validação no formato do FastAPI", async () => {
    const corpo = { detail: [{ loc: ["body", "arquivo"], msg: "Field required", type: "missing" }] };
    const falso = jest.fn().mockResolvedValue(respostaJson(corpo, 422));
    const r = await enviarAtividadeFit(1, arquivo, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "validacao", status: 422, detalhe: corpo } });
  });

  it("corpo que não é JSON: http sem detail", async () => {
    const falso = jest.fn().mockResolvedValue(new Response("<html>", { status: 502 }));
    const r = await enviarAtividadeFit(1, arquivo, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "http", status: 502 } });
  });

  it("falha de rede: erro `rede`, sem lançar", async () => {
    const falso = jest.fn().mockRejectedValue(new Error("Network request failed"));
    const r = await enviarAtividadeFit(1, arquivo, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "rede", mensagem: "Network request failed" } });
  });
});

describe("buscarCarga", () => {
  it("200: devolve a série tipada e monta a URL com o período", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson(exemploCarga));
    const r = await buscarCarga(1, { inicio: "2025-03-01", fim: "2025-03-31" }, { baseUrl: "http://api.local:8000/", fetch: falso });
    expect(falso.mock.calls[0][0]).toBe("http://api.local:8000/atletas/1/carga?inicio=2025-03-01&fim=2025-03-31");
    expect(r.ok).toBe(true);
    if (r.ok) {
      expect(r.dados.versao).toBe("serie_carga@1");
      expect(r.dados.dias.length).toBeGreaterThan(0);
      expect(Object.keys(r.dados.totais.por_motivo)).toHaveLength(6);
    }
  });

  it("404 vira nao_encontrado", async () => {
    const falso = jest.fn().mockResolvedValue(respostaJson({ detail: "atleta não encontrado" }, 404));
    const r = await buscarCarga(9, {}, { fetch: falso });
    expect(r).toEqual({ ok: false, erro: { tipo: "nao_encontrado", status: 404, detalhe: { detail: "atleta não encontrado" } } });
  });
});
