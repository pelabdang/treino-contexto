import { render, screen } from "@testing-library/react-native";

import RootLayout from "../src/app/_layout";
import * as fontes from "../src/tema/fontes";

jest.mock("../src/tema/fontes", () => ({ useFontesInter: jest.fn() }));
jest.mock("expo-router", () => ({ Stack: () => null }));
jest.mock("expo-status-bar", () => ({ StatusBar: () => null }));

describe("_layout", () => {
  it("enquanto a fonte carrega, mostra o fundo do tema em vez de tela vazia", async () => {
    (fontes.useFontesInter as jest.Mock).mockReturnValue(false);
    await render(<RootLayout />);
    const fundo = screen.getByTestId("carregando-fonte");
    expect(fundo.props.style).toMatchObject({ flex: 1, backgroundColor: "#F6F5F1" });
  });

  it("com a fonte pronta, não mostra o fundo de espera", async () => {
    (fontes.useFontesInter as jest.Mock).mockReturnValue(true);
    await render(<RootLayout />);
    expect(screen.queryByTestId("carregando-fonte")).toBeNull();
  });
});
