import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";
import type { Atividade } from "@treino/api-client";

import { TelaTreino } from "../src/componentes/TelaTreino";
import { atividadesCheckin, MARCADOR } from "../__fixtures__/checkin";

jest.mock("@expo/vector-icons", () => {
  const { Text } = require("react-native");
  return { MaterialIcons: ({ name, size }: { name: string; size: number }) => <Text>{`${name}:${size}`}</Text> };
});

jest.setTimeout(20000);

const resposta = (status: number, corpo?: unknown) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;

/** GET devolve a lista de atividades em sequência (a última se repete); DELETE responde 204 ou falha. */
function servidor(atividades: Atividade[], del: "ok" | "falha" = "ok") {
  let i = 0;
  return jest.fn(async (_url: unknown, init?: RequestInit) => {
    if (init?.method === "DELETE") {
      if (del === "falha") throw new Error("x");
      return resposta(204);
    }
    return resposta(200, atividades[Math.min(i++, atividades.length - 1)]);
  }) as unknown as typeof fetch & jest.Mock;
}

const tela = (f: typeof fetch, extra = {}) => (
  <TelaTreino
    apiUrl="http://api.teste"
    atletaId={1}
    atividadeId={101}
    fetchFn={f}
    aoFazerCheckin={jest.fn()}
    aoEditarCheckin={jest.fn()}
    {...extra}
  />
);

describe("cartão Check-in na tela do treino", () => {
  it("sem check-in e prazo aberto: texto, texto da API da carga e botão 'Fazer check-in'", async () => {
    const fazer = jest.fn();
    await render(tela(servidor([atividadesCheckin.semCheckin]), { aoFazerCheckin: fazer }));
    const cartao = await screen.findByTestId("cartao-checkin");
    expect(within(cartao).getByText("Você ainda não fez o check-in deste treino.")).toBeTruthy();
    expect(within(cartao).getByText("Sem check-in: a carga pela PSE precisa da PSE do treino.")).toBeTruthy();
    expect(within(cartao).getByText("assignment:20")).toBeTruthy();
    expect(screen.queryByTestId("cartao-carga-pse")).toBeNull();
    await fireEvent.press(within(cartao).getByText("Fazer check-in"));
    expect(fazer).toHaveBeenCalled();
  });

  it("sem check-in e prazo vencido: aviso de prazo com info-outline e sem o botão", async () => {
    await render(tela(servidor([atividadesCheckin.foraDoPrazo])));
    const cartao = await screen.findByTestId("cartao-checkin");
    const aviso = within(cartao).getByTestId("aviso-prazo");
    expect(within(aviso).getByText("info-outline:20")).toBeTruthy();
    expect(within(aviso).getByText("O prazo para fazer o check-in deste treino acabou (7 dias depois do treino).")).toBeTruthy();
    expect(within(cartao).queryByText("Fazer check-in")).toBeNull();
    expect(within(cartao).queryByText(/Sem check-in: a carga/)).toBeNull();
  });

  it.each(["multiesportePai", "troca"] as const)("%s sem check-in e sem prazo: o cartão não aparece", async (chave) => {
    await render(tela(servidor([atividadesCheckin[chave]])));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByTestId("cartao-checkin")).toBeNull();
    expect(screen.queryByTestId("cartao-carga-pse")).toBeNull();
  });

  it("com check-in: linhas de PSE, sensação e observação, texto livre, Editar e Apagar", async () => {
    const editar = jest.fn();
    await render(tela(servidor([atividadesCheckin.comCheckin]), { aoEditarCheckin: editar }));
    const cartao = await screen.findByTestId("cartao-checkin");
    expect(within(cartao).getByLabelText("Esforço (PSE), 5 · difícil")).toBeTruthy();
    expect(within(cartao).getByLabelText("Sensação, Bem")).toBeTruthy();
    expect(within(cartao).getByLabelText("Observação, Cansaço, Trabalho ou estresse")).toBeTruthy();
    expect(within(cartao).getByText(MARCADOR)).toBeTruthy();
    expect(within(cartao).queryByText("Fazer check-in")).toBeNull();
    await fireEvent.press(within(cartao).getByText("Editar"));
    expect(editar).toHaveBeenCalled();
  });

  it("com check-in 'nada a relatar': mostra a frase e nenhum texto livre", async () => {
    await render(tela(servidor([atividadesCheckin.nada])));
    const cartao = await screen.findByTestId("cartao-checkin");
    expect(within(cartao).getByLabelText("Observação, Nada a relatar")).toBeTruthy();
  });

  it("com check-in vence o prazo: ainda mostra Editar (checkin_aberto falso não importa)", async () => {
    await render(tela(servidor([{ ...atividadesCheckin.comCheckin, checkin_aberto: false } as Atividade])));
    const cartao = await screen.findByTestId("cartao-checkin");
    expect(within(cartao).getByText("Editar")).toBeTruthy();
  });

  it("o cartão vem depois do resumo e antes do clima", async () => {
    await render(tela(servidor([atividadesCheckin.comCheckin])));
    await screen.findByTestId("cartao-checkin");
    const ordem = ["cartao-resumo", "cartao-checkin", "cartao-carga-pse", "cartao-clima"].map((id) => screen.getByTestId(id));
    const arvore = JSON.stringify(screen.toJSON());
    const posicoes = ["cartao-resumo", "cartao-checkin", "cartao-carga-pse", "cartao-clima"].map((id) => arvore.indexOf(`"${id}"`));
    expect([...posicoes].sort((a, b) => a - b)).toEqual(posicoes);
    expect(ordem).toHaveLength(4);
  });

  it("sem os callbacks (uso antigo da tela), os cartões não aparecem", async () => {
    await render(tela(servidor([atividadesCheckin.comCheckin]), { aoFazerCheckin: undefined, aoEditarCheckin: undefined }));
    await screen.findByTestId("cartao-resumo");
    expect(screen.queryByTestId("cartao-checkin")).toBeNull();
  });

  it("apagar: diálogo, 'Cancelar' não chama a API; 'Apagar' chama DELETE, busca o treino e mostra o cartão sem check-in", async () => {
    const f = servidor([atividadesCheckin.comCheckin, atividadesCheckin.semCheckin]);
    await render(tela(f));
    await screen.findByTestId("cartao-checkin");
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    expect(screen.getByText("Apagar este check-in?")).toBeTruthy();
    await fireEvent.press(screen.getByText("Cancelar"));
    expect(f.mock.calls.filter((c) => c[1]?.method === "DELETE")).toHaveLength(0);
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    await fireEvent.press(screen.getByText("Apagar"));
    await screen.findByText("Você ainda não fez o check-in deste treino.");
    expect(screen.getByText("Check-in apagado.")).toBeTruthy();
    expect(String(f.mock.calls.find((c) => c[1]?.method === "DELETE")![0])).toBe("http://api.teste/atletas/1/atividades/101/checkin");
    expect(screen.queryByTestId("cartao-carga-pse")).toBeNull();
  });

  it("erro ao apagar: aviso e o check-in continua", async () => {
    await render(tela(servidor([atividadesCheckin.comCheckin], "falha")));
    await screen.findByTestId("cartao-checkin");
    await fireEvent.press(screen.getByTestId("apagar-checkin"));
    await fireEvent.press(screen.getByText("Apagar"));
    await screen.findByText("Não foi possível apagar. Tente de novo.");
    expect(screen.getByLabelText("Esforço (PSE), 5 · difícil")).toBeTruthy();
  });
});

