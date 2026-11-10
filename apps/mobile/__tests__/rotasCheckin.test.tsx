import { fireEvent, render, screen } from "@testing-library/react-native";

import { atividadesCheckin, pendentes } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const mockParams: { id: string; origem?: string } = { id: "101" };
const mockRouter = { canGoBack: jest.fn(() => true), back: jest.fn(), replace: jest.fn(), push: jest.fn() };
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  useLocalSearchParams: () => mockParams,
  get router() {
    return mockRouter;
  },
}));

import Checkin from "../src/app/checkin/[id]";
import Pendentes from "../src/app/checkins-pendentes";
import Treino from "../src/app/treino/[id]";

jest.setTimeout(20000);

const resposta = (corpo: unknown) => ({ ok: true, status: 200, json: async () => corpo }) as Response;
let original: typeof fetch;
beforeEach(() => {
  original = globalThis.fetch;
  Object.values(mockRouter).forEach((f) => f.mockClear());
  mockRouter.canGoBack.mockReturnValue(true);
  mockParams.origem = undefined;
});
afterEach(() => {
  globalThis.fetch = original;
});

describe("rotas do check-in", () => {
  it("/checkin/[id] busca a atividade do parâmetro e a rota leva só o id", async () => {
    const f = jest.fn(async (..._a: unknown[]) => resposta(atividadesCheckin.semCheckin));
    globalThis.fetch = f as unknown as typeof fetch;
    await render(<Checkin />);
    await screen.findByText("Qual foi o esforço do treino?");
    expect(String(f.mock.calls[0][0])).toMatch(/\/atletas\/1\/atividades\/101$/);
  });

  it("/checkin/[id]: Voltar usa router.back; sem histórico, vai para o treino", async () => {
    globalThis.fetch = jest.fn(async () => resposta(atividadesCheckin.semCheckin)) as unknown as typeof fetch;
    await render(<Checkin />);
    await fireEvent.press(await screen.findByLabelText("Voltar"));
    expect(mockRouter.back).toHaveBeenCalled();
    mockRouter.canGoBack.mockReturnValue(false);
    await fireEvent.press(screen.getByLabelText("Voltar"));
    expect(mockRouter.replace).toHaveBeenCalledWith("/treino/101");
  });

  it("/checkin/[id]?origem=pendentes: o botão de salvo vira 'Voltar aos pendentes'", async () => {
    mockParams.origem = "pendentes";
    globalThis.fetch = jest.fn(async (_u: unknown, init?: RequestInit) =>
      resposta(init?.method === "PUT" ? { ...atividadesCheckin.comCheckin.checkin } : atividadesCheckin.semCheckin),
    ) as unknown as typeof fetch;
    await render(<Checkin />);
    await fireEvent.press(await screen.findByTestId("pse-5"));
    await fireEvent.press(await screen.findByTestId("sensacao-4"));
    await fireEvent.press(await screen.findByTestId("nada-a-relatar"));
    await screen.findByText("Voltar aos pendentes");
  });

  it("/checkins-pendentes: abre /checkin/<id>?origem=pendentes", async () => {
    globalThis.fetch = jest.fn(async () => resposta(pendentes)) as unknown as typeof fetch;
    await render(<Pendentes />);
    await fireEvent.press(await screen.findByTestId("pendente-106"));
    expect(mockRouter.push).toHaveBeenCalledWith("/checkin/106?origem=pendentes");
  });

  it("/treino/[id]: 'Fazer check-in' abre /checkin/<id>", async () => {
    globalThis.fetch = jest.fn(async () => resposta(atividadesCheckin.semCheckin)) as unknown as typeof fetch;
    await render(<Treino />);
    await fireEvent.press(await screen.findByText("Fazer check-in"));
    expect(mockRouter.push).toHaveBeenCalledWith("/checkin/101");
  });

  it("/treino/[id]: 'Editar' abre /checkin/<id>", async () => {
    globalThis.fetch = jest.fn(async () => resposta(atividadesCheckin.comCheckin)) as unknown as typeof fetch;
    await render(<Treino />);
    await fireEvent.press(await screen.findByText("Editar"));
    expect(mockRouter.push).toHaveBeenCalledWith("/checkin/101");
  });
});
