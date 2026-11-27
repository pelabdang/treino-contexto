import type { Atividade } from "@treino/api-client";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react-native";

import { atividades } from "../__fixtures__/atividades";
import { ORIGEM_AUTOMATICO } from "../src/componentes/CartaoFeedback";
import { TelaInicio } from "../src/componentes/TelaInicio";
import type { ItemTreino } from "../src/treinos/api";

jest.mock("@expo/vector-icons", () => require("../__fixtures__/iconesFalsos"));

const resposta = (status: number, corpo?: unknown) => ({ ok: status >= 200 && status < 300, status, json: async () => corpo }) as Response;
const item = (id: number, extra: Partial<ItemTreino> = {}): ItemTreino => ({
  atividade_id: id,
  inicio: "2025-03-18T09:30:00Z",
  data_local: "2025-03-18",
  hora_local: "06:30",
  modalidade: "corrida",
  subtipo: "rua",
  tipo_treino: "leve",
  duracao_s: 3125,
  duracao: "0:52:05",
  distancia_m: 10000,
  distancia: "10,00 km",
  destaque: null,
  checkin_estado: "feito",
  feedback_estado: "pronto",
  normal_estado: "dentro", // a lista e o detalhe do mesmo treino concordam (normal_treino@1)
  ...extra,
});
const lista = (itens: ItemTreino[]) => ({ atleta_id: 1, limite: 5, itens, proximo: null });
const pend = (id: number, modalidade = "ciclismo") => ({ atividade_id: id, data_local: "2025-03-19", hora_local: "06:30", duracao: "0:52:10", modalidade, titulo: `Treino ${id}` });
const dia = (i: number, ctl: number, atl: number) => ({ data: `2025-03-${7 + i}`, ctl, atl, tsb: 0, carga: 0, atividades: 0, calculadas: 0, sem_carga: 0, aprendendo: false, ctl_texto: `${ctl}`, atl_texto: `${atl}` });
const quinzena = { atleta_id: 1, aviso: null, dias: [dia(0, 40, 50), dia(1, 44, 58)], frase_forma: { tipo: "acima", tendencia: "subiu", texto: "Frase da quinzena.", versao: "frase_forma@1" }, periodo: null, totais: {}, versao: "serie_carga@2", versao_carga: "carga@2" };
const comFeedback = (fb: unknown, extra: Partial<Atividade> = {}) => ({ ...atividades.ok, feedback: fb, ...extra }) as Atividade;
const feedbackPronto = { estado: "pronto", texto: "Linha 1\nLinha 2\nLinha 3\nLinha 4", origem: "automatico", checkin_aberto: false };

type Rotas = { lista?: unknown; atividade?: unknown; pendentes?: unknown; quinzena?: unknown; falhar?: string[] };
function servidor(r: Rotas = {}) {
  return jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input).replace("http://api.teste", "");
    const quebra = (nome: string) => r.falhar?.includes(nome);
    if (url.includes("/checkins/pendentes")) return quebra("pendentes") ? resposta(500, {}) : resposta(200, r.pendentes ?? { dias: 7, pendentes: [], total: 0 });
    if (url.includes("/carga")) return quebra("quinzena") ? resposta(500, {}) : resposta(200, r.quinzena ?? quinzena);
    if (/\/atividades\/\d+$/.test(url)) return quebra("atividade") ? resposta(500, {}) : resposta(200, r.atividade ?? comFeedback(feedbackPronto));
    return quebra("lista") ? resposta(500, {}) : resposta(200, r.lista ?? lista([item(1)]));
  }) as unknown as jest.Mock & typeof fetch;
}
const urls = (f: jest.Mock) => f.mock.calls.map((c) => String(c[0]).replace("http://api.teste", ""));

const props = () => ({ aoAbrirTreino: jest.fn(), aoResponderCheckin: jest.fn(), aoVerTodos: jest.fn() });
const tela = (f: typeof fetch, extra = {}) => <TelaInicio apiUrl="http://api.teste" atletaId={1} fetchFn={f} nome="Ana Souza" agora={() => new Date(2025, 2, 21)} {...props()} {...extra} />;

