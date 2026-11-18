import { AccessibilityInfo } from "react-native";
import { act, fireEvent, render, screen } from "@testing-library/react-native";

import { TelaEntrar, tempoEmPalavras } from "../src/componentes/TelaEntrar";
import type { Entrou, ResultadoSessao } from "../src/sessao/api";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const ENTROU = { token: "t", papel: "atleta", atleta_id: 1, professor_id: null, nome: "Atleta Fixture 1", expira_em: "x", troca_de_senha_obrigatoria: false } as Entrou;
const ok: ResultadoSessao<Entrou> = { ok: true, dados: ENTROU };
const falha = (f: object) => ({ ok: false, falha: f }) as ResultadoSessao<Entrou>;

const digitar = async (email: string, senha: string) => {
  await fireEvent.changeText(screen.getByTestId("campo-email"), email);
  await fireEvent.changeText(screen.getByTestId("campo-senha"), senha);
};

describe("tela de entrar", () => {
  it("abre com rótulos visíveis, sem jargão, e o botão desligado enquanto algum campo está vazio", async () => {
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    expect(screen.getByRole("header", { name: "Entrar" })).toBeTruthy();
    expect(screen.getByText("Use o e-mail e a senha do seu cadastro.")).toBeTruthy();
    expect(screen.getByText("E-mail")).toBeTruthy();
    expect(screen.getByText("Senha")).toBeTruthy();
    expect(screen.getByText(/Esqueceu a senha\? Fale com quem convidou você para o piloto/)).toBeTruthy();
    expect(screen.queryByText(/lembrar de mim|criar conta|token|sessão|autenticação/i)).toBeNull();
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(true);
    await fireEvent.changeText(screen.getByTestId("campo-email"), "atleta1@exemplo.com");
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(true);
    await fireEvent.changeText(screen.getByTestId("campo-senha"), "senha");
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(false);
  });

  it("os campos pedem o teclado, o preenchimento e o gerenciador de senhas certos", async () => {
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    const email = screen.getByTestId("campo-email");
    expect(email.props).toMatchObject({ keyboardType: "email-address", autoCapitalize: "none", autoCorrect: false, autoComplete: "email", returnKeyType: "next" });
    const senha = screen.getByTestId("campo-senha");
    expect(senha.props).toMatchObject({ secureTextEntry: true, autoComplete: "current-password", returnKeyType: "done" });
  });

  it("Ver mostra a senha e Esconder volta a esconder", async () => {
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    const ver = screen.getByTestId("campo-senha-ver");
    expect(ver.props.accessibilityLabel).toBe("Ver a senha");
    await fireEvent.press(ver);
    expect(screen.getByTestId("campo-senha").props.secureTextEntry).toBe(false);
    expect(screen.getByTestId("campo-senha-ver").props.accessibilityLabel).toBe("Esconder a senha");
    await fireEvent.press(screen.getByTestId("campo-senha-ver"));
    expect(screen.getByTestId("campo-senha").props.secureTextEntry).toBe(true);
  });

  it("envia o e-mail e a senha, mostra 'Entrando...' com os campos desligados e avisa quando entra", async () => {
    let soltar!: (r: ResultadoSessao<Entrou>) => void;
    const aoEntrar = jest.fn(() => new Promise<ResultadoSessao<Entrou>>((res) => (soltar = res)));
    const aoConcluir = jest.fn();
    await render(<TelaEntrar aoEntrar={aoEntrar} aoConcluir={aoConcluir} />);
    await digitar("atleta1@exemplo.com", "senha-sintetica");
    // Não espera o fim do toque: a chamada fica pendurada de propósito (estado "entrando").
    void fireEvent.press(screen.getByTestId("botao-entrar"));
    expect(await screen.findByText("Entrando...")).toBeTruthy();
    expect(aoEntrar).toHaveBeenCalledWith("atleta1@exemplo.com", "senha-sintetica");
    expect(screen.getByTestId("campo-email").props.editable).toBe(false);
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(true);
    await act(async () => soltar(ok));
    expect(aoConcluir).toHaveBeenCalledWith(ENTROU);
  });

  it("Enter na senha envia", async () => {
    const aoEntrar = jest.fn(async () => ok);
    await render(<TelaEntrar aoEntrar={aoEntrar} />);
    await digitar("a@exemplo.com", "senha");
    await fireEvent(screen.getByTestId("campo-senha"), "submitEditing");
    expect(aoEntrar).toHaveBeenCalledTimes(1);
  });

  it("401: a mesma frase de erro, a senha é apagada e o e-mail fica", async () => {
    const aoEntrar = jest.fn(async () => falha({ motivo: "nao_autorizado" }));
    await render(<TelaEntrar aoEntrar={aoEntrar} />);
    await digitar("alguem@exemplo.com", "errada");
    await fireEvent.press(screen.getByTestId("botao-entrar"));
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getByText("E-mail ou senha incorretos. Confira e tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("campo-senha").props.value).toBe("");
    expect(screen.getByTestId("campo-email").props.value).toBe("alguem@exemplo.com");
    expect(screen.queryByText(/não está cadastrado|senha errada/i)).toBeNull();
  });

  it("429: faixa neutra com o tempo da API e o botão desligado até passar", async () => {
    jest.useFakeTimers();
    let agora = 1_000_000;
    const aoEntrar = jest.fn(async () => falha({ motivo: "espere", espereS: 300 }));
    await render(<TelaEntrar aoEntrar={aoEntrar} agora={() => agora} />);
    await digitar("a@exemplo.com", "senha");
    await fireEvent.press(screen.getByTestId("botao-entrar"));
    expect(screen.getByText("Muitas tentativas. Espere 5 minutos e tente de novo.")).toBeTruthy();
    await digitar("a@exemplo.com", "outra");
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(true);
    agora += 301_000;
    await act(async () => {
      jest.advanceTimersByTime(1000);
    });
    expect(screen.queryByTestId("faixa-espere")).toBeNull();
    expect(screen.getByTestId("botao-entrar").props.accessibilityState.disabled).toBe(false);
    jest.useRealTimers();
  });

  it("sem rede e erro do servidor têm frases próprias", async () => {
    const aoEntrar = jest.fn().mockResolvedValueOnce(falha({ motivo: "rede" })).mockResolvedValueOnce(falha({ motivo: "servidor", status: 500 }));
    await render(<TelaEntrar aoEntrar={aoEntrar} />);
    await digitar("a@exemplo.com", "senha");
    await fireEvent.press(screen.getByTestId("botao-entrar"));
    expect(screen.getByText("Não foi possível falar com o servidor. Confira a conexão e tente de novo.")).toBeTruthy();
    expect(screen.getByTestId("campo-senha").props.value).toBe("senha"); // sem rede não é erro da pessoa: nada se apaga
    await digitar("a@exemplo.com", "senha");
    await fireEvent.press(screen.getByTestId("botao-entrar"));
    expect(screen.getByText("Algo deu errado do nosso lado. Tente de novo mais tarde.")).toBeTruthy();
  });

  it("veio de acesso expirado: faixa neutra no alto", async () => {
    await render(<TelaEntrar expirou aoEntrar={jest.fn()} />);
    expect(screen.getByText("Seu acesso expirou. Entre de novo.")).toBeTruthy();
  });

  it("o nome do botão da senha contém o texto visível (WCAG 2.5.3)", async () => {
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    expect(screen.getByText("Ver")).toBeTruthy();
    expect(screen.getByTestId("campo-senha-ver").props.accessibilityLabel).toContain("Ver");
    await fireEvent.press(screen.getByTestId("campo-senha-ver"));
    expect(screen.getByText("Esconder")).toBeTruthy();
    expect(screen.getByTestId("campo-senha-ver").props.accessibilityLabel).toContain("Esconder");
  });

  it("saiu de propósito: anuncia 'Você saiu.' uma vez; abertura normal não anuncia", async () => {
    const anunciar = jest.spyOn(AccessibilityInfo, "announceForAccessibility").mockImplementation(() => undefined);
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    expect(anunciar).not.toHaveBeenCalled();
    await render(<TelaEntrar saiu aoEntrar={jest.fn()} />);
    expect(anunciar).toHaveBeenCalledTimes(1);
    expect(anunciar).toHaveBeenCalledWith("Você saiu.");
    anunciar.mockRestore();
  });

  it("saiu de propósito: a tela abre limpa, sem faixa", async () => {
    await render(<TelaEntrar aoEntrar={jest.fn()} />);
    expect(screen.queryByText("Seu acesso expirou. Entre de novo.")).toBeNull();
    expect(screen.queryByTestId("faixa-erro")).toBeNull();
  });

  it("nada digitado vai para log", async () => {
    const espiao = jest.spyOn(console, "log").mockImplementation(() => undefined);
    const erro = jest.spyOn(console, "error").mockImplementation(() => undefined);
    await render(<TelaEntrar aoEntrar={jest.fn(async () => falha({ motivo: "nao_autorizado" }))} />);
    await digitar("segredo@exemplo.com", "SENHA-MARCADOR");
    await fireEvent.press(screen.getByTestId("botao-entrar"));
    for (const c of [...espiao.mock.calls, ...erro.mock.calls]) expect(JSON.stringify(c)).not.toMatch(/SENHA-MARCADOR|segredo@/);
    espiao.mockRestore();
    erro.mockRestore();
  });
});

describe("tempoEmPalavras", () => {
  it("fala em segundos ou minutos", () => {
    expect(tempoEmPalavras(1)).toBe("1 segundo");
    expect(tempoEmPalavras(40)).toBe("40 segundos");
    expect(tempoEmPalavras(60)).toBe("1 minuto");
    expect(tempoEmPalavras(61)).toBe("2 minutos");
    expect(tempoEmPalavras(300)).toBe("5 minutos");
  });
});
