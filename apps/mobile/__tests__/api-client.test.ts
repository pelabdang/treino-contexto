import { buscarEvolucaoTiros1km, type EvolucaoTiros1km } from "@treino/api-client";

// Exemplo gerado pelo TestClient com as fixtures sintéticas (services/api/scripts/exportar_openapi.py).
import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";

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
