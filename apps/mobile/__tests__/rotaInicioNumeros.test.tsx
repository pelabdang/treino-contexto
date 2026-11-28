import { fireEvent, render, screen } from "@testing-library/react-native";

import { cartoes } from "../__fixtures__/cartoes";
import { fetchEvolucao } from "../__fixtures__/evolucao";
import { ComSessao } from "../__fixtures__/sessaoFalsa";
import Evolucao from "../src/app/(app)/(abas)/evolucao";
import Inicio from "../src/app/(app)/(abas)/index";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const mockRouter = { push: jest.fn(), navigate: jest.fn() };
let mockParams: Record<string, string> = {};
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  useLocalSearchParams: () => mockParams,
  router: {
    push: (...a: unknown[]) => mockRouter.push(...a),
    navigate: (...a: unknown[]) => mockRouter.navigate(...a),
  },
}));

const resposta = (corpo: unknown) => ({ ok: true, status: 200, json: async () => corpo }) as Response;
const original = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = original;
  mockParams = {};
  mockRouter.push.mockReset();
  mockRouter.navigate.mockReset();
});

describe("rota Início: destino dos cartões de 'Seus números'", () => {
  beforeEach(() => {
    globalThis.fetch = jest.fn(async (url: unknown) => {
      const u = String(url);
      if (u.includes("/inicio/cartoes")) return resposta(cartoes);
      if (u.includes("/checkins/pendentes")) return resposta({ dias: 7, pendentes: [], total: 0 });
      if (u.includes("/carga")) return resposta({ atleta_id: 1, aviso: null, dias: [], frase_forma: null, periodo: null, totais: {}, versao: "serie_carga@2", versao_carga: "carga@2" });
      if (u.includes("/atividades?")) return resposta({ atleta_id: 1, limite: 5, itens: [{ atividade_id: 1, inicio: "2025-03-18T09:30:00Z", data_local: "2025-03-18", hora_local: "06:30", modalidade: "corrida", subtipo: "rua", tipo_treino: "leve", duracao_s: 3125, duracao: "0:52:05", distancia_m: 10000, distancia: "10,00 km", destaque: null, checkin_estado: "feito", feedback_estado: "pronto", normal_estado: "dentro" }], proximo: null });
      return resposta({});
    }) as unknown as typeof fetch;
  });

  it("evolução com a série: navega para /evolucao?serie=<id>", async () => {
    await render(<ComSessao><Inicio /></ComSessao>);
    await fireEvent.press(await screen.findByTestId("cartao-em_movimento"));
    expect(mockRouter.navigate).toHaveBeenCalledWith({ pathname: "/evolucao", params: { serie: "corrida.pace.leve" } });
  });

  it("semana-padrão e treino: abrem a tela deles", async () => {
    await render(<ComSessao><Inicio /></ComSessao>);
    await fireEvent.press(await screen.findByTestId("bloco-hoje"));
    expect(mockRouter.push).toHaveBeenLastCalledWith("/semana-padrao");
    await fireEvent.press(screen.getByTestId("cartao-melhor_marca"));
    expect(mockRouter.push).toHaveBeenLastCalledWith("/treino/77");
  });
});

describe("rota Início: o chat", () => {
  beforeEach(() => {
    globalThis.fetch = jest.fn(async (url: unknown) => {
      const u = String(url);
      if (u.includes("/checkins/pendentes")) return resposta({ dias: 7, pendentes: [], total: 0 });
      if (u.includes("/carga")) return resposta({ atleta_id: 1, aviso: null, dias: [], frase_forma: null, periodo: null, totais: {}, versao: "serie_carga@2", versao_carga: "carga@2" });
      if (u.includes("/inicio/cartoes")) return resposta({ atleta_id: 1, data: "2025-03-21", cartoes: [] });
      return resposta({ atleta_id: 1, limite: 5, itens: [{ atividade_id: 1, inicio: "2025-03-18T09:30:00Z", data_local: "2025-03-18", hora_local: "06:30", modalidade: "corrida", subtipo: "rua", tipo_treino: "leve", duracao_s: 3125, duracao: "0:52:05", distancia_m: 10000, distancia: "10,00 km", destaque: null, checkin_estado: "feito", feedback_estado: "pronto", normal_estado: "dentro" }], proximo: null });
    }) as unknown as typeof fetch;
  });

  it("caixa e ↑ abrem /chat com o teclado; a pergunta pronta vai por índice, nunca pelo texto; 'Conversas ›' abre a lista", async () => {
    await render(<ComSessao><Inicio /></ComSessao>);
    await fireEvent.press(await screen.findByTestId("inicio-caixa"));
    expect(mockRouter.push).toHaveBeenLastCalledWith({ pathname: "/chat", params: { foco: "1" } });
    await fireEvent.press(screen.getByTestId("inicio-pronta-2"));
    expect(mockRouter.push).toHaveBeenLastCalledWith({ pathname: "/chat", params: { pronta: "2" } });
    await fireEvent.press(screen.getByTestId("inicio-conversas"));
    expect(mockRouter.push).toHaveBeenLastCalledWith("/chat/conversas");
  });
});

describe("rota Evolução: ?serie=<id> abre a série pedida", () => {
  it("vence a série padrão e busca a série pedida", async () => {
    mockParams = { serie: "corrida.volume_km" };
    const f = fetchEvolucao();
    globalThis.fetch = f;
    await render(<ComSessao><Evolucao /></ComSessao>);
    await screen.findByTestId("frase-evolucao");
    const urls = f.mock.calls.map((c) => String(c[0]));
    expect(urls).toContain("http://api.teste/atletas/1/evolucao/series/corrida.volume_km?periodo=12s");
    expect(urls.some((u) => u.includes("pace.leve"))).toBe(false);
  });

  it("série pedida que não existe no catálogo: cai na padrão", async () => {
    mockParams = { serie: "nao.existe" };
    const f = fetchEvolucao();
    globalThis.fetch = f;
    await render(<ComSessao><Evolucao /></ComSessao>);
    await screen.findByTestId("frase-evolucao");
    expect(f.mock.calls.map((c) => String(c[0]))).toContain("http://api.teste/atletas/1/evolucao/series/corrida.pace.leve?periodo=12s");
  });
});
