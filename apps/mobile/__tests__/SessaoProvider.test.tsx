import { act, render, waitFor } from "@testing-library/react-native";

import { SessaoProvider, type SessaoContexto, useSessao } from "../src/sessao/SessaoProvider";

const mockMem = new Map<string, string>();
jest.mock("../src/sessao/armazenamento", () => ({
  lerToken: async () => mockMem.get("t") ?? null,
  gravarToken: async (v: string) => void mockMem.set("t", v),
  lerDestino: async () => mockMem.get("d") ?? null,
  gravarDestino: async (v: string) => void mockMem.set("d", v),
  apagarDestino: async () => void mockMem.delete("d"),
  apagarTudo: async (manter = false) => {
    mockMem.delete("t");
    if (!manter) mockMem.delete("d");
  },
}));

const API = "http://api.teste";
const resposta = (status: number, corpo?: unknown): Response =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo, clone() { return resposta(status, corpo); } }) as Response;
const QUEM_ATLETA = { papel: "atleta", atleta_id: 3, professor_id: null, nome: "Atleta Fixture 3", expira_em: "x", troca_de_senha_obrigatoria: false };
const QUEM_PROF = { papel: "professor", atleta_id: null, professor_id: 9, nome: "Professor Fixture 9", expira_em: "x", troca_de_senha_obrigatoria: false };

type Rota = (url: string, init?: RequestInit) => Response | Promise<Response>;
const servidor = (rotas: Record<string, Rota>) =>
  jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const chave = `${init?.method ?? "GET"} ${url.replace(API, "")}`;
    const r = rotas[chave];
    if (!r) throw new Error(`rota sem resposta: ${chave}`);
    return r(url, init);
  }) as unknown as jest.Mock & typeof fetch;

let ctx: SessaoContexto = undefined as unknown as SessaoContexto;
function Sonda() {
  ctx = useSessao();
  return null;
}
const abrir = async (f: typeof fetch) => {
  await render(
    <SessaoProvider apiUrl={API} fetchBase={f}>
      <Sonda />
    </SessaoProvider>,
  );
};

beforeEach(() => {
  mockMem.clear();
  ctx = undefined as unknown as SessaoContexto; // sem sobra de um teste anterior
});

describe("SessaoProvider: abrir o app", () => {
  it("sem acesso guardado: vai à entrada, sem faixa de expirado, e lembra o endereço pedido", async () => {
    const f = servidor({});
    await abrir(f);
    await waitFor(() => expect(ctx?.estado).toEqual({ tipo: "sem_acesso", expirou: false, lembrar: true }));
    expect(f).not.toHaveBeenCalled();
  });

  it("com acesso guardado que a API confirma: está dentro e o id vem da sessão", async () => {
    mockMem.set("t", "token-sintetico-a");
    const f = servidor({ "GET /sessao": () => resposta(200, QUEM_ATLETA) });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("dentro"));
    expect(ctx?.estado).toMatchObject({ papel: "atleta", atletaId: 3, professorId: null, nome: "Atleta Fixture 3" });
    expect((f.mock.calls[0][1]?.headers as Record<string, string>).Authorization).toBe("Bearer token-sintetico-a");
  });

  it("professor: o id do professor vem da sessão", async () => {
    mockMem.set("t", "tk");
    await abrir(servidor({ "GET /sessao": () => resposta(200, QUEM_PROF) }));
    await waitFor(() => expect(ctx?.estado).toMatchObject({ tipo: "dentro", papel: "professor", professorId: 9, atletaId: null }));
  });

  it("401 na abertura: apaga o acesso, guarda o endereço e mostra 'expirou'", async () => {
    mockMem.set("t", "velho");
    await abrir(servidor({ "GET /sessao": () => resposta(401, { detail: "não autenticado" }) }));
    await waitFor(() => expect(ctx?.estado).toEqual({ tipo: "sem_acesso", expirou: true, lembrar: true }));
    expect(mockMem.has("t")).toBe(false);
  });

  it("sem rede ou erro do servidor na abertura: não manda para a entrada e guarda o acesso", async () => {
    mockMem.set("t", "tk");
    const f = servidor({ "GET /sessao": () => resposta(500, {}) });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("sem_rede"));
    expect(mockMem.get("t")).toBe("tk");
    // tentar de novo
    f.mockImplementationOnce(async () => resposta(200, QUEM_ATLETA));
    await act(async () => ctx.verificarDeNovo());
    await waitFor(() => expect(ctx?.estado.tipo).toBe("dentro"));
  });
});

