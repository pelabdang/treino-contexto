import { fireEvent, render, screen, within } from "@testing-library/react-native";

import { TelaCheckinsPendentes } from "../src/componentes/TelaCheckinsPendentes";
import { pendentes } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const fetchCom = (status: number, corpo: unknown) =>
  jest.fn(async (..._a: Parameters<typeof fetch>) => resposta(status, corpo)) as unknown as typeof fetch & jest.Mock;
const tela = (f: typeof fetch, extra = {}) => (
  <TelaCheckinsPendentes apiUrl="http://api.teste" atletaId={1} aoAbrirCheckin={jest.fn()} fetchFn={f} {...extra} />
);

describe("lista de check-ins pendentes", () => {
  it("chama a API de pendentes", async () => {
    const f = fetchCom(200, pendentes);
    await render(tela(f));
    await screen.findByTestId("lista-pendentes");
    expect(f.mock.calls[0][0]).toBe("http://api.teste/atletas/1/checkins/pendentes");
  });

  it("carregando: esqueleto de três linhas e texto", async () => {
    await render(tela(jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch));
    expect(screen.getByText("Carregando seus treinos...")).toBeTruthy();
    expect(screen.getByTestId("esqueleto-pendentes", { includeHiddenElements: true })).toBeTruthy();
  });

  it("lista: título do treino, ícone da modalidade, data e hora, total, mais recente no alto", async () => {
    await render(tela(fetchCom(200, pendentes)));
    const lista = await screen.findByTestId("lista-pendentes");
    expect(screen.getByText("Treinos dos últimos 7 dias sem check-in")).toBeTruthy();
    const linhas = within(lista).getAllByRole("button");
    expect(linhas).toHaveLength(2);
    expect(within(linhas[0]).getByText("Corrida, 52 min")).toBeTruthy();
    expect(within(linhas[0]).getByText("18/03/25 às 06:30")).toBeTruthy();
    expect(within(linhas[0]).getByText("directions-run:24")).toBeTruthy();
    expect(within(linhas[1]).getByText("pool:24")).toBeTruthy();
    expect(linhas[0].props.accessibilityLabel).toBe("Corrida, 52 min, 18/03/25 às 06:30");
    expect(screen.getByTestId("total-pendentes").props.children).toBe("2 treinos sem check-in");
  });

  it("um treino: '1 treino sem check-in'", async () => {
    await render(tela(fetchCom(200, { ...pendentes, total: 1, pendentes: [pendentes.pendentes[0]] })));
    await screen.findByTestId("lista-pendentes");
    expect(screen.getByText("1 treino sem check-in")).toBeTruthy();
  });

  it("tocar a linha abre o check-in daquela atividade", async () => {
    const abrir = jest.fn();
    await render(tela(fetchCom(200, pendentes), { aoAbrirCheckin: abrir }));
    await fireEvent.press(await screen.findByTestId("pendente-106"));
    expect(abrir).toHaveBeenCalledWith(106);
  });

  it("vazio: ícone, título e frase com os dias da API, sem botão primário", async () => {
    await render(tela(fetchCom(200, { dias: 7, total: 0, pendentes: [] })));
    const vazio = await screen.findByTestId("estado-vazio");
    expect(within(vazio).getByText("check-circle-outline:40")).toBeTruthy();
    expect(within(vazio).getByText("Nenhum check-in pendente")).toBeTruthy();
    expect(within(vazio).getByText("Você fez o check-in de todos os treinos dos últimos 7 dias.")).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("erro de rede tem 'Tentar de novo'; outro erro não", async () => {
    const { unmount } = await render(tela(jest.fn().mockRejectedValue(new Error("x")) as unknown as typeof fetch));
    const rede = await screen.findByTestId("estado-erro");
    expect(within(rede).getByText("wifi-off:40")).toBeTruthy();
    expect(within(rede).getByText("Não foi possível falar com o servidor")).toBeTruthy();
    expect(within(rede).getByRole("alert")).toBeTruthy();
    expect(within(rede).getByText("Tentar de novo")).toBeTruthy();
    await unmount();
    await render(tela(fetchCom(500, {})));
    const outro = await screen.findByTestId("estado-erro");
    expect(within(outro).getByText("error-outline:40")).toBeTruthy();
    expect(within(outro).getByText("Não foi possível carregar os pendentes. Tente de novo mais tarde.")).toBeTruthy();
    expect(within(outro).queryByText("Tentar de novo")).toBeNull();
  });

  it("nada do check-in aparece: só o treino", async () => {
    await render(tela(fetchCom(200, pendentes)));
    await screen.findByTestId("lista-pendentes");
    expect(screen.queryByText(/PSE|Sensação|Observação/)).toBeNull();
  });

  it("Voltar chama aoVoltar", async () => {
    const voltar = jest.fn();
    await render(tela(fetchCom(200, pendentes), { aoVoltar: voltar }));
    await fireEvent.press(await screen.findByLabelText("Voltar"));
    expect(voltar).toHaveBeenCalled();
  });

  it("ao voltar ao foco (atualizar muda) busca de novo e mantém a lista se a busca falhar", async () => {
    const f = fetchCom(200, pendentes);
    const { rerender } = await render(tela(f, { atualizar: 0 }));
    await screen.findByTestId("lista-pendentes");
    f.mockImplementationOnce(async () => resposta(200, { dias: 7, total: 1, pendentes: [pendentes.pendentes[1]] }));
    await rerender(tela(f, { atualizar: 1 }));
    await screen.findByText("1 treino sem check-in");
    expect(screen.queryByTestId("pendente-101")).toBeNull();
    f.mockImplementationOnce(async () => {
      throw new Error("x");
    });
    await rerender(tela(f, { atualizar: 2 }));
    expect(f).toHaveBeenCalledTimes(3);
    expect(screen.getByTestId("pendente-106")).toBeTruthy();
    expect(screen.queryByTestId("estado-erro")).toBeNull();
  });
});
