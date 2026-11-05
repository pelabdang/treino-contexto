import type { EvolucaoTiros1km } from "@treino/api-client";
import { StyleSheet } from "react-native";
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
    expect(within(lista).getByText("4:08 min/km")).toBeTruthy();
    expect(within(lista).getByText("175 bpm")).toBeTruthy();
    expect(within(lista).getByText("média 4:11 · 6 tiros")).toBeTruthy();
    expect(within(lista).getByText("3:54 min/km")).toBeTruthy();
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

  it("cartão do último treino: melhor tiro em destaque, FC do melhor tiro e média no secundário", async () => {
    await render(tela(fetchCom(200, base)));
    const cartao = await screen.findByTestId("cartao-ultimo-treino");
    // a última sessão da lista (data crescente) é a de 11/03/25
    expect(within(cartao).getByText("Último treino · 11/03/25")).toBeTruthy();
    expect(within(cartao).getByText("Melhor tiro")).toBeTruthy();
    expect(within(cartao).getByText(/3:54/)).toBeTruthy();
    expect(within(cartao).getByText("FC do melhor tiro: 177 bpm")).toBeTruthy();
    expect(within(cartao).getByText("Média dos tiros: 3:57 min/km · 5 tiros")).toBeTruthy();
  });

  it("lista: mais recente no alto", async () => {
    await render(tela(fetchCom(200, base)));
    const lista = await screen.findByTestId("lista-sessoes");
    const datas = within(lista)
      .getAllByText(/^\d\d\/\d\d\/\d\d$/)
      .map((n) => n.props.children);
    expect(datas).toEqual(["11/03/25", "04/03/25"]);
  });

  it("melhor tiro sem FC: 'sem FC' no cartão e na lista", async () => {
    const d = copia();
    d.sessoes[1].fc_melhor_tiro = null;
    await render(tela(fetchCom(200, d)));
    const cartao = await screen.findByTestId("cartao-ultimo-treino");
    expect(within(cartao).getByText("FC do melhor tiro: sem FC")).toBeTruthy();
    expect(within(screen.getByTestId("lista-sessoes")).getByText("sem FC")).toBeTruthy();
  });

  it("o app não recalcula: pace_melhor e rótulo de eixo trocados aparecem como vieram (9:99)", async () => {
    const d = copia();
    d.sessoes[1].pace_melhor = "9:99";
    d.sessoes[1].pace_medio = "7:77";
    d.eixos!.pace!.marcas[0].rotulo = "8:88";
    await render(tela(fetchCom(200, d)));
    const lista = await screen.findByTestId("lista-sessoes");
    expect(within(lista).getByText("9:99 min/km")).toBeTruthy();
    expect(within(lista).getByText("média 7:77 · 5 tiros")).toBeTruthy();
    expect(within(screen.getByTestId("cartao-ultimo-treino")).getByText(/9:99/)).toBeTruthy();
    expect(screen.getByText("8:88")).toBeTruthy();
  });

  it("margem da tela: 16 no celular e 24 a partir de 600 de largura", async () => {
    const spy = jest.spyOn(require("react-native"), "useWindowDimensions");
    const pad = () => StyleSheet.flatten(screen.getByTestId("rolagem-tela").props.contentContainerStyle).padding;
    spy.mockReturnValue({ width: 360, height: 800, scale: 2, fontScale: 1 });
    const { unmount } = await render(tela(fetchCom(200, base)));
    await screen.findByTestId("lista-sessoes");
    expect(pad()).toBe(16);
    await unmount();
    spy.mockReturnValue({ width: 900, height: 800, scale: 2, fontScale: 1 });
    await render(tela(fetchCom(200, base)));
    await screen.findByTestId("lista-sessoes");
    expect(pad()).toBe(24);
    spy.mockRestore();
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
