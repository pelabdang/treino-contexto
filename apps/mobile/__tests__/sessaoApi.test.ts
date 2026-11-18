import { entrar, quemSou, sair, trocarSenha } from "../src/sessao/api";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo?: unknown) =>
  jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as jest.Mock & typeof fetch;
const base = { baseUrl: "http://api.teste/" };

describe("api de sessão", () => {
  it("POST /sessao manda e-mail e senha e devolve o acesso", async () => {
    const f = fetchCom(200, { token: "t", papel: "atleta", atleta_id: 1, professor_id: null, nome: "Atleta Fixture 1", expira_em: "x", troca_de_senha_obrigatoria: false });
    const r = await entrar("atleta1@exemplo.com", "senha-sintetica", { ...base, fetch: f });
    expect(r.ok && r.dados.atleta_id).toBe(1);
    const [url, init] = f.mock.calls[0];
    expect(url).toBe("http://api.teste/sessao");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(String(init?.body))).toEqual({ email: "atleta1@exemplo.com", senha: "senha-sintetica" });
    expect((init?.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("401 vira não autorizado, sem repetir nada do que foi enviado", async () => {
    const r = await entrar("a@exemplo.com", "SEGREDO-123", { ...base, fetch: fetchCom(401, { detail: "e-mail ou senha incorretos" }) });
    expect(r).toEqual({ ok: false, falha: { motivo: "nao_autorizado" } });
    expect(JSON.stringify(r)).not.toContain("SEGREDO-123");
  });

  it("429 traz o tempo de espera da API", async () => {
    expect(await entrar("a@exemplo.com", "x", { ...base, fetch: fetchCom(429, { detail: "muitas tentativas", espere_s: 300 }) })).toEqual({
      ok: false,
      falha: { motivo: "espere", espereS: 300 },
    });
    expect(await entrar("a@exemplo.com", "x", { ...base, fetch: fetchCom(429, {}) })).toEqual({ ok: false, falha: { motivo: "espere", espereS: 0 } });
  });

  it("rede e erro do servidor", async () => {
    const quebrado = jest.fn(async () => {
      throw new Error("MARCADOR-REDE");
    }) as unknown as typeof fetch;
    const r = await entrar("a@exemplo.com", "x", { ...base, fetch: quebrado });
    expect(r).toEqual({ ok: false, falha: { motivo: "rede" } });
    expect(JSON.stringify(r)).not.toContain("MARCADOR");
    expect(await entrar("a@exemplo.com", "x", { ...base, fetch: fetchCom(500, {}) })).toEqual({ ok: false, falha: { motivo: "servidor", status: 500 } });
  });

  it("GET /sessao e DELETE /sessao mandam o Bearer", async () => {
    const f = fetchCom(200, { papel: "professor", atleta_id: null, professor_id: 2, nome: "Professor Fixture 2", expira_em: "x", troca_de_senha_obrigatoria: false });
    const r = await quemSou({ ...base, fetch: f, token: "token-sintetico" });
    expect(r.ok && r.dados.professor_id).toBe(2);
    expect((f.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBe("Bearer token-sintetico");
    const g = fetchCom(204);
    expect((await sair({ ...base, fetch: g, token: "t" })).ok).toBe(true);
    expect(g.mock.calls[0][1]?.method).toBe("DELETE");
    expect(String(g.mock.calls[0][0])).toBe("http://api.teste/sessao");
  });

  it("PUT /conta/senha: 200 devolve o acesso novo; 422 diz qual senha", async () => {
    const f = fetchCom(200, { token: "novo", expira_em: "x" });
    const r = await trocarSenha("atual", "nova-senha-longa", { ...base, fetch: f, token: "t" });
    expect(r.ok && r.dados.token).toBe("novo");
    expect(JSON.parse(String(f.mock.calls[0][1]?.body))).toEqual({ senha_atual: "atual", senha_nova: "nova-senha-longa" });
    for (const tipo of ["senha_atual_incorreta", "senha_nova_invalida"]) {
      const e = await trocarSenha("a", "b", { ...base, fetch: fetchCom(422, { detail: [{ loc: ["body", "x"], msg: "m", type: tipo }] }) });
      expect(e).toEqual({ ok: false, falha: { motivo: "invalido", tipo } });
    }
    expect(await trocarSenha("a", "b", { ...base, fetch: fetchCom(401, {}) })).toEqual({ ok: false, falha: { motivo: "nao_autorizado" } });
  });
});
