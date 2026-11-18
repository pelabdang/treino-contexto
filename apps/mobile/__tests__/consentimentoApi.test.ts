import { buscarProfessores, buscarTermo, darConsentimento, dataCurta, ordenar, retirarConsentimento, totalAguardando, type Vinculo } from "../src/consentimento/api";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo?: unknown) => jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as jest.Mock & typeof fetch;
const base = { baseUrl: "http://api.teste" };

const v = (id: number, nome: string, consentimento: boolean): Vinculo => ({
  professor_id: id,
  nome,
  consentimento,
  termo_versao: null,
  consentimento_em: consentimento ? "2026-11-10T12:00:00Z" : null,
  consentimento_revogado_em: null,
  termo_desatualizado: false,
});

describe("api do consentimento", () => {
  it("chama as rotas do contrato da ADR 0016", async () => {
    const f = fetchCom(200, { atleta_id: 1, termo_vigente: "t", professores: [] });
    await buscarProfessores(3, { ...base, fetch: f });
    expect(String(f.mock.calls[0][0])).toBe("http://api.teste/atletas/3/professores");
    const t = fetchCom(200, { versao: "t", provisorio: true, texto: "x" });
    await buscarTermo({ ...base, fetch: t });
    expect(String(t.mock.calls[0][0])).toBe("http://api.teste/termo-de-consentimento");
    const p = fetchCom(200, v(5, "X", true));
    await darConsentimento(3, 5, "termo@1", { ...base, fetch: p });
    expect(String(p.mock.calls[0][0])).toBe("http://api.teste/atletas/3/professores/5/consentimento");
    expect(p.mock.calls[0][1]?.method).toBe("PUT");
    expect(JSON.parse(String(p.mock.calls[0][1]?.body))).toEqual({ termo_versao: "termo@1" });
    const d = fetchCom(204);
    const r = await retirarConsentimento(3, 5, { ...base, fetch: d });
    expect(r.ok).toBe(true);
    expect(d.mock.calls[0][1]?.method).toBe("DELETE");
  });

  it("409 e 404 chegam como erro tipado, sem repetir o corpo na mensagem", async () => {
    const r409 = await darConsentimento(1, 2, "velho", { ...base, fetch: fetchCom(409, { detail: "o termo mudou" }) });
    expect(r409).toEqual({ ok: false, erro: { tipo: "http", status: 409 } });
    const r404 = await darConsentimento(1, 2, "t", { ...base, fetch: fetchCom(404, { detail: "vínculo não encontrado" }) });
    expect(!r404.ok && r404.erro.tipo).toBe("nao_encontrado");
  });

  it("ordena aguardando primeiro e conta os pedidos", () => {
    const lista = ordenar([v(1, "Marina", true), v(2, "Paulo", false), v(3, "Carlos", false), v(4, "Ana", true)]);
    expect(lista.map((x) => x.nome)).toEqual(["Carlos", "Paulo", "Ana", "Marina"]);
    expect(totalAguardando(lista)).toBe(2);
  });

  it("formata a data como dd/mm/aa", () => {
    expect(dataCurta("2026-11-10T12:00:00Z")).toBe("10/11/26");
    expect(dataCurta(null)).toBe("");
    expect(dataCurta("lixo")).toBe("");
  });
});
