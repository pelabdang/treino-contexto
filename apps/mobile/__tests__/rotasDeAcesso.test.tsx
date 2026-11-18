// Guarda de rotas (#502): sem acesso -> /entrar (lembrando o endereço), troca obrigatória -> /trocar-senha, papel errado -> início do papel.
import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import { ComSessao, criarSessaoFalsa, dentroAtleta, dentroProfessor } from "../__fixtures__/sessaoFalsa";
import type { EstadoSessao } from "../src/sessao/SessaoProvider";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

let mockCaminho = "/";
const mockReplace = jest.fn();
jest.mock("expo-router", () => {
  const { Text, View } = require("react-native");
  return {
    Stack: () => <View testID="stack" />,
    Redirect: ({ href }: { href: string }) => <Text testID="redirecionou">{href}</Text>,
    usePathname: () => mockCaminho,
    router: { replace: (...a: unknown[]) => mockReplace(...a), push: jest.fn(), canGoBack: () => false, back: jest.fn() },
  };
});

import LayoutDeDentro from "../src/app/(app)/_layout";
import Entrar from "../src/app/entrar";
import TrocarSenha from "../src/app/(app)/trocar-senha";

const noLayout = async (estado: EstadoSessao, caminho: string, extra = {}) => {
  mockCaminho = caminho;
  const sessao = criarSessaoFalsa(estado, extra);
  await render(
    <ComSessao sessao={sessao}>
      <LayoutDeDentro />
    </ComSessao>,
  );
  return sessao;
};

beforeEach(() => mockReplace.mockReset());

describe("guarda das telas de dentro", () => {
  it("verificando: mostra 'Verificando o seu acesso...' e não abre tela nenhuma", async () => {
    await noLayout({ tipo: "verificando" }, "/treino/1");
    expect(screen.getByText("Verificando o seu acesso...")).toBeTruthy();
    expect(screen.queryByTestId("stack")).toBeNull();
  });

  it("sem rede: não manda para a entrada; 'Tentar de novo' verifica de novo", async () => {
    const sessao = await noLayout({ tipo: "sem_rede" }, "/");
    expect(screen.queryByTestId("redirecionou")).toBeNull();
    expect(screen.getByText("Não foi possível falar com o servidor")).toBeTruthy();
    await fireEvent.press(screen.getByText("Tentar de novo"));
    expect(sessao.verificarDeNovo).toHaveBeenCalled();
  });

  it("sem acesso: vai a /entrar e lembra o endereço pedido", async () => {
    const sessao = await noLayout({ tipo: "sem_acesso", expirou: false, lembrar: true }, "/treino/107");
    expect(screen.getByTestId("redirecionou").props.children).toBe("/entrar");
    expect(screen.queryByTestId("stack")).toBeNull();
    await waitFor(() => expect(sessao.lembrarDestino).toHaveBeenCalledWith("/treino/107"));
  });

  it("saiu de propósito: vai a /entrar sem lembrar o endereço", async () => {
    const sessao = await noLayout({ tipo: "sem_acesso", expirou: false, lembrar: false }, "/");
    expect(screen.getByTestId("redirecionou").props.children).toBe("/entrar");
    expect(sessao.lembrarDestino).not.toHaveBeenCalled();
  });

  it("informa o caminho atual à sessão (para o acesso expirado lembrar onde a pessoa estava)", async () => {
    const sessao = await noLayout(dentroAtleta(), "/treino/5");
    expect(sessao.registrarCaminho).toHaveBeenCalledWith("/treino/5");
    expect(screen.getByTestId("stack")).toBeTruthy();
  });

  it("troca de senha obrigatória: abre /trocar-senha antes de qualquer outra tela", async () => {
    await noLayout({ ...(dentroAtleta() as object), trocaObrigatoria: true } as EstadoSessao, "/");
    expect(screen.getByTestId("redirecionou").props.children).toBe("/trocar-senha");
  });

  it("troca obrigatória e já em /trocar-senha: deixa abrir", async () => {
    await noLayout({ ...(dentroAtleta() as object), trocaObrigatoria: true } as EstadoSessao, "/trocar-senha");
    expect(screen.getByTestId("stack")).toBeTruthy();
  });

  it("o professor que cai numa tela do atleta vai à caixa do dia; o atleta na caixa vai ao início", async () => {
    await noLayout(dentroProfessor(), "/treino/1");
    expect(screen.getByTestId("redirecionou").props.children).toBe("/caixa-do-dia");
    await noLayout(dentroAtleta(), "/caixa-do-dia");
    expect(screen.getAllByTestId("redirecionou").at(-1)?.props.children).toBe("/");
  });

  it("o professor abre a caixa e o atleta abre o início", async () => {
    await noLayout(dentroProfessor(), "/caixa-do-dia");
    expect(screen.getByTestId("stack")).toBeTruthy();
  });
});

