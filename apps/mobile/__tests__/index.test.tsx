import type { EvolucaoTiros1km } from "@treino/api-client";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import exemplo from "../../../packages/api-client/exemplos/evolucao-tiros-1km.json";
import Inicio from "../src/app/index";
import { TelaEvolucao } from "../src/componentes/TelaEvolucao";

const base = exemplo as unknown as EvolucaoTiros1km;
const copia = (): EvolucaoTiros1km => JSON.parse(JSON.stringify(base));

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo: unknown) =>
  jest.fn(async (..._args: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch &
    jest.Mock;

const tela = (f: typeof fetch) => <TelaEvolucao apiUrl="http://api.teste" atletaId={1} fetchFn={f} />;

describe("tela de evolução", () => {
  it("mostra o título (rota inicial)", async () => {
    const original = globalThis.fetch;
    globalThis.fetch = fetchCom(200, base);
    await render(<Inicio />);
    expect(screen.getByText("Evolução dos tiros de 1 km")).toBeTruthy();
    await screen.findByTestId("lista-sessoes");
    globalThis.fetch = original;
  });

  it("mostra carregando enquanto espera", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getByText("Carregando seus tiros...")).toBeTruthy();
  });

  it("chama a API do atleta configurado", async () => {
    const f = fetchCom(200, base);
    await render(tela(f));
    await screen.findByTestId("lista-sessoes");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/evolucao/tiros-1km");
  });

  it("sucesso: gráfico, lista das sessões e rodapé", async () => {
    await render(tela(fetchCom(200, base)));
    const lista = await screen.findByTestId("lista-sessoes");
    expect(within(lista).getByText("4:11 min/km")).toBeTruthy();
    expect(within(lista).getByText("170.3 bpm")).toBeTruthy();
    expect(within(lista).getByText("6 tiros")).toBeTruthy();
    expect(within(lista).getByText("3:57 min/km")).toBeTruthy();
    expect(screen.getByTestId("painel-pace")).toBeTruthy();
    expect(screen.getByText(`cálculo: ${base.versao_calculo}`)).toBeTruthy();
  });

  it("vazio: sem sessões", async () => {
    const d = copia();
    d.sessoes = [];
    d.eixos = null;
    await render(tela(fetchCom(200, d)));
    expect(await screen.findByText("Ainda não há treinos de tiros de 1 km.")).toBeTruthy();
  });

  it("erro 404: atleta não encontrado", async () => {
    await render(tela(fetchCom(404, { detail: "atleta não encontrado" })));
    expect(await screen.findByText("Atleta não encontrado")).toBeTruthy();
    expect(screen.queryByText("Tentar de novo")).toBeNull();
  });

  it("erro 422: mensagem genérica", async () => {
    await render(tela(fetchCom(422, { detail: [] })));
    expect(await screen.findByText(/Não foi possível carregar os tiros/)).toBeTruthy();
  });

  it("erro de rede: mensagem e tentar de novo", async () => {
    const f = jest
      .fn()
      .mockRejectedValueOnce(new Error("falhou"))
      .mockResolvedValue(resposta(200, base)) as unknown as typeof fetch & jest.Mock;
    await render(tela(f));
    expect(await screen.findByText("Não foi possível falar com o servidor")).toBeTruthy();
    await fireEvent.press(screen.getByText("Tentar de novo"));
    await screen.findByTestId("lista-sessoes");
    expect(f).toHaveBeenCalledTimes(2);
    expect(screen.queryByText("Não foi possível falar com o servidor")).toBeNull();
  });

  it("o app não reformata: pace_medio e rótulo de eixo trocados aparecem como vieram", async () => {
    const d = copia();
    d.sessoes[0].pace_medio = "9:99";
    d.eixos!.pace!.marcas[0].rotulo = "8:88";
    await render(tela(fetchCom(200, d)));
    const lista = await screen.findByTestId("lista-sessoes");
    expect(within(lista).getByText("9:99 min/km")).toBeTruthy();
    expect(screen.getByText("8:88")).toBeTruthy();
  });

  it("versão desconhecida aparece no rodapé sem quebrar", async () => {
    const d = copia();
    d.versao_calculo = "tiros_1km@9";
    await render(tela(fetchCom(200, d)));
    expect(await screen.findByText("cálculo: tiros_1km@9")).toBeTruthy();
    expect(screen.getByTestId("lista-sessoes")).toBeTruthy();
  });

  it("reclassificacao_pendente true mostra o aviso; false não", async () => {
    const d = copia();
    d.reclassificacao_pendente = true;
    const { unmount } = await render(tela(fetchCom(200, d)));
    expect(await screen.findByText("cálculo em atualização")).toBeTruthy();
    await unmount();

    d.reclassificacao_pendente = false;
    await render(tela(fetchCom(200, d)));
    await waitFor(() => expect(screen.getByTestId("lista-sessoes")).toBeTruthy());
    expect(screen.queryByText("cálculo em atualização")).toBeNull();
  });
});
