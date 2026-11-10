import { fireEvent, render, screen } from "@testing-library/react-native";

import { semanaVazia } from "../__fixtures__/semanaPadrao";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  router: { canGoBack: jest.fn(() => false), back: jest.fn(), replace: jest.fn(), push: jest.fn() },
}));
import { router as mockRouter } from "expo-router";

import Inicio from "../src/app/index";
import SemanaPadrao from "../src/app/semana-padrao";

const resposta = (corpo: unknown) => ({ ok: true, status: 200, json: async () => corpo }) as Response;

describe("rota /semana-padrao e a entrada pela evolução", () => {
  const original = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = original;
    jest.clearAllMocks();
  });

  it("a rota busca a semana-padrão do atleta configurado", async () => {
    const f = jest.fn(async (..._args: unknown[]) => resposta(semanaVazia));
    globalThis.fetch = f as unknown as typeof fetch;
    await render(<SemanaPadrao />);
    await screen.findByTestId("estado-vazio");
    expect(String(f.mock.calls[0][0])).toMatch(/\/atletas\/1\/semana-padrao$/);
  });

  it("'Voltar' sem histórico leva à evolução", async () => {
    globalThis.fetch = jest.fn(async () => resposta(semanaVazia)) as unknown as typeof fetch;
    await render(<SemanaPadrao />);
    await screen.findByTestId("estado-vazio");
    await fireEvent.press(screen.getByLabelText("Voltar"));
    expect(mockRouter.replace).toHaveBeenCalledWith("/");
  });

  it("a evolução tem o botão 'Semana-padrão', que abre /semana-padrao", async () => {
    globalThis.fetch = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(<Inicio />);
    await fireEvent.press(screen.getByTestId("abrir-semana-padrao"));
    expect(mockRouter.push).toHaveBeenCalledWith("/semana-padrao");
  });
});