describe("rota /entrar", () => {
  const naEntrada = async (estado: EstadoSessao, extra = {}) => {
    const sessao = criarSessaoFalsa(estado, extra);
    await render(
      <ComSessao sessao={sessao}>
        <Entrar />
      </ComSessao>,
    );
    return sessao;
  };

  it("sem acesso: mostra o formulário; expirado: com a faixa", async () => {
    await naEntrada({ tipo: "sem_acesso", expirou: true, lembrar: false });
    expect(screen.getByText("Seu acesso expirou. Entre de novo.")).toBeTruthy();
    expect(screen.getByTestId("botao-entrar")).toBeTruthy();
  });

  it("depois de entrar, volta ao endereço lembrado se for do papel", async () => {
    await naEntrada(dentroAtleta(), { consumirDestino: jest.fn(async () => "/treino/107") });
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/treino/107"));
  });

  it("endereço lembrado de outro papel ou de fora é ignorado: vai ao início do papel", async () => {
    await naEntrada(dentroProfessor(), { consumirDestino: jest.fn(async () => "/treino/107") });
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/caixa-do-dia"));
    mockReplace.mockReset();
    await naEntrada(dentroAtleta(), { consumirDestino: jest.fn(async () => "https://outro.site") });
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/"));
  });

  it("com a troca de senha obrigatória, vai a /trocar-senha e guarda o endereço lembrado", async () => {
    const consumir = jest.fn(async () => "/treino/1");
    await naEntrada({ ...(dentroAtleta() as object), trocaObrigatoria: true } as EstadoSessao, { consumirDestino: consumir });
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/trocar-senha"));
    expect(consumir).not.toHaveBeenCalled();
  });

  it("verificando e sem rede têm as próprias telas", async () => {
    await naEntrada({ tipo: "verificando" });
    expect(screen.getByText("Verificando o seu acesso...")).toBeTruthy();
    await naEntrada({ tipo: "sem_rede" });
    expect(screen.getByTestId("acesso-sem-rede")).toBeTruthy();
  });
});

describe("rota /trocar-senha", () => {
  it("no primeiro acesso, depois de salvar e continuar, vai ao endereço lembrado ou ao início do papel", async () => {
    const trocarSenha = jest.fn(async () => ({ ok: true as const, dados: { token: "n", expira_em: "x" } }));
    const sessao = criarSessaoFalsa({ ...(dentroProfessor() as object), trocaObrigatoria: true } as EstadoSessao, { trocarSenha });
    await render(
      <ComSessao sessao={sessao}>
        <TrocarSenha />
      </ComSessao>,
    );
    expect(screen.queryByTestId("voltar")).toBeNull();
    await fireEvent.changeText(screen.getByTestId("campo-senha-atual"), "provisoria-sintetica");
    await fireEvent.changeText(screen.getByTestId("campo-senha-nova"), "senha-nova-sintetica");
    await fireEvent.changeText(screen.getByTestId("campo-senha-repetida"), "senha-nova-sintetica");
    await fireEvent.press(screen.getByTestId("botao-salvar"));
    expect(trocarSenha).toHaveBeenCalledWith("provisoria-sintetica", "senha-nova-sintetica");
    await fireEvent.press(await screen.findByTestId("continuar"));
    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith("/caixa-do-dia"));
  });
});