describe("cartão Carga pela PSE", () => {
  it("calculada: valor_texto em destaque, texto da API e a nota sobre a carga do relógio", async () => {
    await render(tela(servidor([atividadesCheckin.comCheckin])));
    const cartao = await screen.findByTestId("cartao-carga-pse");
    expect(within(cartao).getByText("260 UA")).toBeTruthy();
    expect(within(cartao).getByText("Carga pela PSE: 5 x 52 min = 260 UA.")).toBeTruthy();
    expect(within(cartao).getByText("Não se compara com a carga do relógio (pontos): são escalas diferentes.")).toBeTruthy();
  });

  it("mostra valor e texto exatamente como vieram da API (o app não calcula)", async () => {
    const a = {
      ...atividadesCheckin.comCheckin,
      carga_pse: { ...atividadesCheckin.comCheckin.carga_pse!, valor_texto: "999 UA", texto: "Texto da API." },
    } as Atividade;
    await render(tela(servidor([a])));
    const cartao = await screen.findByTestId("cartao-carga-pse");
    expect(within(cartao).getByText("999 UA")).toBeTruthy();
    expect(within(cartao).getByText("Texto da API.")).toBeTruthy();
  });

  it("pse 0 vale: '0 UA'", async () => {
    const a = {
      ...atividadesCheckin.comCheckin,
      carga_pse: { ...atividadesCheckin.comCheckin.carga_pse!, pse: 0, valor: 0, valor_texto: "0 UA" },
    } as Atividade;
    await render(tela(servidor([a])));
    expect(within(await screen.findByTestId("cartao-carga-pse")).getByText("0 UA")).toBeTruthy();
  });

  it("sem_duracao: só o texto da API, sem número", async () => {
    await render(tela(servidor([atividadesCheckin.semDuracao])));
    const cartao = await screen.findByTestId("cartao-carga-pse");
    expect(within(cartao).getByText("Sem duração para calcular a carga pela PSE.")).toBeTruthy();
    expect(within(cartao).queryByText(/UA/)).toBeNull();
  });

  it("sem carga_pse (atividade não elegível), o cartão não aparece", async () => {
    await render(tela(servidor([{ ...atividadesCheckin.comCheckin, carga_pse: null } as Atividade])));
    await screen.findByTestId("cartao-checkin");
    expect(screen.queryByTestId("cartao-carga-pse")).toBeNull();
  });

  it("atualizar muda: busca o treino de novo sem voltar ao esqueleto", async () => {
    const f = servidor([atividadesCheckin.semCheckin, atividadesCheckin.comCheckin]);
    const { rerender } = await render(tela(f, { atualizar: 0 }));
    await screen.findByText("Fazer check-in");
    await rerender(tela(f, { atualizar: 1 }));
    expect(screen.queryByText("Carregando o treino...")).toBeNull();
    await waitFor(() => expect(screen.getByTestId("cartao-carga-pse")).toBeTruthy());
  });
});
