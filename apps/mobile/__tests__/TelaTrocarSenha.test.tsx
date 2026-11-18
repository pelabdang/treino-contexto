import { act, fireEvent, render, screen } from "@testing-library/react-native";

import { TelaTrocarSenha } from "../src/componentes/TelaTrocarSenha";
import type { NovoAcesso, ResultadoSessao } from "../src/sessao/api";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const ok: ResultadoSessao<NovoAcesso> = { ok: true, dados: { token: "novo", expira_em: "x" } };
const falha = (f: object) => ({ ok: false, falha: f }) as ResultadoSessao<NovoAcesso>;

const digitar = async (atual: string, nova: string, repetida: string) => {
  await fireEvent.changeText(screen.getByTestId("campo-senha-atual"), atual);
  await fireEvent.changeText(screen.getByTestId("campo-senha-nova"), nova);
  await fireEvent.changeText(screen.getByTestId("campo-senha-repetida"), repetida);
};
const salvar = () => fireEvent.press(screen.getByTestId("botao-salvar"));

describe("tela de trocar a senha", () => {
  it("mostra os três campos, a dica fixa e o botão desligado até todos terem texto", async () => {
    await render(<TelaTrocarSenha aoTrocar={jest.fn()} aoConcluir={jest.fn()} aoVoltar={jest.fn()} />);
    expect(screen.getByRole("header", { name: "Trocar a senha" })).toBeTruthy();
    expect(screen.getByText("Senha de agora")).toBeTruthy();
    expect(screen.getByText("Senha nova")).toBeTruthy();
    expect(screen.getByText("Repita a senha nova")).toBeTruthy();
    expect(screen.getByText("Pelo menos 10 caracteres.")).toBeTruthy();
    expect(screen.getByTestId("campo-senha-nova").props.autoComplete).toBe("new-password");
    expect(screen.getByTestId("campo-senha-repetida").props.autoComplete).toBe("new-password");
    expect(screen.getByTestId("botao-salvar").props.accessibilityState.disabled).toBe(true);
    await digitar("a", "b", "");
    expect(screen.getByTestId("botao-salvar").props.accessibilityState.disabled).toBe(true);
    await digitar("a", "b", "b");
    expect(screen.getByTestId("botao-salvar").props.accessibilityState.disabled).toBe(false);
  });

  it("primeiro acesso não tem 'Voltar'; a troca voluntária tem", async () => {
    await render(<TelaTrocarSenha primeiroAcesso aoTrocar={jest.fn()} aoConcluir={jest.fn()} aoVoltar={jest.fn()} />);
    expect(screen.queryByTestId("voltar")).toBeNull();
    await render(<TelaTrocarSenha aoTrocar={jest.fn()} aoConcluir={jest.fn()} aoVoltar={jest.fn()} />);
    expect(screen.getByTestId("voltar")).toBeTruthy();
  });

  it("primeiro acesso tem 'Sair' (a pessoa não fica presa); a troca voluntária não", async () => {
    const aoSair = jest.fn();
    await render(<TelaTrocarSenha primeiroAcesso aoTrocar={jest.fn()} aoConcluir={jest.fn()} aoSair={aoSair} />);
    await fireEvent.press(screen.getByTestId("sair"));
    expect(aoSair).not.toHaveBeenCalled(); // o mesmo diálogo do menu Conta: pergunta antes
    expect(screen.getByText("Sair do app?")).toBeTruthy();
    await fireEvent.press(screen.getByTestId("confirmar-sair"));
    expect(aoSair).toHaveBeenCalledTimes(1);
    await render(<TelaTrocarSenha aoTrocar={jest.fn()} aoConcluir={jest.fn()} aoVoltar={jest.fn()} aoSair={aoSair} />);
    expect(screen.queryByTestId("sair")).toBeNull();
  });

  it("as duas senhas novas diferentes são barradas no app, sem chamar a API", async () => {
    const aoTrocar = jest.fn();
    await render(<TelaTrocarSenha aoTrocar={aoTrocar} aoConcluir={jest.fn()} />);
    await digitar("atual-sintetica", "senha-nova-um", "senha-nova-dois");
    await salvar();
    expect(aoTrocar).not.toHaveBeenCalled();
    expect(screen.getByText("As duas senhas novas não são iguais.")).toBeTruthy();
    expect(screen.getByRole("alert")).toBeTruthy();
  });

  it("422 senha_atual_incorreta e senha_nova_invalida têm frases diferentes", async () => {
    const aoTrocar = jest
      .fn()
      .mockResolvedValueOnce(falha({ motivo: "invalido", tipo: "senha_atual_incorreta" }))
      .mockResolvedValueOnce(falha({ motivo: "invalido", tipo: "senha_nova_invalida" }));
    await render(<TelaTrocarSenha aoTrocar={aoTrocar} aoConcluir={jest.fn()} />);
    await digitar("errada", "senha-nova-longa", "senha-nova-longa");
    await salvar();
    expect(screen.getByText("A senha de agora não confere.")).toBeTruthy();
    await salvar();
    expect(screen.getByText("A senha nova precisa de pelo menos 10 caracteres e ser diferente da de agora.")).toBeTruthy();
    expect(screen.queryByText("A senha de agora não confere.")).toBeNull();
  });

  it("sem rede: pede para tentar de novo e mantém o que foi digitado", async () => {
    await render(<TelaTrocarSenha aoTrocar={jest.fn(async () => falha({ motivo: "rede" }))} aoConcluir={jest.fn()} />);
    await digitar("atual-sintetica", "senha-nova-longa", "senha-nova-longa");
    await salvar();
    expect(screen.getByText("Não foi possível salvar. Tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("campo-senha-nova").props.value).toBe("senha-nova-longa");
  });

  it("salvando: botão 'Salvando...' e campos desligados", async () => {
    let soltar!: (r: ResultadoSessao<NovoAcesso>) => void;
    await render(<TelaTrocarSenha aoTrocar={() => new Promise((res) => (soltar = res))} aoConcluir={jest.fn()} />);
    await digitar("a", "senha-nova-longa", "senha-nova-longa");
    void fireEvent.press(screen.getByTestId("botao-salvar")); // fica pendurado de propósito
    expect(await screen.findByText("Salvando...")).toBeTruthy();
    expect(screen.getByTestId("campo-senha-atual").props.editable).toBe(false);
    await act(async () => soltar(ok));
  });

  it("salvo: apaga os campos, diz 'Senha trocada.' e 'Continuar' conclui", async () => {
    const aoConcluir = jest.fn();
    const aoTrocar = jest.fn(async () => ok);
    await render(<TelaTrocarSenha primeiroAcesso aoTrocar={aoTrocar} aoConcluir={aoConcluir} />);
    await digitar("atual-sintetica", "senha-nova-longa", "senha-nova-longa");
    await salvar();
    expect(aoTrocar).toHaveBeenCalledWith("atual-sintetica", "senha-nova-longa");
    expect(screen.getByText("Senha trocada.")).toBeTruthy();
    expect(screen.getByText("[check-circle-outline]", { includeHiddenElements: true })).toBeTruthy(); // ícone do guia
    expect(screen.getByTestId("senha-trocada").props.accessibilityLiveRegion).toBe("polite");
    expect(screen.queryByTestId("campo-senha-nova")).toBeNull();
    await fireEvent.press(screen.getByTestId("continuar"));
    expect(aoConcluir).toHaveBeenCalled();
  });
});
