import { act, fireEvent, render, screen } from "@testing-library/react-native";

import { AcoesResposta, TEXTO_AVALIAR_ERRO, TEXTO_COPIAR_ERRO } from "../src/componentes/AcoesResposta";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));
const mockCopiar = jest.fn();
jest.mock("expo-clipboard", () => ({ setStringAsync: (t: string) => mockCopiar(t) }));

const marcado = (id: string) => screen.getByTestId(id).props.accessibilityState.checked;
beforeEach(() => mockCopiar.mockReset().mockResolvedValue(true));

describe("copiar", () => {
  it("copia só o texto da resposta, vira 'Copiado' por 2 s e volta a 'Copiar'", async () => {
    jest.useFakeTimers();
    try {
      await render(<AcoesResposta texto="Você correu 28,4 km." avaliacaoInicial={null} aoAvaliar={jest.fn()} />);
      expect(screen.getByText("Copiar")).toBeTruthy();
      await fireEvent.press(screen.getByTestId("chat-copiar"));
      expect(mockCopiar).toHaveBeenCalledWith("Você correu 28,4 km.");
      expect(screen.getByText("Copiado")).toBeTruthy();
      expect(screen.getByText("Resposta copiada")).toBeTruthy();
      await act(async () => {
        jest.advanceTimersByTime(2000);
      });
      expect(screen.getByText("Copiar")).toBeTruthy();
    } finally {
      jest.useRealTimers();
    }
  });

  it("se a cópia falha: 'Não deu para copiar.' e o botão fica 'Copiar'", async () => {
    mockCopiar.mockResolvedValue(false);
    await render(<AcoesResposta texto="x" avaliacaoInicial={null} aoAvaliar={jest.fn()} />);
    await fireEvent.press(screen.getByTestId("chat-copiar"));
    expect(screen.getByText(TEXTO_COPIAR_ERRO)).toBeTruthy();
    expect(screen.getByText("Copiar")).toBeTruthy();
  });

  it("rótulos falados e grupo 'Ações da resposta'", async () => {
    await render(<AcoesResposta texto="x" avaliacaoInicial={null} aoAvaliar={jest.fn()} />);
    expect(screen.getByLabelText("Ações da resposta")).toBeTruthy();
    expect(screen.getByLabelText("Copiar resposta")).toBeTruthy();
    expect(screen.getByLabelText("Gostei da resposta")).toBeTruthy();
    expect(screen.getByLabelText("Não gostei da resposta")).toBeTruthy();
  });
});

describe("👍/👎", () => {
  it("abre com a avaliação que a API guardou", async () => {
    await render(<AcoesResposta texto="x" avaliacaoInicial={1} aoAvaliar={jest.fn()} />);
    expect(marcado("chat-gostei")).toBe(true);
    expect(marcado("chat-nao-gostei")).toBe(false);
  });

  it("um só vale: tocar no outro troca; tocar no marcado desmarca (null); manda só o valor", async () => {
    const aoAvaliar = jest.fn(async (_v: 1 | -1 | null) => true);
    await render(<AcoesResposta texto="x" avaliacaoInicial={null} aoAvaliar={aoAvaliar} />);
    await fireEvent.press(screen.getByTestId("chat-gostei"));
    expect(marcado("chat-gostei")).toBe(true);
    await fireEvent.press(screen.getByTestId("chat-nao-gostei"));
    expect(marcado("chat-gostei")).toBe(false);
    expect(marcado("chat-nao-gostei")).toBe(true);
    await fireEvent.press(screen.getByTestId("chat-nao-gostei"));
    expect(marcado("chat-nao-gostei")).toBe(false);
    expect(aoAvaliar.mock.calls.map((c) => c[0])).toEqual([1, -1, null]);
  });

  it("é otimista: aparece marcado enquanto grava", async () => {
    let fim: (v: boolean) => void = () => {};
    const aoAvaliar = jest.fn(() => new Promise<boolean>((ok) => (fim = ok)));
    await render(<AcoesResposta texto="x" avaliacaoInicial={null} aoAvaliar={aoAvaliar} />);
    await fireEvent.press(screen.getByTestId("chat-gostei"));
    expect(marcado("chat-gostei")).toBe(true);
    await act(async () => fim(true));
    expect(marcado("chat-gostei")).toBe(true);
  });

  it("se a API falha: volta ao estado anterior e avisa", async () => {
    const aoAvaliar = jest.fn(async () => false);
    await render(<AcoesResposta texto="x" avaliacaoInicial={-1} aoAvaliar={aoAvaliar} />);
    await fireEvent.press(screen.getByTestId("chat-gostei"));
    expect(marcado("chat-gostei")).toBe(false);
    expect(marcado("chat-nao-gostei")).toBe(true);
    expect(screen.getByText(TEXTO_AVALIAR_ERRO)).toBeTruthy();
  });
});