describe("início v3", () => {
  it("saudação com o primeiro nome e a data de hoje", async () => {
    await render(tela(servidor()));
    expect(screen.getByText("Olá, Ana")).toBeTruthy();
    expect(screen.getByTestId("data-hoje").props.children).toBe("sexta, 21/03");
    await screen.findByTestId("ultimo-treino");
  });

  it("busca a lista (5), o treino, os pendentes (7 dias) e a quinzena (ultimos=14)", async () => {
    const f = servidor();
    await render(tela(f));
    await screen.findByTestId("quinzena");
    await screen.findByTestId("numero-treino");
    const u = urls(f);
    expect(u).toContain("/atletas/1/atividades?limite=5");
    expect(u).toContain("/atletas/1/atividades/1");
    expect(u).toContain("/atletas/1/checkins/pendentes?dias=7");
    expect(u).toContain("/atletas/1/carga?ultimos=14");
  });

  it("cenário 2: número, apoio, selo de normal e as três primeiras linhas do feedback", async () => {
    const p = props();
    await render(tela(servidor(), p));
    await screen.findByTestId("feedback-resumo");
    expect(screen.getByTestId("numero-treino").props.children).toBe("5:12");
    expect(screen.getByText("10,00 km · 0:52:05 · FC média 152 bpm")).toBeTruthy();
    expect(screen.getByTestId("selo-normal-dentro")).toBeTruthy();
    expect(screen.getByText("Linha 1\nLinha 2\nLinha 3")).toBeTruthy();
    expect(screen.getByText(ORIGEM_AUTOMATICO)).toBeTruthy();
    expect(screen.queryByTestId("convite-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("ler-feedback"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });

  it("o selo do normal segue o normal_estado da lista: o mesmo treino não muda de selo entre as telas", async () => {
    const base = atividades.ok.linha_base!;
    const detalhe = comFeedback(feedbackPronto, {
      linha_base: { ...base, metricas: [{ ...base.metricas[0], chave: "pace_medio", estado: "dentro" }, { ...base.metricas[1], chave: "fc_media", estado: "fora", diferenca_texto: "11 bpm acima" }] },
    } as Partial<Atividade>);
    await render(tela(servidor({ lista: lista([item(1, { normal_estado: "fora" })]), atividade: detalhe })));
    const selo = await screen.findByTestId("selo-normal-fora");
    expect(within(selo).getByText("Fora do seu normal: 11 bpm acima")).toBeTruthy();
    expect(screen.queryByTestId("selo-normal-dentro")).toBeNull();
  });

  it("cenário 1: sem check-in, o convite fica dentro do cartão e abre o check-in; mostra '+ N treinos'", async () => {
    const p = props();
    const f = servidor({
      lista: lista([item(1, { checkin_estado: "pendente", feedback_estado: "sem_checkin" })]),
      atividade: comFeedback({ estado: "sem_checkin", checkin_aberto: true, mensagem: "Faça o check-in para ver o feedback." }),
      pendentes: { dias: 7, pendentes: [pend(1, "corrida"), pend(2), pend(3)], total: 3 },
    });
    await render(tela(f, p));
    const convite = await screen.findByTestId("convite-checkin");
    expect(within(screen.getByTestId("ultimo-treino")).getByTestId("convite-checkin")).toBe(convite);
    expect(within(convite).getByText("Responda o check-in e receba o feedback deste treino.")).toBeTruthy();
    expect(screen.getByTestId("outros-sem-checkin").props.children).toBe("+ 2 treinos sem check-in");
    expect(screen.queryByTestId("faixa-outro-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("responder-checkin"));
    expect(p.aoResponderCheckin).toHaveBeenCalledWith(1);
  });

  it("cenário 2 com outro treino sem check-in: faixa abaixo do cartão 'Como foi o ciclismo?'", async () => {
    const p = props();
    const f = servidor({ pendentes: { dias: 7, pendentes: [pend(2)], total: 1 } });
    await render(tela(f, p));
    const faixa = await screen.findByTestId("faixa-outro-checkin");
    expect(within(faixa).getByText("Como foi o ciclismo?")).toBeTruthy();
    expect(within(faixa).getByText("qua 19/03")).toBeTruthy();
    expect(screen.queryByTestId("convite-checkin")).toBeNull();
    await fireEvent.press(screen.getByTestId("responder-outro"));
    expect(p.aoResponderCheckin).toHaveBeenCalledWith(2);
  });

  it("feedback pendente: mostra a mensagem da API no lugar das linhas", async () => {
    const f = servidor({ atividade: comFeedback({ estado: "pendente", mensagem: "Ainda estamos preparando o feedback." }) });
    await render(tela(f));
    expect((await screen.findByTestId("feedback-estado")).props.children.props.children).toBe("Ainda estamos preparando o feedback.");
    expect(screen.queryByTestId("feedback-resumo")).toBeNull();
  });

  it("quinzena com a frase da API e treinos recentes (do 2º ao 5º) com 'Ver todos'", async () => {
    const p = props();
    const f = servidor({ lista: lista([item(1), item(2), item(3), item(4), item(5)]) });
    await render(tela(f, p));
    await screen.findByTestId("quinzena");
    expect(screen.getByTestId("frase-quinzena").props.children).toBe("Frase da quinzena.");
    const recentes = screen.getByTestId("recentes");
    for (const id of [2, 3, 4, 5]) expect(within(recentes).getByTestId(`treino-${id}`)).toBeTruthy();
    expect(within(recentes).queryByTestId("treino-1")).toBeNull();
    await fireEvent.press(within(recentes).getByTestId("treino-3"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(3);
    await fireEvent.press(screen.getByTestId("ver-todos"));
    expect(p.aoVerTodos).toHaveBeenCalled();
  });

  it("um treino só: sem 'Treinos recentes'", async () => {
    await render(tela(servidor()));
    await screen.findByTestId("ultimo-treino");
    expect(screen.queryByTestId("recentes")).toBeNull();
  });

  it("sem treinos: frase e botão de enviar o arquivo", async () => {
    await render(tela(servidor({ lista: lista([]) })));
    await screen.findByTestId("estado-vazio");
    expect(screen.getByText("Nenhum treino ainda. Envie o arquivo do seu relógio e a análise aparece aqui.")).toBeTruthy();
    expect(screen.getByText("Enviar arquivo FIT")).toBeTruthy();
    expect(screen.queryByTestId("ultimo-treino")).toBeNull();
  });

  it("carregando: texto para leitor de tela", async () => {
    const f = jest.fn(() => new Promise<Response>(() => {})) as unknown as typeof fetch;
    await render(tela(f));
    expect(screen.getAllByText("Carregando").length).toBeGreaterThan(0);
  });

  it("cada cartão falha sozinho e 'Tentar de novo' busca de novo", async () => {
    let quinzenaFalha = true;
    const base = servidor();
    const f = jest.fn(async (input: RequestInfo | URL) => (String(input).includes("/carga") && quinzenaFalha ? resposta(500, {}) : base(input))) as unknown as typeof fetch;
    await render(tela(f));
    await screen.findByTestId("erro-quinzena");
    expect(screen.getByTestId("ultimo-treino")).toBeTruthy(); // o resto da tela segue
    quinzenaFalha = false;
    await fireEvent.press(screen.getByTestId("erro-quinzena-tentar"));
    await screen.findByTestId("quinzena");
    expect(screen.queryByTestId("erro-quinzena")).toBeNull();
  });

  it("erro na lista: mensagem do cartão", async () => {
    await render(tela(servidor({ falhar: ["lista"] })));
    expect(await screen.findByTestId("erro-ultimo")).toBeTruthy();
    expect(screen.queryByTestId("ultimo-treino")).toBeNull();
  });

  it("erro no detalhe: o cartão fica com o que a lista traz e avisa", async () => {
    await render(tela(servidor({ falhar: ["atividade"] })));
    expect(await screen.findByTestId("erro-detalhe")).toBeTruthy();
    expect(screen.getByTestId("numero-treino").props.children).toBe("0:52:05");
  });

  it("tocar no cartão do último treino abre o treino; o rótulo falado traz o número e o selo", async () => {
    const p = props();
    await render(tela(servidor(), p));
    const botao = await screen.findByTestId("abrir-ultimo-treino");
    await waitFor(() => expect(screen.getByTestId("abrir-ultimo-treino").props.accessibilityLabel).toContain("Dentro do seu normal"));
    expect(botao.props.accessibilityLabel).toContain("Pace médio, 5:12");
    await fireEvent.press(screen.getByTestId("abrir-ultimo-treino"));
    expect(p.aoAbrirTreino).toHaveBeenCalledWith(1);
  });
});
