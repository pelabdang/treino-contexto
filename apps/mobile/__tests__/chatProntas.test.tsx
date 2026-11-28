import { act, render, screen, waitFor } from "@testing-library/react-native";
import { Text } from "react-native";

import { limparPerguntasProntas, TEMPO_PERGUNTAS_PRONTAS_MS, usePerguntasProntas } from "../src/chat/prontas";
import { PERGUNTAS_PRONTAS } from "../src/chat/textos";

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const daApi = ["Como foi minha natação de quinta?", "Meu melhor 5 km?", "Quanto nadei em março?", "Como estão minha carga e minha forma?"];

function Sonda({ f, atleta = 1 }: { f: typeof fetch; atleta?: number }) {
  const { perguntas } = usePerguntasProntas("http://api.teste", atleta, f);
  return <Text testID="lista">{perguntas === null ? "carregando" : perguntas.join("|")}</Text>;
}
const texto = () => screen.getByTestId("lista").props.children as string;

beforeEach(() => limparPerguntasProntas());

describe("perguntas prontas: lista da API e plano B", () => {
  it("carrega da rota e mostra a lista como veio", async () => {
    const f = jest.fn(async (..._a: unknown[]) => resposta(200, { atleta_id: 1, versao: "v1", perguntas: daApi })) as unknown as typeof fetch & jest.Mock;
    await render(<Sonda f={f} />);
    await waitFor(() => expect(texto()).toBe(daApi.join("|")));
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/chat/perguntas-prontas");
  });

  it("o app ignora o que passar de 6", async () => {
    const dez = Array.from({ length: 10 }, (_, i) => `Pergunta ${i}?`);
    await render(<Sonda f={jest.fn(async () => resposta(200, { perguntas: dez })) as unknown as typeof fetch} />);
    await waitFor(() => expect(texto().split("|")).toHaveLength(6));
  });

  it.each([
    ["erro 500", () => resposta(500, {})],
    ["lista vazia", () => resposta(200, { perguntas: [] })],
    ["queda de rede", () => Promise.reject(new Error("x"))],
  ])("%s: as 6 fixas, sem aviso", async (_n, r) => {
    await render(<Sonda f={jest.fn(async () => r()) as unknown as typeof fetch} />);
    await waitFor(() => expect(texto()).toBe(PERGUNTAS_PRONTAS.join("|")));
  });

  it("depois de 4 s sem resposta usa as 6 fixas, e a lista da API que chegar depois não troca", async () => {
    jest.useFakeTimers();
    try {
      let chegar: (r: Response) => void = () => {};
      const f = jest.fn(() => new Promise<Response>((ok) => (chegar = ok))) as unknown as typeof fetch;
      await render(<Sonda f={f} />);
      expect(texto()).toBe("carregando");
      await act(async () => {
        jest.advanceTimersByTime(TEMPO_PERGUNTAS_PRONTAS_MS);
      });
      expect(texto()).toBe(PERGUNTAS_PRONTAS.join("|"));
      await act(async () => {
        chegar(resposta(200, { perguntas: daApi }));
      });
      expect(texto()).toBe(PERGUNTAS_PRONTAS.join("|"));
    } finally {
      jest.useRealTimers();
    }
  });

  it("uma lista por sessão: o segundo uso não busca de novo e vê a mesma lista", async () => {
    const f = jest.fn(async (..._a: unknown[]) => resposta(200, { perguntas: daApi })) as unknown as typeof fetch & jest.Mock;
    const { unmount } = await render(<Sonda f={f} />);
    await waitFor(() => expect(texto()).toBe(daApi.join("|")));
    await unmount();
    await render(<Sonda f={f} />);
    expect(texto()).toBe(daApi.join("|")); // sem esqueleto, sem piscar
    expect(f).toHaveBeenCalledTimes(1);
  });

  it("dois blocos ao mesmo tempo (Início e chat) dividem uma busca só", async () => {
    const f = jest.fn(async (..._a: unknown[]) => resposta(200, { perguntas: daApi })) as unknown as typeof fetch & jest.Mock;
    await render(<><Sonda f={f} /><Sonda f={f} /></>);
    await waitFor(() => expect(screen.getAllByText(daApi.join("|"))).toHaveLength(2));
    expect(f).toHaveBeenCalledTimes(1);
  });

  it("cada atleta tem a sua lista", async () => {
    const f = jest.fn(async (u: unknown) => resposta(200, { perguntas: String(u).includes("/atletas/1/") ? ["A?"] : ["B?"] })) as unknown as typeof fetch;
    const { unmount } = await render(<Sonda f={f} atleta={1} />);
    await waitFor(() => expect(texto()).toBe("A?"));
    await unmount();
    await render(<Sonda f={f} atleta={2} />);
    await waitFor(() => expect(texto()).toBe("B?"));
  });
});
