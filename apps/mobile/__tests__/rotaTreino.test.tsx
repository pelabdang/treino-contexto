import { render, screen } from "@testing-library/react-native";

import { atividades } from "../__fixtures__/atividades";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

jest.mock("expo-router", () => ({
  useLocalSearchParams: () => ({ id: "101" }),
  router: { canGoBack: () => false, back: jest.fn(), replace: jest.fn() },
}));

import Treino from "../src/app/treino/[id]";

describe("rota /treino/[id]", () => {
  it("busca a atividade do parâmetro da rota", async () => {
    const f = jest.fn(async (..._args: unknown[]) => ({ ok: true, status: 200, json: async () => atividades.ok }) as Response);
    const original = globalThis.fetch;
    globalThis.fetch = f as unknown as typeof fetch;
    await render(<Treino />);
    await screen.findByTestId("cartao-resumo");
    expect(String(f.mock.calls[0][0])).toMatch(/\/atletas\/1\/atividades\/101$/);
    globalThis.fetch = original;
  });
});
