// Navegação por abas (auditoria de UX da Lia): barra na base, menu lateral, abas por papel, selo da Conta, tela Conta e Treinos.
import { fireEvent, render, screen } from "@testing-library/react-native";

import { ComSessao, criarSessaoFalsa, dentroAtleta, dentroProfessor } from "../__fixtures__/sessaoFalsa";
import { ABAS_ATLETA, ABAS_PROFESSOR, abasDoPapel, BarraDeAbas } from "../src/componentes/BarraDeAbas";
import { TelaConta } from "../src/componentes/TelaConta";
import { caminhoDoPapel } from "../src/sessao/destino";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
jest.mock("expo-document-picker", () => ({ getDocumentAsync: jest.fn() }));

describe("barra de abas", () => {
  it("o atleta tem Início, Treinos, Evolução e Conta; o professor, Caixa do dia e Conta", () => {
    expect(ABAS_ATLETA.map((a) => a.rotulo)).toEqual(["Início", "Treinos", "Evolução", "Conta"]);
    expect(ABAS_PROFESSOR.map((a) => a.rotulo)).toEqual(["Caixa do dia", "Conta"]);
    expect(abasDoPapel("atleta")).toBe(ABAS_ATLETA);
    expect(abasDoPapel("professor")).toBe(ABAS_PROFESSOR);
  });

  it("no celular é a barra da base; no computador, o menu lateral", async () => {
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="index" aoEscolher={jest.fn()} lateral={false} />);
    expect(screen.getByTestId("barra-de-abas")).toBeTruthy();
    expect(screen.queryByTestId("menu-lateral")).toBeNull();
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="index" aoEscolher={jest.fn()} lateral />);
    expect(screen.getByTestId("menu-lateral")).toBeTruthy();
  });

  it("marca a aba ativa (estado, não só cor) e escolhe a aba tocada", async () => {
    const aoEscolher = jest.fn();
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="evolucao" aoEscolher={aoEscolher} lateral={false} />);
    expect(screen.getByTestId("aba-evolucao").props.accessibilityState.selected).toBe(true);
    expect(screen.getByTestId("aba-index").props.accessibilityState.selected).toBe(false);
    await fireEvent.press(screen.getByTestId("aba-conta"));
    expect(aoEscolher).toHaveBeenCalledWith("conta");
  });

  it("selo na Conta: número visível e dito ao leitor de tela; sem pedido não há selo", async () => {
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="index" aoEscolher={jest.fn()} lateral={false} selos={{ conta: 2 }} />);
    expect(screen.getByTestId("selo-conta")).toBeTruthy();
    expect(screen.getByTestId("aba-conta").props.accessibilityLabel).toBe("Conta, 2 pedidos");
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="index" aoEscolher={jest.fn()} lateral={false} selos={{ conta: 1 }} />);
    expect(screen.getByTestId("aba-conta").props.accessibilityLabel).toBe("Conta, 1 pedido");
    await render(<BarraDeAbas abas={ABAS_ATLETA} ativa="index" aoEscolher={jest.fn()} lateral={false} selos={{ conta: 0 }} />);
    expect(screen.queryByTestId("selo-conta")).toBeNull();
  });
});

describe("papéis e a rota /conta", () => {
  it("/conta abre para os dois papéis; as abas do atleta não abrem para o professor", () => {
    expect(caminhoDoPapel("atleta", "/conta")).toBe(true);
    expect(caminhoDoPapel("professor", "/conta")).toBe(true);
    for (const r of ["/", "/treinos", "/evolucao", "/treino/1", "/consentimento"]) expect(caminhoDoPapel("professor", r)).toBe(false);
    expect(caminhoDoPapel("atleta", "/caixa-do-dia")).toBe(false);
  });
});

describe("aba Conta", () => {
  const conta = (extra = {}) => (
    <TelaConta
      papel="atleta"
      nome="Atleta Fixture 1"
      aoAbrirSemanaPadrao={jest.fn()}
      aoAbrirConsentimento={jest.fn()}
      aoTrocarSenha={jest.fn()}
      aoSair={jest.fn()}
      envio={{ apiUrl: "http://api.teste", atletaId: 1 }}
      {...extra}
    />
  );

  it("o atleta junta semana-padrão, consentimento, enviar FIT, trocar senha e sair", async () => {
    await render(conta());
    expect(screen.getByText("Atleta Fixture 1")).toBeTruthy();
    for (const t of ["Semana-padrão", "Consentimento", "Trocar senha", "Sair", "Enviar arquivo FIT"]) expect(screen.getByText(t)).toBeTruthy();
  });

  it("o professor só tem Trocar senha e Sair", async () => {
    await render(conta({ papel: "professor", envio: undefined }));
    expect(screen.getByText("Trocar senha")).toBeTruthy();
    expect(screen.queryByText("Semana-padrão")).toBeNull();
    expect(screen.queryByText("Consentimento")).toBeNull();
    expect(screen.queryByText("Enviar arquivo FIT")).toBeNull();
  });

  it("selo no Consentimento quando há pedido, com texto", async () => {
    await render(conta({ pedidos: 1 }));
    expect(screen.getByText("1 pedido")).toBeTruthy();
    expect(screen.getByTestId("conta-consentimento").props.accessibilityLabel).toBe("Consentimento, 1 pedido");
    await render(conta({ pedidos: 0 }));
    expect(screen.queryByTestId("conta-selo-consentimento")).toBeNull();
  });

  it("os itens chamam as ações e Sair pergunta antes", async () => {
    const aoAbrirSemanaPadrao = jest.fn();
    const aoAbrirConsentimento = jest.fn();
    const aoTrocarSenha = jest.fn();
    const aoSair = jest.fn();
    await render(conta({ aoAbrirSemanaPadrao, aoAbrirConsentimento, aoTrocarSenha, aoSair }));
    await fireEvent.press(screen.getByTestId("conta-semana-padrao"));
    await fireEvent.press(screen.getByTestId("conta-consentimento"));
    await fireEvent.press(screen.getByTestId("conta-trocar-senha"));
    expect([aoAbrirSemanaPadrao, aoAbrirConsentimento, aoTrocarSenha].every((f) => f.mock.calls.length === 1)).toBe(true);
    await fireEvent.press(screen.getByTestId("conta-sair"));
    expect(screen.getByText("Sair do app?")).toBeTruthy();
    expect(aoSair).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByTestId("cancelar-sair"));
    expect(aoSair).not.toHaveBeenCalled();
    await fireEvent.press(screen.getByTestId("conta-sair"));
    await fireEvent.press(screen.getByTestId("confirmar-sair"));
    expect(aoSair).toHaveBeenCalledTimes(1);
  });
});

describe("rotas das abas", () => {
  jest.mock("expo-router", () => ({
    useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
    router: { push: jest.fn(), navigate: jest.fn(), replace: jest.fn() },
  }));

  it("Conta renderiza com a sessão do papel", async () => {
    const Conta = require("../src/app/(app)/(abas)/conta").default;
    globalThis.fetch = jest.fn(async () => ({ ok: true, status: 200, json: async () => ({ professores: [] }) }) as Response) as unknown as typeof fetch;
    await render(<ComSessao sessao={criarSessaoFalsa(dentroAtleta())}><Conta /></ComSessao>);
    expect(screen.getByText("Semana-padrão")).toBeTruthy();
    await render(<ComSessao sessao={criarSessaoFalsa(dentroProfessor())}><Conta /></ComSessao>);
    expect(screen.queryByText("Semana-padrão")).toBeNull();
    expect(screen.getByText("Professor Fixture 1")).toBeTruthy();
  });
});