describe("SessaoProvider: entrar, sair e trocar a senha", () => {
  const ENTROU = { ...QUEM_ATLETA, token: "token-novo" };

  it("entrar guarda o acesso e passa a estar dentro; o e-mail é aparado e nada vai ao armazenamento além do token", async () => {
    const f = servidor({ "POST /sessao": () => resposta(200, ENTROU) });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("sem_acesso"));
    let r!: Awaited<ReturnType<typeof ctx.entrar>>;
    await act(async () => {
      r = await ctx.entrar("  atleta3@exemplo.com ", "senha-sintetica");
    });
    expect(r.ok).toBe(true);
    expect(JSON.parse(String(f.mock.calls[0][1]?.body))).toEqual({ email: "atleta3@exemplo.com", senha: "senha-sintetica" });
    expect(mockMem.get("t")).toBe("token-novo");
    expect([...mockMem.values()].join("|")).not.toContain("senha-sintetica");
    expect(ctx?.estado).toMatchObject({ tipo: "dentro", atletaId: 3 });
  });

  it("entrar com 401 ou 429 continua sem acesso e devolve a falha", async () => {
    const f = servidor({ "POST /sessao": () => resposta(401, { detail: "x" }) });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("sem_acesso"));
    let r!: Awaited<ReturnType<typeof ctx.entrar>>;
    await act(async () => {
      r = await ctx.entrar("a@exemplo.com", "x");
    });
    expect(r).toEqual({ ok: false, falha: { motivo: "nao_autorizado" } });
    expect(ctx?.estado.tipo).toBe("sem_acesso");
    expect(mockMem.has("t")).toBe(false);
  });

  it("sair apaga tudo no aparelho na hora, avisa a API sem esperar e, se a rede falhar, sai mesmo assim", async () => {
    mockMem.set("t", "tk");
    mockMem.set("d", "/treino/1");
    const f = servidor({
      "GET /sessao": () => resposta(200, QUEM_ATLETA),
      "DELETE /sessao": () => {
        throw new Error("sem rede");
      },
    });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("dentro"));
    await act(async () => ctx.sair());
    expect(ctx?.estado).toEqual({ tipo: "sem_acesso", expirou: false, lembrar: false });
    expect(mockMem.size).toBe(0);
    const chamada = f.mock.calls.find((c) => c[1]?.method === "DELETE");
    expect(String(chamada?.[0])).toBe(`${API}/sessao`);
    expect((chamada?.[1]?.headers as Record<string, string>).Authorization).toBe("Bearer tk");
  });

  it("trocar a senha guarda o acesso novo (o antigo foi revogado) e zera a marca de troca obrigatória", async () => {
    mockMem.set("t", "provisorio");
    const f = servidor({
      "GET /sessao": () => resposta(200, { ...QUEM_ATLETA, troca_de_senha_obrigatoria: true }),
      "PUT /conta/senha": () => resposta(200, { token: "token-depois", expira_em: "x" }),
    });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado).toMatchObject({ tipo: "dentro", trocaObrigatoria: true }));
    await act(async () => {
      await ctx.trocarSenha("provisoria", "senha-nova-sintetica");
    });
    expect(mockMem.get("t")).toBe("token-depois");
    expect(ctx?.estado).toMatchObject({ tipo: "dentro", trocaObrigatoria: false });
  });

  it("trocar a senha com a atual errada (422) não mexe no acesso", async () => {
    mockMem.set("t", "tk");
    const f = servidor({
      "GET /sessao": () => resposta(200, QUEM_ATLETA),
      "PUT /conta/senha": () => resposta(422, { detail: [{ type: "senha_atual_incorreta" }] }),
    });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("dentro"));
    let r!: Awaited<ReturnType<typeof ctx.trocarSenha>>;
    await act(async () => {
      r = await ctx.trocarSenha("errada", "senha-nova-sintetica");
    });
    expect(r).toEqual({ ok: false, falha: { motivo: "invalido", tipo: "senha_atual_incorreta" } });
    expect(mockMem.get("t")).toBe("tk");
    expect(ctx?.estado.tipo).toBe("dentro");
  });
});

