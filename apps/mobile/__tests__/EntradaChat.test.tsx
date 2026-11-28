import { fireEvent, render, screen } from "@testing-library/react-native";

import { EntradaChat } from "../src/componentes/EntradaChat";
import { TelaInicio } from "../src/componentes/TelaInicio";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

describe("entrada do chat no Início (#600)", () => {
  it("é um botão com o nome do chat e abre a tela", async () => {
    const abrir = jest.fn();
    await render(<EntradaChat aoAbrir={abrir} />);
    expect(screen.getByText("Pergunte ao seu treino")).toBeTruthy();
    await fireEvent.press(screen.getByRole("button", { name: /Pergunte ao seu treino/ }));
    expect(abrir).toHaveBeenCalled();
  });

  it("no Início aparece só quando a tela recebe aoAbrirChat", async () => {
    const f = jest.fn(async () => ({ ok: false, status: 500, json: async () => ({}) }) as Response) as unknown as typeof fetch;
    const base = { apiUrl: "http://api.teste", atletaId: 1, fetchFn: f, aoAbrirTreino: jest.fn(), aoResponderCheckin: jest.fn(), aoVerTodos: jest.fn() };
    const { unmount } = await render(<TelaInicio {...base} />);
    expect(screen.queryByTestId("entrada-chat")).toBeNull();
    await unmount();
    const abrir = jest.fn();
    await render(<TelaInicio {...base} aoAbrirChat={abrir} />);
    await fireEvent.press(screen.getByTestId("entrada-chat"));
    expect(abrir).toHaveBeenCalled();
  });
});
