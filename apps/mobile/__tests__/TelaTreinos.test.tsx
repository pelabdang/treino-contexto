import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";

import { TEXTO_FIM, TEXTO_VAZIO, TEXTO_VAZIO_FILTRO, TelaTreinos } from "../src/componentes/TelaTreinos";
import { buscarTreinos, type ItemTreino } from "../src/treinos/api";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const item = (id: number, extra: Partial<ItemTreino> = {}): ItemTreino => ({
  atividade_id: id,
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  modalidade: "corrida",
  subtipo: "rua",
  tipo_treino: "intervalado",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
  distancia: "10,00 km",
  destaque: null,
  checkin_estado: "feito",
  feedback_estado: "pronto",
  normal_estado: null,
  ...extra,
});
const lista = (itens: ItemTreino[], proximo: string | null = null) => ({ atleta_id: 1, limite: 20, itens, proximo });

const urlDe = (f: jest.Mock, i: number) => String(f.mock.calls[i][0]).replace("http://api.teste", "");
const servidor = (resp: (url: string) => Response | Promise<Response>) => jest.fn(async (input: RequestInfo | URL) => resp(String(input))) as unknown as jest.Mock & typeof fetch;
const tela = (f: typeof fetch, extra = {}) => <TelaTreinos apiUrl="http://api.teste" atletaId={1} fetchFn={f} aoAbrirTreino={jest.fn()} {...extra} />;

describe("api da lista de treinos", () => {
  it("monta a consulta com limite, cursor, modalidade e check-in pendente", async () => {
    const f = servidor(() => resposta(200, lista([])));
    await buscarTreinos(3, { limite: 10, antesDe: "abc", modalidade: "natacao", checkinPendente: true }, { baseUrl: "http://api.teste", fetch: f });
    expect(urlDe(f, 0)).toBe("/atletas/3/atividades?limite=10&antes_de=abc&modalidade=natacao&checkin_pendente=true");
    const g = servidor(() => resposta(200, lista([])));
    await buscarTreinos(3, {}, { baseUrl: "http://api.teste", fetch: g });
    expect(urlDe(g, 0)).toBe("/atletas/3/atividades");
  });
});

