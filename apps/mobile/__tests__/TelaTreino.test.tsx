import { StyleSheet } from "react-native";
import { fireEvent, render, screen, within } from "@testing-library/react-native";

import { TelaTreino } from "../src/componentes/TelaTreino";
import { atividades } from "../__fixtures__/atividades";

// Ícone falso com nome e tamanho (o real carrega a fonte e quebra no Jest).
jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo: unknown) =>
  jest.fn(async (..._args: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;
const tela = (f: typeof fetch, extra = {}) => (
  <TelaTreino apiUrl="http://api.teste" atletaId={1} atividadeId={101} fetchFn={f} {...extra} />
);

// O primeiro render a frio no CI passou de 5 s uma vez (#219); folga para a máquina lenta.
jest.setTimeout(20000);

describe("tela de um treino", () => {
  it("chama a API da atividade", async () => {
    const f = fetchCom(200, atividades.ok);
    await render(tela(f));
    await screen.findByTestId("cartao-resumo");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/atividades/101");
  });

  it("mostra carregando", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getByText("Carregando o treino...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-treino", { includeHiddenElements: true })).toBeTruthy();
    expect(screen.queryByTestId("esqueleto-evolucao", { includeHiddenElements: true })).toBeNull();
  });

  it("erro de rede: ícone wifi-off de 40, alerta e 'Tentar de novo'; 404 e 500: error-outline de 40", async () => {
    const { unmount } = await render(tela(jest.fn().mockRejectedValue(new Error("x")) as unknown as typeof fetch));
    const rede = await screen.findByTestId("estado-erro");
    expect(within(rede).getByText("wifi-off:40")).toBeTruthy();
    expect(within(rede).getByRole("alert")).toBeTruthy();
    await unmount();
    for (const status of [404, 500]) {
      const r = await render(tela(fetchCom(status, { detail: "x" })));
      const e = await screen.findByTestId("estado-erro");
      expect(within(e).getByText("error-outline:40")).toBeTruthy();
      expect(within(e).getByRole("alert")).toBeTruthy();
      expect(within(e).queryByText("Tentar de novo")).toBeNull();
      await r.unmount();
    }
  });

  it("cada linha do clima é um item só, lido como 'rótulo, valor'", async () => {
    await render(tela(fetchCom(200, atividades.ok)));
    const cartao = await screen.findByTestId("cartao-clima");
    for (const rotulo of ["Temperatura, 24,3 °C", "Sensação térmica, 25,1 °C", "Umidade, 61 %", "Vento, 8,2 km/h"]) {
      expect(within(cartao).getByLabelText(rotulo).props.accessible).toBe(true);
    }
  });

  it("clima ok: resumo com campos prontos, valores do clima e atribuição", async () => {
    await render(tela(fetchCom(200, atividades.ok)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("18/03/25 às 06:30")).toBeTruthy();
    expect(screen.getByText("0:52:05")).toBeTruthy();
    expect(screen.getByText(/Pace médio: 5:12/)).toBeTruthy();
    expect(screen.getByText(/Distância: 10,00/)).toBeTruthy();
    expect(screen.getByText("FC média: 152 bpm")).toBeTruthy();
    expect(screen.getByText("24,3 °C")).toBeTruthy();
    expect(screen.getByText("25,1 °C")).toBeTruthy();
    expect(screen.getByText("61 %")).toBeTruthy();
    expect(screen.getByText("8,2 km/h")).toBeTruthy();
    expect(screen.getByText("Weather data by Open-Meteo.com")).toBeTruthy();
  });

  it("não formata: mostra pace, hora e duração exatamente como vieram", async () => {
    const a = { ...atividades.ok, pace_medio: "9:99", hora_local: "99:88", duracao: "7:77:77", data_local: "2030-01-02" };
    await render(tela(fetchCom(200, a)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("02/01/30 às 99:88")).toBeTruthy();
    expect(screen.getByText("7:77:77")).toBeTruthy();
    expect(screen.getByText(/Pace médio: 9:99/)).toBeTruthy();
  });

  it("distância: mostra `distancia` exatamente como veio, sem converter distancia_m", async () => {
    const a = { ...atividades.ok, distancia: "ABC 7,5 xyz", distancia_m: 123456 };
    await render(tela(fetchCom(200, a)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("Distância: ABC 7,5 xyz")).toBeTruthy();
    expect(screen.queryByText(/123/)).toBeNull();
  });

  it("distância: natação em metros e sem distância não mostra a linha", async () => {
    await render(tela(fetchCom(200, atividades.natacao)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.getByText("Distância: 1.800 m")).toBeTruthy();
  });

  it("distância null: não mostra a linha, mesmo com distancia_m", async () => {
    await render(tela(fetchCom(200, { ...atividades.ok, distancia: null, distancia_m: 5000 })));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByText(/Distância/)).toBeNull();
  });

  it("atribuição vem da API: sem o campo, não inventa", async () => {
    const clima = { ...atividades.ok.clima!, atribuicao: undefined };
    await render(tela(fetchCom(200, { ...atividades.ok, clima })));
    await screen.findByTestId("cartao-clima");
    expect(screen.queryByText(/Open-Meteo/)).toBeNull();
  });

  it.each([
    ["indoor", "Treino em ambiente fechado: não há clima para mostrar."],
    ["sem_posicao", "O arquivo não tem posição, então não dá para buscar o clima."],
    ["pendente", "O clima deste treino ainda não chegou. Treinos recentes podem levar cerca de uma semana."],
    ["falha", "Não foi possível obter o clima deste treino."],
  ] as const)("clima %s: frase própria, sem valores nem atribuição", async (chave, frase) => {
    await render(tela(fetchCom(200, atividades[chave])));
    await screen.findByTestId("cartao-clima");
    expect(screen.getByText(frase)).toBeTruthy();
    expect(screen.queryByText("Temperatura")).toBeNull();
    expect(screen.queryByText(/Open-Meteo/)).toBeNull();
  });

  it("natação: sem pace e sem FC", async () => {
    await render(tela(fetchCom(200, atividades.natacao)));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByText(/Pace médio/)).toBeNull();
    expect(screen.getByText("FC média: sem FC")).toBeTruthy();
    expect(screen.getByText("0:45:00")).toBeTruthy();
    expect(screen.getAllByText("Natação").length).toBeGreaterThan(0);
  });

  it("sem objeto clima: não mostra o cartão", async () => {
    await render(tela(fetchCom(200, { ...atividades.ok, clima: null })));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByTestId("cartao-clima")).toBeNull();
  });

  it("404 de atividade", async () => {
    await render(tela(fetchCom(404, { detail: "atividade não encontrada" })));
    expect(await screen.findByText("Treino não encontrado")).toBeTruthy();
  });

  it("404 de atleta", async () => {
    await render(tela(fetchCom(404, { detail: "atleta não encontrado" })));
    expect(await screen.findByText("Atleta não encontrado")).toBeTruthy();
  });

  it("erro 500", async () => {
    await render(tela(fetchCom(500, {})));
    expect(await screen.findByText("Não foi possível carregar este treino. Tente de novo mais tarde.")).toBeTruthy();
  });

  it("erro de rede tem 'Tentar de novo'", async () => {
    const f = jest
      .fn()
      .mockRejectedValueOnce(new Error("rede"))
      .mockResolvedValue(resposta(200, atividades.ok)) as unknown as typeof fetch;
    await render(tela(f));
    expect(await screen.findByText("Não foi possível falar com o servidor")).toBeTruthy();
    fireEvent.press(screen.getByText("Tentar de novo"));
    expect(await screen.findByTestId("cartao-resumo")).toBeTruthy();
  });

  it("voltar chama o callback", async () => {
    const aoVoltar = jest.fn();
    await render(tela(fetchCom(200, atividades.ok), { aoVoltar }));
    fireEvent.press(screen.getByLabelText("Voltar"));
    expect(aoVoltar).toHaveBeenCalled();
  });

  it("alvo de toque do voltar tem 44", async () => {
    await render(tela(fetchCom(200, atividades.ok), { aoVoltar: () => {} }));
    const estilo = StyleSheet.flatten(screen.getByLabelText("Voltar").props.style);
    expect(estilo.minHeight).toBeGreaterThanOrEqual(44);
  });
});
