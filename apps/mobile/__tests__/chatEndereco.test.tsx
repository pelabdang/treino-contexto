import { fireEvent, render, screen } from "@testing-library/react-native";
import { Platform } from "react-native";

import { ComSessao } from "../__fixtures__/sessaoFalsa";
import { conversa } from "../__fixtures__/chat";
import { trocarEnderecoDaConversa } from "../src/chat/endereco";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
const mockReplace = jest.fn();
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  useLocalSearchParams: () => ({}),
  router: { canGoBack: () => false, back: jest.fn(), replace: (...a: unknown[]) => mockReplace(...a), push: jest.fn() },
}));
import ChatNovo from "../src/app/(app)/chat/index";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

describe("endereço da conversa (#623, bloqueio da Lia)", () => {
  const plataforma = Platform.OS;
  afterEach(() => {
    Platform.OS = plataforma;
    delete (globalThis as { window?: unknown }).window;
  });

  it("na web troca só o endereço do navegador, sem pergunta nem resposta na URL", () => {
    const replaceState = jest.fn();
    (globalThis as { window?: unknown }).window = { history: { state: { a: 1 }, replaceState } };
    Platform.OS = "web";
    trocarEnderecoDaConversa(7);
    expect(replaceState).toHaveBeenCalledWith({ a: 1 }, "", "/chat/7");
  });

  it("no celular não faz nada", () => {
    const replaceState = jest.fn();
    (globalThis as { window?: unknown }).window = { history: { replaceState } };
    Platform.OS = "ios";
    trocarEnderecoDaConversa(7);
    expect(replaceState).not.toHaveBeenCalled();
  });

  it("na rota, depois da primeira resposta a tela não é trocada: cabeçalho, pergunta, resposta e compositor continuam visíveis", async () => {
    const replaceState = jest.fn();
    (globalThis as { window?: unknown }).window = { history: { state: null, replaceState } };
    Platform.OS = "web";
    const original = globalThis.fetch;
    globalThis.fetch = (async (url: string, init?: RequestInit) =>
      url.includes("/atividades") ? resposta(200, { atleta_id: 1, limite: 1, itens: [{ atividade_id: 1 }], proximo: null }) : resposta(201, conversa())) as unknown as typeof fetch;
    try {
      await render(<ComSessao><ChatNovo /></ComSessao>);
      await fireEvent.changeText(screen.getByTestId("chat-campo"), "Como foi minha semana?");
      await fireEvent.press(screen.getByTestId("chat-enviar"));
      await screen.findByTestId("chat-resposta");
      expect(replaceState).toHaveBeenCalledWith(null, "", "/chat/7");
      expect(mockReplace).not.toHaveBeenCalled(); // nada de router.replace: a tela não remonta
      expect(screen.getByText("Pergunte ao seu treino")).toBeTruthy();
      expect(screen.getAllByText("Como foi minha semana?").length).toBeGreaterThan(0);
      expect(screen.getByText("Nesta semana você correu 3 vezes, 28,4 km no total.")).toBeTruthy();
      expect(screen.getByTestId("chat-campo")).toBeTruthy();
    } finally {
      globalThis.fetch = original;
    }
  });
});
