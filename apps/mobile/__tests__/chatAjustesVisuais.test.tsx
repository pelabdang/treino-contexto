import { fireEvent, render, screen } from "@testing-library/react-native";
import { StyleSheet } from "react-native";

import { ComSessao } from "../__fixtures__/sessaoFalsa";
import { conversa, falha } from "../__fixtures__/chat";
import { limparPerguntasProntas } from "../src/chat/prontas";
import { coresClaro } from "../src/tema/tokens";
import { AcoesResposta } from "../src/componentes/AcoesResposta";
import { TelaChat } from "../src/componentes/TelaChat";
import ChatConversa from "../src/app/(app)/chat/[id]";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
jest.mock("expo-clipboard", () => ({ setStringAsync: jest.fn(async () => true) }));
const mockReplace = jest.fn();
jest.mock("expo-router", () => ({
  useFocusEffect: (cb: () => void) => require("react").useEffect(cb, [cb]),
  useLocalSearchParams: () => ({ id: "7" }),
  router: { canGoBack: () => false, back: jest.fn(), replace: (...a: unknown[]) => mockReplace(...a), push: jest.fn() },
}));

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
beforeEach(() => limparPerguntasProntas());

describe("ajustes visuais do chat (#624, #637)", () => {
  it("'Tentar de novo' é o botão primário (fundo e texto do botão do tema)", async () => {
    const f = jest.fn(async (url: string, init?: RequestInit) => {
      if (url.includes("/atividades")) return resposta(200, { itens: [{ atividade_id: 1 }] });
      if (url.includes("/chat/")) return resposta(200, { perguntas: [] });
      return init?.method === "POST" ? resposta(201, conversa({ mensagens: [falha] })) : resposta(200, {});
    }) as unknown as typeof fetch;
    await render(<TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoVoltar={jest.fn()} aoAbrirConversas={jest.fn()} aoAbrirTreino={jest.fn()} aoAbrirEvolucao={jest.fn()} />);
    await fireEvent.changeText(screen.getByTestId("chat-campo"), "Oi");
    await fireEvent.press(screen.getByTestId("chat-enviar"));
    const botao = StyleSheet.flatten((await screen.findByTestId("chat-tentar-de-novo")).props.style);
    expect(botao.backgroundColor).toBe(coresClaro.botao);
    expect(botao.minHeight).toBe(48);
  });

  it("o campo focado ganha o anel de cor.foco, e perde ao sair", async () => {
    const f = jest.fn(async () => resposta(200, { itens: [], perguntas: [] })) as unknown as typeof fetch;
    await render(<TelaChat apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoVoltar={jest.fn()} aoAbrirConversas={jest.fn()} aoAbrirTreino={jest.fn()} aoAbrirEvolucao={jest.fn()} />);
    const estilo = () => StyleSheet.flatten(screen.getByTestId("chat-campo").props.style);
    expect(estilo().outlineColor).toBeUndefined();
    await fireEvent(screen.getByTestId("chat-campo"), "focus");
    expect(estilo().outlineColor).toBe(coresClaro.foco);
    await fireEvent(screen.getByTestId("chat-campo"), "blur");
    expect(estilo().outlineColor).toBeUndefined();
  });

  it("Copiar, 👍 e 👎 têm contorno de 1,5 em borda-forte; o marcado, de 2", async () => {
    await render(<AcoesResposta texto="x" avaliacaoInicial={1} aoAvaliar={jest.fn()} />);
    for (const id of ["chat-copiar", "chat-nao-gostei"]) {
      const e = StyleSheet.flatten(screen.getByTestId(id).props.style);
      expect(e.borderWidth).toBe(1.5);
      expect(e.borderColor).toBe(coresClaro["borda-forte"]);
    }
    expect(StyleSheet.flatten(screen.getByTestId("chat-gostei").props.style).borderWidth).toBe(2);
  });

  it("'Voltar' de uma conversa aberta direto (sem pilha, depois de recarregar) leva ao Início", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = jest.fn(async () => resposta(200, conversa())) as unknown as typeof fetch;
    try {
      await render(<ComSessao><ChatConversa /></ComSessao>);
      await screen.findByTestId("chat-resposta");
      await fireEvent.press(screen.getByTestId("chat-voltar"));
      expect(mockReplace).toHaveBeenCalledWith("/");
    } finally {
      globalThis.fetch = original;
    }
  });
});