describe("SessaoProvider: o fetch das telas", () => {
  const dentro = async (extra: Record<string, Rota>) => {
    mockMem.set("t", "tk");
    const f = servidor({ "GET /sessao": () => resposta(200, QUEM_ATLETA), ...extra });
    await abrir(f);
    await waitFor(() => expect(ctx?.estado.tipo).toBe("dentro"));
    return f;
  };

  it("manda o Bearer para a API e preserva o que a tela já mandou", async () => {
    const f = await dentro({ "GET /atletas/3/carga": () => resposta(200, {}) });
    await ctx.fetch(`${API}/atletas/3/carga`, { headers: { Accept: "application/json" } });
    const h = new Headers(f.mock.calls.at(-1)?.[1]?.headers);
    expect(h.get("authorization")).toBe("Bearer tk");
    expect(h.get("accept")).toBe("application/json");
  });

  it("nunca manda o token para outro endereço", async () => {
    const f = await dentro({});
    f.mockImplementationOnce(async () => resposta(200, {}));
    await ctx.fetch("http://outro.site/x", { headers: { Accept: "x" } });
    const h = new Headers(f.mock.calls.at(-1)?.[1]?.headers);
    expect(h.get("authorization")).toBeNull();
  });

  it("um 401 depois de entrar limpa o acesso, guarda o endereço da tela e mostra 'expirou'", async () => {
    await dentro({ "GET /atletas/3/carga": () => resposta(401, { detail: "não autenticado" }) });
    await act(async () => ctx.registrarCaminho("/treino/107"));
    await act(async () => {
      await ctx.fetch(`${API}/atletas/3/carga`);
    });
    expect(ctx?.estado).toEqual({ tipo: "sem_acesso", expirou: true, lembrar: false });
    expect(mockMem.has("t")).toBe(false);
    expect(mockMem.get("d")).toBe("/treino/107");
    expect(await ctx.consumirDestino()).toBe("/treino/107");
    expect(mockMem.has("d")).toBe(false);
  });

  it("403 troca_de_senha_obrigatoria liga a marca para a guarda abrir a tela de troca", async () => {
    await dentro({
      "GET /atletas/3/carga": () => resposta(403, { detail: [{ loc: [], msg: "m", type: "troca_de_senha_obrigatoria" }] }),
    });
    await act(async () => {
      await ctx.fetch(`${API}/atletas/3/carga`);
    });
    expect(ctx?.estado).toMatchObject({ tipo: "dentro", trocaObrigatoria: true });
  });

  it("404 e 5xx passam direto para a tela (não derrubam o acesso)", async () => {
    await dentro({ "GET /atletas/3/carga": () => resposta(404, { detail: "x" }) });
    const r = await ctx.fetch(`${API}/atletas/3/carga`);
    expect(r.status).toBe(404);
    expect(ctx?.estado.tipo).toBe("dentro");
  });

  it("o endereço lembrado de fora do app é ignorado", async () => {
    await dentro({});
    await act(async () => ctx.lembrarDestino("https://outro.site/x"));
    expect(await ctx.consumirDestino()).toBeNull();
  });
});
