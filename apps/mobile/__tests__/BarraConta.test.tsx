import { fireEvent, render, screen } from "@testing-library/react-native";

import { BarraConta } from "../src/componentes/BarraConta";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

describe("menu Conta e diálogo de sair", () => {
  it("o menu abre com 'Trocar senha' e 'Sair' e fecha ao escolher", async () => {
    const aoTrocarSenha = jest.fn();
    await render(<BarraConta aoTrocarSenha={aoTrocarSenha} aoSair={jest.fn()} />);
    expect(screen.queryByTestId("menu-conta")).toBeNull();
    await fireEvent.press(screen.getByTestId("abrir-conta"));
    expect(screen.getByTestId("abrir-conta").props.accessibilityState.expanded).toBe(true);
    expect(screen.getByText("Trocar senha")).toBeTruthy();
    expect(screen.getByText("Sair")).toBeTruthy();
    expect(screen.queryByText("Consentimento")).toBeNull(); // entra com a #503
    await fireEvent.press(screen.getByTestId("trocar-senha"));
    expect(aoTrocarSenha).toHaveBeenCalled();
    expect(screen.queryByTestId("menu-conta")).toBeNull();
  });

  it("o menu fecha ao tocar fora e com Esc", async () => {
    await render(<BarraConta aoTrocarSenha={jest.fn()} aoSair={jest.fn()} />);
    await fireEvent.press(screen.getByTestId("abrir-conta"));
    await fireEvent.press(screen.getByTestId("fundo-menu-conta", { includeHiddenElements: true }));
    expect(screen.queryByTestId("menu-conta")).toBeNull();
    await fireEvent.press(screen.getByTestId("abrir-conta"));
    expect(screen.getByTestId("menu-conta")).toBeTruthy();
    // Esc na web e o botão voltar no Android chamam `onRequestClose` do Modal.
    await fireEvent(screen.getByTestId("menu-conta"), "requestClose");
    expect(screen.queryByTestId("menu-conta")).toBeNull();
  });

  it("Sair pergunta antes; 'Cancelar' não sai", async () => {
    const aoSair = jest.fn();
    await render(<BarraConta aoTrocarSenha={jest.fn()} aoSair={aoSair} />);
    await fireEvent.press(screen.getByTestId("abrir-conta"));
    await fireEvent.press(screen.getByTestId("sair"));
    expect(screen.getByText("Sair do app?")).toBeTruthy();
    expect(screen.getByText("Você vai precisar entrar de novo com o e-mail e a senha.")).toBeTruthy();
    expect(aoSair).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByTestId("cancelar-sair"));
    expect(aoSair).not.toHaveBeenCalled();
    expect(screen.queryByText("Sair do app?")).toBeNull();
  });

  it("confirmar sai", async () => {
    const aoSair = jest.fn();
    await render(<BarraConta aoTrocarSenha={jest.fn()} aoSair={aoSair} />);
    await fireEvent.press(screen.getByTestId("abrir-conta"));
    await fireEvent.press(screen.getByTestId("sair"));
    await fireEvent.press(screen.getByTestId("confirmar-sair"));
    expect(aoSair).toHaveBeenCalledTimes(1);
    expect(screen.queryByText("Sair do app?")).toBeNull();
  });
});
