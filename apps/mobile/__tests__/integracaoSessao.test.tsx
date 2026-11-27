// Sessão de verdade (provider + armazenamento em memória) com as rotas do atleta e do professor: o id vem da sessão, o Bearer vai em
// toda chamada de dado e um 401 leva o app ao estado "acesso expirado".
import { render, screen, waitFor } from "@testing-library/react-native";
import { type ReactNode } from "react";

import { fetchEvolucao } from "../__fixtures__/evolucao";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  router: { push: jest.fn(), replace: jest.fn(), canGoBack: () => false, back: jest.fn() },
}));

const mockMem = new Map<string, string>();
jest.mock("../src/sessao/armazenamento", () => ({
  lerUltimaSerie: async () => null,
  gravarUltimaSerie: async () => undefined,
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

import CaixaDoDia from "../src/app/(app)/(abas)/caixa-do-dia";
import Inicio from "../src/app/(app)/(abas)/evolucao"; // a evolução dos tiros mora na aba Evolução (o início é a TelaInicio)
import { SessaoProvider, useSessao } from "../src/sessao/SessaoProvider";

const API = "http://api.teste";
const resposta = (status: number, corpo: unknown): Response => ({ ok: status < 300, status, json: async () => corpo, clone: () => resposta(status, corpo) }) as Response;
const quem = (extra: object) => ({ nome: "Fixture", expira_em: "x", troca_de_senha_obrigatoria: false, ...extra });

let estadoAtual = "";
function Estado() {
  estadoAtual = useSessao().estado.tipo;
  return null;
}
const app = (filho: ReactNode, f: typeof fetch) => (
  <SessaoProvider apiUrl={API} fetchBase={f}>
    <Estado />
    {filho}
  </SessaoProvider>
);

beforeEach(() => mockMem.clear());

describe("rotas com sessão", () => {
  it("o atleta da sessão (3) vem da conta, não de variável de ambiente, e a chamada leva o Bearer", async () => {
    mockMem.set("t", "token-sintetico-3");
    const evolucao = fetchEvolucao();
    const f = jest.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/sessao")
        ? resposta(200, quem({ papel: "atleta", atleta_id: 3, professor_id: null }))
        : evolucao(input),
    ) as unknown as typeof fetch & jest.Mock;
    await render(app(<Inicio />, f));
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]) === `${API}/atletas/3/evolucao/series`)).toBe(true));
    const chamada = f.mock.calls.find((c) => String(c[0]) === `${API}/atletas/3/evolucao/series`);
    expect(new Headers(chamada?.[1]?.headers).get("authorization")).toBe("Bearer token-sintetico-3");
    expect(screen.queryByTestId("abrir-conta")).toBeNull(); // o menu Conta do topo saiu: a Conta é uma aba
  });

  it("o professor da sessão (9) abre a caixa dele", async () => {
    mockMem.set("t", "tk");
    const f = jest.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/sessao")
        ? resposta(200, quem({ papel: "professor", atleta_id: null, professor_id: 9 }))
        : resposta(200, { versao: "atencao@2", hoje: "2025-11-13", janela_atencao_dias: 7, janela_novos_dias: 14, alunos: [], novos: [] }),
    ) as unknown as typeof fetch & jest.Mock;
    await render(app(<CaixaDoDia />, f));
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]) === `${API}/professores/9/caixa-do-dia`)).toBe(true));
  });

  it("um 401 numa tela de dado leva o app ao acesso expirado e apaga o token", async () => {
    mockMem.set("t", "tk");
    const f = jest.fn(async (input: RequestInfo | URL) =>
      String(input).endsWith("/sessao") ? resposta(200, quem({ papel: "atleta", atleta_id: 3, professor_id: null })) : resposta(401, { detail: "não autenticado" }),
    ) as unknown as typeof fetch;
    await render(app(<Inicio />, f));
    await waitFor(() => expect(estadoAtual).toBe("sem_acesso"));
    expect(mockMem.has("t")).toBe(false);
  });
});
