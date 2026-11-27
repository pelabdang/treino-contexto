import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

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
  it("mostra o cartão com modalidade, data e hora, tipo, valor principal, meta e um selo só", async () => {
    const f = servidor(() =>
      resposta(200, lista([item(1, { destaque: "5 x 1 km a 4:11 min/km", checkin_estado: "pendente", feedback_estado: "sem_checkin" }), item(2, { modalidade: "natacao", tipo_treino: null, distancia: null, checkin_estado: "vencido", feedback_estado: "desatualizado" })])),
    );
    await render(tela(f));
    await screen.findByTestId("treino-1");
    expect(screen.getAllByText("Corrida")).toBeTruthy();
    expect(screen.getAllByText("18/03/25 às 06:30")).toHaveLength(2);
    expect(screen.getByText("Intervalado")).toBeTruthy();
    // Com texto da API, ele é o valor principal e a duração vai para a meta; sem ele, a duração é o valor principal.
    expect(screen.getByTestId("principal-1").props.children).toBe("5 x 1 km a 4:11 min/km");
    expect(screen.getByText("0:52:05 · 10,00 km")).toBeTruthy();
    expect(screen.getByTestId("principal-2").props.children).toBe("0:52:05");
    expect(screen.getByTestId("selo-pendente-1")).toBeTruthy();
    expect(screen.getByText("Check-in vencido")).toBeTruthy();
    // Um selo por treino: o feedback não ganha selo.
    expect(screen.queryByText("Feedback desatualizado")).toBeNull();
    expect(screen.queryByText("Feedback pronto")).toBeNull();
    expect(screen.getAllByTestId(/^selo-/)).toHaveLength(2);
    expect(screen.getByTestId("treino-1").props.accessibilityLabel).toContain("Sem check-in");
    expect(within(screen.getByTestId("selo-pendente-1")).getByText("Sem check-in")).toBeTruthy();
  });

  it("check-in feito não tem selo", async () => {
    await render(tela(servidor(() => resposta(200, lista([item(1)])))));
    await screen.findByTestId("treino-1");
    expect(screen.queryAllByTestId(/^selo-/)).toHaveLength(0);
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
    expect(TEXTO_VAZIO).toBe("Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.");
    expect(screen.getAllByText("Enviar FIT")).toHaveLength(2); // o do cabeçalho e o do estado vazio
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

describe("aba Treinos: ajustes do #545", () => {
  it("o primeiro filtro é 'Todas as modalidades' e o cabeçalho tem 'Enviar FIT'", async () => {
    await render(tela(servidor(() => resposta(200, lista([item(1)])))));
    await screen.findByTestId("treino-1");
    expect(screen.getByText("Todas as modalidades")).toBeTruthy();
    expect(screen.queryByText("Todos")).toBeNull();
    expect(screen.getAllByText("Enviar FIT")).toHaveLength(1);
  });

  it("vazio com filtro não oferece o envio no estado vazio", async () => {
    await render(tela(servidor(() => resposta(200, lista([]))), { semCheckinInicial: true }));
    await screen.findByText(TEXTO_VAZIO_FILTRO);
    expect(screen.getAllByText("Enviar FIT")).toHaveLength(1);
  });

  // Bug apontado na revisão do #540: se o filtro muda durante a busca da página seguinte, a resposta atrasada é descartada
  // e `maisCarregando` ficava em true para sempre; a rolagem infinita parava.
  it("trocar o filtro durante 'carregar mais' não trava a rolagem infinita", async () => {
    let soltar: (r: Response) => void = () => {};
    const f = servidor((url) => {
      if (url.includes("antes_de=c1")) return new Promise<Response>((ok) => (soltar = ok));
      if (url.includes("antes_de=n1")) return resposta(200, lista([item(11, { modalidade: "natacao" })], null));
      if (url.includes("modalidade=natacao")) return resposta(200, lista([item(10, { modalidade: "natacao" })], "n1"));
      return resposta(200, lista([item(1)], "c1"));
    });
    await render(tela(f));
    await screen.findByTestId("treino-1");
    void fireEvent(screen.getByTestId("tela-treinos"), "endReached"); // página 2 fica pendente (não se espera)
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]).includes("antes_de=c1"))).toBe(true));
    await fireEvent.press(screen.getByTestId("chip-natacao")); // troca o filtro no meio da busca
    await screen.findByTestId("treino-10");
    soltar(resposta(200, lista([item(2)], null))); // a resposta atrasada chega e é descartada
    await fireEvent(screen.getByTestId("tela-treinos"), "endReached");
    await screen.findByTestId("treino-11"); // a página seguinte do novo filtro foi pedida
    expect(screen.queryByTestId("treino-2")).toBeNull();
    expect(screen.queryByTestId("carregando-mais")).toBeNull();
  });
});

describe("aba Treinos: selo do normal (#553)", () => {
  const selos = async (itens: ItemTreino[]) => {
    await render(tela(servidor(() => resposta(200, lista(itens)))));
    await screen.findByTestId(`treino-${itens[0].atividade_id}`);
  };

  it("fora do normal, no normal e aprendendo, com ícone e palavra", async () => {
    await selos([item(1, { normal_estado: "fora" }), item(2, { normal_estado: "dentro" }), item(3, { normal_estado: "aprendendo" })]);
    expect(within(screen.getByTestId("selo-fora-1")).getByText("Fora do normal")).toBeTruthy();
    expect(within(screen.getByTestId("selo-dentro-2")).getByText("No normal")).toBeTruthy();
    expect(within(screen.getByTestId("selo-aprendendo-3")).getByText("Aprendendo")).toBeTruthy();
    expect(screen.getByTestId("treino-1").props.accessibilityLabel).toContain("Fora do normal");
  });

  it("sem normal_estado, sem selo", async () => {
    await selos([item(1, { normal_estado: null })]);
    expect(screen.queryAllByTestId(/^selo-/)).toHaveLength(0);
  });

  it("um selo só, na prioridade: sem check-in > vencido > fora > no normal > aprendendo", async () => {
    await selos([
      item(1, { checkin_estado: "pendente", normal_estado: "fora" }),
      item(2, { checkin_estado: "vencido", normal_estado: "fora" }),
      item(3, { normal_estado: "fora" }),
      item(4, { normal_estado: "dentro" }),
    ]);
    expect(screen.getByTestId("selo-pendente-1")).toBeTruthy();
    expect(screen.getByTestId("selo-vencido-2")).toBeTruthy();
    expect(screen.getByTestId("selo-fora-3")).toBeTruthy();
    expect(screen.getByTestId("selo-dentro-4")).toBeTruthy();
    expect(screen.getAllByTestId(/^selo-/)).toHaveLength(4);
  });
});