describe("aba Treinos", () => {
  it("mostra o cartão com modalidade, data e hora, tipo, números, destaque e selos em ícone e palavra", async () => {
    const f = servidor(() =>
      resposta(200, lista([item(1, { destaque: "5 x 1 km a 4:11 min/km", checkin_estado: "pendente", feedback_estado: "sem_checkin" }), item(2, { modalidade: "natacao", tipo_treino: null, distancia: null, checkin_estado: "vencido", feedback_estado: "desatualizado" })])),
    );
    await render(tela(f));
    await screen.findByTestId("treino-1");
    expect(screen.getAllByText("Corrida")).toBeTruthy();
    expect(screen.getAllByText("18/03/25 às 06:30")).toHaveLength(2);
    expect(screen.getByText("Intervalado")).toBeTruthy();
    expect(screen.getAllByText("0:52:05")).toHaveLength(2);
    expect(screen.getByText("10,00 km")).toBeTruthy();
    expect(screen.getByTestId("destaque-1").props.children).toBe("5 x 1 km a 4:11 min/km");
    expect(screen.getByText("Check-in pendente")).toBeTruthy();
    expect(screen.getByText("Check-in vencido")).toBeTruthy();
    expect(screen.getByText("Feedback desatualizado")).toBeTruthy();
    expect(screen.queryByText("Feedback pronto")).toBeNull();
    expect(screen.getByTestId("treino-1").props.accessibilityLabel).toContain("Check-in pendente");
  });

  it("feedback pronto tem selo; check-in feito não", async () => {
    await render(tela(servidor(() => resposta(200, lista([item(1)])))));
    await screen.findByTestId("treino-1");
    expect(screen.getByText("Feedback pronto")).toBeTruthy();
    expect(screen.queryByText("Check-in pendente")).toBeNull();
  });

  it("tocar no cartão abre o treino", async () => {
    const aoAbrirTreino = jest.fn();
    await render(tela(servidor(() => resposta(200, lista([item(7)]))), { aoAbrirTreino }));
    await fireEvent.press(await screen.findByTestId("treino-7"));
    expect(aoAbrirTreino).toHaveBeenCalledWith(7);
  });

  it("rolagem infinita: ao chegar ao fim pede a próxima página pelo cursor, sem repetir itens, e mostra o fim da lista", async () => {
    const f = servidor((url) =>
      url.includes("antes_de=c1") ? resposta(200, lista([item(3), item(2)], null)) : resposta(200, lista([item(1), item(2)], "c1")),
    );
    await render(tela(f));
    await screen.findByTestId("treino-1");
    expect(screen.queryByTestId("fim-da-lista")).toBeNull();
    await fireEvent(screen.getByTestId("tela-treinos"), "endReached");
    await screen.findByTestId("treino-3");
    expect(urlDe(f, 1)).toContain("antes_de=c1");
    expect(screen.getAllByTestId("treino-2")).toHaveLength(1);
    expect(screen.getByText(TEXTO_FIM)).toBeTruthy();
  });

  it("erro ao carregar mais: avisa, mantém a lista e 'Tentar de novo' pede de novo", async () => {
    let falhar = true;
    const f = servidor((url) => (url.includes("antes_de=c1") ? (falhar ? resposta(500, {}) : resposta(200, lista([item(3)]))) : resposta(200, lista([item(1)], "c1"))));
    await render(tela(f));
    await screen.findByTestId("treino-1");
    await fireEvent(screen.getByTestId("tela-treinos"), "endReached");
    expect(await screen.findByText("Não foi possível carregar mais treinos.")).toBeTruthy();
    expect(screen.getByTestId("treino-1")).toBeTruthy();
    falhar = false;
    await fireEvent.press(screen.getByTestId("tentar-mais"));
    await screen.findByTestId("treino-3");
  });

  it("chips de modalidade e 'Sem check-in' mandam o filtro e recomeçam a lista", async () => {
    const f = servidor(() => resposta(200, lista([item(1)])));
    await render(tela(f));
    await screen.findByTestId("treino-1");
    await fireEvent.press(screen.getByTestId("chip-natacao"));
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]).includes("modalidade=natacao"))).toBe(true));
    expect(screen.getByTestId("chip-natacao").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("chip-sem-checkin"));
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]).includes("modalidade=natacao&checkin_pendente=true"))).toBe(true));
    expect(screen.getByTestId("chip-sem-checkin").props.accessibilityState.checked).toBe(true);
    await fireEvent.press(screen.getByTestId("chip-todos"));
    await waitFor(() => expect(urlDe(f, f.mock.calls.length - 1)).toBe("/atletas/1/atividades?limite=20&checkin_pendente=true"));
  });

  it("abre já filtrada pelos treinos sem check-in (link do Início)", async () => {
    const f = servidor(() => resposta(200, lista([item(1, { checkin_estado: "pendente" })])));
    await render(tela(f, { semCheckinInicial: true }));
    await screen.findByTestId("treino-1");
    expect(urlDe(f, 0)).toContain("checkin_pendente=true");
    expect(screen.getByTestId("chip-sem-checkin").props.accessibilityState.checked).toBe(true);
  });

  it("vazio: 'Nenhum treino ainda'; vazio com filtro tem frase própria", async () => {
    await render(tela(servidor(() => resposta(200, lista([])))));
    expect(await screen.findByText(TEXTO_VAZIO)).toBeTruthy();
    await render(tela(servidor(() => resposta(200, lista([]))), { semCheckinInicial: true }));
    expect(await screen.findByText(TEXTO_VAZIO_FILTRO)).toBeTruthy();
  });

  it("erro de rede e erro do servidor: frase e 'Tentar de novo' recarrega", async () => {
    let quebrar = true;
    const f = jest.fn(async () => {
      if (quebrar) throw new Error("rede");
      return resposta(200, lista([item(1)]));
    }) as unknown as typeof fetch;
    await render(tela(f));
    expect(await screen.findByText("Não foi possível falar com o servidor")).toBeTruthy();
    quebrar = false;
    await fireEvent.press(screen.getByTestId("tentar-de-novo"));
    await screen.findByTestId("treino-1");
    await render(tela(servidor(() => resposta(500, {}))));
    expect(await screen.findByText(/Não foi possível carregar os treinos/)).toBeTruthy();
  });

  it("carregando: mostra o texto de espera", async () => {
    await render(tela(jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch));
    expect(screen.getByText("Carregando seus treinos...")).toBeTruthy();
  });
});
